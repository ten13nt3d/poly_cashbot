"""Order model for tracking order submissions."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Order(Base, TimestampMixin):
    """Represents an order submitted to Polymarket."""

    __tablename__ = "orders"

    # Primary key
    id: Mapped[str] = mapped_column(String(255), primary_key=True, doc="Unique order ID")

    # Foreign keys
    market_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("markets.id", ondelete="CASCADE"),
        nullable=False,
        doc="Market where order is placed",
    )

    # Order details
    side: Mapped[str] = mapped_column(String(10), nullable=False, doc="BUY or SELL")
    size: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, doc="Order size in USDC")
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 8), nullable=False, doc="Limit price (0.0-1.0)"
    )

    # Fill information
    filled_size: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0"), doc="Amount filled in USDC"
    )
    average_fill_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 8), nullable=True, doc="Average fill price"
    )

    # Strategy metadata
    strategy: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Strategy that created this order"
    )
    confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True, doc="Signal confidence (0.0-1.0)"
    )
    sentiment_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True, doc="Sentiment score (-100 to +100)"
    )

    # Order lifecycle
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", doc="Order status"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, doc="When order created"
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="When order submitted to exchange"
    )
    filled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="When order fully filled"
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="When order cancelled"
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, doc="Error message if order failed"
    )
    retry_count: Mapped[int] = mapped_column(
        nullable=False, default=0, doc="Number of submission retries"
    )

    # Indexes
    __table_args__ = (
        Index("idx_orders_market", "market_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_created", "created_at"),
    )

    def is_active(self) -> bool:
        """Check if order is still active (pending or open)."""
        return self.status in ("pending", "open", "partially_filled")

    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.status == "filled"

    def fill_percentage(self) -> Decimal:
        """Calculate fill percentage."""
        if self.size > Decimal("0"):
            return (self.filled_size / self.size) * Decimal("100")
        return Decimal("0")
