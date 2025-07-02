# Multi-stage Dockerfile for GitHub Action Handler
# This Dockerfile creates an optimized production image with security best practices

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETARCH

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app/build

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user .

# Production stage
FROM python:3.11-slim as production

# Set metadata labels
LABEL maintainer="AI Development Team <dev@example.com>"
LABEL org.opencontainers.image.title="GitHub Action Handler"
LABEL org.opencontainers.image.description="Comprehensive GitHub Action event handler with Docker support"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="AI Development Team"
LABEL org.opencontainers.image.url="https://github.com/your-org/github-action-handler"
LABEL org.opencontainers.image.source="https://github.com/your-org/github-action-handler"
LABEL org.opencontainers.image.vendor="Your Organization"
LABEL org.opencontainers.image.licenses="MIT"

# Install runtime dependencies and security updates
RUN apt-get update && apt-get install -y \
    ca-certificates \
    tini \
    curl \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r github-handler && \
    useradd -r -g github-handler -d /app -s /bin/bash -c "GitHub Action Handler" github-handler

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/github-handler/.local

# Copy application source
COPY --from=builder /app/build/src ./src

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data /app/config && \
    chown -R github-handler:github-handler /app && \
    chmod -R 755 /app

# Switch to non-root user
USER github-handler

# Set environment variables
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/github-handler/.local/bin:$PATH \
    HOME=/app

# Default configuration
ENV HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    LOG_FORMAT=json \
    STRUCTURED_LOGGING=true \
    WEBHOOK_SIGNATURE_REQUIRED=true \
    RATE_LIMIT_ENABLED=true \
    METRICS_ENABLED=true \
    HEALTH_CHECK_ENABLED=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command
CMD ["python", "-m", "github_action_handler.main"]

# Development stage (optional)
FROM production as development

# Switch back to root for development tools installation
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    vim \
    less \
    htop \
    strace \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy \
    pre-commit

# Switch back to app user
USER github-handler

# Override default command for development
CMD ["python", "-m", "github_action_handler.main", "--debug", "--reload"]

# Testing stage
FROM builder as testing

# Install test dependencies
RUN pip install --no-cache-dir .[test]

# Copy test files
COPY tests/ ./tests/

# Run tests
RUN python -m pytest tests/ -v --cov=src/github_action_handler --cov-report=xml --cov-report=term-missing

# Final production stage
FROM production as final

# Re-declare metadata for final stage
LABEL org.opencontainers.image.title="GitHub Action Handler"
LABEL org.opencontainers.image.description="Comprehensive GitHub Action event handler with Docker support"
LABEL org.opencontainers.image.version="1.0.0"

# Add build info
ARG BUILD_DATE
ARG VCS_REF
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.revision=${VCS_REF}

# Final security check - ensure we're running as non-root
USER github-handler

# Verify installation
RUN python -c "import github_action_handler; print('GitHub Action Handler installed successfully')"

# Default command
CMD ["python", "-m", "github_action_handler.main"] 