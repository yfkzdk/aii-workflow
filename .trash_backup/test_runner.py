#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文助手测试工具包 - 统一入口脚本
整合所有测试功能，提供最简单的使用方式
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def setup_encoding():
    """设置编码环境"""
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

    if sys.platform == 'win32':
        os.environ['LC_ALL'] = 'zh_CN.UTF-8'
    else:
        os.environ['LC_ALL'] = 'zh_CN.UTF-8'
        os.environ['LANG'] = 'zh_CN.UTF-8'

def run_quick_test():
    """运行快速测试"""
    print("\n" + "="*60)
    print("[测试] 运行快速测试")
    print("="*60)

    try:
        result = subprocess.run(
            [sys.executable, "run_full_test_simple.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        print(result.stdout)

        if result.returncode == 0:
            print("[成功] 快速测试完成！")
            print("[下一步] 查看测试报告: 一键测试报告.json")
            return True
        else:
            print("[警告] 快速测试发现一些问题")
            if result.stderr:
                print(f"[错误] {result.stderr[:200]}")
            return False

    except Exception as e:
        print(f"[错误] 运行快速测试失败: {e}")
        return False

def run_encoding_test():
    """运行编码测试"""
    print("\n" + "="*60)
    print("[测试] 运行编码测试")
    print("="*60)

    try:
        result = subprocess.run(
            [sys.executable, "validate_encoding.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        print(result.stdout)

        if result.returncode == 0:
            print("[成功] 编码测试完成")
            return True
        else:
            print("[警告] 编码测试发现问题")
            return False

    except Exception as e:
        print(f"[错误] 运行编码测试失败: {e}")
        return False

def run_complete_validation():
    """运行完整验证"""
    print("\n" + "="*60)
    print("[测试] 运行完整验证")
    print("="*60)

    try:
        result = subprocess.run(
            [sys.executable, "complete_validation.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        print(result.stdout)

        if result.returncode == 0:
            print("[成功] 完整验证完成")
            print("[下一步] 查看验证报告: 完整验证报告.json")
            return True
        else:
            print("[警告] 完整验证发现问题")
            return False

    except Exception as e:
        print(f"[错误] 运行完整验证失败: {e}")
        return False

def fix_encoding():
    """修复编码问题"""
    print("\n" + "="*60)
    print("[修复] 修复编码问题")
    print("="*60)

    try:
        result = subprocess.run(
            [sys.executable, "fix_encoding_issues.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        print(result.stdout)

        if result.returncode == 0:
            print("[成功] 编码修复完成")
            return True
        else:
            print("[警告] 编码修复可能未完全成功")
            return False

    except Exception as e:
        print(f"[错误] 运行编码修复失败: {e}")
        return False

def show_help():
    """显示帮助信息"""
    help_text = """
上下文助手测试工具包 - 统一入口

使用方法:
  python test_runner.py [选项]

选项:
  --quick       快速测试 (默认)
  --encoding    编码测试
  --full        完整验证
  --fix         修复编码问题
  --all         运行所有测试
  --help        显示此帮助信息

示例:
  1. 快速测试 (推荐):
     python test_runner.py --quick

  2. 运行所有测试:
     python test_runner.py --all

  3. 仅修复编码问题:
     python test_runner.py --fix

  4. 编码测试:
     python test_runner.py --encoding

功能说明:
  --quick:    基本功能测试，检查项目完整性
  --encoding: 详细编码环境验证
  --full:     完整功能验证，包括跨目录测试
  --fix:      修复编码问题和环境配置
  --all:      运行所有测试和修复

输出文件:
  一键测试报告.json          - 快速测试结果
  编码环境诊断报告.json      - 编码环境信息
  完整验证报告.json         - 完整验证结果
  编码修复持久性报告.json   - 编码修复验证

技术支持:
  如有问题，请查看:
  1. FINAL_TEST_PACKAGE.md    - 交付包说明
  2. encoding_config_guide.md - 编码配置指南
  3. UPGRADE_WORK_LOG.md      - 完整工作日志
"""
    print(help_text)

def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("[测试] 运行所有测试和验证")
    print("="*60)

    results = []

    # 1. 修复编码
    print("\n[步骤1] 修复编码问题...")
    if fix_encoding():
        results.append(("编码修复", "成功"))
    else:
        results.append(("编码修复", "警告"))

    # 2. 编码测试
    print("\n[步骤2] 运行编码测试...")
    if run_encoding_test():
        results.append(("编码测试", "成功"))
    else:
        results.append(("编码测试", "失败"))

    # 3. 快速测试
    print("\n[步骤3] 运行快速测试...")
    if run_quick_test():
        results.append(("快速测试", "成功"))
    else:
        results.append(("快速测试", "失败"))

    # 4. 完整验证
    print("\n[步骤4] 运行完整验证...")
    if run_complete_validation():
        results.append(("完整验证", "成功"))
    else:
        results.append(("完整验证", "失败"))

    # 显示结果汇总
    print("\n" + "="*60)
    print("[汇总] 所有测试结果")
    print("="*60)

    success_count = sum(1 for _, status in results if status == "成功")
    total_count = len(results)

    for test_name, status in results:
        if status == "成功":
            print(f"  ✅ {test_name}: {status}")
        elif status == "警告":
            print(f"  ⚠️ {test_name}: {status}")
        else:
            print(f"  ❌ {test_name}: {status}")

    print(f"\n[统计] 成功: {success_count}/{total_count}")

    if success_count == total_count:
        print("[结论] 所有测试通过！")
        print("[建议] 您可以开始使用上下文助手")
        return True
    elif success_count >= total_count * 0.75:
        print("[结论] 大部分测试通过")
        print("[建议] 检查警告和失败的测试")
        return True
    else:
        print("[结论] 测试发现问题较多")
        print("[建议] 运行编码修复并重新测试")
        return False

def main():
    """主函数"""
    # 设置编码
    setup_encoding()

    # 解析参数
    parser = argparse.ArgumentParser(description='上下文助手测试工具包', add_help=False)
    parser.add_argument('--quick', action='store_true', help='快速测试')
    parser.add_argument('--encoding', action='store_true', help='编码测试')
    parser.add_argument('--full', action='store_true', help='完整验证')
    parser.add_argument('--fix', action='store_true', help='修复编码问题')
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    parser.add_argument('--help', action='store_true', help='显示帮助信息')

    args = parser.parse_args()

    print("="*70)
    print("上下文助手测试工具包 - 统一入口")
    print("="*70)

    # 检查是否有任何参数
    if args.help or (not args.quick and not args.encoding and not args.full and not args.fix and not args.all):
        show_help()
        sys.exit(0)

    # 运行相应的测试
    success = True

    try:
        if args.all:
            success = run_all_tests()
        elif args.fix:
            success = fix_encoding()
        elif args.encoding:
            success = run_encoding_test()
        elif args.full:
            success = run_complete_validation()
        elif args.quick:
            success = run_quick_test()

        # 最终结果
        print("\n" + "="*60)
        if success:
            print("[完成] 测试执行完成")
            print("[下一步] 查看生成的报告文件")
            sys.exit(0)
        else:
            print("[完成] 测试发现问题")
            print("[建议] 运行 --fix 修复编码问题")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n[中断] 测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n[错误] 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()