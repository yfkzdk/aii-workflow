# AII Workflow PowerShell Module - Reset Manager
# 重置管理模块：负责系统一键重置和清理功能

using namespace System.Management.Automation
using namespace System.IO

class ResetManager {
    # 重置管理器类
    [string]$RootPath
    [hashtable]$BackupInfo

    ResetManager([string]$rootPath) {
        $this.RootPath = $rootPath
        $this.BackupInfo = @{}
    }

    [hashtable] CreateBackup([string]$backupType = "manual") {
        # 创建系统备份
        try {
            $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
            $backupDir = Join-Path $this.RootPath "backups\$backupType-$timestamp"

            # 创建备份目录
            New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

            $backupItems = @{
                Config = @{
                    Source = Join-Path $this.RootPath "config"
                    Destination = Join-Path $backupDir "config"
                    Required = $true
                }
                Tasks = @{
                    Source = Join-Path $this.RootPath "tasks"
                    Destination = Join-Path $backupDir "tasks"
                    Required = $false
                }
                Cache = @{
                    Source = Join-Path $this.RootPath "cache"
                    Destination = Join-Path $backupDir "cache"
                    Required = $false
                }
                Logs = @{
                    Source = Join-Path $this.RootPath "logs"
                    Destination = Join-Path $backupDir "logs"
                    Required = $false
                }
                StateFiles = @{
                    Source = Join-Path $this.RootPath "AI_WORKFLOW_LOG.md"
                    Destination = Join-Path $backupDir "AI_WORKFLOW_LOG.md"
                    Required = $true
                }
            }

            $backupSummary = @{
                Items = @()
                TotalSize = 0
                SuccessCount = 0
                FailedCount = 0
            }

            foreach ($itemName in $backupItems.Keys) {
                $item = $backupItems[$itemName]

                if (-not (Test-Path $item.Source)) {
                    if ($item.Required) {
                        Write-Warning "必需备份项不存在: $itemName"
                        continue
                    } else {
                        Write-Verbose "可选备份项不存在，跳过: $itemName"
                        continue
                    }
                }

                try {
                    # 计算大小
                    $size = 0
                    if (Test-Path $item.Source -PathType Container) {
                        $size = (Get-ChildItem -Path $item.Source -Recurse -File | Measure-Object -Property Length -Sum).Sum
                    } else {
                        $size = (Get-Item $item.Source).Length
                    }

                    # 复制项目
                    if (Test-Path $item.Source -PathType Container) {
                        Copy-Item -Path $item.Source -Destination $item.Destination -Recurse -Force -ErrorAction Stop
                    } else {
                        Copy-Item -Path $item.Source -Destination $item.Destination -Force -ErrorAction Stop
                    }

                    $backupSummary.Items += @{
                        Name = $itemName
                        Source = $item.Source
                        Destination = $item.Destination
                        Size = $size
                        Status = "成功"
                    }
                    $backupSummary.TotalSize += $size
                    $backupSummary.SuccessCount++

                    Write-Verbose "备份成功: $itemName ($([math]::Round($size/1KB, 2)) KB)"

                } catch {
                    Write-Warning "备份失败 $itemName : $_"

                    $backupSummary.Items += @{
                        Name = $itemName
                        Source = $item.Source
                        Destination = $item.Destination
                        Size = $size
                        Status = "失败"
                        Error = $_.Exception.Message
                    }
                    $backupSummary.FailedCount++
                }
            }

            # 保存备份信息
            $backupInfoFile = Join-Path $backupDir "backup-info.json"
            $backupInfo = @{
                BackupType = $backupType
                Timestamp = $timestamp
                CreatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                Summary = $backupSummary
                RootPath = $this.RootPath
            }

            $backupInfoJson = $backupInfo | ConvertTo-Json -Depth 10
            Set-Content -Path $backupInfoFile -Value $backupInfoJson -Encoding UTF8

            $this.BackupInfo = $backupInfo

            Write-Verbose "备份创建完成: $backupDir"
            Write-Verbose "总计: $($backupSummary.SuccessCount) 项成功, $($backupSummary.FailedCount) 项失败"
            Write-Verbose "大小: $([math]::Round($backupSummary.TotalSize/1MB, 2)) MB"

            return @{
                Success = $true
                BackupDir = $backupDir
                BackupInfo = $backupInfo
                Summary = $backupSummary
            }

        } catch {
            Write-Error "创建备份失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [hashtable] ResetSystem([switch]$Force, [switch]$KeepConfig, [switch]$KeepTasks, [int]$DaysToKeep = 7) {
        # 重置系统
        try {
            if (-not $Force) {
                Write-Warning "重置操作将清理系统数据，使用 -Force 参数确认执行。"
                return @{
                    Success = $false
                    Message = "需要 -Force 参数确认重置操作"
                    RequiresForce = $true
                }
            }

            Write-Host "🔄 开始系统重置..." -ForegroundColor Yellow

            # 1. 创建备份
            Write-Host "  1. 创建系统备份..." -ForegroundColor Cyan
            $backupResult = $this.CreateBackup("reset-$(Get-Date -Format 'yyyyMMdd-HHmmss')")
            if (-not $backupResult.Success) {
                Write-Warning "备份创建失败，但继续执行重置..."
            } else {
                Write-Host "    ✅ 备份创建成功: $($backupResult.BackupDir)" -ForegroundColor Green
            }

            # 2. 停止所有相关进程
            Write-Host "  2. 停止相关进程..." -ForegroundColor Cyan
            $this.StopAllProcesses()

            # 3. 清理缓存和状态
            Write-Host "  3. 清理缓存和状态..." -ForegroundColor Cyan
            $cacheResult = $this.CleanCacheAndState($KeepConfig, $KeepTasks)

            # 4. 清理旧备份
            Write-Host "  4. 清理旧备份..." -ForegroundColor Cyan
            $cleanupResult = $this.CleanupOldBackups($DaysToKeep)

            # 5. 重新初始化系统
            Write-Host "  5. 重新初始化系统..." -ForegroundColor Cyan
            $initResult = $this.ReinitializeSystem()

            # 汇总结果
            $result = @{
                Success = $true
                Backup = $backupResult
                CacheCleanup = $cacheResult
                BackupCleanup = $cleanupResult
                Reinitialization = $initResult
                Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            }

            Write-Host "✅ 系统重置完成" -ForegroundColor Green
            Write-Host "   备份位置: $($backupResult.BackupDir)" -ForegroundColor White
            Write-Host "   清理缓存: $($cacheResult.DeletedFiles) 个文件" -ForegroundColor White
            Write-Host "   清理备份: $($cleanupResult.DeletedBackups) 个旧备份" -ForegroundColor White

            return $result

        } catch {
            Write-Error "系统重置失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [void] StopAllProcesses() {
        # 停止所有相关进程
        try {
            # 停止Python工作流进程
            $pythonProcesses = Get-Process | Where-Object {
                $_.ProcessName -eq "python" -and
                $_.CommandLine -like "*ww_enhanced.py*" -or
                $_.CommandLine -like "*ww.py*"
            }

            foreach ($process in $pythonProcesses) {
                try {
                    Write-Verbose "停止进程: $($process.ProcessName) (PID: $($process.Id))"
                    $process.Kill()
                    Start-Sleep -Milliseconds 100
                } catch {
                    Write-Warning "无法停止进程 $($process.Id): $_"
                }
            }

            # 停止PowerShell相关进程
            $psProcesses = Get-Process | Where-Object {
                $_.ProcessName -like "*powershell*" -and
                $_.CommandLine -like "*AIIWorkflow*"
            }

            foreach ($process in $psProcesses) {
                try {
                    if ($process.Id -ne $PID) {  # 不停止当前进程
                        Write-Verbose "停止进程: $($process.ProcessName) (PID: $($process.Id))"
                        $process.Kill()
                        Start-Sleep -Milliseconds 100
                    }
                } catch {
                    Write-Warning "无法停止进程 $($process.Id): $_"
                }
            }

        } catch {
            Write-Warning "停止进程时出错: $_"
        }
    }

    [hashtable] CleanCacheAndState([bool]$keepConfig, [bool]$keepTasks) {
        # 清理缓存和状态
        $result = @{
            DeletedFiles = 0
            DeletedDirs = 0
            KeptConfig = $keepConfig
            KeptTasks = $keepTasks
            Errors = @()
        }

        try {
            # 清理缓存目录
            $cacheDir = Join-Path $this.RootPath "cache"
            if (Test-Path $cacheDir) {
                Get-ChildItem -Path $cacheDir -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
                    try {
                        Remove-Item $_.FullName -Force -Recurse -ErrorAction Stop
                        $result.DeletedFiles++
                    } catch {
                        $result.Errors += "无法删除: $($_.FullName) - $_"
                    }
                }
                Write-Verbose "清理缓存目录: $cacheDir"
            }

            # 清理日志目录（保留error.log）
            $logsDir = Join-Path $this.RootPath "logs"
            if (Test-Path $logsDir) {
                Get-ChildItem -Path $logsDir -File -ErrorAction SilentlyContinue | Where-Object {
                    $_.Name -ne "error.log"
                } | ForEach-Object {
                    try {
                        Remove-Item $_.FullName -Force -ErrorAction Stop
                        $result.DeletedFiles++
                    } catch {
                        $result.Errors += "无法删除: $($_.FullName) - $_"
                    }
                }
                Write-Verbose "清理日志目录: $logsDir"
            }

            # 清理状态文件
            $stateFiles = @(
                Join-Path $this.RootPath "cache\session_state.json",
                Join-Path $this.RootPath "cache\.state.lock",
                Join-Path $this.RootPath "cache\recovery.json"
            )

            foreach ($file in $stateFiles) {
                if (Test-Path $file) {
                    try {
                        Remove-Item $file -Force -ErrorAction Stop
                        $result.DeletedFiles++
                    } catch {
                        $result.Errors += "无法删除: $file - $_"
                    }
                }
            }

            # 清理任务目录（可选）
            if (-not $keepTasks) {
                $tasksDir = Join-Path $this.RootPath "tasks"
                if (Test-Path $tasksDir) {
                    Get-ChildItem -Path $tasksDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                        try {
                            Remove-Item $_.FullName -Force -Recurse -ErrorAction Stop
                            $result.DeletedDirs++
                        } catch {
                            $result.Errors += "无法删除任务目录: $($_.FullName) - $_"
                        }
                    }
                    Write-Verbose "清理任务目录: $tasksDir"
                }
            }

            # 清理配置（可选）
            if (-not $keepConfig) {
                $configDir = Join-Path $this.RootPath "config"
                if (Test-Path $configDir) {
                    # 只删除非必要文件，保留user_prefs.json的备份
                    $configBackup = Join-Path $configDir "user_prefs.json.backup"
                    $configFile = Join-Path $configDir "user_prefs.json"

                    if (Test-Path $configFile) {
                        try {
                            Copy-Item $configFile $configBackup -Force -ErrorAction SilentlyContinue
                            Remove-Item $configFile -Force -ErrorAction Stop
                            $result.DeletedFiles++
                        } catch {
                            $result.Errors += "无法清理配置: $configFile - $_"
                        }
                    }

                    # 清理其他配置文件
                    Get-ChildItem -Path $configDir -File -ErrorAction SilentlyContinue | Where-Object {
                        $_.Name -ne "user_prefs.json.backup"
                    } | ForEach-Object {
                        try {
                            Remove-Item $_.FullName -Force -ErrorAction Stop
                            $result.DeletedFiles++
                        } catch {
                            $result.Errors += "无法删除配置文件: $($_.FullName) - $_"
                        }
                    }
                    Write-Verbose "清理配置目录: $configDir"
                }
            }

            # 清理工作流日志（保留最后100行）
            $logFile = Join-Path $this.RootPath "AI_WORKFLOW_LOG.md"
            if (Test-Path $logFile) {
                try {
                    $logContent = Get-Content $logFile -Tail 100 -ErrorAction SilentlyContinue
                    if ($logContent) {
                        Set-Content -Path $logFile -Value $logContent -Encoding UTF8 -Force
                        Write-Verbose "清理工作流日志，保留最后100行"
                    }
                } catch {
                    $result.Errors += "无法清理日志文件: $logFile - $_"
                }
            }

        } catch {
            $result.Errors += "清理缓存和状态时出错: $_"
        }

        return $result
    }

