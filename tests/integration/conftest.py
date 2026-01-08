"""Integration test fixtures - isolated from unit tests."""

import pytest
import logging


# Disable logging in integration tests
@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during integration tests."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


# Add integration test marker
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (run separately)"
    )
