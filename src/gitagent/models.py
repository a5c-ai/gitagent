"""
Pydantic models for GitHub Action events and data structures.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class GitHubActionTrigger(str, Enum):
    """Enumeration of all GitHub Action event triggers."""
    
    # Workflow events
    WORKFLOW_RUN = "workflow_run"
    WORKFLOW_JOB = "workflow_job"
    WORKFLOW_DISPATCH = "workflow_dispatch"
    
    # Code events
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW = "pull_request_review"
    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"
    PULL_REQUEST_TARGET = "pull_request_target"
    
    # Issue events
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    
    # Project events
    PROJECT = "project"
    PROJECT_CARD = "project_card"
    PROJECT_COLUMN = "project_column"
    
    # Repository events
    CREATE = "create"
    DELETE = "delete"
    FORK = "fork"
    GOLLUM = "gollum"
    PUBLIC = "public"
    REPOSITORY = "repository"
    STAR = "star"
    WATCH = "watch"
    
    # Release events
    RELEASE = "release"
    
    # Deployment events
    DEPLOYMENT = "deployment"
    DEPLOYMENT_STATUS = "deployment_status"
    ENVIRONMENT = "environment"
    
    # Security events
    SECURITY_ADVISORY = "security_advisory"
    VULNERABILITY_ALERT = "vulnerability_alert"
    CODE_SCANNING_ALERT = "code_scanning_alert"
    SECRET_SCANNING_ALERT = "secret_scanning_alert"
    
    # Team and organization events
    MEMBER = "member"
    MEMBERSHIP = "membership"
    ORGANIZATION = "organization"
    ORG_BLOCK = "org_block"
    TEAM = "team"
    TEAM_ADD = "team_add"
    
    # App events
    INSTALLATION = "installation"
    INSTALLATION_REPOSITORIES = "installation_repositories"
    MARKETPLACE_PURCHASE = "marketplace_purchase"
    
    # Other events
    CHECK_RUN = "check_run"
    CHECK_SUITE = "check_suite"
    COMMIT_COMMENT = "commit_comment"
    DISCUSSION = "discussion"
    DISCUSSION_COMMENT = "discussion_comment"
    LABEL = "label"
    MILESTONE = "milestone"
    PAGE_BUILD = "page_build"
    REPOSITORY_DISPATCH = "repository_dispatch"
    STATUS = "status"
    REGISTRY_PACKAGE = "registry_package"
    PACKAGE = "package"


class AgentType(str, Enum):
    """Enumeration of supported AI agent types."""
    
    CODEX = "codex"
    GEMINI = "gemini"
    CLAUDE = "claude"
    CLAUDE_CODE_SDK = "claude_code_sdk"
    CUSTOM = "custom"


class OutputDestination(str, Enum):
    """Enumeration of output destinations for agent responses."""
    
    COMMENT = "comment"
    PR_REVIEW = "pr_review"
    FILE = "file"
    ISSUE = "issue"
    CONSOLE = "console"
    ARTIFACT = "artifact"
    STATUS_CHECK = "status_check"
    CREATE_ISSUE = "create_issue"


class AgentCliConfiguration(BaseModel):
    """Configuration for AI agent CLI tools."""
    
    executable_path: str = Field(..., description="Path to the agent CLI executable")
    api_key_env: Optional[str] = Field(None, description="Environment variable containing API key")
    api_key: Optional[str] = Field(None, description="Direct API key (not recommended)")
    base_url: Optional[str] = Field(None, description="Custom API base URL")
    model: Optional[str] = Field(None, description="Default model to use")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens for responses")
    temperature: Optional[float] = Field(None, description="Temperature for response generation")
    timeout_seconds: int = Field(default=300, description="Timeout for CLI execution")
    additional_args: List[str] = Field(default_factory=list, description="Additional CLI arguments")
    environment_vars: Dict[str, str] = Field(default_factory=dict, description="Additional environment variables")


class ClaudeCodeSDKConfiguration(BaseModel):
    """Configuration for Claude Code SDK integration."""
    
    api_key: Optional[str] = Field(None, description="Claude/Anthropic API key")
    api_key_env: Optional[str] = Field(None, description="Environment variable containing API key")
    model: Optional[str] = Field("claude-3-sonnet-20241022", description="Claude model to use")
    max_tokens: Optional[int] = Field(4000, description="Maximum tokens for responses")
    temperature: Optional[float] = Field(0.1, description="Temperature for response generation")
    timeout_seconds: int = Field(300, description="Timeout for SDK execution")
    max_turns: int = Field(10, description="Maximum conversation turns")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")
    append_system_prompt: Optional[str] = Field(None, description="Text to append to system prompt")
    output_format: str = Field("text", description="Output format (text, json, stream-json)")
    use_bedrock: bool = Field(False, description="Use Amazon Bedrock instead of Anthropic API")
    use_vertex: bool = Field(False, description="Use Google Vertex AI instead of Anthropic API")
    mcp_config_path: Optional[str] = Field(None, description="Path to MCP configuration file")
    allowed_tools: List[str] = Field(default_factory=list, description="List of allowed tools")
    disallowed_tools: List[str] = Field(default_factory=list, description="List of disallowed tools")
    permission_mode: str = Field("default", description="Permission mode (default, acceptEdits, bypassPermissions, plan)")
    cwd: Optional[str] = Field(None, description="Working directory for Claude Code execution")


class McpServerConfig(BaseModel):
    """Configuration for MCP (Model Context Protocol) servers."""
    
    name: str = Field(..., description="Server name")
    url: str = Field(..., description="Server URL or protocol")
    config: Dict[str, Any] = Field(default_factory=dict, description="Server-specific configuration")
    enabled: bool = Field(default=True, description="Whether the server is enabled")
    timeout_seconds: int = Field(default=30, description="Timeout for server connections")


class AgentTriggerCondition(BaseModel):
    """Trigger conditions for when an agent should run."""
    
    branches: Optional[List[str]] = Field(None, description="Branch patterns (glob)")
    tags: Optional[List[str]] = Field(None, description="Tag patterns (glob)")
    paths: Optional[List[str]] = Field(None, description="File path patterns (glob)")
    conditions: Optional[List[str]] = Field(None, description="Jinja2 template conditions")
    event_actions: Optional[List[str]] = Field(None, description="Specific event actions")
    files_changed_min: Optional[int] = Field(None, description="Minimum files changed")
    files_changed_max: Optional[int] = Field(None, description="Maximum files changed")
    
    # File-specific change monitoring
    files_changed: Optional[List[str]] = Field(None, description="Specific file patterns that must have changed (glob)")
    include_file_content: bool = Field(default=False, description="Include file content in template variables")
    include_file_diff: bool = Field(default=False, description="Include file diff in template variables")
    file_diff_context: int = Field(default=3, description="Number of context lines for file diffs")


class AgentOutputConfig(BaseModel):
    """Configuration for agent output handling."""
    
    format: str = Field(default="markdown", description="Output format")
    destination: OutputDestination = Field(default=OutputDestination.CONSOLE, description="Where to send output")
    file_path: Optional[str] = Field(None, description="File path for file destination")
    max_length: Optional[int] = Field(None, description="Maximum output length")
    template: Optional[str] = Field(None, description="Output template")
    
    # File-based output configuration
    output_file: Optional[str] = Field(None, description="Path to file where agent writes its output")
    comment_output_file: Optional[str] = Field(None, description="Path to file where agent writes comment content")
    
    # Status check configuration
    status_check_name: Optional[str] = Field(None, description="Name for GitHub status check")
    status_check_success_on: List[str] = Field(default_factory=list, description="Keywords that indicate success")
    status_check_failure_on: List[str] = Field(default_factory=list, description="Keywords that indicate failure")
    
    # Comment configuration  
    comment_on_success: bool = Field(default=True, description="Post comment on successful execution")
    comment_on_failure: bool = Field(default=True, description="Post comment on failed execution")
    comment_template: Optional[str] = Field(None, description="Template for comment content")
    
    # Issue creation configuration
    issue_title_template: Optional[str] = Field(None, description="Template for created issue title")
    issue_body_template: Optional[str] = Field(None, description="Template for created issue body")
    issue_labels: List[str] = Field(default_factory=list, description="Labels to add to created issues")
    issue_assignees: List[str] = Field(default_factory=list, description="Assignees for created issues")
    issue_milestone: Optional[str] = Field(None, description="Milestone for created issues")


class AgentBranchAutomation(BaseModel):
    """Configuration for automated branch creation and PR workflows."""
    
    enabled: bool = Field(default=False, description="Enable branch automation")
    branch_prefix: str = Field(default="agent-fix", description="Prefix for created branches")
    commit_message: Optional[str] = Field(None, description="Template for commit message (Jinja2)")
    create_pull_request: bool = Field(default=False, description="Create pull request after pushing branch")
    pr_title: Optional[str] = Field(None, description="Template for PR title (Jinja2)")
    pr_body: Optional[str] = Field(None, description="Template for PR body (Jinja2)")
    pr_labels: List[str] = Field(default_factory=list, description="Labels to add to created PR")
    pr_assignees: List[str] = Field(default_factory=list, description="Assignees for created PR")
    pr_reviewers: List[str] = Field(default_factory=list, description="Reviewers for created PR")
    target_branch: Optional[str] = Field(None, description="Target branch for PR (defaults to repo default branch)")
    delete_branch_on_merge: bool = Field(default=True, description="Delete branch when PR is merged")


class FileChange(BaseModel):
    """Model for file change information."""
    
    filename: str = Field(..., description="File path")
    status: str = Field(..., description="Change status (added, removed, modified)")
    additions: int = Field(default=0, description="Number of lines added")
    deletions: int = Field(default=0, description="Number of lines deleted")
    changes: int = Field(default=0, description="Total number of changes")
    blob_url: Optional[str] = Field(None, description="URL to blob")
    raw_url: Optional[str] = Field(None, description="URL to raw file")
    contents_url: Optional[str] = Field(None, description="URL to file contents")
    patch: Optional[str] = Field(None, description="Unified diff patch")
    content: Optional[str] = Field(None, description="File content (if requested)")
    content_before: Optional[str] = Field(None, description="File content before changes")
    content_after: Optional[str] = Field(None, description="File content after changes")


class AgentDefinition(BaseModel):
    """Definition of an AI agent for handling events."""
    
    agent: Dict[str, Any] = Field(..., description="Agent metadata")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    triggers: AgentTriggerCondition = Field(default_factory=AgentTriggerCondition, description="When to run this agent")
    prompt_template: str = Field(..., description="Jinja2 template for the agent prompt")
    mcp_servers: List[McpServerConfig] = Field(default_factory=list, description="MCP servers for this agent")
    output: AgentOutputConfig = Field(default_factory=AgentOutputConfig, description="Output configuration")
    branch_automation: Optional[AgentBranchAutomation] = Field(None, description="Branch automation configuration")
    enabled: bool = Field(default=True, description="Whether the agent is enabled")
    priority: int = Field(default=100, description="Execution priority (lower = higher priority)")


class GitHubCommit(BaseModel):
    """Model for Git commit information."""
    
    sha: str = Field(..., description="Commit SHA hash")
    message: str = Field(..., description="Commit message")
    author_name: str = Field(..., description="Author name")
    author_email: str = Field(..., description="Author email")
    committer_name: str = Field(..., description="Committer name")
    committer_email: str = Field(..., description="Committer email")
    timestamp: datetime = Field(..., description="Commit timestamp")
    url: Optional[str] = Field(None, description="Commit URL")


class GitHubBranch(BaseModel):
    """Model for Git branch information."""
    
    name: str = Field(..., description="Branch name")
    ref: str = Field(..., description="Git reference")
    sha: str = Field(..., description="Branch HEAD SHA")
    protected: Optional[bool] = Field(None, description="Is branch protected")


class GitHubRepository(BaseModel):
    """Model for GitHub repository information."""
    
    id: int = Field(..., description="Repository ID")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Repository full name (owner/repo)")
    owner: Dict[str, Any] = Field(..., description="Repository owner information")
    private: bool = Field(..., description="Is repository private")
    html_url: str = Field(..., description="Repository HTML URL")
    description: Optional[str] = Field(None, description="Repository description")
    fork: bool = Field(..., description="Is repository a fork")
    created_at: datetime = Field(..., description="Repository creation timestamp")
    updated_at: datetime = Field(..., description="Repository last update timestamp")
    pushed_at: Optional[datetime] = Field(None, description="Repository last push timestamp")
    stargazers_count: int = Field(0, description="Number of stars")
    watchers_count: int = Field(0, description="Number of watchers")
    language: Optional[str] = Field(None, description="Primary language")
    forks_count: int = Field(0, description="Number of forks")
    open_issues_count: int = Field(0, description="Number of open issues")
    default_branch: str = Field("main", description="Default branch name")


class GitHubUser(BaseModel):
    """Model for GitHub user information."""
    
    login: str = Field(..., description="User login/username")
    id: int = Field(..., description="User ID")
    type: str = Field(..., description="User type (User, Bot, Organization)")
    site_admin: bool = Field(False, description="Is site admin")
    name: Optional[str] = Field(None, description="User display name")
    email: Optional[str] = Field(None, description="User email")


class GitHubWorkflow(BaseModel):
    """Model for GitHub workflow information."""
    
    id: int = Field(..., description="Workflow ID")
    name: str = Field(..., description="Workflow name")
    path: str = Field(..., description="Workflow file path")
    state: str = Field(..., description="Workflow state")
    created_at: datetime = Field(..., description="Workflow creation timestamp")
    updated_at: datetime = Field(..., description="Workflow last update timestamp")
    url: str = Field(..., description="Workflow API URL")
    html_url: str = Field(..., description="Workflow HTML URL")
    badge_url: str = Field(..., description="Workflow badge URL")


class GitHubWorkflowRun(BaseModel):
    """Model for GitHub workflow run information."""
    
    id: int = Field(..., description="Workflow run ID")
    name: str = Field(..., description="Workflow run name")
    head_branch: str = Field(..., description="Head branch")
    head_sha: str = Field(..., description="Head commit SHA")
    path: str = Field(..., description="Workflow file path")
    run_number: int = Field(..., description="Workflow run number")
    event: str = Field(..., description="Triggering event")
    status: str = Field(..., description="Workflow run status")
    conclusion: Optional[str] = Field(None, description="Workflow run conclusion")
    workflow_id: int = Field(..., description="Workflow ID")
    url: str = Field(..., description="Workflow run API URL")
    html_url: str = Field(..., description="Workflow run HTML URL")
    created_at: datetime = Field(..., description="Workflow run creation timestamp")
    updated_at: datetime = Field(..., description="Workflow run last update timestamp")
    run_started_at: Optional[datetime] = Field(None, description="Workflow run start timestamp")
    actor: GitHubUser = Field(..., description="Workflow run actor")


class GitHubWorkflowJob(BaseModel):
    """Model for GitHub workflow job information."""
    
    id: int = Field(..., description="Job ID")
    run_id: int = Field(..., description="Workflow run ID")
    run_url: str = Field(..., description="Workflow run URL")
    node_id: str = Field(..., description="Job node ID")
    head_sha: str = Field(..., description="Head commit SHA")
    url: str = Field(..., description="Job API URL")
    html_url: str = Field(..., description="Job HTML URL")
    status: str = Field(..., description="Job status")
    conclusion: Optional[str] = Field(None, description="Job conclusion")
    started_at: datetime = Field(..., description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    name: str = Field(..., description="Job name")


class GitHubPullRequest(BaseModel):
    """Model for GitHub pull request information."""
    
    id: int = Field(..., description="Pull request ID")
    number: int = Field(..., description="Pull request number")
    state: str = Field(..., description="Pull request state")
    title: str = Field(..., description="Pull request title")
    body: Optional[str] = Field(None, description="Pull request body")
    user: GitHubUser = Field(..., description="Pull request author")
    created_at: datetime = Field(..., description="Pull request creation timestamp")
    updated_at: datetime = Field(..., description="Pull request last update timestamp")
    closed_at: Optional[datetime] = Field(None, description="Pull request close timestamp")
    merged_at: Optional[datetime] = Field(None, description="Pull request merge timestamp")
    head: Dict[str, Any] = Field(..., description="Head branch information")
    base: Dict[str, Any] = Field(..., description="Base branch information")
    draft: bool = Field(False, description="Is pull request a draft")
    mergeable: Optional[bool] = Field(None, description="Is pull request mergeable")


class GitHubIssue(BaseModel):
    """Model for GitHub issue information."""
    
    id: int = Field(..., description="Issue ID")
    number: int = Field(..., description="Issue number")
    title: str = Field(..., description="Issue title")
    body: Optional[str] = Field(None, description="Issue body")
    state: str = Field(..., description="Issue state")
    user: GitHubUser = Field(..., description="Issue author")
    assignee: Optional[GitHubUser] = Field(None, description="Issue assignee")
    assignees: List[GitHubUser] = Field(default_factory=list, description="Issue assignees")
    labels: List[Dict[str, Any]] = Field(default_factory=list, description="Issue labels")
    created_at: datetime = Field(..., description="Issue creation timestamp")
    updated_at: datetime = Field(..., description="Issue last update timestamp")
    closed_at: Optional[datetime] = Field(None, description="Issue close timestamp")


class CommitHistory(BaseModel):
    """Model for commit history context."""
    
    branch: str = Field(..., description="Current branch name")
    total_commits: int = Field(..., description="Total number of commits retrieved")
    commits: List[GitHubCommit] = Field(..., description="List of commits")
    head_sha: str = Field(..., description="HEAD commit SHA")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow, description="When history was retrieved")


class GitHubActionContext(BaseModel):
    """Model for GitHub Action execution context."""
    
    event_name: str = Field(..., description="GitHub event name")
    workflow: str = Field(..., description="Workflow name")
    job: str = Field(..., description="Job name")
    run_id: str = Field(..., description="Workflow run ID")
    run_number: int = Field(..., description="Workflow run number")
    actor: str = Field(..., description="Actor who triggered the workflow")
    repository: str = Field(..., description="Repository name")
    ref: str = Field(..., description="Git reference")
    sha: str = Field(..., description="Commit SHA")
    workspace: str = Field(..., description="Workspace directory")
    server_url: str = Field(..., description="GitHub server URL")
    api_url: str = Field(..., description="GitHub API URL")
    graphql_url: str = Field(..., description="GitHub GraphQL URL")


class AgentExecutionResult(BaseModel):
    """Result of executing an AI agent."""
    
    agent_name: str = Field(..., description="Name of the executed agent")
    agent_type: AgentType = Field(..., description="Type of agent")
    success: bool = Field(..., description="Whether execution was successful")
    output: str = Field(default="", description="Agent output")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    output_destination: OutputDestination = Field(..., description="Where output was sent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Branch automation results
    branch_created: Optional[str] = Field(None, description="Name of branch created (if any)")
    pr_created: Optional[int] = Field(None, description="PR number created (if any)")
    pr_url: Optional[str] = Field(None, description="URL of created PR (if any)")
    files_changed: List[FileChange] = Field(default_factory=list, description="Files that triggered this agent")
    
    # GitHub integration results
    status_check_posted: Optional[str] = Field(None, description="Status check state posted (success/failure/pending)")
    comment_posted: Optional[str] = Field(None, description="URL of comment posted (if any)")
    issue_created: Optional[int] = Field(None, description="Issue number created (if any)")
    issue_url: Optional[str] = Field(None, description="URL of created issue (if any)")
    
    # Claude Code SDK specific results
    session_id: Optional[str] = Field(None, description="Claude Code SDK session ID")
    total_cost_usd: Optional[float] = Field(None, description="Total cost in USD")
    num_turns: Optional[int] = Field(None, description="Number of conversation turns")
    duration_api_ms: Optional[float] = Field(None, description="API duration in milliseconds")


class ClaudeCodeSDKMessage(BaseModel):
    """Model for Claude Code SDK messages."""
    
    type: str = Field(..., description="Message type (user, assistant, result, system)")
    subtype: Optional[str] = Field(None, description="Message subtype")
    session_id: Optional[str] = Field(None, description="Session ID")
    message: Optional[Dict[str, Any]] = Field(None, description="Message content")
    duration_ms: Optional[float] = Field(None, description="Duration in milliseconds")
    duration_api_ms: Optional[float] = Field(None, description="API duration in milliseconds")
    is_error: Optional[bool] = Field(None, description="Whether this is an error message")
    num_turns: Optional[int] = Field(None, description="Number of turns")
    result: Optional[str] = Field(None, description="Result text")
    total_cost_usd: Optional[float] = Field(None, description="Total cost in USD")
    
    # System message specific fields
    api_key_source: Optional[str] = Field(None, description="API key source")
    cwd: Optional[str] = Field(None, description="Working directory")
    tools: Optional[List[str]] = Field(None, description="Available tools")
    mcp_servers: Optional[List[Dict[str, Any]]] = Field(None, description="MCP servers")
    model: Optional[str] = Field(None, description="Model name")
    permission_mode: Optional[str] = Field(None, description="Permission mode")


class GitHubEvent(BaseModel):
    """Base model for GitHub events with flexible field support."""
    
    action: Optional[str] = Field(None, description="Event action")
    repository: Optional[GitHubRepository] = Field(None, description="Repository information")
    sender: Optional[GitHubUser] = Field(None, description="Event sender")
    
    # Additional fields for different event types
    workflow: Optional[GitHubWorkflow] = Field(None, description="Workflow information")
    workflow_run: Optional[GitHubWorkflowRun] = Field(None, description="Workflow run information")
    workflow_job: Optional[GitHubWorkflowJob] = Field(None, description="Workflow job information")
    pull_request: Optional[GitHubPullRequest] = Field(None, description="Pull request information")
    issue: Optional[GitHubIssue] = Field(None, description="Issue information")
    
    # Flexible fields for other event-specific data
    commits: Optional[List[Dict[str, Any]]] = Field(None, description="Commit information")
    head_commit: Optional[Dict[str, Any]] = Field(None, description="Head commit information")
    ref: Optional[str] = Field(None, description="Git reference")
    before: Optional[str] = Field(None, description="Before commit SHA")
    after: Optional[str] = Field(None, description="After commit SHA")
    
    # Allow additional fields
    model_config = {"extra": "allow"}


class EventProcessingResult(BaseModel):
    """Model for event processing results."""
    
    event_type: str = Field(..., description="Type of GitHub event processed")
    processing_time: float = Field(..., description="Time taken to process event in seconds")
    success: bool = Field(..., description="Whether processing was successful")
    message: str = Field(..., description="Processing result message")
    commit_history: Optional[CommitHistory] = Field(None, description="Commit history context")
    github_context: Optional[GitHubActionContext] = Field(None, description="GitHub Action context")
    agent_results: List[AgentExecutionResult] = Field(default_factory=list, description="Results from executed agents")
    agents_discovered: int = Field(default=0, description="Number of agents discovered")
    agents_executed: int = Field(default=0, description="Number of agents executed")
    error: Optional[str] = Field(None, description="Error message if processing failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class HealthCheck(BaseModel):
    """Model for basic health check response."""
    
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    uptime: Optional[str] = Field(None, description="Service uptime")


class DetailedHealthCheck(HealthCheck):
    """Model for detailed health check response."""
    
    system: Dict[str, Any] = Field(default_factory=dict, description="System metrics")
    application: Dict[str, Any] = Field(default_factory=dict, description="Application metrics")
    github_api: Dict[str, Any] = Field(default_factory=dict, description="GitHub API status")
    agents: Dict[str, Any] = Field(default_factory=dict, description="Agent CLI status")


class EventStatistics(BaseModel):
    """Model for event processing statistics."""
    
    total_events: int = Field(0, description="Total events processed")
    successful_events: int = Field(0, description="Successfully processed events")
    failed_events: int = Field(0, description="Failed event processing attempts")
    events_per_second: float = Field(0.0, description="Average events processed per second")
    processing_times: Dict[str, float] = Field(default_factory=dict, description="Processing time statistics")
    event_types: Dict[str, int] = Field(default_factory=dict, description="Event type counts")
    agent_statistics: Dict[str, Any] = Field(default_factory=dict, description="Agent execution statistics")
    last_processed: Optional[datetime] = Field(None, description="Last event processing timestamp")
    uptime: Optional[str] = Field(None, description="Service uptime")


class ConfigurationInfo(BaseModel):
    """Model for configuration information (sanitized)."""
    
    log_level: str = Field(..., description="Current log level")
    log_format: str = Field(..., description="Current log format")
    max_concurrent_events: int = Field(..., description="Maximum concurrent events")
    event_timeout_seconds: int = Field(..., description="Event timeout in seconds")
    background_tasks: bool = Field(..., description="Background tasks enabled")
    metrics_enabled: bool = Field(..., description="Metrics collection enabled")
    health_check_enabled: bool = Field(..., description="Health checks enabled")
    event_storage_enabled: bool = Field(..., description="Event storage enabled")
    enabled_events: Optional[List[str]] = Field(None, description="Enabled event types")
    disabled_events: Optional[List[str]] = Field(None, description="Disabled event types")
    agents_directory: str = Field(..., description="Agents configuration directory")
    configured_agents: Dict[str, int] = Field(default_factory=dict, description="Number of configured agents by type")
    agent_clis: Dict[str, bool] = Field(default_factory=dict, description="Available agent CLIs") 