# Prompt Templates

This directory contains Jinja2 prompt templates for the gitagent GitHub Action workflows.

## Overview

The prompt templates have been extracted from the inline workflow configurations to improve maintainability and versioning. Each template corresponds to a specific AI agent workflow.

## Template Files

| Template File | Workflow | Agent Type | Description |
|---------------|----------|------------|-------------|
| `gemini-simple-analyzer.md` | `gemini-simple-analyzer.yml` | Gemini | Documentation analysis and improvement suggestions |
| `pr-reviewer.md` | `pr-reviewer.yml` | Claude | Comprehensive code review for pull requests |
| `ai-bug-fixer.md` | `ai-bug-fixer.yml` | Claude | Automated bug fixing with code modifications |
| `claude-code-sdk-advanced.md` | `claude-code-sdk-advanced.yml` | Claude Code SDK | Advanced code analysis with full toolkit access |
| `security-scanner.md` | `security-scanner.yml` | Claude | Security vulnerability scanning and analysis |
| `issue-processor.md` | `issue-processor.yml` | Claude | Bug report analysis and processing |
| `auto-build-fixer.md` | `auto-build-fixer.yml` | Claude | CI/CD build failure analysis and fixes |

## Usage

To use a prompt template in a workflow, use the `prompt-template-file` parameter:

```yaml
- name: Run AI Agent
  uses: a5c-ai/gitagent@main
  with:
    agent-type: 'claude'
    prompt-template-file: 'prompts/pr-reviewer.md'
    # ... other parameters
```

## Template Syntax

Templates use Jinja2 syntax with access to:

- **GitHub Context**: `{{ github.repository }}`, `{{ github.event.number }}`, etc.
- **Files Changed**: `{% for file in files_changed %}...{% endfor %}`
- **Event Data**: `{{ github.event.issue.title }}`, `{{ github.event.pull_request.title }}`, etc.
- **File Includes**: `{{ include("filename.md") }}` for including other repository files

## Template Structure

Each template follows a consistent structure:

1. **Role Definition**: Clear description of the AI agent's role and capabilities
2. **Context Information**: Repository, event, and file information
3. **Task Instructions**: Step-by-step workflow for the agent
4. **Output Format**: Specific format requirements for generated content
5. **Important Notes**: Key considerations and constraints

## Benefits

- **Maintainability**: Easy to update prompts without modifying workflow files
- **Version Control**: Proper tracking of prompt changes
- **Reusability**: Templates can be shared across different workflows
- **Readability**: Cleaner workflow files focusing on configuration
- **Testing**: Easier to test and iterate on prompt designs

## Best Practices

1. **Keep Context Relevant**: Only include necessary context information
2. **Be Specific**: Provide clear, actionable instructions
3. **Format Consistently**: Use consistent markdown formatting
4. **Document Changes**: Include comments explaining significant modifications
5. **Test Thoroughly**: Verify templates work correctly with different scenarios

## Backward Compatibility

The action still supports the deprecated `prompt-template` parameter for inline prompts, but it's recommended to migrate to `prompt-template-file` for better maintainability. 