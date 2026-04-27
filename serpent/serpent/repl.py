"""Interactive REPL with prompt_toolkit and rich."""

import asyncio
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from serpent.config import SerpentConfig
from serpent.guard import FileGuard, GitAwareness
from serpent.llm.factory import create_client
from serpent.session import SessionStore
from serpent.tools.base import ToolResult
from serpent.tools.registry import ToolRegistry


class ReplSession:
    """Main REPL session handler."""
    
    def __init__(self, config: SerpentConfig, session_id: Optional[str] = None) -> None:
        self.config = config
        self.console = Console()
        self.guard = FileGuard(config.working_dir)
        self.git = GitAwareness(config.working_dir)
        self.store = SessionStore(config)
        self.tools = ToolRegistry(self.guard, config)
        
        self.client = create_client(config)
        
        if session_id:
            self.session = self.store.load_session(session_id)
            if self.session:
                self.console.print(f"[green]Resumed session {session_id}[/green]")
            else:
                self.console.print(f"[yellow]Session {session_id} not found, starting new[/yellow]")
                self.session = self.store.create_session(config.provider, config.model)
        else:
            self.session = self.store.create_session(config.provider, config.model)
        
        history_path = config.session_dir / ".history"
        self.prompt_session = PromptSession(
            history=FileHistory(str(history_path)),
            multiline=False,
        )
        
        self.messages: list[dict] = []
        if self.session and self.session.summary:
            self.messages.append({
                "role": "system",
                "content": f"Previous conversation summary: {self.session.summary}"
            })
    
    def run(self) -> None:
        """Run the REPL loop."""
        self.console.print("\n[dim]Type /help for commands, Ctrl+C to exit[/dim]\n")
        
        while True:
            try:
                with patch_stdout():
                    user_input = self.prompt_session.prompt(
                        "> ",
                        bottom_toolbar=self._get_toolbar,
                    )
                
                if not user_input.strip():
                    continue
                
                if user_input.startswith("/"):
                    if self._handle_command(user_input):
                        break
                    continue
                
                self._process_message(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\n[dim]Use /exit to quit[/dim]")
                continue
            except EOFError:
                break
        
        self.console.print("\n[green]Session saved. Goodbye! 👋[/green]")
    
    def _get_toolbar(self) -> str:
        """Get status bar text."""
        provider = self.config.provider
        model = self.config.model
        git_info = f" | 🌿 {self.git.branch}" if self.git.branch else ""
        return f" {provider}/{model}{git_info} | Session: {self.session.id if self.session else 'new'} "
    
    def _handle_command(self, cmd: str) -> bool:
        """Handle slash commands. Returns True if should exit."""
        parts = cmd.strip().split()
        command = parts[0].lower()
        
        if command == "/exit" or command == "/quit":
            return True
        
        elif command == "/help":
            self._show_help()
        
        elif command == "/clear":
            self.console.clear()
        
        elif command == "/models":
            self._show_models()
        
        elif command == "/sessions":
            self._show_sessions()
        
        elif command == "/compact":
            self._compact_conversation()
        
        elif command == "/status":
            self._show_status()
        
        else:
            self.console.print(f"[red]Unknown command: {command}[/red]")
        
        return False
    
    def _show_help(self) -> None:
        """Show help text."""
        help_text = """
[bold]Available Commands:[/bold]
  /help      - Show this help
  /clear     - Clear screen
  /models    - Show available models
  /sessions  - List and resume sessions
  /compact   - Summarize conversation history
  /status    - Show current configuration
  /exit      - Quit Serpent

[bold]Tips:[/bold]
  • The agent can read, write, and edit files in your working directory
  • Use `bash` tool for shell commands (always requires confirmation)
  • File reads outside working directory are blocked for security
        """
        self.console.print(Panel(help_text, title="Help", border_style="blue"))
    
    def _show_models(self) -> None:
        """Show available models from registry."""
        from serpent.llm.factory import load_registry
        
        registry = load_registry()
        self.console.print("\n[bold]Available Models:[/bold]\n")
        
        for provider_name, provider in registry.providers.items():
            self.console.print(f"[cyan]{provider.name}[/cyan]")
            for model_id, model in provider.models.items():
                marker = " → " if f"{provider_name}/{model_id}" == f"{self.config.provider}/{self.config.model}" else "   "
                self.console.print(f"{marker}{model.name} ({model.context_window//1000}k context)")
            self.console.print()
    
    def _show_sessions(self) -> None:
        """Show saved sessions."""
        sessions = self.store.list_sessions()
        
        if not sessions:
            self.console.print("[dim]No saved sessions[/dim]")
            return
        
        self.console.print("\n[bold]Saved Sessions:[/bold]\n")
        for s in sessions[:10]:
            date = s.updated_at.strftime("%Y-%m-%d %H:%M")
            event_count = len(s.events)
            self.console.print(f"  [cyan]{s.id}[/cyan] {date} | {s.provider}/{s.model} | {event_count} messages")
        
        self.console.print("\n[dim]Resume with: serpent --session <id>[/dim]")
    
    def _compact_conversation(self) -> None:
        """Compact conversation by summarizing."""
        self.console.print("[yellow]Compacting conversation...[/yellow]")
        
        summary_prompt = "Summarize the key points of our conversation so far in 2-3 sentences."
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task("Summarizing...", total=None)
            summary = asyncio.run(self.client.chat([
                *self.messages,
                {"role": "user", "content": summary_prompt}
            ]))
        
        if summary:
            self.store.compact_session(summary)
            self.messages = [{
                "role": "system",
                "content": f"Previous conversation summary: {summary}"
            }]
            self.console.print("[green]Conversation compacted successfully[/green]")
    
    def _show_status(self) -> None:
        """Show current status."""
        status = f"""
Provider: {self.config.provider}
Model: {self.config.model}
Working Dir: {self.config.working_dir}
Git: {self.git.branch or "Not detected"}
Session: {self.session.id if self.session else "None"}
Messages: {len(self.messages)}
        """
        self.console.print(Panel(status, title="Status", border_style="green"))
    
    def _process_message(self, user_input: str) -> None:
        """Process a user message through the LLM."""
        self.store.add_event("user", user_input)
        self.messages.append({"role": "user", "content": user_input})
        
        system_prompt = self._build_system_prompt()
        full_messages = [{"role": "system", "content": system_prompt}] + self.messages
        
        try:
            response = asyncio.run(self._chat_with_tools(full_messages))
            
            if response:
                self.messages.append({"role": "assistant", "content": response})
                self.store.add_event("assistant", response)
                
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with tool descriptions."""
        tools_desc = self.tools.get_tools_description()
        
        from datetime import datetime
        
        prompt = f"""You are Serpent, a minimal AI coding agent. You help users write, read, and modify code.

Working directory: {self.config.working_dir}
{self.git.get_context()}

You have access to the following tools:
{tools_desc}

Rules:
1. Always use tools for file operations — never hallucinate file contents
2. Ask permission before destructive operations (writes, edits, bash)
3. Prefer reading files before editing them
4. Use glob to discover files, grep to search content
5. Keep responses concise and focused
6. When using bash, explain what the command does first

Current date: {datetime.now().strftime('%Y-%m-%d')}
"""
        return prompt
    
    async def _chat_with_tools(self, messages: list[dict]) -> str:
        """Chat with LLM, handling tool calls in a loop."""
        max_iterations = 10
        final_response = ""
        
        for iteration in range(max_iterations):
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[progress.description]Thinking... (turn {iteration + 1})"),
                transient=True,
            ) as progress:
                progress.add_task("thinking", total=None)
                
                response = await self.client.chat_with_tools(
                    messages,
                    tools=self.tools.get_tool_schemas(),
                )
            
            if not response:
                break
            
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_results = []
                for tool_call in response.tool_calls:
                    result = await self.tools.execute(tool_call)
                    tool_results.append(result)
                    self._show_tool_result(result)
                
                messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        } for tc in response.tool_calls
                    ]
                })
                
                for result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result.tool_call_id,
                        "content": result.content,
                    })
            else:
                final_response = response.content or ""
                self.console.print(Markdown(final_response))
                break
        
        return final_response
    
    def _show_tool_result(self, result: ToolResult) -> None:
        """Display tool execution result."""
        if result.success:
            if len(result.content) > 200:
                content = result.content[:200] + "..."
            else:
                content = result.content
            self.console.print(f"[dim]✓ {result.tool_name}: {content}[/dim]")
        else:
            self.console.print(f"[red]✗ {result.tool_name}: {result.content}[/red]")