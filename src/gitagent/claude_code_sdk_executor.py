"""
Claude Code SDK Executor for gitagent.

This module provides direct integration with the Claude Code SDK Python library,
offering better programmatic control, structured responses, and improved performance
compared to CLI-based execution.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import anyio
import structlog
from claude_code_sdk import query, ClaudeCodeOptions, Message

from .config import settings
from .models import (
    AgentDefinition,
    AgentExecutionResult,
    AgentType,
    ClaudeCodeSDKConfiguration,
    ClaudeCodeSDKMessage,
    GitHubEvent,
    GitHubActionContext,
    CommitHistory,
    FileChange,
)

logger = structlog.get_logger()


class ClaudeCodeSDKExecutor:
    """Executes Claude Code SDK operations with advanced configuration and error handling."""
    
    def __init__(self, configuration: ClaudeCodeSDKConfiguration):
        self.config = configuration
        self._setup_environment()
    
    def _setup_environment(self):
        """Set up environment variables for Claude Code SDK."""
        # Set API key from configuration
        if self.config.api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.config.api_key
        elif self.config.api_key_env and os.getenv(self.config.api_key_env):
            os.environ["ANTHROPIC_API_KEY"] = os.getenv(self.config.api_key_env)
        
        # Set provider-specific environment variables
        if self.config.use_bedrock:
            os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
        elif self.config.use_vertex:
            os.environ["CLAUDE_CODE_USE_VERTEX"] = "1"
    
    async def execute_agent(
        self,
        agent: AgentDefinition,
        prompt: str,
        context: GitHubActionContext,
        commit_history: Optional[CommitHistory] = None,
        file_changes: Optional[List[FileChange]] = None
    ) -> AgentExecutionResult:
        """Execute an agent using the Claude Code SDK."""
        start_time = time.time()
        agent_name = agent.agent.get('name', 'unknown')
        
        logger.info(
            "Executing Claude Code SDK agent",
            agent=agent_name,
            prompt_length=len(prompt),
            max_tokens=self.config.max_tokens,
            model=self.config.model
        )
        
        try:
            # Prepare Claude Code options
            options = self._prepare_options(agent, context)
            
            # Execute the query
            messages, result_message = await self._execute_query(prompt, options)
            
            # Process results
            execution_result = self._process_results(
                agent, messages, result_message, start_time, file_changes or []
            )
            
            logger.info(
                "Claude Code SDK agent executed successfully",
                agent=agent_name,
                execution_time=execution_result.execution_time,
                num_turns=execution_result.num_turns,
                total_cost=execution_result.total_cost_usd,
                session_id=execution_result.session_id
            )
            
            return execution_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Claude Code SDK agent execution failed",
                agent=agent_name,
                error=str(e),
                execution_time=execution_time
            )
            
            return AgentExecutionResult(
                agent_name=agent_name,
                agent_type=AgentType.CLAUDE_CODE_SDK,
                success=False,
                error=str(e),
                execution_time=execution_time,
                output_destination=agent.output.destination,
                files_changed=file_changes or []
            )
    
    def _prepare_options(self, agent: AgentDefinition, context: GitHubActionContext) -> ClaudeCodeOptions:
        """Prepare Claude Code options from agent configuration."""
        # Start with agent-specific configuration
        options_dict = {
            "max_turns": self.config.max_turns,
            "system_prompt": self.config.system_prompt,
            "append_system_prompt": self.config.append_system_prompt,
            "cwd": Path(self.config.cwd or context.workspace),
        }
        
        # Add agent-specific configuration overrides
        if agent.configuration:
            if "max_turns" in agent.configuration:
                options_dict["max_turns"] = agent.configuration["max_turns"]
            if "system_prompt" in agent.configuration:
                options_dict["system_prompt"] = agent.configuration["system_prompt"]
            if "append_system_prompt" in agent.configuration:
                options_dict["append_system_prompt"] = agent.configuration["append_system_prompt"]
            if "temperature" in agent.configuration:
                options_dict["temperature"] = agent.configuration["temperature"]
            if "max_tokens" in agent.configuration:
                options_dict["max_tokens"] = agent.configuration["max_tokens"]
        
        # Add tool configurations
        if self.config.allowed_tools:
            options_dict["allowed_tools"] = self.config.allowed_tools
        if self.config.disallowed_tools:
            options_dict["disallowed_tools"] = self.config.disallowed_tools
        
        # Add permission mode
        if self.config.permission_mode != "default":
            options_dict["permission_mode"] = self.config.permission_mode
        
        # Add MCP configuration if available
        if self.config.mcp_config_path and Path(self.config.mcp_config_path).exists():
            options_dict["mcp_config"] = self.config.mcp_config_path
        
        return ClaudeCodeOptions(**options_dict)
    
    async def _execute_query(
        self, prompt: str, options: ClaudeCodeOptions
    ) -> Tuple[List[Message], Optional[ClaudeCodeSDKMessage]]:
        """Execute the Claude Code SDK query and collect all messages."""
        messages: List[Message] = []
        result_message: Optional[ClaudeCodeSDKMessage] = None
        
        try:
            # Execute the query with timeout
            async with anyio.create_task_group() as tg:
                async def query_task():
                    nonlocal messages, result_message
                    async for message in query(prompt=prompt, options=options):
                        messages.append(message)
                        
                        # Check if this is a result message
                        if message.get("type") == "result":
                            result_message = ClaudeCodeSDKMessage(**message)
                
                tg.start_soon(query_task)
                
                # Add timeout handling
                with anyio.move_on_after(self.config.timeout_seconds):
                    await tg.start()
                    
        except Exception as e:
            logger.error("Claude Code SDK query failed", error=str(e))
            raise
        
        return messages, result_message
    
    def _process_results(
        self,
        agent: AgentDefinition,
        messages: List[Message],
        result_message: Optional[ClaudeCodeSDKMessage],
        start_time: float,
        file_changes: List[FileChange]
    ) -> AgentExecutionResult:
        """Process the results from Claude Code SDK execution."""
        execution_time = time.time() - start_time
        agent_name = agent.agent.get('name', 'unknown')
        
        # Extract the final result text
        output = ""
        if result_message and result_message.result:
            output = result_message.result
        elif messages:
            # Find the last assistant message
            for message in reversed(messages):
                if message.get("type") == "assistant" and message.get("message"):
                    msg_content = message["message"]
                    if isinstance(msg_content, dict) and "content" in msg_content:
                        content = msg_content["content"]
                        if isinstance(content, list) and content:
                            # Extract text from content blocks
                            text_blocks = [
                                block.get("text", "") for block in content
                                if isinstance(block, dict) and block.get("type") == "text"
                            ]
                            output = "\n".join(text_blocks)
                            break
                        elif isinstance(content, str):
                            output = content
                            break
        
        # Create execution result
        result = AgentExecutionResult(
            agent_name=agent_name,
            agent_type=AgentType.CLAUDE_CODE_SDK,
            success=True,
            output=output,
            execution_time=execution_time,
            output_destination=agent.output.destination,
            files_changed=file_changes,
            metadata={
                "prompt_length": len(messages[0].get("message", {}).get("content", [{}])[0].get("text", "")) if messages else 0,
                "output_length": len(output),
                "sdk_version": "claude-code-sdk",
                "num_messages": len(messages),
            }
        )
        
        # Add SDK-specific metadata
        if result_message:
            result.session_id = result_message.session_id
            result.total_cost_usd = result_message.total_cost_usd
            result.num_turns = result_message.num_turns
            result.duration_api_ms = result_message.duration_api_ms
        
        return result
    
    async def execute_streaming_query(
        self, prompt: str, options: ClaudeCodeOptions
    ) -> List[ClaudeCodeSDKMessage]:
        """Execute a streaming query and return structured messages."""
        messages = []
        
        try:
            async for message in query(prompt=prompt, options=options):
                sdk_message = ClaudeCodeSDKMessage(**message)
                messages.append(sdk_message)
                
                # Log progress for long-running operations
                if sdk_message.type == "assistant":
                    logger.debug(
                        "Received assistant message",
                        session_id=sdk_message.session_id,
                        message_length=len(str(sdk_message.message)) if sdk_message.message else 0
                    )
        
        except Exception as e:
            logger.error("Streaming query failed", error=str(e))
            raise
        
        return messages
    
    def create_session_options(
        self, 
        session_id: Optional[str] = None,
        resume_conversation: bool = False
    ) -> ClaudeCodeOptions:
        """Create options for session-based conversations."""
        options_dict = {
            "max_turns": self.config.max_turns,
            "system_prompt": self.config.system_prompt,
            "append_system_prompt": self.config.append_system_prompt,
            "cwd": Path(self.config.cwd or settings.github_workspace),
        }
        
        # Add session management options
        if session_id and resume_conversation:
            options_dict["resume"] = session_id
        elif resume_conversation:
            options_dict["continue"] = True
        
        return ClaudeCodeOptions(**options_dict)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the Claude Code SDK integration."""
        try:
            # Simple test query
            test_options = ClaudeCodeOptions(
                max_turns=1,
                system_prompt="You are a health check assistant."
            )
            
            start_time = time.time()
            messages = []
            
            async for message in query(prompt="Say 'OK' if you're working properly.", options=test_options):
                messages.append(message)
                if message.get("type") == "result":
                    break
            
            execution_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "execution_time": execution_time,
                "messages_received": len(messages),
                "sdk_available": True,
                "configuration": {
                    "model": self.config.model,
                    "max_tokens": self.config.max_tokens,
                    "timeout_seconds": self.config.timeout_seconds,
                    "use_bedrock": self.config.use_bedrock,
                    "use_vertex": self.config.use_vertex,
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "sdk_available": False,
                "configuration": {
                    "model": self.config.model,
                    "max_tokens": self.config.max_tokens,
                    "timeout_seconds": self.config.timeout_seconds,
                    "use_bedrock": self.config.use_bedrock,
                    "use_vertex": self.config.use_vertex,
                }
            } 