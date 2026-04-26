# meta/self_benchmark.py
"""Self-assessment and capability coverage scoring.

Evaluates the agent's capabilities across standard domains and identifies gaps.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import structlog

from tools.registry import ToolRegistry

logger = structlog.get_logger()


@dataclass
class BenchmarkResult:
    """Result of self-benchmark assessment."""
    coverage_score: float  # 0.0 to 1.0
    top_gaps: list[str]
    tools_registered: int
    memory_utilization: dict[str, int]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class SelfBenchmark:
    """Self-assessment for capability coverage.

    Evaluates the agent across 10 standard capability domains and provides
    a coverage score with identified gaps.
    """

    # 10 standard capability domains
    CAPABILITY_DOMAINS = [
        {
            "name": "web_research",
            "description": "Ability to search and retrieve information from the web",
            "required_tools": ["web_search", "web_fetch"],
            "required_skills": ["web_search", "web_fetch"],
        },
        {
            "name": "code_execution",
            "description": "Ability to execute code and scripts",
            "required_tools": ["bash", "python_execute"],
            "required_skills": ["code_execution"],
        },
        {
            "name": "file_operations",
            "description": "Ability to read, write, and manipulate files",
            "required_tools": ["read", "write", "edit"],
            "required_skills": ["file_operations"],
        },
        {
            "name": "memory_management",
            "description": "Ability to store and retrieve information",
            "required_tools": ["memory_write", "memory_recall"],
            "required_skills": ["memory_management"],
        },
        {
            "name": "reasoning",
            "description": "Ability to perform complex reasoning and planning",
            "required_tools": ["plan", "analyze"],
            "required_skills": ["reasoning", "planning"],
        },
        {
            "name": "communication",
            "description": "Ability to communicate with users and systems",
            "required_tools": ["chat", "notify"],
            "required_skills": ["communication"],
        },
        {
            "name": "data_analysis",
            "description": "Ability to analyze and process data",
            "required_tools": ["analyze", "process"],
            "required_skills": ["data_analysis"],
        },
        {
            "name": "automation",
            "description": "Ability to automate tasks and workflows",
            "required_tools": ["automate", "schedule"],
            "required_skills": ["automation"],
        },
        {
            "name": "security",
            "description": "Ability to perform security checks and validations",
            "required_tools": ["validate", "check_security"],
            "required_skills": ["security"],
        },
        {
            "name": "integration",
            "description": "Ability to integrate with external systems and APIs",
            "required_tools": ["api_call", "mcp_connect"],
            "required_skills": ["integration"],
        },
    ]

    def __init__(self, registry: ToolRegistry):
        """Initialize SelfBenchmark.

        Args:
            registry: The tool registry to check against
        """
        self.registry = registry
        logger.info("self_benchmark.initialized")

    async def run(self) -> dict[str, Any]:
        """Run the self-benchmark assessment.

        Returns:
            Dict with coverage score and identified gaps
        """
        logger.info("self_benchmark.running")

        # Get available tools
        available_tools = self.registry.list_tools()
        tool_names = {tool.name for tool in available_tools}

        # Evaluate each domain
        domain_scores = []
        gaps = []

        for domain in self.CAPABILITY_DOMAINS:
            domain_name = domain["name"]
            required_tools = domain.get("required_tools", [])
            required_skills = domain.get("required_skills", [])

            # Check tool coverage
            tools_covered = sum(1 for tool in required_tools if tool in tool_names)
            tool_score = tools_covered / len(required_tools) if required_tools else 1.0

            # For skills, we'd check skill registry (simplified here)
            skill_score = 1.0  # Assume skills are available for now

            # Domain score is average of tool and skill scores
            domain_score = (tool_score + skill_score) / 2.0
            domain_scores.append(domain_score)

            # Identify gaps
            missing_tools = [tool for tool in required_tools if tool not in tool_names]
            if missing_tools:
                gaps.append(f"{domain_name}: Missing tools {missing_tools}")

        # Calculate overall coverage score
        coverage_score = sum(domain_scores) / len(domain_scores) if domain_scores else 0.0

        # Get top gaps (most critical domains)
        top_gaps = sorted(gaps, key=lambda x: domain_scores[gaps.index(x)])[:5]

        # Get memory utilization (would need memory core reference)
        memory_utilization = {
            "working": 0,  # Would get from memory core
            "episodic": 0,
            "semantic": 0,
            "procedural": 0,
        }

        result = {
            "coverage_score": coverage_score,
            "top_gaps": top_gaps,
            "tools_registered": len(available_tools),
            "memory_utilization": memory_utilization,
            "metadata": {
                "domain_scores": dict(zip(
                    [d["name"] for d in self.CAPABILITY_DOMAINS],
                    domain_scores
                )),
                "total_domains": len(self.CAPABILITY_DOMAINS),
            }
        }

        logger.info(
            "self_benchmark.completed",
            coverage_score=coverage_score,
            tools_registered=len(available_tools),
            gaps_found=len(gaps)
        )

        return result

    def get_domain_status(self, domain_name: str) -> Optional[dict]:
        """Get status of a specific capability domain.

        Args:
            domain_name: Name of the domain to check

        Returns:
            Domain status dict or None if domain not found
        """
        for domain in self.CAPABILITY_DOMAINS:
            if domain["name"] == domain_name:
                available_tools = self.registry.list_tools()
                tool_names = {tool.name for tool in available_tools}

                required_tools = domain.get("required_tools", [])
                missing_tools = [tool for tool in required_tools if tool not in tool_names]

                return {
                    "name": domain["name"],
                    "description": domain["description"],
                    "required_tools": required_tools,
                    "available_tools": [t for t in required_tools if t in tool_names],
                    "missing_tools": missing_tools,
                    "coverage": len([t for t in required_tools if t in tool_names]) / len(required_tools)
                    if required_tools else 1.0,
                }

        return None

    def get_critical_gaps(self, threshold: float = 0.5) -> list[str]:
        """Get domains with coverage below threshold.

        Args:
            threshold: Coverage threshold (default 0.5)

        Returns:
            List of domain names with low coverage
        """
        available_tools = self.registry.list_tools()
        tool_names = {tool.name for tool in available_tools}

        critical = []
        for domain in self.CAPABILITY_DOMAINS:
            required_tools = domain.get("required_tools", [])
            if not required_tools:
                continue

            tools_covered = sum(1 for tool in required_tools if tool in tool_names)
            coverage = tools_covered / len(required_tools)

            if coverage < threshold:
                critical.append(domain["name"])

        return critical
