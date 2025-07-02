"""
Template Functions for AI Agent Management.

This module provides advanced template functions for including files
with complex path resolution, wildcards, and directory traversal.
"""

import glob
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import structlog

from .models import FileChange, GitHubActionContext

logger = structlog.get_logger()


class TemplateFileIncluder:
    """Handles file inclusion for templates with advanced path resolution."""
    
    def __init__(self, workspace_path: Union[str, Path], files_changed: List[FileChange]):
        """Initialize the file includer.
        
        Args:
            workspace_path: Path to the repository workspace
            files_changed: List of files that changed in the current event
        """
        self.workspace_path = Path(workspace_path)
        self.files_changed = files_changed
        self._changed_dirs_cache: Optional[Set[Path]] = None
        self._ancestor_dirs_cache: Optional[Set[Path]] = None
    
    @property
    def changed_file_dirs(self) -> Set[Path]:
        """Get unique directories containing changed files."""
        if self._changed_dirs_cache is None:
            dirs = set()
            for file_change in self.files_changed:
                file_path = Path(file_change.filename)
                # Add the directory containing the file
                if file_path.parent != Path('.'):
                    dirs.add(file_path.parent)
                # Also add the root if file is in root
                dirs.add(Path('.'))
            self._changed_dirs_cache = dirs
        return self._changed_dirs_cache
    
    @property  
    def changed_file_dirs_and_ancestors(self) -> Set[Path]:
        """Get unique directories and all their ancestors up to repository root."""
        if self._ancestor_dirs_cache is None:
            dirs = set()
            
            # Start with changed file directories
            changed_dirs = self.changed_file_dirs
            
            for dir_path in changed_dirs:
                # Add the directory itself
                dirs.add(dir_path)
                
                # Add all parent directories up to root
                current = dir_path
                while current != Path('.') and current.parts:
                    current = current.parent
                    dirs.add(current)
                    if current == Path('.'):
                        break
            
            # Always include root
            dirs.add(Path('.'))
            self._ancestor_dirs_cache = dirs
        return self._ancestor_dirs_cache
    
    def include_files(self, pattern: str) -> str:
        """Include files matching a pattern.
        
        Args:
            pattern: File pattern to match. Can include special variables:
                - $ALL_UNIQUE_CHANGED_FILE_DIRS: directories containing changed files
                - $ALL_UNIQUE_CHANGED_FILE_DIRS_AND_THEIR_ANCESTORS: above + ancestors
                - $WORKSPACE: repository root
                - $CHANGED_FILES: list of changed file paths
        
        Returns:
            Combined content of all matching files
        """
        try:
            # Replace special variables in pattern
            resolved_pattern = self._resolve_pattern_variables(pattern)
            
            # Find all matching files
            matching_files = self._find_matching_files(resolved_pattern)
            
            # Read and combine file contents
            combined_content = []
            
            for file_path in sorted(matching_files):
                try:
                    content = self._read_file_content(file_path)
                    if content.strip():  # Only include non-empty files
                        combined_content.append(f"<!-- File: {file_path} -->")
                        combined_content.append(content)
                        combined_content.append("")  # Add separator
                except Exception as e:
                    logger.warning(
                        "Failed to read file for inclusion",
                        file_path=str(file_path),
                        error=str(e)
                    )
                    combined_content.append(f"<!-- Error reading file: {file_path} - {e} -->")
            
            result = "\n".join(combined_content)
            
            logger.info(
                "Included files in template",
                pattern=pattern,
                resolved_pattern=resolved_pattern,
                files_count=len(matching_files),
                total_length=len(result)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to include files",
                pattern=pattern,
                error=str(e)
            )
            return f"<!-- Error including files with pattern '{pattern}': {e} -->"
    
    def _resolve_pattern_variables(self, pattern: str) -> List[str]:
        """Resolve special variables in the pattern to actual paths.
        
        Returns a list of resolved patterns to search.
        """
        resolved_patterns = []
        
        if "$ALL_UNIQUE_CHANGED_FILE_DIRS_AND_THEIR_ANCESTORS" in pattern:
            # Replace with each directory and its ancestors
            for dir_path in self.changed_file_dirs_and_ancestors:
                resolved = pattern.replace(
                    "$ALL_UNIQUE_CHANGED_FILE_DIRS_AND_THEIR_ANCESTORS",
                    str(dir_path) if dir_path != Path('.') else "."
                )
                resolved_patterns.append(resolved)
        
        elif "$ALL_UNIQUE_CHANGED_FILE_DIRS" in pattern:
            # Replace with each changed file directory
            for dir_path in self.changed_file_dirs:
                resolved = pattern.replace(
                    "$ALL_UNIQUE_CHANGED_FILE_DIRS", 
                    str(dir_path) if dir_path != Path('.') else "."
                )
                resolved_patterns.append(resolved)
        
        elif "$WORKSPACE" in pattern:
            # Replace with workspace root
            resolved = pattern.replace("$WORKSPACE", str(self.workspace_path))
            resolved_patterns.append(resolved)
        
        elif "$CHANGED_FILES" in pattern:
            # Replace with each changed file path
            for file_change in self.files_changed:
                resolved = pattern.replace("$CHANGED_FILES", file_change.filename)
                resolved_patterns.append(resolved)
        
        else:
            # No special variables, use pattern as-is
            resolved_patterns.append(pattern)
        
        return resolved_patterns
    
    def _find_matching_files(self, resolved_patterns: List[str]) -> Set[Path]:
        """Find all files matching the resolved patterns."""
        matching_files = set()
        
        for pattern in resolved_patterns:
            try:
                # Handle absolute paths vs relative paths
                if os.path.isabs(pattern):
                    search_pattern = pattern
                else:
                    # Make relative to workspace
                    search_pattern = str(self.workspace_path / pattern)
                
                # Use glob to find matching files
                matches = glob.glob(search_pattern, recursive=True)
                
                for match in matches:
                    match_path = Path(match)
                    if match_path.is_file():  # Only include actual files
                        # Convert back to relative path for consistency
                        try:
                            relative_path = match_path.relative_to(self.workspace_path)
                            matching_files.add(relative_path)
                        except ValueError:
                            # File is outside workspace, use absolute path
                            matching_files.add(match_path)
                
            except Exception as e:
                logger.warning(
                    "Failed to glob pattern",
                    pattern=pattern,
                    error=str(e)
                )
        
        return matching_files
    
    def _read_file_content(self, file_path: Path) -> str:
        """Read content from a file."""
        # Convert to absolute path if relative
        if not file_path.is_absolute():
            abs_path = self.workspace_path / file_path
        else:
            abs_path = file_path
        
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()


