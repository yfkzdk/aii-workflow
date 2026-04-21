# AII Workflow PowerShell Module - VS Code Integration
# VS Code集成模块：负责与VS Code扩展的交互和集成

using namespace System.Management.Automation
using namespace System.IO
using namespace System.Diagnostics

class VSCodeIntegration {
    # VS Code集成类
    [string]$RootPath
    [string]$VSCodePath
    [hashtable]$ExtensionInfo
    [System.Diagnostics.Process]$VSCodeProcess

    VSCodeIntegration([string]$rootPath) {
        $this.RootPath = $rootPath
        $this.VSCodePath = $this.FindVSCodePath()
        $this.ExtensionInfo = $this.DetectExtension()
    }

    [string] FindVSCodePath() {
        # 查找VS Code可执行文件路径
        $possiblePaths = @(
            "code",
            "code.cmd",
            "$env:LOCALAPPDATA\Programs\Microsoft VS Code\Code.exe",
            "$env:ProgramFiles\Microsoft VS Code\Code.exe",
            "$env:ProgramFiles(x86)\Microsoft VS Code\Code.exe",
            "/usr/bin/code",
            "/usr/local/bin/code",
            "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
        )

        foreach ($path in $possiblePaths) {
            try {
                $result = Get-Command $path -ErrorAction Stop 2>$null
                if ($result) {
                    Write-Verbose "找到VS Code: $($result.Source)"
                    return $result.Source
                }
            } catch {
                # 继续尝试下一个路径
            }
        }

        # 尝试通过注册表查找（Windows）
        if ($IsWindows -or $env:OS -like "*Windows*") {
            try {
                $regPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Code.exe"
                if (Test-Path $regPath) {
                    $codePath = Get-ItemProperty -Path $regPath -Name "(default)" -ErrorAction Stop
                    if ($codePath."(default)" -and (Test-Path $codePath."(default)")) {
                        Write-Verbose "通过注册表找到VS Code: $($codePath.'(default)')"
                        return $codePath."(default)"
                    }
                }
            } catch {
                # 注册表查找失败
            }
        }

        Write-Warning "未找到VS Code，部分功能可能受限"
        return $null
    }

    [hashtable] DetectExtension() {
        # 检测AII工作流扩展
        $extensionInfo = @{
            Installed = $false
            Enabled = $false
            Version = $null
            Path = $null
        }

        if (-not $this.VSCodePath) {
            return $extensionInfo
        }

        try {
            # 列出已安装的扩展
            $output = & $this.VSCodePath --list-extensions --show-versions 2>$null
            if ($LASTEXITCODE -eq 0 -and $output) {
                foreach ($line in $output -split "`n") {
                    if ($line -match "aii-workflow|AII\.workflow") {
                        $extensionInfo.Installed = $true
                        $extensionInfo.Version = ($line -split '@')[1]
                        break
                    }
                }
            }

            # 检查扩展目录
            $extensionDirs = @(
                "$env:USERPROFILE\.vscode\extensions",
                "$env:HOME\.vscode\extensions",
                "$env:APPDATA\Code\extensions"
            )

            foreach ($dir in $extensionDirs) {
                if (Test-Path $dir) {
                    $extensions = Get-ChildItem -Path $dir -Directory -ErrorAction SilentlyContinue |
                                 Where-Object { $_.Name -like "*aii-workflow*" -or $_.Name -like "*AII.workflow*" }

                    if ($extensions) {
                        $extensionInfo.Path = $extensions[0].FullName
                        break
                    }
                }
            }

            # 检查扩展是否启用
            if ($extensionInfo.Installed) {
                $settingsPath = @(
                    "$env:APPDATA\Code\User\settings.json",
                    "$env:HOME\.config\Code\User\settings.json",
                    "$env:USERPROFILE\.vscode\settings.json"
                ) | Where-Object { Test-Path $_ } | Select-Object -First 1

                if ($settingsPath) {
                    $settings = Get-Content $settingsPath -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json -ErrorAction SilentlyContinue
                    if ($settings -and $settings."aii-workflow.enabled" -ne $false) {
                        $extensionInfo.Enabled = $true
                    } else {
                        $extensionInfo.Enabled = $true  # 默认启用
                    }
                } else {
                    $extensionInfo.Enabled = $true  # 默认启用
                }
            }

        } catch {
            Write-Warning "检测VS Code扩展失败: $_"
        }

        return $extensionInfo
    }

