#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文编码环境验证工具
确保所有脚本在UTF-8环境下正常运行，支持纯中文输出
"""

import os
import sys
import locale
import json
from pathlib import Path

# 设置编码环境
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 中文输出函数
def 输出成功(消息):
    """输出成功信息"""
    print(f"[成功] {消息}")

def 输出错误(消息):
    """输出错误信息"""
    print(f"[错误] {消息}")

def 输出信息(消息):
    """输出信息"""
    print(f"[信息] {消息}")

def 输出标题(标题):
    """输出标题"""
    print("\n" + "=" * 60)
    print(f"[标题] {标题}")
    print("=" * 60)

def 检查Python编码环境():
    """检查Python编码环境"""
    输出标题("Python编码环境检查")

    问题列表 = []

    # 检查Python默认编码
    默认编码 = sys.getdefaultencoding()
    输出信息(f"Python默认编码: {默认编码}")
    if 默认编码.lower() != 'utf-8':
        问题列表.append(f"Python默认编码不是UTF-8: {默认编码}")

    # 检查文件系统编码
    文件系统编码 = sys.getfilesystemencoding()
    输出信息(f"文件系统编码: {文件系统编码}")
    if 文件系统编码.lower() != 'utf-8':
        问题列表.append(f"文件系统编码不是UTF-8: {文件系统编码}")

    # 检查标准输出编码
    try:
        标准输出编码 = sys.stdout.encoding
        输出信息(f"标准输出编码: {标准输出编码}")
        if 标准输出编码.lower() != 'utf-8':
            问题列表.append(f"标准输出编码不是UTF-8: {标准输出编码}")
    except:
        输出信息("标准输出编码: 无法检测")

    return 问题列表

def 检查环境变量():
    """检查环境变量"""
    输出标题("环境变量检查")

    问题列表 = []

    # 检查关键环境变量
    关键变量 = {
        'PYTHONIOENCODING': 'utf-8',
        'LC_ALL': 'zh_CN.UTF-8',
        'LANG': 'zh_CN.UTF-8'
    }

    for 变量名, 期望值 in 关键变量.items():
        实际值 = os.getenv(变量名, '未设置')
        输出信息(f"{变量名}: {实际值}")

        if 实际值 == '未设置':
            问题列表.append(f"环境变量 {变量名} 未设置")
        elif 期望值 not in 实际值.lower():
            问题列表.append(f"环境变量 {变量名} 不是 {期望值}: {实际值}")

    return 问题列表

def 检查系统Locale():
    """检查系统Locale设置"""
    输出标题("系统Locale检查")

    问题列表 = []

    try:
        # 获取当前locale
        当前locale = locale.getlocale()
        输出信息(f"当前locale: {当前locale}")

        # 检查是否为中文UTF-8环境
        locale_ok = False
        for item in 当前locale:
            if item and ('zh_cn' in str(item).lower() or 'utf-8' in str(item).lower()):
                locale_ok = True
                break

        if not locale_ok:
            问题列表.append(f"Locale设置不包含中文UTF-8: {当前locale}")

        # 获取所有locale设置
        所有locale = locale.locale_alias
        中文locale数量 = sum(1 for k in 所有locale.keys() if 'zh_cn' in k.lower())
        输出信息(f"系统中已配置的中文locale数量: {中文locale数量}")

    except Exception as e:
        输出错误(f"获取locale信息失败: {e}")
        问题列表.append(f"Locale检测失败: {e}")

    return 问题列表

def 测试中文字符处理():
    """测试中文字符处理能力"""
    输出标题("中文字符处理测试")

    问题列表 = []

    # 测试1: 控制台输出
    try:
        测试文本 = "这是一段中文测试文字！包含特殊符号：测试是否支持完整UTF-8编码。"
        print(f"控制台输出测试: {测试文本}")
        输出成功("控制台输出测试通过")
    except Exception as e:
        输出错误(f"控制台输出测试失败: {e}")
        问题列表.append(f"控制台输出失败: {e}")

    # 测试2: 文件读写
    try:
        临时文件 = "编码测试_临时文件.txt"

        # 写入文件
        写入内容 = "UTF-8编码测试内容 - 中文测试 特殊符号测试"
        with open(临时文件, 'w', encoding='utf-8') as 文件:
            文件.write(写入内容)
        输出成功("文件写入测试通过")

        # 读取文件
        with open(临时文件, 'r', encoding='utf-8') as 文件:
            读取内容 = 文件.read()

        if 读取内容 == 写入内容:
            输出成功("文件读取测试通过")
            print(f"  读取内容: {读取内容}")
        else:
            输出错误(f"文件读取内容不匹配")
            问题列表.append("文件读取内容不匹配")

        # 清理临时文件
        os.remove(临时文件)
        输出成功("临时文件清理成功")

    except Exception as e:
        输出错误(f"文件读写测试失败: {e}")
        问题列表.append(f"文件读写失败: {e}")

    # 测试3: JSON处理
    try:
        测试数据 = {
            "项目": "上下文助手",
            "描述": "这是一个中文测试项目",
            "状态": "测试中",
            "特殊字符": "测试字符",
            "列表测试": ["项目1", "项目2", "项目3"]
        }

        # 序列化
        json_str = json.dumps(测试数据, ensure_ascii=False, indent=2)
        输出成功("JSON序列化测试通过")

        # 反序列化
        解析数据 = json.loads(json_str)
        if 解析数据 == 测试数据:
            输出成功("JSON反序列化测试通过")
        else:
            输出错误("JSON反序列化数据不匹配")
            问题列表.append("JSON反序列化失败")

    except Exception as e:
        输出错误(f"JSON处理测试失败: {e}")
        问题列表.append(f"JSON处理失败: {e}")

    return 问题列表

def 检查项目文件编码():
    """检查项目文件编码"""
    输出标题("项目文件编码检查")

    问题列表 = []
    项目根目录 = Path("O:/AII/上下文助手")

    # 要检查的文件类型
    文件扩展名 = ['.py', '.md', '.json', '.txt', '.bat', '.ps1', '.sh']

    for 扩展 in 文件扩展名:
        文件列表 = list(项目根目录.rglob(f"*{扩展}"))
        for 文件路径 in 文件列表[:10]:  # 限制检查数量
            try:
                # 检查文件头部是否包含编码声明
                with open(文件路径, 'r', encoding='utf-8', errors='ignore') as 文件:
                    内容 = 文件.read(200)  # 只读取前200个字符

                # 对于Python文件，检查是否有编码声明
                if 扩展 == '.py' and '# -*- coding: utf-8 -*-' not in 内容:
                    # 如果是脚本文件但不是测试工具，建议添加编码声明
                    if 'test' not in str(文件路径).lower() and 'encoding' not in str(文件路径).lower():
                        相对路径 = 文件路径.relative_to(项目根目录)
                        问题列表.append(f"Python文件缺少编码声明: {相对路径}")

            except Exception as e:
                输出错误(f"检查文件 {文件路径.name} 时出错: {e}")

    if not 问题列表:
        输出成功("项目文件编码检查通过")

    return 问题列表

def 生成修复建议(问题列表):
    """生成编码修复建议"""
    if not 问题列表:
        return []

    输出标题("编码问题修复建议")

    修复建议 = []

    for 问题 in 问题列表:
        if "Python默认编码" in 问题:
            修复建议.append("设置Python启动参数: export PYTHONUTF8=1")
            if sys.platform == "win32":
                修复建议.append("Windows修复: 设置环境变量 PYTHONUTF8=1")

        elif "环境变量" in 问题:
            if "PYTHONIOENCODING" in 问题:
                修复建议.append("立即修复: os.environ['PYTHONIOENCODING'] = 'utf-8'")
                修复建议.append("永久修复: 在系统环境变量中添加 PYTHONIOENCODING=utf-8")
            elif "LC_ALL" in 问题 or "LANG" in 问题:
                修复建议.append("设置中文locale: export LC_ALL=zh_CN.UTF-8")
                if sys.platform == "win32":
                    修复建议.append("Windows: chcp 65001 并设置代码页为UTF-8")

        elif "Locale" in 问题:
            修复建议.append("安装中文语言包: sudo apt-get install language-pack-zh-hans")
            修复建议.append("生成locale: sudo locale-gen zh_CN.UTF-8")

        elif "文件缺少编码声明" in 问题:
            修复建议.append("在Python文件开头添加: # -*- coding: utf-8 -*-")

        elif "控制台输出" in 问题:
            修复建议.append("使用包装函数: print(内容.encode('utf-8').decode('utf-8'))")

        elif "文件读写" in 问题:
            修复建议.append("始终指定编码: open(文件路径, encoding='utf-8')")

    # 去重
    修复建议 = list(set(修复建议))

    for 建议 in 修复建议:
        输出信息(f"建议: {建议}")

    return 修复建议

def 生成诊断报告(所有问题, 修复建议):
    """生成完整的诊断报告"""
    输出标题("编码环境诊断报告")

    报告 = {
        "诊断时间": "2026-04-17",
        "系统平台": sys.platform,
        "Python版本": sys.version,
        "发现问题数量": len(所有问题),
        "问题详情": 所有问题,
        "修复建议": 修复建议,
        "总体状态": "通过" if len(所有问题) == 0 else "失败"
    }

    # 保存报告
    报告文件 = "编码环境诊断报告.json"
    with open(报告文件, 'w', encoding='utf-8') as f:
        json.dump(报告, f, ensure_ascii=False, indent=2)

    输出成功(f"诊断报告已保存: {报告文件}")

    # 打印摘要
    print(f"\n诊断摘要:")
    print(f"  系统平台: {sys.platform}")
    print(f"  Python版本: {sys.version.split()[0]}")
    print(f"  发现问题: {len(所有问题)} 个")
    print(f"  总体状态: {'通过' if len(所有问题) == 0 else '需要修复'}")

    return 报告

def 主函数():
    """主函数"""
    输出标题("中文UTF-8编码环境验证工具")

    所有问题 = []

    # 执行各项检查
    所有问题.extend(检查Python编码环境())
    所有问题.extend(检查环境变量())
    所有问题.extend(检查系统Locale())
    所有问题.extend(测试中文字符处理())
    所有问题.extend(检查项目文件编码())

    # 生成修复建议
    修复建议 = 生成修复建议(所有问题)

    # 生成报告
    报告 = 生成诊断报告(所有问题, 修复建议)

    # 输出最终结果
    输出标题("验证完成")

    if len(所有问题) == 0:
        输出成功("🎉 所有编码检查通过！系统已准备好处理中文UTF-8内容。")
        print("\n📋 建议操作:")
        print("  1. 将此工具集成到您的测试流程中")
        print("  2. 在项目README中添加编码要求说明")
        print("  3. 定期运行此工具验证编码环境")
        return True
    else:
        输出错误(f"⚠️ 发现 {len(所有问题)} 个编码问题，需要修复后才能正常运行中文工具流。")
        print(f"\n🚀 立即修复:")
        print("  运行: python fix_encoding_issues.py")
        print("  或查看: encoding_specification.md")
        return False

if __name__ == "__main__":
    try:
        # 确保在项目目录中运行
        当前目录 = Path.cwd()
        if "上下文助手" not in str(当前目录):
            输出信息(f"当前目录: {当前目录}")
            输出信息("建议在项目目录中运行此工具")

        成功 = 主函数()
        sys.exit(0 if 成功 else 1)

    except Exception as e:
        输出错误(f"工具执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)