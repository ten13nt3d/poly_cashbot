"""Tests for database manager (src/database.py)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from unittest.mock import AsyncMock, MagicMock, patch

from src.database import DatabaseManager, get_session, init_database, shutdown_database


class TestDatabaseManagerInit:
    """Test DatabaseManager initialization."""

    def test_init_with_defaults(self) -> None:
        """Test DatabaseManager initialization with default settings."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        assert db_manager.database_url == "postgresql+asyncpg://test:test@localhost/test"
        assert db_manager.echo is False
        assert db_manager._engine is None
        assert db_manager._async_session_maker is None

    def test_init_with_custom_settings(self) -> None:
        """Test DatabaseManager initialization with custom settings."""
        db_manager = DatabaseManager(
            database_url="postgresql+asyncpg://custom:custom@localhost/custom",
            echo=True,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=False,
        )

        assert db_manager.database_url == "postgresql+asyncpg://custom:custom@localhost/custom"
        assert db_manager.echo is True
        assert "pool_size" in db_manager._engine_kwargs
        assert db_manager._engine_kwargs["pool_size"] == 10
        assert db_manager._engine_kwargs["max_overflow"] == 20
        assert db_manager._engine_kwargs["pool_pre_ping"] is False

    def test_init_with_null_pool(self) -> None:
        """Test DatabaseManager initialization with NullPool for testing."""
        db_manager = DatabaseManager(
            database_url="postgresql+asyncpg://test:test@localhost/test",
            use_pool=False,
        )

        assert db_manager._engine_kwargs["poolclass"] == NullPool
        assert "pool_size" not in db_manager._engine_kwargs

    def test_init_with_queue_pool(self) -> None:
        """Test DatabaseManager initialization with AsyncAdaptedQueuePool."""
        db_manager = DatabaseManager(
            database_url="postgresql+asyncpg://test:test@localhost/test",
            use_pool=True,
            pool_size=5,
        )

        assert db_manager._engine_kwargs["poolclass"] == AsyncAdaptedQueuePool
        assert db_manager._engine_kwargs["pool_size"] == 5


class TestDatabaseManagerEngine:
    """Test DatabaseManager engine property."""

    def test_engine_lazy_creation(self) -> None:
        """Test engine is created lazily when first accessed."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        assert db_manager._engine is None

        engine = db_manager.engine

        assert engine is not None
        assert isinstance(engine, AsyncEngine)
        assert db_manager._engine is engine  # Same instance returned

    def test_engine_singleton(self) -> None:
        """Test engine property returns same instance on multiple accesses."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        engine1 = db_manager.engine
        engine2 = db_manager.engine

        assert engine1 is engine2