    [hashtable] StartVSCode([string]$workspacePath, [switch]$NewWindow, [switch]$ReuseWindow) {
        # 启动VS Code
        try {
            if (-not $this.VSCodePath) {
                throw "未找到VS Code可执行文件"
            }

            $args = @()

            if ($NewWindow) {
                $args += "--new-window"
            } elseif ($ReuseWindow) {
                $args += "--reuse-window"
            }

            if ($workspacePath) {
                if (Test-Path $workspacePath) {
                    $args += "`"$workspacePath`""
                } else {
                    Write-Warning "工作空间路径不存在: $workspacePath"
                }
            }

            Write-Verbose "启动VS Code: $($this.VSCodePath) $args"

            $processInfo = New-Object System.Diagnostics.ProcessStartInfo
            $processInfo.FileName = $this.VSCodePath
            $processInfo.Arguments = $args -join " "
            $processInfo.UseShellExecute = $false
            $processInfo.RedirectStandardOutput = $true
            $processInfo.RedirectStandardError = $true
            $processInfo.CreateNoWindow = $true

            $this.VSCodeProcess = New-Object System.Diagnostics.Process
            $this.VSCodeProcess.StartInfo = $processInfo
            $this.VSCodeProcess.Start() | Out-Null

            # 等待VS Code启动
            Start-Sleep -Seconds 2

            # 检查进程是否在运行
            if ($this.VSCodeProcess.HasExited) {
                $errorOutput = $this.VSCodeProcess.StandardError.ReadToEnd()
                throw "VS Code启动失败: $errorOutput"
            }

            Write-Verbose "VS Code已启动，进程ID: $($this.VSCodeProcess.Id)"

            return @{
                Success = $true
                ProcessId = $this.VSCodeProcess.Id
                VSCodePath = $this.VSCodePath
                Arguments = $args -join " "
            }

        } catch {
            Write-Error "启动VS Code失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [hashtable] ExecuteVSCodeCommand([string]$command, [hashtable]$args = @{}) {
        # 执行VS Code命令
        try {
            if (-not $this.VSCodePath) {
                throw "未找到VS Code可执行文件"
            }

            # 构建命令参数
            $commandArgs = @("--command", $command)

            # 添加额外参数
            if ($args.Count -gt 0) {
                $jsonArgs = $args | ConvertTo-Json -Compress
                $commandArgs += "--args", $jsonArgs
            }

            Write-Verbose "执行VS Code命令: $command"

            $processInfo = New-Object System.Diagnostics.ProcessStartInfo
            $processInfo.FileName = $this.VSCodePath
            $processInfo.Arguments = $commandArgs -join " "
            $processInfo.UseShellExecute = $false
            $processInfo.RedirectStandardOutput = $true
            $processInfo.RedirectStandardError = $true
            $processInfo.CreateNoWindow = $true

            $process = New-Object System.Diagnostics.Process
            $process.StartInfo = $processInfo
            $process.Start() | Out-Null

            $output = $process.StandardOutput.ReadToEnd()
            $errorOutput = $process.StandardError.ReadToEnd()
            $process.WaitForExit()

            if ($process.ExitCode -eq 0) {
                Write-Verbose "VS Code命令执行成功"
                return @{
                    Success = $true
                    Output = $output.Trim()
                    Command = $command
                }
            } else {
                throw "VS Code命令执行失败: $errorOutput"
            }

        } catch {
            Write-Error "执行VS Code命令失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
                Command = $command
            }
        }
    }

    [hashtable] OpenAIIWorkflow([string]$taskId) {
        # 在VS Code中打开AII工作流
        try {
            $stateManager = Get-AIIStateManager
            $taskManager = Get-AIITaskManager

            # 确定要打开的任务
            if (-not $taskId) {
                if ($stateManager.CurrentState.CurrentTask) {
                    $taskId = $stateManager.CurrentState.CurrentTask.TaskId
                } else {
                    # 打开工作流根目录
                    return $this.StartVSCode($this.RootPath, -NewWindow)
                }
            }

            # 获取任务信息
            $taskInfo = $taskManager.GetTaskInfo($taskId)
            if (-not $taskInfo.Success) {
                throw "无法获取任务信息: $($taskInfo.Error)"
            }

            # 在VS Code中打开任务目录
            return $this.StartVSCode($taskInfo.TaskDir, -NewWindow)

        } catch {
            Write-Error "打开AII工作流失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [hashtable] InstallExtension() {
        # 安装AII工作流扩展
        try {
            if (-not $this.VSCodePath) {
                throw "未找到VS Code可执行文件"
            }

            # 检查扩展是否已安装
            if ($this.ExtensionInfo.Installed) {
                Write-Verbose "AII工作流扩展已安装，版本: $($this.ExtensionInfo.Version)"
                return @{
                    Success = $true
                    AlreadyInstalled = $true
                    Version = $this.ExtensionInfo.Version
                }
            }

            # 从本地安装扩展（如果存在）
            $localExtensionPath = Join-Path $this.RootPath "vscode-extension"
            if (Test-Path $localExtensionPath) {
                Write-Verbose "从本地安装扩展: $localExtensionPath"

                $processInfo = New-Object System.Diagnostics.ProcessStartInfo
                $processInfo.FileName = $this.VSCodePath
                $processInfo.Arguments = "--install-extension `"$localExtensionPath`""
                $processInfo.UseShellExecute = $false
                $processInfo.RedirectStandardOutput = $true
                $processInfo.RedirectStandardError = $true
                $processInfo.CreateNoWindow = $true

                $process = New-Object System.Diagnostics.Process
                $process.StartInfo = $processInfo
                $process.Start() | Out-Null

                $output = $process.StandardOutput.ReadToEnd()
                $errorOutput = $process.StandardError.ReadToEnd()
                $process.WaitForExit()

                if ($process.ExitCode -eq 0) {
                    Write-Verbose "扩展安装成功"
                    # 重新检测扩展
                    $this.ExtensionInfo = $this.DetectExtension()

                    return @{
                        Success = $true
                        AlreadyInstalled = $false
                        Version = $this.ExtensionInfo.Version
                        Output = $output.Trim()
                    }
                } else {
                    throw "扩展安装失败: $errorOutput"
                }
            } else {
                # 从市场安装扩展
                Write-Verbose "从VS Code市场安装扩展"
                return $this.ExecuteVSCodeCommand("workbench.extensions.installExtension", @{
                    id = "aii.workflow"
                })
            }

        } catch {
            Write-Error "安装VS Code扩展失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [hashtable] ConfigureExtension([hashtable]$settings) {
        # 配置AII工作流扩展
        try {
            if (-not $this.ExtensionInfo.Installed) {
                throw "AII工作流扩展未安装"
            }

            # 获取用户设置文件路径
            $settingsPath = $this.GetUserSettingsPath()
            if (-not $settingsPath) {
                throw "无法找到VS Code用户设置文件"
            }

            # 读取现有设置
            $currentSettings = @{}
            if (Test-Path $settingsPath) {
                try {
                    $content = Get-Content $settingsPath -Raw -ErrorAction Stop
                    $currentSettings = $content | ConvertFrom-Json -AsHashtable -ErrorAction SilentlyContinue
                } catch {
                    Write-Warning "无法解析现有设置文件，将创建新文件"
                }
            }

            # 更新AII工作流设置
            $aiiSettings = @{}
            if ($currentSettings.ContainsKey("aii-workflow")) {
                $aiiSettings = $currentSettings["aii-workflow"]
            }

            foreach ($key in $settings.Keys) {
                $aiiSettings[$key] = $settings[$key]
            }

            $currentSettings["aii-workflow"] = $aiiSettings

            # 保存设置
            $settingsJson = $currentSettings | ConvertTo-Json -Depth 10
            Set-Content -Path $settingsPath -Value $settingsJson -Encoding UTF8

            Write-Verbose "VS Code扩展配置已更新: $settingsPath"

            return @{
                Success = $true
                SettingsPath = $settingsPath
                Settings = $aiiSettings
            }

        } catch {
            Write-Error "配置VS Code扩展失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [string] GetUserSettingsPath() {
        # 获取VS Code用户设置文件路径
        $possiblePaths = @(
            "$env:APPDATA\Code\User\settings.json",
            "$env:HOME\.config\Code\User\settings.json",
            "$env:USERPROFILE\.vscode\settings.json",
            "$env:HOME\.vscode\settings.json"
        )

        foreach ($path in $possiblePaths) {
            if (Test-Path $path) {
                return $path
            }
        }

        # 如果不存在，返回默认路径
        if ($IsWindows -or $env:OS -like "*Windows*") {
            return "$env:APPDATA\Code\User\settings.json"
        } else {
            return "$env:HOME/.config/Code/User/settings.json"
        }
    }

    [hashtable] GetVSCodeWindows() {
        # 获取VS Code窗口信息
        try {
            if (-not $this.VSCodePath) {
                throw "未找到VS Code可执行文件"
            }

            # 使用VS Code的--status命令获取窗口信息
            $result = $this.ExecuteVSCodeCommand("workbench.action.showWindowStatus")

            if ($result.Success) {
                # 解析窗口信息（简化版本，实际需要更复杂的解析）
                $windows = @()

                # 这里应该解析VS Code的输出，但为了简化，我们返回基本信息
                $windows += @{
                    Id = "main"
                    Type = "main"
                    Workspace = $this.RootPath
                    PID = $this.VSCodeProcess ? $this.VSCodeProcess.Id : $null
                }

                return @{
                    Success = $true
                    Windows = $windows
                    Count = $windows.Count
                }
            } else {
                return @{
                    Success = $false
                    Error = $result.Error
                    Windows = @()
                    Count = 0
                }
            }

        } catch {
            Write-Error "获取VS Code窗口信息失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
                Windows = @()
                Count = 0
            }
        }
    }

    [hashtable] FocusAIIWorkflow() {
        # 聚焦到AII工作流窗口
        try {
            # 获取所有VS Code窗口
            $windowsInfo = $this.GetVSCodeWindows()
            if (-not $windowsInfo.Success) {
                throw "无法获取VS Code窗口信息"
            }

            # 查找包含AII工作流的窗口
            foreach ($window in $windowsInfo.Windows) {
                if ($window.Workspace -and $window.Workspace.Contains("AII")) {
                    # 发送焦点命令（简化实现）
                    return $this.ExecuteVSCodeCommand("workbench.action.focusWindow", @{
                        windowId = $window.Id
                    })
                }
            }

            # 如果没有找到，打开新的窗口
            return $this.OpenAIIWorkflow($null)

        } catch {
            Write-Error "聚焦AII工作流窗口失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    [void] Dispose() {
        # 清理资源
        if ($this.VSCodeProcess -and -not $this.VSCodeProcess.HasExited) {
            try {
                # 不强制关闭VS Code，只是释放引用
                $this.VSCodeProcess = $null
            } catch {
                Write-Verbose "释放VS Code进程引用失败: $_"
            }
        }
    }
}

# 全局VS Code集成实例
$global:VSCodeIntegrationInstance = $null

function Get-AIIVSCodeIntegration {
<#
.SYNOPSIS
获取或创建VS Code集成实例

.DESCRIPTION
返回全局VS Code集成实例，如果不存在则创建。

.EXAMPLE
$vscode = Get-AIIVSCodeIntegration

.OUTPUTS
[VSCodeIntegration] VS Code集成实例
#>
    [CmdletBinding()]
    [OutputType([VSCodeIntegration])]
    param()

    if (-not $global:VSCodeIntegrationInstance) {
        $root = $global:AIIWorkflowRoot
        if (-not $root) {
            throw "AII工作流根目录未设置，请先调用 Initialize-AIIWorkflow"
        }

        $global:VSCodeIntegrationInstance = [VSCodeIntegration]::new($root)
        Write-Verbose "创建新的VS Code集成实例"
    }

    return $global:VSCodeIntegrationInstance
}

function Open-AIIInVSCode {
<#
.SYNOPSIS
在VS Code中打开AII工作流

.DESCRIPTION
启动或切换到VS Code并打开AII工作流。

.PARAMETER TaskId
要打开的任务ID，如果未指定则打开工作流根目录

.PARAMETER NewWindow
在新窗口中打开

.PARAMETER ReuseWindow
重用现有窗口

.EXAMPLE
Open-AIIInVSCode

.EXAMPLE
Open-AIIInVSCode -TaskId "TASK-20240415-123456" -NewWindow

.OUTPUTS
[hashtable] 打开结果
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter()]
        [string]$TaskId,

        [Parameter()]
        [switch]$NewWindow,

        [Parameter()]
        [switch]$ReuseWindow
    )

    begin {
        Write-Verbose "在VS Code中打开AII工作流..."
    }

    process {
        try {
            $vscode = Get-AIIVSCodeIntegration -ErrorAction Stop

            if ($TaskId) {
                $result = $vscode.OpenAIIWorkflow($TaskId)
            } else {
                $result = $vscode.StartVSCode($vscode.RootPath, $NewWindow, $ReuseWindow)
            }

            if ($result.Success) {
                Write-Host "✅ 已在VS Code中打开AII工作流" -ForegroundColor Green
                if ($result.ProcessId) {
                    Write-Host "   VS Code进程ID: $($result.ProcessId)" -ForegroundColor White
                }
                if ($result.VSCodePath) {
                    Write-Host "   VS Code路径: $($result.VSCodePath)" -ForegroundColor White
                }
            } else {
                Write-Error "在VS Code中打开AII工作流失败: $($result.Error)"
            }

            return $result

        } catch {
            Write-Error "在VS Code中打开AII工作流失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "VS Code打开过程完成"
    }
}

function Install-AIIVSCodeExtension {
<#
.SYNOPSIS
安装AII工作流VS Code扩展

.DESCRIPTION
安装或更新AII工作流的VS Code扩展。

.EXAMPLE
Install-AIIVSCodeExtension

.OUTPUTS
[hashtable] 安装结果
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param()

    begin {
        Write-Verbose "安装AII工作流VS Code扩展..."
    }

    process {
        try {
            $vscode = Get-AIIVSCodeIntegration -ErrorAction Stop
            $result = $vscode.InstallExtension()

            if ($result.Success) {
                if ($result.AlreadyInstalled) {
                    Write-Host "✅ AII工作流扩展已安装，版本: $($result.Version)" -ForegroundColor Green
                } else {
                    Write-Host "✅ AII工作流扩展安装成功，版本: $($result.Version)" -ForegroundColor Green
                }
            } else {
                Write-Error "安装VS Code扩展失败: $($result.Error)"
            }

            return $result

        } catch {
            Write-Error "安装VS Code扩展失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "VS Code扩展安装过程完成"
    }
}

function Get-AIIVSCodeStatus {
<#
.SYNOPSIS
获取VS Code集成状态

.DESCRIPTION
显示VS Code和AII工作流扩展的状态信息。

.EXAMPLE
Get-AIIVSCodeStatus

.OUTPUTS
[pscustomobject] VS Code状态信息
#>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param()

    begin {
        Write-Verbose "获取VS Code集成状态..."
    }

    process {
        try {
            $vscode = Get-AIIVSCodeIntegration -ErrorAction Stop

            $status = [pscustomobject]@{
                VSCodeInstalled = [bool]$vscode.VSCodePath
                VSCodePath = $vscode.VSCodePath
                ExtensionInstalled = $vscode.ExtensionInfo.Installed
                ExtensionEnabled = $vscode.ExtensionInfo.Enabled
                ExtensionVersion = $vscode.ExtensionInfo.Version
                ExtensionPath = $vscode.ExtensionInfo.Path
                CanIntegrate = $vscode.VSCodePath -and $vscode.ExtensionInfo.Installed -and $vscode.ExtensionInfo.Enabled
                Status = if ($vscode.VSCodePath) {
                    if ($vscode.ExtensionInfo.Installed) {
                        if ($vscode.ExtensionInfo.Enabled) {
                            "已就绪"
                        } else {
                            "扩展已安装但未启用"
                        }
                    } else {
                        "VS Code已安装但扩展未安装"
                    }
                } else {
                    "VS Code未安装"
                }
            }

            return $status

        } catch {
            Write-Error "获取VS Code状态失败: $_"
            return [pscustomobject]@{
                VSCodeInstalled = $false
                VSCodePath = $null
                ExtensionInstalled = $false
                ExtensionEnabled = $false
                ExtensionVersion = $null
                ExtensionPath = $null
                CanIntegrate = $false
                Status = "错误: $_"
            }
        }
    }

    end {
        Write-Verbose "VS Code状态获取完成"
    }
}

function Set-AIIVSCodeSettings {
<#
.SYNOPSIS
配置AII工作流VS Code扩展设置

.DESCRIPTION
配置AII工作流扩展的VS Code设置。

.PARAMETER Settings
要配置的设置哈希表

.EXAMPLE
Set-AIIVSCodeSettings -Settings @{
    autoStart = $true
    notificationEnabled = $true
    defaultWorkspace = "O:\AII\上下文助手"
}

.OUTPUTS
[hashtable] 配置结果
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory=$true)]
        [hashtable]$Settings
    )

