# 上下文助手 — AI 工作流编排系统

Python 编排器驱动的 AI 工作流系统，通过状态外部化和 Tool Use 审批机制协调 LLM Agent 执行任务。

## 架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────┐     ┌───────────┐
│ Orchestrator │────▶│ AgentCaller  │────▶│   LLM   │────▶│ Tool Use  │
│  (Python)    │     │ (SDK/Fallback)│     │ (Claude)│     │  审批      │
└─────────────┘     └──────────────┘     └─────────┘     └───────────┘
      │                                       │
      ▼                                       ▼
  StateDB (SQLite WAL)              artifacts/ 输出文件
```

- **编排器** 驱动管线流转，Agent 只做推理
- **AgentCaller** 自动选择 SDK 或 subprocess fallback
- **Tool Use 审批** 防止 Agent 跳步或非法转换
- **StateDB** SQLite WAL 持久化任务状态，支持快照/回滚

## 核心模块

| 模块 | 职责 |
|------|------|
| `core/db.py` | StateDB — SQLite WAL 状态存储、快照、token 追踪 |
| `core/agent_caller.py` | AgentCaller — SDKCaller + FallbackCaller 工厂 |
| `core/orchestrator.py` | Orchestrator — 管线驱动、验证、重试、质量门 |
| `core/quality_gates.py` | QualityGateRunner — 检查 skill 输出文件 |
| `core/pipeline_def.py` | PIPELINE 权威定义 |
| `scripts/validator.py` | 步骤输出验证 |
| `scripts/requirement_optimizer.py` | 需求优化与 Schema 校验 |
| `scripts/utils.py` | 公共工具函数 |

## 管线阶段

```
input_collecting → requirement_optimizing → confirmation →
planning → prompt_optimizing → executing → verifying → archiving
```

- `input_collecting`: 收集用户需求（等待用户输入）
- `requirement_optimizing`: Agent 优化需求、生成多方案对比
- `confirmation`: 用户确认/修订/拒绝（等待用户决策）
- `planning`: Agent 生成执行计划
- `prompt_optimizing`: Agent 优化提示词
- `executing`: Agent 执行代码生成
- `verifying`: Agent 验证产出 + 质量门检查
- `archiving`: Agent 归档最终产出

## 运行

```bash
# 安装依赖（SDK 模式需要）
pip install -r requirements.txt

# 运行测试
python tests/test_phase3.py
python tests/test_phase1.py
```

## 项目结构

```
core/           核心模块（StateDB, Orchestrator, AgentCaller, QualityGates）
scripts/        辅助脚本（validator, requirement_optimizer, utils）
tests/          测试套件
config/         配置文件（requirement_schema.json 等）
workflows/      运行时任务目录
.claude/        Agent 定义文件（agents/*.md）
demo/           端到端 demo
archive/        隔离的非核心目录（bin, powershell, vscode-extension, backup）
```