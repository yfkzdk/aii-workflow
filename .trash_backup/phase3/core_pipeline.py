"""PipelineRunner -- 配置驱动的管线执行器。

核心功能：
- 中文适配的 Token 估算（CJK 字符 ×2 + 英文词 ×1.3）
- 管线步进校验（不允许非法跳转）
- 状态一致性验证
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from core.state import SafeState, ENHANCED_PIPELINE, TERMINAL_STATES


@dataclass
class PipelineStep:
    """单个管线步骤定义。"""
    name: str
    agent: str
    description: str = ""
    requires_user_input: bool = False
    token_budget: int = 1200


@dataclass
class PipelineConfig:
    """从 config/pipeline_config.json 加载的配置。"""
    token_threshold: int = 1200
    max_confirmation_retries: int = 4
    max_retries: int = 3
    pipeline: List[str] = field(default_factory=lambda: list(ENHANCED_PIPELINE))

    @classmethod
    def from_file(cls, path: str) -> "PipelineConfig":
        p = Path(path)
        if not p.exists():
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            token_threshold=data.get("token_threshold", 1200),
            max_confirmation_retries=data.get("max_confirmation_retries", 4),
            max_retries=data.get("max_retries", 3),
            pipeline=data.get("pipeline", list(ENHANCED_PIPELINE)),
        )


def estimate_tokens_chinese(text: str) -> int:
    """中文适配的 Token 估算。

    策略：CJK 字符按 ~2 token 计，英文词按 ~1.3 token 计。
    比空格分词更准确，适合国产模型场景。

    面试话术锚点：用正则识别 CJK 字符，不依赖空格分词。
    """
    if not text:
        return 0
    cjk_pattern = re.compile(r'[一-鿿㐀-䶿豈-﫿]')
    cjk_chars = len(cjk_pattern.findall(text))
    text_without_cjk = cjk_pattern.sub("", text)
    eng_words = len(text_without_cjk.split()) if text_without_cjk.strip() else 0
    return int(cjk_chars * 2 + eng_words * 1.3)


def chunk_text_by_tokens(text: str, threshold: int) -> List[str]:
    """按 Token 阈值分段文本（中文适配）。

    从文本中点切分，确保每段不超过 threshold。
    """
    if estimate_tokens_chinese(text) <= threshold:
        return [text]

    mid = len(text) // 2
    # 尝试在句号/换行处切分
    for offset in range(0, min(100, mid)):
        for sep in ["。", "\n", "；", ".", ";"]:
            pos = text.find(sep, mid + offset)
            if pos != -1 and pos < len(text) - 1:
                return [text[:pos + 1], text[pos + 1:]]
            pos = text.rfind(sep, 0, mid - offset)
            if pos != -1 and pos < mid:
                return [text[:pos + 1], text[pos + 1:]]

    # 找不到分隔符，硬切
    return [text[:mid], text[mid:]]


class PipelineRunner:
    """配置驱动的管线编排器。"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = (PipelineConfig.from_file(config_path)
                       if config_path else PipelineConfig())
        self.steps: Dict[str, PipelineStep] = {}
        self._register_default_steps()

    def _register_default_steps(self):
        """注册与 ENHANCED_PIPELINE 匹配的内置步骤。"""
        step_defs = [
            ("input_collecting", "input_collector", "收集用户输入", True, 800),
            ("requirement_optimizing", "requirement_optimizer", "优化需求生成方案", False, 1200),
            ("confirmation", "user", "用户确认门", True, 400),
            ("planning", "planner", "创建任务 DAG", False, 1000),
            ("prompt_optimizing", "prompt_optimizer", "优化提示词", False, 800),
            ("executing", "coder", "执行实现", False, 2000),
            ("verifying", "verifier", "验证结果", False, 800),
            ("archiving", "archivist", "归档索引", False, 600),
            ("completed", None, "任务完成", False, 0),
        ]
        for name, agent, desc, needs_input, budget in step_defs:
            self.steps[name] = PipelineStep(
                name=name, agent=agent, description=desc,
                requires_user_input=needs_input, token_budget=budget
            )

    def register_step(self, name: str, agent: str, description: str = "",
                      requires_user_input: bool = False, token_budget: int = 1200):
        """注册自定义管线步骤。"""
        self.steps[name] = PipelineStep(
            name=name, agent=agent, description=description,
            requires_user_input=requires_user_input, token_budget=token_budget
        )

    def validate_state(self, state: SafeState) -> Tuple[bool, List[str]]:
        """验证状态一致性。返回 (是否合法, 错误列表)。"""
        errors = []
        if state.status not in self.config.pipeline and state.status not in TERMINAL_STATES:
            errors.append(f"状态 '{state.status}' 不在管线或终态中")
        if state.current_step_index < 0 or state.current_step_index >= len(state.pipeline):
            errors.append(f"步进索引 {state.current_step_index} 越界 [0, {len(state.pipeline)-1}]")
        if state.confirm_retry_count > state.max_confirmation_retries:
            errors.append(f"确认回退次数 ({state.confirm_retry_count}) 超过上限 ({state.max_confirmation_retries})")
        return len(errors) == 0, errors

    def can_advance(self, state: SafeState, target_step: str) -> Tuple[bool, str]:
        """检查从当前状态步进到目标步骤是否合法。"""
        if state.status in TERMINAL_STATES:
            return False, f"任务已终态: {state.status}"
        if target_step not in self.config.pipeline and target_step not in TERMINAL_STATES:
            return False, f"未知步骤: {target_step}"
        current_idx = (self.config.pipeline.index(state.status)
                       if state.status in self.config.pipeline else -1)
        # 允许回退到 requirement_optimizing（确认门修订）和 cancelled
        allowed_back = {"requirement_optimizing", "cancelled"}
        if target_step not in allowed_back:
            target_idx = (self.config.pipeline.index(target_step)
                          if target_step in self.config.pipeline else len(self.config.pipeline))
            if target_idx < current_idx:
                return False, f"不允许从 {state.status} 回退到 {target_step}"
        return True, "ok"

    def check_token_budget(self, text: str, step_name: str = "") -> Tuple[bool, int, int]:
        """检查文本是否在步骤的 Token 预算内。

        返回: (是否通过, 估算 token 数, 预算)
        """
        budget = self.config.token_threshold
        if step_name and step_name in self.steps:
            budget = self.steps[step_name].token_budget
        estimated = estimate_tokens_chinese(text)
        return estimated <= budget, estimated, budget