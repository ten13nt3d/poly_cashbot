"""Market model for Polymarket markets."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Market(Base, TimestampMixin):
    """Represents a Polymarket prediction market."""

    __tablename__ = "markets"

    # Primary key
    id: Mapped[str] = mapped_column(String(255), primary_key=True, doc="Market ID from Polymarket")

    # Market details
    question: Mapped[str] = mapped_column(
        String, nullable=False, doc="The question being predicted"
    )
    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, doc="When the market closes"
    )

    # Current prices (YES/NO outcomes)
    yes_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 8), nullable=True, doc="Current price of YES outcome (0.0-1.0)"
    )
    no_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 8), nullable=True, doc="Current price of NO outcome (0.0-1.0)"
    )

    # Market metrics
    volume_24h: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True, doc="24-hour trading volume in USDC"
    )
    liquidity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True, doc="Available liquidity in USDC"
    )

    # Categorization
    related_asset: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, doc="Related crypto asset (XRP, BTC, ETH, etc.)"
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_markets_asset", "related_asset"),
        Index("idx_markets_end_date", "end_date"),
        Index("idx_markets_created", "created_at"),
    )

    def is_active(self) -> bool:
        """Check if market is still active (not yet closed)."""
        return datetime.now() < self.end_date.replace(tzinfo=None)

    def mid_price(self) -> Optional[Decimal]:
        """Calculate the mid price between YES and NO."""
        if self.yes_price is not None and self.no_price is not None:
            return (self.yes_price + self.no_price) / Decimal("2")
        return None

    def has_minimum_liquidity(self, min_liquidity: Decimal = Decimal("10000")) -> bool:
        """Check if market meets minimum liquidity threshold."""
        return self.liquidity is not None and self.liquidity >= min_liquidity
