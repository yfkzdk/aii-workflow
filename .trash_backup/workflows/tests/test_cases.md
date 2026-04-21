# 端到端测试用例

## 测试目的
验证AI工作流编排系统的完整功能，包括任务创建、方案生成、方案对比、方案实施和结果归档。

## 测试环境
- Python 3.8+
- Windows/Linux/macOS
- 上下文助手项目目录结构完整

## 测试用例1: 基础目录结构验证
### 测试目标
验证项目目录结构是否正确

### 测试步骤
1. 检查必需目录是否存在：
   - `.claude/agents/`
   - `scripts/`
   - `tasks/`
   - `workflows/`
   - `workflows/tasks/`
   - `workflows/states/`
   - `workflows/tests/`
   - `workflows/pipelines/`
   - `logs/`

2. 检查必需文件是否存在：
   - `.claude/CLAUDE.md`
   - `.claude/agents/workflow_agent.md`
   - `scripts/workflow_manager.py`
   - `AI_WORKFLOW_LOG.md`
   - `tasks/input_task.md`
   - `tasks/output_result.md`
   - `workflows/pipeline_config.json`

### 预期结果
所有目录和文件都存在且可访问

### 通过标准
- 所有目录都存在
- 所有文件都存在
- 文件可正常读取

## 测试用例2: 配置文件验证
### 测试目标
验证pipeline_config.json配置文件的完整性

### 测试步骤
1. 读取`workflows/pipeline_config.json`
2. 验证JSON格式正确性
3. 检查必需字段：
   - `pipeline_name`
   - `version`
   - `pipeline_stages`
   - `test_scenarios`
4. 验证pipeline_stages结构：
   - 每个阶段必须包含`stage`、`description`、`input`、`output`字段

### 预期结果
配置文件格式正确，所有必需字段都存在

### 通过标准
- JSON解析无错误
- 所有必需字段都存在
- pipeline_stages结构正确

## 测试用例3: 工作流管理器功能测试
### 测试目标
验证workflow_manager.py的核心功能

### 测试步骤
1. 导入workflow_manager.py模块
2. 检查必需的类：
   - `WorkflowManager`
   - `WorkflowState`
3. 检查必需的函数：
   - `create_task()`
   - `update_task_status()`
   - `generate_solutions()`
   - `compare_solutions()`
4. 检查文件内容完整性

### 预期结果
所有必需的类和函数都存在

### 通过标准
- 模块可以正常导入
- 所有必需类和函数都存在
- 没有语法错误

## 测试用例4: 任务创建工作流测试
### 测试目标
验证任务创建流程

### 测试步骤
1. 使用workflow_manager.py创建新任务：
   ```bash
   python scripts/workflow_manager.py create \
     --title "测试任务" \
     --goal "测试工作流功能" \
     --constraints "时间限制: 15分钟" \
     --expected "验证系统功能"
   ```

2. 检查`tasks/input_task.md`是否创建
3. 验证文件内容包含提供的参数
4. 检查`AI_WORKFLOW_LOG.md`是否更新

### 预期结果
- 命令执行成功（返回码为0）
- 创建了input_task.md文件
- 文件内容包含任务标题和目标
- 工作流日志更新了新任务记录

### 通过标准
- 命令执行成功
- 任务文件正确创建
- 日志正确更新

## 测试用例5: 方案生成测试
### 测试目标
验证方案生成功能

### 测试步骤
1. 使用最新创建的任务ID
2. 运行方案生成命令：
   ```bash
   python scripts/workflow_manager.py solutions --task TASK-XXXXXX
   ```

3. 检查是否生成结果文件
4. 验证结果文件包含三个方案：
   - 方案A（激进）
   - 方案B（平衡）
   - 方案C（保守）

### 预期结果
- 命令执行成功
- 生成结果文件
- 文件包含三个完整的方案

### 通过标准
- 方案生成命令成功执行
- 结果文件正确创建
- 三个方案都存在且完整

## 测试用例6: 管道集成测试
### 测试目标
验证与Claude Code的集成

### 测试步骤
1. 检查Claude配置文件`.claude/CLAUDE.md`：
   - 包含"任务编排器"角色描述
   - 引用`workflow_agent.md`
   - 包含`tasks/input_task.md`和`tasks/output_result.md`引用

