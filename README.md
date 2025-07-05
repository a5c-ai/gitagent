# gitagent: GitHub Action that executes [AI-GitOps](ARTICLE.md) agents from the prompts in your repo


[![Docker Publish](https://github.com/a5c-ai/gitagent/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/a5c-ai/gitagent/actions/workflows/docker-publish.yml)

gitagent is an intelligent orchestration system for GitHub Actions that seamlessly processes events and triggers AI-powered responses. This advanced platform provides multi-model AI integration, dynamic file handling, and comprehensive GitHub automation with **pre-installed CLI tools for OpenAI Codex, Claude, and Gemini** - no setup required!

## 🚀 Features

- **Single-Agent-Per-Step**: Each workflow step runs one AI agent for maximum clarity and control
- **AI Agent Integration**: Support for Claude, Gemini, OpenAI, and custom AI providers
- **Claude Code SDK**: Advanced integration with file system access and multi-turn conversations
- **Built-in CLI Tools**: Pre-installed Claude, Gemini, and Codex CLI tools
- **GitHub Context**: Automatic access to commit history, file changes, and GitHub event data
- **Template System**: Jinja2 template support for dynamic prompts with event context
- **Commit History Context**: Automatically includes recent commit history in agent prompts
- **Highly Configurable**: Extensive configuration options for all aspects of event processing
- **CLI Management**: Complete CLI for agent discovery, testing, and validation

## 📦 Quick Start

### Basic Code Review Agent

```yaml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]
    paths: ['**.py', '**.js', '**.ts']

jobs:
  code-review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Claude Code Review
        id: claude-review
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'claude'
          agent-name: 'code-reviewer'
          model: 'claude-3-sonnet-20241022'
          
          include-file-content: true
          include-file-diff: true
          
          prompt-template: |
            You are an expert code reviewer. Please review the following changes:
            
            ## Repository: {{ github_context.repository }}
            ## Pull Request: #{{ event.pull_request.number }}
            
            ## Files Changed
            {% for file in files_changed %}
            - **{{ file.filename }}** ({{ file.status }})
            {% endfor %}
            
            Please provide constructive feedback on:
            - Code quality and best practices
            - Potential bugs or security issues
            - Performance considerations
            - Documentation and testing needs
          
          output-file: '/tmp/review.md'
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
      
      - name: Post Review Comment
        if: steps.claude-review.outputs.success == 'true'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const review = fs.readFileSync('/tmp/review.md', 'utf8');
            
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `## 🤖 AI Code Review\n\n${review}`
            });
```

### Security Scanner

```yaml
name: Security Scan
on:
  push:
    branches: [main]
    paths: ['**.py', '**.js', '**.ts']

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Gemini Security Analysis
        id: security-scan
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'gemini'
          agent-name: 'security-scanner'
          model: 'gemini-2.0-flash'
          max-tokens: 3000
          
          include-file-content: true
          
          prompt-template: |
            Analyze the following code changes for security vulnerabilities:
            
            {% for file in files_changed %}
            ## {{ file.filename }}
            ```{{ file.filename.split('.')[-1] }}
            {{ file.content }}
            ```
            {% endfor %}
            
            Report any security issues found. Use "✅ No issues" if clean.
          
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
      
      - name: Create Security Status Check
        uses: actions/github-script@v7
        with:
          script: |
            const output = `${{ steps.security-scan.outputs.output }}`;
            const success = output.includes('✅ No issues');
            
            await github.rest.repos.createCommitStatus({
              owner: context.repo.owner,
              repo: context.repo.repo,
              sha: context.sha,
              state: success ? 'success' : 'failure',
              context: 'Security Scan',
              description: success ? 'No security issues found' : 'Security issues detected'
            });
```

## 🤖 AI Agent Types

### Claude Agents

**Basic Claude Agent:**
```yaml
- name: Claude Analysis
  uses: a5c-ai/gitagent@v1
  with:
    agent-type: 'claude'
    model: 'claude-3-sonnet-20241022'
    prompt-template: |
      Analyze the following code changes...
    claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
```

**Advanced Claude Code SDK Agent:**
```yaml
- name: Advanced Claude Analysis
  uses: a5c-ai/gitagent@v1
  with:
    agent-type: 'claude_code_sdk'
    model: 'claude-3-sonnet-20241022'
    max-tokens: 8000
    max-turns: 10
    permission-mode: 'acceptEdits'
    allowed-tools: 'file_editor,bash'
    
    prompt-template: |
      You are an expert developer with file system access.
      Analyze the codebase and implement improvements...
    
    claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
