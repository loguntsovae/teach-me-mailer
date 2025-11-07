# Security Configuration

## 🔒 Security Features Implementation

This document outlines the security measures implemented in the mail gateway service.

## ✅ Authentication Security

### Header-Only API Key Authentication
- **Requirement**: API keys are ONLY accepted via `X-API-Key` header
- **Implementation**: FastAPI `Header()` dependency injection
- **Query Parameter Protection**: Query parameters are completely ignored for authentication
- **Code Location**: `app/core/deps.py:get_current_api_key()`

```python
async def get_current_api_key(
    x_api_key: str = Header(alias="X-API-Key"),  # Header only!
    auth_service: AuthService = Depends(get_auth_service),
) -> APIKey:
```

### Constant-Time Comparison
- **Requirement**: All API key comparisons use constant-time algorithms
- **Implementation**: Delegated to `bcrypt.checkpw()` which provides constant-time comparison
- **Protection**: Prevents timing attacks against API key verification
- **Code Location**: `app/services/auth.py:_verify_api_key()`

```python
def _verify_api_key(self, api_key: str, hashed: str) -> bool:
    """Verify API key against hash using constant-time comparison."""
    return bcrypt.checkpw(api_key.encode('utf-8'), hashed.encode('utf-8'))
```

## ✅ CORS Security

### Restrictive CORS by Default
- **Production**: CORS disabled by default (`allow_origins=[]`)
- **Development**: Only localhost origins allowed in debug mode
- **Configurable**: `CORS_ORIGINS` environment variable for explicit control
- **Credentials**: `allow_credentials=False` for security
- **Methods**: Only `GET` and `POST` allowed
- **Headers**: Only `X-API-Key`, `Content-Type`, `X-Request-ID` allowed

```python
# Production: No CORS unless explicitly configured
cors_origins = []
if settings.debug and not settings.cors_origins:
    cors_origins = ["http://localhost:3000", "http://localhost:8080"]
elif settings.cors_origins:
    cors_origins = settings.cors_origins
```

## ✅ Request Size Limiting

### 256KB Request Limit
- **Default Limit**: 256KB (262,144 bytes)
- **Configurable**: `MAX_REQUEST_SIZE` environment variable
- **Protection**: Prevents DoS attacks via large request bodies
- **Response**: HTTP 413 with clear error message
- **Implementation**: Middleware checks `Content-Length` header

```python
@app.middleware("http")
async def limit_request_size(request: Request, call_next: Callable) -> Response:
    """Limit request body size to prevent abuse."""
    max_size = settings.max_request_size  # 256KB default
    
    if request.headers.get("content-length"):
        content_length = int(request.headers["content-length"])
        if content_length > max_size:
            return Response(status_code=413, ...)
```

## ✅ Credential Protection

### SMTP Credentials Never Logged
- **Implementation**: Explicit exclusion of SMTP credentials from all log statements
- **Protection**: Prevents credential leakage in logs
- **Code Locations**: 
  - `app/services/mailer.py` - SMTP operations
  - `app/main.py` - Secret masking processor

```python
logger.info(
    "Sending email",
    smtp_host=self.settings.smtp_host,
    smtp_port=self.settings.smtp_port,
    # NEVER log smtp_user or smtp_password
)
```

### Universal Secret Masking
- **Implementation**: Structured logging processor masks all sensitive data
- **Sensitive Keys**: `password`, `secret`, `key`, `token`, `auth`, `credential`, etc.
- **Pattern Matching**: Detects credential-like strings and masks them
- **Format**: Shows first/last 4 characters: `abcd***MASKED***xyz9`

```python
SENSITIVE_KEYS = {
    'password', 'secret', 'key', 'token', 'auth', 'credential',
    'smtp_password', 'smtp_user', 'api_key', 'x_api_key',
    'secret_key', 'database_url'
}

def mask_sensitive_data(event_dict):
    """Mask sensitive data in log events."""
    # Automatically masks any field matching sensitive patterns
```

## ✅ API Key Security

### No Plaintext Storage
- **Storage**: Only bcrypt hashes stored in database
- **Generation**: Cryptographically secure random generation
- **Display**: Plaintext shown ONLY during initial creation
- **Validation**: Always via constant-time bcrypt comparison

### No API Key Logging
- **Implementation**: API keys never appear in any log output
- **Protection**: Even partial API keys are masked
- **Code Locations**: All auth-related logging excludes API key content

```python
logger.info(
    "API key validated successfully",
    api_key_id=str(key_obj.id),  # Only log the UUID
    name=key_obj.name,
    # NEVER log the actual API key
)
```

## 🔧 Configuration

### Security Environment Variables

```bash
# Required security settings
SECRET_KEY=your-64-character-secret-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# Optional security settings
CORS_ORIGINS=https://yourdomain.com,https://trusted.com  # Comma-separated
MAX_REQUEST_SIZE=262144  # 256KB in bytes
DEBUG=false  # ALWAYS false in production

# SMTP credentials (never logged)
SMTP_HOST=smtp.provider.com
SMTP_USER=your-email@domain.com
SMTP_PASSWORD=your-secure-app-password
```

### Security Headers

All responses include:
- `X-Request-ID`: Request correlation ID
- No `Server` header exposure
- No credential information in any headers

## 🔍 Security Testing

### Test Coverage
- Header-only authentication validation
- CORS policy enforcement
- Request size limit testing
- Credential masking verification
- Timing attack resistance

### Example Security Tests

```python
# Test header-only auth
async def test_query_param_auth_rejected(client):
    response = await client.get("/api/v1/health?api_key=test-key")
    assert response.status_code == 401  # Should fail

# Test request size limiting
async def test_large_request_rejected(client):
    large_payload = {"text": "x" * 300000}  # >256KB
    response = await client.post("/api/v1/send", json=large_payload)
    assert response.status_code == 413  # Request too large
```

## 🚨 Security Best Practices

### Production Deployment

1. **Environment Variables**: Store ALL secrets in environment variables, never in code
2. **CORS**: Explicitly configure `CORS_ORIGINS` for your domains
3. **HTTPS Only**: Always use HTTPS in production
4. **Log Monitoring**: Monitor for masked credential attempts in logs
5. **Key Rotation**: Regularly rotate API keys and SMTP credentials
6. **Database Security**: Use SSL connections to PostgreSQL
7. **Container Security**: Run as non-root user (already implemented)

### Monitoring

```bash
# Look for security issues in logs
docker logs app | grep "MASKED"  # Should not appear
docker logs app | grep "401\|403"  # Monitor auth failures
docker logs app | grep "413"  # Monitor size limit hits
```

### Incident Response

If credentials are exposed:
1. Immediately rotate affected credentials
2. Review logs for unauthorized access
3. Update environment variables
4. Restart services to clear memory
5. Monitor for abuse patterns

This security configuration provides defense-in-depth protection against common attack vectors while maintaining usability for legitimate users.