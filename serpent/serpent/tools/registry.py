"""Tool registry for managing and executing tools."""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from serpent.config import SerpentConfig
from serpent.guard import FileGuard
from serpent.tools.base import Tool, ToolResult
from serpent.tools.bash import BashTool
from serpent.tools.edit_file import EditFileTool
from serpent.tools.glob_tool import GlobTool
from serpent.tools.grep_tool import GrepTool
from serpent.tools.read_file import ReadFileTool
from serpent.tools.write_file import WriteFileTool


class ToolRegistry:
    """Registry of all available tools."""
    
    def __init__(self, guard: FileGuard, config: SerpentConfig) -> None:
        self.guard = guard
        self.config = config
        self.console = Console()
        
        self._tools: dict[str, Tool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register all built-in tools."""
        tools = [
            ReadFileTool(self.guard, self.config),
            WriteFileTool(self.guard, self.config),
            EditFileTool(self.guard, self.config),
            BashTool(self.guard, self.config),
            GlobTool(self.guard, self.config),
            GrepTool(self.guard, self.config),
        ]
        
        for tool in tools:
            self._tools[tool.name] = tool
    
    def get_tool_schemas(self) -> list[dict]:
        """Get all tool schemas for LLM."""
        return [tool.get_schema() for tool in self._tools.values()]
    
    def get_tools_description(self) -> str:
        """Get human-readable tool descriptions."""
        lines = []
        for tool in self._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)
    
    async def execute(self, tool_call: Any) -> ToolResult:
        """Execute a tool call from LLM."""
        name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        tool_call_id = tool_call.id
        
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                tool_call_id=tool_call_id,
                content=f"Unknown tool: {name}",
                success=False,
            )
        
        # Check permissions for destructive tools
        if name in ("write_file", "edit_file") and not self.config.auto_confirm_writes:
            path = arguments.get("path", "unknown")
            if not Confirm.ask(f"[yellow]Allow {name} on {path}?[/yellow]", default=False):
                return ToolResult(
                    tool_name=name,
                    tool_call_id=tool_call_id,
                    content="User denied permission",
                    success=False,
                )
        
        if name == "bash" and not self.config.auto_confirm_bash:
            command = arguments.get("command", "unknown")
            self.console.print(Panel(
                f"[yellow]Command:[/yellow] {command}",
                title="Bash Execution Request",
                border_style="yellow",
            ))
            if not Confirm.ask("Execute this command?", default=False):
                return ToolResult(
                    tool_name=name,
                    tool_call_id=tool_call_id,
                    content="User denied permission",
                    success=False,
                )
        
        try:
            result = await tool.execute(arguments)
            result.tool_call_id = tool_call_id
            return result
        except Exception as e:
            return ToolResult(
                tool_name=name,
                tool_call_id=tool_call_id,
                content=str(e),
                success=False,
            )