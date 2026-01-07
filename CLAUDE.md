# Claude Code Agent Guide
# XRP Polymarket Cash Bot

**Version**: 1.0.0
**Date**: 2026-01-07
**Framework**: RBI (Research → Backtest → Implement)
**For**: Claude Code, Claude Sonnet, and all Claude AI agents

---

## 🏆 Golden Rule: RBI Framework

**RBI (Research → Backtest → Implement)** is the GOLDEN RULE for all quant/algo trading development.

### Why RBI Matters

Jumping straight to implementation without research and backtesting is how trading bots lose money. RBI ensures:
- **No Capital Risk Until Proven**: Never trade real money with unvalidated strategies
- **Data-Driven Decisions**: Every feature backed by backtesting results
- **Systematic Development**: Predictable, repeatable process
- **High Success Rate**: Proven strategies before deployment

### RBI is NOT Optional

Every trading feature, strategy, or algorithm MUST go through all three phases:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│             │     │             │     │             │
│  RESEARCH   │────▶│  BACKTEST   │────▶│  IMPLEMENT  │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
     ↓                   ↓                   ↓
 Understand          Validate            Build
 Problem             Strategy            System
```

**Never skip a phase. Ever.**

---

## Phase 1: RESEARCH (R)

### When to Use Research Phase

- Starting a new strategy
- Adding a new data source
- Changing risk parameters
- Evaluating new market opportunities

### Research Checklist

Before writing ANY code for a trading feature:

- [ ] **Problem Statement**: What are we trying to solve?
- [ ] **Market Analysis**: Is the opportunity real and measurable?
- [ ] **Data Sources**: What data do we need? Is it available?
- [ ] **Success Metrics**: How will we know if it works?
- [ ] **Risk Parameters**: What's the maximum acceptable loss?
- [ ] **Documentation**: PRD/spec written and reviewed

### Research Deliverables

```markdown
## Research Document Template

### Problem Statement
[Clear 1-2 sentence description]

### Market Opportunity
- Size: [Trading volume, available markets]
- Edge: [What information asymmetry exists?]
- Competition: [Who else is trading this?]

### Proposed Strategy
- Entry criteria: [When to enter]
- Exit criteria: [When to exit]
- Position sizing: [How much to risk]
- Expected win rate: [Target %]
- Expected profit factor: [Target ratio]

### Data Requirements
- Historical data: [Source, timeframe, format]
- Real-time data: [API, latency, cost]
- Storage needs: [Database size estimate]

### Success Criteria
- Primary KPI: [e.g., Win rate >70%]
- Secondary KPIs: [e.g., Profit factor >2.0, Max DD <25%]

### Risks
- Market risk: [What if markets change?]
- Technical risk: [What could break?]
- Capital risk: [Maximum loss scenario?]
```

### Research Phase Gate

**Exit Criteria**: All stakeholders agree on:
1. Problem is worth solving
2. Data is available
3. Success metrics are clear
4. Risks are acceptable

**Next Phase**: Proceed to Backtest

---

## Phase 2: BACKTEST (B)

### Golden Rules of Backtesting

1. **Never skip backtesting** - Even "obvious" strategies fail in practice
2. **Use realistic assumptions** - Include fees, slippage, latency
3. **Test multiple scenarios** - Bull, bear, sideways markets
4. **Require statistical significance** - Minimum 100 trades, 90 days
5. **Document everything** - Save all results, parameters, observations

### Backtest Requirements (MANDATORY)

| Requirement | Minimum | Target | Status Check |
|-------------|---------|--------|--------------|
| Historical Period | 90 days | 180 days | `backtest.days >= 90` |
| Number of Trades | 100 | 300+ | `backtest.trades >= 100` |
| Win Rate | 65% | 70%+ | `backtest.win_rate >= 0.70` |
| Profit Factor | 1.5 | 2.0+ | `backtest.profit_factor >= 2.0` |
| Max Drawdown | 30% | <25% | `backtest.max_drawdown < 0.25` |
| Sharpe Ratio | 1.0 | 1.5+ | `backtest.sharpe >= 1.0` |

### Backtest Checklist

- [ ] **Historical Data Collected**: 90+ days of market data
- [ ] **Strategy Implemented**: In isolated test environment
- [ ] **Backtest Executed**: Full historical period tested
- [ ] **Results Documented**: All metrics calculated and saved
- [ ] **Edge Cases Tested**: What happens in crashes, rallies, flat markets?
- [ ] **Parameter Sensitivity**: Tested with ±20% parameter changes
- [ ] **Walk-Forward Analysis**: Out-of-sample validation
- [ ] **Results Review**: Win rate, profit factor, drawdown all meet targets

### Backtest Code Template

```python
# tests/backtest/test_strategy_backtest.py

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from src.lib.backtest import BacktestEngine, BacktestResult
from src.lib.strategy import MyStrategy

