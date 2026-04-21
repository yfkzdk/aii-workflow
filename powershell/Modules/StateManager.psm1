# AII Workflow PowerShell Module - State Manager
# 状态管理模块：负责状态管理、恢复和窗口间同步

using namespace System.Management.Automation
using namespace System.IO
using namespace System.Threading

# 模块私有变量
$script:StateLockFile = $null
$script:StateWatchers = @{}
$script:StateSyncInterval = 2000  # 2秒同步间隔

class StateManager {
    # 状态管理器类
    [string]$RootPath
    [hashtable]$CurrentState
    [string]$SessionId
    [string]$WindowId
    [System.Threading.Timer]$SyncTimer
    [bool]$IsSyncing = $false

    StateManager([string]$rootPath) {
        $this.RootPath = $rootPath
        $this.SessionId = [Guid]::NewGuid().ToString()
        $this.WindowId = [Guid]::NewGuid().ToString()
        $this.CurrentState = @{}
        $this.InitializeState()
    }

    [void] InitializeState() {
        # 初始化状态
        $this.LoadState()
        $this.RegisterWindow()
        $this.StartSyncTimer()
    }

    [void] LoadState() {
        # 加载状态文件
        $stateFile = Join-Path $this.RootPath "cache\session_state.json"
        $taskHistoryFile = Join-Path $this.RootPath "config\task_history.json"

        try {
            if (Test-Path $stateFile) {
                $stateJson = Get-Content $stateFile -Raw -ErrorAction Stop
                $this.CurrentState.Session = $stateJson | ConvertFrom-Json -AsHashtable
            } else {
                $this.CurrentState.Session = @{
                    SessionId = $this.SessionId
                    StartedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                    WindowCount = 0
                    LastWindowId = $null
                    ActiveWindows = @()
                }
            }

            if (Test-Path $taskHistoryFile) {
                $historyJson = Get-Content $taskHistoryFile -Raw -ErrorAction Stop
                $this.CurrentState.History = $historyJson | ConvertFrom-Json -AsHashtable
            } else {
                $this.CurrentState.History = @{
                    Tasks = @()
                    LastTaskId = $null
                    LastActivity = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                }
            }

            # 检测当前任务
            $this.CurrentState.CurrentTask = $this.DetectCurrentTask()

            Write-Verbose "状态加载完成"
        } catch {
            Write-Warning "状态加载失败: $_"
            $this.CurrentState = @{
                Session = @{
                    SessionId = $this.SessionId
                    StartedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                    WindowCount = 0
                    LastWindowId = $null
                    ActiveWindows = @()
                }
                History = @{
                    Tasks = @()
                    LastTaskId = $null
                    LastActivity = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                }
                CurrentTask = $null
            }
        }
    }

    [hashtable] DetectCurrentTask() {
        # 检测当前运行的任务
        $tasksDir = Join-Path $this.RootPath "tasks"
        if (-not (Test-Path $tasksDir)) {
            return $null
        }

        # 查找最新的状态文件
        $stateFiles = Get-ChildItem -Path $tasksDir -Filter "*.json" -Recurse -ErrorAction SilentlyContinue |
                     Sort-Object LastWriteTime -Descending

        foreach ($file in $stateFiles) {
            try {
                $stateJson = Get-Content $file.FullName -Raw -ErrorAction Stop
                $state = $stateJson | ConvertFrom-Json -AsHashtable

                if ($state.Status -and $state.Status -notin @("archiving", "completed", "failed")) {
                    $taskDir = Split-Path $file.FullName -Parent
                    return @{
                        TaskId = $state.TaskId
                        Status = $state.Status
                        CreatedAt = $state.CreatedAt
                        UpdatedAt = $state.UpdatedAt
                        StateFile = $file.FullName
                        TaskDir = $taskDir
                        NextAgent = $state.NextAgent
                        Checkpoint = $state.Checkpoint
                    }
                }
            } catch {
                Write-Verbose "无法解析状态文件: $($file.FullName)"
            }
        }

        return $null
    }

