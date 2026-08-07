# tests/conftest.py
import os

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.ai import models as _ai  # noqa: F401
from app.core.database import Base
from app.ingredients import models as _ingredients  # noqa: F401
from app.inventory import models as _inventory  # noqa: F401
from app.meal_plans import models as _meal_plans  # noqa: F401
from app.nutrition import models as _nutrition  # noqa: F401
from app.recipes import models as _recipes  # noqa: F401
from app.shopping import models as _shopping  # noqa: F401

# import 全部 model 模块, 让 Base.metadata 收齐所有表(create_all 需要)
from app.users import models as _users  # noqa: F401


def _test_db_url() -> str:
    """测试库 URL: 优先 TEST_DATABASE_URL; 否则由 dev URL 换库名为 *_test。"""
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        return url
    from app.core.config import get_settings
    base = get_settings().database_url
    return base.rsplit("/", 1)[0] + "/mealforge_test"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _engine():
    """session 级: 建一次 schema(create_all), 跑完 drop, 独立测试库不碰 dev。"""
    engine = create_async_engine(_test_db_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db(_engine) -> AsyncSession:
    """每测试一个事务, 结束回滚 → 零残留、测试间隔离。种子数据用 flush(不 commit)。"""
    conn = await _engine.connect()
    trans = await conn.begin()
    session = AsyncSession(
        bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await conn.close()


@pytest_asyncio.fixture(loop_scope="session")
async def api_client(_engine):
    """HTTP 层测试客户端: 绕过 Clerk auth, 复用回滚事务。

    端点内的 db.commit() 经 join_transaction_mode='create_savepoint' 只提交
    savepoint, 外层事务结束仍整体回滚 → HTTP 测试也零残留。
    返回 (client, session, user)。
    """
    from httpx import ASGITransport, AsyncClient

    from app.auth.dependencies import get_current_user
    from app.core.database import get_db
    from app.main import app
    from app.users.models import User

    conn = await _engine.connect()
    trans = await conn.begin()
    session = AsyncSession(
        bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    user = User(clerk_user_id="api_test_user")
    session.add(user)
    await session.flush()

    async def _override_db():
        yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session, user

    app.dependency_overrides.clear()
    await session.close()
    await trans.rollback()
    await conn.close()