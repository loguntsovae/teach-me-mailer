# Mail Gateway - Observability & Operations

## Overview

This mail gateway service includes comprehensive observability and operational tooling for production deployment.

## 🔍 Observability Features

### Prometheus Metrics (`/metrics`)
- **HTTP request metrics**: Request count, duration, status codes
- **Application metrics**: Custom business metrics via prometheus-fastapi-instrumentator
- **System metrics**: Memory usage, response times, error rates
- **Rate limiting metrics**: API key usage, quota consumption

**Endpoint**: `GET /metrics`
```bash
curl http://localhost:8000/metrics
```

### Structured Logging
- **JSON format**: All logs output as structured JSON to stdout
- **Request tracing**: Unique `request_id` for every HTTP request
- **Contextual logging**: Includes API key ID, operation type, timing
- **Log levels**: Configurable via `LOG_LEVEL` environment variable

**Request ID Middleware**: Adds `X-Request-ID` header to all responses for correlation.

**Example log entry**:
```json
{
  "event": "Send mail request",
  "level": "info", 
  "timestamp": "2024-11-07T10:30:45.123Z",
  "request_id": "abc-123-def",
  "api_key_id": "uuid-here",
  "recipient": "user@example.com"
}
```

## 🐳 Docker & Deployment

### Slim Docker Image
- **Base**: `python:3.12-slim` for minimal attack surface
- **Non-root user**: Runs as `appuser` (UID 1000) for security
- **Health checks**: Built-in health endpoint monitoring
- **Layer caching**: Optimized for fast rebuilds

### Docker Compose Stack
- **App service**: Mail gateway application
- **PostgreSQL**: Database with persistence
- **Health checks**: Both services monitored
- **Networking**: Isolated internal network

## 📋 Development Workflow

### Makefile Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start local development server |
| `make migrate` | Run database migrations |
| `make up` | Start all services with docker-compose |
| `make down` | Stop all services |
| `make test` | Run pytest suite |
| `make clean` | Clean up containers and volumes |
| `make logs` | Show application logs |
| `make shell` | Open shell in app container |
| `make seed` | Create initial API key |

### Quick Start
```bash
# Start the stack
make up

# Run migrations
make migrate

# Create your first API key
make seed

# Run tests
make test

# View logs
make logs
```

## 🧪 Test Suite

Comprehensive pytest suite covering:

### Authentication Tests
- ✅ Valid API key authentication
- ✅ Invalid/missing API key rejection
- ✅ Inactive API key handling
- ✅ bcrypt hash verification

### Rate Limiting Tests  
- ✅ Within bounds operation
- ✅ **Boundary testing** (exactly at limit)
- ✅ Exceeding limit scenarios
- ✅ **Concurrent upsert safety** (10 parallel tasks)
- ✅ Zero-increment usage checking

### Send Endpoint Tests
- ✅ **Happy path** with mocked SMTP
- ✅ Rate limit exceeded (429 responses)
- ✅ Validation errors (422 responses)
- ✅ SMTP failure handling
- ✅ Domain allowlist validation

### Concurrency Tests
- ✅ **10 parallel atomic operations** 
- ✅ Race condition prevention
- ✅ Consistent database state under load

**Run tests**:
```bash
pytest -v tests/
```

## 🔑 API Key Management

### Seed Script (`scripts/seed.py`)
Creates initial API keys with secure generation:

- **Secure random generation**: Uses `secrets` module
- **bcrypt hashing**: Industry-standard password hashing
- **One-time display**: Plaintext shown only during creation
- **Interactive prompts**: Name and daily limit configuration

**Usage**:
```bash
python scripts/seed.py
```

**Output**:
```
🔑 Mail Gateway - API Key Creation
==================================================
Creating API key...
✅ API key created successfully!

📋 API Key Details:
==============================
ID:          abc-123-def-456
Name:        Production API  
Daily Limit: 1000
Status:      Active

🚨 IMPORTANT: Save this API key - it will NOT be shown again!
============================================================
API Key: sk_abc123def456ghi789...
============================================================
```

## 📊 Monitoring Setup

### Prometheus Configuration
Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'mail-gateway'
    static_configs:
      - targets: ['mail-gateway:8000']
    metrics_path: /metrics
    scrape_interval: 15s
```

### Grafana Dashboard
Key metrics to monitor:

- **Request Rate**: `rate(http_requests_total[5m])`
- **Error Rate**: `rate(http_requests_total{status=~"5.."}[5m])`
- **Response Time**: `http_request_duration_seconds`
- **Rate Limit Usage**: Custom metrics for quota consumption

### Alerting Rules
```yaml
groups:
  - name: mail-gateway
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        
      - alert: HighResponseTime  
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 2
        for: 5m
```

## 🔒 Security Features

- **Non-root container**: Runs as unprivileged user
- **bcrypt hashing**: API keys never stored in plaintext
- **Input validation**: Comprehensive pydantic validation
- **Rate limiting**: Atomic PostgreSQL-based quotas
- **Domain allowlist**: Optional recipient domain restrictions
- **Request ID tracking**: Full request correlation

## 🚀 Production Deployment

### Environment Variables
```bash
# Database (required)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# SMTP (required)  
SMTP_HOST=smtp.provider.com
SMTP_PORT=587
SMTP_USER=your-email@domain.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=sender@domain.com

# Security (required)
SECRET_KEY=your-64-char-secret-key

# Optional settings
DEBUG=false
LOG_LEVEL=INFO
DEFAULT_DAILY_LIMIT=1000
ALLOW_DOMAINS=trusted1.com,trusted2.com
```

### Health Checks
- **Application**: `GET /api/v1/health`
- **Metrics**: `GET /metrics` 
- **Database**: Connection verification in health endpoint

### Scaling Considerations
- **Stateless**: Scales horizontally with load balancer
- **Database**: PostgreSQL handles concurrent atomic operations
- **Background tasks**: Uses FastAPI BackgroundTasks for email sending
- **Metrics**: Per-instance metrics aggregated by Prometheus

This setup provides production-ready observability with metrics, logging, testing, and operational tooling for reliable service deployment.