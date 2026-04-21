# AII Workflow PowerShell Module - Core Module
# 核心功能模块：提供基础功能和工作流根目录管理

using namespace System.Management.Automation
using namespace System.Management.Automation.Host
using namespace System.IO

# 全局变量
$global:AIIConfig = $null
$global:AIIWorkflowRoot = $null
$global:AIIState = @{}

# 模块私有变量
$script:ModuleName = "AIIWorkflow"
$script:ModuleVersion = "1.0.0"
$script:DefaultConfig = @{
    Version = "2.0"
    AutoCopyToClipboard = $true
    AutoOpenClaude = $false
    DefaultTheme = "light"
    NotificationEnabled = $true
    MaxHistorySize = 100
    AutoCleanupDays = 30
    InteractiveMode = $true
    ColorOutput = $true
    PreferredTaskTypes = @()
    LastUsedTemplate = "general"
    InstalledAt = (Get-Date -Format "yyyy-MM-dd")
}

function Get-AIIWorkflowRoot {
<#
.SYNOPSIS
获取AII工作流系统的根目录

.DESCRIPTION
自动检测AII工作流系统的安装目录，支持多种检测方法。

.EXAMPLE
Get-AIIWorkflowRoot
返回工作流根目录路径

.OUTPUTS
[string] 工作流根目录路径
#>
    [CmdletBinding()]
    [OutputType([string])]
    param()

    # 方法1：检查环境变量
    $envPath = [Environment]::GetEnvironmentVariable("AII_WORKFLOW_ROOT", "User")
    if ($envPath -and (Test-Path $envPath)) {
        Write-Verbose "通过环境变量找到工作流根目录: $envPath"
        return $envPath
    }

    # 方法2：检查当前目录
    $currentDir = Get-Location
    $possiblePaths = @(
        ".\AII工作流",
        ".\AII-Workflow",
        ".\AII_Workflow",
        ".\上下文助手",
        "."
    )

    foreach ($path in $possiblePaths) {
        $fullPath = Join-Path $currentDir $path
        if (Test-Path (Join-Path $fullPath "ww.py") -or
            Test-Path (Join-Path $fullPath "ww_enhanced.py")) {
            Write-Verbose "在当前目录找到工作流根目录: $fullPath"
            return $fullPath
        }
    }

    # 方法3：检查标准安装路径
    $standardPaths = @(
        "O:\AII\上下文助手",
        "C:\AII\上下文助手",
        "$env:USERPROFILE\AII\上下文助手",
        "$env:HOME\AII\上下文助手"
    )

    foreach ($path in $standardPaths) {
        if (Test-Path (Join-Path $path "ww.py") -or
            Test-Path (Join-Path $path "ww_enhanced.py")) {
            Write-Verbose "在标准路径找到工作流根目录: $path"
            return $path
        }
    }

    # 方法4：提示用户输入
    Write-Warning "无法自动找到AII工作流根目录"
    $userPath = Read-Host "请输入AII工作流根目录路径（如 O:\AII\上下文助手）"

    if ($userPath -and (Test-Path $userPath)) {
        # 保存到环境变量供下次使用
        [Environment]::SetEnvironmentVariable("AII_WORKFLOW_ROOT", $userPath, "User")
        Write-Verbose "已保存工作流根目录到环境变量: $userPath"
        return $userPath
    }

    throw "无效的工作流根目录路径: $userPath"
}

