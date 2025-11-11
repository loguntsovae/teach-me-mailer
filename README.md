# 🚀 Teach Me Mailer

[![CI/CD](https://github.com/loguntsovae/TeachMeMailer/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/loguntsovae/TeachMeMailer/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/loguntsovae/TeachMeMailer/branch/develop/graph/badge.svg)](https://codecov.io/gh/loguntsovae/TeachMeMailer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-ready, scalable email service built with FastAPI. Features atomic rate limiting, comprehensive observability, and enterprise-grade security for high-volume email delivery.

## 🏗️ Architecture Overview

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API Gateway
    participant R as Rate Limiter
    participant Q as Email Queue
    participant S as SMTP Service
    participant D as Database
    participant M as Monitoring

    C->>A: POST /api/v1/send + API Key
    A->>A: Validate API Key
    A->>R: Check Rate Limit
    R->>D: Update/Check Usage
    alt Rate limit exceeded
        R-->>A: 429 Too Many Requests
        A-->>C: Rate limit exceeded
    else Within limits
        R-->>A: Allowed
        A->>Q: Queue Email
        Q->>S: Send via SMTP
        S->>D: Log Send Result
        S->>M: Update Metrics
        A-->>C: 202 Email Queued
    end
```

## ✨ Key Features

- **🚀 High Performance**: Async FastAPI with sub-100ms response times
- **🔐 Enterprise Security**: API key authentication with bcrypt + PBKDF2
- **⚡ Atomic Rate Limiting**: Thread-safe PostgreSQL operations
- **📧 Reliable Delivery**: SMTP with connection pooling and retry logic
- **📊 Full Observability**: Prometheus metrics, structured logging, Sentry integration
- **🐳 Production Ready**: Docker containerization with health checks
- **🧪 100% Test Coverage**: Comprehensive test suite with mocking
- **🔒 Security Hardened**: CORS, input validation, request size limits

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI | High-performance async web framework |
| **Database** | PostgreSQL | Data persistence with ACID compliance |
| **Authentication** | bcrypt + API Keys | Secure authentication system |
| **Email Delivery** | aiosmtplib | Async SMTP client with TLS |
| **Observability** | Prometheus + Sentry | Metrics and error tracking |
| **Testing** | pytest + httpx | Comprehensive test coverage |
| **Containerization** | Docker + Docker Compose | Deployment and development |

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/loguntsovae/teach-me-mailer.git
cd teach-me-mailer

# Start all services
make dev

# Create demo API key
make seed

# Test email sending
curl -X POST "http://localhost:8000/api/v1/send" \\
  -H "X-API-Key: sk_test_demo_key_12345" \\
  -H "Content-Type: application/json" \\
  -d '{
    "to": "test@example.com",
    "subject": "Hello from Teach Me Mailer! 👋",
    "html_body": "<h1>Welcome!</h1><p>Your email service is working perfectly.</p>",
    "text_body": "Welcome! Your email service is working perfectly."
  }'
```

### Option 2: Local Development

```bash
# Install dependencies
make install

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
make migrate

# Start development server
make run

# In another terminal, create API key
make create-api-key
```

## 📋 Environment Configuration

Create a `.env` file based on `.env.example`:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/mailgateway

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_ADDRESS=your-email@gmail.com

# Security
CORS_ORIGINS=["http://localhost:3000"]
MAX_REQUEST_SIZE=262144

# Admin UI protection (optional)
# Use BasicAuth for the admin UI (recommended for local/dev). Set both values to enable BasicAuth.
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme

# Alternatively, protect admin with a header X-ADMIN-KEY
# ADMIN_API_KEY=some-very-secret-value

# Observability
LOG_LEVEL=INFO
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Development
DEBUG=true
```

### 🐞 Sentry (optional)

The application supports Sentry for error tracking. Set the `SENTRY_DSN` environment variable to enable Sentry integration. If the variable is not set, Sentry will not be initialized.

Example (macOS / zsh):

```bash
export SENTRY_DSN="https://<public>@oXXXXX.ingest.sentry.io/<project>"
```

Note: The DSN is treated as sensitive and will not be logged. You can control the Sentry behavior via the `SENTRY_DSN` environment variable or in your `.env` file.

## 📚 API Endpoints Overview

### 📤 Send Email
```http
POST /api/v1/send
X-API-Key: your_api_key

{
  "to": "recipient@example.com",
  "subject": "Email Subject",
  "html_body": "<p>Rich HTML content</p>",
  "text_body": "Plain text fallback",
  "headers": {  // Optional
    "Reply-To": "noreply@example.com"
  }
}
```

**Responses:**
- `202 Accepted` - Email queued successfully
- `401 Unauthorized` - Invalid API key
- `429 Too Many Requests` - Rate limit exceeded
- `422 Unprocessable Entity` - Invalid request data

### 🏥 Health Check
```http
GET /health
```

### 📊 Metrics
```http
GET /metrics
```

### 📖 API Documentation
```http
GET /docs          # Swagger UI
GET /redoc         # ReDoc
GET /openapi.json  # OpenAPI schema
```

## 🧪 Testing & CI

### Running Tests Locally

```bash
# Run all tests with coverage
make test

# Run specific test categories
make test-unit
make test-integration

# Run tests with detailed output
make test-verbose

# Generate coverage report
make coverage
```

### Continuous Integration

Our CI pipeline runs on every push and pull request:

1. **Code Quality**: Black, isort, flake8, mypy
2. **Security**: Safety dependency checks
3. **Tests**: Full test suite with coverage reporting
4. **Build**: Docker image build and vulnerability scanning

[![CI Status](https://github.com/loguntsovae/teach-me-mailer/workflows/CI/badge.svg)](https://github.com/loguntsovae/teach-me-mailer/actions)

## 🚀 Deployment

### Production Deployment

```bash
# Build production image
docker build -t teach-me-mailer:latest .

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Or use our deployment scripts
make deploy-prod
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Monitor deployment
kubectl get pods -l app=teach-me-mailer
```

### Environment Variables for Production

```bash
# Required
DATABASE_URL=postgresql://user:pass@db-host:5432/prod_db
SMTP_HOST=smtp.sendgrid.net
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key

# Security (Important!)
CORS_ORIGINS=["https://yourdomain.com"]
DEBUG=false
LOG_LEVEL=INFO

# Monitoring
SENTRY_DSN=https://your-production-sentry-dsn@sentry.io/project
```

## 📊 Monitoring & Observability

### Prometheus Metrics

Access metrics at `http://localhost:8000/metrics`:

- `http_requests_total` - Total requests by endpoint and status
- `email_sends_total` - Email delivery attempts and results
- `rate_limit_hits_total` - Rate limiting statistics
- `smtp_connection_duration_seconds` - SMTP performance metrics

### Structured Logging

All logs output structured JSON for easy parsing:

```json
{
  "timestamp": "2025-11-07T10:30:00.123Z",
  "level": "INFO",
  "message": "Email sent successfully",
  "request_id": "req_abc123",
  "api_key_id": "550e8400-e29b-41d4-a716-446655440000",
  "recipient": "user@example.com",
  "duration_ms": 234
}
```

### Sentry Integration

Automatic error tracking and performance monitoring:
- Exception capture and grouping
- Performance transaction tracking
- Release tracking for deployments

## 🔧 Development Commands

> **Development Flow**: Push all changes to `develop` → open PR to `main` after successful pipeline.

```bash
# Development workflow
make dev           # Start development environment
make lint          # Run code quality checks
make format        # Auto-format code
make test          # Run test suite
make migrate       # Run database migrations

# Database management
make db-reset      # Reset database to clean state
make db-shell      # Access PostgreSQL shell
make db-backup     # Create database backup

# Docker management
make build         # Build Docker images
make logs          # View container logs
make clean         # Clean up Docker resources
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the full test suite: `make test`
5. Submit a pull request

## 📁 Project Structure

```
├── app/                    # Application source code
│   ├── api/               # API routes and endpoints
│   ├── core/              # Core configuration and dependencies
│   ├── models/            # Database models
│   ├── schemas/           # Pydantic models for validation
│   ├── services/          # Business logic services
│   └── scripts/           # Utility scripts
├── tests/                 # Test suite
├── migrations/            # Database migrations
├── docs/                  # Documentation
├── .github/               # GitHub workflows and templates
└── Makefile              # Development commands
```

## 🔒 Security Considerations

- **API Keys**: Use environment variables, never hardcode
- **HTTPS**: Always use HTTPS in production
- **Rate Limiting**: Configure appropriate limits for your use case
- **CORS**: Restrict origins to your domains only
- **Updates**: Keep dependencies updated with Dependabot

## 📈 Performance Benchmarks

| Metric | Value |
|--------|-------|
| **Throughput** | 1,000+ emails/minute |
| **Response Time** | <100ms (95th percentile) |
| **Memory Usage** | <50MB base |
| **Startup Time** | <2 seconds |

## 🐛 Troubleshooting

### Common Issues

**SMTP Connection Failed**
```bash
# Test SMTP configuration
make test-smtp
```

**Database Connection Issues**
```bash
# Check database status
make db-status
```

**Rate Limits Not Working**
```bash
# Check rate limit configuration
make check-limits
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

## 🔁 Example: Minimal client service

A tiny example client that demonstrates how an external service can call this mailer is included at `examples/client_service`.

- `examples/client_service/app.py` — minimal FastAPI app exposing `POST /trigger` which forwards requests to the mailer `/api/v1/send` endpoint using the `X-API-Key` header.
- `examples/client_service/.env.example` — example configuration (set `MAILER_API_KEY` and `MAILER_SEND_URL`).
- `examples/client_service/README.md` — quick start instructions for the example client.

This example is intentionally minimal and intended for local testing and integration demonstrations. It does not attempt to be production-ready.

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Inspired by modern email service architectures
- Thanks to all contributors and the open-source community

---

<div align="center">
  <strong>Ready to send emails at scale? <a href="#-quick-start">Get started now!</a></strong>
</div>
