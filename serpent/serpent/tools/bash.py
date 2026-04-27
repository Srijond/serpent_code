"""Bash execution tool implementation."""

import asyncio
import subprocess
from pathlib import Path

from serpent.config import SerpentConfig
from serpent.guard import FileGuard
from serpent.tools.base import Tool, ToolResult


class BashTool(Tool):
    """Tool to execute shell commands."""
    
    def __init__(self, guard: FileGuard, config: SerpentConfig) -> None:
        self.guard = guard
        self.config = config
    
    @property
    def name(self) -> str:
        return "bash"
    
    @property
    def description(self) -> str:
        return "Execute a bash command in the working directory. Use with caution."
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds",
                    "default": 30,
                },
            },
            "required": ["command"],
        }
    
    async def execute(self, arguments: dict) -> ToolResult:
        """Execute a bash command."""
        command = arguments.get("command", "")
        timeout = arguments.get("timeout", 30)
        
        try:
            working_dir = self.config.working_dir
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    tool_name=self.name,
                    tool_call_id="",
                    content=f"Command timed out after {timeout} seconds",
                    success=False,
                )
            
            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")
            
            if process.returncode != 0:
                return ToolResult(
                    tool_name=self.name,
                    tool_call_id="",
                    content=f"Exit code {process.returncode}:\\n{error_output}\\n{output}",
                    success=False,
                )
            
            result = output
            if error_output:
                result += f"\n[stderr]:\\n{error_output}"
            
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