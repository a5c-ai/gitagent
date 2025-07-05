# Migration Guide: From Directory-Based to Step-Based Agents

This guide explains how to migrate from the old `.github/action-handlers/` directory approach to the new single-agent-per-step workflow format.

## Key Changes Overview

### Old Approach ❌
- **Agent Discovery**: Agents defined in `.github/action-handlers/[event_type]/agent.yml`
- **Batch Execution**: Multiple agents executed automatically per event
- **Complex Triggers**: Extensive trigger rules (branches, tags, file patterns, conditions)
- **Built-in Outputs**: Predefined output destinations (comments, status checks, issues)
- **One Installation**: Single action installation handles all events

### New Approach ✅
- **Explicit Definition**: Each agent defined as a workflow step with inputs
- **Single Execution**: One agent per step for clarity and control
- **GitHub Conditions**: Use native GitHub workflow conditions for triggering
- **Flexible Outputs**: Agent outputs available for subsequent steps to handle
- **Step-by-Step**: Each agent is its own step in the workflow

## Migration Steps

### 1. Identify Your Current Agents

First, list all your existing agent files:
```bash
find .github/action-handlers -name "*.yml" -o -name "*.yaml"
```

### 2. Convert Agent Definitions

For each agent file, extract the key components:

**Old Format Example:**
```yaml
# .github/action-handlers/pull_request/claude-reviewer.yml
agent:
  type: "claude"
  name: "code-reviewer"
  executable: "claude"

configuration:
  model: "claude-3-sonnet-20241022"

triggers:
  branches: ["main", "develop"]
  event_actions: ["opened", "synchronize"]
  files_changed: ["*.py", "*.js"]
  include_file_content: true

prompt_template: |
  Review the following code changes...

output:
  destination: "comment"
```

**New Format Conversion:**
```yaml
# .github/workflows/code-review.yml
name: Code Review
on:
  pull_request:                    # ← Moved from triggers.event_actions
    types: [opened, synchronize]   # ← Moved from triggers.event_actions
    branches: [main, develop]      # ← Moved from triggers.branches
    paths: ['**.py', '**.js']      # ← Moved from triggers.files_changed

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Claude Code Review  # ← From agent.name
        id: review
        uses: a5c-ai/gitagent@v1
        with:
          agent-type: claude        # ← From agent.type
          model: claude-3-sonnet-20241022  # ← From configuration.model
          include-file-content: true # ← From triggers.include_file_content
          
          prompt-template: |        # ← From prompt_template
            Review the following code changes...
          
          output-file: '/tmp/review.md'  # ← For next step
          claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
      
      - name: Post Comment         # ← Replaces output.destination
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const review = fs.readFileSync('/tmp/review.md', 'utf8');
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: review
            });
```

### 3. Handle Complex Triggers

**Old Complex Triggers:**
```yaml
triggers:
  branches: ["main", "develop"]
  tags: ["v*"]
  paths: ["src/**", "docs/**"]
  conditions:
    - "{{ event.pull_request.draft == false }}"
    - "{{ commit_history.total_commits > 0 }}"
  files_changed_min: 1
  files_changed_max: 10
```

**New GitHub Workflow Conditions:**
```yaml
on:
  push:
    branches: [main, develop]
    tags: ['v*']
    paths: ['src/**', 'docs/**']
  pull_request:
    types: [opened, synchronize]

jobs:
  process:
    runs-on: ubuntu-latest
    if: |
      github.event.pull_request.draft == false &&
      github.event.commits && 
      length(github.event.commits) > 0 &&
      length(github.event.commits) <= 10
```

### 4. Convert Output Destinations

**Status Checks:**
```yaml
# Old
output:
  destination: "status_check"
  status_check_name: "Security Scan"

# New
- name: Create Status Check
  uses: actions/github-script@v7
  with:
    script: |
      const output = '${{ steps.agent.outputs.output }}';
      const success = output.includes('✅');
      await github.rest.repos.createCommitStatus({
        owner: context.repo.owner,
        repo: context.repo.repo,
        sha: context.sha,
        state: success ? 'success' : 'failure',
        context: 'Security Scan'
      });
```

