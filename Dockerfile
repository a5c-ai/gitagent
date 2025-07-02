# Multi-stage Dockerfile for gitagent
# This Dockerfile creates an optimized production image with security best practices

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETARCH

# Install build dependencies including Node.js for CLI tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app/build

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies to a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

    # install node and npm version 
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Install AI CLI tools
RUN npm i -g @openai/codex@native

RUN npm install -g @anthropic-ai/claude-code

RUN npm install -g @google/gemini-cli


# Create CLI tools directory and set up symlinks for easier access
RUN mkdir -p /opt/cli-tools/bin && \
    ln -s /usr/bin/codex /opt/cli-tools/bin/codex && \
    ln -s /opt/venv/bin/anthropic-cli /opt/cli-tools/bin/claude && \
    ln -s /opt/venv/bin/gemini-cli /opt/cli-tools/bin/gemini

# Production stage
FROM python:3.11-slim as production

# Set metadata labels
LABEL maintainer="Tal Muskal <tal@a5c.ai>"
LABEL org.opencontainers.image.title="gitagent"
LABEL org.opencontainers.image.description="Intelligent GitHub Action orchestration with AI-powered event processing and AI CLI tools"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="Tal Muskal"
LABEL org.opencontainers.image.url="https://github.com/a5c-ai/gitagent"
LABEL org.opencontainers.image.source="https://github.com/a5c-ai/gitagent"
LABEL org.opencontainers.image.vendor="Your Organization"
LABEL org.opencontainers.image.licenses="MIT"

# Install runtime dependencies and security updates including Node.js
RUN apt-get update && apt-get install -y \
    ca-certificates \
    tini \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r github-handler && \
    useradd -r -g github-handler -d /app -s /bin/bash -c "gitagent" github-handler

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy CLI tools from builder stage
COPY --from=builder /opt/cli-tools /opt/cli-tools
COPY --from=builder /usr/lib/node_modules/@openai/codex /usr/lib/node_modules/@openai/codex

# Copy application source
COPY --from=builder /app/build/src ./src

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data /app/config && \
    chown -R github-handler:github-handler /app && \
    chmod -R 755 /app

# Switch to non-root user
USER github-handler

# Set environment variables
ENV PATH="/opt/venv/bin:/opt/cli-tools/bin:/usr/lib/node_modules/.bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
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
CMD ["python", "-m", "gitagent.main"]

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
USER gitagent

# Override default command for development
CMD ["python", "-m", "gitagent.main", "--debug", "--reload"]

# Testing stage
FROM builder as testing

# Install test dependencies (virtual environment already activated from builder)
RUN pip install --no-cache-dir .[test]

# Copy test files
COPY tests/ ./tests/

# Run tests
RUN python -m pytest tests/ -v --cov=src/gitagent --cov-report=xml --cov-report=term-missing

# Final production stage
FROM production as final

# Re-declare metadata for final stage
LABEL org.opencontainers.image.title="gitagent"
LABEL org.opencontainers.image.description="Intelligent GitHub Action orchestration with AI-powered event processing and AI CLI tools"
LABEL org.opencontainers.image.version="1.0.0"

# Add build info
ARG BUILD_DATE
ARG VCS_REF
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.revision=${VCS_REF}

# Final security check - ensure we're running as non-root
USER gitagent

# Verify dependencies and installation
RUN python -c "import gitagent; print('gitagent and dependencies installed successfully')" && \
    codex --version && echo "OpenAI Codex CLI installed successfully" && \
    claude --help && echo "Claude Code installed successfully" && \
    gemini --help && echo "Gemini CLI installed successfully"

# Default command
CMD ["python", "-m", "gitagent.main"] 