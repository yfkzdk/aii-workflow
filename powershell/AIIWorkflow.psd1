@{
    RootModule = 'AIIWorkflow.psm1'
    ModuleVersion = '1.0.0'
    GUID = 'a8e3f6c2-1b47-4a9d-9f5c-7d2b8c1e3f4a'
    Author = 'AII Workflow Team'
    CompanyName = 'AII'
    Copyright = '(c) 2026 AII Workflow Team. All rights reserved.'
    Description = 'AII工作流系统的PowerShell管理模块'
    PowerShellVersion = '5.1'
    DotNetFrameworkVersion = '4.7.2'

    # 要导入的嵌套模块
    NestedModules = @(
        'Modules\Core.psm1',
        'Modules\StateManager.psm1',
        'Modules\TaskManager.psm1',
        'Modules\VSCodeIntegration.psm1',
        'Modules\ResetManager.psm1'
    )

    # 要从此模块导出的函数
    FunctionsToExport = @(
        'New-AIITask',
        'Get-AIIStatus',
        'Resume-AIITask',
        'Reset-AIISystem',
        'Show-AIIPanel',
        'Stop-AIITask',
        'Get-AIIHistory',
        'Clear-AIICache',
        'Test-AIIConnection',
        'Invoke-AIISync',
        'Export-AIIReport',
        'Import-AIIConfig'
    )

    # 要导出的Cmdlets
    CmdletsToExport = @()

    # 要导出的变量
    VariablesToExport = @(
        '$AIIConfig',
        '$AIIWorkflowRoot',
        '$AIIState'
    )

    # 要导出的别名
    AliasesToExport = @(
        'aii-start',
        'aii-status',
        'aii-resume',
        'aii-reset',
        'aii-panel'
    )

    PrivateData = @{
        PSData = @{
            Tags = @('AII', 'Workflow', 'Automation', 'Claude', 'AI')
            LicenseUri = 'https://opensource.org/licenses/MIT'
            ProjectUri = 'https://github.com/AII-Workflow/PowerShellModule'
            IconUri = ''
            ReleaseNotes = @'
## 1.0.0 - 初始发布
### 新增功能
- 支持通过PowerShell启动AII工作流任务
- 提供状态管理和系统重置功能
- 集成VS Code扩展启动功能
- 支持一键冷启动重置
- 提供全面的任务历史管理
'@
        }
    }
}