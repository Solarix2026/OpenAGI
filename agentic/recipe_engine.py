# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
recipe_engine.py — YAML-based skill execution v2.0

Load YAML from ./skills/. Jinja2 template all {{ vars }}.
Steps: type=tool → executor.execute(). type=llm → call_nvidia().
Pass step output as context to next step via {{ step_id.field }}.

New v2.0: Subrecipes, triggers, error handling
"""
import yaml
import json
import re
import logging
from pathlib import Path
from jinja2 import Template
from core.llm_gateway import call_nvidia

log = logging.getLogger("RecipeEngine")
SKILLS_DIR = Path("./skills")


class RecipeEngine:
    def __init__(self, memory=None):
        self._recipes: dict[str, dict] = {}
        self.memory = memory
        self._load_all()
        self._triggers = self._load_triggers()

    def _load_all(self):
        """Load all YAML recipes from skills directory."""
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        for path in SKILLS_DIR.glob("*.yaml"):
            try:
                recipe = yaml.safe_load(path.read_text())
                if recipe and isinstance(recipe, dict):
                    self._recipes[path.stem] = recipe
                    log.info(f"[RECIPE] Loaded: {path.stem}")
            except Exception as e:
                log.warning(f"Failed to load recipe {path}: {e}")

    def get_recipe(self, name: str) -> dict | None:
        """Get a recipe by name."""
        if name not in self._recipes:
            self._load_all()
        return self._recipes.get(name)

    def list_recipes(self) -> list[str]:
        """List all available recipe names."""
        self._load_all()
        return list(self._recipes.keys())

    def execute_recipe(self, name: str, executor, variables: dict = None) -> dict:
        """
        Execute a recipe with given variables.
        Returns: {"success": bool, "results": dict, "steps_completed": int}
        """
        recipe = self.get_recipe(name)
        if not recipe:
            return {"success": False, "error": f"Recipe '{name}' not found"}

        ctx = {}
        step_results = {}
        results = []

        steps = recipe.get("steps", [])
        for i, step in enumerate(steps):
            step_id = step.get("id", f"step_{i}")
            step_type = step.get("type", "tool")

            rendered = self._render_step(step, variables, step_results)

            try:
                if step_type == "tool":
                    tool_name = rendered.get("tool")
                    params = rendered.get("params", {})
                    result = executor.execute({"action": tool_name, "parameters": params})
                elif step_type == "llm":
                    prompt = rendered.get("prompt", "")
                    result_text = call_nvidia([{"role": "user", "content": prompt}], max_tokens=rendered.get("max_tokens", 500))
                    result = {"success": True, "text": result_text}
                elif step_type == "recipe":
                    # Subrecipe: call another recipe
                    sub_name = rendered.get("recipe")
                    sub_params = rendered.get("params", {})
                    merged_params = {**(variables or {}), **sub_params, **step_results}
                    result = self.execute_subrecipe(sub_name, executor, merged_params, step_results)
                elif step_type == "set":
                    ctx[step_id] = rendered.get("value", "")
                    result = {"success": True, "value": ctx[step_id]}
                else:
                    result = {"success": False, "error": f"Unknown step type: {step_type}"}

                step_results[step_id] = result
                results.append({"step": step_id, "type": step_type, "success": result.get("success")})

                if not result.get("success"):
                    return {"success": False, "error": result.get("error"), "steps": results}

            except Exception as e:
                return {"success": False, "error": str(e), "steps": results}

        return {"success": True, "results": step_results, "steps_completed": len(steps)}

    def _render_step(self, step: dict, variables: dict, step_results: dict) -> dict:
        """Render Jinja2 templates in step configuration."""
        import copy
        rendered = copy.deepcopy(step)

        ctx = {}
        if variables:
            ctx.update(variables)
        for step_id, result in step_results.items():
            ctx[step_id] = result
            if isinstance(result, dict):
                for key, val in result.items():
                    ctx[f"{step_id}.{key}"] = val

        def render_obj(obj):
            if isinstance(obj, str):
                try:
                    return Template(obj).render(**ctx)
                except Exception:
                    return obj
            elif isinstance(obj, dict):
                return {k: render_obj(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [render_obj(item) for item in obj]
            return obj

        return render_obj(rendered)

    def recipe_to_tool(self, name: str, executor) -> callable:
        """Convert a recipe into a callable tool function."""
        recipe = self.get_recipe(name)
        if not recipe:
            return None

        def tool_func(params: dict) -> dict:
            return self.execute_recipe(name, executor, params)

        executor.registry.register(
            name=name,
            func=tool_func,
            description=recipe.get("description", f"Execute {name} recipe"),
            parameters=recipe.get("parameters", {}),
            category="recipe"
        )
        return tool_func

    # ── Subrecipe Support ───────────────────────────────────────────

    def execute_subrecipe(self, sub_name: str, executor, params: dict = None, parent_ctx: dict = None) -> dict:
        """
        Execute a sub-recipe with merged context from parent.
        Subrecipes can call other recipes.
        """
        merged_params = {**(parent_ctx or {}), **(params or {})}
        log.info(f"[SUBRECIPE] {sub_name} called with {len(merged_params)} params")
        return self.execute_recipe_with_error_handling(sub_name, executor, merged_params, parent_ctx)

    def execute_recipe_with_error_handling(self, name: str, executor, variables: dict = None, parent_ctx: dict = None) -> dict:
        """
        Execute recipe with error path support.
        """
        result = self.execute_recipe(name, executor, variables)
        if result.get("success"):
            return result

        recipe = self.get_recipe(name)
        error_steps = recipe.get("on_error", [])
        if error_steps:
            error_ctx = {
                "error": result.get("error", ""),
                "failed_step": result.get("steps", [])[:-1] if result.get("steps") else [],
                "variables": variables
            }
            if parent_ctx:
                error_ctx.update(parent_ctx)

            log.info(f"[RECIPE] Running {len(error_steps)} error handlers for {name}")
            for err_step in error_steps:
                rendered = self._render_step(err_step, error_ctx, {})
                try:
                    if rendered.get("type") == "notify":
                        msg = rendered.get("message", "Recipe failed")
                        log.warning(f"[RECIPE ERROR] {msg}")
                except Exception as e:
                    log.error(f"Error handler failed: {e}")

        return result

    # ── Trigger Support ─────────────────────────────────────────────

    def _load_triggers(self) -> dict:
        """Load trigger recipes from meta_knowledge."""
        if not self.memory:
            return {}
        try:
            meta = self.memory.get_meta_knowledge("recipe_triggers")
            return meta.get("content", {}) if meta else {}
        except Exception:
            return {}

    def _save_triggers(self, triggers: dict):
        """Save trigger recipes to meta_knowledge."""
        if self.memory:
            self.memory.update_meta_knowledge("recipe_triggers", triggers)

    def register_trigger(self, recipe_name: str, trigger: dict):
        """
        Register a trigger for automatic recipe execution.
        trigger = {
            "type": "cron",
            "schedule": "0 8 * * *",
            "event": "user_idle_30min",
            "webhook_url": "..."
        }
        """
        self._triggers[recipe_name] = trigger
        self._save_triggers(self._triggers)
        log.info(f"[TRIGGER] Registered {recipe_name}: {trigger}")

    def check_and_fire_triggers(self, executor, memory) -> list:
        """Called by ProactiveEngine every cycle."""
        from datetime import datetime
        fired = []
        for recipe_name, trigger in self._triggers.items():
            if trigger.get("type") == "cron":
                cron = trigger.get("schedule", "")
                if self._cron_matches(cron, datetime.now()):
                    result = self.execute_recipe(recipe_name, executor, {})
                    if result.get("success"):
                        fired.append(recipe_name)
                        log.info(f"[TRIGGER] Fired {recipe_name} at {datetime.now()}")
        return fired

    def _cron_matches(self, cron: str, dt: datetime) -> bool:
        """Simple cron matching (minute hour * * *)."""
        try:
            parts = cron.split()
            if len(parts) >= 2:
                minute, hour = int(parts[0]), int(parts[1])
                return dt.minute == minute and dt.hour == hour
        except Exception:
            pass
        return False