    [hashtable] CleanupOldBackups([int]$daysToKeep = 7) {
        # 清理旧备份
        $result = @{
            DeletedBackups = 0
            KeptBackups = 0
            Errors = @()
        }

        try {
            $backupsDir = Join-Path $this.RootPath "backups"
            if (-not (Test-Path $backupsDir)) {
                Write-Verbose "备份目录不存在: $backupsDir"
                return $result
            }

            $cutoffDate = (Get-Date).AddDays(-$daysToKeep)
            $backupDirs = Get-ChildItem -Path $backupsDir -Directory -ErrorAction SilentlyContinue

            foreach ($dir in $backupDirs) {
                try {
                    # 检查备份信息文件
                    $infoFile = Join-Path $dir.FullName "backup-info.json"
                    if (Test-Path $infoFile) {
                        $infoJson = Get-Content $infoFile -Raw -ErrorAction Stop
                        $info = $infoJson | ConvertFrom-Json -AsHashtable

                        if ($info.CreatedAt) {
                            $createdAt = [DateTime]::Parse($info.CreatedAt)
                            if ($createdAt -lt $cutoffDate) {
                                Remove-Item $dir.FullName -Recurse -Force -ErrorAction Stop
                                $result.DeletedBackups++
                                Write-Verbose "删除旧备份: $($dir.Name)"
                                continue
                            }
                        }
                    }

                    # 如果没有信息文件，根据目录修改时间判断
                    if ($dir.LastWriteTime -lt $cutoffDate) {
                        Remove-Item $dir.FullName -Recurse -Force -ErrorAction Stop
                        $result.DeletedBackups++
                        Write-Verbose "删除旧备份（按修改时间）: $($dir.Name)"
                    } else {
                        $result.KeptBackups++
                    }

                } catch {
                    $result.Errors += "无法删除备份目录 $($dir.Name): $_"
                }
            }

            Write-Verbose "备份清理完成: 删除了 $($result.DeletedBackups) 个旧备份，保留了 $($result.KeptBackups) 个备份"

        } catch {
            $result.Errors += "清理旧备份时出错: $_"
        }

        return $result
    }

