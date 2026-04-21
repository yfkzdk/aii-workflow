@echo off
chcp 65001 > nul
echo 竞品监控助手 - 阿里云价格监控
echo ========================================
cd /d "O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch"
python chat_monitor.py --command "每小时检查阿里云的价格变化"
echo.
echo 按任意键退出...
pause > nul