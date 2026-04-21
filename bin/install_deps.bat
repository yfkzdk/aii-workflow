@echo off
chcp 65001 > nul
echo 竞品监控助手 - 依赖包安装
echo ========================================
echo.
echo 正在安装必要的依赖包...

cd /d "O:\AII\IDE.CLOUD\mystudy\workflows\competitor-watch"

echo 1. 安装 pyyaml...
pip install pyyaml>=6.0.1

echo.
echo 2. 安装其他核心依赖...
pip install requests>=2.31.0
pip install pandas>=2.1.0

echo.
echo 3. 可选安装完整依赖包...
echo 如果需要完整功能，运行: pip install -r requirements.txt

echo.
echo 安装完成！
echo 现在可以运行: python chat_monitor.py --command "每小时检查阿里云的价格变化"
echo.
pause