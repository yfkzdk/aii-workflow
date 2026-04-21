# 最简单的方法 - 直接在PowerShell中运行

# 设置路径
$monitorDir = "O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch"

# 切换到监控目录
Set-Location $monitorDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "竞品监控系统 - 最简用法" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否在正确目录
if (-not (Test-Path "chat_monitor.py")) {
    Write-Host "错误: 不在监控目录中" -ForegroundColor Red
    Write-Host "请手动切换到: $monitorDir" -ForegroundColor Yellow
    exit 1
}

# 如果没有参数，显示使用说明
if ($args.Count -eq 0) {
    Write-Host "使用方法:" -ForegroundColor Green
    Write-Host "  1. 运行监控: python chat_monitor.py --command `"监控抖音的产品和价格`"" -ForegroundColor Gray
    Write-Host "  2. 查看成果: python check_results.py" -ForegroundColor Gray
    Write-Host "  3. 查看状态: python chat_monitor_cli.py --status" -ForegroundColor Gray
    Write-Host "  4. 交互模式: python chat_monitor.py --interactive" -ForegroundColor Gray
    Write-Host ""
    Write-Host "快速示例:" -ForegroundColor Green
    Write-Host "  python chat_monitor.py --command `"每天检查阿里云的价格变化`"" -ForegroundColor Gray
    Write-Host "  python chat_monitor.py --command `"监控腾讯云的API变更`"" -ForegroundColor Gray
    Write-Host "  python check_results.py" -ForegroundColor Gray
    exit
}

# 如果提供参数，直接传递给chat_monitor.py
$command = $args -join ' '
python chat_monitor.py --command $command