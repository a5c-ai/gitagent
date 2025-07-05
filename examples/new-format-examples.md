# New Format Examples

This document shows how to use the new single-agent-per-step approach instead of the old `.github/action-handlers/` directory structure.

## Overview

**Old approach:**
- Define agents in `.github/action-handlers/[event_type]/agent.yml`
- Use one action installation with complex trigger rules
- Batch execution of multiple agents per event

**New approach:**
- Define each agent as a separate workflow step
- Use workflow conditions for triggering (GitHub's native features)
- Decouple output handling with subsequent steps
- More flexible and maintainable

## Basic Examples

### 1. Claude Code Review Agent

**Old format** (`.github/action-handlers/pull_request/claude-reviewer.yml`):
```yaml
agent:
  type: "claude"
  name: "code-reviewer"
  description: "Automated code reviewer"
  executable: "claude"

configuration:
  model: "claude-3-sonnet-20241022"

triggers:
  branches: ["main", "develop"]
  event_actions: ["opened", "synchronize"]
  files_changed: ["*.py", "*.js", "*.ts"]
  include_file_content: true
  include_file_diff: true

prompt_template: |
  You are an expert code reviewer. Please review the following changes:
  
  ## Files Changed
  {% for file in files_changed %}
  - **{{ file.filename }}** ({{ file.status }})
  {% endfor %}
  
  Please provide constructive feedback on:
  - Code quality and best practices
  - Potential bugs or security issues
  - Performance considerations
  - Documentation and testing needs

output:
  destination: "comment"
  comment_template: |
    ## 🤖 AI Code Review
    
    {{ output }}
```

**New format** (workflow step):
```yaml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]
    branches: [main, develop]
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
          # Agent configuration
          agent-type: 'claude'
          agent-name: 'code-reviewer'
          agent-description: 'Automated code reviewer'
          model: 'claude-3-sonnet-20241022'
          
          # File context
          include-file-content: true
          include-file-diff: true
          
          # Prompt template
          prompt-template: |
            You are an expert code reviewer. Please review the following changes:
            
            ## Repository Context
            - **Repository:** {{ github_context.repository }}
            - **Pull Request:** #{{ event.pull_request.number }}
            - **Branch:** {{ event.pull_request.head.ref }}
            
            ## Files Changed
            {% for file in files_changed %}
            - **{{ file.filename }}** ({{ file.status }})
            {% endfor %}
            
            Please provide constructive feedback on:
            - Code quality and best practices
            - Potential bugs or security issues
            - Performance considerations
            - Documentation and testing needs
            
            Write your review in markdown format.
          
          # Output to file for next step
          output-file: '/tmp/review.md'
          
          # API key
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

### 2. Gemini Security Scanner

**Old format** (`.github/action-handlers/push/security-scanner.yml`):
```yaml
agent:
  type: "gemini"
  name: "security-scanner"
  executable: "gemini"

configuration:
  model: "gemini-2.0-flash"

triggers:
  branches: ["main"]
  files_changed: ["*.py", "*.js", "*.ts", "*.java"]
  include_file_content: true

prompt_template: |
  Analyze the following code changes for security vulnerabilities:
  
  {% for file in files_changed %}
  ## {{ file.filename }}
  ```{{ file.filename.split('.')[-1] }}
  {{ file.content }}
  ```
  {% endfor %}
  
  Report any security issues found.

output:
  destination: "status_check"
  status_check_name: "Security Scan"
  status_check_success_on: ["✅ No issues", "CLEAN"]
  status_check_failure_on: ["❌ Issues found", "VULNERABLE"]
```

**New format** (workflow step):
```yaml
name: Security Scan
on:
  push:
    branches: [main]
    paths: ['**.py', '**.js', '**.ts', '**.java']

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Gemini Security Scan
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
            
            ## Repository: {{ github_context.repository }}
            ## Commit: {{ github_context.sha }}
            
            {% for file in files_changed %}
            ## {{ file.filename }}
            ```{{ file.filename.split('.')[-1] }}
            {{ file.content }}
            ```
            {% endfor %}
            
            Report any security issues found. Use "✅ No issues" if clean, "❌ Issues found" if vulnerable.
          
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
      
      - name: Create Security Status Check
        uses: actions/github-script@v7
        with:
          script: |
            const output = `${{ steps.security-scan.outputs.output }}`;
            const success = output.includes('✅ No issues') || output.includes('CLEAN');
            
            await github.rest.repos.createCommitStatus({
              owner: context.repo.owner,
              repo: context.repo.repo,
              sha: context.sha,
              state: success ? 'success' : 'failure',
              context: 'Security Scan',
              description: success ? 'No security issues found' : 'Security issues detected'
            });
```

### 3. Claude Code SDK Advanced Agent

**Old format** (`.github/action-handlers/issues/bug-processor.yml`):
```yaml
agent:
  type: "claude_code_sdk"
  name: "bug-processor"
  description: "Process bug reports and create fixes"

configuration:
  model: "claude-3-sonnet-20241022"
  max_turns: 10
  permission_mode: "acceptEdits"
  allowed_tools: ["file_editor", "bash"]

triggers:
  event_actions: ["opened", "labeled"]
  files_changed: ["bug-reports/*.md"]
  include_file_content: true

prompt_template: |
  You are a bug processing assistant. A new bug report has been filed:
  
  **Issue:** {{ event.issue.title }}
  **Description:** {{ event.issue.body }}
  
  {% if files_changed %}
  **Bug Report Files:**
  {% for file in files_changed %}
  ### {{ file.filename }}
  {{ file.content }}
  {% endfor %}
  {% endif %}
  
  Your task:
  1. Analyze the bug report
  2. Reproduce the issue if possible
  3. Implement a fix
  4. Create tests for the fix
  5. Write a summary report

branch_automation:
  enabled: true
  branch_prefix: "bug-fix"
  commit_message: "🐛 Fix: {{ event.issue.title }}"
  create_pull_request: true
  pr_title: "🐛 Bug Fix: {{ event.issue.title }}"
```

**New format** (workflow step):
```yaml
name: Bug Processing
on:
  issues:
    types: [opened, labeled]

jobs:
  process-bug:
    runs-on: ubuntu-latest
    if: contains(github.event.issue.labels.*.name, 'bug') || contains(github.event.issue.title, 'bug')
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Claude Code SDK Bug Processing
        id: bug-processor
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'claude_code_sdk'
          agent-name: 'bug-processor'
          model: 'claude-3-sonnet-20241022'
          max-tokens: 8000
          max-turns: 10
          permission-mode: 'acceptEdits'
          allowed-tools: 'file_editor,bash'
          
          include-file-content: true
          
          prompt-template: |
            You are a bug processing assistant. A new bug report has been filed:
            
            **Issue:** {{ event.issue.title }}
            **Description:** {{ event.issue.body }}
            **Reporter:** {{ event.issue.user.login }}
            **Repository:** {{ github_context.repository }}
            
            {% if files_changed %}
            **Bug Report Files:**
            {% for file in files_changed %}
            ### {{ file.filename }}
            {{ file.content }}
            {% endfor %}
            {% endif %}
            
            Your task:
            1. Analyze the bug report thoroughly
            2. Explore the codebase to understand the issue
            3. Reproduce the issue if possible
            4. Implement a comprehensive fix
            5. Create or update tests for the fix
            6. Write a detailed summary report
            
            Please be thorough and methodical in your approach.
          
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
      
      - name: Create Bug Fix Branch
        if: steps.bug-processor.outputs.success == 'true'
        run: |
          git config --global user.name "Bug Fix Bot"
          git config --global user.email "bot@example.com"
          
          # Create new branch
          BRANCH_NAME="bug-fix-${{ github.event.issue.number }}"
          git checkout -b "$BRANCH_NAME"
          
          # Commit any changes made by the agent
          git add .
          if git diff --staged --quiet; then
            echo "No changes to commit"
          else
            git commit -m "🐛 Fix: ${{ github.event.issue.title }}"
            git push origin "$BRANCH_NAME"
            
            # Create pull request
            gh pr create \
              --title "🐛 Bug Fix: ${{ github.event.issue.title }}" \
              --body "Automated bug fix for issue #${{ github.event.issue.number }}" \
              --label "bug-fix,automated" \
              --assignee "${{ github.event.issue.user.login }}"
          fi
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Advanced Patterns

### 4. Multi-Step Workflow with Agent Chaining

```yaml
name: Comprehensive Code Analysis
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  analyze-code:
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
            Perform a security analysis of the code changes. Focus on:
            - Authentication and authorization issues
            - Input validation vulnerabilities
            - SQL injection possibilities
            - XSS vulnerabilities
            - Insecure dependencies
            
            {% for file in files_changed %}
            ## {{ file.filename }}
            {{ file.content }}
            {% endfor %}
            
            Provide a structured JSON report with findings.
          output-file: '/tmp/security-report.json'
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
      
      # Step 2: Code quality analysis
      - name: Code Quality Analysis
        id: quality
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'gemini'
          agent-name: 'quality-analyzer'
          model: 'gemini-2.0-flash'
          include-file-content: true
          prompt-template: |
            Analyze code quality and best practices:
            
            {% for file in files_changed %}
            ## {{ file.filename }}
            {{ file.content }}
            {% endfor %}
            
            Focus on:
            - Code complexity and maintainability
            - Design patterns and architecture
            - Performance considerations
            - Documentation quality
            
            Provide a JSON report with scores and recommendations.
          output-file: '/tmp/quality-report.json'
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
      
      # Step 3: Comprehensive review synthesis
      - name: Synthesis Review
        id: synthesis
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'claude_code_sdk'
          agent-name: 'review-synthesizer'
          model: 'claude-3-sonnet-20241022'
          max-turns: 5
          permission-mode: 'acceptEdits'
          prompt-template: |
            You are a senior code reviewer synthesizing multiple analysis reports.
            
            **Security Report:**
            {{ include('/tmp/security-report.json') }}
            
            **Quality Report:**
            {{ include('/tmp/quality-report.json') }}
            
            **Code Changes:**
            {% for file in files_changed %}
            ## {{ file.filename }}
            {{ file.content }}
            {% endfor %}
            
            Create a comprehensive review that:
            1. Synthesizes findings from both reports
            2. Prioritizes issues by severity
            3. Provides actionable recommendations
            4. Suggests specific code improvements
            5. Writes the final review to `/tmp/final-review.md`
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
      
      # Step 4: Post comprehensive review
      - name: Post Review
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            
            let review = '## 🤖 Comprehensive AI Code Review\n\n';
            
            try {
              const finalReview = fs.readFileSync('/tmp/final-review.md', 'utf8');
              review += finalReview;
            } catch (error) {
              review += 'Review synthesis failed. Individual reports:\n\n';
              
              if (fs.existsSync('/tmp/security-report.json')) {
                review += '### Security Analysis\n';
                review += '${{ steps.security.outputs.output }}\n\n';
              }
              
              if (fs.existsSync('/tmp/quality-report.json')) {
                review += '### Quality Analysis\n';
                review += '${{ steps.quality.outputs.output }}\n\n';
              }
            }
            
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: review
            });
```

### 5. Conditional Agent Execution

```yaml
name: Smart Agent Routing
on:
  issues:
    types: [opened]

jobs:
  route-issue:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      # Different agents for different issue types
      - name: Bug Report Handler
        if: contains(github.event.issue.labels.*.name, 'bug')
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'claude_code_sdk'
          agent-name: 'bug-handler'
          # ... bug-specific configuration
          
      - name: Feature Request Handler
        if: contains(github.event.issue.labels.*.name, 'feature')
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'gemini'
          agent-name: 'feature-handler'
          # ... feature-specific configuration
          
      - name: Documentation Request Handler
        if: contains(github.event.issue.labels.*.name, 'documentation')
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: 'claude'
          agent-name: 'docs-handler'
          # ... docs-specific configuration
```

## Migration Guide

### Converting Old Agent Files

1. **Identify triggers** → Convert to GitHub workflow conditions
2. **Extract agent configuration** → Move to workflow step inputs
3. **Move prompt template** → Set as `prompt-template` input
4. **Handle outputs** → Use subsequent workflow steps
5. **Branch automation** → Replace with workflow steps using `git` commands

### Benefits of New Approach

- **Better separation of concerns**: Each agent has a single responsibility
- **Easier debugging**: Individual steps can be tested independently
- **More flexible**: Can combine agents in complex workflows
- **GitHub-native**: Uses standard GitHub Actions features
- **Better visibility**: Each agent execution is a separate step in the workflow
- **Conditional execution**: Use GitHub's `if` conditions instead of complex trigger rules

### Best Practices

1. **Use descriptive step names** for easy identification
2. **Store outputs in files** for multi-step workflows
3. **Use conditional execution** to optimize performance
4. **Set appropriate timeouts** for agent executions
5. **Use secrets** for API keys
6. **Add error handling** with `if: always()` or `if: failure()`
7. **Test agents individually** before combining them 