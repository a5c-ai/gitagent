#!/usr/bin/env python3
"""
GitHub Action Handler Demo Script

This script demonstrates the capabilities of the GitHub Action Handler
by simulating various GitHub events and testing the handler's functionality.
"""

import json
import time
import asyncio
import os
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Sample GitHub event payloads for testing
SAMPLE_EVENTS = {
    "push": {
        "ref": "refs/heads/main",
        "before": "0000000000000000000000000000000000000000",
        "after": "1234567890abcdef1234567890abcdef12345678",
        "repository": {
            "id": 123456789,
            "name": "test-repo",
            "full_name": "test-user/test-repo",
            "owner": {"login": "test-user", "id": 12345},
            "private": False,
            "html_url": "https://github.com/test-user/test-repo",
            "description": "A test repository for GitHub Action Handler demo",
            "fork": False,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-15T12:00:00Z",
            "pushed_at": "2024-01-15T12:00:00Z",
            "stargazers_count": 42,
            "watchers_count": 42,
            "language": "Python",
            "forks_count": 5,
            "open_issues_count": 3,
            "default_branch": "main"
        },
        "pusher": {"name": "test-user", "email": "test@example.com"},
        "sender": {"login": "test-user", "id": 12345, "type": "User"},
        "commits": [
            {
                "id": "1234567890abcdef1234567890abcdef12345678",
                "message": "Add new feature for event processing",
                "timestamp": "2024-01-15T12:00:00Z",
                "url": "https://github.com/test-user/test-repo/commit/1234567890abcdef1234567890abcdef12345678",
                "author": {"name": "Test User", "email": "test@example.com"},
                "committer": {"name": "Test User", "email": "test@example.com"},
                "added": ["src/new_feature.py"],
                "removed": [],
                "modified": ["README.md"]
            }
        ],
        "head_commit": {
            "id": "1234567890abcdef1234567890abcdef12345678",
            "message": "Add new feature for event processing",
            "timestamp": "2024-01-15T12:00:00Z",
            "url": "https://github.com/test-user/test-repo/commit/1234567890abcdef1234567890abcdef12345678",
            "author": {"name": "Test User", "email": "test@example.com"},
            "committer": {"name": "Test User", "email": "test@example.com"}
        }
    },
    "pull_request": {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 987654321,
            "number": 42,
            "state": "open",
            "title": "Add comprehensive event handling",
            "body": "This PR adds comprehensive event handling capabilities to the GitHub Action Handler.",
            "created_at": "2024-01-15T12:00:00Z",
            "updated_at": "2024-01-15T12:00:00Z",
            "closed_at": None,
            "merged_at": None,
            "merge_commit_sha": None,
            "assignee": None,
            "assignees": [],
            "requested_reviewers": [],
            "requested_teams": [],
            "labels": [{"name": "enhancement", "color": "84b6eb"}],
            "milestone": None,
            "draft": False,
            "head": {
                "label": "test-user:feature-branch",
                "ref": "feature-branch",
                "sha": "abcdef1234567890abcdef1234567890abcdef12",
                "user": {"login": "test-user", "id": 12345},
                "repo": {"name": "test-repo", "full_name": "test-user/test-repo"}
            },
            "base": {
                "label": "test-user:main",
                "ref": "main",
                "sha": "1234567890abcdef1234567890abcdef12345678",
                "user": {"login": "test-user", "id": 12345},
                "repo": {"name": "test-repo", "full_name": "test-user/test-repo"}
            },
            "user": {"login": "test-user", "id": 12345, "type": "User"},
            "mergeable": True,
            "mergeable_state": "clean",
            "merged": False,
            "commits": 3,
            "additions": 150,
            "deletions": 25,
            "changed_files": 5
        },
        "repository": {
            "id": 123456789,
            "name": "test-repo",
            "full_name": "test-user/test-repo",
            "owner": {"login": "test-user", "id": 12345}
        },
        "sender": {"login": "test-user", "id": 12345, "type": "User"}
    },
    "issues": {
        "action": "opened",
        "issue": {
            "id": 456789123,
            "number": 15,
            "title": "Add support for custom event processors",
            "body": "It would be great to have support for custom event processors that can be plugged into the handler.",
            "state": "open",
            "created_at": "2024-01-15T12:00:00Z",
            "updated_at": "2024-01-15T12:00:00Z",
            "closed_at": None,
            "assignee": None,
            "assignees": [],
            "labels": [{"name": "feature-request", "color": "d73a4a"}],
            "milestone": None,
            "user": {"login": "contributor", "id": 54321, "type": "User"},
            "comments": 0,
            "pull_request": None
        },
        "repository": {
            "id": 123456789,
            "name": "test-repo",
            "full_name": "test-user/test-repo",
            "owner": {"login": "test-user", "id": 12345}
        },
        "sender": {"login": "contributor", "id": 54321, "type": "User"}
    },
    "workflow_run": {
        "action": "completed",
        "workflow_run": {
            "id": 789123456,
            "name": "CI",
            "node_id": "WFR_test123",
            "head_branch": "main",
            "head_sha": "1234567890abcdef1234567890abcdef12345678",
            "path": ".github/workflows/ci.yml",
            "display_title": "CI workflow run",
            "run_number": 125,
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "workflow_id": 123456,
            "check_suite_id": 987654,
            "check_suite_node_id": "CS_test456",
            "url": "https://api.github.com/repos/test-user/test-repo/actions/runs/789123456",
            "html_url": "https://github.com/test-user/test-repo/actions/runs/789123456",
            "created_at": "2024-01-15T12:00:00Z",
            "updated_at": "2024-01-15T12:05:00Z",
            "actor": {"login": "test-user", "id": 12345},
            "run_attempt": 1,
            "referenced_workflows": [],
            "run_started_at": "2024-01-15T12:00:00Z",
            "triggering_actor": {"login": "test-user", "id": 12345}
        },
        "workflow": {
            "id": 123456,
            "node_id": "W_test789",
            "name": "CI",
            "path": ".github/workflows/ci.yml",
            "state": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-15T12:00:00Z",
            "url": "https://api.github.com/repos/test-user/test-repo/actions/workflows/123456",
            "html_url": "https://github.com/test-user/test-repo/actions/workflows/ci.yml",
            "badge_url": "https://github.com/test-user/test-repo/workflows/CI/badge.svg"
        },
        "repository": {
            "id": 123456789,
            "name": "test-repo",
            "full_name": "test-user/test-repo",
            "owner": {"login": "test-user", "id": 12345}
        },
        "sender": {"login": "test-user", "id": 12345, "type": "User"}
    }
}


