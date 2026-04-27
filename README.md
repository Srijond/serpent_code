# 🐍 Serpent

A minimal Python AI coding agent for the terminal — inspired by Keen Code, Claude Code, and Codex CLI.

&gt; **Philosophy**: Simple, opinionated, no bloat. The agent trusts the model and avoids unnecessary complexity.

## Features

- **Multi-provider LLM support**: OpenAI, Anthropic Claude, Google Gemini, DeepSeek, Moonshot AI
- **Built-in tools**: `read_file`, `write_file`, `edit_file`, `bash`, `glob`, `grep`
- **Permission system**: Ask before destructive operations
- **Session persistence**: Conversations survive across restarts
- **Context management**: Visual context window indicator + `/compact` command
- **Git awareness**: Includes branch info and repo context in prompts
- **Streaming responses**: Real-time token output

## Installation

```bash
pip install serpent-cli