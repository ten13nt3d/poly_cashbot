# Project Constitution
# XRP Polymarket Cash Bot

**Version**: 1.0.0
**Established**: 2026-01-04
**Status**: Active
**Scope**: All project development and operations

---

## Preamble

This Constitution establishes the foundational principles, architectural standards, and governance rules for the XRP Polymarket Cash Bot project. All code, decisions, and operations must align with these principles.

**Core Mission**: Build a profitable, reliable, and ethical autonomous trading system for XRP prediction markets on Polymarket.

---

## Article I: Architectural Principles

### 1.1 Library-First Architecture

**Principle**: Every feature must be implemented as a reusable library before CLI/bot integration.

**Rationale**:
- Enables unit testing in isolation
- Promotes code reuse across contexts
- Facilitates future integrations (web UI, APIs, etc.)
- Enforces separation of concerns

**Implementation**:
```
src/
├── lib/               # Core libraries (pure Python, no I/O)
│   ├── sentiment/     # Sentiment analysis logic
│   ├── whale/         # Whale detection algorithms
│   ├── strategy/      # Trading strategies
│   └── risk/          # Risk management
├── services/          # Service layer (I/O, API calls)
│   ├── polymarket.py  # Polymarket API client
│   ├── price_feed.py  # Price data fetching
│   └── news.py        # News aggregation
└── bot/               # Bot orchestration
    └── main.py        # Entry point
```

**Enforcement**: Code reviews must reject PRs that skip library implementation.

### 1.2 Test-Driven Development (TDD)

**Principle**: Tests are written BEFORE implementation code, not after.

**Requirements**:
- All library code: unit tests (>90% coverage)
- All service code: integration tests + contract tests
- All strategies: backtests with historical data
- All bot workflows: end-to-end tests

**Test Structure**:
```
tests/
├── unit/              # Fast, isolated tests
├── integration/       # Service + external API tests
├── contract/          # API contract tests
├── e2e/               # Full bot workflow tests
└── backtest/          # Strategy backtesting
```

**Enforcement**: CI pipeline fails if coverage <80%.

### 1.3 API-First Design

**Principle**: All integrations use documented, versioned APIs.

**Requirements**:
- Never scrape web pages (use APIs only)
- Document all API contracts in `/docs/api-contracts/`
- Implement circuit breakers for all external APIs
- Version all internal APIs (semantic versioning)
- Mock all external APIs in tests

**API Contract Example**:
```python
# tests/contract/test_polymarket_api.py
def test_polymarket_orderbook_contract():
    """Ensure Polymarket API returns expected schema"""
    response = polymarket.get_orderbook(market_id="test")
    assert "bids" in response
    assert "asks" in response
    assert all("price" in bid for bid in response["bids"])
```

### 1.4 Fail-Safe by Default

**Principle**: System must degrade gracefully, never catastrophically.

**Requirements**:
- All external API calls: timeout + retry logic
- All trading operations: pre-execution validation
- All position changes: risk limit checks BEFORE execution
- All errors: logged + alerted, never silently swallowed
- Circuit breaker: halt trading after 3 consecutive failures

**Example**:
```python
@with_circuit_breaker(max_failures=3)
@with_retry(max_attempts=3, backoff=exponential)
@with_timeout(seconds=10)
def execute_trade(order):
    validate_risk_limits(order)  # Fails fast if risk exceeded
    return polymarket.submit_order(order)
```

### 1.5 Observability-First

**Principle**: Every critical operation must be logged, metered, and traceable.

**Requirements**:
- **Logging**: Structured JSON logs with correlation IDs
- **Metrics**: Prometheus-style metrics for all key operations
- **Tracing**: Distributed tracing for all external calls
- **Alerting**: Telegram alerts for critical events

**Log Levels**:
- DEBUG: Detailed execution flow (dev only)
- INFO: Normal operations (trades, signals)
- WARNING: Recoverable errors (retries, fallbacks)
- ERROR: Actionable failures (requires investigation)
- CRITICAL: Immediate intervention required (trading halted)

**Example**:
```python
logger.info("trade_executed", extra={
    "correlation_id": request_id,
    "market_id": market.id,
    "side": "buy",
    "size": 1000,
    "price": 0.55,
    "strategy": "whale_frontrun",
    "latency_ms": 234
})
```

---

## Article II: Code Quality Standards

### 2.1 Python Best Practices

**Requirements**:
- Python 3.11+ (use latest stable features)
- Type hints on all functions (enforce with mypy)
- Docstrings on all public functions (Google style)
- Black for formatting (line length: 100)
- Ruff for linting (strict mode)
- isort for import sorting

