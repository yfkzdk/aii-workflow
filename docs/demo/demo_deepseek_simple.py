#!/usr/bin/env python3
"""DeepSeek API 简单测试

直接测试 DeepSeek API 调用，不经过复杂的流水线。
"""

import sys
import os
from pathlib import Path

# 设置编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 添加项目路径
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from core.agent_caller import OpenAICaller

def main():
    """主函数"""
    print("="*60)
    print("  DeepSeek API 直接测试")
    print("="*60)

    # 创建调用器
    caller = OpenAICaller()

    if not caller.client:
        print("❌ DeepSeek API 初始化失败")
        return

    print("✅ DeepSeek API 初始化成功")
    print(f"   Model: {caller.model}")
    print(f"   Base URL: {caller.base_url}")
    print()

    # 测试 1: 简单问答
    print("测试 1: 简单问答")
    print("-" * 60)
    result = caller.call(
        agent_id="test",
        task_dir=".",
        context="请用一句话介绍你自己"
    )

    if result['success']:
        print(f"✅ 成功")
        print(f"回答: {result['output']}")
        print(f"Token: {result['usage']['input_tokens']} in / {result['usage']['output_tokens']} out")
    else:
        print(f"❌ 失败: {result['error']}")

    print()

    # 测试 2: 代码生成
    print("测试 2: 代码生成")
    print("-" * 60)
    result = caller.call(
        agent_id="coder",
        task_dir=".",
        context="写一个 Python 冒泡排序函数"
    )

    if result['success']:
        print(f"✅ 成功")
        print(f"代码:\n{result['output'][:500]}...")
        print(f"\nToken: {result['usage']['input_tokens']} in / {result['usage']['output_tokens']} out")
    else:
        print(f"❌ 失败: {result['error']}")

    print()
    print("="*60)
    print("  测试完成")
    print("="*60)


if __name__ == "__main__":
    main()