function Test-AIIEnvironment {
<#
.SYNOPSIS
测试AII工作流环境是否可用

.DESCRIPTION
检查AII工作流系统所需的所有组件是否完整可用。

.EXAMPLE
Test-AIIEnvironment
测试环境并返回结果

.OUTPUTS
[bool] 环境是否可用
#>
    [CmdletBinding()]
    [OutputType([bool])]
    param()

    try {
        $root = Get-AIIWorkflowRoot -ErrorAction Stop

        # 检查核心文件
        $requiredFiles = @(
            "ww_enhanced.py",
            "ww.bat",
            ".claude\CLAUDE.md",
            ".claude\agents\manifest.json",
            "scripts\state_machine.py"
        )

        foreach ($file in $requiredFiles) {
            $fullPath = Join-Path $root $file
            if (-not (Test-Path $fullPath)) {
                Write-Warning "缺少必要文件: $file"
                return $false
            }
        }

        # 检查Python可用性
        try {
            $pythonVersion = python --version 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Python未正确安装或不在PATH中"
                return $false
            }
            Write-Verbose "Python版本: $pythonVersion"
        } catch {
            Write-Warning "无法执行Python命令: $_"
            return $false
        }

        # 检查工作流脚本可执行性
        $testScript = Join-Path $root "ww_enhanced.py"
        try {
            $result = python $testScript "--version" 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "工作流脚本无法执行: $result"
                return $false
            }
        } catch {
            Write-Warning "工作流脚本测试失败: $_"
            return $false
        }

        Write-Verbose "AII工作流环境测试通过"
        return $true

    } catch {
        Write-Error "环境测试失败: $_"
        return $false
    }
}

function Initialize-AIIWorkflow {
<#
.SYNOPSIS
初始化AII工作流系统

.DESCRIPTION
初始化工作流系统，加载配置，设置环境变量。

.EXAMPLE
Initialize-AIIWorkflow
初始化工作流系统

.OUTPUTS
[hashtable] 初始化后的配置
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter()]
        [switch]$Force
    )

    begin {
        Write-Verbose "开始初始化AII工作流系统..."
    }

    process {
        try {
            # 1. 获取工作流根目录
            $root = Get-AIIWorkflowRoot -ErrorAction Stop
            $global:AIIWorkflowRoot = $root
            Write-Verbose "工作流根目录: $root"

            # 2. 检查环境
            if (-not (Test-AIIEnvironment)) {
                throw "AII工作流环境检查失败"
            }

            # 3. 加载或创建配置
            $configPath = Join-Path $root "config\user_prefs.json"
            $configDir = Split-Path $configPath -Parent

            if (-not (Test-Path $configDir)) {
                New-Item -ItemType Directory -Path $configDir -Force | Out-Null
                Write-Verbose "创建配置目录: $configDir"
            }

            if (Test-Path $configPath -and -not $Force) {
                # 加载现有配置
                $configJson = Get-Content $configPath -Raw -ErrorAction Stop
                $global:AIIConfig = $configJson | ConvertFrom-Json -AsHashtable
                Write-Verbose "从文件加载配置: $configPath"
            } else {
                # 创建默认配置
                $global:AIIConfig = $script:DefaultConfig.Clone()

                # 保存配置
                $configJson = $global:AIIConfig | ConvertTo-Json -Depth 10
                Set-Content -Path $configPath -Value $configJson -Encoding UTF8
                Write-Verbose "创建默认配置: $configPath"
            }

            # 4. 加载状态
            Initialize-AIIState

            # 5. 设置环境变量
            Set-EnvironmentVariables

            # 6. 验证关键组件
            Test-KeyComponents

            Write-Verbose "AII工作流系统初始化完成"
            return $global:AIIConfig

        } catch {
            Write-Error "初始化失败: $_"
            throw
        }
    }

    end {
        Write-Verbose "初始化过程结束"
    }
}

function Initialize-AIIState {
<#
.SYNOPSIS
初始化AII工作流状态

.DESCRIPTION
加载工作流状态信息，包括当前任务、历史记录等。

.EXAMPLE
Initialize-AIIState
初始化工作流状态

.NOTES
此函数由Initialize-AIIWorkflow自动调用
#>
    [CmdletBinding()]
    param()

    try {
        $root = $global:AIIWorkflowRoot

        # 1. 加载任务历史
        $historyPath = Join-Path $root "config\task_history.json"
        if (Test-Path $historyPath) {
            $historyJson = Get-Content $historyPath -Raw -ErrorAction SilentlyContinue
            if ($historyJson) {
                $global:AIIState.History = $historyJson | ConvertFrom-Json -AsHashtable
            }
        }

        if (-not $global:AIIState.History) {
            $global:AIIState.History = @{
                Tasks = @()
                LastTaskId = $null
                LastActivity = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            }
        }

        # 2. 检测当前任务
        $currentTask = Find-CurrentTask
        $global:AIIState.CurrentTask = $currentTask

        # 3. 加载会话状态
        $sessionPath = Join-Path $root "cache\session_state.json"
        if (Test-Path $sessionPath) {
            $sessionJson = Get-Content $sessionPath -Raw -ErrorAction SilentlyContinue
            if ($sessionJson) {
                $global:AIIState.Session = $sessionJson | ConvertFrom-Json -AsHashtable
            }
        }

        if (-not $global:AIIState.Session) {
            $global:AIIState.Session = @{
                SessionId = [Guid]::NewGuid().ToString()
                StartedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                WindowCount = 0
                LastWindowId = $null
            }
        }

        # 4. 更新会话状态
        $global:AIIState.Session.WindowCount++
        $global:AIIState.Session.LastWindowId = [Guid]::NewGuid().ToString()

        Write-Verbose "工作流状态初始化完成"
        Write-Verbose "当前任务: $(if ($global:AIIState.CurrentTask) { $global:AIIState.CurrentTask.TaskId } else { '无' })"
        Write-Verbose "历史任务数: $($global:AIIState.History.Tasks.Count)"

    } catch {
        Write-Warning "状态初始化失败: $_"
        $global:AIIState = @{
            History = @{ Tasks = @(); LastTaskId = $null }
            CurrentTask = $null
            Session = @{
                SessionId = [Guid]::NewGuid().ToString()
                StartedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                WindowCount = 1
                LastWindowId = [Guid]::NewGuid().ToString()
            }
        }
    }
}

function Find-CurrentTask {
<#
.SYNOPSIS
查找当前正在运行的任务

.DESCRIPTION
通过检查状态文件和进程来查找当前任务。

.OUTPUTS
[hashtable] 当前任务信息
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param()

    $root = $global:AIIWorkflowRoot

    # 方法1：检查tasks目录中的状态文件
    $tasksDir = Join-Path $root "tasks"
    if (Test-Path $tasksDir) {
        $stateFiles = Get-ChildItem -Path $tasksDir -Filter "*.json" -Recurse

        foreach ($file in $stateFiles) {
            try {
                $stateJson = Get-Content $file.FullName -Raw -ErrorAction Stop
                $state = $stateJson | ConvertFrom-Json -AsHashtable

                if ($state.Status -and $state.Status -ne "archiving" -and $state.Status -ne "completed") {
                    return @{
                        TaskId = $state.TaskId
                        Status = $state.Status
                        CreatedAt = $state.CreatedAt
                        UpdatedAt = $state.UpdatedAt
                        StateFile = $file.FullName
                    }
                }
            } catch {
                Write-Verbose "无法解析状态文件: $($file.FullName)"
            }
        }
    }

    # 方法2：检查日志文件中的最近任务
    $logFile = Join-Path $root "AI_WORKFLOW_LOG.md"
    if (Test-Path $logFile) {
        $logContent = Get-Content $logFile -Tail 20 -ErrorAction SilentlyContinue
        if ($logContent) {
            foreach ($line in $logContent) {
                if ($line -match "任务ID:\s*(\S+)") {
                    return @{
                        TaskId = $matches[1]
                        Status = "unknown"
                        Source = "log"
                        LogLine = $line
                    }
                }
            }
        }
    }

    # 方法3：检查进程
    $processes = Get-Process | Where-Object {
        $_.ProcessName -eq "python" -and
        $_.CommandLine -like "*ww_enhanced.py*"
    }

    if ($processes) {
        return @{
            TaskId = "running_python_process"
            Status = "executing"
            ProcessId = $processes[0].Id
            ProcessName = $processes[0].ProcessName
        }
    }

    return $null
}

function Set-EnvironmentVariables {
<#
.SYNOPSIS
设置AII工作流相关的环境变量

.DESCRIPTION
设置PowerShell会话中使用的环境变量。

.EXAMPLE
Set-EnvironmentVariables
设置环境变量
#>
    [CmdletBinding()]
    param()

    $root = $global:AIIWorkflowRoot

    # 设置会话级环境变量
    $env:AII_WORKFLOW_ROOT = $root
    $env:AII_WORKFLOW_CONFIG = Join-Path $root "config\user_prefs.json"
    $env:AII_WORKFLOW_LOG = Join-Path $root "AI_WORKFLOW_LOG.md"

    # 添加到PATH（仅当前会话）
    $env:Path = "$root;$env:Path"

    Write-Verbose "已设置环境变量"
}

function Test-KeyComponents {
<#
.SYNOPSIS
测试关键组件是否可用

.DESCRIPTION
测试AII工作流系统的关键组件。

.EXAMPLE
Test-KeyComponents
测试关键组件
#>
    [CmdletBinding()]
    param()

    $root = $global:AIIWorkflowRoot

    Write-Verbose "测试关键组件..."

    # 测试Python脚本
    $scripts = @(
        "ww_enhanced.py",
        "scripts\state_machine.py",
        "scripts\workflow_utils.py",
        "scripts\log_manager.py"
    )

    foreach ($script in $scripts) {
        $fullPath = Join-Path $root $script
        if (Test-Path $fullPath) {
            Write-Verbose "✅ $script 存在"
        } else {
            Write-Warning "⚠️  $script 不存在"
        }
    }

    # 测试Agent文件
    $agents = @(
        ".claude\CLAUDE.md",
        ".claude\agents\manifest.json",
        ".claude\agents\workflow_agent.md"
    )

    foreach ($agent in $agents) {
        $fullPath = Join-Path $root $agent
        if (Test-Path $fullPath) {
            Write-Verbose "✅ $agent 存在"
        } else {
            Write-Warning "⚠️  $agent 不存在"
        }
    }

    # 测试目录结构
    $dirs = @(
        "tasks",
        "config",
        "cache",
        "logs",
        "scripts"
    )

    foreach ($dir in $dirs) {
        $fullPath = Join-Path $root $dir
        if (Test-Path $fullPath) {
            Write-Verbose "✅ 目录 $dir 存在"
        } else {
            Write-Warning "⚠️  目录 $dir 不存在"
        }
    }

    Write-Verbose "关键组件测试完成"
}

function Save-AIIConfig {
<#
.SYNOPSIS
保存AII工作流配置

.DESCRIPTION
将当前配置保存到配置文件。

.EXAMPLE
Save-AIIConfig
保存配置
#>
    [CmdletBinding()]
    param()

    try {
        $configPath = Join-Path $global:AIIWorkflowRoot "config\user_prefs.json"
        $configJson = $global:AIIConfig | ConvertTo-Json -Depth 10
        Set-Content -Path $configPath -Value $configJson -Encoding UTF8
        Write-Verbose "配置已保存: $configPath"
    } catch {
        Write-Error "保存配置失败: $_"
    }
}

function Save-AIIState {
<#
.SYNOPSIS
保存AII工作流状态

.DESCRIPTION
将当前状态保存到文件，用于窗口间同步。

.EXAMPLE
Save-AIIState
保存状态
#>
    [CmdletBinding()]
    param()

    try {
        $root = $global:AIIWorkflowRoot

        # 保存任务历史
        $historyPath = Join-Path $root "config\task_history.json"
        $historyDir = Split-Path $historyPath -Parent

        if (-not (Test-Path $historyDir)) {
            New-Item -ItemType Directory -Path $historyDir -Force | Out-Null
        }

        $historyJson = $global:AIIState.History | ConvertTo-Json -Depth 10
        Set-Content -Path $historyPath -Value $historyJson -Encoding UTF8

        # 保存会话状态
        $sessionPath = Join-Path $root "cache\session_state.json"
        $sessionDir = Split-Path $sessionPath -Parent

        if (-not (Test-Path $sessionDir)) {
            New-Item -ItemType Directory -Path $sessionDir -Force | Out-Null
        }

        $global:AIIState.Session.UpdatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        $sessionJson = $global:AIIState.Session | ConvertTo-Json -Depth 10
        Set-Content -Path $sessionPath -Value $sessionJson -Encoding UTF8

        Write-Verbose "状态已保存"

    } catch {
        Write-Warning "状态保存失败: $_"
    }
}

function Get-AIIInfo {
<#
.SYNOPSIS
获取AII工作流系统信息

.DESCRIPTION
显示系统版本、配置、状态等信息。

.EXAMPLE
Get-AIIInfo
显示系统信息

.OUTPUTS
[pscustomobject] 系统信息
#>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param()

    $info = [pscustomobject]@{
        ModuleName = $script:ModuleName
        ModuleVersion = $script:ModuleVersion
        WorkflowRoot = $global:AIIWorkflowRoot
        Config = $global:AIIConfig
        State = $global:AIIState
        EnvironmentOk = Test-AIIEnvironment
        CurrentTask = $global:AIIState.CurrentTask
        HistoryCount = if ($global:AIIState.History.Tasks) { $global:AIIState.History.Tasks.Count } else { 0 }
        SessionId = $global:AIIState.Session.SessionId
        WindowCount = $global:AIIState.Session.WindowCount
    }

    return $info
}

function Show-AIIWelcome {
<#
.SYNOPSIS
显示AII工作流欢迎信息

.DESCRIPTION
显示系统欢迎信息和快速开始指南。

.EXAMPLE
Show-AIIWelcome
显示欢迎信息
#>
    [CmdletBinding()]
    param()

    Write-Host "`n" -NoNewline
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "🚀 AII 工作流系统 - PowerShell 模块" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "版本: $($script:ModuleVersion)" -ForegroundColor Yellow
    Write-Host "工作流根目录: $global:AIIWorkflowRoot" -ForegroundColor Yellow
    Write-Host ""

    # 显示当前状态
    if ($global:AIIState.CurrentTask) {
        Write-Host "📋 当前任务:" -ForegroundColor Cyan
        Write-Host "   任务ID: $($global:AIIState.CurrentTask.TaskId)" -ForegroundColor White
        Write-Host "   状态: $($global:AIIState.CurrentTask.Status)" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host "📋 当前任务: 无" -ForegroundColor Gray
        Write-Host ""
    }

    # 显示快速开始命令
    Write-Host "💡 快速开始:" -ForegroundColor Cyan
    Write-Host "   New-AIITask '任务描述'     # 启动新任务" -ForegroundColor White
    Write-Host "   Get-AIIStatus              # 查看状态" -ForegroundColor White
    Write-Host "   Resume-AIITask             # 恢复任务" -ForegroundColor White
    Write-Host "   Reset-AIISystem            # 重置系统" -ForegroundColor White
    Write-Host ""

    # 显示快捷别名
    Write-Host "⚡ 快捷别名:" -ForegroundColor Cyan
    Write-Host "   aii-start  = New-AIITask" -ForegroundColor White
    Write-Host "   aii-status = Get-AIIStatus" -ForegroundColor White
    Write-Host "   aii-resume = Resume-AIITask" -ForegroundColor White
    Write-Host "   aii-reset  = Reset-AIISystem" -ForegroundColor White
    Write-Host ""

    Write-Host "输入 'Get-Help AIIWorkflow' 查看完整帮助" -ForegroundColor Gray
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host ""
}

# 导出模块函数
Export-ModuleMember -Function @(
    'Get-AIIWorkflowRoot',
    'Test-AIIEnvironment',
    'Initialize-AIIWorkflow',
    'Get-AIIInfo',
    'Show-AIIWelcome',
    'Save-AIIConfig',
    'Save-AIIState'
)

# 模块初始化
if (-not $global:AIIWorkflowRoot) {
    try {
        Initialize-AIIWorkflow -ErrorAction SilentlyContinue | Out-Null
    } catch {
        Write-Warning "AII工作流初始化失败: $_"
    }
}