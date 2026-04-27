"""Grep text search tool implementation."""

import re
from pathlib import Path

from serpent.config import SerpentConfig
from serpent.guard import FileGuard
from serpent.tools.base import Tool, ToolResult


class GrepTool(Tool):
    """Tool to search text in files."""
    
    def __init__(self, guard: FileGuard, config: SerpentConfig) -> None:
        self.guard = guard
        self.config = config
    
    @property
    def name(self) -> str:
        return "grep"
    
    @property
    def description(self) -> str:
        return "Search for text patterns in files using regex. Returns matching lines with file names and line numbers."
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in",
                    "default": ".",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern for files to search (e.g., '*.py')",
                    "default": "*",
                },
            },
            "required": ["pattern"],
        }
    
    async def execute(self, arguments: dict) -> ToolResult:
        """Search for text pattern in files."""
        pattern = arguments.get("pattern", "")
        search_path = arguments.get("path", ".")
        file_pattern = arguments.get("file_pattern", "*")
        
        try:
            target = self.guard.check_path(search_path)
            
            if target.is_file():
                files = [target]
            else:
                files = list(target.rglob(file_pattern))
                files = [f for f in files if f.is_file()]
            
            regex = re.compile(pattern)
            matches = []
            match_count = 0
            
            for file_path in files:
                try:
                    self.guard.is_text_file(file_path, self.config.max_file_size_mb)
                    
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                rel_path = self.guard.get_relative_path(file_path)
                                matches.append(f"{rel_path}:{line_num}: {line.rstrip()}")
                                match_count += 1
                                if match_count >= 50:  # Limit matches
                                    break
                    
                    if match_count >= 50:
                        break
                        
                except (PermissionError, ValueError):
                    continue
            
            if not matches:
                return ToolResult(
                    tool_name=self.name,
                    tool_call_id="",
                    content=f"No matches found for '{pattern}'",
                    success=True,
                )
            
            result = f"Found {match_count} matches:\\n" + "\n".join(matches[:50])
            if match_count >= 50:
                result += "\n... (truncated to 50 matches)"
            
            return ToolResult(
                tool_name=self.name,
                tool_call_id="",
                content=result,
                success=True,
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                tool_call_id="",
                content=str(e),
                success=False,
            )