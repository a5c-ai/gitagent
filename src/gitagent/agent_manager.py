"""
AI Agent Management for gitagent.

This module handles discovery, configuration, and execution of AI agents
based on YAML configuration files in the target repository.
"""

import asyncio
import fnmatch
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from jinja2 import Environment, FileSystemLoader, Template
import structlog

from .config import settings
from .models import (
    AgentDefinition,
    AgentExecutionResult,
    AgentType,
    GitHubEvent,
    GitHubActionContext,
    CommitHistory,
    OutputDestination,
    McpServerConfig,
    FileChange,
)
from .git_operations import (
    GitOperations,
    GitHubAPI,
    BranchAutomationManager,
    extract_file_changes_from_event,
    GitOperationError,
    GitHubAPIError,
)
from .template_functions import render_template_with_file_inclusion
from .claude_code_sdk_executor import ClaudeCodeSDKExecutor

logger = structlog.get_logger()


class AgentManager:
    """Manages AI agent discovery, configuration, and execution."""
    
    def __init__(self, github_token: Optional[str] = None):
        self.jinja_env = Environment(
            loader=FileSystemLoader("."),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._agent_cache: Dict[str, List[AgentDefinition]] = {}
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 300  # 5 minutes
        
        # Git operations (initialized when needed)
        self._git_ops: Optional[GitOperations] = None
        self._branch_automation: Optional[BranchAutomationManager] = None
        self._github_token = github_token
        
        # Claude Code SDK executor (initialized when needed)
        self._claude_code_sdk_executor: Optional[ClaudeCodeSDKExecutor] = None
    
    def _get_claude_code_sdk_executor(self) -> Optional[ClaudeCodeSDKExecutor]:
        """Get or create Claude Code SDK executor."""
        if self._claude_code_sdk_executor is None:
            sdk_config = settings.get_claude_code_sdk_config()
            if sdk_config:
                self._claude_code_sdk_executor = ClaudeCodeSDKExecutor(sdk_config)
        return self._claude_code_sdk_executor
    
    async def health_check_claude_code_sdk(self) -> Dict[str, Any]:
        """Perform health check for Claude Code SDK executor."""
        sdk_executor = self._get_claude_code_sdk_executor()
        if not sdk_executor:
            return {
                "status": "unavailable",
                "error": "Claude Code SDK executor not configured"
            }
        
        try:
            return await sdk_executor.health_check()
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def discover_agents(
        self,
        event_type: str,
        workspace_path: Optional[str] = None
    ) -> List[AgentDefinition]:
        """Discover agents for a specific event type."""
        workspace_path = workspace_path or settings.github_workspace
        agents_dir = Path(workspace_path) / settings.agents_directory
        
        # Check cache first
        cache_key = f"{event_type}:{agents_dir}"
        if self._is_cache_valid(cache_key):
            return self._agent_cache.get(cache_key, [])
        
        agents = []
        
        if not agents_dir.exists():
            logger.info(
                "Agents directory not found",
                agents_directory=str(agents_dir),
                event_type=event_type
            )
            return agents
        
        # Look for event-specific directory
        event_dir = agents_dir / event_type
        if event_dir.exists():
            agents.extend(await self._load_agents_from_directory(event_dir, event_type))
        
        # Look for wildcard directories (e.g., "*", "all")
        for dir_path in agents_dir.iterdir():
            if dir_path.is_dir() and dir_path.name in ["*", "all", "common"]:
                agents.extend(await self._load_agents_from_directory(dir_path, event_type))
        
        # Cache the results
        self._agent_cache[cache_key] = agents
        self._cache_timestamp = time.time()
        
        logger.info(
            "Discovered agents",
            event_type=event_type,
            agents_count=len(agents),
            agents_directory=str(agents_dir)
        )
        
        return agents
    
    async def _load_agents_from_directory(
        self,
        directory: Path,
        event_type: str
    ) -> List[AgentDefinition]:
        """Load agent definitions from a directory."""
        agents = []
        
        for yaml_file in directory.glob("*.yml"):
            try:
                agent_def = await self._load_agent_definition(yaml_file, event_type)
                if agent_def and agent_def.enabled:
                    agents.append(agent_def)
            except Exception as e:
                logger.error(
                    "Failed to load agent definition",
                    file=str(yaml_file),
                    error=str(e),
                    event_type=event_type
                )
        
        for yaml_file in directory.glob("*.yaml"):
            try:
                agent_def = await self._load_agent_definition(yaml_file, event_type)
                if agent_def and agent_def.enabled:
                    agents.append(agent_def)
            except Exception as e:
                logger.error(
                    "Failed to load agent definition",
                    file=str(yaml_file),
                    error=str(e),
                    event_type=event_type
                )
        
        return agents
    
    async def _load_agent_definition(
        self,
        yaml_file: Path,
        event_type: str
    ) -> Optional[AgentDefinition]:
        """Load a single agent definition from YAML file."""
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return None
            
            # Add file metadata to agent definition
            if "agent" not in data:
                data["agent"] = {}
            
            data["agent"]["file_path"] = str(yaml_file)
            data["agent"]["file_name"] = yaml_file.stem
            data["agent"]["event_type"] = event_type
            
            # Set default agent name from file name if not provided
            if "name" not in data["agent"]:
                data["agent"]["name"] = yaml_file.stem
            
            return AgentDefinition(**data)
        
        except Exception as e:
            logger.error(
                "Failed to parse agent definition",
                file=str(yaml_file),
                error=str(e)
            )
            return None
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid."""
        if cache_key not in self._agent_cache:
            return False
        
        return (time.time() - self._cache_timestamp) < self._cache_ttl
    
    def _clear_cache(self):
        """Clear the agent cache."""
        self._agent_cache.clear()
        self._cache_timestamp = 0
    
    def _get_git_ops(self, workspace_path: Optional[str] = None) -> GitOperations:
        """Get or create GitOperations instance."""
        if self._git_ops is None:
            workspace = workspace_path or settings.github_workspace
            self._git_ops = GitOperations(settings, workspace)
        return self._git_ops
    
    def _get_branch_automation(self, workspace_path: Optional[str] = None) -> Optional[BranchAutomationManager]:
        """Get or create BranchAutomationManager instance."""
        if not self._github_token:
            return None
        
        if self._branch_automation is None:
            workspace = workspace_path or settings.github_workspace
            self._branch_automation = BranchAutomationManager(
                settings, self._github_token, workspace
            )
        return self._branch_automation
    
    async def filter_agents(
        self,
        agents: List[AgentDefinition],
        event: GitHubEvent,
        github_context: GitHubActionContext,
        commit_history: Optional[CommitHistory] = None
    ) -> List[AgentDefinition]:
        """Filter agents based on trigger conditions."""
        # Extract file changes from event if needed
        file_changes = []
        try:
            git_ops = self._get_git_ops()
            file_changes = await extract_file_changes_from_event(event, git_ops)
        except Exception as e:
            logger.warning("Failed to extract file changes", error=str(e))
        
        filtered_agents = []
        
        for agent in agents:
            if await self._should_run_agent(agent, event, github_context, commit_history, file_changes):
                filtered_agents.append(agent)
        
        # Sort by priority (lower number = higher priority)
        filtered_agents.sort(key=lambda a: a.priority)
        
        return filtered_agents
    
    async def _should_run_agent(
        self,
        agent: AgentDefinition,
        event: GitHubEvent,
        github_context: GitHubActionContext,
        commit_history: Optional[CommitHistory] = None,
        file_changes: Optional[List[FileChange]] = None
    ) -> bool:
        """Check if an agent should run based on trigger conditions."""
        triggers = agent.triggers
        file_changes = file_changes or []
        
        # Check branch patterns
        if triggers.branches and github_context.ref:
            branch_name = github_context.ref.replace("refs/heads/", "")
            if not any(fnmatch.fnmatch(branch_name, pattern) for pattern in triggers.branches):
                return False
        
        # Check tag patterns
        if triggers.tags and github_context.ref:
            if github_context.ref.startswith("refs/tags/"):
                tag_name = github_context.ref.replace("refs/tags/", "")
                if not any(fnmatch.fnmatch(tag_name, pattern) for pattern in triggers.tags):
                    return False
            else:
                # Not a tag, but tag patterns are specified
                return False
        
        # Check event actions
        if triggers.event_actions and event.action:
            if event.action not in triggers.event_actions:
                return False
        
        # Check file changes (if applicable)
        if hasattr(event, 'commits') and event.commits:
            total_files_changed = sum(
                len(commit.get('added', [])) + 
                len(commit.get('removed', [])) + 
                len(commit.get('modified', []))
                for commit in event.commits
            )
            
            if triggers.files_changed_min and total_files_changed < triggers.files_changed_min:
                return False
            
            if triggers.files_changed_max and total_files_changed > triggers.files_changed_max:
                return False
        
        # Check path patterns
        if triggers.paths and hasattr(event, 'commits') and event.commits:
            changed_files = set()
            for commit in event.commits:
                changed_files.update(commit.get('added', []))
                changed_files.update(commit.get('removed', []))
                changed_files.update(commit.get('modified', []))
            
            if not any(
                fnmatch.fnmatch(file_path, pattern)
                for file_path in changed_files
                for pattern in triggers.paths
            ):
                return False
        
        # Check specific file change patterns
        if triggers.files_changed and file_changes:
            changed_filenames = [fc.filename for fc in file_changes]
            
            if not any(
                fnmatch.fnmatch(filename, pattern)
                for filename in changed_filenames
                for pattern in triggers.files_changed
            ):
                return False
        
        # Check Jinja2 template conditions
        if triggers.conditions:
            template_context = {
                'event': event.dict(),
                'github_context': github_context.dict(),
                'commit_history': commit_history.dict() if commit_history else None,
                'files_changed': [fc.dict() for fc in (file_changes or [])],
            }
            
            for condition in triggers.conditions:
                try:
                    template = Template(condition)
                    result = template.render(**template_context)
                    # Evaluate the result as a boolean expression
                    if not eval(result.strip()):
                        return False
                except Exception as e:
                    logger.warning(
                        "Failed to evaluate agent condition",
                        agent=agent.agent.get('name', 'unknown'),
                        condition=condition,
                        error=str(e)
                    )
                    return False
        
        return True
    
    async def execute_agents(
        self,
        agents: List[AgentDefinition],
        event: GitHubEvent,
        github_context: GitHubActionContext,
        commit_history: Optional[CommitHistory] = None,
        file_changes: Optional[List[FileChange]] = None
    ) -> List[AgentExecutionResult]:
        """Execute a list of agents."""
        results = []
        
        for agent in agents:
            try:
                result = await self.execute_agent(agent, event, github_context, commit_history, file_changes)
                results.append(result)
            except Exception as e:
                logger.error(
                    "Failed to execute agent",
                    agent=agent.agent.get('name', 'unknown'),
                    error=str(e)
                )
                results.append(AgentExecutionResult(
                    agent_name=agent.agent.get('name', 'unknown'),
                    agent_type=AgentType(agent.agent.get('type', 'custom')),
                    success=False,
                    error=str(e),
                    execution_time=0.0,
                    output_destination=agent.output.destination
                ))
        
        return results
    
    async def execute_agent(
        self,
        agent: AgentDefinition,
        event: GitHubEvent,
        github_context: GitHubActionContext,
        commit_history: Optional[CommitHistory] = None,
        file_changes: Optional[List[FileChange]] = None
    ) -> AgentExecutionResult:
        """Execute a single agent."""
        start_time = time.time()
        agent_name = agent.agent.get('name', 'unknown')
        agent_type = AgentType(agent.agent.get('type', 'custom'))
        file_changes = file_changes or []
        
        logger.info(
            "Executing agent",
            agent=agent_name,
            agent_type=agent_type,
            event_type=github_context.event_name
        )
        
        try:
            # Enhance file changes with content/diff if requested
            enhanced_file_changes = await self._enhance_file_changes(agent, file_changes)
            
            # Render the prompt template
            rendered_prompt = await self._render_prompt_template(
                agent, event, github_context, commit_history, enhanced_file_changes
            )
            
            # Execute the agent based on type
            if agent_type == AgentType.CLAUDE_CODE_SDK:
                # Use Claude Code SDK executor
                sdk_executor = self._get_claude_code_sdk_executor()
                if not sdk_executor:
                    raise ValueError("Claude Code SDK executor not available")
                
                return await sdk_executor.execute_agent(
                    agent, rendered_prompt, github_context, commit_history, enhanced_file_changes
                )
            else:
                # Use CLI executor for other agent types
                output = await self._execute_agent_cli(agent, rendered_prompt)
            
            # Initialize result with base information
            result = AgentExecutionResult(
                agent_name=agent_name,
                agent_type=agent_type,
                success=True,
                output=output,
                execution_time=0.0,  # Will be updated below
                output_destination=agent.output.destination,
                files_changed=enhanced_file_changes,
                metadata={
                    'prompt_length': len(rendered_prompt),
                    'output_length': len(output),
                }
            )
            
            # Handle branch automation if enabled
            if agent.branch_automation and agent.branch_automation.enabled:
                branch_automation = self._get_branch_automation()
                if branch_automation:
                    try:
                        template_vars = {
                            'event': event.dict(),
                            'github_context': github_context.dict(),
                            'commit_history': commit_history.dict() if commit_history else None,
                            'agent': agent.dict(),
                            'config': agent.configuration,
                            'files_changed': [fc.dict() for fc in enhanced_file_changes],
                        }
                        
                        branch_name, pr_number, pr_url = await branch_automation.execute_branch_workflow(
                            agent.branch_automation,
                            agent_name,
                            output,
                            github_context,
                            event,
                            template_vars
                        )
                        
                        result.branch_created = branch_name
                        result.pr_created = pr_number
                        result.pr_url = pr_url
                        
                        logger.info(
                            "Branch automation completed",
                            agent=agent_name,
                            branch_created=branch_name,
                            pr_created=pr_number
                        )
                    except Exception as e:
                        logger.error(
                            "Branch automation failed",
                            agent=agent_name,
                            error=str(e)
                        )
                        result.metadata['branch_automation_error'] = str(e)
            
            # Handle regular output destination and GitHub integrations
            github_results = await self._handle_agent_output(agent, output, github_context, event, enhanced_file_changes)
            
            # Update result with GitHub integration results
            result.status_check_posted = github_results.get('status_check_posted')
            result.comment_posted = github_results.get('comment_posted')
            result.issue_created = github_results.get('issue_created')
            result.issue_url = github_results.get('issue_url')
            
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            logger.info(
                "Agent executed successfully",
                agent=agent_name,
                execution_time=execution_time,
                output_length=len(output)
            )
            
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Agent execution failed",
                agent=agent_name,
                error=str(e),
                execution_time=execution_time
            )
            
            return AgentExecutionResult(
                agent_name=agent_name,
                agent_type=agent_type,
                success=False,
                error=str(e),
                execution_time=execution_time,
                output_destination=agent.output.destination
            )
    
    async def _enhance_file_changes(
        self,
        agent: AgentDefinition,
        file_changes: List[FileChange]
    ) -> List[FileChange]:
        """Enhance file changes with content and diff if requested."""
        if not file_changes:
            return file_changes
        
        triggers = agent.triggers
        
        # Check if we need to enhance with content or diff
        if not (triggers.include_file_content or triggers.include_file_diff):
            return file_changes
        
        try:
            git_ops = self._get_git_ops()
            enhanced_changes = []
            
            for file_change in file_changes:
                enhanced_change = file_change.copy()
                
                if triggers.include_file_content:
                    # Get current file content
                    enhanced_change.content = await git_ops.get_file_content(file_change.filename)
                
                if triggers.include_file_diff and file_change.patch is None:
                    # Try to get diff from git if not already present
                    # This would require before/after commit SHAs which may not be available
                    # in all contexts, so we'll leave it as is for now
                    pass
                
                enhanced_changes.append(enhanced_change)
            
            return enhanced_changes
            
        except Exception as e:
            logger.warning(
                "Failed to enhance file changes",
                agent=agent.agent.get('name', 'unknown'),
                error=str(e)
            )
            return file_changes
    
    async def _render_prompt_template(
        self,
        agent: AgentDefinition,
        event: GitHubEvent,
        github_context: GitHubActionContext,
        commit_history: Optional[CommitHistory] = None,
        file_changes: Optional[List[FileChange]] = None
    ) -> str:
        """Render the agent's prompt template with context variables and file inclusion support."""
        template_context = {
            'event': event.dict(),
            'github_context': github_context.dict(),
            'commit_history': commit_history.dict() if commit_history else None,
            'files_changed': [fc.dict() for fc in (file_changes or [])],
            'agent': agent.agent,
            'config': agent.configuration,
        }
        
        try:
            # Use enhanced template rendering with file inclusion support
            return render_template_with_file_inclusion(
                template_str=agent.prompt_template,
                context_vars=template_context,
                workspace_path=github_context.workspace,
                files_changed=file_changes or [],
                github_context=github_context
            )
        except Exception as e:
            logger.error(
                "Failed to render prompt template",
                agent=agent.agent.get('name', 'unknown'),
                error=str(e)
            )
            raise
    
    async def _execute_agent_cli(
        self,
        agent: AgentDefinition,
        prompt: str
    ) -> str:
        """Execute the agent CLI with the rendered prompt."""
        agent_type = agent.agent.get('type', 'custom')
        # cli_config = settings.get_agent_cli_config(agent_type)
        env_vars = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        }
        
        # Prepare environment variables
        env = os.environ.copy()
        env.update(env_vars)
        executable_path = os.getenv("EXECUTABLE_PATH", "")
        # resolve the executable path according to the agent type
        
        additional_args = os.getenv("ADDITIONAL_ARGS", "")
        model = os.getenv("MODEL", "")
        max_tokens = os.getenv("MAX_TOKENS", "")
        temperature = os.getenv("TEMPERATURE", "")
        base_url = os.getenv("BASE_URL", "")
        timeout_seconds = os.getenv("TIMEOUT_SECONDS", 900)
        additional_args = []
        if agent_type == "claude":
            executable_path = "/usr/bin/claude"
            additional_args = ["-d", "--model", "sonnet","--dangerously-skip-permissions",prompt]
        elif agent_type == "gemini":
            executable_path = "gemini"            
            additional_args = ["-y" ,"--model", "gemini-2.0-flash","-p",prompt]
        elif agent_type == "codex":
            executable_path = "codex"
            # additional_args = ["--api-key", env_vars["OPENAI_API_KEY"]]
        # Build command arguments
        cmd = [executable_path]
        cmd.extend(additional_args)
        
        # Add model if specified
        if model:
            cmd.extend(['--model', model])
        
        # Add max tokens if specified
        if max_tokens:
            cmd.extend(['--max-tokens', str(max_tokens)])
        
        # Add temperature if specified
        if temperature is not None:
            cmd.extend(['--temperature', str(temperature)])
        
        # Add base URL if specified
        if base_url:
            cmd.extend(['--base-url', base_url])
        
        # Add agent-specific configuration
        for key, value in agent.configuration.items():
            if isinstance(value, (str, int, float)):
                cmd.extend([f'--{key}', str(value)])
        
        try:
            logger.debug(
                "Executing agent CLI",
                command=cmd[0],  # Don't log full command to avoid exposing secrets
                agent=agent.agent.get('name', 'unknown'),
                timeout=timeout_seconds
            )
            
            # Execute the CLI command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode('utf-8')),
                timeout=timeout_seconds
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else f"Process exited with code {process.returncode}"
                raise subprocess.CalledProcessError(process.returncode, cmd[0], stderr=error_msg)
            
            return stdout.decode('utf-8')
        
        except asyncio.TimeoutError:
            raise TimeoutError(f"Agent CLI execution timed out after {timeout_seconds} seconds")
        except Exception as e:
            logger.error(
                "CLI execution failed",
                agent=agent.agent.get('name', 'unknown'),
                error=str(e)
            )
            raise
    
    async def _handle_agent_output(
        self,
        agent: AgentDefinition,
        output: str,
        github_context: GitHubActionContext,
        event: GitHubEvent,
        file_changes: List[FileChange]
    ) -> Dict[str, Any]:
        """Handle agent output based on configured destination."""
        destination = agent.output.destination
        results = {}
        
        # For file-based outputs, read from the specified file
        if agent.output.output_file:
            try:
                with open(agent.output.output_file, 'r', encoding='utf-8') as f:
                    output = f.read()
                logger.info(
                    "Read agent output from file",
                    agent=agent.agent.get('name', 'unknown'),
                    output_file=agent.output.output_file,
                    output_length=len(output)
                )
            except Exception as e:
                logger.warning(
                    "Failed to read output file, using direct output",
                    agent=agent.agent.get('name', 'unknown'),
                    output_file=agent.output.output_file,
                    error=str(e)
                )
        
        # Apply output template if specified
        if agent.output.template:
            try:
                template_vars = {
                    'output': output,
                    'agent': agent.agent,
                    'event': event.dict(),
                    'github_context': github_context.dict(),
                    'files_changed': [fc.dict() for fc in file_changes]
                }
                output = render_template_with_file_inclusion(
                    template_str=agent.output.template,
                    context_vars=template_vars,
                    workspace_path=github_context.workspace,
                    files_changed=file_changes,
                    github_context=github_context
                )
            except Exception as e:
                logger.warning(
                    "Failed to apply output template",
                    agent=agent.agent.get('name', 'unknown'),
                    error=str(e)
                )
        
        # Truncate output if max_length is specified
        if agent.output.max_length and len(output) > agent.output.max_length:
            output = output[:agent.output.max_length] + "...\n[Output truncated]"
        
        if destination == OutputDestination.CONSOLE:
            print(f"\n=== Agent: {agent.agent.get('name', 'unknown')} ===")
            print(output)
            print("=" * 50)
        
        elif destination == OutputDestination.FILE:
            if agent.output.file_path:
                file_path = Path(agent.output.file_path)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(output)
                logger.info(
                    "Agent output written to file",
                    agent=agent.agent.get('name', 'unknown'),
                    file_path=str(file_path)
                )
        
        elif destination == OutputDestination.ARTIFACT:
            # For GitHub Actions artifacts, write to a file in a known location
            artifacts_dir = Path(github_context.workspace) / "agent-artifacts"
            artifacts_dir.mkdir(exist_ok=True)
            
            artifact_file = artifacts_dir / f"{agent.agent.get('name', 'unknown')}-output.{agent.output.format}"
            with open(artifact_file, 'w', encoding='utf-8') as f:
                f.write(output)
            
            logger.info(
                "Agent output written to artifact",
                agent=agent.agent.get('name', 'unknown'),
                artifact_path=str(artifact_file)
            )
        
        elif destination == OutputDestination.STATUS_CHECK:
            # Post status check to GitHub
            if self._github_token:
                await self._handle_status_check(agent, output, github_context, results)
        
        elif destination == OutputDestination.COMMENT:
            # Post comment to PR/issue
            if self._github_token:
                await self._handle_comment(agent, output, github_context, event, results, file_changes)
        
        elif destination == OutputDestination.CREATE_ISSUE:
            # Create new issue
            if self._github_token:
                await self._handle_create_issue(agent, output, github_context, event, file_changes, results)
        
        else:
            logger.info(
                "Agent output ready for destination",
                agent=agent.agent.get('name', 'unknown'),
                destination=destination,
                output_length=len(output)
            )
        
        return results
    
    async def _handle_status_check(
        self,
        agent: AgentDefinition,
        output: str,
        github_context: GitHubActionContext,
        results: Dict[str, Any]
    ) -> None:
        """Handle posting a status check to GitHub."""
        try:
            github_api = GitHubAPI(self._github_token)
            
            # Determine status based on keywords in output
            state = "success"  # Default to success
            if agent.output.status_check_failure_on:
                for keyword in agent.output.status_check_failure_on:
                    if keyword.lower() in output.lower():
                        state = "failure"
                        break
            
            if state == "success" and agent.output.status_check_success_on:
                # Only consider success if success keywords are found
                found_success = False
                for keyword in agent.output.status_check_success_on:
                    if keyword.lower() in output.lower():
                        found_success = True
                        break
                if not found_success:
                    state = "error"  # Neither success nor failure keywords found
            
            # Get repository info
            repository_parts = github_context.repository.split('/')
            owner, repo = repository_parts[0], repository_parts[1]
            
            # Use SHA from context
            sha = github_context.sha
            
            # Status check name
            context = agent.output.status_check_name or f"AI Agent: {agent.agent.get('name', 'unknown')}"
            
            # Description (first 140 chars of output)
            description = output[:140].replace('\n', ' ').strip()
            if len(output) > 140:
                description += "..."
            
            success = await github_api.create_status_check(
                owner=owner,
                repo=repo,
                sha=sha,
                state=state,
                context=context,
                description=description
            )
            
            if success:
                results['status_check_posted'] = state
                logger.info(
                    "Status check posted successfully",
                    agent=agent.agent.get('name', 'unknown'),
                    state=state,
                    context=context
                )
            else:
                logger.error(
                    "Failed to post status check",
                    agent=agent.agent.get('name', 'unknown')
                )
                
        except Exception as e:
            logger.error(
                "Error posting status check",
                agent=agent.agent.get('name', 'unknown'),
                error=str(e)
            )
    
    async def _handle_comment(
        self,
        agent: AgentDefinition,
        output: str,
        github_context: GitHubActionContext,
        event: GitHubEvent,
        results: Dict[str, Any],
        file_changes: Optional[List[FileChange]] = None
    ) -> None:
        """Handle posting a comment to a PR or issue."""
        try:
            github_api = GitHubAPI(self._github_token)
            
            # Get repository info
            repository_parts = github_context.repository.split('/')
            owner, repo = repository_parts[0], repository_parts[1]
            
            # Determine issue/PR number from event
            issue_number = None
            if hasattr(event, 'pull_request') and event.pull_request:
                issue_number = event.pull_request.get('number')
            elif hasattr(event, 'issue') and event.issue:
                issue_number = event.issue.get('number')
            
            if not issue_number:
                logger.warning(
                    "No PR or issue number found for comment",
                    agent=agent.agent.get('name', 'unknown'),
                    event_type=github_context.event_name
                )
                return
            
            # Prepare comment body - read from file if specified
            comment_body = output
            if agent.output.comment_output_file:
                try:
                    with open(agent.output.comment_output_file, 'r', encoding='utf-8') as f:
                        comment_body = f.read()
                    logger.info(
                        "Read comment content from file",
                        agent=agent.agent.get('name', 'unknown'),
                        comment_file=agent.output.comment_output_file
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to read comment file, using output",
                        agent=agent.agent.get('name', 'unknown'),
                        comment_file=agent.output.comment_output_file,
                        error=str(e)
                    )
            elif agent.output.comment_template:
                try:
                    template_vars = {
                        'output': output,
                        'agent': agent.agent,
                        'event': event.dict(),
                        'github_context': github_context.dict(),
                        'comment_output_content': comment_body
                    }
                    comment_body = render_template_with_file_inclusion(
                        template_str=agent.output.comment_template,
                        context_vars=template_vars,
                        workspace_path=github_context.workspace,
                        files_changed=file_changes,
                        github_context=github_context
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to apply comment template",
                        agent=agent.agent.get('name', 'unknown'),
                        error=str(e)
                    )
            
            comment_url = await github_api.create_comment(
                owner=owner,
                repo=repo,
                issue_number=issue_number,
                body=comment_body
            )
            
            if comment_url:
                results['comment_posted'] = comment_url
                logger.info(
                    "Comment posted successfully",
                    agent=agent.agent.get('name', 'unknown'),
                    comment_url=comment_url
                )
            else:
                logger.error(
                    "Failed to post comment",
                    agent=agent.agent.get('name', 'unknown')
                )
                
        except Exception as e:
            logger.error(
                "Error posting comment",
                agent=agent.agent.get('name', 'unknown'),
                error=str(e)
            )
    
    async def _handle_create_issue(
        self,
        agent: AgentDefinition,
        output: str,
        github_context: GitHubActionContext,
        event: GitHubEvent,
        file_changes: List[FileChange],
        results: Dict[str, Any]
    ) -> None:
        """Handle creating a new GitHub issue."""
        try:
            github_api = GitHubAPI(self._github_token)
            
            # Get repository info
            repository_parts = github_context.repository.split('/')
            owner, repo = repository_parts[0], repository_parts[1]
            
            # For create_issue destination, the body should come from output_file if specified
            issue_body = output
            if agent.output.output_file:
                try:
                    with open(agent.output.output_file, 'r', encoding='utf-8') as f:
                        issue_body = f.read()
                    logger.info(
                        "Read issue content from output file",
                        agent=agent.agent.get('name', 'unknown'),
                        output_file=agent.output.output_file
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to read issue content from output file, using direct output",
                        agent=agent.agent.get('name', 'unknown'),
                        output_file=agent.output.output_file,
                        error=str(e)
                    )
            
            # Prepare template variables
            template_vars = {
                'output': issue_body,
                'agent': agent.agent,
                'event': event.dict(),
                'github_context': github_context.dict(),
                'files_changed': [fc.dict() for fc in file_changes]
            }
            
            # Issue title
            title = f"AI Agent Report: {agent.agent.get('name', 'unknown')}"
            if agent.output.issue_title_template:
                try:
                    title = render_template_with_file_inclusion(
                        template_str=agent.output.issue_title_template,
                        context_vars=template_vars,
                        workspace_path=github_context.workspace,
                        files_changed=file_changes,
                        github_context=github_context
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to apply issue title template",
                        agent=agent.agent.get('name', 'unknown'),
                        error=str(e)
                    )
            
            # Issue body - use the content from output_file or direct output
            body = issue_body
            if agent.output.issue_body_template:
                try:
                    body = render_template_with_file_inclusion(
                        template_str=agent.output.issue_body_template,
                        context_vars=template_vars,
                        workspace_path=github_context.workspace,
                        files_changed=file_changes,
                        github_context=github_context
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to apply issue body template",
                        agent=agent.agent.get('name', 'unknown'),
                        error=str(e)
                    )
            
            issue_number, issue_url = await github_api.create_issue(
                owner=owner,
                repo=repo,
                title=title,
                body=body,
                labels=agent.output.issue_labels or None,
                assignees=agent.output.issue_assignees or None,
                milestone=None  # Would need milestone number, not name
            )
            
            if issue_number and issue_url:
                results['issue_created'] = issue_number
                results['issue_url'] = issue_url
                logger.info(
                    "Issue created successfully",
                    agent=agent.agent.get('name', 'unknown'),
                    issue_number=issue_number,
                    issue_url=issue_url
                )
            else:
                logger.error(
                    "Failed to create issue",
                    agent=agent.agent.get('name', 'unknown')
                )
                
        except Exception as e:
            logger.error(
                "Error creating issue",
                agent=agent.agent.get('name', 'unknown'),
                error=str(e)
            )
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """Get statistics about agents."""
        return {
            "cache_size": len(self._agent_cache),
            "cache_timestamp": self._cache_timestamp,
            "cache_ttl": self._cache_ttl,
            "available_agent_types": settings.get_available_agent_types(),
        }


# Global agent manager instance
agent_manager = AgentManager() 