def test_strategy_backtest_achieves_target_metrics():
    """
    Backtest MyStrategy over 90 days of historical data.

    Requirements:
    - Win rate >70%
    - Profit factor >2.0
    - Max drawdown <25%
    """
    # Load historical data
    historical_data = load_historical_data(
        start_date=datetime.now() - timedelta(days=90),
        end_date=datetime.now(),
        assets=["XRP", "BTC", "ETH"]
    )

    # Initialize strategy
    strategy = MyStrategy(
        confidence_threshold=0.80,
        sentiment_threshold=40,
        max_positions=3
    )

    # Run backtest
    engine = BacktestEngine(
        initial_capital=Decimal("1000"),
        commission=Decimal("0.01"),  # 1% fees
        slippage=Decimal("0.005")    # 0.5% slippage
    )

    result: BacktestResult = engine.run(strategy, historical_data)

    # Validate requirements
    assert result.win_rate >= 0.70, f"Win rate {result.win_rate:.1%} below target"
    assert result.profit_factor >= 2.0, f"Profit factor {result.profit_factor:.2f} too low"
    assert result.max_drawdown <= 0.25, f"Max drawdown {result.max_drawdown:.1%} too high"
    assert result.total_trades >= 100, f"Only {result.total_trades} trades, need 100+"

    # Print results for documentation
    print("\n" + "="*50)
    print("BACKTEST RESULTS")
    print("="*50)
    print(f"Period: {result.start_date} to {result.end_date}")
    print(f"Total Trades: {result.total_trades}")
    print(f"Win Rate: {result.win_rate:.1%}")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    print(f"Max Drawdown: {result.max_drawdown:.1%}")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Total P&L: ${result.total_pnl:.2f}")
    print("="*50)

    # Save results
    result.save_to_file(f"backtest_results_{datetime.now():%Y%m%d}.json")
```

### What to Do When Backtest Fails

**If win rate <70%**:
1. Increase entry threshold (e.g., confidence 0.80 → 0.85)
2. Add more confirmation signals
3. Reduce position count (be more selective)
4. Analyze losing trades for patterns
5. Consider abandoning strategy if fundamentally flawed

**If profit factor <2.0**:
1. Take profits earlier (smaller targets)
2. Cut losses faster (tighter stops)
3. Reduce trading frequency (higher quality trades)
4. Check if fees/slippage assumptions are realistic

**If max drawdown >25%**:
1. Reduce position sizes
2. Implement stricter risk limits
3. Add circuit breakers
4. Diversify across uncorrelated strategies

### Backtest Phase Gate

**Exit Criteria**:
- ✅ Backtest shows win rate >70%
- ✅ Profit factor >2.0
- ✅ Max drawdown <25%
- ✅ Results documented and reviewed
- ✅ Strategy parameters finalized

**Next Phase**: Proceed to Implement

**CRITICAL**: If backtest fails, return to Research phase. Do NOT implement a failing strategy.

---

## Phase 3: IMPLEMENT (I)

### Implementation with TDD

Now that strategy is validated, implement with Test-Driven Development:

```
For each component:
1. Write test first (fails)
2. Implement code (test passes)
3. Refactor (test still passes)
4. Repeat
```

### Implementation Checklist

- [ ] **Core Logic in src/lib/**: Pure Python, no I/O
- [ ] **Unit Tests**: >90% coverage for all libraries
- [ ] **Integration Tests**: Services tested with real APIs
- [ ] **Type Hints**: Every function has type annotations
- [ ] **Docstrings**: Google-style on all public functions
- [ ] **Error Handling**: Specific exceptions, no bare `except:`
- [ ] **Logging**: Structured logging for all decisions
- [ ] **Paper Trading**: Run with fake money first
- [ ] **Monitoring**: Metrics, alerts, dashboards
- [ ] **Deployment**: Automated, repeatable process

### RBI-Compliant Implementation Example

```python
# src/lib/strategy/my_strategy.py

from typing import Optional
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class Signal:
    """Trading signal from strategy."""
    direction: str  # "BUY" or "SELL"
    confidence: float  # 0.0 to 1.0
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal

    # RBI Metadata
    backtest_win_rate: float  # From backtest results
    backtest_profit_factor: float
    research_doc: str  # Link to research document

