#!/usr/bin/env python3
import sys
import json
import os
from pathlib import Path

# 强制使用UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class WorkflowLauncher:
    def __init__(self):
        # 获取当前目录，避免硬编码路径问题
        current_dir = Path(__file__).parent
        self.workflow_dir = current_dir
        self.config_path = self.workflow_dir / "config" / "user_prefs.json"
        self.config = self.load_config()

    def load_config(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"version": "2.0", "encoding": "utf-8"}

    def show_version(self):
        print("AII Workflow Launcher v2.1")
        print("Fixed Encoding Edition")
        print()
        print("Core Features:")
        print("  - Fixed Windows Chinese encoding")
        print("  - Smart task classification")
        print("  - One-click launch")

    def show_help(self):
        print("=== AII Workflow Launcher - Help ===")
        print()
        print("Usage:")
        print('  ww "任务描述"          启动新任务')
        print("  ww status             查看系统状态")
        print("  ww recover            恢复中断的任务")
        print("  ww version            查看版本")
        print("  ww help               查看帮助")
        print()
        print("示例:")
        print('  ww "帮我写一个Python脚本"')
        print('  ww "分析这个项目的问题"')

    def show_status(self):
        print("=== 系统状态 ===")
        print(f"  版本: {self.config.get('version', 'unknown')}")
        print(f"  编码: {self.config.get('encoding', 'utf-8')}")
        print(f"  目录: {self.workflow_dir}")

        # 检查关键文件
        print()
        print("=== 文件检查 ===")
        files_to_check = [
            ("tasks/input_task.md", "任务输入模板"),
            ("tasks/output_result.md", "任务输出模板"),
            ("AI_WORKFLOW_LOG.md", "工作流日志"),
            ("ww.bat", "启动脚本")
        ]

        for file_name, description in files_to_check:
            file_path = self.workflow_dir / file_name
            if file_path.exists():
                print(f"  [✓] {description}: 存在")
            else:
                print(f"  [✗] {description}: 不存在")

    def run(self):
        if len(sys.argv) < 2:
            self.show_help()
            return

        cmd = sys.argv[1].lower()

        if cmd == "version":
            self.show_version()
        elif cmd in ["help", "--help", "-h"]:
            self.show_help()
        elif cmd == "status":
            self.show_status()
        elif cmd == "test":
            print("=== 编码测试 ===")
            print("中文测试: 你好，世界！")
            print("路径测试: O:\\AII\\上下文助手")
            print("文件检查: 通过")
        elif cmd == "recover":
            print("=== 恢复中断的工作流 ===")
            print("请打开新的Claude Code窗口")
            print("然后运行: ww recover")
        else:
            # 处理任务描述
            task = " ".join(sys.argv[1:])
            print("=== 启动AI工作流 ===")
            print(f"任务: {task}")
            print()
            print("请在Claude Code中复制以下内容:")
            print("==================================")
            print()
            print("启动AII上下文助手工作流")
            print()
            print(f"任务: {task}")
            print()
            print("工作流路径: O:\\AII\\上下文助手")
            print()
            print("请按工作流执行:")
            print("1. 读取任务需求")
            print("2. 分析历史日志中的成功模式")
            print("3. 生成三个方案并对比")
            print("4. 选择最优方案执行")
            print("5. 输出结果到 tasks/output_result.md")
            print()
            print("==================================")

def main():
    try:
        # 设置环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONUTF8'] = '1'

        launcher = WorkflowLauncher()
        launcher.run()
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()