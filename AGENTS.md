# AI Agent Coordination Guide
# XRP Polymarket Cash Bot

**Version**: 1.0.0
**Date**: 2026-01-04
**Purpose**: Guide AI coding agents (Claude, GPT, etc.) working on this project

---

## Project Overview

**Name**: XRP Polymarket Cash Bot
**Goal**: Achieve >70% win rate trading XRP prediction markets on Polymarket
**Capital**: Scalable from $10 to $1000+
**Tech Stack**: Python 3.11+, PostgreSQL, Redis, Polymarket API

**Core Principles**: Library-first, TDD, API-first, Fail-safe, High observability

---

## For AI Agents: How to Work on This Project

### Before Starting Any Task

1. **Read the Constitution**: `/memory/constitution.md` - This is the law
2. **Check the PRD**: `/docs/prd.md` - Understand requirements
3. **Review Tech Spec**: `/docs/technical-specification.md` - Know the architecture
4. **Check MVP Scope**: `/docs/mvp-definition.md` - Know what's in/out of scope
5. **Follow the Roadmap**: `/docs/roadmap.md` - Know where we are

### Golden Rules for AI Agents

1. **Library-First**: All logic goes in `src/lib/`, not in services or bot
2. **Test-First**: Write tests BEFORE implementation
3. **Type Hints**: Every function must have type hints
4. **Docstrings**: Google-style docstrings on all public functions
5. **No Secrets**: Never hardcode API keys or credentials
6. **Error Handling**: Never use bare `except:`, always specific exceptions
7. **Win Rate Focus**: Every decision should optimize for >70% win rate

---

## Project Structure

```
poly_cashbot/
├── src/
│   ├── lib/                    # PURE LOGIC (no I/O) - AI agents work here most
│   │   ├── sentiment/          # Sentiment analysis algorithms
│   │   │   └── analyzer.py
│   │   ├── whale/              # Whale detection logic
│   │   │   └── detector.py
│   │   ├── strategy/           # Trading strategies
│   │   │   ├── interval_strategy.py
│   │   │   └── frontrun_strategy.py
│   │   └── risk/               # Risk management
│   │       └── manager.py
│   │
│   ├── services/               # EXTERNAL I/O - API clients
│   │   ├── polymarket.py       # Polymarket CLOB client
│   │   ├── price_feed.py       # CoinGecko client
│   │   └── news.py             # CryptoPanic client
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── market.py
│   │   ├── trade.py
│   │   └── position.py
│   │
│   ├── bot/                    # Bot orchestration
│   │   └── main.py             # Entry point
│   │
│   └── cli/                    # CLI commands (if needed)
│
├── tests/
│   ├── unit/                   # Test src/lib/ (fast, isolated)
│   ├── integration/            # Test src/services/ (with real APIs)
│   ├── contract/               # Verify external API schemas
│   ├── e2e/                    # Full workflow tests
│   └── backtest/               # Strategy backtests
│
├── docs/
│   ├── prd.md
│   ├── technical-specification.md
│   ├── mvp-definition.md
│   └── roadmap.md
│
├── memory/
│   └── constitution.md         # PROJECT LAW - READ THIS FIRST
│
├── specs/                      # Feature specifications
├── changelog/                  # Version history
├── scripts/                    # Utility scripts
└── .env                        # Secrets (NEVER COMMIT)
```

---

## Common Tasks for AI Agents

### Task 1: Implement a New Trading Strategy

**Location**: `src/lib/strategy/`

**Steps**:
1. Create test file: `tests/unit/test_new_strategy.py`
2. Write failing test:
   ```python
   def test_new_strategy_generates_buy_signal():
       strategy = NewStrategy()
       signal = strategy.analyze(mock_data)
       assert signal.direction == "BUY"
       assert signal.confidence > 0.8
   ```
3. Implement strategy in `src/lib/strategy/new_strategy.py`
4. Make test pass
5. Add docstrings and type hints
6. Run full test suite: `pytest`
7. Update docs if public API changes

**Template**:
```python
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal

@dataclass
class Signal:
    direction: str  # "BUY" or "SELL"
    confidence: float  # 0.0 to 1.0
    sentiment_score: float  # -100 to +100

class NewStrategy:
    """
    One-line description.

    Longer description of what this strategy does,
    when to use it, and expected win rate.
    """

    def analyze(self, data: pd.DataFrame) -> Optional[Signal]:
        """
        Analyze data and generate trading signal.

        Args:
            data: OHLCV price data

        Returns:
            Signal if confidence >80%, else None

        Raises:
            InsufficientDataError: If data has <10 rows
        """
        # Implementation here
        pass
```

### Task 2: Add a New Data Source

**Location**: `src/services/`

