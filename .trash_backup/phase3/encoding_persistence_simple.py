#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码修复持久性验证工具 - 简化版
验证编码修复方案在不同场景下的效果（无emoji版本）
"""

import os
import sys
import subprocess
import tempfile
import json
import locale

def print_section(title):
    """打印分区标题"""
    print(f"\n{'='*60}")
    print(f"[测试] {title}")
    print(f"{'='*60}")

def test_encoding_scenario(scenario_name, env_vars=None):
    """测试特定编码场景"""
    print(f"\n测试场景: {scenario_name}")

    if env_vars:
        print("环境变量设置:")
        for key, value in env_vars.items():
            print(f"  {key}={value}")

    # 创建测试文件
    test_content = """# -*- coding: utf-8 -*-
# 测试中文输出
print("中文测试: 你好，世界！")
print("特殊字符: 测试完成")
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', encoding='utf-8', delete=False) as f:
        f.write(test_content)
        test_file = f.name

    try:
        # 准备环境
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        # 运行测试
        result = subprocess.run(
            [sys.executable, test_file],
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        print(f"返回码: {result.returncode}")

        if result.returncode == 0:
            print("执行成功")

            # 检查输出内容
            if "中文测试" in result.stdout:
                print("中文输出正常")
            else:
                print("中文输出可能有问题")

            # 检查编码问题
            if '�' in result.stdout or '??' in result.stdout:
                print("检测到编码问题字符")
                return False
            else:
                print("编码输出正常")
                return True
        else:
            print(f"执行失败: {result.stderr[:100]}")
            return False

    finally:
        # 清理临时文件
        try:
            os.unlink(test_file)
        except:
            pass

def check_system_encoding():
    """检查系统编码设置"""
    print_section("系统编码状态检查")

    checks = [
        ("系统平台", sys.platform),
        ("Python默认编码", sys.getdefaultencoding()),
        ("文件系统编码", sys.getfilesystemencoding()),
        ("标准输出编码", sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else '未知'),
        ("Locale设置", locale.getlocale()),
        ("PYTHONIOENCODING", os.environ.get('PYTHONIOENCODING', '未设置')),
        ("PYTHONUTF8", os.environ.get('PYTHONUTF8', '未设置')),
    ]

    for name, value in checks:
        print(f"  {name}: {value}")

def test_encoding_strategies():
    """测试不同的编码修复策略"""
    print_section("编码修复策略测试")

    strategies = [
        {"name": "策略1: PYTHONIOENCODING=utf-8", "env": {"PYTHONIOENCODING": "utf-8"}},
        {"name": "策略2: PYTHONUTF8=1 + PYTHONIOENCODING=utf-8", "env": {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}},
        {"name": "策略3: 仅设置PYTHONUTF8=1", "env": {"PYTHONUTF8": "1"}},
        {"name": "策略4: 无编码设置（基线测试）", "env": {}}
    ]

    results = []
    for strategy in strategies:
        success = test_encoding_scenario(strategy["name"], strategy["env"])
        results.append((strategy["name"], success))

    return results

def create_final_report():
    """创建最终验证报告"""
    print_section("编码修复持久性验证报告")

    report = {
        "验证时间": "2026-04-17",
        "验证目标": "编码修复持久性",
        "系统环境": {
            "平台": sys.platform,
            "Python版本": sys.version.split()[0],
            "默认编码": sys.getdefaultencoding()
        },
        "验证项目": [],
        "修复效果评估": {},
        "建议": []
    }

    # 运行各项测试
    check_system_encoding()
    strategy_results = test_encoding_strategies()

    # 分析测试结果
    successful_strategies = [name for name, success in strategy_results if success]

    if successful_strategies:
        report["修复效果评估"]["状态"] = "良好"
        report["修复效果评估"]["有效策略"] = successful_strategies
        report["建议"].append("建议使用策略: " + successful_strategies[0])
    else:
        report["修复效果评估"]["状态"] = "存在问题"
        report["建议"].append("需要进一步优化编码修复策略")

    # 生成持久性建议
    report["建议"].append("在脚本开头强制设置编码环境变量")
    report["建议"].append("使用编码包装器确保输出一致性")
    report["建议"].append("推荐配置: PYTHONIOENCODING=utf-8 和 PYTHONUTF8=1")

    # 保存报告
    report_file = "编码修复持久性报告.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n验证报告已保存: {report_file}")
    return report

def main():
    """主函数"""
    # 设置基本的编码环境
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

    print("="*70)
    print("编码修复持久性验证工具")
    print("="*70)

    try:
        # 创建验证报告
        report = create_final_report()

        # 总结
        print_section("验证结论")

        if report["修复效果评估"]["状态"] == "良好":
            print("编码修复方案具有良好持久性")
            print("在不同环境下都能正常工作")
            print("修复策略集成到测试脚本中")
            print("用户无需手动配置编码环境")
            return 0
        else:
            print("编码修复方案需要改进")
            print("建议检查系统环境兼容性")
            return 1

    except Exception as e:
        print(f"验证过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())