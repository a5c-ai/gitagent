"""
Configuration management for gitagent using Pydantic Settings.
"""

import os
from typing import Dict, List, Optional, Set

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from .models import AgentCliConfiguration, ClaudeCodeSDKConfiguration


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # GitHub Configuration
    github_token: str = Field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN", ""),
        description="GitHub personal access token"
    )
    github_repository: str = Field(
        default_factory=lambda: os.getenv("GITHUB_REPOSITORY", ""),
        description="GitHub repository in format owner/repo"
    )
    github_workspace: str = Field(
        default_factory=lambda: os.getenv("GITHUB_WORKSPACE", "."),
        description="GitHub workspace directory"
    )
    github_event_name: str = Field(
        default_factory=lambda: os.getenv("GITHUB_EVENT_NAME", ""),
        description="GitHub event name"
    )
    github_event_path: str = Field(
        default_factory=lambda: os.getenv("GITHUB_EVENT_PATH", ""),
        description="Path to GitHub event JSON file"
    )
    github_ref: str = Field(
        default_factory=lambda: os.getenv("GITHUB_REF", ""),
        description="GitHub reference (branch/tag)"
    )
    github_sha: str = Field(
        default_factory=lambda: os.getenv("GITHUB_SHA", ""),
        description="GitHub commit SHA"
    )
    github_workflow: str = Field(
        default_factory=lambda: os.getenv("GITHUB_WORKFLOW", ""),
        description="GitHub workflow name"
    )
    github_job: str = Field(
        default_factory=lambda: os.getenv("GITHUB_JOB", ""),
        description="GitHub job name"
    )
    github_run_id: str = Field(
        default_factory=lambda: os.getenv("GITHUB_RUN_ID", ""),
        description="GitHub workflow run ID"
    )
    github_run_number: int = Field(
        default_factory=lambda: int(os.getenv("GITHUB_RUN_NUMBER", "0")),
        description="GitHub workflow run number"
    )
    github_actor: str = Field(
        default_factory=lambda: os.getenv("GITHUB_ACTOR", ""),
        description="GitHub actor who triggered the workflow"
    )
    github_server_url: str = Field(
        default="https://github.com",
        description="GitHub server URL"
    )
    github_api_url: str = Field(
        default="https://api.github.com",
        description="GitHub API URL"
    )
    github_graphql_url: str = Field(
        default="https://api.github.com/graphql",
        description="GitHub GraphQL URL"
    )
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json, console)")
    log_file: Optional[str] = Field(None, description="Log file path")
    structured_logging: bool = Field(default=True, description="Enable structured logging")
    
    # Processing Configuration
    max_concurrent_events: int = Field(default=10, description="Maximum concurrent event processing")
    event_timeout_seconds: int = Field(default=30, description="Event processing timeout")
    background_tasks: bool = Field(default=True, description="Enable background task processing")
    commit_history_count: int = Field(default=10, description="Number of commits to retrieve for context")
    
    # Feature Toggles
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    health_check_enabled: bool = Field(default=True, description="Enable health check endpoints")
    event_storage_enabled: bool = Field(default=False, description="Enable event storage")
    event_storage_path: str = Field(default="/tmp/events", description="Path to store event data")
    
    # Event Configuration
    enabled_events: Optional[List[str]] = Field(None, description="Enabled event types (empty = all)")
    disabled_events: Optional[List[str]] = Field(default_factory=list, description="Disabled event types")
    
    # Agent Configuration
    agents_directory: str = Field(
        default=".github/action-handlers",
        description="Directory containing agent configuration files"
    )
    agents_enabled: bool = Field(default=True, description="Enable agent processing")
    
    # Agent CLI Configurations
    claude_code_sdk: Optional[ClaudeCodeSDKConfiguration] = Field(None, description="Claude Code SDK configuration")
    cli: Optional[AgentCliConfiguration] = Field(None, description="Custom CLI configuration")
    
    # Agent CLI Environment Variables
    gemini_api_key: Optional[str] = Field(default=os.getenv("GEMINI_API_KEY", ""), description="Gemini API key")
    claude_api_key: Optional[str] = Field(default=os.getenv("CLAUDE_API_KEY", ""), description="Claude API key")
    openai_api_key: Optional[str] = Field(default=os.getenv("OPENAI_API_KEY", ""), description="OpenAI API key (used for Codex agents)")
    anthropic_api_key: Optional[str] = Field(default=os.getenv("ANTHROPIC_API_KEY", ""), description="Anthropic API key")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = {"json", "console"}
        if v.lower() not in valid_formats:
            raise ValueError(f"Log format must be one of: {', '.join(valid_formats)}")
        return v.lower()
    
    @field_validator("max_concurrent_events")
    @classmethod
    def validate_max_concurrent_events(cls, v):
        """Validate max concurrent events."""
        if v < 1 or v > 100:
            raise ValueError("Max concurrent events must be between 1 and 100")
        return v
    
    @field_validator("event_timeout_seconds")
    @classmethod
    def validate_event_timeout(cls, v):
        """Validate event timeout."""
        if v < 1 or v > 3600:
            raise ValueError("Event timeout must be between 1 and 3600 seconds")
        return v
    
    @field_validator("commit_history_count")
    @classmethod
    def validate_commit_history_count(cls, v):
        """Validate commit history count."""
        if v < 1 or v > 100:
            raise ValueError("Commit history count must be between 1 and 100")
        return v
    
    def get_enabled_events(self) -> Optional[Set[str]]:
        """Get set of enabled events."""
        if self.enabled_events:
            return set(self.enabled_events)
        return None
    
    def get_disabled_events(self) -> Set[str]:
        """Get set of disabled events."""
        return set(self.disabled_events or [])
    
    def is_event_enabled(self, event_type: str) -> bool:
        """Check if an event type is enabled."""
        disabled = self.get_disabled_events()
        if event_type in disabled:
            return False
        
        enabled = self.get_enabled_events()
        if enabled is None:
            return True
        
        return event_type in enabled
    
    def get_github_context(self) -> Dict[str, str]:
        """Get GitHub context information."""
        return {
            "repository": self.github_repository,
            "workspace": self.github_workspace,
            "event_name": self.github_event_name,
            "event_path": self.github_event_path,
            "ref": self.github_ref,
            "sha": self.github_sha,
            "workflow": self.github_workflow,
            "job": self.github_job,
            "run_id": self.github_run_id,
            "run_number": str(self.github_run_number),
            "actor": self.github_actor,
            "server_url": self.github_server_url,
            "api_url": self.github_api_url,
            "graphql_url": self.github_graphql_url,
        }
    
    def get_agent_cli_config(self, agent_type: str) -> Optional[AgentCliConfiguration]:
        """Get agent CLI configuration by type."""
        configs = {
            "codex": self.codex_cli,
            "gemini": self.gemini_cli,
            "claude": self.claude_cli,
            "claude_code_sdk": self.claude_code_sdk,
            "custom": self.custom_cli,
        }
        return configs.get(agent_type.lower())
    
    def get_claude_code_sdk_config(self) -> Optional[ClaudeCodeSDKConfiguration]:
        """Get Claude Code SDK configuration."""
        return self.claude_code_sdk
    
    def get_agent_api_key(self, agent_type: str) -> Optional[str]:
        """Get API key for agent type."""
        keys = {
            "codex": self.openai_api_key,
            "gemini": self.gemini_api_key,
            "claude": self.claude_api_key or self.anthropic_api_key,
            "claude_code_sdk": self.claude_api_key or self.anthropic_api_key,
        }
        return keys.get(agent_type.lower())
    
    def setup_default_agent_configs(self):
        """Set up default agent CLI configurations."""
        # Codex CLI configuration
        if not self.codex_cli and self.openai_api_key:
            self.codex_cli = AgentCliConfiguration(
                executable_path="codex",
                api_key_env="OPENAI_API_KEY",  # Codex uses OpenAI API key
                model="code-davinci-002",
                max_tokens=2048,
                timeout_seconds=300
            )
        
        # Gemini CLI configuration
        if not self.gemini_cli and self.gemini_api_key:
            self.gemini_cli = AgentCliConfiguration(
                executable_path="gemini",
                api_key_env="GEMINI_API_KEY",
                model="gemini-pro",
                max_tokens=2048,
                timeout_seconds=300
            )
        
        # Claude Code configuration
        if not self.claude_cli and (self.claude_api_key or self.anthropic_api_key):
            self.claude_cli = AgentCliConfiguration(
                executable_path="claude",
                api_key_env="CLAUDE_API_KEY",
                model="claude-3-sonnet-20241022",
                max_tokens=4000,
                timeout_seconds=300
            )
        
        # Claude Code SDK configuration
        if not self.claude_code_sdk and (self.claude_api_key or self.anthropic_api_key):
            self.claude_code_sdk = ClaudeCodeSDKConfiguration(
                api_key=self.claude_api_key or self.anthropic_api_key,
                api_key_env="CLAUDE_API_KEY",
                model="claude-3-sonnet-20241022",
                max_tokens=4000,
                temperature=0.1,
                timeout_seconds=300,
                max_turns=10,
                output_format="text",
                cwd=self.github_workspace
            )
        

    
    def get_available_agent_types(self) -> List[str]:
        """Get list of available agent types."""
        available = []
        if self.codex_cli or self.openai_api_key:
            available.append("codex")
        if self.gemini_cli or self.gemini_api_key:
            available.append("gemini")
        if self.claude_cli or self.claude_api_key or self.anthropic_api_key:
            available.append("claude")
        if self.claude_code_sdk or self.claude_api_key or self.anthropic_api_key:
            available.append("claude_code_sdk")
        if self.custom_cli:
            available.append("custom")
        return available


# Global settings instance
settings = Settings()

# Set up default agent configurations
settings.setup_default_agent_configs() 