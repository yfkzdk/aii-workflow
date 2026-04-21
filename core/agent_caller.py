"""AgentCaller -- Agent 调用器。

阶段三：SDKCaller (Anthropic SDK) + FallbackCaller (subprocess)。
工厂方法 create() 自动选择。
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

AGENT_DIR = ".claude/agents"
CALLER_TIMEOUT = 300
TRANSITION_TOOL = {
    "name": "transition_state",
    "description": "请求编排器推进到下一阶段。编排器会验证你的输出后决定是否批准。",
    "input_schema": {
        "type": "object",
        "properties": {
            "next_step": {
                "type": "string",
                "description": "建议的下一步阶段名",
            },
            "output_summary": {
                "type": "string",
                "description": "输出摘要（≤100字）",
            },
            "errors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "遇到的错误列表（可为空）",
            },
        },
        "required": ["next_step", "output_summary", "errors"],
    },
}


class AgentCaller:
    """基类，定义调用接口。"""

    def __init__(self, project_root: str = ".") -> None:
        self.project_root = Path(project_root).resolve()
        self.agents_dir = self.project_root / AGENT_DIR

    def call(self, agent_id: str, task_dir: str,
             context: str = "") -> Dict[str, Any]:
        raise NotImplementedError

    def get_available_agents(self) -> List[str]:
        if not self.agents_dir.exists():
            return []
        return sorted(p.stem for p in self.agents_dir.glob("*.md"))

    def _read_agent_def(self, agent_id: str) -> Optional[str]:
        path = self.agents_dir / f"{agent_id}.md"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    @classmethod
    def create(cls, project_root: str = ".") -> "AgentCaller":
        """工厂方法：有 anthropic 库用 SDKCaller，否则 FallbackCaller。"""
        try:
            import anthropic  # noqa: F401
            return SDKCaller(project_root)
        except ImportError:
            print("[AgentCaller] anthropic 库未安装，降级到 FallbackCaller (subprocess)")
            return FallbackCaller(project_root)


class FallbackCaller(AgentCaller):
    """subprocess 调 claude CLI — 阶段一逻辑保留。"""

    def call(self, agent_id: str, task_dir: str,
             context: str = "") -> Dict[str, Any]:
        agent_def = self._read_agent_def(agent_id)
        if agent_def is None:
            msg = f"Agent 定义不存在: {agent_id}"
            print(f"[FallbackCaller] {msg}")
            return {"output": "", "tool_calls": [], "usage": {},
                    "success": False, "error": msg}

        prompt = agent_def
        if context:
            prompt = f"{agent_def}\n\n--- 任务上下文 ---\n{context}"

        print(f"[FallbackCaller] 调用: {agent_id} | task_dir={task_dir}")
        try:
            result = subprocess.run(
                ["claude", "--print", "-p", prompt],
                capture_output=True, text=True, encoding="utf-8",
                timeout=CALLER_TIMEOUT, cwd=str(task_dir),
            )
            if result.returncode == 0:
                print(f"[FallbackCaller] 成功: {agent_id}")
                return {"output": result.stdout, "tool_calls": [], "usage": {},
                        "success": True, "error": None}
            else:
                err = result.stderr.strip() or f"exit code {result.returncode}"
                print(f"[FallbackCaller] 失败: {agent_id} — {err}")
                return {"output": result.stdout, "tool_calls": [], "usage": {},
                        "success": False, "error": err}
        except subprocess.TimeoutExpired:
            msg = f"超时 ({CALLER_TIMEOUT}s): {agent_id}"
            print(f"[FallbackCaller] {msg}")
            return {"output": "", "tool_calls": [], "usage": {},
                    "success": False, "error": msg}
        except FileNotFoundError:
            msg = "claude CLI 未找到"
            print(f"[FallbackCaller] {msg}")
            return {"output": "", "tool_calls": [], "usage": {},
                    "success": False, "error": msg}
        except Exception as e:
            msg = f"未知错误: {e}"
            print(f"[FallbackCaller] {msg}")
            return {"output": "", "tool_calls": [], "usage": {},
                    "success": False, "error": msg}


class SDKCaller(AgentCaller):
    """Anthropic SDK 调用 — 阶段三。"""

    def __init__(self, project_root: str = ".") -> None:
        super().__init__(project_root)
        try:
            from anthropic import Anthropic
            self.client = Anthropic()
        except Exception as e:
            print(f"[SDKCaller] Anthropic 初始化失败: {e}")
            self.client = None

    def call(self, agent_id: str, task_dir: str,
             context: str = "") -> Dict[str, Any]:
        if self.client is None:
            print("[SDKCaller] 客户端未初始化，降级到 FallbackCaller")
            fallback = FallbackCaller(str(self.project_root))
            return fallback.call(agent_id, task_dir, context)

        agent_def = self._read_agent_def(agent_id)
        if agent_def is None:
            msg = f"Agent 定义不存在: {agent_id}"
            print(f"[SDKCaller] {msg}")
            return {"output": "", "tool_calls": [], "usage": {},
                    "success": False, "error": msg}

        print(f"[SDKCaller] 调用: {agent_id} | task_dir={task_dir}")
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=[{
                    "type": "text",
                    "text": agent_def,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": context or "请执行你的职责"}],
                tools=[TRANSITION_TOOL],
            )

            # 解析响应
            output_parts: List[str] = []
            tool_calls: List[Dict[str, Any]] = []

            for block in response.content:
                if block.type == "text":
                    output_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_input_tokens": getattr(
                    response.usage, "cache_read_input_tokens", 0),
                "cache_creation_input_tokens": getattr(
                    response.usage, "cache_creation_input_tokens", 0),
            }

            print(f"[SDKCaller] 成功: {agent_id} | tokens: "
                  f"{usage['input_tokens']}in/{usage['output_tokens']}out")
            return {
                "output": "\n".join(output_parts),
                "tool_calls": tool_calls,
                "usage": usage,
                "success": True,
                "error": None,
            }

        except Exception as e:
            err_msg = self._classify_error(e)
            print(f"[SDKCaller] 失败: {agent_id} — {err_msg}")
            return {"output": "", "tool_calls": [], "usage": {},
                    "success": False, "error": err_msg}

    @staticmethod
    def _classify_error(exc: Exception) -> str:
        """分类 API 错误，返回可读消息。"""
        err_type = type(exc).__name__
        err_str = str(exc).lower()

        if "connection" in err_str or "timeout" in err_str:
            return f"API 连接失败: {exc}"
        if "rate" in err_str or "429" in err_str:
            return f"API 限流: {exc}"
        if "token" in err_str or "too long" in err_str or "context_length" in err_str:
            return f"Token 超限: {exc}"
        return f"API 错误 ({err_type}): {exc}"