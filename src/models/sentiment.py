"""Sentiment score model for time-series tracking."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class SentimentScore(Base, TimestampMixin):
    """Time-series record of sentiment scores for crypto assets."""

    __tablename__ = "sentiment_scores"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Timestamp of the sentiment calculation
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, doc="When sentiment was calculated"
    )

    # Asset identification
    asset: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Crypto asset (XRP, BTC, ETH)"
    )

    # Composite sentiment score
    score: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, doc="Composite sentiment score (-100 to +100)"
    )

    # Component scores
    price_component: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True, doc="Price momentum component"
    )
    news_component: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True, doc="News sentiment component"
    )
    social_component: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True, doc="Social sentiment component"
    )
    volume_component: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True, doc="Volume analysis component"
    )

    # Confidence metrics
    confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True, doc="Confidence in sentiment score (0.0-1.0)"
    )

    # Timeframe metadata
    timeframe: Mapped[str] = mapped_column(
        String(20), nullable=False, default="15m", doc="Analysis timeframe (15m, 1h, 4h)"
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_sentiment_timestamp", "timestamp"),
        Index("idx_sentiment_asset", "asset"),
        Index("idx_sentiment_asset_timestamp", "asset", "timestamp"),
    )

    def is_bullish(self, threshold: Decimal = Decimal("40")) -> bool:
        """Check if sentiment is bullish (above threshold)."""
        return self.score > threshold

    def is_bearish(self, threshold: Decimal = Decimal("-40")) -> bool:
        """Check if sentiment is bearish (below threshold)."""
        return self.score < threshold

    def is_neutral(
        self, lower_threshold: Decimal = Decimal("-40"), upper_threshold: Decimal = Decimal("40")
    ) -> bool:
        """Check if sentiment is neutral (between thresholds)."""
        return lower_threshold <= self.score <= upper_threshold

    def magnitude(self) -> Decimal:
        """Get absolute magnitude of sentiment score."""
        return abs(self.score)
