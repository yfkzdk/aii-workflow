#!/usr/bin/env pwsh
# AII Workflow PowerShell Module - 安装脚本

param(
    [switch]$Force,
    [switch]$SkipTests,
    [string]$InstallPath
)

# 脚本信息
$ScriptName = "AII Workflow PowerShell Module Installer"
$ScriptVersion = "1.0.0"
$Author = "AII Workflow Team"
$Copyright = "(c) 2026 AII Workflow Team. All rights reserved."

# 颜色定义
$Colors = @{
    Reset = "`e[0m"
    Red = "`e[91m"
    Green = "`e[92m"
    Yellow = "`e[93m"
    Blue = "`e[94m"
    Magenta = "`e[95m"
    Cyan = "`e[96m"
    White = "`e[97m"
    Bold = "`e[1m"
}

function Write-Color {
    param(
        [string]$Message,
        [string]$Color = "White",
        [switch]$NoNewline
    )

    $colorCode = $Colors[$Color]
    if (-not $colorCode) {
        $colorCode = $Colors.White
    }

    if ($NoNewline) {
        Write-Host "$colorCode$Message" -NoNewline
    } else {
        Write-Host "$colorCode$Message"
    }
    Write-Host $Colors.Reset -NoNewline
}

function Write-Header {
    Write-Color "=========================================" -Color Cyan
    Write-Color "🚀 $ScriptName" -Color Green -NoNewline
    Write-Color " v$ScriptVersion" -Color Yellow
    Write-Color "=========================================" -Color Cyan
    Write-Host ""
}

function Write-Step {
    param(
        [string]$Step,
        [string]$Message
    )

    Write-Color "  [$Step] " -Color Blue -NoNewline
    Write-Color $Message -Color White
}

function Write-Success {
    param([string]$Message)
    Write-Color "  ✅ $Message" -Color Green
}

function Write-Warning {
    param([string]$Message)
    Write-Color "  ⚠️  $Message" -Color Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Color "  ❌ $Message" -Color Red
}

function Write-Info {
    param([string]$Message)
    Write-Color "  ℹ️  $Message" -Color Cyan
}

