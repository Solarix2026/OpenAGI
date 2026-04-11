"""
innovation_engine.py — L5 Creative Problem Solving

Not pattern matching. Combinatorial synthesis from first principles.

Three mechanisms:
  1. Axiom decomposition (Feynman/Musk style)
  2. Analogical transfer (cross-domain solution borrowing)
  3. Contradiction resolution (TRIZ-inspired)

These combine to generate solutions that do NOT exist in training data.
"""
import re, json, logging
from llm_gateway import call_nvidia

log = logging.getLogger("Innovation")


class InnovationEngine:
    def decompose_to_axioms(self, problem: str) -> dict:
        """Break any problem into irreducible constraints from first principles."""
        prompt = f"""Decompose this problem from first principles:

"{problem}"

Think like Feynman or Musk — ignore conventional solutions.
Start from physics, logic, or human needs.

Return JSON:
{{"axioms": ["fundamental constraint 1", ...], "key_constraints": ["hard limit 1", ...], "success_criteria": ["how to know it's solved", ...], "what_to_ignore": ["conventional assumptions to discard", ...]}}"""

        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=600)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        return json.loads(m.group(0)) if m else {"axioms": []}

    def analogical_transfer(self, problem: str, domains: list = None) -> list:
        """Find solutions from analogous domains."""
        domains = domains or ["biology", "military strategy", "economics", "architecture", "physics"]

        prompt = f"""Find analogous solutions for:

"{problem}"

Domains to search: {domains}

For each domain, find a SPECIFIC mechanism that solved a similar problem.
The mechanism must be concrete, not vague.

Return JSON:
{{"analogies": [
  {{"domain": "...", "mechanism": "specific name/concept", "how_it_works": "...", "transfer_to_problem": "..."}}
]}}"""

        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=800)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(m.group(0)) if m else {}
        return result.get("analogies", [])

    def resolve_contradiction(self, req_a: str, req_b: str) -> list:
        """TRIZ: find inventive principles that satisfy both conflicting requirements."""
        prompt = f"""Resolve this contradiction using inventive thinking:

Requirement A: {req_a}
Requirement B: {req_b}

These seem to conflict. Find solutions that satisfy BOTH simultaneously.
Use TRIZ principles: segmentation, prior action, inversion, merging, etc.

Return JSON:
{{"principles_used": ["..."], "solutions": ["solution 1 that satisfies both", "solution 2", ...]}}"""

        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=600)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(m.group(0)) if m else {}
        return result.get("solutions", [])

    def generate_novel_solutions(self, problem: str, constraints: list = None, n: int = 5) -> list:
        """Full pipeline: axioms + analogies → synthesize N novel solutions."""
        axioms = self.decompose_to_axioms(problem)
        analogies = self.analogical_transfer(problem)

        analogy_summary = "\n".join(
            f"- From {a.get('domain','?')}: {a.get('transfer_to_problem','')}"
            for a in analogies[:3]
        )

        prompt = f"""Generate {n} novel solutions for:

"{problem}"

Axioms/constraints: {json.dumps(axioms.get('axioms', []), ensure_ascii=False)}
Cross-domain inspirations: {analogy_summary}
User constraints: {constraints or "none specified"}

Each solution must:
1. Satisfy the axioms
2. Be genuinely different from the obvious approach
3. Have a concrete mechanism (not vague description)

Return JSON:
{{"solutions": [
  {{"solution": "concrete description", "mechanism": "how it works", "novelty_score": 0.0-1.0, "feasibility": 0.0-1.0, "why_non_obvious": "..."}}
]}}"""

        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=2000)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(m.group(0)) if m else {}
        return result.get("solutions", [])

    def evolve_solution(self, solution: str, feedback: str, iterations: int = 2) -> str:
        """Iteratively improve a solution via LLM mutation."""
        current = solution
        for i in range(iterations):
            prompt = f"""Improve this solution based on feedback:

Current: {current}
Feedback: {feedback}

Make it more practical and implementable.
Return only the improved solution."""
            current = call_nvidia(
                [{"role": "user", "content": prompt}],
                max_tokens=400,
                fast=True
            )
        return current

    def register_as_tool(self, registry):
        def innovate(params: dict) -> dict:
            problem = params.get("problem", "")
            mode = params.get("mode", "full")

            if mode == "axioms":
                return self.decompose_to_axioms(problem)
            elif mode == "analogies":
                return {"analogies": self.analogical_transfer(problem)}
            else:
                solutions = self.generate_novel_solutions(problem)
                top = solutions[0] if solutions else {}
                return {"solutions": solutions, "top_solution": top, "problem": problem}

        registry.register(
            name="innovate",
            func=innovate,
            description="Generate novel creative solutions using first principles, analogies, and contradiction resolution",
            parameters={"problem": {"type": "string", "required": True}, "mode": {"type": "string", "default": "full"}},
            category="innovation"
        )