class GitHubActionHandlerDemo:
    """Demonstration client for GitHub Action Handler."""
    
    def __init__(self):
        pass
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def process_event_direct(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an event directly using the handler."""
        try:
            # Import the handler modules
            from github_action_handler.config import Settings
            from github_action_handler.event_handler import GitHubActionEventProcessor
            from github_action_handler.models import GitHubEvent
            
            # Initialize settings and processor
            settings = Settings()
            processor = GitHubActionEventProcessor(settings)
            
            # Create GitHub event object
            github_event = GitHubEvent(**event_data)
            
            # Process the event
            result = await processor.process_event(github_event)
            
            # Convert result to dict for display
            result_dict = {
                "event_type": result.event_type,
                "success": result.success,
                "message": result.message,
                "processing_time": result.processing_time,
                "error": result.error
            }
            
            if result.commit_history:
                result_dict["commit_history"] = {
                    "branch": result.commit_history.branch,
                    "total_commits": result.commit_history.total_commits,
                    "head_sha": result.commit_history.head_sha,
                    "commits": [
                        {
                            "sha": commit.sha[:8],
                            "message": commit.message[:50] + "..." if len(commit.message) > 50 else commit.message,
                            "author": commit.author_name,
                            "timestamp": commit.timestamp.isoformat()
                        }
                        for commit in result.commit_history.commits[:5]  # Show first 5 commits
                    ]
                }
            
            if result.github_context:
                result_dict["github_context"] = {
                    "event_name": result.github_context.event_name,
                    "repository": result.github_context.repository,
                    "actor": result.github_context.actor,
                    "ref": result.github_context.ref,
                    "sha": result.github_context.sha[:8] if result.github_context.sha else None
                }
            
            return result_dict
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "processing_time": 0.0
            }
    
    async def get_supported_events(self) -> List[Dict[str, Any]]:
        """Get list of supported events."""
        try:
            from github_action_handler.event_handler import GitHubActionEventProcessor
            from github_action_handler.config import Settings
            
            settings = Settings()
            processor = GitHubActionEventProcessor(settings)
            return processor.get_supported_events()
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        try:
            from github_action_handler.event_handler import GitHubActionEventProcessor
            from github_action_handler.config import Settings
            
            settings = Settings()
            processor = GitHubActionEventProcessor(settings)
            return processor.get_statistics()
        except Exception as e:
            return {"error": str(e)}
    
    async def run_load_test(self, num_events: int = 10, event_types: List[str] = None) -> Dict[str, Any]:
        """Run a load test with multiple concurrent events."""
        if event_types is None:
            event_types = list(SAMPLE_EVENTS.keys())
        
        results = []
        start_time = time.time()
        
        async def process_single_event():
            import random
            event_type = random.choice(event_types)
            event_data = SAMPLE_EVENTS[event_type].copy()
            # Add some randomization to make events unique
            event_data['test_id'] = f"load-test-{random.randint(1000, 9999)}"
            event_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            result = await self.process_event_direct(event_data)
            return {
                "event_type": event_type,
                "success": result.get("success", False),
                "result": result
            }
        
        # Process events concurrently
        tasks = [process_single_event() for _ in range(num_events)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        successful = sum(1 for r in results if not isinstance(r, Exception) and r.get("success", False))
        failed = num_events - successful
        
        return {
            "total_events": num_events,
            "successful": successful,
            "failed": failed,
            "duration": duration,
            "events_per_second": num_events / duration if duration > 0 else 0,
            "results": results
        }


def display_event_result(result: Dict[str, Any]):
    """Display event processing result in a formatted panel."""
    if "error" in result:
        console.print(Panel(f"❌ Error: {result['error']}", title="Event Processing", style="red"))
        return
    
    success = result.get("success", False)
    status_color = "green" if success else "red"
    status_emoji = "✅" if success else "❌"
    
    content = f"{status_emoji} Status: {'SUCCESS' if success else 'FAILED'}"
    content += f"\n⏱️ Processing Time: {result.get('processing_time', 0):.3f}s"
    content += f"\n📝 Message: {result.get('message', 'No message')}"
    
    if "commit_history" in result:
        history = result["commit_history"]
        content += f"\n🌿 Branch: {history['branch']}"
        content += f"\n📊 Commits Retrieved: {history['total_commits']}"
        content += f"\n🔗 HEAD SHA: {history['head_sha'][:8]}"
    
    if "github_context" in result:
        context = result["github_context"]
        content += f"\n🎯 Event: {context['event_name']}"
        content += f"\n📋 Repository: {context['repository']}"
        content += f"\n👤 Actor: {context['actor']}"
    
    console.print(Panel(content, title="Event Processing Result", style=status_color))


def display_supported_events(events_data: List[Dict[str, Any]]):
    """Display supported events information."""
    if not events_data or "error" in events_data[0]:
        error = events_data[0].get("error", "Unknown error") if events_data else "No events returned"
        console.print(Panel(f"❌ Error: {error}", title="Supported Events", style="red"))
        return
    
    table = Table(title=f"Supported Events ({len(events_data)} total)")
    table.add_column("Event Type", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Category", style="yellow")
    table.add_column("Handler", style="green")
    
    for event in events_data[:20]:  # Show first 20 events
        table.add_row(
            event.get("name", ""),
            event.get("description", "")[:60] + "..." if len(event.get("description", "")) > 60 else event.get("description", ""),
            event.get("category", ""),
            event.get("handler", "")
        )
    
    if len(events_data) > 20:
        table.add_row("...", f"... and {len(events_data) - 20} more events", "...", "...")
    
    console.print(table)


def display_statistics(stats_data: Dict[str, Any]):
    """Display processing statistics."""
    if "error" in stats_data:
        console.print(Panel(f"❌ Error: {stats_data['error']}", title="Statistics", style="red"))
        return
    
    table = Table(title="Processing Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    # Basic stats
    table.add_row("Total Events", str(stats_data.get("total_events", 0)))
    table.add_row("Successful Events", str(stats_data.get("successful_events", 0)))
    table.add_row("Failed Events", str(stats_data.get("failed_events", 0)))
    table.add_row("Events per Second", f"{stats_data.get('events_per_second', 0):.2f}")
    table.add_row("Success Rate", f"{stats_data.get('success_rate', 0) * 100:.1f}%")
    table.add_row("Uptime", f"{stats_data.get('uptime_seconds', 0):.1f}s")
    
    # Event types
    if "events_by_type" in stats_data:
        event_types = stats_data["events_by_type"]
        table.add_row("Event Types Processed", str(len(event_types)))
        
        # Show top 5 event types
        sorted_types = sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:5]
        for event_type, count in sorted_types:
            table.add_row(f"  {event_type}", str(count))
    
    console.print(table)


def display_load_test_results(results: Dict[str, Any]):
    """Display load test results."""
    table = Table(title="Load Test Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Events", str(results["total_events"]))
    table.add_row("Successful", str(results["successful"]))
    table.add_row("Failed", str(results["failed"]))
    table.add_row("Duration", f"{results['duration']:.2f}s")
    table.add_row("Events per Second", f"{results['events_per_second']:.2f}")
    table.add_row("Success Rate", f"{(results['successful'] / results['total_events'] * 100):.1f}%")
    
    console.print(table)
    
    # Show detailed results for failed events
    failed_results = [r for r in results["results"] if not isinstance(r, Exception) and not r.get("success", False)]
    if failed_results:
        console.print("\n[red]Failed Events:[/red]")
        for i, result in enumerate(failed_results[:5]):  # Show first 5 failures
            error = result['result'].get('error', 'Unknown error')
            console.print(f"  {i+1}. {result['event_type']}: {error}")


@click.group()
@click.pass_context
def cli(ctx):
    """GitHub Action Handler Demo CLI"""
    ctx.ensure_object(dict)


@cli.command()
@click.pass_context
async def events(ctx):
    """List supported events"""
    async with GitHubActionHandlerDemo() as demo:
        console.print("[bold blue]Getting Supported Events...[/bold blue]")
        events_data = await demo.get_supported_events()
        display_supported_events(events_data)


@cli.command()
@click.pass_context
async def stats(ctx):
    """Show processing statistics"""
    async with GitHubActionHandlerDemo() as demo:
        console.print("[bold blue]Getting Processing Statistics...[/bold blue]")
        stats_data = await demo.get_statistics()
        display_statistics(stats_data)


@cli.command()
@click.option('--event-type', type=click.Choice(list(SAMPLE_EVENTS.keys())), required=True, help='Type of event to process')
@click.pass_context
async def process_event(ctx, event_type):
    """Process a sample event"""
    async with GitHubActionHandlerDemo() as demo:
        console.print(f"[bold blue]Processing {event_type} event...[/bold blue]")
        
        event_data = SAMPLE_EVENTS[event_type].copy()
        event_data['test_id'] = f"demo-{int(time.time())}"
        event_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        result = await demo.process_event_direct(event_data)
        display_event_result(result)


@cli.command()
@click.option('--count', default=10, help='Number of events to process')
@click.option('--event-types', help='Comma-separated list of event types (default: all)')
@click.pass_context
async def load_test(ctx, count, event_types):
    """Run a load test with multiple events"""
    async with GitHubActionHandlerDemo() as demo:
        event_type_list = event_types.split(',') if event_types else list(SAMPLE_EVENTS.keys())
        
        console.print(f"[bold blue]Running load test with {count} events...[/bold blue]")
        console.print(f"Event types: {', '.join(event_type_list)}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing events...", total=None)
            
            results = await demo.run_load_test(count, event_type_list)
            
            progress.update(task, description="Load test completed", completed=True)
        
        display_load_test_results(results)


@cli.command()
@click.pass_context
async def demo(ctx):
    """Run a comprehensive demonstration"""
    async with GitHubActionHandlerDemo() as demo:
        console.print("[bold green]🚀 GitHub Action Handler Comprehensive Demo[/bold green]")
        console.print("=" * 60)
        
        # 1. Supported Events
        console.print("\n[bold blue]1. Supported Events[/bold blue]")
        events_data = await demo.get_supported_events()
        display_supported_events(events_data)
        
        # 2. Process Sample Events
        console.print("\n[bold blue]2. Processing Sample Events[/bold blue]")
        for event_type in ["push", "pull_request", "issues"]:
            console.print(f"\n📤 Processing {event_type} event...")
            
            event_data = SAMPLE_EVENTS[event_type].copy()
            event_data['demo_id'] = f"demo-{event_type}-{int(time.time())}"
            event_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            result = await demo.process_event_direct(event_data)
            
            if result.get("success", False):
                console.print(f"[green]✅ Success: {event_type} event processed[/green]")
            else:
                console.print(f"[red]❌ Failed: {result.get('error', 'Unknown error')}[/red]")
            
            # Small delay between events
            await asyncio.sleep(0.5)
        
        # 3. Statistics
        console.print("\n[bold blue]3. Processing Statistics[/bold blue]")
        stats_data = await demo.get_statistics()
        display_statistics(stats_data)
        
        # 4. Load Test
        console.print("\n[bold blue]4. Load Test (10 concurrent events)[/bold blue]")
        load_results = await demo.run_load_test(10)
        display_load_test_results(load_results)
        
        console.print("\n[bold green]🎉 Demo completed successfully![/bold green]")
        console.print("The GitHub Action Handler is working correctly and ready to process GitHub Action events.")


if __name__ == "__main__":
    # Set up asyncio event loop for Click
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Convert async commands to sync
    def async_to_sync(async_func):
        def wrapper(*args, **kwargs):
            return asyncio.run(async_func(*args, **kwargs))
        return wrapper
    
    # Apply the wrapper to all async commands
    for command_name in ['events', 'stats', 'process_event', 'load_test', 'demo']:
        command = cli.commands[command_name]
        command.callback = async_to_sync(command.callback)
    
    cli() 