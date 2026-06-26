from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_settings = get_settings()

# ── SQLAlchemy async engine + session factory ──────────────────────────────────
engine = create_async_engine(
    _settings.database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session


# ── Redis ──────────────────────────────────────────────────────────────────────
_redis_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            _settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


# ── JWT Auth ───────────────────────────────────────────────────────────────────
_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(_oauth2)) -> dict:
    """Validate Bearer JWT and return the payload. Raises 401 on failure."""
    cfg = get_settings()
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, cfg.secret_key, algorithms=[cfg.algorithm])
        username: str | None = payload.get("sub")
        if not username:
            raise exc
        return {"username": username}
    except JWTError:
        raise exc
