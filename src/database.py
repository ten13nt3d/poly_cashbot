"""Database session management with SQLAlchemy 2.0 async support."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from .config import settings
from .models.base import Base

# Configure structured logging
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database engine and session lifecycle.

    Provides:
    - Connection pooling with configurable pool size
    - Async session factory
    - Health check capabilities
    - Graceful shutdown
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_pre_ping: bool = True,
        use_pool: bool = True,
    ) -> None:
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL (defaults to settings.database_url)
            echo: Enable SQL query logging
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
            pool_pre_ping: Enable connection health checks
            use_pool: Use connection pooling (False for testing)
        """
        self.database_url = database_url or settings.database_url
        self.echo = echo

        # Engine configuration
        engine_kwargs = {
            "url": self.database_url,
            "echo": echo,
            "pool_pre_ping": pool_pre_ping,
        }

        # Use NullPool for testing, AsyncAdaptedQueuePool for production
        if not use_pool:
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
            engine_kwargs["pool_size"] = pool_size
            engine_kwargs["max_overflow"] = max_overflow

        self._engine: Optional[AsyncEngine] = None
        self._async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None
        self._engine_kwargs = engine_kwargs

        logger.info(
            "DatabaseManager initialized",
            extra={
                "database_url": self.database_url.split("@")[-1],  # Hide credentials
                "pool_size": pool_size if use_pool else "NullPool",
                "max_overflow": max_overflow if use_pool else "N/A",
            },
        )

    @property
    def engine(self) -> AsyncEngine:
        """Get or create database engine."""
        if self._engine is None:
            self._engine = create_async_engine(**self._engine_kwargs)
            logger.info("Database engine created")
        return self._engine

    @property
    def session_maker(self) -> async_sessionmaker[AsyncSession]:
        """Get or create session factory."""
        if self._async_session_maker is None:
            self._async_session_maker = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Prevent lazy loading after commit
                autoflush=False,  # Explicit control over flushing
            )
            logger.info("Session factory created")
        return self._async_session_maker

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """
        Create a database session context manager.

        Usage:
            async with db_manager.session() as session:
                result = await session.execute(select(Market))
                await session.commit()

        Yields:
            AsyncSession: Database session
        """
        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(
                    "Session rolled back due to error",
                    extra={"error": str(e), "error_type": type(e).__name__},
                )
                raise
            finally:
                await session.close()

    async def create_all_tables(self) -> None:
        """
        Create all database tables.

        WARNING: Only use in development/testing.
        Use Alembic migrations in production.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created")

    async def drop_all_tables(self) -> None:
        """
        Drop all database tables.

        WARNING: Destructive operation. Only use in testing.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")

    async def health_check(self) -> bool:
        """
        Check database connectivity.

        Returns:
            bool: True if database is accessible
        """
        try:
            async with self.session() as session:
                await session.execute("SELECT 1")
            logger.info("Database health check passed")
            return True
        except Exception as e:
            logger.error(
                "Database health check failed",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            return False

    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connections closed")
            self._engine = None
            self._async_session_maker = None


# Global database manager instance
db_manager = DatabaseManager(
    echo=settings.log_level == "DEBUG",
    pool_size=5,
    max_overflow=10,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Dependency injection function for FastAPI or other frameworks.

    Usage in FastAPI:
        @app.get("/markets")
        async def get_markets(session: AsyncSession = Depends(get_session)):
            result = await session.execute(select(Market))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session
    """
    async with db_manager.session() as session:
        yield session


# Convenience function for direct access
async def init_database() -> None:
    """Initialize database (for application startup)."""
    await db_manager.health_check()
    logger.info("Database initialized and ready")


async def shutdown_database() -> None:
    """Shutdown database (for application cleanup)."""
    await db_manager.close()
    logger.info("Database shutdown complete")
