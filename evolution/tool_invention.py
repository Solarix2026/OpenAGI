# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""
tool_invention.py — L5 Dynamic Tool Creation

Triggered when:
1. User requests capability that no tool handles
2. Proactive engine detects tool failure rate > 60%
3. EvolutionEngine identifies a gap requiring a new capability

Process:
1. NVIDIA designs the tool (what it should do, what APIs to use)
2. NVIDIA writes Python function code
3. Code safety check (guard_protocols)
4. Dynamic exec() into registry namespace
5. Test with minimal call
6. If test passes → permanent registration + save to ./skills/invented/
"""
import json
import re
import logging
from pathlib import Path
from core.llm_gateway import call_nvidia

log = logging.getLogger("ToolInvention")
INVENTED_DIR = Path("./skills/invented")


class ToolInventionEngine:
    def __init__(self, memory, registry):
        self.memory = memory
        self.registry = registry
        INVENTED_DIR.mkdir(parents=True, exist_ok=True)
        self._load_previously_invented()

    def _load_previously_invented(self):
        """Load tools invented in previous sessions."""
        for path in INVENTED_DIR.glob("*.py"):
            try:
                code = path.read_text()
                ns = {}
                exec(code, ns)
                func = ns.get("tool_func")
                meta = ns.get("TOOL_META", {})
                if func and meta.get("name"):
                    self.registry.register(
                        name=meta["name"],
                        func=func,
                        description=meta.get("description", "Invented tool"),
                        category="invented"
                    )
                    log.info(f"[INVENTOR] Loaded: {meta['name']}")
            except Exception as e:
                log.debug(f"Failed to load invented tool {path}: {e}")

    def invent_tool(self, capability_needed: str, context: str = "") -> dict:
        """
        Design and create a new tool from a capability description.
        Returns: {"success", "tool_name", "code", "description"}
        """
        # Step 1: Design phase
        design_prompt = f"""Design a Python tool function for an AI agent.

Capability needed: "{capability_needed}"
Context: {context}

Hardware: i5-1135G7, Windows 11, Python 3.11, can use pip packages

Design:
1. What should this function do specifically?
2. What Python packages does it need?
3. What are the inputs and outputs?

Return JSON: {{"tool_name": "snake_case_name", "description": "one sentence", "packages": ["package1"], "input_params": {{"param": "type"}}, "output_format": {{"key": "type"}}, "approach": "how it works in 2 sentences"}}"""
        design_raw = call_nvidia([{"role": "user", "content": design_prompt}], max_tokens=500)
        m = re.search(r'\{.*\}', design_raw, re.DOTALL)
        if not m:
            return {"success": False, "error": "Design phase failed"}
        design = json.loads(m.group(0))

        # Step 2: Code generation
        code_prompt = f"""Write a complete Python function for this tool:

Design: {json.dumps(design)}

Requirements:
- Function name: tool_func
- Takes ONE dict argument: params
- Returns dict with "success" key always present
- Handle ALL exceptions with try/except, return {{"success": False, "error": str(e)}}
- Install packages with subprocess if missing (check ImportError first)
- Real working code — no placeholders

Also define at module level: TOOL_META = {{"name": "{design.get('tool_name', 'new_tool')}", "description": "{design.get('description', '')}"}}

Write ONLY the Python code, no explanation:"""
        code = call_nvidia([{"role": "user", "content": code_prompt}], max_tokens=1500)
        # Strip markdown fences
        code = re.sub(r'```python\n?|```\n?', '', code).strip()

        # Safety check: reject dangerous patterns
        dangerous = ['os.remove', 'shutil.rmtree', 'subprocess.call("rm', '__import__("os").system', 'eval(', 'exec(input']
        for d in dangerous:
            if d in code:
                return {"success": False, "error": f"Safety rejected: contains '{d}'"}

        # Step 3: Test execution
        try:
            ns = {}
            exec(code, ns)
            func = ns.get("tool_func")
            meta = ns.get("TOOL_META", {})
            if not func:
                return {"success": False, "error": "No tool_func found in generated code"}

            # Minimal smoke test
            test_result = func({})
            if not isinstance(test_result, dict):
                return {"success": False, "error": "tool_func must return dict"}

            # Step 4: Register and save
            tool_name = meta.get("name", design.get("tool_name", "invented_tool"))
            self.registry.register(
                name=tool_name,
                func=func,
                description=meta.get("description", capability_needed),
                category="invented"
            )

            # Save to disk
            save_path = INVENTED_DIR / f"{tool_name}.py"
            save_path.write_text(code)
            self.memory.log_event("tool_invented", tool_name, {"capability": capability_needed}, importance=0.9)
            log.info(f"[INVENTOR] ✅ Invented and registered: {tool_name}")
            return {
                "success": True,
                "tool_name": tool_name,
                "description": meta.get("description", ""),
                "code": code[:300] + "...",
                "saved_to": str(save_path)
            }
        except Exception as e:
            log.error(f"Tool invention failed: {e}")
            return {"success": False, "error": str(e)}

    def register_as_tool(self, registry):
        def invent_tool(params: dict) -> dict:
            capability = params.get("capability", "") or params.get("description", "")
            if not capability:
                return {"success": False, "error": "Describe the capability needed"}
            return self.invent_tool(capability)

        registry.register(
            name="invent_tool",
            func=invent_tool,
            description="Invent and register a new tool when no existing tool handles a capability",
            parameters={"capability": {"type": "string", "required": True}},
            category="self_evolution"
        )