class MyStrategy:
    """
    My validated trading strategy.

    **RBI Status**: PRODUCTION READY

    Research Phase:
        - Completed: 2026-01-05
        - Document: /docs/research/my-strategy-research.md
        - Market edge: Whale front-running with sentiment confirmation

    Backtest Phase:
        - Period: 2025-10-01 to 2026-01-01 (90 days)
        - Win rate: 72.5% (target: >70%)
        - Profit factor: 2.3 (target: >2.0)
        - Max drawdown: 18% (target: <25%)
        - Document: /docs/backtest/my-strategy-backtest-20260105.json

    Implementation:
        - Test coverage: 95%
        - Paper trading: 14 days, 71% win rate
        - Live capital: $50 pilot, 73% win rate over 30 trades

    Parameters (optimized via backtest):
        - confidence_threshold: 0.82
        - sentiment_threshold: 45
        - take_profit_pct: 0.15
        - stop_loss_pct: 0.08
    """

    def __init__(self, confidence_threshold: float = 0.82):
        self.confidence_threshold = confidence_threshold
        # Store RBI metadata
        self.rbi_metadata = {
            "research_doc": "/docs/research/my-strategy-research.md",
            "backtest_results": "/docs/backtest/my-strategy-backtest-20260105.json",
            "validated_win_rate": 0.725,
            "validated_profit_factor": 2.3
        }

    def analyze(self, data: dict) -> Optional[Signal]:
        """
        Generate trading signal if conditions met.

        RBI validation: This method has been backtested over 90 days
        with a 72.5% win rate. Only generates signals when confidence
        exceeds the optimized threshold of 0.82.
        """
        # Implementation...
        pass
```

### Implementation Phase Gate

**Exit Criteria**:
- ✅ All tests passing (>90% coverage)
- ✅ Paper trading shows >65% win rate (7-14 days)
- ✅ Infrastructure tested (database, monitoring)
- ✅ Deployment automated
- ✅ Runbook documented

**Next Phase**: Production deployment with small capital

---

## Claude Code Workflow with RBI

### Starting a New Task

```bash
# 1. Check RBI status
cat RBI_STATUS.md

# 2. Determine which RBI phase applies
# - Adding new strategy? Start at Research
# - Optimizing existing? May skip Research, re-run Backtest
# - Bug fix? Implement only (no RBI needed)
# - New data source? Research + Backtest

# 3. Create appropriate documentation
# For Research: Create /docs/research/feature-name.md
# For Backtest: Create /tests/backtest/test_feature_backtest.py
# For Implement: Create /src/lib/feature.py + /tests/unit/test_feature.py
```

### Example: Adding Whale Detection Feature

#### Phase 1: Research (Day 1)

```bash
# Create research document
cat > docs/research/whale-detection-research.md <<EOF
# Whale Detection Strategy Research

## Problem Statement
Large traders ("whales") move markets. Detecting their orders before execution allows front-running for profit.

## Market Opportunity
- Polymarket: 5-10 whale orders per day in XRP markets
- Average size: $10k-$50k (10-50x typical order)
- Detection window: 15-45 seconds before execution
- Expected edge: 2-3% profit per front-run

## Proposed Strategy
1. Monitor orderbook for orders >10x average size
2. Calculate expected price impact
3. Place smaller order ahead of whale
4. Take profit when whale moves price
5. Stop loss if whale cancels

## Data Requirements
- Real-time orderbook via WebSocket
- Historical whale order database
- Average order size metrics per market

## Success Criteria
- Detect >80% of whale orders (>$10k size)
- False positive rate <10%
- Front-run execution <5 seconds
- Expected win rate: 75%+ (better than base 70%)

## Risks
- Whale may cancel order
- Slippage on execution
- Market may not move as expected
- Polymarket may detect and ban
EOF

# Get approval before proceeding
echo "Research phase complete. Proceed to backtest? (y/n)"
```

#### Phase 2: Backtest (Day 2-3)

```python
# tests/backtest/test_whale_detection_backtest.py

def test_whale_detection_historical_performance():
    """
    Backtest whale detection over 90 days.

    Expected results:
    - Detection rate >80%
    - Win rate >75%
    - Profit factor >2.5
    """
    # Load 90 days of orderbook data
    historical_orderbook = load_orderbook_history(days=90)

    # Initialize whale detector
    detector = WhaleDetector(
        size_threshold_multiplier=10.0,
        min_absolute_size=Decimal("10000")
    )

    # Simulate detection and trading
    results = simulate_whale_trading(
        detector=detector,
        orderbook_data=historical_orderbook,
        capital=Decimal("1000")
    )

    # Validate
    assert results.detection_rate >= 0.80
    assert results.win_rate >= 0.75
    assert results.profit_factor >= 2.5

    print(f"Detection rate: {results.detection_rate:.1%}")
    print(f"Win rate: {results.win_rate:.1%}")
    print(f"Profit factor: {results.profit_factor:.2f}")
```

#### Phase 3: Implement (Day 4-6)

```python
# src/lib/whale/detector.py

