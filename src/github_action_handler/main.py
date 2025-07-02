"""
Main entry point for GitHub Action Handler.

This module provides the main CLI interface for the GitHub Action Handler,
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
from .models import GitHubEvent, GitHubActionContext
from .logging_config import setup_logging


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="GitHub Action Handler - Process GitHub Action events with commit history context",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process current GitHub Action event
  python -m github_action_handler process

  # Process a specific event file
  python -m github_action_handler process --event-file event.json

  # List supported events
  python -m github_action_handler list-events

  # Show configuration
  python -m github_action_handler config

  # Validate configuration
  python -m github_action_handler validate-config
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
    
    # Process command
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
    
    return parser


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
            print("GitHub Action Handler Configuration")
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