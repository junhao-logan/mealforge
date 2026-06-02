from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.users.models import User

settings = get_settings()
_bearer = HTTPBearer(auto_error=True)

# 实例化一次；JWKS 在首次用时拉取并缓存（默认 cache_jwk_set=True, lifespan=300s）
_jwks_client = PyJWKClient(settings.clerk_jwks_url)


def _verify_clerk_jwt(token: str) -> dict[str, Any]:
    """同步验签：取签名公钥 + 验 RS256/iss/exp。放 threadpool 跑，避免堵事件循环。"""
    signing_key = _jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=settings.clerk_issuer,
        options={"require": ["exp", "iat", "sub"], "verify_aud": False},
    )


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        claims = await run_in_threadpool(_verify_clerk_jwt, creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or expired token"
        ) from exc

    # azp 校验：留空则跳过（dev 裸 token 测试用）
    if settings.clerk_authorized_parties:
        if claims.get("azp") not in settings.clerk_authorized_parties:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Untrusted party")

    clerk_user_id: str = claims["sub"]
    email: str | None = claims.get("email")

    # JIT provisioning：首次见到这个 sub 就建影子行
    user = (
        await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
    ).scalar_one_or_none()

    if user is None:
        user = User(clerk_user_id=clerk_user_id, email=email)
        db.add(user)
        try:
            await db.commit()
        except IntegrityError:
            # 并发首请求竞态：另一个请求抢先插了，回滚后重读
            await db.rollback()
            user = (
                await db.execute(
                    select(User).where(User.clerk_user_id == clerk_user_id)
                )
            ).scalar_one()
        else:
            await db.refresh(user)
    elif email and user.email != email:
        user.email = email
        await db.commit()
        await db.refresh(user)

    return user