# 主安装函数
function Install-AIIWorkflowModule {
    Write-Header

    # 检查PowerShell版本
    Write-Step "1" "检查PowerShell版本"
    $psVersion = $PSVersionTable.PSVersion
    if ($psVersion.Major -lt 5) {
        Write-Error "需要PowerShell 5.1或更高版本，当前版本: $psVersion"
        return $false
    }
    Write-Success "PowerShell版本: $psVersion"

    # 确定安装路径
    Write-Step "2" "确定安装路径"
    if ($InstallPath) {
        $targetPath = $InstallPath
    } else {
        # 默认安装到用户模块目录
        $targetPath = Join-Path $env:USERPROFILE "Documents\WindowsPowerShell\Modules\AIIWorkflow"

        # 如果不存在，尝试Program Files路径
        if (-not (Test-Path $env:USERPROFILE)) {
            $targetPath = Join-Path $env:ProgramFiles "WindowsPowerShell\Modules\AIIWorkflow"
        }
    }

    Write-Info "安装路径: $targetPath"

    # 检查目标目录是否存在
    if (Test-Path $targetPath -and -not $Force) {
        Write-Warning "目标目录已存在: $targetPath"
        $confirmation = Read-Host "是否覆盖？(输入 'yes' 继续)"
        if ($confirmation -ne "yes") {
            Write-Error "安装已取消"
            return $false
        }
    }

    # 源目录（当前脚本所在目录的父目录）
    $scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
    $sourcePath = Join-Path $scriptDir "powershell"

    if (-not (Test-Path $sourcePath)) {
        Write-Error "源目录不存在: $sourcePath"
        Write-Info "请确保在AII工作流目录中运行此脚本"
        return $false
    }

    # 创建目标目录
    Write-Step "3" "创建目标目录"
    try {
        if (Test-Path $targetPath) {
            if ($Force) {
                Remove-Item -Path $targetPath -Recurse -Force -ErrorAction Stop
                Write-Info "已删除现有目录"
            }
        }

        New-Item -ItemType Directory -Path $targetPath -Force -ErrorAction Stop | Out-Null
        Write-Success "目录创建成功"
    } catch {
        Write-Error "创建目录失败: $_"
        return $false
    }

    # 复制文件
    Write-Step "4" "复制模块文件"
    $filesToCopy = @(
        "AIIWorkflow.psd1",
        "AIIWorkflow.psm1",
        "Modules\Core.psm1",
        "Modules\StateManager.psm1",
        "Modules\TaskManager.psm1",
        "Modules\VSCodeIntegration.psm1",
        "Modules\ResetManager.psm1"
    )

    $copySuccess = 0
    $copyFailed = 0

    foreach ($file in $filesToCopy) {
        $sourceFile = Join-Path $sourcePath $file
        $targetFile = Join-Path $targetPath $file

        try {
            # 确保目标目录存在
            $targetDir = Split-Path $targetFile -Parent
            if (-not (Test-Path $targetDir)) {
                New-Item -ItemType Directory -Path $targetDir -Force -ErrorAction Stop | Out-Null
            }

            Copy-Item -Path $sourceFile -Destination $targetFile -Force -ErrorAction Stop
            $copySuccess++
            Write-Info "复制: $file"
        } catch {
            $copyFailed++
            Write-Warning "复制失败 $file : $_"
        }
    }

    if ($copyFailed -gt 0) {
        Write-Warning "有 $copyFailed 个文件复制失败"
    }

    Write-Success "文件复制完成: $copySuccess 成功, $copyFailed 失败"

    # 创建配置文件
    Write-Step "5" "创建配置文件"
    $configPath = Join-Path $targetPath "AIIWorkflow.Config.ps1"
    $configContent = @"
# AII Workflow PowerShell模块配置
# 自动生成于 $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# 工作流根目录
`$AIIWorkflowRoot = "$scriptDir"

# 模块设置
`$AIIModuleSettings = @{
    AutoLoad = `$true
    ShowWelcome = `$true
    EnableAliases = `$true
    EnableAutoComplete = `$true
}

# 导入模块
if (`$AIIModuleSettings.AutoLoad) {
    try {
        Import-Module "$targetPath\AIIWorkflow.psd1" -Force -ErrorAction Stop
        Write-Host "✅ AII工作流模块已加载" -ForegroundColor Green

        if (`$AIIModuleSettings.ShowWelcome) {
            Show-AIIWelcome
        }
    } catch {
        Write-Warning "无法加载AII工作流模块: `$_"
    }
}

# 设置自动完成
if (`$AIIModuleSettings.EnableAutoComplete) {
    Register-ArgumentCompleter -CommandName New-AIITask -ParameterName Template -ScriptBlock {
        param(`$commandName, `$parameterName, `$wordToComplete, `$commandAst, `$fakeBoundParameters)
        @("general", "data_analysis", "code_generation", "documentation", "debugging") |
            Where-Object { `$_ -like "`$wordToComplete*" }
    }

    Register-ArgumentCompleter -CommandName New-AIITask -ParameterName Priority -ScriptBlock {
        param(`$commandName, `$parameterName, `$wordToComplete, `$commandAst, `$fakeBoundParameters)
        @("Low", "Normal", "High") |
            Where-Object { `$_ -like "`$wordToComplete*" }
    }
}

# 添加到PATH（可选）
# `$env:Path = "`$scriptDir;`$env:Path"

