@echo off
REM 快速启动竞品监控的批处理文件
REM 保存为: O:\AII\上下文助手\monitor_quick.bat

echo ========================================
echo 🚀 竞品监控系统快速启动
echo ========================================
echo.

REM 切换到监控系统目录
cd /d "O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch"

echo 当前目录: %cd%
echo.

if "%1"=="" (
    echo 使用方法:
    echo   %~nx0 [命令]
    echo.
    echo 示例:
    echo   %~nx0 "监控抖音的产品和价格"
    echo   %~nx0 interactive
    echo   %~nx0 status
    echo   %~nx0 results
    echo   %~nx0 test
    echo.
    goto :end
)

if "%1"=="interactive" (
    echo 进入交互式聊天模式...
    echo.
    python chat_monitor.py --interactive
    goto :end
)

if "%1"=="status" (
    echo 查看监控状态...
    echo.
    python chat_monitor_cli.py --status
    goto :end
)

if "%1"=="results" (
    echo 查看监控成果...
    echo.
    python view_results.py
    goto :end
)

if "%1"=="test" (
    echo 运行系统测试...
    echo.
    python system_test.py
    goto :end
)

REM 执行监控命令
echo 执行监控命令: %*
echo.
python chat_monitor.py --command "%*"

:end
echo.
echo ========================================
echo 按任意键退出...
pause > nul