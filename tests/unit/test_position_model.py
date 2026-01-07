"""Unit tests for Position model."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models.position import Position


class TestPositionModel:
    """Test cases for the Position model."""

    @pytest.fixture
    def sample_position_data(self):
        """Create sample position data."""
        return {
            "id": "pos_123",
            "market_id": "market_456",
            "side": "BUY",
            "size": Decimal("100.00"),
            "entry_price": Decimal("0.55"),
            "current_price": Decimal("0.60"),
            "unrealized_pnl": Decimal("5.00"),
            "opened_at": datetime.now(),
            "is_open": True,
            "strategy": "temporal_arbitrage",
            "entry_confidence": Decimal("0.85"),
            "entry_sentiment": Decimal("45.50"),
        }

    @pytest.fixture
    def open_position(self, sample_position_data):
        """Create an open position."""
        return Position(**sample_position_data)

    @pytest.fixture
    def closed_position(self, sample_position_data):
        """Create a closed position."""
        data = sample_position_data.copy()
        data["is_open"] = False
        data["opened_at"] = datetime.now() - timedelta(minutes=30)
        data["closed_at"] = datetime.now() - timedelta(minutes=15)
        return Position(**data)

    def test_position_creation(self, sample_position_data):
        """Test creating a position with valid data."""
        position = Position(**sample_position_data)

        assert position.id == "pos_123"
        assert position.market_id == "market_456"
        assert position.side == "BUY"
        assert position.size == Decimal("100.00")
        assert position.entry_price == Decimal("0.55")
        assert position.is_open is True
        assert position.strategy == "temporal_arbitrage"

    def test_position_buy_side(self):
        """Test BUY position creation."""
        position = Position(
            id="pos_buy",
            market_id="market_1",
            side="BUY",
            size=Decimal("50.00"),
            entry_price=Decimal("0.45"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        assert position.side == "BUY"
        assert position.size == Decimal("50.00")

    def test_position_sell_side(self):
        """Test SELL position creation."""
        position = Position(
            id="pos_sell",
            market_id="market_1",
            side="SELL",
            size=Decimal("75.00"),
            entry_price=Decimal("0.65"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        assert position.side == "SELL"
        assert position.size == Decimal("75.00")

    def test_update_pnl_buy_profit(self):
        """Test P&L update for profitable BUY position."""
        position = Position(
            id="pos_1",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        # Price goes up - profit for BUY
        position.update_pnl(Decimal("0.60"))

        assert position.current_price == Decimal("0.60")
        assert position.unrealized_pnl == Decimal("10.00")  # (0.60 - 0.50) * 100

    def test_update_pnl_buy_loss(self):
        """Test P&L update for losing BUY position."""
        position = Position(
            id="pos_2",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.60"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        # Price goes down - loss for BUY
        position.update_pnl(Decimal("0.50"))

        assert position.current_price == Decimal("0.50")
        assert position.unrealized_pnl == Decimal("-10.00")  # (0.50 - 0.60) * 100

    def test_update_pnl_sell_profit(self):
        """Test P&L update for profitable SELL position."""
        position = Position(
            id="pos_3",
            market_id="market_1",
            side="SELL",
            size=Decimal("100.00"),
            entry_price=Decimal("0.60"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        # Price goes down - profit for SELL
        position.update_pnl(Decimal("0.50"))

        assert position.current_price == Decimal("0.50")
        assert position.unrealized_pnl == Decimal("10.00")  # -(0.50 - 0.60) * 100

    def test_update_pnl_sell_loss(self):
        """Test P&L update for losing SELL position."""
        position = Position(
            id="pos_4",
            market_id="market_1",
            side="SELL",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        # Price goes up - loss for SELL
        position.update_pnl(Decimal("0.60"))

        assert position.current_price == Decimal("0.60")
        assert position.unrealized_pnl == Decimal("-10.00")  # -(0.60 - 0.50) * 100

    def test_unrealized_pnl_pct_profit(self):
        """Test unrealized P&L percentage calculation for profit."""
        position = Position(
            id="pos_5",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        position.unrealized_pnl = Decimal("10.00")

        pnl_pct = position.unrealized_pnl_pct()
        assert pnl_pct == Decimal("10.00")  # 10 / 100 * 100

    def test_unrealized_pnl_pct_loss(self):
        """Test unrealized P&L percentage calculation for loss."""
        position = Position(
            id="pos_6",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.60"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        position.unrealized_pnl = Decimal("-20.00")

        pnl_pct = position.unrealized_pnl_pct()
        assert pnl_pct == Decimal("-20.00")  # -20 / 100 * 100

    def test_unrealized_pnl_pct_none(self):
        """Test unrealized P&L percentage when pnl is None."""
        position = Position(
            id="pos_7",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        # unrealized_pnl is None by default
        pnl_pct = position.unrealized_pnl_pct()
        assert pnl_pct is None

    def test_unrealized_pnl_pct_zero_size(self):
        """Test unrealized P&L percentage when size is zero."""
        position = Position(
            id="pos_8",
            market_id="market_1",
            side="BUY",
            size=Decimal("0.00"),
            entry_price=Decimal("0.50"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        position.unrealized_pnl = Decimal("10.00")

        pnl_pct = position.unrealized_pnl_pct()
        assert pnl_pct is None  # Should return None to avoid division by zero

    def test_age_minutes_open_position(self):
        """Test age calculation for open position."""
        # Create position opened 30 minutes ago
        opened_at = datetime.now() - timedelta(minutes=30)
        position = Position(
            id="pos_9",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
            opened_at=opened_at,
            is_open=True,
            strategy="test",
        )

        age = position.age_minutes()
        # Should be approximately 30 minutes (allow small tolerance)
        assert 29.9 < age < 30.1

    def test_age_minutes_closed_position(self):
        """Test age calculation for closed position."""
        # Position was open for 15 minutes
        opened_at = datetime.now() - timedelta(minutes=45)
        closed_at = datetime.now() - timedelta(minutes=30)

        position = Position(
            id="pos_10",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
            opened_at=opened_at,
            closed_at=closed_at,
            is_open=False,
            strategy="test",
        )

        age = position.age_minutes()
        # Should be approximately 15 minutes
        assert 14.9 < age < 15.1

    def test_age_minutes_closed_without_timestamp(self):
        """Test age calculation for closed position without closed_at."""
        position = Position(
            id="pos_11",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
            opened_at=datetime.now(),
            is_open=False,
            strategy="test",
        )

        age = position.age_minutes()
        assert age == 0.0  # Should return 0 if closed_at is None

    def test_position_state_open(self, open_position):
        """Test open position state."""
        assert open_position.is_open is True
        assert open_position.closed_at is None

    def test_position_state_closed(self, closed_position):
        """Test closed position state."""
        assert closed_position.is_open is False
        assert closed_position.closed_at is not None

    def test_position_with_confidence(self):
        """Test position with entry confidence."""
        position = Position(
            id="pos_12",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
            entry_confidence=Decimal("0.92"),
        )

        assert position.entry_confidence == Decimal("0.92")

    def test_position_with_sentiment(self):
        """Test position with entry sentiment."""
        position = Position(
            id="pos_13",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
            entry_sentiment=Decimal("65.50"),
        )

        assert position.entry_sentiment == Decimal("65.50")

    def test_position_negative_pnl(self):
        """Test position with negative unrealized P&L."""
        position = Position(
            id="pos_14",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.70"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        position.update_pnl(Decimal("0.50"))
        assert position.unrealized_pnl == Decimal("-20.00")

    def test_position_zero_pnl(self):
        """Test position with zero P&L (no price movement)."""
        position = Position(
            id="pos_15",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.50"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        position.update_pnl(Decimal("0.50"))
        assert position.unrealized_pnl == Decimal("0.00")

    def test_position_large_size(self):
        """Test position with large size."""
        position = Position(
            id="pos_16",
            market_id="market_1",
            side="BUY",
            size=Decimal("10000.00"),
            entry_price=Decimal("0.50"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        position.update_pnl(Decimal("0.51"))
        # 0.01 * 10000 = 100
        assert position.unrealized_pnl == Decimal("100.00")

    def test_position_small_price_movement(self):
        """Test position with very small price movement."""
        position = Position(
            id="pos_17",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            entry_price=Decimal("0.5000"),
            opened_at=datetime.now(),
            is_open=True,
            strategy="test",
        )

        position.update_pnl(Decimal("0.5001"))
        # 0.0001 * 100 = 0.01
        assert position.unrealized_pnl == Decimal("0.01")
