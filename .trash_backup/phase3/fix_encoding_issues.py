#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文编码问题修复脚本
自动修复Windows终端的GBK编码问题，确保支持UTF-8中文输出
"""

import os
import sys
import subprocess
import platform

def 设置编码环境():
    """设置UTF-8编码环境"""
    print("=" * 60)
    print("[标题] 中文编码修复工具")
    print("=" * 60)

    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    # Windows系统特殊处理
    if platform.system() == 'Windows':
        print("[信息] 检测到Windows系统，进行特殊处理...")

        # 尝试设置代码页为UTF-8
        try:
            subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
            print("[成功] 已设置Windows控制台代码页为UTF-8 (65001)")
        except Exception as e:
            print(f"[错误] 设置代码页失败: {e}")

        # 尝试设置控制台字体
        try:
            # 这是一个友好的提示，不是实际修改注册表
            print("[信息] 建议手动设置控制台字体: 设置 -> 默认值 -> 字体 -> 选择 'Consolas' 或 '微软雅黑'")
        except:
            pass

    # 设置其他环境变量
    os.environ['LC_ALL'] = 'zh_CN.UTF-8'
    os.environ['LANG'] = 'zh_CN.UTF-8'

    print("[成功] 环境变量设置完成")

def 修复Python输出编码():
    """修复Python标准输出编码"""
    print("\n[标题] 修复Python输出编码")

    try:
        # 重新配置标准输出
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
            print("[成功] 已重新配置标准输出为UTF-8编码")
        else:
            # Python 3.7以下版本的处理方式
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            print("[成功] 已包装标准输出为UTF-8编码")

    except Exception as e:
        print(f"[错误] 修复Python输出编码失败: {e}")
        return False

    return True

def 验证修复效果():
    """验证修复效果"""
    print("\n[标题] 验证修复效果")

    # 测试中文输出
    测试文本 = "这是一段中文测试文字！验证UTF-8编码修复效果。"

    try:
        print(f"测试输出: {测试文本}")
        print("[成功] 中文输出测试通过")
    except UnicodeEncodeError as e:
        print(f"[错误] 中文输出失败: {e}")
        return False

    # 测试Unicode字符
    try:
        unicode测试 = "测试Unicode字符: αβγδε 和中文混合"
        print(f"Unicode测试: {unicode测试}")
        print("[成功] Unicode字符输出测试通过")
    except UnicodeEncodeError as e:
        print(f"[警告] Unicode字符输出有限制: {e}")
        print("[信息] 当前终端可能不支持完整的Unicode字符集")

    return True

def 创建修复脚本():
    """创建永久修复脚本"""
    print("\n[标题] 创建永久修复方案")

    # Windows批处理文件
    if platform.system() == 'Windows':
        bat_content = '''@echo off
REM 中文工作流编码修复脚本
echo 正在设置UTF-8编码环境...

REM 设置代码页为UTF-8
chcp 65001 > nul

REM 设置环境变量
set PYTHONIOENCODING=utf-8
set LANG=zh_CN.UTF-8

REM 设置Python路径
set PYTHONPATH=O:\\AII\\上下文助手

echo ✅ 编码环境修复完成！
echo 建议：将此脚本添加到系统启动项，或在每次使用前运行。

REM 启动Python
python %*
'''

        with open('fix_encoding.bat', 'w', encoding='utf-8') as f:
            f.write(bat_content)

        print("[成功] 已创建修复脚本: fix_encoding.bat")
        print("[信息] 使用方法: fix_encoding.bat [python脚本参数]")

    # PowerShell脚本
    ps_content = '''# 中文工作流编码修复脚本
Write-Host "正在设置UTF-8编码环境..." -ForegroundColor Yellow

# 设置输出编码
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 设置环境变量
$env:PYTHONIOENCODING = "utf-8"
$env:LANG = "zh_CN.UTF-8"
$env:LC_ALL = "zh_CN.UTF-8"

# 设置Python路径
$env:PYTHONPATH = "O:\\AII\\上下文助手"

Write-Host "✅ 编码环境修复完成！" -ForegroundColor Green
Write-Host "建议：将此脚本添加到PowerShell配置文件" -ForegroundColor Cyan

# 恢复原始提示符
function prompt {
    "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}
'''

    with open('fix_encoding.ps1', 'w', encoding='utf-8') as f:
        f.write(ps_content)

    print("[成功] 已创建修复脚本: fix_encoding.ps1")
    print("[信息] 使用方法: .\\fix_encoding.ps1")

def 创建Python包装器():
    """创建Python包装器脚本"""
    print("\n[标题] 创建Python编码包装器")

    wrapper_content = '''#!/usr/bin/env python3
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
'''

    with open('cn_wrapper.py', 'w', encoding='utf-8') as f:
        f.write(wrapper_content)

    print("[成功] 已创建Python包装器: cn_wrapper.py")
    print("[信息] 使用方法: python cn_wrapper.py [目标脚本]")

def 生成配置指南():
    """生成编码配置指南"""
    print("\n[标题] 生成配置指南")

    guide_content = '''# 中文编码环境配置指南

## 问题描述
在Windows系统中，命令行终端默认使用GBK编码，导致：
1. UTF-8编码的中文显示为乱码
2. Unicode字符（如emoji）无法显示
3. JSON文件中的中文无法正确处理

## 解决方案

### 临时解决方案（每次会话）
1. **运行修复脚本**:
   ```bash
   # 方法1: 批处理
   fix_encoding.bat

   # 方法2: PowerShell
   .\\fix_encoding.ps1

   # 方法3: Python包装器
   python cn_wrapper.py [您的脚本]
   ```

2. **手动设置**:
   ```bash
   chcp 65001
   set PYTHONIOENCODING=utf-8
   ```

### 永久解决方案

#### Windows系统
1. **修改注册表**（高级用户）:
   - 位置: `HKEY_CURRENT_USER\\Console`
   - 设置: `CodePage` = `65001` (十进制)

2. **修改快捷方式**:
   - 右键点击命令行快捷方式 -> 属性
   - 选项 -> 代码页 -> 选择UTF-8

3. **使用现代终端**:
   - Windows Terminal (推荐)
   - PowerShell 7+
   - Git Bash

#### Python项目
1. **在每个脚本开头添加**:
   ```python
   #!/usr/bin/env python3
   # -*- coding: utf-8 -*-
   ```

2. **文件操作始终指定编码**:
   ```python
   with open(file, 'r', encoding='utf-8') as f:
       content = f.read()
   ```

3. **使用包装函数输出**:
   ```python
   def print_cn(text):
       try:
           print(text)
       except UnicodeEncodeError:
           print(text.encode('utf-8').decode('gbk', errors='ignore'))
   ```

## 验证方法
运行验证脚本检查编码环境:
```bash
python validate_encoding.py
```

## 最佳实践
1. **始终使用UTF-8**: 即使是英文内容也使用UTF-8编码
2. **尽早检测**: 在脚本开始时检测和修复编码问题
3. **优雅降级**: 当UTF-8不可用时提供替代方案
4. **清晰错误提示**: 当编码失败时给出明确的修复建议

## 故障排除

### 问题1: 中文显示为乱码
**解决**: 运行 `chcp 65001` 或使用包装脚本

### 问题2: 无法保存含中文的文件
**解决**: 在文件操作中指定 `encoding='utf-8'`

### 问题3: 第三方库输出乱码
**解决**: 设置环境变量 `PYTHONIOENCODING=utf-8`

### 问题4: 日志文件乱码
**解决**: 确保日志处理器使用UTF-8编码

## 支持的工具
- ✅ Python脚本 (.py)
- ✅ 批处理文件 (.bat)
- ✅ PowerShell脚本 (.ps1)
- ✅ 配置文件 (.json, .yaml)
- ✅ 文档文件 (.md, .txt)

---

**最后更新**: 2026-04-17
**状态**: 正式配置指南
'''

    with open('encoding_config_guide.md', 'w', encoding='utf-8') as f:
        f.write(guide_content)

    print("[成功] 已创建配置指南: encoding_config_guide.md")

def 主函数():
    """主函数"""
    设置编码环境()

    if not 修复Python输出编码():
        print("[错误] 编码修复失败，无法继续")
        return False

    if not 验证修复效果():
        print("[警告] 修复效果验证失败，某些功能可能受限")

    创建修复脚本()
    创建Python包装器()
    生成配置指南()

    print("\n" + "=" * 60)
    print("[标题] 修复完成总结")
    print("=" * 60)

    print("[成功] 所有修复脚本已创建完成！")
    print("\n📋 可用工具:")
    print("  1. fix_encoding.bat      - Windows批处理修复")
    print("  2. fix_encoding.ps1      - PowerShell修复")
    print("  3. cn_wrapper.py        - Python脚本包装器")
    print("  4. encoding_config_guide.md - 详细配置指南")

    print("\n🚀 下一步建议:")
    print("  1. 运行验证: python cn_wrapper.py validate_encoding.py")
    print("  2. 测试工作流: python cn_wrapper.py ww_simple.py status")
    print("  3. 将修复脚本集成到您的测试流程中")

    print("\n💡 提示: 对于生产环境，建议将编码设置添加到系统启动脚本中")

    return True

if __name__ == "__main__":
    try:
        成功 = 主函数()
        sys.exit(0 if 成功 else 1)
    except Exception as e:
        print(f"[错误] 修复工具执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)