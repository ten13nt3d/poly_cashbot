"""Custom exceptions for the trading bot."""


class BotError(Exception):
    """Base exception for all bot errors."""
    pass


class DataError(BotError):
    """Data fetching or parsing errors."""
    pass


class InsufficientDataError(DataError):
    """Not enough data points for analysis."""
    pass


class TradingError(BotError):
    """Trading execution errors."""
    pass


class RiskLimitExceeded(TradingError):
    """Risk limits would be exceeded."""
    pass


class LowConfidenceError(TradingError):
    """Signal confidence too low for trading."""
    pass


class MarketError(BotError):
    """Market-related errors."""
    pass


class LiquidityInsufficientError(MarketError):
    """Market has insufficient liquidity."""
    pass


class WhaleDetectionError(BotError):
    """Whale detection failed."""
    pass


class OrderExecutionError(TradingError):
    """Order execution failed."""
    pass


class StrategyError(BotError):
    """Strategy-related errors."""
    pass
