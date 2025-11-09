# Architecture Documentation

This document describes the technical architecture and design patterns used in the Teach Me Mailer service.

## Overview

Teach Me Mailer is a production-ready email service built with modern async Python technologies. It provides a secure, scalable, and observable API for sending emails with built-in rate limiting and comprehensive monitoring.

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    Client[Client Applications]
    LB[Load Balancer]
    API[FastAPI Application]
    DB[(PostgreSQL)]
    SMTP[SMTP Server]
    Monitor[Monitoring Stack]

    Client --> LB
    LB --> API
    API --> DB
    API --> SMTP
    API --> Monitor

    subgraph "Application Layer"
        API --> Auth[Authentication Service]
        API --> RateLimit[Rate Limiting Service]
        API --> EmailService[Email Service]
        API --> Logger[Logging Service]
    end

    subgraph "Data Layer"
        DB --> APIKeys[API Keys Table]
        DB --> Usage[Daily Usage Table]
        DB --> Logs[Send Logs Table]
    end

    subgraph "External Services"
        SMTP
        Monitor --> Prometheus[Prometheus]
        Monitor --> Sentry[Sentry]
    end
```

### Request Flow Architecture

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI App
    participant Auth as Auth Service
    participant RL as Rate Limiter
    participant ES as Email Service
    participant DB as PostgreSQL
    participant SMTP as SMTP Server
    participant Mon as Monitoring

    Note over C,Mon: Email Send Request Flow

    C->>API: POST /api/v1/send + X-API-Key
    API->>API: Parse request & validate schema

    API->>Auth: Authenticate API key
    Auth->>DB: Query api_keys table
    DB-->>Auth: Return key details
    Auth-->>API: Authentication result

    alt Authentication failed
        API-->>C: 401 Unauthorized
    else Authentication successful
        API->>RL: Check rate limit
        RL->>DB: Atomic upsert daily_usage
        DB-->>RL: Current usage count

        alt Rate limit exceeded
            RL-->>API: Rate limit exceeded
            API->>Mon: Log rate limit hit
            API-->>C: 429 Too Many Requests
        else Within limits
            RL-->>API: Request allowed

            API->>ES: Queue email for sending
            ES->>SMTP: Send email via STARTTLS
            SMTP-->>ES: Send result

            ES->>DB: Log send attempt
            ES->>Mon: Update metrics

            API-->>C: 202 Email Queued
        end
    end
```

## Component Architecture

### 1. API Layer

```mermaid
graph LR
    subgraph "FastAPI Application"
        Router[API Router]
        Middleware[Middleware Stack]
        Deps[Dependencies]

        Router --> Auth[Auth Dependency]
        Router --> RateLimit[Rate Limit Check]
        Router --> Validation[Request Validation]

        Middleware --> CORS[CORS Middleware]
        Middleware --> Logging[Request Logging]
        Middleware --> Metrics[Metrics Collection]
        Middleware --> Security[Security Headers]
    end
```

**Key Components:**
- **FastAPI Router**: RESTful endpoint definitions
- **Dependency Injection**: Clean separation of concerns
- **Middleware Stack**: Cross-cutting concerns (CORS, logging, metrics)
- **Pydantic Models**: Request/response validation

### 2. Authentication Service

```mermaid
graph TD
    Request[Incoming Request] --> Extract[Extract API Key]
    Extract --> Validate[Validate Format]
    Validate --> Hash[Hash Lookup]
    Hash --> DB[(Database Query)]
    DB --> Verify[Verify with bcrypt]
    Verify --> Result{Valid Key?}

    Result -->|Yes| Allow[Allow Request]
    Result -->|No| Deny[Return 401]

    Allow --> Context[Set Auth Context]
```

**Security Features:**
- bcrypt password hashing with configurable rounds
- Constant-time comparison to prevent timing attacks
- API key format validation (sk_test_* or sk_live_*)
- Database-backed key storage with UUIDs

### 3. Rate Limiting Service

