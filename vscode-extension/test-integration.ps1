# AII Workflow VS Code 扩展集成测试脚本

Write-Host "🎯 AII Workflow VS Code 扩展集成测试" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查工作流根目录
$workflowRoot = "O:\AII\上下文助手"
Write-Host "1. 检查工作流根目录..." -ForegroundColor Yellow
if (Test-Path $workflowRoot) {
    Write-Host "   ✅ 工作流根目录存在: $workflowRoot" -ForegroundColor Green
} else {
    Write-Host "   ❌ 工作流根目录不存在: $workflowRoot" -ForegroundColor Red
    exit 1
}

# 2. 检查PowerShell模块
Write-Host "2. 检查PowerShell模块..." -ForegroundColor Yellow
$modulePath = Join-Path $workflowRoot "powershell\AIIWorkflow.psd1"
if (Test-Path $modulePath) {
    Write-Host "   ✅ PowerShell模块存在: $modulePath" -ForegroundColor Green

    # 尝试导入模块
    try {
        Import-Module $modulePath -Force -ErrorAction Stop
        Write-Host "   ✅ PowerShell模块导入成功" -ForegroundColor Green

        # 检查导出的命令
        $commands = Get-Command -Module AIIWorkflow
        Write-Host "   ✅ 导出的命令数量: $($commands.Count)" -ForegroundColor Green

        # 列出主要命令
        $mainCommands = @('Get-AIIWorkflowRoot', 'Initialize-AIIWorkflow', 'Start-AIIWorkflow',
                         'New-AIITask', 'Get-AIIStatus', 'Reset-AIISystem', 'Test-AIISystem')
        foreach ($cmd in $mainCommands) {
            if ($commands.Name -contains $cmd) {
                Write-Host "      ✅ $cmd" -ForegroundColor Green
            } else {
                Write-Host "      ⚠️  $cmd (未找到)" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "   ❌ PowerShell模块导入失败: $_" -ForegroundColor Red
    }
} else {
    Write-Host "   ❌ PowerShell模块不存在: $modulePath" -ForegroundColor Red
}

# 3. 检查VS Code扩展目录
Write-Host "3. 检查VS Code扩展目录结构..." -ForegroundColor Yellow
$vscodeExtensionPath = Join-Path $workflowRoot "vscode-extension"
if (Test-Path $vscodeExtensionPath) {
    Write-Host "   ✅ VS Code扩展目录存在: $vscodeExtensionPath" -ForegroundColor Green

    # 检查关键文件
    $requiredFiles = @(
        "package.json",
        "tsconfig.json",
        "webpack.config.js",
        "src\extension.ts",
        "src\statusMonitor.ts",
        "src\taskManager.ts",
        "src\resetManager.ts",
        "src\backupManager.ts",
        "src\utils\psExecutor.ts"
    )

    $missingFiles = @()
    foreach ($file in $requiredFiles) {
        $fullPath = Join-Path $vscodeExtensionPath $file
        if (Test-Path $fullPath) {
            Write-Host "      ✅ $file" -ForegroundColor Green
        } else {
            Write-Host "      ❌ $file" -ForegroundColor Red
            $missingFiles += $file
        }
    }

    if ($missingFiles.Count -gt 0) {
        Write-Host "   ⚠️  缺少文件: $($missingFiles.Count)个" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ❌ VS Code扩展目录不存在: $vscodeExtensionPath" -ForegroundColor Red
}

# 4. 检查Node.js依赖
Write-Host "4. 检查Node.js环境..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "   ✅ Node.js版本: $nodeVersion" -ForegroundColor Green

    $npmVersion = npm --version
    Write-Host "   ✅ npm版本: $npmVersion" -ForegroundColor Green

    # 检查是否安装了TypeScript
    $tscVersion = tsc --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ TypeScript已安装" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  TypeScript未安装，需要编译扩展" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Node.js环境检查失败: $_" -ForegroundColor Red
}

# 5. 检查Webpack配置
Write-Host "5. 检查构建配置..." -ForegroundColor Yellow
$packageJsonPath = Join-Path $vscodeExtensionPath "package.json"
if (Test-Path $packageJsonPath) {
    try {
        $packageJson = Get-Content $packageJsonPath -Raw | ConvertFrom-Json
        Write-Host "   ✅ package.json解析成功" -ForegroundColor Green

        # 检查脚本
        if ($packageJson.scripts) {
            Write-Host "   ✅ 包含构建脚本:" -ForegroundColor Green
            $buildScripts = @('compile', 'watch', 'package')
            foreach ($script in $buildScripts) {
                if ($packageJson.scripts.$script) {
                    Write-Host "      ✅ $script: $($packageJson.scripts.$script)" -ForegroundColor Green
                } else {
                    Write-Host "      ⚠️  $script (未定义)" -ForegroundColor Yellow
                }
            }
        }
    } catch {
        Write-Host "   ❌ package.json解析失败: $_" -ForegroundColor Red
    }
}

# 6. 测试扩展功能
Write-Host "6. 测试扩展功能模拟..." -ForegroundColor Yellow
Write-Host "   模拟测试扩展命令:" -ForegroundColor Cyan

$testCommands = @(
    @{ Name = "启动工作流"; Command = "aii-workflow.start" },
    @{ Name = "显示控制面板"; Command = "aii-workflow.showPanel" },
    @{ Name = "创建新任务"; Command = "aii-workflow.createTask" },
    @{ Name = "查看任务列表"; Command = "aii-workflow.listTasks" },
    @{ Name = "重置系统"; Command = "aii-workflow.resetSystem" },
    @{ Name = "显示系统状态"; Command = "aii-workflow.showStatus" },
    @{ Name = "验证系统完整性"; Command = "aii-workflow.validateSystem" },
    @{ Name = "修复系统"; Command = "aii-workflow.repairSystem" },
    @{ Name = "列出系统备份"; Command = "aii-workflow.listBackups" },
    @{ Name = "备份系统"; Command = "aii-workflow.backupSystem" },
    @{ Name = "刷新"; Command = "aii-workflow.refresh" }
)

foreach ($testCmd in $testCommands) {
    Write-Host "      🔧 $($testCmd.Name) ($($testCmd.Command))" -ForegroundColor White
}

# 7. 检查配置文件
Write-Host "7. 检查配置文件..." -ForegroundColor Yellow
$configFiles = @(
    "scripts\state_machine.py",
    "scripts\workflow_utils.py",
    ".claude\CLAUDE.md",
    ".claude\agents\manifest.json",
    "ww_enhanced.py",
    "ww.bat"
)

$configErrors = 0
foreach ($configFile in $configFiles) {
    $fullPath = Join-Path $workflowRoot $configFile
    if (Test-Path $fullPath) {
        Write-Host "      ✅ $configFile" -ForegroundColor Green
    } else {
        Write-Host "      ❌ $configFile" -ForegroundColor Red
        $configErrors++
    }
}

# 8. 总结
Write-Host "`n📊 测试结果总结" -ForegroundColor Cyan
Write-Host "=================" -ForegroundColor Cyan

if ($configErrors -eq 0 -and $missingFiles.Count -eq 0) {
    Write-Host "✅ 所有测试通过！" -ForegroundColor Green
    Write-Host "   扩展已准备就绪，可以开始编译和测试。" -ForegroundColor White
} else {
    Write-Host "⚠️  测试发现一些问题：" -ForegroundColor Yellow
    if ($missingFiles.Count -gt 0) {
        Write-Host "   - 缺少VS Code扩展文件: $($missingFiles.Count)个" -ForegroundColor Yellow
    }
    if ($configErrors -gt 0) {
        Write-Host "   - 缺少配置文件: $configErrors个" -ForegroundColor Yellow
    }
    Write-Host "   请检查并修复上述问题后再继续。" -ForegroundColor White
}

# 9. 提供下一步建议
Write-Host "`n🚀 下一步建议" -ForegroundColor Cyan
Write-Host "=============" -ForegroundColor Cyan
Write-Host "1. 编译VS Code扩展:" -ForegroundColor White
Write-Host "   cd `"$vscodeExtensionPath`"" -ForegroundColor Gray
Write-Host "   npm install" -ForegroundColor Gray
Write-Host "   npm run compile" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 安装扩展:" -ForegroundColor White
Write-Host "   npm run package" -ForegroundColor Gray
Write-Host "   然后在VS Code中通过Ctrl+Shift+P → 'Extensions: Install from VSIX'安装生成的.vsix文件" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 测试扩展功能:" -ForegroundColor White
Write-Host "   - 在VS Code命令面板中输入'AII Workflow: 启动工作流'" -ForegroundColor Gray
Write-Host "   - 检查侧边栏的AII Workflow图标" -ForegroundColor Gray
Write-Host "   - 测试状态监控和任务管理功能" -ForegroundColor Gray
Write-Host ""
Write-Host "4. 开发调试:" -ForegroundColor White
Write-Host "   npm run watch  # 开发模式，自动编译" -ForegroundColor Gray
Write-Host "   按F5启动调试会话" -ForegroundColor Gray

Write-Host "`n✨ 集成测试完成！" -ForegroundColor Green