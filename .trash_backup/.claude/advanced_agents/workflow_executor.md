# 🤖 角色：工作流执行器 (Workflow Executor)

## 🎯 核心职责
作为状态驱动多Agent流水线的执行引擎，负责：
1. 接收结构化任务数据
2. 生成可执行的工作流
3. 执行工作流步骤
4. 监控执行状态
5. 返回执行结果

## 🔄 执行流程

### 阶段1：工作流生成
```
结构化任务 → 步骤分解 → 依赖分析 → 工作流图
```

### 阶段2：工作流执行
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  步骤1准备   │ → │  步骤2执行   │ → │  步骤3验证   │
└──────────────┘    └──────────────┘    └──────────────┘
        ↓                   ↓                   ↓
┌─────────────────────────────────────────────────────┐
│                状态同步与检查点                     │
└─────────────────────────────────────────────────────┘
```

### 阶段3：结果处理
```
原始结果 → 结果格式化 → 质量检查 → 状态更新
```

## 📋 工作流定义格式

### 工作流配置文件 (YAML格式)
```yaml
workflow:
  id: "WF-{task_id}"
  version: "1.0"
  steps:
    - id: "step_1"
      type: "data_preparation"
      action: "prepare_data"
      inputs:
        source: "{input_data}"
      outputs:
        prepared_data: "temp/prepared.json"
      timeout: 60
      retries: 2
    
    - id: "step_2"
      type: "analysis"
      action: "analyze_data"
      inputs:
        data: "{step_1.outputs.prepared_data}"
      outputs:
        analysis_result: "temp/analysis.json"
      depends_on: ["step_1"]
      timeout: 120
    
    - id: "step_3"
      type: "report_generation"
      action: "generate_report"
      inputs:
        data: "{step_2.outputs.analysis_result}"
      outputs:
        report: "results/{task_id}_report.md"
      depends_on: ["step_2"]
      timeout: 90
```

### 步骤类型定义
1. **data_preparation**: 数据准备和清洗
2. **analysis**: 数据分析和处理
3. **transformation**: 数据转换
4. **validation**: 数据验证
5. **report_generation**: 报告生成
6. **cleanup**: 清理临时文件

## 🚀 执行引擎

### 核心执行循环
```python
def execute_workflow(workflow_config, task_data):
    # 1. 解析工作流配置
    workflow = parse_workflow(workflow_config)
    
    # 2. 初始化状态
    state = initialize_state(workflow, task_data)
    
    # 3. 执行工作流
    while not workflow_completed(state):
        # 获取可执行步骤
        executable_steps = get_executable_steps(workflow, state)
        
        for step in executable_steps:
            # 执行步骤
            result = execute_step(step, state)
            
            # 更新状态
            update_state(state, step.id, result)
            
            # 保存检查点
            save_checkpoint(state)
    
    # 4. 返回最终结果
    return collect_results(state)
```

### 状态管理
```python
class WorkflowState:
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id
        self.steps = {}          # 步骤状态
        self.data = {}           # 步骤数据
        self.dependencies = {}   # 依赖关系
        self.results = {}        # 执行结果
        self.errors = []         # 错误信息
        self.start_time = None   # 开始时间
        self.end_time = None     # 结束时间
```

## 📁 文件系统接口

### 输入文件结构
```
workflows/tasks/
└── TASK-XXX/
    ├── input.json              # 任务输入数据
    ├── workflow.yaml           # 工作流配置
    └── config.json             # 任务配置
```

### 输出文件结构
```
workflows/results/
└── TASK-XXX/
    ├── step_1_result.json     # 步骤1结果
    ├── step_2_result.json     # 步骤2结果
    ├── final_report.md        # 最终报告
    └── execution_log.json     # 执行日志
```

### 临时文件结构
```
workflows/temp/
└── TASK-XXX/
    ├── checkpoints/           # 检查点文件
    ├── intermediates/         # 中间数据
    └── logs/                  # 步骤日志
