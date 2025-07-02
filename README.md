# GitHub Action Handler

[![CI](https://github.com/tmusk/github-actions/actions/workflows/ci.yml/badge.svg)](https://github.com/tmusk/github-actions/actions/workflows/ci.yml)
[![Docker Publish](https://github.com/tmusk/github-actions/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/tmusk/github-actions/actions/workflows/docker-publish.yml)
[![Security Scan](https://github.com/tmusk/github-actions/actions/workflows/security-scan.yml/badge.svg)](https://github.com/tmusk/github-actions/actions/workflows/security-scan.yml)

A comprehensive GitHub Action for handling and processing all GitHub Action events and triggers. This action provides a Docker-based event handler with extensive logging, monitoring, and notification capabilities.

## 🚀 Features

- **Complete Event Coverage**: Handles all 60+ GitHub Action event types (workflows, issues, PRs, security events, etc.)
- **AI Agent Integration**: Dynamic AI agent discovery and execution with support for multiple AI providers
- **Agent CLI Support**: Integrated support for Codex, Gemini, Claude, and OpenAI CLIs
- **Dynamic Configuration**: YAML-based agent definitions with hierarchical organization by event type
- **Template System**: Jinja2 template support for dynamic prompts with event context
- **Commit History Context**: Automatically includes recent commit history in agent prompts
- **MCP Server Support**: Model Context Protocol integration for enhanced agent capabilities
- **Flexible Output**: Multiple output destinations (console, files, artifacts, comments)
- **Production Ready**: Comprehensive logging, monitoring, health checks, and error handling
- **Security First**: Secure agent execution with environment variable protection
- **Highly Configurable**: Extensive configuration options for all aspects of event processing
- **CLI Management**: Complete CLI for agent discovery, testing, and validation

## 📦 Quick Start

### Basic Usage

```yaml
name: GitHub Event Handler with AI Agents
on: [push, pull_request, issues]

jobs:
  handle-events:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Handle GitHub Events
        uses: tmusk/github-actions@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          log-level: INFO
          # Agent CLI Configuration
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          agents-enabled: true
```

## 🤖 AI Agent System

The GitHub Action Handler supports a powerful AI agent system that allows you to create custom AI-powered responses to GitHub events. Agents are defined using YAML configuration files organized in a hierarchical structure.

### Agent Directory Structure

```
.github/action-handlers/
├── push/                    # Agents for push events
│   ├── claude-reviewer.yml
│   ├── codex-analyzer.yml
│   └── security-scanner.yml
├── pull_request/           # Agents for PR events
│   ├── gemini-analyzer.yml
│   └── claude-merger.yml
├── issues/                 # Agents for issue events
│   └── support-bot.yml
├── security_advisory/      # Agents for security events
│   └── alert-handler.yml
└── all/                   # Agents that run on all events
    └── logger.yml
```

### Agent Configuration

Each agent is defined in a YAML file with the following structure:

```yaml
agent:
  type: "claude"  # Agent type: codex, gemini, claude, custom
  name: "code-reviewer"
  description: "Automated code reviewer"
  version: "1.0.0"

configuration:
  model: "claude-3-sonnet-20241022"
  max_tokens: 4000
  temperature: 0.1

triggers:
  branches: ["main", "develop"]  # Branch patterns (glob)
  tags: ["v*"]                   # Tag patterns (glob)
  paths: ["*.py", "*.js"]        # File patterns (glob)
  event_actions: ["opened"]      # Specific event actions
  conditions:                    # Jinja2 template conditions
    - "{{ event.pull_request.draft == false }}"
    - "{{ commit_history.total_commits > 0 }}"

prompt_template: |
  You are reviewing code changes in {{ github_context.repository }}.
  
  ## Changes
  {% for commit in commit_history.commits[:5] %}
  - {{ commit.message }} ({{ commit.author_name }})
  {% endfor %}
  
  Please provide a detailed review focusing on:
  1. Code quality and best practices
  2. Security vulnerabilities
  3. Performance considerations

mcp_servers:
  - name: "github-server"
    url: "github://api"
    config:
      token: "${GITHUB_TOKEN}"
    enabled: true

output:
  format: "markdown"
  destination: "artifact"  # console, file, artifact, comment, pr_review
  file_path: "review-{{ github_context.sha[:8] }}.md"
  max_length: 5000

enabled: true
priority: 10  # Lower = higher priority
```

### Supported Agent Types

- **Codex**: OpenAI models including Codex (requires `OPENAI_API_KEY`)
- **Gemini**: Google's Gemini AI (requires `GEMINI_API_KEY`)
- **Claude**: Anthropic's Claude AI (requires `CLAUDE_API_KEY`)
- **Custom**: Custom CLI implementation

### Template Variables

Agent prompts have access to rich context through Jinja2 templates:

- `{{ event }}` - Complete GitHub event data
- `{{ github_context }}` - GitHub Action context (repository, ref, actor, etc.)
- `{{ commit_history }}` - Recent commit history with messages and authors
- `{{ agent }}` - Agent configuration and metadata
- `{{ config }}` - Agent-specific configuration

### Output Destinations

- **console**: Print to workflow logs
- **file**: Write to specified file path
- **artifact**: Create GitHub Actions artifact
- **comment**: Post as issue/PR comment (requires GitHub API)
- **pr_review**: Submit as PR review (requires GitHub API)

### CLI Management

The system includes comprehensive CLI commands for agent management:

```bash
# List all discovered agents
python -m github_action_handler agents list

# Test a specific agent configuration
python -m github_action_handler agents test .github/action-handlers/push/claude-reviewer.yml

# Validate all agent configurations
python -m github_action_handler agents validate

# Show agent statistics
python -m github_action_handler agents stats
```

### Advanced Configuration

```yaml
name: Advanced Event Handler with AI Agents
on: [workflow_run, deployment, security_advisory, push, pull_request]

jobs:
  advanced-handler:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Advanced Event Handler
        uses: tmusk/github-actions@v1
        with:
          # Authentication
          github-token: ${{ secrets.GITHUB_TOKEN }}
          
          # Processing Configuration
          log-level: DEBUG
          log-format: json
          max-concurrent-events: 20
          event-timeout: 60
          commit-history-count: 15
          
          # Agent Configuration
          agents-enabled: true
          agents-directory: ".github/action-handlers"
          
          # Agent CLI Configurations
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          
          # Event Filtering
          enabled-events: "push,pull_request,workflow_run,deployment,security_advisory"
          
          # Features
          metrics-enabled: true
          background-tasks: true
          event-storage-enabled: true
```

## 🔧 Configuration Options

### Authentication & Security

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `github-token` | GitHub personal access token | `${{ github.token }}` | No |

### Processing Configuration

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `log-level` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` | No |
| `log-format` | Log format (json, console) | `json` | No |
| `max-concurrent-events` | Maximum concurrent event processing | `10` | No |
| `event-timeout` | Event processing timeout in seconds | `30` | No |
| `background-tasks` | Enable background task processing | `true` | No |
| `commit-history-count` | Number of commits to include in history context | `10` | No |

### Agent Configuration

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `agents-enabled` | Enable AI agent processing | `true` | No |
| `agents-directory` | Directory containing agent configurations | `.github/action-handlers` | No |
| `claude-api-key` | Anthropic Claude API key | `''` | No |
| `gemini-api-key` | Google Gemini API key | `''` | No |
| `openai-api-key` | OpenAI API key (used for Codex agents) | `''` | No |
| `anthropic-api-key` | Alternative Anthropic API key | `''` | No |

### Feature Toggles

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `metrics-enabled` | Enable metrics collection | `true` | No |
| `health-check-enabled` | Enable health check endpoints | `true` | No |
| `structured-logging` | Enable structured logging | `true` | No |
| `event-storage-enabled` | Enable event storage | `false` | No |
| `event-storage-path` | Path to store event data | `/tmp/events` | No |

### Event Configuration

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `enabled-events` | Comma-separated list of enabled event types | `''` (all) | No |
| `disabled-events` | Comma-separated list of disabled event types | `''` | No |

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `processing-result` | JSON result of event processing including agent execution results |
| `agents-discovered` | Number of agents discovered for the event |
| `agents-executed` | Number of agents that were executed |
| `commit-history` | JSON object containing commit history context |
| `artifacts-created` | List of artifacts created by agents |

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
