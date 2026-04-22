# Skill 调用集成设计文档

> **版本**: v1.0
> **日期**: 2026-04-22
> **状态**: 设计完成，待实施
> **作者**: AI 架构工程师 + 用户协作设计

---

## 目录

1. [概述](#概述)
2. [架构设计](#架构设计)
3. [核心组件](#核心组件)
4. [数据流与执行流程](#数据流与执行流程)
5. [配置规范](#配置规范)
6. [错误处理与审计](#错误处理与审计)
7. [测试策略](#测试策略)
8. [实施计划](#实施计划)
9. [风险控制](#风险控制)
10. [文档与维护](#文档与维护)

---

## 概述

### 背景

当前系统（v0.5.0）已完成方案A（止血优先），修复了阻断性 bug 并清理了僵尸文件。现在需要实现方案二：**Skill 调用集成**，让 Agent 能在执行过程中调用 Claude Code 的 skill（如 security-review、simplify、review）增强能力。

### 目标

1. **配置层**：创建 `config/skill_whitelist.json` 定义各阶段可调用的 skill 白名单
2. **编排层**：扩展 `orchestrator.py` 支持 `invoke_skill` tool 调用和审批
3. **执行层**：实现声明式 Skill 注册 + 统一执行接口 + Python 适配层
4. **验证层**：扩展 `validator.py` 和 `quality_gates.py` 检查 skill 结果
5. **测试层**：编写分层测试用例验证完整集成

### 核心原则

- **职责分离**：权限审批（白名单）与质量检查（质量门）独立
- **确定性执行**：分相执行管道，状态机完整可追溯
- **配置驱动**：动态注入 skill 说明，无需修改 agent.md
- **Fail-Fast**：结构校验失败立即阻断，策略评估后置

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        完整架构                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ Agent 定义   │───▶│ Agent 调用   │───▶│ Tool Use    │         │
│  │ (.md文件)   │    │ (LLM推理)    │    │ 审批        │         │
│  └─────────────┘    └─────────────┘    └──────┬──────┘         │
│         │                                      │                │
│         │ 动态注入 skill 说明                   │                │
│         ▼                                      ▼                │
│  ┌─────────────┐                      ┌─────────────┐          │
│  │ skill_whitelist│◀─────────────────│ Orchestrator│          │
│  │ .json       │   白名单检查          │             │          │
│  └─────────────┘                      └──────┬──────┘          │
│                                              │                 │
│                                              ▼                 │
│                                      ┌─────────────┐          │
│                                      │ SkillEngine │          │
│                                      │ (统一接口)  │          │
│                                      └──────┬──────┘          │
│                                              │                 │
│                         ┌────────────────────┼────────────────┐│
│                         ▼                    ▼                ▼│
│                  ┌─────────────┐    ┌─────────────┐  ┌────────┐│
│                  │BuiltinAdapter│    │ CLIAdapter  │  │...     ││
│                  └──────┬──────┘    └──────┬──────┘  └────────┘│
│                         │                  │                   │
│                         └──────────┬───────┘                   │
│                                    ▼                           │
│                           ┌─────────────┐                     │
│                           │ artifacts/  │                     │
│                           │ *_result.json│                     │
│                           └──────┬──────┘                     │
│                                  │                             │
│         ┌────────────────────────┘                             │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ Validator   │───▶│ QualityGate │───▶│ 管线推进    │         │
│  │ (结构校验)  │    │ (策略评估)  │    │             │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 双层配置架构

```
┌─────────────────────────────────────────────────────────┐
│                  配置层分离设计                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  config/skill_whitelist.json    config/quality_gates.py │
│  ┌─────────────────────┐       ┌─────────────────────┐ │
│  │ 权限白名单配置       │       │ 质量门强制检查      │ │
│  │                     │       │                     │ │
│  │ • 阶段允许的 skill  │       │ • 自动执行的 skill  │ │
│  │ • 失败策略配置      │       │ • 检查阈值与动作    │ │
│  │ • 超时与关键性      │       │ • 重试与阻断规则    │ │
│  └─────────────────────┘       └─────────────────────┘ │
│           ↓                             ↓               │
│      Agent 主动调用              编排器自动检查         │
│      需要审批                     强制执行              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 分相执行管道

```
Agent 返回 tool_calls
    ↓
Orchestrator._handle_tool_calls()
    ↓
┌─────────────────────────────────────────────────────┐
│ 第一相：执行所有 invoke_skill                       │
│  • Registry.is_allowed() 白名单检查                 │
│  • Engine.execute() 执行 skill                      │
│  • 结果写入 artifacts/*_result.json                 │
│  • 收集所有 skill 执行结果                          │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ 第二相：质量门评估                                  │
│  • Validator 校验结果文件结构（Fail-Fast）          │
│  • QualityGate 评估指标与策略                       │
│  • 生成阶段质量报告                                 │
│  • 应用失败策略（block/warn/retry/log）             │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ 第三相：状态流转                                    │
│  • 处理 transition_state                            │
│  • 携带 stage_execution_context                     │
│  • 推进到下一阶段                                   │
└─────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. SkillRegistry（策略注册表）

**职责**：启动时加载 `skill_whitelist.json` + `skills.json`，构建只读策略字典

**核心接口**：
```python
class SkillRegistry:
    def __init__(self, whitelist_path: str, skills_path: str):
        """加载配置并解析继承链"""
        self._policies = self._load_and_resolve(whitelist_path, skills_path)

    def is_allowed(self, stage: str, skill_name: str) -> bool:
        """检查 skill 是否在白名单中"""

    def get_policy(self, stage: str, skill_name: str) -> SkillPolicy:
        """获取 skill 的完整策略配置"""

    def get_allowed_skills(self, stage: str) -> List[SkillPolicy]:
        """获取该阶段所有允许的 skill"""
```

**关键特性**：
- 启动期强校验：JSON Schema 校验，拒绝非法配置
- 层级继承：全局默认 → 阶段默认 → skill 级覆盖
- 运行时只读：禁止动态修改白名单

### 2. SkillEngine（执行引擎）

**职责**：统一执行接口，不关心底层实现

**核心接口**：
```python
class SkillEngine:
    def __init__(self, registry: SkillRegistry, task_dir: str):
        self._registry = registry
        self._task_dir = task_dir
        self._adapters: Dict[str, SkillAdapter] = {}

    def execute(self, stage: str, skill_name: str, context: dict) -> SkillResult:
        """执行 skill 并返回标准化结果"""
        adapter = self._get_adapter(skill_name)
        policy = self._registry.get_policy(stage, skill_name)
        return self._run_with_timeout(adapter, context, policy.timeout)
```

**关键特性**：
- 超时控制：进程级管控，强制终止 + 资源清理
- 重试策略：区分错误类型（网络/权限/超时），指数退避
- 错误分类：ExecutionFault（执行异常）vs QualityViolation（策略违规）

### 3. SkillAdapter（适配器基类）

**职责**：抽象执行媒介差异，统一输出契约

**核心接口**：
```python
class SkillAdapter(ABC):
    @abstractmethod
    def run(self, context: dict) -> SkillResult:
        """执行 skill 并返回标准化结果"""

class BuiltinSkillAdapter(SkillAdapter):
    """内置 skill（simplify, review 等）的 Python 实现"""

class CLISkillAdapter(SkillAdapter):
    """外部 CLI 工具的包装器"""
```

**关键特性**：
- 无状态设计：每次执行显式重置
- 契约强制：输出必须符合 `skill-result-schema-v1.json`
- 资源隔离：独立工作目录 + 临时文件生命周期管理

### 4. Validator 扩展

**职责**：检查 skill 结果文件的结构完整性

**新增函数**：
```python
def _check_skill_results(task_dir: Path, step: str) -> tuple[bool, str]:
    """检查该阶段所有已执行 skill 的结果"""
    artifacts = task_dir / "artifacts"
    skill_results = list(artifacts.glob("*_result.json"))

    for result_file in skill_results:
        data = json.loads(result_file.read_text(encoding="utf-8"))

        # 检查契约必需字段
        required = ["status", "outputs", "metrics", "errors", "metadata"]
        missing = [f for f in required if f not in data]
        if missing:
            return (False, f"{result_file.name} 缺少字段: {missing}")

        # 检查执行状态
        if data["status"] not in ["success", "partial_success", "failed", "timeout"]:
            return (False, f"{result_file.name} 非法状态: {data['status']}")

    return (True, "PASS")
```

**关键特性**：
- Fail-Fast：结构错误立即阻断，不进入质量门
- 契约校验：JSON Schema 验证，版本化管理
- 错误分类：ExecutionFault 归类，触发重试或人工介入

### 5. QualityGate 扩展

**职责**：评估 skill 执行结果的策略合规性

**新增方法**：
```python
class QualityGateRunner:
    def _check_invoked_skills(self, task_dir: Path, step: str) -> List[Dict]:
        """检查 Agent 主动调用的 skill 结果"""
        results = []
        artifacts = task_dir / "artifacts"

        for result_file in artifacts.glob("*_result.json"):
            data = json.loads(result_file.read_text(encoding="utf-8"))

            # 读取元数据
            metadata = data.get("metadata", {})
            critical = metadata.get("critical", False)
            invocation_type = metadata.get("invocation_type", "agent")

            # 评估策略
            if data["status"] in ["failed", "timeout"]:
                if critical:
                    results.append({
                        "skill": result_file.stem,
                        "action": "block",
                        "passed": False,
                        "reason": f"关键技能失败: {data['errors']}"
                    })
                else:
                    results.append({
                        "skill": result_file.stem,
                        "action": "warn",
                        "passed": False,
                        "reason": f"非关键技能失败: {data['errors']}"
                    })

        return results
```

**关键特性**：
- 策略评估：读取 `invocation_type` 和 `critical` 元数据
- 失败策略：block（阻断）/ warn（警告）/ retry（重试）/ log（记录）
- 与 Validator 分离：结构校验前置，策略评估后置

### 6. 动态 Prompt 注入

**职责**：在 Orchestrator 调用 Agent 时，动态注入 skill 说明

**四段式上下文组装**：
```python
def _build_context(self, state: Dict[str, Any]) -> str:
    parts = []

    # 1. 角色基座：加载 agent.md
    parts.append(self._load_agent_def(state["agent_id"]))

    # 2. 任务上下文：注入当前状态
    parts.append(self._build_task_context(state))

    # 3. 动态 Skill Block：查询白名单并渲染模板
    allowed_skills = self.skill_registry.get_allowed_skills(state["status"])
    if allowed_skills:
        parts.append(self._render_skill_block(allowed_skills))

    # 4. 安全护栏：追加强制声明
    parts.append(self._build_safety_guardrails())

    return "\n\n".join(parts)
```

**模板渲染示例**：
```markdown
## 可用 Skill

本阶段可请求以下 skill（通过 `invoke_skill` tool）：

| Skill | 用途 | 失败策略 | 关键性 |
|-------|------|---------|--------|
| security-review | 扫描代码安全漏洞 | block | critical |
| simplify | 代码简化重构 | warn | non-critical |

### 调用示例

```json
{
  "name": "invoke_skill",
  "input": {
    "skill": "security-review",
    "context": {
      "target_path": "artifacts/code/"
    }
  }
}
```

### 执行结果

结果写入 `artifacts/security_review_result.json`，包含：

```json
{
  "status": "success|failed|timeout",
  "outputs": {...},
  "metrics": {...},
  "errors": [],
  "metadata": {
    "critical": true,
    "invocation_type": "agent"
  }
}
```

### 失败处理

- **block**：关键技能失败，流水线暂停
- **warn**：非关键失败，记录警告，流水线继续
```

**关键特性**：
- 配置驱动：无需修改 agent.md
- 权限收敛：仅注入白名单 skill
- 调试保障：Prompt 快照归档 + DEBUG_PROMPT 固化模式

---

## 数据流与执行流程

### 完整执行流程

```
1. Agent 推理并返回 tool_calls
   ↓
2. Orchestrator._handle_tool_calls() 接收 tool_calls
   ↓
3. 第一相：执行所有 invoke_skill
   ├─ 3.1 白名单检查（Registry.is_allowed）
   ├─ 3.2 执行 skill（Engine.execute）
   ├─ 3.3 写入结果文件（artifacts/*_result.json）
   └─ 3.4 收集所有结果
   ↓
4. 第二相：质量门评估
   ├─ 4.1 Validator 校验结果文件结构
   ├─ 4.2 QualityGate 评估策略合规性
   ├─ 4.3 生成阶段质量报告
   └─ 4.4 应用失败策略（block/warn/retry）
   ↓
5. 第三相：状态流转
   ├─ 5.1 处理 transition_state
   ├─ 5.2 携带 stage_execution_context
   └─ 5.3 推进到下一阶段
```

### 关键数据结构

**SkillPolicy（策略配置）**：
```python
@dataclass
class SkillPolicy:
    name: str
    on_fail: str  # block/warn/retry/log/skip
    critical: bool
    timeout_seconds: int
    enabled: bool
    args: Dict[str, Any]
```

**SkillResult（执行结果）**：
```python
@dataclass
class SkillResult:
    status: str  # success/partial_success/failed/timeout
    outputs: Dict[str, Any]
    metrics: Dict[str, Any]
    errors: List[str]
    metadata: Dict[str, Any]
```

**stage_execution_context（阶段上下文）**：
```python
{
    "stage": "executing",
    "skills_executed": ["security-review", "simplify"],
    "skill_results": {
        "security-review": {"status": "success", ...},
        "simplify": {"status": "failed", ...}
    },
    "quality_report": {...},
    "errors": [...],
    "warnings": [...]
}
```

---

## 配置规范

### skill_whitelist.json 格式

```json
{
  "version": "1.0",
  "defaults": {
    "timeout_seconds": 120,
    "on_fail": "warn",
    "critical": false,
    "enabled": true
  },
  "whitelist": {
    "input_collecting": {
      "skills": [
        {
          "name": "brainstorming",
          "on_fail": "warn",
          "timeout_seconds": 60
        }
      ]
    },
    "executing": {
      "skills": [
        {
          "name": "security-review",
          "on_fail": "block",
          "critical": true,
          "timeout_seconds": 180,
          "args": {
            "level": "${project.security_level}",
            "output_format": "json"
          }
        },
        {
          "name": "simplify",
          "on_fail": "warn",
          "timeout_seconds": 60
        }
      ]
    },
    "verifying": {
      "skills": [
        {
          "name": "simplify",
          "on_fail": "retry",
          "critical": true
        },
        {
          "name": "systematic-debugging",
          "enabled": false
        }
      ]
    },
    "archiving": {
      "skills": [
        {
          "name": "review",
          "on_fail": "log"
        }
      ]
    }
  }
}
```

### 配置字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | string | 是 | 配置版本号 |
| `defaults` | object | 是 | 全局默认值 |
| `whitelist` | object | 是 | 阶段级白名单 |
| `skills[].name` | string | 是 | skill 名称 |
| `skills[].on_fail` | enum | 否 | 失败策略：block/warn/retry/log/skip |
| `skills[].critical` | bool | 否 | 关键性标识 |
| `skills[].timeout_seconds` | int | 否 | 超时时间（秒） |
| `skills[].enabled` | bool | 否 | 启用开关 |
| `skills[].args` | object | 否 | 参数传递 |

### 配置校验规则

**非法组合检测**：
- `critical=true` 且 `on_fail=skip` → 拒绝加载
- `timeout_seconds <= 0` → 拒绝加载
- `on_fail` 不在枚举值中 → 拒绝加载

**继承链解析**：
1. 全局默认值（`defaults`）
2. 阶段默认值（可选）
3. skill 级覆盖（`skills[]`）

**参数占位符解析**：
- 支持上下文变量：`${plan.id}`, `${user.role}`, `${stage.name}`
- 安全白名单：仅允许预定义变量
- 未解析变量：按默认值填充或拒绝执行

---

## 错误处理与审计

### 错误码体系

**命名空间**：`{模块}-{分类}-{序号}`

| 错误码 | 分类 | 说明 | 处置动作 |
|--------|------|------|---------|
| CFG-001 | 配置加载 | 白名单文件缺失 | block |
| CFG-002 | 配置校验 | Schema 不匹配 | block |
| CFG-003 | 配置校验 | 非法配置组合 | block |
| EXE-101 | 技能执行 | 超时 | retry |
| EXE-102 | 技能执行 | 进程退出码非零 | retry/warn |
| EXE-103 | 技能执行 | 沙箱隔离失败 | block |
| EXE-104 | 技能执行 | 文件写入冲突 | retry |
| QTY-201 | 质量门 | 指标阈值未达标 | warn/block |
| QTY-202 | 质量门 | 关键 Skill 失败 | block |
| QTY-203 | 质量门 | 结构校验断裂 | block |
| APP-301 | 审批流 | 超时未批复 | warn |
| APP-302 | 审批流 | 权限越权 | block |
| APP-303 | 审批流 | 状态非法跃迁 | block |

### 审计日志格式

**结构化格式**：JSON Lines，每行独立事务

**核心字段**：
```json
{
  "timestamp": "2026-04-22T15:30:45.123Z",
  "trace_id": "trace-abc123",
  "plan_id": "plan-xyz789",
  "execution_id": "exec-def456",
  "stage": "executing",
  "skill_name": "security-review",
  "event_type": "skill_execution",
  "status": "success",
  "error_code": null,
  "duration_ms": 45230,
  "config_version": "v1.2.0",
  "metadata": {
    "critical": true,
    "invocation_type": "agent",
    "files_scanned": 12,
    "vulnerabilities_found": 3
  }
}
```

**关联链路**：
- `trace_id`：贯穿单次任务全生命周期
- `plan_id`：绑定业务计划
- `execution_id`：绑定单批次 Skill 调用

**存储策略**：
- V1：本地追加写入 + 按日轮转 + 最大保留 30 天
- 敏感字段脱敏：路径、用户标识
- 审计边界：仅记录决策事件，不记录完整 Prompt

### 性能监控指标

**核心指标**：
- `skill_execution_duration`：单次技能执行耗时（P50/P95/P99）
- `skill_failure_rate`：按阶段/技能分类的失败率
- `pipeline_stage_latency`：阶段完成总耗时
- `approval_wait_time`：人工审批排队时长
- `config_validation_errors`：配置校验失败次数

**采集方式**：
- V1：内置轻量收集器，输出 JSON 至 `artifacts/metrics/`
- 支持后续桥接 Prometheus

**告警基线**：
- P95 耗时 > 2x 基线 → 高优告警
- 关键技能失败率 > 5% → 高优告警

---

## 测试策略

### 分层测试目录

```
tests/
├── unit/
│   ├── test_skill_registry.py
│   ├── test_skill_adapter.py
│   └── test_template_renderer.py
├── integration/
│   ├── test_skill_engine.py
│   └── test_orchestrator_skill_flow.py
└── e2e/
    └── test_full_pipeline_with_skills.py
```

### 测试策略矩阵

| 层级 | Mock 策略 | 执行时间 | 覆盖目标 |
|------|----------|---------|---------|
| unit | 全面 Mock | < 30s | 核心逻辑 100% |
| integration | 有限 Mock | < 2min | 组件契约验证 |
| e2e | 混合策略 | < 10min | 业务价值闭环 |

### 验收标准

**单元测试**：
```bash
make test-unit
# 覆盖率要求：≥ 85%（核心逻辑 ≥ 95%）
# 执行时间：< 30s
```

**集成测试**：
```bash
make test-integration
# 要求：无未处理异常
# 执行时间：< 2min
```

**端到端测试**：
```bash
make test-e2e
# 要求：核心场景 100% 通过，零静默失败
# 执行时间：< 10min
```

**契约校验**：
```bash
make contract-check
# 要求：白名单、质量门、Skill 输出契约、Prompt 模板四者一致性零偏差
```

### 测试数据管理

**fixtures/ 目录**：
- `unit/`：JSON/YAML 契约样本
- `integration/`：完整阶段工件树
- `e2e/`：脱敏的真实项目快照

**夹具管理**：
- 版本化、只读
- 哈希校验防篡改
- 测试前自动拷贝至隔离沙箱

### CI 门禁策略

| 门禁 | 触发条件 | 测试范围 | 反馈时间 |
|------|---------|---------|---------|
| PR | Pull Request | unit + contract-check | < 3min |
| Merge | 合并到主分支 | unit + integration | < 5min |
| Release | 发布前 | unit + integration + e2e | < 15min |

---

## 实施计划

### 阶段划分

**阶段 1：配置层（预估 2 小时）**
- 创建 `config/skill_whitelist.json`
- 实现 `SkillRegistry` 类
- 编写单元测试

**阶段 2：执行层（预估 3 小时）**
- 实现 `SkillEngine` 类
- 实现 `BuiltinSkillAdapter` 和 `CLISkillAdapter`
- 编写单元测试

**阶段 3：编排层（预估 3 小时）**
- 扩展 `Orchestrator._handle_tool_calls()`
- 实现分相执行管道
- 实现动态 Prompt 注入
- 编写集成测试

**阶段 4：验证层（预估 2 小时）**
- 扩展 `validator.py`
- 扩展 `quality_gates.py`
- 编写集成测试

**阶段 5：测试与文档（预估 2 小时）**
- 编写 E2E 测试
- 更新 README 和架构文档
- 编写 API 文档

**总计**：约 12 小时

### 文件修改清单

**新增文件**：
- `config/skill_whitelist.json`
- `core/skill_registry.py`
- `core/skill_engine.py`
- `core/skill_adapter.py`
- `schemas/skill-result-schema-v1.json`
- `tests/unit/test_skill_registry.py`
- `tests/unit/test_skill_adapter.py`
- `tests/integration/test_skill_engine.py`
- `tests/integration/test_orchestrator_skill_flow.py`
- `tests/e2e/test_full_pipeline_with_skills.py`

**修改文件**：
- `core/orchestrator.py`：扩展 `_handle_tool_calls()`，新增 `_build_context()`
- `scripts/validator.py`：新增 `_check_skill_results()`
- `core/quality_gates.py`：新增 `_check_invoked_skills()`
- `core/__init__.py`：导出新模块

### 风险点与回滚方案

**风险 1：配置与实现脱节**
- 缓解：CI 中增加配置一致性校验
- 回滚：配置文件版本控制，一键回退

**风险 2：CLI 进程泄漏**
- 缓解：Engine 层实施进程树追踪与优雅退出
- 回滚：超时强制终止 + 健康巡检

**风险 3：Token 膨胀**
- 缓解：限制动态注入清单长度，紧凑表格格式
- 回滚：提供 DEBUG_PROMPT=false 禁用注入

**风险 4：测试覆盖不足**
- 缓解：契约校验作为硬性门禁
- 回滚：测试失败阻断合并

---

## 风险控制

### 配置漂移防护

- 将 `skill_whitelist.json` 纳入版本控制
- 配置变更需同步更新架构文档与测试用例
- 配置变更审批流程

### 默认值陷阱

- `on_fail` 默认值设为 `block` 或 `warn`（而非 `skip` 或 `log`）
- 确保问题显性化，避免静默失败

### 可观测性绑定

- 每次技能执行携带配置版本号与策略快照标识
- 日志明确记录：命中策略、应用参数、超时阈值
- 便于事后审计与策略调优

### 降级预案

**配置文件损坏**：
- Orchestrator fallback 至内置最小安全集
- 仅放行只读/无害 skill，关键 skill 全部阻断
- 告警提示人工介入

**模板渲染失败**：
- Fallback 至内置最小 Skill Block
- 记录高优告警
- 防止向 Agent 暴露空白或错误指令

---

## 文档与维护

### 文档结构

```
docs/
├── README.md（更新）
├── architecture/
│   ├── skill-integration.md（新增）
│   └── data-flow.md（更新）
├── api/
│   ├── skill-registry.md（新增）
│   ├── skill-engine.md（新增）
│   └── skill-adapter.md（新增）
├── configuration/
│   ├── skill-whitelist.md（新增）
│   └── quality-gates.md（更新）
└── testing/
    ├── test-strategy.md（新增）
    └── fixtures-guide.md（新增）
```

### 维护职责

| 文档类型 | 维护者 | 更新频率 |
|---------|--------|---------|
| 架构文档 | 架构师 | 重大变更时 |
| API 文档 | 开发者 | 每次发布 |
| 配置文档 | 运维 | 配置变更时 |
| 测试文档 | QA | 测试策略调整时 |

### 版本演进路线

**V1（当前）**：
- 声明式注册 + 工厂适配器 + 静态策略加载
- 稳定基线

**V2（未来）**：
- 技能依赖图解析与并发调度优化
- 配置热更新（文件监听 + 优雅重载）
- 集中式日志平台集成（ELK/Loki）

**V3（远期）**：
- 插件市场与动态扩展
- 多租户隔离与资源配额
- AI 驱动的策略自适应调优

---

## 附录

### A. Skill 执行契约 Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Skill Execution Result",
  "type": "object",
  "required": ["status", "outputs", "metrics", "errors", "metadata"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["success", "partial_success", "failed", "timeout"]
    },
    "outputs": {
      "type": "object",
      "properties": {
        "report_file": {"type": "string"},
        "artifacts": {"type": "array", "items": {"type": "string"}}
      }
    },
    "metrics": {
      "type": "object",
      "properties": {
        "execution_time_seconds": {"type": "number"},
        "files_processed": {"type": "integer"},
        "issues_found": {"type": "integer"}
      }
    },
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "code": {"type": "string"},
          "message": {"type": "string"},
          "severity": {"type": "string", "enum": ["warning", "error", "critical"]}
        }
      }
    },
    "metadata": {
      "type": "object",
      "required": ["skill_version", "critical", "invocation_type", "execution_id", "config_version"],
      "properties": {
        "skill_version": {"type": "string"},
        "critical": {"type": "boolean"},
        "invocation_type": {"type": "string", "enum": ["agent", "system"]},
        "execution_id": {"type": "string"},
        "config_version": {"type": "string"}
      }
    }
  }
}
```

### B. 错误码完整列表

（见"错误处理与审计"章节）

### C. 配置示例

（见"配置规范"章节）

---

**文档结束**

> 本设计文档由 AI 架构工程师与用户协作完成，所有设计决策均经过充分讨论和验证。
