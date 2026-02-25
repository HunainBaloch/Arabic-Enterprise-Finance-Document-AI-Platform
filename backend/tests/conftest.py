"""
conftest.py
───────────
Shared pytest fixtures for the Arabic Enterprise Finance Document AI Platform.
Uses an isolated SQLite in-memory database and a TestClient with mocked AI services.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure the backend app directory is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Lightweight SQLite for tests (avoids Postgres dependency) ─────────
# File-based so all connections (API + worker in e2e) share the same DB.
# :memory: + StaticPool can fail when TestClient uses a different event loop.
# Use a dir outside .pytest-tmp so pytest cleanup doesn't delete an open DB.
_test_db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".test-db"))
os.makedirs(_test_db_dir, exist_ok=True)
_test_db_path = os.path.join(_test_db_dir, "test.db").replace("\\", "/")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{_test_db_path}"

from app.db.base_class import Base  # noqa: E402
from app.db.session import get_db   # noqa: E402
from app.main import app             # noqa: E402

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


# ── JWT helper fixtures ────────────────────────────────────────────────────────
from app.core.security import get_password_hash, create_access_token  # noqa: E402
from app.models.user import User  # noqa: E402
from datetime import timedelta


@pytest_asyncio.fixture(autouse=True)
async def create_tables():
    """Create all tables in the in-memory SQLite database once per session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def reviewer_user(db_session: AsyncSession) -> User:
    """Creates and returns a reviewer-role test user."""
    user = User(
        email="reviewer@test.com",
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True,
        role="reviewer",
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@test.com",
        hashed_password=get_password_hash("AdminPass123!"),
        is_active=True,
        role="admin",
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def make_bearer_token(user: User) -> str:
    return create_access_token({"sub": str(user.id)}, expires_delta=timedelta(minutes=60))


@pytest.fixture
def client(reviewer_user) -> Generator:
    """Sync test client with DB and auth overrides, reviewer role."""
    app.dependency_overrides[get_db] = override_get_db
    token = make_bearer_token(reviewer_user)
    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {token}"
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client() -> Generator:
    """Unauthenticated test client."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
