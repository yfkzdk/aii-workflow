# ⚠️ DEPRECATED - 此文档已过时

> **注意**: 此文档描述的是一个旧的 3 阶段系统架构，与当前项目实际使用的 9 阶段增强管线不符。
> 
> 当前架构请参考 `.claude/CLAUDE.md`，其中定义了：
> - input_collecting → requirement_optimizing → confirmation
> - → planning → prompt_optimizing → executing → verifying → archiving
> 
> 此文档中引用的脚本（task_parser.py, workflow_executor.py, test_executor.py）不存在于当前项目中。
> 保留此文档仅作为历史参考。

---

# 🤖 角色：主调度器 (Orchestrator)

## 🎯 核心职责
作为状态驱动多Agent流水线的中央调度器，负责：
1. 接收用户任务请求
2. 分配任务给专用Agent
3. 监控任务执行状态
4. 协调Agent间通信
5. 最终结果汇总与交付

## 🔄 工作流程

### 阶段1：任务接收与解析
```
输入 → 任务解析 → 任务分解 → Agent分配
```

### 阶段2：多Agent协同执行
```
┌─────────┐    ┌─────────┐    ┌─────────┐
│任务解析器│ → │工作流执行│ → │测试执行器│
└─────────┘    └─────────┘    └─────────┘
      ↓              ↓              ↓
┌─────────────────────────────────────┐
│        状态管理器 (统一状态)        │
└─────────────────────────────────────┘
```

### 阶段3：结果聚合与交付
```
各Agent结果 → 结果聚合 → 质量验证 → 最终交付
```

## 📋 Agent通信协议

### 状态格式 (JSON)
```json
{
  "task_id": "TASK-YYYYMMDD-HHMMSS",
  "status": "pending|running|success|failed",
  "current_agent": "agent_name",
  "progress": 0-100,
  "data": {},
  "timestamp": "ISO-8601",
  "next_agent": "agent_name|null"
}
```

### 任务数据格式
```json
{
  "task": {
    "id": "TASK-YYYYMMDD-HHMMSS",
    "type": "analysis|development|testing|deployment",
    "priority": "high|medium|low",
    "requirements": "任务描述",
    "constraints": "约束条件",
    "expected_output": "期望输出格式"
  },
  "context": {
    "previous_results": [],
    "dependencies": [],
    "environment": {}
  }
}
```

## 🚀 Agent调用规范

### 1. 任务解析器 (Task Parser)
- **文件**: `scripts/task_parser.py`
- **输入**: 原始任务描述
- **输出**: 结构化任务数据
- **调用**: `python scripts/task_parser.py "任务描述"`

### 2. 工作流执行器 (Workflow Executor)
- **文件**: `scripts/workflow_executor.py`
- **输入**: 结构化任务数据
- **输出**: 执行方案和步骤
- **调用**: `python scripts/workflow_executor.py --task-id TASK-XXX`

### 3. 测试执行器 (Test Executor)
- **文件**: `scripts/test_executor.py`
- **输入**: 执行方案
- **输出**: 测试结果和验证
- **调用**: `python scripts/test_executor.py --task-id TASK-XXX`

### 4. 状态管理器 (State Manager)
- **文件**: `scripts/state_manager.py`
- **输入**: 所有Agent状态更新
- **输出**: 统一状态视图
- **调用**: 自动由各Agent调用

## 📁 文件系统结构

### 状态文件
```
workflows/
├── tasks/              # 任务输入文件
│   └── TASK-XXX.md    # 单个任务文件
├── states/             # 状态文件
│   └── TASK-XXX.json  # 任务状态
└── results/            # 结果文件
    └── TASK-XXX.md    # 最终结果
```

### 日志文件
```
logs/
├── orchestrator.log    # 调度器日志
├── task_parser.log    # 任务解析器日志
├── workflow_executor.log # 工作流执行器日志
└── test_executor.log  # 测试执行器日志
```

## ⚙️ 错误处理机制

### 错误等级
1. **WARNING**: 可恢复错误，自动重试
2. **ERROR**: 需要人工干预的错误
3. **CRITICAL**: 系统级错误，停止流水线

### 重试策略
- 网络错误: 3次重试，指数退避
- 解析错误: 2次重试，人工干预
- 执行错误: 1次重试，回滚操作

## 🧪 测试模式

### 模拟数据生成
```python
# 测试模式下使用模拟数据
if TEST_MODE:
    data = generate_mock_data(task_type)
    return simulate_execution(data)
```

### 验证规则
1. 每个Agent必须通过单元测试
2. 端到端流程必须通过集成测试
3. 状态一致性必须通过验证测试

## 📊 性能指标

### 监控指标
- **任务吞吐量**: 任务/小时
- **平均处理时间**: 秒/任务
- **错误率**: 错误数/总任务数
- **Agent利用率**: 各Agent忙碌时间占比

### 优化目标
- 95%任务在5分钟内完成
- 错误率低于1%
- Agent利用率均衡（40-70%）

## 🔧 配置管理

### 环境变量
```bash
export AGENT_TIMEOUT=300        # Agent超时时间（秒）
export MAX_RETRIES=3            # 最大重试次数
export LOG_LEVEL=INFO           # 日志级别
export TEST_MODE=false          # 测试模式开关
```

### 配置文件
```json
{
  "agents": {
    "task_parser": {
      "timeout": 60,
      "retries": 2
    },
    "workflow_executor": {
      "timeout": 300,
      "retries": 3
    }
  },
  "state": {
    "persistence": "file",
    "sync_interval": 5
  }
}
```

## 🚨 紧急操作

### 停止流水线
```bash
# 优雅停止
python scripts/orchestrator.py --stop

# 强制停止
python scripts/orchestrator.py --force-stop
```

### 状态恢复
```bash
# 从最后检查点恢复
python scripts/orchestrator.py --recover

# 重置任务状态
python scripts/orchestrator.py --reset TASK-XXX
```

## 📝 使用示例

### 启动调度器
```bash
python scripts/orchestrator.py --start
```

### 提交任务
```bash
python scripts/orchestrator.py --task "分析用户行为数据，生成报告"
```

### 查看状态
```bash
python scripts/orchestrator.py --status
python scripts/orchestrator.py --status TASK-XXX
```

### 查看日志
```bash
tail -f logs/orchestrator.log
```

---

**注意**: 本系统为零外部依赖，仅使用Python标准库。所有Agent通过文件系统进行状态同步，确保高可靠性和可恢复性。