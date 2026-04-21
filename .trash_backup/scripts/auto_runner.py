import os, json, time, shutil, subprocess
from pathlib import Path
from datetime import datetime

# ================= 配置区 =================
MAX_RETRIES = 3
TIMEOUT_SECONDS = 180
LOOP_DELAY = 5
WEBHOOK_URL = ""  # 留空则不发送通知
# ==========================================

# 动态获取项目根目录（解决 WinError 2 路径丢失）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 移除表情符号和特殊字符
    safe_msg = msg.encode('ascii', errors='ignore').decode('ascii')
    print(f"[{level}] {ts} - {safe_msg}")

def find_pending_task():
    """自动寻找未完成的 state.json"""
    # 尝试多个可能的workflows目录位置
    possible_paths = [
        PROJECT_ROOT / "workflows",  # 方案1：上下文助手/workflows
        Path.cwd() / "workflows",    # 方案2：当前目录/workflows
        Path.cwd() / "上下文助手" / "workflows",  # 方案3：上下文助手下的workflows
        Path(__file__).resolve().parent.parent / "workflows",  # 方案4：基于脚本位置的workflows
    ]

    for target in possible_paths:
        if target.exists():
            log(f"找到workflows目录: {target}", "INFO")
            for d in target.iterdir():
                sf = d / "state.json"
                if sf.exists():
                    try:
                        with open(sf, 'r', encoding='utf-8') as f: state = json.load(f)
                        if state.get("status") not in ["completed", "CRITICAL_FAILED"]:
                            return d, state
                    except: pass
    log("未找到可用的workflows目录", "WARN")
    return None, None

def build_prompt(state, task_dir):
    agent = state.get("next_agent", "planner")
    agent_md = PROJECT_ROOT / ".claude" / "agents" / f"{agent}.md"
    if not agent_md.exists():
        raise FileNotFoundError(f"Agent 文件缺失: {agent_md}")
        
    prompt = agent_md.read_text(encoding="utf-8")
    prompt += f"\n\n⚡ 执行环境:\n- 根目录: `{PROJECT_ROOT}`\n- 任务目录: `{task_dir}`\n"
    prompt += f"- 核心指令: 执行完毕后，必须调用 `python scripts/state_machine.py update \"{task_dir}\" \"{state['status']}\" \"下一步\" \"下一步agent\"` 更新状态。"
    return prompt

def run_agent_step(task_dir, prompt):
    # 检查 claude 命令是否在 PATH 中
    claude_cmd = shutil.which("claude") or "claude"
    cmd = [claude_cmd, "-p", prompt]
    
    log(f"执行 Agent: {task_dir.name} -> {task_dir.name}")
    try:
        # 关键修复：显式继承环境变量 + 强制工作目录
        env = os.environ.copy()
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
            cwd=str(PROJECT_ROOT), env=env
        )
        if result.returncode == 0:
            log("Agent 执行成功", "OK")
            return True
        else:
            log(f"执行异常 (Exit {result.returncode})\n{result.stderr[:300]}", "WARN")
            return False
    except subprocess.TimeoutExpired:
        log(f"执行超时 ({TIMEOUT_SECONDS}s)", "ERR")
        return False
    except Exception as e:
        log(f"运行异常: {e}", "ERR")
        return False

def increment_retry(task_dir):
    sf = task_dir / "state.json"
    try:
        with open(sf, 'r', encoding='utf-8') as f: st = json.load(f)
        st["retry_count"] = st.get("retry_count", 0) + 1
        st["updated_at"] = datetime.now().isoformat()
        if st["retry_count"] >= MAX_RETRIES:
            st["status"] = "CRITICAL_FAILED"
            log(f"任务 {task_dir.name} 触发熔断", "ERR")
        with open(sf, 'w', encoding='utf-8') as f: json.dump(st, f, indent=2, ensure_ascii=False)
    except: pass

def main():
    log(f"监控启动 | 根目录: {PROJECT_ROOT}")
    while True:
        task_dir, state = find_pending_task()
        if not task_dir:
            log("无待办任务，休眠...", "WAIT")
            time.sleep(LOOP_DELAY)
            continue

        log(f"待办: {task_dir.name} [{state['status']}] -> {state.get('next_agent','?')}")
        if state.get("retry_count", 0) >= MAX_RETRIES:
            log(f"跳过熔断任务", "SKIP")
            time.sleep(LOOP_DELAY)
            continue

        success = False
        try:
            success = run_agent_step(task_dir, build_prompt(state, task_dir))
        except Exception as e:
            log(f"异常: {e}", "ERR")

        if not success:
            increment_retry(task_dir)
        else:
            log("等待状态流转...", "WAIT")
            time.sleep(3)
        time.sleep(LOOP_DELAY)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: log("监控已停止", "INFO")
