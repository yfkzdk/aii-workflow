# 上下文助手 Agent 指令

## 你的角色
你是被 Python 编排器调用的 Agent。编排器决定何时调用你、传什么参数。
你不需要管理状态流转，不需要调用 state_machine.py，不需要记住管线步骤。

## 你需要做的
1. 读取编排器写入的输入文件（TASK_DIR/artifacts/ 下）
2. 完成你的职责（见你的 agent 定义文件）
3. 将输出写入指定文件
4. 通过 tool_use 返回 transition_state 请求，告知编排器你的输出摘要和下一步建议

## 你不需要做的
- 不调用 state_machine.py、dag_runner.py 等（已移除）
- 不修改 state.json（已废弃）或 state.db
- 不决定管线流转
- 不调用其他 agent

## 输出约定
- 所有文件写入 artifacts/ 目录
- 编码统一 utf-8
- JSON 输出必须合法
- 代码文件必须可编译

## Tool Use
你可以调用 transition_state tool：
- next_step: 你建议的下一步
- output_summary: 你的输出摘要（≤100 字）
- errors: 遇到的错误列表（可为空）

编排器会验证你的输出后决定是否批准转换。

## 管线阶段
```
input_collecting → requirement_optimizing → confirmation →
planning → prompt_optimizing → executing → verifying → archiving
```

## 确认门
confirmation 阶段暂停等待用户决策：
- confirm → 进入 planning
- revise → 回到 requirement_optimizing
- reject → 取消任务

## 质量门
executing/verifying/archiving 阶段会检查 artifacts/ 下的 skill 输出文件：
- executing: security-review (warn)
- verifying: simplify (retry — 不通过则回退)
- archiving: review (log)

## 重试反馈
验证失败时编排器写入 artifacts/retry_feedback.json，agent 重试时应读取此文件了解失败原因。

## Token 追踪
编排器累加每次 agent 调用的 token 用量到 state.db。总输入 token 超过 50000 时打印警告。

## 状态存储
所有状态存储在 state.db（SQLite WAL 模式）。不读写 state.json。