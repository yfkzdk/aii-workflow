"""Debate engine — N agents generate independently, reviewer picks the best.

Pattern: AutoGen GroupChat's multi-speaker debate, adapted for pipeline style.
Each agent sees the same task context but produces from their specialized perspective.
The reviewer evaluates all outputs against quality criteria and selects the winner.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.multi_agent import AgentRole, MultiAgentStrategy

logger = logging.getLogger("debate_engine")

REVIEWER_PROMPT_TEMPLATE = """## 评审任务
你是评审专家。请评价以下 {n} 份输出，选出最佳的一份。

**重要：winner 字段必须使用下面列出的 agent_id（例如 prompt_optimizer），不能用数字编号。**

## 原始任务背景
{task_context}

{agent_outputs}

## 评审标准
1. 完整性 — 是否覆盖了任务的所有关键点
2. 清晰性 — 表述是否精确、无歧义
3. 可执行性 — 下游 agent 能否直接使用
4. 稳健性 — 是否考虑了边界情况和错误处理

## 输出格式
```json
{{
  "winner": "<使用上面列出的 agent_id，不要用数字>",
  "scores": {{
    "<agent_id>": {{"completeness": 0.0, "clarity": 0.0, "actionability": 0.0, "robustness": 0.0}}
  }},
  "reasoning": "选择理由（≤150字）"
}}
```
"""


class DebateEngine:
    """Runs N agents on the same task and uses a reviewer to pick the best output."""

    def __init__(self, caller, task_dir: str):
        self.caller = caller
        self.task_dir = Path(task_dir)

    def run(self, agents: List[AgentRole], task_context: str,
            reviewer_agent_id: str) -> Dict[str, Any]:
        """Execute debate: all agents generate → reviewer picks best.

        Returns:
            {
                "success": bool,
                "output": str,           # winning output
                "winner": str,           # winning agent_id
                "scores": dict,          # per-agent scores
                "all_outputs": dict,     # agent_id → output
                "reviewer_reasoning": str,
                "error": str | None
            }
        """
        if len(agents) < 2:
            return {
                "success": False,
                "error": f"Debate requires >= 2 agents, got {len(agents)}",
                "output": "",
            }

        # Phase 1: Run all agents
        outputs: Dict[str, Dict[str, Any]] = {}
        for agent in agents:
            logger.info(f"Debate: running {agent.agent_id} ({agent.role})")
            agent_prompt = self._build_agent_prompt(agent, task_context)
            result = self.caller.call(agent.agent_id, str(self.task_dir), agent_prompt)
            outputs[agent.agent_id] = {
                "agent": agent,
                "result": result,
            }

        # Check for complete failure
        successes = {aid: o for aid, o in outputs.items() if o["result"].get("success")}
        if len(successes) == 0:
            return {
                "success": False,
                "error": "All debate agents failed",
                "output": "",
                "all_outputs": {aid: o["result"].get("output", "") for aid, o in outputs.items()},
            }

        if len(successes) == 1:
            # Only one agent succeeded — skip review, use it directly
            sole = list(successes.keys())[0]
            logger.info(f"Debate: only {sole} succeeded, using directly")
            return {
                "success": True,
                "output": successes[sole]["result"]["output"],
                "winner": sole,
                "scores": {sole: {}},
                "all_outputs": {aid: o["result"].get("output", "") for aid, o in outputs.items()},
                "reviewer_reasoning": "Sole successful agent — no review needed",
            }

        # Phase 2: Reviewer evaluates
        review_prompt = self._build_review_prompt(successes, task_context)
        logger.info(f"Debate: reviewer evaluating {len(successes)} outputs")
        review_result = self.caller.call(reviewer_agent_id, str(self.task_dir), review_prompt)

        if not review_result.get("success"):
            # Reviewer failed — fall back to first successful agent
            fallback = list(successes.keys())[0]
            logger.warning(f"Debate: reviewer failed, falling back to {fallback}")
            return {
                "success": True,
                "output": successes[fallback]["result"]["output"],
                "winner": fallback,
                "scores": {},
                "all_outputs": {aid: o["result"].get("output", "") for aid, o in outputs.items()},
                "reviewer_reasoning": f"Reviewer failed: {review_result.get('error')}",
            }

        # Phase 3: Parse verdict (with safety fallback)
        verdict = self._parse_verdict(review_result.get("output", ""), list(successes.keys()))
        winner_id = verdict.get("winner", list(successes.keys())[0])

        # Safety: if LLM returned a non-existent agent_id, fall back
        if winner_id not in successes:
            logger.warning(f"Debate: reviewer returned unknown winner '{winner_id}', "
                           f"falling back to first successful agent")
            winner_id = list(successes.keys())[0]

        return {
            "success": True,
            "output": successes[winner_id]["result"]["output"],
            "winner": winner_id,
            "scores": verdict.get("scores", {}),
            "all_outputs": {aid: o["result"].get("output", "") for aid, o in outputs.items()},
            "reviewer_reasoning": verdict.get("reasoning", ""),
        }

    def _build_agent_prompt(self, agent: AgentRole, task_context: str) -> str:
        """Build a focused prompt for the agent based on its role and expertise."""
        parts = [
            f"## 你的角色\n{agent.role}",
            f"## 你的目标\n{agent.goal}",
        ]
        if agent.expertise:
            parts.append(f"## 专长领域\n{', '.join(agent.expertise)}")

        if agent.input_hint:
            parts.append(f"## 聚焦方向\n{agent.input_hint}")

        parts.append(f"## 任务背景\n{task_context}")
        parts.append(f"\n## 指令\n请基于你的角色和专长完成上述任务。直接输出结果，不要输出额外的解释。")

        return "\n\n".join(parts)

    def _build_review_prompt(self, successes: Dict[str, Dict], task_context: str) -> str:
        """Build the reviewer's evaluation prompt with all agent outputs."""
        output_sections = []
        for i, (agent_id, data) in enumerate(successes.items(), 1):
            agent = data["agent"]
            output = data["result"].get("output", "")
            # Truncate long outputs for the reviewer
            truncated = output[:3000] + "\n... (已截断)" if len(output) > 3000 else output
            output_sections.append(
                f"### Agent: {agent.agent_id}\n"
                f"**角色**: {agent.role}\n"
                f"**目标**: {agent.goal}\n"
                f"**专长**: {', '.join(agent.expertise)}\n\n"
                f"**输出**:\n```\n{truncated}\n```"
            )

        return REVIEWER_PROMPT_TEMPLATE.format(
            n=len(successes),
            task_context=task_context[:2000],
            agent_outputs="\n\n".join(output_sections),
        )

    @staticmethod
    def _parse_verdict(reviewer_output: str, agent_ids: List[str]) -> Dict[str, Any]:
        """Parse the reviewer's JSON verdict from LLM output."""
        # Try direct JSON parse
        try:
            return json.loads(reviewer_output)
        except json.JSONDecodeError:
            pass

        # Try extracting from ```json ... ``` block
        import re
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", reviewer_output, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try { ... } range
        start = reviewer_output.find("{")
        end = reviewer_output.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(reviewer_output[start:end + 1])
            except json.JSONDecodeError:
                pass

        # Fallback: match an agent_id from the output
        for aid in agent_ids:
            if aid in reviewer_output:
                logger.info(f"Debate verdict fallback: found agent_id '{aid}' in output")
                return {"winner": aid, "scores": {}, "reasoning": "Fallback from text match"}

        logger.warning("Could not parse reviewer verdict, using first agent")
        return {"winner": agent_ids[0], "scores": {}, "reasoning": "Parse failed — fallback"}
