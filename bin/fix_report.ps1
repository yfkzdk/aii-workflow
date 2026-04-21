<#
Report Fix and Viewer Script
功能：修复乱码报告并显示清晰的分析结果
使用方法：.\fix_report.ps1 [选项]
#>

param(
    [Parameter(HelpMessage="要修复的报告文件路径")]
    [string]$ReportPath,

    [Parameter(HelpMessage="修复所有报告文件")]
    [switch]$FixAll,

    [Parameter(HelpMessage="显示修复后的内容")]
    [switch]$ShowFixed,

    [Parameter(HelpMessage="重新运行分析生成新报告")]
    [switch]$RerunAnalysis,

    [Parameter(HelpMessage="数据文件路径（仅当使用-RerunAnalysis时）")]
    [string]$DataFile = "sample_data.csv"
)

# 颜色定义
$ColorHeader = "Cyan"
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "Gray"

# 修复单个报告文件
function Fix-ReportFile {
    param([string]$FilePath)

    if (-not (Test-Path $FilePath)) {
        Write-Host "文件不存在: $FilePath" -ForegroundColor $ColorError
        return $false
    }

    Write-Host "修复报告文件: $(Split-Path $FilePath -Leaf)" -ForegroundColor $ColorHeader

    try {
        # 读取原始内容
        $content = Get-Content $FilePath -Raw

        # 常见乱码修复
        $fixes = @{
            "鉁\?" = "✓"
            "聽" = " "
            "鈥?" = "-"
            "鈥?|" = "|"
            "鈥?`"" = "`""
            # 添加更多乱码映射
        }

        foreach ($bad in $fixes.Keys) {
            $good = $fixes[$bad]
            $content = $content -replace $bad, $good
        }

        # 保存修复后的文件
        $fixedPath = $FilePath -replace '\.md$', '_fixed.md'
        $content | Out-File -FilePath $fixedPath -Encoding UTF8

        Write-Host "  ✅ 修复完成: $fixedPath" -ForegroundColor $ColorSuccess
        return $fixedPath

    } catch {
        Write-Host "  ❌ 修复失败: $_" -ForegroundColor $ColorError
        return $false
    }
}

# 显示修复后的报告
function Show-FixedReport {
    param([string]$FilePath)

    Write-Host "=== 修复后的报告内容 ===" -ForegroundColor $ColorHeader
    Write-Host "文件: $(Split-Path $FilePath -Leaf)" -ForegroundColor $ColorInfo
    Write-Host "-" * 80 -ForegroundColor $ColorInfo

    try {
        $content = Get-Content $FilePath
        $lineNum = 0

        foreach ($line in $content) {
            $lineNum++

            # 根据内容类型着色
            if ($line -match "^# ") {
                # 主标题
                Write-Host $line -ForegroundColor "Magenta"
            } elseif ($line -match "^## ") {
                # 二级标题
                Write-Host $line -ForegroundColor "Cyan"
            } elseif ($line -match "^### ") {
                # 三级标题
                Write-Host $line -ForegroundColor "Yellow"
            } elseif ($line -match "^- |^\* |^\+ ") {
                # 列表项
                if ($line -match "✓|COMPLETE|SUCCESS|完成") {
                    Write-Host "  ✓ $($line -replace '^[-*+]\s*', '')" -ForegroundColor $ColorSuccess
                } elseif ($line -match "⏳|PENDING|IN PROGRESS|进行中") {
                    Write-Host "  ⏳ $($line -replace '^[-*+]\s*', '')" -ForegroundColor $ColorWarning
                } else {
                    Write-Host "  • $($line -replace '^[-*+]\s*', '')" -ForegroundColor $ColorInfo
                }
            } elseif ($line -match "^[0-9]+\. ") {
                # 数字列表
                Write-Host $line -ForegroundColor "Green"
            } elseif ($line -match "`"|```") {
                # 代码块
                Write-Host $line -ForegroundColor "DarkGray"
            } elseif ($line -match "---|===|___") {
                # 分隔线
                Write-Host $line -ForegroundColor "DarkGray"
            } elseif ($line -match "@") {
                # 邮箱或引用
                Write-Host $line -ForegroundColor "Blue"
            } elseif ($line -match "http") {
                # 链接
                Write-Host $line -ForegroundColor "Blue"
            } else {
                # 普通文本
                Write-Host $line -ForegroundColor "White"
            }
        }

        Write-Host "-" * 80 -ForegroundColor $ColorInfo
        Write-Host ""

        # 显示文件信息
        $fileInfo = Get-Item $FilePath
        Write-Host "文件信息:" -ForegroundColor $ColorHeader
        Write-Host "  大小: $($fileInfo.Length) 字节" -ForegroundColor $ColorInfo
        Write-Host "  修改时间: $($fileInfo.LastWriteTime)" -ForegroundColor $ColorInfo
        Write-Host "  编码: UTF-8" -ForegroundColor $ColorInfo
        Write-Host ""

    } catch {
        Write-Host "读取文件失败: $_" -ForegroundColor $ColorError
    }
}

