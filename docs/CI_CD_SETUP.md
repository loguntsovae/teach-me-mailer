# GitHub Actions & Codecov Setup

## Setup Instructions

### 1. Codecov Integration

1. Go to [codecov.io](https://codecov.io) and sign in with GitHub
2. Add your repository: `loguntsovae/TeachMeMailer`
3. Get your Codecov token from the repository settings
4. Add the token to GitHub Secrets:
   - Go to: `https://github.com/loguntsovae/TeachMeMailer/settings/secrets/actions`
   - Click "New repository secret"
   - Name: `CODECOV_TOKEN`
   - Value: [paste your token]

### 2. Required GitHub Secrets

Add these secrets to your repository:

```
CODECOV_TOKEN - Codecov upload token (required for coverage reports)
```

### 3. Workflows Overview

#### CI/CD Workflow (`.github/workflows/ci.yml`)
- Runs on: push to `develop`, PR to `main`/`develop`
- Jobs:
  - **lint**: Code quality checks (black, isort, flake8, mypy)
  - **security**: Dependency vulnerability scanning
  - **test**: Run tests with coverage (Python 3.11 & 3.12)
  - **build**: Docker image build

#### PR Coverage Workflow (`.github/workflows/pr-coverage.yml`)
- Runs on: Pull requests
- Adds coverage comments to PRs
- Shows coverage changes

#### Nightly Tests (`.github/workflows/nightly.yml`)
- Runs: Daily at 2 AM UTC
- Full test suite with detailed reports
- Creates GitHub issue on failure

### 4. Coverage Configuration

Coverage settings are in `codecov.yml`:
- Project target: 85%
- Patch target: 80%
- Ignores: tests, migrations, scripts, docs

### 5. Local Testing

Test the workflows locally:

```bash
# Run all tests with coverage
pytest tests/ --cov=app --cov-report=term --cov-report=html

# Run specific test suites
pytest tests/unit -v
pytest tests/integration -v
pytest tests/test_smoke.py -v

# Check coverage report
open htmlcov/index.html
```

### 6. Verify Setup

After pushing:
1. Check Actions tab: `https://github.com/loguntsovae/TeachMeMailer/actions`
2. Verify workflows are running
3. Check Codecov dashboard: `https://codecov.io/gh/loguntsovae/TeachMeMailer`

### 7. Troubleshooting

Common issues:

**Tests fail in CI but pass locally:**
- Check environment variables
- Verify PostgreSQL service is healthy
- Check Python version compatibility

**Coverage not uploading:**
- Verify `CODECOV_TOKEN` is set
- Check codecov action logs
- Ensure `coverage.xml` is generated

**Build fails:**
- Check Docker configuration
- Verify all dependencies in `pyproject.toml`
- Check cache if build is slow

### 8. Badge URLs

Add these to README.md:

```markdown
[![CI/CD](https://github.com/loguntsovae/TeachMeMailer/actions/workflows/ci.yml/badge.svg)](https://github.com/loguntsovae/TeachMeMailer/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/loguntsovae/TeachMeMailer/branch/develop/graph/badge.svg)](https://codecov.io/gh/loguntsovae/TeachMeMailer)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```
