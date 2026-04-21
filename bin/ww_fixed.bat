@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title AI工作流启动器 (修复版)
color 0F

set WORKFLOW_DIR=O:\AII\上下文助手
set PYTHON_SCRIPT=%WORKFLOW_DIR%\ww_fixed.py

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python
    echo 请安装Python 3.x并添加到PATH
    pause
    exit /b 1
)

REM 检查修复脚本
if not exist "%PYTHON_SCRIPT%" (
    echo [错误] 修复脚本不存在: %PYTHON_SCRIPT%
    echo 请确保 ww_fixed.py 文件存在
    pause
    exit /b 1
)

REM 无参数时显示帮助
if "%~1"=="" (
    echo.
    echo ========================================
    echo    AI工作流启动器 - 修复版
    echo ========================================
    echo.
    echo 使用方式:
    echo   ww "任务描述"         启动新任务
    echo   ww status             查看系统状态
    echo   ww test               测试环境
    echo   ww version            版本信息
    echo   ww help               帮助信息
    echo.
    echo 示例:
    echo   ww "帮我写一个Python脚本"
    echo   ww "分析这个项目的问题"
    echo.
    echo 编码修复: 已解决Windows中文环境问题
    echo.
    echo ========================================
    echo.

    set /p "task_desc=请输入任务描述 (或直接按回车退出): "

    if "!task_desc!"=="" (
        echo 已退出
        timeout /t 2 >nul
        exit /b 0
    )

    echo.
    echo 正在启动任务...
    python "%PYTHON_SCRIPT%" "!task_desc!"
    pause
    exit /b 0
)

REM 处理带参数的情况
python "%PYTHON_SCRIPT%" %*

if errorlevel 1 (
    echo.
    echo [错误] 执行失败
    pause
    exit /b 1
)

REM 如果不是状态或测试命令，等待用户查看
echo %1 | findstr /i "status test version help" >nul
if errorlevel 1 (
    echo.
    echo 请复制上方内容到Claude Code窗口
    timeout /t 5 >nul
)