```

### Gemini Agents

```yaml
- name: Gemini Analysis
  uses: a5c-ai/gitagent@v1
  with:
    agent-type: 'gemini'
    model: 'gemini-2.0-flash'
    prompt-template: |
      Analyze the following code...
    gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
```

### OpenAI Agents

```yaml
- name: OpenAI Analysis
  uses: a5c-ai/gitagent@v1
  with:
    agent-type: 'codex'
    model: 'gpt-4'
    prompt-template: |
      Review the following code...
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

## 🔧 Configuration Options

### Core Configuration

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `agent-type` | Agent type: `claude`, `claude_code_sdk`, `gemini`, `codex`, `custom` | | ✅ |
| `agent-name` | Agent name for identification | `ai-agent` | |
| `model` | AI model to use | | |
| `timeout-seconds` | Timeout for agent execution | `300` | |
| `prompt-template` | Jinja2 prompt template | | ✅ |

### Claude Code SDK Configuration

| Input | Description | Default |
|-------|-------------|---------|
| `max-turns` | Maximum conversation turns | `5` |
| `permission-mode` | Permission mode: `default`, `acceptEdits`, `bypassPermissions`, `plan` | `default` |
| `allowed-tools` | Comma-separated list of allowed tools | |
| `disallowed-tools` | Comma-separated list of disallowed tools | |
| `system-prompt` | System prompt for agent | |
| `output-format` | Output format: `text`, `json`, `stream-json` | `text` |
| `use-bedrock` | Use Amazon Bedrock | `false` |
| `use-vertex` | Use Google Vertex AI | `false` |

### File Context Configuration

| Input | Description | Default |
|-------|-------------|---------|
| `include-file-content` | Include file content in context | `false` |
| `include-file-diff` | Include file diffs in context | `false` |
| `file-diff-context` | Number of context lines for diffs | `3` |

### Output Configuration

| Input | Description | Default |
|-------|-------------|---------|
| `output-file` | File path to write agent output | |
| `output-format-type` | Output format: `text`, `markdown`, `json` | `text` |
| `max-output-length` | Maximum output length | |

### API Keys

| Input | Description |
|-------|-------------|
| `claude-api-key` | Anthropic Claude API key |
| `gemini-api-key` | Google Gemini API key |
| `openai-api-key` | OpenAI API key |
| `anthropic-api-key` | Alternative Anthropic API key |

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `success` | Whether the agent executed successfully |
| `output` | Agent output content |
| `error` | Error message if execution failed |
| `execution-time` | Agent execution time in seconds |
| `agent-name` | Name of the executed agent |
| `agent-type` | Type of the executed agent |
| `model-used` | AI model that was used |
| `tokens-used` | Number of tokens used (if available) |
| `cost-usd` | Estimated cost in USD (if available) |
| `commit-history` | JSON object containing commit history context |
| `files-changed` | JSON array of changed files with content/diffs |
| `github-context` | GitHub Action context information |
| `session-id` | Session ID for Claude Code SDK |
| `turns-used` | Number of conversation turns used |
| `output-file-path` | Path to the output file (if specified) |

## 🎯 Template Variables

Agent prompts have access to rich context through Jinja2 templates:

- `{{ event }}` - Complete GitHub event data
- `{{ github_context }}` - GitHub Action context (repository, ref, actor, etc.)
- `{{ commit_history }}` - Recent commit history with messages and authors
- `{{ files_changed }}` - List of changed files with content and diffs
- `{{ agent }}` - Agent configuration and metadata
- `{{ config }}` - Agent-specific configuration

### Template Examples

**Basic Context:**
```jinja2
Repository: {{ github_context.repository }}
Event: {{ github_context.event_name }}
Actor: {{ github_context.actor }}
Commit: {{ github_context.sha }}
```

**File Changes:**
```jinja2
{% for file in files_changed %}
## {{ file.filename }} ({{ file.status }})
- Lines added: {{ file.additions }}
- Lines removed: {{ file.deletions }}

{% if file.content %}
### Content:
{{ file.content }}
{% endif %}
{% endfor %}
```

**Commit History:**
```jinja2
Recent commits:
{% for commit in commit_history.commits %}
- {{ commit.sha[:8] }}: {{ commit.message }} ({{ commit.author_name }})
{% endfor %}
```

## 🔥 Advanced Examples

### Multi-Step Analysis Workflow

