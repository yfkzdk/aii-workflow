# 数据分析自动化脚本使用指南

## 🚀 快速开始

### 1. 基本用法
```powershell
# 基础分析
.\auto_analytics.ps1 "C:\data\your_data.csv"

# 高级分析
.\auto_analytics.ps1 "C:\data\your_data.csv" -AnalysisType advanced

# 完整分析
.\auto_analytics.ps1 "C:\data\your_data.csv" -AnalysisType full -OutputDir ".\reports"
```

### 2. 完整参数说明
```powershell
.\auto_analytics.ps1
    -DataPath "数据文件路径"       # 必需：CSV、Excel、JSON等数据文件
    [-AnalysisType basic]          # 可选：basic | advanced | full
    [-OutputDir ".\output"]        # 可选：输出目录
    [-WaitTime 30]                # 可选：每个步骤等待时间（秒）
    [-Verbose]                    # 可选：详细输出
```

## 📊 支持的格式
- CSV文件 (.csv)
- Excel文件 (.xlsx, .xls)
- JSON文件 (.json)
- 文本文件 (.txt)
- Parquet文件 (.parquet)

## 🔧 功能特点

### 自动化流程
1. ✅ **数据质量检查** - 自动检测缺失值、异常值
2. ✅ **基础统计分析** - 描述性统计、分布分析
3. ✅ **高级分析** - 相关性、趋势、模式识别
4. ✅ **可视化生成** - 自动创建图表
5. ✅ **报告生成** - 完整的分析报告

### 进度监控
- 实时进度条显示
- 详细日志记录
- 错误自动处理
- 失败重试机制

### 输出管理
- 自动创建目录结构
- 时间戳文件命名
- 报告自动打开

## 📁 输出目录结构
```
output/
├── reports/      # 分析报告
├── charts/       # 可视化图表
├── data/         # 处理后的数据
└── logs/         # 执行日志
```

## 🎯 使用示例

### 示例1：快速数据分析
```powershell
# 分析销售数据
.\auto_analytics.ps1 "D:\sales_data_2024.csv" -WaitTime 45
```

### 示例2：批量处理
```powershell
# 批量分析多个文件
$files = Get-ChildItem "C:\data\*.csv"
foreach ($file in $files) {
    .\auto_analytics.ps1 $file.FullName -OutputDir ".\output\$($file.BaseName)"
}
```

### 示例3：定时任务
```powershell
# Windows任务计划程序
# 每天9点自动分析最新数据
$dataFile = "\\server\data\daily_export.csv"
$outputDir = "C:\reports\daily_$(Get-Date -Format 'yyyyMMdd')"
.\auto_analytics.ps1 $dataFile -OutputDir $outputDir -AnalysisType advanced
```

## 🔍 高级功能

### 自定义等待时间
```powershell
# 复杂分析需要更多时间
.\auto_analytics.ps1 "large_dataset.csv" -WaitTime 120
```

### 详细输出模式
```powershell
# 查看详细执行过程
.\auto_analytics.ps1 "data.csv" -Verbose
```

### 集成到现有工作流
```powershell
# 作为更大流程的一部分
function Run-AnalyticsPipeline {
    param($DataPath)
    
    # 1. 数据预处理
    .\auto_analytics.ps1 $DataPath -AnalysisType basic
    
    # 2. 深度分析
    .\auto_analytics.ps1 $DataPath -AnalysisType advanced
    
    # 3. 生成总结报告
    # ... 自定义逻辑
}
```

## ⚠️ 注意事项

### 执行权限
```powershell
# 首次运行可能需要设置执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 文件路径
- 使用完整路径或相对路径
- 避免路径中的空格和特殊字符
- 确保有读取权限

### 资源使用
- 大文件需要更多等待时间
- 复杂分析可能需要更长时间
- 监控内存和CPU使用

## 🔄 故障排除

### 常见问题
1. **权限错误**
   ```powershell
   # 以管理员身份运行PowerShell
   Start-Process PowerShell -Verb RunAs
   ```

2. **文件不存在**
   ```powershell
   # 检查文件路径
   Test-Path "your_data.csv"
   ```

3. **执行策略限制**
   ```powershell
   # 临时允许脚本执行
   powershell -ExecutionPolicy Bypass -File .\auto_analytics.ps1 "data.csv"
   ```

### 查看日志
```powershell
# 查看执行日志
Get-Content ".\logs\analytics_$(Get-Date -Format 'yyyyMMdd').log"

# 查看错误详情
$Error[0] | Format-List -Force
```

## 📈 最佳实践

### 数据准备
1. **清理数据** - 删除无关列，处理缺失值
2. **格式标准化** - 统一日期、数字格式
3. **备份原始数据** - 处理前先备份

### 执行策略
1. **先小后大** - 先用小数据集测试
2. **逐步增加** - 逐步增加分析复杂度
3. **监控进度** - 使用-Verbose监控执行

### 结果验证
1. **检查输出** - 验证所有文件都已生成
2. **查看报告** - 阅读自动生成的报告
3. **比较结果** - 与手动分析结果对比

## 🚀 进阶用法

### 集成Python脚本
```python
# analytics_integration.py
import subprocess
import os

def run_analytics(data_path, analysis_type="basic"):
    """调用PowerShell脚本"""
    ps_script = os.path.join(os.path.dirname(__file__), "auto_analytics.ps1")
    cmd = f"powershell -ExecutionPolicy Bypass -File \"{ps_script}\" -DataPath \"{data_path}\" -AnalysisType {analysis_type}"
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0
```

### 创建批处理文件
```batch
@echo off
REM analytics_daily.bat - 每日数据分析
echo 开始每日数据分析...
powershell -ExecutionPolicy Bypass -File "auto_analytics.ps1" "C:\data\daily.csv" -OutputDir "C:\reports\daily"
echo 分析完成！
pause
```

## 📞 支持

### 获取帮助
```powershell
# 显示脚本帮助
Get-Help .\auto_analytics.ps1 -Detailed

# 查看示例
Get-Help .\auto_analytics.ps1 -Examples
```

### 问题反馈
1. 检查日志文件：`logs\analytics_*.log`
2. 查看错误信息：`$Error`变量
3. 验证文件路径和权限

---

**自动化脚本已就绪！开始你的数据分析之旅吧！** 🎯