def create_template_environment(
    workspace_path: Union[str, Path],
    files_changed: List[FileChange],
    github_context: Optional[GitHubActionContext] = None
) -> Dict[str, Any]:
    """Create template environment with file inclusion functions.
    
    Args:
        workspace_path: Path to the repository workspace
        files_changed: List of files that changed
        github_context: GitHub action context for additional variables
    
    Returns:
        Dictionary of template functions and variables
    """
    includer = TemplateFileIncluder(workspace_path, files_changed)
    
    # Create template functions
    template_functions = {
        'include': includer.include_files,
        'include_files': includer.include_files,  # Alias
    }
    
    # Add convenience variables
    template_vars = {
        'WORKSPACE': str(workspace_path),
        'ALL_UNIQUE_CHANGED_FILE_DIRS': [str(d) for d in includer.changed_file_dirs],
        'ALL_UNIQUE_CHANGED_FILE_DIRS_AND_THEIR_ANCESTORS': [
            str(d) for d in includer.changed_file_dirs_and_ancestors
        ],
        'CHANGED_FILES': [fc.filename for fc in files_changed],
        'CHANGED_FILE_PATHS': [fc.filename for fc in files_changed],  # Alias
    }
    
    # Combine functions and variables
    result = {**template_functions, **template_vars}
    
    return result


def render_template_with_file_inclusion(
    template_str: str,
    context_vars: Dict[str, Any],
    workspace_path: Union[str, Path],
    files_changed: List[FileChange],
    github_context: Optional[GitHubActionContext] = None
) -> str:
    """Render a template with file inclusion support.
    
    Args:
        template_str: Template string to render
        context_vars: Base context variables for template
        workspace_path: Path to the repository workspace  
        files_changed: List of files that changed
        github_context: GitHub action context
    
    Returns:
        Rendered template string
    """
    from jinja2 import Template
    
    # Create enhanced template environment
    file_functions = create_template_environment(workspace_path, files_changed, github_context)
    
    # Combine with existing context
    enhanced_context = {**context_vars, **file_functions}
    
    try:
        template = Template(template_str)
        return template.render(**enhanced_context)
    except Exception as e:
        logger.error(
            "Failed to render template with file inclusion",
            error=str(e),
            template_length=len(template_str)
        )
        raise 