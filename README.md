# Mail Gateway Service

A production-ready async FastAPI service for sending emails with API key authentication, atomic rate limiting, and comprehensive observability.

## Features

- 🚀 **Async FastAPI** with high-performance email processing
- 🔐 **API Key Authentication** with bcrypt hashing and constant-time verification
- ⚡ **Atomic Rate Limiting** with PostgreSQL upsert for thread-safe operations
- 📧 **Email Delivery** via SMTP with STARTTLS and domain validation
- 📊 **Observability** with Prometheus metrics and structured JSON logging
- 🐳 **Docker Ready** with slim images and non-root security
- 🧪 **Comprehensive Tests** with pytest and async support
- 🔒 **Security Hardened** with CORS restrictions and request size limits

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone and enter directory
git clone <repo> mail-gateway
cd mail-gateway

# Start services
make up

# Create an API key
make seed

# Test the service
curl -X POST "http://localhost:8000/api/v1/send" \
  -H "X-API-Key: sk_test_default_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "test@example.com",
    "subject": "Test Email",
    "html_body": "<h1>Hello World!</h1>",
    "text_body": "Hello World!"
  }'

# Check metrics
curl http://localhost:8000/metrics
```

### Manual Setup

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Setup Database**
```bash
# Start PostgreSQL
docker run --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:15

# Run migrations
alembic upgrade head
```

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your SMTP settings
```

4. **Create API Key**
```bash
python -m app.scripts.create_api_key --name "default" --limit 15
```

5. **Start Service**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Configuration

Environment variables (see `.env.example`):

### Database
- `DATABASE_URL` - PostgreSQL connection string
- `DATABASE_ECHO` - Enable SQL query logging (default: false)

### SMTP
- `SMTP_HOST` - SMTP server hostname
- `SMTP_PORT` - SMTP server port (default: 587)
- `SMTP_USERNAME` - SMTP authentication username
- `SMTP_PASSWORD` - SMTP authentication password
- `SMTP_FROM_ADDRESS` - Default sender email address

### Security
- `CORS_ORIGINS` - Allowed CORS origins (default: none)
- `MAX_REQUEST_SIZE` - Maximum request size in bytes (default: 262144)

### Logging
- `LOG_LEVEL` - Logging level (default: INFO)
- `LOG_JSON` - Enable JSON logging (default: true)

## API Documentation

### Authentication
All API endpoints require authentication via the `X-API-Key` header:
```bash
-H "X-API-Key: your_api_key_here"
```

### Send Email

**POST** `/api/v1/send`

Send an email with rate limiting and background processing.

#### Request
```json
{
  "to": "recipient@example.com",
  "subject": "Email Subject",
  "html_body": "<p>HTML content</p>",
  "text_body": "Plain text content"
}
```

#### Response
- **202 Accepted** - Email queued for delivery
```json
{
  "message": "Email queued for delivery"
}
```

- **401 Unauthorized** - Invalid API key
- **429 Too Many Requests** - Rate limit exceeded
- **422 Unprocessable Entity** - Invalid request data

#### curl Examples

**Basic Send:**
```bash
curl -X POST "http://localhost:8000/api/v1/send" \
  -H "X-API-Key: sk_test_default_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "user@example.com",
    "subject": "Welcome!",
    "html_body": "<h1>Welcome to our service!</h1><p>Thank you for signing up.</p>",
    "text_body": "Welcome to our service! Thank you for signing up."
  }'
```

**With Custom Headers:**
```bash
curl -X POST "http://localhost:8000/api/v1/send" \
  -H "X-API-Key: sk_test_default_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "user@example.com",
    "subject": "Newsletter",
    "html_body": "<h2>Latest Updates</h2>",
    "text_body": "Latest Updates",
    "headers": {
      "Reply-To": "noreply@example.com",
      "X-Priority": "1"
    }
  }'
```

### Health Check

**GET** `/health`

Returns service health status.

```bash
curl http://localhost:8000/health
```

### Metrics