# 重新运行分析
function Rerun-Analysis {
    param([string]$DataPath)

    Write-Host "重新运行数据分析..." -ForegroundColor $ColorHeader

    if (-not (Test-Path $DataPath)) {
        Write-Host "数据文件不存在: $DataPath" -ForegroundColor $ColorError
        return $false
    }

    try {
        # 运行分析脚本
        & .\auto_analytics_simple.ps1 -DataPath $DataPath -WaitTime 30

        # 查找最新的报告
        $reportsDir = ".\output\reports"
        if (Test-Path $reportsDir) {
            $latestReport = Get-ChildItem $reportsDir -Filter "*.md" |
                           Sort-Object LastWriteTime -Descending |
                           Select-Object -First 1

            if ($latestReport) {
                Write-Host "✅ 新报告已生成: $($latestReport.Name)" -ForegroundColor $ColorSuccess
                return $latestReport.FullName
            }
        }

        Write-Host "⚠️  分析完成但未找到新报告" -ForegroundColor $ColorWarning
        return $false

    } catch {
        Write-Host "❌ 重新运行分析失败: $_" -ForegroundColor $ColorError
        return $false
    }
}

# 显示所有报告
function Show-AllReports {
    $reportsDir = ".\output\reports"

    if (-not (Test-Path $reportsDir)) {
        Write-Host "报告目录不存在: $reportsDir" -ForegroundColor $ColorWarning
        return
    }

    $reports = Get-ChildItem $reportsDir -Filter "*.md" | Sort-Object LastWriteTime -Descending

    if ($reports.Count -eq 0) {
        Write-Host "未找到任何报告文件" -ForegroundColor $ColorWarning
        return
    }

    Write-Host "=== 所有可用报告 ===" -ForegroundColor $ColorHeader
    $index = 1
    foreach ($report in $reports) {
        $status = if ($report.Name -match "_fixed") { "[已修复]" } else { "[原始]" }
        Write-Host "[$index] $status $($report.Name)" -ForegroundColor $ColorInfo
        Write-Host "    时间: $($report.LastWriteTime) | 大小: $($report.Length) 字节" -ForegroundColor $ColorInfo
        $index++
    }
    Write-Host ""
}

# 主函数
function Main {
    Write-Host "=== 报告修复与查看工具 ===" -ForegroundColor $ColorHeader
    Write-Host "版本: 1.0 | 解决乱码显示问题" -ForegroundColor $ColorInfo
    Write-Host ""

    # 显示所有报告
    Show-AllReports

    # 重新运行分析
    if ($RerunAnalysis) {
        $newReport = Rerun-Analysis -DataPath $DataFile
        if ($newReport) {
            $ReportPath = $newReport
        }
    }

    # 修复指定报告
    if ($ReportPath) {
        if ($ReportPath -eq "latest") {
            # 查找最新的报告
            $reportsDir = ".\output\reports"
            if (Test-Path $reportsDir) {
                $latest = Get-ChildItem $reportsDir -Filter "*.md" |
                         Sort-Object LastWriteTime -Descending |
                         Select-Object -First 1
                if ($latest) {
                    $ReportPath = $latest.FullName
                }
            }
        }

        $fixedPath = Fix-ReportFile -FilePath $ReportPath
        if ($fixedPath -and $ShowFixed) {
            Show-FixedReport -FilePath $fixedPath
        }
    }

    # 修复所有报告
    if ($FixAll) {
        $reportsDir = ".\output\reports"
        if (Test-Path $reportsDir) {
            $reports = Get-ChildItem $reportsDir -Filter "*.md" | Where-Object { $_.Name -notmatch "_fixed" }

            Write-Host "修复所有报告 ($($reports.Count) 个文件)..." -ForegroundColor $ColorHeader

            $fixedCount = 0
            foreach ($report in $reports) {
                if (Fix-ReportFile -FilePath $report.FullName) {
                    $fixedCount++
                }
            }

            Write-Host "✅ 修复完成: $fixedCount/$($reports.Count) 个文件" -ForegroundColor $ColorSuccess
        }
    }

    # 如果没有指定任何操作，显示帮助
    if (-not ($ReportPath -or $FixAll -or $RerunAnalysis)) {
        Write-Host "=== 使用说明 ===" -ForegroundColor $ColorHeader
        Write-Host "修复指定报告: .\fix_report.ps1 -ReportPath '报告文件.md'" -ForegroundColor $ColorInfo
        Write-Host "修复最新报告: .\fix_report.ps1 -ReportPath latest -ShowFixed" -ForegroundColor $ColorInfo
        Write-Host "修复所有报告: .\fix_report.ps1 -FixAll" -ForegroundColor $ColorInfo
        Write-Host "重新运行分析: .\fix_report.ps1 -RerunAnalysis -DataFile '数据文件.csv'" -ForegroundColor $ColorInfo
        Write-Host "显示修复内容: .\fix_report.ps1 -ReportPath '报告文件.md' -ShowFixed" -ForegroundColor $ColorInfo
        Write-Host ""
        Write-Host "示例:" -ForegroundColor $ColorHeader
        Write-Host "  .\fix_report.ps1 -ReportPath latest -ShowFixed" -ForegroundColor $ColorInfo
        Write-Host "  .\fix_report.ps1 -FixAll" -ForegroundColor $ColorInfo
        Write-Host "  .\fix_report.ps1 -RerunAnalysis -DataFile 'sample_data.csv'" -ForegroundColor $ColorInfo
    }
}

# 脚本入口
try {
    Main
} catch {
    Write-Host "脚本执行错误: $_" -ForegroundColor $ColorError
    exit 1
}