    [hashtable] ReinitializeSystem() {
        # 重新初始化系统
        try {
            # 1. 重新创建必要的目录
            $requiredDirs = @(
                "cache",
                "logs",
                "config",
                "tasks",
                "backups"
            )

            foreach ($dir in $requiredDirs) {
                $fullPath = Join-Path $this.RootPath $dir
                if (-not (Test-Path $fullPath)) {
                    New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
                    Write-Verbose "创建目录: $dir"
                }
            }

            # 2. 重新初始化配置（如果有备份）
            $configBackup = Join-Path $this.RootPath "config\user_prefs.json.backup"
            $configFile = Join-Path $this.RootPath "config\user_prefs.json"

            if (Test-Path $configBackup -and -not (Test-Path $configFile)) {
                Copy-Item $configBackup $configFile -Force -ErrorAction SilentlyContinue
                Write-Verbose "从备份恢复配置"
            } elseif (-not (Test-Path $configFile)) {
                # 创建默认配置
                $defaultConfig = @{
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
                    ResetCount = 0
                    LastReset = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                }

                $configJson = $defaultConfig | ConvertTo-Json -Depth 10
                Set-Content -Path $configFile -Value $configJson -Encoding UTF8
                Write-Verbose "创建默认配置"
            }

            # 3. 更新重置计数
            if (Test-Path $configFile) {
                try {
                    $configJson = Get-Content $configFile -Raw -ErrorAction Stop
                    $config = $configJson | ConvertFrom-Json -AsHashtable

                    $config.ResetCount = ($config.ResetCount -as [int]) + 1
                    $config.LastReset = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

                    $configJson = $config | ConvertTo-Json -Depth 10
                    Set-Content -Path $configFile -Value $configJson -Encoding UTF8
                    Write-Verbose "更新重置计数: $($config.ResetCount)"
                } catch {
                    Write-Warning "无法更新重置计数: $_"
                }
            }

            # 4. 初始化状态管理器
            $stateManager = Get-AIIStateManager -ErrorAction SilentlyContinue
            if ($stateManager) {
                $stateManager.Dispose()
                $global:StateManagerInstance = $null
                Write-Verbose "状态管理器已重置"
            }

            # 5. 初始化任务管理器
            $taskManager = Get-AIITaskManager -ErrorAction SilentlyContinue
            if ($taskManager) {
                $taskManager.Dispose()
                $global:TaskManagerInstance = $null
                Write-Verbose "任务管理器已重置"
            }

            # 6. 重新初始化工作流
            $coreModule = Join-Path $this.RootPath "powershell\Modules\Core.psm1"
            if (Test-Path $coreModule) {
                try {
                    # 重新导入核心模块以重新初始化
                    Import-Module $coreModule -Force -ErrorAction Stop
                    Initialize-AIIWorkflow -Force | Out-Null
                    Write-Verbose "工作流重新初始化完成"
                } catch {
                    Write-Warning "重新初始化工作流失败: $_"
                }
            }

            return @{
                Success = $true
                Message = "系统重新初始化完成"
                ResetTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            }

        } catch {
            Write-Error "重新初始化系统失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [hashtable] RestoreFromBackup([string]$backupDir, [switch]$Force) {
        # 从备份恢复系统
        try {
            if (-not (Test-Path $backupDir)) {
                throw "备份目录不存在: $backupDir"
            }

            # 检查备份信息
            $infoFile = Join-Path $backupDir "backup-info.json"
            if (-not (Test-Path $infoFile)) {
                throw "备份信息文件不存在: $infoFile"
            }

            $infoJson = Get-Content $infoFile -Raw -ErrorAction Stop
            $backupInfo = $infoJson | ConvertFrom-Json -AsHashtable

            if (-not $Force) {
                Write-Host "⚠️  警告：将从备份恢复系统" -ForegroundColor Yellow
                Write-Host "   备份时间: $($backupInfo.CreatedAt)" -ForegroundColor White
                Write-Host "   备份类型: $($backupInfo.BackupType)" -ForegroundColor White
                Write-Host "   备份大小: $([math]::Round($backupInfo.Summary.TotalSize/1MB, 2)) MB" -ForegroundColor White

                $confirmation = Read-Host "确认恢复？(输入 'yes' 继续)"
                if ($confirmation -ne "yes") {
                    return @{
                        Success = $false
                        Message = "恢复操作已取消"
                    }
                }
            }

            Write-Host "🔄 开始从备份恢复..." -ForegroundColor Yellow

            # 1. 停止所有进程
            Write-Host "  1. 停止相关进程..." -ForegroundColor Cyan
            $this.StopAllProcesses()

            # 2. 备份当前状态
            Write-Host "  2. 备份当前状态..." -ForegroundColor Cyan
            $currentBackup = $this.CreateBackup("pre-restore-$(Get-Date -Format 'yyyyMMdd-HHmmss')")

            # 3. 恢复备份
            Write-Host "  3. 恢复备份..." -ForegroundColor Cyan
            $restoreResult = $this.RestoreBackupFiles($backupDir, $backupInfo)

            # 4. 重新初始化系统
            Write-Host "  4. 重新初始化系统..." -ForegroundColor Cyan
            $initResult = $this.ReinitializeSystem()

            $result = @{
                Success = $true
                BackupDir = $backupDir
                BackupInfo = $backupInfo
                CurrentBackup = $currentBackup
                RestoreResult = $restoreResult
                Reinitialization = $initResult
                Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            }

            Write-Host "✅ 备份恢复完成" -ForegroundColor Green
            Write-Host "   从备份恢复: $backupDir" -ForegroundColor White
            Write-Host "   当前状态备份: $($currentBackup.BackupDir)" -ForegroundColor White
            Write-Host "   恢复项目: $($restoreResult.RestoredItems.Count)" -ForegroundColor White

            return $result

        } catch {
            Write-Error "备份恢复失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [hashtable] RestoreBackupFiles([string]$backupDir, [hashtable]$backupInfo) {
        # 恢复备份文件
        $result = @{
            RestoredItems = @()
            FailedItems = @()
            TotalItems = 0
        }

        try {
            foreach ($item in $backupInfo.Summary.Items) {
                if ($item.Status -ne "成功") {
                    Write-Warning "跳过失败的备份项: $($item.Name)"
                    continue
                }

                $result.TotalItems++

                try {
                    $destination = $item.Source  # 恢复原始位置

                    # 确保目标目录存在
                    $destDir = Split-Path $destination -Parent
                    if (-not (Test-Path $destDir)) {
                        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
                    }

                    # 恢复文件或目录
                    if (Test-Path $item.Destination -PathType Container) {
                        Copy-Item -Path $item.Destination -Destination $destination -Recurse -Force -ErrorAction Stop
                    } else {
                        Copy-Item -Path $item.Destination -Destination $destination -Force -ErrorAction Stop
                    }

                    $result.RestoredItems += @{
                        Name = $item.Name
                        Source = $item.Destination
                        Destination = $destination
                        Status = "恢复成功"
                    }

                    Write-Verbose "恢复成功: $($item.Name) -> $destination"

                } catch {
                    $result.FailedItems += @{
                        Name = $item.Name
                        Source = $item.Destination
                        Destination = $item.Source
                        Status = "恢复失败"
                        Error = $_.Exception.Message
                    }
                    Write-Warning "恢复失败 $($item.Name): $_"
                }
            }

            return $result

        } catch {
            throw "恢复备份文件时出错: $_"
        }
    }

    [array] ListBackups() {
        # 列出所有备份
        try {
            $backupsDir = Join-Path $this.RootPath "backups"
            if (-not (Test-Path $backupsDir)) {
                return @()
            }

            $backups = @()
            $backupDirs = Get-ChildItem -Path $backupsDir -Directory -ErrorAction SilentlyContinue |
                         Sort-Object LastWriteTime -Descending

            foreach ($dir in $backupDirs) {
                $infoFile = Join-Path $dir.FullName "backup-info.json"
                $backupInfo = $null

                if (Test-Path $infoFile) {
                    try {
                        $infoJson = Get-Content $infoFile -Raw -ErrorAction Stop
                        $backupInfo = $infoJson | ConvertFrom-Json -AsHashtable
                    } catch {
                        Write-Verbose "无法解析备份信息文件: $infoFile"
                    }
                }

                $backups += @{
                    Name = $dir.Name
                    Path = $dir.FullName
                    LastWriteTime = $dir.LastWriteTime
                    Size = (Get-ChildItem -Path $dir.FullName -Recurse -File -ErrorAction SilentlyContinue |
                           Measure-Object -Property Length -Sum).Sum
                    Info = $backupInfo
                }
            }

            return $backups

        } catch {
            Write-Error "列出备份失败: $_"
            return @()
        }
    }

    [hashtable] ValidateSystem() {
        # 验证系统完整性
        try {
            $validationResults = @{
                Checks = @()
                Passed = 0
                Failed = 0
                Warnings = 0
                Status = "未知"
            }

            # 检查必要目录
            $requiredDirs = @("config", "cache", "logs", "tasks", "scripts", ".claude", ".claude\agents")
            foreach ($dir in $requiredDirs) {
                $fullPath = Join-Path $this.RootPath $dir
                if (Test-Path $fullPath) {
                    $validationResults.Checks += @{
                        Check = "目录: $dir"
                        Status = "通过"
                        Details = "存在"
                    }
                    $validationResults.Passed++
                } else {
                    $validationResults.Checks += @{
                        Check = "目录: $dir"
                        Status = "失败"
                        Details = "不存在"
                    }
                    $validationResults.Failed++
                }
            }

            # 检查必要文件
            $requiredFiles = @(
                "ww_enhanced.py",
                "ww.bat",
                ".claude\CLAUDE.md",
                ".claude\agents\manifest.json",
                "scripts\state_machine.py",
                "scripts\workflow_utils.py"
            )

            foreach ($file in $requiredFiles) {
                $fullPath = Join-Path $this.RootPath $file
                if (Test-Path $fullPath) {
                    $validationResults.Checks += @{
                        Check = "文件: $file"
                        Status = "通过"
                        Details = "存在"
                    }
                    $validationResults.Passed++
                } else {
                    $validationResults.Checks += @{
                        Check = "文件: $file"
                        Status = "失败"
                        Details = "不存在"
                    }
                    $validationResults.Failed++
                }
            }

            # 检查Python环境
            try {
                $pythonVersion = python --version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $validationResults.Checks += @{
                        Check = "Python环境"
                        Status = "通过"
                        Details = $pythonVersion
                    }
                    $validationResults.Passed++
                } else {
                    $validationResults.Checks += @{
                        Check = "Python环境"
                        Status = "失败"
                        Details = "Python未正确安装"
                    }
                    $validationResults.Failed++
                }
            } catch {
                $validationResults.Checks += @{
                    Check = "Python环境"
                    Status = "失败"
                    Details = "Python命令不可用"
                }
                $validationResults.Failed++
            }

            # 检查PowerShell模块
            $moduleFiles = @(
                "powershell\AIIWorkflow.psd1",
                "powershell\Modules\Core.psm1",
                "powershell\Modules\StateManager.psm1",
                "powershell\Modules\TaskManager.psm1",
                "powershell\Modules\VSCodeIntegration.psm1",
                "powershell\Modules\ResetManager.psm1"
            )

            foreach ($file in $moduleFiles) {
                $fullPath = Join-Path $this.RootPath $file
                if (Test-Path $fullPath) {
                    $validationResults.Checks += @{
                        Check = "PowerShell模块: $file"
                        Status = "通过"
                        Details = "存在"
                    }
                    $validationResults.Passed++
                } else {
                    $validationResults.Checks += @{
                        Check = "PowerShell模块: $file"
                        Status = "警告"
                        Details = "不存在"
                    }
                    $validationResults.Warnings++
                }
            }

            # 确定总体状态
            if ($validationResults.Failed -eq 0) {
                if ($validationResults.Warnings -eq 0) {
                    $validationResults.Status = "健康"
                } else {
                    $validationResults.Status = "警告"
                }
            } else {
                $validationResults.Status = "异常"
            }

            return $validationResults

        } catch {
            Write-Error "系统验证失败: $_"
            return @{
                Checks = @()
                Passed = 0
                Failed = 1
                Warnings = 0
                Status = "验证失败"
                Error = $_.Exception.Message
            }
        }
    }

    [void] Dispose() {
        # 清理资源
        # 当前类没有需要清理的资源
    }
}

# 全局重置管理器实例
$global:ResetManagerInstance = $null

function Get-AIIResetManager {
<#
.SYNOPSIS
获取或创建重置管理器实例

.DESCRIPTION
返回全局重置管理器实例，如果不存在则创建。

.EXAMPLE
$resetManager = Get-AIIResetManager

.OUTPUTS
[ResetManager] 重置管理器实例
#>
    [CmdletBinding()]
    [OutputType([ResetManager])]
    param()

    if (-not $global:ResetManagerInstance) {
        $root = $global:AIIWorkflowRoot
        if (-not $root) {
            throw "AII工作流根目录未设置，请先调用 Initialize-AIIWorkflow"
        }

        $global:ResetManagerInstance = [ResetManager]::new($root)
        Write-Verbose "创建新的重置管理器实例"
    }

    return $global:ResetManagerInstance
}

function Reset-AIISystem {
<#
.SYNOPSIS
重置AII工作流系统

.DESCRIPTION
重置系统到初始状态，可选择保留配置和任务。

.PARAMETER Force
强制重置，不需要确认

.PARAMETER KeepConfig
保留配置文件

.PARAMETER KeepTasks
保留任务数据

.PARAMETER DaysToKeep
保留多少天内的备份，默认7天

.EXAMPLE
Reset-AIISystem -Force

.EXAMPLE
Reset-AIISystem -Force -KeepConfig -KeepTasks

.OUTPUTS
[hashtable] 重置结果
#>
    [CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
    [OutputType([hashtable])]
    param(
        [Parameter()]
        [switch]$Force,

        [Parameter()]
        [switch]$KeepConfig,

        [Parameter()]
        [switch]$KeepTasks,

        [Parameter()]
        [int]$DaysToKeep = 7
    )

    begin {
        Write-Verbose "重置AII工作流系统..."
    }

    process {
        try {
            if ($PSCmdlet.ShouldProcess("AII工作流系统", "重置")) {
                $resetManager = Get-AIIResetManager -ErrorAction Stop
                $result = $resetManager.ResetSystem($Force, $KeepConfig, $KeepTasks, $DaysToKeep)

                return $result
            }

        } catch {
            Write-Error "重置系统失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "系统重置过程完成"
    }
}

function Backup-AIISystem {
<#
.SYNOPSIS
备份AII工作流系统

.DESCRIPTION
创建系统备份。

.PARAMETER BackupType
备份类型（manual, auto, reset）

.EXAMPLE
Backup-AIISystem

.EXAMPLE
Backup-AIISystem -BackupType "manual"

.OUTPUTS
[hashtable] 备份结果
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter()]
        [ValidateSet("manual", "auto", "reset")]
        [string]$BackupType = "manual"
    )

    begin {
        Write-Verbose "备份AII工作流系统..."
    }

    process {
        try {
            $resetManager = Get-AIIResetManager -ErrorAction Stop
            $result = $resetManager.CreateBackup($BackupType)

            if ($result.Success) {
                Write-Host "✅ 系统备份创建成功" -ForegroundColor Green
                Write-Host "   备份位置: $($result.BackupDir)" -ForegroundColor White
                Write-Host "   备份大小: $([math]::Round($result.Summary.TotalSize/1MB, 2)) MB" -ForegroundColor White
                Write-Host "   成功项目: $($result.Summary.SuccessCount)" -ForegroundColor White
                Write-Host "   失败项目: $($result.Summary.FailedCount)" -ForegroundColor White
            } else {
                Write-Error "系统备份失败: $($result.Error)"
            }

            return $result

        } catch {
            Write-Error "系统备份失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "系统备份过程完成"
    }
}

function Restore-AIISystem {
<#
.SYNOPSIS
从备份恢复AII工作流系统

.DESCRIPTION
从指定备份恢复系统。

.PARAMETER BackupDir
备份目录路径

.PARAMETER Force
强制恢复，不需要确认

.EXAMPLE
Restore-AIISystem -BackupDir "O:\AII\上下文助手\backups\manual-20240415-153000"

.EXAMPLE
Restore-AIISystem -BackupDir "backups\auto-20240415-120000" -Force

.OUTPUTS
[hashtable] 恢复结果
#>
    [CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory=$true)]
        [string]$BackupDir,

        [Parameter()]
        [switch]$Force
    )

