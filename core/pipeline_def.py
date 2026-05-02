"""PIPELINE 权威定义，db.py 和 orchestrator.py 共用。

支持两种 stage 类型：
- 单 Agent: (status, agent_id, needs_user)
- 多 Agent: (status, None, needs_user) + MULTI_AGENT_CONFIG 注册
"""

from typing import Any, Dict, Optional, Tuple

# (status, agent_id, needs_user)
# agent_id 为 None 时，检查 MULTI_AGENT_CONFIG 是否为多 agent stage
PIPELINE: list[Tuple[str, Optional[str], bool]] = [
    ("input_collecting", "input_collector", True),
    ("requirement_optimizing", "requirement_optimizer", False),
    ("confirmation", None, True),
    ("planning", "planner", False),
    ("prompt_optimizing", None, False),  # Multi-agent DEBATE
    ("executing", None, False),          # Multi-agent PARALLEL (with fallback)
    ("verifying", "verifier", False),
    ("archiving", "archivist", False),
]

PIPELINE_STEPS: list[str] = [s for s, _, _ in PIPELINE]

# Multi-agent stage configuration — lazy-imported by orchestrator.
# Keys must match step names in PIPELINE whose agent_id is None.
# Populated by core.multi_agent.MULTI_AGENT_STAGES.
MULTI_AGENT_CONFIG: Dict[str, Any] = {}