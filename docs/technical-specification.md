# Technical Specification
# XRP Polymarket Cash Bot

**Version**: 1.0.0
**Date**: 2026-01-04
**Status**: Active Development
**Related**: [PRD](/docs/prd.md) | [Constitution](/memory/constitution.md)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [System Architecture](#system-architecture)
4. [Data Models](#data-models)
5. [API Specifications](#api-specifications)
6. [Component Design](#component-design)
7. [Database Schema](#database-schema)
8. [Security Architecture](#security-architecture)
9. [Performance Requirements](#performance-requirements)
10. [Deployment Architecture](#deployment-architecture)

---

## System Overview

### Purpose

The XRP Polymarket Cash Bot is a real-time algorithmic trading system that executes automated trades on Polymarket's XRP prediction markets using sentiment analysis, whale detection, and market making strategies.

### System Boundaries

**In Scope**:
- Polymarket API integration (CLOB)
- XRP price and sentiment monitoring
- Whale position detection
- Automated trade execution
- Risk management
- Performance analytics

**Out of Scope**:
- Other prediction market platforms (Kalshi, Augur)
- Non-XRP cryptocurrency markets
- Web UI (terminal + Telegram only)
- Machine learning models (rule-based only for MVP)

### System Context Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Dependencies                         │
├──────────────────┬──────────────────┬──────────────────┬─────────┤
│  Polymarket API  │  Price Feeds     │  News APIs       │ Polygon │
│  (CLOB)          │  (CoinGecko)     │  (CryptoPanic)   │  RPC    │
└────────┬─────────┴────────┬─────────┴────────┬─────────┴────┬────┘
         │                  │                  │              │
         │                  │                  │              │
┌────────▼──────────────────▼──────────────────▼──────────────▼────┐
│                   XRP Polymarket Cash Bot                         │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│ │ Data Layer   │  │ Strategy     │  │ Execution    │            │
│ │              │  │ Layer        │  │ Layer        │            │
│ └──────────────┘  └──────────────┘  └──────────────┘            │
│                                                                   │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│ │ PostgreSQL   │  │ Redis Cache  │  │ Prometheus   │            │
│ │ Database     │  │              │  │ Metrics      │            │
│ └──────────────┘  └──────────────┘  └──────────────┘            │
└────────┬──────────────────────────────────────────────┬──────────┘
         │                                              │
         ▼                                              ▼
┌────────────────┐                            ┌───────────────────┐
│  Telegram Bot  │                            │  Monitoring       │
│  (Alerts)      │                            │  (Grafana)        │
└────────────────┘                            └───────────────────┘
```

---

## Technology Stack

### Core Language & Runtime

**Python 3.11+**
- **Rationale**: Modern syntax, type hints, excellent library ecosystem
- **Features Used**: Type hints, async/await, dataclasses, pattern matching
- **Alternative Considered**: Node.js (rejected: Python better for data analysis)

### Web Framework & API Client

**FastAPI** (if REST API needed)
- **Rationale**: Fast, async, automatic OpenAPI docs
- **Use Case**: Internal admin API (optional)

**HTTPX**
- **Rationale**: Modern async HTTP client
- **Use Case**: All external API calls

**WebSockets** (built-in)
- **Rationale**: Real-time data streaming from Polymarket
- **Library**: `websockets` or `aiohttp`

### Database

**PostgreSQL 15+**
- **Rationale**: ACID compliance, reliability, JSON support
- **Use Cases**:
  - Trade history
  - Market data snapshots
  - Performance analytics
  - Configuration storage
- **Alternative Considered**: MongoDB (rejected: need strong consistency)

**SQLAlchemy 2.0** (ORM)
- **Rationale**: Mature, supports async, type-safe with mypy plugin
- **Migration Tool**: Alembic

### Caching & Message Queue

**Redis 7+**
- **Use Cases**:
  - Real-time market data caching
  - Pub/Sub for event streaming
  - Rate limiting
  - Session storage
- **Libraries**: `redis-py`, `aioredis`

### Task Scheduling

**APScheduler**
- **Rationale**: Pure Python, supports async
- **Use Cases**:
  - Periodic data fetching
  - Daily P&L reports
  - Strategy re-evaluation

### Data Processing

**Pandas 2.1+**
- **Use Cases**: Time series analysis, backtesting
- **Why**: Industry standard for financial data

**NumPy 1.24+**
- **Use Cases**: Numerical calculations, array operations

**TA-Lib** (Technical Analysis Library)
- **Use Cases**: RSI, MACD, Bollinger Bands calculations
- **Installation**: Requires C dependencies

### Testing

**pytest**
- **Rationale**: Most popular, excellent plugin ecosystem
- **Plugins**:
  - `pytest-asyncio`: async test support
  - `pytest-cov`: coverage reporting
  - `pytest-mock`: mocking utilities
  - `pytest-timeout`: timeout enforcement

**Hypothesis**
- **Use Case**: Property-based testing
- **Example**: Fuzz test risk calculations

**responses** / **aioresponses**
- **Use Case**: Mock HTTP requests

### Code Quality

**Black**
- **Purpose**: Code formatting
- **Config**: 100 character line length

**Ruff**
- **Purpose**: Fast linting (replaces flake8, isort, etc.)
- **Strictness**: Medium to high

**mypy**
- **Purpose**: Static type checking
- **Strictness**: `--strict` mode

**pre-commit**
- **Purpose**: Git hooks for automatic checks
- **Hooks**: black, ruff, mypy, tests

### Monitoring & Observability

**Prometheus**
- **Purpose**: Metrics collection
- **Client**: `prometheus-client`
- **Metrics**: Trade counts, latency, error rates

**Grafana**
- **Purpose**: Metrics visualization
- **Dashboards**: Trading performance, system health

**Sentry** (optional)
- **Purpose**: Error tracking and alerting
- **Alternative**: Custom error logging

**Structlog**
- **Purpose**: Structured logging
- **Format**: JSON for machine parsing

### Deployment

**Docker**
- **Rationale**: Consistent environments
- **Images**: python:3.11-slim-bookworm

**Docker Compose**
- **Use Case**: Local development
- **Services**: app, postgres, redis, prometheus, grafana

**Kubernetes** (optional, for scaling)
- **Alternative**: Single VPS with systemd

### CI/CD

**GitHub Actions**
- **Workflows**:
  - Test on every PR
  - Deploy on merge to main
  - Scheduled security scans

### External API Clients

**Polymarket**
- **Library**: `py-clob-client` (official Polymarket library)
- **Docs**: https://github.com/Polymarket/py-clob-client

**Blockchain**
- **Library**: `web3.py` for Polygon RPC
- **Use Case**: Whale wallet monitoring

**Price Feeds**
- **Library**: `pycoingecko` for CoinGecko API
- **Alternative**: Direct REST calls to multiple exchanges

**News**
- **Library**: `newsapi-python` (NewsAPI)
- **Alternative**: `feedparser` for RSS feeds

### Development Tools

**Poetry**
- **Purpose**: Dependency management
- **Why**: Better than pip + requirements.txt

**Jupyter Lab** (optional)
- **Use Case**: Interactive analysis and strategy development

**ipdb**
- **Purpose**: Interactive debugging

---

## System Architecture

### High-Level Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        Bot Orchestrator                        │
│                         (main.py)                              │
└─────────┬─────────────────────────────────────────────────────┘
          │
          ├─────────────┬─────────────┬─────────────┬───────────┐
          │             │             │             │           │
┌─────────▼────────┐ ┌──▼──────────┐ ┌─▼────────┐ ┌▼─────────┐ │
│  Data Collector  │ │  Sentiment  │ │  Whale   │ │  Market  │ │
│                  │ │  Analyzer   │ │ Detector │ │  Maker   │ │
│ - Polymarket     │ │             │ │          │ │          │ │
│ - Price feeds    │ │ - Technical │ │ - Order  │ │ - Spread │ │
│ - News           │ │ - News      │ │   book   │ │   mgmt   │ │
│ - Social         │ │ - Social    │ │ - Wallet │ │ - Inv.   │ │
│                  │ │             │ │   track  │ │   balance│ │
└──────────────────┘ └─────────────┘ └──────────┘ └──────────┘ │
          │             │             │             │           │
          └─────────────┴─────────────┴─────────────┴───────────┘
                                  │
                        ┌─────────▼──────────┐
                        │  Strategy Engine   │
                        │                    │
                        │ - Signal generation│
                        │ - Position sizing  │
                        │ - Risk validation  │
                        └─────────┬──────────┘
                                  │
                        ┌─────────▼──────────┐
                        │  Execution Engine  │
                        │                    │
                        │ - Order routing    │
                        │ - Position mgmt    │
                        │ - Trade logging    │
                        └─────────┬──────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
┌─────────▼────────┐    ┌─────────▼────────┐    ┌────────▼────────┐
│  PostgreSQL      │    │  Redis           │    │  Polymarket API │
│                  │    │                  │    │                 │
│ - Trades         │    │ - Market cache   │    │ - Order submit  │
│ - Positions      │    │ - Rate limiting  │    │ - Market data   │
│ - Performance    │    │ - Pub/sub        │    │ - Positions     │
└──────────────────┘    └──────────────────┘    └─────────────────┘
```

### Layer Responsibilities

#### 1. Data Collection Layer

**Purpose**: Fetch and normalize data from external sources

**Components**:
- `PolymarketClient`: CLOB API integration
- `PriceFeedClient`: XRP price from exchanges
- `NewsClient`: Crypto news aggregation
- `SocialClient`: Twitter/Reddit sentiment (optional)
- `BlockchainClient`: Polygon RPC for whale tracking

**Interface**:
```python
class DataSource(Protocol):
    async def fetch(self) -> DataFrame:
        """Fetch latest data"""

    async def stream(self) -> AsyncIterator[Event]:
        """Stream real-time data"""
```

#### 2. Analysis Layer

**Purpose**: Process raw data into trading signals

**Components**:
- `SentimentAnalyzer`: Composite sentiment scoring
- `WhaleDetector`: Large order identification
- `TechnicalIndicators`: RSI, MACD, etc.
- `MarketMicrostructure`: Order book analysis

**Interface**:
```python
class Analyzer(Protocol):
    def analyze(self, data: DataFrame) -> Signal:
        """Generate trading signal from data"""
```

#### 3. Strategy Layer

**Purpose**: Make trading decisions based on signals

**Components**:
- `IntervalStrategy`: 15-minute interval trading
- `FrontRunStrategy`: Whale front-running
- `MarketMakingStrategy`: Liquidity provision

**Interface**:
```python
class Strategy(Protocol):
    def should_trade(self, signals: List[Signal]) -> Optional[Order]:
        """Decide if/how to trade"""

    def size_position(self, signal: Signal) -> Decimal:
        """Calculate position size"""
```

#### 4. Execution Layer

**Purpose**: Execute trades and manage positions

**Components**:
- `OrderExecutor`: Submit orders to Polymarket
- `PositionManager`: Track and manage open positions
- `RiskManager`: Enforce risk limits

**Interface**:
```python
class Executor(Protocol):
    async def execute(self, order: Order) -> Trade:
        """Submit order to exchange"""

    async def cancel(self, order_id: str) -> bool:
        """Cancel open order"""
```

#### 5. Storage Layer

**Purpose**: Persist data for analysis and auditing

**Components**:
- `TradeRepository`: Trade history
- `MarketRepository`: Market snapshots
- `PerformanceRepository`: P&L tracking

**Interface**:
```python
class Repository(Protocol):
    async def save(self, entity: Entity) -> None:
        """Persist entity"""

    async def get(self, id: str) -> Optional[Entity]:
        """Retrieve entity by ID"""

    async def query(self, filter: Filter) -> List[Entity]:
        """Query entities"""
```

---

## Data Models

### Core Domain Models

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Optional

class MarketSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"

class StrategyType(Enum):
    INTERVAL_15M = "interval_15m"
    WHALE_FRONTRUN = "whale_frontrun"
    MARKET_MAKING = "market_making"

@dataclass
class Market:
    """Polymarket market"""
    id: str
    question: str
    end_date: datetime
    yes_price: Decimal
    no_price: Decimal
    volume_24h: Decimal
    liquidity: Decimal
    related_asset: str  # e.g., "XRP"

@dataclass
class Signal:
    """Trading signal"""
    timestamp: datetime
    market_id: str
    direction: MarketSide
    confidence: float  # 0.0 to 1.0
    sentiment_score: float  # -100 to +100
    strategy: StrategyType
    metadata: dict

@dataclass
class Order:
    """Trade order"""
    id: str
    market_id: str
    side: MarketSide
    size: Decimal  # in dollars
    price: Decimal  # 0.0 to 1.0
    strategy: StrategyType
    created_at: datetime
    status: OrderStatus

@dataclass
class Position:
    """Open position"""
    id: str
    market_id: str
    side: MarketSide
    size: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    opened_at: datetime

@dataclass
class Trade:
    """Executed trade"""
    id: str
    order_id: str
    market_id: str
    side: MarketSide
    size: Decimal
    price: Decimal
    fee: Decimal
    executed_at: datetime
    strategy: StrategyType

@dataclass
class WhaleAlert:
    """Large order detection"""
    timestamp: datetime
    market_id: str
    wallet_address: str
    order_size: Decimal
    side: MarketSide
    relative_size: float  # multiple of average order
    action_taken: Optional[str]

@dataclass
class PerformanceSnapshot:
    """Daily performance metrics"""
    date: datetime
    total_trades: int
    winning_trades: int
    total_pnl: Decimal
    win_rate: float
    sharpe_ratio: float
    max_drawdown: Decimal
```

---

## API Specifications

### External API Integration

#### Polymarket CLOB API

**Base URL**: `https://clob.polymarket.com`

**Authentication**: API Key in header

**Key Endpoints**:

```python
# Get markets
GET /markets?active=true&closed=false

# Get orderbook
GET /markets/{market_id}/book

# Place order
POST /orders
{
    "market_id": "...",
    "side": "buy",
    "price": "0.55",
    "size": "100"
}

# Get positions
GET /positions

# Cancel order
DELETE /orders/{order_id}
```

**WebSocket**: Real-time orderbook updates
```python
# Subscribe to market
ws://clob.polymarket.com/ws
{"type": "subscribe", "market_id": "..."}
```

**Rate Limits**: 100 requests/minute

**Error Handling**:
- 429: Rate limit → exponential backoff
- 401: Invalid API key → alert operator
- 503: Service down → switch to polling fallback

#### CoinGecko API

**Base URL**: `https://api.coingecko.com/api/v3`

**Endpoints**:
```python
# XRP price
GET /simple/price?ids=ripple&vs_currencies=usd

# XRP OHLCV
GET /coins/ripple/ohlc?vs_currency=usd&days=1
```

**Rate Limits**: 50 calls/minute (free tier)

#### CryptoPanic News API

**Base URL**: `https://cryptopanic.com/api/v1`

**Endpoints**:
```python
# XRP news
GET /posts/?auth_token={token}&currencies=XRP&public=true
```

**Rate Limits**: 100 calls/hour

### Internal API (Optional)

If building admin interface:

```python
# Health check
GET /health
Response: {"status": "ok", "uptime": 3600}

# Get performance
GET /api/v1/performance?period=7d
Response: {
    "win_rate": 0.58,
    "total_pnl": 1250.50,
    "sharpe_ratio": 1.65
}

# List positions
GET /api/v1/positions
Response: [
    {
        "market_id": "...",
        "size": 1000,
        "pnl": 45.20
    }
]

# Emergency stop
POST /api/v1/emergency-stop
Response: {"status": "stopped", "positions_closed": 3}
```

---

## Component Design

### 1. Polymarket Client

**Location**: `src/services/polymarket.py`

**Responsibilities**:
- Connect to CLOB API
- Fetch market data
- Submit/cancel orders
- Stream real-time updates

**Key Methods**:
```python
class PolymarketClient:
    async def get_xrp_markets(self) -> List[Market]:
        """Fetch active XRP markets"""

    async def get_orderbook(self, market_id: str) -> OrderBook:
        """Get current orderbook"""

    async def submit_order(self, order: Order) -> str:
        """Submit order, return order ID"""

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""

    async def stream_orderbook(
        self, market_id: str
    ) -> AsyncIterator[OrderBook]:
        """Stream real-time orderbook updates"""
```

**Error Handling**:
- Retry on network errors (3 attempts)
- Circuit breaker after 5 consecutive failures
- Alert on authentication errors

### 2. Sentiment Analyzer

**Location**: `src/lib/sentiment/analyzer.py`

**Responsibilities**:
- Aggregate price, news, social data
- Calculate composite sentiment score
- Detect sentiment shifts

**Key Methods**:
```python
class SentimentAnalyzer:
    def analyze(
        self,
        price_data: DataFrame,
        news_items: List[NewsItem],
        social_sentiment: Optional[float] = None
    ) -> SentimentScore:
        """
        Returns: Sentiment score -100 (bearish) to +100 (bullish)
        """

    def detect_shift(
        self,
        current: SentimentScore,
        historical: List[SentimentScore]
    ) -> Optional[SentimentShift]:
        """Detect significant sentiment changes"""
```

**Calculation**:
```python
# Weighted composite sentiment
sentiment = (
    0.5 * price_momentum_score +
    0.3 * news_sentiment_score +
    0.2 * social_sentiment_score
)
```

### 3. Whale Detector

**Location**: `src/lib/whale/detector.py`

**Responsibilities**:
- Monitor orderbook for large orders
- Track whale wallet addresses
- Generate front-run signals

**Key Methods**:
```python
class WhaleDetector:
    def detect_large_orders(
        self,
        orderbook: OrderBook,
        threshold_multiplier: float = 10.0
    ) -> List[WhaleAlert]:
        """Detect orders >10x average size"""

    async def track_wallet(
        self,
        address: str
    ) -> AsyncIterator[WalletEvent]:
        """Monitor wallet for new positions"""

    def should_frontrun(
        self,
        alert: WhaleAlert
    ) -> Optional[FrontRunSignal]:
        """Decide if/how to front-run"""
```

**Detection Logic**:
```python
average_order_size = rolling_mean(order_sizes, window=100)
if order.size > average_order_size * 10:
    emit WhaleAlert
```

### 4. Market Maker

**Location**: `src/lib/strategy/market_making.py`

**Responsibilities**:
- Place simultaneous buy/sell orders
- Manage inventory
- Capture bid-ask spread

**Key Methods**:
```python
class MarketMaker:
    def calculate_quotes(
        self,
        market: Market,
        inventory: Inventory,
        volatility: float
    ) -> Tuple[Quote, Quote]:
        """Generate bid/ask quotes"""

    def rebalance(
        self,
        current_inventory: Inventory,
        target_ratio: float = 0.5
    ) -> List[Order]:
        """Generate rebalancing orders"""

    def should_exit(
        self,
        market: Market,
        position: Position
    ) -> bool:
        """Decide if market conditions require exit"""
```

**Spread Calculation**:
```python
base_spread = 0.01  # 1%
volatility_adj = volatility * 0.5
inventory_adj = abs(inventory_ratio - 0.5) * 0.02
total_spread = base_spread + volatility_adj + inventory_adj
```

### 5. Risk Manager

**Location**: `src/lib/risk/manager.py`

**Responsibilities**:
- Enforce position limits
- Calculate risk exposure
- Trigger circuit breakers

**Key Methods**:
```python
class RiskManager:
    def validate_order(self, order: Order) -> RiskCheck:
        """Check if order violates risk limits"""

    def calculate_exposure(
        self,
        positions: List[Position]
    ) -> RiskExposure:
        """Calculate total risk exposure"""

    def should_halt_trading(
        self,
        recent_trades: List[Trade]
    ) -> bool:
        """Check circuit breaker conditions"""
```

**Risk Checks**:
```python
# Per-trade limit
if order.size > total_capital * 0.01:
    return RiskCheck(passed=False, reason="Exceeds per-trade limit")

# Daily loss limit
if daily_pnl < -total_capital * 0.03:
    return RiskCheck(passed=False, reason="Daily loss limit reached")

# Correlation check
if correlation_between_positions > 0.9:
    return RiskCheck(passed=False, reason="Positions too correlated")
```

---

## Database Schema

### PostgreSQL Tables

```sql
-- Markets
CREATE TABLE markets (
    id VARCHAR(255) PRIMARY KEY,
    question TEXT NOT NULL,
    end_date TIMESTAMP NOT NULL,
    yes_price DECIMAL(10, 8),
    no_price DECIMAL(10, 8),
    volume_24h DECIMAL(18, 2),
    liquidity DECIMAL(18, 2),
    related_asset VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_markets_asset ON markets(related_asset);
CREATE INDEX idx_markets_end_date ON markets(end_date);

-- Orders
CREATE TABLE orders (
    id VARCHAR(255) PRIMARY KEY,
    market_id VARCHAR(255) REFERENCES markets(id),
    side VARCHAR(10) NOT NULL,
    size DECIMAL(18, 2) NOT NULL,
    price DECIMAL(10, 8) NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_orders_market ON orders(market_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at DESC);

-- Trades
CREATE TABLE trades (
    id VARCHAR(255) PRIMARY KEY,
    order_id VARCHAR(255) REFERENCES orders(id),
    market_id VARCHAR(255) REFERENCES markets(id),
    side VARCHAR(10) NOT NULL,
    size DECIMAL(18, 2) NOT NULL,
    price DECIMAL(10, 8) NOT NULL,
    fee DECIMAL(18, 2) NOT NULL,
    pnl DECIMAL(18, 2),
    strategy VARCHAR(50) NOT NULL,
    executed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trades_market ON trades(market_id);
CREATE INDEX idx_trades_executed ON trades(executed_at DESC);
CREATE INDEX idx_trades_strategy ON trades(strategy);

-- Positions
CREATE TABLE positions (
    id VARCHAR(255) PRIMARY KEY,
    market_id VARCHAR(255) REFERENCES markets(id),
    side VARCHAR(10) NOT NULL,
    size DECIMAL(18, 2) NOT NULL,
    entry_price DECIMAL(10, 8) NOT NULL,
    current_price DECIMAL(10, 8),
    unrealized_pnl DECIMAL(18, 2),
    opened_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,
    is_open BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_positions_open ON positions(is_open);
CREATE INDEX idx_positions_market ON positions(market_id);

-- Whale Alerts
CREATE TABLE whale_alerts (
    id SERIAL PRIMARY KEY,
    market_id VARCHAR(255) REFERENCES markets(id),
    wallet_address VARCHAR(255) NOT NULL,
    order_size DECIMAL(18, 2) NOT NULL,
    side VARCHAR(10) NOT NULL,
    relative_size DECIMAL(10, 2),
    action_taken VARCHAR(100),
    detected_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_whale_detected ON whale_alerts(detected_at DESC);
CREATE INDEX idx_whale_wallet ON whale_alerts(wallet_address);

-- Performance Snapshots
CREATE TABLE performance_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    total_trades INT NOT NULL,
    winning_trades INT NOT NULL,
    total_pnl DECIMAL(18, 2) NOT NULL,
    win_rate DECIMAL(5, 4),
    sharpe_ratio DECIMAL(8, 4),
    max_drawdown DECIMAL(18, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_perf_date ON performance_snapshots(snapshot_date DESC);

-- Sentiment Scores (time series)
CREATE TABLE sentiment_scores (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    asset VARCHAR(50) NOT NULL,
    score DECIMAL(6, 2) NOT NULL,  -- -100 to +100
    price_component DECIMAL(6, 2),
    news_component DECIMAL(6, 2),
    social_component DECIMAL(6, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sentiment_timestamp ON sentiment_scores(timestamp DESC);
CREATE INDEX idx_sentiment_asset ON sentiment_scores(asset);
```

### Redis Data Structures

```python
# Market cache (hash)
# Key: market:{market_id}
# Value: JSON serialized Market object
# TTL: 60 seconds

# Orderbook cache (sorted set)
# Key: orderbook:{market_id}:bids
# Members: price (score) -> size (value)

# Rate limiting (counter)
# Key: ratelimit:polymarket:{timestamp_minute}
# Value: request count
# TTL: 60 seconds

# Circuit breaker state (string)
# Key: circuit_breaker:{service_name}
# Value: "open" | "closed" | "half_open"
# TTL: 300 seconds (5 minutes)

# Real-time events (pub/sub)
# Channel: events:whale_alerts
# Channel: events:trade_executions
# Channel: events:risk_alerts
```

---

## Security Architecture

### Secrets Management

**Environment Variables** (`.env` file):
```bash
POLYMARKET_API_KEY=...
POLYMARKET_SECRET_KEY=...
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379
TELEGRAM_BOT_TOKEN=...
```

**Storage**:
- Local dev: `.env` file (gitignored)
- Production: AWS Secrets Manager or HashiCorp Vault
- Never hardcode secrets

**Access**:
```python
from pydantic import BaseSettings

class Config(BaseSettings):
    polymarket_api_key: str
    database_url: str

    class Config:
        env_file = ".env"
```

### API Key Security

- **Principle of Least Privilege**: Use read-only keys where possible
- **Key Rotation**: Rotate every 90 days
- **Scoping**: Limit keys to specific IP addresses if supported

### Network Security

- **TLS/SSL**: All external API calls over HTTPS
- **WebSocket**: Use WSS (WebSocket Secure)
- **Firewall**: Whitelist only necessary ports

### Data Encryption

- **At Rest**: Encrypt PostgreSQL data volume
- **In Transit**: TLS for all connections
- **Sensitive Logs**: Redact wallet addresses, API keys

### Access Control

**Database**:
- Application user: read/write on application tables
- Admin user: full access (separate credentials)
- No root access from application

**Production Server**:
- SSH key-based auth only (no passwords)
- Separate deploy keys (read-only GitHub)
- Principle of least privilege for all services

---

## Performance Requirements

### Latency Targets

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| API call (Polymarket) | <100ms | <200ms | <500ms |
| Database query | <10ms | <50ms | <100ms |
| Signal generation | <500ms | <1s | <2s |
| Order execution | <200ms | <500ms | <1s |
| Sentiment calculation | <100ms | <200ms | <500ms |

### Throughput

- **API requests**: 100 req/min sustained
- **Database writes**: 1000 inserts/min
- **Event processing**: 100 events/sec
- **WebSocket messages**: 1000 msgs/sec

### Resource Limits

**Memory**:
- Steady state: <500MB
- Peak usage: <1GB
- Redis cache: <100MB

**CPU**:
- Average: <20% of 1 core
- Peak: <80% of 1 core

**Disk**:
- Database growth: ~1GB/month
- Logs: ~100MB/day (rotated)

### Optimization Strategies

1. **Database**: Connection pooling, query optimization, indexes
2. **Caching**: Redis for frequently accessed data
3. **Async I/O**: Use `asyncio` for concurrent API calls
4. **Batch Processing**: Bulk database inserts
5. **Lazy Loading**: Load data only when needed

---

## Deployment Architecture

### Development Environment

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres/db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: devpassword

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes

volumes:
  postgres_data:
```

### Production Deployment

**Option 1: Single VPS** (recommended for MVP)

```
┌─────────────────────────────────────┐
│         VPS (DigitalOcean)          │
│                                     │
│  ┌──────────────────────────────┐   │
│  │   systemd service (bot)      │   │
│  │   - Auto-restart on crash    │   │
│  │   - Log to journald          │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │   PostgreSQL                 │   │
│  │   - Daily backups            │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │   Redis                      │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │   Nginx (reverse proxy)      │   │
│  │   - SSL termination          │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

**Systemd Service**:
```ini
# /etc/systemd/system/cashbot.service
[Unit]
Description=XRP Polymarket Cash Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=cashbot
WorkingDirectory=/opt/cashbot
ExecStart=/opt/cashbot/venv/bin/python -m src.bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Option 2: Kubernetes** (for scaling)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cashbot
spec:
  replicas: 1  # Increase for redundancy
  selector:
    matchLabels:
      app: cashbot
  template:
    metadata:
      labels:
        app: cashbot
    spec:
      containers:
      - name: cashbot
        image: cashbot:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: cashbot-secrets
              key: database-url
        resources:
          limits:
            memory: "1Gi"
            cpu: "1000m"
          requests:
            memory: "500Mi"
            cpu: "500m"
```

### Monitoring Stack

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Cash Bot   │─────→│ Prometheus  │─────→│  Grafana    │
│             │      │  (metrics)  │      │ (dashboard) │
└─────────────┘      └─────────────┘      └─────────────┘
       │
       │ logs
       ▼
┌─────────────┐
│   Loki /    │
│  Journald   │
└─────────────┘
```

### Backup Strategy

**Database Backups**:
```bash
# Daily PostgreSQL dump
pg_dump cashbot > backup_$(date +%Y%m%d).sql
# Retain: 7 daily, 4 weekly, 12 monthly
```

**Code Backups**:
- Git repository (primary)
- GitHub (remote)
- Local backup of `.env` and config

**Disaster Recovery**:
1. Provision new VPS
2. Install dependencies
3. Restore database from backup
4. Deploy latest code from Git
5. Restart service
6. Total time: <15 minutes

---

## Appendix A: Technology Decision Matrix

| Requirement | Options Considered | Chosen | Rationale |
|-------------|-------------------|--------|-----------|
| Language | Python, Node.js, Rust | Python 3.11+ | Best libraries for data analysis |
| Database | PostgreSQL, MongoDB | PostgreSQL | ACID compliance critical |
| Cache | Redis, Memcached | Redis | Pub/sub + caching in one |
| Testing | pytest, unittest | pytest | Better plugin ecosystem |
| Deployment | Docker, bare metal, K8s | Docker + systemd | Balance simplicity and reliability |

---

## Appendix B: API Rate Limits

| Service | Limit | Strategy |
|---------|-------|----------|
| Polymarket | 100 req/min | Redis rate limiter, queue requests |
| CoinGecko | 50 req/min | Cache aggressively (60s TTL) |
| NewsAPI | 100 req/hour | Batch fetch, long cache |
| Polygon RPC | 10000 req/day | Use only for whale detection |

---

## Appendix C: Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| E001 | API authentication failed | Alert operator, check API key |
| E002 | Database connection lost | Retry, fail if >3 attempts |
| E003 | Risk limit exceeded | Halt trading, alert operator |
| E004 | Order execution failed | Log, retry once, alert if fails |
| E005 | Circuit breaker open | Wait, log all rejected requests |

---

**Document Version**: 1.0.0
**Last Updated**: 2026-01-04
**Next Review**: After MVP completion