Write-Host "🎉 AII工作流PowerShell模块安装完成" -ForegroundColor Green
Write-Host "   使用 'Get-Command -Module AIIWorkflow' 查看所有命令" -ForegroundColor White
Write-Host "   使用 'Get-Help New-AIITask' 查看命令帮助" -ForegroundColor White
Write-Host "   使用 'aii-start `"任务描述`"' 快速启动任务" -ForegroundColor White
"@

    try {
        Set-Content -Path $configPath -Value $configContent -Encoding UTF8
        Write-Success "配置文件创建成功: $configPath"
    } catch {
        Write-Error "创建配置文件失败: $_"
    }

    # 创建配置文件快捷方式
    Write-Step "6" "创建配置文件快捷方式"
    $profilePath = $PROFILE.CurrentUserAllHosts
    $profileDir = Split-Path $profilePath -Parent

    if (-not (Test-Path $profileDir)) {
        try {
            New-Item -ItemType Directory -Path $profileDir -Force -ErrorAction Stop | Out-Null
            Write-Info "创建PowerShell配置目录"
        } catch {
            Write-Warning "无法创建配置目录: $_"
        }
    }

    if (Test-Path $profilePath) {
        # 检查是否已包含配置
        $profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
        if ($profileContent -and $profileContent.Contains("AIIWorkflow.Config.ps1")) {
            Write-Info "配置文件已包含AII工作流设置"
        } else {
            # 添加配置引用
            $configLine = ". `"$configPath`""
            try {
                Add-Content -Path $profilePath -Value "`n# AII Workflow Module`n$configLine" -Encoding UTF8
                Write-Success "已将AII工作流配置添加到PowerShell配置文件"
            } catch {
                Write-Warning "无法添加到配置文件: $_"
                Write-Info "请手动添加以下行到 $profilePath :"
                Write-Color "  . `"$configPath`"" -Color Yellow
            }
        }
    } else {
        # 创建新的配置文件
        try {
            $profileContent = @"
# PowerShell配置文件
# 生成于 $(Get-Date -Format "yyyy-MM-dd")

# AII Workflow Module
. "$configPath"
"@
            Set-Content -Path $profilePath -Value $profileContent -Encoding UTF8
            Write-Success "已创建PowerShell配置文件并添加AII工作流设置"
        } catch {
            Write-Warning "无法创建配置文件: $_"
            Write-Info "请手动创建 $profilePath 并添加以下内容:"
            Write-Color "  . `"$configPath`"" -Color Yellow
        }
    }

    # 运行测试（可选）
    if (-not $SkipTests) {
        Write-Step "7" "运行安装测试"
        $testResult = Test-AIIWorkflowInstallation -InstallPath $targetPath -SourcePath $sourcePath
        if ($testResult.Success) {
            Write-Success "安装测试通过"
        } else {
            Write-Warning "安装测试发现问题: $($testResult.Message)"
        }
    }

    # 显示完成信息
    Write-Host ""
    Write-Color "=========================================" -Color Cyan
    Write-Color "🎉 安装完成！" -Color Green
    Write-Color "=========================================" -Color Cyan
    Write-Host ""
    Write-Color "模块已安装到:" -Color White
    Write-Color "  $targetPath" -Color Yellow
    Write-Host ""
    Write-Color "使用方法:" -Color White
    Write-Color "  1. 重新启动PowerShell或运行: . `"$configPath`"" -Color Cyan
    Write-Color "  2. 使用命令: Get-Command -Module AIIWorkflow" -Color Cyan
    Write-Color "  3. 查看帮助: Get-Help New-AIITask" -Color Cyan
    Write-Color "  4. 快速开始: aii-start `"你的任务描述`"" -Color Cyan
    Write-Host ""
    Write-Color "常用命令别名:" -Color White
    Write-Color "  aii-start  = New-AIITask" -Color Cyan
    Write-Color "  aii-status = Get-AIIStatus" -Color Cyan
    Write-Color "  aii-resume = Resume-AIITask" -Color Cyan
    Write-Color "  aii-reset  = Reset-AIISystem" -Color Cyan
    Write-Color "  aii-vscode = Open-AIIInVSCode" -Color Cyan
    Write-Host ""

    return $true
}

