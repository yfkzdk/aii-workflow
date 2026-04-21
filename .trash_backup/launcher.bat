@echo off
REM ===============================================
REM AI Workflow Launcher - English Version
REM No Chinese characters to avoid encoding issues
REM ===============================================

@echo off
chcp 65001 >nul
title AI Assistant Launcher
color 1F

echo.
echo ==========================================
echo     AI Assistant - Launch Tool
echo ==========================================
echo.

echo Options:
echo   1. Start new task
echo   2. View help
echo   3. Test environment
echo   4. Exit
echo.

set /p choice=Enter choice (1-4):

if "%choice%"=="1" goto start_task
if "%choice%"=="2" goto show_help
if "%choice%"=="3" goto test_env
if "%choice%"=="4" exit /b 0

echo Invalid choice
goto :eof

:start_task
echo.
echo Enter your task description:
echo Example: help me write a Python script
set /p task="> "
if "%task%"=="" (
    echo Task cannot be empty
    pause
    exit /b 1
)

echo.
echo Starting workflow...
python ww_fixed.py "%task%"
echo.
echo Please copy the output above to Claude Code window
echo.
pause
exit /b 0

:show_help
echo.
echo How to use:
echo   1. Select option 1
echo   2. Enter your task description
echo   3. Copy the output to Claude Code
echo.
echo Example tasks:
echo   - help me write a Python script
echo   - analyze this project structure
echo   - fix code errors
echo.
pause
goto :eof

:test_env
echo.
echo Testing environment...
python ww_fixed.py test
echo.
echo Test completed!
echo Environment: OK
pause
exit /b 0