2. 检查工作流代理文件`.claude/agents/workflow_agent.md`：
   - 包含必需函数：`generate_solutions`、`compare_solutions`、`create_task`
   - 符合Agent模板格式

### 预期结果
Claude Code集成文件完整且正确

### 通过标准
- Claude配置文件包含所有必需内容
- 工作流代理文件完整
- 文件引用路径正确

## 测试用例7: 性能基准测试
### 测试目标
验证系统基本性能

### 测试步骤
1. 运行小任务测试（10次迭代）：
   - 文件创建和删除
   - 基础文件操作性能

2. 运行中任务测试（5次迭代）：
   - JSON序列化和反序列化
   - 数据结构操作

3. 运行大任务测试（2次迭代）：
   - 大文件操作
   - 内存使用检查

### 预期结果
- 平均每次操作时间小于2秒
- 没有内存泄漏
- 操作稳定可靠

### 通过标准
- 所有性能测试通过
- 平均操作时间符合要求
- 没有异常错误

## 测试用例8: 错误处理测试
### 测试目标
验证系统的错误处理能力

### 测试步骤
1. 无效文件路径访问测试
2. 无效JSON解析测试
3. 权限错误测试
4. 超时处理测试

### 预期结果
系统能正确处理各种错误情况

### 通过标准
- 错误被正确捕获和处理
- 系统不会崩溃
- 错误信息清晰

## 测试用例9: 端到端流程测试
### 测试目标
验证完整的端到端工作流程

### 测试步骤
1. **需求分析阶段**：
   - 用户输入：优化Python函数calculate_total
   - 生成任务文件

2. **方案生成阶段**：
   - 生成三个对比方案
   - 方案A：激进优化（使用缓存）
   - 方案B：平衡方案（算法优化）
   - 方案C：保守方案（代码重构）

3. **方案对比阶段**：
   - 计算各方案得分
   - 选择最优方案

4. **方案实施阶段**：
   - 实施最优方案
   - 生成实施结果

5. **结果归档阶段**：
   - 归档到workflows目录
   - 更新工作流日志

### 预期结果
完整的工作流程成功执行，所有阶段都正确完成

### 通过标准
- 所有阶段都成功执行
- 生成完整的任务记录
- 归档文件正确创建
- 日志记录完整准确

## 测试用例10: 边界条件测试
### 测试目标
验证系统在边界条件下的行为

### 测试步骤
1. **空输入测试**：
   - 创建空任务
   - 验证系统如何处理

2. **超长输入测试**：
   - 创建包含超长字符串的任务
   - 验证系统如何处理

3. **并发访问测试**：
   - 模拟并发任务创建
   - 验证文件锁和同步机制

4. **磁盘空间不足测试**：
   - 模拟磁盘空间不足情况
   - 验证错误处理

### 预期结果
系统能正确处理各种边界条件

### 通过标准
- 空输入正确处理
- 超长输入正确处理
- 并发访问无冲突
- 磁盘错误正确处理

## 测试执行脚本
使用`e2e_test.py`脚本自动执行所有测试用例：

```bash
cd 上下文助手
python workflows/tests/e2e_test.py
```

## 测试数据准备
### 样本任务数据
```json
{
  "simple_task": {
    "title": "优化Python函数",
    "goal": "提高calculate_total函数的性能",
    "constraints": "保持向后兼容性，不改变函数签名",
    "expected": "性能提升20%以上"
  },
  "medium_task": {
    "title": "数据处理流水线",
    "goal": "创建完整的数据处理流程",
    "constraints": "支持CSV和JSON格式，内存使用不超过1GB",
    "expected": "可扩展的数据处理框架"
  },
  "complex_task": {
    "title": "系统架构设计",
    "goal": "设计微服务架构",
    "constraints": "高可用性，99.9% SLA，水平扩展",
    "expected": "完整的架构文档和实施路线图"
  }
}
```

## 测试报告
测试完成后生成以下报告：
1. JSON格式详细报告
2. HTML格式可视化报告
3. 控制台汇总输出

## 验收标准
- 所有测试用例通过率 ≥ 90%
- 端到端流程完整执行
- 性能基准测试达标
- 错误处理测试通过
- 集成测试通过

## 维护指南
1. **定期运行测试**：每次代码更新后运行端到端测试
2. **更新测试用例**：新功能开发时添加相应测试用例
3. **性能监控**：持续监控测试性能，确保不退化
4. **错误处理**：记录并分析测试失败原因，持续改进