"""Parallel executor — runs multiple agents concurrently on sub-tasks.

Pattern: LangGraph's parallel node execution, adapted for I/O-bound LLM calls.
Uses ThreadPoolExecutor since LLM API calls are I/O-bound (GIL doesn't block).

When merged, outputs are organized by agent. A post-merge stage combines them
into a coherent whole (e.g., frontend + backend files in code/).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.multi_agent import AgentRole

logger = logging.getLogger("parallel_executor")

MAX_PARALLEL_WORKERS = 4  # avoid overwhelming API rate limits


class ParallelExecutor:
    """Runs multiple agents in parallel, collecting and merging results."""

    def __init__(self, caller, task_dir: str):
        self.caller = caller
        self.task_dir = Path(task_dir)

    def run(self, agents: List[AgentRole], task_context: str,
            merge_strategy: str = "concat") -> Dict[str, Any]:
        """Execute agents in parallel.

        Args:
            agents: List of agent roles to run
            task_context: Shared task background
            merge_strategy: "concat" (concatenate outputs) | "by_file" (each to own file)

        Returns:
            {
                "success": bool,
                "output": str,              # merged output
                "per_agent": dict,          # agent_id → individual result
                "failed_agents": list[str], # agents that failed
                "error": str | None
            }
        """
        if not agents:
            return {"success": False, "error": "No agents provided", "output": ""}

        per_agent: Dict[str, Dict[str, Any]] = {}
        failed_agents: List[str] = []

        workers = min(len(agents), MAX_PARALLEL_WORKERS)
        logger.info(f"Parallel: running {len(agents)} agents with {workers} workers")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {}
            for agent in agents:
                agent_prompt = self._build_agent_prompt(agent, task_context)
                future = executor.submit(
                    self.caller.call, agent.agent_id, str(self.task_dir), agent_prompt
                )
                futures[future] = agent

            for future in as_completed(futures):
                agent = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    logger.error(f"Parallel: {agent.agent_id} crashed: {e}")
                    failed_agents.append(agent.agent_id)
                    per_agent[agent.agent_id] = {
                        "success": False,
                        "output": "",
                        "error": str(e),
                        "output_path": agent.output_path,
                    }
                    continue

                per_agent[agent.agent_id] = {
                    "success": result.get("success", False),
                    "output": result.get("output", ""),
                    "error": result.get("error"),
                    "output_path": agent.output_path,
                }

                if not result.get("success"):
                    failed_agents.append(agent.agent_id)
                    logger.warning(f"Parallel: {agent.agent_id} failed: {result.get('error')}")

        # Merge results
        merged_output = self._merge(per_agent, merge_strategy)

        all_failed = len(failed_agents) == len(agents)
        return {
            "success": not all_failed,
            "output": merged_output,
            "per_agent": per_agent,
            "failed_agents": failed_agents,
            "error": f"All agents failed" if all_failed else None,
        }

    def _build_agent_prompt(self, agent: AgentRole, task_context: str) -> str:
        parts = [
            f"## 你的角色\n{agent.role}",
            f"## 你的目标\n{agent.goal}",
        ]
        if agent.expertise:
            parts.append(f"## 专长领域\n{', '.join(agent.expertise)}")

        if agent.input_hint:
            parts.append(f"## 你的任务\n{agent.input_hint}")

        parts.append(f"## 整体项目背景\n{task_context}")
        parts.append(f"\n## 指令\n基于你的角色和专长完成你的任务部分。直接输出结果。")

        return "\n\n".join(parts)

    def _merge(self, per_agent: Dict[str, Dict], strategy: str) -> str:
        """Merge individual agent outputs into a single result."""
        if strategy == "by_file":
            # Each agent's output is saved to its own file — return a summary
            files = []
            for agent_id, data in per_agent.items():
                if data["success"]:
                    path = data.get("output_path", f"unknown/{agent_id}")
                    files.append(f"- [{agent_id}] → {path}")
            return "# 并行执行结果\n\n" + "\n".join(files) if files else "# 并行执行结果\n\n(无成功输出)"

        # "concat" — join all successful outputs with section headers
        sections = []
        for agent_id, data in per_agent.items():
            if data["success"] and data["output"]:
                sections.append(f"## {agent_id}\n\n{data['output'].strip()}")
        return "\n\n".join(sections) if sections else ""
