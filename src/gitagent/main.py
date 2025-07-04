"""
Main entry point for gitagent.

This module provides the main CLI interface for the gitagent,
supporting direct event processing and configuration management.
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

import structlog

from .config import Settings
from .event_handler import GitHubActionEventProcessor
from .models import (
    GitHubEvent, 
    GitHubActionContext, 
    AgentDefinition, 
    AgentType,
    AgentTriggers,
    AgentOutputConfig,
    OutputDestination
)
from .logging_config import setup_logging
from .agent_manager import agent_manager


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="gitagent - Process GitHub Action events with commit history context",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute single agent from environment variables (GitHub Action mode)
  python -m gitagent execute-agent

  # Process current GitHub Action event (legacy mode)
  python -m gitagent process

  # Process a specific event file
  python -m gitagent process --event-file event.json

  # List supported events
  python -m gitagent list-events

  # Show configuration
  python -m gitagent config

  # Validate configuration
  python -m gitagent validate-config
        """
    )
    
    # Global options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (overrides environment/config)"
    )
    parser.add_argument(
        "--log-format",
        choices=["json", "console"],
        help="Set log format (overrides environment/config)"
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-error output"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Execute single agent command (new GitHub Action mode)
    execute_agent_parser = subparsers.add_parser(
        "execute-agent",
        help="Execute single agent from environment variables"
    )
    execute_agent_parser.add_argument(
        "--event-file",
        type=Path,
        help="Path to event JSON file (default: $GITHUB_EVENT_PATH)"
    )
    execute_agent_parser.add_argument(
        "--output-file",
        type=Path,
        help="Write processing result to file"
    )
    execute_agent_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output"
    )
    
    # Process command (legacy mode)
    process_parser = subparsers.add_parser(
        "process",
        help="Process GitHub Action events"
    )
    process_parser.add_argument(
        "--event-file",
        type=Path,
        help="Path to event JSON file (default: $GITHUB_EVENT_PATH)"
    )
    process_parser.add_argument(
        "--output-file",
        type=Path,
        help="Write processing result to file"
    )
    process_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output"
    )
    
    # List events command
    list_events_parser = subparsers.add_parser(
        "list-events",
        help="List supported event types"
    )
    list_events_parser.add_argument(
        "--category",
        help="Filter by event category"
    )
    list_events_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format"
    )
    
    # Configuration commands
    config_parser = subparsers.add_parser(
        "config",
        help="Show current configuration"
    )
    config_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format"
    )
    
    validate_config_parser = subparsers.add_parser(
        "validate-config",
        help="Validate configuration"
    )
    
    # Statistics command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show processing statistics"
    )
    stats_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format"
    )
    
    # Agent commands
    agents_parser = subparsers.add_parser(
        "agents",
        help="Agent management commands"
    )
    agents_subparsers = agents_parser.add_subparsers(dest="agent_command", help="Agent subcommands")
    
    # List agents command
    list_agents_parser = agents_subparsers.add_parser(
        "list",
        help="List discovered agents"
    )
    list_agents_parser.add_argument(
        "--event-type",
        help="Filter agents by event type"
    )
    list_agents_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format"
    )
    
    # Test agent command
    test_agent_parser = agents_subparsers.add_parser(
        "test",
        help="Test agent configuration"
    )
    test_agent_parser.add_argument(
        "agent_file",
        type=Path,
        help="Path to agent YAML file"
    )
    test_agent_parser.add_argument(
        "--event-file",
        type=Path,
        help="Path to test event JSON file"
    )
    
    # Agent stats command
    agent_stats_parser = agents_subparsers.add_parser(
        "stats",
        help="Show agent statistics"
    )
    agent_stats_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format"
    )
    
    # Validate agents command
    validate_agents_parser = agents_subparsers.add_parser(
        "validate",
        help="Validate agent configurations"
    )
    validate_agents_parser.add_argument(
        "--directory",
        type=Path,
        help="Directory to validate (default: agents directory from config)"
    )
    
    return parser


