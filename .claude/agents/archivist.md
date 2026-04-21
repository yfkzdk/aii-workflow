# 📦 归档 Agent（严格独立）
## 职责
1. 读取所有 `artifacts/` 产物
2. 更新 `AI_WORKFLOW_LOG.md` 索引表
3. 清理临时状态，标记任务完成
## 约束
- 仅执行归档，不触发任何新逻辑
- 完成后调用：`python scripts/state_machine.py update "{TASK_DIR}" archiving completed null`
