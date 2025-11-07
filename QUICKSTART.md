# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Clone and Start
```bash
git clone <repo>
cd mail-gateway
make up
```

### 2. Run Migrations  
```bash
make migrate
```

### 3. Create API Key
```bash
make seed
# Follow prompts, save the generated API key!
```

### 4. Test the Service
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Send test email (replace YOUR_API_KEY)
curl -X POST http://localhost:8000/api/v1/send \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "test@example.com",
    "subject": "Hello World",
    "text": "Test message from mail gateway",
    "html": "<h1>Hello!</h1><p>Test message</p>"
  }'

# Check metrics
curl http://localhost:8000/metrics
```

### 5. View Logs
```bash
make logs
```

## 🛠️ Development Setup

```bash
# Install dependencies locally
pip install -r requirements.txt

# Start development server
make dev

# Run tests
make test

# Code formatting
make format

# Security scan
make security
```

## 📋 Configuration

Create `.env` file:
```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mailgateway
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com  
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
SECRET_KEY=your-secret-key-change-in-production

# Optional
DEBUG=true
DEFAULT_DAILY_LIMIT=100
ALLOW_DOMAINS=trusted1.com,trusted2.com
```

## 🔍 Monitoring URLs

- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/v1/health  
- **Metrics**: http://localhost:8000/metrics
- **Usage**: http://localhost:8000/api/v1/usage (with API key)

## 🧪 Test Coverage

```bash
# Run full test suite
pytest -v tests/

# Test specific area
pytest tests/test_auth.py -v
pytest tests/test_rate_limit.py -v
pytest tests/test_send.py -v
```

## 🐳 Production Deployment

```bash
# Build and deploy
docker-compose -f docker-compose.yml up -d

# Scale the app service
docker-compose up --scale app=3

# Update configuration
docker-compose down
# Edit docker-compose.yml environment
docker-compose up -d
```

## 🆘 Troubleshooting

**Database connection issues**:
```bash
make reset-db
```

**View detailed logs**:
```bash
docker-compose logs -f postgres
docker-compose logs -f app
```

**Clean rebuild**:
```bash
make clean
make up
```

**Test SMTP settings**:
```bash
# Use the test endpoints with valid API key
curl -H "X-API-Key: YOUR_KEY" \
     http://localhost:8000/api/v1/usage
```

That's it! Your mail gateway is ready for production use with full observability. 🎉