**Example**:
```python
def calculate_sentiment_score(
    price_data: pd.DataFrame,
    news_items: List[NewsItem],
    time_window: timedelta = timedelta(minutes=15)
) -> SentimentScore:
    """
    Calculate composite sentiment score for XRP.

    Args:
        price_data: OHLCV data for XRP
        news_items: Recent news articles
        time_window: Lookback period for analysis

    Returns:
        Sentiment score between -100 (very bearish) and +100 (very bullish)

    Raises:
        InsufficientDataError: If price_data has <10 rows
    """
    ...
```

### 2.2 Error Handling

**Principle**: Errors are expected, handle them explicitly.

**Requirements**:
- Use custom exceptions (never bare `except:`)
- Validate inputs at function boundaries
- Return Result types for operations that can fail
- Never catch exceptions just to log and re-raise

**Exception Hierarchy**:
```python
# src/lib/exceptions.py
class BotError(Exception):
    """Base exception for all bot errors"""

class DataError(BotError):
    """Data fetching or parsing errors"""

class TradingError(BotError):
    """Trading execution errors"""

class RiskLimitExceeded(TradingError):
    """Risk limits would be exceeded"""
```

### 2.3 Configuration Management

**Principle**: All configuration via environment variables or config files, never hardcoded.

**Requirements**:
- Use `.env` files for secrets (never commit to Git)
- Use YAML/TOML for strategy parameters
- Validate all config on startup
- Provide sane defaults
- Document all config options