class WhaleDetector:
    """
    Detect large orders in Polymarket orderbook.

    RBI Status: VALIDATED
    - Research: /docs/research/whale-detection-research.md
    - Backtest: 82% detection rate, 76% win rate, 2.6 profit factor
    - Backtest period: 90 days (2025-10-01 to 2026-01-01)
    """

    def detect(self, orderbook: Orderbook) -> Optional[WhaleAlert]:
        """Detect whale orders in orderbook."""
        # Tested implementation
        pass

# tests/unit/test_whale_detector.py

def test_whale_detector_identifies_large_orders():
    """Test whale detector finds orders >10x average."""
    # Unit test implementation
    pass
```

---

## Common RBI Violations (DON'T DO THIS)

### ❌ Skipping Research

```python
# BAD: Implementing without understanding
def new_strategy():
    # "I think this will work, let's code it"
    return random_algorithm()  # No research, no edge
```

**Fix**: Write research doc first. Understand the market opportunity.

### ❌ Skipping Backtest

```python
# BAD: Going straight to production
strategy = MyStrategy()
trade_with_real_money(strategy)  # DISASTER WAITING TO HAPPEN
```

**Fix**: Run 90-day backtest first. Validate win rate >70%.

### ❌ Incomplete Backtest

```python
# BAD: Testing on 7 days of data
backtest(strategy, days=7)  # Not statistically significant
```

**Fix**: Minimum 90 days, 100+ trades. Longer is better.

### ❌ Ignoring Failed Backtest

```python
# BAD: Deploying despite 45% win rate
result = backtest(strategy, days=90)
assert result.win_rate == 0.45
deploy_anyway(strategy)  # "Maybe it'll work in production"
```

**Fix**: Return to Research. Fix strategy or abandon it.

### ❌ No Documentation

```python
# BAD: No RBI metadata
class Strategy:
    """Some strategy."""  # Where's the research? Backtest results?
    pass
```

**Fix**: Document RBI status in docstrings. Link to research and backtest files.

---

## RBI Checklist for Claude Code

Before marking any trading feature complete:

### Research Phase
- [ ] Research document created in `/docs/research/`
- [ ] Problem statement is clear (1-2 sentences)
- [ ] Market opportunity is quantified (size, edge, competition)
- [ ] Data requirements are identified and available
- [ ] Success metrics are defined (win rate, profit factor, drawdown)
- [ ] Risks are documented and acceptable
- [ ] Stakeholders have approved research

### Backtest Phase
- [ ] Historical data collected (90+ days minimum)
- [ ] Backtest code written in `/tests/backtest/`
- [ ] Backtest executed over full historical period
- [ ] Results meet ALL requirements:
  - [ ] Win rate ≥70%
  - [ ] Profit factor ≥2.0
  - [ ] Max drawdown ≤25%
  - [ ] Total trades ≥100
- [ ] Results documented and saved
- [ ] Parameter sensitivity tested
- [ ] Walk-forward validation completed
- [ ] Backtest reviewed and approved

### Implementation Phase
- [ ] Core logic in `/src/lib/` (pure Python, no I/O)
- [ ] Unit tests written FIRST (TDD)
- [ ] Test coverage >90%
- [ ] Integration tests for services
- [ ] Type hints on all functions
- [ ] Docstrings with RBI metadata
- [ ] Error handling (specific exceptions)
- [ ] Logging (structured, JSON)
- [ ] Paper trading validation (7-14 days)
- [ ] Infrastructure tested
- [ ] Deployment automated
- [ ] Monitoring in place
- [ ] Runbook documented

---

## Quick Reference: When to Use Each RBI Phase

| Scenario | Research | Backtest | Implement |
|----------|----------|----------|-----------|
| New trading strategy | ✅ Required | ✅ Required | ✅ Required |
| New data source | ✅ Required | ⚠️ If affects trading | ✅ Required |
| Strategy optimization | ⚠️ Document changes | ✅ Re-backtest | ✅ Implement |
| Bug fix (non-trading) | ❌ Skip | ❌ Skip | ✅ Only this |
| New risk parameter | ✅ Research impact | ✅ Validate safety | ✅ Implement |
| Infrastructure change | ⚠️ Document | ❌ Skip | ✅ Implement |
| Monitoring/logging | ❌ Skip | ❌ Skip | ✅ Implement |

---

## Final Reminders for Claude Code

1. **RBI is mandatory for all trading features** - No exceptions
2. **Never skip backtesting** - This is how you lose money
3. **Document everything** - Link research → backtest → implementation
4. **Validate before deploying** - Paper trading first, then small capital
5. **When in doubt, ask** - Better to clarify than to assume

**RBI saves capital. Follow it religiously.**

---

**Version**: 1.0.0
**Last Updated**: 2026-01-07
**Framework**: RBI (Research → Backtest → Implement)
**For**: Claude Code and all Claude AI agents