    begin {
        Write-Verbose "配置VS Code扩展设置..."
    }

    process {
        try {
            $vscode = Get-AIIVSCodeIntegration -ErrorAction Stop

            # 验证扩展是否安装
            if (-not $vscode.ExtensionInfo.Installed) {
                Write-Warning "AII工作流扩展未安装，正在安装..."
                $installResult = $vscode.InstallExtension()
                if (-not $installResult.Success) {
                    throw "扩展安装失败: $($installResult.Error)"
                }
            }

            $result = $vscode.ConfigureExtension($Settings)

            if ($result.Success) {
                Write-Host "✅ VS Code扩展设置已更新" -ForegroundColor Green
                Write-Host "   设置文件: $($result.SettingsPath)" -ForegroundColor White

                foreach ($key in $Settings.Keys) {
                    Write-Host "   $key = $($Settings[$key])" -ForegroundColor White
                }
            } else {
                Write-Error "配置VS Code扩展设置失败: $($result.Error)"
            }

            return $result

        } catch {
            Write-Error "配置VS Code扩展设置失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "VS Code扩展配置过程完成"
    }
}

function Start-AIIWithVSCode {
<#
.SYNOPSIS
启动AII工作流并在VS Code中打开

.DESCRIPTION
创建新任务并在VS Code中打开。

.PARAMETER Description
任务描述

.PARAMETER OpenInVSCode
是否在VS Code中打开

.EXAMPLE
Start-AIIWithVSCode -Description "帮我写一个Python脚本"

.EXAMPLE
Start-AIIWithVSCode "分析数据" -OpenInVSCode

.OUTPUTS
[hashtable] 启动结果
#>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory=$true, Position=0)]
        [string]$Description,

        [Parameter()]
        [switch]$OpenInVSCode = $true
    )

