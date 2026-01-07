"""Simple logging configuration."""

import logging
import time
from functools import wraps
from typing import Any, Callable


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Output format ("json" or "console")
    """
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler()],
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically module name)

    Returns:
        Configured logger
    """
    return logging.getLogger(name)


def log_api_call(operation: str) -> Callable:
    """
    Decorator to log API calls with timing information.

    Args:
        operation: Name of the API operation

    Returns:
        Decorator function

    Example:
        @log_api_call("get_markets")
        async def get_markets(self):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                logger.info(
                    "api_call_success",
                    operation=operation,
                    duration_ms=round(duration_ms, 2),
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                logger.error(
                    "api_call_failed",
                    operation=operation,
                    duration_ms=round(duration_ms, 2),
                    error_type=type(e).__name__,
                    error_message=str(e),
                )

                raise

        return wrapper

    return decorator