    [void] RegisterWindow() {
        # 注册当前窗口
        if (-not $this.CurrentState.Session.ActiveWindows) {
            $this.CurrentState.Session.ActiveWindows = @()
        }

        $windowInfo = @{
            WindowId = $this.WindowId
            SessionId = $this.SessionId
            RegisteredAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            LastHeartbeat = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            ProcessId = $PID
            CommandLine = [Environment]::CommandLine
        }

        # 添加或更新窗口信息
        $existingIndex = $this.CurrentState.Session.ActiveWindows |
                        ForEach-Object { $_.WindowId } |
                        IndexOf $this.WindowId

        if ($existingIndex -ge 0) {
            $this.CurrentState.Session.ActiveWindows[$existingIndex] = $windowInfo
        } else {
            $this.CurrentState.Session.ActiveWindows += $windowInfo
        }

        $this.CurrentState.Session.WindowCount = $this.CurrentState.Session.ActiveWindows.Count
        $this.CurrentState.Session.LastWindowId = $this.WindowId

        $this.SaveState()
        Write-Verbose "窗口注册完成: $($this.WindowId)"
    }

    [void] UnregisterWindow() {
        # 注销当前窗口
        if ($this.CurrentState.Session.ActiveWindows) {
            $this.CurrentState.Session.ActiveWindows = @(
                $this.CurrentState.Session.ActiveWindows |
                Where-Object { $_.WindowId -ne $this.WindowId }
            )
            $this.CurrentState.Session.WindowCount = $this.CurrentState.Session.ActiveWindows.Count
            $this.SaveState()
            Write-Verbose "窗口注销完成: $($this.WindowId)"
        }
    }

    [void] StartSyncTimer() {
        # 启动状态同步定时器
        $timerCallback = {
            param($state)
            try {
                $stateManager = [StateManager]$state
                $stateManager.SyncState()
            } catch {
                Write-Warning "状态同步失败: $_"
            }
        }

        $this.SyncTimer = [System.Threading.Timer]::new(
            $timerCallback,
            $this,
            $script:StateSyncInterval,
            $script:StateSyncInterval
        )

        Write-Verbose "状态同步定时器已启动"
    }

    [void] StopSyncTimer() {
        # 停止状态同步定时器
        if ($this.SyncTimer) {
            $this.SyncTimer.Dispose()
            $this.SyncTimer = $null
            Write-Verbose "状态同步定时器已停止"
        }
    }

    [void] SyncState() {
        # 同步状态（避免重复同步）
        if ($this.IsSyncing) {
            return
        }

        $this.IsSyncing = $true

        try {
            # 1. 更新心跳
            $this.UpdateHeartbeat()

            # 2. 检查其他窗口状态
            $this.CheckOtherWindows()

            # 3. 重新加载状态（获取其他窗口的更新）
            $this.ReloadState()

            # 4. 广播状态变更
            $this.BroadcastStateChanges()

            Write-Verbose "状态同步完成"
        } catch {
            Write-Warning "状态同步过程中出错: $_"
        } finally {
            $this.IsSyncing = $false
        }
    }

    [void] UpdateHeartbeat() {
        # 更新窗口心跳
        if ($this.CurrentState.Session.ActiveWindows) {
            foreach ($window in $this.CurrentState.Session.ActiveWindows) {
                if ($window.WindowId -eq $this.WindowId) {
                    $window.LastHeartbeat = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                    break
                }
            }
            $this.SaveState()
        }
    }

    [void] CheckOtherWindows() {
        # 检查其他窗口的活动状态
        $timeoutMinutes = 5
        $timeoutTime = (Get-Date).AddMinutes(-$timeoutMinutes)

        if ($this.CurrentState.Session.ActiveWindows) {
            $activeWindows = @()
            foreach ($window in $this.CurrentState.Session.ActiveWindows) {
                $lastHeartbeat = [DateTime]::Parse($window.LastHeartbeat)
                if ($lastHeartbeat -gt $timeoutTime -or $window.WindowId -eq $this.WindowId) {
                    $activeWindows += $window
                } else {
                    Write-Verbose "窗口超时移除: $($window.WindowId)"
                }
            }

            if ($activeWindows.Count -ne $this.CurrentState.Session.ActiveWindows.Count) {
                $this.CurrentState.Session.ActiveWindows = $activeWindows
                $this.CurrentState.Session.WindowCount = $activeWindows.Count
                $this.SaveState()
            }
        }
    }

