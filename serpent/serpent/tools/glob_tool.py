"""Glob file search tool implementation."""

from pathlib import Path

from serpent.config import SerpentConfig
from serpent.guard import FileGuard
from serpent.tools.base import Tool, ToolResult


class GlobTool(Tool):
    """Tool to find files by glob patterns."""
    
    def __init__(self, guard: FileGuard, config: SerpentConfig) -> None:
        self.guard = guard
        self.config = config
    
    @property
    def name(self) -> str:
        return "glob"
    
    @property
    def description(self) -> str:
        return "Find files matching a glob pattern. Returns list of matching file paths."
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., '**/*.py', 'src/*.js')",
                },
            },
            "required": ["pattern"],
        }
    
    async def execute(self, arguments: dict) -> ToolResult:
        """Find files matching a glob pattern."""
        pattern = arguments.get("pattern", "")
        
        try:
            working_dir = self.config.working_dir
            
            matches = list(working_dir.glob(pattern))
            
            # Filter to only files within working directory
            valid_matches = []
            for match in matches:
                try:
                    self.guard.check_path(match)
                    valid_matches.append(str(match.relative_to(working_dir)))
                except PermissionError:
                    continue
            
            if not valid_matches:
                return ToolResult(
                    tool_name=self.name,
                    tool_call_id="",
                    content=f"No files found matching '{pattern}'",
                    success=True,
                )
            
            result = f"Found {len(valid_matches)} files:\\n" + "\n".join(valid_matches)
            
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