    begin {
        Write-Verbose "启动AII工作流并在VS Code中打开..."
    }

    process {
        try {
            # 1. 创建任务
            $taskResult = New-AIITask -Description $Description
            if (-not $taskResult.Success) {
                throw "任务创建失败: $($taskResult.Error)"
            }

            $taskId = $taskResult.TaskId

            # 2. 在VS Code中打开
            if ($OpenInVSCode) {
                $vscodeResult = Open-AIIInVSCode -TaskId $taskId -NewWindow
                if (-not $vscodeResult.Success) {
                    Write-Warning "无法在VS Code中打开任务，但任务已创建: $($vscodeResult.Error)"
                }
            }

            # 3. 启动任务
            $startResult = Start-AIITask -TaskId $taskId
            if (-not $startResult.Success) {
                Write-Warning "任务启动失败: $($startResult.Error)"
            }

            return @{
                Success = $true
                TaskId = $taskId
                TaskResult = $taskResult
                VSCodeResult = $vscodeResult
                StartResult = $startResult
            }

        } catch {
            Write-Error "启动AII工作流失败: $_"
            return @{
                Success = $false
                Error = $_.Exception.Message
            }
        }
    }

    end {
        Write-Verbose "AII工作流启动过程完成"
    }
}

# 导出模块函数
Export-ModuleMember -Function @(
    'Get-AIIVSCodeIntegration',
    'Open-AIIInVSCode',
    'Install-AIIVSCodeExtension',
    'Get-AIIVSCodeStatus',
    'Set-AIIVSCodeSettings',
    'Start-AIIWithVSCode'
)

# 模块初始化
if ($global:AIIWorkflowRoot) {
    try {
        # 确保VS Code集成已初始化
        Get-AIIVSCodeIntegration | Out-Null
    } catch {
        Write-Warning "VS Code集成初始化失败: $_"
    }
}

# 注册清理处理程序
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    if ($global:VSCodeIntegrationInstance) {
        $global:VSCodeIntegrationInstance.Dispose()
        $global:VSCodeIntegrationInstance = $null
    }
}