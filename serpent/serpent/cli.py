"""CLI entry point using Typer."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from serpent.config import load_config
from serpent.logging_config import setup_logging
from serpent.repl import ReplSession

app = typer.Typer(
    name="serpent",
    help="A minimal Python AI coding agent for the terminal",
    add_completion=False,
)
console = Console()


def print_banner() -> None:
    """Print the Serpent banner."""
    banner = Text()
    banner.append("🐍 ", style="bold green")
    banner.append("Serpent", style="bold cyan")
    banner.append(" v0.1.0", style="dim")
    banner.append("\n")
    banner.append("The Python AI coding agent", style="italic dim")
    console.print(Panel(banner, border_style="green", padding=(1, 2)))


@app.command()
def main(
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="LLM provider (anthropic, openai, google, deepseek, moonshot)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model ID to use"
    ),
    working_dir: Optional[Path] = typer.Option(
        None, "--working-dir", "-d", help="Working directory"
    ),
    session_id: Optional[str] = typer.Option(
        None, "--session", "-s", help="Resume a specific session"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
) -> None:
    """Start the Serpent interactive coding agent."""
    if version:
        console.print("serpent v0.1.0")
        raise typer.Exit()

    setup_logging(verbose)
    config = load_config()

    if provider:
        config.provider = provider
    if model:
        config.model = model
    if working_dir:
        config.working_dir = working_dir.resolve()

    print_banner()

    try:
        repl = ReplSession(config, session_id=session_id)
        repl.run()
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()