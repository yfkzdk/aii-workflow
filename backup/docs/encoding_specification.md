# 中文UTF-8编码强制规范

## 🎯 目标
确保所有脚本和工具流在任意环境下都能正确处理中文字符，输出纯中文内容

## 📜 强制规范

### 1. 脚本头部声明
所有Python脚本必须在开头添加：
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文脚本描述
"""
```

### 2. 环境变量设置
测试脚本必须设置以下环境变量：

#### Windows (批处理/PowerShell)
```batch
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
```

#### Linux/macOS/跨平台Python
```python
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'zh_CN.UTF-8'
```

### 3. 文件读写规范
所有文件操作必须指定编码：
```python
# 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 写入文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
```

### 4. 输出包装器
使用统一的输出函数处理中文：
```python
def print_cn(*args, **kwargs):
    """中文输出包装器"""
    text = ' '.join(str(arg) for arg in args)
    # 强制转换为UTF-8字符串
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    print(text, **kwargs)

def print_error(msg):
    """输出错误信息"""
    print_cn(f"[错误] {msg}")

def print_success(msg):
    """输出成功信息"""
    print_cn(f"[成功] {msg}")

def print_info(msg):
    """输出信息"""
    print_cn(f"[信息] {msg}")
```

### 5. 错误处理
捕获英文错误信息并转换为中文：
```python
import sys
import traceback

def handle_exception(e):
    """异常处理与翻译"""
    error_type = type(e).__name__
    
    # 常见错误类型映射
    error_translations = {
        'FileNotFoundError': '文件不存在',
        'PermissionError': '权限不足',
        'JSONDecodeError': 'JSON格式错误',
        'KeyError': '配置字段缺失',
        'AttributeError': '对象属性错误',
        'TypeError': '类型错误',
        'ValueError': '值错误',
        'IndentationError': '缩进错误',
        'SyntaxError': '语法错误',
        'ImportError': '导入错误'
    }
    
    cn_type = error_translations.get(error_type, error_type)
    print_error(f"{cn_type}: {str(e)}")
    
    # 调试模式时输出详细堆栈
    if os.getenv('DEBUG', 'false').lower() == 'true':
        traceback.print_exc()
    
    return False
```

## 🔧 编码验证工具

### 编码检查脚本
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码环境验证工具
"""

import os
import sys
import locale

def check_encoding_environment():
    """检查编码环境"""
    print("=" * 60)
    print("编码环境诊断")
    print("=" * 60)
    
    issues = []
    
    # 检查Python默认编码
    default_encoding = sys.getdefaultencoding()
    print(f"Python默认编码: {default_encoding}")
    if default_encoding.lower() != 'utf-8':
        issues.append(f"Python默认编码不是UTF-8: {default_encoding}")
    
    # 检查文件系统编码
    fs_encoding = sys.getfilesystemencoding()
    print(f"文件系统编码: {fs_encoding}")
    if fs_encoding.lower() != 'utf-8':
        issues.append(f"文件系统编码不是UTF-8: {fs_encoding}")
    
    # 检查环境变量
    py_io_encoding = os.getenv('PYTHONIOENCODING', '未设置')
    print(f"PYTHONIOENCODING: {py_io_encoding}")
    if py_io_encoding.lower() != 'utf-8':
        issues.append(f"环境变量PYTHONIOENCODING不是UTF-8: {py_io_encoding}")
    
    # 检查locale
    try:
        current_locale = locale.getlocale()
        print(f"当前locale: {current_locale}")
        if 'utf-8' not in str(current_locale).lower():
            issues.append(f"locale不包含UTF-8: {current_locale}")
    except:
        pass
    
    # 测试中文字符输出
    print("\n中文字符测试:")
    test_text = "✅ 这是一段中文测试文字！测试是否支持UTF-8编码。"
    print(test_text)
    
    # 测试文件读写
    print("\n文件读写测试:")
    try:
        test_file = "编码测试临时文件.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("UTF-8编码测试内容 - 中文测试 ✅")
        
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"  文件读取成功: {content}")
        
        os.remove(test_file)
        print("  临时文件清理成功")
    except Exception as e:
        issues.append(f"文件读写测试失败: {e}")
    
    # 输出结果
    print("\n" + "=" * 60)
    if not issues:
        print("✅ 编码环境验证通过！所有测试正常。")
        return True
    else:
        print("⚠️ 发现编码问题:")
        for issue in issues:
            print(f"  - {issue}")
        print(f"\n总计发现 {len(issues)} 个问题")
        return False

if __name__ == "__main__":
    success = check_encoding_environment()
    sys.exit(0 if success else 1)
```

## 🚀 快速修复命令

### Windows环境修复
```batch
@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set LANG=zh_CN.UTF-8
echo ✅ 编码环境已设置为UTF-8
```

### Linux/macOS环境修复
```bash
#!/bin/bash
export PYTHONIOENCODING=utf-8
export LC_ALL=zh_CN.UTF-8
export LANG=zh_CN.UTF-8
echo "✅ 编码环境已设置为UTF-8"
```

### Python环境修复
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

def fix_encoding_environment():
    """修复编码环境"""
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['LC_ALL'] = 'zh_CN.UTF-8'
    
    # 重新加载标准输出
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    
    print("✅ 编码环境已修复为UTF-8")
    
if __name__ == "__main__":
    fix_encoding_environment()
```

## 📋 合规检查清单
- [ ] 所有脚本包含 `# -*- coding: utf-8 -*-`
- [ ] 所有文件操作指定 `encoding='utf-8'`
- [ ] 环境变量已设置 `PYTHONIOENCODING=utf-8`
- [ ] 输出使用中文包装函数
- [ ] 错误信息已翻译为中文
- [ ] 日志文件使用UTF-8编码
- [ ] 配置文件使用JSON UTF-8格式

## 📚 最佳实践
1. **始终使用UTF-8**: 即使是英文内容也使用UTF-8编码
2. **尽早验证**: 在脚本开始时验证编码环境
3. **优雅降级**: 编码失败时提供友好的错误提示
4. **自动修复**: 检测到编码问题时尝试自动修复
5. **文档说明**: 在README中说明编码要求

## 🔍 常见问题排查

### 问题1: 中文显示为乱码
**原因**: 终端编码不是UTF-8
**解决**: 
```bash
# Windows
chcp 65001

# Linux/macOS
export LANG=zh_CN.UTF-8
```

### 问题2: 文件读取时出现解码错误
**原因**: 文件编码不是UTF-8
**解决**: 使用正确的编码打开文件
```python
with open(file_path, 'r', encoding='gbk') as f:  # 对于GBK编码文件
    content = f.read()
```

### 问题3: Python默认编码不是UTF-8
**原因**: Python环境配置问题
**解决**: 设置环境变量
```python
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

---

**最后更新**: 2026-04-17  
**维护者**: AII上下文助手测试团队  
**状态**: 正式规范