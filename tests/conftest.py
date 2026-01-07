"""Pytest configuration and shared fixtures."""

import asyncio
import pytest
import os
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.models.base import Base
from src.models import Market, Order, Trade, Position, SentimentScore, WhaleAlert


# ============================================================================
# EVENT LOOP CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for the entire test session.

    This prevents "Event loop is closed" errors in async tests.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
async def test_engine():
    """
    Create async engine for test database.

    Uses separate test database to avoid conflicts with development data.
    """
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://cashbot_user:dev_password@localhost:5432/poly_cashbot_test",
    )

    engine = create_async_engine(
        test_db_url,
        echo=False,  # Set to True for SQL debugging
        poolclass=NullPool,  # Don't pool connections in tests
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncIterator[AsyncSession]:
    """
    Create a fresh database session for each test.

    Each test gets a clean transaction that is rolled back after the test,
    ensuring test isolation.

    Usage:
        async def test_create_market(db_session):
            market = Market(id="test", question="Test?", end_date=datetime.now())
            db_session.add(market)
            await db_session.flush()  # Flush to get ID, but don't commit
            assert market.id == "test"
    """
    # Create connection
    async with test_engine.connect() as connection:
        # Start a transaction
        async with connection.begin() as transaction:
            # Create session bound to the transaction
            async_session = async_sessionmaker(
                bind=connection,
                expire_on_commit=False,
                class_=AsyncSession,
            )

            async with async_session() as session:
                yield session

                # Rollback the transaction to clean up
                await transaction.rollback()


# ============================================================================
# MODEL FACTORY FIXTURES
# ============================================================================

@pytest.fixture
def create_market(db_session):
    """
    Factory fixture to create Market instances with sensible defaults.

    Usage:
        async def test_market_creation(create_market):
            market = await create_market(id="market1", question="Will XRP moon?")
    """
    async def _create_market(
        id: str = None,
        question: str = "Will XRP reach $2 by end of day?",
        end_date: datetime = None,
        yes_price: Decimal = Decimal("0.55"),
        no_price: Decimal = Decimal("0.45"),
        volume_24h: Decimal = Decimal("50000"),
        liquidity: Decimal = Decimal("15000"),
        related_asset: str = "XRP",
    ) -> Market:
        """Create and persist a Market."""
        if id is None:
            id = f"test_market_{uuid.uuid4().hex[:8]}"
        if end_date is None:
            end_date = datetime.now() + timedelta(hours=1)

        market = Market(
            id=id,
            question=question,
            end_date=end_date,
            yes_price=yes_price,
            no_price=no_price,
            volume_24h=volume_24h,
            liquidity=liquidity,
            related_asset=related_asset,
        )
        db_session.add(market)
        await db_session.flush()  # Get ID without committing
        return market

    return _create_market


@pytest.fixture
def create_order(db_session, create_market):
    """Factory fixture to create Order instances."""
    async def _create_order(
        id: str = None,
        market_id: str = None,
        side: str = "BUY",
        size: Decimal = Decimal("100.00"),
        price: Decimal = Decimal("0.55"),
        strategy: str = "interval_15m",
        status: str = "pending",
        filled_size: Decimal = None,
    ) -> Order:
        """Create and persist an Order."""
        if id is None:
            id = f"test_order_{uuid.uuid4().hex[:8]}"
        if filled_size is None:
            filled_size = Decimal("0")
        # Create market if not provided
        if market_id is None:
            market = await create_market()
            market_id = market.id

        order = Order(
            id=id,
            market_id=market_id,
            side=side,
            size=size,
            price=price,
            strategy=strategy,
            status=status,
            filled_size=filled_size,
        )
        db_session.add(order)
        await db_session.flush()
        return order

    return _create_order


@pytest.fixture
def create_position(db_session, create_market):
    """Factory fixture to create Position instances."""
    async def _create_position(
        id: str = None,
        market_id: str = None,
        side: str = "BUY",
        size: Decimal = Decimal("100.00"),
        entry_price: Decimal = Decimal("0.55"),
        strategy: str = "interval_15m",
        is_open: bool = True,
    ) -> Position:
        """Create and persist a Position."""
        if id is None:
            id = f"test_position_{uuid.uuid4().hex[:8]}"
        if market_id is None:
            market = await create_market()
            market_id = market.id

        position = Position(
            id=id,
            market_id=market_id,
            side=side,
            size=size,
            entry_price=entry_price,
            strategy=strategy,
            is_open=is_open,
        )
        db_session.add(position)
        await db_session.flush()
        return position

    return _create_position


@pytest.fixture
def create_sentiment_score(db_session):
    """Factory fixture to create SentimentScore instances."""
    async def _create_sentiment_score(
        asset: str = "XRP",
        score: Decimal = Decimal("65.00"),
        timestamp: datetime = None,
        timeframe: str = "15m",
        confidence: Decimal = Decimal("0.85"),
    ) -> SentimentScore:
        """Create and persist a SentimentScore."""
        if timestamp is None:
            timestamp = datetime.now()

        sentiment = SentimentScore(
            asset=asset,
            score=score,
            timestamp=timestamp,
            timeframe=timeframe,
            confidence=confidence,
        )
        db_session.add(sentiment)
        await db_session.flush()
        return sentiment

    return _create_sentiment_score


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture
async def sample_markets(db_session, create_market):
    """Create sample markets for testing."""
    markets = []

    # Active XRP market
    markets.append(
        await create_market(
            id="xrp_market_1",
            question="Will XRP reach $2.50 by 23:59 UTC?",
            related_asset="XRP",
            liquidity=Decimal("20000"),
        )
    )

    # Active BTC market
    markets.append(
        await create_market(
            id="btc_market_1",
            question="Will BTC stay above $45k?",
            related_asset="BTC",
            liquidity=Decimal("50000"),
        )
    )

    # Low liquidity market
    markets.append(
        await create_market(
            id="low_liquidity_market",
            question="Obscure crypto question?",
            related_asset="DOGE",
            liquidity=Decimal("5000"),  # Below minimum
        )
    )

    await db_session.commit()
    return markets


# ============================================================================
# CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session")
def test_settings():
    """Provide test configuration overrides."""
    return {
        "min_market_liquidity": Decimal("10000"),
        "min_position_size": Decimal("5.00"),
        "per_trade_risk_pct": Decimal("0.02"),
    }
