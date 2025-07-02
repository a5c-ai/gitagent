"""
Configuration management for GitHub Action Handler.

This module handles all configuration settings for the GitHub Action Handler,
using environment variables and providing validation.
"""

import os
from typing import List, Optional, Set
from pathlib import Path

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """GitHub Action Handler configuration settings."""
    
    # GitHub Configuration
    github_token: Optional[str] = Field(
        default=None,
        env="GITHUB_TOKEN",
        description="GitHub personal access token for API access"
    )
    
    # Server Configuration
    port: int = Field(
        default=8000,
        env="PORT",
        description="Port to run the server on"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    log_format: str = Field(
        default="json",
        env="LOG_FORMAT",
        description="Log format (json, console)"
    )
    
    structured_logging: bool = Field(
        default=True,
        env="STRUCTURED_LOGGING",
        description="Enable structured logging"
    )
    
    log_file_path: Optional[str] = Field(
        default=None,
        env="LOG_FILE_PATH",
        description="Path to log file (optional)"
    )
    
    # Processing Configuration
    max_concurrent_events: int = Field(
        default=10,
        env="MAX_CONCURRENT_EVENTS",
        description="Maximum number of concurrent event processing tasks"
    )
    
    event_timeout_seconds: int = Field(
        default=30,
        env="EVENT_TIMEOUT_SECONDS",
        description="Timeout for event processing in seconds"
    )
    
    background_tasks: bool = Field(
        default=True,
        env="BACKGROUND_TASKS",
        description="Enable background task processing"
    )
    
    # Feature Configuration
    metrics_enabled: bool = Field(
        default=True,
        env="METRICS_ENABLED",
        description="Enable metrics collection and endpoint"
    )
    
    health_check_enabled: bool = Field(
        default=True,
        env="HEALTH_CHECK_ENABLED",
        description="Enable health check endpoints"
    )
    
    development_mode: bool = Field(
        default=False,
        env="DEVELOPMENT_MODE",
        description="Enable development mode (exposes docs, detailed errors)"
    )
    
    # Event Configuration
    enabled_events: Optional[List[str]] = Field(
        default=None,
        env="ENABLED_EVENTS",
        description="Comma-separated list of enabled event types (empty means all)"
    )
    
    disabled_events: Optional[List[str]] = Field(
        default=None,
        env="DISABLED_EVENTS", 
        description="Comma-separated list of disabled event types"
    )
    
    # Event Storage Configuration
    event_storage_enabled: bool = Field(
        default=False,
        env="EVENT_STORAGE_ENABLED",
        description="Enable event storage to disk"
    )
    
    event_storage_path: str = Field(
        default="/app/data/events",
        env="EVENT_STORAGE_PATH",
        description="Path to store event data"
    )
    
    # Git Configuration
    git_commit_history_count: int = Field(
        default=10,
        env="GIT_COMMIT_HISTORY_COUNT",
        description="Number of commits to retrieve for history context"
    )
    
    git_timeout_seconds: int = Field(
        default=30,
        env="GIT_TIMEOUT_SECONDS",
        description="Timeout for git operations in seconds"
    )
    
    # GitHub Action Context (these are typically set by GitHub Actions)
    github_workspace: Optional[str] = Field(
        default=None,
        env="GITHUB_WORKSPACE",
        description="GitHub Actions workspace directory"
    )
    
    github_event_name: Optional[str] = Field(
        default=None,
        env="GITHUB_EVENT_NAME",
        description="GitHub event name that triggered the workflow"
    )
    
    github_event_path: Optional[str] = Field(
        default=None,
        env="GITHUB_EVENT_PATH",
        description="Path to the event payload file"
    )
    
    github_workflow: Optional[str] = Field(
        default=None,
        env="GITHUB_WORKFLOW",
        description="GitHub workflow name"
    )
    
    github_job: Optional[str] = Field(
        default=None,
        env="GITHUB_JOB",
        description="GitHub job name"
    )
    
    github_run_id: Optional[str] = Field(
        default=None,
        env="GITHUB_RUN_ID",
        description="GitHub workflow run ID"
    )
    
    github_run_number: Optional[int] = Field(
        default=None,
        env="GITHUB_RUN_NUMBER",
        description="GitHub workflow run number"
    )
    
    github_actor: Optional[str] = Field(
        default=None,
        env="GITHUB_ACTOR",
        description="GitHub actor who triggered the workflow"
    )
    
    github_repository: Optional[str] = Field(
        default=None,
        env="GITHUB_REPOSITORY",
        description="GitHub repository name (owner/repo)"
    )
    
    github_ref: Optional[str] = Field(
        default=None,
        env="GITHUB_REF",
        description="GitHub reference (branch or tag)"
    )
    
    github_sha: Optional[str] = Field(
        default=None,
        env="GITHUB_SHA",
        description="GitHub commit SHA"
    )
    
    github_server_url: str = Field(
        default="https://github.com",
        env="GITHUB_SERVER_URL",
        description="GitHub server URL"
    )
    
    github_api_url: str = Field(
        default="https://api.github.com",
        env="GITHUB_API_URL",
        description="GitHub API URL"
    )
    
    github_graphql_url: str = Field(
        default="https://api.github.com/graphql",
        env="GITHUB_GRAPHQL_URL",
        description="GitHub GraphQL URL"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    @validator("log_format")
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = {"json", "console"}
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid log format: {v}. Must be one of: {', '.join(valid_formats)}")
        return v.lower()
    
    @validator("port")
    def validate_port(cls, v):
        """Validate port number."""
        if not (1 <= v <= 65535):
            raise ValueError(f"Invalid port: {v}. Must be between 1 and 65535")
        return v
    
    @validator("max_concurrent_events")
    def validate_max_concurrent_events(cls, v):
        """Validate max concurrent events."""
        if v < 1:
            raise ValueError(f"Invalid max_concurrent_events: {v}. Must be at least 1")
        return v
    
    @validator("event_timeout_seconds")
    def validate_event_timeout(cls, v):
        """Validate event timeout."""
        if v < 1:
            raise ValueError(f"Invalid event_timeout_seconds: {v}. Must be at least 1")
        return v
    
    @validator("git_commit_history_count")
    def validate_git_commit_history_count(cls, v):
        """Validate git commit history count."""
        if not (1 <= v <= 100):
            raise ValueError(f"Invalid git_commit_history_count: {v}. Must be between 1 and 100")
        return v
    
    @validator("enabled_events", pre=True)
    def parse_enabled_events(cls, v):
        """Parse comma-separated enabled events."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return [event.strip() for event in v.split(",") if event.strip()]
        return v
    
    @validator("disabled_events", pre=True)
    def parse_disabled_events(cls, v):
        """Parse comma-separated disabled events."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return [event.strip() for event in v.split(",") if event.strip()]
        return v
    
    def get_enabled_event_types(self) -> Optional[Set[str]]:
        """Get enabled event types as a set."""
        if self.enabled_events is None:
            return None
        return set(self.enabled_events)
    
    def get_disabled_event_types(self) -> Set[str]:
        """Get disabled event types as a set."""
        if self.disabled_events is None:
            return set()
        return set(self.disabled_events)
    
    def is_event_enabled(self, event_type: str) -> bool:
        """Check if an event type is enabled."""
        # Check disabled events first
        if event_type in self.get_disabled_event_types():
            return False
        
        # If enabled events is specified, only allow those
        enabled_events = self.get_enabled_event_types()
        if enabled_events is not None:
            return event_type in enabled_events
        
        # Default to enabled
        return True
    
    def get_log_file_path(self) -> Optional[Path]:
        """Get log file path as Path object."""
        if self.log_file_path is None:
            return None
        return Path(self.log_file_path)
    
    def get_event_storage_path(self) -> Path:
        """Get event storage path as Path object."""
        return Path(self.event_storage_path)
    
    def ensure_event_storage_directory(self) -> None:
        """Ensure event storage directory exists."""
        if self.event_storage_enabled:
            storage_path = self.get_event_storage_path()
            storage_path.mkdir(parents=True, exist_ok=True)
    
    def get_github_workspace_path(self) -> Optional[Path]:
        """Get GitHub workspace path as Path object."""
        if self.github_workspace is None:
            return None
        return Path(self.github_workspace)
    
    def get_github_event_payload(self) -> Optional[dict]:
        """Get GitHub event payload from file."""
        if self.github_event_path is None:
            return None
        
        try:
            event_path = Path(self.github_event_path)
            if event_path.exists():
                import json
                with open(event_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        
        return None
    
    def is_github_actions_context(self) -> bool:
        """Check if running in GitHub Actions context."""
        return (
            self.github_event_name is not None and
            self.github_workflow is not None and
            self.github_repository is not None
        )
    
    def get_summary(self) -> dict:
        """Get configuration summary (sanitized for logging)."""
        return {
            "log_level": self.log_level,
            "log_format": self.log_format,
            "port": self.port,
            "max_concurrent_events": self.max_concurrent_events,
            "event_timeout_seconds": self.event_timeout_seconds,
            "background_tasks": self.background_tasks,
            "metrics_enabled": self.metrics_enabled,
            "health_check_enabled": self.health_check_enabled,
            "event_storage_enabled": self.event_storage_enabled,
            "git_commit_history_count": self.git_commit_history_count,
            "github_actions_context": self.is_github_actions_context(),
            "github_repository": self.github_repository,
            "github_event_name": self.github_event_name,
            "enabled_events_count": len(self.enabled_events) if self.enabled_events else None,
            "disabled_events_count": len(self.disabled_events) if self.disabled_events else None,
        }


# Global settings instance
settings = Settings() 