    begin {
        Write-Verbose "从备份恢复AII工作流系统..."
    }

    process {
        try {
            if ($PSCmdlet.ShouldProcess("AII工作流系统", "从备份恢复")) {
                $resetManager = Get-AIIResetManager -ErrorAction Stop
                $result = $resetManager.RestoreFromBackup($BackupDir, $Force)

                return $result
            }

        } catch {
            Write-Error "从备份恢复失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "备份恢复过程完成"
    }
}

function Get-AIIBackups {
<#
.SYNOPSIS
获取AII工作流系统备份列表

.DESCRIPTION
列出所有可用的系统备份。

.EXAMPLE
Get-AIIBackups

.OUTPUTS
[array] 备份列表
#>
    [CmdletBinding()]
    [OutputType([array])]
    param()

    begin {
        Write-Verbose "获取AII工作流系统备份列表..."
    }

    process {
        try {
            $resetManager = Get-AIIResetManager -ErrorAction Stop
            $backups = $resetManager.ListBackups()

            return $backups

        } catch {
            Write-Error "获取备份列表失败: $_"
            return @()
        }
    }

    end {
        Write-Verbose "备份列表获取完成"
    }
}

function Test-AIISystem {
<#
.SYNOPSIS
测试AII工作流系统完整性

.DESCRIPTION
验证系统所有组件的完整性。

.EXAMPLE
Test-AIISystem

.OUTPUTS
[hashtable] 验证结果
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param()

    begin {
        Write-Verbose "测试AII工作流系统完整性..."
    }

    process {
        try {
            $resetManager = Get-AIIResetManager -ErrorAction Stop
            $result = $resetManager.ValidateSystem()

            # 显示验证结果
            Write-Host "🔍 系统完整性测试" -ForegroundColor Cyan
            Write-Host "   总体状态: $($result.Status)" -ForegroundColor $(
                switch ($result.Status) {
                    "健康" { "Green" }
                    "警告" { "Yellow" }
                    "异常" { "Red" }
                    default { "White" }
                }
            )
            Write-Host "   通过: $($result.Passed)" -ForegroundColor Green
            Write-Host "   失败: $($result.Failed)" -ForegroundColor $($result.Failed -gt 0 ? "Red" : "White")
            Write-Host "   警告: $($result.Warnings)" -ForegroundColor $($result.Warnings -gt 0 ? "Yellow" : "White")

            if ($result.Checks.Count -gt 0) {
                Write-Host ""
                Write-Host "详细检查结果:" -ForegroundColor Cyan
                foreach ($check in $result.Checks) {
                    $color = switch ($check.Status) {
                        "通过" { "Green" }
                        "失败" { "Red" }
                        "警告" { "Yellow" }
                        default { "White" }
                    }
                    Write-Host "   [$($check.Status)] $($check.Check)" -ForegroundColor $color
                    if ($check.Details) {
                        Write-Host "       详情: $($check.Details)" -ForegroundColor Gray
                    }
                }
            }

            return $result

        } catch {
            Write-Error "系统测试失败: $_"
            return @{
                Checks = @()
                Passed = 0
                Failed = 1
                Warnings = 0
                Status = "测试失败"
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "系统测试完成"
    }
}

function Repair-AIISystem {
<#
.SYNOPSIS
修复AII工作流系统

.DESCRIPTION
尝试自动修复系统问题。

.EXAMPLE
Repair-AIISystem

.OUTPUTS
[hashtable] 修复结果
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param()

    begin {
        Write-Verbose "修复AII工作流系统..."
    }

    process {
        try {
            # 1. 验证系统
            Write-Host "1. 验证系统状态..." -ForegroundColor Cyan
            $validation = Test-AIISystem

            if ($validation.Status -eq "健康") {
                Write-Host "   ✅ 系统状态健康，无需修复" -ForegroundColor Green
                return @{
                    Success = $true
                    Message = "系统状态健康，无需修复"
                    Validation = $validation
                }
            }

            # 2. 创建备份
            Write-Host "2. 创建修复前备份..." -ForegroundColor Cyan
            $backupResult = Backup-AIISystem -BackupType "repair"
            if (-not $backupResult.Success) {
                Write-Warning "备份创建失败，但继续修复..."
            }

            # 3. 修复缺失的目录
            Write-Host "3. 修复缺失的目录和文件..." -ForegroundColor Cyan
            $repairResults = @{
                CreatedDirs = 0
                CreatedFiles = 0
                FixedIssues = @()
            }

            $requiredDirs = @("config", "cache", "logs", "tasks", "backups", "powershell\Modules")
            foreach ($dir in $requiredDirs) {
                $fullPath = Join-Path $global:AIIWorkflowRoot $dir
                if (-not (Test-Path $fullPath)) {
                    try {
                        New-Item -ItemType Directory -Path $fullPath -Force -ErrorAction Stop | Out-Null
                        $repairResults.CreatedDirs++
                        $repairResults.FixedIssues += "创建目录: $dir"
                        Write-Host "   ✅ 创建目录: $dir" -ForegroundColor Green
                    } catch {
                        Write-Warning "无法创建目录 $dir : $_"
                    }
                }
            }

            # 4. 重新初始化配置
            Write-Host "4. 重新初始化配置..." -ForegroundColor Cyan
            try {
                Initialize-AIIWorkflow -Force | Out-Null
                $repairResults.FixedIssues += "重新初始化配置"
                Write-Host "   ✅ 配置重新初始化完成" -ForegroundColor Green
            } catch {
                Write-Warning "重新初始化配置失败: $_"
            }

            # 5. 重新验证
            Write-Host "5. 重新验证系统..." -ForegroundColor Cyan
            $finalValidation = Test-AIISystem

            $result = @{
                Success = $finalValidation.Status -eq "健康" -or $finalValidation.Status -eq "警告"
                InitialStatus = $validation.Status
                FinalStatus = $finalValidation.Status
                BackupResult = $backupResult
                RepairResults = $repairResults
                Validation = $finalValidation
                Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            }

            if ($result.Success) {
                Write-Host "✅ 系统修复完成" -ForegroundColor Green
                Write-Host "   修复前状态: $($validation.Status)" -ForegroundColor White
                Write-Host "   修复后状态: $($finalValidation.Status)" -ForegroundColor White
                Write-Host "   修复问题数: $($repairResults.FixedIssues.Count)" -ForegroundColor White
            } else {
                Write-Host "⚠️  系统修复部分完成" -ForegroundColor Yellow
                Write-Host "   修复前状态: $($validation.Status)" -ForegroundColor White
                Write-Host "   修复后状态: $($finalValidation.Status)" -ForegroundColor White
                Write-Host "   仍有问题需要手动处理" -ForegroundColor Yellow
            }

            return $result

        } catch {
            Write-Error "系统修复失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
                Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            }
        }
    }

    end {
        Write-Verbose "系统修复过程完成"
    }
}

# 导出模块函数
Export-ModuleMember -Function @(
    'Get-AIIResetManager',
    'Reset-AIISystem',
    'Backup-AIISystem',
    'Restore-AIISystem',
    'Get-AIIBackups',
    'Test-AIISystem',
    'Repair-AIISystem'
)

# 模块初始化
if ($global:AIIWorkflowRoot) {
    try {
        # 确保重置管理器已初始化
        Get-AIIResetManager | Out-Null
    } catch {
        Write-Warning "重置管理器初始化失败: $_"
    }
}

# 注册清理处理程序
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    if ($global:ResetManagerInstance) {
        $global:ResetManagerInstance.Dispose()
        $global:ResetManagerInstance = $null
    }
}