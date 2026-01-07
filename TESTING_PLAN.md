# Comprehensive Testing Plan for poly_cashbot

## Current Status
- ✅ **analyzer.py**: 91% coverage (31 tests)
- ✅ **Overall coverage**: 87.52% (with omissions)
- 🎯 **Target**: 80%+ coverage for ALL modules

## Phase 1: Models Layer Tests (Easiest - ~2-3 hours)
*Models already have 62-92% coverage, need to fill gaps*

### 1.1 Complete models/position.py (62% → 95%)
**File**: `tests/unit/test_position_model.py`
**Missing**: Lines 79-85, 89-91, 95-101
**Tests needed**:
- [ ] Test position lifecycle methods (open, update, close)
- [ ] Test position PnL calculations
- [ ] Test position risk metrics
- [ ] Test position state transitions
- [ ] Test edge cases (zero values, negative amounts)

### 1.2 Complete models/base.py (71% → 95%)
**File**: `tests/unit/test_base_model.py`
**Missing**: Lines 33-36
**Tests needed**:
- [ ] Test timestamp auto-generation
- [ ] Test base model serialization
- [ ] Test model equality and hashing

### 1.3 Complete models/market.py (80% → 95%)
**File**: `tests/unit/test_market_model.py`
**Missing**: Lines 59, 63-65, 69
**Tests needed**:
- [ ] Test market status transitions
- [ ] Test market resolution logic
- [ ] Test market validation rules

### 1.4 Complete other models (85-92% → 95%)
**Files**: 
- `tests/unit/test_order_model.py` (88% → 95%)
- `tests/unit/test_sentiment_model.py` (85% → 95%)
- `tests/unit/test_trade_model.py` (89% → 95%)
- `tests/unit/test_whale_alert_model.py` (92% → 95%)

**Tests needed**:
- [ ] Test order lifecycle and status changes
- [ ] Test sentiment score calculations
- [ ] Test trade execution tracking
- [ ] Test whale alert thresholds

## Phase 2: Core Libraries Tests (~4-6 hours)

### 2.1 lib/risk/manager.py (0% → 85%)
**File**: `tests/unit/test_risk_manager.py`
**Statements**: 126 lines
**Priority**: HIGH (critical for trading safety)

**Tests needed**:
- [ ] Test position sizing calculations
- [ ] Test risk limits enforcement (max position, max loss)
- [ ] Test circuit breaker activation/deactivation
- [ ] Test portfolio risk aggregation
- [ ] Test stop-loss and take-profit triggers
- [ ] Test leverage calculations
- [ ] Test correlation risk checks
- [ ] Test edge cases (zero balance, negative values)
- [ ] Test concurrent position management
- [ ] Test risk metrics reporting

**Key Methods to Test**:
```python
- calculate_position_size()
- check_risk_limits()
- update_exposure()
- trigger_circuit_breaker()
- calculate_portfolio_risk()
- apply_stop_loss()
- validate_trade()
```

### 2.2 lib/strategy/interval_strategy.py (0% → 85%)
**File**: `tests/unit/test_interval_strategy.py`
**Statements**: 170 lines
**Priority**: HIGH (core trading logic)

**Tests needed**:
- [ ] Test signal generation for 15-minute intervals
- [ ] Test entry/exit criteria evaluation
- [ ] Test position management logic
- [ ] Test win rate tracking
- [ ] Test strategy state machine
- [ ] Test market condition filtering
- [ ] Test timing and scheduling logic
- [ ] Test strategy performance metrics
- [ ] Test edge cases (market close, low liquidity)
- [ ] Test strategy parameter validation

**Key Methods to Test**:
```python
- generate_signals()
- should_enter_trade()
- should_exit_trade()
- calculate_win_rate()
- evaluate_market_conditions()
- update_strategy_state()
```

### 2.3 lib/whale/detector.py (0% → 85%)
**File**: `tests/unit/test_whale_detector.py`
**Statements**: 156 lines
**Priority**: MEDIUM

**Tests needed**:
- [ ] Test whale trade detection thresholds
- [ ] Test volume spike detection
- [ ] Test whale alert generation
- [ ] Test alert filtering and deduplication
- [ ] Test historical whale tracking
- [ ] Test whale impact estimation
- [ ] Test alert priority classification
- [ ] Test edge cases (small markets, flash trades)

**Key Methods to Test**:
```python
- detect_whale_activity()
- calculate_trade_size_percentile()
- generate_alert()
- filter_noise()
- estimate_market_impact()
```

## Phase 3: Services Layer Tests (~6-8 hours)

### 3.1 services/polymarket.py (0% → 85%)
**File**: `tests/unit/test_polymarket_service.py`
**Statements**: 120 lines
**Priority**: HIGH (external API integration)

**Tests needed**:
- [ ] Test market data fetching (mock HTTP requests)
- [ ] Test order placement
- [ ] Test order cancellation
- [ ] Test position queries
- [ ] Test balance queries
- [ ] Test error handling (network errors, API errors)
- [ ] Test rate limiting
- [ ] Test retry logic
- [ ] Test authentication
- [ ] Test websocket connection management
- [ ] Test data parsing and validation

**Key Methods to Test**:
```python
- fetch_markets()
- place_order()
- cancel_order()
- get_positions()
- get_balance()
- handle_api_error()
- parse_market_data()
```

**Mocking Strategy**:
```python
@pytest.fixture
def mock_polymarket_client(mocker):
    mock = mocker.Mock()
    mock.fetch_markets.return_value = [...]
    return mock
```