**Steps**:
1. Create service file: `src/services/new_datasource.py`
2. Create test file: `tests/integration/test_new_datasource.py`
3. Implement client with error handling:
   ```python
   class NewDataSourceClient:
       def __init__(self, api_key: str):
           self.api_key = api_key
           self.session = httpx.AsyncClient()

       @with_retry(max_attempts=3)
       @with_timeout(seconds=10)
       async def fetch(self) -> pd.DataFrame:
           try:
               response = await self.session.get(
                   "https://api.example.com/data",
                   headers={"Authorization": f"Bearer {self.api_key}"}
               )
               response.raise_for_status()
               return self._parse_response(response.json())
           except httpx.HTTPError as e:
               logger.error("API fetch failed", error=str(e))
               raise DataError(f"Failed to fetch data: {e}")
   ```
4. Add rate limiting
5. Add caching (Redis)
6. Test with real API
7. Add to documentation

### Task 3: Implement Risk Check

**Location**: `src/lib/risk/manager.py`

**Steps**:
1. Add test in `tests/unit/test_risk_manager.py`:
   ```python
   def test_rejects_oversized_position():
       manager = RiskManager(capital=Decimal("1000"))
       order = Order(size=Decimal("200"))  # 20% of capital
       result = manager.validate_order(order)
       assert result.passed == False
       assert "per-trade limit" in result.reason
   ```
2. Implement validation in `RiskManager.validate_order()`
3. Ensure all edge cases tested
4. Coverage must be >95% for risk code
5. Add to risk documentation

### Task 4: Add Telegram Command

**Location**: `src/bot/telegram_bot.py`

**Steps**:
1. Define command handler:
   ```python
   async def handle_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
       """Send performance summary to user"""
       metrics = calculate_performance_metrics()

       message = f"""
       📊 Performance Summary

       Win Rate: {metrics.win_rate:.1%}
       Total P&L: ${metrics.total_pnl:.2f}
       Trades Today: {metrics.trades_today}
       """

       await update.message.reply_text(message)
   ```
2. Register command: `application.add_handler(CommandHandler("performance", handle_performance))`
3. Add to `/help` command
4. Test manually
5. Document in README

### Task 5: Optimize for Win Rate

**When Optimizing**:

AI agents should focus on:
1. **Signal Selectivity**: Increase confidence threshold (80% → 85%)
2. **Multi-Confirmation**: Require more signals to align
3. **Early Exits**: Take profits faster (10-15% targets)
4. **Fast Stops**: Cut losses quickly (<10% per trade)
5. **Market Filters**: Avoid low-liquidity markets (<$10k)
6. **Sentiment Thresholds**: Only trade strong sentiment (>40 or <-40)

**Optimization Loop**:
```python
# Backtest with parameters
results = backtest(confidence_threshold=0.80)
print(f"Win rate: {results.win_rate:.1%}")

if results.win_rate < 0.70:
    # Increase selectivity
    results = backtest(confidence_threshold=0.85)
    print(f"New win rate: {results.win_rate:.1%}")

# Find optimal threshold
best_threshold = optimize_parameter(
    parameter="confidence_threshold",
    target_metric="win_rate",
    target_value=0.70
)
```

---

## Testing Guidelines for AI Agents

### Unit Tests (src/lib/)

**Requirements**:
- Fast (<1ms per test)
- No external dependencies (mock everything)
- >90% coverage
- Test edge cases

**Example**:
```python
import pytest
from unittest.mock import Mock
from src.lib.sentiment.analyzer import SentimentAnalyzer

def test_sentiment_analyzer_returns_high_confidence():
    analyzer = SentimentAnalyzer()

    # Mock price data
    price_data = pd.DataFrame({
        'price': [1.0, 1.05, 1.10, 1.15, 1.20],
        'timestamp': pd.date_range('2024-01-01', periods=5, freq='15min')
    })

    # Mock news data
    news_items = [
        NewsItem(sentiment=0.8, title="XRP surges"),
        NewsItem(sentiment=0.9, title="XRP bullish")
    ]

    signal = analyzer.analyze(price_data, news_items)

    assert signal is not None
    assert signal.confidence > 0.80
    assert signal.direction == "BUY"

def test_sentiment_analyzer_rejects_low_confidence():
    analyzer = SentimentAnalyzer()

    # Choppy price data
    price_data = pd.DataFrame({
        'price': [1.0, 1.02, 0.99, 1.01, 1.00],
        'timestamp': pd.date_range('2024-01-01', periods=5, freq='15min')
    }

    signal = analyzer.analyze(price_data, [])

    assert signal is None  # Should reject low confidence
```

### Integration Tests (src/services/)

**Requirements**:
- Test with real APIs (sandbox/test accounts)
- May be slower (<10s per test)
- >80% coverage
- Test error scenarios