class TestDatabaseManagerSessionMaker:
    """Test DatabaseManager session_maker property."""

    def test_session_maker_lazy_creation(self) -> None:
        """Test session maker is created lazily when first accessed."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        assert db_manager._async_session_maker is None

        session_maker = db_manager.session_maker

        assert session_maker is not None
        assert isinstance(session_maker, async_sessionmaker)
        assert db_manager._async_session_maker is session_maker

    def test_session_maker_singleton(self) -> None:
        """Test session_maker property returns same instance on multiple accesses."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        maker1 = db_manager.session_maker
        maker2 = db_manager.session_maker

        assert maker1 is maker2

    def test_session_maker_configuration(self) -> None:
        """Test session maker has correct configuration."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        session_maker = db_manager.session_maker

        assert session_maker.kw["expire_on_commit"] is False
        assert session_maker.kw["autoflush"] is False


class TestDatabaseManagerSessionContext:
    """Test DatabaseManager session context manager."""

    @pytest.mark.asyncio
    async def test_session_context_success(self) -> None:
        """Test session context manager commits on success."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        # Mock the session maker to return a mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        mock_session_maker.return_value.__aexit__.return_value = None

        db_manager._async_session_maker = mock_session_maker

        async with db_manager.session() as session:
            assert session is mock_session

        # Verify commit and close were called
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_context_rollback_on_error(self) -> None:
        """Test session context manager rolls back on error."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        # Mock the session maker to return a mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        mock_session_maker.return_value.__aexit__.return_value = None

        db_manager._async_session_maker = mock_session_maker

        # Simulate an error during session usage
        with pytest.raises(ValueError):
            async with db_manager.session() as session:
                raise ValueError("Test error")

        # Verify rollback and close were called
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()


class TestDatabaseManagerTableOperations:
    """Test DatabaseManager table operations."""

    @pytest.mark.asyncio
    async def test_create_all_tables(self) -> None:
        """Test create_all_tables creates database tables."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        # Mock engine
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_connection = AsyncMock()
        mock_engine.begin.return_value.__aenter__.return_value = mock_connection
        mock_engine.begin.return_value.__aexit__.return_value = None

        db_manager._engine = mock_engine

        await db_manager.create_all_tables()

        # Verify run_sync was called to create tables
        mock_connection.run_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_drop_all_tables(self) -> None:
        """Test drop_all_tables drops database tables."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        # Mock engine
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_connection = AsyncMock()
        mock_engine.begin.return_value.__aenter__.return_value = mock_connection
        mock_engine.begin.return_value.__aexit__.return_value = None

        db_manager._engine = mock_engine

        await db_manager.drop_all_tables()

        # Verify run_sync was called to drop tables
        mock_connection.run_sync.assert_called_once()


class TestDatabaseManagerHealthCheck:
    """Test DatabaseManager health check."""

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        """Test health_check returns True when database is accessible."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock()
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        mock_session_maker.return_value.__aexit__.return_value = None

        db_manager._async_session_maker = mock_session_maker

        result = await db_manager.health_check()

        assert result is True
        mock_session.execute.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_health_check_failure(self) -> None:
        """Test health_check returns False when database is not accessible."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        # Mock session that raises error
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("Database connection failed")
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        mock_session_maker.return_value.__aexit__.return_value = None

        db_manager._async_session_maker = mock_session_maker

        result = await db_manager.health_check()

        assert result is False


class TestDatabaseManagerClose:
    """Test DatabaseManager close method."""

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self) -> None:
        """Test close() disposes engine and resets state."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        # Mock engine
        mock_engine = AsyncMock(spec=AsyncEngine)
        db_manager._engine = mock_engine
        db_manager._async_session_maker = MagicMock()

        await db_manager.close()

        # Verify dispose was called
        mock_engine.dispose.assert_called_once()

        # Verify state was reset
        assert db_manager._engine is None
        assert db_manager._async_session_maker is None

    @pytest.mark.asyncio
    async def test_close_when_no_engine(self) -> None:
        """Test close() handles case when engine is None."""
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://test:test@localhost/test")

        # Engine is None by default
        assert db_manager._engine is None

        # Should not raise error
        await db_manager.close()

        # Still None
        assert db_manager._engine is None


class TestGetSessionDependency:
    """Test get_session dependency injection function."""

    @pytest.mark.asyncio
    async def test_get_session_yields_session(self) -> None:
        """Test get_session yields a session from global db_manager."""
        with patch("src.database.db_manager") as mock_db_manager:
            # Mock the session context manager
            mock_session = AsyncMock(spec=AsyncSession)
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_db_manager.session.return_value = mock_context

            # Use the dependency
            async_generator = get_session()
            session = await async_generator.__anext__()

            assert session is mock_session


class TestInitAndShutdownFunctions:
    """Test init_database and shutdown_database convenience functions."""

    @pytest.mark.asyncio
    async def test_init_database(self) -> None:
        """Test init_database calls health_check on global db_manager."""
        with patch("src.database.db_manager") as mock_db_manager:
            mock_db_manager.health_check = AsyncMock(return_value=True)

            await init_database()

            mock_db_manager.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_database(self) -> None:
        """Test shutdown_database calls close on global db_manager."""
        with patch("src.database.db_manager") as mock_db_manager:
            mock_db_manager.close = AsyncMock()

            await shutdown_database()

            mock_db_manager.close.assert_called_once()
