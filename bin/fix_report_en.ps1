<#
Report Fix and Viewer Script (English Version)
Function: Fix garbled reports and display analysis results
Usage: .\fix_report_en.ps1 [options]
#>

param(
    [Parameter(HelpMessage="Report file path to fix")]
    [string]$ReportPath,

    [Parameter(HelpMessage="Fix all report files")]
    [switch]$FixAll,

    [Parameter(HelpMessage="Show fixed content")]
    [switch]$ShowFixed,

    [Parameter(HelpMessage="Re-run analysis to generate new report")]
    [switch]$RerunAnalysis,

    [Parameter(HelpMessage="Data file path (only with -RerunAnalysis)")]
    [string]$DataFile = "sample_data.csv"
)

# Color definitions
$ColorHeader = "Cyan"
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "Gray"

# Fix single report file
function Fix-ReportFile {
    param([string]$FilePath)

    if (-not (Test-Path $FilePath)) {
        Write-Host "File not found: $FilePath" -ForegroundColor $ColorError
        return $false
    }

    Write-Host "Fixing report: $(Split-Path $FilePath -Leaf)" -ForegroundColor $ColorHeader

    try {
        # Read original content
        $content = Get-Content $FilePath -Raw

        # Common garbled character fixes
        $fixes = @{
            "鉁\?" = "✓"
            # Add more mappings as needed
        }

        foreach ($bad in $fixes.Keys) {
            $good = $fixes[$bad]
            $content = $content -replace $bad, $good
        }

        # Save fixed file
        $fixedPath = $FilePath -replace '\.md$', '_fixed.md'
        $content | Out-File -FilePath $fixedPath -Encoding UTF8

        Write-Host "  ✓ Fixed: $fixedPath" -ForegroundColor $ColorSuccess
        return $fixedPath

    } catch {
        Write-Host "  ✗ Fix failed: $_" -ForegroundColor $ColorError
        return $false
    }
}

# Show fixed report
function Show-FixedReport {
    param([string]$FilePath)

    Write-Host "=== Fixed Report Content ===" -ForegroundColor $ColorHeader
    Write-Host "File: $(Split-Path $FilePath -Leaf)" -ForegroundColor $ColorInfo
    Write-Host "-" * 80 -ForegroundColor $ColorInfo

    try {
        $content = Get-Content $FilePath

        foreach ($line in $content) {
            # Color coding by content type
            if ($line -match "^# ") {
                # Main title
                Write-Host $line -ForegroundColor "Magenta"
            } elseif ($line -match "^## ") {
                # Section title
                Write-Host $line -ForegroundColor "Cyan"
            } elseif ($line -match "^### ") {
                # Subsection title
                Write-Host $line -ForegroundColor "Yellow"
            } elseif ($line -match "^- |^\* |^\+ ") {
                # List items
                if ($line -match "✓|COMPLETE|SUCCESS") {
                    Write-Host "  ✓ $($line -replace '^[-*+]\s*', '')" -ForegroundColor $ColorSuccess
                } elseif ($line -match "⏳|PENDING|IN PROGRESS") {
                    Write-Host "  ⏳ $($line -replace '^[-*+]\s*', '')" -ForegroundColor $ColorWarning
                } else {
                    Write-Host "  • $($line -replace '^[-*+]\s*', '')" -ForegroundColor $ColorInfo
                }
            } elseif ($line -match "^[0-9]+\. ") {
                # Numbered list
                Write-Host $line -ForegroundColor "Green"
            } elseif ($line -match "`"|```") {
                # Code blocks
                Write-Host $line -ForegroundColor "DarkGray"
            } else {
                # Normal text
                Write-Host $line -ForegroundColor "White"
            }
        }

        Write-Host "-" * 80 -ForegroundColor $ColorInfo
        Write-Host ""

        # Show file info
        $fileInfo = Get-Item $FilePath
        Write-Host "File Info:" -ForegroundColor $ColorHeader
        Write-Host "  Size: $($fileInfo.Length) bytes" -ForegroundColor $ColorInfo
        Write-Host "  Modified: $($fileInfo.LastWriteTime)" -ForegroundColor $ColorInfo
        Write-Host "  Encoding: UTF-8" -ForegroundColor $ColorInfo
        Write-Host ""

    } catch {
        Write-Host "Failed to read file: $_" -ForegroundColor $ColorError
    }
}

# Show all reports
function Show-AllReports {
    $reportsDir = ".\output\reports"

    if (-not (Test-Path $reportsDir)) {
        Write-Host "Report directory not found: $reportsDir" -ForegroundColor $ColorWarning
        return
    }

    $reports = Get-ChildItem $reportsDir -Filter "*.md" | Sort-Object LastWriteTime -Descending

    if ($reports.Count -eq 0) {
        Write-Host "No report files found" -ForegroundColor $ColorWarning
        return
    }

    Write-Host "=== Available Reports ===" -ForegroundColor $ColorHeader
    $index = 1
    foreach ($report in $reports) {
        $status = if ($report.Name -match "_fixed") { "[Fixed]" } else { "[Original]" }
        Write-Host "[$index] $status $($report.Name)" -ForegroundColor $ColorInfo
        Write-Host "    Time: $($report.LastWriteTime) | Size: $($report.Length) bytes" -ForegroundColor $ColorInfo
        $index++
    }
    Write-Host ""
}

# Main function
function Main {
    Write-Host "=== Report Fix Tool ===" -ForegroundColor $ColorHeader
    Write-Host "Version: 1.0 | Fix garbled characters" -ForegroundColor $ColorInfo
    Write-Host ""

    # Show all reports
    Show-AllReports

    # Fix specified report
    if ($ReportPath) {
        if ($ReportPath -eq "latest") {
            # Find latest report
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

    # Fix all reports
    if ($FixAll) {
        $reportsDir = ".\output\reports"
        if (Test-Path $reportsDir) {
            $reports = Get-ChildItem $reportsDir -Filter "*.md" | Where-Object { $_.Name -notmatch "_fixed" }

            Write-Host "Fixing all reports ($($reports.Count) files)..." -ForegroundColor $ColorHeader

            $fixedCount = 0
            foreach ($report in $reports) {
                if (Fix-ReportFile -FilePath $report.FullName) {
                    $fixedCount++
                }
            }

            Write-Host "✓ Fixed: $fixedCount/$($reports.Count) files" -ForegroundColor $ColorSuccess
        }
    }

    # Show usage if no action specified
    if (-not ($ReportPath -or $FixAll -or $RerunAnalysis)) {
        Write-Host "=== Usage ===" -ForegroundColor $ColorHeader
        Write-Host "Fix specific report: .\fix_report_en.ps1 -ReportPath 'report.md'" -ForegroundColor $ColorInfo
        Write-Host "Fix latest report: .\fix_report_en.ps1 -ReportPath latest -ShowFixed" -ForegroundColor $ColorInfo
        Write-Host "Fix all reports: .\fix_report_en.ps1 -FixAll" -ForegroundColor $ColorInfo
        Write-Host "Show fixed content: .\fix_report_en.ps1 -ReportPath 'report.md' -ShowFixed" -ForegroundColor $ColorInfo
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor $ColorHeader
        Write-Host "  .\fix_report_en.ps1 -ReportPath latest -ShowFixed" -ForegroundColor $ColorInfo
        Write-Host "  .\fix_report_en.ps1 -FixAll" -ForegroundColor $ColorInfo
    }
}

# Script entry
try {
    Main
} catch {
    Write-Host "Script error: $_" -ForegroundColor $ColorError
    exit 1
}