# 测试函数
function Test-AIIWorkflowInstallation {
    param(
        [string]$InstallPath,
        [string]$SourcePath
    )

    $tests = @()
    $passed = 0
    $failed = 0

    # 测试1: 检查模块文件
    $test1 = @{
        Name = "检查模块文件"
        Status = "失败"
        Message = ""
    }

    $requiredFiles = @(
        "AIIWorkflow.psd1",
        "AIIWorkflow.psm1",
        "Modules\Core.psm1",
        "Modules\StateManager.psm1",
        "Modules\TaskManager.psm1",
        "Modules\VSCodeIntegration.psm1",
        "Modules\ResetManager.psm1"
    )

    $missingFiles = @()
    foreach ($file in $requiredFiles) {
        $fullPath = Join-Path $InstallPath $file
        if (-not (Test-Path $fullPath)) {
            $missingFiles += $file
        }
    }

    if ($missingFiles.Count -eq 0) {
        $test1.Status = "通过"
        $test1.Message = "所有模块文件都存在"
        $passed++
    } else {
        $test1.Message = "缺失文件: $($missingFiles -join ', ')"
        $failed++
    }
    $tests += $test1

    # 测试2: 检查模块清单
    $test2 = @{
        Name = "检查模块清单"
        Status = "失败"
        Message = ""
    }

    $manifestPath = Join-Path $InstallPath "AIIWorkflow.psd1"
    if (Test-Path $manifestPath) {
        try {
            $manifest = Import-PowerShellDataFile -Path $manifestPath -ErrorAction Stop
            if ($manifest.ModuleVersion -and $manifest.GUID) {
                $test2.Status = "通过"
                $test2.Message = "模块清单有效"
                $passed++
            } else {
                $test2.Message = "模块清单缺少必要信息"
                $failed++
            }
        } catch {
            $test2.Message = "无法解析模块清单: $_"
            $failed++
        }
    } else {
        $test2.Message = "模块清单不存在"
        $failed++
    }
    $tests += $test2

    # 测试3: 尝试导入模块
    $test3 = @{
        Name = "测试模块导入"
        Status = "失败"
        Message = ""
    }

    try {
        Import-Module $InstallPath -Force -ErrorAction Stop
        $module = Get-Module -Name AIIWorkflow -ErrorAction SilentlyContinue
        if ($module) {
            $test3.Status = "通过"
            $test3.Message = "模块导入成功，版本: $($module.Version)"
            $passed++

            # 测试基本功能
            $commands = Get-Command -Module AIIWorkflow -ErrorAction SilentlyContinue
            if ($commands) {
                $test3.Message += ", $($commands.Count) 个命令可用"
            }

            # 移除模块
            Remove-Module -Name AIIWorkflow -ErrorAction SilentlyContinue
        } else {
            $test3.Message = "模块导入后未找到"
            $failed++
        }
    } catch {
        $test3.Message = "模块导入失败: $_"
        $failed++
    }
    $tests += $test3

    # 显示测试结果
    Write-Host ""
    Write-Color "安装测试结果:" -Color Cyan
    foreach ($test in $tests) {
        $color = if ($test.Status -eq "通过") { "Green" } else { "Red" }
        Write-Color "  [$($test.Status)] $($test.Name)" -Color $color
        if ($test.Message) {
            Write-Color "      $($test.Message)" -Color "White"
        }
    }

    Write-Host ""
    Write-Color "测试摘要:" -Color Cyan
    Write-Color "  通过: $passed" -Color Green
    Write-Color "  失败: $failed" -Color $($failed -gt 0 ? "Red" : "White")

    return @{
        Success = $failed -eq 0
        Tests = $tests
        Passed = $passed
        Failed = $failed
        Message = if ($failed -eq 0) { "所有测试通过" } else { "$failed 个测试失败" }
    }
}

