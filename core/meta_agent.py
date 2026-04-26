"""Meta-Agent (L3) - Self-improvement loop and higher-level reasoning.

This is the meta-cognitive layer that enables:
- Self-improvement: Analyze performance and improve strategies
- HDC active memory: Hyperdimensional computing for active memory
- MCP client hub: Integration with Model Context Protocol servers
- Strategic reasoning: High-level planning and decision making
- Hypothesis evaluation: Test and refine hypotheses
- Meta-learning: Learn from past executions
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional, Callable, Dict, List
from uuid import uuid4

import numpy as np
import structlog
import httpx

from config.settings import get_settings
from core.telos_core import TelosCore
from core.world_model import WorldModel, ReasoningMode
from memory.memory_core import MemoryCore, MemoryLayer
from memory.hdc_store import HDCStore

logger = structlog.get_logger()


class ImprovementStrategy(Enum):
    """Strategies for self-improvement."""
    REFINE_PLANNING = auto()  # Improve planning algorithms
    OPTIMIZE_EXECUTION = auto()  # Optimize execution patterns
    ENHANCE_MEMORY = auto()  # Improve memory consolidation
    EXPAND_TOOLS = auto()  # Discover and integrate new tools
    TUNE_PARAMETERS = auto()  # Adjust system parameters


@dataclass(frozen=True)
class Hypothesis:
    """A hypothesis to test."""
    hypothesis_id: str = field(default_factory=lambda: str(uuid4()))
    statement: str = ""
    confidence: float = 0.5
    evidence: list[dict[str, Any]] = field(default_factory=list)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    status: str = "pending"  # pending, testing, confirmed, refuted
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class ImprovementAction:
    """An action to improve the system."""
    action_id: str = field(default_factory=lambda: str(uuid4()))
    strategy: ImprovementStrategy = ImprovementStrategy.REFINE_PLANNING
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    expected_benefit: float = 0.0
    priority: int = 0
    status: str = "pending"  # pending, in_progress, completed, failed


@dataclass(frozen=True)
class MCPClient:
    """Model Context Protocol client."""
    client_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    endpoint: str = ""
    capabilities: list[str] = field(default_factory=list)
    connected: bool = False
    last_used: Optional[datetime] = None


class MetaAgent:
    """
    Meta-Agent (L3) - Self-improvement and higher-level reasoning.

    This layer provides:
    - Self-improvement loop: Analyze performance and improve strategies
    - HDC active memory: Hyperdimensional computing for working memory
    - MCP client hub: Integration with external MCP servers
    - Strategic reasoning: High-level planning and decision making
    - Hypothesis evaluation: Test and refine hypotheses
    """

    def __init__(
        self,
        telos: Optional[TelosCore] = None,
        memory: Optional[MemoryCore] = None,
        world_model: Optional[WorldModel] = None,
        hdc_dim: int = 10000,
    ):
        self.telos = telos
        self.memory = memory
        self.world_model = world_model
        self.config = get_settings()
        self.hdc_dim = hdc_dim

        # HDC active memory for working memory
        self._active_memory = HDCStore(dim=hdc_dim)

        # Hypothesis tracking
        self._hypotheses: dict[str, Hypothesis] = {}

        # Improvement actions
        self._improvement_actions: dict[str, ImprovementAction] = {}

        # Performance metrics
        self._performance_history: list[dict[str, Any]] = []

        # MCP clients
        self._mcp_clients: dict[str, MCPClient] = {}

        # Self-improvement state
        self._improvement_cycle_count = 0
        self._last_improvement_time: Optional[datetime] = None

        logger.info("metaagent.initialized", hdc_dim=hdc_dim)

    async def reason_about_strategy(
        self,
        context: dict[str, Any],
        goal: str,
    ) -> dict[str, Any]:
        """
        Reason about high-level strategy.

        Args:
            context: Current context and state
            goal: The goal to achieve

        Returns:
            Strategy recommendations
        """
        logger.info("metaagent.strategy.reasoning", goal=goal)

        # Use world model for reasoning if available
        if self.world_model:
            reasoning_result = await self.world_model.reason(
                query=goal,
                mode=ReasoningMode.ABDUCTIVE,
                context=context,
            )

            strategy = {
                "goal": goal,
                "reasoning": reasoning_result.conclusion,
                "confidence": reasoning_result.confidence,
                "steps": reasoning_result.reasoning_steps,
                "assumptions": reasoning_result.assumptions,
            }
        else:
            # Fallback: simple strategy generation
            strategy = {
                "goal": goal,
                "reasoning": "Direct execution without world model",
                "confidence": 0.5,
                "steps": ["Analyze goal", "Plan execution", "Execute", "Reflect"],
                "assumptions": [],
            }

        # Store in active memory
        strategy_text = json.dumps(strategy, sort_keys=True)
        self._active_memory.add(
            memory_id=f"strategy_{uuid4().hex[:8]}",
            content=strategy_text,
            metadata={"type": "strategy", "goal": goal},
        )

        return strategy

    async def evaluate_hypotheses(
        self,
        hypotheses: list[Hypothesis],
        context: dict[str, Any],
    ) -> list[Hypothesis]:
        """
        Evaluate competing hypotheses.

        Args:
            hypotheses: List of hypotheses to evaluate
            context: Current context for evaluation

        Returns:
            Updated hypotheses with test results
        """
        logger.info("metaagent.hypotheses.evaluating", count=len(hypotheses))

        for hypothesis in hypotheses:
            # Store hypothesis
            self._hypotheses[hypothesis.hypothesis_id] = hypothesis

            # Test hypothesis
            test_result = await self._test_hypothesis(hypothesis, context)

            # Update hypothesis
            updated_hypothesis = Hypothesis(
                hypothesis_id=hypothesis.hypothesis_id,
                statement=hypothesis.statement,
                confidence=test_result["confidence"],
                evidence=hypothesis.evidence + [test_result],
                test_results=hypothesis.test_results + [test_result],
                status=test_result["status"],
                created_at=hypothesis.created_at,
            )

            self._hypotheses[hypothesis.hypothesis_id] = updated_hypothesis

        return list(self._hypotheses.values())

    async def _test_hypothesis(
        self,
        hypothesis: Hypothesis,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Test a single hypothesis."""
        # Simple hypothesis testing based on statement analysis
        statement_lower = hypothesis.statement.lower()

        # Check for evidence in context
        evidence_score = 0.0
        evidence_found = []

        for key, value in context.items():
            if key.lower() in statement_lower:
                evidence_score += 0.2
                evidence_found.append(f"{key}: {value}")

        # Check memory for supporting evidence
        if self.memory:
            memories = await self.memory.recall(
                query=hypothesis.statement,
                layers=[MemoryLayer.EPISODIC, MemoryLayer.SEMANTIC],
                top_k=3,
            )
            if memories:
                evidence_score += 0.3
                evidence_found.extend([m.content for m in memories])

        # Determine status
        if evidence_score >= 0.7:
            status = "confirmed"
            confidence = min(1.0, hypothesis.confidence + 0.2)
        elif evidence_score >= 0.4:
            status = "testing"
            confidence = hypothesis.confidence
        else:
            status = "refuted"
            confidence = max(0.0, hypothesis.confidence - 0.3)

        return {
            "confidence": confidence,
            "status": status,
            "evidence_score": evidence_score,
            "evidence_found": evidence_found,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def run_self_improvement_cycle(
        self,
        performance_metrics: dict[str, Any],
    ) -> list[ImprovementAction]:
        """
        Run a self-improvement cycle.

        Args:
            performance_metrics: Current performance metrics

        Returns:
            List of improvement actions to take
        """
        logger.info("metaagent.improvement.cycle.start", cycle=self._improvement_cycle_count)

        # Store performance metrics
        self._performance_history.append({
            **performance_metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "cycle": self._improvement_cycle_count,
        })

        # Analyze performance
        analysis = await self._analyze_performance(performance_metrics)

        # Generate improvement actions
        actions = await self._generate_improvement_actions(analysis)

        # Prioritize actions
        prioritized_actions = self._prioritize_actions(actions)

        # Store actions
        for action in prioritized_actions:
            self._improvement_actions[action.action_id] = action

        self._improvement_cycle_count += 1
        self._last_improvement_time = datetime.utcnow()

        logger.info(
            "metaagent.improvement.cycle.complete",
            cycle=self._improvement_cycle_count,
            actions_generated=len(prioritized_actions),
        )

        return prioritized_actions

    async def _analyze_performance(
        self,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze performance metrics."""
        analysis = {
            "overall_score": 0.0,
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        }

        # Analyze different aspects
        if "success_rate" in metrics:
            success_rate = metrics["success_rate"]
            if success_rate >= 0.9:
                analysis["strengths"].append("High success rate")
            elif success_rate < 0.7:
                analysis["weaknesses"].append("Low success rate")
                analysis["recommendations"].append("Improve error handling")

        if "execution_time" in metrics:
            exec_time = metrics["execution_time"]
            if exec_time < 1.0:
                analysis["strengths"].append("Fast execution")
            elif exec_time > 5.0:
                analysis["weaknesses"].append("Slow execution")
                analysis["recommendations"].append("Optimize execution paths")

        if "memory_efficiency" in metrics:
            mem_eff = metrics["memory_efficiency"]
            if mem_eff >= 0.8:
                analysis["strengths"].append("Efficient memory usage")
            elif mem_eff < 0.5:
                analysis["weaknesses"].append("Poor memory efficiency")
                analysis["recommendations"].append("Improve memory consolidation")

        # Calculate overall score
        strength_count = len(analysis["strengths"])
        weakness_count = len(analysis["weaknesses"])
        analysis["overall_score"] = (strength_count - weakness_count * 0.5) / max(1, strength_count + weakness_count)

        return analysis

    async def _generate_improvement_actions(
        self,
        analysis: dict[str, Any],
    ) -> list[ImprovementAction]:
        """Generate improvement actions based on analysis."""
        actions = []

        # Generate actions for each weakness
        for weakness in analysis["weaknesses"]:
            if "success rate" in weakness.lower():
                actions.append(ImprovementAction(
                    strategy=ImprovementStrategy.REFINE_PLANNING,
                    description="Improve planning to increase success rate",
                    expected_benefit=0.3,
                    priority=1,
                ))
            elif "execution" in weakness.lower():
                actions.append(ImprovementAction(
                    strategy=ImprovementStrategy.OPTIMIZE_EXECUTION,
                    description="Optimize execution for better performance",
                    expected_benefit=0.4,
                    priority=2,
                ))
            elif "memory" in weakness.lower():
                actions.append(ImprovementAction(
                    strategy=ImprovementStrategy.ENHANCE_MEMORY,
                    description="Enhance memory consolidation",
                    expected_benefit=0.2,
                    priority=3,
                ))

        # Generate actions for recommendations
        for recommendation in analysis["recommendations"]:
            if "error handling" in recommendation.lower():
                actions.append(ImprovementAction(
                    strategy=ImprovementStrategy.REFINE_PLANNING,
                    description="Improve error handling and recovery",
                    expected_benefit=0.25,
                    priority=2,
                ))
            elif "optimize" in recommendation.lower():
                actions.append(ImprovementAction(
                    strategy=ImprovementStrategy.OPTIMIZE_EXECUTION,
                    description=recommendation,
                    expected_benefit=0.35,
                    priority=1,
                ))

        return actions

    def _prioritize_actions(
        self,
        actions: list[ImprovementAction],
    ) -> list[ImprovementAction]:
        """Prioritize improvement actions."""
        # Sort by priority (lower number = higher priority)
        sorted_actions = sorted(actions, key=lambda a: a.priority)

        # Add status to actions
        prioritized = []
        for i, action in enumerate(sorted_actions):
            prioritized.append(ImprovementAction(
                action_id=action.action_id,
                strategy=action.strategy,
                description=action.description,
                parameters=action.parameters,
                expected_benefit=action.expected_benefit,
                priority=action.priority,
                status="pending" if i > 0 else "in_progress",
            ))

        return prioritized

    async def execute_improvement_action(
        self,
        action: ImprovementAction,
    ) -> dict[str, Any]:
        """
        Execute an improvement action.

        Args:
            action: The improvement action to execute

        Returns:
            Execution result
        """
        logger.info("metaagent.improvement.action.execute", action_id=action.action_id)

        result = {
            "action_id": action.action_id,
            "success": False,
            "message": "",
            "metrics": {},
        }

        try:
            if action.strategy == ImprovementStrategy.REFINE_PLANNING:
                strategy_result = await self._refine_planning(action)
                result.update(strategy_result)
            elif action.strategy == ImprovementStrategy.OPTIMIZE_EXECUTION:
                strategy_result = await self._optimize_execution(action)
                result.update(strategy_result)
            elif action.strategy == ImprovementStrategy.ENHANCE_MEMORY:
                strategy_result = await self._enhance_memory(action)
                result.update(strategy_result)
            elif action.strategy == ImprovementStrategy.EXPAND_TOOLS:
                strategy_result = await self._expand_tools(action)
                result.update(strategy_result)
            elif action.strategy == ImprovementStrategy.TUNE_PARAMETERS:
                strategy_result = await self._tune_parameters(action)
                result.update(strategy_result)
            else:
                result["message"] = f"Unknown strategy: {action.strategy}"

        except Exception as e:
            logger.exception("metaagent.improvement.action.failed", action_id=action.action_id)
            result["success"] = False
            result["message"] = str(e)

        # Update action status
        if result["success"]:
            updated_action = ImprovementAction(
                action_id=action.action_id,
                strategy=action.strategy,
                description=action.description,
                parameters=action.parameters,
                expected_benefit=action.expected_benefit,
                priority=action.priority,
                status="completed",
            )
        else:
            updated_action = ImprovementAction(
                action_id=action.action_id,
                strategy=action.strategy,
                description=action.description,
                parameters=action.parameters,
                expected_benefit=action.expected_benefit,
                priority=action.priority,
                status="failed",
            )

        self._improvement_actions[action.action_id] = updated_action

        return result

    async def _refine_planning(self, action: ImprovementAction) -> dict[str, Any]:
        """Refine planning algorithms."""
        # Store improvement in active memory
        self._active_memory.add(
            memory_id=f"planning_improvement_{uuid4().hex[:8]}",
            content=action.description,
            metadata={"type": "improvement", "strategy": "planning"},
        )

        return {
            "success": True,
            "message": "Planning refinement recorded",
            "metrics": {"improvement_type": "planning"},
        }

    async def _optimize_execution(self, action: ImprovementAction) -> dict[str, Any]:
        """Optimize execution patterns."""
        # Store improvement in active memory
        self._active_memory.add(
            memory_id=f"execution_optimization_{uuid4().hex[:8]}",
            content=action.description,
            metadata={"type": "improvement", "strategy": "execution"},
        )

        return {
            "success": True,
            "message": "Execution optimization recorded",
            "metrics": {"improvement_type": "execution"},
        }

    async def _enhance_memory(self, action: ImprovementAction) -> dict[str, Any]:
        """Enhance memory consolidation."""
        # Store improvement in active memory
        self._active_memory.add(
            memory_id=f"memory_enhancement_{uuid4().hex[:8]}",
            content=action.description,
            metadata={"type": "improvement", "strategy": "memory"},
        )

        return {
            "success": True,
            "message": "Memory enhancement recorded",
            "metrics": {"improvement_type": "memory"},
        }

    async def _expand_tools(self, action: ImprovementAction) -> dict[str, Any]:
        """Discover and integrate new tools."""
        # Store improvement in active memory
        self._active_memory.add(
            memory_id=f"tool_expansion_{uuid4().hex[:8]}",
            content=action.description,
            metadata={"type": "improvement", "strategy": "tools"},
        )

        return {
            "success": True,
            "message": "Tool expansion recorded",
            "metrics": {"improvement_type": "tools"},
        }

    async def _tune_parameters(self, action: ImprovementAction) -> dict[str, Any]:
        """Adjust system parameters."""
        # Store improvement in active memory
        self._active_memory.add(
            memory_id=f"parameter_tuning_{uuid4().hex[:8]}",
            content=action.description,
            metadata={"type": "improvement", "strategy": "parameters"},
        )

        return {
            "success": True,
            "message": "Parameter tuning recorded",
            "metrics": {"improvement_type": "parameters"},
        }

    # MCP Client Hub Methods

    async def register_mcp_client(
        self,
        name: str,
        endpoint: str,
        capabilities: list[str],
    ) -> str:
        """
        Register an MCP client.

        Args:
            name: Client name
            endpoint: Client endpoint URL
            capabilities: List of capabilities

        Returns:
            client_id
        """
        client_id = str(uuid4())

        client = MCPClient(
            client_id=client_id,
            name=name,
            endpoint=endpoint,
            capabilities=capabilities,
            connected=False,
        )

        self._mcp_clients[client_id] = client

        logger.info("metaagent.mcp.client.registered", name=name, client_id=client_id)

        return client_id

    async def connect_mcp_client(self, client_id: str) -> bool:
        """
        Connect to an MCP client.

        Args:
            client_id: The client ID to connect

        Returns:
            True if successful
        """
        if client_id not in self._mcp_clients:
            logger.warning("metaagent.mcp.client.not_found", client_id=client_id)
            return False

        client = self._mcp_clients[client_id]

        try:
            # Test connection
            async with httpx.AsyncClient(timeout=10) as http_client:
                response = await http_client.get(f"{client.endpoint}/health")
                response.raise_for_status()

            # Update client status
            updated_client = MCPClient(
                client_id=client.client_id,
                name=client.name,
                endpoint=client.endpoint,
                capabilities=client.capabilities,
                connected=True,
                last_used=datetime.utcnow(),
            )

            self._mcp_clients[client_id] = updated_client

            logger.info("metaagent.mcp.client.connected", name=client.name)
            return True

        except Exception as e:
            logger.exception("metaagent.mcp.client.connect_failed", name=client.name)
            return False

    async def call_mcp_tool(
        self,
        client_id: str,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a tool on an MCP client.

        Args:
            client_id: The client ID
            tool_name: The tool name
            parameters: Tool parameters

        Returns:
            Tool result
        """
        if client_id not in self._mcp_clients:
            return {
                "success": False,
                "error": f"Client {client_id} not found",
            }

        client = self._mcp_clients[client_id]

        if not client.connected:
            return {
                "success": False,
                "error": f"Client {client.name} not connected",
            }

        try:
            async with httpx.AsyncClient(timeout=30) as http_client:
                response = await http_client.post(
                    f"{client.endpoint}/tools/{tool_name}",
                    json=parameters,
                )
                response.raise_for_status()

                result = response.json()

                # Update last used time
                updated_client = MCPClient(
                    client_id=client.client_id,
                    name=client.name,
                    endpoint=client.endpoint,
                    capabilities=client.capabilities,
                    connected=True,
                    last_used=datetime.utcnow(),
                )
                self._mcp_clients[client_id] = updated_client

                logger.info(
                    "metaagent.mcp.tool.called",
                    client=client.name,
                    tool=tool_name,
                )

                return result

        except Exception as e:
            logger.exception("metaagent.mcp.tool.failed", client=client.name, tool=tool_name)
            return {
                "success": False,
                "error": str(e),
            }

    def list_mcp_clients(self) -> list[MCPClient]:
        """List all registered MCP clients."""
        return list(self._mcp_clients.values())

    def get_mcp_client(self, client_id: str) -> Optional[MCPClient]:
        """Get an MCP client by ID."""
        return self._mcp_clients.get(client_id)

    # Active Memory Methods

    async def store_in_active_memory(
        self,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> str:
        """
        Store content in HDC active memory.

        Args:
            content: Content to store
            metadata: Optional metadata

        Returns:
            memory_id
        """
        memory_id = str(uuid4())

        self._active_memory.add(
            memory_id=memory_id,
            content=content,
            metadata=metadata or {},
        )

        logger.debug("metaagent.active_memory.stored", memory_id=memory_id)

        return memory_id

    async def recall_from_active_memory(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Recall from active memory.

        Args:
            query: Query text
            top_k: Number of results to return

        Returns:
            List of memory items
        """
        results = self._active_memory.query(query, top_k=top_k)

        return [
            {
                "memory_id": memory_id,
                "content": metadata.get("content", ""),
                "score": score,
                "metadata": metadata,
            }
            for memory_id, score, metadata in results
        ]

    def clear_active_memory(self) -> None:
        """Clear active memory."""
        self._active_memory.clear()
        logger.info("metaagent.active_memory.cleared")

    # Statistics and Status

    def get_stats(self) -> dict[str, Any]:
        """Get meta-agent statistics."""
        return {
            "improvement_cycles": self._improvement_cycle_count,
            "last_improvement_time": self._last_improvement_time.isoformat() if self._last_improvement_time else None,
            "hypotheses_count": len(self._hypotheses),
            "improvement_actions_count": len(self._improvement_actions),
            "performance_history_size": len(self._performance_history),
            "active_memory_size": len(self._active_memory.memories),
            "mcp_clients_count": len(self._mcp_clients),
            "mcp_clients_connected": sum(1 for c in self._mcp_clients.values() if c.connected),
        }

    def get_hypotheses(self) -> list[Hypothesis]:
        """Get all hypotheses."""
        return list(self._hypotheses.values())

    def get_improvement_actions(self) -> list[ImprovementAction]:
        """Get all improvement actions."""
        return list(self._improvement_actions.values())

    def get_performance_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get performance history."""
        return self._performance_history[-limit:]