    [void] ReloadState() {
        # 重新加载状态（检查其他窗口的更新）
        $stateFile = Join-Path $this.RootPath "cache\session_state.json"

        if (Test-Path $stateFile) {
            try {
                $fileLastWrite = (Get-Item $stateFile).LastWriteTime
                $currentLastWrite = $null

                if ($this.CurrentState.Session._LastWriteTime) {
                    $currentLastWrite = [DateTime]::Parse($this.CurrentState.Session._LastWriteTime)
                }

                # 如果文件有更新，重新加载
                if (-not $currentLastWrite -or $fileLastWrite -gt $currentLastWrite) {
                    $stateJson = Get-Content $stateFile -Raw -ErrorAction Stop
                    $newSessionState = $stateJson | ConvertFrom-Json -AsHashtable

                    # 保留当前窗口信息
                    $currentWindow = $this.CurrentState.Session.ActiveWindows |
                                    Where-Object { $_.WindowId -eq $this.WindowId } |
                                    Select-Object -First 1

                    if ($currentWindow) {
                        # 更新新状态中的当前窗口信息
                        $windowIndex = $newSessionState.ActiveWindows |
                                      ForEach-Object { $_.WindowId } |
                                      IndexOf $this.WindowId

                        if ($windowIndex -ge 0) {
                            $newSessionState.ActiveWindows[$windowIndex] = $currentWindow
                        } else {
                            $newSessionState.ActiveWindows += $currentWindow
                        }
                        $newSessionState.WindowCount = $newSessionState.ActiveWindows.Count
                        $newSessionState.LastWindowId = $this.WindowId
                    }

                    $this.CurrentState.Session = $newSessionState
                    $this.CurrentState.Session._LastWriteTime = $fileLastWrite.ToString("o")

                    Write-Verbose "状态已从文件重新加载"
                }
            } catch {
                Write-Warning "重新加载状态失败: $_"
            }
        }

        # 重新检测当前任务
        $newTask = $this.DetectCurrentTask()
        if ($newTask -and (
            -not $this.CurrentState.CurrentTask -or
            $newTask.TaskId -ne $this.CurrentState.CurrentTask.TaskId -or
            $newTask.UpdatedAt -ne $this.CurrentState.CurrentTask.UpdatedAt
        )) {
            $this.CurrentState.CurrentTask = $newTask
            Write-Verbose "当前任务已更新: $($newTask.TaskId)"
        }
    }

