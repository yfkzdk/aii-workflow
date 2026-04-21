# 竞品监控简化脚本 - PowerShell
# 保存为: O:\AII\上下文助手\monitor_simple.ps1

# 切换到监控目录
Set-Location "O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch"

# 显示帮助
function Show-Help {
    Write-Host "竞品监控简化脚本" -ForegroundColor Green
    Write-Host "使用方法: .\monitor_simple.ps1 [命令]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "可用命令:" -ForegroundColor Cyan
    Write-Host "  monitor <命令>    - 执行监控 (例如: monitor '监控抖音的产品和价格')" -ForegroundColor Gray
    Write-Host "  results           - 查看监控成果" -ForegroundColor Gray
    Write-Host "  status            - 查看监控状态" -ForegroundColor Gray
    Write-Host "  interactive       - 进入交互模式" -ForegroundColor Gray
    Write-Host "  test              - 运行系统测试" -ForegroundColor Gray
    Write-Host "  help              - 显示此帮助" -ForegroundColor Gray
}

# 执行监控
function Run-Monitor {
    param([string]$Command)

    Write-Host "执行监控命令: $Command" -ForegroundColor Green
    python chat_monitor.py --command $Command
}

# 查看成果
function Show-Results {
    Write-Host "查看监控成果..." -ForegroundColor Green
    python check_results.py
}

# 查看状态
function Show-Status {
    Write-Host "查看监控状态..." -ForegroundColor Green
    python chat_monitor_cli.py --status
}

# 运行测试
function Run-Test {
    Write-Host "运行系统测试..." -ForegroundColor Green
    python system_test.py
}

# 主逻辑
if ($args.Count -eq 0) {
    Show-Help
    exit
}

$action = $args[0]

switch ($action) {
    "monitor" {
        if ($args.Count -lt 2) {
            Write-Host "错误: monitor命令需要参数" -ForegroundColor Red
            Write-Host "示例: .\monitor_simple.ps1 monitor '监控抖音的产品和价格'" -ForegroundColor Yellow
        } else {
            $command = $args[1..($args.Count-1)] -join ' '
            Run-Monitor -Command $command
        }
    }
    "results" {
        Show-Results
    }
    "status" {
        Show-Status
    }
    "interactive" {
        Write-Host "进入交互模式..." -ForegroundColor Green
        python chat_monitor.py --interactive
    }
    "test" {
        Run-Test
    }
    "help" {
        Show-Help
    }
    default {
        Write-Host "未知命令: $action" -ForegroundColor Red
        Show-Help
    }
}