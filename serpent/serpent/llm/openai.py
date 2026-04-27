"""OpenAI-compatible client (OpenAI, DeepSeek, Moonshot)."""

from typing import Optional

from openai import AsyncOpenAI

from serpent.llm.base import ChatResponse, LLMClient, ToolCall


class OpenAIClient(LLMClient):
    """Client for OpenAI-compatible APIs."""
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None) -> None:
        super().__init__(api_key, model, base_url)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    async def chat(self, messages: list[dict]) -> str:
        """Simple chat without tools."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""
    
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
    ) -> ChatResponse:
        """Chat with tool support."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            max_tokens=4096,
        )
        
        message = response.choices[0].message
        
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                ))
        
        return ChatResponse(
            content=message.content,
            tool_calls=tool_calls,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            }
        )
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4