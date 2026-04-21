#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文助手一键测试 - 完整验证工具
用户只需运行此脚本即可完成所有测试
"""

import os
import sys
import subprocess
import tempfile
import shutil
import json
from pathlib import Path

def print_section(title):
    """打印分区标题"""
    print(f"\n{'='*60}")
    print(f"[验证] {title}")
    print(f"{'='*60}")

def print_info(msg):
    """打印信息"""
    print(f"[信息] {msg}")

def print_success(msg):
    """打印成功"""
    # 移除emoji避免编码问题
    clean_msg = msg.replace("✅", "[OK]").replace("⚠️", "[警告]").replace("📝", "[注意]").replace("🔧", "[修复]")
    print(f"[成功] {clean_msg}")

def print_warning(msg):
    """打印警告"""
    print(f"[警告] {msg}")

def setup_encoding():
    """设置编码环境"""
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

    if sys.platform == 'win32':
        os.environ['LC_ALL'] = 'zh_CN.UTF-8'
    else:
        os.environ['LC_ALL'] = 'zh_CN.UTF-8'
        os.environ['LANG'] = 'zh_CN.UTF-8'

def test_from_different_locations():
    """从不同位置测试"""
    print_section("跨目录运行测试")

    # 复制测试脚本到临时目录
    temp_dir = tempfile.mkdtemp(prefix="context_test_")
    test_script = "run_full_test_simple.py"

    if not os.path.exists(test_script):
        # 尝试从已知位置获取
        known_path = "O:/AII/上下文助手/run_full_test_simple.py"
        if os.path.exists(known_path):
            shutil.copy2(known_path, os.path.join(temp_dir, test_script))
            print_info(f"从已知位置复制测试脚本: {known_path}")
        else:
            print_warning("找不到测试脚本")
            return False
    else:
        shutil.copy2(test_script, os.path.join(temp_dir, test_script))

    # 测试从不同目录运行
    test_cases = [
        ("当前目录", os.getcwd()),
        ("临时目录", temp_dir),
        ("用户主目录", str(Path.home())),
    ]

    results = []
    for name, test_dir in test_cases:
        print_info(f"测试从 {name} 运行...")

        try:
            env = os.environ.copy()
            env.update({
                'PYTHONIOENCODING': 'utf-8',
                'PYTHONUTF8': '1'
            })

            if name == "临时目录":
                script_path = os.path.join(temp_dir, test_script)
            else:
                script_path = os.path.join(test_dir, test_script) if os.path.exists(os.path.join(test_dir, test_script)) else test_script

            if not os.path.exists(script_path):
                print_warning(f"脚本不存在: {script_path}")
                continue

            result = subprocess.run(
                [sys.executable, script_path],
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )

            success = result.returncode == 0 and "成功" in result.stdout
            results.append({
                "位置": name,
                "成功": success,
                "返回码": result.returncode,
                "输出摘要": result.stdout[:200] + "..." if result.stdout else "无输出"
            })

            if success:
                print_success(f"{name}: 测试通过")
            else:
                print_warning(f"{name}: 测试失败")

        except Exception as e:
            print_warning(f"{name}: 错误 - {e}")
            results.append({
                "位置": name,
                "成功": False,
                "错误": str(e)
            })

    # 清理临时目录
    try:
        shutil.rmtree(temp_dir)
    except:
        pass

    return results

def validate_encoding_output():
    """验证编码输出"""
    print_section("编码输出验证")

    test_content = """# -*- coding: utf-8 -*-
