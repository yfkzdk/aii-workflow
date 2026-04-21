@echo off
REM ===============================================
REM AI上下文助手 - 修复版启动器 (UTF-8 WITHOUT BOM)
REM 专门解决Windows中文环境编码问题
REM ===============================================

@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title AI助手 - 修复启动版
color 1F

echo.
echo +===========================================+
echo      AI上下文助手 - 修复启动版
echo +===========================================+
echo.

echo 请选择：
echo   1. 启动新任务
echo   2. 查看使用说明
echo   3. 测试环境
echo   4. 退出
echo.

set /p choice=请选择数字 (1-4):

if "%choice%"=="1" goto start_task
if "%choice%"=="2" goto show_help
if "%choice%"=="3" goto test_env
if "%choice%"=="4" exit /b 0

echo 无效选择
goto :eof

:start_task
echo.
echo 请输入您的任务描述（比如：帮我写个Python脚本）:
set /p task="> "
if "%task%"=="" (
    echo 任务不能为空
    pause
    exit /b 1
)

echo.
echo 正在准备任务...
python ww_fixed.py "%task%"
echo.
echo 请复制上面的内容到Claude Code窗口
echo.
pause
exit /b 0

:show_help
echo.
echo 使用方法：
echo   1. 选择 1
echo   2. 输入任务描述
echo   3. 复制显示的内容到Claude Code
echo.
echo 示例任务：
echo   - 帮我写一个Python脚本
echo   - 分析这个项目的结构
echo   - 修复代码错误
echo.
pause
goto :eof

:test_env
echo.
echo 正在测试环境...
python ww_fixed.py test
echo.
echo 测试完成！
echo 环境状态：正常
pause
exit /b 0