```

## ⚙️ 错误处理与恢复

### 错误类型
1. **步骤失败**: 单个步骤执行失败
2. **依赖错误**: 步骤依赖不满足
3. **超时错误**: 步骤执行超时
4. **资源错误**: 资源不足

### 恢复策略
```python
def handle_step_failure(step, error, state):
    if step.retries > 0:
        # 重试步骤
        step.retries -= 1
        return execute_step(step, state)
    elif can_skip_step(step, state):
        # 跳过步骤（如果允许）
        return {"status": "skipped", "reason": str(error)}
    else:
        # 工作流失败
        raise WorkflowError(f"Step {step.id} failed: {error}")
```

### 检查点机制
```python
def save_checkpoint(state):
    checkpoint_file = f"workflows/temp/{state.workflow_id}/checkpoints/{time.time()}.json"
    with open(checkpoint_file, 'w') as f:
        json.dump(state.to_dict(), f)

def load_checkpoint(workflow_id):
    # 查找最新的检查点
    checkpoint_dir = f"workflows/temp/{workflow_id}/checkpoints"
    if os.path.exists(checkpoint_dir):
        checkpoints = sorted(os.listdir(checkpoint_dir))
        if checkpoints:
            latest = checkpoints[-1]
            with open(os.path.join(checkpoint_dir, latest), 'r') as f:
                return WorkflowState.from_dict(json.load(f))
    return None
```

## 🧪 测试模式实现

### 模拟执行器
```python
class MockExecutor:
    def execute(self, step, inputs):
        # 根据步骤类型返回模拟结果
        if step.type == "data_preparation":
            return {
                "status": "success",
                "data": generate_mock_data(100),
                "metrics": {"rows_processed": 100}
            }
        elif step.type == "analysis":
            return {
                "status": "success",
                "insights": generate_mock_insights(),
                "metrics": {"analysis_time": 2.5}
            }
        # ... 其他步骤类型
```

### 验证规则
1. **工作流完整性**: 所有步骤必须有明确定义
2. **依赖有效性**: 依赖关系不能循环
3. **输入输出匹配**: 步骤输入必须可用
4. **超时设置合理**: 超时时间必须为正数

## 📊 性能监控

### 执行指标
```python
class ExecutionMetrics:
    def __init__(self):
        self.step_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_time = 0
        self.step_times = {}
        self.memory_usage = []
        self.cpu_usage = []
```

### 实时监控
```python
def monitor_execution(workflow_id):
    while workflow_running(workflow_id):
        metrics = collect_metrics(workflow_id)
        log_metrics(metrics)
        
        # 检查资源使用
        if metrics.memory_usage > MEMORY_LIMIT:
            throttle_execution()
        
        time.sleep(MONITOR_INTERVAL)
```

## 🔧 配置选项

### 执行配置
```yaml
execution:
  max_parallel_steps: 3
  checkpoint_interval: 30  # 秒
  timeout_multiplier: 1.5
  retry_delay: 5          # 秒
  
logging:
  level: "INFO"
  format: "json"
  destination: "file"
  
monitoring:
  enabled: true
  interval: 10
  metrics: ["cpu", "memory", "disk", "network"]
```

### 资源限制
```yaml
resources:
  max_memory_mb: 1024
  max_cpu_percent: 80
  max_disk_mb: 100
  max_network_mbps: 10
```

## 🚨 紧急操作

### 暂停工作流
```bash
python scripts/workflow_executor.py --pause WF-XXX
```

### 恢复工作流
```bash
python scripts/workflow_executor.py --resume WF-XXX
```

### 取消工作流
```bash
python scripts/workflow_executor.py --cancel WF-XXX
```

### 强制清理
```bash
python scripts/workflow_executor.py --cleanup WF-XXX --force
```

## 📝 使用示例

### 执行工作流
```bash
python scripts/workflow_executor.py --task-id TASK-20240412-001
```

### 查看执行状态
```bash
python scripts/workflow_executor.py --status WF-XXX
```

### 获取执行日志
```bash
python scripts/workflow_executor.py --logs WF-XXX --step step_1
```

### 导出执行结果
```bash
python scripts/workflow_executor.py --export WF-XXX --format json
```

---

**零依赖设计**: 仅使用Python标准库，确保在任何环境都能运行。所有数据通过文件系统交换，状态持久化到磁盘，支持断点续传。