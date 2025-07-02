"""
Git operations and GitHub API integration for agent automation.

This module provides functionality for:
- Git branch creation, commits, and push operations
- GitHub API interactions for PR creation
- File change detection and diff extraction
- Branch automation workflows
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse

import httpx
from jinja2 import Template

from .models import (
    FileChange, 
    AgentBranchAutomation,
    GitHubActionContext,
    GitHubEvent
)
from .config import Settings

logger = logging.getLogger(__name__)


class GitOperationError(Exception):
    """Raised when git operations fail."""
    pass


class GitHubAPIError(Exception):
    """Raised when GitHub API operations fail."""
    pass


class GitOperations:
    """Handles git operations for agent automation."""
    
    def __init__(self, settings: Settings, workspace_path: str):
        self.settings = settings
        self.workspace_path = Path(workspace_path)
        self.git_executable = self._find_git_executable()
    
    def _find_git_executable(self) -> str:
        """Find git executable path."""
        # Try common locations
        for git_path in ['git', '/usr/bin/git', '/usr/local/bin/git']:
            try:
                result = subprocess.run([git_path, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return git_path
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        
        raise GitOperationError("Git executable not found")
    
    async def run_git_command(self, args: List[str], cwd: Optional[Path] = None) -> Tuple[str, str]:
        """Run a git command asynchronously."""
        cmd = [self.git_executable] + args
        work_dir = cwd or self.workspace_path
        
        logger.debug(f"Running git command: {' '.join(cmd)} in {work_dir}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            stdout_str = stdout.decode('utf-8').strip()
            stderr_str = stderr.decode('utf-8').strip()
            
            if process.returncode != 0:
                raise GitOperationError(f"Git command failed: {stderr_str}")
            
            return stdout_str, stderr_str
            
        except asyncio.TimeoutError:
            raise GitOperationError("Git command timed out")
        except Exception as e:
            raise GitOperationError(f"Git command error: {e}")
    
    async def get_current_branch(self) -> str:
        """Get the current branch name."""
        stdout, _ = await self.run_git_command(['branch', '--show-current'])
        return stdout.strip()
    
    async def get_remote_url(self) -> str:
        """Get the remote origin URL."""
        stdout, _ = await self.run_git_command(['remote', 'get-url', 'origin'])
        return stdout.strip()
    
    async def create_branch(self, branch_name: str, base_branch: Optional[str] = None) -> str:
        """Create a new branch."""
        if base_branch:
            await self.run_git_command(['checkout', base_branch])
            await self.run_git_command(['pull', 'origin', base_branch])
        
        # Create and checkout new branch
        await self.run_git_command(['checkout', '-b', branch_name])
        
        logger.info(f"Created branch: {branch_name}")
        return branch_name
    
    async def commit_changes(self, message: str, files: Optional[List[str]] = None) -> str:
        """Commit changes to the current branch."""
        # Add files (all changes if none specified)
        if files:
            for file in files:
                await self.run_git_command(['add', file])
        else:
            await self.run_git_command(['add', '.'])
        
        # Check if there are changes to commit
        try:
            stdout, _ = await self.run_git_command(['diff', '--cached', '--name-only'])
            if not stdout.strip():
                logger.info("No changes to commit")
                return ""
        except GitOperationError:
            logger.info("No changes to commit")
            return ""
        
        # Commit changes
        await self.run_git_command(['commit', '-m', message])
        
        # Get commit SHA
        stdout, _ = await self.run_git_command(['rev-parse', 'HEAD'])
        commit_sha = stdout.strip()
        
        logger.info(f"Committed changes: {commit_sha}")
        return commit_sha
    
    async def push_branch(self, branch_name: str) -> None:
        """Push branch to remote."""
        await self.run_git_command(['push', 'origin', branch_name])
        logger.info(f"Pushed branch: {branch_name}")
    
    async def get_file_changes(self, base_sha: str, head_sha: str) -> List[FileChange]:
        """Get list of changed files between two commits."""
        try:
            # Get list of changed files
            stdout, _ = await self.run_git_command([
                'diff', '--name-status', f"{base_sha}..{head_sha}"
            ])
            
            file_changes = []
            for line in stdout.split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split('\t', 1)
                if len(parts) < 2:
                    continue
                
                status = parts[0]
                filename = parts[1]
                
                # Get diff stats
                try:
                    stats_stdout, _ = await self.run_git_command([
                        'diff', '--numstat', f"{base_sha}..{head_sha}", '--', filename
                    ])
                    
                    additions, deletions = 0, 0
                    if stats_stdout.strip():
                        stats_parts = stats_stdout.split('\t')
                        if len(stats_parts) >= 2:
                            try:
                                additions = int(stats_parts[0]) if stats_parts[0] != '-' else 0
                                deletions = int(stats_parts[1]) if stats_parts[1] != '-' else 0
                            except ValueError:
                                pass
                    
                    file_change = FileChange(
                        filename=filename,
                        status=self._normalize_status(status),
                        additions=additions,
                        deletions=deletions,
                        changes=additions + deletions
                    )
                    
                    file_changes.append(file_change)
                    
                except GitOperationError as e:
                    logger.warning(f"Could not get stats for {filename}: {e}")
            
            return file_changes
            
        except GitOperationError as e:
            logger.error(f"Failed to get file changes: {e}")
            return []
    
    async def get_file_diff(self, filename: str, base_sha: str, head_sha: str, 
                           context_lines: int = 3) -> Optional[str]:
        """Get diff for a specific file."""
        try:
            stdout, _ = await self.run_git_command([
                'diff', f"--unified={context_lines}", f"{base_sha}..{head_sha}", '--', filename
            ])
            return stdout if stdout.strip() else None
        except GitOperationError as e:
            logger.warning(f"Could not get diff for {filename}: {e}")
            return None
    
    async def get_file_content(self, filename: str, commit_sha: Optional[str] = None) -> Optional[str]:
        """Get file content at a specific commit."""
        try:
            if commit_sha:
                stdout, _ = await self.run_git_command(['show', f"{commit_sha}:{filename}"])
            else:
                file_path = self.workspace_path / filename
                if file_path.exists():
                    stdout = file_path.read_text(encoding='utf-8')
                else:
                    return None
            return stdout
        except (GitOperationError, UnicodeDecodeError, OSError) as e:
            logger.warning(f"Could not get content for {filename}: {e}")
            return None
    
    def _normalize_status(self, status: str) -> str:
        """Normalize git status to standard format."""
        status_map = {
            'A': 'added',
            'M': 'modified',
            'D': 'removed',
            'R': 'renamed',
            'C': 'copied',
            'T': 'modified',  # Type change
            'U': 'modified',  # Unmerged
        }
        return status_map.get(status[0], 'modified')
    
    def generate_branch_name(self, prefix: str) -> str:
        """Generate a unique branch name."""
        suffix = str(uuid.uuid4())[:8]
        return f"{prefix}-{suffix}"


class GitHubAPI:
    """Handles GitHub API operations."""
    
    def __init__(self, settings: Settings, github_token: str):
        self.settings = settings
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        
    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        reviewers: Optional[List[str]] = None
    ) -> Tuple[int, str]:
        """Create a pull request."""
        
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": False
        }
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Action-Handler/1.0"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
                
                if response.status_code == 201:
                    pr_data = response.json()
                    pr_number = pr_data["number"]
                    pr_url = pr_data["html_url"]
                    
                    # Add labels if specified
                    if labels:
                        await self._add_labels(client, owner, repo, pr_number, labels, headers)
                    
                    # Add assignees if specified
                    if assignees:
                        await self._add_assignees(client, owner, repo, pr_number, assignees, headers)
                    
                    # Request reviewers if specified
                    if reviewers:
                        await self._request_reviewers(client, owner, repo, pr_number, reviewers, headers)
                    
                    logger.info(f"Created PR #{pr_number}: {pr_url}")
                    return pr_number, pr_url
                else:
                    error_msg = f"Failed to create PR: {response.status_code} {response.text}"
                    logger.error(error_msg)
                    raise GitHubAPIError(error_msg)
                    
        except httpx.RequestError as e:
            error_msg = f"GitHub API request failed: {e}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg)
    
    async def _add_labels(self, client: httpx.AsyncClient, owner: str, repo: str, 
                         issue_number: int, labels: List[str], headers: Dict[str, str]) -> None:
        """Add labels to an issue or PR."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/labels"
        response = await client.post(url, json={"labels": labels}, headers=headers)
        if response.status_code != 200:
            logger.warning(f"Failed to add labels: {response.status_code}")
    
    async def _add_assignees(self, client: httpx.AsyncClient, owner: str, repo: str,
                            issue_number: int, assignees: List[str], headers: Dict[str, str]) -> None:
        """Add assignees to an issue or PR."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/assignees"
        response = await client.post(url, json={"assignees": assignees}, headers=headers)
        if response.status_code != 201:
            logger.warning(f"Failed to add assignees: {response.status_code}")
    
    async def _request_reviewers(self, client: httpx.AsyncClient, owner: str, repo: str,
                                pr_number: int, reviewers: List[str], headers: Dict[str, str]) -> None:
        """Request reviewers for a PR."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers"
        response = await client.post(url, json={"reviewers": reviewers}, headers=headers)
        if response.status_code != 201:
            logger.warning(f"Failed to request reviewers: {response.status_code}")
    
    async def create_status_check(
        self,
        owner: str,
        repo: str,
        sha: str,
        state: str,  # "success", "failure", "error", "pending"
        context: str,
        description: str,
        target_url: Optional[str] = None
    ) -> bool:
        """Create a status check on a commit."""
        url = f"{self.base_url}/repos/{owner}/{repo}/statuses/{sha}"
        
        data = {
            "state": state,
            "context": context,
            "description": description
        }
        
        if target_url:
            data["target_url"] = target_url
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Action-Handler/1.0"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
                
                if response.status_code == 201:
                    logger.info(f"Created status check: {context} - {state}")
                    return True
                else:
                    error_msg = f"Failed to create status check: {response.status_code} {response.text}"
                    logger.error(error_msg)
                    return False
                    
        except httpx.RequestError as e:
            error_msg = f"GitHub API request failed: {e}"
            logger.error(error_msg)
            return False
    
    async def create_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str
    ) -> Optional[str]:
        """Create a comment on an issue or PR."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        
        data = {"body": body}
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Action-Handler/1.0"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
                
                if response.status_code == 201:
                    comment_data = response.json()
                    comment_url = comment_data["html_url"]
                    logger.info(f"Created comment: {comment_url}")
                    return comment_url
                else:
                    error_msg = f"Failed to create comment: {response.status_code} {response.text}"
                    logger.error(error_msg)
                    return None
                    
        except httpx.RequestError as e:
            error_msg = f"GitHub API request failed: {e}"
            logger.error(error_msg)
            return None
    
    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> Tuple[Optional[int], Optional[str]]:
        """Create a new issue."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        if milestone:
            data["milestone"] = milestone
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Action-Handler/1.0"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
                
                if response.status_code == 201:
                    issue_data = response.json()
                    issue_number = issue_data["number"]
                    issue_url = issue_data["html_url"]
                    logger.info(f"Created issue #{issue_number}: {issue_url}")
                    return issue_number, issue_url
                else:
                    error_msg = f"Failed to create issue: {response.status_code} {response.text}"
                    logger.error(error_msg)
                    return None, None
                    
        except httpx.RequestError as e:
            error_msg = f"GitHub API request failed: {e}"
            logger.error(error_msg)
            return None, None