### 3.2 services/price_feed.py (0% → 85%)
**File**: `tests/unit/test_price_feed.py`
**Statements**: 110 lines
**Priority**: HIGH (real-time price data)

**Tests needed**:
- [ ] Test real-time price streaming
- [ ] Test price aggregation from multiple sources
- [ ] Test OHLCV data generation
- [ ] Test price update callbacks
- [ ] Test websocket reconnection
- [ ] Test data validation
- [ ] Test stale data detection
- [ ] Test price anomaly detection
- [ ] Test historical data fetching
- [ ] Test concurrent feed management

**Key Methods to Test**:
```python
- start_feed()
- stop_feed()
- get_latest_price()
- aggregate_prices()
- handle_price_update()
- detect_anomaly()
```

### 3.3 services/market_discovery.py (0% → 85%)
**File**: `tests/unit/test_market_discovery.py`
**Statements**: 112 lines
**Priority**: MEDIUM

**Tests needed**:
- [ ] Test market scanning and filtering
- [ ] Test 15-minute market identification
- [ ] Test market liquidity checks
- [ ] Test market eligibility criteria
- [ ] Test market ranking/scoring
- [ ] Test cache management
- [ ] Test periodic market updates
- [ ] Test market blacklist/whitelist

**Key Methods to Test**:
```python
- discover_markets()
- filter_15min_markets()
- check_liquidity()
- score_market()
- refresh_market_list()
```

## Phase 4: Bot Main Loop Tests (~4-5 hours)

### 4.1 bot/main.py (0% → 80%)
**File**: `tests/unit/test_bot_main.py`
**Statements**: 292 lines
**Priority**: HIGH (orchestration logic)

**Tests needed**:
- [ ] Test bot initialization
- [ ] Test main trading loop
- [ ] Test signal processing
- [ ] Test trade execution flow
- [ ] Test error recovery
- [ ] Test graceful shutdown
- [ ] Test state persistence
- [ ] Test logging and monitoring
- [ ] Test scheduled tasks
- [ ] Test event handling
- [ ] Test integration between components
- [ ] Test concurrent operation

**Key Methods to Test**:
```python
- initialize_bot()
- run_trading_loop()
- process_signal()
- execute_trade()
- handle_error()
- shutdown()
- persist_state()
```

**Integration Test Strategy**:
```python
@pytest.fixture
def bot_with_mocks(mocker):
    # Mock all external dependencies
    mock_polymarket = mocker.Mock()
    mock_price_feed = mocker.Mock()
    mock_risk_manager = mocker.Mock()
    
    bot = Bot(
        polymarket=mock_polymarket,
        price_feed=mock_price_feed,
        risk_manager=mock_risk_manager
    )
    return bot, mock_polymarket, mock_price_feed, mock_risk_manager
```

## Phase 5: Infrastructure Tests (~2-3 hours)

### 5.1 config.py (0% → 80%)
**File**: `tests/unit/test_config.py`
**Statements**: 45 lines

**Tests needed**:
- [ ] Test config loading from environment
- [ ] Test config validation
- [ ] Test default values
- [ ] Test config overrides
- [ ] Test missing required config

### 5.2 database.py (0% → 80%)
**File**: `tests/unit/test_database.py`
**Statements**: 79 lines

**Tests needed**:
- [ ] Test database connection
- [ ] Test session management
- [ ] Test transaction handling
- [ ] Test connection pooling
- [ ] Test migration compatibility

## Testing Best Practices

### Mock External Dependencies
```python
# Example: Mocking HTTP requests
@pytest.fixture
def mock_httpx(mocker):
    mock = mocker.patch('httpx.AsyncClient')
    mock.return_value.get.return_value.json.return_value = {...}
    return mock
```

### Use Fixtures for Test Data
```python
@pytest.fixture
def sample_market():
    return Market(
        market_id="0x123",
        question="Will BTC be above $50k?",
        end_time=datetime.now() + timedelta(minutes=15)
    )
```

### Test Edge Cases
- Null/None values
- Empty lists/dicts
- Zero values
- Negative values
- Very large values
- Concurrent operations
- Network failures
- Timeouts

### Async Test Pattern
```python
@pytest.mark.asyncio
async def test_async_operation(mock_service):
    result = await service.fetch_data()
    assert result is not None
```

## Execution Timeline

### Week 1: Foundation
- Day 1-2: Complete Models tests (Phase 1)
- Day 3-4: Core Libraries - Risk Manager (Phase 2.1)
- Day 5: Core Libraries - Strategy (Phase 2.2)

### Week 2: Services & Integration
- Day 1-2: Services - Polymarket & Price Feed (Phase 3.1, 3.2)
- Day 3: Services - Market Discovery (Phase 3.3)
- Day 4-5: Bot Main Loop (Phase 4)

### Week 3: Cleanup & Optimization
- Day 1: Infrastructure tests (Phase 5)
- Day 2-3: Increase coverage for all modules to 90%+
- Day 4: Remove all coverage omissions
- Day 5: Final verification and documentation

## Success Criteria

- [ ] All modules have ≥85% test coverage
- [ ] Total project coverage ≥80% (without omissions)
- [ ] All tests pass reliably
- [ ] No flaky tests
- [ ] Test execution time <30 seconds
- [ ] CI/CD pipeline green
- [ ] Documentation updated

## Notes

- Start with Phase 1 (models) as they're easiest and already have partial coverage
- Phase 2 (core libs) is most critical for trading safety
- Phase 3 (services) requires careful mocking of external APIs
- Phase 4 (bot main) requires integration testing approach
- Use `pytest-mock` for all external dependencies
- Use `pytest-asyncio` for async operations
- Use `pytest-cov` to track coverage improvements
