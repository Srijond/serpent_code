"""Read file tool implementation."""

from serpent.config import SerpentConfig
from serpent.guard import FileGuard
from serpent.tools.base import Tool, ToolResult


class ReadFileTool(Tool):
    """Tool to read text files."""
    
    def __init__(self, guard: FileGuard, config: SerpentConfig) -> None:
        self.guard = guard
        self.config = config
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Read a UTF-8 text file. Returns file contents. Only reads files within working directory. Max 1MB."
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative or absolute path to the file",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line offset to start reading from (0-indexed)",
                    "default": 0,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read",
                    "default": 100,
                },
            },
            "required": ["path"],
        }
    
    async def execute(self, arguments: dict) -> ToolResult:
        """Read a file and return contents."""
        path = arguments.get("path", "")
        offset = arguments.get("offset", 0)
        limit = arguments.get("limit", 100)
        
        try:
            target = self.guard.check_path(path)
            self.guard.is_text_file(target, self.config.max_file_size_mb)
            
            with open(target, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            start = max(0, offset)
            end = min(len(lines), start + limit)
            selected_lines = lines[start:end]
            
            numbered = []
            for i, line in enumerate(selected_lines, start=start + 1):
                numbered.append(f"{i:4d} | {line}")
            
            result = "".join(numbered)
            
            if end < len(lines):
                result += f"\n... ({len(lines) - end} more lines)"
            
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