**Issue Creation:**
```yaml
# Old
output:
  destination: "create_issue"
  issue_title_template: "Bug Report: {{ github_context.ref }}"
  issue_labels: ["bug", "automated"]

# New
- name: Create Issue
  uses: actions/github-script@v7
  with:
    script: |
      const content = '${{ steps.agent.outputs.output }}';
      await github.rest.issues.create({
        owner: context.repo.owner,
        repo: context.repo.repo,
        title: `Bug Report: ${context.ref}`,
        body: content,
        labels: ['bug', 'automated']
      });
```

### 5. Handle Branch Automation

**Old Branch Automation:**
```yaml
branch_automation:
  enabled: true
  branch_prefix: "auto-fix"
  commit_message: "🤖 Fix: {{ event.issue.title }}"
  create_pull_request: true
  pr_title: "🤖 Automated Fix"
```

**New Workflow Steps:**
```yaml
- name: Create Fix Branch
  if: steps.agent.outputs.success == 'true'
  run: |
    git config --global user.name "Bot"
    git config --global user.email "bot@example.com"
    
    BRANCH_NAME="auto-fix-${{ github.run_number }}"
    git checkout -b "$BRANCH_NAME"
    git add .
    git commit -m "🤖 Fix: ${{ github.event.issue.title }}"
    git push origin "$BRANCH_NAME"
    
    gh pr create \
      --title "🤖 Automated Fix" \
      --body "Automated fix generated by AI agent" \
      --label "automation"
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Benefits of Migration

### 1. **Better Debugging**
- Each agent execution is a separate step
- Clear success/failure status per agent
- Easier to isolate issues

### 2. **More Flexible**
- Combine agents in complex workflows
- Conditional execution based on previous steps
- Chain agents with custom logic

### 3. **GitHub Native**
- Uses standard GitHub Actions features
- Better integration with existing workflows
- Familiar syntax for GitHub users

### 4. **Clearer Separation**
- Agent logic separate from trigger logic
- Output handling decoupled from agent execution
- Easier to test and maintain

## Common Migration Patterns

### Pattern 1: Simple Agent Conversion
```yaml
# Old: .github/action-handlers/push/linter.yml
# New: .github/workflows/lint.yml with single step

# Old: .github/action-handlers/issues/labeler.yml  
# New: .github/workflows/auto-label.yml with single step
```

### Pattern 2: Multi-Agent Workflow
```yaml
# Old: Multiple agents in same event directory
# New: Multiple steps in same job
steps:
  - name: Security Scan
    uses: a5c-ai/gitagent@v1
    # ...
  - name: Quality Check  
    uses: a5c-ai/gitagent@v1
    # ...
  - name: Final Review
    uses: a5c-ai/gitagent@v1
    # ...
```

### Pattern 3: Conditional Agents
```yaml
# Old: Complex trigger conditions
# New: GitHub if conditions
- name: Bug Handler
  if: contains(github.event.issue.labels.*.name, 'bug')
  uses: a5c-ai/gitagent@v1
  # ...

- name: Feature Handler
  if: contains(github.event.issue.labels.*.name, 'enhancement')
  uses: a5c-ai/gitagent@v1
  # ...
```

## Testing Your Migration

1. **Start Small**: Migrate one simple agent first
2. **Test Locally**: Use `act` to test workflows locally
3. **Use Staging**: Test in a staging repository first
4. **Monitor**: Watch for any issues in the first few runs
5. **Iterate**: Refine based on actual usage

## Rollback Plan

If you need to rollback:
1. Keep your old `.github/action-handlers/` directory
2. Revert to the old action version
3. Disable new workflows

## Getting Help

- Check [examples/new-format-examples.md](examples/new-format-examples.md) for detailed examples
- Review the updated [README.md](README.md) for complete documentation
- Open an issue if you encounter migration problems

The new format provides much more flexibility and better integration with GitHub Actions while maintaining all the AI-powered capabilities you love! 