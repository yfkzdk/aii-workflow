"""Multi-agent collaboration strategies for pipeline stages.

Inspired by patterns from:
- AutoGen (GroupChat): agent-to-agent communication via shared context
- CrewAI (AgentRole): role/goal/expertise-based agent identity
- LangGraph (StateGraph): parallel nodes with conditional routing

Strategies:
  DEBATE: N agents generate independently → reviewer picks best output
  PARALLEL: N agents run concurrently on sub-tasks → outputs merged
  SPECIALIST_ROUTER: Router assigns task to best-matching specialist
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MultiAgentStrategy(Enum):
    DEBATE = "debate"
    PARALLEL = "parallel"
    SPECIALIST_ROUTER = "specialist_router"


@dataclass
class AgentRole:
    """Defines an agent's identity — role, goal, expertise — for multi-agent stages.

    Mirrors CrewAI's Agent model: role + goal + backstory → focused behavior.
    """
    agent_id: str
    role: str
    goal: str
    expertise: List[str] = field(default_factory=list)
    output_path: str = ""  # relative path within task_dir/artifacts/
    input_hint: str = ""   # what part of the task this agent focuses on


@dataclass
class MultiAgentStage:
    """Configuration for a pipeline stage that uses multiple agents."""
    stage_name: str
    strategy: MultiAgentStrategy
    agents: List[AgentRole]
    reviewer: Optional[str] = None       # agent_id of reviewer (DEBATE)
    merge_strategy: str = "concat"       # "concat" | "pick_best" | "merge_by_file"
    router_agent: Optional[str] = None   # agent_id of router (SPECIALIST_ROUTER)


# Mapping from pipeline stage → multi-agent config (None = single agent)
# Defined here and referenced by pipeline_def.py to avoid circular imports.
MULTI_AGENT_STAGES: Dict[str, MultiAgentStage] = {
    "prompt_optimizing": MultiAgentStage(
        stage_name="prompt_optimizing",
        strategy=MultiAgentStrategy.DEBATE,
        agents=[
            AgentRole(
                agent_id="prompt_optimizer",
                role="通用提示词优化师",
                goal="生成平衡简洁性与完整性的通用代码生成提示词",
                expertise=["prompt engineering", "code generation", "general purpose"],
                output_path="artifacts/optimal_prompt.md",
            ),
            AgentRole(
                agent_id="prompt_optimizer_v2",
                role="激进提示词优化师",
                goal="用创造性和非传统结构生成高创新性提示词",
                expertise=["creative prompting", "chain-of-thought", "few-shot"],
                output_path="artifacts/optimal_prompt_v2.md",
            ),
            AgentRole(
                agent_id="prompt_optimizer_v3",
                role="安全保守型提示词优化师",
                goal="强调边界条件、错误处理和输入验证的安全提示词",
                expertise=["defensive programming", "edge cases", "validation"],
                output_path="artifacts/optimal_prompt_v3.md",
            ),
        ],
        reviewer="reviewer",
        merge_strategy="pick_best",
    ),
    "executing": MultiAgentStage(
        stage_name="executing",
        strategy=MultiAgentStrategy.PARALLEL,
        agents=[
            AgentRole(
                agent_id="coder",
                role="全栈开发工程师",
                goal="生成核心业务逻辑代码",
                expertise=["python", "algorithms", "backend"],
                output_path="artifacts/code/main.py",
                input_hint="实现核心业务逻辑",
            ),
            AgentRole(
                agent_id="coder_tests",
                role="测试工程师",
                goal="为需求中描述的功能生成完整的 pytest 单元测试",
                expertise=["pytest", "unit testing", "edge cases", "error handling"],
                output_path="artifacts/code/test_main.py",
                input_hint="基于需求规格编写测试，不依赖具体实现细节。覆盖正常路径、边界条件和异常处理。",
            ),
        ],
        merge_strategy="concat",
    ),
}
