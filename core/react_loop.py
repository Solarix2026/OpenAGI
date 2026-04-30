"""ReAct (Reason + Act) implementation for iterative tool calling."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any
import structlog

logger = structlog.get_logger()


class ThoughtStatus(Enum):
    """Status of a thought."""
    CONTINUE = "continue"  # Need to take more actions
    FINAL = "final"  # Ready to respond to user
    ERROR = "error"  # Something went wrong


@dataclass
class Thought:
    """A single thought in the ReAct loop."""
    status: ThoughtStatus
    reasoning: str
    tool: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    response: Optional[str] = None
    observation: Optional[str] = None

    def is_final(self) -> bool:
        """Check if this is the final thought."""
        return self.status == ThoughtStatus.FINAL

    def needs_action(self) -> bool:
        """Check if this thought requires an action."""
        return self.status == ThoughtStatus.CONTINUE and self.tool is not None


class ReActLoop:
    """ReAct (Reason + Act) loop for iterative tool calling."""

    def __init__(self, tool_caller, registry, gateway):
        self.tool_caller = tool_caller
        self.registry = registry
        self.gateway = gateway

    async def reason(
        self,
        history: list[dict[str, str]],
        observations: list[str]
    ) -> Thought:
        """
        Reason about what to do next.

        Args:
            history: Conversation history
            observations: Previous tool results

        Returns:
            Thought with next action or final response
        """
        # Build reasoning prompt
        prompt = self._build_reasoning_prompt(history, observations)

        try:
            # Get LLM reasoning
            from gateway.llm_gateway import LLMMessage
            response = await self.gateway.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                max_tokens=512,
                temperature=0.0
            )

            # Parse the reasoning
            return self._parse_reasoning(response.content)

        except Exception as e:
            logger.exception("react.reasoning_failed", error=str(e))
            return Thought(
                status=ThoughtStatus.ERROR,
                reasoning=f"Reasoning failed: {str(e)}",
                response="I encountered an error while thinking about your request."
            )

    def _build_reasoning_prompt(
        self,
        history: list[dict[str, str]],
        observations: list[str]
    ) -> str:
        """Build the reasoning prompt."""
        # Get available tools
        tools_info = self._get_tools_info()

        # Build context
        context = "Conversation history:\n"
        for msg in history:
            context += f"{msg['role']}: {msg['content']}\n"

        if observations:
            context += "\nPrevious observations:\n"
            for i, obs in enumerate(observations):
                context += f"{i+1}. {obs}\n"

        prompt = f"""You are an AI assistant that uses tools to help users. Think step by step about what to do.

{context}

Available tools:
{tools_info}

Think about what you need to do. Respond in this exact format:

If you need to use a tool:
THOUGHT: [your reasoning about what to do next]
ACTION: [tool_name]
PARAMS: {{"param": "value"}}

If you're ready to respond to the user:
THOUGHT: [your reasoning about the final answer]
FINAL: [your response to the user]

IMPORTANT RULES:
- For the 'code' tool: ALWAYS use print() to output results. Example: print(2+2) not 2+2
- For the 'code' tool: If you need imports, put them first, then print() the result
- For the 'shell' tool: Use commands that produce output to stdout
- Be concise and direct. Think carefully about whether you need more information or can answer now."""

        return prompt

    def _parse_reasoning(self, response: str) -> Thought:
        """Parse the LLM reasoning response."""
        lines = response.strip().split('\n')

        thought = Thought(
            status=ThoughtStatus.CONTINUE,
            reasoning="",
            tool=None,
            params=None,
            response=None
        )

        for line in lines:
            line = line.strip()

            if line.startswith("THOUGHT:"):
                thought.reasoning = line[8:].strip()
            elif line.startswith("ACTION:"):
                thought.tool = line[7:].strip()
            elif line.startswith("PARAMS:"):
                import json
                try:
                    thought.params = json.loads(line[7:].strip())
                except json.JSONDecodeError:
                    thought.params = {}
            elif line.startswith("FINAL:"):
                thought.status = ThoughtStatus.FINAL
                thought.response = line[6:].strip()

        # If no FINAL but no ACTION either, treat as final
        if thought.status == ThoughtStatus.CONTINUE and thought.tool is None:
            thought.status = ThoughtStatus.FINAL
            thought.response = thought.reasoning or "I'm not sure what to do next."

        return thought

    def _get_tools_info(self) -> str:
        """Get formatted information about available tools."""
        tools_info = []
        for tool_meta in self.registry.list_tools():
            tools_info.append(
                f"- {tool_meta.name}: {tool_meta.description}\n"
                f"  Parameters: {tool_meta.parameters}"
            )
        return "\n".join(tools_info)

    async def act(self, thought: Thought) -> str:
        """
        Execute the action specified in the thought.

        Args:
            thought: Thought with action to execute

        Returns:
            Observation string
        """
        if not thought.tool or not thought.params:
            return "No action specified"

        try:
            result = await self.registry.invoke(thought.tool, thought.params)

            if result.success:
                observation = f"Tool '{thought.tool}' succeeded: {result.data}"
            else:
                observation = f"Tool '{thought.tool}' failed: {result.error}"

            logger.info("react.action_executed", tool=thought.tool, success=result.success)
            return observation

        except Exception as e:
            logger.exception("react.action_failed", tool=thought.tool, error=str(e))
            return f"Action failed: {str(e)}"
