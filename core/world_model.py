"""WorldModel (L4) - Latent space reasoning and simulation.

This is the highest cognitive layer in OpenAGI v5. It provides:
- Latent space reasoning: Reason about abstract concepts and relationships
- Advanced simulation: Simulate outcomes and explore possibilities
- World state tracking: Maintain a model of the world state
- Counterfactual reasoning: Explore "what if" scenarios
- Temporal reasoning: Reason about time, causality, and sequences
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional, Callable
from uuid import uuid4

import numpy as np
import structlog

from config.settings import get_settings
from core.telos_core import TelosCore
from memory.memory_core import MemoryCore, MemoryLayer

logger = structlog.get_logger()


class ReasoningMode(Enum):
    """Different modes of reasoning."""
    DEDUCTIVE = auto()  # Logical deduction from premises
    INDUCTIVE = auto()  # Generalization from observations
    ABDUCTIVE = auto()  # Inference to best explanation
    ANALOGICAL = auto()  # Reasoning by analogy
    COUNTERFACTUAL = auto()  # "What if" reasoning


@dataclass(frozen=True)
class Concept:
    """A concept in the latent space."""
    concept_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    embedding: np.ndarray = field(default_factory=lambda: np.array([]))
    properties: dict[str, Any] = field(default_factory=dict)
    relationships: dict[str, float] = field(default_factory=dict)  # concept_id -> strength
    confidence: float = 1.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class SimulationState:
    """State of a simulation."""
    simulation_id: str = field(default_factory=lambda: str(uuid4()))
    state_vector: np.ndarray = field(default_factory=lambda: np.array([]))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass(frozen=True)
class ReasoningResult:
    """Result of a reasoning operation."""
    conclusion: str
    confidence: float
    reasoning_steps: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    mode: ReasoningMode = ReasoningMode.DEDUCTIVE
    metadata: dict[str, Any] = field(default_factory=dict)


class WorldModel:
    """
    WorldModel (L4) - Latent space reasoning and simulation.

    This is the highest cognitive layer that enables:
    - Abstract reasoning about concepts and relationships
    - Simulation of possible outcomes
    - Counterfactual exploration
    - Temporal and causal reasoning
    """

    def __init__(
        self,
        telos: Optional[TelosCore] = None,
        memory: Optional[MemoryCore] = None,
        latent_dim: int = 512,
    ):
        self.telos = telos
        self.memory = memory
        self.config = get_settings()
        self.latent_dim = latent_dim

        # Concept graph
        self._concepts: dict[str, Concept] = {}
        self._concept_embeddings: dict[str, np.ndarray] = {}

        # Simulation state
        self._simulations: dict[str, SimulationState] = {}
        self._simulation_history: list[SimulationState] = []

        # World state tracking
        self._world_state: dict[str, Any] = {}
        self._world_state_history: list[tuple[datetime, dict[str, Any]]] = []

        # Reasoning cache
        self._reasoning_cache: dict[str, ReasoningResult] = {}

        logger.info("worldmodel.initialized", latent_dim=latent_dim)

    def _encode_concept(self, text: str) -> np.ndarray:
        """
        Encode text into latent space representation.

        Uses a simple hash-based encoding for now.
        In production, use sentence-transformers or similar.
        """
        import hashlib

        vec = np.zeros(self.latent_dim, dtype=np.float32)

        for i, word in enumerate(text.lower().split()):
            hash_val = int(hashlib.sha256(word.encode()).hexdigest(), 16)
            for j in range(self.latent_dim):
                val = ((hash_val + i * j * 31) % 1000) / 500.0 - 1.0
                vec[j] += val

        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec

    def add_concept(
        self,
        name: str,
        properties: dict[str, Any],
        relationships: dict[str, float] = None,
    ) -> str:
        """
        Add a concept to the world model.

        Args:
            name: Concept name
            properties: Concept properties
            relationships: Related concepts and their strengths

        Returns:
            concept_id
        """
        concept_id = str(uuid4())
        embedding = self._encode_concept(name)

        if relationships is None:
            relationships = {}

        concept = Concept(
            concept_id=concept_id,
            name=name,
            embedding=embedding,
            properties=properties,
            relationships=relationships,
        )

        self._concepts[concept_id] = concept
        self._concept_embeddings[concept_id] = embedding

        logger.info("worldmodel.concept.added", name=name, concept_id=concept_id)

        return concept_id

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get a concept by ID."""
        return self._concepts.get(concept_id)

    def find_similar_concepts(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5,
    ) -> list[tuple[Concept, float]]:
        """
        Find concepts similar to a query.

        Args:
            query: Query text
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (concept, similarity) tuples
        """
        if not self._concepts:
            return []

        query_embedding = self._encode_concept(query)

        similarities = []
        for concept_id, concept in self._concepts.items():
            # Cosine similarity
            sim = np.dot(query_embedding, concept.embedding)
            if sim >= min_similarity:
                similarities.append((concept, float(sim)))

        # Sort by similarity descending
        similarities.sort(key=lambda x: -x[1])

        return similarities[:top_k]

    def update_world_state(self, state: dict[str, Any]) -> None:
        """
        Update the current world state.

        Args:
            state: Dictionary of state variables
        """
        self._world_state.update(state)
        self._world_state_history.append((datetime.utcnow(), state.copy()))

        # Keep history manageable
        if len(self._world_state_history) > 1000:
            self._world_state_history = self._world_state_history[-1000:]

        logger.debug("worldmodel.state.updated", keys=list(state.keys()))

    def get_world_state(self) -> dict[str, Any]:
        """Get the current world state."""
        return self._world_state.copy()

    def get_state_history(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[tuple[datetime, dict[str, Any]]]:
        """
        Get world state history.

        Args:
            since: Only return states after this time
            limit: Maximum number of states to return

        Returns:
            List of (timestamp, state) tuples
        """
        history = self._world_state_history

        if since:
            history = [h for h in history if h[0] >= since]

        return history[-limit:]

    async def simulate(
        self,
        initial_state: dict[str, Any],
        steps: int = 10,
        step_function: Optional[Callable] = None,
    ) -> list[SimulationState]:
        """
        Simulate a sequence of states.

        Args:
            initial_state: Starting state
            steps: Number of simulation steps
            step_function: Optional function to compute next state

        Returns:
            List of simulation states
        """
        simulation_id = str(uuid4())
        states = []

        current_state = initial_state.copy()

        for i in range(steps):
            # Encode state as vector
            state_vector = self._encode_state(current_state)

            state = SimulationState(
                simulation_id=simulation_id,
                state_vector=state_vector,
                metadata={"step": i, "state": current_state.copy()},
            )

            states.append(state)

            # Compute next state
            if step_function:
                current_state = await step_function(current_state, i)
            else:
                # Default: simple random walk
                current_state = self._default_step_function(current_state, i)

        # Store simulation
        self._simulations[simulation_id] = states[-1]
        self._simulation_history.extend(states)

        logger.info("worldmodel.simulation.completed", simulation_id=simulation_id, steps=steps)

        return states

    def _encode_state(self, state: dict[str, Any]) -> np.ndarray:
        """Encode a state dictionary into a vector."""
        vec = np.zeros(self.latent_dim, dtype=np.float32)

        for i, (key, value) in enumerate(state.items()):
            # Simple hash-based encoding
            hash_val = hash(str(key) + str(value))
            for j in range(self.latent_dim):
                val = ((hash_val + i * j * 31) % 1000) / 500.0 - 1.0
                vec[j] += val

        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec

    def _default_step_function(self, state: dict[str, Any], step: int) -> dict[str, Any]:
        """Default step function for simulation."""
        new_state = state.copy()

        # Add some noise to simulate uncertainty
        for key in new_state:
            if isinstance(new_state[key], (int, float)):
                noise = np.random.normal(0, 0.1)
                new_state[key] = new_state[key] * (1 + noise)

        return new_state

    async def reason(
        self,
        query: str,
        mode: ReasoningMode = ReasoningMode.DEDUCTIVE,
        context: dict[str, Any] = None,
    ) -> ReasoningResult:
        """
        Perform reasoning about a query.

        Args:
            query: The question or problem to reason about
            mode: Reasoning mode to use
            context: Additional context for reasoning

        Returns:
            ReasoningResult with conclusion and confidence
        """
        if context is None:
            context = {}

        # Check cache
        cache_key = f"{query}:{mode.name}:{hash(json.dumps(context, sort_keys=True))}"
        if cache_key in self._reasoning_cache:
            cached = self._reasoning_cache[cache_key]
            logger.debug("worldmodel.reasoning.cache_hit", query=query)
            return cached

        # Perform reasoning based on mode
        if mode == ReasoningMode.DEDUCTIVE:
            result = await _deductive_reasoning(query, context, self._concepts)
        elif mode == ReasoningMode.INDUCTIVE:
            result = await _inductive_reasoning(query, context, self._world_state_history)
        elif mode == ReasoningMode.ABDUCTIVE:
            result = await _abductive_reasoning(query, context, self._concepts)
        elif mode == ReasoningMode.ANALOGICAL:
            result = await _analogical_reasoning(query, context, self._concepts)
        elif mode == ReasoningMode.COUNTERFACTUAL:
            result = await _counterfactual_reasoning(query, context, self._world_state)
        else:
            result = ReasoningResult(
                conclusion="Unknown reasoning mode",
                confidence=0.0,
                mode=mode,
            )

        # Cache result
        self._reasoning_cache[cache_key] = result

        logger.info(
            "worldmodel.reasoning.completed",
            query=query,
            mode=mode.name,
            confidence=result.confidence,
        )

        return result

    async def explore_counterfactuals(
        self,
        base_state: dict[str, Any],
        changes: dict[str, Any],
        steps: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Explore "what if" scenarios.

        Args:
            base_state: The base world state
            changes: Changes to apply to explore alternatives
            steps: Number of steps to simulate

        Returns:
            List of alternative states
        """
        # Apply changes to base state
        alternative_state = base_state.copy()
        alternative_state.update(changes)

        # Simulate
        states = await self.simulate(
            initial_state=alternative_state,
            steps=steps,
        )

        # Extract state dictionaries
        result = [state.metadata["state"] for state in states]

        logger.info(
            "worldmodel.counterfactual.explored",
            changes=list(changes.keys()),
            steps=steps,
        )

        return result

    def get_simulation(self, simulation_id: str) -> Optional[list[SimulationState]]:
        """Get a simulation by ID."""
        if simulation_id in self._simulations:
            # Return all states for this simulation
            return [s for s in self._simulation_history if s.simulation_id == simulation_id]
        return None

    def clear_cache(self) -> None:
        """Clear reasoning cache."""
        self._reasoning_cache.clear()
        logger.info("worldmodel.cache.cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get world model statistics."""
        return {
            "concepts": len(self._concepts),
            "simulations": len(self._simulations),
            "world_state_vars": len(self._world_state),
            "state_history_size": len(self._world_state_history),
            "reasoning_cache_size": len(self._reasoning_cache),
        }


async def _deductive_reasoning(
    query: str,
    context: dict[str, Any],
    concepts: dict[str, Concept],
) -> ReasoningResult:
    """Deductive reasoning: derive conclusions from premises."""
    # Simple implementation: find relevant concepts and derive conclusion
    steps = []
    assumptions = []

    # Extract key terms from query
    query_lower = query.lower()
    relevant_concepts = [
        c for c in concepts.values()
        if any(term in c.name.lower() for term in query_lower.split())
    ]

    if relevant_concepts:
        steps.append(f"Found {len(relevant_concepts)} relevant concepts")
        for concept in relevant_concepts[:3]:
            steps.append(f"  - {concept.name}: {list(concept.properties.keys())}")

        # Derive conclusion from properties
        all_properties = {}
        for concept in relevant_concepts:
            all_properties.update(concept.properties)

        conclusion = f"Based on {len(relevant_concepts)} concepts, the answer involves: {list(all_properties.keys())[:5]}"
        confidence = 0.7
    else:
        conclusion = "No relevant concepts found for deductive reasoning"
        confidence = 0.3

    return ReasoningResult(
        conclusion=conclusion,
        confidence=confidence,
        reasoning_steps=steps,
        assumptions=assumptions,
        mode=ReasoningMode.DEDUCTIVE,
    )


async def _inductive_reasoning(
    query: str,
    context: dict[str, Any],
    state_history: list[tuple[datetime, dict[str, Any]]],
) -> ReasoningResult:
    """Inductive reasoning: generalize from observations."""
    steps = []
    assumptions = []

    if not state_history:
        return ReasoningResult(
            conclusion="No observations available for inductive reasoning",
            confidence=0.0,
            mode=ReasoningMode.INDUCTIVE,
        )

    # Analyze patterns in state history
    steps.append(f"Analyzing {len(state_history)} historical states")

    # Find patterns
    patterns = {}
    for timestamp, state in state_history[-10:]:  # Last 10 states
        for key, value in state.items():
            if key not in patterns:
                patterns[key] = []
            patterns[key].append(value)

    # Generalize from patterns
    generalizations = []
    for key, values in patterns.items():
        if len(values) > 1:
            # Check for trends
            if all(isinstance(v, (int, float)) for v in values):
                trend = "increasing" if values[-1] > values[0] else "decreasing"
                generalizations.append(f"{key} appears to be {trend}")

    if generalizations:
        conclusion = f"Observed patterns: {', '.join(generalizations[:3])}"
        confidence = 0.6
    else:
        conclusion = "Insufficient data for inductive generalization"
        confidence = 0.4

    return ReasoningResult(
        conclusion=conclusion,
        confidence=confidence,
        reasoning_steps=steps,
        assumptions=assumptions,
        mode=ReasoningMode.INDUCTIVE,
    )


async def _abductive_reasoning(
    query: str,
    context: dict[str, Any],
    concepts: dict[str, Concept],
) -> ReasoningResult:
    """Abductive reasoning: inference to best explanation."""
    steps = []
    assumptions = []

    # Find concepts that could explain the query
    query_lower = query.lower()
    explanations = []

    for concept in concepts.values():
        # Check if concept properties relate to query
        relevance = 0
        for prop_name, prop_value in concept.properties.items():
            if prop_name.lower() in query_lower:
                relevance += 1
            if isinstance(prop_value, str) and prop_value.lower() in query_lower:
                relevance += 1

        if relevance > 0:
            explanations.append((concept, relevance))

    # Sort by relevance
    explanations.sort(key=lambda x: -x[1])

    if explanations:
        best_concept, relevance = explanations[0]
        conclusion = f"Best explanation: {best_concept.name} (relevance: {relevance})"
        confidence = min(0.8, 0.3 + relevance * 0.1)
        steps.append(f"Considered {len(explanations)} potential explanations")
    else:
        conclusion = "No suitable explanation found"
        confidence = 0.2

    return ReasoningResult(
        conclusion=conclusion,
        confidence=confidence,
        reasoning_steps=steps,
        assumptions=assumptions,
        mode=ReasoningMode.ABDUCTIVE,
    )


async def _analogical_reasoning(
    query: str,
    context: dict[str, Any],
    concepts: dict[str, Concept],
) -> ReasoningResult:
    """Analogical reasoning: reason by similarity to known cases."""
    steps = []
    assumptions = []

    # Find similar concepts
    query_lower = query.lower()
    similarities = []

    for concept in concepts.values():
        # Simple similarity based on name overlap
        query_words = set(query_lower.split())
        concept_words = set(concept.name.lower().split())
        overlap = len(query_words & concept_words)
        if overlap > 0:
            similarities.append((concept, overlap))

    # Sort by similarity
    similarities.sort(key=lambda x: -x[1])

    if similarities:
        best_concept, overlap = similarities[0]
        conclusion = f"Analogous to: {best_concept.name} (similarity: {overlap} words)"
        confidence = min(0.7, 0.3 + overlap * 0.1)
        steps.append(f"Found {len(similarities)} analogous concepts")
    else:
        conclusion = "No analogous concepts found"
        confidence = 0.2

    return ReasoningResult(
        conclusion=conclusion,
        confidence=confidence,
        reasoning_steps=steps,
        assumptions=assumptions,
        mode=ReasoningMode.ANALOGICAL,
    )


async def _counterfactual_reasoning(
    query: str,
    context: dict[str, Any],
    world_state: dict[str, Any],
) -> ReasoningResult:
    """Counterfactual reasoning: explore 'what if' scenarios."""
    steps = []
    assumptions = []

    # Identify what would need to change
    query_lower = query.lower()

    # Find state variables mentioned in query
    relevant_vars = [
        key for key in world_state.keys()
        if key.lower() in query_lower
    ]

    if relevant_vars:
        steps.append(f"Identified {len(relevant_vars)} relevant state variables")

        # Propose counterfactual changes
        changes = {}
        for var in relevant_vars[:3]:
            current_value = world_state[var]
            if isinstance(current_value, bool):
                changes[var] = not current_value
            elif isinstance(current_value, (int, float)):
                changes[var] = current_value * 1.5  # Increase by 50%
            else:
                changes[var] = f"alternative_{current_value}"

        conclusion = f"Counterfactual: If {list(changes.keys())} were changed, outcomes would differ"
        confidence = 0.5
        assumptions.append(f"Assumes changes to: {list(changes.keys())}")
    else:
        conclusion = "No relevant state variables for counterfactual reasoning"
        confidence = 0.3

    return ReasoningResult(
        conclusion=conclusion,
        confidence=confidence,
        reasoning_steps=steps,
        assumptions=assumptions,
        mode=ReasoningMode.COUNTERFACTUAL,
    )
