# meta/skill_inventor.py
"""Auto-generates tools and skills on demand.

Uses LLM to design and generate tool code and skill .md files,
with importlib-based validation (no exec/eval).
"""
import importlib
import importlib.util
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

import structlog

from gateway.llm_gateway import LLMGateway
from tools.base_tool import BaseTool, ToolMeta, ToolResult

logger = structlog.get_logger()


class SkillInventor:
    """Auto-generates tools and skills on demand.

    Uses LLM to design specifications and generate code, then validates
    using importlib (safe, no exec/eval).
    """

    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        """Initialize SkillInventor.

        Args:
            llm_gateway: LLM gateway for generating code and specs
        """
        self.llm_gateway = llm_gateway
        logger.info("skill_inventor.initialized")

    async def invent_tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        examples: Optional[list[dict]] = None,
    ) -> Optional[BaseTool]:
        """Generate a new tool from specification.

        Args:
            name: Name of the tool to generate
            description: Description of what the tool should do
            parameters: JSON schema for tool parameters
            examples: Optional example usage

        Returns:
            Instantiated BaseTool or None if generation fails
        """
        logger.info("skill_inventor.inventing_tool", name=name)

        try:
            # Design tool spec
            spec = await self._design_tool_spec(name, description, parameters, examples)

            # Generate tool code
            code = await self._generate_tool_code(spec)

            # Validate and instantiate
            tool = await self._validate_and_instantiate(code, name)

            if tool:
                logger.info("skill_inventor.tool_created", name=name)
            else:
                logger.warning("skill_inventor.tool_creation_failed", name=name)

            return tool

        except Exception as e:
            logger.exception("skill_inventor.tool_error", name=name, error=str(e))
            return None

    async def invent_skill(
        self,
        name: str,
        description: str,
        output_path: Optional[str] = None,
    ) -> Optional[Path]:
        """Generate a new skill .md file.

        Args:
            name: Name of the skill to generate
            description: Description of what the skill should do
            output_path: Optional path to save the skill file

        Returns:
            Path to the generated skill file or None if generation fails
        """
        logger.info("skill_inventor.inventing_skill", name=name)

        try:
            if not self.llm_gateway:
                logger.warning("skill_inventor.no_llm_gateway")
                return None

            # Generate skill content
            prompt = f"""Generate a skill markdown file for a skill named "{name}".

Description: {description}

The skill file should follow this format:
```markdown
# {name}

## Description
{description}

## When to Use
[Describe when this skill should be triggered]

## Parameters
[List any parameters this skill accepts]

## Examples
[Provide example usage]

## Implementation Notes
[Any implementation notes or requirements]
```

Generate only the markdown content, no additional text."""

            from gateway.llm_gateway import LLMRequest
            response = await self.llm_gateway.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                )
            )

            if not response or not response.content:
                logger.warning("skill_inventor.empty_llm_response")
                return None

            # Determine output path
            if output_path is None:
                output_path = str(Path.cwd() / "skills" / f"{name}.md")

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Write skill file
            output_file.write_text(response.content, encoding="utf-8")

            logger.info("skill_inventor.skill_created", path=str(output_file))
            return output_file

        except Exception as e:
            logger.exception("skill_inventor.skill_error", name=name, error=str(e))
            return None

    async def _design_tool_spec(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        examples: Optional[list[dict]],
    ) -> dict[str, Any]:
        """Design tool specification using LLM.

        Args:
            name: Tool name
            description: Tool description
            parameters: Parameter schema
            examples: Example usage

        Returns:
            Tool specification dict
        """
        if not self.llm_gateway:
            # Return basic spec without LLM
            return {
                "name": name,
                "description": description,
                "parameters": parameters,
                "examples": examples or [],
                "risk_score": 0.0,
                "categories": [],
            }

        prompt = f"""Design a tool specification for a tool named "{name}".

Description: {description}

Parameters schema:
{parameters}

Examples:
{examples or []}

Provide a JSON response with:
- name: tool name
- description: detailed description
- parameters: JSON schema for parameters
- examples: list of example usage
- risk_score: float from 0.0 (safe) to 1.0 (dangerous)
- categories: list of relevant categories

Return only valid JSON, no additional text."""

        from gateway.llm_gateway import LLMRequest
        response = await self.llm_gateway.complete(
            LLMRequest(
                messages=[{"role": "user", "content": prompt}],
            )
        )

        if not response or not response.content:
            logger.warning("skill_inventor.empty_spec_response")
            return {
                "name": name,
                "description": description,
                "parameters": parameters,
                "examples": examples or [],
                "risk_score": 0.0,
                "categories": [],
            }

        try:
            import json
            spec = json.loads(response.content)
            return spec
        except json.JSONDecodeError:
            logger.warning("skill_inventor.invalid_json_response")
            return {
                "name": name,
                "description": description,
                "parameters": parameters,
                "examples": examples or [],
                "risk_score": 0.0,
                "categories": [],
            }

    async def _generate_tool_code(self, spec: dict[str, Any]) -> str:
        """Generate tool code from specification.

        Args:
            spec: Tool specification

        Returns:
            Generated Python code
        """
        if not self.llm_gateway:
            # Return basic template without LLM
            return self._generate_basic_tool_template(spec)

        prompt = f"""Generate Python code for a tool based on this specification:

{spec}

The tool should:
1. Extend BaseTool from tools.base_tool
2. Implement the 'meta' property returning ToolMeta
3. Implement the 'execute' async method
4. Return ToolResult from execute
5. Include proper error handling
6. Be production-ready with logging

Generate only the Python code, no additional text or explanation."""

        from gateway.llm_gateway import LLMRequest
        response = await self.llm_gateway.complete(
            LLMRequest(
                messages=[{"role": "user", "content": prompt}],
            )
        )

        if not response or not response.content:
            logger.warning("skill_inventor.empty_code_response")
            return self._generate_basic_tool_template(spec)

        return response.content

    def _generate_basic_tool_template(self, spec: dict[str, Any]) -> str:
        """Generate a basic tool template without LLM.

        Args:
            spec: Tool specification

        Returns:
            Basic Python code template
        """
        name = spec.get("name", "generated_tool")
        description = spec.get("description", "Auto-generated tool")
        parameters = spec.get("parameters", {})
        risk_score = spec.get("risk_score", 0.0)
        categories = spec.get("categories", [])

        return f'''# tools/generated/{name}.py
"""Auto-generated tool: {name}."""

from datetime import datetime
from typing import Any

import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult

logger = structlog.get_logger()


class Generated{name.capitalize()}(BaseTool):
    """Auto-generated tool: {name}."""

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="{name}",
            description="{description}",
            parameters={parameters},
            risk_score={risk_score},
            categories={categories},
            examples=[]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the {name} tool."""
        try:
            # TODO: Implement tool logic here
            result = "Tool executed successfully"

            return ToolResult(
                success=True,
                tool_name="{name}",
                data=result,
                execution_time_ms=0.0,
                timestamp=datetime.utcnow(),
                metadata={{}}
            )
        except Exception as e:
            logger.exception("tool.error", tool_name="{name}", error=str(e))
            return ToolResult(
                success=False,
                tool_name="{name}",
                error=str(e),
                execution_time_ms=0.0,
                timestamp=datetime.utcnow(),
                metadata={{}}
            )
'''

    async def _validate_and_instantiate(self, code: str, name: str) -> Optional[BaseTool]:
        """Validate and instantiate tool code using importlib.

        Args:
            code: Generated Python code
            name: Tool name

        Returns:
            Instantiated BaseTool or None if validation fails
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                delete=False,
                encoding="utf-8"
            ) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Load module using importlib (safe, no exec/eval)
                spec = importlib.util.spec_from_file_location(
                    f"generated_{name}",
                    temp_path
                )

                if spec is None or spec.loader is None:
                    logger.error("skill_inventor.invalid_module_spec")
                    return None

                module = importlib.util.module_from_spec(spec)
                sys.modules[f"generated_{name}"] = module
                spec.loader.exec_module(module)

                # Find BaseTool subclass
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseTool)
                        and attr is not BaseTool
                    ):
                        # Instantiate the tool
                        tool_instance = attr()
                        logger.info("skill_inventor.tool_validated", name=name)
                        return tool_instance

                logger.warning("skill_inventor.no_basetool_found")
                return None

            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.exception("skill_inventor.validation_error", name=name, error=str(e))
            return None
