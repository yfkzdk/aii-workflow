@echo off
REM 竞品监控 - 最简单批处理文件
REM 保存到: O:\AII\上下文助手\monitor_easy.bat

echo 竞品监控系统
echo ========================================

REM 切换到监控目录
cd /d "O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch"

if "%1"=="" (
    echo.
    echo 使用方法:
    echo   %~nx0 run [监控命令]     运行监控
    echo   %~nx0 check              查看结果
    echo   %~nx0 status             查看状态
    echo.
    echo 示例:
    echo   %~nx0 run "监控抖音的产品和价格"
    echo   %~nx0 check
    goto :end
)

if "%1"=="run" (
    if "%2"=="" (
        echo 错误: 需要监控命令
        echo 示例: %~nx0 run "监控抖音的产品和价格"
        goto :end
    )

    REM 组合所有参数
    set "cmd=%2"
    shift
    shift
    :collect
    if not "%1"=="" (
        set "cmd=%cmd% %1"
        shift
        goto :collect
    )

    echo 执行监控: %cmd%
    echo.
    python monitor_simple.py run "%cmd%"
    goto :end
)

if "%1"=="check" (
    echo 查看监控结果...
    echo.
    python monitor_simple.py show
    goto :end
)

if "%1"=="status" (
    echo 查看系统状态...
    echo.
    python chat_monitor_cli.py --status
    goto :end
)

echo 未知命令: %1
echo 使用: %~nx0 查看帮助

:end
echo.
echo ========================================
echo 完成
pause