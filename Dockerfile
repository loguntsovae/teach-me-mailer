# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_CACHE_DIR=/tmp/uv-cache

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install system dependencies, postgresql-client (for pg_isready), and uv
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
        curl \
        postgresql-client \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app


# Copy uv configuration files and README.md first for better layer caching and build
COPY pyproject.toml uv.lock README.md ./

# Copy entrypoint script for app container
COPY docker/entrypoint.sh /docker/entrypoint.sh
RUN chmod +x /docker/entrypoint.sh

# Create cache directory and install dependencies
RUN mkdir -p /tmp/uv-cache && \
    uv sync --no-dev --frozen && \
    pip install alembic && \
    rm -rf /tmp/uv-cache

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["uv", "run", "--no-sync", "gunicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Production stage
FROM base AS production

# No extra steps needed for production, base image is ready

# Development stage
FROM base AS development

# Install development dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
        curl \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create cache directory and install dependencies
RUN mkdir -p /tmp/uv-cache && \
    uv sync --frozen && \
    rm -rf /tmp/uv-cache

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000
