<#
Task Report Viewer Script
功能：查看自动化任务执行报告和状态
使用方法：.\view_report.ps1 [选项]
#>

param(
    [Parameter(HelpMessage="报告目录路径")]
    [string]$ReportDir = ".\output\reports",

    [Parameter(HelpMessage="显示最近N个报告")]
    [int]$RecentCount = 5,

    [Parameter(HelpMessage="打开最新的报告文件")]
    [switch]$OpenLatest,

    [Parameter(HelpMessage="显示详细执行日志")]
    [switch]$ShowLogs,

    [Parameter(HelpMessage="检查AI任务状态")]
    [switch]$CheckAIStatus
)

# 颜色定义
$ColorHeader = "Cyan"
$ColorSuccess = "Green"
$ColorInfo = "Yellow"
$ColorDetail = "Gray"

# 显示头部
function Show-Header {
    Write-Host "=== 自动化任务报告查看器 ===" -ForegroundColor $ColorHeader
    Write-Host "版本: 1.0 | 时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor $ColorDetail
    Write-Host ""
}

# 查找报告文件
function Get-ReportFiles {
    param([string]$Directory)

    if (-not (Test-Path $Directory)) {
        Write-Host "报告目录不存在: $Directory" -ForegroundColor Red
        return @()
    }

    $reports = Get-ChildItem $Directory -Filter "*.md" | Sort-Object LastWriteTime -Descending
    return $reports
}

# 显示报告摘要
function Show-ReportSummary {
    param([System.IO.FileInfo]$Report)

    Write-Host "报告: $($Report.Name)" -ForegroundColor $ColorInfo
    Write-Host "  时间: $($Report.LastWriteTime)" -ForegroundColor $ColorDetail
    Write-Host "  大小: $($Report.Length) 字节" -ForegroundColor $ColorDetail
    Write-Host "  路径: $($Report.FullName)" -ForegroundColor $ColorDetail

    # 读取报告内容摘要
    $content = Get-Content $Report.FullName -TotalCount 10
    Write-Host "  摘要:" -ForegroundColor $ColorDetail
    foreach ($line in $content) {
        if ($line -match "^#|^##|^-") {
            Write-Host "    $line" -ForegroundColor $ColorDetail
        }
    }
    Write-Host ""
}

# 显示详细报告
function Show-FullReport {
    param([System.IO.FileInfo]$Report)

    Write-Host "=== 详细报告内容 ===" -ForegroundColor $ColorHeader
    Write-Host "文件: $($Report.Name)" -ForegroundColor $ColorInfo
    Write-Host "-" * 60 -ForegroundColor $ColorDetail

    $content = Get-Content $Report.FullName
    foreach ($line in $content) {
        # 根据内容类型着色
        if ($line -match "^# ") {
            Write-Host $line -ForegroundColor "Magenta"
        } elseif ($line -match "^## ") {
            Write-Host $line -ForegroundColor "Cyan"
        } elseif ($line -match "^### ") {
            Write-Host $line -ForegroundColor "Yellow"
        } elseif ($line -match "^- |^[0-9]+\. ") {
            Write-Host $line -ForegroundColor "Green"
        } elseif ($line -match "✓|COMPLETE|SUCCESS") {
            Write-Host $line -ForegroundColor $ColorSuccess
        } elseif ($line -match "⏳|PENDING|IN PROGRESS") {
            Write-Host $line -ForegroundColor "Yellow"
        } else {
            Write-Host $line -ForegroundColor $ColorDetail
        }
    }

    Write-Host "-" * 60 -ForegroundColor $ColorDetail
    Write-Host ""
}

