# Atomic Rate Limiting Implementation

## Overview

This implementation provides **thread-safe, atomic rate limiting** for the mail gateway service using PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE` pattern. The rate limiting happens in a **single database transaction** to prevent race conditions under high concurrency.

## Key Components

### 1. AtomicRateLimitService (`app/services/atomic_rate_limit.py`)

**Core Method**: `check_and_increment_rate_limit(api_key_id, email_count)`

**SQL Pattern**:
```sql
INSERT INTO daily_usage (api_key_id, date, count) 
VALUES (:api_key_id, :today, :email_count)
ON CONFLICT (api_key_id, date) 
DO UPDATE SET 
    count = daily_usage.count + :email_count 
WHERE daily_usage.count + :email_count <= :effective_limit 
RETURNING count
```

**Key Features**:
- **Atomic Operation**: Rate check + increment in single transaction
- **Conditional Update**: Only increments if within limit
- **Race Condition Safe**: Uses PostgreSQL's MVCC and unique constraints
- **Returns Current Count**: Provides immediate feedback on usage

### 2. Integration with API Routes

**Send Mail Endpoint** (`/api/v1/send`):
1. **Pre-flight Rate Check**: Atomic check before any email processing
2. **429 Response**: Returns `Retry-After` header with seconds until reset
3. **Detailed Error Messages**: Shows current count, requested count, and limit
4. **Automatic Logging**: Tracks successful sends after email delivery

**Usage Endpoint** (`/api/v1/usage`):
- **Zero-increment Query**: Gets current usage without incrementing
- **Reset Time**: Shows when daily limit resets (next day at midnight)

### 3. Error Handling

**Rate Limit Exceeded (429)**:
```json
{
  "detail": "Daily email limit exceeded. Current: 95, Requested: 10, Limit: 100. Try again in 3847 seconds.",
  "headers": {
    "Retry-After": "3847"
  }
}
```

**Benefits of This Approach**:
- **No Race Conditions**: Multiple concurrent requests can't exceed limits
- **Efficient**: Single database round-trip for check + increment
- **Reliable**: Uses PostgreSQL's ACID properties for consistency
- **Production Ready**: Handles timezone-aware date calculations
- **HTTP Compliant**: Proper 429 responses with Retry-After headers

## Database Schema

**daily_usage table**:
```sql
CREATE TABLE daily_usage (
    id BIGSERIAL PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    date DATE NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_daily_usage_api_key_date UNIQUE (api_key_id, date)
);
```

**Critical Constraint**: `UNIQUE (api_key_id, date)` enables atomic upsert pattern.

## Testing Scenarios

1. **Concurrent Requests**: Multiple requests for same API key should never exceed limit
2. **Boundary Conditions**: Requests exactly at limit should work correctly
3. **Timezone Handling**: Daily resets should work across timezones
4. **Error Recovery**: Failed email sends shouldn't consume quota

## Migration from Old System

The old `UsageTrackingService` had potential race conditions:
1. Check rate limit (SELECT)
2. Send email
3. Track usage (INSERT/UPDATE)

The new `AtomicRateLimitService` combines steps 1 & 3 into a single atomic operation.