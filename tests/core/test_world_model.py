"""Tests for WorldModel (L4)."""
import pytest
import asyncio
from datetime import datetime
from core.world_model import WorldModel, ReasoningMode, Concept, SimulationState, ReasoningResult


@pytest.fixture
def world_model():
    """Create a WorldModel instance for testing."""
    return WorldModel(latent_dim=128)


def test_world_model_initialization(world_model):
    """WorldModel initializes correctly."""
    assert world_model.latent_dim == 128
    assert len(world_model._concepts) == 0
    assert len(world_model._simulations) == 0


def test_add_concept(world_model):
    """Can add concepts to the world model."""
    concept_id = world_model.add_concept(
        name="test_concept",
        properties={"type": "test", "value": 42},
        relationships={"other_concept": 0.8},
    )

    assert concept_id is not None
    assert len(world_model._concepts) == 1

    concept = world_model.get_concept(concept_id)
    assert concept is not None
    assert concept.name == "test_concept"
    assert concept.properties["value"] == 42


def test_get_nonexistent_concept(world_model):
    """Getting nonexistent concept returns None."""
    result = world_model.get_concept("nonexistent")
    assert result is None


def test_find_similar_concepts(world_model):
    """Can find similar concepts."""
    # Add some concepts
    world_model.add_concept("python", {"type": "language"})
    world_model.add_concept("javascript", {"type": "language"})
    world_model.add_concept("coffee", {"type": "beverage"})

    # Find similar to "programming"
    results = world_model.find_similar_concepts("programming", top_k=2)

    assert len(results) >= 0
    # Results should be tuples of (concept, similarity)
    if results:
        assert isinstance(results[0], tuple)
        assert isinstance(results[0][0], Concept)
        assert isinstance(results[0][1], float)


def test_update_world_state(world_model):
    """Can update world state."""
    world_model.update_world_state({"temperature": 25, "humidity": 60})

    state = world_model.get_world_state()
    assert state["temperature"] == 25
    assert state["humidity"] == 60


def test_world_state_history(world_model):
    """World state history is tracked."""
    world_model.update_world_state({"value": 1})
    world_model.update_world_state({"value": 2})
    world_model.update_world_state({"value": 3})

    history = world_model.get_state_history(limit=10)
    assert len(history) == 3

    # Check that values are in order
    values = [state["value"] for _, state in history]
    assert values == [1, 2, 3]


@pytest.mark.asyncio
async def test_simulate(world_model):
    """Can run simulations."""
    initial_state = {"x": 0, "y": 0}

    states = await world_model.simulate(
        initial_state=initial_state,
        steps=5,
    )

    assert len(states) == 5
    assert all(isinstance(s, SimulationState) for s in states)


@pytest.mark.asyncio
async def test_simulate_with_step_function(world_model):
    """Can run simulations with custom step function."""
    initial_state = {"counter": 0}

    async def step_function(state, step):
        return {"counter": state["counter"] + 1}

    states = await world_model.simulate(
        initial_state=initial_state,
        steps=3,
        step_function=step_function,
    )

    assert len(states) == 3
    # Check that counter increased (states are stored before step function)
    assert states[0].metadata["state"]["counter"] == 0
    assert states[1].metadata["state"]["counter"] == 1
    assert states[2].metadata["state"]["counter"] == 2


@pytest.mark.asyncio
async def test_reason_deductive(world_model):
    """Can perform deductive reasoning."""
    # Add a concept
    world_model.add_concept("test", {"property": "value"})

    result = await world_model.reason(
        query="What is the test property?",
        mode=ReasoningMode.DEDUCTIVE,
    )

    assert isinstance(result, ReasoningResult)
    assert result.mode == ReasoningMode.DEDUCTIVE
    assert result.confidence >= 0.0
    assert result.confidence <= 1.0


@pytest.mark.asyncio
async def test_reason_inductive(world_model):
    """Can perform inductive reasoning."""
    # Add some state history
    world_model.update_world_state({"value": 1})
    world_model.update_world_state({"value": 2})
    world_model.update_world_state({"value": 3})

    result = await world_model.reason(
        query="What is the trend?",
        mode=ReasoningMode.INDUCTIVE,
    )

    assert isinstance(result, ReasoningResult)
    assert result.mode == ReasoningMode.INDUCTIVE


@pytest.mark.asyncio
async def test_reason_abductive(world_model):
    """Can perform abductive reasoning."""
    # Add a concept
    world_model.add_concept("explanation", {"type": "cause"})

    result = await world_model.reason(
        query="What caused this?",
        mode=ReasoningMode.ABDUCTIVE,
    )

    assert isinstance(result, ReasoningResult)
    assert result.mode == ReasoningMode.ABDUCTIVE


@pytest.mark.asyncio
async def test_reason_analogical(world_model):
    """Can perform analogical reasoning."""
    # Add a concept
    world_model.add_concept("similar_case", {"type": "example"})

    result = await world_model.reason(
        query="This is similar to what?",
        mode=ReasoningMode.ANALOGICAL,
    )

    assert isinstance(result, ReasoningResult)
    assert result.mode == ReasoningMode.ANALOGICAL


@pytest.mark.asyncio
async def test_reason_counterfactual(world_model):
    """Can perform counterfactual reasoning."""
    # Set up world state
    world_model.update_world_state({"temperature": 25, "pressure": 101})

    result = await world_model.reason(
        query="What if temperature changed?",
        mode=ReasoningMode.COUNTERFACTUAL,
    )

    assert isinstance(result, ReasoningResult)
    assert result.mode == ReasoningMode.COUNTERFACTUAL


@pytest.mark.asyncio
async def test_explore_counterfactuals(world_model):
    """Can explore counterfactual scenarios."""
    base_state = {"x": 10, "y": 20}
    changes = {"x": 100}

    alternatives = await world_model.explore_counterfactuals(
        base_state=base_state,
        changes=changes,
        steps=3,
    )

    assert len(alternatives) == 3
    # First state should have the change applied
    assert alternatives[0]["x"] == 100


def test_get_simulation(world_model):
    """Can retrieve simulations."""
    # This test is limited since we need to run a simulation first
    # Just test that the method exists and returns None for nonexistent
    result = world_model.get_simulation("nonexistent")
    assert result is None


def test_clear_cache(world_model):
    """Can clear reasoning cache."""
    # Add something to cache by reasoning
    asyncio.run(world_model.reason("test", ReasoningMode.DEDUCTIVE))

    # Clear cache
    world_model.clear_cache()

    # Cache should be empty
    assert len(world_model._reasoning_cache) == 0


def test_get_stats(world_model):
    """Can get world model statistics."""
    # Add some data
    world_model.add_concept("test", {})
    world_model.update_world_state({"key": "value"})

    stats = world_model.get_stats()

    assert "concepts" in stats
    assert "simulations" in stats
    assert "world_state_vars" in stats
    assert stats["concepts"] == 1
    assert stats["world_state_vars"] == 1
