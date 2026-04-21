"""PIPELINE 权威定义，db.py 和 orchestrator.py 共用。"""

from typing import Optional, Tuple

# (status, agent_id, needs_user)
PIPELINE: list[Tuple[str, Optional[str], bool]] = [
    ("input_collecting", "input_collector", True),
    ("requirement_optimizing", "requirement_optimizer", False),
    ("confirmation", None, True),
    ("planning", "planner", False),
    ("prompt_optimizing", "prompt_optimizer", False),
    ("executing", "coder", False),
    ("verifying", "verifier", False),
    ("archiving", "archivist", False),
]

PIPELINE_STEPS: list[str] = [s for s, _, _ in PIPELINE]