```mermaid
graph TD
    Check[Rate Limit Check] --> Query[Query Current Usage]
    Query --> DB[(PostgreSQL)]
    DB --> Atomic[Atomic Upsert]

    Atomic --> Count{Check Count}
    Count -->|Under Limit| Allow[Allow + Increment]
    Count -->|Over Limit| Deny[Deny Request]

    Allow --> Update[Update Usage Count]
    Deny --> Log[Log Rate Limit Hit]

    subgraph "Database Operations"
        Atomic --> Insert[INSERT ON CONFLICT]
        Insert --> DoUpdate[DO UPDATE SET]
        DoUpdate --> Return[RETURNING count]
    end
```

**Technical Implementation:**
- PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` for atomicity
- Daily usage tracking with automatic reset
- Thread-safe operations in high-concurrency scenarios
- Configurable rate limits per API key

### 4. Email Service

```mermaid
graph TB
    Queue[Email Queue] --> Validate[Validate Email]
    Validate --> Domain[Domain Check]
    Domain --> Template[Process Template]
    Template --> SMTP[SMTP Connection]

    SMTP --> TLS[STARTTLS Negotiation]
    TLS --> Auth[SMTP Authentication]
    Auth --> Send[Send Email]

    Send --> Success{Success?}
    Success -->|Yes| LogSuccess[Log Success]
    Success -->|No| LogError[Log Error]

    LogSuccess --> DB[(Database)]
    LogError --> DB

    subgraph "Email Processing"
        Template --> HTMLRender[HTML Rendering]
        Template --> TextFallback[Text Fallback]
        Template --> Headers[Custom Headers]
    end
