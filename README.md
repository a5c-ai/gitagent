# GitHub Action Handler

[![CI](https://github.com/tmusk/github-actions/actions/workflows/ci.yml/badge.svg)](https://github.com/tmusk/github-actions/actions/workflows/ci.yml)
[![Docker Publish](https://github.com/tmusk/github-actions/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/tmusk/github-actions/actions/workflows/docker-publish.yml)
[![Security Scan](https://github.com/tmusk/github-actions/actions/workflows/security-scan.yml/badge.svg)](https://github.com/tmusk/github-actions/actions/workflows/security-scan.yml)

A comprehensive GitHub Action for handling and processing all GitHub Action events and triggers. This action provides a Docker-based event handler with extensive logging, monitoring, and notification capabilities.

## 🚀 Features

- **Complete Event Coverage**: Handles all 60+ GitHub Action event types (workflows, issues, PRs, security events, etc.)
- **Docker-based**: Runs as a containerized service with multi-architecture support
- **Production Ready**: Comprehensive logging, monitoring, health checks, and error handling
- **Security First**: Webhook signature verification, rate limiting, and security event detection
- **Highly Configurable**: Extensive configuration options for all aspects of event processing
- **Notification Support**: Built-in Slack and Discord webhook integrations
- **Metrics & Monitoring**: Prometheus metrics, health checks, and detailed statistics
- **Event Storage**: Optional persistent event storage and analysis
- **Background Processing**: Concurrent event processing with timeout protection

## 📦 Quick Start

### Basic Usage

```yaml
name: GitHub Event Handler
on: [push, pull_request, issues]

jobs:
  handle-events:
    runs-on: ubuntu-latest
    steps:
      - name: Handle GitHub Events
        uses: tmusk/github-actions@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          webhook-secret: ${{ secrets.WEBHOOK_SECRET }}
          log-level: INFO
```

### Advanced Configuration

```yaml
name: Advanced Event Handler
on: [workflow_run, deployment, security_advisory]

jobs:
  advanced-handler:
    runs-on: ubuntu-latest
    steps:
      - name: Advanced Event Handler
        uses: tmusk/github-actions@v1
        with:
          # Authentication
          github-token: ${{ secrets.GITHUB_TOKEN }}
          webhook-secret: ${{ secrets.WEBHOOK_SECRET }}
          
          # Server Configuration
          port: 8080
          log-level: DEBUG
          log-format: json
          
          # Processing Configuration
          max-concurrent-events: 20
          event-timeout: 60
          webhook-signature-required: true
          
          # Features
          rate-limit-enabled: true
          rate-limit-requests: 200
          metrics-enabled: true
          background-tasks: true
          event-storage-enabled: true
          
          # Event Filtering
          enabled-events: "workflow_run,deployment,security_advisory"
          notification-events: "security_advisory,vulnerability_alert"
          
          # Notifications
          slack-webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
          discord-webhook-url: ${{ secrets.DISCORD_WEBHOOK_URL }}
```

## 🔧 Configuration Options

### Authentication & Security

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `github-token` | GitHub personal access token | `${{ github.token }}` | No |
| `webhook-secret` | GitHub webhook secret for signature verification | `''` | No |
| `webhook-signature-required` | Require webhook signature verification | `true` | No |

### Server Configuration

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `port` | Port to run the handler on | `8000` | No |
| `log-level` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` | No |
| `log-format` | Log format (json, console) | `json` | No |

### Processing Configuration

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `max-concurrent-events` | Maximum concurrent event processing | `10` | No |
| `event-timeout` | Event processing timeout in seconds | `30` | No |
| `background-tasks` | Enable background task processing | `true` | No |

### Feature Toggles

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `rate-limit-enabled` | Enable rate limiting | `true` | No |
| `rate-limit-requests` | Rate limit requests per minute | `100` | No |
| `metrics-enabled` | Enable metrics collection | `true` | No |
| `health-check-enabled` | Enable health check endpoints | `true` | No |
| `structured-logging` | Enable structured logging | `true` | No |

### Event Configuration

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `enabled-events` | Comma-separated list of enabled event types | `''` (all) | No |
| `disabled-events` | Comma-separated list of disabled event types | `''` | No |
| `event-storage-enabled` | Enable event storage | `false` | No |
| `event-storage-path` | Path to store event data | `/app/data/events` | No |

### Notifications

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `slack-webhook-url` | Slack webhook URL for notifications | `''` | No |
| `discord-webhook-url` | Discord webhook URL for notifications | `''` | No |
| `notification-events` | Events that trigger notifications | `security_advisory,vulnerability_alert` | No |

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `container-url` | URL of the running container |
| `container-id` | ID of the running container |
| `health-status` | Health status of the handler |

## 🎯 Supported Events

The handler supports all GitHub Action event types:

### Workflow Events
- `workflow_run` - Workflow run completed
- `workflow_job` - Workflow job completed
- `workflow_dispatch` - Manual workflow trigger

### Code Events
- `push` - Code pushed to repository
- `pull_request` - Pull request events
- `pull_request_review` - PR review events
- `pull_request_review_comment` - PR review comment events
- `commit_comment` - Commit comment events

### Issue & Project Events
- `issues` - Issue events
- `issue_comment` - Issue comment events
- `project` - Project events
- `project_card` - Project card events
- `project_column` - Project column events

### Repository Events
- `create` - Branch/tag creation
- `delete` - Branch/tag deletion
- `fork` - Repository forked
- `star` - Repository starred
- `watch` - Repository watched
- `repository` - Repository settings changed

### Security Events
- `security_advisory` - Security advisory published
- `vulnerability_alert` - Vulnerability alert
- `code_scanning_alert` - Code scanning alert
- `secret_scanning_alert` - Secret scanning alert

### Deployment Events
- `deployment` - Deployment created
- `deployment_status` - Deployment status changed
- `environment` - Environment events

### Team & Organization Events
- `member` - Organization member events
- `membership` - Team membership events
- `organization` - Organization events
- `team` - Team events
- `team_add` - Repository added to team

### App Events
- `installation` - GitHub App installation
- `installation_repositories` - App repository access
- `marketplace_purchase` - GitHub Marketplace events

And many more! See the [GitHub Events documentation](https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads) for complete details.

## 🚀 API Endpoints

Once running, the handler exposes several endpoints:

### Core Endpoints
- `POST /webhook` - Main webhook endpoint for GitHub events
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health check with system metrics

### Information Endpoints
- `GET /events/supported` - List all supported event types
- `GET /events/structure/{event_type}` - Get event structure documentation
- `GET /stats` - Processing statistics
- `GET /config` - Current configuration (sanitized)

### Monitoring Endpoints
- `GET /metrics` - Prometheus metrics (if enabled)

## 🏗️ Development

### Prerequisites

- Python 3.11+
- Docker
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/tmusk/github-actions.git
   cd github-actions
   ```

2. **Set up development environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -e ".[dev]"
   ```

3. **Run tests**
   ```bash
   pytest
   ```

4. **Code formatting and linting**
   ```bash
   black src/ tests/
   isort src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

### Docker Development

1. **Build the image**
   ```bash
   docker build -t github-action-handler .
   ```

2. **Run locally**
   ```bash
   docker run -p 8000:8000 \
     -e GITHUB_TOKEN=your_token \
     -e LOG_LEVEL=DEBUG \
     github-action-handler
   ```

3. **Test the endpoints**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/events/supported
   ```

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=src/github_action_handler

# Specific test file
pytest tests/test_event_handler.py -v
```

## 🔒 Security

### Webhook Signature Verification

The handler verifies GitHub webhook signatures using HMAC-SHA256:

```python
# Automatic signature verification
signature = request.headers.get("X-Hub-Signature-256")
is_valid = verify_signature(payload, signature, webhook_secret)
```

### Security Features

- **Signature Verification**: All webhooks are verified against the configured secret
- **Rate Limiting**: Configurable rate limiting to prevent abuse
- **Input Validation**: All inputs are validated using Pydantic models
- **Secure Defaults**: Security-first configuration defaults
- **Security Event Detection**: Automatic detection and notification of security events

### Security Events

The handler automatically monitors and can notify on:
- Security advisories
- Vulnerability alerts
- Code scanning alerts
- Secret scanning alerts
- Suspicious activity patterns

## 📊 Monitoring & Observability

### Logging

Structured logging with configurable formats:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "event_type": "pull_request",
  "repository": "owner/repo",
  "action": "opened",
  "processing_time": 0.145,
  "message": "Successfully processed pull_request event"
}
```

### Metrics

When metrics are enabled, the handler exposes Prometheus metrics:

- `github_events_total` - Total events processed
- `github_events_duration_seconds` - Event processing duration
- `github_events_errors_total` - Processing errors
- `github_webhook_requests_total` - Webhook requests received

### Health Checks

- **Basic Health Check** (`/health`): Simple up/down status
- **Detailed Health Check** (`/health/detailed`): System metrics, memory usage, uptime

## 🔧 Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   # Check logs
   docker logs github-action-handler-<run-id>
   
   # Verify configuration
   curl http://localhost:8000/config
   ```

2. **Webhook signature verification fails**
   - Ensure `webhook-secret` matches your GitHub webhook configuration
   - Check that `webhook-signature-required` is set correctly

3. **Events not being processed**
   - Verify `enabled-events` and `disabled-events` configuration
   - Check the `/events/supported` endpoint
   - Review logs for processing errors

4. **Performance issues**
   - Adjust `max-concurrent-events` and `event-timeout`
   - Monitor `/metrics` endpoint for bottlenecks
   - Check system resources with `/health/detailed`

### Debug Mode

Enable debug logging for detailed troubleshooting:

```yaml
- uses: tmusk/github-actions@v1
  with:
    log-level: DEBUG
    log-format: console
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

### Code Quality

All contributions must pass:
- Unit and integration tests
- Code formatting (Black, isort)
- Linting (Flake8, MyPy)
- Security scanning (Bandit, Safety)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- [structlog](https://www.structlog.org/) for structured logging
- [GitHub](https://github.com/) for the comprehensive webhook system

## 📞 Support

- 📖 [Documentation](https://github.com/tmusk/github-actions/wiki)
- 🐛 [Issue Tracker](https://github.com/tmusk/github-actions/issues)
- 💬 [Discussions](https://github.com/tmusk/github-actions/discussions)
- 📧 [Email Support](mailto:support@example.com)

---

<p align="center">
  <strong>Built with ❤️ for the GitHub community</strong>
</p>