    [void] BroadcastStateChanges() {
        # 广播状态变更（文件锁机制）
        $lockFile = Join-Path $this.RootPath "cache\.state.lock"

        try {
            # 尝试获取锁
            $lockAcquired = $false
            $maxRetries = 3
            $retryCount = 0

            while (-not $lockAcquired -and $retryCount -lt $maxRetries) {
                try {
                    $stream = [System.IO.File]::Open($lockFile, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
                    $stream.Close()
                    $lockAcquired = $true
                } catch {
                    $retryCount++
                    if ($retryCount -lt $maxRetries) {
                        Start-Sleep -Milliseconds 100
                    }
                }
            }

            if ($lockAcquired) {
                # 保存状态（广播更新）
                $this.SaveState()

                # 释放锁
                Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Warning "状态广播失败: $_"
        }
    }

    [void] SaveState() {
        # 保存状态到文件
        $stateFile = Join-Path $this.RootPath "cache\session_state.json"
        $stateDir = Split-Path $stateFile -Parent

        if (-not (Test-Path $stateDir)) {
            New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
        }

        try {
            # 添加时间戳
            $this.CurrentState.Session.UpdatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            $this.CurrentState.Session._LastWriteTime = (Get-Date).ToString("o")

            # 转换为JSON并保存
            $stateJson = $this.CurrentState.Session | ConvertTo-Json -Depth 10
            Set-Content -Path $stateFile -Value $stateJson -Encoding UTF8 -Force

            # 保存任务历史
            $this.SaveTaskHistory()

            Write-Verbose "状态已保存: $stateFile"
        } catch {
            Write-Error "保存状态失败: $_"
        }
    }

    [void] SaveTaskHistory() {
        # 保存任务历史
        $historyFile = Join-Path $this.RootPath "config\task_history.json"
        $historyDir = Split-Path $historyFile -Parent

        if (-not (Test-Path $historyDir)) {
            New-Item -ItemType Directory -Path $historyDir -Force | Out-Null
        }

        try {
            $historyJson = $this.CurrentState.History | ConvertTo-Json -Depth 10
            Set-Content -Path $historyFile -Value $historyJson -Encoding UTF8 -Force
            Write-Verbose "任务历史已保存: $historyFile"
        } catch {
            Write-Warning "保存任务历史失败: $_"
        }
    }

    [void] AddTaskToHistory([string]$taskId, [string]$description, [string]$status) {
        # 添加任务到历史记录
        $taskEntry = @{
            TaskId = $taskId
            Description = $description
            Status = $status
            StartedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            CompletedAt = if ($status -eq "completed") { (Get-Date).ToString("yyyy-MM-dd HH:mm:ss") } else { $null }
            SessionId = $this.SessionId
            WindowId = $this.WindowId
        }

        if (-not $this.CurrentState.History.Tasks) {
            $this.CurrentState.History.Tasks = @()
        }

        # 添加到历史记录
        $this.CurrentState.History.Tasks = @($taskEntry) + $this.CurrentState.History.Tasks

        # 限制历史记录大小
        $maxHistorySize = 100
        if ($this.CurrentState.History.Tasks.Count -gt $maxHistorySize) {
            $this.CurrentState.History.Tasks = $this.CurrentState.History.Tasks[0..($maxHistorySize-1)]
        }

        $this.CurrentState.History.LastTaskId = $taskId
        $this.CurrentState.History.LastActivity = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

        $this.SaveTaskHistory()
        Write-Verbose "任务已添加到历史: $taskId"
    }

    [hashtable] GetTaskHistory([int]$limit = 10) {
        # 获取任务历史
        if (-not $this.CurrentState.History.Tasks) {
            return @{ Tasks = @() }
        }

        $history = $this.CurrentState.History.Tasks | Select-Object -First $limit
        return @{
            Tasks = $history
            TotalCount = $this.CurrentState.History.Tasks.Count
            LastActivity = $this.CurrentState.History.LastActivity
        }
    }

    [hashtable] GetWindowInfo() {
        # 获取当前窗口信息
        return @{
            WindowId = $this.WindowId
            SessionId = $this.SessionId
            ProcessId = $PID
            CommandLine = [Environment]::CommandLine
            CurrentTask = $this.CurrentState.CurrentTask
            ActiveWindows = $this.CurrentState.Session.ActiveWindows.Count
        }
    }

    [array] GetActiveWindows() {
        # 获取活动窗口列表
        return @($this.CurrentState.Session.ActiveWindows)
    }

    [void] CleanupStaleWindows() {
        # 清理过期的窗口
        $timeoutMinutes = 10
        $timeoutTime = (Get-Date).AddMinutes(-$timeoutMinutes)

        if ($this.CurrentState.Session.ActiveWindows) {
            $activeWindows = @()
            foreach ($window in $this.CurrentState.Session.ActiveWindows) {
                $lastHeartbeat = [DateTime]::Parse($window.LastHeartbeat)
                if ($lastHeartbeat -gt $timeoutTime) {
                    $activeWindows += $window
                } else {
                    Write-Verbose "清理过期窗口: $($window.WindowId)"
                }
            }

            if ($activeWindows.Count -ne $this.CurrentState.Session.ActiveWindows.Count) {
                $this.CurrentState.Session.ActiveWindows = $activeWindows
                $this.CurrentState.Session.WindowCount = $activeWindows.Count
                $this.SaveState()
            }
        }
    }

    [void] Dispose() {
        # 清理资源
        $this.StopSyncTimer()
        $this.UnregisterWindow()
        $this.CleanupStaleWindows()
    }
}

# 全局状态管理器实例
$global:StateManagerInstance = $null

function Get-AIIStateManager {
<#
.SYNOPSIS
获取或创建状态管理器实例

.DESCRIPTION
返回全局状态管理器实例，如果不存在则创建。

.EXAMPLE
$stateManager = Get-AIIStateManager

.OUTPUTS
[StateManager] 状态管理器实例
#>
    [CmdletBinding()]
    [OutputType([StateManager])]
    param()

    if (-not $global:StateManagerInstance) {
        $root = $global:AIIWorkflowRoot
        if (-not $root) {
            throw "AII工作流根目录未设置，请先调用 Initialize-AIIWorkflow"
        }

        $global:StateManagerInstance = [StateManager]::new($root)
        Write-Verbose "创建新的状态管理器实例"
    }

    return $global:StateManagerInstance
}

function Get-AIIStatus {
<#
.SYNOPSIS
获取AII工作流系统状态

.DESCRIPTION
显示当前系统状态，包括任务状态、窗口信息等。

.EXAMPLE
Get-AIIStatus
显示完整状态信息

.EXAMPLE
Get-AIIStatus -Brief
显示简要状态信息

.OUTPUTS
[pscustomobject] 状态信息
#>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param(
        [Parameter()]
        [switch]$Brief
    )

    begin {
        Write-Verbose "获取AII工作流状态..."
    }

    process {
        try {
            $stateManager = Get-AIIStateManager -ErrorAction Stop

            if ($Brief) {
                $status = [pscustomobject]@{
                    CurrentTask = if ($stateManager.CurrentState.CurrentTask) {
                        $stateManager.CurrentState.CurrentTask.TaskId
                    } else {
                        $null
                    }
                    TaskStatus = if ($stateManager.CurrentState.CurrentTask) {
                        $stateManager.CurrentState.CurrentTask.Status
                    } else {
                        "空闲"
                    }
                    ActiveWindows = $stateManager.CurrentState.Session.ActiveWindows.Count
                    LastActivity = $stateManager.CurrentState.History.LastActivity
                }
            } else {
                $status = [pscustomobject]@{
                    SessionId = $stateManager.CurrentState.Session.SessionId
                    WindowId = $stateManager.WindowId
                    CurrentTask = $stateManager.CurrentState.CurrentTask
                    ActiveWindows = $stateManager.CurrentState.Session.ActiveWindows
                    WindowCount = $stateManager.CurrentState.Session.WindowCount
                    History = @{
                        TotalTasks = $stateManager.CurrentState.History.Tasks.Count
                        LastTaskId = $stateManager.CurrentState.History.LastTaskId
                        LastActivity = $stateManager.CurrentState.History.LastActivity
                    }
                    SystemInfo = @{
                        WorkflowRoot = $stateManager.RootPath
                        StateFile = Join-Path $stateManager.RootPath "cache\session_state.json"
                        HistoryFile = Join-Path $stateManager.RootPath "config\task_history.json"
                        LastSync = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                    }
                }
            }

            return $status

        } catch {
            Write-Error "获取状态失败: $_"
            return [pscustomobject]@{
                Status = "错误"
                Error = $_.Exception.Message
                WorkflowRoot = $global:AIIWorkflowRoot
            }
        }
    }

    end {
        Write-Verbose "状态获取完成"
    }
}

function Resume-AIITask {
<#
.SYNOPSIS
恢复最近的任务

.DESCRIPTION
恢复最近的任务或指定任务ID的任务。

.EXAMPLE
Resume-AIITask
恢复最近的任务

.EXAMPLE
Resume-AIITask -TaskId "TASK-20240415-123456"
恢复指定任务ID的任务

.OUTPUTS
[bool] 是否成功恢复
#>
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter()]
        [string]$TaskId,

