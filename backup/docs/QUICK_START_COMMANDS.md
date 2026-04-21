# 上下文助手测试流程 - 用户可直接运行的命令

## 🎯 一句话命令（在任何终端粘贴即可运行）

```bash
# 方法1：直接运行（需要已下载脚本）
python run_full_test_simple.py

# 方法2：使用编码包装器确保中文正确显示
python cn_wrapper.py run_full_test_simple.py
```

## 📋 完整使用流程

### 第一步：准备环境
```bash
# 1. 确保您在项目目录或上级目录
cd /o/AII  # 或您的项目位置

# 2. 修复编码环境（Windows必做）
python 上下文助手/fix_encoding_issues.py
# 或
上下文助手/fix_encoding.bat
```

### 第二步：运行完整测试
```bash
# 从任何位置运行（自动定位项目）
python 上下文助手/run_full_test_simple.py
```

### 第三步：查看结果
```bash
# 查看详细报告
cat 上下文助手/一键测试报告.json

# 查看文本摘要
cat 上下文助手/完整测试报告.txt
```

## 🔧 分步验证命令

### Step 1: 环境诊断
```bash
python 上下文助手/validate_encoding.py
```

### Step 2: 文件检查
```bash
# 检查基本文件
python -c "
from pathlib import Path
p = Path('上下文助手')
files = ['ww.bat', 'ww_simple.py', 'README.md', 'config/user_prefs.json']
for f in files:
    if (p/f).exists():
        print(f'✅ {f}')
    else:
        print(f'❌ {f} (缺失)')
"
```

### Step 3: 命令测试
```bash
python 上下文助手/ww_simple.py status
```

### Step 4: 工作流测试
```bash
python 上下文助手/ww_simple.py "测试工作流验证"
```

## 🚀 快速验证脚本

将以下内容保存为 `quick_test.bat`（Windows）或 `quick_test.sh`（Linux/macOS）：

**Windows批处理版本：**
```batch
@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
echo 正在运行上下文助手测试...

cd /d "O:\AII\上下文助手"
python run_full_test_simple.py

if %errorlevel% equ 0 (
    echo ✅ 测试通过！
    echo 报告文件: 一键测试报告.json
) else (
    echo ❌ 测试失败，请查看错误信息
    echo 建议运行: python fix_encoding_issues.py
)
pause
```

**Linux/macOS Shell版本：**
```bash
#!/bin/bash
export PYTHONIOENCODING=utf-8
export LC_ALL=zh_CN.UTF-8
echo "正在运行上下文助手测试..."

cd "O:/AII/上下文助手" || cd "./上下文助手" || { echo "找不到项目目录"; exit 1; }
python run_full_test_simple.py

if [ $? -eq 0 ]; then
    echo "✅ 测试通过！"
    echo "报告文件: 一键测试报告.json"
else
    echo "❌ 测试失败，请查看错误信息"
    echo "建议运行: python fix_encoding_issues.py"
fi
```

## 💡 一键命令生成器

如果您想创建自定义的一键命令，使用以下Python代码：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

def 生成一键命令():
    """生成用户可直接运行的一键命令"""
    
    命令模板 = '''# 上下文助手一键测试命令
# 复制以下所有内容到终端运行

# 设置编码环境
{python} -c "import os; os.environ['PYTHONIOENCODING']='utf-8'; print('✅ 编码环境设置完成')"

# 运行测试
cd "{project_dir}" && {python} run_full_test_simple.py

# 输出结果
echo "测试完成！"
echo "查看报告: {project_dir}/一键测试报告.json"
'''
    
    # 获取当前Python路径
    python_path = sys.executable
    
    # 获取项目路径（假设脚本在项目目录中运行）
    project_dir = os.path.abspath(os.path.dirname(__file__))
    
    # 生成命令
    最终命令 = 命令模板.format(python=python_path, project_dir=project_dir)
    
    print("=" * 60)
    print("复制以下所有内容到终端运行：")
    print("=" * 60)
    print(最终命令)
    print("=" * 60)
    
    return 最终命令

if __name__ == "__main__":
    生成一键命令()
```

## 📞 故障排除命令

### 问题1：中文乱码
```bash
# Windows
chcp 65001
set PYTHONIOENCODING=utf-8
python run_full_test_simple.py

# Linux/macOS
export PYTHONIOENCODING=utf-8
export LC_ALL=zh_CN.UTF-8
python run_full_test_simple.py
```

### 问题2：找不到文件
```bash
# 手动指定路径
python "O:/AII/上下文助手/run_full_test_simple.py"

# 或使用完整路径
cd "O:/AII/上下文助手" && python run_full_test_simple.py
```

### 问题3：依赖错误
```bash
# 检查Python版本
python --version

# 检查必需模块
python -c "import json, pathlib, subprocess, platform, datetime; print('✅ 所有依赖正常')"
```

## 🎯 最简单的方式

**只需这一行命令：**
```bash
cd "O:/AII/上下文助手" && python run_full_test_simple.py
```

或者，如果您想更简单：

```bash
# 创建一个别名（Linux/macOS）
alias test_ai_workflow='cd "O:/AII/上下文助手" && python run_full_test_simple.py'

# 然后就可以这样运行
test_ai_workflow
```

## 📊 验证成功的标准

当您看到以下输出时，表示测试成功：

```
==================================================
[测试] 上下文助手一键测试
==================================================
[信息] 开始时间: 2026-04-17
[信息] Python版本: 3.9.13
...
[成功] 所有测试通过！
[下一步] 现在您可以:
  1. 运行工作流: python ww_simple.py "您的任务"
  2. 查看报告: 一键测试报告.json
  3. 开始使用上下文助手
```

## 🎉 恭喜！

您现在已经拥有了一个完整的、可立即使用的测试流程。只需运行一个命令，即可验证整个上下文助手工具流的完整性和正确性。

**记住核心命令：**
```bash
python run_full_test_simple.py
```

**问题解决命令：**
```bash
python fix_encoding_issues.py
```

**最佳实践：**
```bash
python cn_wrapper.py [您的脚本]
```

现在，您可以开始使用经过完整验证的上下文助手工具流了！