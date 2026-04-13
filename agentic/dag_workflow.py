# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
dag_workflow.py — Directed Acyclic Graph workflow engine

Unlike StrategicPlanner (sequential), DAGWorkflow executes steps in PARALLEL
where no dependencies exist. Max speedup on constrained hardware.

Example: "research topic, generate outline, write slides, save to disk"
    research (node 0) → outline depends on research (node 1) →
    slides depends on outline (node 2) → save depends on slides (node 3)
    Node 0 runs alone. Node 1 waits for 0. Node 2 waits for 1. Etc.

But: "research + fetch weather + check email" → all 3 in parallel.
"""
import json
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.llm_gateway import call_nvidia

log = logging.getLogger("DAGWorkflow")


class DAGWorkflowEngine:
    def __init__(self, kernel_ref):
        self.kernel = kernel_ref

    def plan_dag(self, goal: str) -> dict:
        """Generate DAG plan with parallel execution opportunities."""
        tools = self.kernel.executor.registry.list_tools()
        prompt = f"""Create a DAG (Directed Acyclic Graph) workflow for: "{goal}"

Available tools: {tools}

Identify which steps can run IN PARALLEL (no dependency) vs must be SEQUENTIAL.

Return JSON: {{
  "nodes": [
    {{"id": "A", "tool": "tool_name", "params": {{}}, "description": "what this does"}},
    ...
  ],
  "edges": [["A","B"],["A","C"]],  // A must complete before B and C
  "parallel_groups": [["A","B"],["C","D"]]  // these can run together
}}"""
        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=1000)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(m.group(0)) if m else {"nodes": [], "edges": [], "parallel_groups": []}

    def execute_dag(self, dag: dict, notify_fn=None) -> dict:
        """Execute DAG with parallel groups using ThreadPoolExecutor."""
        nodes = {n["id"]: n for n in dag.get("nodes", [])}
        edges = dag.get("edges", [])
        results = {}

        # Build dependency map
        deps = {nid: set() for nid in nodes}
        for src, dst in edges:
            deps.get(dst, set()).add(src)

        # Topological execution
        completed = set()
        max_workers = min(3, len(nodes))  # Hardware constraint: max 3 threads
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            while len(completed) < len(nodes):
                # Find nodes whose deps are all completed
                ready = [
                    nid for nid in nodes
                    if nid not in completed and deps[nid].issubset(completed)
                ]
                if not ready:
                    break

                if notify_fn:
                    notify_fn(f"⚡ Parallel: {', '.join(ready)}")

                # Execute ready nodes in parallel
                futures = {
                    pool.submit(self._exec_node, nodes[nid], results): nid
                    for nid in ready
                }
                for future in as_completed(futures):
                    nid = futures[future]
                    try:
                        results[nid] = future.result(timeout=60)
                        completed.add(nid)
                    except Exception as e:
                        results[nid] = {"success": False, "error": str(e)}
                        completed.add(nid)  # Mark done even on failure to avoid deadlock

        return {"results": results, "completed": len(completed), "total": len(nodes)}

    def _exec_node(self, node: dict, prior_results: dict) -> dict:
        """Execute a single DAG node. Inject prior results into params if needed."""
        tool = node.get("tool")
        params = dict(node.get("params", {}))

        # Template injection: {{node_A.output}} patterns
        for key, val in params.items():
            if isinstance(val, str) and "{{" in val:
                import re as re_inner
                for ref in re_inner.findall(r'\{\{(\w+)\.(\w+)\}\}', val):
                    dep_id, field = ref
                    dep_result = prior_results.get(dep_id, {})
                    replacement = str(dep_result.get(field, dep_result.get("data", "")))[:200]
                    params[key] = val.replace(f"{{{{{dep_id}.{field}}}}}", replacement)

        return self.kernel.executor.execute({"action": tool, "parameters": params})

    def register_as_tool(self, registry):
        def dag_execute(params: dict) -> dict:
            goal = params.get("goal", "")
            if not goal:
                return {"success": False, "error": "Provide goal"}
            dag = self.plan_dag(goal)
            result = self.execute_dag(dag)
            return {"success": True, "data": result, "dag": dag}

        registry.register(
            name="dag_execute",
            func=dag_execute,
            description="Execute a complex multi-step goal as a parallel DAG workflow for maximum efficiency",
            parameters={"goal": {"type": "string", "required": True}},
            category="agentic"
        )
