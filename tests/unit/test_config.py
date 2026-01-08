"""Tests for configuration system (src/config.py)."""

import os
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from src.config import Settings


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Clean environment and point to empty .env file."""
    # Create empty .env file in temp dir
    empty_env = tmp_path / ".env"
    empty_env.write_text("")

    # Change to temp directory so Settings doesn't load project .env
    monkeypatch.chdir(tmp_path)

    # Clear all relevant environment variables
    env_vars = [
        "DATABASE_URL", "REDIS_URL", "POLYMARKET_API_KEY", "POLYMARKET_SECRET_KEY",
        "POLYMARKET_CHAIN_ID", "POLYMARKET_HOST", "COINGECKO_API_KEY",
        "COINCAP_API_KEY", "NEWSAPI_KEY", "GNEWS_API_KEY", "STARTING_CAPITAL",
        "PER_TRADE_RISK_PCT", "DAILY_LOSS_LIMIT_PCT", "MAX_CONCURRENT_POSITIONS",
        "MIN_POSITION_SIZE", "MIN_CONFIDENCE_THRESHOLD", "MIN_SENTIMENT_MAGNITUDE",
        "MIN_MARKET_LIQUIDITY", "PRIORITY_CRYPTO_ASSET", "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID", "LOG_LEVEL", "LOG_FORMAT", "PAPER_TRADING"
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


class TestSettingsDefaults:
    """Test default values for configuration settings."""

    def test_redis_url_default(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Redis URL has correct default value."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert settings.redis_url == "redis://localhost:6379"

    def test_polymarket_chain_id_default(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Polymarket chain ID defaults to Polygon mainnet (137)."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert settings.polymarket_chain_id == 137

    def test_polymarket_host_default(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Polymarket host has correct default value."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert settings.polymarket_host == "https://clob.polymarket.com"

    def test_risk_management_defaults(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test risk management parameters have correct defaults."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert settings.per_trade_risk_pct == Decimal("0.02")
        assert settings.daily_loss_limit_pct == Decimal("0.10")
        assert settings.max_concurrent_positions == 5
        assert settings.min_position_size == Decimal("5.00")

    def test_trading_strategy_defaults(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test trading strategy parameters have correct defaults."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert settings.min_confidence_threshold == Decimal("0.80")
        assert settings.min_sentiment_magnitude == Decimal("40")
        assert settings.min_market_liquidity == Decimal("10000")
        assert settings.priority_crypto_asset == "XRP"

    def test_logging_defaults(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test logging configuration has correct defaults."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert settings.log_level == "INFO"
        assert settings.log_format == "json"

    def test_paper_trading_default(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test paper trading mode defaults to False."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert settings.paper_trading is False

    def test_optional_api_keys_default_none(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test optional API keys default to None."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert settings.coingecko_api_key is None
        assert settings.coincap_api_key is None
        assert settings.newsapi_key is None
        assert settings.gnews_api_key is None


class TestSettingsValidation:
    """Test field validation for configuration settings."""

    def test_database_url_auto_adds_asyncpg(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database URL validator automatically adds asyncpg driver."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert "asyncpg" in settings.database_url
        assert settings.database_url == "postgresql+asyncpg://test:test@localhost/test"

    def test_database_url_preserves_asyncpg(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database URL validator preserves existing asyncpg driver."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert settings.database_url == "postgresql+asyncpg://test:test@localhost/test"

    def test_starting_capital_minimum_validation(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test starting capital validator rejects values below $10."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "5")  # Below minimum
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "Starting capital must be at least $10" in str(exc_info.value)

    def test_starting_capital_maximum_validation(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test starting capital validator rejects unreasonably high values."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "2000000")  # Above maximum
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "Starting capital seems unreasonably high" in str(exc_info.value)

    def test_starting_capital_valid_range(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test starting capital accepts values in valid range."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "10000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert settings.starting_capital == Decimal("10000")


class TestSettingsTypeConversion:
    """Test type conversion for configuration settings."""

    def test_decimal_fields_from_string(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Decimal fields are correctly parsed from string environment variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "5000.50")
        monkeypatch.setenv("PER_TRADE_RISK_PCT", "0.03")
        monkeypatch.setenv("DAILY_LOSS_LIMIT_PCT", "0.15")
        monkeypatch.setenv("MIN_POSITION_SIZE", "10.00")
        monkeypatch.setenv("MIN_CONFIDENCE_THRESHOLD", "0.85")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert isinstance(settings.starting_capital, Decimal)
        assert settings.starting_capital == Decimal("5000.50")
        assert isinstance(settings.per_trade_risk_pct, Decimal)
        assert settings.per_trade_risk_pct == Decimal("0.03")

    def test_integer_fields_from_string(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test integer fields are correctly parsed from string environment variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("POLYMARKET_CHAIN_ID", "80001")  # Mumbai testnet
        monkeypatch.setenv("MAX_CONCURRENT_POSITIONS", "10")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        settings = Settings()
        assert isinstance(settings.polymarket_chain_id, int)
        assert settings.polymarket_chain_id == 80001
        assert isinstance(settings.max_concurrent_positions, int)
        assert settings.max_concurrent_positions == 10

    def test_boolean_fields_from_string(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test boolean fields are correctly parsed from string environment variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")
        monkeypatch.setenv("PAPER_TRADING", "true")

        settings = Settings()
        assert isinstance(settings.paper_trading, bool)
        assert settings.paper_trading is True

    def test_boolean_false_from_string(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test boolean False is correctly parsed from string environment variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")
        monkeypatch.setenv("PAPER_TRADING", "false")

        settings = Settings()
        assert settings.paper_trading is False


class TestSettingsRequiredFields:
    """Test that required fields raise validation errors when missing."""

    def test_database_url_required(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database URL is required."""
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "database_url" in str(exc_info.value).lower()

    def test_polymarket_api_key_required(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Polymarket API key is required."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "polymarket_api_key" in str(exc_info.value).lower()

    def test_starting_capital_required(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test starting capital is required."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "starting_capital" in str(exc_info.value).lower()

    def test_telegram_bot_token_required(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Telegram bot token is required."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "telegram_bot_token" in str(exc_info.value).lower()


class TestSettingsRangeValidation:
    """Test range validation for numeric fields."""

    def test_per_trade_risk_pct_range(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test per_trade_risk_pct must be between 0 and 0.20."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")
        monkeypatch.setenv("PER_TRADE_RISK_PCT", "0.25")  # Above maximum

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "per_trade_risk_pct" in str(exc_info.value).lower()

    def test_min_confidence_threshold_range(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test min_confidence_threshold must be between 0.50 and 0.99."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")
        monkeypatch.setenv("MIN_CONFIDENCE_THRESHOLD", "0.40")  # Below minimum

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "min_confidence_threshold" in str(exc_info.value).lower()

    def test_max_concurrent_positions_range(self, clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test max_concurrent_positions must be between 1 and 20."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("POLYMARKET_API_KEY", "test_api_key")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", "test_secret_key")
        monkeypatch.setenv("STARTING_CAPITAL", "1000")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")
        monkeypatch.setenv("MAX_CONCURRENT_POSITIONS", "25")  # Above maximum

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "max_concurrent_positions" in str(exc_info.value).lower()
