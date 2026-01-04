"""Configuration system using Pydantic Settings."""

from decimal import Decimal
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL",
        examples=["postgresql+asyncpg://user:pass@localhost/poly_cashbot"],
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL",
    )

    # Polymarket API
    polymarket_api_key: str = Field(
        ...,
        description="Polymarket API key for CLOB access",
    )
    polymarket_secret_key: str = Field(
        ...,
        description="Polymarket secret key for signing orders",
    )
    polymarket_chain_id: int = Field(
        default=137,
        description="Polygon chain ID (137 for mainnet)",
    )
    polymarket_host: str = Field(
        default="https://clob.polymarket.com",
        description="Polymarket CLOB API host",
    )

    # Price Feed APIs
    coingecko_api_key: Optional[str] = Field(
        default=None,
        description="CoinGecko API key (optional, for higher rate limits)",
    )
    coincap_api_key: Optional[str] = Field(
        default=None,
        description="CoinCap API key (optional, fallback price feed)",
    )

    # News APIs
    newsapi_key: Optional[str] = Field(
        default=None,
        description="NewsAPI key for crypto news",
    )
    gnews_api_key: Optional[str] = Field(
        default=None,
        description="GNews API key (fallback news source)",
    )

    # Risk Management
    starting_capital: Decimal = Field(
        ...,
        description="Initial trading capital in USDC",
        gt=Decimal("0"),
    )
    per_trade_risk_pct: Decimal = Field(
        default=Decimal("0.02"),
        description="Maximum risk per trade as percentage of capital (0.02 = 2%)",
        ge=Decimal("0"),
        le=Decimal("0.20"),
    )
    daily_loss_limit_pct: Decimal = Field(
        default=Decimal("0.10"),
        description="Maximum daily loss as percentage of capital (0.10 = 10%)",
        ge=Decimal("0"),
        le=Decimal("0.50"),
    )
    max_concurrent_positions: int = Field(
        default=5,
        description="Maximum number of concurrent open positions",
        ge=1,
        le=20,
    )
    min_position_size: Decimal = Field(
        default=Decimal("5.00"),
        description="Minimum position size in USDC",
        gt=Decimal("0"),
    )

    # Trading Strategy
    min_confidence_threshold: Decimal = Field(
        default=Decimal("0.80"),
        description="Minimum confidence score to execute trade (0.80 = 80%)",
        ge=Decimal("0.50"),
        le=Decimal("0.99"),
    )
    min_sentiment_magnitude: Decimal = Field(
        default=Decimal("40"),
        description="Minimum sentiment score magnitude to trade (40 = ±40)",
        ge=Decimal("0"),
        le=Decimal("100"),
    )
    min_market_liquidity: Decimal = Field(
        default=Decimal("10000"),
        description="Minimum market liquidity in USDC",
        ge=Decimal("1000"),
    )
    priority_crypto_asset: str = Field(
        default="XRP",
        description="Priority crypto asset for market filtering",
        pattern="^(XRP|BTC|ETH)$",
    )

    # Telegram Alerts
    telegram_bot_token: str = Field(
        ...,
        description="Telegram bot token for alerts",
    )
    telegram_chat_id: str = Field(
        ...,
        description="Telegram chat ID for sending alerts",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or console)",
        pattern="^(json|console)$",
    )

    # Paper Trading Mode
    paper_trading: bool = Field(
        default=False,
        description="Enable paper trading mode (no real orders)",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses asyncpg driver."""
        if "postgresql://" in v and "asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://")
        return v

    @field_validator("starting_capital")
    @classmethod
    def validate_starting_capital(cls, v: Decimal) -> Decimal:
        """Ensure starting capital is reasonable."""
        if v < Decimal("10"):
            raise ValueError("Starting capital must be at least $10")
        if v > Decimal("1000000"):
            raise ValueError("Starting capital seems unreasonably high")
        return v


# Global settings instance
settings = Settings()