```yaml
name: Comprehensive Analysis
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      # Step 1: Security analysis
      - name: Security Analysis
        id: security
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'claude'
          agent-name: 'security-analyzer'
          model: 'claude-3-sonnet-20241022'
          include-file-content: true
          prompt-template: |
            Perform security analysis of the code changes...
          output-file: '/tmp/security-report.json'
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
      
      # Step 2: Code quality analysis
      - name: Quality Analysis
        id: quality
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'gemini'
          agent-name: 'quality-analyzer'
          model: 'gemini-2.0-flash'
          include-file-content: true
          prompt-template: |
            Analyze code quality and best practices...
          output-file: '/tmp/quality-report.json'
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
      
      # Step 3: Synthesis
      - name: Synthesis Review
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'claude_code_sdk'
          agent-name: 'review-synthesizer'
          model: 'claude-3-sonnet-20241022'
          max-turns: 5
          permission-mode: 'acceptEdits'
          prompt-template: |
            Synthesize the following analysis reports:
            
            Security Report: {{ include('/tmp/security-report.json') }}
            Quality Report: {{ include('/tmp/quality-report.json') }}
            
            Create a comprehensive review...
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
```

### Conditional Agent Execution

```yaml
name: Smart Issue Processing
on:
  issues:
    types: [opened]

jobs:
  process-issue:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Bug Report Handler
        if: contains(github.event.issue.labels.*.name, 'bug')
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'claude_code_sdk'
          agent-name: 'bug-handler'
          model: 'claude-3-sonnet-20241022'
          max-turns: 10
          permission-mode: 'acceptEdits'
          allowed-tools: 'file_editor,bash'
          
          prompt-template: |
            Process this bug report and implement a fix:
            
            **Issue:** {{ event.issue.title }}
            **Description:** {{ event.issue.body }}
            
            Steps:
            1. Analyze the bug report
            2. Locate the issue in the codebase
            3. Implement a fix
            4. Create tests
            5. Commit changes
          
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
      
      - name: Feature Request Handler
        if: contains(github.event.issue.labels.*.name, 'enhancement')
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'gemini'
          agent-name: 'feature-handler'
          model: 'gemini-2.0-flash'
          
          prompt-template: |
            Analyze this feature request:
            
            **Request:** {{ event.issue.title }}
            **Description:** {{ event.issue.body }}
            
            Provide implementation recommendations...
          
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
```

## 🚀 Built-in CLI Tools

The Docker image includes pre-installed CLI tools for all supported AI providers:

- **Claude CLI** (`claude`) - Direct access to Claude models
- **Gemini CLI** (`gemini`) - Google Gemini integration
- **OpenAI CLI** (`codex`) - OpenAI and Codex models

### CLI vs SDK Comparison

| Feature | Claude CLI | Claude Code SDK |
|---------|------------|----------------|
| **Performance** | Good | Excellent |
| **Configuration** | Basic | Advanced |
| **Multi-turn Support** | No | Yes |
| **File System Access** | Limited | Full |
| **Tool Control** | Basic | Fine-grained |
| **Cost Tracking** | No | Yes |
| **Use Case** | Simple prompts | Complex workflows |

## 🔒 Security

- **API Key Management**: Secure handling of API keys through GitHub Secrets
- **Sandboxed Execution**: Agents run in isolated Docker containers
- **Permission Control**: Fine-grained tool permissions for Claude Code SDK
- **Input Validation**: All inputs are validated and sanitized

## 📊 Best Practices

1. **Use descriptive agent names** for easy identification in logs
2. **Store outputs in files** for multi-step workflows
3. **Set appropriate timeouts** to prevent hanging executions
4. **Use conditional execution** to optimize performance
5. **Monitor token usage** and costs for production usage
6. **Test agents individually** before chaining them together
7. **Use specific models** rather than defaults for consistent results

## 🤝 Migration from Old Format

If you're migrating from the old `.github/action-handlers/` approach:

1. **Convert trigger rules** to GitHub workflow conditions
2. **Move agent configuration** to workflow step inputs
3. **Replace output destinations** with subsequent workflow steps
4. **Update branch automation** to use git commands in workflow steps

See [examples/new-format-examples.md](examples/new-format-examples.md) for detailed migration examples.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude AI
- [Google](https://ai.google/) for Gemini AI
- [OpenAI](https://openai.com/) for GPT models
- [GitHub](https://github.com/) for the Actions platform

---

<p align="center">
  <strong>Built with ❤️ for AI-powered development workflows</strong>
</p>