**Example**:
```python
import pytest
from src.services.polymarket import PolymarketClient

@pytest.mark.integration
async def test_polymarket_fetches_markets():
    client = PolymarketClient(api_key=os.getenv("POLYMARKET_TEST_KEY"))

    markets = await client.get_xrp_markets()

    assert len(markets) > 0
    assert all(m.related_asset == "XRP" for m in markets)

@pytest.mark.integration
async def test_polymarket_handles_rate_limit():
    client = PolymarketClient(api_key=os.getenv("POLYMARKET_TEST_KEY"))

    # Spam requests to trigger rate limit
    with pytest.raises(RateLimitError):
        for _ in range(200):
            await client.get_markets()
```

### Backtest Tests

**Requirements**:
- Use historical data (90 days)
- Must show >70% win rate
- Test at different capital levels
- Document results

**Example**:
```python
def test_interval_strategy_achieves_target_win_rate():
    strategy = IntervalStrategy()
    historical_data = load_historical_data(days=90)

    results = backtest(strategy, historical_data, capital=Decimal("1000"))

    assert results.win_rate > 0.70
    assert results.profit_factor > 2.0
    assert results.max_drawdown < 0.25
    print(f"Win rate: {results.win_rate:.1%}")
    print(f"Total P&L: ${results.total_pnl:.2f}")
```

---

## Code Style for AI Agents

### Formatting
```bash
# Before committing, always run:
black src/ tests/                    # Code formatting
ruff check src/ tests/ --fix         # Linting
mypy src/                             # Type checking
```

### Naming Conventions

**Variables**: `snake_case`
```python
win_rate = 0.73
total_pnl = Decimal("285.50")
```

**Functions**: `snake_case`
```python
def calculate_sentiment_score(data: pd.DataFrame) -> float:
    pass
```

**Classes**: `PascalCase`
```python
class SentimentAnalyzer:
    pass
```

**Constants**: `UPPER_SNAKE_CASE`
```python
MIN_CONFIDENCE_THRESHOLD = 0.80
MAX_POSITION_SIZE_PCT = 0.10
```

### Type Hints (Required)

```python
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

def process_trade(
    order: Order,
    market: Market,
    timestamp: datetime
) -> Optional[Trade]:
    """Process order into executed trade"""
    pass

async def fetch_markets() -> List[Market]:
    """Fetch active markets from API"""
    pass
```

### Docstrings (Required)

**Google Style**:
```python
def calculate_position_size(
    capital: Decimal,
    confidence: float,
    risk_pct: float = 0.02
) -> Decimal:
    """
    Calculate position size based on confidence and capital.

    Uses confidence-weighted position sizing to scale
    position size with signal strength while respecting
    risk limits.

    Args:
        capital: Total available capital in dollars
        confidence: Signal confidence (0.0 to 1.0)
        risk_pct: Maximum risk per trade (default: 2%)

    Returns:
        Position size in dollars

    Raises:
        ValueError: If confidence <0 or >1
        ValueError: If capital <=0

    Example:
        >>> calculate_position_size(Decimal("1000"), 0.85, 0.02)
        Decimal("20.00")
    """
    pass
```

---

## Error Handling for AI Agents

### Custom Exceptions

Always use specific exceptions:

```python
# src/lib/exceptions.py
class BotError(Exception):
    """Base exception"""

class DataError(BotError):
    """Data fetch or parse error"""

class TradingError(BotError):
    """Trading execution error"""

class RiskLimitExceeded(TradingError):
    """Risk limit would be exceeded"""

# Usage
if order.size > max_size:
    raise RiskLimitExceeded(
        f"Order size {order.size} exceeds limit {max_size}"
    )
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def fetch_with_retry():
    response = await api_call()
    return response
```

### Circuit Breaker

```python
@with_circuit_breaker(max_failures=5, timeout=300)
async def call_external_api():
    return await api.fetch()
```

---

## Performance Optimization Tips

### Database Queries

**Bad**:
```python
for trade in trades:
    market = db.query(Market).filter_by(id=trade.market_id).first()
```

**Good**:
```python
trades_with_markets = db.query(Trade, Market).join(Market).all()
```

### Caching

```python
import redis

redis_client = redis.Redis()

def get_market(market_id: str) -> Market:
    # Check cache first
    cached = redis_client.get(f"market:{market_id}")
    if cached:
        return Market.from_json(cached)

    # Fetch from API
    market = api.get_market(market_id)

    # Cache for 60 seconds
    redis_client.setex(
        f"market:{market_id}",
        60,
        market.to_json()
    )

    return market
```

### Async/Await

