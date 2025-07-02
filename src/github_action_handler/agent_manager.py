"""
AI Agent Management for GitHub Action Handler.

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
)

logger = structlog.get_logger()


class AgentManager:
    """Manages AI agent discovery, configuration, and execution."""
    
    def __init__(self):
        self.jinja_env = Environment(
            loader=FileSystemLoader("."),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._agent_cache: Dict[str, List[AgentDefinition]] = {}
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 300  # 5 minutes
    
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
    
    async def filter_agents(
        self,
        agents: List[AgentDefinition],
        event: GitHubEvent,
        github_context: GitHubActionContext,
        commit_history: Optional[CommitHistory] = None
    ) -> List[AgentDefinition]:
        """Filter agents based on trigger conditions."""
        filtered_agents = []
        
        for agent in agents:
            if await self._should_run_agent(agent, event, github_context, commit_history):
                filtered_agents.append(agent)
        
        # Sort by priority (lower number = higher priority)
        filtered_agents.sort(key=lambda a: a.priority)
        
        return filtered_agents
    
    async def _should_run_agent(
        self,
        agent: AgentDefinition,
        event: GitHubEvent,
        github_context: GitHubActionContext,
        commit_history: Optional[CommitHistory] = None
    ) -> bool:
        """Check if an agent should run based on trigger conditions."""
        triggers = agent.triggers
        
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
        
        # Check Jinja2 template conditions
        if triggers.conditions:
            template_context = {
                'event': event.dict(),
                'github_context': github_context.dict(),
                'commit_history': commit_history.dict() if commit_history else None,
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
        commit_history: Optional[CommitHistory] = None
    ) -> List[AgentExecutionResult]:
        """Execute a list of agents."""
        results = []
        
        for agent in agents:
            try:
                result = await self.execute_agent(agent, event, github_context, commit_history)
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
        commit_history: Optional[CommitHistory] = None
    ) -> AgentExecutionResult:
        """Execute a single agent."""
        start_time = time.time()
        agent_name = agent.agent.get('name', 'unknown')
        agent_type = AgentType(agent.agent.get('type', 'custom'))
        
        logger.info(
            "Executing agent",
            agent=agent_name,
            agent_type=agent_type,
            event_type=github_context.event_name
        )
        
        try:
            # Render the prompt template
            rendered_prompt = await self._render_prompt_template(
                agent, event, github_context, commit_history
            )
            
            # Execute the agent CLI
            output = await self._execute_agent_cli(agent, rendered_prompt)
            
            # Handle output destination
            await self._handle_agent_output(agent, output, github_context)
            
            execution_time = time.time() - start_time
            
            logger.info(
                "Agent executed successfully",
                agent=agent_name,
                execution_time=execution_time,
                output_length=len(output)
            )
            
            return AgentExecutionResult(
                agent_name=agent_name,
                agent_type=agent_type,
                success=True,
                output=output,
                execution_time=execution_time,
                output_destination=agent.output.destination,
                metadata={
                    'prompt_length': len(rendered_prompt),
                    'output_length': len(output),
                }
            )
        
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
    
    async def _render_prompt_template(
        self,
        agent: AgentDefinition,
        event: GitHubEvent,
        github_context: GitHubActionContext,
        commit_history: Optional[CommitHistory] = None
    ) -> str:
        """Render the agent's prompt template with context variables."""
        template_context = {
            'event': event.dict(),
            'github_context': github_context.dict(),
            'commit_history': commit_history.dict() if commit_history else None,
            'agent': agent.agent,
            'config': agent.configuration,
        }
        
        try:
            template = Template(agent.prompt_template)
            return template.render(**template_context)
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
        cli_config = settings.get_agent_cli_config(agent_type)
        
        if not cli_config:
            raise ValueError(f"No CLI configuration found for agent type: {agent_type}")
        
        # Prepare environment variables
        env = os.environ.copy()
        env.update(cli_config.environment_vars)
        
        # Add API key if available
        api_key = settings.get_agent_api_key(agent_type)
        if api_key and cli_config.api_key_env:
            env[cli_config.api_key_env] = api_key
        
        # Build command arguments
        cmd = [cli_config.executable_path]
        cmd.extend(cli_config.additional_args)
        
        # Add model if specified
        if cli_config.model:
            cmd.extend(['--model', cli_config.model])
        
        # Add max tokens if specified
        if cli_config.max_tokens:
            cmd.extend(['--max-tokens', str(cli_config.max_tokens)])
        
        # Add temperature if specified
        if cli_config.temperature is not None:
            cmd.extend(['--temperature', str(cli_config.temperature)])
        
        # Add base URL if specified
        if cli_config.base_url:
            cmd.extend(['--base-url', cli_config.base_url])
        
        # Add agent-specific configuration
        for key, value in agent.configuration.items():
            if isinstance(value, (str, int, float)):
                cmd.extend([f'--{key}', str(value)])
        
        try:
            logger.debug(
                "Executing agent CLI",
                command=cmd[0],  # Don't log full command to avoid exposing secrets
                agent=agent.agent.get('name', 'unknown'),
                timeout=cli_config.timeout_seconds
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
                timeout=cli_config.timeout_seconds
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else f"Process exited with code {process.returncode}"
                raise subprocess.CalledProcessError(process.returncode, cmd[0], stderr=error_msg)
            
            return stdout.decode('utf-8')
        
        except asyncio.TimeoutError:
            raise TimeoutError(f"Agent CLI execution timed out after {cli_config.timeout_seconds} seconds")
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
        github_context: GitHubActionContext
    ) -> None:
        """Handle agent output based on configured destination."""
        destination = agent.output.destination
        
        # Apply output template if specified
        if agent.output.template:
            try:
                template = Template(agent.output.template)
                output = template.render(output=output, agent=agent.agent)
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
        
        # For other destinations (COMMENT, PR_REVIEW, ISSUE), we would need
        # GitHub API integration, which is not implemented in this stub version
        else:
            logger.info(
                "Agent output ready for destination",
                agent=agent.agent.get('name', 'unknown'),
                destination=destination,
                output_length=len(output)
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