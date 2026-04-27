"""Google Gemini client implementation."""

import json
from typing import Optional

import google.generativeai as genai

from serpent.llm.base import ChatResponse, LLMClient, ToolCall


class GeminiClient(LLMClient):
    """Client for Google Gemini API."""
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None) -> None:
        super().__init__(api_key, model, base_url)
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(model)
    
    async def chat(self, messages: list[dict]) -> str:
        """Simple chat without tools."""
        chat = self.model_instance.start_chat(history=self._convert_history(messages[:-1]))
        response = await chat.send_message_async(messages[-1]["content"])
        return response.text
    
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
    ) -> ChatResponse:
        """Chat with tool support."""
        gemini_tools = self._convert_tools(tools) if tools else None
        
        chat = self.model_instance.start_chat(history=self._convert_history(messages[:-1]))
        
        response = await chat.send_message_async(
            messages[-1]["content"],
            tools=gemini_tools,
        )
        
        tool_calls = []
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    tool_calls.append(ToolCall(
                        id=fc.name,
                        name=fc.name,
                        arguments=json.dumps(dict(fc.args)),
                    ))
        
        return ChatResponse(
            content=response.text,
            tool_calls=tool_calls,
        )
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4
    
    def _convert_history(self, messages: list[dict]) -> list:
        """Convert messages to Gemini chat history format."""
        history = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg.get("content", "")]})
        return history
    
    def _convert_tools(self, tools: list[dict]) -> list:
        """Convert tools to Gemini function declarations."""
        declarations = []
        for tool in tools:
            func = tool["function"]
            declarations.append({
                "name": func["name"],
                "description": func["description"],
                "parameters": func["parameters"],
            })
        return [{"function_declarations": declarations}]