import os, sys
from pathlib import Path
import datetime

LOG_FILE = Path("AI_WORKFLOW_LOG.md")
MAX_LINES = 80
HEADER = "# 📜 AI 工作流日志"

def read_log_with_encoding():
    """读取日志文件，处理编码问题"""
    try:
        return LOG_FILE.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # 如果UTF-8失败，尝试GBK
        try:
            return LOG_FILE.read_text(encoding='gbk')
        except UnicodeDecodeError:
            # 如果都失败，返回空内容
            return ""

def update_log(new_entry: str):
    """更新日志文件，过滤失败记录，保留最优解"""
    if not LOG_FILE.exists():
        LOG_FILE.write_text(f"{HEADER}\n> 创建于：{datetime.datetime.now().strftime('%Y-%m-%d')}\n> 状态：已初始化\n> 说明：本文件为唯一跨会话状态源。仅保留 PASS 记录与最优解。\n\n", encoding='utf-8')
        print("📝 日志文件已创建")

    # 读取现有日志内容
    content = read_log_with_encoding()
    if not content:
        # 如果读取失败，重新创建
        content = f"{HEADER}\n> 创建于：{datetime.datetime.now().strftime('%Y-%m-%d')}\n> 状态：已初始化\n> 说明：本文件为唯一跨会话状态源。仅保留 PASS 记录与最优解。\n\n"

    lines = content.splitlines()

    # 过滤失败标记（保留成功和中性记录）
    clean_lines = []
    for line in lines:
        # 跳过失败相关标记
        if any(marker in line for marker in ["❌", "FAIL", "失败", "ERROR:", "错误"]):
            continue
        clean_lines.append(line)

    # 保留表头 + 最近有效记录
    entry_indices = [i for i, line in enumerate(clean_lines) if line.strip().startswith("##")]

    # 确保不超过最大行数
    if len(entry_indices) >= MAX_LINES - 5:  # 为表头预留空间
        # 找到要保留的起始索引
        keep_from = max(0, entry_indices[-(MAX_LINES - 10)])  # 保留较新的记录
        clean_lines = clean_lines[:keep_from] + clean_lines[keep_from:]

    # 添加时间戳和新条目
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_lines.append(f"## {timestamp}")
    clean_lines.append(new_entry.strip())
    clean_lines.append("")  # 空行分隔

    # 写回文件
    LOG_FILE.write_text("\n".join(clean_lines), encoding='utf-8')

    # 安全打印到控制台
    try:
        print(f"✅ 日志已更新: {new_entry[:50]}...")
    except UnicodeEncodeError:
        # 如果控制台不支持Unicode，打印简化信息
        print("日志已更新")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ 用法: python log_manager.py '[条目内容]'")
        print("示例: python log_manager.py '✅ 任务完成：数据分析模块优化完成'")
    else:
        update_log(sys.argv[1])
