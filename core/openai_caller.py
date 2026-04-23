"""OpenAI 兼容 API 调用器"""

import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class OpenAICaller:
    """支持 OpenAI 兼容 API 的调用器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()

        # 从环境变量读取配置
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        # 初始化客户端
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            print(f"[OpenAICaller] Initialized with model={self.model}, base_url={self.base_url}")
        except Exception as e:
            print(f"[OpenAICaller] Failed to initialize: {e}")
            self.client = None

    def call(self, agent_def: str, context: str = "") -> Dict[str, Any]:
        """调用 API"""
        if self.client is None:
            return {
                "output": "",
                "success": False,
                "error": "Client not initialized"
            }

        prompt = f"{agent_def}\n\n--- Task Context ---\n{context}" if context else agent_def

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.7
            )

            output = response.choices[0].message.content
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }

            print(f"[OpenAICaller] Success! Tokens: {usage['input_tokens']}in/{usage['output_tokens']}out")

            return {
                "output": output,
                "usage": usage,
                "success": True,
                "error": None
            }

        except Exception as e:
            error_msg = str(e)
            print(f"[OpenAICaller] Failed: {error_msg}")
            return {
                "output": "",
                "success": False,
                "error": error_msg
            }

# 测试代码
if __name__ == "__main__":
    caller = OpenAICaller()

    if caller.client:
        result = caller.call(
            agent_def="You are a helpful assistant.",
            context="Say hello in Chinese."
        )

        if result['success']:
            print(f"\nResponse:\n{result['output']}")
        else:
            print(f"\nError: {result['error']}")
