"""
subagent_manager.py — Parallel subagent task execution

ThreadPoolExecutor(max_workers=3). Each subagent is kernel.process(task) in isolation.
spawn(task) → agent_id.
get_status(id).
wait(id, timeout).
spawn_parallel([task1,task2,task3]) → [id1,id2,id3].
register_as_tool: "spawn_subagent" tool.
"""
import threading
import time
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from typing import Optional

log = logging.getLogger("SubagentManager")


class SubagentManager:
    def __init__(self, kernel_ref):
        self.kernel = kernel_ref
        self._agents: dict[str, dict] = {}
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="subagent")
        self._lock = threading.Lock()

    def spawn(self, task: str, priority: float = 0.5) -> str:
        """Spawn a new subagent to execute task. Returns agent_id."""
        agent_id = f"sa_{uuid.uuid4().hex[:8]}"

        def _run():
            with self._lock:
                self._agents[agent_id] = {
                    "id": agent_id,
                    "task": task,
                    "status": "running",
                    "started": datetime.now().isoformat(),
                    "result": None,
                    "error": None
                }
            try:
                result = self.kernel.process(task)
                with self._lock:
                    self._agents[agent_id]["status"] = "completed"
                    self._agents[agent_id]["result"] = result
                    self._agents[agent_id]["finished"] = datetime.now().isoformat()
                return result
            except Exception as e:
                with self._lock:
                    self._agents[agent_id]["status"] = "failed"
                    self._agents[agent_id]["error"] = str(e)
                    self._agents[agent_id]["finished"] = datetime.now().isoformat()
                raise

        future = self._executor.submit(_run)
        with self._lock:
            self._agents[agent_id]["_future"] = future

        log.info(f"[SUBAGENT] Spawned {agent_id}: {task[:50]}")
        return agent_id

    def get_status(self, agent_id: str) -> Optional[dict]:
        """Get current status of a subagent."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return None
            # Return copy without internal _future
            return {k: v for k, v in agent.items() if not k.startswith("_")}

    def wait(self, agent_id: str, timeout: float = 60.0) -> dict:
        """Wait for subagent to complete and return result."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return {"success": False, "error": "Agent not found"}
            future = agent.get("_future")

        if future:
            try:
                future.result(timeout=timeout)
            except Exception as e:
                return {"success": False, "error": str(e)}

        return self.get_status(agent_id) or {"success": False, "error": "Unknown"}

    def spawn_parallel(self, tasks: list[str], priorities: list[float] = None) -> list[str]:
        """Spawn multiple subagents in parallel. Returns list of agent_ids."""
        if priorities is None:
            priorities = [0.5] * len(tasks)
        return [self.spawn(t, p) for t, p in zip(tasks, priorities)]

    def list_active(self) -> list[dict]:
        """List all active subagents."""
        with self._lock:
            return [
                {k: v for k, v in agent.items() if not k.startswith("_")}
                for agent in self._agents.values()
                if agent["status"] == "running"
            ]

    def register_as_tool(self, registry):
        """Register spawn_subagent tool."""
        mgr = self

        def spawn_subagent(params: dict) -> dict:
            task = params.get("task", "")
            priority = float(params.get("priority", 0.5))
            if not task:
                return {"success": False, "error": "No task provided"}
            agent_id = mgr.spawn(task, priority)
            return {"success": True, "agent_id": agent_id, "status": "spawned"}

        def subagent_status(params: dict) -> dict:
            agent_id = params.get("agent_id", "")
            status = mgr.get_status(agent_id)
            return {"success": bool(status), "status": status}

        def wait_subagent(params: dict) -> dict:
            agent_id = params.get("agent_id", "")
            timeout = float(params.get("timeout", 60))
            result = mgr.wait(agent_id, timeout)
            return {"success": True, "result": result}

        registry.register(
            "spawn_subagent",
            spawn_subagent,
            "Spawn a parallel subagent to execute a task asynchronously",
            {"task": {"type": "string", "required": True}, "priority": {"type": "float", "default": 0.5}},
            "subagent"
        )
        registry.register(
            "subagent_status",
            subagent_status,
            "Get status of a spawned subagent",
            {"agent_id": {"type": "string", "required": True}},
            "subagent"
        )
        registry.register(
            "wait_subagent",
            wait_subagent,
            "Wait for subagent to complete and return result",
            {"agent_id": {"type": "string", "required": True}, "timeout": {"type": "float", "default": 60}},
            "subagent"
        )
