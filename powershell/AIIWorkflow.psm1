# AII Workflow PowerShell Module - Main Module
# 主模块：导出所有功能和提供统一的入口点

# 导入子模块
$modulePath = Split-Path $MyInvocation.MyCommand.Path -Parent
$modulesPath = Join-Path $modulePath "Modules"

# 导入所有子模块
$moduleFiles = @(
    "Core.psm1",
    "StateManager.psm1",
    "TaskManager.psm1",
    "VSCodeIntegration.psm1",
    "ResetManager.psm1"
)

foreach ($moduleFile in $moduleFiles) {
    $moduleFullPath = Join-Path $modulesPath $moduleFile
    if (Test-Path $moduleFullPath) {
        try {
            . $moduleFullPath
            Write-Verbose "已导入模块: $moduleFile"
        } catch {
            Write-Warning "导入模块 $moduleFile 失败: $_"
        }
    } else {
        Write-Warning "模块文件不存在: $moduleFullPath"
    }
}

# 重新导出所有函数（确保它们在全局作用域中可用）
Export-ModuleMember -Function * -Alias *

# 模块初始化脚本
$MyInvocation.MyCommand.ScriptBlock.Module.OnRemove = {
    Write-Verbose "清理AII工作流模块资源..."

    # 清理全局实例
    if ($global:StateManagerInstance) {
        $global:StateManagerInstance.Dispose()
        $global:StateManagerInstance = $null
    }

    if ($global:TaskManagerInstance) {
        $global:TaskManagerInstance.Dispose()
        $global:TaskManagerInstance = $null
    }

    if ($global:VSCodeIntegrationInstance) {
        $global:VSCodeIntegrationInstance.Dispose()
        $global:VSCodeIntegrationInstance = $null
    }

    if ($global:ResetManagerInstance) {
        $global:ResetManagerInstance.Dispose()
        $global:ResetManagerInstance = $null
    }

    # 清理环境变量
    $envVars = @(
        "AII_WORKFLOW_ROOT",
        "AII_WORKFLOW_CONFIG",
        "AII_WORKFLOW_LOG"
    )

    foreach ($envVar in $envVars) {
        if (Test-Path "env:$envVar") {
            Remove-Item "env:$envVar" -ErrorAction SilentlyContinue
        }
    }

    Write-Verbose "AII工作流模块清理完成"
}

# 模块加载时初始化
Write-Verbose "AII工作流PowerShell模块加载中..."

try {
    # 尝试初始化工作流
    Initialize-AIIWorkflow -ErrorAction SilentlyContinue | Out-Null

    # 显示欢迎信息
    $config = $global:AIIConfig
    if ($config -and $config.InteractiveMode) {
        Show-AIIWelcome
    }

    Write-Verbose "AII工作流PowerShell模块加载完成"
} catch {
    Write-Warning "AII工作流初始化失败: $_"
    Write-Warning "部分功能可能受限，请检查工作流系统配置"
}

# 设置模块变量
$script:ModuleLoaded = $true
$script:ModuleVersion = "1.0.0"
$script:ModuleName = "AIIWorkflow"

# 导出模块信息函数
function Get-AIIModuleInfo {
<#
.SYNOPSIS
获取AII工作流模块信息

.DESCRIPTION
显示模块版本、加载状态和功能信息。

.EXAMPLE
Get-AIIModuleInfo

.OUTPUTS
[pscustomobject] 模块信息
#>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param()

    $info = [pscustomobject]@{
        ModuleName = $script:ModuleName
        ModuleVersion = $script:ModuleVersion
        ModuleLoaded = $script:ModuleLoaded
        WorkflowRoot = $global:AIIWorkflowRoot
        ConfigLoaded = [bool]$global:AIIConfig
        StateManagerLoaded = [bool]$global:StateManagerInstance
        TaskManagerLoaded = [bool]$global:TaskManagerInstance
        VSCodeIntegrationLoaded = [bool]$global:VSCodeIntegrationInstance
        ResetManagerLoaded = [bool]$global:ResetManagerInstance
        AvailableFunctions = (Get-Command -Module AIIWorkflow).Count
        LoadTime = Get-Date
    }

    return $info
}

# 导出模块信息函数
Export-ModuleMember -Function Get-AIIModuleInfo

# 设置模块别名
Set-Alias -Name aii-start -Value New-AIITask -Description "启动新AII工作流任务"
Set-Alias -Name aii-status -Value Get-AIIStatus -Description "获取AII工作流状态"
Set-Alias -Name aii-resume -Value Resume-AIITask -Description "恢复AII工作流任务"
Set-Alias -Name aii-reset -Value Reset-AIISystem -Description "重置AII工作流系统"
Set-Alias -Name aii-panel -Value Show-AIIWelcome -Description "显示AII工作流面板"
Set-Alias -Name aii-vscode -Value Open-AIIInVSCode -Description "在VS Code中打开AII工作流"
Set-Alias -Name aii-backup -Value Backup-AIISystem -Description "备份AII工作流系统"
Set-Alias -Name aii-restore -Value Restore-AIISystem -Description "从备份恢复AII工作流系统"
Set-Alias -Name aii-test -Value Test-AIISystem -Description "测试AII工作流系统完整性"
Set-Alias -Name aii-repair -Value Repair-AIISystem -Description "修复AII工作流系统"
Set-Alias -Name aii-list -Value Get-AIITaskList -Description "列出AII工作流任务"
Set-Alias -Name aii-info -Value Get-AIITaskInfo -Description "获取AII任务信息"
Set-Alias -Name aii-stop -Value Stop-AIITask -Description "停止当前AII任务"
Set-Alias -Name aii-clean -Value Clear-AIITasks -Description "清理旧AII任务"
Set-Alias -Name aii-clear -Value Clear-AIIState -Description "清理AII工作流状态"

# 导出别名
Export-ModuleMember -Alias *