# agents/tool_caller.py
"""Tool Calling Agent — Decides when and how to use tools.

This is the "orchestrator" that makes AGI like OpenClaw:
- Analyzes user intent
- Decides which tools to use
- Executes tool calls
- Integrates results into response
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

import structlog

from gateway.llm_gateway import LLMGateway, LLMMessage
from gateway.llm_gateway import LLMRequest as LLMRequestType
from tools.registry import ToolRegistry

logger = structlog.get_logger()


@dataclass
class ToolCall:
    """A tool call decision."""
    tool_name: str
    params: dict[str, Any]
    reasoning: str


@dataclass
class ToolCallResult:
    """Result of a tool call."""
    tool_name: str
    success: bool
    data: Any
    error: Optional[str] = None


class ToolCallerAgent:
    """
    Agent that decides when to use tools.

    Unlike simple function calling, this agent:
    - Analyzes user intent
    - Decides which tools are relevant
    - Executes tool calls
    - Integrates results into response
    """

    def __init__(self, registry: ToolRegistry, gateway: LLMGateway):
        self.registry = registry
        self.gateway = gateway

    async def analyze_and_call(self, message: str) -> list[ToolCall]:
        """
        Analyze message and decide which tools to call.

        Returns list of tool calls to execute.
        """
        # Get available tools
        tools_info = self._get_tools_info()

        # Build analysis prompt
        prompt = f"""Analyze this user message and decide if any tools should be called.

User message: {message}

Available tools:
{tools_info}

Respond in this exact JSON format:
{{
    "needs_tools": true/false,
    "tool_calls": [
        {{
            "tool_name": "tool_name",
            "params": {{"param": "value"}},
            "reasoning": "why this tool is needed"
        }}
    ],
    "reasoning": "overall reasoning"
}}

If no tools are needed, set needs_tools to false and empty tool_calls array."""

        try:
            # Get LLM decision
            response = await self.gateway.complete(
                LLMRequestType(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0.0
                )
            )

            # Parse response
            decision = json.loads(response.content.strip())

            if not decision.get("needs_tools", False):
                logger.info("tool_caller.no_tools_needed")
                return []

            # Build tool calls
            tool_calls = []
            for call_data in decision.get("tool_calls", []):
                tool_call = ToolCall(
                    tool_name=call_data["tool_name"],
                    params=call_data["params"],
                    reasoning=call_data["reasoning"]
                )
                tool_calls.append(tool_call)
                logger.info("tool_caller.decided", tool=tool_call.tool_name, reasoning=tool_call.reasoning)

            return tool_calls

        except Exception as e:
            logger.exception("tool_caller.analysis_failed", error=str(e))
            return []

    async def execute_calls(self, tool_calls: list[ToolCall]) -> list[ToolCallResult]:
        """
        Execute tool calls and return results.

        Executes calls in parallel where possible.
        """
        results = []

        for tool_call in tool_calls:
            try:
                logger.info("tool_caller.executing", tool=tool_call.tool_name)

                result = await self.registry.invoke(
                    tool_call.tool_name,
                    tool_call.params
                )

                call_result = ToolCallResult(
                    tool_name=tool_call.tool_name,
                    success=result.success,
                    data=result.data,
                    error=result.error
                )

                results.append(call_result)

                logger.info(
                    "tool_caller.executed",
                    tool=tool_call.tool_name,
                    success=result.success
                )

            except Exception as e:
                logger.exception("tool_caller.execution_failed", tool=tool_call.tool_name, error=str(e))
                results.append(ToolCallResult(
                    tool_name=tool_call.tool_name,
                    success=False,
                    data=None,
                    error=str(e)
                ))

        return results

    async def generate_response(
        self,
        message: str,
        tool_results: list[ToolCallResult]
    ) -> str:
        """
        Generate response incorporating tool results.

        Uses LLM to synthesize tool results into natural response.
        """
        # Build tool results context
        tool_context = ""
        if tool_results:
            tool_context = "\n\nTool Results:\n"
            for result in tool_results:
                if result.success:
                    tool_context += f"- {result.tool_name}: {result.data}\n"
                else:
                    tool_context += f"- {result.tool_name} (failed): {result.error}\n"

        # Build response prompt
        prompt = f"""Provide a direct, concise response to the user's question using the tool results.

User message: {message}
{tool_context}

Guidelines:
- Be direct and concise
- Answer the question directly
- Don't over-explain unless asked
- Use natural, conversational tone
- If tool results contain the answer, use it directly"""

        try:
            response = await self.gateway.complete(
                LLMRequestType(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                    temperature=0.7
                )
            )

            return response.content

        except Exception as e:
            logger.exception("tool_caller.response_generation_failed", error=str(e))
            return "I encountered an error generating the response."

    def _get_tools_info(self) -> str:
        """Get formatted information about available tools."""
        tools_info = []
        for tool_meta in self.registry.list_tools():
            tools_info.append(
                f"- {tool_meta.name}: {tool_meta.description}\n"
                f"  Parameters: {json.dumps(tool_meta.parameters, indent=2)}"
            )
        return "\n".join(tools_info)
