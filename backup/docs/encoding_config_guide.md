# 中文编码环境配置指南

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
   .\fix_encoding.ps1

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
   - 位置: `HKEY_CURRENT_USER\Console`
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
