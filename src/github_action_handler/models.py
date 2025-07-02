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
    class Config:
        extra = "allow"


class EventProcessingResult(BaseModel):
    """Model for event processing results."""
    
    event_type: str = Field(..., description="Type of GitHub event processed")
    processing_time: float = Field(..., description="Time taken to process event in seconds")
    success: bool = Field(..., description="Whether processing was successful")
    message: str = Field(..., description="Processing result message")
    commit_history: Optional[CommitHistory] = Field(None, description="Commit history context")
    github_context: Optional[GitHubActionContext] = Field(None, description="GitHub Action context")
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


class EventStatistics(BaseModel):
    """Model for event processing statistics."""
    
    total_events: int = Field(0, description="Total events processed")
    successful_events: int = Field(0, description="Successfully processed events")
    failed_events: int = Field(0, description="Failed event processing attempts")
    events_per_second: float = Field(0.0, description="Average events processed per second")
    processing_times: Dict[str, float] = Field(default_factory=dict, description="Processing time statistics")
    event_types: Dict[str, int] = Field(default_factory=dict, description="Event type counts")
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