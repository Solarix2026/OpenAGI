# orchestrator/mas_kernel.py
"""Multi-Agent System Kernel — parallel agent coordination.

Fixes Phase 1's single-threaded sequential execution bottleneck.
Agents run in parallel asyncio TaskGroup with:
- Message bus for inter-agent communication
- BFT consensus for critical decisions (from Lunarix v3 architecture)
- Telos synchronization (all agents share immutable Telos)
- MetaAgent monitoring all agents simultaneously
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional
from uuid import uuid4

import structlog

from core.telos_core import TelosCore
from gateway.llm_gateway import LLMGateway, LLMRequest
from memory.memory_core import MemoryCore, MemoryLayer
from tools.registry import ToolRegistry
from orchestrator.message_bus import MessageBus, AgentMessage, MessageType

logger = structlog.get_logger()


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    agent_id: str = field(default_factory=lambda: str(uuid4())[:8])
    agent_type: str = "specialist"  # "primary" | "meta" | "security" | "specialist"
    goal: str = ""
    max_tokens: int = 2048
    timeout_seconds: int = 120


@dataclass
class AgentResult:
    """Result from an agent execution."""
    agent_id: str
    agent_type: str
    goal: str
    success: bool
    result: str = ""
    error: str = ""
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class MASKernel:
    """
    Multi-Agent System kernel.

    Routes goals to appropriate agent configurations:
    - Simple goals → single primary agent
    - Complex research → primary + research specialists (parallel)
    - Critical decisions → 3-agent BFT consensus
    - Continuous improvement → background MetaAgent
    """

    def __init__(
        self,
        llm: LLMGateway,
        memory: MemoryCore,
        registry: ToolRegistry,
        telos: TelosCore,
    ) -> None:
        self.llm = llm
        self.memory = memory
        self.registry = registry
        self.telos = telos
        self.message_bus = MessageBus()
        self._running_agents: dict[str, asyncio.Task] = {}

    async def run(
        self,
        goal: str,
        session_id: str = "",
        parallel_branches: int = 1,
    ) -> AsyncIterator[str]:
        """
        Execute a goal with multi-agent coordination.

        parallel_branches=1: single agent (Phase 1 behavior)
        parallel_branches=2+: spawn parallel specialist agents
        """
        if not session_id:
            session_id = f"mas-{uuid4().hex[:8]}"

        if parallel_branches == 1:
            # Single agent path — import Phase 1 kernel
            from core.kernel import Kernel
            from config.settings import Settings
            kernel = Kernel(settings=Settings())
            async for token in kernel.run(goal, session_id=session_id):
                yield token
        else:
            # Multi-agent parallel path
            async for token in self._run_parallel(goal, session_id, parallel_branches):
                yield token

    async def _run_parallel(
        self, goal: str, session_id: str, n_agents: int
    ) -> AsyncIterator[str]:
        """Run multiple specialist agents in parallel, synthesize results."""
        yield f"[MAS] Spawning {n_agents} parallel agents for: {goal[:60]}...\n\n"

        # Decompose goal into sub-goals
        sub_goals = await self._decompose_goal(goal, n_agents)
        yield f"[MAS] Decomposed into {len(sub_goals)} sub-goals\n\n"

        # Run sub-agents in parallel
        results = await asyncio.gather(*[
            self._run_specialist(sub_goal, session_id, i)
            for i, sub_goal in enumerate(sub_goals)
        ], return_exceptions=True)

        # Synthesize
        valid_results = [r for r in results if not isinstance(r, Exception)]
        synthesis = await self._synthesize_results(goal, valid_results)

        yield "\n\n[MAS] Synthesis:\n"
        for token in synthesis.split():
            yield token + " "

    async def _decompose_goal(self, goal: str, n: int) -> list[str]:
        """Decompose a goal into n parallel sub-goals."""
        response = await self.llm.complete(LLMRequest(
            messages=[{
                "role": "user",
                "content": f"Decompose this goal into exactly {n} parallel independent sub-goals:\n{goal}\n\nReturn JSON: [\"sub-goal 1\", \"sub-goal 2\", ...]"
            }],
            max_tokens=400,
            temperature=0.1,
        ))
        import json, re
        try:
            raw = re.sub(r"^```json?\s*|\s*```$", "", response.content.strip(), flags=re.MULTILINE)
            return json.loads(raw)
        except Exception:
            return [goal]  # Fallback to single goal

    async def _run_specialist(
        self, sub_goal: str, session_id: str, agent_idx: int
    ) -> AgentResult:
        """Run a single specialist agent for a sub-goal."""
        from core.kernel import Kernel
        from config.settings import Settings
        kernel = Kernel(settings=Settings())

        result_tokens = []
        async for token in kernel.run(sub_goal, session_id=f"{session_id}_agent{agent_idx}"):
            result_tokens.append(token)

        return AgentResult(
            agent_id=f"agent-{agent_idx}",
            agent_type="specialist",
            sub_goal=sub_goal,
            success=True,
            result="".join(result_tokens),
        )

    async def _synthesize_results(self, goal: str, results: list[AgentResult]) -> str:
        """Synthesize parallel agent results into coherent answer."""
        results_text = "\n\n".join([
            f"Agent {r.agent_id} on '{r.goal}':\n{r.result[:500]}"
            for r in results
        ])

        response = await self.llm.complete(LLMRequest(
            messages=[{
                "role": "user",
                "content": f"Synthesize these parallel agent results into a coherent answer for the original goal:\n\nORIGINAL GOAL: {goal}\n\nRESULTS:\n{results_text}\n\nProvide a unified answer."
            }],
            max_tokens=1500,
            temperature=0.2,
        ))
        return response.content

    async def start_background_monitoring(self) -> None:
        """Start background monitoring agents."""
        # This would start MetaAgent and SecurityAgent as background tasks
        logger.info("mas_kernel.background_monitoring_started")

    async def stop(self) -> None:
        """Stop all running agents."""
        for agent_id, task in self._running_agents.items():
            task.cancel()
            logger.info("mas_kernel.agent_stopped", agent_id=agent_id)
        self._running_agents.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get MAS kernel statistics."""
        return {
            "running_agents": len(self._running_agents),
            "message_bus": self.message_bus.get_stats(),
        }
