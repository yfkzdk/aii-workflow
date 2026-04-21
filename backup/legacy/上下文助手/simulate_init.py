import json, os
from pathlib import Path
from datetime import datetime

# 创建必要的目录
task_dir = "workflows/test-fib"
artifacts_dir = os.path.join(task_dir, "artifacts")
os.makedirs(task_dir, exist_ok=True)
os.makedirs(artifacts_dir, exist_ok=True)

# 1. 创建state.json
state_data = {
    "task_id": "test-fib",
    "status": "planning",
    "pipeline": ["planning", "prompt_optimizing", "executing", "verifying", "archiving"],
    "current_step_index": 0,
    "retry_count": 0,
    "max_retries": 3,
    "next_agent": "planner",
    "checkpoint": {},
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat()
}

state_path = os.path.join(task_dir, "state.json")
with open(state_path, "w", encoding="utf-8") as f:
    json.dump(state_data, f, indent=2, ensure_ascii=False)

print("创建 state.json 内容:")
print(json.dumps(state_data, indent=2, ensure_ascii=False))

# 2. 创建input.md
input_content = """# 🧪 测试任务：计算斐波那契数列

## 任务描述
编写一个 Python 函数，计算并返回斐波那契数列的前 N 项。

## 要求
- 函数名：fibonacci_sequence
- 参数：n（整数，表示要计算的项数）
- 返回值：包含前 n 个斐波那契数的列表
- 处理边缘情况：n <= 0 时返回空列表，n = 1 时返回 [0]
- 要求代码简洁、高效、有良好的注释
- 包含单元测试

## 验收标准
1. ✅ 函数能正确计算前 10 项斐波那契数列：[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
2. ✅ 处理 n <= 0 的边缘情况
3. ✅ 代码有完整的文档字符串
4. ✅ 包含简单的测试代码
5. ✅ 代码风格符合 PEP 8
"""

input_path = os.path.join(task_dir, "input.md")
with open(input_path, "w", encoding="utf-8") as f:
    f.write(input_content)

print(f"\n创建 input.md 文件: {input_path}")
print("=" * 50)