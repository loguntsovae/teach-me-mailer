# 🧪 Tests

Comprehensive test suite for teach-me-mailer.

## 📁 Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── pytest.ini               # Pytest configuration
│
├── unit/                    # Unit tests (isolated components)
│   ├── services/            # Service layer tests
│   ├── models/              # Database model tests
│   ├── schemas/             # Pydantic schema tests
│   └── core/                # Core functionality tests
│
├── integration/             # Integration tests (component interaction)
│   ├── api/                 # API endpoint tests
│   ├── test_database.py     # Database integration tests
│   ├── test_rate_limiting.py
│   ├── test_email_flow.py
│   └── test_auth_flow.py
│
└── e2e/                     # End-to-end tests (full flows)
    ├── test_complete_flow.py
    ├── test_monitoring.py
    └── test_error_handling.py
```

## 🚀 Quick Start

### 1. Install Test Dependencies

```bash
# Install all test dependencies
pip install -e ".[test]"
```

### 2. Setup Test Database

Make sure PostgreSQL is running on localhost:

```bash
# Create test database and run migrations
python scripts/setup_test_db.py
```

This will:
- Create `test_teach_me_mailer` database
- Run all Alembic migrations
- Verify database connection

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run tests by marker
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m e2e           # Only e2e tests

# Run tests in parallel (faster)
pytest -n auto

# Run specific test file
pytest tests/unit/services/test_auth.py

# Run specific test function
pytest tests/unit/services/test_auth.py::test_hash_api_key
```

## 🧪 Test Fixtures

Main fixtures available in `conftest.py`:

### Database Fixtures
- `db_session` - Fresh database session with transaction rollback
- `test_engine` - Async SQLAlchemy engine for tests

### API Key Fixtures
- `test_api_key` - Active test API key
- `test_api_key_inactive` - Inactive test API key
- `test_api_key_with_recipient_limit` - API key with recipient restrictions

### HTTP Client Fixtures
- `test_client` - Async HTTP client for API testing
- `app` - FastAPI application with test settings

### Mock Fixtures
- `mock_smtp` - Mocked SMTP client
- `mock_mailer_service` - Mocked mailer service
- `mock_rate_limit_service` - Mocked rate limit service
- `mock_sentry` - Mocked Sentry SDK

### Settings Fixture
- `test_settings` - Test configuration settings

## 📊 Coverage

Target coverage: **≥ 95%**

View coverage report:
```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open in browser (macOS)
open htmlcov/index.html

# View terminal coverage report
pytest --cov=app --cov-report=term-missing
```

## 🏷️ Test Markers

Tests are categorized using markers:

```python
@pytest.mark.unit           # Unit test
@pytest.mark.integration    # Integration test
@pytest.mark.e2e            # End-to-end test
@pytest.mark.slow           # Slow test
@pytest.mark.smtp           # Requires SMTP mocking
@pytest.mark.database       # Requires database access
```

Run tests by marker:
```bash
pytest -m unit              # Run only unit tests
pytest -m "not slow"        # Skip slow tests
pytest -m "unit and smtp"   # Unit tests with SMTP
```

## 🔧 Configuration

### Environment Variables

Tests use `.env.test` configuration:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_teach_me_mailer
TESTING=1
DEBUG=true
```

### Pytest Configuration

See `pytest.ini` for full configuration.

Key settings:
- `asyncio_mode = auto` - Automatic async test detection
- Coverage threshold: 85%
- Max failures: 5
- Parallel execution supported

## 📝 Writing Tests

### Unit Test Example

```python
import pytest
from app.services.auth import AuthService

@pytest.mark.unit
async def test_hash_api_key(db_session, test_settings):
    """Test API key hashing."""
    auth_service = AuthService(db_session, test_settings)

    raw_key = "sk_test_12345"
    hashed = auth_service._hash_api_key(raw_key)

    assert hashed != raw_key
    assert len(hashed) > 20
```

### Integration Test Example

```python
import pytest

@pytest.mark.integration
async def test_send_email_success(test_client, test_api_key):
    """Test successful email sending."""
    response = await test_client.post(
        "/api/v1/send",
        headers={"X-API-Key": test_api_key.raw_key},
        json={
            "to": "test@example.com",
            "subject": "Test",
            "html_body": "<p>Test</p>",
        }
    )

    assert response.status_code == 202
    assert "message_id" in response.json()
```

## 🐛 Debugging Tests

### Run with verbose output
```bash
pytest -vv
```

### Show print statements
```bash
pytest -s
```

### Run last failed tests
```bash
pytest --lf
```

### Stop on first failure
```bash
pytest -x
```

### Drop into debugger on failure
```bash
pytest --pdb
```

## 🔄 CI/CD

Tests run automatically on GitHub Actions for:
- Every push
- Every pull request

See `.github/workflows/test.yml` for CI configuration.

## 📈 Performance

### Parallel Execution

Run tests in parallel for faster execution:

```bash
# Auto-detect number of CPUs
pytest -n auto

# Use specific number of workers
pytest -n 4
```

### Speed Optimization

- Unit tests: < 1s each
- Integration tests: < 5s each
- E2E tests: < 10s each
- Full test suite: < 5 minutes

## 🆘 Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Recreate test database
dropdb test_teach_me_mailer
python scripts/setup_test_db.py
```

### Import Errors

```bash
# Reinstall dependencies
pip install -e ".[test]"
```

### Fixture Not Found

Make sure `conftest.py` is in the correct location and pytest can discover it.

### Async Test Errors

Ensure `pytest-asyncio` is installed and `asyncio_mode = auto` is set in `pytest.ini`.

## 📚 Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [httpx testing](https://www.python-httpx.org/async/)
- [SQLAlchemy async testing](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

## ✅ Checklist for New Tests

- [ ] Test function name starts with `test_`
- [ ] Appropriate marker added (`@pytest.mark.unit`, etc.)
- [ ] Docstring explains what is being tested
- [ ] Arrange-Act-Assert pattern followed
- [ ] Edge cases covered
- [ ] Async/await used correctly for async tests
- [ ] Mocks used for external dependencies
- [ ] Assertions are clear and specific

---

**Happy Testing! 🎉**
