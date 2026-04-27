"""Anthropic Claude client implementation."""

import json
from typing import Optional

from anthropic import AsyncAnthropic

from serpent.llm.base import ChatResponse, LLMClient, ToolCall


class AnthropicClient(LLMClient):
    """Client for Anthropic's Claude API."""
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None) -> None:
        super().__init__(api_key, model, base_url)
        self.client = AsyncAnthropic(api_key=api_key, base_url=base_url)
    
    async def chat(self, messages: list[dict]) -> str:
        """Simple chat without tools."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=self._convert_messages(messages),
        )
        return response.content[0].text if response.content else ""
    
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
    ) -> ChatResponse:
        """Chat with tool support."""
        anthropic_tools = self._convert_tools(tools) if tools else []
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=self._convert_messages(messages),
            tools=anthropic_tools,
        )
        
        content = ""
        thinking = None
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "thinking":
                thinking = getattr(block, 'thinking', None)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=json.dumps(block.input),
                ))
        
        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            thinking=thinking,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        )
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text) // 4
    
    def _convert_messages(self, messages: list[dict]) -> list:
        """Convert generic messages to Anthropic format."""
        result = []
        system_content = ""
        
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            
            if role == "system":
                system_content += content + "\n"
                continue
            
            if role == "tool":
                result.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": content,
                    }]
                })
            else:
                result.append({"role": role, "content": content})
        
        if system_content:
            if result and result[0]["role"] == "user":
                result[0]["content"] = system_content + "\n" + str(result[0]["content"])
            else:
                result.insert(0, {"role": "user", "content": system_content})
        
        return result
    
    def _convert_tools(self, tools: list[dict]) -> list:
        """Convert generic tool schemas to Anthropic format."""
        return [{
            "name": tool["function"]["name"],
            "description": tool["function"]["description"],
            "input_schema": tool["function"]["parameters"],
        } for tool in tools]