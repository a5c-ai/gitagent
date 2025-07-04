# Multi-stage Dockerfile for gitagent
# This Dockerfile creates an optimized production image with security best practices

# Build stage
FROM ubuntu:noble AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETARCH

# Install build dependencies including Node.js for CLI tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    python3 \
    python3-venv \
    python3-pip \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app/build

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies to a virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# Production stage
FROM ubuntu:noble AS production

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
    python3 \
    python3-venv \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r gitagent && \
    useradd -r -g gitagent -d /app -s /bin/bash -c "gitagent" gitagent

RUN npm i -g @openai/codex@native

RUN npm i -g @anthropic-ai/claude-code

RUN npm i -g @google/gemini-cli

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv


# Copy application source
COPY --from=builder /app/build/src ./src

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data /app/config /app/.claude /github/home && \
    mkdir -p /github/home/.claude && \
    echo '{"permissions": {"defaultMode": "default"}}' > /app/.claude/settings.json && \
    echo '{"permissions": {"defaultMode": "default"}}' > /github/home/.claude/settings.json && \
    echo '{}' > /github/home/.claude.json && \
    echo '{}' > /app/.claude.json && \
    chown -R gitagent:gitagent /app && \
    chmod -R 755 /app && \
    chmod -R 755 /github/home && \
    chown -R gitagent:gitagent /github/home || true

# Switch to non-root user
USER gitagent

# Set environment variables
ENV PATH="/opt/venv/bin:/opt/cli-tools/bin:/usr/lib/node_modules/.bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/app \
    CLAUDE_CONFIG_PATH=/app/.claude \
    DISABLE_AUTOUPDATER=1 \
    DISABLE_TELEMETRY=1

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
CMD ["python3", "-m", "gitagent.main"]

# Final production stage
FROM production AS final

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
RUN python3 -c "import gitagent; print('gitagent and dependencies installed successfully')" && \
    codex --version && echo "OpenAI Codex CLI installed successfully" && \
    claude --help && echo "Claude Code installed successfully" && \
    gemini --help && echo "Gemini CLI installed successfully" && \
    echo "Testing Claude CLI config..." && \
    ls -la /app/.claude* && \
    ls -la /github/home/.claude* || true

# Default command
CMD ["python3", "-m", "gitagent.main", "execute-agent"] 