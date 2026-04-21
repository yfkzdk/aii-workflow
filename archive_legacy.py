#!/usr/bin/env python3
"""归档旧测试数据 — 将 workflows/ 下的测试目录移至 workflows/_archive/

运行: python archive_legacy.py
"""

import json
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
WORKFLOWS_DIR = PROJECT_DIR / "workflows"
ARCHIVE_DIR = WORKFLOWS_DIR / "_archive"

# 已知的测试数据目录
LEGACY_DIRS = [
    "test-auto-run",
    "test-fib",
    "test-stability-01",
    "test-stability-02",
    "tests",
]

# 已知的测试任务（TASK- 开头的旧数据）
LEGACY_PREFIXES = ["TASK-20260419", "TASK-20260420-02"]


def archive_legacy():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    archived = []
    skipped = []

    # 归档固定名称的测试目录
    for dirname in LEGACY_DIRS:
        src = WORKFLOWS_DIR / dirname
        if src.exists() and src.is_dir():
            dst = ARCHIVE_DIR / dirname
            if dst.exists():
                shutil.rmtree(str(dst))
            shutil.move(str(src), str(dst))
            archived.append(dirname)
            print(f"  [ARCHIVED] {dirname} -> _archive/{dirname}")
        else:
            skipped.append(dirname)

    # 归档旧格式任务目录
    for item in WORKFLOWS_DIR.iterdir():
        if not item.is_dir():
            continue
        name = item.name
        if name.startswith("_") or name == "_archive":
            continue
        # 检查 state.json 中的状态
        state_file = item / "state.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                status = state.get("status", "")
                created = state.get("created_at", "")
                # 归档已完成的任务和 2026-04-20 之前的任务
                if status == "completed" or any(prefix in name for prefix in LEGACY_PREFIXES):
                    dst = ARCHIVE_DIR / name
                    if dst.exists():
                        shutil.rmtree(str(dst))
                    shutil.move(str(item), str(dst))
                    archived.append(name)
                    print(f"  [ARCHIVED] {name} (status={status}) -> _archive/{name}")
            except (json.JSONDecodeError, OSError):
                pass

    print(f"\n  归档完成: {len(archived)} 个目录已移至 workflows/_archive/")
    if skipped:
        print(f"  跳过（不存在）: {len(skipped)} 个")


if __name__ == "__main__":
    print("归档旧测试数据...")
    archive_legacy()