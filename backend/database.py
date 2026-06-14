from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

# libpq/psycopg2 query params that asyncpg does not accept as connect kwargs.
# SSL is handled separately via connect_args below.
_INCOMPATIBLE_QUERY_PARAMS = {"sslmode", "channel_binding"}

def _normalize_async_url(url: str) -> str:
    """Force the asyncpg driver and drop libpq-only query params.

    Hosting providers hand out a bare ``postgresql://`` URL (which SQLAlchemy
    maps to psycopg2, not installed) with ``?sslmode=...&channel_binding=...``
    query params that asyncpg rejects as unexpected keyword arguments."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
            break

    parts = urlsplit(url)
    kept = [(k, v) for k, v in parse_qsl(parts.query) if k not in _INCOMPATIBLE_QUERY_PARAMS]
    return urlunsplit(parts._replace(query=urlencode(kept)))

DATABASE_URL = _normalize_async_url(settings.DATABASE_URL)

connect_args = {"ssl": "require"} if "neon.tech" in DATABASE_URL else {}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
