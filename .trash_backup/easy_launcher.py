# -*- coding: utf-8 -*-
"""
超简单启动器 - 没有任何编码问题
使用方法：
1. 运行：python easy_launcher.py "你的任务"
2. 或者双击运行：easy_launcher.bat
"""
import sys
import os

def main():
    print("=" * 60)
    print("AI上下文助手 - 超简单启动器")
    print("=" * 60)
    print()

    if len(sys.argv) > 1:
        # 如果有参数，直接启动任务
        task = " ".join(sys.argv[1:])
        print(f"任务：{task}")
        print()
        print("请复制以下内容到Claude Code：")
        print("=" * 60)
        print()
        print(f"启动AII上下文助手工作流，任务：{task}")
        print(f"工作流路径：O:\\AII\\上下文助手")
        print()
        print("=" * 60)
        return

    # 交互模式
    print("使用方法：")
    print("  1. python easy_launcher.py \"你的任务描述\"")
    print("  2. 或者双击 easy_launcher.bat")
    print()
    print("示例：")
    print('  python easy_launcher.py "帮我写个Python脚本"')
    print()

    # 问用户要任务
    task = input("请输入你的任务描述（直接回车跳过）：").strip()

    if task:
        print()
        print("请复制以下内容到Claude Code：")
        print("=" * 60)
        print()
        print(f"启动AII上下文助手工作流，任务：{task}")
        print(f"工作流路径：O:\\AII\\上下文助手")
        print()
        print("=" * 60)

    input("\n按回车键退出...")

if __name__ == "__main__":
    # 设置编码
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    main()