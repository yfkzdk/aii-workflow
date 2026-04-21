"""用户输入收集器 — 追加写入，不分割，等用户明确完成后才处理"""

import json
import sys
from pathlib import Path
from datetime import datetime
from utils import atomic_write_json


COMPLETION_KEYWORDS = ["/done", "/submit", "完成", "就这样", "开始吧", "确认", "/ok"]
TIMEOUT_SECONDS = 300  # 5分钟无输入视为完成


def add_chunk(task_dir: str, content: str) -> dict:
    """追加一条用户输入，不触发任何处理"""
    sf = Path(task_dir) / "state.json"
    with open(sf, "r", encoding="utf-8") as f:
        state = json.load(f)

    if "user_input" not in state:
        state["user_input"] = {"chunks": [], "is_complete": False, "completed_at": None}

    chunk = {
        "seq": len(state["user_input"]["chunks"]) + 1,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    state["user_input"]["chunks"].append(chunk)
    state["updated_at"] = datetime.now().isoformat()

    # 检查是否包含完成关键词
    is_complete = False
    stripped = content.strip().lower()
    for kw in COMPLETION_KEYWORDS:
        if kw in stripped:
            is_complete = True
            break

    if is_complete:
        # 去掉完成关键词本身
        content_clean = content
        for kw in COMPLETION_KEYWORDS:
            content_clean = content_clean.replace(kw, "")
        if content_clean.strip() != chunk["content"].strip():
            chunk["content"] = content_clean.strip()
        state["user_input"]["is_complete"] = True
        state["user_input"]["completed_at"] = datetime.now().isoformat()

    atomic_write_json(sf, state)

    return {
        "seq": chunk["seq"],
        "is_complete": state["user_input"]["is_complete"],
        "total_chunks": len(state["user_input"]["chunks"])
    }


def mark_complete(task_dir: str) -> dict:
    """手动标记输入完成（不依赖关键词）"""
    sf = Path(task_dir) / "state.json"
    with open(sf, "r", encoding="utf-8") as f:
        state = json.load(f)

    if "user_input" not in state:
        return {"error": "无输入数据"}

    state["user_input"]["is_complete"] = True
    state["user_input"]["completed_at"] = datetime.now().isoformat()
    state["updated_at"] = datetime.now().isoformat()
    atomic_write_json(sf, state)

    return {"is_complete": True, "total_chunks": len(state["user_input"]["chunks"])}


def get_full_input(task_dir: str) -> str:
    """获取完整用户输入（拼接所有chunk）"""
    sf = Path(task_dir) / "state.json"
    with open(sf, "r", encoding="utf-8") as f:
        state = json.load(f)

    if "user_input" not in state:
        return ""

    chunks = state["user_input"]["chunks"]
    return "\n\n".join(c["content"] for c in chunks if c["content"].strip())


def is_input_complete(task_dir: str) -> bool:
    """检查用户输入是否已标记完成"""
    sf = Path(task_dir) / "state.json"
    with open(sf, "r", encoding="utf-8") as f:
        state = json.load(f)

    return state.get("user_input", {}).get("is_complete", False)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python input_collector.py <command> [args]")
        print("Commands: add, complete, get, status")
        sys.exit(1)
    cmd, *args = sys.argv[1:]
    if cmd == "add":
        result = add_chunk(args[0], " ".join(args[1:]))
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "complete":
        result = mark_complete(args[0])
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "get":
        print(get_full_input(args[0]))
    elif cmd == "status":
        print(json.dumps({"is_complete": is_input_complete(args[0])}, ensure_ascii=False))
    else:
        print(f"[ERROR] 未知命令: {cmd} | 可用: add, complete, get, status")