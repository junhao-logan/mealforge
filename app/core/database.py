from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# Stable, deterministic constraint names so Alembic autogenerate produces
# clean, reviewable diffs instead of random hashes.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _build_connect_args(database_url: str) -> dict:
    """连接参数按目标动态决定。

    Neon(及一切 PgBouncer 事务模式的 pooled 端点)有两个约束:

    1. 不支持 prepared statements: 每条语句可能落到不同后端连接, asyncpg 缓存的
       statement 在新连接上不存在, 报
       `prepared statement "__asyncpg_stmt_N__" does not exist`。
       故必须 statement_cache_size=0 关闭缓存。

    2. 强制 SSL, 但 asyncpg 不认 URL 里的 ?sslmode=require(那是 psycopg 语法)。
       asyncpg 需通过 connect_args 传 ssl 参数。传 ssl=True 即启用 SSL 且校验证书。

    这是【按需】配置, 非全局:
    本地直连 Postgres 无 PgBouncer、无强制 SSL, prepared statement 是有益优化,
    关掉是白白损失性能, SSL 也非必需。故仅在识别为 pooled 端点时应用这两项。

    识别依据: 主机名含 'neon.tech'(Neon 托管)或 'pooler'(通用 PgBouncer 池)。
    """
    pooled_markers = ("neon.tech", "pooler")
    is_pooled = any(marker in database_url for marker in pooled_markers)
    if is_pooled:
        return {
            "statement_cache_size": 0,  # 关闭 prepared statement 缓存(PgBouncer 事务模式必需)
            "ssl": True,                # 启用 SSL(Neon 强制); 替代 URL 里的 sslmode 参数
        }
    return {}


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_build_connect_args(settings.database_url),
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session