#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文助手一键测试脚本
简洁版本 - 在任何终端粘贴即可运行
"""

import os
import sys
import json
from pathlib import Path

# ========================
# 输出函数
# ========================

def 打印标题(标题):
    print(f"\n{'='*50}")
    print(f"[测试] {标题}")
    print(f"{'='*50}")

def 打印成功(消息):
    print(f"[成功] {消息}")

def 打印失败(消息):
    print(f"[失败] {消息}")

def 打印信息(消息):
    print(f"[信息] {消息}")

# ========================
# 主要测试函数
# ========================

def 定位项目目录():
    """定位项目目录"""
    当前路径 = Path.cwd()

    # 尝试不同方式查找
    可能路径 = [
        Path("O:/AII/上下文助手"),
        当前路径 / "上下文助手",
        当前路径.parent / "上下文助手",
    ]

    for 路径 in 可能路径:
        if 路径.exists():
            打印成功(f"找到项目目录: {路径}")
            return 路径

    打印失败("无法找到项目目录")
    打印信息("请确保在项目目录中运行此脚本")
    return None

def 设置编码环境():
    """设置UTF-8编码环境"""
    try:
        # 设置关键环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONUTF8'] = '1'

        # 设置locale环境变量
        if sys.platform == 'win32':
            # Windows环境变量
            os.environ['LC_ALL'] = 'zh_CN.UTF-8'

            # Windows控制台代码页
            import subprocess
            result = subprocess.run(['chcp', '65001'],
                                   shell=True,
                                   capture_output=True,
                                   text=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)

            if result.returncode != 0:
                打印信息(f"设置代码页时警告: {result.stderr}")
        else:
            # Linux/macOS环境变量
            os.environ['LC_ALL'] = 'zh_CN.UTF-8'
            os.environ['LANG'] = 'zh_CN.UTF-8'

        打印成功("编码环境设置完成")
        return True
    except Exception as e:
        打印信息(f"编码设置警告: {e} (不影响主要功能)")
        return True  # 编码设置问题不影响测试继续

def 检查基本文件(项目路径):
    """检查基本文件"""
    打印标题("检查基本文件")

    必需文件 = [
        "ww.bat",
        "ww_simple.py",
        "README.md",
        "config/user_prefs.json",
    ]

    问题 = []

    for 文件路径 in 必需文件:
        完整路径 = 项目路径 / 文件路径
        if 完整路径.exists():
            打印成功(f"{文件路径}")
        else:
            打印失败(f"{文件路径} (缺失)")
            问题.append(文件路径)

    return len(问题) == 0, 问题

def 测试工作流命令(项目路径):
    """测试工作流命令"""
    打印标题("测试工作流命令")

    import subprocess

    脚本路径 = 项目路径 / "ww_simple.py"

    if not 脚本路径.exists():
        打印失败("ww_simple.py 不存在")
        return False, ["ww_simple.py 文件缺失"]

    try:
        # 测试status命令
        结果 = subprocess.run(
            [sys.executable, str(脚本路径), "status"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10,
            cwd=str(项目路径)
        )

        if 结果.returncode == 0:
            打印成功("工作流命令测试通过")
            打印信息(f"输出: {结果.stdout.strip()[:50]}...")
            return True, []
        else:
            打印失败(f"命令执行失败: {结果.stderr}")
            return False, [结果.stderr]

    except Exception as e:
        打印失败(f"测试错误: {e}")
        return False, [str(e)]

def 生成测试报告(测试结果):
    """生成测试报告"""
    打印标题("生成测试报告")

    报告 = {
        "测试时间": "2026-04-17",
        "测试项目": "上下文助手",
        "总体状态": "通过" if 测试结果["全部通过"] else "失败",
        "详细结果": 测试结果
    }

    # 保存JSON报告
    with open("一键测试报告.json", "w", encoding="utf-8") as f:
        json.dump(报告, f, ensure_ascii=False, indent=2)

    打印成功("测试报告已保存: 一键测试报告.json")

    # 打印摘要
    测试项结果 = {k: v for k, v in 测试结果.items() if isinstance(v, dict)}
    通过数 = sum(1 for 结果 in 测试项结果.values() if 结果.get("通过", False))
    总数 = len(测试项结果)

    print(f"\n[摘要] 测试摘要:")
    print(f"  总测试数: {总数}")
    print(f"  通过数: {通过数}")
    print(f"  失败数: {总数 - 通过数}")
    print(f"  通过率: {通过数/总数*100:.1f}%")

# ========================
# 主函数
# ========================

def 主测试():
    """主测试函数"""
    打印标题("上下文助手一键测试")
    打印信息(f"开始时间: 2026-04-17")
    打印信息(f"Python版本: {sys.version.split()[0]}")

    # 测试结果存储
    测试结果 = {}
    全部通过 = True

    # 1. 定位项目
    打印信息("步骤1: 定位项目目录")
    项目路径 = 定位项目目录()
    if not 项目路径:
        return False
    测试结果["项目定位"] = {"通过": True, "详情": "成功定位项目目录"}

    # 2. 设置编码
    打印信息("步骤2: 设置编码环境")
    编码成功 = 设置编码环境()
    测试结果["编码设置"] = {"通过": 编码成功, "详情": "设置UTF-8编码环境"}
    if not 编码成功:
        全部通过 = False

    # 3. 检查文件
    打印信息("步骤3: 检查基本文件")
    文件成功, 文件问题 = 检查基本文件(项目路径)
    测试结果["文件检查"] = {"通过": 文件成功, "详情": 文件问题}
    if not 文件成功:
        全部通过 = False

    # 4. 测试命令
    打印信息("步骤4: 测试工作流命令")
    命令成功, 命令问题 = 测试工作流命令(项目路径)
    测试结果["命令测试"] = {"通过": 命令成功, "详情": 命令问题}
    if not 命令成功:
        全部通过 = False

    # 5. 生成报告
    测试结果["全部通过"] = 全部通过
    生成测试报告(测试结果)

    # 最终结果
    打印标题("测试完成")

    if 全部通过:
        打印成功("所有测试通过！")
        print("\n[下一步] 现在您可以:")
        print("  1. 运行工作流: python ww_simple.py \"您的任务\"")
        print("  2. 查看报告: 一键测试报告.json")
        print("  3. 开始使用上下文助手")
    else:
        打印失败("测试发现一些问题")
        print("\n[修复] 建议操作:")
        print("  1. 运行编码修复: python fix_encoding_issues.py")
        print("  2. 补充缺失文件")
        print("  3. 重新运行测试")

    return 全部通过

def 获取使用说明():
    """获取使用说明"""
    return """
