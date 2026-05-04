"""Orchestrator -- 编排器核心，Python 驱动管线，LLM 只做推理。

Web 模式适配：
- LLM 输出自动持久化到产物文件
- 错误信息写入 DB
- 前序产物作为上下文传递给后续 agent

v0.6: 多 Agent 协作 — DEBATE / PARALLEL / SPECIALIST_ROUTER
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.db import StateDB
from core.agent_caller import AgentCaller
from core.pipeline_def import PIPELINE, PIPELINE_STEPS
from core.multi_agent import MultiAgentStage, MultiAgentStrategy, MULTI_AGENT_STAGES
from core.debate_engine import DebateEngine
from core.parallel_executor import ParallelExecutor
from scripts.validator import validate_step

logger = logging.getLogger("orchestrator")

TOKEN_WARNING_THRESHOLD = 50000

# 步骤 → 产物文件映射（Web 模式下 LLM 输出需持久化到这些路径）
STEP_ARTIFACT_MAP = {
    "requirement_optimizing": "artifacts/optimized_requirement.json",
    "planning": "artifacts/requirements.md",
    "prompt_optimizing": "artifacts/optimal_prompt.md",
    "executing": "artifacts/code/main.py",
    "verifying": "artifacts/test_report.json",
    "archiving": "AI_WORKFLOW_LOG.md",
}

# 多 Agent 阶段的额外产物映射（debate 产生多个中间文件）
MULTI_AGENT_ARTIFACTS = {
    "prompt_optimizing": [
        "artifacts/optimal_prompt_v2.md",
        "artifacts/optimal_prompt_v3.md",
        "artifacts/debate_verdict.json",
    ],
}


class Orchestrator:
    """Python 编排器，外层驱动管线流转。"""

    def __init__(self, task_dir: str, task_id: str,
                 project_root: str = ".",
                 max_retries: int = 3) -> None:
        self.task_id = task_id
        self.task_dir = task_dir
        self.db = StateDB(task_dir)
        self.caller = AgentCaller.create(project_root)
        self.max_retries = max_retries
        self._force_fail_steps: set = set()

        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0

    # ---- 主循环 ----

    def run(self) -> Dict[str, Any]:
        """遍历 PIPELINE，自动执行 needs_user=False 的阶段。

        返回值区分三种情况：
        - {"status": "completed"} — 全部完成
        - {"status": "confirmation", "waiting_for": "confirmation"} — 暂停等待确认
        - {"status": "failed", "error": "..."} — 失败
        """
        state = self.db.get_state(self.task_id)

        idx = 0
        while idx < len(PIPELINE):
            status, agent_id, needs_user = PIPELINE[idx]

            # 跳过已完成的阶段
            step_index = state["step_index"]
            stage_index = PIPELINE_STEPS.index(status)
            if stage_index < step_index:
                idx += 1
                continue

            # 需要用户输入的阶段 → 暂停等待
            if needs_user:
                logger.info(f"暂停于 {status}，等待用户输入")
                return {
                    "status": status,
                    "waiting_for": "user_input" if agent_id else "confirmation",
                    "step_index": stage_index,
                }

            # 自动阶段 → 调用 agent（单 agent 或多 agent）
            if agent_id is not None or status in MULTI_AGENT_STAGES:
                self.db.save_snapshot(self.task_id, label=f"before_{status}")
                context = self._build_context(state)

                # 检查是否为多 Agent 阶段
                multi_config = MULTI_AGENT_STAGES.get(status)
                if multi_config is not None:
                    result = self._run_multi_agent_stage(status, multi_config, context)
                else:
                    try:
                        result = self.caller.call(agent_id, str(self.db.task_dir), context)
                    except Exception as exc:
                        logger.exception("Agent 调用异常: %s / %s", agent_id, exc)
                        result = {"success": False, "error": f"Agent 调用异常: {exc}", "usage": {}}

                self._record_token_usage(result.get("usage", {}))

                if not result["success"]:
                    self.db.save_error(self.task_id, result.get("error", "Agent call failed"))
                    retry = self.db.increment_retry(self.task_id)
                    if retry >= self.max_retries:
                        self.db.update_status(self.task_id, "failed")
                        logger.info(f"Agent 调用失败，重试耗尽: {self.task_id}")
                        return {"status": "failed", "error": result["error"]}
                    logger.info(f"Agent 失败，重试 {retry}/{self.max_retries}")
                    continue

                # Web 模式：将 LLM 输出持久化到产物文件
                # PARALLEL 阶段：各 agent 的独立产物已由 _persist_multi_artifacts 保存，
                # 跳过合并输出的持久化（合并输出是拼接摘要，不应覆盖代码文件）
                if result.get("output") and not (
                    multi_config is not None and
                    multi_config.strategy == MultiAgentStrategy.PARALLEL
                ):
                    self._persist_output(status, result["output"])

                # 多 Agent 阶段：持久化额外产物
                if multi_config is not None and result.get("extra_artifacts"):
                    self._persist_multi_artifacts(status, result["extra_artifacts"])

            # 验证步骤输出
            passed, msg = self._validate_step(status)

            if not passed:
                self.db.save_error(self.task_id, msg)
                self._handle_validation_failure(status, msg)
                retry_count = self.db.get_state(self.task_id).get("retry_count", 0)
                if retry_count >= self.max_retries:
                    self.db.update_status(self.task_id, "failed")
                    logger.info(f"验证重试耗尽，任务失败: {self.task_id}")
                    return {"status": "failed", "step": status, "error": msg}
                state = self.db.get_state(self.task_id)
                # 如果回退了阶段，idx 也要回退
                current_status = state["status"]
                if current_status in PIPELINE_STEPS:
                    new_idx = PIPELINE_STEPS.index(current_status)
                    if new_idx < stage_index:
                        idx = new_idx
                        continue
                continue

            # 验证通过，重置重试计数和错误
            self.db.reset_retry_count(self.task_id)
            self.db.save_error(self.task_id, "")

            # 推进到下一阶段
            next_idx = stage_index + 1
            if next_idx < len(PIPELINE):
                next_status, next_agent, _ = PIPELINE[next_idx]
                self.db.update_status(self.task_id, next_status, next_agent)
                logger.info(f"{status} → {next_status} | Agent: {next_agent}")
            else:
                self.db.update_status(self.task_id, "completed")
                logger.info(f"{status} → completed")

            state = self.db.get_state(self.task_id)
            idx += 1

        return {"status": "completed", "step_index": len(PIPELINE) - 1}

    # ---- 多 Agent 阶段 ----

    def _run_multi_agent_stage(self, status: str, config: MultiAgentStage,
                               context: str) -> Dict[str, Any]:
        """Execute a multi-agent pipeline stage based on strategy."""
        logger.info(f"Multi-agent stage: {status} strategy={config.strategy.value} "
                     f"agents={[a.agent_id for a in config.agents]}")

        if config.strategy == MultiAgentStrategy.DEBATE:
            return self._run_debate(status, config, context)

        elif config.strategy == MultiAgentStrategy.PARALLEL:
            return self._run_parallel(status, config, context)

        elif config.strategy == MultiAgentStrategy.SPECIALIST_ROUTER:
            return self._run_specialist_router(status, config, context)

        return {"success": False, "error": f"Unknown strategy: {config.strategy}"}

    def _run_debate(self, status: str, config: MultiAgentStage,
                    context: str) -> Dict[str, Any]:
        """Run debate strategy: N agents → reviewer picks best."""
        engine = DebateEngine(self.caller, str(self.db.task_dir))
        result = engine.run(
            agents=config.agents,
            task_context=context,
            reviewer_agent_id=config.reviewer or "reviewer",
        )

        if not result.get("success"):
            return result

        # Package extra artifacts for persistence
        extra: Dict[str, str] = {}

        all_outputs = result.get("all_outputs", {})
        for agent_role in config.agents:
            aid = agent_role.agent_id
            if aid in all_outputs and agent_role.output_path and \
               agent_role.output_path != "artifacts/optimal_prompt.md":
                extra[agent_role.output_path] = all_outputs[aid]

        # Save debate verdict
        verdict = {
            "winner": result.get("winner"),
            "scores": result.get("scores"),
            "reasoning": result.get("reviewer_reasoning"),
        }
        extra["artifacts/debate_verdict.json"] = json.dumps(
            verdict, ensure_ascii=False, indent=2
        )

        logger.info(f"Debate complete: winner={result.get('winner')} "
                     f"reasoning={verdict.get('reasoning', '')[:80]}")

        return {
            "success": True,
            "output": result["output"],
            "extra_artifacts": extra,
            "usage": {},  # Token usage is tracked per-agent call
        }

    def _run_parallel(self, status: str, config: MultiAgentStage,
                      context: str) -> Dict[str, Any]:
        """Run parallel strategy: all agents execute concurrently."""
        executor = ParallelExecutor(self.caller, str(self.db.task_dir))
        result = executor.run(
            agents=config.agents,
            task_context=context,
            merge_strategy=config.merge_strategy,
        )

        if not result.get("success"):
            return result

        # Package per-agent outputs
        extra: Dict[str, str] = {}
        for agent_role in config.agents:
            aid = agent_role.agent_id
            per_data = result.get("per_agent", {}).get(aid, {})
            if per_data.get("success") and per_data.get("output"):
                if agent_role.output_path:
                    extra[agent_role.output_path] = per_data["output"]

        return {
            "success": True,
            "output": result["output"],
            "extra_artifacts": extra,
            "usage": {},
        }

    def _run_specialist_router(self, status: str, config: MultiAgentStage,
                               context: str) -> Dict[str, Any]:
        """Run specialist router: router agent assigns task to best specialist."""
        router_id = config.router_agent or "requirement_optimizer"

        # Phase 1: Router analyzes task and picks specialist
        route_prompt = self._build_route_prompt(config.agents, context)
        route_result = self.caller.call(router_id, str(self.db.task_dir), route_prompt)

        if not route_result.get("success"):
            return route_result

        # Phase 2: Parse routing decision
        chosen_agent_id = self._parse_routing(route_result.get("output", ""),
                                              [a.agent_id for a in config.agents])
        logger.info(f"Specialist router: task → {chosen_agent_id}")

        # Phase 3: Execute the chosen specialist
        chosen = next(a for a in config.agents if a.agent_id == chosen_agent_id)
        agent_prompt = self._build_specialist_prompt(chosen, context)
        result = self.caller.call(chosen_agent_id, str(self.db.task_dir), agent_prompt)

        return result

    @staticmethod
    def _build_route_prompt(agents: list, context: str) -> str:
        agent_list = "\n".join(
            f"- **{a.agent_id}** ({a.role}): {a.goal} [专长: {', '.join(a.expertise)}]"
            for a in agents
        )
        return (
            f"## 任务背景\n{context}\n\n"
            f"## 可用专家\n{agent_list}\n\n"
            f"## 指令\n分析任务需求，选择最适合的专家 agent_id。"
            f"输出格式: ```json\n{{\"agent_id\": \"<选择的agent_id>\", \"reason\": \"<理由>\"}}\n```"
        )

    @staticmethod
    def _parse_routing(router_output: str, agent_ids: List[str]) -> str:
        try:
            data = json.loads(router_output)
            aid = data.get("agent_id", "")
            if aid in agent_ids:
                return aid
        except json.JSONDecodeError:
            pass
        # Fallback: return first agent_id found in output
        for aid in agent_ids:
            if aid in router_output:
                return aid
        return agent_ids[0]

    @staticmethod
    def _build_specialist_prompt(agent, context: str) -> str:
        return (
            f"## 你的角色\n{agent.role}\n\n"
            f"## 你的目标\n{agent.goal}\n\n"
            f"## 任务背景\n{context}\n\n"
            f"## 指令\n基于你的专长完成此任务，直接输出结果。"
        )

    def _persist_multi_artifacts(self, status: str, extra: Dict[str, str]) -> None:
        """Persist additional artifacts from multi-agent stages."""
        artifact_dir = Path(self.task_dir)
        for rel_path, content in extra.items():
            full_path = artifact_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            logger.info(f"Extra artifact persisted: {rel_path} ({len(content)} 字符)")

    def advance(self) -> Dict[str, Any]:
        """手动推进管线一步。跳过 needs_user 的阶段。"""
        state = self.db.get_state(self.task_id)
        current = state["status"]
        if current == "completed":
            return {"status": "completed", "step_index": len(PIPELINE)}
        if current == "failed":
            return {"status": "failed", "error": state.get("error", "")}

        idx = PIPELINE_STEPS.index(current) if current in PIPELINE_STEPS else -1
        next_idx = idx + 1
        if next_idx >= len(PIPELINE):
            self.db.update_status(self.task_id, "completed")
            return {"status": "completed", "step_index": len(PIPELINE)}

        next_status, next_agent, _ = PIPELINE[next_idx]
        self.db.update_status(self.task_id, next_status, next_agent)
        return self.db.get_state(self.task_id)

    def handle_user_input(self, user_text: str) -> Dict[str, Any]:
        """处理用户输入，追加为结构化 chunk。"""
        state = self.db.get_state(self.task_id)
        user_input = json.loads(state.get("user_input_json", "{}"))
        chunks = user_input.get("chunks", [])
        seq = len(chunks)
        chunks.append({"seq": seq, "content": user_text, "timestamp": datetime.now().isoformat()})
        user_input["chunks"] = chunks
        user_input["is_complete"] = True
        self.db.set_user_input(self.task_id, json.dumps(user_input, ensure_ascii=False))
        return self.db.get_state(self.task_id)

    def force_fail_step(self, step: str) -> None:
        """标记某步骤为强制失败（测试用）。"""
        self._force_fail_steps.add(step)

    def get_retry_count(self) -> int:
        """返回当前重试计数。"""
        state = self.db.get_state(self.task_id)
        return state.get("retry_count", 0)

    def _handle_tool_call(self, current_step: str,
                          tool_call: Dict[str, Any]) -> bool:
        """验证并处理 agent 的 transition_state tool call。

        返回 True 表示批准推进，False 表示拒绝。
        """
        if tool_call.get("name") != "transition_state":
            return False

        inp = tool_call.get("input", {})
        next_step = inp.get("next_step", "")

        if next_step not in PIPELINE_STEPS:
            return False

        current_idx = PIPELINE_STEPS.index(current_step) if current_step in PIPELINE_STEPS else -1
        next_idx = PIPELINE_STEPS.index(next_step)

        # 禁止跳步（只能推进到下一步）
        if next_idx != current_idx + 1:
            return False

        passed, _ = self._validate_step(next_step)
        if not passed:
            return False

        self.db.update_status(self.task_id, next_step, None)
        return True

    # ---- 验证与回退 ----

    def _validate_step(self, step: str) -> Tuple[bool, str]:
        if step in self._force_fail_steps:
            return False, f"强制失败: {step}"
        return validate_step(Path(self.task_dir), step)

    def _handle_validation_failure(self, step: str, msg: str) -> None:
        retry = self.db.increment_retry(self.task_id)

        feedback_path = Path(self.task_dir) / "artifacts" / "retry_feedback.json"
        feedback_path.parent.mkdir(parents=True, exist_ok=True)
        feedback = {"step": step, "error": msg, "retry_count": retry}
        feedback_path.write_text(
            json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        if step == "verifying":
            self.db.update_status(self.task_id, "executing", "coder")
            logger.info(f"verifying 验证失败 → 回退到 executing")
        elif step == "executing":
            self.db.update_status(self.task_id, "prompt_optimizing", "prompt_optimizer")
            logger.info(f"executing 验证失败 → 回退到 prompt_optimizing")
        else:
            logger.info(f"{step} 验证失败 → 保持当前步骤重试")

    # ---- 用户交互 ----

    def handle_confirmation(self, action: str,
                            proposal_id: Optional[str] = None) -> Dict[str, Any]:
        """处理确认门决策。

        confirm  → 推进到 planning
        revise   → 回退到 requirement_optimizing
        reject   → 标记 cancelled
        """
        self.db.save_snapshot(self.task_id, label="before_confirmation")

        if action == "confirm":
            self.db.update_status(self.task_id, "planning", "planner")
            logger.info(f"confirmation → planning | Agent: planner")
            return {"result": "confirmed", "next": "planning"}

        elif action == "revise":
            self.db.update_status(self.task_id, "requirement_optimizing",
                                  "requirement_optimizer")
            logger.info(f"confirmation → requirement_optimizing | Agent: requirement_optimizer")
            return {"result": "revised", "next": "requirement_optimizing"}

        elif action == "reject":
            self.db.update_status(self.task_id, "cancelled")
            logger.info(f"confirmation → cancelled")
            return {"result": "cancelled", "next": "cancelled"}

        return {"result": "error", "error": f"未知操作: {action}"}

    # ---- Token 监控 ----

    def _record_token_usage(self, usage: Dict[str, Any]) -> None:
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cache_hits = usage.get("cache_read_input_tokens", 0)

        if input_tokens == 0 and output_tokens == 0:
            return

        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self.db.add_token_usage(self.task_id, input_tokens, output_tokens, cache_hits)

        if self._total_input_tokens > TOKEN_WARNING_THRESHOLD:
            logger.warning(f"Token 超限: 总输入 {self._total_input_tokens}")

    # ---- 产物持久化 ----

    def _persist_output(self, step: str, output: str) -> None:
        """将 LLM 输出持久化到产物文件（Web 模式必需）。"""
        artifact_rel = STEP_ARTIFACT_MAP.get(step)
        if not artifact_rel:
            return

        artifact_path = Path(self.task_dir) / artifact_rel
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        content = output.strip()

        if artifact_rel.endswith(".json"):
            extracted = self._extract_json(content)
            if extracted:
                content = json.dumps(extracted, ensure_ascii=False, indent=2)
            else:
                logger.warning(f"步骤 {step} 的 LLM 输出无法提取有效 JSON，原样写入")
        else:
            content = self._strip_code_fences(content)

            # 对 .py 文件做额外检查：确保内容是 Python
            if artifact_rel.endswith(".py") and not self._looks_like_python(content):
                # 尝试从所有代码块中找到 Python 块
                blocks = re.findall(r"```(\w+)?\s*\n(.*?)\n```", output, re.DOTALL)
                for lang, block in blocks:
                    if lang in ("python", "py", "") and self._looks_like_python(block):
                        content = block.strip()
                        break
                else:
                    logger.warning(f"步骤 {step} 的 LLM 输出不像 Python 代码，原样写入")

        artifact_path.write_text(content, encoding="utf-8")
        logger.info(f"产物已持久化: {artifact_rel} ({len(content)} 字符)")

    @staticmethod
    def _extract_json(text: str) -> Optional[Any]:
        # 尝试提取 ```json ... ``` 代码块
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试 { ... } 范围
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """剥离所有 markdown 代码块，返回最后一个（通常是实际代码）。"""
        blocks = re.findall(r"```(?:\w+)?\s*\n(.*?)\n```", text, re.DOTALL)
        if blocks:
            return blocks[-1].strip()
        return text

    @staticmethod
    def _looks_like_python(text: str) -> bool:
        """快速检查文本是否像 Python 代码。"""
        text = text.strip()
        if not text:
            return False
        # 常见 Python 关键字/模式
        python_indicators = [
            "import ", "from ", "def ", "class ", "if __name__",
            "print(", "return ", "async def", "with open",
        ]
        return any(ind in text for ind in python_indicators)

    # ---- 上下文构建 ----

    def _build_context(self, state: Dict[str, Any]) -> str:
        """构建传给 agent 的任务上下文文本，包含前序产物。"""
        parts = [f"## 任务状态\n- status: {state['status']}\n- step: {state['step_index']}"]

        user_input = json.loads(state.get("user_input_json", "{}"))
        chunks = user_input.get("chunks", [])
        if chunks:
            chunk_texts = []
            for c in chunks:
                if isinstance(c, dict):
                    chunk_texts.append(c.get("content", ""))
                else:
                    chunk_texts.append(str(c))
            parts.append("## 用户输入\n" + "\n".join(chunk_texts))

        confirmation = json.loads(state.get("confirmation_json", "{}"))
        if confirmation.get("status") and confirmation["status"] != "pending":
            parts.append(f"## 确认状态\n- status: {confirmation['status']}")

        # 包含前序阶段的产物内容
        current_step = state.get("status", "")
        if current_step not in PIPELINE_STEPS:
            return "\n\n".join(parts)

        current_idx = PIPELINE_STEPS.index(current_step)
        artifacts_dir = Path(self.task_dir) / "artifacts"
        artifact_map = [
            ("requirement_optimizing", artifacts_dir / "optimized_requirement.json"),
            ("planning", artifacts_dir / "requirements.md"),
            ("prompt_optimizing", artifacts_dir / "optimal_prompt.md"),
        ]
        for step_name, fpath in artifact_map:
            step_idx = PIPELINE_STEPS.index(step_name)
            if step_idx < current_idx and fpath.exists():
                try:
                    content = fpath.read_text(encoding="utf-8")
                    if len(content) > 2000:
                        content = content[:2000] + "\n... (已截断)"
                    parts.append(f"## 前序产物: {fpath.name}\n{content}")
                except Exception:
                    pass

        # verifying / archiving 阶段：注入代码文件内容，让 agent 能真正审查代码
        code_dir = artifacts_dir / "code"
        verify_stage_idx = PIPELINE_STEPS.index("verifying")
        if current_idx >= verify_stage_idx and code_dir.exists():
            py_files = list(code_dir.glob("*.py"))
            if py_files:
                parts.append(f"## 已生成代码文件\n" + ", ".join(f.name for f in py_files))
                # 注入文件内容（每个文件最多 3000 字符）
                for py_file in py_files:
                    try:
                        code_content = py_file.read_text(encoding="utf-8")
                        if len(code_content) > 3000:
                            code_content = code_content[:3000] + "\n# ... (已截断)"
                        parts.append(f"### {py_file.name}\n```python\n{code_content}\n```")
                    except Exception:
                        parts.append(f"### {py_file.name}\n(无法读取)")

        return "\n\n".join(parts)