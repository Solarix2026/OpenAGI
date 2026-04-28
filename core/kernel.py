# core/kernel.py
"""The Kernel (K) — Main orchestration loop with async streaming.

Coordinates all components:
- Telos: Value alignment
- Planner: Task decomposition
- Executor: Parallel execution
- Reflector: Post-execution learning
- Gateway: LLM routing
- Memory: Stratified storage
- Registry: Tool discovery
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Optional

import structlog

from config.settings import get_settings
from core.telos_core import TelosCore, AlignmentResult, TelosAction
from agents.planner import Planner, TaskGraph, TaskStatus
from agents.executor import Executor
from agents.reflector import Reflector
from agents.tool_caller import ToolCallerAgent
from tools.registry import ToolRegistry
from memory.memory_core import MemoryCore, MemoryLayer
from gateway.llm_gateway import LLMGateway, LLMMessage, LLMResponse

logger = structlog.get_logger()


@dataclass
class KernelState:
    """Current state of the kernel."""
    initialized: bool = False
    initialized_at: Optional[datetime] = None
    current_goal: Optional[str] = None
    current_plan: Optional[TaskGraph] = None
    execution_in_progress: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class Kernel:
    """
    The Kernel — Central orchestration hub.

    Run() is AsyncIterator[str] for streaming.
    All tool calls go through registry.invoke() — no hardcoded calls.
    """

    def __init__(
        self,
        telos: TelosCore,
        memory: Optional[MemoryCore] = None,
        registry: Optional[ToolRegistry] = None,
        planner: Optional[Planner] = None,
        executor: Optional[Executor] = None,
        reflector: Optional[Reflector] = None,
        gateway: Optional[LLMGateway] = None,
        skill_loader: Optional["SkillLoader"] = None,
    ):
        """Initialize kernel with all components."""
        self.config = get_settings()
        self.telos = telos
        self.memory = memory or MemoryCore(telos=telos)
        self.registry = registry or ToolRegistry()
        self.planner = planner or Planner(telos=telos)
        self.executor = executor or Executor(self.planner, self.registry, telos)
        self.reflector = reflector or Reflector(self.memory, telos)
        self.gateway = gateway or LLMGateway()
        self.tool_caller = ToolCallerAgent(self.registry, self.gateway)

        # Auto-load builtin tools
        from pathlib import Path
        builtin_path = Path(__file__).parent.parent / "tools" / "builtin"
        registered = self.registry.scan_builtin_directory(builtin_path)
        logger.info("kernel.builtin_tools_loaded", count=registered)

        # Inject dependencies into tools that need them
        self._inject_tool_dependencies()

        # Initialize skill loader
        if skill_loader is None:
            from skills.skill_loader import SkillLoader
            self.skill_loader = SkillLoader(
                llm=self.gateway,
                registry=self.registry,
                telos=telos,
            )
            # Load builtin skills
            loaded = self.skill_loader.scan()
            logger.info("kernel.skills_loaded", count=loaded)
        else:
            self.skill_loader = skill_loader

        self.state = KernelState(
            initialized=True,
            initialized_at=datetime.utcnow()
        )

        logger.info("kernel.initialized",
            agent_name=self.config.agent_name,
            tools_loaded=registered)

    def _inject_tool_dependencies(self) -> None:
        """Inject kernel dependencies into tools that need them."""
        # Inject memory core into MemoryTool
        memory_tool = self.registry.get("memory")
        if memory_tool and hasattr(memory_tool, "memory_core"):
            memory_tool.memory_core = self.memory

        # Inject REPL and LLM into CodeTool
        code_tool = self.registry.get("code")
        if code_tool:
            from sandbox.repl import PythonREPL
            if hasattr(code_tool, "repl") and code_tool.repl is None:
                code_tool.repl = PythonREPL()
            if hasattr(code_tool, "llm") and code_tool.llm is None:
                code_tool.llm = self.gateway

        logger.info("kernel.tool_dependencies_injected")

    async def run(self, goal: str) -> AsyncIterator[str]:
        """
        Execute a goal and yield streaming output.

        AsyncIterator[str] for streaming.
        """
        yield f"Processing goal: {goal}\n"

        # Check Telos alignment
        alignment = self.telos.check_alignment(
            {"name": "process_goal", "risk_score": 0.5, "parameters": {"goal": goal}}
        )

        if alignment.decision == TelosAction.BLOCK:
            yield f"Goal blocked by Telos: {alignment.reasoning}\n"
            return

        if alignment.decision == TelosAction.WARN:
            yield f"Warning: {alignment.reasoning}\n"

        self.state.current_goal = goal

        # Recall similar memories
        memories = await self.memory.recall(
            query=goal,
            layers=[MemoryLayer.EPISODIC, MemoryLayer.SEMANTIC],
            top_k=3
        )

        if memories:
            yield f"Recalled {len(memories)} relevant memories\n"

        # Create plan
        yield "Creating plan...\n"
        plan = self.planner.create_plan([goal])
        self.state.current_plan = plan

        if self.planner.has_cycles():
            yield "Error: Plan contains cycles\n"
            return

        yield f"Plan created with {len(plan.nodes)} tasks\n"

        # Execute plan
        self.state.execution_in_progress = True
        yield "Executing plan...\n"

        async for result in self.executor.execute_plan():
            status = "✓" if result.success else "✗"
            yield f"  {status} {result.task_id}: {result.output or result.error}\n"

        self.state.execution_in_progress = False

        # Reflect
        yield "Reflecting on execution...\n"
        reflection = await self.reflector.reflect(self.planner)

        yield f"Reflection: {reflection.memory_updates} lessons learned\n"

        # Summary
        summary = self.executor.get_summary()
        yield f"\nCompleted in {summary.get('total_time_ms', 0):.0f}ms\n"
        yield f"Success rate: {summary.get('success_rate', 0)*100:.0f}%\n"

    async def chat(self, message: str) -> AsyncIterator[str]:
        """
        Respond to user message with streaming output.

        Uses ToolCallerAgent for intelligent tool calling and memory integration.
        """
        logger.info("kernel.chat_start", message_length=len(message))

        try:
            # Query memories
            memories = await self.memory.recall(
                query=message,
                layers=[MemoryLayer.EPISODIC, MemoryLayer.WORKING],
                top_k=3
            )

            context = ""
            if memories:
                context = "\n".join([m.content for m in memories[:3]])
                logger.info("kernel.chat_memories_found", count=len(memories))

            # Analyze if tools are needed
            tool_calls = await self.tool_caller.analyze_and_call(message)

            # Execute tool calls if any
            tool_results = []
            if tool_calls:
                yield f"[Analyzing request and determining tools needed...]\n"
                tool_results = await self.tool_caller.execute_calls(tool_calls)

                # Report tool results
                for result in tool_results:
                    if result.success:
                        yield f"[Used {result.tool_name}: {str(result.data)[:100]}...]\n"
                    else:
                        yield f"[{result.tool_name} failed: {result.error}]\n"

            # Generate response
            yield "[Generating response...]\n"

            # Build context for response generation
            response_context = f"User message: {message}\n"
            if context:
                response_context += f"\nRelevant memories:\n{context}\n"

            if tool_results:
                response_context += "\nTool results:\n"
                for result in tool_results:
                    if result.success:
                        response_context += f"- {result.tool_name}: {result.data}\n"
                    else:
                        response_context += f"- {result.tool_name} (failed): {result.error}\n"

            # Generate response
            response = await self.tool_caller.generate_response(message, tool_results)
            yield response

            # Store conversation in episodic memory
            memory_content = f"User: {message}\n"
            if tool_calls:
                memory_content += f"Tools used: {[tc.tool_name for tc in tool_calls]}\n"
            memory_content += f"Assistant: {response[:200]}..."

            await self.memory.write(
                content=memory_content,
                layer=MemoryLayer.EPISODIC,
                metadata={
                    "session_id": "chat",
                    "tool_calls": len(tool_calls),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            logger.info(
                "kernel.chat_complete",
                tool_calls=len(tool_calls),
                memory_written=True
            )

        except Exception as e:
            logger.exception("kernel.chat_error", error=str(e))
            yield f"\n[Error: {str(e)}]"

    def get_status(self) -> dict[str, Any]:
        """Get kernel status."""
        return {
            "initialized": self.state.initialized,
            "initialized_at": self.state.initialized_at.isoformat() if self.state.initialized_at else None,
            "execution_in_progress": self.state.execution_in_progress,
            "current_goal": self.state.current_goal,
            "memory_stats": self.memory.get_stats() if self.memory else {},
            "plan_summary": self.planner.get_summary() if self.state.current_plan else None,
        }

    async def close(self) -> None:
        """Clean up resources."""
        await self.gateway.close()
        logger.info("kernel.closed")