        [Parameter()]
        [switch]$Force
    )

    begin {
        Write-Verbose "尝试恢复AII工作流任务..."
    }

    process {
        try {
            $stateManager = Get-AIIStateManager -ErrorAction Stop

            # 确定要恢复的任务ID
            if (-not $TaskId) {
                if ($stateManager.CurrentState.CurrentTask) {
                    $TaskId = $stateManager.CurrentState.CurrentTask.TaskId
                    Write-Verbose "使用当前任务: $TaskId"
                } elseif ($stateManager.CurrentState.History.LastTaskId) {
                    $TaskId = $stateManager.CurrentState.History.LastTaskId
                    Write-Verbose "使用最后任务: $TaskId"
                } else {
                    Write-Warning "没有找到可恢复的任务"
                    return $false
                }
            }

            # 查找任务目录
            $taskDir = Find-TaskDirectory -TaskId $TaskId
            if (-not $taskDir) {
                Write-Warning "未找到任务目录: $TaskId"
                return $false
            }

            # 检查任务状态
            $stateFile = Join-Path $taskDir "state.json"
            if (-not (Test-Path $stateFile)) {
                Write-Warning "任务状态文件不存在: $stateFile"
                return $false
            }

            $stateJson = Get-Content $stateFile -Raw -ErrorAction Stop
            $state = $stateJson | ConvertFrom-Json -AsHashtable

            # 检查任务是否可恢复
            if ($state.Status -in @("completed", "failed", "archiving")) {
                if (-not $Force) {
                    Write-Warning "任务状态为 '$($state.Status)'，无法恢复。使用 -Force 参数强制恢复。"
                    return $false
                }
                Write-Verbose "强制恢复已完成的任務: $TaskId"
            }

            # 更新状态管理器
            $stateManager.CurrentState.CurrentTask = @{
                TaskId = $TaskId
                Status = $state.Status
                CreatedAt = $state.CreatedAt
                UpdatedAt = $state.UpdatedAt
                StateFile = $stateFile
                TaskDir = $taskDir
                NextAgent = $state.NextAgent
                Checkpoint = $state.Checkpoint
            }

            $stateManager.SaveState()

            # 启动恢复流程
            $result = Start-TaskRecovery -TaskId $TaskId -TaskDir $taskDir -State $state
            return $result

        } catch {
            Write-Error "恢复任务失败: $_"
            return $false
        }
    }

    end {
        Write-Verbose "任务恢复操作完成"
    }
}

