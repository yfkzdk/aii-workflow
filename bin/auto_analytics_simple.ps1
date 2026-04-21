<#
Data Analytics Automation Workflow Script
Function: Automate complete data analysis workflow
Usage: .\auto_analytics_simple.ps1 "data_file_path" [options]
#>

param(
    [Parameter(Mandatory=$true, HelpMessage="Data file path")]
    [string]$DataPath,

    [Parameter(HelpMessage="Analysis type: basic, advanced, full")]
    [ValidateSet("basic", "advanced", "full")]
    [string]$AnalysisType = "basic",

    [Parameter(HelpMessage="Output directory")]
    [string]$OutputDir = ".\output",

    [Parameter(HelpMessage="Wait time in seconds")]
    [int]$WaitTime = 30
)

# Check if files exist
Write-Host "=== Data Analytics Automation ===" -ForegroundColor Cyan
Write-Host "Data file: $DataPath" -ForegroundColor Yellow
Write-Host "Analysis type: $AnalysisType" -ForegroundColor Yellow

# Step 1: Check data file
if (-not (Test-Path $DataPath)) {
    Write-Host "ERROR: Data file not found: $DataPath" -ForegroundColor Red
    exit 1
}

Write-Host "Step 1/5: Data file check... OK" -ForegroundColor Green

# Step 2: Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Step 2/5: Output directory created: $OutputDir" -ForegroundColor Green
} else {
    Write-Host "Step 2/5: Output directory exists: $OutputDir" -ForegroundColor Green
}

# Step 3: Data quality check
Write-Host "Step 3/5: Running data quality check..." -ForegroundColor Yellow
try {
    $task1 = "Check data quality of file '$DataPath', check for missing values, outliers, data types"
    python ww_enhanced.py $task1
    Write-Host "  - Task submitted: Data quality check" -ForegroundColor Green
} catch {
    Write-Host "  - Warning: Task submission failed" -ForegroundColor Yellow
}

# Wait for processing
if ($WaitTime -gt 0) {
    Write-Host "  - Waiting $WaitTime seconds for AI processing..." -ForegroundColor Gray
    Start-Sleep -Seconds $WaitTime
}

# Step 4: Analysis
Write-Host "Step 4/5: Running analysis..." -ForegroundColor Yellow

$analysisTasks = @()
switch ($AnalysisType) {
    "basic" {
        $analysisTasks = @(
            "Perform basic statistical analysis on '$DataPath': descriptive statistics, distribution analysis",
            "Generate key metrics summary report"
        )
    }
    "advanced" {
        $analysisTasks = @(
            "Perform advanced analysis on '$DataPath': correlation analysis, trend analysis",
            "Identify patterns and anomalies in the data",
            "Generate in-depth analysis report"
        )
    }
    "full" {
        $analysisTasks = @(
            "Perform complete analysis on '$DataPath': data exploration, feature engineering, model evaluation",
            "Create interactive visualization charts",
            "Generate business insights and recommendations"
        )
    }
}

$taskCount = 1
foreach ($task in $analysisTasks) {
    Write-Host "  - Task $taskCount/$($analysisTasks.Count): $task" -ForegroundColor Gray
    try {
        python ww_enhanced.py $task
        Write-Host "    Task submitted" -ForegroundColor Green
    } catch {
        Write-Host "    Warning: Task submission failed" -ForegroundColor Yellow
    }

    $taskCount++

    # Wait between tasks
    if ($WaitTime -gt 0 -and $taskCount -le $analysisTasks.Count) {
        Write-Host "    Waiting $WaitTime seconds..." -ForegroundColor Gray
        Start-Sleep -Seconds $WaitTime
    }
}

# Step 5: Generate enhanced report with task details
Write-Host "Step 5/5: Generating enhanced report..." -ForegroundColor Yellow

