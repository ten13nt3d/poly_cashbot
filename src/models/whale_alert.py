"""Whale alert model for tracking large orders."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class WhaleAlert(Base, TimestampMixin):
    """Represents detection of a large order (whale activity)."""

    __tablename__ = "whale_alerts"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Detection timestamp
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, doc="When whale was detected"
    )

    # Foreign key
    market_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("markets.id", ondelete="CASCADE"),
        nullable=False,
        doc="Market where whale order was detected",
    )

    # Whale details
    wallet_address: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Polygon wallet address of whale"
    )
    order_size: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, doc="Size of whale order in USDC"
    )
    side: Mapped[str] = mapped_column(String(10), nullable=False, doc="BUY or SELL")

    # Analysis metrics
    relative_size: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True, doc="Order size relative to average (e.g., 10x = 10.0)"
    )
    expected_impact_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True, doc="Expected price impact percentage"
    )

    # Action taken
    action_taken: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, doc="Action taken by bot (e.g., 'frontrun', 'ignored')"
    )
    frontrun_order_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, doc="Order ID if frontrun was executed"
    )
    frontrun_success: Mapped[Optional[bool]] = mapped_column(
        nullable=True, doc="Whether frontrun trade was successful"
    )

    # Metadata
    detection_latency_ms: Mapped[Optional[int]] = mapped_column(
        nullable=True, doc="Time from whale order to detection in milliseconds"
    )

    # Indexes
    __table_args__ = (
        Index("idx_whale_detected", "detected_at"),
        Index("idx_whale_wallet", "wallet_address"),
        Index("idx_whale_market", "market_id"),
    )

    def is_significant(self, threshold: Decimal = Decimal("10.0")) -> bool:
        """Check if whale order is significant (>= threshold multiplier)."""
        return self.relative_size is not None and self.relative_size >= threshold

    def was_frontrun(self) -> bool:
        """Check if bot executed a frontrun on this whale."""
        return self.action_taken == "frontrun" and self.frontrun_order_id is not None
