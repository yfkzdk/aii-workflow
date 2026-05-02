# AI Agent 协作引擎 — 多模型工作流编排与容错系统

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57?logo=sqlite)](https://sqlite.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://docker.com)
[![Tests](https://img.shields.io/badge/tests-96%20passed-brightgreen)]()
[![Version](https://img.shields.io/badge/version-0.6.0-blue)]()

从零设计的 AI Agent 编排系统，研究多 Agent 协作行为与失效模式。8 阶段确定性管线，3 种多 Agent 协作策略，事件溯源状态机 + Saga 补偿事务。

---

## 一分钟启动

```bash
git clone <repo-url> && cd 上下文助手
docker compose up -d
# 打开 http://localhost:8080
```

或者本地开发模式：

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 核心亮点（面试展示用）

### 多 Agent 辩论
`prompt_optimizing` 阶段启动 3 个不同风格的优化师竞争，Reviewer 四维度评分选出最优提示词。

> 通用型 vs 激进型 vs 保守型 → Reviewer 判词 + 评分 → 胜出提示词进入代码生成

### 确定性编排
8 阶段管线不是简单的"调 API"：
- **事件溯源状态机** — 每一步可审计、可回滚
- **Saga 补偿事务** — Agent 失败自动回退到前一阶段重试
- **Poisson 抖动重试** — 避免 LLM API 限流的雪崩效应

### 三道防线
1. Agent 系统指令约束
2. 代码特征检测（`_looks_like_python`）
3. `py_compile` 语法编译验证 → 语法错误自动拦截回退

---

## 架构

```
User Input → Requirement Optimizer → Confirmation Gate → Planner
                ↓                                              ↓
         Multi-Agent DEBATE ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
    ┌───────────┼───────────┐
    ▼           ▼           ▼
 OptimizerV1  V2(Creative) V3(Safe)
    └───────────┼───────────┘
                ▼
            Reviewer (4-dimension scoring)
                ↓
         Coder ══╦══ Test Engineer (PARALLEL)
                ↓
         Verifier → Archiver
```

---

## 管线阶段

| 阶段 | Agent | 说明 |
|------|-------|------|
| `input_collecting` | 用户 | 自然语言输入需求 |
| `requirement_optimizing` | 需求优化器 | 多方案对比 + Agent 角色分配 |
| `confirmation` | 确认门 | 用户确认/修改/拒绝方案 |
| `planning` | 规划器 | 结构化执行计划 |
| `prompt_optimizing` | **3 个优化师辩论** | Reviewer 四维度评分选最优 |
| `executing` | 编码器 + 测试工程师（并行） | 代码 + 测试同步生成 |
| `verifying` | 验证器 | 语法检查 + 功能验证 |
| `archiving` | 归档器 | 产物归档 |

---

## 稳定性机制（对齐业界最佳实践）

| 机制 | 实现 | 对标 |
|------|------|------|
| 事件溯源状态机 | `core/event_sourced_state.py` | Temporal |
| Saga 补偿事务 | `core/saga_orchestrator.py` | Prefect |
| Poisson 抖动重试 | `core/retry_policy.py` | AWS SDK |
| 心跳检查点 | `core/heartbeat_checkpoint.py` | Temporal |
| 流水线快照回滚 | `core/pipeline_snapshot.py` | Haystack |
| 优先级队列 | `core/priority_queue.py` | Haystack |

---

## 技术栈

- **后端**: Python 3.9+ / FastAPI / Uvicorn
- **前端**: Vanilla JS / CSS Glassmorphism / WebSocket 实时推送
- **存储**: SQLite WAL / 快照回滚
- **LLM**: Anthropic Claude / DeepSeek / OpenAI 兼容 API
- **部署**: Docker / docker-compose

---

## 快速演示流程

1. 打开 `http://localhost:8080`
2. 输入任务，例如：
   > 写一个命令行待办事项工具，支持添加、删除、列出、标记完成。数据存 JSON 文件。要有完整的错误处理。
3. 点击「启动流水线」
4. 观察管线实时推进 → **重点看 `prompt_optimizing` 阶段的辩论面板** — 三栏对比 3 个优化师的输出
5. 确认方案后继续 → 代码生成 → 验证 → 归档
6. 产物品面板下载/预览生成的代码

---

## 测试

```bash
# 多 Agent 协作测试（22 个）
python -m pytest tests/test_multi_agent.py -v

# 全部测试（96 个）
python -m pytest tests/ -v
```

---

## 稳定性组件库（v0.6 体系）

`core/` 目录下包含 7 个稳定性组件。其中 RetryPolicy、PipelineSnapshot 和 Saga 被 `Orchestrator.run()` 主循环直接集成（快照回滚、重试、补偿）；EventSourcedStateMachine、HeartbeatCheckpoint、PrioritySkillQueue 通过 `SkillOrchestrator` 整合，作为下一阶段主循环重构的架构预留。

| 组件 | 行数 | 集成状态 | 对标 |
|------|------|----------|------|
| `retry_policy.py` | 116 | ✅ 已集成到主循环 | AWS SDK |
| `pipeline_snapshot.py` | 174 | ✅ 已集成到 StateDB | Haystack |
| `saga_orchestrator.py` | 233 | ✅ 校验失败回退走 Saga | Prefect |
| `event_sourced_state.py` | 298 | 🔧 SkillOrchestrator 中 | Temporal |
| `heartbeat_checkpoint.py` | 142 | 🔧 SkillOrchestrator 中 | Temporal |
| `priority_queue.py` | 135 | 🔧 SkillOrchestrator 中 | Haystack |
| `skill_orchestrator.py` | 263 | 🔧 集成容器 | — |

> 设计思路：主循环保持轻量（直接操作 StateDB），全功能集成走 SkillOrchestrator。两套方案各有适用场景，详见 `docs/架构图.md`。

---

## 项目动机

市面上的 AI coding 工具让开发变简单了，但也让 Agent 行为变成了黑盒。这个项目是为了**打开黑盒**——理解 Agent 什么时候会失败、多 Agent 怎么协作最有效、管线设计对最终产出质量有什么影响。

> "I didn't just use AI tools. I built one to understand how they fail."