**GET** `/metrics`

Returns Prometheus metrics for monitoring.

```bash
curl http://localhost:8000/metrics
```

## Rate Limiting

- Rate limits are enforced per API key per day
- Limits are configurable when creating API keys
- Uses atomic PostgreSQL upsert operations for thread-safety
- Returns HTTP 429 when limit exceeded

## Monitoring

### Prometheus Metrics

The service exposes metrics at `/metrics`:

- `http_requests_total` - Total HTTP requests by method and status
- `http_request_duration_seconds` - HTTP request duration histogram
- `email_sends_total` - Total email sends by status
- `rate_limit_checks_total` - Rate limit checks by result

### Structured Logging

All logs are output as JSON with:
- Request IDs for correlation
- Structured fields for filtering
- Sensitive data masking (SMTP credentials, API keys)

Example log entry:
```json
{
  "timestamp": "2024-11-07T10:30:00.123Z",
  "level": "INFO",
  "message": "Email sent successfully",
  "request_id": "req_abc123",
  "api_key_id": "550e8400-e29b-41d4-a716-446655440000",
  "recipient": "user@example.com",
  "message_id": "msg_def456"
}
```

## API Key Management

### Create API Key

```bash
python -m app.scripts.create_api_key --name "production" --limit 100
```

Options:
- `--name` - Human-readable name for the key
- `--limit` - Daily email limit (default: 15)

### Database Access

API keys are stored with:
- UUID primary keys
- bcrypt-hashed key values
- Configurable daily limits
- Active/inactive status

```sql
-- Check API key usage
SELECT k.name, k.daily_limit, u.count, u.date
FROM api_keys k
LEFT JOIN daily_usage u ON k.id = u.api_key_id
WHERE u.date = CURRENT_DATE;
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_send.py -v
```

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Type checking
mypy app/

# Linting
flake8 app/ tests/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Deployment

### Docker

```bash
# Build image
docker build -t mail-gateway .

# Run container
docker run -p 8000:8000 --env-file .env mail-gateway
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale web service
docker-compose up -d --scale web=3
```

### Makefile Commands

```bash
make help          # Show all commands
make up            # Start services with Docker Compose
make down          # Stop and remove services
make seed          # Create default API key
make test          # Run tests in Docker
make logs          # View service logs
make shell         # Access container shell
make migrate       # Run database migrations
make clean         # Clean up Docker resources
```

## Security

### Authentication
- API keys only accepted via `X-API-Key` header
- bcrypt hashing with constant-time verification
- No API key exposure in URLs or query parameters

### Network Security
- CORS disabled by default
- Request size limited to 256KB
- HTTPS recommended for production

### Data Protection
- SMTP credentials never logged
- API keys masked in logs
- Sensitive data excluded from error responses

### Production Hardening
- Non-root Docker user (UID 1000)
- Minimal attack surface with slim base images
- Health checks for container orchestration
- Structured logging for security monitoring

## Troubleshooting

### Common Issues

**SMTP Connection Failed**
```bash
# Check SMTP settings
docker-compose logs web | grep SMTP

# Test SMTP connectivity
python -c "
import asyncio
from app.services.mailer import MailerService
from app.core.config import settings
asyncio.run(MailerService().test_connection())
"
```

**Database Connection Issues**
```bash
# Check database connectivity
docker-compose ps postgres
docker-compose logs postgres

# Test database connection
python -c "
import asyncio
from app.core.database import test_connection
asyncio.run(test_connection())
"
```

**Rate Limit Not Working**
```bash
# Check daily usage table
docker-compose exec postgres psql -U postgres -d mailgateway -c "
SELECT * FROM daily_usage WHERE date = CURRENT_DATE;
"
```

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
docker-compose up
```

This will show detailed logs including:
- SQL queries
- SMTP conversation
- Request/response bodies
- Rate limit calculations

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Open an issue on GitHub
4. Check Prometheus metrics for insights

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app

# Test configuration
python test_config.py
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## License

MIT