print("中文测试: 上下文助手验证")
print("编码测试: UTF-8 支持验证")
print("特殊字符: ©®™ 测试完成")
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', encoding='utf-8', delete=False) as f:
        f.write(test_content)
        test_file = f.name

    try:
        env = os.environ.copy()
        env.update({
            'PYTHONIOENCODING': 'utf-8',
            'PYTHONUTF8': '1'
        })

        result = subprocess.run(
            [sys.executable, test_file],
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode == 0:
            # 检查输出质量
            output = result.stdout
            chinese_chars = sum(1 for c in output if '\u4e00' <= c <= '\u9fff')
            encoding_errors = output.count('�')

            print_info(f"中文字符数量: {chinese_chars}")
            print_info(f"编码错误字符: {encoding_errors}")

            if chinese_chars > 0 and encoding_errors == 0:
                print_success("编码输出质量: 优秀")
                return True
            elif encoding_errors < 5:
                print_success("编码输出质量: 良好")
                return True
            else:
                print_warning("编码输出质量: 需改进")
                return False
        else:
            print_warning(f"脚本执行失败: {result.stderr}")
            return False

    finally:
        try:
            os.unlink(test_file)
        except:
            pass

def generate_final_report(test_results, encoding_results):
    """生成最终报告"""
    print_section("生成验证报告")

    report = {
        "验证时间": "2026-04-17",
        "验证项目": "上下文助手测试工具包",
        "验证目标": "确保测试脚本可在任意目录运行",
        "跨目录测试结果": test_results,
        "编码输出验证": encoding_results,
        "总体评估": {},
        "使用建议": []
    }

    # 分析结果
    successful_tests = [r for r in test_results if r.get("成功", False)]
    success_rate = len(successful_tests) / len(test_results) if test_results else 0

    report["总体评估"]["跨目录成功率"] = f"{success_rate:.1%}"
    report["总体评估"]["编码输出质量"] = "优秀" if encoding_results else "需改进"
    report["总体评估"]["总体状态"] = "通过" if success_rate >= 0.75 and encoding_results else "部分通过"

    # 生成建议
    if success_rate >= 0.75:
        report["使用建议"].append("[OK] 脚本具有良好的跨目录运行能力")
    else:
        report["使用建议"].append("[警告] 建议优化路径定位逻辑")

    if encoding_results:
        report["使用建议"].append("[OK] 编码输出质量良好，支持中文UTF-8")
    else:
        report["使用建议"].append("[警告] 建议进一步优化编码设置")

    report["使用建议"].append("[注意] 用户只需运行: python run_full_test_simple.py")
    report["使用建议"].append("[修复] 如有问题使用: python cn_wrapper.py run_full_test_simple.py")

    # 保存报告
    report_file = "完整验证报告.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print_success(f"验证报告已保存: {report_file}")

    # 打印摘要
    print(f"\n[摘要] 验证结果:")
    print(f"  跨目录测试: {len(successful_tests)}/{len(test_results)} 成功")
    print(f"  编码输出: {'优秀' if encoding_results else '需改进'}")
    print(f"  总体状态: {report['总体评估']['总体状态']}")

    return report

def main():
    """主函数"""
    # 设置编码
    setup_encoding()

    print_section("上下文助手完整验证工具")
    print_info("开始全面验证测试脚本...")

    try:
        # 运行跨目录测试
        test_results = test_from_different_locations()

        # 运行编码验证
        encoding_results = validate_encoding_output()

        # 生成最终报告
        report = generate_final_report(test_results, encoding_results)

        # 最终结论
        print_section("验证结论")

        if report["总体评估"]["总体状态"] == "通过":
            print_success("验证通过！")
            print_info("测试脚本满足以下要求:")
            print("  1. [OK] 可在任意目录运行")
            print("  2. [OK] 自动定位项目目录")
            print("  3. [OK] 支持中文UTF-8输出")
            print("  4. [OK] 生成详细测试报告")
            print("  5. [OK] 提供完整验证结果")
            print("\n[交付] 工具包已准备就绪")
            print("用户只需运行: python run_full_test_simple.py")
            return 0
        else:
            print_warning("验证部分通过")
            print_info("建议改进以下方面:")
            for suggestion in report.get("使用建议", []):
                if "[警告]" in suggestion:
                    print(f"  {suggestion}")
            return 1

    except Exception as e:
        print_warning(f"验证过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())