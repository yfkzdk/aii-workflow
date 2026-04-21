# 🚀 AII工作流智能启动器 - 安装指南

## 📋 系统要求

### **基本要求**
- ✅ Python 3.6+
- ✅ Windows 10/11 或 Linux/macOS
- ✅ AII工作流系统（已安装在 `O:\AII\上下文助手`）
- ✅ 命令行终端（CMD, PowerShell, Terminal, Bash）

### **推荐环境**
- ✅ Claude Code 已安装和配置
- ✅ 基本的命令行使用经验
- ✅ 管理员/root权限（用于全局安装）

## 🔧 安装步骤

### **方法1：一键安装（推荐）**

```bash
# 1. 打开终端/命令提示符
# 2. 进入工作流目录
cd "O:\AII\上下文助手"

# 3. 运行安装脚本
python install_enhanced.py
```

### **方法2：手动安装**

```bash
# 1. 下载或创建以下文件到 O:\AII\上下文助手\
#    - ww_enhanced.py
#    - ww.bat (Windows)
#    - ww_enhanced.sh (Linux/Mac)
#    - QUICK_START.md

# 2. 设置执行权限（Linux/Mac）
chmod +x ww_enhanced.sh

# 3. 创建全局命令（可选）
# Linux/Mac:
sudo ln -s "$(pwd)/ww_enhanced.sh" /usr/local/bin/ww

# Windows（添加到PATH）:
# 将 O:\AII\上下文助手 添加到系统PATH环境变量
```

### **方法3：开发模式安装**

```bash
# 1. 克隆或下载增强版文件
cd "O:\AII\上下文助手"

# 2. 测试安装
python ww_enhanced.py version

# 3. 创建桌面快捷方式（Windows）
copy ww.bat "%USERPROFILE%\Desktop\AII工作流.bat"

# 4. 创建开始菜单快捷方式（可选）
# 参考Windows快捷方式创建方法
```

## 🎯 验证安装

### **基本验证**
```bash
# 进入工作流目录
cd "O:\AII\上下文助手"

# 测试版本信息
ww version

# 测试帮助信息
ww help

# 测试状态查看
ww status
```

### **功能测试**
```bash
# 测试任务启动
ww "测试工作流系统"

# 测试恢复功能（如果有中断的任务）
ww recover

# 测试配置管理
ww config auto_copy_to_clipboard true

# 测试清理功能
ww clean 7
```

## ⚙️ 配置说明

### **配置文件位置**
```
O:\AII\上下文助手\config\user_prefs.json
```

### **默认配置**
```json
{
  "version": "2.0",
  "auto_copy_to_clipboard": true,
  "auto_open_claude": false,
  "default_theme": "light",
  "notification_enabled": true,
  "max_history_size": 100,
  "auto_cleanup_days": 30,
  "interactive_mode": true,
  "color_output": true,
  "preferred_task_types": [],
  "last_used_template": "general",
  "installed_at": "2024-04-15"
}
```

### **配置说明**
| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `auto_copy_to_clipboard` | 自动复制指令到剪贴板 | `true` |
| `interactive_mode` | 交互模式（无参数时显示菜单） | `true` |
| `color_output` | 彩色终端输出 | `true` |
| `auto_cleanup_days` | 自动清理多少天前的数据 | `30` |
| `max_history_size` | 最大历史记录数 | `100` |
| `default_theme` | 默认主题（light/dark） | `light` |

### **修改配置**
```bash
# 命令行修改
ww config auto_copy_to_clipboard false
ww config interactive_mode true
ww config auto_cleanup_days 7

# 或直接编辑配置文件
notepad "O:\AII\上下文助手\config\user_prefs.json"
```

## 🔄 升级说明

### **从旧版本升级**
```bash
# 1. 备份当前配置（自动完成）
cd "O:\AII\上下文助手"
python install_enhanced.py

# 2. 安装程序会自动：
#    - 备份现有文件到 backup/ 目录
#    - 安装新版本文件
#    - 保留用户配置
#    - 清理旧文件
```

### **手动升级**
```bash
# 1. 备份重要文件
copy "O:\AII\上下文助手\config\user_prefs.json" "O:\AII\上下文助手\config\user_prefs.json.backup"

# 2. 下载新版本文件
# 3. 替换以下文件：
#    - ww_enhanced.py
#    - ww.bat
#    - ww_enhanced.sh
#    - QUICK_START.md

# 4. 恢复配置（如果需要）
copy "O:\AII\上下文助手\config\user_prefs.json.backup" "O:\AII\上下文助手\config\user_prefs.json"
```

## 🐛 故障排除

### **问题1：命令无法执行**
```bash
# 检查Python是否安装
python --version

# 检查是否在工作流目录
cd "O:\AII\上下文助手"
pwd  # 或 echo %CD%

# 检查文件是否存在
dir ww_enhanced.py  # Windows
ls -la ww_enhanced.py  # Linux/Mac
```

### **问题2：权限错误**
```bash
# Linux/Mac: 设置执行权限
chmod +x ww_enhanced.sh

# Windows: 以管理员身份运行命令提示符
```

### **问题3：配置问题**
```bash
# 重置配置文件
del "O:\AII\上下文助手\config\user_prefs.json"
ww version  # 会自动创建默认配置
```

### **问题4：路径问题**
```bash
# Windows: 添加到PATH
setx PATH "%PATH%;O:\AII\上下文助手"

# Linux/Mac: 创建符号链接
sudo ln -s "/path/to/AII/上下文助手/ww_enhanced.sh" /usr/local/bin/ww
```