# 卸载函数
function Uninstall-AIIWorkflowModule {
    param(
        [switch]$Force,
        [string]$InstallPath
    )

    Write-Header
    Write-Color "卸载 AII Workflow PowerShell 模块" -Color Yellow
    Write-Host ""

    # 确定安装路径
    if (-not $InstallPath) {
        # 尝试查找模块
        $module = Get-Module -Name AIIWorkflow -ErrorAction SilentlyContinue
        if ($module) {
            $InstallPath = $module.ModuleBase
        } else {
            # 默认路径
            $InstallPath = Join-Path $env:USERPROFILE "Documents\WindowsPowerShell\Modules\AIIWorkflow"
            if (-not (Test-Path $InstallPath)) {
                $InstallPath = Join-Path $env:ProgramFiles "WindowsPowerShell\Modules\AIIWorkflow"
            }
        }
    }

    if (-not (Test-Path $InstallPath)) {
        Write-Error "未找到AII工作流模块安装路径: $InstallPath"
        return $false
    }

    Write-Info "安装路径: $InstallPath"

    if (-not $Force) {
        $confirmation = Read-Host "确认卸载？这将删除整个目录。 (输入 'yes' 继续)"
        if ($confirmation -ne "yes") {
            Write-Error "卸载已取消"
            return $false
        }
    }

    try {
        # 从配置文件中移除引用
        $profilePath = $PROFILE.CurrentUserAllHosts
        if (Test-Path $profilePath) {
            $content = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
            if ($content) {
                # 移除AII工作流配置行
                $lines = $content -split "`n" | Where-Object {
                    $_ -notmatch "AIIWorkflow.Config.ps1" -and
                    $_ -notmatch "# AII Workflow Module"
                }
                $newContent = $lines -join "`n"
                Set-Content -Path $profilePath -Value $newContent -Encoding UTF8
                Write-Info "已从配置文件中移除AII工作流设置"
            }
        }

        # 删除模块目录
        Remove-Item -Path $InstallPath -Recurse -Force -ErrorAction Stop
        Write-Success "已删除模块目录: $InstallPath"

        # 尝试移除模块（如果已加载）
        Remove-Module -Name AIIWorkflow -ErrorAction SilentlyContinue
        Write-Info "已尝试从内存中移除模块"

        Write-Host ""
        Write-Color "✅ 卸载完成" -Color Green
        Write-Color "AII工作流PowerShell模块已成功卸载" -Color White

        return $true

    } catch {
        Write-Error "卸载失败: $_"
        return $false
    }
}

# 显示帮助
function Show-Help {
    Write-Header
    Write-Color "使用方法:" -Color White
    Write-Host ""
    Write-Color "安装模块:" -Color Cyan
    Write-Color "  .\install.ps1" -Color Yellow
    Write-Color "  .\install.ps1 -Force" -Color Yellow
    Write-Color "  .\install.ps1 -InstallPath C:\MyModules" -Color Yellow
    Write-Host ""
    Write-Color "卸载模块:" -Color Cyan
    Write-Color "  .\install.ps1 -Uninstall" -Color Yellow
    Write-Color "  .\install.ps1 -Uninstall -Force" -Color Yellow
    Write-Host ""
    Write-Color "参数:" -Color White
    Write-Color "  -Force          强制覆盖现有安装" -Color Cyan
    Write-Color "  -SkipTests      跳过安装测试" -Color Cyan
    Write-Color "  -InstallPath    指定安装路径" -Color Cyan
    Write-Color "  -Uninstall      卸载模块" -Color Cyan
    Write-Color "  -Help           显示此帮助" -Color Cyan
    Write-Host ""
    Write-Color "示例:" -Color White
    Write-Color "  # 安装到默认位置" -Color Yellow
    Write-Color "  .\install.ps1" -Color Green
    Write-Host ""
    Write-Color "  # 强制安装到指定位置" -Color Yellow
    Write-Color "  .\install.ps1 -Force -InstallPath C:\PowerShell\Modules" -Color Green
    Write-Host ""
    Write-Color "  # 卸载模块" -Color Yellow
    Write-Color "  .\install.ps1 -Uninstall" -Color Green
}

# 主脚本逻辑
if ($Help) {
    Show-Help
    exit 0
}

if ($Uninstall) {
    $result = Uninstall-AIIWorkflowModule -Force:$Force -InstallPath $InstallPath
    exit $(if ($result) { 0 } else { 1 })
}

# 安装模块
$result = Install-AIIWorkflowModule
exit $(if ($result) { 0 } else { 1 })