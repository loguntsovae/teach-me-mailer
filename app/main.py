import logging
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

import structlog

# Sentry integration for error tracking and performance monitoring
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.core.config import get_settings
from app.api.v1 import routes

# Initialize Sentry SDK
sentry_sdk.init(
    dsn="https://fccb9ee60a71cb42db499c0546e83160@o4510323039535104.ingest.de.sentry.io/4510323045892176",
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
    environment="dev",
)

# Configure structured logging
def mask_sensitive_data(event_dict):
    """Mask sensitive data in log events."""
    SENSITIVE_KEYS = {
        'password', 'secret', 'key', 'token', 'auth', 'credential',
        'smtp_password', 'smtp_user', 'api_key', 'x_api_key',
        'secret_key', 'database_url'
    }
    
    def mask_dict(data, path=""):
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                key_lower = key.lower().replace('-', '_')
                if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
                    masked[key] = "***MASKED***"
                else:
                    masked[key] = mask_dict(value, f"{path}.{key}" if path else key)
            return masked
        elif isinstance(data, str):
            # Mask values that look like credentials (long strings with mixed case/numbers)
            if len(data) > 20 and any(c.isdigit() for c in data) and any(c.isupper() for c in data):
                return f"{data[:4]}***MASKED***{data[-4:]}"
            return data
        elif isinstance(data, list):
            return [mask_dict(item, path) for item in data]
        else:
            return data
    
    return mask_dict(event_dict)


def configure_logging():
    """Configure JSON structured logging to stdout with secret masking."""
    settings = get_settings()
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Configure structlog with secret masking
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            mask_sensitive_data,  # Add secret masking processor
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """Add request_id to all requests for tracing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add request_id to structlog context
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    response = await call_next(request)
    
    # Add request_id to response headers
    response.headers["X-Request-ID"] = request_id
    
    # Clear context after request
    structlog.contextvars.clear_contextvars()
    
    return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    configure_logging()
    logger = structlog.get_logger(__name__)
    settings = get_settings()
    
    logger.info(
        "Application starting up",
        app_name=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Minimal async FastAPI mail gateway service",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
        # OpenAPI security scheme for X-API-Key
        openapi_tags=[
            {"name": "health", "description": "Health check endpoint"},
            {"name": "mail", "description": "Mail sending operations"},
            {"name": "metrics", "description": "Prometheus metrics"},
        ],
    )
    
    # Add request ID middleware for tracing
    app.middleware("http")(request_id_middleware)
    
    # Add request size limiting (configurable)
    @app.middleware("http")
    async def limit_request_size(request: Request, call_next: Callable) -> Response:
        """Limit request body size to prevent abuse."""
        max_size = settings.max_request_size
        
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > max_size:
                return Response(
                    status_code=413,
                    content=f'{{"detail": "Request entity too large. Maximum size is {max_size // 1024}KB."}}',
                    media_type="application/json"
                )
        
        return await call_next(request)
    
    # Add CORS middleware - restrictive by default
    cors_origins = []
    if settings.debug and not settings.cors_origins:
        # Allow localhost in debug mode if no explicit CORS config
        cors_origins = ["http://localhost:3000", "http://localhost:8080"]
    elif settings.cors_origins:
        cors_origins = settings.cors_origins
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,  # Don't allow credentials for security
        allow_methods=["GET", "POST"],  # Only allow necessary methods
        allow_headers=["X-API-Key", "Content-Type", "X-Request-ID"],  # Only necessary headers
    )
    
    # Setup Prometheus metrics (skip during testing to avoid registry conflicts)
    import os
    if os.getenv("PYTEST_CURRENT_TEST") is None:  # Not running in pytest
        instrumentator = Instrumentator(
            should_group_status_codes=False,
            should_ignore_untemplated=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics", "/health", "/docs", "/redoc", "/openapi.json"],
        )
        instrumentator.instrument(app)
        instrumentator.expose(app, endpoint="/metrics", tags=["metrics"])
    
    # Include API routes
    app.include_router(
        routes.router,
        prefix="/api/v1",
        tags=["mail"],
    )
    
    # Add health endpoint at root level
    app.include_router(
        routes.router,
        prefix="",
        tags=["health"],
        include_in_schema=False,
    )
    
    return app


# Create app instance
app = create_app()


# Root endpoint redirect
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with basic info."""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )