# AII Workflow PowerShell Module - Task Manager
# 任务管理模块：负责任务创建、执行和管理

using namespace System.Management.Automation
using namespace System.IO
using namespace System.Diagnostics
using namespace System.Text

class TaskManager {
    # 任务管理器类
    [string]$RootPath
    [hashtable]$CurrentTask
    [System.Diagnostics.Process]$TaskProcess
    [System.Threading.Timer]$TaskMonitor
    [bool]$IsTaskRunning = $false

    TaskManager([string]$rootPath) {
        $this.RootPath = $rootPath
    }

    [hashtable] CreateTask([string]$description) {
        # 创建新任务
        $taskId = "TASK-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        $taskDir = Join-Path $this.RootPath "tasks\$taskId"

        try {
            # 创建任务目录
            New-Item -ItemType Directory -Path $taskDir -Force | Out-Null
            New-Item -ItemType Directory -Path (Join-Path $taskDir "artifacts") -Force | Out-Null

            # 创建任务输入文件
            $inputFile = Join-Path $taskDir "input.md"
            $inputContent = @"
# 任务描述
$description

# 创建时间
$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

# 任务ID
$taskId

# 状态
待处理
"@
            Set-Content -Path $inputFile -Value $inputContent -Encoding UTF8

            # 创建状态文件
            $stateFile = Join-Path $taskDir "state.json"
            $state = @{
                TaskId = $taskId
                Description = $description
                Status = "planning"
                Pipeline = @("planning", "prompt_optimizing", "executing", "verifying", "archiving")
                CurrentStepIndex = 0
                RetryCount = 0
                MaxRetries = 3
                NextAgent = "planner"
                Checkpoint = @{}
                CreatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                UpdatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                InputFile = $inputFile
                OutputDir = Join-Path $taskDir "artifacts"
            }

            $stateJson = $state | ConvertTo-Json -Depth 10
            Set-Content -Path $stateFile -Value $stateJson -Encoding UTF8

            # 更新状态管理器
            $stateManager = Get-AIIStateManager
            $stateManager.CurrentState.CurrentTask = @{
                TaskId = $taskId
                Status = "planning"
                CreatedAt = $state.CreatedAt
                UpdatedAt = $state.UpdatedAt
                StateFile = $stateFile
                TaskDir = $taskDir
                NextAgent = "planner"
                Checkpoint = @{}
            }

            $stateManager.AddTaskToHistory($taskId, $description, "created")
            $stateManager.SaveState()

            Write-Verbose "任务创建成功: $taskId"
            return @{
                Success = $true
                TaskId = $taskId
                TaskDir = $taskDir
                State = $state
            }

        } catch {
            Write-Error "任务创建失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [hashtable] StartTask([string]$taskId) {
        # 启动任务执行
        try {
            # 查找任务目录
            $taskDir = Find-TaskDirectory -TaskId $taskId
            if (-not $taskDir) {
                throw "未找到任务目录: $taskId"
            }

            # 检查任务状态
            $stateFile = Join-Path $taskDir "state.json"
            if (-not (Test-Path $stateFile)) {
                throw "任务状态文件不存在: $stateFile"
            }

            $stateJson = Get-Content $stateFile -Raw -ErrorAction Stop
            $state = $stateJson | ConvertFrom-Json -AsHashtable

            # 更新状态管理器
            $stateManager = Get-AIIStateManager
            $stateManager.CurrentState.CurrentTask = @{
                TaskId = $taskId
                Status = $state.Status
                CreatedAt = $state.CreatedAt
                UpdatedAt = $state.UpdatedAt
                StateFile = $stateFile
                TaskDir = $taskDir
                NextAgent = $state.NextAgent
                Checkpoint = $state.Checkpoint
            }

            $stateManager.SaveState()

            # 启动任务执行
            $scriptPath = Join-Path $this.RootPath "ww_enhanced.py"
            $args = @("start", $taskId)

            $processInfo = New-Object System.Diagnostics.ProcessStartInfo
            $processInfo.FileName = "python"
            $processInfo.Arguments = "`"$scriptPath`" $args"
            $processInfo.WorkingDirectory = $this.RootPath
            $processInfo.UseShellExecute = $false
            $processInfo.RedirectStandardOutput = $true
            $processInfo.RedirectStandardError = $true
            $processInfo.CreateNoWindow = $true

            $this.TaskProcess = New-Object System.Diagnostics.Process
            $this.TaskProcess.StartInfo = $processInfo
            $this.TaskProcess.EnableRaisingEvents = $true

            # 注册进程退出事件
            Register-ObjectEvent -InputObject $this.TaskProcess -EventName Exited -Action {
                param($source, $eventArgs)
                $taskManager = [TaskManager]$this
                $taskManager.OnTaskProcessExited($source, $eventArgs)
            }

            $this.TaskProcess.Start() | Out-Null
            $this.IsTaskRunning = $true

            # 启动任务监控
            $this.StartTaskMonitor()

            Write-Verbose "任务启动成功: $taskId"
            return @{
                Success = $true
                TaskId = $taskId
                ProcessId = $this.TaskProcess.Id
                Status = "running"
            }

        } catch {
            Write-Error "任务启动失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [void] StartTaskMonitor() {
        # 启动任务监控定时器
        $timerCallback = {
            param($state)
            try {
                $taskManager = [TaskManager]$state
                $taskManager.MonitorTask()
            } catch {
                Write-Warning "任务监控失败: $_"
            }
        }

        $this.TaskMonitor = [System.Threading.Timer]::new(
            $timerCallback,
            $this,
            1000,  # 1秒检查一次
            1000
        )

        Write-Verbose "任务监控定时器已启动"
    }

    [void] StopTaskMonitor() {
        # 停止任务监控定时器
        if ($this.TaskMonitor) {
            $this.TaskMonitor.Dispose()
            $this.TaskMonitor = $null
            Write-Verbose "任务监控定时器已停止"
        }
    }

    [void] MonitorTask() {
        # 监控任务执行状态
        if (-not $this.IsTaskRunning -or -not $this.TaskProcess) {
            return
        }

        try {
            # 检查进程是否还在运行
            if ($this.TaskProcess.HasExited) {
                $this.OnTaskProcessExited($this.TaskProcess, $null)
                return
            }

            # 检查任务状态文件
            if ($this.CurrentTask -and $this.CurrentTask.TaskDir) {
                $stateFile = Join-Path $this.CurrentTask.TaskDir "state.json"
                if (Test-Path $stateFile) {
                    $stateJson = Get-Content $stateFile -Raw -ErrorAction SilentlyContinue
                    if ($stateJson) {
                        $state = $stateJson | ConvertFrom-Json -AsHashtable

                        # 更新当前任务状态
                        $stateManager = Get-AIIStateManager
                        if ($stateManager.CurrentState.CurrentTask.TaskId -eq $state.TaskId) {
                            $stateManager.CurrentState.CurrentTask.Status = $state.Status
                            $stateManager.CurrentState.CurrentTask.UpdatedAt = $state.UpdatedAt
                            $stateManager.CurrentState.CurrentTask.NextAgent = $state.NextAgent
                            $stateManager.CurrentState.CurrentTask.Checkpoint = $state.Checkpoint

                            # 如果任务完成，更新历史
                            if ($state.Status -in @("completed", "failed", "archiving")) {
                                $stateManager.AddTaskToHistory(
                                    $state.TaskId,
                                    $state.Description,
                                    $state.Status
                                )
                            }

                            $stateManager.SaveState()
                        }
                    }
                }
            }

        } catch {
            Write-Verbose "任务监控出错: $_"
        }
    }

    [void] OnTaskProcessExited([object]$source, [object]$eventArgs) {
        # 任务进程退出处理
        $this.IsTaskRunning = $false
        $this.StopTaskMonitor()

        $exitCode = $source.ExitCode
        $stateManager = Get-AIIStateManager

        if ($exitCode -eq 0) {
            Write-Verbose "任务进程正常退出"
            if ($stateManager.CurrentState.CurrentTask) {
                $stateManager.CurrentState.CurrentTask.Status = "completed"
                $stateManager.SaveState()
            }
        } else {
            Write-Warning "任务进程异常退出，代码: $exitCode"
            if ($stateManager.CurrentState.CurrentTask) {
                $stateManager.CurrentState.CurrentTask.Status = "failed"
                $stateManager.SaveState()
            }
        }

        $this.TaskProcess = $null
    }

    [hashtable] StopTask() {
        # 停止当前任务
        try {
            if (-not $this.IsTaskRunning -or -not $this.TaskProcess) {
                Write-Warning "没有正在运行的任务"
                return @{
                    Success = $false
                    Error = "没有正在运行的任务"
                }
            }

            Write-Verbose "正在停止任务..."

            # 停止进程
            if (-not $this.TaskProcess.HasExited) {
                $this.TaskProcess.Kill()
                Start-Sleep -Milliseconds 500
            }

            $this.IsTaskRunning = $false
            $this.StopTaskMonitor()
            $this.TaskProcess = $null

            # 更新状态
            $stateManager = Get-AIIStateManager
            if ($stateManager.CurrentState.CurrentTask) {
                $stateManager.CurrentState.CurrentTask.Status = "stopped"
                $stateManager.AddTaskToHistory(
                    $stateManager.CurrentState.CurrentTask.TaskId,
                    "手动停止的任务",
                    "stopped"
                )
                $stateManager.SaveState()
            }

            Write-Verbose "任务已停止"
            return @{
                Success = $true
                Message = "任务已停止"
            }

        } catch {
            Write-Error "停止任务失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [hashtable] GetTaskInfo([string]$taskId) {
        # 获取任务详细信息
        try {
            $taskDir = Find-TaskDirectory -TaskId $taskId
            if (-not $taskDir) {
                throw "未找到任务目录: $taskId"
            }

            $stateFile = Join-Path $taskDir "state.json"
            if (-not (Test-Path $stateFile)) {
                throw "任务状态文件不存在: $stateFile"
            }

            $stateJson = Get-Content $stateFile -Raw -ErrorAction Stop
            $state = $stateJson | ConvertFrom-Json -AsHashtable

            # 收集任务文件信息
            $inputFile = Join-Path $taskDir "input.md"
            $artifactsDir = Join-Path $taskDir "artifacts"
            $artifacts = @()

            if (Test-Path $artifactsDir) {
                $artifactFiles = Get-ChildItem -Path $artifactsDir -File -Recurse -ErrorAction SilentlyContinue
                $artifacts = $artifactFiles | ForEach-Object {
                    @{
                        Name = $_.Name
                        FullName = $_.FullName
                        Size = $_.Length
                        LastWriteTime = $_.LastWriteTime
                    }
                }
            }

            # 读取输入文件内容
            $inputContent = if (Test-Path $inputFile) {
                Get-Content $inputFile -Raw -ErrorAction SilentlyContinue
            } else {
                $null
            }

            # 获取进程信息（如果正在运行）
            $processInfo = $null
            if ($this.IsTaskRunning -and $this.TaskProcess -and -not $this.TaskProcess.HasExited) {
                $processInfo = @{
                    ProcessId = $this.TaskProcess.Id
                    StartTime = $this.TaskProcess.StartTime
                    TotalProcessorTime = $this.TaskProcess.TotalProcessorTime
                    PeakWorkingSet64 = $this.TaskProcess.PeakWorkingSet64
                }
            }

            return @{
                Success = $true
                TaskId = $taskId
                State = $state
                InputFile = $inputFile
                InputContent = $inputContent
                Artifacts = $artifacts
                ArtifactsCount = $artifacts.Count
                ProcessInfo = $processInfo
                TaskDir = $taskDir
                IsRunning = $this.IsTaskRunning -and $this.TaskProcess -and -not $this.TaskProcess.HasExited
            }

        } catch {
            Write-Error "获取任务信息失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [array] ListTasks([int]$limit = 10) {
        # 列出所有任务
        try {
            $tasksDir = Join-Path $this.RootPath "tasks"
            if (-not (Test-Path $tasksDir)) {
                return @()
            }

            $taskDirs = Get-ChildItem -Path $tasksDir -Directory -ErrorAction SilentlyContinue |
                       Sort-Object LastWriteTime -Descending

            $tasks = @()
            $count = 0

            foreach ($dir in $taskDirs) {
                if ($count -ge $limit) {
                    break
                }

                $stateFile = Join-Path $dir.FullName "state.json"
                if (Test-Path $stateFile) {
                    try {
                        $stateJson = Get-Content $stateFile -Raw -ErrorAction Stop
                        $state = $stateJson | ConvertFrom-Json -AsHashtable

                        $tasks += @{
                            TaskId = $state.TaskId
                            Description = $state.Description
                            Status = $state.Status
                            CreatedAt = $state.CreatedAt
                            UpdatedAt = $state.UpdatedAt
                            TaskDir = $dir.FullName
                            IsCurrent = $false
                        }

                        $count++
                    } catch {
                        Write-Verbose "无法解析任务状态文件: $stateFile"
                    }
                }
            }

            # 标记当前任务
            $stateManager = Get-AIIStateManager
            if ($stateManager.CurrentState.CurrentTask) {
                $currentTaskId = $stateManager.CurrentState.CurrentTask.TaskId
                foreach ($task in $tasks) {
                    if ($task.TaskId -eq $currentTaskId) {
                        $task.IsCurrent = $true
                        break
                    }
                }
            }

            return $tasks

        } catch {
            Write-Error "列出任务失败: $_"
            return @()
        }
    }

    [hashtable] CleanupTasks([int]$daysOld = 30) {
        # 清理旧任务
        try {
            $tasksDir = Join-Path $this.RootPath "tasks"
            if (-not (Test-Path $tasksDir)) {
                return @{
                    Success = $true
                    Message = "任务目录不存在，无需清理"
                    DeletedCount = 0
                }
            }

            $cutoffDate = (Get-Date).AddDays(-$daysOld)
            $taskDirs = Get-ChildItem -Path $tasksDir -Directory -ErrorAction SilentlyContinue

            $deletedCount = 0
            $skippedCount = 0

            foreach ($dir in $taskDirs) {
                $stateFile = Join-Path $dir.FullName "state.json"
                $shouldDelete = $false

                if (Test-Path $stateFile) {
                    try {
                        $stateJson = Get-Content $stateFile -Raw -ErrorAction Stop
                        $state = $stateJson | ConvertFrom-Json -AsHashtable

                        $updatedAt = [DateTime]::Parse($state.UpdatedAt)
                        if ($updatedAt -lt $cutoffDate -and $state.Status -in @("completed", "failed", "archiving")) {
                            $shouldDelete = $true
                        }
                    } catch {
                        # 如果无法解析状态文件，根据目录修改时间判断
                        if ($dir.LastWriteTime -lt $cutoffDate) {
                            $shouldDelete = $true
                        }
                    }
                } else {
                    # 如果没有状态文件，根据目录修改时间判断
                    if ($dir.LastWriteTime -lt $cutoffDate) {
                        $shouldDelete = $true
                    }
                }

                if ($shouldDelete) {
                    try {
                        Remove-Item -Path $dir.FullName -Recurse -Force -ErrorAction Stop
                        $deletedCount++
                        Write-Verbose "删除旧任务目录: $($dir.Name)"
                    } catch {
                        Write-Warning "无法删除任务目录 $($dir.Name): $_"
                        $skippedCount++
                    }
                }
            }

            return @{
                Success = $true
                Message = "任务清理完成"
                DeletedCount = $deletedCount
                SkippedCount = $skippedCount
                CutoffDate = $cutoffDate.ToString("yyyy-MM-dd")
            }

        } catch {
            Write-Error "清理任务失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
                DeletedCount = 0
                SkippedCount = 0
            }
        }
    }

    [void] Dispose() {
        # 清理资源
        $this.StopTaskMonitor()

        if ($this.TaskProcess -and -not $this.TaskProcess.HasExited) {
            try {
                $this.TaskProcess.Kill()
            } catch {
                Write-Verbose "停止任务进程失败: $_"
            }
        }

        $this.TaskProcess = $null
        $this.IsTaskRunning = $false
    }
}

# 全局任务管理器实例
$global:TaskManagerInstance = $null

function Get-AIITaskManager {
<#
.SYNOPSIS
获取或创建任务管理器实例

.DESCRIPTION
返回全局任务管理器实例，如果不存在则创建。

.EXAMPLE
$taskManager = Get-AIITaskManager

.OUTPUTS
[TaskManager] 任务管理器实例
#>
    [CmdletBinding()]
    [OutputType([TaskManager])]
    param()

    if (-not $global:TaskManagerInstance) {
        $root = $global:AIIWorkflowRoot
        if (-not $root) {
            throw "AII工作流根目录未设置，请先调用 Initialize-AIIWorkflow"
        }

        $global:TaskManagerInstance = [TaskManager]::new($root)
        Write-Verbose "创建新的任务管理器实例"
    }

    return $global:TaskManagerInstance
}

function New-AIITask {
<#
.SYNOPSIS
创建新的AII工作流任务

.DESCRIPTION
创建新的工作流任务并返回任务信息。

.PARAMETER Description
任务描述

.PARAMETER Template
任务模板名称

.PARAMETER Priority
任务优先级 (Low, Normal, High)

.EXAMPLE
New-AIITask -Description "帮我写一个Python脚本"

.EXAMPLE
New-AIITask "分析销售数据" -Template "data_analysis" -Priority High

.OUTPUTS
[hashtable] 任务创建结果
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory=$true, Position=0)]
        [string]$Description,

        [Parameter()]
        [ValidateSet("general", "data_analysis", "code_generation", "documentation", "debugging")]
        [string]$Template = "general",

        [Parameter()]
        [ValidateSet("Low", "Normal", "High")]
        [string]$Priority = "Normal"
    )

    begin {
        Write-Verbose "创建新的AII工作流任务..."
    }

    process {
        try {
            # 获取任务管理器
            $taskManager = Get-AIITaskManager -ErrorAction Stop

            # 添加模板信息到描述
            $enhancedDescription = @"
$Description

模板: $Template
优先级: $Priority
创建方式: PowerShell模块
"@

            # 创建任务
            $result = $taskManager.CreateTask($enhancedDescription)

            if ($result.Success) {
                # 更新配置中的最后使用模板
                $global:AIIConfig.LastUsedTemplate = $Template
                Save-AIIConfig

                # 显示任务信息
                $taskInfo = $taskManager.GetTaskInfo($result.TaskId)

                Write-Host "✅ 任务创建成功" -ForegroundColor Green
                Write-Host "   任务ID: $($result.TaskId)" -ForegroundColor White
                Write-Host "   状态: $($taskInfo.State.Status)" -ForegroundColor White
                Write-Host "   创建时间: $($taskInfo.State.CreatedAt)" -ForegroundColor White
                Write-Host "   任务目录: $($result.TaskDir)" -ForegroundColor White

                return $result
            } else {
                Write-Error "任务创建失败: $($result.Error)"
                return $result
            }

        } catch {
            Write-Error "创建任务失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "任务创建过程完成"
    }
}

function Start-AIITask {
<#
.SYNOPSIS
启动AII工作流任务

.DESCRIPTION
启动指定的任务或当前任务。

.PARAMETER TaskId
要启动的任务ID，如果未指定则启动当前任务

.PARAMETER Wait
等待任务完成

.EXAMPLE
Start-AIITask -TaskId "TASK-20240415-123456"

.EXAMPLE
Start-AIITask -Wait

.OUTPUTS
[hashtable] 任务启动结果
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter()]
        [string]$TaskId,

        [Parameter()]
        [switch]$Wait
    )

    begin {
        Write-Verbose "启动AII工作流任务..."
    }

    process {
        try {
            # 获取任务管理器
            $taskManager = Get-AIITaskManager -ErrorAction Stop

            # 确定任务ID
            if (-not $TaskId) {
                $stateManager = Get-AIIStateManager
                if (-not $stateManager.CurrentState.CurrentTask) {
                    throw "没有当前任务，请指定TaskId或先创建任务"
                }
                $TaskId = $stateManager.CurrentState.CurrentTask.TaskId
                Write-Verbose "使用当前任务: $TaskId"
            }

            # 启动任务
            $result = $taskManager.StartTask($TaskId)

            if ($result.Success) {
                Write-Host "🚀 任务启动成功" -ForegroundColor Green
                Write-Host "   任务ID: $($result.TaskId)" -ForegroundColor White
                Write-Host "   进程ID: $($result.ProcessId)" -ForegroundColor White
                Write-Host "   状态: $($result.Status)" -ForegroundColor White

                # 如果需要等待
                if ($Wait) {
                    Write-Host "⏳ 等待任务完成..." -ForegroundColor Yellow
                    while ($taskManager.IsTaskRunning -and $taskManager.TaskProcess -and -not $taskManager.TaskProcess.HasExited) {
                        Start-Sleep -Seconds 1
                        Write-Progress -Activity "任务执行中" -Status "请稍候..." -PercentComplete -1
                    }
                    Write-Host "✅ 任务完成" -ForegroundColor Green
                }

                return $result
            } else {
                Write-Error "任务启动失败: $($result.Error)"
                return $result
            }

        } catch {
            Write-Error "启动任务失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "任务启动过程完成"
    }
}

function Stop-AIITask {
<#
.SYNOPSIS
停止当前运行的AII工作流任务

.DESCRIPTION
停止当前正在运行的任务。

.EXAMPLE
Stop-AIITask

.OUTPUTS
[hashtable] 任务停止结果
#>
    [CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
    [OutputType([hashtable])]
    param()

    begin {
        Write-Verbose "停止AII工作流任务..."
    }

    process {
        try {
            if ($PSCmdlet.ShouldProcess("当前任务", "停止")) {
                $taskManager = Get-AIITaskManager -ErrorAction Stop
                $result = $taskManager.StopTask()

                if ($result.Success) {
                    Write-Host "🛑 任务已停止" -ForegroundColor Yellow
                    return $result
                } else {
                    Write-Error "停止任务失败: $($result.Error)"
                    return $result
                }
            }

        } catch {
            Write-Error "停止任务失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "任务停止过程完成"
    }
}

function Get-AIITaskInfo {
<#
.SYNOPSIS
获取AII工作流任务信息

.DESCRIPTION
获取指定任务的详细信息。

.PARAMETER TaskId
任务ID，如果未指定则获取当前任务信息

.EXAMPLE
Get-AIITaskInfo

.EXAMPLE
Get-AIITaskInfo -TaskId "TASK-20240415-123456"

.OUTPUTS
[hashtable] 任务信息
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter()]
        [string]$TaskId
    )

    begin {
        Write-Verbose "获取AII工作流任务信息..."
    }

    process {
        try {
            # 获取任务管理器
            $taskManager = Get-AIITaskManager -ErrorAction Stop

            # 确定任务ID
            if (-not $TaskId) {
                $stateManager = Get-AIIStateManager
                if (-not $stateManager.CurrentState.CurrentTask) {
                    throw "没有当前任务，请指定TaskId"
                }
                $TaskId = $stateManager.CurrentState.CurrentTask.TaskId
                Write-Verbose "使用当前任务: $TaskId"
            }

            # 获取任务信息
            $result = $taskManager.GetTaskInfo($TaskId)

            if ($result.Success) {
                return $result
            } else {
                Write-Error "获取任务信息失败: $($result.Error)"
                return $result
            }

        } catch {
            Write-Error "获取任务信息失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "任务信息获取完成"
    }
}

function Get-AIITaskList {
<#
.SYNOPSIS
获取AII工作流任务列表

.DESCRIPTION
获取所有任务的列表。

.PARAMETER Limit
限制返回的任务数量

.PARAMETER Status
按状态筛选任务

.EXAMPLE
Get-AIITaskList

.EXAMPLE
Get-AIITaskList -Limit 5 -Status "running"

.OUTPUTS
[array] 任务列表
#>
    [CmdletBinding()]
    [OutputType([array])]
    param(
        [Parameter()]
        [int]$Limit = 10,

        [Parameter()]
        [ValidateSet("all", "running", "completed", "failed", "pending")]
        [string]$Status = "all"
    )

    begin {
        Write-Verbose "获取AII工作流任务列表..."
    }

    process {
        try {
            # 获取任务管理器
            $taskManager = Get-AIITaskManager -ErrorAction Stop

            # 获取所有任务
            $allTasks = $taskManager.ListTasks($Limit * 2)  # 获取更多以便筛选

            # 按状态筛选
            if ($Status -ne "all") {
                $allTasks = $allTasks | Where-Object { $_.Status -eq $Status }
            }

            # 限制数量
            $tasks = $allTasks | Select-Object -First $Limit

            return $tasks

        } catch {
            Write-Error "获取任务列表失败: $_"
            return @()
        }
    }

    end {
        Write-Verbose "任务列表获取完成"
    }
}

function Clear-AIITasks {
<#
.SYNOPSIS
清理旧的AII工作流任务

.DESCRIPTION
清理指定天数前的已完成任务。

.PARAMETER DaysOld
清理多少天前的任务，默认30天

.EXAMPLE
Clear-AIITasks

.EXAMPLE
Clear-AIITasks -DaysOld 7

.OUTPUTS
[hashtable] 清理结果
#>
    [CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
    [OutputType([hashtable])]
    param(
        [Parameter()]
        [int]$DaysOld = 30
    )

    begin {
        Write-Verbose "清理AII工作流任务..."
    }

    process {
        try {
            if ($PSCmdlet.ShouldProcess("$DaysOld 天前的任务", "清理")) {
                $taskManager = Get-AIITaskManager -ErrorAction Stop
                $result = $taskManager.CleanupTasks($DaysOld)

                if ($result.Success) {
                    Write-Host "🧹 任务清理完成" -ForegroundColor Green
                    Write-Host "   清理了 $($result.DeletedCount) 个旧任务" -ForegroundColor White
                    Write-Host "   跳过了 $($result.SkippedCount) 个任务" -ForegroundColor White
                    Write-Host "   清理截止日期: $($result.CutoffDate)" -ForegroundColor White
                } else {
                    Write-Error "任务清理失败: $($result.Error)"
                }

                return $result
            }

        } catch {
            Write-Error "任务清理失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
                DeletedCount = 0
                SkippedCount = 0
            }
        }
    }

    end {
        Write-Verbose "任务清理过程完成"
    }
}

# 导出模块函数
Export-ModuleMember -Function @(
    'Get-AIITaskManager',
    'New-AIITask',
    'Start-AIITask',
    'Stop-AIITask',
    'Get-AIITaskInfo',
    'Get-AIITaskList',
    'Clear-AIITasks'
)

# 模块初始化
if ($global:AIIWorkflowRoot) {
    try {
        # 确保任务管理器已初始化
        Get-AIITaskManager | Out-Null
    } catch {
        Write-Warning "任务管理器初始化失败: $_"
    }
}

# 注册清理处理程序
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    if ($global:TaskManagerInstance) {
        $global:TaskManagerInstance.Dispose()
        $global:TaskManagerInstance = $null
    }
}