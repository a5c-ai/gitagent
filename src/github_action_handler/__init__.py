"""
GitHub Action Handler - Comprehensive event processing for GitHub Actions.

This package provides a complete solution for handling GitHub Action events
with comprehensive logging, Docker support, and production-ready features.
"""

__version__ = "1.0.0"
__author__ = "AI Development Team"
__email__ = "dev@example.com"

from .config import Settings
from .event_handler import EventHandler
from .models import GitHubActionTrigger, GitHubEvent

__all__ = [
    "Settings", 
    "EventHandler",
    "GitHubActionTrigger",
    "GitHubEvent",
] 