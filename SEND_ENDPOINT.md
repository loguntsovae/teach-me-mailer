# POST /api/v1/send Endpoint

## Overview
Asynchronous email sending endpoint with atomic rate limiting and background processing.

## Request

### Method & URL
```
POST /api/v1/send
```

### Headers
```
X-API-Key: your-api-key-here
Content-Type: application/json
```

### Request Schema
```json
{
  "to": "user@example.com",
  "subject": "string",
  "html": "string",
  "text": "string|null",
  "headers": {"X-Custom": "v"} | null
}
```

### Field Validation
- **`to`**: EmailStr (pydantic email validation)
- **`subject`**: string, max_length=256
- **`html`**: string (optional)
- **`text`**: string (optional)
- **`headers`**: Dict[str, str] (optional)
- **Constraint**: Either `html` OR `text` must be provided (custom validator)

## Response

### Success Response (202 Accepted)
```json
{
  "status": "queued",
  "remaining": 95
}
```

### Error Responses

#### 401 Unauthorized
```json
{
  "detail": "Missing or invalid API key"
}
```

#### 403 Forbidden  
```json
{
  "detail": "API key disabled or invalid"
}
```

#### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "subject"],
      "msg": "ensure this value has at most 256 characters",
      "type": "value_error.any_str.max_length"
    }
  ]
}
```

#### 429 Rate Limited
```json
{
  "detail": "Daily email limit exceeded. Current: 100, Limit: 100. Try again in 3600 seconds."
}
```
**Headers**: `Retry-After: 3600`

## Processing Flow

### 1. Authentication
- Validates X-API-Key header
- Returns 401/403 if invalid/disabled

### 2. Rate Limiting (Atomic)
- Checks daily limit against current usage
- Increments counter atomically in single transaction
- Returns 429 with Retry-After header if exceeded

### 3. Send Log Creation
- Creates `SendLog` entry immediately with `message_id=null`
- Commits to database before queuing
- Provides tracking ID for the email

### 4. Background Queuing
- Adds email sending to FastAPI BackgroundTasks
- Returns 202 immediately without waiting
- Client gets instant response

### 5. Background Processing
- Sends actual email via SMTP
- Updates `SendLog.message_id` with SMTP response
- Handles domain validation and errors
- Logs success/failure for monitoring

### 6. Response
- Status: 202 Accepted
- Body: `{"status": "queued", "remaining": <count>}`
- Client knows email is queued and remaining quota

## Database Schema

### SendLog Table
```sql
CREATE TABLE send_logs (
    id BIGSERIAL PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recipient VARCHAR(255) NOT NULL,
    message_id TEXT NULL  -- Updated after background send
);
```

**Flow**:
1. Row created with `message_id=NULL`
2. Background task updates with SMTP message ID
3. `NULL` indicates send failure or pending

## Example Usage

### Curl Request
```bash
curl -X POST http://localhost:8000/api/v1/send \
  -H "X-API-Key: your-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "customer@example.com",
    "subject": "Welcome to our service", 
    "html": "<h1>Welcome!</h1><p>Thank you for signing up.</p>",
    "text": "Welcome! Thank you for signing up.",
    "headers": {
      "X-Campaign": "welcome",
      "X-Priority": "normal"
    }
  }'
```

### Python Client
```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/v1/send",
    headers={"X-API-Key": "your-key-here"},
    json={
        "to": "user@example.com",
        "subject": "Test Email",
        "html": "<p>HTML content</p>",
        "headers": {"X-Test": "true"}
    }
)

if response.status_code == 202:
    data = response.json()
    print(f"Queued! Remaining: {data['remaining']}")
elif response.status_code == 429:
    retry_after = response.headers.get("Retry-After")
    print(f"Rate limited. Retry in {retry_after} seconds")
```

## Key Features

### ✅ **Atomic Rate Limiting**
- Single database transaction for check + increment
- No race conditions under high concurrency
- Immediate feedback on quota usage

### ✅ **Asynchronous Processing**
- Instant 202 response to client
- Email sending happens in background
- Better user experience and API performance

### ✅ **Tracking & Monitoring**
- Every email gets SendLog entry with tracking ID
- Message IDs from SMTP for external correlation
- Comprehensive structured logging

### ✅ **Robust Error Handling**
- Proper HTTP status codes and messages
- Retry-After headers for rate limiting
- Graceful handling of SMTP failures

### ✅ **Production Ready**
- Domain validation via ALLOW_DOMAINS
- Custom headers support
- Timezone-aware date handling
- Background task error isolation