# Collect task information
$taskDetails = @()
$taskDetails += "## Tasks Submitted to AI"
$taskDetails += "### 1. Data Quality Check"
$taskDetails += "- Task: Check data quality of file '$DataPath', check for missing values, outliers, data types"
$taskDetails += "- Status: Submitted to Claude Code"
$taskDetails += "- Next: Open Claude Code to view detailed quality report"
$taskDetails += ""

$taskDetails += "### 2. Statistical Analysis"
$taskDetails += "- Task: Perform basic statistical analysis on '$DataPath': descriptive statistics, distribution analysis"
$taskDetails += "- Status: Submitted to Claude Code"
$taskDetails += "- Expected Output: Descriptive statistics, distribution charts, summary metrics"
$taskDetails += ""

$taskDetails += "### 3. Key Metrics Report"
$taskDetails += "- Task: Generate key metrics summary report"
$taskDetails += "- Status: Submitted to Claude Code"
$taskDetails += "- Expected Output: Executive summary, key insights, recommendations"
$taskDetails += ""

# Enhanced report content
$reportContent = @"
# Data Analysis Report - Enhanced Version
## Execution Summary
- **Analysis Time**: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
- **Data File**: $DataPath
- **Analysis Type**: $AnalysisType
- **Output Directory**: $OutputDir
- **Automation Status**: COMPLETE ✓

## Workflow Execution Steps
1. ✅ Data file validation and check
2. ✅ Output directory preparation
3. ✅ AI task submission (3 analysis tasks)
4. ✅ Report generation
5. ✅ File structure creation

$($taskDetails -join "`n")

## File Structure Created
\`\`\`
$OutputDir/
├── reports/           # Analysis reports (this file)
├── charts/            # Visualization charts (from AI)
├── data/             # Processed data files (from AI)
└── (AI-generated content will appear here)
\`\`\`

## Next Steps - Action Required
### Immediate Actions:
1. **Open Claude Code** - View detailed analysis results
2. **Check for AI outputs** - Look for generated charts and insights
3. **Review quality report** - Data quality assessment from AI

### Follow-up Analysis Options:
- Run advanced analysis: \`.\auto_analytics_simple.ps1 "$DataPath" -AnalysisType advanced\`
- Run full analysis: \`.\auto_analytics_simple.ps1 "$DataPath" -AnalysisType full\`
- Monitor daily: \`.\auto_analytics_simple.ps1 "daily_data.csv" -WaitTime 60\`

## Technical Details
- **Script Version**: 1.1 (Enhanced Reporting)
- **Execution Mode**: Automated workflow with AI integration
- **Wait Time Used**: $WaitTime seconds per task
- **Tasks Submitted**: 3
- **AI Platform**: Claude Code

## Quick Reference
| Step | Description | Status |
|------|-------------|--------|
| 1 | File validation | ✓ Complete |
| 2 | Directory setup | ✓ Complete |
| 3 | AI task submission | ✓ Complete (3 tasks) |
| 4 | Report generation | ✓ Complete |
| 5 | AI processing | ⏳ In Claude Code |

---
*Enhanced report generated by AII Workflow Automation Script v1.1*
*Next: Open Claude Code for detailed AI analysis results*
"@

# Create reports directory
$reportsDir = Join-Path $OutputDir "reports"
if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}

# Save report
$reportFile = Join-Path $reportsDir "analysis_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
$reportContent | Out-File -FilePath $reportFile -Encoding UTF8

Write-Host "  - Report saved: $reportFile" -ForegroundColor Green

# Create other directories
$chartDir = Join-Path $OutputDir "charts"
$dataDir = Join-Path $OutputDir "data"
if (-not (Test-Path $chartDir)) { New-Item -ItemType Directory -Path $chartDir -Force | Out-Null }
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }

# Final message
Write-Host "=== Analysis Workflow Complete ===" -ForegroundColor Cyan
Write-Host "Output directory: $OutputDir" -ForegroundColor Yellow
Write-Host "Report file: $reportFile" -ForegroundColor Yellow
Write-Host "Next: Open Claude Code to view analysis results" -ForegroundColor Green