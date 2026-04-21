#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文工作流编码包装器
自动修复编码问题，确保中文正确显示
"""

import os
import sys
import subprocess

def setup_encoding():
    """设置编码环境"""
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['LC_ALL'] = 'zh_CN.UTF-8'
    os.environ['LANG'] = 'zh_CN.UTF-8'

    # Windows特殊处理
    if sys.platform == 'win32':
        try:
            # 设置控制台代码页
            subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
        except:
            pass

    # 修复标准输出
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

    return True

def run_with_encoding(command, *args):
    """使用正确的编码运行命令"""
    # 设置环境
    setup_encoding()

    # 构建完整命令
    full_command = [sys.executable, command] + list(args)

    # 运行命令
    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # 输出结果
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        return result.returncode

    except Exception as e:
        print(f"执行命令失败: {e}")
        return 1

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python cn_wrapper.py <python脚本> [参数...]")
        print("示例: python cn_wrapper.py validate_encoding.py")
        return 1

    script = sys.argv[1]
    script_args = sys.argv[2:] if len(sys.argv) > 2 else []

    # 设置编码环境
    setup_encoding()

    # 运行目标脚本
    print(f"以UTF-8编码运行: {script}")
    print("-" * 60)

    return run_with_encoding(script, *script_args)

if __name__ == "__main__":
    sys.exit(main())
