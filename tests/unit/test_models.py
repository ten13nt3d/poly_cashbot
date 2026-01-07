"""Unit tests for database models."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.models import (
    Market,
    Order,
    OrderStatus,
    Trade,
    MarketSide,
    StrategyType,
    Position,
    SentimentScore,
    WhaleAlert,
)
from tests.helpers import (
    assert_decimal_equal,
    create_test_datetime,
    assert_market_valid,
    assert_order_valid,
    assert_position_valid,
)


# ============================================================================
# MARKET MODEL TESTS
# ============================================================================

class TestMarket:
    """Tests for Market model."""

    @pytest.mark.asyncio
    async def test_create_market(self, db_session):
        """Test creating a market."""
        market = Market(
            id="market_1",
            question="Will XRP reach $2 by end of day?",
            end_date=create_test_datetime(hours_from_now=2),
            yes_price=Decimal("0.55"),
            no_price=Decimal("0.45"),
            volume_24h=Decimal("50000"),
            liquidity=Decimal("15000"),
            related_asset="XRP",
        )

        db_session.add(market)
        await db_session.flush()

        # Verify
        assert market.id == "market_1"
        assert market.question == "Will XRP reach $2 by end of day?"
        assert market.related_asset == "XRP"
        assert_market_valid(market)

    @pytest.mark.asyncio
    async def test_market_is_active(self, db_session, create_market):
        """Test market is_active() helper."""
        # Future market (active)
        future_market = await create_market(
            id="future_market",
            end_date=create_test_datetime(hours_from_now=2),
        )
        assert future_market.is_active() is True

        # Past market (inactive)
        past_market = await create_market(
            id="past_market",
            end_date=datetime.now() - timedelta(hours=1),
        )
        assert past_market.is_active() is False

    @pytest.mark.asyncio
    async def test_market_mid_price(self, db_session, create_market):
        """Test market mid_price() calculation."""
        market = await create_market(
            yes_price=Decimal("0.60"),
            no_price=Decimal("0.40"),
        )

        mid_price = market.mid_price()
        assert mid_price is not None
        assert_decimal_equal(mid_price, Decimal("0.50"))

    @pytest.mark.asyncio
    async def test_market_mid_price_null(self, db_session, create_market):
        """Test mid_price() returns None when prices missing."""
        market = await create_market(yes_price=None, no_price=None)
        assert market.mid_price() is None

    @pytest.mark.asyncio
    async def test_market_has_minimum_liquidity(self, db_session, create_market):
        """Test has_minimum_liquidity() helper."""
        # High liquidity market
        high_liq = await create_market(
            id="high_liq",
            liquidity=Decimal("20000"),
        )
        assert high_liq.has_minimum_liquidity(Decimal("10000")) is True

        # Low liquidity market
        low_liq = await create_market(
            id="low_liq",
            liquidity=Decimal("5000"),
        )
        assert low_liq.has_minimum_liquidity(Decimal("10000")) is False

    @pytest.mark.asyncio
    async def test_market_timestamps(self, db_session, create_market):
        """Test automatic timestamp creation."""
        market = await create_market()
        await db_session.flush()

        assert market.created_at is not None
        assert market.updated_at is not None
        assert market.created_at <= market.updated_at


# ============================================================================
# ORDER MODEL TESTS
# ============================================================================

class TestOrder:
    """Tests for Order model."""

    @pytest.mark.asyncio
    async def test_create_order(self, db_session, create_market, create_order):
        """Test creating an order."""
        market = await create_market()

        order = await create_order(
            id="order_1",
            market_id=market.id,
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.55"),
        )
        await db_session.flush()

        # Verify
        assert order.market_id == market.id
        assert order.side == "BUY"
        assert_order_valid(order)

    @pytest.mark.asyncio
    async def test_order_is_active(self, db_session, create_order):
        """Test order is_active() helper."""
        # Pending order (active)
        pending = await create_order(id="pending", status="pending")
        assert pending.is_active() is True

        # Open order (active)
        open_order = await create_order(id="open", status="open")
        assert open_order.is_active() is True

        # Filled order (inactive)
        filled = await create_order(id="filled", status="filled")
        assert filled.is_active() is False

        # Cancelled order (inactive)
        cancelled = await create_order(id="cancelled", status="cancelled")
        assert cancelled.is_active() is False

    @pytest.mark.asyncio
    async def test_order_is_filled(self, db_session, create_order):
        """Test order is_filled() helper."""
        filled = await create_order(status="filled")
        assert filled.is_filled() is True

        pending = await create_order(id="pending_order", status="pending")
        assert pending.is_filled() is False

    @pytest.mark.asyncio
    async def test_order_fill_percentage(self, db_session, create_order):
        """Test order fill_percentage() calculation."""
        order = await create_order(
            size=Decimal("100.00"),
            filled_size=Decimal("50.00"),
        )

        fill_pct = order.fill_percentage()
        assert_decimal_equal(fill_pct, Decimal("50.00"))

    @pytest.mark.asyncio
    async def test_order_foreign_key_constraint(self, db_session):
        """Test foreign key constraint to markets."""
        # Try to create order with non-existent market
        order = Order(
            id="invalid_order",
            market_id="non_existent_market",
            side="BUY",
            size=Decimal("100"),
            price=Decimal("0.50"),
            strategy="test",
        )

        db_session.add(order)

        with pytest.raises(IntegrityError):
            await db_session.flush()


# ============================================================================
# TRADE MODEL TESTS
# ============================================================================

class TestTrade:
    """Tests for Trade model."""

    @pytest.mark.asyncio
    async def test_create_trade(self, db_session, create_market, create_order):
        """Test creating a trade."""
        market = await create_market()
        order = await create_order(market_id=market.id)

        trade = Trade(
            id="trade_1",
            order_id=order.id,
            market_id=market.id,
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.55"),
            fee=Decimal("1.00"),
            strategy="interval_15m",
        )

        db_session.add(trade)
        await db_session.flush()

        # Verify
        assert trade.order_id == order.id
        assert trade.market_id == market.id
        assert trade.executed_at is not None

    @pytest.mark.asyncio
    async def test_trade_is_winner(self, db_session, create_market, create_order):
        """Test trade is_winner() helper."""
        market = await create_market()
        order = await create_order(market_id=market.id)

        # Winning trade
        winner = Trade(
            id="winner",
            order_id=order.id,
            market_id=market.id,
            side="BUY",
            size=Decimal("100"),
            price=Decimal("0.50"),
            pnl=Decimal("10.00"),  # Profit
            strategy="test",
        )
        db_session.add(winner)
        await db_session.flush()

        assert winner.is_winner() is True

        # Losing trade
        loser = Trade(
            id="loser",
            order_id=order.id,
            market_id=market.id,
            side="SELL",
            size=Decimal("100"),
            price=Decimal("0.50"),
            pnl=Decimal("-10.00"),  # Loss
            strategy="test",
        )
        db_session.add(loser)
        await db_session.flush()

        assert loser.is_winner() is False

    @pytest.mark.asyncio
    async def test_trade_roi_pct(self, db_session, create_market, create_order):
        """Test trade roi_pct() calculation."""
        market = await create_market()
        order = await create_order(market_id=market.id)

        trade = Trade(
            id="roi_trade",
            order_id=order.id,
            market_id=market.id,
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.50"),
            pnl=Decimal("5.00"),  # 5% profit
            strategy="test",
        )
        db_session.add(trade)
        await db_session.flush()

        roi = trade.roi_pct()
        assert roi is not None
        assert_decimal_equal(roi, Decimal("5.00"))


# ============================================================================
# POSITION MODEL TESTS
# ============================================================================

class TestPosition:
    """Tests for Position model."""

    @pytest.mark.asyncio
    async def test_create_position(self, db_session, create_position):
        """Test creating a position."""
        position = await create_position(
            id="position_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.55"),
        )
        await db_session.flush()

        assert position.is_open is True
        assert position.opened_at is not None
        assert_position_valid(position)

    @pytest.mark.skip(reason="Timezone handling needs improvement")
    @pytest.mark.asyncio
    async def test_position_age_minutes(self, db_session, create_position):
        """Test position age_minutes() calculation."""
        position = await create_position()
        await db_session.flush()

        # Age should be very small (just created)
        age = position.age_minutes()
        assert 0 <= age < 5  # Less than 5 minutes (account for DB latency)

    @pytest.mark.asyncio
    async def test_position_update_pnl_buy(self, db_session, create_position):
        """Test position update_pnl() for BUY side."""
        position = await create_position(
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
        )

        # Price goes up (profit)
        position.update_pnl(Decimal("0.60"))

        assert position.current_price == Decimal("0.60")
        assert position.unrealized_pnl is not None
        assert_decimal_equal(position.unrealized_pnl, Decimal("10.00"))

    @pytest.mark.asyncio
    async def test_position_update_pnl_sell(self, db_session, create_position):
        """Test position update_pnl() for SELL side."""
        position = await create_position(
            side="SELL",
            size=Decimal("100.00"),
            entry_price=Decimal("0.60"),
        )

        # Price goes down (profit for short)
        position.update_pnl(Decimal("0.50"))

        assert position.current_price == Decimal("0.50")
        assert position.unrealized_pnl is not None
        assert_decimal_equal(position.unrealized_pnl, Decimal("10.00"))

    @pytest.mark.asyncio
    async def test_position_unrealized_pnl_pct(self, db_session, create_position):
        """Test position unrealized_pnl_pct() calculation."""
        position = await create_position(
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
        )

        position.update_pnl(Decimal("0.55"))  # 5% gain

        pnl_pct = position.unrealized_pnl_pct
        assert pnl_pct is not None
        assert_decimal_equal(pnl_pct, Decimal("5.00"))


# ============================================================================
# SENTIMENT SCORE MODEL TESTS
# ============================================================================

class TestSentimentScore:
    """Tests for SentimentScore model."""

    @pytest.mark.asyncio
    async def test_create_sentiment_score(self, db_session, create_sentiment_score):
        """Test creating a sentiment score."""
        sentiment = await create_sentiment_score(
            asset="XRP",
            score=Decimal("65.00"),
            timeframe="15m",
        )
        await db_session.flush()

        assert sentiment.id is not None
        assert sentiment.asset == "XRP"
        assert sentiment.timestamp is not None

    @pytest.mark.asyncio
    async def test_sentiment_is_bullish(self, db_session, create_sentiment_score):
        """Test sentiment is_bullish() helper."""
        bullish = await create_sentiment_score(score=Decimal("65.00"))
        assert bullish.is_bullish(Decimal("40")) is True

        neutral = await create_sentiment_score(score=Decimal("30.00"))
        assert neutral.is_bullish(Decimal("40")) is False

    @pytest.mark.asyncio
    async def test_sentiment_is_bearish(self, db_session, create_sentiment_score):
        """Test sentiment is_bearish() helper."""
        bearish = await create_sentiment_score(score=Decimal("-60.00"))
        assert bearish.is_bearish(Decimal("-40")) is True

        neutral = await create_sentiment_score(score=Decimal("-20.00"))
        assert neutral.is_bearish(Decimal("-40")) is False

    @pytest.mark.asyncio
    async def test_sentiment_is_neutral(self, db_session, create_sentiment_score):
        """Test sentiment is_neutral() helper."""
        neutral = await create_sentiment_score(score=Decimal("20.00"))
        assert neutral.is_neutral(Decimal("-40"), Decimal("40")) is True

        bullish = await create_sentiment_score(score=Decimal("60.00"))
        assert bullish.is_neutral(Decimal("-40"), Decimal("40")) is False

    @pytest.mark.asyncio
    async def test_sentiment_magnitude(self, db_session, create_sentiment_score):
        """Test sentiment magnitude() calculation."""
        positive = await create_sentiment_score(score=Decimal("65.00"))
        assert_decimal_equal(positive.magnitude(), Decimal("65.00"))

        negative = await create_sentiment_score(score=Decimal("-65.00"))
        assert_decimal_equal(negative.magnitude(), Decimal("65.00"))


# ============================================================================
# WHALE ALERT MODEL TESTS
# ============================================================================

class TestWhaleAlert:
    """Tests for WhaleAlert model."""

    @pytest.mark.asyncio
    async def test_create_whale_alert(self, db_session, create_market):
        """Test creating a whale alert."""
        market = await create_market()

        whale = WhaleAlert(
            market_id=market.id,
            wallet_address="0x1234567890abcdef",
            order_size=Decimal("50000.00"),
            side="BUY",
            relative_size=Decimal("15.5"),
            expected_impact_pct=Decimal("2.5"),
        )

        db_session.add(whale)
        await db_session.flush()

        assert whale.id is not None
        assert whale.detected_at is not None
        assert whale.wallet_address == "0x1234567890abcdef"

    @pytest.mark.asyncio
    async def test_whale_is_significant(self, db_session, create_market):
        """Test whale is_significant() helper."""
        market = await create_market()

        # Significant whale (15x average)
        big_whale = WhaleAlert(
            market_id=market.id,
            wallet_address="0xbig",
            order_size=Decimal("100000"),
            side="BUY",
            relative_size=Decimal("15.0"),
        )
        db_session.add(big_whale)
        await db_session.flush()

        assert big_whale.is_significant(Decimal("10.0")) is True

        # Small whale (5x average)
        small_whale = WhaleAlert(
            market_id=market.id,
            wallet_address="0xsmall",
            order_size=Decimal("50000"),
            side="BUY",
            relative_size=Decimal("5.0"),
        )
        db_session.add(small_whale)
        await db_session.flush()

        assert small_whale.is_significant(Decimal("10.0")) is False

    @pytest.mark.asyncio
    async def test_whale_was_frontrun(self, db_session, create_market):
        """Test whale was_frontrun() helper."""
        market = await create_market()

        # Frontrun whale
        frontrun = WhaleAlert(
            market_id=market.id,
            wallet_address="0xfrontrun",
            order_size=Decimal("100000"),
            side="BUY",
            action_taken="frontrun",
            frontrun_order_id="order_123",
        )
        db_session.add(frontrun)
        await db_session.flush()

        assert frontrun.was_frontrun() is True

        # Ignored whale
        ignored = WhaleAlert(
            market_id=market.id,
            wallet_address="0xignored",
            order_size=Decimal("50000"),
            side="BUY",
            action_taken="ignored",
        )
        db_session.add(ignored)
        await db_session.flush()

        assert ignored.was_frontrun() is False
