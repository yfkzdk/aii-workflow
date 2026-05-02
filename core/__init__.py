"""core -- v3 瘦身架构 for 上下文助手

提供：
- StateDB: SQLite WAL 状态存储
- Orchestrator: Python 编排器，外层驱动管线（v0.6 支持多 Agent 协作）
- AgentCaller: Agent 调用器（SDK + subprocess fallback）
- MultiAgentStage / AgentRole: 多 Agent 协作角色与策略定义
- DebateEngine: 辩论策略（N agent → reviewer 选最优）
- ParallelExecutor: 并行执行策略
"""

from core.db import StateDB
from core.orchestrator import Orchestrator
from core.agent_caller import AgentCaller
from core.multi_agent import (
    AgentRole,
    MultiAgentStage,
    MultiAgentStrategy,
    MULTI_AGENT_STAGES,
)
from core.debate_engine import DebateEngine
from core.parallel_executor import ParallelExecutor

__all__ = [
    "StateDB",
    "Orchestrator",
    "AgentCaller",
    "AgentRole",
    "MultiAgentStage",
    "MultiAgentStrategy",
    "MULTI_AGENT_STAGES",
    "DebateEngine",
    "ParallelExecutor",
]