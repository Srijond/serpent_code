"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Optional


class ToolCall:
    """Represents a tool call from the LLM."""
    def __init__(self, id: str, name: str, arguments: str) -> None:
        self.id = id
        self.function = type('Function', (), {'name': name, 'arguments': arguments})()


class ChatResponse:
    """Standardized response from any LLM provider."""
    def __init__(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[list] = None,
        thinking: Optional[str] = None,
        usage: Optional[dict] = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls or []
        self.thinking = thinking
        self.usage = usage or {}


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
    
    @abstractmethod
    async def chat(self, messages: list[dict]) -> str:
        """Simple chat without tools. Returns text response."""
        pass
    
    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
    ) -> ChatResponse:
        """Chat with tool support. Returns structured response."""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        pass