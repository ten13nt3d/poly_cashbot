# Integration Testing Guide

## Overview

Integration tests verify that services work together correctly. Unlike unit tests which mock all dependencies, integration tests use real implementations where possible (while still mocking external APIs).

## Test Structure

```
tests/integration/
├── __init__.py
├── conftest.py              # Integration-specific fixtures
└── test_simple_integration.py  # Basic service integration tests
```

## Running Integration Tests

### Run integration tests only
```bash
poetry run pytest tests/integration/ -v
```

### Run specific integration test
```bash
poetry run pytest tests/integration/test_simple_integration.py -v
```

### Run integration tests with markers
```bash
poetry run pytest -m integration
```

## Test Categories

### 1. Service Integration Tests
Tests that verify services can be instantiated and used together:
- PolymarketClient in paper trading mode
- PriceFeedService with mocked Redis
- Multiple services coexisting without conflicts

### 2. Component Integration Tests
Tests that verify internal components work together:
- Circuit breaker with retry logic
- Caching layer with API fallback
- Database persistence with service layer

## Test Isolation

Integration tests are isolated from unit tests to prevent test fixture conflicts:

1. **Separate conftest.py**: Integration tests have their own fixtures
2. **Logging disabled**: Prevents structlog issues in test environment
3. **External APIs mocked**: Only test our integration logic, not external services
4. **Minimal database usage**: Avoid complex session-scoped database fixtures

## Known Limitations

### Database Integration Tests
Full database integration tests (with test_engine fixture) have pytest async fixture conflicts when run together with unit tests. Two solutions:

1. **Simple approach (current)**: Test services with mocked dependencies
2. **Full integration**: Run database tests separately with:
   ```bash
   pytest tests/integration/test_database_*.py -v
   ```

### Event Loop Warnings
The session-scoped event loop fixture in `tests/conftest.py` causes deprecation warnings. This is a known pytest-asyncio issue and doesn't affect test functionality.

## Writing Integration Tests

### Good Integration Test
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_services_work_together():
    """Test that services can coexist and interact."""
    # Create real service instances
    poly_client = PolymarketClient(paper_trading=True)

    # Mock only external dependencies
    mock_redis = AsyncMock()
    with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
        price_feed = PriceFeedService()

        # Test interaction
        mock_redis.get.return_value = "2.45"
        price = await price_feed.get_price("XRP")

        order = {"market_id": "test", "side": "BUY", "size": 100, "price": 0.55}
        result = await poly_client.submit_order(order)

        # Verify both worked
        assert price == Decimal("2.45")
        assert result["status"] == "simulated"

        await price_feed.close()
```

### What to Mock
- ✅ External APIs (Polymarket, CoinGecko, CoinCap)
- ✅ Redis connections (use AsyncMock)
- ✅ HTTP clients for external services
- ❌ Our own service classes
- ❌ Internal business logic
- ❌ Database models (use real models)

### What NOT to Mock
Integration tests should use real implementations of:
- Service classes (PolymarketClient, PriceFeedService, MarketDiscoveryService)
- Internal logic (circuit breakers, retry logic, filtering)
- Database models (Market, Position, Trade, etc.)

## Test Coverage Goals

Integration tests complement unit tests:
- **Unit tests**: 95%+ coverage of individual components
- **Integration tests**: Verify components work together correctly
- **E2E tests**: Test full bot workflow (separate suite)

Integration tests don't need high coverage metrics - they verify integration points, not line-by-line coverage.

## Troubleshooting

### Tests fail when run together with unit tests
This is due to pytest fixture scoping with async tests. Run integration tests separately:
```bash
poetry run pytest tests/integration/ -v
```

### "Event loop is closed" errors
Ensure you're using `@pytest.mark.asyncio` decorator on async tests.

### Database connection errors
Integration tests should mock the database or use isolated fixtures. Full database integration testing should be done in separate test files.

### Logging errors (TypeError with kwargs)
The `disable_logging` fixture in `tests/integration/conftest.py` fixes this. Ensure it's being used.

## Future Improvements

1. **Docker-based integration tests**: Spin up real Redis and PostgreSQL in containers
2. **API contract tests**: Verify our mocks match real API behavior
3. **Performance tests**: Measure service response times and throughput
4. **Load tests**: Test circuit breakers and retry logic under heavy load

## Related Documentation

- [Testing Plan](TESTING_PLAN.md) - Overall testing strategy
- [TODO Testing](TODO_TESTING.md) - Detailed task breakdown
- [Next Session](NEXT_SESSION.md) - Current development status
