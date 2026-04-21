# 🚀 AII工作流PowerShell模块 - 快速开始指南

## 📋 概述
AII工作流PowerShell模块提供了专业级的命令行接口，用于管理和操作AII工作流系统。通过该模块，您可以：
- 使用PowerShell命令启动和管理工作流任务
- 在VS Code中无缝集成工作流
- 实现跨窗口状态同步和恢复
- 一键重置系统状态
- 自动化常见工作流操作

## 🔧 系统要求
- Windows PowerShell 5.1+ 或 PowerShell Core 6+
- Python 3.6+（已添加到PATH）
- AII工作流系统（已安装在 `O:\AII\上下文助手`）
- VS Code（可选，用于扩展集成）

## 📥 安装

### 方法1：使用安装脚本（推荐）
```powershell
# 进入AII工作流目录
cd "O:\AII\上下文助手\powershell"

# 运行安装脚本（需要管理员权限）
.\install.ps1

# 或使用强制安装覆盖现有版本
.\install.ps1 -Force

# 指定安装路径
.\install.ps1 -InstallPath "C:\MyModules"
```

### 方法2：手动安装
```powershell
# 1. 复制模块文件到PowerShell模块目录
$modulePath = "$env:USERPROFILE\Documents\WindowsPowerShell\Modules\AIIWorkflow"
mkdir $modulePath -Force
Copy-Item "O:\AII\上下文助手\powershell\*" $modulePath -Recurse

# 2. 导入模块
Import-Module AIIWorkflow

# 3. 初始化工作流
Initialize-AIIWorkflow
```

### 方法3：开发模式安装
```powershell
# 1. 将模块目录添加到PSModulePath
$env:PSModulePath = "O:\AII\上下文助手\powershell;" + $env:PSModulePath

# 2. 导入模块
Import-Module AIIWorkflow -Force

# 3. 测试模块
Get-AIIModuleInfo
```

## 🎯 快速开始

### 1. 基本使用
```powershell
# 查看模块信息
Get-AIIModuleInfo

# 显示欢迎信息
Show-AIIWelcome

# 查看系统状态
Get-AIIStatus

# 获取系统信息
Get-AIIInfo
```

### 2. 任务管理
```powershell
# 创建新任务
New-AIITask -Description "帮我写一个Python数据分析脚本"

# 启动任务
Start-AIITask

# 查看任务列表
Get-AIITaskList

# 获取任务详情
Get-AIITaskInfo

# 停止当前任务
Stop-AIITask

# 恢复最近的任务
Resume-AIITask
```

### 3. VS Code集成
```powershell
# 在VS Code中打开工作流
Open-AIIInVSCode

# 安装VS Code扩展
Install-AIIVSCodeExtension

# 查看VS Code状态
Get-AIIVSCodeStatus

# 配置VS Code扩展设置
Set-AIIVSCodeSettings -Settings @{
    autoStart = $true
    notificationEnabled = $true
    defaultWorkspace = "O:\AII\上下文助手"
}
```

### 4. 系统管理
```powershell
# 重置系统（需要确认）
Reset-AIISystem -Force

# 创建备份
Backup-AIISystem

# 从备份恢复
Restore-AIISystem -BackupDir "backups\manual-20240415-153000"

# 列出备份
Get-AIIBackups

# 测试系统完整性
Test-AIISystem

# 修复系统问题
Repair-AIISystem
```

## ⚡ 快捷别名
模块提供了简短的别名，便于快速使用：

```powershell
# 任务管理
aii-start "任务描述"      # 创建并启动新任务
aii-status                # 查看状态
aii-resume                # 恢复任务
aii-list                  # 列出任务
aii-info                  # 查看任务详情
aii-stop                  # 停止任务
aii-clean                 # 清理旧任务

# VS Code集成
aii-vscode               # 在VS Code中打开

# 系统管理
aii-reset                # 重置系统
aii-backup               # 创建备份
aii-restore              # 从备份恢复
aii-test                 # 测试系统
aii-repair               # 修复系统
aii-clear                # 清理状态
```

## 🔄 状态管理和恢复

### 跨窗口状态同步
模块自动维护状态文件，支持多窗口同步：
```powershell
# 窗口1：启动任务
New-AIITask "分析销售数据"
Start-AIITask

# 窗口2：查看状态（自动同步）
Get-AIIStatus
# 显示当前任务状态，包括其他窗口的活动状态
```

### 自动恢复
```powershell
# 如果VS Code崩溃或关闭
# 重新打开后，系统自动检测并恢复上次状态
Resume-AIITask
```

### 心跳检测
模块自动维护窗口心跳，超时窗口自动清理：
```powershell
# 查看活动窗口
(Get-AIIStatus).ActiveWindows
```

## 🛠️ 高级功能

### 任务模板
```powershell
# 使用特定模板创建任务
New-AIITask -Description "数据分析报告" -Template "data_analysis" -Priority "High"

# 可用模板：
# - general: 通用任务
# - data_analysis: 数据分析
# - code_generation: 代码生成
# - documentation: 文档编写
# - debugging: 调试任务
```

### 任务筛选和清理
```powershell
# 按状态筛选任务
Get-AIITaskList -Status "completed" -Limit 5

# 清理30天前的任务
Clear-AIITasks -DaysOld 30

# 清理时保留配置
Reset-AIISystem -Force -KeepConfig
```