class BranchAutomationManager:
    """Manages branch automation workflows for agents."""
    
    def __init__(self, settings: Settings, github_token: str, workspace_path: str):
        self.settings = settings
        self.git_ops = GitOperations(settings, workspace_path)
        self.github_api = GitHubAPI(settings, github_token)
        self.workspace_path = Path(workspace_path)
    
    async def execute_branch_workflow(
        self,
        automation_config: AgentBranchAutomation,
        agent_name: str,
        agent_output: str,
        github_context: GitHubActionContext,
        event: GitHubEvent,
        template_vars: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """
        Execute the complete branch automation workflow.
        
        Returns:
            Tuple of (branch_name, pr_number, pr_url)
        """
        if not automation_config.enabled:
            return None, None, None
        
        try:
            # Generate branch name
            branch_name = self.git_ops.generate_branch_name(automation_config.branch_prefix)
            
            # Parse repository info
            repo_full_name = github_context.repository
            owner, repo = repo_full_name.split('/', 1)
            
            # Get current branch for base
            current_branch = await self.git_ops.get_current_branch()
            base_branch = automation_config.target_branch or current_branch
            
            # Create new branch
            await self.git_ops.create_branch(branch_name, base_branch)
            
            # Write agent output to a file or apply changes
            await self._apply_agent_changes(agent_output, agent_name)
            
            # Prepare commit message
            commit_message = await self._render_template(
                automation_config.commit_message or f"Auto-fix by {agent_name}",
                template_vars
            )
            
            # Commit changes
            commit_sha = await self.git_ops.commit_changes(commit_message)
            
            if not commit_sha:
                logger.info("No changes to commit, skipping branch creation")
                return None, None, None
            
            # Push branch
            await self.git_ops.push_branch(branch_name)
            
            # Create PR if requested
            pr_number, pr_url = None, None
            if automation_config.create_pull_request:
                pr_title = await self._render_template(
                    automation_config.pr_title or f"Auto-fix by {agent_name}",
                    template_vars
                )
                
                pr_body = await self._render_template(
                    automation_config.pr_body or f"Automated changes by {agent_name}:\n\n{agent_output}",
                    template_vars
                )
                
                pr_number, pr_url = await self.github_api.create_pull_request(
                    owner=owner,
                    repo=repo,
                    title=pr_title,
                    body=pr_body,
                    head_branch=branch_name,
                    base_branch=base_branch,
                    labels=automation_config.pr_labels,
                    assignees=automation_config.pr_assignees,
                    reviewers=automation_config.pr_reviewers
                )
            
            return branch_name, pr_number, pr_url
            
        except Exception as e:
            logger.error(f"Branch automation workflow failed: {e}")
            # Try to cleanup - switch back to original branch
            try:
                current_branch = await self.git_ops.get_current_branch()
                if current_branch == branch_name:
                    await self.git_ops.run_git_command(['checkout', base_branch])
            except:
                pass
            raise
    
    async def _apply_agent_changes(self, agent_output: str, agent_name: str) -> None:
        """Apply agent output as changes to the repository."""
        # For now, we'll create a simple output file
        # In the future, this could be enhanced to parse and apply specific changes
        output_file = self.workspace_path / f"{agent_name}-output.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Agent Output: {agent_name}\n\n")
            f.write(agent_output)
        
        logger.info(f"Applied agent changes to {output_file}")
    
    async def _render_template(self, template_str: str, variables: Dict[str, Any]) -> str:
        """Render a Jinja2 template string with file inclusion support."""
        try:
            from .template_functions import render_template_with_file_inclusion
            
            # Extract file changes and github context if available
            files_changed = variables.get('files_changed', [])
            github_context = variables.get('github_context', {})
            
            # Convert file change dicts back to FileChange objects if needed
            if files_changed and isinstance(files_changed[0], dict):
                from .models import FileChange
                files_changed = [FileChange(**fc) for fc in files_changed]
            
            return render_template_with_file_inclusion(
                template_str=template_str,
                context_vars=variables,
                workspace_path=self.workspace_path,
                files_changed=files_changed,
                github_context=None  # We don't have GitHubActionContext object here
            )
        except Exception as e:
            logger.warning(f"Template rendering failed: {e}")
            # Fallback to basic template rendering
            try:
                template = Template(template_str)
                return template.render(**variables)
            except Exception as e2:
                logger.warning(f"Fallback template rendering also failed: {e2}")
                return template_str


async def extract_file_changes_from_event(
    event: GitHubEvent,
    git_ops: GitOperations,
    include_content: bool = False,
    include_diff: bool = False,
    diff_context: int = 3
) -> List[FileChange]:
    """Extract file changes from a GitHub event."""
    
    file_changes = []
    
    # Handle push events
    if hasattr(event, 'before') and hasattr(event, 'after') and event.before and event.after:
        file_changes = await git_ops.get_file_changes(event.before, event.after)
        
        # Enhance with content and diffs if requested
        for file_change in file_changes:
            if include_diff:
                diff = await git_ops.get_file_diff(
                    file_change.filename, event.before, event.after, diff_context
                )
                file_change.patch = diff
            
            if include_content:
                # Get content before and after
                file_change.content_before = await git_ops.get_file_content(
                    file_change.filename, event.before
                )
                file_change.content_after = await git_ops.get_file_content(
                    file_change.filename, event.after
                )
                file_change.content = file_change.content_after
    
    # Handle pull request events
    elif hasattr(event, 'pull_request') and event.pull_request:
        # For PR events, we'd need to use GitHub API to get the diff
        # For now, we'll return empty list
        logger.info("Pull request file changes not yet implemented")
    
    return file_changes 