def create_agent_definition_from_env() -> AgentDefinition:
    """Create agent definition from environment variables."""
    logger = structlog.get_logger(__name__)
    
    def get_env_bool(key: str, default: bool = False) -> bool:
        """Get boolean value from environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def get_env_int(key: str, default: int = 0) -> int:
        """Get integer value from environment variable."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def get_env_float(key: str, default: float = 0.0) -> float:
        """Get float value from environment variable."""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def get_env_list(key: str, default: Optional[list] = None) -> list:
        """Get list value from environment variable (comma-separated)."""
        value = os.getenv(key, "")
        if not value:
            return default or []
        return [item.strip() for item in value.split(',') if item.strip()]
    
    # Agent definition
    agent_dict = {
        "type": os.getenv("AGENT_TYPE", "custom"),
        "name": os.getenv("AGENT_NAME", "ai-agent"),
        "description": os.getenv("AGENT_DESCRIPTION", "AI agent execution"),
        "version": os.getenv("AGENT_VERSION", "1.0.0"),
    }
    
    # Add executable if specified
    if os.getenv("EXECUTABLE"):
        agent_dict["executable"] = os.getenv("EXECUTABLE")
    
    # Agent configuration
    configuration = {}
    
    # Basic configuration
    if os.getenv("MODEL"):
        configuration["model"] = os.getenv("MODEL")
    if os.getenv("MAX_TOKENS"):
        configuration["max_tokens"] = get_env_int("MAX_TOKENS")
    if os.getenv("TEMPERATURE"):
        configuration["temperature"] = get_env_float("TEMPERATURE")
    if os.getenv("TIMEOUT_SECONDS"):
        configuration["timeout_seconds"] = get_env_int("TIMEOUT_SECONDS")
    
    # Claude Code SDK specific configuration
    if os.getenv("MAX_TURNS"):
        configuration["max_turns"] = get_env_int("MAX_TURNS")
    if os.getenv("SYSTEM_PROMPT"):
        configuration["system_prompt"] = os.getenv("SYSTEM_PROMPT")
    if os.getenv("APPEND_SYSTEM_PROMPT"):
        configuration["append_system_prompt"] = os.getenv("APPEND_SYSTEM_PROMPT")
    if os.getenv("OUTPUT_FORMAT"):
        configuration["output_format"] = os.getenv("OUTPUT_FORMAT")
    if os.getenv("PERMISSION_MODE"):
        configuration["permission_mode"] = os.getenv("PERMISSION_MODE")
    if os.getenv("ALLOWED_TOOLS"):
        configuration["allowed_tools"] = get_env_list("ALLOWED_TOOLS")
    if os.getenv("DISALLOWED_TOOLS"):
        configuration["disallowed_tools"] = get_env_list("DISALLOWED_TOOLS")
    if os.getenv("USE_BEDROCK"):
        configuration["use_bedrock"] = get_env_bool("USE_BEDROCK")
    if os.getenv("USE_VERTEX"):
        configuration["use_vertex"] = get_env_bool("USE_VERTEX")
    
    # Triggers (simplified for single-agent mode)
    triggers = AgentTriggers(
        include_file_content=get_env_bool("INCLUDE_FILE_CONTENT"),
        include_file_diff=get_env_bool("INCLUDE_FILE_DIFF"),
        file_diff_context=get_env_int("FILE_DIFF_CONTEXT", 3)
    )
    
    # Output configuration
    output_config = AgentOutputConfig(
        destination=OutputDestination.CONSOLE,  # Default, can be overridden
        format=os.getenv("OUTPUT_FORMAT_TYPE", "text"),
        max_length=get_env_int("MAX_OUTPUT_LENGTH") if os.getenv("MAX_OUTPUT_LENGTH") else None,
        output_file=os.getenv("OUTPUT_FILE")
    )
    
    # Prompt template - support both direct template and file path
    prompt_template = os.getenv("PROMPT_TEMPLATE")
    prompt_template_file = os.getenv("PROMPT_TEMPLATE_FILE")
    
    if prompt_template_file:
        # Read prompt template from file
        try:
            with open(prompt_template_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except FileNotFoundError:
            logger.error(f"Prompt template file not found: {prompt_template_file}")
            raise ValueError(f"Prompt template file not found: {prompt_template_file}")
        except Exception as e:
            logger.error(f"Failed to read prompt template file: {e}")
            raise ValueError(f"Failed to read prompt template file: {e}")
    
    if not prompt_template:
        prompt_template = "Please process the following GitHub event."
    
    return AgentDefinition(
        agent=agent_dict,
        configuration=configuration,
        triggers=triggers,
        prompt_template=prompt_template,
        output=output_config,
        enabled=True,
        priority=0
    )


async def execute_single_agent(args: argparse.Namespace, settings: Settings) -> int:
    """Execute a single agent from environment variables."""
    logger = structlog.get_logger(__name__)
    
    try:
        # Create agent definition from environment variables
        agent_definition = create_agent_definition_from_env()
        
        # Determine event file path
        event_file = args.event_file
        if not event_file:
            event_file = os.getenv('GITHUB_EVENT_PATH')
            if not event_file:
                if not args.quiet:
                    print("Error: No event file specified and GITHUB_EVENT_PATH not set", file=sys.stderr)
                return 1
        
        event_file = Path(event_file)
        
        # Load event data if file exists
        event_data = {}
        if event_file.exists():
            try:
                with open(event_file, 'r', encoding='utf-8') as f:
                    event_data = json.load(f)
            except json.JSONDecodeError as e:
                if not args.quiet:
                    print(f"Error: Invalid JSON in event file: {e}", file=sys.stderr)
                return 1
            except Exception as e:
                if not args.quiet:
                    print(f"Error: Failed to read event file: {e}", file=sys.stderr)
                return 1
        
        # Create GitHub event object
        github_event = GitHubEvent(**event_data)
        
        # Get GitHub Action context
        github_context = GitHubActionContext(
            event_name=os.getenv("GITHUB_EVENT_NAME", "unknown"),
            workflow=os.getenv("GITHUB_WORKFLOW", "unknown"),
            job=os.getenv("GITHUB_JOB", "unknown"),
            run_id=os.getenv("GITHUB_RUN_ID", "0"),
            run_number=int(os.getenv("GITHUB_RUN_NUMBER", "0")),
            actor=os.getenv("GITHUB_ACTOR", "unknown"),
            repository=os.getenv("GITHUB_REPOSITORY", "unknown"),
            ref=os.getenv("GITHUB_REF", "refs/heads/main"),
            sha=os.getenv("GITHUB_SHA", "unknown"),
            workspace=os.getenv("WORKSPACE_PATH") or os.getenv("GITHUB_WORKSPACE", os.getcwd()),
            server_url=os.getenv("GITHUB_SERVER_URL", "https://github.com"),
            api_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
            graphql_url=os.getenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
        )
        
        # Get commit history
        from .event_handler import BaseEventHandler
        base_handler = BaseEventHandler(settings)
        commit_history = await base_handler._get_commit_history(
            github_context, 
            settings.git_commit_history_count
        )
        
        # Execute the agent
        agent_manager_instance = agent_manager
        agent_manager_instance._github_token = settings.github_token
        
        result = await agent_manager_instance.execute_agent(
            agent_definition,
            github_event,
            github_context,
            commit_history
        )
        
        # Prepare output data
        output_data = {
            "success": result.success,
            "output": result.output or "",
            "error": result.error or "",
            "execution_time": result.execution_time,
            "agent_name": result.agent_name,
            "agent_type": result.agent_type.value,
            "commit_history": commit_history.dict() if commit_history else None,
            "files_changed": [fc.dict() for fc in (result.files_changed or [])],
            "github_context": github_context.dict(),
            "model_used": agent_definition.configuration.get("model"),
            "tokens_used": result.metadata.get("tokens_used") if result.metadata else None,
            "cost_usd": result.metadata.get("cost_usd") if result.metadata else None,
            "session_id": result.metadata.get("session_id") if result.metadata else None,
            "turns_used": result.metadata.get("turns_used") if result.metadata else None,
            "output_file_path": agent_definition.output.output_file if agent_definition.output.output_file else None
        }
        
        # Set GitHub Actions outputs
        github_outputs_path = os.getenv("GITHUB_OUTPUT")
        if github_outputs_path:
            try:
                with open(github_outputs_path, 'a', encoding='utf-8') as f:
                    f.write(f"success={str(result.success).lower()}\n")
                    f.write(f"output={result.output or ''}\n")
                    f.write(f"error={result.error or ''}\n")
                    f.write(f"execution-time={result.execution_time}\n")
                    f.write(f"agent-name={result.agent_name}\n")
                    f.write(f"agent-type={result.agent_type.value}\n")
                    f.write(f"commit-history={json.dumps(commit_history.dict()) if commit_history else '{}'}\n")
                    f.write(f"files-changed={json.dumps([fc.dict() for fc in (result.files_changed or [])])}\n")
                    f.write(f"github-context={json.dumps(github_context.dict())}\n")
                    
                    # Optional metadata outputs
                    if agent_definition.configuration.get("model"):
                        f.write(f"model-used={agent_definition.configuration['model']}\n")
                    if result.metadata and result.metadata.get("tokens_used"):
                        f.write(f"tokens-used={result.metadata['tokens_used']}\n")
                    if result.metadata and result.metadata.get("cost_usd"):
                        f.write(f"cost-usd={result.metadata['cost_usd']}\n")
                    if result.metadata and result.metadata.get("session_id"):
                        f.write(f"session-id={result.metadata['session_id']}\n")
                    if result.metadata and result.metadata.get("turns_used"):
                        f.write(f"turns-used={result.metadata['turns_used']}\n")
                    if agent_definition.output.output_file:
                        f.write(f"output-file-path={agent_definition.output.output_file}\n")
            except Exception as e:
                logger.warning("Failed to write GitHub Actions outputs", error=str(e))
        
        # Write to output file if specified
        if args.output_file:
            try:
                with open(args.output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2 if args.pretty else None)
                logger.info("Output written to file", file=args.output_file)
            except Exception as e:
                logger.error("Failed to write output file", error=str(e))
                return 1
        
        # Print output if not quiet
        if not args.quiet:
            if args.pretty:
                print(json.dumps(output_data, indent=2))
            else:
                print(json.dumps(output_data))
        
        # Return appropriate exit code
        return 0 if result.success else 1
        
    except Exception as e:
        logger.error("Single agent execution failed", error=str(e))
        
        # Set GitHub Actions outputs for failure
        github_outputs_path = os.getenv("GITHUB_OUTPUT")
        if github_outputs_path:
            try:
                with open(github_outputs_path, 'a', encoding='utf-8') as f:
                    f.write("success=false\n")
                    f.write(f"error={str(e)}\n")
                    f.write("execution-time=0\n")
            except Exception:
                pass
        
        if not args.quiet:
            print(f"Error: {e}", file=sys.stderr)
        return 1


async def process_github_event(args: argparse.Namespace, settings: Settings) -> int:
    """Process a GitHub Action event."""
    logger = structlog.get_logger(__name__)
    
    try:
        # Determine event file path
        event_file = args.event_file
        if not event_file:
            event_file = os.getenv('GITHUB_EVENT_PATH')
            if not event_file:
                if not args.quiet:
                    print("Error: No event file specified and GITHUB_EVENT_PATH not set", file=sys.stderr)
                return 1
        
        event_file = Path(event_file)
        if not event_file.exists():
            if not args.quiet:
                print(f"Error: Event file not found: {event_file}", file=sys.stderr)
            return 1
        
        # Load event data
        try:
            with open(event_file, 'r', encoding='utf-8') as f:
                event_data = json.load(f)
        except json.JSONDecodeError as e:
            if not args.quiet:
                print(f"Error: Invalid JSON in event file: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            if not args.quiet:
                print(f"Error: Failed to read event file: {e}", file=sys.stderr)
            return 1
        
        # Create event processor
        processor = GitHubActionEventProcessor(settings)
        
        # Create GitHub event object
        github_event = GitHubEvent(**event_data)
        
        # Process the event
        result = await processor.process_event(github_event)
        
        # Prepare output
        output_data = {
            "success": result.success,
            "event_type": result.event_type,
            "processing_time": result.processing_time,
            "message": result.message
        }
        
        if result.error:
            output_data["error"] = result.error
        
        if result.commit_history:
            output_data["commit_history"] = {
                "branch": result.commit_history.branch,
                "total_commits": result.commit_history.total_commits,
                "head_sha": result.commit_history.head_sha,
                "commits": [
                    {
                        "sha": commit.sha,
                        "message": commit.message,
                        "author_name": commit.author_name,
                        "author_email": commit.author_email,
                        "timestamp": commit.timestamp.isoformat()
                    }
                    for commit in result.commit_history.commits
                ]
            }
        
        if result.github_context:
            output_data["github_context"] = {
                "event_name": result.github_context.event_name,
                "workflow": result.github_context.workflow,
                "job": result.github_context.job,
                "repository": result.github_context.repository,
                "actor": result.github_context.actor,
                "ref": result.github_context.ref,
                "sha": result.github_context.sha
            }
        
        if result.metadata:
            output_data["metadata"] = result.metadata
        
        # Format output
        if args.pretty:
            output_str = json.dumps(output_data, indent=2, ensure_ascii=False)
        else:
            output_str = json.dumps(output_data, ensure_ascii=False)
        
        # Write output
        if args.output_file:
            try:
                with open(args.output_file, 'w', encoding='utf-8') as f:
                    f.write(output_str)
                if not args.quiet:
                    print(f"Result written to: {args.output_file}")
            except Exception as e:
                if not args.quiet:
                    print(f"Error: Failed to write output file: {e}", file=sys.stderr)
                return 1
        else:
            print(output_str)
        
        # Log result
        if result.success:
            logger.info(
                "Event processed successfully",
                event_type=result.event_type,
                processing_time=result.processing_time,
                commit_count=result.commit_history.total_commits if result.commit_history else 0
            )
        else:
            logger.error(
                "Event processing failed",
                event_type=result.event_type,
                error=result.error
            )
        
        return 0 if result.success else 1
        
    except Exception as e:
        logger.error("Unexpected error during event processing", error=str(e))
        if not args.quiet:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def list_supported_events(args: argparse.Namespace, settings: Settings) -> int:
    """List supported event types."""
    try:
        processor = GitHubActionEventProcessor(settings)
        events = processor.get_supported_events()
        
        # Filter by category if specified
        if args.category:
            events = [e for e in events if e.get("category", "").lower() == args.category.lower()]
        
        if args.format == "json":
            output = {
                "events": events,
                "total_count": len(events),
                "categories": list(set(e.get("category", "") for e in events))
            }
            print(json.dumps(output, indent=2))
        else:
            # Table format
            print(f"Supported Events ({len(events)} total)")
            print("=" * 80)
            
            # Group by category
            categories = {}
            for event in events:
                category = event.get("category", "other")
                if category not in categories:
                    categories[category] = []
                categories[category].append(event)
            
            for category, category_events in sorted(categories.items()):
                print(f"\n{category.upper()}")
                print("-" * len(category))
                
                for event in sorted(category_events, key=lambda x: x.get("name", "")):
                    name = event.get("name", "")
                    handler = event.get("handler", "")
                    print(f"  {name:<30} {handler}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def show_configuration(args: argparse.Namespace, settings: Settings) -> int:
    """Show current configuration."""
    try:
        config_data = settings.get_summary()
        
        if args.format == "json":
            print(json.dumps(config_data, indent=2))
        else:
            # Table format
            print("gitagent Configuration")
            print("=" * 50)
            
            for key, value in config_data.items():
                formatted_key = key.replace("_", " ").title()
                print(f"{formatted_key:<30} {value}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def validate_configuration(args: argparse.Namespace, settings: Settings) -> int:
    """Validate configuration."""
    try:
        # Basic validation checks
        issues = []
        
        # Check GitHub Actions context
        if not settings.is_github_actions_context():
            issues.append("Not running in GitHub Actions context (missing required environment variables)")
        
        # Check event file path
        if settings.github_event_path:
            event_path = Path(settings.github_event_path)
            if not event_path.exists():
                issues.append(f"GitHub event file not found: {event_path}")
        else:
            issues.append("GITHUB_EVENT_PATH not set")
        
        # Check workspace
        if settings.github_workspace:
            workspace_path = Path(settings.github_workspace)
            if not workspace_path.exists():
                issues.append(f"GitHub workspace not found: {workspace_path}")
        
        # Check git commit history count
        if not (1 <= settings.git_commit_history_count <= 100):
            issues.append(f"Invalid git_commit_history_count: {settings.git_commit_history_count} (must be 1-100)")
        
        # Check event storage
        if settings.event_storage_enabled:
            try:
                settings.ensure_event_storage_directory()
            except Exception as e:
                issues.append(f"Cannot create event storage directory: {e}")
        
        # Output results
        if issues:
            print("Configuration Validation: FAILED")
            print("=" * 40)
            for i, issue in enumerate(issues, 1):
                print(f"{i}. {issue}")
            return 1
        else:
            print("Configuration Validation: PASSED")
            print("All configuration checks passed successfully.")
            return 0
            
    except Exception as e:
        print(f"Error during validation: {e}", file=sys.stderr)
        return 1


def show_statistics(args: argparse.Namespace, settings: Settings) -> int:
    """Show processing statistics."""
    try:
        processor = GitHubActionEventProcessor(settings)
        stats = processor.get_statistics()
        
        if args.format == "json":
            print(json.dumps(stats, indent=2))
        else:
            # Table format
            print("Processing Statistics")
            print("=" * 30)
            
            print(f"Total Events:      {stats['total_events']}")
            print(f"Successful Events: {stats['successful_events']}")
            print(f"Failed Events:     {stats['failed_events']}")
            print(f"Events per Second: {stats['events_per_second']:.2f}")
            print(f"Success Rate:      {stats['success_rate'] * 100:.1f}%")
            print(f"Uptime:            {stats['uptime_seconds']:.1f}s")
            
            if stats['events_by_type']:
                print("\nEvent Types:")
                for event_type, count in sorted(stats['events_by_type'].items()):
                    print(f"  {event_type:<20} {count}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def list_agents(args: argparse.Namespace, settings: Settings) -> int:
    """List discovered agents."""
    try:
        # Determine event types to check
        event_types = []
        if args.event_type:
            event_types = [args.event_type]
        else:
            # Get all supported event types
            from .models import GitHubActionTrigger
            event_types = [trigger.value for trigger in GitHubActionTrigger]
        
        all_agents = []
        for event_type in event_types:
            agents = await agent_manager.discover_agents(event_type, settings.github_workspace)
            for agent in agents:
                agent_info = {
                    "name": agent.agent.get("name", "unknown"),
                    "type": agent.agent.get("type", "custom"),
                    "event_type": event_type,
                    "file_path": agent.agent.get("file_path", "unknown"),
                    "priority": agent.priority,
                    "enabled": agent.enabled,
                    "description": agent.agent.get("description", "")
                }
                all_agents.append(agent_info)
        
        # Remove duplicates based on file path
        seen_paths = set()
        unique_agents = []
        for agent in all_agents:
            if agent["file_path"] not in seen_paths:
                unique_agents.append(agent)
                seen_paths.add(agent["file_path"])
        
        if args.format == "json":
            output = {
                "agents": unique_agents,
                "total_count": len(unique_agents),
                "agent_types": list(set(a["type"] for a in unique_agents)),
                "event_types": list(set(a["event_type"] for a in all_agents))
            }
            print(json.dumps(output, indent=2))
        else:
            # Table format
            print(f"Discovered Agents ({len(unique_agents)} total)")
            print("=" * 80)
            
            if not unique_agents:
                print("No agents found.")
                print(f"Agents directory: {settings.agents_directory}")
                return 0
            
            # Group by type
            agent_types = {}
            for agent in unique_agents:
                agent_type = agent["type"]
                if agent_type not in agent_types:
                    agent_types[agent_type] = []
                agent_types[agent_type].append(agent)
            
            for agent_type, type_agents in sorted(agent_types.items()):
                print(f"\n{agent_type.upper()} AGENTS")
                print("-" * (len(agent_type) + 7))
                
                for agent in sorted(type_agents, key=lambda x: x["name"]):
                    status = "✓" if agent["enabled"] else "✗"
                    print(f"  {status} {agent['name']:<25} (Priority: {agent['priority']})")
                    if agent["description"]:
                        print(f"    {agent['description']}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def test_agent(args: argparse.Namespace, settings: Settings) -> int:
    """Test agent configuration."""
    try:
        import yaml
        
        # Load agent configuration
        if not args.agent_file.exists():
            print(f"Agent file not found: {args.agent_file}", file=sys.stderr)
            return 1
        
        with open(args.agent_file, 'r', encoding='utf-8') as f:
            agent_data = yaml.safe_load(f)
        
        # Add file metadata
        if "agent" not in agent_data:
            agent_data["agent"] = {}
        agent_data["agent"]["file_path"] = str(args.agent_file)
        agent_data["agent"]["file_name"] = args.agent_file.stem
        
        # Create agent definition
        try:
            agent_def = AgentDefinition(**agent_data)
        except Exception as e:
            print(f"Invalid agent configuration: {e}", file=sys.stderr)
            return 1
        
        print(f"Agent Configuration Test: {agent_def.agent.get('name', 'unknown')}")
        print("=" * 50)
        
        # Validate agent type
        agent_type = agent_def.agent.get('type', 'custom')
        # cli_config = settings.get_agent_cli_config(agent_type)
        api_key = settings.get_agent_api_key(agent_type)
        
        print(f"Agent Type:     {agent_type}")
        print(f"Enabled:        {agent_def.enabled}")
        print(f"Priority:       {agent_def.priority}")
        # print(f"CLI Available:  {'✓' if cli_config else '✗'}")
        print(f"API Key Set:    {'✓' if api_key else '✗'}")
        
        # Test with sample event if provided
        if args.event_file:
            if not args.event_file.exists():
                print(f"Event file not found: {args.event_file}", file=sys.stderr)
                return 1
            
            with open(args.event_file, 'r', encoding='utf-8') as f:
                event_data = json.load(f)
            
            event = GitHubEvent(**event_data)
            context = GitHubActionContext(
                event_name=event_data.get("event_name", "test"),
                workflow="test-workflow",
                job="test-job",
                run_id="12345",
                run_number=1,
                actor="test-actor",
                repository="test/repo",
                ref="refs/heads/main",
                sha="abc123",
                workspace=settings.github_workspace,
                server_url=settings.github_server_url,
                api_url=settings.github_api_url,
                graphql_url=settings.github_graphql_url
            )
            
            print(f"\nTesting with event: {context.event_name}")
            
            # Test trigger conditions
            should_run = await agent_manager._should_run_agent(agent_def, event, context, None)
            print(f"Should Run:     {'✓' if should_run else '✗'}")
            
            # Test prompt rendering
            try:
                rendered_prompt = await agent_manager._render_prompt_template(
                    agent_def, event, context, None
                )
                print(f"Prompt Length:  {len(rendered_prompt)} characters")
                print(f"Template Valid: ✓")
            except Exception as e:
                print(f"Template Error: ✗ ({e})")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def show_agent_statistics(args: argparse.Namespace, settings: Settings) -> int:
    """Show agent statistics."""
    try:
        stats = agent_manager.get_agent_statistics()
        
        if args.format == "json":
            print(json.dumps(stats, indent=2))
        else:
            # Table format
            print("Agent Statistics")
            print("=" * 30)
            
            print(f"Cache Size:         {stats['cache_size']}")
            print(f"Cache TTL:          {stats['cache_ttl']}s")
            print(f"Available Types:    {', '.join(stats['available_agent_types'])}")
            print(f"Agents Enabled:     {'✓' if settings.agents_enabled else '✗'}")
            print(f"Agents Directory:   {settings.agents_directory}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def validate_agents(args: argparse.Namespace, settings: Settings) -> int:
    """Validate agent configurations."""
    try:
        import yaml
        from pathlib import Path
        
        # Determine directory to validate
        agents_dir = args.directory or Path(settings.github_workspace) / settings.agents_directory
        
        if not agents_dir.exists():
            print(f"Agents directory not found: {agents_dir}")
            return 1
        
        print(f"Validating agents in: {agents_dir}")
        print("=" * 50)
        
        issues = []
        valid_agents = 0
        total_files = 0
        
        # Find all YAML files
        for yaml_file in agents_dir.rglob("*.yml"):
            total_files += 1
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if not data:
                    issues.append(f"{yaml_file}: Empty file")
                    continue
                
                # Add metadata
                if "agent" not in data:
                    data["agent"] = {}
                data["agent"]["file_path"] = str(yaml_file)
                data["agent"]["file_name"] = yaml_file.stem
                
                # Validate against schema
                agent_def = AgentDefinition(**data)
                
                # Additional validation
                agent_type = agent_def.agent.get('type', 'custom')
                if agent_type not in ['codex', 'gemini', 'claude', 'custom']:
                    issues.append(f"{yaml_file}: Unknown agent type '{agent_type}'")
                
                # Check CLI availability if not custom
                # if agent_type != 'custom':
                #     cli_config = settings.get_agent_cli_config(agent_type)
                #     if not cli_config:
                #         issues.append(f"{yaml_file}: No CLI configuration for type '{agent_type}'")
                
                valid_agents += 1
                
            except yaml.YAMLError as e:
                issues.append(f"{yaml_file}: YAML error - {e}")
            except Exception as e:
                issues.append(f"{yaml_file}: Validation error - {e}")
        
        for yaml_file in agents_dir.rglob("*.yaml"):
            total_files += 1
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if not data:
                    issues.append(f"{yaml_file}: Empty file")
                    continue
                
                # Add metadata
                if "agent" not in data:
                    data["agent"] = {}
                data["agent"]["file_path"] = str(yaml_file)
                data["agent"]["file_name"] = yaml_file.stem
                
                # Validate against schema
                agent_def = AgentDefinition(**data)
                
                # Additional validation
                agent_type = agent_def.agent.get('type', 'custom')
                if agent_type not in ['codex', 'gemini', 'claude', 'custom']:
                    issues.append(f"{yaml_file}: Unknown agent type '{agent_type}'")
                
                # Check CLI availability if not custom
                # if agent_type != 'custom':
                #     cli_config = settings.get_agent_cli_config(agent_type)
                #     if not cli_config:
                #         issues.append(f"{yaml_file}: No CLI configuration for type '{agent_type}'")
                
                valid_agents += 1
                
            except yaml.YAMLError as e:
                issues.append(f"{yaml_file}: YAML error - {e}")
            except Exception as e:
                issues.append(f"{yaml_file}: Validation error - {e}")
        
        # Results
        print(f"Files Processed:    {total_files}")
        print(f"Valid Agents:       {valid_agents}")
        print(f"Issues Found:       {len(issues)}")
        
        if issues:
            print("\nIssues:")
            for i, issue in enumerate(issues, 1):
                print(f"{i}. {issue}")
            return 1
        else:
            print("\nAll agent configurations are valid!")
            return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def handle_agent_commands(args: argparse.Namespace, settings: Settings) -> int:
    """Handle agent subcommands."""
    if args.agent_command == "list":
        return await list_agents(args, settings)
    elif args.agent_command == "test":
        return await test_agent(args, settings)
    elif args.agent_command == "stats":
        return show_agent_statistics(args, settings)
    elif args.agent_command == "validate":
        return await validate_agents(args, settings)
    else:
        print(f"Unknown agent command: {args.agent_command}", file=sys.stderr)
        return 1


async def main():
    """Main entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Handle no command specified
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # Load settings
        settings = Settings()
        
        # Override settings from command line
        if args.log_level:
            settings.log_level = args.log_level
        if args.log_format:
            settings.log_format = args.log_format
        
        # Set up logging
        setup_logging(settings)
        
        # Execute command
        if args.command == "process":
            return await process_github_event(args, settings)
        elif args.command == "list-events":
            return list_supported_events(args, settings)
        elif args.command == "config":
            return show_configuration(args, settings)
        elif args.command == "validate-config":
            return validate_configuration(args, settings)
        elif args.command == "stats":
            return show_statistics(args, settings)
        elif args.command == "agents":
            return await handle_agent_commands(args, settings)
        elif args.command == "execute-agent":
            return await execute_single_agent(args, settings)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1
            
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        if not args.quiet:
            print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cli():
    """CLI entry point for package installation."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 