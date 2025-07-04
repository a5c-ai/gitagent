# Migration Examples: From Action-Handlers to Workflows

This document shows how to migrate from the old `.github/action-handlers` format to the new single-agent-per-step workflow format.

## Table of Contents

1. [Basic Migration Pattern](#basic-migration-pattern)
2. [Simple Agents](#simple-agents)
3. [Pull Request Workflows](#pull-request-workflows)
4. [Push-Triggered Workflows](#push-triggered-workflows)
5. [Advanced Features](#advanced-features)
6. [Branch Automation](#branch-automation)
7. [Issue Processing](#issue-processing)
8. [Workflow Run Triggers](#workflow-run-triggers)

## Basic Migration Pattern

### Old Format (action-handlers)
```yaml
# .github/action-handlers/[event_type]/[agent-name].yml
agent:
  type: "claude"
  name: "example-agent"
  description: "Example agent"
  version: "1.0.0"

configuration:
  model: "claude-3-sonnet-20241022"
  max_tokens: 4000
  temperature: 0.2

triggers:
  branches: ["main", "develop"]
  paths: ["*.py", "*.js"]
  event_actions: ["opened", "synchronize"]

prompt_template: |
  Your prompt here...

output:
  format: "markdown"
  destination: "comment"
  
enabled: true
```

### New Format (workflows)
```yaml
# .github/workflows/[agent-name].yml
name: Example Agent
on:
  push:
    branches: ["main", "develop"]
    paths: ["*.py", "*.js"]
  pull_request:
    branches: ["main", "develop"]
    types: ["opened", "synchronize"]
    paths: ["*.py", "*.js"]

permissions:
  contents: read
  pull-requests: write

jobs:
  example-agent:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run Example Agent
        uses: a5c-ai/gitagent@main
        with:
          agent-type: 'claude'
          model: 'claude-3-sonnet-20241022'
          max-tokens: 4000
          temperature: 0.2
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          prompt-template: |
            Your prompt here...

      - name: Post Results
        # Custom post-processing logic here
```

## Simple Agents

### Example: Gemini Documentation Analyzer

**Old Format:**
```yaml
# .github/action-handlers/examples/gemini-simple.yml
agent:
  type: "gemini"
  name: "gemini-analyzer"
  description: "Simple Google Gemini analyzer"
  executable: "gemini"

configuration:
  model: "gemini-2.5-flash"
  max_tokens: 3000
  temperature: 0.3

triggers:
  branches: ["main", "develop"]
  paths: ["*.md", "*.txt"]
  include_file_content: true

output:
  format: "markdown"
  destination: "comment"
  comment_template: |
    ## 📝 Documentation Analysis
    {{ output }}
```

**New Format:**
```yaml
# .github/workflows/gemini-simple-analyzer.yml
name: Gemini Simple Documentation Analyzer
on:
  push:
    branches: ["main", "develop"]
    paths: ["*.md", "*.txt"]
  pull_request:
    branches: ["main", "develop"]
    paths: ["*.md", "*.txt"]

permissions:
  contents: read
  pull-requests: write

jobs:
  gemini-doc-analysis:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run Gemini Documentation Analysis
        uses: a5c-ai/gitagent@main
        with:
          agent-type: 'gemini'
          model: 'gemini-2.5-flash'
          max-tokens: 3000
          temperature: 0.3
          include-file-content: true
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
          prompt-template: |
            Your documentation analysis prompt...

      - name: Post Analysis Comment
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const analysis = fs.readFileSync('/tmp/output.md', 'utf8');
            
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 📝 Documentation Analysis\n\n${analysis}`
            });
```

## Pull Request Workflows

### Example: AI Code Reviewer

**Old Format:**
```yaml
# .github/action-handlers/pull_request/pr-reviewer.yml
agent:
  type: "claude"
  name: "pr-reviewer"
  description: "AI code reviewer"

configuration:
  model: "claude-3-sonnet-20241022"
  max_tokens: 4000
  temperature: 0.2

triggers:
  branches: ["main", "develop"]
  event_actions: ["opened", "synchronize"]
  paths: ["*.py", "*.js", "*.ts"]
  include_file_content: true
  include_file_diff: true

output:
  format: "markdown"
  destination: "comment"
  max_length: 6000
```

**New Format:**
```yaml
# .github/workflows/pr-reviewer.yml
name: AI Code Review
on:
  pull_request:
    branches: ["main", "develop"]
    types: ["opened", "synchronize"]
    paths: ["*.py", "*.js", "*.ts"]

permissions:
  contents: read
  pull-requests: write

jobs:
  ai-code-review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run AI Code Review
        uses: a5c-ai/gitagent@main
        with:
          agent-type: 'claude'
          model: 'claude-3-sonnet-20241022'
          max-tokens: 4000
          temperature: 0.2
          include-file-content: true
          include-file-diff: true
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          prompt-template: |
            Your code review prompt...

      - name: Post Review Comment
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const review = fs.readFileSync('/tmp/output.md', 'utf8');
            
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: review
            });
```

## Push-Triggered Workflows

### Example: Security Scanner

**Old Format:**
```yaml
# .github/action-handlers/push/security-scanner.yml
agent:
  type: "claude"
  name: "security-scanner"
  description: "Security vulnerability scanner"

configuration:
  model: "claude-3-sonnet-20241022"
  max_tokens: 6000
  temperature: 0.1

triggers:
  branches: ["main", "develop"]
  paths: ["*.py", "*.js", "*.ts"]
  include_file_content: true

output:
  format: "markdown"
  destination: "status_check"
  status_check_name: "Security Scanner"
  status_check_success_on: ["✅ SECURE"]
  status_check_failure_on: ["🔥 CRITICAL", "🚨 MAJOR"]
```

**New Format:**
```yaml
# .github/workflows/security-scanner.yml
name: Security Scanner
on:
  push:
    branches: ["main", "develop"]
    paths: ["*.py", "*.js", "*.ts"]
  pull_request:
    branches: ["main", "develop"]
    paths: ["*.py", "*.js", "*.ts"]

permissions:
  contents: read
  pull-requests: write
  security-events: write

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run Security Scanner
        uses: a5c-ai/gitagent@main
        with:
          agent-type: 'claude'
          model: 'claude-3-sonnet-20241022'
          max-tokens: 6000
          temperature: 0.1
          include-file-content: true
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          prompt-template: |
            Your security analysis prompt...

      - name: Create Security Status Check
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('/tmp/output.md', 'utf8');
            
            let state = 'success';
            let description = 'No security issues found';
            
            if (report.includes('🔥 CRITICAL')) {
              state = 'failure';
              description = 'Critical security vulnerabilities found';
            } else if (report.includes('🚨 MAJOR')) {
              state = 'failure';
              description = 'Major security issues identified';
            }
            
            await github.rest.repos.createCommitStatus({
              owner: context.repo.owner,
              repo: context.repo.repo,
              sha: context.sha,
              state: state,
              description: description,
              context: 'Security Scanner'
            });
```

## Advanced Features

### Example: Claude Code SDK with Advanced Tools

**Old Format:**
```yaml
# .github/action-handlers/examples/file-inclusion-demo.yml
agent:
  type: "claude"
  name: "file-inclusion-demo"
  description: "Advanced file inclusion with Claude Code"
  executable: "claude"

configuration:
  model: "claude-3-sonnet-20241022"
  max_tokens: 4000
  temperature: 0.1

triggers:
  branches: ["main", "develop"]
  files_changed: ["src/**/*.py", "docs/**/*.md"]
  include_file_content: true
  include_file_diff: true

prompt_template: |
  ## Project Context
  {{ include("README.md") }}
  
  ## Directory Guidelines
  {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/**/.coding-standards.md") }}
  
  Your analysis task...
```

**New Format:**
```yaml
# .github/workflows/claude-code-sdk-advanced.yml
name: Claude Code SDK Advanced Analysis
on:
  push:
    branches: ["main", "develop"]
    paths: ["src/**/*.py", "docs/**/*.md"]
  pull_request:
    branches: ["main", "develop"]
    paths: ["src/**/*.py", "docs/**/*.md"]

permissions:
  contents: write
  pull-requests: write

jobs:
  claude-code-analysis:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run Claude Code SDK Analysis
        uses: a5c-ai/gitagent@main
        with:
          agent-type: 'claude-code-sdk'
          model: 'claude-3-sonnet-20241022'
          max-tokens: 4000
          temperature: 0.1
          max-turns: 10
          permission-mode: 'ask'
          allowed-tools: 'read_file,edit_file,grep_search,run_terminal_cmd'
          include-file-content: true
          include-file-diff: true
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          prompt-template: |
            ## Project Context
            {{ include("README.md") }}
            
            ## Directory Guidelines
            {{ include("$ALL_UNIQUE_CHANGED_FILE_DIRS/**/.coding-standards.md") }}
            
            Your analysis task...

      - name: Handle Results
        # Custom post-processing...
```

## Branch Automation

### Example: AI Bug Fixer with Branch Automation

**Old Format:**
```yaml
# .github/action-handlers/push/ai-bug-fixer.yml
agent:
  type: "claude"
  name: "ai-bug-fixer"
  description: "AI bug fixer with branch automation"

configuration:
  model: "claude-3-sonnet-20241022"
  max_tokens: 8000
  temperature: 0.1

triggers:
  branches: ["main", "develop"]
  files_changed: ["bug-reports/*.md"]
  include_file_content: true

output:
  format: "markdown"
  destination: "status_check"

branch_automation:
  enabled: true
  branch_prefix: "ai-bugfix"
  commit_message: "🤖 AI Bug Fixes"
  create_pull_request: true
  pr_title: "🤖 Automated Bug Fixes"
  pr_labels: ["ai-generated", "bug-fix"]
```

**New Format:**
```yaml
# .github/workflows/ai-bug-fixer.yml
name: AI Bug Fixer
on:
  push:
    branches: ["main", "develop"]
    paths: ["bug-reports/*.md"]

permissions:
  contents: write
  pull-requests: write

jobs:
  ai-bug-fixer:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run AI Bug Fixer
        uses: a5c-ai/gitagent@main
        with:
          agent-type: 'claude'
          model: 'claude-3-sonnet-20241022'
          max-tokens: 8000
          temperature: 0.1
          include-file-content: true
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          prompt-template: |
            Your bug fixing prompt...

      - name: Create Bug Fix Branch
        id: create_branch
        run: |
          BRANCH_NAME="ai-bugfix-$(date +%Y%m%d-%H%M%S)"
          echo "branch_name=$BRANCH_NAME" >> $GITHUB_OUTPUT
          
          git checkout -b $BRANCH_NAME
          git config user.name "AI Bug Fixer"
          git config user.email "ai-bug-fixer@github-actions"

      - name: Commit Bug Fixes
        run: |
          git add -A
          if ! git diff --cached --quiet; then
            git commit -m "🤖 AI Bug Fixes"
            git push origin ${{ steps.create_branch.outputs.branch_name }}
          fi

      - name: Create Pull Request
        uses: actions/github-script@v7
        with:
          script: |
            const pr = await github.rest.pulls.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '🤖 Automated Bug Fixes',
              head: '${{ steps.create_branch.outputs.branch_name }}',
              base: 'main',
              body: 'Automated bug fixes generated by AI...'
            });
            
            await github.rest.issues.addLabels({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: pr.data.number,
              labels: ['ai-generated', 'bug-fix']
            });
```

## Issue Processing

### Example: Bug Report Processor

**Old Format:**
```yaml
# .github/action-handlers/issues/bug-report-processor.yml
agent:
  type: "claude"
  name: "bug-report-processor"
  description: "Process bug reports automatically"

configuration:
  model: "claude-3-sonnet-20241022"
  max_tokens: 6000
  temperature: 0.2

triggers:
  event_actions: ["opened", "edited"]
  labels: ["bug"]

output:
  format: "markdown"
  destination: "comment"
```

**New Format:**
```yaml
# .github/workflows/issue-processor.yml
name: Issue Processor
on:
  issues:
    types: ["opened", "edited", "labeled"]

permissions:
  contents: read
  issues: write

jobs:
  process-issue:
    runs-on: ubuntu-latest
    if: contains(github.event.issue.labels.*.name, 'bug')
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Process Bug Report
        uses: a5c-ai/gitagent@main
        with:
          agent-type: 'claude'
          model: 'claude-3-sonnet-20241022'
          max-tokens: 6000
          temperature: 0.2
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          prompt-template: |
            ## Issue Context
            - **Issue:** #${{ github.event.issue.number }}
            - **Title:** ${{ github.event.issue.title }}
            - **Author:** ${{ github.event.issue.user.login }}
            
            ## Bug Report Content
            ${{ github.event.issue.body }}
            
            Your analysis task...

      - name: Post Bug Analysis
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const analysis = fs.readFileSync('/tmp/output.md', 'utf8');
            
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 🤖 Automated Bug Analysis\n\n${analysis}`
            });
```

## Workflow Run Triggers

### Example: Auto Build Fixer

**Old Format:**
```yaml
# .github/action-handlers/workflow_run/auto-build-fixer.yml
agent:
  type: "claude"
  name: "auto-build-fixer"
  description: "Fix build failures automatically"

configuration:
  model: "claude-3-sonnet-20241022"
  max_tokens: 8000
  temperature: 0.1

triggers:
  workflow_names: ["CI", "Build", "Test"]
  workflow_conclusion: ["failure"]
  branches: ["main", "develop"]

output:
  format: "markdown"
  destination: "status_check"
```

**New Format:**
```yaml
# .github/workflows/auto-build-fixer.yml
name: Auto Build Fixer
on:
  workflow_run:
    workflows: ["CI", "Build", "Test"]
    types: [completed]
    branches: [main, develop]

permissions:
  contents: write
  actions: read
  pull-requests: write

jobs:
  fix-build:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Get workflow logs
        uses: actions/github-script@v7
        with:
          script: |
            const logs = await github.rest.actions.downloadWorkflowRunLogs({
              owner: context.repo.owner,
              repo: context.repo.repo,
              run_id: ${{ github.event.workflow_run.id }}
            });
            
            require('fs').writeFileSync('/tmp/workflow-logs.zip', Buffer.from(logs.data));

      - name: Run Build Fixer
        uses: a5c-ai/gitagent@main
        with:
          agent-type: 'claude'
          model: 'claude-3-sonnet-20241022'
          max-tokens: 8000
          temperature: 0.1
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
          prompt-template: |
            ## Workflow Context
            - **Failed Workflow:** ${{ github.event.workflow_run.name }}
            - **Branch:** ${{ github.event.workflow_run.head_branch }}
            - **Author:** ${{ github.event.workflow_run.actor.login }}
            
            ## Build Logs
            {{ include("/tmp/workflow-logs.zip") }}
            
            Your build fix task...

      - name: Create Fix Branch and PR
        # Branch creation and PR logic...
```

## Key Migration Principles

1. **Trigger Conversion:**
   - `triggers.branches` → `on.push.branches` and `on.pull_request.branches`
   - `triggers.paths` → `on.push.paths` and `on.pull_request.paths`
   - `triggers.event_actions` → `on.pull_request.types`

2. **Output Handling:**
   - `output.destination: "comment"` → Custom GitHub Script step
   - `output.destination: "status_check"` → Custom status check step
   - `output.destination: "issue"` → Custom issue creation step

3. **Branch Automation:**
   - `branch_automation` → Custom git commands and PR creation steps
   - Use `actions/github-script@v7` for GitHub API interactions

4. **File Inclusion:**
   - `{{ include("file.md") }}` → Use `include-file-content: true` and template variables
   - Complex file patterns → Use the Claude Code SDK for advanced file operations

5. **Permissions:**
   - Always specify appropriate permissions for the workflow
   - Use the principle of least privilege

This migration approach provides more flexibility, better debugging capabilities, and native GitHub Actions integration while maintaining all the AI agent functionality. 