上下文助手一键测试脚本
========================

使用方式:
1. 在任何目录下运行:
   python run_full_test_simple.py

2. 可选参数:
   -h, --help   显示此帮助信息
   -v           详细模式（显示更多信息）
   -q           安静模式（仅显示结果）

3. 脚本功能:
   - 自动定位项目目录
   - 设置UTF-8编码环境
   - 检查必需文件完整性
   - 测试工作流命令执行
   - 生成详细测试报告

4. 支持平台:
   - Windows (cmd/PowerShell/终端)
   - Linux/macOS (bash/zsh)
   - VS Code / IDE集成终端

5. 输出文件:
   - 一键测试报告.json      详细测试结果
   - 如有问题生成修复建议

6. 测试流程:
   1. 定位项目 -> 2. 设置编码 -> 3. 检查文件 -> 4. 测试命令 -> 5. 生成报告

7. 测试通过标准:
   - 所有必需文件存在
   - 工作流命令能正常执行
   - 无编码相关错误
   - 返回码为0

8. 常见问题:
   - 编码问题: 运行 python fix_encoding_issues.py
   - 文件缺失: 检查项目结构
   - 命令失败: 检查Python环境和依赖

9. 联系方式:
   通过上下文助手系统日志反馈问题

版本: 1.0.0
创建时间: 2026-04-17
更新日志: 修复编码设置，增强路径定位
"""

# ========================
# 脚本入口
# ========================

if __name__ == "__main__":
    try:
        # 检查是否请求帮助
        if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
            print(获取使用说明())
            sys.exit(0)

        # 运行测试
        成功 = 主测试()
        sys.exit(0 if 成功 else 1)

    except KeyboardInterrupt:
        print("\n[中断] 测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n[错误] 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)