### **问题5：Python依赖**
```bash
# 检查Python版本
python -c "import sys; print(f'Python {sys.version}')"

# 安装必要模块（通常不需要）
pip install pathlib
```

## 📁 文件结构

### **安装后的目录结构**
```
O:\AII\上下文助手\
├── 📁 backup/                    # 备份文件
│   └── *.backup                 # 安装前的备份
├── 📁 config/                   # 配置文件
│   ├── user_prefs.json         # 用户偏好
│   └── task_history.json       # 任务历史
├── 📁 logs/                    # 日志文件
│   ├── launcher.log           # 启动器日志
│   └── error.log              # 错误日志
├── 📁 cache/                   # 缓存文件
├── 📁 templates/               # 任务模板
├── 📄 ww_enhanced.py          # 主启动器脚本
├── 📄 ww.bat                  # Windows启动脚本
├── 📄 ww_enhanced.sh          # Linux/Mac启动脚本
├── 📄 install_enhanced.py     # 安装脚本
├── 📄 QUICK_START.md          # 快速开始指南
├── 📄 INSTALLATION_GUIDE.md   # 安装指南（本文件）
└── （原有文件保持不变）
```

### **原有文件处理**
安装程序会自动备份以下文件：
- `ww.py` → `backup/ww.py.backup`
- `ww.bat` → `backup/ww.bat.backup`
- `ww.sh` → `backup/ww.sh.backup`
- `user_prefs.json` → `backup/user_prefs.json.backup`

## 🎮 快速测试

### **测试脚本**
```python
# test_installation.py
import subprocess
import sys

def test_command(cmd, description):
    print(f"测试: {description}")
    print(f"命令: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ 成功")
            print(f"输出: {result.stdout[:200]}...")
        else:
            print(f"❌ 失败")
            print(f"错误: {result.stderr}")
        print()
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 异常: {e}")
        print()
        return False

# 运行测试
tests = [
    ("ww version", "版本信息"),
    ("ww help", "帮助信息"),
    ("ww status", "系统状态"),
    ("ww \"测试安装\"", "任务启动"),
    ("ww config auto_copy_to_clipboard true", "配置修改"),
]

all_pass = True
for cmd, desc in tests:
    if not test_command(cmd, desc):
        all_pass = False

if all_pass:
    print("🎉 所有测试通过！安装成功。")
else:
    print("⚠️  部分测试失败，请检查安装。")
```

### **运行测试**
```bash
cd "O:\AII\上下文助手"
python test_installation.py
```

## 🔄 卸载

### **完全卸载**
```bash
# 1. 删除安装的文件
del ww_enhanced.py
del ww.bat
del ww_enhanced.sh
del install_enhanced.py
del QUICK_START.md
del INSTALLATION_GUIDE.md

# 2. 删除配置和日志（可选）
rmdir /s /q config  # Windows
rm -rf config       # Linux/Mac

rmdir /s /q logs    # Windows
rm -rf logs         # Linux/Mac

# 3. 从PATH中移除（如果添加了）
# Windows: 编辑系统环境变量
# Linux/Mac: rm /usr/local/bin/ww
```

### **保留配置卸载**
```bash
# 只删除程序文件，保留配置和数据
del ww_enhanced.py
del ww.bat
del ww_enhanced.sh
del install_enhanced.py

# 恢复备份文件（如果需要）
copy backup\ww.py.backup ww.py
copy backup\ww.bat.backup ww.bat
copy backup\user_prefs.json.backup config\user_prefs.json
```

## 💡 使用技巧

### **添加到PATH（Windows）**
```batch
REM 临时添加到PATH
set PATH=%PATH%;O:\AII\上下文助手

REM 永久添加到PATH
setx PATH "%PATH%;O:\AII\上下文助手"
```

### **创建桌面快捷方式（Windows）**
```batch
copy ww.bat "%USERPROFILE%\Desktop\AII工作流.bat"
```

### **创建别名（Linux/Mac）**
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'alias ww="python3 /path/to/AII/上下文助手/ww_enhanced.py"' >> ~/.bashrc
source ~/.bashrc
```

### **定时清理（Cron/任务计划）**
```bash
# Linux/Mac (每天凌晨3点清理)
0 3 * * * cd /path/to/AII/上下文助手 && ./ww_enhanced.sh clean 7

# Windows (任务计划程序)
# 创建定时任务运行: ww clean 7
```

## 📞 支持与反馈

### **获取帮助**
```bash
# 查看完整帮助
ww help

# 查看使用指南
ww guide

# 查看版本信息
ww version
```

### **查看日志**
```bash
# 查看启动器日志
type logs\launcher.log  # Windows
cat logs/launcher.log   # Linux/Mac

# 查看错误日志
type logs\error.log     # Windows
cat logs/error.log      # Linux/Mac
```

### **报告问题**
1. 检查日志文件
2. 运行 `ww status` 查看系统状态
3. 尝试重置配置：删除 `config/user_prefs.json`
4. 重新安装：运行 `python install_enhanced.py`

---

**安装完成！** 现在你可以使用 `ww` 命令来启动AII工作流了。

试试这些命令：
- `ww "帮我写一个Python脚本"` - 启动新任务
- `ww status` - 查看系统状态
- `ww guide` - 查看完整指南

如果有任何问题，请参考本指南或运行 `ww help`。