**Example**:
```python
# src/config.py
from pydantic import BaseSettings, Field

class BotConfig(BaseSettings):
    """Bot configuration from environment variables"""

    polymarket_api_key: str = Field(..., env="POLYMARKET_API_KEY")
    postgres_url: str = Field(..., env="DATABASE_URL")
    max_position_size: Decimal = Field(Decimal("5000"), env="MAX_POSITION_SIZE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### 2.4 Performance Standards

**Requirements**:
- All database queries: <50ms (99th percentile)
- All API calls: timeout after 10 seconds
- Trading signal generation: <1 second
- Order execution: <500ms from signal
- Memory usage: <500MB steady state

**Enforcement**:
- Performance tests in CI
- Profiling on every release
- Database query explain plans reviewed

---

## Article III: Security Principles

### 3.1 Secrets Management

**Requirements**:
- API keys: encrypted at rest, in memory only when needed
- Private keys: hardware wallet or secure enclave only
- Never log secrets (even in debug mode)
- Rotate secrets every 90 days
- Use different keys for dev/staging/prod

**Prohibited**:
- Secrets in code
- Secrets in Git history
- Secrets in error messages
- Secrets in database without encryption

### 3.2 Access Control

**Requirements**:
- Principle of least privilege
- Separate read/write database users
- API keys with minimal scopes
- IP whitelisting for admin endpoints
- Audit log for all privileged operations

### 3.3 Data Privacy

**Requirements**:
- No PII collection unless required
- Anonymize logs (no wallet addresses in plain text)
- Data retention: 1 year max, then delete
- Encrypt sensitive data at rest
- Comply with GDPR/CCPA if applicable

---

## Article IV: Testing Standards

### 4.1 Test Coverage Requirements

**Minimum Coverage**:
- Library code: 90%
- Service code: 80%
- Bot orchestration: 70%
- Overall project: 80%

**Enforcement**: CI fails if coverage drops below threshold.

### 4.2 Test Types

**Unit Tests**:
- Test single function in isolation
- No external dependencies (mock everything)
- Fast (<1ms per test)
- Deterministic (no randomness)

**Integration Tests**:
- Test service + real external API
- Use test accounts/sandbox environments
- Slower (up to 10s per test)
- May have API rate limits

**Contract Tests**:
- Verify external API schemas
- Run on every deployment
- Alert if API contract changes

**End-to-End Tests**:
- Test complete workflows
- Use staging environment
- Run nightly (not on every commit)

**Backtest Tests**:
- Strategy performance on historical data
- Must show positive returns over 90 days
- Test edge cases (flash crashes, low liquidity)

### 4.3 Test Data Management

**Requirements**:
- All test data in `tests/fixtures/`
- Use factories for test object creation
- Never use production data in tests
- Sanitize any real data before committing

---

## Article V: Development Workflow

### 5.1 Git Workflow

**Branch Strategy**: GitHub Flow (simplified)

**Branches**:
- `main`: Always deployable, production-ready
- `feature/*`: New features
- `fix/*`: Bug fixes
- `refactor/*`: Code improvements

**Commit Messages**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, test, refactor, perf, chore

**Example**:
```
feat(whale): add orderbook depth monitoring

Implement real-time orderbook depth tracking to detect
large order placements. Triggers alert when depth changes
>20% in single block.

Closes #42
```

### 5.2 Code Review Requirements

**All PRs Must**:
- Pass CI (tests, linting, type checks)
- Have >80% test coverage
- Include tests for new functionality
- Update docs if API changes
- Be reviewed by at least 1 person
- Have descriptive PR description

**Review Checklist**:
- [ ] Follows library-first architecture
- [ ] Has appropriate tests
- [ ] No secrets committed
- [ ] Documentation updated
- [ ] Performance acceptable
- [ ] Error handling comprehensive

### 5.3 Versioning

**Semantic Versioning** (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes (API incompatibility)
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

**Release Process**:
1. Update CHANGELOG.md
2. Bump version in `pyproject.toml`
3. Tag release in Git
4. Deploy to staging
5. Run E2E tests
6. Deploy to production

---

## Article VI: Deployment & Operations

### 6.1 Continuous Integration (CI)

**On Every Commit**:
- Run all unit + integration tests
- Check code formatting (black, isort)
- Run linters (ruff, mypy)
- Check test coverage
- Build Docker image

**On Every PR**:
- Full CI suite
- Contract tests against staging APIs
- Security scan (bandit, safety)

**On Every Merge to Main**:
- Deploy to staging
- Run E2E tests
- If successful, auto-deploy to production

### 6.2 Continuous Deployment (CD)

**Deployment Strategy**: Blue-Green

**Process**:
1. Deploy new version to "green" environment
2. Run smoke tests
3. Switch traffic to "green"
4. Monitor for 10 minutes
5. If errors, instant rollback to "blue"
6. If successful, "green" becomes new "blue"

**Rollback Criteria**:
- Error rate >1% of requests
- Latency >2x normal
- Any trading failures
- Manual operator decision

### 6.3 Monitoring & Alerting

**Health Checks**:
- Every 30 seconds: API connectivity
- Every 1 minute: Database health
- Every 5 minutes: Trading strategy status
- Every 15 minutes: Risk limit validation

**Alerts** (Telegram):
- CRITICAL: System down, trading halted
- WARNING: Approaching risk limits, API errors
- INFO: Daily performance summary

### 6.4 Disaster Recovery

**Backup Strategy**:
- Database: Hourly snapshots, 7-day retention
- Logs: Real-time streaming to external storage
- Configuration: Versioned in Git
- Secrets: Encrypted backups in separate location

**Recovery Time Objectives**:
- RTO (Recovery Time): <15 minutes
- RPO (Recovery Point): <1 hour data loss max

**Runbook**: `/docs/runbooks/disaster-recovery.md`

---

## Article VII: Risk Management

### 7.1 Trading Risk Limits

**Hard Limits** (cannot be exceeded):
- Per-trade risk: 1% of total capital
- Daily loss limit: 3% of total capital
- Maximum concurrent positions: 5
- Maximum position size: $5,000

**Soft Limits** (trigger warnings):
- Consecutive losses: 3
- Daily volatility: >10%
- Correlation: >0.9 between positions

### 7.2 Operational Risk Controls

**Access Control**:
- Production access: 2 people max
- Read-only monitoring: unlimited
- Emergency stop: 1-click button

**Change Management**:
- No direct production changes
- All changes via CI/CD
- Rollback tested before every deploy

### 7.3 Market Risk

**Position Limits**:
- Never >10% of market liquidity
- Never >20% of total capital in single market
- Diversification: at least 3 uncorrelated markets

**Stop-Loss**:
- Automatic stop-loss on all positions
- Maximum loss per position: 2% of capital
- Trailing stops on winning positions

---

## Article VIII: Ethics & Compliance

### 8.1 Ethical Trading

**Principles**:
- No manipulation or spoofing
- No wash trading or self-dealing
- No exploitation of bugs or glitches
- Transparent operation (no hidden strategies)

**Prohibited**:
- Front-running user orders (only whale detection)
- Market manipulation
- Insider trading (using non-public info)
- Exploiting protocol vulnerabilities

### 8.2 Legal Compliance

**Requirements**:
- Comply with all applicable laws
- Respect API terms of service
- Pay applicable taxes
- Maintain audit trail

**Disclaimer**:
This software is for educational/research purposes. Users are responsible for compliance with their local regulations.

### 8.3 Responsible AI

**If ML/AI Added**:
- Explainable models (no black boxes)
- Bias testing and mitigation
- Human oversight on AI decisions
- Kill switch for AI strategies

---

## Article IX: Documentation Standards

### 9.1 Required Documentation

**Code-Level**:
- Docstrings on all public functions
- Inline comments for complex logic
- Type hints everywhere

**Project-Level**:
- README.md: Quick start
- SETUP.md: Installation guide
- AGENTS.md: AI agent coordination
- API documentation (auto-generated)

**Operational**:
- Runbooks: Common operations
- Incident playbooks: Error resolution
- Architecture decision records (ADRs)

### 9.2 Documentation Updates

**When to Update**:
- Before merging PR (if API changes)
- Weekly changelog updates
- Monthly architecture review

**Format**:
- Markdown for all docs
- Diagrams: Mermaid or PlantUML (text-based)
- API docs: OpenAPI 3.0 spec

---

## Article X: Performance Benchmarks

### 10.1 Trading Performance

**Minimum Acceptable**:
- Win rate: >52% (breakeven with fees)
- Sharpe ratio: >1.0
- Maximum drawdown: <25%
- Profit factor: >1.5

**Target Performance**:
- Win rate: >55%
- Sharpe ratio: >1.5
- Maximum drawdown: <20%
- Profit factor: >1.8

**If Below Minimum for 14 Days**:
Halt live trading, review strategy, backtest improvements.

### 10.2 System Performance

**Latency Budgets**:
- P50: <200ms
- P95: <500ms
- P99: <1000ms

**Availability**: 99.5% (downtime <3.6 hours/month)

**Error Budget**: 0.5% of requests can fail

---

## Article XI: Governance

### 11.1 Constitution Amendments

**Process**:
1. Propose amendment (GitHub Issue)
2. Discuss with team (minimum 3 days)
3. Vote (requires majority approval)
4. Update this document
5. Announce change

### 11.2 Exception Handling

**When to Break Rules**:
- Critical bug requires immediate fix
- Security vulnerability
- Regulatory requirement

**Process**:
1. Document exception reason
2. Get approval from lead developer
3. Create task to fix properly
4. Log in exceptions registry

### 11.3 Principle Conflicts

**Resolution**:
If two principles conflict, priority order:
1. Security
2. Risk management
3. Correctness
4. Performance
5. Developer experience

---

## Article XII: Enforcement

### 12.1 Automated Enforcement

**CI Pipeline Checks**:
- [ ] All tests pass
- [ ] Coverage >80%
- [ ] Type checks pass (mypy)
- [ ] Linting passes (ruff)
- [ ] Formatting correct (black)
- [ ] No secrets in code
- [ ] Security scan passes

### 12.2 Code Review Enforcement

**Reviewers Must**:
- Verify adherence to this Constitution
- Reject PRs that violate principles
- Provide constructive feedback

### 12.3 Consequences

**Violations**:
- First violation: Warning + correction
- Repeated violations: PR rejected
- Severe violations: Revert commit

---

## Appendix A: Key Technologies

**Programming**: Python 3.11+
**Database**: PostgreSQL 15+
**Cache**: Redis 7+
**Message Queue**: Redis Pub/Sub or RabbitMQ
**Monitoring**: Prometheus + Grafana
**Logging**: Structured JSON (ELK stack or similar)
**Testing**: pytest + hypothesis
**CI/CD**: GitHub Actions
**Infrastructure**: Docker + Kubernetes or single VPS

---

## Appendix B: Project Structure

```
poly_cashbot/
├── src/
│   ├── lib/                    # Pure logic libraries
│   │   ├── sentiment/
│   │   ├── whale/
│   │   ├── strategy/
│   │   └── risk/
│   ├── services/               # External integrations
│   │   ├── polymarket.py
│   │   ├── price_feed.py
│   │   └── news.py
│   ├── models/                 # Data models (SQLAlchemy)
│   ├── bot/                    # Bot orchestration
│   │   └── main.py
│   └── cli/                    # CLI interface
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── e2e/
│   └── backtest/
├── docs/
│   ├── prd.md
│   ├── technical-specification.md
│   ├── api-contracts/
│   ├── runbooks/
│   └── architecture/
├── memory/
│   └── constitution.md         # This file
├── specs/                      # Feature specifications
├── changelog/                  # Version history
├── scripts/                    # Utility scripts
├── .github/
│   └── workflows/              # CI/CD
├── .env.example                # Config template
├── pyproject.toml              # Project metadata
├── Dockerfile
└── README.md
```

---

## Appendix C: Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-04 | Python 3.11+ required | Type hints, performance, modern syntax |
| 2026-01-04 | PostgreSQL over SQLite | Production reliability, ACID guarantees |
| 2026-01-04 | TDD mandatory | Reduce bugs, enable refactoring |
| 2026-01-04 | Library-first architecture | Testability, reusability |

---

**Signed**: Development Team
**Date**: 2026-01-04
**Version**: 1.0.0

**This Constitution is binding on all project contributors and operations.**
