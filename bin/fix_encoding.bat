@echo off
REM 中文工作流编码修复脚本
echo 正在设置UTF-8编码环境...

REM 设置代码页为UTF-8
chcp 65001 > nul

REM 设置环境变量
set PYTHONIOENCODING=utf-8
set LANG=zh_CN.UTF-8

REM 设置Python路径
set PYTHONPATH=O:\AII\上下文助手

echo ✅ 编码环境修复完成！
echo 建议：将此脚本添加到系统启动项，或在每次使用前运行。

REM 启动Python
python %*
