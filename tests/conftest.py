"""
tests/conftest.py — pytest 全局 fixtures
"""
import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, get_db, get_engine
from app.core.security import create_access_token
from app.main import app
from app.models.user import User
from app.core.security import hash_password


# ── Event Loop ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop() -> Any:
    """session 级 event loop（macOS/Linux）"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── DB ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    每个测试函数独立的 DB session。
    测试完成后回滚，不污染真实数据库。
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = get_db.__wrapped__  # type: ignore[attr-defined]
    # 重建 session（lifespan 外）
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession,
        expire_on_commit=False, autoflush=False, autocommit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── HTTP Client ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """带 DB session 的 async HTTP client"""
    # 覆盖 get_db dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Auth Fixtures ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """带有效 JWT 的 Authorization header"""
    token = create_access_token({"sub": str(test_user.id), "username": test_user.username})
    return {"Authorization": f"Bearer {token}"}
