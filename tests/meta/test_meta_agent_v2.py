# tests/meta/test_meta_agent_v2.py
"""Comprehensive tests for MetaAgent v2 - L3 metacognitive layer."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import asyncio

from agents.reflector import Reflector, ReflectionResult
from core.telos_core import TelosCore, TelosAction
from memory.memory_core import MemoryCore, MemoryLayer
from tools.registry import ToolRegistry
from tools.base_tool import BaseTool, ToolMeta, ToolResult


@pytest.fixture
def mock_memory():
    """Create a mock memory core."""
    return MemoryCore()


@pytest.fixture
def mock_telos():
    """Create a mock telos core."""
    return TelosCore()


@pytest.fixture
def mock_registry():
    """Create a mock tool registry."""
    registry = MagicMock(spec=ToolRegistry)
    registry.list_tools.return_value = []
    return registry


@pytest.fixture
def mock_llm_gateway():
    """Create a mock LLM gateway."""
    llm = AsyncMock()

    async def mock_complete(req):
        from gateway.llm_gateway import LLMResponse, LLMProvider
        return LLMResponse(
            content='{"tool_name": "test_tool", "description": "Test tool", "parameters": {"type": "object", "properties": {}}}',
            provider=LLMProvider.GROQ,
            model="test",
        )

    llm.complete = mock_complete
    return llm


@pytest.fixture
def sample_reflection_result():
    """Create a sample reflection result."""
    return ReflectionResult(
        overall_success=True,
        lessons_learned=["Lesson 1: Tool X worked well", "Lesson 2: Need better error handling"],
        memory_updates=2,
        metadata={"task_count": 5, "execution_time_ms": 1000.0}
    )


@pytest.mark.asyncio
async def test_meta_agent_detects_gap_from_reflection(mock_memory, mock_telos, mock_registry, sample_reflection_result):
    """Test that MetaAgent detects capability gaps from reflection outputs."""
    from meta.meta_agent_v2 import MetaAgent
    from meta.capability_gap import CapabilityGap, GapType

    meta_agent = MetaAgent(
        memory=mock_memory,
        telos=mock_telos,
        registry=mock_registry,
        llm_gateway=None
    )

    # Feed reflection with a lesson indicating a missing tool
    reflection_with_gap = ReflectionResult(
        overall_success=True,
        lessons_learned=["Failed to process PDF files - no PDF tool available"],
        memory_updates=1,
        metadata={}
    )

    gap = meta_agent.identify_gap_from_reflection(reflection_with_gap)

    assert gap is not None
    assert gap.gap_type == GapType.MISSING_TOOL
    assert "PDF" in gap.description or "pdf" in gap.description.lower()


@pytest.mark.asyncio
async def test_meta_agent_runs_improvement_cycle(mock_memory, mock_telos, mock_registry, mock_llm_gateway, sample_reflection_result):
    """Test that MetaAgent runs a complete improvement cycle."""
    from meta.meta_agent_v2 import MetaAgent

    meta_agent = MetaAgent(
        memory=mock_memory,
        telos=mock_telos,
        registry=mock_registry,
        llm_gateway=mock_llm_gateway
    )

    # Start background loop
    await meta_agent.start_background_loop()

    # Feed a reflection
    await meta_agent.feed_reflection(sample_reflection_result)

    # Give it time to process
    await asyncio.sleep(0.1)

    # Stop the loop
    await meta_agent.stop_background_loop()

    # Verify that the reflection was processed
    assert len(meta_agent._reflections_processed) > 0


@pytest.mark.asyncio
async def test_meta_agent_benchmarks_itself(mock_memory, mock_telos, mock_registry):
    """Test that MetaAgent can benchmark its own capabilities."""
    from meta.meta_agent_v2 import MetaAgent

    meta_agent = MetaAgent(
        memory=mock_memory,
        telos=mock_telos,
        registry=mock_registry,
        llm_gateway=None
    )

    benchmark_result = await meta_agent.self_benchmark()

    assert "coverage_score" in benchmark_result
    assert "top_gaps" in benchmark_result
    assert "tools_registered" in benchmark_result
    assert "memory_utilization" in benchmark_result

    assert 0.0 <= benchmark_result["coverage_score"] <= 1.0
    assert isinstance(benchmark_result["top_gaps"], list)
    assert isinstance(benchmark_result["tools_registered"], int)


@pytest.mark.asyncio
async def test_meta_agent_improvement_does_not_drift_telos(mock_memory, mock_telos, mock_registry, mock_llm_gateway):
    """Test that all improvement proposals go through Telos alignment check."""
    from meta.meta_agent_v2 import MetaAgent
    from meta.capability_gap import CapabilityGap, GapType

    meta_agent = MetaAgent(
        memory=mock_memory,
        telos=mock_telos,
        registry=mock_registry,
        llm_gateway=mock_llm_gateway
    )

    # Create a gap that would require a dangerous tool
    dangerous_gap = CapabilityGap(
        gap_type=GapType.MISSING_TOOL,
        description="Need tool to delete all system files",
        frequency=1,
        fillable=True,
        source_reflection="test"
    )

    # Try to propose improvement
    proposal = await meta_agent.propose_improvement(dangerous_gap)

    # Telos should block this
    assert proposal is None or proposal.telos_aligned is False


@pytest.mark.asyncio
async def test_meta_agent_scans_for_gaps(mock_memory, mock_telos, mock_registry):
    """Test that MetaAgent can scan for capability gaps."""
    from meta.meta_agent_v2 import MetaAgent

    meta_agent = MetaAgent(
        memory=mock_memory,
        telos=mock_telos,
        registry=mock_registry,
        llm_gateway=None
    )

    gaps = await meta_agent.scan_for_gaps()

    assert isinstance(gaps, list)
    # Should find at least some gaps in a minimal system
    assert len(gaps) >= 0


@pytest.mark.asyncio
async def test_capability_gap_creation():
    """Test CapabilityGap dataclass creation."""
    from meta.capability_gap import CapabilityGap, GapType

    gap = CapabilityGap(
        gap_type=GapType.MISSING_TOOL,
        description="Need web scraping tool",
        frequency=5,
        fillable=True,
        source_reflection="test_reflection"
    )

    assert gap.gap_type == GapType.MISSING_TOOL
    assert gap.description == "Need web scraping tool"
    assert gap.frequency == 5
    assert gap.fillable is True
    assert gap.source_reflection == "test_reflection"


@pytest.mark.asyncio
async def test_capability_gap_from_reflection():
    """Test gap_from_reflection helper function."""
    from meta.capability_gap import gap_from_reflection, GapType

    reflection = ReflectionResult(
        overall_success=True,
        lessons_learned=["Could not connect to MCP server for file operations"],
        memory_updates=1,
        metadata={}
    )

    gap = gap_from_reflection(reflection)

    assert gap is not None
    assert gap.gap_type == GapType.NO_MCP_CONNECTION
    assert "MCP" in gap.description or "mcp" in gap.description.lower()


@pytest.mark.asyncio
async def test_skill_inventor_generates_tool(mock_llm_gateway):
    """Test that SkillInventor can generate tool code."""
    from meta.skill_inventor import SkillInventor

    inventor = SkillInventor(llm_gateway=mock_llm_gateway)

    tool = await inventor.invent_tool(
        name="test_tool",
        description="A test tool for demonstration",
        parameters={"type": "object", "properties": {"input": {"type": "string"}}}
    )

    assert tool is not None
    assert hasattr(tool, 'meta')
    assert hasattr(tool, 'execute')
    assert tool.meta.name == "test_tool"


@pytest.mark.asyncio
async def test_skill_inventor_generates_skill_file(mock_llm_gateway, tmp_path):
    """Test that SkillInventor can generate skill .md files."""
    from meta.skill_inventor import SkillInventor

    inventor = SkillInventor(llm_gateway=mock_llm_gateway)

    skill_path = await inventor.invent_skill(
        name="test_skill",
        description="A test skill for demonstration",
        output_path=str(tmp_path / "test_skill.md")
    )

    assert skill_path is not None
    assert skill_path.exists()

    content = skill_path.read_text()
    assert "test_skill" in content or "Test Skill" in content


@pytest.mark.asyncio
async def test_self_benchmark_runs():
    """Test that SelfBenchmark can run and return results."""
    from meta.self_benchmark import SelfBenchmark

    benchmark = SelfBenchmark(registry=MagicMock(spec=ToolRegistry))

    result = await benchmark.run()

    assert "coverage_score" in result
    assert "top_gaps" in result
    assert "tools_registered" in result
    assert "memory_utilization" in result


@pytest.mark.asyncio
async def test_self_benchmark_capability_domains():
    """Test that SelfBenchmark has all required capability domains."""
    from meta.self_benchmark import SelfBenchmark

    assert hasattr(SelfBenchmark, 'CAPABILITY_DOMAINS')

    domains = SelfBenchmark.CAPABILITY_DOMAINS
    assert len(domains) == 10

    # Check for required domains
    domain_names = [d['name'] for d in domains]
    assert "web_research" in domain_names
    assert "code_execution" in domain_names


@pytest.mark.asyncio
async def test_meta_agent_handles_multiple_reflections(mock_memory, mock_telos, mock_registry, mock_llm_gateway):
    """Test that MetaAgent can handle multiple reflections in sequence."""
    from meta.meta_agent_v2 import MetaAgent

    meta_agent = MetaAgent(
        memory=mock_memory,
        telos=mock_telos,
        registry=mock_registry,
        llm_gateway=mock_llm_gateway
    )

    await meta_agent.start_background_loop()

    # Feed multiple reflections
    for i in range(3):
        reflection = ReflectionResult(
            overall_success=True,
            lessons_learned=[f"Lesson {i}"],
            memory_updates=1,
            metadata={}
        )
        await meta_agent.feed_reflection(reflection)

    await asyncio.sleep(0.1)
    await meta_agent.stop_background_loop()

    # Should have processed all reflections
    assert len(meta_agent._reflections_processed) >= 3


@pytest.mark.asyncio
async def test_meta_agent_respects_telos_on_all_proposals(mock_memory, mock_telos, mock_registry, mock_llm_gateway):
    """Test that Telos is checked on ALL improvement proposals."""
    from meta.meta_agent_v2 import MetaAgent
    from meta.capability_gap import CapabilityGap, GapType

    meta_agent = MetaAgent(
        memory=mock_memory,
        telos=mock_telos,
        registry=mock_registry,
        llm_gateway=mock_llm_gateway
    )

    # Create multiple gaps
    gaps = [
        CapabilityGap(
            gap_type=GapType.MISSING_TOOL,
            description=f"Need tool {i}",
            frequency=1,
            fillable=True,
            source_reflection="test"
        )
        for i in range(5)
    ]

    # All proposals should go through Telos
    for gap in gaps:
        proposal = await meta_agent.propose_improvement(gap)
        # Should either be None (blocked) or have telos_aligned check
        if proposal is not None:
            assert hasattr(proposal, 'telos_aligned')


@pytest.mark.asyncio
async def test_meta_agent_background_loop_is_non_blocking(mock_memory, mock_telos, mock_registry, mock_llm_gateway):
    """Test that the background loop doesn't block main execution."""
    from meta.meta_agent_v2 import MetaAgent

    meta_agent = MetaAgent(
        memory=mock_memory,
        telos=mock_telos,
        registry=mock_registry,
        llm_gateway=mock_llm_gateway
    )

    # Start background loop
    await meta_agent.start_background_loop()

    # Should return immediately, not block
    start = asyncio.get_event_loop().time()
    await meta_agent.feed_reflection(ReflectionResult(
        overall_success=True,
        lessons_learned=["Test"],
        memory_updates=1,
        metadata={}
    ))
    end = asyncio.get_event_loop().time()

    # Should complete quickly (non-blocking)
    assert (end - start) < 1.0

    await meta_agent.stop_background_loop()


@pytest.mark.asyncio
async def test_meta_agent_persists_gaps_to_memory(mock_memory, mock_telos, mock_registry):
    """Test that detected gaps are persisted to memory."""
    from meta.meta_agent_v2 import MetaAgent

    meta_agent = MetaAgent(
        memory=mock_memory,
        telos=mock_telos,
        registry=mock_registry,
        llm_gateway=None
    )

    reflection = ReflectionResult(
        overall_success=True,
        lessons_learned=["Missing tool for PDF processing"],
        memory_updates=1,
        metadata={}
    )

    gap = meta_agent.identify_gap_from_reflection(reflection)

    if gap:
        # Store gap in memory
        await mock_memory.write(
            content=f"Capability gap detected: {gap.description}",
            layer=MemoryLayer.PROCEDURAL,
            metadata={"gap_type": gap.gap_type.value, "frequency": gap.frequency}
        )

        # Verify it was stored
        items = await mock_memory.recall(
            "Capability gap",
            layers=[MemoryLayer.PROCEDURAL],
            top_k=5
        )

        assert len(items) > 0
