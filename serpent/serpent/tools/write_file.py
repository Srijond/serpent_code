"""Write file tool implementation."""

from serpent.config import SerpentConfig
from serpent.guard import FileGuard
from serpent.tools.base import Tool, ToolResult


class WriteFileTool(Tool):
    """Tool to write/create files."""
    
    def __init__(self, guard: FileGuard, config: SerpentConfig) -> None:
        self.guard = guard
        self.config = config
    
    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "Create a new file or overwrite an existing file with new content."
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to create or overwrite",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        }
    
    async def execute(self, arguments: dict) -> ToolResult:
        """Write content to a file."""
        path = arguments.get("path", "")
        content = arguments.get("content", "")
        
        try:
            target = self.guard.check_path(path)
            
            target.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            
            return ToolResult(
                tool_name=self.name,
                tool_call_id="",
                content=f"Successfully wrote {len(content)} characters to {self.guard.get_relative_path(target)}",
                success=True,
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                tool_call_id="",
                content=str(e),
                success=False,
            )