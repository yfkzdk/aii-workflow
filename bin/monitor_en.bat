@echo off
REM 竞品监控快速启动 - 简单英文版
REM 保存为: O:\AII\上下文助手\monitor_en.bat

echo ========================================
echo Competitor Monitor Quick Start
echo ========================================
echo.

REM 切换到监控目录
cd /d "O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch"

echo Current directory: %cd%
echo.

if "%1"=="" (
    echo Usage:
    echo   %~nx0 [command]
    echo.
    echo Commands:
    echo   %~nx0 run [command]    - Run monitor command
    echo   %~nx0 results          - View monitoring results
    echo   %~nx0 status           - View system status
    echo   %~nx0 interactive      - Start interactive mode
    echo   %~nx0 test             - Run system test
    echo   %~nx0 help             - Show this help
    echo.
    echo Examples:
    echo   %~nx0 run "monitor Douyin products and prices"
    echo   %~nx0 run "monitor Aliyun price changes daily"
    echo   %~nx0 results
    goto :end
)

if "%1"=="run" (
    if "%2"=="" (
        echo Error: run command needs argument
        echo Example: %~nx0 run "monitor Douyin products and prices"
        goto :end
    )

    REM 获取所有参数（从第二个开始）
    set "cmd=%2"
    shift
    shift
    :getargs
    if not "%1"=="" (
        set "cmd=%cmd% %1"
        shift
        goto :getargs
    )

    echo Running: %cmd%
    echo.
    python chat_monitor.py --command "%cmd%"
    goto :end
)

if "%1"=="results" (
    echo Viewing monitoring results...
    echo.
    python check_results.py
    goto :end
)

if "%1"=="status" (
    echo Viewing system status...
    echo.
    python chat_monitor_cli.py --status
    goto :end
)

if "%1"=="interactive" (
    echo Starting interactive mode...
    echo.
    python chat_monitor.py --interactive
    goto :end
)

if "%1"=="test" (
    echo Running system test...
    echo.
    python system_test.py
    goto :end
)

if "%1"=="help" (
    echo Competitor Monitor System - Help
    echo ================================
    echo.
    echo Available commands:
    echo   monitor Douyin products and prices
    echo   monitor Aliyun price changes daily
    echo   monitor Huawei cloud updates hourly
    echo   monitor Tencent API changes with high priority
    echo.
    echo Quick commands:
    echo   .\monitor_en.bat run "monitor Douyin products and prices"
    echo   .\monitor_en.bat results
    echo   .\monitor_en.bat status
    echo.
    echo Directory:
    echo   O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch
    goto :end
)

echo Unknown command: %1
echo Use: %~nx0 help

:end
echo.
echo ========================================
echo Press any key to exit...
pause > nul