### 自动化脚本
```powershell
# 创建自动化工作流脚本
$task1 = New-AIITask "第一步：数据收集"
Start-AIITask -TaskId $task1.TaskId -Wait

$task2 = New-AIITask "第二步：数据分析"
Start-AIITask -TaskId $task2.TaskId -Wait

$task3 = New-AIITask "第三步：生成报告"
Start-AIITask -TaskId $task3.TaskId -Wait

# 在VS Code中打开所有任务
Open-AIIInVSCode -TaskId $task1.TaskId
```

## 🐛 故障排除

### 常见问题

#### 1. 模块无法导入
```powershell
# 检查模块路径
Get-Module -ListAvailable -Name AIIWorkflow

# 手动导入
Import-Module "O:\AII\上下文助手\powershell\AIIWorkflow.psd1" -Force
```

#### 2. 工作流根目录未找到
```powershell
# 手动设置工作流根目录
$env:AII_WORKFLOW_ROOT = "O:\AII\上下文助手"
Initialize-AIIWorkflow -Force
```

#### 3. VS Code集成失败
```powershell
# 检查VS Code安装
Get-AIIVSCodeStatus

# 手动指定VS Code路径
# 编辑配置文件或在脚本中设置
```

#### 4. 状态同步问题
```powershell
# 清理状态并重新初始化
Clear-AIIState
Initialize-AIIWorkflow -Force
```

### 调试模式
```powershell
# 启用详细日志
$VerbosePreference = "Continue"

# 运行命令查看详细信息
Get-AIIStatus -Verbose
New-AIITask "测试任务" -Verbose
```

### 获取帮助
```powershell
# 查看模块所有命令
Get-Command -Module AIIWorkflow

# 查看命令帮助
Get-Help New-AIITask -Detailed
Get-Help Reset-AIISystem -Examples

# 查看别名
Get-Alias | Where-Object { $_.Definition -like "*AII*" }
```

## 📊 性能优化

### 状态同步间隔
默认状态同步间隔为2秒，可在代码中调整：
```powershell
# 在StateManager.psm1中修改
$script:StateSyncInterval = 5000  # 改为5秒
```

### 历史记录限制
默认保留100条历史记录，可在配置中调整：
```powershell
# 修改配置
$global:AIIConfig.MaxHistorySize = 50
Save-AIIConfig
```

### 自动清理
```powershell
# 设置自动清理天数
$global:AIIConfig.AutoCleanupDays = 14
Save-AIIConfig

# 手动清理
Clear-AIITasks -DaysOld 30
```

## 🔄 与原始ww.py的兼容性

### 命令映射
| 原始命令 | PowerShell命令 | 说明 |
|---------|---------------|------|
| `ww "任务描述"` | `New-AIITask "任务描述"` | 创建新任务 |
| `ww status` | `Get-AIIStatus` | 查看状态 |
| `ww recover` | `Resume-AIITask` | 恢复任务 |
| `ww clean 30` | `Clear-AIITasks -DaysOld 30` | 清理旧任务 |

### 状态文件兼容
PowerShell模块完全兼容现有的状态文件格式：
- 使用相同的JSON状态文件格式
- 共享相同的任务目录结构
- 兼容现有的Python脚本和工作流

## 📈 监控和日志

### 查看系统日志
```powershell
# 查看工作流日志
Get-Content "O:\AII\上下文助手\AI_WORKFLOW_LOG.md" -Tail 20

# 查看错误日志
Get-Content "O:\AII\上下文助手\logs\error.log" -Tail 10
```

### 监控系统状态
```powershell
# 持续监控状态
while ($true) {
    Clear-Host
    Get-AIIStatus | Format-List
    Start-Sleep -Seconds 5
}
```

### 导出状态报告
```powershell
# 导出状态为JSON
Get-AIIStatus | ConvertTo-Json -Depth 10 | Out-File "status-report.json"

# 导出任务列表为CSV
Get-AIITaskList | Export-Csv "tasks.csv" -NoTypeInformation
```

## 🎉 开始使用

### 第一步：安装和初始化
```powershell
# 1. 安装模块
.\install.ps1

# 2. 重新启动PowerShell或运行
. "$env:USERPROFILE\Documents\WindowsPowerShell\Modules\AIIWorkflow\AIIWorkflow.Config.ps1"

# 3. 验证安装
Get-AIIModuleInfo
```

### 第二步：创建第一个任务
```powershell
# 创建简单任务
aii-start "帮我写一个Python脚本，读取CSV文件并生成统计报告"

# 查看任务状态
aii-status

# 在VS Code中打开
aii-vscode
```

### 第三步：探索高级功能
```powershell
# 使用模板创建任务
New-AIITask "数据分析" -Template data_analysis -Priority High

# 批量处理任务
1..5 | ForEach-Object {
    New-AIITask "任务 $_"
    Start-Sleep -Seconds 1
}

# 系统维护
Test-AIISystem
Backup-AIISystem
```

## 📞 获取帮助

### 在线帮助
```powershell
# 查看完整帮助系统
Get-Help about_AIIWorkflow

# 查看特定命令帮助
Get-Help New-AIITask -Full
Get-Help Reset-AIISystem -Examples
```

### 错误报告
遇到问题时：
1. 检查日志文件：`O:\AII\上下文助手\logs\`
2. 运行系统测试：`Test-AIISystem`
3. 尝试修复：`Repair-AIISystem`
4. 重置系统：`Reset-AIISystem -Force -KeepConfig`

### 反馈和建议
- 查看 `AI_WORKFLOW_LOG.md` 了解系统行为
- 使用 `-Verbose` 参数获取详细输出
- 检查PowerShell事件日志

---

**提示**：PowerShell模块提供了比原始脚本更强大和灵活的功能，同时保持了完全兼容性。建议新用户从基础命令开始，逐步探索高级功能。