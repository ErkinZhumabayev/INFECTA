# Database configuration and session management

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import config


class DatabaseConfig:
    """Database connection settings"""
    # These should be set via environment variables
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "viralabs"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    
    @classmethod
    def get_database_url(cls) -> str:
        return (
            f"postgresql+asyncpg://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )


# Create async engine
engine = create_async_engine(
    DatabaseConfig.get_database_url(),
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables (for development)"""
    from app.game.models.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await engine.dispose()