function Find-TaskDirectory {
<#
.SYNOPSIS
查找任务目录

.DESCRIPTION
根据任务ID查找对应的任务目录。

.PARAMETER TaskId
任务ID

.OUTPUTS
[string] 任务目录路径
#>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory=$true)]
        [string]$TaskId
    )

    $root = $global:AIIWorkflowRoot
    $tasksDir = Join-Path $root "tasks"

    if (-not (Test-Path $tasksDir)) {
        return $null
    }

    # 查找匹配的任务目录
    $taskDirs = Get-ChildItem -Path $tasksDir -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -like "*$TaskId*" }

    if ($taskDirs) {
        return $taskDirs[0].FullName
    }

    return $null
}

function Start-TaskRecovery {
<#
.SYNOPSIS
启动任务恢复流程

.DESCRIPTION
启动任务恢复流程，包括状态更新和任务继续。

.PARAMETER TaskId
任务ID

.PARAMETER TaskDir
任务目录

.PARAMETER State
任务状态

.OUTPUTS
[bool] 是否成功
#>
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory=$true)]
        [string]$TaskId,

        [Parameter(Mandatory=$true)]
        [string]$TaskDir,

        [Parameter(Mandatory=$true)]
        [hashtable]$State
    )

    try {
        $root = $global:AIIWorkflowRoot

        Write-Host "🔄 恢复任务: $TaskId" -ForegroundColor Yellow
        Write-Host "   状态: $($State.Status)" -ForegroundColor White
        Write-Host "   下一步Agent: $($State.NextAgent)" -ForegroundColor White

        # 构建恢复命令
        $recoveryCommand = @{
            Action = "recover"
            TaskId = $TaskId
            TaskDir = $TaskDir
            NextAgent = $State.NextAgent
            Checkpoint = $State.Checkpoint
        }

        # 保存恢复信息到文件
        $recoveryFile = Join-Path $root "cache\recovery.json"
        $recoveryJson = $recoveryCommand | ConvertTo-Json -Depth 10
        Set-Content -Path $recoveryFile -Value $recoveryJson -Encoding UTF8

        # 启动恢复流程
        $scriptPath = Join-Path $root "ww_enhanced.py"
        $args = @("recover", $TaskId)

        $processInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processInfo.FileName = "python"
        $processInfo.Arguments = "`"$scriptPath`" $args"
        $processInfo.WorkingDirectory = $root
        $processInfo.UseShellExecute = $false
        $processInfo.RedirectStandardOutput = $true
        $processInfo.RedirectStandardError = $true
        $processInfo.CreateNoWindow = $true

        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $processInfo
        $process.Start() | Out-Null

        # 异步读取输出
        $outputJob = Start-Job -ScriptBlock {
            param($proc)
            $proc.StandardOutput.ReadToEnd()
        } -ArgumentList $process

        $errorJob = Start-Job -ScriptBlock {
            param($proc)
            $proc.StandardError.ReadToEnd()
        } -ArgumentList $process

        $process.WaitForExit()

        $output = Receive-Job $outputJob -Wait -AutoRemoveJob
        $errorOutput = Receive-Job $errorJob -Wait -AutoRemoveJob

        if ($process.ExitCode -eq 0) {
            Write-Host "✅ 任务恢复成功" -ForegroundColor Green
            Write-Verbose "输出: $output"
            return $true
        } else {
            Write-Host "❌ 任务恢复失败" -ForegroundColor Red
            Write-Error "错误: $errorOutput"
            return $false
        }

    } catch {
        Write-Error "恢复流程失败: $_"
        return $false
    }
}

function Clear-AIIState {
<#
.SYNOPSIS
清理AII工作流状态

.DESCRIPTION
清理状态文件，重置状态管理器。

.EXAMPLE
Clear-AIIState
清理所有状态

.EXAMPLE
Clear-AIIState -KeepHistory
保留历史记录，只清理会话状态
#>
    [CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
    param(
        [Parameter()]
        [switch]$KeepHistory
    )

    begin {
        Write-Verbose "清理AII工作流状态..."
    }

    process {
        try {
            $root = $global:AIIWorkflowRoot

            if ($PSCmdlet.ShouldProcess("AII工作流状态", "清理")) {
                # 清理状态管理器
                if ($global:StateManagerInstance) {
                    $global:StateManagerInstance.Dispose()
                    $global:StateManagerInstance = $null
                }

                # 清理状态文件
                $stateFiles = @(
                    Join-Path $root "cache\session_state.json"
                    Join-Path $root "cache\.state.lock"
                    Join-Path $root "cache\recovery.json"
                )

                foreach ($file in $stateFiles) {
                    if (Test-Path $file) {
                        Remove-Item $file -Force -ErrorAction SilentlyContinue
                        Write-Verbose "清理状态文件: $file"
                    }
                }

                # 清理任务历史（可选）
                if (-not $KeepHistory) {
                    $historyFile = Join-Path $root "config\task_history.json"
                    if (Test-Path $historyFile) {
                        Remove-Item $historyFile -Force -ErrorAction SilentlyContinue
                        Write-Verbose "清理历史文件: $historyFile"
                    }
                }

                # 重新初始化
                Initialize-AIIWorkflow -Force | Out-Null

                Write-Host "✅ AII工作流状态已清理" -ForegroundColor Green
                return $true
            }

        } catch {
            Write-Error "清理状态失败: $_"
            return $false
        }
    }

    end {
        Write-Verbose "状态清理完成"
    }
}

# 导出模块函数
Export-ModuleMember -Function @(
    'Get-AIIStateManager',
    'Get-AIIStatus',
    'Resume-AIITask',
    'Clear-AIIState'
)

# 模块初始化
if ($global:AIIWorkflowRoot) {
    try {
        # 确保状态管理器已初始化
        Get-AIIStateManager | Out-Null
    } catch {
        Write-Warning "状态管理器初始化失败: $_"
    }
}

# 注册清理处理程序
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    if ($global:StateManagerInstance) {
        $global:StateManagerInstance.Dispose()
        $global:StateManagerInstance = $null
    }
}