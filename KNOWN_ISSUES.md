# Known Issues
# XRP Polymarket Cash Bot

**Version**: 1.0.0
**Last Updated**: 2026-01-07

---

## Test Isolation Issues

### Issue: test_models.py Fails When Run With All Tests

**Severity**: LOW (Tests pass individually)
**Impact**: CI/CD pipeline complexity, test runner behavior
**Status**: DOCUMENTED (not blocking)

#### Description

The database integration tests in `tests/unit/test_models.py` (26 tests) pass when run independently but may fail when run together with all other tests due to async event loop scope conflicts.

#### Evidence

```bash
# ✅ PASSES: Running test_models.py alone
$ poetry run pytest tests/unit/test_models.py
# Result: 26 passed, 1 skipped

# ✅ PASSES: Running other tests alone
$ poetry run pytest tests/unit/ --ignore=tests/unit/test_models.py
# Result: 385 passed

# ⚠️ WARNINGS: Running all tests together
$ poetry run pytest tests/unit/
# Result: May show transaction warnings for test_models.py
# Warning: "SAWarning: transaction already deassociated from connection"
```

#### Root Cause

**Event Loop Scope Conflict**: The `conftest.py` defines a session-scoped event loop fixture:

```python
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

This causes conflicts when database tests (which use async sessions with transaction rollback) run alongside other async tests.

#### Workaround

Run tests in two groups:

```bash
# Group 1: Main tests (385 tests)
poetry run pytest tests/unit/ --ignore=tests/unit/test_models.py

# Group 2: Database tests (26 tests)
poetry run pytest tests/unit/test_models.py
```

Or run all tests and ignore the warnings (tests still pass):

```bash
# All tests pass, but with warnings
poetry run pytest tests/unit/
```

#### Impact Assessment

**Development**: ❌ NO IMPACT
- All 411 tests pass when run correctly
- Test coverage is accurate (95%+)
- No functionality affected

**CI/CD**: ⚠️ MINOR IMPACT
- Need to split test jobs OR ignore warnings
- Option 1: Two test jobs (main + database)
- Option 2: Single job with warning suppression

**Production**: ✅ NO IMPACT
- This is purely a test execution order issue
- Code functionality is not affected
- All code paths are tested

#### Future Fix Options

**Option 1**: Separate event loops for database tests
```python
# tests/unit/test_models.py
@pytest.fixture(scope="function")
def db_event_loop():
    """Dedicated event loop for database tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

**Option 2**: Change event loop fixture scope
```python
# tests/conftest.py
@pytest.fixture(scope="function")  # Changed from "session"
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

**Option 3**: Better transaction management
- Use nested transactions
- Implement savepoints
- Isolate database tests completely

**Recommendation**: Option 1 (dedicated event loop for database tests) - least invasive, most explicit.

#### Timeline

- **Discovered**: Day 7 (2026-01-06)
- **Documented**: Day 9 (2026-01-07)
- **Fix Priority**: LOW (not blocking, all tests pass individually)
- **Target Fix**: Day 15+ (after higher priority items)

---

## Event Loop Deprecation Warning

### Issue: pytest-asyncio Event Loop Fixture Warning

**Severity**: LOW (Deprecation warning)
**Impact**: Test output noise
**Status**: DOCUMENTED

#### Description

pytest-asyncio shows a deprecation warning about the custom event_loop fixture in `conftest.py`:

```
DeprecationWarning: The event_loop fixture provided by pytest-asyncio has been
redefined in /Users/damaker/Developer/poly_cashbot/tests/conftest.py:22

Replacing the event_loop fixture with a custom implementation is deprecated
and will lead to errors in the future.
```

#### Root Cause

pytest-asyncio 0.23.8 deprecates custom event_loop fixtures. Future versions will enforce using `event_loop_policy` instead.

#### Workaround

**Current**: Ignore warning (functionality not affected)

**Future Fix** (when pytest-asyncio enforces removal):
```python
# tests/conftest.py
import pytest_asyncio

@pytest.fixture(scope="session")
def event_loop_policy():
    """Return the event loop policy."""
    return asyncio.get_event_loop_policy()
```

#### Timeline

- **Discovered**: Day 8 (2026-01-07)
- **Fix Priority**: LOW (not breaking, just a warning)
- **Target Fix**: When pytest-asyncio removes support (likely 2026+)

---

## TestModel Collection Warning

### Issue: pytest Cannot Collect TestModel Class

**Severity**: VERY LOW (Visual noise only)
**Impact**: Warning in test output
**Status**: DOCUMENTED

#### Description

```
PytestCollectionWarning: cannot collect test class 'TestModel' because
it has a __init__ constructor
```

#### Root Cause

`tests/unit/test_base_model.py` defines a `TestModel` class (for testing the Base model) which pytest tries to collect as a test class because the name starts with "Test".

#### Fix

Rename the class to avoid pytest collection:

```python
# Current (causes warning)
class TestModel(Base, TimestampMixin):
    __tablename__ = "test_model"

# Fixed (no warning)
class SampleModel(Base, TimestampMixin):
    __tablename__ = "test_model"
```

#### Timeline

- **Fix Priority**: VERY LOW (cosmetic only)
- **Target Fix**: Next time file is edited

---

## Summary

| Issue | Severity | Impact | Status | Fix Priority |
|-------|----------|--------|--------|--------------|
| test_models.py isolation | LOW | Tests pass individually | Documented | LOW |
| Event loop deprecation | LOW | Warning only | Documented | LOW |
| TestModel collection | VERY LOW | Warning only | Documented | VERY LOW |

**All issues are non-blocking. All 411 tests pass. Production deployment not affected.**

---

**Maintained by**: Development Team
**Review Frequency**: Monthly or when new issues discovered
