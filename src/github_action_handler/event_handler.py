"""
Core event processing logic for GitHub Action Handler.

This module provides the main event processing functionality with commit history context
and pluggable event handlers for different GitHub event types.
"""

import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
import asyncio
import time

import structlog
from github import Github

from .config import Settings
from .models import (
    GitHubEvent,
    EventProcessingResult,
    GitHubActionTrigger,
    CommitHistory,
    GitHubCommit,
    GitHubActionContext,
)

logger = structlog.get_logger(__name__)


class EventHandler(Protocol):
    """Protocol for event handlers."""
    
    async def handle(self, event: GitHubEvent, context: GitHubActionContext) -> EventProcessingResult:
        """Handle a GitHub event with context."""
        ...


class BaseEventHandler:
    """Base class for event handlers."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger(self.__class__.__name__)
    
    async def handle(self, event: GitHubEvent, context: GitHubActionContext) -> EventProcessingResult:
        """Handle a GitHub event. Override this method in subclasses."""
        start_time = time.time()
        
        try:
            # Get commit history for context
            commit_history = await self._get_commit_history(context)
            
            # Process the event (stub implementation)
            result = await self._process_event(event, context, commit_history)
            
            processing_time = time.time() - start_time
            
            return EventProcessingResult(
                event_type=context.event_name,
                processing_time=processing_time,
                success=True,
                message=f"Successfully processed {context.event_name} event",
                commit_history=commit_history,
                github_context=context,
                metadata=result
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error("Event processing failed", event_type=context.event_name, error=str(e))
            
            return EventProcessingResult(
                event_type=context.event_name,
                processing_time=processing_time,
                success=False,
                message=f"Failed to process {context.event_name} event",
                error=str(e),
                github_context=context
            )
    
    async def _process_event(self, event: GitHubEvent, context: GitHubActionContext, commit_history: CommitHistory) -> Dict[str, Any]:
        """Process the event. Override this method in subclasses for specific event handling."""
        self.logger.info(
            "Processing event (stub implementation)",
            event_type=context.event_name,
            repository=context.repository,
            actor=context.actor,
            commit_count=commit_history.total_commits if commit_history else 0
        )
        
        return {
            "handler": self.__class__.__name__,
            "event_processed": True,
            "processing_note": "This is a stub implementation - extend this class for specific event handling"
        }
    
    async def _get_commit_history(self, context: GitHubActionContext, count: int = 10) -> Optional[CommitHistory]:
        """Get commit history for the current branch."""
        try:
            # Get current branch from context
            branch = self._extract_branch_name(context.ref)
            
            # Get commit history using git commands
            commits = await self._get_git_commits(branch, count)
            
            if not commits:
                return None
            
            return CommitHistory(
                branch=branch,
                total_commits=len(commits),
                commits=commits,
                head_sha=context.sha,
                retrieved_at=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.warning("Failed to get commit history", error=str(e))
            return None
    
    def _extract_branch_name(self, ref: str) -> str:
        """Extract branch name from git reference."""
        if ref.startswith("refs/heads/"):
            return ref[11:]  # Remove "refs/heads/"
        elif ref.startswith("refs/tags/"):
            return ref[10:]   # Remove "refs/tags/"
        else:
            return ref
    
    async def _get_git_commits(self, branch: str, count: int) -> List[GitHubCommit]:
        """Get git commits using git log command."""
        try:
            # Use git log to get commit history
            cmd = [
                "git", "log", 
                f"-{count}",
                "--pretty=format:%H|%s|%an|%ae|%cn|%ce|%ai",
                branch
            ]
            
            # Run git command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.logger.warning("Git command failed", stderr=stderr.decode())
                return []
            
            # Parse git log output
            commits = []
            for line in stdout.decode().strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split('|')
                if len(parts) >= 7:
                    commit = GitHubCommit(
                        sha=parts[0],
                        message=parts[1],
                        author_name=parts[2],
                        author_email=parts[3],
                        committer_name=parts[4],
                        committer_email=parts[5],
                        timestamp=datetime.fromisoformat(parts[6].replace('Z', '+00:00'))
                    )
                    commits.append(commit)
            
            return commits
            
        except Exception as e:
            self.logger.error("Failed to get git commits", error=str(e))
            return []


class WorkflowEventHandler(BaseEventHandler):
    """Handler for workflow-related events."""
    
    async def _process_event(self, event: GitHubEvent, context: GitHubActionContext, commit_history: CommitHistory) -> Dict[str, Any]:
        """Process workflow events."""
        self.logger.info(
            "Processing workflow event",
            event_type=context.event_name,
            workflow_name=event.workflow.name if event.workflow else "unknown",
            run_id=event.workflow_run.id if event.workflow_run else None,
            job_id=event.workflow_job.id if event.workflow_job else None
        )
        
        return {
            "handler": "WorkflowEventHandler",
            "workflow_processed": True,
            "workflow_name": event.workflow.name if event.workflow else None,
            "run_status": event.workflow_run.status if event.workflow_run else None,
            "job_status": event.workflow_job.status if event.workflow_job else None
        }


class PullRequestEventHandler(BaseEventHandler):
    """Handler for pull request events."""
    
    async def _process_event(self, event: GitHubEvent, context: GitHubActionContext, commit_history: CommitHistory) -> Dict[str, Any]:
        """Process pull request events."""
        pr = event.pull_request
        if pr:
            self.logger.info(
                "Processing pull request event",
                event_type=context.event_name,
                action=event.action,
                pr_number=pr.number,
                pr_title=pr.title,
                pr_state=pr.state
            )
            
            return {
                "handler": "PullRequestEventHandler",
                "pull_request_processed": True,
                "pr_number": pr.number,
                "pr_title": pr.title,
                "pr_state": pr.state,
                "action": event.action
            }
        
        return {"handler": "PullRequestEventHandler", "pull_request_processed": False}


class IssueEventHandler(BaseEventHandler):
    """Handler for issue events."""
    
    async def _process_event(self, event: GitHubEvent, context: GitHubActionContext, commit_history: CommitHistory) -> Dict[str, Any]:
        """Process issue events."""
        issue = event.issue
        if issue:
            self.logger.info(
                "Processing issue event",
                event_type=context.event_name,
                action=event.action,
                issue_number=issue.number,
                issue_title=issue.title,
                issue_state=issue.state
            )
            
            return {
                "handler": "IssueEventHandler",
                "issue_processed": True,
                "issue_number": issue.number,
                "issue_title": issue.title,
                "issue_state": issue.state,
                "action": event.action
            }
        
        return {"handler": "IssueEventHandler", "issue_processed": False}


class PushEventHandler(BaseEventHandler):
    """Handler for push events."""
    
    async def _process_event(self, event: GitHubEvent, context: GitHubActionContext, commit_history: CommitHistory) -> Dict[str, Any]:
        """Process push events."""
        self.logger.info(
            "Processing push event",
            event_type=context.event_name,
            ref=event.ref,
            before=event.before,
            after=event.after,
            commit_count=len(event.commits) if event.commits else 0
        )
        
        return {
            "handler": "PushEventHandler",
            "push_processed": True,
            "ref": event.ref,
            "before_sha": event.before,
            "after_sha": event.after,
            "commits_in_push": len(event.commits) if event.commits else 0
        }


class SecurityEventHandler(BaseEventHandler):
    """Handler for security-related events."""
    
    async def _process_event(self, event: GitHubEvent, context: GitHubActionContext, commit_history: CommitHistory) -> Dict[str, Any]:
        """Process security events."""
        self.logger.warning(
            "Processing security event",
            event_type=context.event_name,
            action=event.action,
            repository=context.repository
        )
        
        # Security events should be logged and potentially trigger notifications
        # This is a stub - implement actual security handling as needed
        
        return {
            "handler": "SecurityEventHandler",
            "security_event_processed": True,
            "severity": "high",
            "requires_attention": True,
            "action": event.action
        }


class GitHubActionEventProcessor:
    """Main event processor for GitHub Actions."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger(__name__)
        
        # Initialize event handlers
        self.handlers = {
            GitHubActionTrigger.WORKFLOW_RUN: WorkflowEventHandler(settings),
            GitHubActionTrigger.WORKFLOW_JOB: WorkflowEventHandler(settings),
            GitHubActionTrigger.WORKFLOW_DISPATCH: WorkflowEventHandler(settings),
            
            GitHubActionTrigger.PULL_REQUEST: PullRequestEventHandler(settings),
            GitHubActionTrigger.PULL_REQUEST_REVIEW: PullRequestEventHandler(settings),
            GitHubActionTrigger.PULL_REQUEST_REVIEW_COMMENT: PullRequestEventHandler(settings),
            
            GitHubActionTrigger.ISSUES: IssueEventHandler(settings),
            GitHubActionTrigger.ISSUE_COMMENT: IssueEventHandler(settings),
            
            GitHubActionTrigger.PUSH: PushEventHandler(settings),
            
            GitHubActionTrigger.SECURITY_ADVISORY: SecurityEventHandler(settings),
            GitHubActionTrigger.VULNERABILITY_ALERT: SecurityEventHandler(settings),
            GitHubActionTrigger.CODE_SCANNING_ALERT: SecurityEventHandler(settings),
            GitHubActionTrigger.SECRET_SCANNING_ALERT: SecurityEventHandler(settings),
        }
        
        # Default handler for unspecified events
        self.default_handler = BaseEventHandler(settings)
        
        # Statistics tracking
        self.stats = {
            "total_events": 0,
            "successful_events": 0,
            "failed_events": 0,
            "events_by_type": {},
            "start_time": time.time()
        }
    
    def _get_github_context(self) -> GitHubActionContext:
        """Get GitHub Action context from environment variables."""
        return GitHubActionContext(
            event_name=os.getenv("GITHUB_EVENT_NAME", "unknown"),
            workflow=os.getenv("GITHUB_WORKFLOW", "unknown"),
            job=os.getenv("GITHUB_JOB", "unknown"),
            run_id=os.getenv("GITHUB_RUN_ID", "0"),
            run_number=int(os.getenv("GITHUB_RUN_NUMBER", "0")),
            actor=os.getenv("GITHUB_ACTOR", "unknown"),
            repository=os.getenv("GITHUB_REPOSITORY", "unknown"),
            ref=os.getenv("GITHUB_REF", "refs/heads/main"),
            sha=os.getenv("GITHUB_SHA", "unknown"),
            workspace=os.getenv("GITHUB_WORKSPACE", os.getcwd()),
            server_url=os.getenv("GITHUB_SERVER_URL", "https://github.com"),
            api_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
            graphql_url=os.getenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
        )
    
    async def process_event(self, event: GitHubEvent) -> EventProcessingResult:
        """Process a GitHub event."""
        start_time = time.time()
        
        # Get GitHub Action context
        context = self._get_github_context()
        
        # Update statistics
        self.stats["total_events"] += 1
        event_type = context.event_name
        self.stats["events_by_type"][event_type] = self.stats["events_by_type"].get(event_type, 0) + 1
        
        try:
            # Check if event is enabled
            if not self._is_event_enabled(event_type):
                self.logger.info("Event type is disabled, skipping", event_type=event_type)
                return EventProcessingResult(
                    event_type=event_type,
                    processing_time=time.time() - start_time,
                    success=True,
                    message=f"Event type {event_type} is disabled",
                    github_context=context
                )
            
            # Get appropriate handler
            handler = self._get_handler(event_type)
            
            # Process the event
            result = await handler.handle(event, context)
            
            # Update statistics
            if result.success:
                self.stats["successful_events"] += 1
            else:
                self.stats["failed_events"] += 1
            
            self.logger.info(
                "Event processed",
                event_type=event_type,
                success=result.success,
                processing_time=result.processing_time,
                repository=context.repository
            )
            
            return result
            
        except Exception as e:
            self.stats["failed_events"] += 1
            processing_time = time.time() - start_time
            
            self.logger.error(
                "Event processing failed",
                event_type=event_type,
                error=str(e),
                processing_time=processing_time
            )
            
            return EventProcessingResult(
                event_type=event_type,
                processing_time=processing_time,
                success=False,
                message=f"Failed to process {event_type} event",
                error=str(e),
                github_context=context
            )
    
    def _is_event_enabled(self, event_type: str) -> bool:
        """Check if an event type is enabled."""
        # Check disabled events first
        if self.settings.disabled_events and event_type in self.settings.disabled_events:
            return False
        
        # If enabled events is specified, only allow those
        if self.settings.enabled_events:
            return event_type in self.settings.enabled_events
        
        # Default to enabled
        return True
    
    def _get_handler(self, event_type: str) -> EventHandler:
        """Get the appropriate handler for an event type."""
        try:
            trigger = GitHubActionTrigger(event_type)
            return self.handlers.get(trigger, self.default_handler)
        except ValueError:
            # Unknown event type, use default handler
            return self.default_handler
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        uptime = time.time() - self.stats["start_time"]
        events_per_second = self.stats["total_events"] / uptime if uptime > 0 else 0
        
        return {
            "total_events": self.stats["total_events"],
            "successful_events": self.stats["successful_events"],
            "failed_events": self.stats["failed_events"],
            "events_per_second": events_per_second,
            "events_by_type": self.stats["events_by_type"],
            "uptime_seconds": uptime,
            "success_rate": (
                self.stats["successful_events"] / self.stats["total_events"] 
                if self.stats["total_events"] > 0 else 0
            )
        }
    
    def get_supported_events(self) -> List[Dict[str, Any]]:
        """Get list of supported events."""
        events = []
        for trigger in GitHubActionTrigger:
            events.append({
                "name": trigger.value,
                "description": f"GitHub {trigger.value} event",
                "category": self._get_event_category(trigger.value),
                "handler": self.handlers.get(trigger, self.default_handler).__class__.__name__
            })
        
        return sorted(events, key=lambda x: x["name"])
    
    def _get_event_category(self, event_type: str) -> str:
        """Get the category for an event type."""
        if event_type.startswith("workflow"):
            return "workflow"
        elif event_type in ["push", "pull_request", "pull_request_review", "pull_request_review_comment"]:
            return "code"
        elif event_type in ["issues", "issue_comment"]:
            return "issues"
        elif "security" in event_type or "vulnerability" in event_type or "scanning" in event_type:
            return "security"
        elif event_type in ["deployment", "deployment_status"]:
            return "deployment"
        elif event_type in ["team", "member", "organization"]:
            return "collaboration"
        else:
            return "other" 