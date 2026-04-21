#!/usr/bin/env python3
"""
AI 工作流工具集
辅助脚本，用于自动化工作流管理
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class WorkflowUtils:
    """工作流工具类"""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.log_file = self.base_dir / "AI_WORKFLOW_LOG.md"
        self.input_task = self.base_dir / "tasks" / "input_task.md"
        self.output_result = self.base_dir / "tasks" / "output_result.md"

    def create_task_id(self) -> str:
        """生成任务ID"""
        now = datetime.datetime.now()
        return f"TASK-{now.strftime('%Y%m%d-%H%M%S')}"

    def validate_task_input(self) -> Dict[str, Any]:
        """验证任务输入文件的完整性"""
        if not self.input_task.exists():
            return {"valid": False, "error": "任务输入文件不存在"}

        content = self.input_task.read_text(encoding='utf-8')
        validation_result = {
            "valid": True,
            "has_task_id": "任务标识" in content,
            "has_goal": "任务目标" in content,
            "has_constraints": "约束条件" in content,
            "has_expected_output": "期望输出格式" in content,
            "line_count": len(content.splitlines()),
            "word_count": len(content.split())
        }

        # 检查必要字段
        required_fields = ["任务标识", "任务目标", "约束条件", "期望输出格式"]
        missing_fields = [field for field in required_fields if field not in content]

        if missing_fields:
            validation_result["valid"] = False
            validation_result["missing_fields"] = missing_fields
            validation_result["error"] = f"缺少必要字段: {', '.join(missing_fields)}"

        return validation_result

    def extract_history_patterns(self, limit: int = 10) -> List[str]:
        """从日志中提取历史成功模式"""
        if not self.log_file.exists():
            return []

        try:
            content = self.log_file.read_text(encoding='utf-8')
            lines = content.splitlines()

            patterns = []
            for i, line in enumerate(lines):
                if "✅" in line and i > 0 and lines[i-1].startswith("##"):
                    # 提取成功记录
                    timestamp = lines[i-1].replace("##", "").strip()
                    success_msg = line.strip()
                    patterns.append(f"{timestamp}: {success_msg}")

            return patterns[-limit:]  # 返回最近的记录
        except:
            return []

    def format_three_solutions(self,
                              solution_a: Dict[str, Any],
                              solution_b: Dict[str, Any],
                              solution_c: Dict[str, Any]) -> str:
        """格式化三个方案用于对比"""

        def format_solution(name: str, solution: Dict) -> str:
            return f"""### {name}
**核心思路**：{solution.get('核心思路', '')}
- **效率评分**：{solution.get('效率评分', 'N/A')}/10
- **可维护性**：{solution.get('可维护性', 'N/A')}
- **风险评估**：{solution.get('风险评估', 'N/A')}
- **历史一致性**：{solution.get('历史一致性', 'N/A')}
- **预估时间**：{solution.get('预估时间', 'N/A')}
"""

        output = "## 💡 三方案对比分析\n\n"
        output += format_solution("方案A：[激进方案名称]", solution_a)
        output += "\n"
        output += format_solution("方案B：[平衡方案名称]", solution_b)
        output += "\n"
        output += format_solution("方案C：[保守方案名称]", solution_c)

        return output

    def calculate_score_matrix(self,
                              weights: Dict[str, float],
                              scores_a: Dict[str, float],
                              scores_b: Dict[str, float],
                              scores_c: Dict[str, float]) -> Dict[str, Any]:
        """计算择优决策矩阵"""

        def calculate_weighted_score(scores: Dict[str, float]) -> float:
            total = 0.0
            for dimension, weight in weights.items():
                if dimension in scores:
                    total += scores[dimension] * weight
            return total

        score_a = calculate_weighted_score(scores_a)
        score_b = calculate_weighted_score(scores_b)
        score_c = calculate_weighted_score(scores_c)

        scores = {
            "方案A": score_a,
            "方案B": score_b,
            "方案C": score_c
        }

        best_solution = max(scores, key=scores.get)

        return {
            "scores": scores,
            "best_solution": best_solution,
            "best_score": scores[best_solution],
            "matrix": {
                "方案A": scores_a,
                "方案B": scores_b,
                "方案C": scores_c
            }
        }

    def prepare_output_template(self, task_id: str,
                               best_solution: str,
                               summary: str) -> str:
        """准备输出模板"""
        template = Path(__file__).parent.parent / "tasks" / "output_result.md"
        if template.exists():
            content = template.read_text(encoding='utf-8')
            content = content.replace("${YYYYMMDD}-${HHMMSS}", task_id[5:])
            content = content.replace("[方案X]", best_solution)
            content = content.replace("[2-3句话总结任务完成情况和核心成果]", summary)
            return content
        return ""

    def cleanup_task_files(self):
        """清理任务文件（准备下次使用）"""
        # 清空但不删除文件
        for file_path in [self.input_task, self.output_result]:
            if file_path.exists():
                file_path.write_text("", encoding='utf-8')
                print(f"🔄 已清空: {file_path.name}")

    def check_token_count(self, text: str, max_tokens: int = 2000) -> Dict[str, Any]:
        """粗略估算token数量并检查是否超限"""
        # 简单估算：1个中文字符 ≈ 1.5 tokens，1个英文字符 ≈ 0.25 tokens
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = len(text) - chinese_chars

        estimated_tokens = int(chinese_chars * 1.5 + english_chars * 0.25)
        is_over_limit = estimated_tokens > max_tokens

        return {
            "estimated_tokens": estimated_tokens,
            "is_over_limit": is_over_limit,
            "max_tokens": max_tokens,
            "suggested_chunks": max(1, estimated_tokens // 1500 + 1)  # 建议分块数
        }


def main():
    """命令行工具"""
    import argparse

    parser = argparse.ArgumentParser(description="AI工作流工具")
    parser.add_argument("--validate", action="store_true", help="验证任务输入文件")
    parser.add_argument("--history", type=int, default=5, help="提取最近N条历史模式")
    parser.add_argument("--cleanup", action="store_true", help="清理任务文件")
    parser.add_argument("--token-check", metavar="TEXT", help="估算文本token数量")

    args = parser.parse_args()
    utils = WorkflowUtils()

    if args.validate:
        result = utils.validate_task_input()
        print("📋 任务输入验证结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.history:
        patterns = utils.extract_history_patterns(args.history)
        print(f"📜 最近{args.history}条成功模式:")
        for i, pattern in enumerate(patterns, 1):
            print(f"{i}. {pattern}")

    elif args.token_check:
        result = utils.check_token_count(args.token_check)
        print("🔢 Token估算结果:")
        print(f"  估算token数: {result['estimated_tokens']}")
        print(f"  限制: {result['max_tokens']}")
        print(f"  是否超限: {'是' if result['is_over_limit'] else '否'}")
        if result['is_over_limit']:
            print(f"  建议分块数: {result['suggested_chunks']}")

    elif args.cleanup:
        utils.cleanup_task_files()
        print("🧹 任务文件已清理")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()