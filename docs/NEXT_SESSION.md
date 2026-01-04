# Next Session Plan - Day 5
**Date**: 2026-01-05
**Phase**: Phase 1 (Foundation) - Week 1, Day 5
**Status**: 50% complete (Day 4 of 10 completed)

---

## ✅ Completed Today (Day 1-4)

### Project Configuration
- ✅ Poetry configuration with 90+ dependencies
- ✅ Pydantic Settings system
- ✅ Environment variables template
- ✅ Docker Compose (PostgreSQL + Redis)
- ✅ Git configuration (.gitignore)

### Database Models (SQLAlchemy 2.0)
- ✅ Base model with TimestampMixin
- ✅ Market model (Polymarket markets)
- ✅ Order model (order submissions)
- ✅ Trade model (executed trades)
- ✅ Position model (open positions)
- ✅ SentimentScore model (time-series)
- ✅ WhaleAlert model (whale detection)

### Verification
- ✅ Code compilation verified
- ✅ All models import successfully
- ✅ Type safety (mypy ready)

---

## 🎯 Tomorrow's Tasks (Day 5)

### 1. Start Docker Services (15 min)
```bash
# Start Docker Desktop manually
open -a Docker

# Then start services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Database Session Manager (1 hour)
**File**: `src/database.py`

Create async session manager:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_async_engine(
    settings.database_url,
    echo=True,
    pool_size=5,
    max_overflow=10
)

async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        yield session
```

**Tasks**:
- [ ] Create `src/database.py`
- [ ] Add connection pooling
- [ ] Add session lifecycle management
- [ ] Test connection to PostgreSQL

---

### 3. Alembic Migrations (2 hours)
**Initialize Alembic**:
```bash
export PATH="$HOME/.local/bin:$PATH"
poetry run alembic init migrations
```

**Configure Alembic**:
- [ ] Edit `alembic.ini` to use DATABASE_URL from env
- [ ] Update `migrations/env.py` to import our models
- [ ] Update `migrations/env.py` to use async engine

**Create Initial Migration**:
```bash
poetry run alembic revision --autogenerate -m "Initial schema: markets, orders, trades, positions, sentiment, whale_alerts"
```

**Apply Migration**:
```bash
poetry run alembic upgrade head
```

**Verify**:
```bash
# Connect to PostgreSQL and verify tables
docker-compose exec postgres psql -U cashbot_user -d poly_cashbot -c "\dt"
```

**Expected tables**:
- markets
- orders
- trades
- positions
- sentiment_scores
- whale_alerts
- alembic_version

---

### 4. Test Infrastructure (1.5 hours)
**File**: `tests/conftest.py`

Create pytest fixtures:
```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session():
    """Create test database session."""
    # Use test database
    engine = create_async_engine(
        "postgresql+asyncpg://cashbot_user:dev_password@localhost/poly_cashbot_test"
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()
```

**Tasks**:
- [ ] Create `tests/conftest.py`
- [ ] Add database fixtures
- [ ] Add event loop fixture
- [ ] Create test database

---

### 5. Basic Model Tests (1.5 hours)
**File**: `tests/unit/test_models.py`

Test all models:
```python
import pytest
from decimal import Decimal
from datetime import datetime
from src.models import Market, Order, Trade, Position

@pytest.mark.asyncio
async def test_market_creation(db_session):
    """Test Market model creation."""
    market = Market(
        id="test_market_1",
        question="Will XRP reach $2 by end of day?",
        end_date=datetime(2026, 1, 5, 23, 59, 59),
        yes_price=Decimal("0.55"),
        no_price=Decimal("0.45"),
        liquidity=Decimal("15000"),
        related_asset="XRP"
    )

    db_session.add(market)
    await db_session.commit()

    assert market.id == "test_market_1"
    assert market.is_active()
    assert market.mid_price() == Decimal("0.50")
    assert market.has_minimum_liquidity()

# Similar tests for Order, Trade, Position, SentimentScore, WhaleAlert
```

**Tasks**:
- [ ] Create `tests/unit/test_models.py`
- [ ] Test Market model (CRUD, helpers)
- [ ] Test Order model (lifecycle, helpers)
- [ ] Test Trade model (P&L calculations)
- [ ] Test Position model (P&L updates)
- [ ] Test SentimentScore model (thresholds)
- [ ] Test WhaleAlert model (detection logic)
- [ ] Run tests: `poetry run pytest -v`

---

### 6. Verification & Documentation (30 min)
**Run full test suite**:
```bash
poetry run pytest --cov=src --cov-report=html
```

**Expected**:
- ✅ All tests passing
- ✅ >80% code coverage
- ✅ Database migrations successful
- ✅ All 6 tables created

**Update CHANGELOG.md**:
- Add Day 5 progress
- Document database session manager
- Document Alembic setup
- Document test infrastructure

---

## 📋 Success Criteria for Day 5

By end of Day 5, you should have:

### Infrastructure ✓
- [x] Docker services running (PostgreSQL + Redis)
- [x] Database session manager (async)
- [x] Alembic configured and working
- [x] Initial migration applied
- [x] All 6 tables created in database

### Testing ✓
- [x] Test infrastructure (conftest.py)
- [x] Model unit tests (>80% coverage)
- [x] All tests passing
- [x] pytest configuration working

### Verification ✓
- [x] Can create database records
- [x] Can query database
- [x] Migrations work (up/down)
- [x] Tests run automatically

---

## 🚀 Quick Start Commands for Tomorrow

```bash
# 1. Start Docker
open -a Docker
docker-compose up -d

# 2. Activate Poetry environment
export PATH="$HOME/.local/bin:$PATH"

# 3. Initialize Alembic
poetry run alembic init migrations

# 4. Create migration
poetry run alembic revision --autogenerate -m "Initial schema"

# 5. Apply migration
poetry run alembic upgrade head

# 6. Run tests
poetry run pytest -v

# 7. Check coverage
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

## 📚 Reference Documentation

- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Alembic Tutorial**: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- **Pytest Async**: https://pytest-asyncio.readthedocs.io/
- **Our Tech Spec**: `docs/technical-specification.md` (lines 848-996 for database schema)

---

## ⚠️ Potential Issues & Solutions

### Issue: Docker not starting
**Solution**: Start Docker Desktop manually before running docker-compose

### Issue: PostgreSQL connection refused
**Solution**: Check Docker services with `docker-compose ps`

### Issue: Alembic can't find models
**Solution**: Update `migrations/env.py` to import all models from `src.models`

### Issue: Async tests not working
**Solution**: Ensure `pytest-asyncio` is installed and `asyncio_mode = "auto"` in `pyproject.toml`

### Issue: Migration conflicts
**Solution**: Drop test database and recreate: `docker-compose down -v && docker-compose up -d`

---

## 📊 Progress Tracking

**Overall Phase 1**: 50% (5 of 10 days)
**Week 1**: 80% (4 of 5 days)

**Completed**: 7 major tasks
**Remaining Today**: 5 tasks
**Remaining Week 1**: 2 tasks (Day 5 completion)
**Remaining Week 2**: 20+ tasks

---

## 🎯 Week 1 Completion Goal

By end of Week 1 (Day 5), we should have:
1. ✅ Complete project configuration
2. ✅ All database models
3. ✅ Database migrations working
4. ✅ Test infrastructure
5. ✅ Basic model tests passing

**Next**: Week 2 starts with Polymarket API integration (TASK-010)

---

**Prepared**: 2026-01-04 23:55
**For Session**: 2026-01-05
**Estimated Time**: 6-7 hours total
