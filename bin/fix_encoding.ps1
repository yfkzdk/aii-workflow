# 中文工作流编码修复脚本
Write-Host "正在设置UTF-8编码环境..." -ForegroundColor Yellow

# 设置输出编码
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 设置环境变量
$env:PYTHONIOENCODING = "utf-8"
$env:LANG = "zh_CN.UTF-8"
$env:LC_ALL = "zh_CN.UTF-8"

# 设置Python路径
$env:PYTHONPATH = "O:\AII\上下文助手"

Write-Host "✅ 编码环境修复完成！" -ForegroundColor Green
Write-Host "建议：将此脚本添加到PowerShell配置文件" -ForegroundColor Cyan

# 恢复原始提示符
function prompt {
    "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}
