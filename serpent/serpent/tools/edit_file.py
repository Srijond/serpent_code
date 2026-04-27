"""Edit file tool implementation."""

import re

from serpent.config import SerpentConfig
from serpent.guard import FileGuard
from serpent.tools.base import Tool, ToolResult


class EditFileTool(Tool):
    """Tool to edit existing files via search/replace."""
    
    def __init__(self, guard: FileGuard, config: SerpentConfig) -> None:
        self.guard = guard
        self.config = config
    
    @property
    def name(self) -> str:
        return "edit_file"
    
    @property
    def description(self) -> str:
        return "Replace specific text in an existing file. Uses exact string matching or regex."
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": "Text to search for (exact match)",
                },
                "new_string": {
                    "type": "string",
                    "description": "Text to replace with",
                },
                "use_regex": {
                    "type": "boolean",
                    "description": "Whether to use regex matching",
                    "default": False,
                },
            },
            "required": ["path", "old_string", "new_string"],
        }
    
    async def execute(self, arguments: dict) -> ToolResult:
        """Edit a file by replacing text."""
        path = arguments.get("path", "")
        old_string = arguments.get("old_string", "")
        new_string = arguments.get("new_string", "")
        use_regex = arguments.get("use_regex", False)
        
        try:
            target = self.guard.check_path(path)
            self.guard.is_text_file(target, self.config.max_file_size_mb)
            
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            
            if use_regex:
                new_content = re.sub(old_string, new_string, content)
                if new_content == content:
                    raise ValueError(f"Regex pattern '{old_string}' not found in file")
            else:
                if old_string not in content:
                    raise ValueError(f"Text '{old_string}' not found in file")
                new_content = content.replace(old_string, new_string, 1)
            
            with open(target, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            return ToolResult(
                tool_name=self.name,
                tool_call_id="",
                content=f"Successfully edited {self.guard.get_relative_path(target)}",
                success=True,
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                tool_call_id="",
                content=str(e),
                success=False,
            )