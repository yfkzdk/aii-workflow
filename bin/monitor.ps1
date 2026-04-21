# 竞品监控系统快速启动 - PowerShell版本
# 保存为: O:\AII\上下文助手\monitor.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 竞品监控系统快速启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 切换到监控系统目录
Set-Location "O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch"

Write-Host "当前目录: $(Get-Location)" -ForegroundColor Green
Write-Host ""

# 如果没有参数，显示帮助
if ($args.Count -eq 0) {
    Write-Host "使用方法:" -ForegroundColor Yellow
    Write-Host "  .\monitor.ps1 [命令]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "示例命令:" -ForegroundColor Yellow
    Write-Host "  .\monitor.ps1 `"监控抖音的产品和价格`"" -ForegroundColor Gray
    Write-Host "  .\monitor.ps1 interactive" -ForegroundColor Gray
    Write-Host "  .\monitor.ps1 status" -ForegroundColor Gray
    Write-Host "  .\monitor.ps1 results" -ForegroundColor Gray
    Write-Host "  .\monitor.ps1 test" -ForegroundColor Gray
    Write-Host "  .\monitor.ps1 examples" -ForegroundColor Gray
    Write-Host ""
    Write-Host "特殊命令:" -ForegroundColor Yellow
    Write-Host "  monitor-help   显示详细帮助" -ForegroundColor Gray
    Write-Host "  monitor-dir    切换到监控目录" -ForegroundColor Gray
    exit
}

$command = $args[0]

switch ($command) {
    "interactive" {
        Write-Host "进入交互式聊天模式..." -ForegroundColor Green
        Write-Host ""
        python chat_monitor.py --interactive
    }
    "status" {
        Write-Host "查看监控状态..." -ForegroundColor Green
        Write-Host ""
        python chat_monitor_cli.py --status
    }
    "results" {
        Write-Host "查看监控成果..." -ForegroundColor Green
        Write-Host ""
        python view_results.py
    }
    "test" {
        Write-Host "运行系统测试..." -ForegroundColor Green
        Write-Host ""
        python system_test.py
    }
    "examples" {
        Write-Host "查看使用示例..." -ForegroundColor Green
        Write-Host ""
        python chat_monitor_cli.py --examples
    }
    "monitor-help" {
        Write-Host "竞品监控系统详细帮助" -ForegroundColor Cyan
        Write-Host "========================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "常用监控命令:" -ForegroundColor Yellow
        Write-Host "  监控抖音的产品和价格" -ForegroundColor Gray
        Write-Host "  每天检查阿里云的价格变化" -ForegroundColor Gray
        Write-Host "  实时关注华为云的文档更新" -ForegroundColor Gray
        Write-Host "  高优先级监控微信小程序的版本更新" -ForegroundColor Gray
        Write-Host ""
        Write-Host "系统管理命令:" -ForegroundColor Yellow
        Write-Host "  .\monitor.ps1 status    查看监控状态" -ForegroundColor Gray
        Write-Host "  .\monitor.ps1 results   查看监控成果" -ForegroundColor Gray
        Write-Host "  .\monitor.ps1 test      运行系统测试" -ForegroundColor Gray
        Write-Host "  .\monitor.ps1 examples  查看使用示例" -ForegroundColor Gray
        Write-Host ""
        Write-Host "文件位置:" -ForegroundColor Yellow
        Write-Host "  监控系统目录: O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch" -ForegroundColor Gray
        Write-Host "  配置文件: generated_configs\chat_config_*.yaml" -ForegroundColor Gray
        Write-Host "  监控日志: logs\pipeline_trace.json" -ForegroundColor Gray
        Write-Host "  数据导出: exports\*.csv" -ForegroundColor Gray
    }
    "monitor-dir" {
        Write-Host "已切换到监控目录: O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch" -ForegroundColor Green
        Set-Location "O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch"
    }
    default {
        Write-Host "执行监控命令: $($args -join ' ')" -ForegroundColor Green
        Write-Host ""
        python chat_monitor.py --command ($args -join ' ')
    }
}