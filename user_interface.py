#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文助手 - 用户友好界面
运行此脚本获得简单的交互式界面
"""

import sys
import os
import subprocess

def clear_screen():
    """清屏函数"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """打印标题"""
    print("=" * 60)
    print("           🚀 上下文助手 - 用户界面")
    print("=" * 60)
    print()

def print_menu():
    """打印主菜单"""
    print("📋 请选择操作:")
    print()
    print("  1. 📝 开始新任务")
    print("  2. 📊 查看系统状态")
    print("  3. 🔄 恢复中断的任务")
    print("  4. ℹ️  显示版本信息")
    print("  5. 🛠️  运行系统测试")
    print("  6. ❓ 显示帮助")
    print("  0. 🚪 退出")
    print()

def run_command(command):
    """运行命令并显示结果"""
    try:
        # 切换到项目目录
        project_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(project_dir)

        # 使用编码包装器运行命令
        cmd = ["python", "cn_wrapper.py", "ww_simple.py"] + command.split()

        print(f"\n🔧 执行命令: {' '.join(cmd)}")
        print("-" * 60)

        # 运行命令
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

        # 显示输出
        if result.stdout:
            print("📤 输出:")
            print(result.stdout)

        if result.stderr:
            print("⚠️  错误信息:")
            print(result.stderr)

        print("-" * 60)

        input("\n按回车键继续...")

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        input("\n按回车键继续...")

def run_test():
    """运行系统测试"""
    try:
        print("\n🧪 正在运行系统测试...")
        print("-" * 60)

        # 运行测试脚本
        project_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(project_dir)

        test_cmd = ["python", "cn_wrapper.py", "run_full_test_simple.py"]
        result = subprocess.run(test_cmd, capture_output=True, text=True, encoding='utf-8')

        # 显示简化的测试结果
        output = result.stdout

        if "所有测试通过" in output:
            print("✅ 系统测试通过！")
        elif "测试发现问题" in output:
            print("⚠️  测试发现一些问题")
        else:
            print("📋 测试完成")

        # 显示关键信息
        lines = output.split('\n')
        for line in lines:
            if "通过率" in line or "测试时间" in line or "下一步" in line:
                print(f"  {line}")

        print("-" * 60)

        # 检查测试报告
        report_file = "一键测试报告.json"
        if os.path.exists(report_file):
            try:
                import json
                with open(report_file, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                print(f"📄 测试报告: {report.get('总体状态', '未知')}")
            except:
                pass

        input("\n按回车键返回主菜单...")

    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        input("\n按回车键继续...")

def main():
    """主函数"""
    while True:
        clear_screen()
        print_header()
        print_menu()

        try:
            choice = input("请输入选项数字 (0-6): ").strip()

            if choice == "0":
                print("\n👋 再见！")
                sys.exit(0)

            elif choice == "1":
                clear_screen()
                print("=" * 60)
                print("           📝 开始新任务")
                print("=" * 60)
                print("\n请输入您的任务描述:")
                print("(示例: '请帮我分析这个项目的结构')")
                print()
                task = input("> ").strip()
                if task:
                    run_command(f'"{task}"')
                else:
                    print("❌ 任务描述不能为空")
                    input("\n按回车键继续...")

            elif choice == "2":
                run_command("status")

            elif choice == "3":
                run_command("recover")

            elif choice == "4":
                run_command("version")

            elif choice == "5":
                run_test()

            elif choice == "6":
                run_command("help")

            else:
                print("❌ 无效选项，请重新选择")
                input("\n按回车键继续...")

        except KeyboardInterrupt:
            print("\n\n👋 用户取消操作")
            sys.exit(0)
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            input("\n按回车键继续...")

if __name__ == "__main__":
    # 检查是否在项目目录中
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(script_dir, "ww_simple.py")):
        print("❌ 错误: 请在 '上下文助手' 项目目录中运行此脚本")
        print(f"当前目录: {script_dir}")
        input("按回车键退出...")
        sys.exit(1)

    try:
        main()
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        input("按回车键退出...")