**Bad** (blocking):
```python
def fetch_all_data():
    prices = fetch_prices()  # 2 seconds
    news = fetch_news()      # 3 seconds
    # Total: 5 seconds
```

**Good** (concurrent):
```python
async def fetch_all_data():
    prices, news = await asyncio.gather(
        fetch_prices(),  # 2 seconds
        fetch_news()     # 3 seconds
    )
    # Total: 3 seconds (concurrent)
```

---

## Git Workflow for AI Agents

### Commit Messages

Format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, test, refactor, perf, chore

**Example**:
```
feat(sentiment): add multi-timeframe momentum analysis

Implement momentum calculation for 15m, 1h, and 4h timeframes.
Improves signal confidence by requiring timeframe alignment.

Increases win rate from 68% to 72% in backtests.
```

### Branching

- `main`: Production-ready code
- `feature/whale-detection`: New feature
- `fix/api-rate-limit`: Bug fix

```bash
git checkout -b feature/new-strategy
# ... make changes ...
git add .
git commit -m "feat(strategy): add new interval strategy"
git push origin feature/new-strategy
# Create PR on GitHub
```

---

## AI Agent Success Checklist

Before marking a task complete:

- [ ] All tests passing (`pytest`)
- [ ] Code formatted (`black`, `ruff`)
- [ ] Type checks passing (`mypy`)
- [ ] Coverage >80% (`pytest --cov`)
- [ ] Docstrings on all public functions
- [ ] No secrets committed
- [ ] Updated documentation if needed
- [ ] Backward compatible (or migration plan)
- [ ] Performance acceptable
- [ ] Logs structured (JSON)

---

## Common Pitfalls for AI Agents

### ❌ Don't Do This

1. **Skip tests**: "I'll add tests later"
2. **Hardcode values**: `api_key = "abc123"`
3. **Ignore types**: `def process(data):`
4. **Broad exceptions**: `except Exception:`
5. **No logging**: Silent failures
6. **Forget docs**: Code without context
7. **Optimize early**: Premature optimization

### ✅ Do This Instead

1. **Test-first**: Write test, then code
2. **Use env vars**: `api_key = os.getenv("API_KEY")`
3. **Add type hints**: `def process(data: DataFrame) -> Signal:`
4. **Specific exceptions**: `except httpx.HTTPError as e:`
5. **Log everything**: `logger.info("trade_executed", trade_id=123)`
6. **Document well**: Docstrings + comments
7. **Measure first**: Profile before optimizing

---

## Questions for AI Agents

**Q: Should I implement this feature?**
A: Check MVP scope in `/docs/mvp-definition.md`. If not listed, it's out of scope.

**Q: What testing framework should I use?**
A: pytest for all tests. See `/tests/` for examples.

**Q: How should I handle API errors?**
A: Retry 3 times, exponential backoff, then alert. See constitution Article II.

**Q: Can I use a different database?**
A: No. PostgreSQL is mandated in tech spec. See constitution for exceptions process.

**Q: What's the target win rate?**
A: >70% for MVP. This is the primary KPI. Optimize for this above all else.

**Q: Can I skip type hints?**
A: No. Type hints are required (constitution Article II). CI will fail without them.

**Q: How do I add a new dependency?**
A: Add to `pyproject.toml`, run `poetry install`, commit lockfile.

---

## Resources for AI Agents

### Internal Docs
- Constitution: `/memory/constitution.md`
- PRD: `/docs/prd.md`
- Tech Spec: `/docs/technical-specification.md`
- MVP Scope: `/docs/mvp-definition.md`
- Roadmap: `/docs/roadmap.md`

### External Docs
- Polymarket API: https://docs.polymarket.com/
- py-clob-client: https://github.com/Polymarket/py-clob-client
- CoinGecko API: https://www.coingecko.com/en/api
- Python 3.11: https://docs.python.org/3.11/
- Pandas: https://pandas.pydata.org/docs/
- SQLAlchemy: https://docs.sqlalchemy.org/

### Code Examples
- Tests: `/tests/` directory
- Libraries: `/src/lib/` directory
- Services: `/src/services/` directory

---

## Final Reminders for AI Agents

1. **Read the Constitution**: It's the law. Follow it.
2. **Test-Driven**: Tests first, then code.
3. **Win Rate First**: Optimize for >70% win rate.
4. **Capital Agnostic**: Support $10 to $1000+.
5. **Type Safety**: mypy strict mode.
6. **Document Everything**: Future you will thank you.
7. **Security**: Never commit secrets.
8. **Performance**: Measure, then optimize.

**When in doubt, ask questions. Better to clarify than assume.**

---

**Version**: 1.0.0
**Last Updated**: 2026-01-04
**For**: Claude Code, GPT-4, and all AI coding assistants
**Contact**: Development Team
