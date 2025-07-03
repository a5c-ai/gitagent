# gitagent: GitHub Action that executes [AI-GitOps](ARTICLE.md) agents from the prompts in your repo

[![Docker Publish](https://github.com/a5c-ai/gitagent/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/a5c-ai/gitagent/actions/workflows/docker-publish.yml)

gitagent is an intelligent orchestration system for GitHub Actions that seamlessly processes events and triggers AI-powered responses. This advanced platform provides multi-model AI integration, dynamic file handling, and comprehensive GitHub automation with **pre-installed CLI tools for OpenAI Codex, Claude, and Gemini** - no setup required!

## 🚀 Features

- **Complete Event Coverage**: Handles all 60+ GitHub Action event types (workflows, issues, PRs, security events, etc.)
- **AI Agent Integration**: Dynamic AI agent discovery and execution with support for multiple AI providers
- **Agent CLI Support**: Integrated support for Codex, Gemini, Claude, and OpenAI CLIs
- **Dynamic Configuration**: YAML-based agent definitions with hierarchical organization by event type
- **Template System**: Jinja2 template support for dynamic prompts with event context
- **Commit History Context**: Automatically includes recent commit history in agent prompts
- **Highly Configurable**: Extensive configuration options for all aspects of event processing
- **CLI Management**: Complete CLI for agent discovery, testing, and validation

## 📦 Quick Start

### Basic Usage

```yaml
name: gitagent Intelligent Event Orchestration
on: [push, pull_request, issues]

jobs:
  handle-events:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: gitagent Orchestration
        uses: a5c-ai/gitagent@v1
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

gitagent features a powerful AI agent system that allows you to create custom AI-powered responses to GitHub events. Agents are defined using YAML configuration files organized in a hierarchical structure.

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
  executable: "claude"  # Built-in CLI tool (no path required)

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
  
  # File-specific change monitoring
  files_changed: ["src/*.py", "docs/*.md"]  # Specific file patterns that must have changed
  include_file_content: true      # Include file content in template variables
  include_file_diff: true         # Include file diffs in template variables
  file_diff_context: 3           # Number of context lines for diffs

prompt_template: |
  You are an expert code reviewer with direct file system access. You can read and analyze files in the repository to provide comprehensive reviews.
  
  ## Repository Context
  - **Repository:** {{ github_context.repository }}
  - **Workspace:** {{ github_context.workspace }}
  - **Event:** {{ github_context.event_name }}
  - **Commit:** {{ github_context.sha }}
  
  ## Files to Review
  {% for file in files_changed %}
  - **{{ file.filename }}** ({{ file.status }})
  {% endfor %}
  
  ## Your File-Based Review Workflow
  
  1. **Read Files Directly:**
     {% for file in files_changed %}
     - Read and analyze: `{{ file.filename }}`
     {% endfor %}
     - Examine complete file context, not just changes
     - Look at related files and dependencies
  
  2. **Comprehensive Analysis:**
     - Code quality and best practices
     - Security vulnerabilities and risks
     - Performance considerations and optimizations
     - Testing coverage and documentation
  
  3. **Write Review Report:**
     - Create detailed review: `code-reviews/review-{{ github_context.sha[:8] }}.md`
     - Include specific findings and recommendations
     - Provide actionable feedback for developers
  
  4. **Generate Status Check:**
     - Write concise status to: `/tmp/code-review-status.md`
     - Include overall assessment and key findings
  
  ## Important Notes
  - You have full read access to analyze all repository files
  - Create the `code-reviews/` directory if needed
  - Focus on providing constructive, actionable feedback

mcp_servers:
  - name: "mcp-server"
    url: "https://remote.mcp.dev/sse"
    config:
      token: "${GITHUB_TOKEN}"
    enabled: true

output:
  format: "markdown"
  destination: "status_check"  # console, file, artifact, comment, pr_review, status_check, create_issue
  output_file: "/tmp/code-review-status.md"  # Agent writes status check content here
  file_path: "review-{{ github_context.sha[:8] }}.md"
  max_length: 5000
  
  # Status check configuration
  status_check_name: "AI Code Review"
  status_check_success_on: ["✅", "LGTM", "approved", "passed"]
  status_check_failure_on: ["❌", "failed", "error", "rejected"]
  
  # Comment configuration (agent writes to separate file)
  comment_on_success: true
  comment_on_failure: true
  comment_output_file: "/tmp/code-review-comment.md"  # Agent writes comment content here
  comment_template: |
    ## 🤖 AI Code Review by {{ agent.name }}
    
    {{ comment_output_content }}
    
    ---
    *Generated automatically for commit {{ github_context.sha[:8] }}*
  
  # Issue creation configuration (agent writes content to output_file)
  issue_title_template: "🐛 Code Review Issue: {{ github_context.ref }}"
  issue_labels: ["ai-review", "automated", "code-quality"]
  issue_assignees: ["maintainer-username"]

# Branch automation for automatic fixes
branch_automation:
  enabled: true                   # Enable branch automation
  branch_prefix: "auto-fix"       # Prefix for created branches
  commit_message: "🤖 Automated fixes by {{ agent.name }}"  # Commit message template
  create_pull_request: true       # Create PR after pushing branch
  pr_title: "🤖 Automated Code Review Fixes"  # PR title template
  pr_body: |                      # PR description template
    Automated fixes generated by {{ agent.name }}.
    
    Changes made:
    {% for file in files_changed %}
    - {{ file.filename }}
    {% endfor %}
  pr_labels: ["automation", "code-review"]  # Labels for the PR
  pr_assignees: []                # Assignees for the PR
  pr_reviewers: []                # Reviewers for the PR
  target_branch: "main"           # Target branch for PR
  delete_branch_on_merge: true    # Delete branch when PR is merged

enabled: true
priority: 10  # Lower = higher priority
```

### Supported Agent Types

- **Codex**: OpenAI models including Codex (requires `OPENAI_API_KEY`) - Uses built-in `codex` CLI
- **Gemini**: Google's Gemini AI (requires `GEMINI_API_KEY`) - Uses built-in `gemini` CLI
- **Claude**: Anthropic's Claude AI (requires `CLAUDE_API_KEY`) - Uses built-in `claude` CLI
- **Claude Code SDK**: Advanced Claude integration with direct Python SDK access (requires `CLAUDE_API_KEY`) - Uses Claude Code SDK for enhanced capabilities
- **Custom**: Custom CLI implementation

### Built-in CLI Tools

The Docker image includes pre-installed CLI tools for all supported AI providers:

- **OpenAI Codex CLI** (`codex`)
- **Claude Code** (`claude`)
- **Gemini CLI** (`gemini`)

These tools are available system-wide and can be used directly in agent configurations without specifying executable paths.

### Template Variables

Agent prompts have access to rich context through Jinja2 templates:

- `{{ event }}` - Complete GitHub event data
- `{{ github_context }}` - GitHub Action context (repository, ref, actor, etc.)
- `{{ commit_history }}` - Recent commit history with messages and authors
- `{{ files_changed }}` - List of changed files with content and diffs (if enabled)
- `{{ agent }}` - Agent configuration and metadata
- `{{ config }}` - Agent-specific configuration

#### File Change Variables

When `files_changed` triggers are used, each file object contains:

- `filename` - Path to the changed file
- `status` - Change type: "added", "modified", "removed"
- `additions` - Number of lines added
- `deletions` - Number of lines deleted
- `content` - Current file content (if `include_file_content: true`)
- `patch` - Unified diff patch (if `include_file_diff: true`)
- `content_before` - File content before changes
- `content_after` - File content after changes

### File-Specific Change Monitoring

Agents can be configured to only run when specific files are changed:

```yaml
triggers:
  # Run only when markdown files in specific directories change
  files_changed: ["docs/*.md", "README.md", "bug-reports/*.md"]
  include_file_content: true    # Include full file content
  include_file_diff: true       # Include diff patches
  file_diff_context: 5         # Lines of context around changes
```

This enables powerful workflows like:
- **Documentation fixes**: Auto-fix markdown formatting when docs are updated
- **Code quality**: Run linters/formatters on specific file types
- **Security scans**: Analyze security-sensitive files when modified
- **Bug processing**: Auto-process bug reports in specific directories

Example use case: Run a markdown formatter only on `.md` files in the `bug-reports/` directory, automatically fixing formatting issues and creating a PR with the fixes.

### Output Destinations

- **console**: Print to workflow logs
- **file**: Write to specified file path
- **artifact**: Create GitHub Actions artifact
- **comment**: Post as issue/PR comment (requires GitHub API)
- **pr_review**: Submit as PR review (requires GitHub API)
- **status_check**: Post GitHub status check on commits
- **create_issue**: Create new GitHub issue with agent results

### File-Based Agent Workflow

All agents now support a **file-based workflow** where they can directly read, analyze, and modify repository files:

#### Agent Capabilities
- **Direct File Access**: Agents can read any file in the repository workspace
- **File Modification**: Agents can create, update, or delete files as needed
- **Repository Exploration**: Agents can examine the entire codebase structure
- **Output Files**: Agents write their results to temporary files that are then processed

#### File-Based Output Configuration

```yaml
output:
  destination: "status_check"
  output_file: "/tmp/agent-output.md"        # Agent writes main output here
  comment_output_file: "/tmp/comment.md"     # Agent writes comment content here
  
  # Traditional template (reads from output_file if specified)
  comment_template: |
    ## Agent Results
    {{ comment_output_content }}
```

#### Agent Instructions
Agents are instructed to:
1. **Read input files directly** from the repository (e.g., markdown bug reports)
2. **Explore the codebase** to understand context and dependencies
3. **Make actual code changes** when implementing fixes
4. **Write structured reports** to the repository for audit trails
5. **Write communication outputs** to `/tmp/` files for GitHub integration

### Advanced Template File Inclusion

The action supports powerful **file inclusion** capabilities in agent templates, allowing dynamic inclusion of documentation, configuration files, and other content based on changed files and directory structure.

#### Template Functions

Use the `include()` function in templates to dynamically include file content:

```yaml
prompt_template: |
  ## Project Documentation
  {{ include("README.md") }}
  {{ include(".github/CONTRIBUTING.md") }}
  
  ## Directory-Specific Instructions
  {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS_AND_THEIR_ANCESTORS/.instructions.md") }}
  
  ## Configuration Files
  {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/**/config.yml") }}
  {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/**/settings.json") }}
```

#### Special Variables

Templates have access to special path variables that resolve based on changed files:

- **`$WORKSPACE`** - Repository root directory
- **`$ALL_UNIQUE_CHANGED_FILE_DIRS`** - Directories containing changed files
- **`$ALL_UNIQUE_CHANGED_FILE_DIRS_AND_THEIR_ANCESTORS`** - Above + all parent directories up to root
- **`$CHANGED_FILES`** - List of changed file paths

#### Wildcard Patterns

Support for glob patterns and recursive matching:

```yaml
# Include all markdown files in changed directories
{{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/**/*.md") }}

# Include specific instruction files from any subdirectory
{{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS_AND_THEIR_ANCESTORS/**/instructions-*.md") }}

# Include configuration files relative to changed file locations
{{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/.config/*") }}
```

#### Example Use Cases

1. **Context-Aware Code Review:**
   ```yaml
   prompt_template: |
     ## Coding Standards for Changed Areas
     {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS_AND_THEIR_ANCESTORS/.coding-standards.md") }}
     
     ## Test Guidelines
     {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/**/testing-guide.md") }}
   ```

2. **Dynamic Documentation Inclusion:**
   ```yaml
   prompt_template: |
     ## Relevant Documentation
     {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/**/README.md") }}
     {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/**/*.md") }}
   ```

3. **Configuration Context:**
   ```yaml
   prompt_template: |
     ## Project Configuration
     {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/**/config.yml") }}
     {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/**/.env.example") }}
   ```

This enables agents to automatically access relevant project documentation, coding standards, and configuration files based on which files are being modified, providing rich context for analysis and decision-making.

### GitHub Integration Features

The action provides advanced GitHub integration capabilities:

#### Status Checks
Agents can post status checks to commits based on their analysis results:

```yaml
output:
  destination: "status_check"
  status_check_name: "Security Scan"
  status_check_success_on: ["✅ No issues found", "PASSED", "CLEAN"]
  status_check_failure_on: ["❌ Vulnerabilities found", "FAILED", "CRITICAL"]
```

Status checks support automatic success/failure detection based on keywords in the agent output. The status check will appear in the GitHub UI alongside other CI checks.

#### Smart Comments
Agents can post intelligent comments on PRs and issues:

```yaml
output:
  destination: "comment"
  comment_template: |
    ## 🤖 {{ agent.name }} Analysis
    
    **Event:** {{ github_context.event_name }}
    **Files:** {{ files_changed | length }} changed
    
    ### Results
    {{ output }}
    
    {% if files_changed %}
    ### Files Analyzed
    {% for file in files_changed %}
    - `{{ file.filename }}` ({{ file.additions }}+ {{ file.deletions }}-)
    {% endfor %}
    {% endif %}
```

Comments are automatically posted to the relevant PR or issue based on the triggering event.

#### Issue Creation
Agents can create new issues to track problems or recommendations:

```yaml
output:
  destination: "create_issue"
  issue_title_template: "🚨 {{ agent.name }}: {{ github_context.ref }}"
  issue_body_template: |
    ## Automated Issue Report
    
    **Triggered by:** {{ github_context.event_name }}
    **Repository:** {{ github_context.repository }}
    **Commit:** {{ github_context.sha }}
    
    {{ output }}
  issue_labels: ["automation", "needs-review"]
  issue_assignees: ["team-lead"]
```

### Branch Automation

Agents can automatically create branches, commit changes, and open pull requests:

```yaml
branch_automation:
  enabled: true
  branch_prefix: "auto-fix"
  commit_message: "🤖 Fix by {{ agent.name }}: {{ ', '.join([f.filename for f in files_changed]) }}"
  
  create_pull_request: true
  pr_title: "🤖 Automated fixes from {{ agent.name }}"
  pr_body: |
    ## Automated Changes
    
    This PR contains automated changes generated by {{ agent.name }}.
    
    ### Files Modified
    {% for file in files_changed %}
    - `{{ file.filename }}` ({{ file.status }})
    {% endfor %}
    
    **Event:** {{ github_context.event_name }}
    **Branch:** {{ github_context.ref }}
  
  pr_labels: ["automation", "ai-generated"]
  pr_assignees: ["maintainer-username"]
  pr_reviewers: ["reviewer-username"]
  target_branch: "main"
  delete_branch_on_merge: true
```

When branch automation is enabled:

1. **Branch Creation**: A new branch is created with the specified prefix and random suffix
2. **Changes Applied**: Agent output is written to files in the repository
3. **Commit**: Changes are committed with the templated message
4. **Push**: The branch is pushed to the remote repository
5. **Pull Request**: Optionally creates a PR with templated title and description
6. **Output Variables**: Returns branch name, PR number, and PR URL

### CLI Tool Configuration

With the built-in CLI tools, you can simplify your agent configurations:

```yaml
# Simplified OpenAI Codex agent
agent:
  type: "codex"
  name: "code-assistant"
  executable: "codex"  # No path required - built into container

# Simplified Claude agent  
agent:
  type: "claude"
  name: "claude-reviewer"
  executable: "claude"  # No path required - built into container

# Simplified Gemini agent
agent:
  type: "gemini" 
  name: "gemini-analyzer"
  executable: "gemini"  # No path required - built into container
```

The built-in CLI tools support all standard command-line arguments and can be configured with appropriate API keys through environment variables.

### Claude Code SDK Integration

gitagent now includes **advanced Claude Code SDK integration** that provides superior capabilities compared to the CLI approach:

#### Benefits of Claude Code SDK

✅ **Direct Python SDK Integration** - No subprocess overhead, better performance  
✅ **Structured Message Handling** - Access to rich message types and metadata  
✅ **Multi-turn Conversations** - Session management for complex workflows  
✅ **Advanced Configuration** - Fine-grained control over tools and permissions  
✅ **Better Error Handling** - Detailed error information and recovery  
✅ **Cost Tracking** - Built-in usage and cost monitoring  
✅ **MCP Support** - Native Model Context Protocol integration  

#### Claude Code SDK Agent Configuration

```yaml
agent:
  type: "claude_code_sdk"  # Use the advanced SDK integration
  name: "claude-code-reviewer"
  description: "Advanced Claude Code SDK agent with enhanced capabilities"
  version: "1.0.0"

configuration:
  model: "claude-3-sonnet-20241022"
  max_tokens: 4000
  temperature: 0.1
  max_turns: 10                    # Multi-turn conversation support
  system_prompt: "You are an expert code reviewer..."
  append_system_prompt: "Always provide constructive feedback."
  output_format: "text"            # Options: text, json, stream-json
  permission_mode: "acceptEdits"   # Options: default, acceptEdits, bypassPermissions, plan
  use_bedrock: false               # Use Amazon Bedrock instead of Anthropic API
  use_vertex: false                # Use Google Vertex AI instead of Anthropic API
  
  # Tool Configuration
  allowed_tools: ["file_editor", "bash", "computer"]
  disallowed_tools: ["web_search"]
  
  # MCP Configuration
  mcp_config_path: ".claude/mcp_config.json"

triggers:
  files_changed: ["*.py", "*.js", "*.ts"]
  include_file_content: true
  include_file_diff: true

prompt_template: |
  You are an expert code reviewer with full file system access through the Claude Code SDK.
  
  ## Repository Context
  - **Repository:** {{ github_context.repository }}
  - **Event:** {{ github_context.event_name }}
  - **Files Changed:** {{ files_changed | length }}
  
  ## Enhanced Capabilities
  With the Claude Code SDK, you can:
  - Read and analyze any file in the repository
  - Execute bash commands for testing
  - Create and modify files directly
  - Access structured project information
  - Maintain conversation context across turns
  
  ## Files to Review
  {% for file in files_changed %}
  - **{{ file.filename }}** ({{ file.status }})
  {% endfor %}
  
  Please provide a comprehensive code review with specific recommendations.

output:
  destination: "comment"
  comment_template: |
    ## 🚀 Claude Code SDK Review
    
    **Session ID:** {{ session_id }}
    **Turns:** {{ num_turns }}
    **Cost:** ${{ total_cost_usd }}
    
    {{ output }}
    
    ---
    *Powered by Claude Code SDK*

enabled: true
```

#### Key Features of Claude Code SDK Integration

1. **Session Management**: Maintains conversation state across multiple interactions
2. **Rich Metadata**: Access to cost tracking, timing, and session information
3. **Advanced Permissions**: Fine-grained control over tool usage and file access
4. **Multi-Provider Support**: Works with Anthropic API, Amazon Bedrock, or Google Vertex AI
5. **Structured Output**: Support for JSON and streaming JSON response formats
6. **MCP Integration**: Native support for Model Context Protocol servers

#### Configuration Options

The Claude Code SDK agent supports extensive configuration options:

```yaml
configuration:
  # Model Configuration
  model: "claude-3-sonnet-20241022"     # Claude model to use
  max_tokens: 4000                      # Maximum response tokens
  temperature: 0.1                      # Response randomness (0.0-1.0)
  timeout_seconds: 300                  # Request timeout
  
  # Conversation Management
  max_turns: 10                         # Maximum conversation turns
  system_prompt: "Custom system prompt"
  append_system_prompt: "Additional instructions"
  
  # Output Format
  output_format: "text"                 # text, json, stream-json
  
  # Tool Management
  allowed_tools: ["file_editor", "bash"]
  disallowed_tools: ["web_search"]
  permission_mode: "acceptEdits"        # default, acceptEdits, bypassPermissions, plan
  
  # Provider Configuration
  use_bedrock: false                    # Use Amazon Bedrock
  use_vertex: false                     # Use Google Vertex AI
  
  # MCP Configuration
  mcp_config_path: ".claude/mcp_config.json"
  
  # Working Directory
  cwd: "/workspace"                     # Custom working directory
```

#### Usage Examples

**Basic Code Review Agent:**
```yaml
agent:
  type: "claude_code_sdk"
  name: "code-reviewer"

configuration:
  model: "claude-3-sonnet-20241022"
  max_tokens: 4000
  permission_mode: "acceptEdits"
  allowed_tools: ["file_editor"]
```

**Advanced Multi-Turn Agent:**
```yaml
agent:
  type: "claude_code_sdk"
  name: "interactive-assistant"

configuration:
  max_turns: 20
  system_prompt: "You are a helpful coding assistant."
  permission_mode: "bypassPermissions"
  output_format: "json"
  use_bedrock: true
```

**Secure Analysis Agent:**
```yaml
agent:
  type: "claude_code_sdk"
  name: "security-analyzer"

configuration:
  permission_mode: "default"
  disallowed_tools: ["bash", "computer"]
  allowed_tools: ["file_editor"]
  max_turns: 5
```

#### Claude CLI vs Claude Code SDK Comparison

Choose the right Claude integration for your needs:

| Feature | Claude CLI | Claude Code SDK |
|---------|------------|----------------|
| **Performance** | Good | Excellent (no subprocess overhead) |
| **Configuration** | Basic | Advanced (fine-grained control) |
| **Error Handling** | Standard | Rich error information |
| **Cost Tracking** | None | Built-in usage monitoring |
| **Multi-turn Support** | No | Yes (session management) |
| **Tool Control** | Limited | Fine-grained permissions |
| **Output Formats** | Text only | Text, JSON, streaming JSON |
| **Provider Support** | Anthropic API | Anthropic API, Bedrock, Vertex AI |
| **MCP Integration** | No | Native support |
| **Setup Complexity** | Simple | Moderate |
| **Use Case** | Simple prompts | Complex workflows |

**When to use Claude CLI:**
- Simple prompt/response interactions
- Basic code review tasks
- Quick prototyping
- Minimal configuration needs

**When to use Claude Code SDK:**
- Complex multi-step workflows
- Need for session management
- Advanced tool usage control
- Cost tracking requirements
- Integration with MCP servers
- Custom permission models

### CLI Management

gitagent includes comprehensive CLI commands for agent management:

```bash
# List all discovered agents
python -m gitagent agents list

# Test a specific agent configuration
python -m gitagent agents test .github/action-handlers/push/claude-reviewer.yml

# Validate all agent configurations
python -m gitagent agents validate

# Show agent statistics
python -m gitagent agents stats
```

### Advanced Configuration

```yaml
name: Advanced gitagent Orchestration
on: [workflow_run, deployment, security_advisory, push, pull_request]

jobs:
  advanced-handler:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Advanced gitagent Orchestration
        uses: a5c-ai/gitagent@v1
        with:
          # Authentication
          github-token: ${{ secrets.GITHUB_TOKEN }}
          
          # Processing Configuration
          log-level: DEBUG
          log-format: json
          max-concurrent-events: 20
          event-timeout: 60
          git-commit-history-count: 15
          
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
| `git-commit-history-count` | Number of commits to include in history context | `10` | No |

### Agent Configuration

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `agents-enabled` | Enable AI agent processing | `true` | No |
| `agents-directory` | Directory containing agent configurations | `.github/action-handlers` | No |
| `claude-api-key` | Anthropic Claude API key (for built-in `claude` CLI) | `''` | No |
| `gemini-api-key` | Google Gemini API key (for built-in `gemini` CLI) | `''` | No |
| `openai-api-key` | OpenAI API key (for built-in `codex` CLI) | `''` | No |
| `anthropic-api-key` | Alternative Anthropic API key | `''` | No |

**Note**: All CLI tools are pre-installed in the Docker image. Simply provide the appropriate API key and reference the tool name (e.g., `codex`, `claude`, `gemini`) in your agent configurations.

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
| `agent-results` | JSON array of individual agent execution results with branch automation info |
| `branches-created` | List of branch names created by agent automation |
| `prs-created` | List of PR numbers created by agent automation |
| `status-checks-posted` | List of status check states posted by agents |
| `comments-posted` | List of comment URLs posted by agents |
| `issues-created` | List of issue numbers created by agents |

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
   git clone https://github.com/a5c-ai/gitagent.git
   cd gitagent
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
   docker build -t gitagent .
   ```

2. **Run locally**
   ```bash
   docker run -p 8000:8000 \
     -e GITHUB_TOKEN=your_token \
     -e LOG_LEVEL=DEBUG \
     gitagent
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
pytest --cov=src/gitagent

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
   docker logs gitagent-<run-id>
   
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
- uses: a5c-ai/gitagent@v1
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

## 🚀 Quick Start with Built-in CLI Tools and SDK Integration

gitagent includes pre-installed CLI tools for all major AI providers **plus advanced Claude Code SDK integration** for enhanced capabilities:

### Simple Agent Configuration

```yaml
# OpenAI Codex Agent - Just specify the executable name
agent:
  type: "codex"
  name: "my-codex-assistant"
  executable: "codex"  # No path required!

# Claude Agent - Built-in and ready to use  
agent:
  type: "claude"
  name: "my-claude-reviewer"
  executable: "claude"  # No path required!

# Claude Code SDK Agent - Advanced integration for complex workflows
agent:
  type: "claude_code_sdk"
  name: "my-advanced-claude-agent"
  # No executable needed - uses Python SDK directly!

# Gemini Agent - Pre-installed for convenience
agent:
  type: "gemini" 
  name: "my-gemini-analyzer"
  executable: "gemini"  # No path required!
```

### Benefits of Built-in Tools and SDK Integration

✅ **Zero Configuration** - No need to install or configure CLI tools manually  
✅ **Consistent Versions** - All tools are tested and compatible  
✅ **Simplified Configs** - Just specify the tool name, not the full path  
✅ **Ready to Use** - Docker image includes everything you need  
✅ **Security** - Tools are installed in a controlled, secure environment  
✅ **Advanced SDK** - Claude Code SDK provides enhanced capabilities for complex workflows  

### Getting Started

1. **Set API Keys** - Add your API keys as environment variables
2. **Create Agents** - Use the simple configuration format above
3. **Choose Integration** - Use CLI for simple tasks, SDK for complex workflows
4. **Deploy** - Run the action and your agents will work immediately

No complex setup, no path configuration, no CLI installation - just pure AI-powered automation with advanced SDK capabilities!

## 📞 Support

- 📖 [Documentation](https://github.com/a5c-ai/gitagent/wiki)
- 🐛 [Issue Tracker](https://github.com/a5c-ai/gitagent/issues)
- 💬 [Discussions](https://github.com/a5c-ai/gitagent/discussions)
- 📧 [Email Support](mailto:support@example.com)

---

<p align="center">
  <strong>Built with ❤️ for the GitHub community</strong>
</p>
