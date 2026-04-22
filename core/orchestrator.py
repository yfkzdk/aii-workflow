"""Orchestrator -- 编排器核心，Python 驱动管线，LLM 只做推理。

阶段三升级：
- Tool Use 审批：agent 返回 transition_state 请求，编排器验证后决定
- Token 监控：每次 agent 调用后累加到 db，超限警告
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.db import StateDB
from core.agent_caller import AgentCaller
from core.pipeline_def import PIPELINE, PIPELINE_STEPS
from core.quality_gates import QualityGateRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validator import validate_step

TOKEN_WARNING_THRESHOLD = 50000


class Orchestrator:
    """Python 编排器，外层驱动管线流转。

    阶段二新增：验证、重试、质量门。
    """

    def __init__(self, task_dir: str, task_id: str,
                 project_root: str = ".",
                 max_retries: int = 3) -> None:
        self.task_id = task_id
        self.task_dir = task_dir
        self.db = StateDB(task_dir)
        self.caller = AgentCaller.create(project_root)
        self.gate_runner = QualityGateRunner()
        self.max_retries = max_retries

        # 阶段二状态
        self._last_validation: Tuple[bool, str] = (True, "")
        self._last_gate_result: Dict[str, Any] = {"approved": True, "results": []}
        self._force_fail_step: Optional[str] = None

        # 阶段三：token 监控
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0

    # ---- 阶段二公开查询接口 ----

    def get_validation_status(self) -> Tuple[bool, str]:
        """返回最近一次验证结果 (passed, message)。"""
        return self._last_validation

    def get_retry_count(self) -> int:
        """从 DB 返回当前重试次数。"""
        return self.db.get_state(self.task_id).get("retry_count", 0)

    def force_fail_step(self, step_name: str) -> None:
        """用于测试：强制指定步骤验证失败。"""
        self._force_fail_step = step_name

    # ---- 主循环 ----

    def run(self) -> Dict[str, Any]:
        """遍历 PIPELINE，自动执行 needs_user=False 的阶段。

        阶段三升级：
        - agent 返回 tool_calls 时走 Tool Use 审批流程
        - 每次 agent 调用后累加 token 用量到 db
        """
        state = self.db.get_state(self.task_id)
        current_status = state["status"]

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
                print(f"[Orchestrator] 暂停于 {status}，等待用户输入")
                return {
                    "status": status,
                    "waiting_for": "user_input" if agent_id else "confirmation",
                    "step_index": stage_index,
                }

            # 自动阶段 → 调用 agent
            if agent_id is not None:
                self.db.save_snapshot(self.task_id, label=f"before_{status}")
                context = self._build_context(state)
                result = self.caller.call(agent_id, str(self.db.task_dir), context)

                # 阶段三：累加 token 用量
                self._record_token_usage(result.get("usage", {}))

                if not result["success"]:
                    retry = self.db.increment_retry(self.task_id)
                    if retry >= self.max_retries:
                        self.db.update_status(self.task_id, "failed")
                        print(f"[Orchestrator] Agent 调用失败，重试耗尽: {self.task_id}")
                        return {"status": "failed", "error": result["error"]}
                    print(f"[Orchestrator] Agent 失败，重试 {retry}/{self.max_retries}")
                    # 不推进 idx，重试当前阶段
                    continue

                # 阶段三：处理 Tool Use 审批
                tool_calls = result.get("tool_calls", [])
                if tool_calls:
                    approved = self._handle_tool_calls(status, tool_calls)
                    if not approved:
                        # 审批拒绝，验证失败，走重试
                        retry_count = self.db.get_state(self.task_id).get("retry_count", 0)
                        if retry_count >= self.max_retries:
                            self.db.update_status(self.task_id, "failed")
                            print(f"[Orchestrator] Tool Use 审批重试耗尽: {self.task_id}")
                            return {"status": "failed", "step": status}
                        state = self.db.get_state(self.task_id)
                        continue
                    # 审批通过，执行质量门检查
                    gate_result = self.gate_runner.run_gates(
                        Path(self.task_dir), status
                    )
                    self._last_gate_result = gate_result
                    if not gate_result["approved"]:
                        self._handle_gate_failure(status, gate_result)
                        retry_count = self.db.get_state(self.task_id).get("retry_count", 0)
                        if retry_count >= self.max_retries:
                            self.db.update_status(self.task_id, "failed")
                            print(f"[Orchestrator] 质量门重试耗尽，任务失败: {self.task_id}")
                            return {"status": "failed", "step": status, "gate": gate_result}
                        state = self.db.get_state(self.task_id)
                        current_status = state["status"]
                        continue
                    state = self.db.get_state(self.task_id)
                    # 质量门通过，推进到下一阶段
                    idx += 1
                    continue

            # --- 阶段二：验证步骤输出（纯文本输出路径） ---
            passed, msg = self._validate_step(status)
            self._last_validation = (passed, msg)

            if not passed:
                self._handle_validation_failure(status, msg)
                retry_count = self.db.get_state(self.task_id).get("retry_count", 0)
                if retry_count >= self.max_retries:
                    self.db.update_status(self.task_id, "failed")
                    print(f"[Orchestrator] 验证重试耗尽，任务失败: {self.task_id}")
                    return {"status": "failed", "step": status, "error": msg}
                # 重新获取 state（回退后状态已变）
                state = self.db.get_state(self.task_id)
                current_status = state["status"]
                # 如果回退了阶段，idx 也要回退到对应位置
                if current_status in PIPELINE_STEPS:
                    new_idx = PIPELINE_STEPS.index(current_status)
                    if new_idx < stage_index:
                        idx = new_idx
                        continue
                continue

            # 验证通过，重置重试计数
            self.db.reset_retry_count(self.task_id)

            # --- 阶段二：质量门检查 ---
            gate_result = self.gate_runner.run_gates(
                Path(self.task_dir), status
            )
            self._last_gate_result = gate_result

            if not gate_result["approved"]:
                self._handle_gate_failure(status, gate_result)
                retry_count = self.db.get_state(self.task_id).get("retry_count", 0)
                if retry_count >= self.max_retries:
                    self.db.update_status(self.task_id, "failed")
                    print(f"[Orchestrator] 质量门重试耗尽，任务失败: {self.task_id}")
                    return {"status": "failed", "step": status, "gate": gate_result}
                state = self.db.get_state(self.task_id)
                current_status = state["status"]
                # 如果回退了阶段，idx 也要回退
                if current_status in PIPELINE_STEPS:
                    new_idx = PIPELINE_STEPS.index(current_status)
                    if new_idx < stage_index:
                        idx = new_idx
                        continue
                continue

            # 推进到下一阶段
            next_idx = stage_index + 1
            if next_idx < len(PIPELINE):
                next_status, next_agent, _ = PIPELINE[next_idx]
                self.db.update_status(self.task_id, next_status, next_agent)
                print(f"[Orchestrator] {status} → {next_status} | Agent: {next_agent}")
            else:
                self.db.update_status(self.task_id, "archiving")
                print(f"[Orchestrator] {status} → archiving (最终阶段)")

            state = self.db.get_state(self.task_id)
            idx += 1

        return {"status": "archiving", "step_index": len(PIPELINE) - 1}

    # ---- 阶段二：验证与回退 ----

    def _validate_step(self, step: str) -> Tuple[bool, str]:
        """执行步骤验证，支持 force_fail_step 测试钩子。"""
        if self._force_fail_step == step:
            return False, f"强制失败: {step}"
        return validate_step(Path(self.task_dir), step)

    def _handle_validation_failure(self, step: str, msg: str) -> None:
        """处理验证失败：回退步骤、增加重试、写反馈文件。"""
        retry = self.db.increment_retry(self.task_id)

        # 写入 retry_feedback.json
        feedback_path = Path(self.task_dir) / "artifacts" / "retry_feedback.json"
        feedback_path.parent.mkdir(parents=True, exist_ok=True)
        feedback = {
            "step": step, "error": msg,
            "retry_count": retry,
        }
        feedback_path.write_text(
            json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 回退逻辑
        if step == "verifying":
            self.db.update_status(self.task_id, "executing", "coder")
            print(f"[Orchestrator] verifying 验证失败 → 回退到 executing")
        elif step == "executing":
            self.db.update_status(self.task_id, "prompt_optimizing", "prompt_optimizer")
            print(f"[Orchestrator] executing 验证失败 → 回退到 prompt_optimizing")
        else:
            print(f"[Orchestrator] {step} 验证失败 → 保持当前步骤重试")

    def _handle_gate_failure(self, step: str,
                             gate_result: Dict[str, Any]) -> None:
        """处理质量门失败：retry → 回退+重试，warn/log → 记录继续。"""
        for r in gate_result["results"]:
            if r.get("passed") is False and r["action"] == "retry":
                self.db.increment_retry(self.task_id)
                step_idx = PIPELINE_STEPS.index(step) if step in PIPELINE_STEPS else -1
                if step_idx > 0:
                    prev_step = PIPELINE_STEPS[step_idx - 1]
                    prev_agent = dict((s, a) for s, a, _ in PIPELINE).get(prev_step)
                    self.db.update_status(self.task_id, prev_step, prev_agent)
                    print(f"[Orchestrator] 质量门 retry → 回退到 {prev_step}")
                break
            elif r.get("passed") is False and r["action"] in ("warn", "log"):
                action_verb = "警告" if r["action"] == "warn" else "日志"
                print(f"[Orchestrator] 质量门 {r['action']}: {r['skill']} — {action_verb}")

    # ---- 手动推进 ----

    def advance(self) -> Dict[str, Any]:
        """推进到下一阶段。"""
        state = self.db.get_state(self.task_id)
        current_status = state["status"]

        current_idx = None
        for i, (s, _, _) in enumerate(PIPELINE):
            if s == current_status:
                current_idx = i
                break

        if current_idx is None:
            return {"status": "error", "error": f"未知状态: {current_status}"}

        if current_idx + 1 >= len(PIPELINE):
            return {"status": "completed", "message": "已是最终阶段"}

        self.db.save_snapshot(self.task_id, label=f"before_advance_{current_status}")
        next_status, next_agent, _ = PIPELINE[current_idx + 1]
        self.db.update_status(self.task_id, next_status, next_agent)
        print(f"[Orchestrator] {current_status} → {next_status} | Agent: {next_agent}")
        return self.db.get_state(self.task_id)

    # ---- 用户交互 ----

    def handle_user_input(self, content: str) -> Dict[str, Any]:
        """追加用户输入到 db（结构化chunk，含seq编号）。"""
        state = self.db.get_state(self.task_id)
        user_input: Dict[str, Any] = json.loads(state.get("user_input_json", "{}"))
        chunks: list = user_input.get("chunks", [])
        chunks.append({"seq": len(chunks), "content": content})
        user_input["chunks"] = chunks

        self.db.set_user_input(self.task_id, json.dumps(user_input, ensure_ascii=False))
        print(f"[Orchestrator] 用户输入已追加: {self.task_id}")
        return self.db.get_state(self.task_id)

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
            print(f"[Orchestrator] confirmation → planning | Agent: planner")
            return {"result": "confirmed", "next": "planning"}

        elif action == "revise":
            self.db.update_status(self.task_id, "requirement_optimizing",
                                  "requirement_optimizer")
            print(f"[Orchestrator] confirmation → requirement_optimizing | Agent: requirement_optimizer")
            return {"result": "revised", "next": "requirement_optimizing"}

        elif action == "reject":
            self.db.update_status(self.task_id, "cancelled")
            print(f"[Orchestrator] confirmation → cancelled")
            return {"result": "cancelled", "next": "cancelled"}

        return {"result": "error", "error": f"未知操作: {action}"}

    # ---- 阶段三：Tool Use 审批 ----

    def _handle_tool_calls(self, current_step: str,
                           tool_calls: List[Dict[str, Any]]) -> bool:
        """处理 agent 返回的 tool_calls，验证后决定是否批准。

        返回 True 表示全部通过，False 表示有拒绝。
        """
        for tc in tool_calls:
            if tc.get("name") != "transition_state":
                print(f"[Orchestrator] 忽略未知 tool: {tc.get('name')}")
                continue

            approved = self._handle_tool_call(current_step, tc)
            if not approved:
                return False
        return True

    def _handle_tool_call(self, current_step: str,
                          tool_call: Dict[str, Any]) -> bool:
        """处理单个 transition_state tool call。

        合法转换 → 验证输出 → 批准
        非法转换（跳步） → 拒绝
        """
        inp = tool_call.get("input", {})
        next_step = inp.get("next_step", "")
        summary = inp.get("output_summary", "")
        errors = inp.get("errors", [])

        # 检查是否合法转换（不跳步）
        if next_step not in PIPELINE_STEPS:
            print(f"[Orchestrator] Tool Use 拒绝: 未知步骤 '{next_step}'")
            self._feedback_to_agent(current_step,
                                    f"非法步骤 '{next_step}'，可选: {PIPELINE_STEPS}")
            return False

        current_idx = PIPELINE_STEPS.index(current_step)
        target_idx = PIPELINE_STEPS.index(next_step)

        if target_idx > current_idx + 1:
            print(f"[Orchestrator] Tool Use 拒绝: 跳步 "
                  f"{current_step}({current_idx}) → {next_step}({target_idx})")
            self._feedback_to_agent(current_step,
                                    f"不允许从 {current_step} 跳到 {next_step}，"
                                    f"只能推进到下一步")
            return False

        # 合法转换 → 验证当前步骤输出
        passed, msg = self._validate_step(current_step)
        self._last_validation = (passed, msg)

        if not passed:
            print(f"[Orchestrator] Tool Use 验证失败: {msg}")
            self._feedback_to_agent(current_step, f"验证失败: {msg}")
            self._handle_validation_failure(current_step, msg)
            return False

        # 验证通过 → 批准转换
        target_agent = dict((s, a) for s, a, _ in PIPELINE).get(next_step)
        self.db.update_status(self.task_id, next_step, target_agent)
        print(f"[Orchestrator] Tool Use 批准: {current_step} → {next_step} "
              f"| summary: {summary[:80]}")
        return True

    def _feedback_to_agent(self, step: str, error_msg: str) -> None:
        """构造反馈文件，供下次 agent 调用使用。"""
        feedback_path = Path(self.task_dir) / "artifacts" / "retry_feedback.json"
        feedback_path.parent.mkdir(parents=True, exist_ok=True)
        feedback = {
            "step": step, "error": error_msg,
            "retry_count": self.db.get_state(self.task_id).get("retry_count", 0) + 1,
            "type": "tool_use_rejection",
        }
        feedback_path.write_text(
            json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---- 阶段三：Token 监控 ----

    def _record_token_usage(self, usage: Dict[str, Any]) -> None:
        """记录 agent 调用的 token 用量到 db。"""
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cache_hits = usage.get("cache_read_input_tokens", 0)

        if input_tokens == 0 and output_tokens == 0:
            return  # 无 token 数据（FallbackCaller 不追踪）

        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self.db.add_token_usage(self.task_id, input_tokens, output_tokens,
                                cache_hits)

        if self._total_input_tokens > TOKEN_WARNING_THRESHOLD:
            print(f"[Orchestrator] WARNING Token 超限: 总输入 {self._total_input_tokens} "
                  f"超过 {TOKEN_WARNING_THRESHOLD}")

    # ---- 内部工具 ----

    def _build_context(self, state: Dict[str, Any]) -> str:
        """构建传给 agent 的任务上下文文本。"""
        parts = [f"## 任务状态\n- status: {state['status']}\n- step: {state['step_index']}"]

        user_input = json.loads(state.get("user_input_json", "{}"))
        chunks = user_input.get("chunks", [])
        if chunks:
            # 兼容两种格式：字典列表 {"seq":N,"content":"..."} 或字符串列表
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

        return "\n\n".join(parts)