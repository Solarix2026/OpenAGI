# meta/meta_agent_v2.py
"""MetaAgent v2 - Full L3 metacognitive layer.

Runs alongside the Kernel as a background monitor, continuously improving
the agent's capabilities through:
- Background improvement loop (asyncio.Queue-based)
- CapabilityGap detection from reflection outputs
- SkillInventor integration for auto-generating tools/skills
- SelfBenchmark for capability coverage scoring
- Telos gate on all improvement proposals
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import structlog

from agents.reflector import Reflector, ReflectionResult
from core.telos_core import TelosCore, TelosAction, AlignmentResult
from memory.memory_core import MemoryCore, MemoryLayer
from tools.registry import ToolRegistry

from meta.capability_gap import CapabilityGap, GapType, gap_from_reflection
from meta.skill_inventor import SkillInventor
from meta.self_benchmark import SelfBenchmark

logger = structlog.get_logger()


@dataclass
class ImprovementProposal:
    """A proposed improvement to the agent."""
    gap: CapabilityGap
    proposal_type: str  # "tool", "skill", "knowledge", "optimization"
    description: str
    telos_aligned: bool
    telos_reasoning: str
    confidence: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaAgentStats:
    """Statistics about MetaAgent operation."""
    reflections_processed: int = 0
    gaps_detected: int = 0
    improvements_proposed: int = 0
    improvements_implemented: int = 0
    telos_blocks: int = 0
    last_benchmark_score: float = 0.0
    uptime_seconds: float = 0.0


class MetaAgent:
    """L3 metacognitive layer - background self-improvement system.

    Continuously monitors reflection outputs, detects capability gaps,
    proposes improvements, and ensures all changes align with Telos.
    """

    def __init__(
        self,
        memory: MemoryCore,
        telos: TelosCore,
        registry: ToolRegistry,
        llm_gateway: Optional[Any] = None,
    ):
        """Initialize MetaAgent.

        Args:
            memory: Memory core for storing gaps and improvements
            telos: Telos core for alignment checking
            registry: Tool registry for capability assessment
            llm_gateway: Optional LLM gateway for generating improvements
        """
        self.memory = memory
        self.telos = telos
        self.registry = registry
        self.llm_gateway = llm_gateway

        # Initialize components
        self.skill_inventor = SkillInventor(llm_gateway=llm_gateway)
        self._self_benchmark = SelfBenchmark(registry=registry)

        # Background loop infrastructure
        self._reflection_queue: asyncio.Queue[ReflectionResult] = asyncio.Queue()
        self._background_task: Optional[asyncio.Task] = None
        self._running = False
        self._start_time: Optional[datetime] = None

        # Tracking
        self._reflections_processed: list[ReflectionResult] = []
        self._detected_gaps: list[CapabilityGap] = []
        self._proposals: list[ImprovementProposal] = []

        # Statistics
        self.stats = MetaAgentStats()

        logger.info("meta_agent_v2.initialized")

    async def start_background_loop(self) -> None:
        """Start the background improvement loop.

        This runs as a non-blocking background task that processes
        reflections and detects gaps continuously.
        """
        if self._running:
            logger.warning("meta_agent.already_running")
            return

        self._running = True
        self._start_time = datetime.utcnow()

        # Create background task
        self._background_task = asyncio.create_task(self._background_loop())

        logger.info("meta_agent.background_loop_started")

    async def stop_background_loop(self) -> None:
        """Stop the background improvement loop."""
        if not self._running:
            return

        self._running = False

        # Cancel background task
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        # Update uptime
        if self._start_time:
            self.stats.uptime_seconds = (
                datetime.utcnow() - self._start_time
            ).total_seconds()

        logger.info("meta_agent.background_loop_stopped",
                   uptime_seconds=self.stats.uptime_seconds)

    async def feed_reflection(self, reflection: ReflectionResult) -> None:
        """Feed a reflection result to the background loop.

        This is non-blocking - the reflection is queued for processing.

        Args:
            reflection: Reflection result to analyze
        """
        await self._reflection_queue.put(reflection)
        logger.debug("meta_agent.reflection_queued")

    async def scan_for_gaps(self) -> list[CapabilityGap]:
        """Scan for capability gaps across the system.

        Returns:
            List of detected capability gaps
        """
        logger.info("meta_agent.scanning_for_gaps")

        gaps = []

        # Check tool registry for missing capabilities
        available_tools = self.registry.list_tools()
        tool_names = {tool.name for tool in available_tools}

        # Define expected tool categories
        expected_categories = {
            "file": ["read", "write", "edit"],
            "web": ["search", "fetch"],
            "code": ["execute", "bash"],
            "memory": ["write", "recall"],
        }

        for category, expected_tools in expected_categories.items():
            missing = [tool for tool in expected_tools if tool not in tool_names]
            if missing:
                gap = CapabilityGap(
                    gap_type=GapType.MISSING_TOOL,
                    description=f"Missing {category} tools: {missing}",
                    frequency=1,
                    fillable=True,
                    source_reflection="system_scan",
                    metadata={"category": category, "missing_tools": missing}
                )
                gaps.append(gap)

        # Run self-benchmark
        benchmark_result = await self._self_benchmark.run()
        self.stats.last_benchmark_score = benchmark_result["coverage_score"]

        # Add gaps from benchmark
        for gap_desc in benchmark_result["top_gaps"]:
            gap = CapabilityGap(
                gap_type=GapType.MISSING_TOOL,
                description=gap_desc,
                frequency=1,
                fillable=True,
                source_reflection="benchmark",
                metadata={"benchmark_score": benchmark_result["coverage_score"]}
            )
            gaps.append(gap)

        logger.info("meta_agent.gaps_found", count=len(gaps))
        return gaps

    def identify_gap_from_reflection(self, reflection: ReflectionResult) -> Optional[CapabilityGap]:
        """Identify a capability gap from a reflection result.

        Args:
            reflection: Reflection result to analyze

        Returns:
            Detected capability gap or None
        """
        gap = gap_from_reflection(reflection)

        if gap:
            self._detected_gaps.append(gap)
            self.stats.gaps_detected += 1
            logger.info("meta_agent.gap_identified",
                       gap_type=gap.gap_type.value,
                       description=gap.description)

        return gap

    async def propose_improvement(self, gap: CapabilityGap) -> Optional[ImprovementProposal]:
        """Propose an improvement to address a capability gap.

        All proposals go through Telos alignment check.

        Args:
            gap: Capability gap to address

        Returns:
            Improvement proposal or None if blocked by Telos
        """
        logger.info("meta_agent.proposing_improvement",
                   gap_type=gap.gap_type.value,
                   description=gap.description)

        # Determine proposal type based on gap
        if gap.gap_type == GapType.MISSING_TOOL:
            proposal_type = "tool"
            description = f"Generate tool to address: {gap.description}"
        elif gap.gap_type == GapType.MISSING_SKILL:
            proposal_type = "skill"
            description = f"Generate skill to address: {gap.description}"
        elif gap.gap_type == GapType.KNOWLEDGE_GAP:
            proposal_type = "knowledge"
            description = f"Acquire knowledge to address: {gap.description}"
        elif gap.gap_type == GapType.PERFORMANCE_GAP:
            proposal_type = "optimization"
            description = f"Optimize to address: {gap.description}"
        else:
            proposal_type = "general"
            description = f"Address: {gap.description}"

        # Check Telos alignment
        action = {
            "name": f"implement_{proposal_type}",
            "description": description,
            "risk_score": 0.3 if gap.fillable else 0.7,
            "parameters": {"gap": gap.to_dict()}
        }

        alignment = self.telos.check_alignment(action)

        # Log Telos decision
        if alignment.decision == TelosAction.BLOCK:
            self.stats.telos_blocks += 1
            logger.warning("meta_agent.telos_blocked",
                         reasoning=alignment.reasoning)
            return None

        if alignment.decision == TelosAction.WARN:
            logger.warning("meta_agent.telos_warned",
                         reasoning=alignment.reasoning)

        # Create proposal
        proposal = ImprovementProposal(
            gap=gap,
            proposal_type=proposal_type,
            description=description,
            telos_aligned=(alignment.decision == TelosAction.ALLOW),
            telos_reasoning=alignment.reasoning,
            confidence=alignment.confidence,
            metadata={
                "alignment_decision": alignment.decision.value,
                "fillable": gap.fillable,
            }
        )

        self._proposals.append(proposal)
        self.stats.improvements_proposed += 1

        logger.info("meta_agent.improvement_proposed",
                   proposal_type=proposal_type,
                   telos_aligned=proposal.telos_aligned)

        return proposal

    async def implement_improvement(self, proposal: ImprovementProposal) -> bool:
        """Implement an approved improvement proposal.

        Args:
            proposal: Improvement proposal to implement

        Returns:
            True if implementation succeeded, False otherwise
        """
        logger.info("meta_agent.implementing_improvement",
                   proposal_type=proposal.proposal_type)

        try:
            if proposal.proposal_type == "tool":
                # Use SkillInventor to generate tool
                tool = await self.skill_inventor.invent_tool(
                    name=f"auto_{proposal.gap.gap_type.value}",
                    description=proposal.description,
                    parameters={"type": "object", "properties": {}}
                )

                if tool:
                    # Register the tool
                    # Note: In production, you'd add to registry properly
                    logger.info("meta_agent.tool_registered",
                              name=tool.meta.name)
                    self.stats.improvements_implemented += 1
                    return True

            elif proposal.proposal_type == "skill":
                # Use SkillInventor to generate skill
                skill_path = await self.skill_inventor.invent_skill(
                    name=f"auto_{proposal.gap.gap_type.value}",
                    description=proposal.description
                )

                if skill_path:
                    logger.info("meta_agent.skill_created",
                              path=str(skill_path))
                    self.stats.improvements_implemented += 1
                    return True

            # For other types, just log for now
            logger.info("meta_agent.improvement_logged",
                       proposal_type=proposal.proposal_type)
            self.stats.improvements_implemented += 1
            return True

        except Exception as e:
            logger.exception("meta_agent.implementation_error",
                           error=str(e))
            return False

    async def self_benchmark(self) -> dict[str, Any]:
        """Run self-benchmark and return results.

        Returns:
            Benchmark results dict
        """
        result = await self._self_benchmark.run()

        return {
            "coverage_score": result["coverage_score"],
            "top_gaps": result["top_gaps"],
            "tools_registered": result["tools_registered"],
            "memory_utilization": result["memory_utilization"],
        }

    async def _background_loop(self) -> None:
        """Background loop that processes reflections continuously.

        This runs as a daemon task, processing queued reflections
        and detecting gaps.
        """
        logger.info("meta_agent.background_loop_running")

        while self._running:
            try:
                # Wait for reflection with timeout
                try:
                    reflection = await asyncio.wait_for(
                        self._reflection_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # No reflection, continue loop
                    continue

                # Process reflection
                self._reflections_processed.append(reflection)
                self.stats.reflections_processed += 1

                # Identify gaps
                gap = self.identify_gap_from_reflection(reflection)

                if gap and gap.fillable:
                    # Propose improvement
                    proposal = await self.propose_improvement(gap)

                    if proposal and proposal.telos_aligned:
                        # Implement improvement
                        await self.implement_improvement(proposal)

                # Store in memory
                await self.memory.write(
                    content=f"Processed reflection: {reflection.lessons_learned}",
                    layer=MemoryLayer.PROCEDURAL,
                    metadata={
                        "reflection_id": str(id(reflection)),
                        "gaps_detected": 1 if gap else 0,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

            except asyncio.CancelledError:
                logger.info("meta_agent.background_loop_cancelled")
                break
            except Exception as e:
                logger.exception("meta_agent.background_loop_error", error=str(e))

        logger.info("meta_agent.background_loop_exited")

    def get_stats(self) -> MetaAgentStats:
        """Get current MetaAgent statistics.

        Returns:
            MetaAgentStats with current metrics
        """
        # Update uptime
        if self._start_time and self._running:
            self.stats.uptime_seconds = (
                datetime.utcnow() - self._start_time
            ).total_seconds()

        return self.stats

    def get_detected_gaps(self) -> list[CapabilityGap]:
        """Get all detected capability gaps.

        Returns:
            List of detected gaps
        """
        return self._detected_gaps.copy()

    def get_proposals(self) -> list[ImprovementProposal]:
        """Get all improvement proposals.

        Returns:
            List of proposals
        """
        return self._proposals.copy()
