# 🎯 AII工作流极简启动器使用指南

## 🚀 安装和使用

### **安装**
1. 确保 `ww.py`、`ww.bat`、`ww.sh` 在 `O:\AII\上下文助手` 目录
2. (可选) 添加 `O:\AII\上下文助手` 到系统PATH环境变量

### **基本使用**
```bash
# 方法1: 直接使用（最简单）
cd "O:\AII\上下文助手"
ww "帮我写一个Python脚本"

# 方法2: 添加到PATH后全局使用
ww "帮我解决这个错误"

# 方法3: 双击 ww.bat（Windows）
# 然后输入任务描述
```

## 🎮 完整命令参考

### **1. 启动新任务**
```bash
# 最基本用法
ww "你的任务描述"

# 示例
ww "帮我创建一个用户登录系统"
ww "修复Python中的编码问题"
ww "学习FastAPI的基本用法"
```

### **2. 查看状态**
```bash
# 查看所有工作流状态
ww status

# 输出示例:
# 📊 AII工作流系统状态
# ==================================================
# ✅ 没有中断的工作流
# 👤 用户偏好:
#   • 最后任务类型: code
#   • 常用模板: code, debug, learn
```

### **3. 恢复中断任务**
```bash
# 恢复中断的工作流
ww recover

# 输出示例:
# 🔄 发现 2 个中断的工作流:
# 1. TASK-20240415-123456 (executing) - 重试 1/3
# 2. TASK-20240415-234567 (prompt_optimizing) - 重试 0/3
#
# 选择要恢复的工作流 (输入编号或 'a' 全部恢复):
```

### **4. 清理旧数据**
```bash
# 清理30天前的已完成工作流
ww clean 30

# 清理7天前的数据（默认）
ww clean
```

### **5. 配置设置**
```bash
# 禁用自动复制到剪贴板
ww config auto_copy_to_clipboard false

# 启用自动复制到剪贴板（默认）
ww config auto_copy_to_clipboard true

# 设置默认主题
ww config theme dark
```

## 🔄 400错误恢复流程

### **自动恢复**
系统会自动处理400错误，最多重试3次。

### **手动恢复（如果自动失败）**
```bash
# 1. 查看中断的任务
ww status

# 2. 恢复特定任务
ww recover
# 然后选择任务编号

# 3. 复制恢复指令到新的Claude Code窗口
```

### **一键恢复所有**
```bash
ww recover
# 输入 'a' 恢复所有中断任务
```

## ⚡ 快速启动技巧

### **技巧1: 智能任务识别**
```bash
# 系统会自动识别任务类型
ww "Python中如何读取CSV文件"          # → 学习类型
ww "这个JSON解析报错怎么解决"         # → 调试类型
ww "写一个快速排序算法"               # → 代码类型
```

### **技巧2: 批量操作**
```bash
# 一次启动多个任务
ww "任务1: 写个爬虫；任务2: 数据分析；任务3: 可视化"
```

### **技巧3: 使用历史记录**
```bash
# 查看常用模板
ww status
# 会显示你常用的任务类型，下次会自动优化模板
```

## 🛠️ 配置说明

### **配置文件位置**
```
O:\AII\上下文助手\config\user_prefs.json
```

### **可配置项**
```json
{
  "last_task_type": "code",           // 最后使用的任务类型
  "favorite_templates": ["code", "debug"], // 常用模板
  "auto_copy_to_clipboard": true,     // 自动复制到剪贴板
  "auto_open_claude": false,          // 自动打开Claude Code
  "default_priority": "medium",       // 默认优先级
  "theme": "light"                    // 界面主题
}
```

### **修改配置**
```bash
# 命令行修改
ww config auto_copy_to_clipboard false

# 或直接编辑文件
notepad "O:\AII\上下文助手\config\user_prefs.json"
```

## 💡 最佳实践

### **首次使用**
```bash
# 1. 测试系统
ww "测试工作流系统"

# 2. 查看状态
ww status

# 3. 配置偏好
ww config auto_copy_to_clipboard true
```

### **日常使用**
```bash
# 启动任务
ww "今天的任务描述"

# 如果遇到400错误，系统会自动重试
# 如果重试失败，查看状态
ww status

# 恢复中断的任务
ww recover

# 定期清理
ww clean 30
```

### **冷启动重置**
```bash
# 清理所有旧数据
ww clean 0

# 重置配置
del "O:\AII\上下文助手\config\user_prefs.json"

# 重新启动
ww "新的开始"
```

## 🐛 故障排除

### **问题1: 命令无法执行**
```bash
# 确保在正确目录
cd "O:\AII\上下文助手"

# 或添加PATH
set PATH=%PATH%;O:\AII\上下文助手
```

### **问题2: Python脚本错误**
```bash
# 检查Python版本
python --version  # 需要Python 3.6+

# 安装依赖
pip install pathlib

# 检查脚本权限（Linux/Mac）
chmod +x ww.sh
```

### **问题3: 无法复制到剪贴板**
```bash
# 禁用自动复制
ww config auto_copy_to_clipboard false

# 然后手动复制输出的指令
```

### **问题4: 恢复失败**
```bash
# 查看具体错误
ww status

# 手动清理中断的任务
rmdir /s /q "O:\AII\上下文助手\workflows\TASK-xxxx"

# 重新开始
ww "重新开始任务"
```

## 🎯 与原始流程对比

### **原始流程（复杂）**
1. 打开 `input_task.md`
2. 填写复杂模板
3. 复制到Claude Code
4. 手动处理400错误
5. 手动恢复中断

### **新流程（简单）**
```bash
# 1. 一句话启动
ww "我的任务"

# 2. 系统自动处理一切
#    - 生成任务文件 ✓
#    - 复制指令到剪贴板 ✓
#    - 智能识别任务类型 ✓
#    - 自动处理400错误 ✓
#    - 一键恢复中断 ✓

# 3. 查看结果
cat tasks/output_result.md
```

## 📈 效果对比

| 指标 | 原始流程 | 新流程 | 改进 |
|------|---------|--------|------|
| **启动时间** | 30-60秒 | 5-10秒 | 6倍提速 |
| **步骤数量** | 5+步 | 1步 | 简化80% |
| **400错误处理** | 手动恢复 | 自动重试 | 完全自动化 |
| **学习成本** | 高 | 低 | 简单易用 |
| **首次使用** | 复杂 | 简单 | 极简启动 |

## 🚀 开始使用

### **Windows用户**
```bash
# 打开命令提示符
cd "O:\AII\上下文助手"

# 第一次使用
ww "帮我测试工作流系统"
```

### **Linux/Mac用户**
```bash
# 打开终端
cd "O:\AII/上下文助手"

# 第一次使用
./ww.sh "帮我测试工作流系统"
```

### **添加到PATH（推荐）**
```bash
# Windows（管理员命令提示符）
setx PATH "%PATH%;O:\AII\上下文助手"

# Linux/Mac
echo 'export PATH="$PATH:/path/to/AII/上下文助手"' >> ~/.bashrc
source ~/.bashrc

# 然后全局使用
ww "任务描述"
```

---

**总结**：现在你只需要记住一个命令 `ww`，系统会自动处理所有复杂流程！