```

**Features:**
- Async SMTP client with connection pooling
- STARTTLS encryption for secure delivery
- Domain validation and MX record checking
- HTML and text body support
- Custom header support
- Comprehensive error handling and logging

## Data Model

### Database Schema

```mermaid
erDiagram
    API_KEYS ||--o{ DAILY_USAGE : "tracks usage"
    API_KEYS ||--o{ SEND_LOGS : "logs sends"

    API_KEYS {
        uuid id PK
        string name
        string key_hash
        int daily_limit
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    DAILY_USAGE {
        uuid id PK
        uuid api_key_id FK
        date date
        int count
        timestamp created_at
        timestamp updated_at
    }

    SEND_LOGS {
        uuid id PK
        uuid api_key_id FK
        string recipient
        string subject
        boolean success
        string error_message
        timestamp created_at
    }
```

### Key Design Decisions

1. **UUIDs for Primary Keys**: Better security and distributed system support
2. **Separate Usage Tracking**: Enables efficient rate limiting queries
3. **Audit Trail**: Complete send log history for debugging and compliance
4. **Timestamp Tracking**: Enables time-based analytics and cleanup

## Security Architecture

### Defense in Depth

```mermaid
graph TD
    Internet[Internet] --> WAF[Web Application Firewall]
    WAF --> LB[Load Balancer]
    LB --> TLS[TLS Termination]
    TLS --> API[FastAPI Application]

    subgraph "Application Security"
        API --> CORS[CORS Protection]
        CORS --> RateLimit[Rate Limiting]
        RateLimit --> Auth[API Key Auth]
        Auth --> Validation[Input Validation]
        Validation --> Sanitization[Data Sanitization]
    end

    subgraph "Data Security"
        Sanitization --> Encryption[Data Encryption]
        Encryption --> Hashing[Password Hashing]
        Hashing --> DB[(Encrypted Storage)]
    end

    subgraph "Monitoring Security"
        DB --> Audit[Audit Logging]
        Audit --> SIEM[SIEM Integration]
        SIEM --> Alerts[Security Alerts]
    end
```

**Security Layers:**
1. **Network**: TLS encryption, CORS, request size limits
2. **Authentication**: bcrypt hashing, secure API key format
3. **Authorization**: Per-key rate limiting
4. **Input Validation**: Pydantic schema validation
5. **Data Protection**: Sensitive data masking in logs
6. **Monitoring**: Comprehensive audit trails and alerting

## Observability Architecture

### Monitoring Stack

```mermaid
graph TB
    App[FastAPI App] --> Metrics[Prometheus Metrics]
    App --> Logs[Structured Logging]
    App --> Traces[Distributed Tracing]
    App --> Errors[Error Tracking]

    Metrics --> Prometheus[Prometheus Server]
    Logs --> Aggregator[Log Aggregator]
    Traces --> Jaeger[Jaeger]
    Errors --> Sentry[Sentry]

    Prometheus --> Grafana[Grafana Dashboards]
    Aggregator --> ElasticSearch[ElasticSearch]
    ElasticSearch --> Kibana[Kibana]

    subgraph "Alerting"
        Grafana --> AlertManager[Alert Manager]
        Sentry --> Notifications[Error Notifications]
        AlertManager --> PagerDuty[PagerDuty]
    end

    subgraph "Business Metrics"
        Metrics --> EmailRate[Email Send Rate]
        Metrics --> ErrorRate[Error Rate]
        Metrics --> Latency[Response Latency]
        Metrics --> RateLimits[Rate Limit Hits]
    end
```

### Key Metrics

1. **Performance Metrics**:
   - HTTP request duration (p50, p95, p99)
   - Email send latency
   - Database query performance
   - SMTP connection time

2. **Business Metrics**:
   - Total emails sent per day/hour
   - Success/failure rates
   - Rate limit hit rate
   - API key usage patterns

3. **System Metrics**:
   - CPU and memory usage
   - Database connection pool status
   - Active concurrent connections
   - Error rates by endpoint

## Deployment Architecture

### Container Strategy

```mermaid
graph TB
    subgraph "Development"
        DevCode[Source Code] --> DevBuild[Docker Build]
        DevBuild --> DevTest[Run Tests]
        DevTest --> DevDeploy[Local Deploy]
    end

    subgraph "CI/CD Pipeline"
        DevDeploy --> CI[GitHub Actions]
        CI --> TestSuite[Full Test Suite]
        TestSuite --> SecurityScan[Security Scan]
        SecurityScan --> BuildProd[Production Build]
        BuildProd --> Registry[Container Registry]
    end

    subgraph "Production"
        Registry --> Deploy[Deployment]
        Deploy --> Health[Health Checks]
        Health --> LoadBalancer[Load Balancer]
        LoadBalancer --> Monitoring[Monitoring]
    end
```

### Scaling Strategy

**Horizontal Scaling**:
- Stateless application design
- Database connection pooling
- Shared session state via Redis (future)

**Vertical Scaling**:
- Async I/O for high concurrency
- Efficient memory usage
- Database query optimization

## Performance Considerations

### Optimization Strategies

1. **Database Optimization**:
   - Connection pooling with SQLAlchemy
   - Efficient indexing on query patterns
   - Atomic operations for rate limiting
   - Read replicas for analytics queries

2. **Application Optimization**:
   - Async/await for I/O operations
   - Connection pooling for SMTP
   - Response streaming for large payloads
   - Caching frequently accessed data

3. **Infrastructure Optimization**:
   - CDN for static assets
   - Database read replicas
   - Redis caching layer
   - Horizontal pod autoscaling

### Performance Targets

| Metric | Target | Monitoring |
|--------|--------|------------|
| Response Time (p95) | < 100ms | Prometheus |
| Email Send Rate | 1000/min | Business metrics |
| Availability | 99.9% | Health checks |
| Database Queries | < 50ms | Query logging |

## Future Architecture Enhancements

### Planned Improvements

1. **Message Queue Integration**:
   - Redis/RabbitMQ for email queuing
   - Retry logic with exponential backoff
   - Dead letter queue for failed sends

2. **Multi-tenant Architecture**:
   - Tenant isolation
   - Per-tenant rate limiting
   - Tenant-specific SMTP configurations

3. **Advanced Monitoring**:
   - Custom business dashboards
   - Predictive alerting
   - Cost optimization metrics

4. **Enhanced Security**:
   - OAuth 2.0 integration
   - Role-based access control
   - API versioning strategy

This architecture provides a solid foundation for a production email service while maintaining flexibility for future enhancements and scaling requirements.