# 检查输出目录状态
function Check-OutputStructure {
    param([string]$ReportPath)

    $outputDir = Split-Path (Split-Path $ReportPath -Parent) -Parent
    Write-Host "=== 输出目录结构检查 ===" -ForegroundColor $ColorHeader
    Write-Host "输出目录: $outputDir" -ForegroundColor $ColorInfo

    if (-not (Test-Path $outputDir)) {
        Write-Host "  ❌ 输出目录不存在" -ForegroundColor Red
        return
    }

    $subDirs = @("reports", "charts", "data")
    foreach ($dir in $subDirs) {
        $fullPath = Join-Path $outputDir $dir
        if (Test-Path $fullPath) {
            $item = Get-Item $fullPath
            if ($item.PSIsContainer) {
                $count = (Get-ChildItem $fullPath -File).Count
                Write-Host "  ✅ $dir/ - $count 个文件" -ForegroundColor $ColorSuccess
            } else {
                Write-Host "  ⚠️  $dir - 不是目录" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  📁 $dir/ - 目录为空或不存在" -ForegroundColor Gray
        }
    }
    Write-Host ""
}

# 显示执行统计
function Show-ExecutionStats {
    $reportsDir = ".\output\reports"
    if (Test-Path $reportsDir) {
        $totalReports = (Get-ChildItem $reportsDir -Filter "*.md").Count
        $latestReport = Get-ChildItem $reportsDir -Filter "*.md" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

        Write-Host "=== 执行统计 ===" -ForegroundColor $ColorHeader
        Write-Host "总报告数量: $totalReports" -ForegroundColor $ColorInfo
        if ($latestReport) {
            Write-Host "最新报告: $($latestReport.Name)" -ForegroundColor $ColorInfo
            Write-Host "报告时间: $($latestReport.LastWriteTime)" -ForegroundColor $ColorDetail
        }
        Write-Host ""
    }
}

# 显示AI任务状态
function Show-AITaskStatus {
    Write-Host "=== AI任务状态 ===" -ForegroundColor $ColorHeader

    $tasks = @(
        @{Name="数据质量检查"; Status="已提交"; Location="Claude Code"; Action="查看详细报告"},
        @{Name="统计分析"; Status="已提交"; Location="Claude Code"; Action="查看统计结果"},
        @{Name="关键指标报告"; Status="已提交"; Location="Claude Code"; Action="查看总结"}
    )

    Write-Host "已提交的任务:" -ForegroundColor $ColorInfo
    foreach ($task in $tasks) {
        Write-Host "  • $($task.Name)" -ForegroundColor $ColorDetail
        Write-Host "    状态: $($task.Status) | 位置: $($task.Location) | 操作: $($task.Action)" -ForegroundColor $ColorDetail
    }
    Write-Host ""

    Write-Host "下一步操作建议:" -ForegroundColor $ColorInfo
    Write-Host "  1. 打开Claude Code查看详细分析结果" -ForegroundColor $ColorSuccess
    Write-Host "  2. 检查 output/charts/ 目录查看生成的图表" -ForegroundColor $ColorSuccess
    Write-Host "  3. 运行高级分析: .\auto_analytics_simple.ps1 '数据文件.csv' -AnalysisType advanced" -ForegroundColor $ColorSuccess
    Write-Host ""
}

# 主函数
function Main {
    Show-Header
    Show-ExecutionStats

    # 获取报告文件
    $reports = Get-ReportFiles -Directory $ReportDir

    if ($reports.Count -eq 0) {
        Write-Host "未找到任何报告文件" -ForegroundColor Yellow
        Write-Host "请先运行数据分析脚本: .\auto_analytics_simple.ps1 '数据文件.csv'" -ForegroundColor Green
        return
    }

    # 显示最近的报告
    Write-Host "=== 最近 $RecentCount 个报告 ===" -ForegroundColor $ColorHeader
    $recentReports = $reports | Select-Object -First $RecentCount

    $index = 1
    foreach ($report in $recentReports) {
        Write-Host "[$index] " -NoNewline -ForegroundColor $ColorInfo
        Show-ReportSummary -Report $report
        $index++
    }

    # 检查输出结构
    if ($recentReports.Count -gt 0) {
        Check-OutputStructure -ReportPath $recentReports[0].FullName
    }

    # 显示AI任务状态
    if ($CheckAIStatus) {
        Show-AITaskStatus
    }

    # 打开最新报告
    if ($OpenLatest -and $recentReports.Count -gt 0) {
        $latest = $recentReports[0]
        Write-Host "正在打开最新报告: $($latest.Name)" -ForegroundColor $ColorSuccess
        Start-Process $latest.FullName
    }

    # 显示详细日志（如果请求）
    if ($ShowLogs -and $recentReports.Count -gt 0) {
        $latest = $recentReports[0]
        Show-FullReport -Report $latest
    }

    # 显示使用提示
    Write-Host "=== 使用提示 ===" -ForegroundColor $ColorHeader
    Write-Host "打开最新报告: .\view_report.ps1 -OpenLatest" -ForegroundColor $ColorDetail
    Write-Host "查看详细内容: .\view_report.ps1 -ShowLogs" -ForegroundColor $ColorDetail
    Write-Host "检查AI状态: .\view_report.ps1 -CheckAIStatus" -ForegroundColor $ColorDetail
    Write-Host "指定报告目录: .\view_report.ps1 -ReportDir '路径'" -ForegroundColor $ColorDetail
    Write-Host ""
}

# 脚本入口
try {
    Main
} catch {
    Write-Host "脚本执行错误: $_" -ForegroundColor Red
    exit 1
}