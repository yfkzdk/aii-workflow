#!/usr/bin/env python3
"""
简化版日志管理器 - 向后兼容模式
此脚本保持原有的简单日志记录功能，同时支持新的表格格式
"""

import os
import sys
import datetime
from pathlib import Path

LOG_FILE = Path("AI_WORKFLOW_LOG.md")

def add_simple_log(message: str):
    """添加简单的日志条目（向后兼容）"""
    if not LOG_FILE.exists():
        # 初始化表格格式
        init_table_log()

    # 读取现有内容
    content = LOG_FILE.read_text(encoding='utf-8')
    lines = content.splitlines()

    # 检查是否为表格格式
    is_table_format = "| 日期 | 任务ID |" in content

    if is_table_format:
        # 表格格式 - 添加到表格末尾
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        task_id = f"AUTO-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # 找到表格开始位置
        table_start = -1
        for i, line in enumerate(lines):
            if "|---|---|---|---|---|" in line:
                table_start = i + 1
                break

        if table_start == -1:
            table_start = len(lines)

        # 创建新行
        new_row = f"| {date_str} | {task_id} | 📝 系统日志 | {message[:50]}... | scripts/log_manager.py |"
        lines.insert(table_start, new_row)

        # 限制行数
        if len(lines) > 55:
            lines = lines[:2] + lines[2:50]
    else:
        # 旧格式 - 添加时间戳和消息
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"## {timestamp}")
        lines.append(f"✅ {message}")
        lines.append("")

        # 限制行数
        if len(lines) > 80:
            lines = lines[:3] + lines[-77:]

    # 写回文件
    LOG_FILE.write_text("\n".join(lines), encoding='utf-8')

    try:
        print(f"📝 日志已记录: {message[:50]}...")
    except UnicodeEncodeError:
        print("日志已记录")

def init_table_log():
    """初始化表格格式日志"""
    header = "# 📜 AI 工作流主控日志\n"
    header += "| 日期 | 任务ID | 状态 | 最优方案 | 归档路径 |\n"
    header += "|---|---|---|---|---|\n"

    LOG_FILE.write_text(header, encoding='utf-8')
    print("✅ 日志表格已初始化")

def convert_to_table_format():
    """将旧格式日志转换为表格格式"""
    if not LOG_FILE.exists():
        init_table_log()
        return

    content = LOG_FILE.read_text(encoding='utf-8')

    # 检查是否已经是表格格式
    if "| 日期 | 任务ID |" in content:
        print("📋 日志已经是表格格式")
        return

    # 解析旧格式日志
    lines = content.splitlines()
    table_rows = []

    current_date = ""
    for line in lines:
        line = line.strip()
        if line.startswith("## "):
            current_date = line.replace("##", "").strip()
        elif line.startswith("✅ "):
            message = line.replace("✅", "").strip()
            if current_date and message:
                task_id = f"LEGACY-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
                table_rows.append(f"| {current_date} | {task_id} | 📝 历史记录 | {message[:50]}... | 旧格式转换 |")

    # 创建新表格
    init_table_log()
    content = LOG_FILE.read_text(encoding='utf-8')
    lines = content.splitlines()

    # 插入转换的行
    table_start = -1
    for i, line in enumerate(lines):
        if "|---|---|---|---|---|" in line:
            table_start = i + 1
            break

    if table_start > 0:
        # 插入转换的行
        for row in reversed(table_rows[-10:]):  # 只保留最近的10条
            lines.insert(table_start, row)

        # 添加转换说明
        lines.insert(table_start, f"| {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | CONVERT | 🔄 格式转换 | 旧日志已转换为表格格式 | scripts/log_manager.py |")

        LOG_FILE.write_text("\n".join(lines), encoding='utf-8')
        print(f"🔄 已转换 {len(table_rows)} 条旧日志到表格格式")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("📖 用法:")
        print("  python log_manager.py '[日志内容]'    # 添加日志")
        print("  python log_manager.py --convert       # 转换为表格格式")
        print("  python log_manager.py --init          # 初始化表格格式")
    elif sys.argv[1] == "--convert":
        convert_to_table_format()
    elif sys.argv[1] == "--init":
        init_table_log()
    else:
        add_simple_log(sys.argv[1])
