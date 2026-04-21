#!/usr/bin/env python3
"""
AI工作流管理器 - 主控制脚本
处理表格格式的日志记录和任务管理
"""

import os
import sys
import json
import datetime
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional


class WorkflowManager:
    """工作流管理器，处理表格格式日志和任务协调"""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.log_file = self.base_dir / "AI_WORKFLOW_LOG.md"
        self.tasks_dir = self.base_dir / "tasks"
        self.workflows_dir = self.base_dir / "workflows"

        # 确保目录存在
        self.tasks_dir.mkdir(exist_ok=True)
        self.workflows_dir.mkdir(exist_ok=True)

    def init_log_table(self):
        """初始化表格格式的日志文件"""
        header = "# 📜 AI 工作流主控日志\n"
        header += "| 日期 | 任务ID | 状态 | 最优方案 | 归档路径 |\n"
        header += "|---|---|---|---|---|\n"

        self.log_file.write_text(header, encoding='utf-8')
        print("日志表格已初始化")

    def add_log_entry(self, task_id: str, status: str,
                     best_solution: str, archive_path: str = ""):
        """添加新的日志条目到表格"""

        # 如果日志文件不存在，先初始化
        if not self.log_file.exists():
            self.init_log_table()

        # 读取现有内容
        content = self.log_file.read_text(encoding='utf-8')
        lines = content.splitlines()

        # 找到表格开始的位置（表头后的第一行）
        table_start = -1
        for i, line in enumerate(lines):
            if "|---|---|---|---|---|" in line:
                table_start = i + 1
                break

        if table_start == -1:
            # 表格格式错误，重新初始化
            self.init_log_table()
            content = self.log_file.read_text(encoding='utf-8')
            lines = content.splitlines()
            table_start = 2  # 表头后的第一行

        # 创建新行（使用纯文本状态）
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        # 替换emoji状态为文本
        status_text = status
        if "📋" in status:
            status_text = status.replace("📋", "[创建]")
        elif "✅" in status:
            status_text = status.replace("✅", "[完成]")
        elif "🔄" in status:
            status_text = status.replace("🔄", "[转换]")
        elif "📝" in status:
            status_text = status.replace("📝", "[日志]")

        new_row = f"| {date_str} | {task_id} | {status_text} | {best_solution} | {archive_path} |"

        # 插入新行到表格开始位置
        lines.insert(table_start, new_row)

        # 限制表格行数（最多50行数据）
        if len(lines) > 55:  # 表头2行 + 50行数据 + 可能的空行
            # 保留表头和最新的48行数据
            lines = lines[:2] + lines[2:50]

        # 写回文件
        self.log_file.write_text("\n".join(lines), encoding='utf-8')
        print(f"日志已记录: {task_id} - {status_text}")

    def create_task(self, task_data: Dict[str, Any]) -> str:
        """创建新任务并返回任务ID"""
        task_id = f"TASK-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # 创建任务文件
        task_file = self.tasks_dir / f"{task_id}.md"

        content = f"""# 🎯 任务: {task_data.get('title', '未命名任务')}

## 🆔 任务ID
`{task_id}`

## 📅 创建时间
{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 任务目标
{task_data.get('goal', '')}

## ⚠️ 约束条件
{task_data.get('constraints', '')}

## 📊 期望输出
{task_data.get('expected_output', '')}

## 📋 输入数据
{task_data.get('input_data', '')}

## 🏷️ 标签
- 优先级: {task_data.get('priority', '中')}
- 复杂度: {task_data.get('complexity', '中')}
- 类型: {task_data.get('type', '通用')}

## 📝 备注
{task_data.get('notes', '')}
"""

        task_file.write_text(content, encoding='utf-8')

        # 记录到日志
        self.add_log_entry(
            task_id=task_id,
            status="[创建] 已创建",
            best_solution="等待分析",
            archive_path=str(task_file.relative_to(self.base_dir))
        )

        return task_id

    def update_task_status(self, task_id: str, status: str,
                          solution: str = "", archive_path: str = ""):
        """更新任务状态"""
        # 查找日志中的任务行并更新
        if not self.log_file.exists():
            print("错误: 日志文件不存在")
            return

        content = self.log_file.read_text(encoding='utf-8')
        lines = content.splitlines()

        for i, line in enumerate(lines):
            if task_id in line and line.startswith("| "):
                # 解析现有行
                parts = line.strip("|").split("|")
                if len(parts) >= 5:
                    date = parts[0].strip()
                    existing_task_id = parts[1].strip()
                    existing_archive = parts[4].strip() if len(parts) > 4 else ""

                    # 使用传入的归档路径，如果为空则使用现有的
                    final_archive = archive_path if archive_path else existing_archive

                    # 更新状态和最优方案
                    new_line = f"| {date} | {existing_task_id} | {status} | {solution} | {final_archive} |"
                    lines[i] = new_line

                    # 写回文件
                    self.log_file.write_text("\n".join(lines), encoding='utf-8')
                    print(f"已更新: {task_id} -> {status}")
                    return

        print(f"未找到任务: {task_id}")

    def get_task_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取任务历史记录"""
        if not self.log_file.exists():
            return []

        content = self.log_file.read_text(encoding='utf-8')
        lines = content.splitlines()

        tasks = []
        for line in lines:
            if line.startswith("| ") and "TASK-" in line and "|---|---|---|---|---|" not in line:
                parts = line.strip("|").split("|")
                if len(parts) >= 5:
                    task = {
                        "date": parts[0].strip(),
                        "task_id": parts[1].strip(),
                        "status": parts[2].strip(),
                        "best_solution": parts[3].strip(),
                        "archive_path": parts[4].strip()
                    }
                    tasks.append(task)

        return tasks[:limit]

    def archive_task(self, task_id: str, result_content: str):
        """归档任务结果"""
        archive_file = self.workflows_dir / f"{task_id}_result.md"
        archive_file.write_text(result_content, encoding='utf-8')

        # 更新日志中的归档路径
        self.update_task_status(
            task_id=task_id,
            status="✅ 已归档",
            archive_path=str(archive_file.relative_to(self.base_dir))
        )

        return str(archive_file)

    def generate_three_solutions(self, task_id: str) -> Dict[str, Any]:
        """为任务生成三个解决方案"""
        task_file = self.tasks_dir / f"{task_id}.md"
        if not task_file.exists():
            return {"error": "任务文件不存在"}

        # 这里可以集成AI生成三个方案
        # 目前返回模拟数据
        return {
            "task_id": task_id,
            "solutions": [
                {
                    "name": "激进方案",
                    "description": "高风险高回报，采用最新技术栈",
                    "efficiency": 9,
                    "maintainability": 6,
                    "risk": 8,
                    "history_consistency": 7,
                    "estimated_time": "2小时"
                },
                {
                    "name": "平衡方案",
                    "description": "综合考虑，采用稳定可靠的技术",
                    "efficiency": 7,
                    "maintainability": 8,
                    "risk": 5,
                    "history_consistency": 9,
                    "estimated_time": "4小时"
                },
                {
                    "name": "保守方案",
                    "description": "低风险稳定，采用成熟方案",
                    "efficiency": 5,
                    "maintainability": 9,
                    "risk": 3,
                    "history_consistency": 10,
                    "estimated_time": "6小时"
                }
            ]
        }

    def compare_solutions(self, solutions_data: Dict[str, Any]) -> Dict[str, Any]:
        """比较三个解决方案并选择最优"""
        solutions = solutions_data.get("solutions", [])

        if len(solutions) != 3:
            return {"error": "需要正好三个方案"}

        # 权重配置
        weights = {
            "efficiency": 0.4,      # 效率 40%
            "maintainability": 0.3, # 可维护性 30%
            "risk": 0.2,            # 风险控制 20%
            "history_consistency": 0.1  # 历史一致性 10%
        }

        # 计算每个方案的总分（风险是负向指标，需要取反）
        scored_solutions = []
        for sol in solutions:
            total_score = (
                sol["efficiency"] * weights["efficiency"] +
                sol["maintainability"] * weights["maintainability"] +
                (10 - sol["risk"]) * weights["risk"] +  # 风险越低越好
                sol["history_consistency"] * weights["history_consistency"]
            )
            scored_solutions.append({
                **sol,
                "total_score": round(total_score, 2)
            })

        # 按总分排序
        scored_solutions.sort(key=lambda x: x["total_score"], reverse=True)

        return {
            "task_id": solutions_data["task_id"],
            "solutions": scored_solutions,
            "best_solution": scored_solutions[0],
            "comparison_matrix": [
                ["比较维度", "权重", "方案A", "方案B", "方案C", "最优"],
                ["效率", "40%",
                 f"{scored_solutions[0]['efficiency']}/10",
                 f"{scored_solutions[1]['efficiency']}/10",
                 f"{scored_solutions[2]['efficiency']}/10",
                 "✓" if scored_solutions[0]['efficiency'] == max(s['efficiency'] for s in scored_solutions) else ""],
                ["可维护性", "30%",
                 f"{scored_solutions[0]['maintainability']}/10",
                 f"{scored_solutions[1]['maintainability']}/10",
                 f"{scored_solutions[2]['maintainability']}/10",
                 "✓" if scored_solutions[0]['maintainability'] == max(s['maintainability'] for s in scored_solutions) else ""],
                ["风险控制", "20%",
                 f"{10 - scored_solutions[0]['risk']}/10",
                 f"{10 - scored_solutions[1]['risk']}/10",
                 f"{10 - scored_solutions[2]['risk']}/10",
                 "✓" if scored_solutions[0]['risk'] == min(s['risk'] for s in scored_solutions) else ""],
                ["历史一致性", "10%",
                 f"{scored_solutions[0]['history_consistency']}/10",
                 f"{scored_solutions[1]['history_consistency']}/10",
                 f"{scored_solutions[2]['history_consistency']}/10",
                 "✓" if scored_solutions[0]['history_consistency'] == max(s['history_consistency'] for s in scored_solutions) else ""],
                ["总分", "100%",
                 f"{scored_solutions[0]['total_score']}",
                 f"{scored_solutions[1]['total_score']}",
                 f"{scored_solutions[2]['total_score']}",
                 f"方案{['A','B','C'][scored_solutions.index(max(scored_solutions, key=lambda x: x['total_score']))]}"]
            ]
        }


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="AI工作流管理器")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # 初始化命令
    init_parser = subparsers.add_parser("init", help="初始化日志表格")

    # 创建任务命令
    create_parser = subparsers.add_parser("create", help="创建新任务")
    create_parser.add_argument("--title", required=True, help="任务标题")
    create_parser.add_argument("--goal", required=True, help="任务目标")
    create_parser.add_argument("--constraints", default="", help="约束条件")
    create_parser.add_argument("--expected", default="", help="期望输出")

    # 更新状态命令
    update_parser = subparsers.add_parser("update", help="更新任务状态")
    update_parser.add_argument("--task", required=True, help="任务ID")
    update_parser.add_argument("--status", required=True, help="新状态")
    update_parser.add_argument("--solution", default="", help="最优方案")

    # 列出任务命令
    list_parser = subparsers.add_parser("list", help="列出任务历史")
    list_parser.add_argument("--limit", type=int, default=10, help="显示数量")

    # 生成方案命令
    solutions_parser = subparsers.add_parser("solutions", help="生成三个方案")
    solutions_parser.add_argument("--task", required=True, help="任务ID")

    # 比较方案命令
    compare_parser = subparsers.add_parser("compare", help="比较方案")
    compare_parser.add_argument("--task", required=True, help="任务ID")

    args = parser.parse_args()
    manager = WorkflowManager()

    if args.command == "init":
        manager.init_log_table()

    elif args.command == "create":
        task_data = {
            "title": args.title,
            "goal": args.goal,
            "constraints": args.constraints,
            "expected_output": args.expected
        }
        task_id = manager.create_task(task_data)
        print(f"任务已创建: {task_id}")

    elif args.command == "update":
        manager.update_task_status(args.task, args.status, args.solution)

    elif args.command == "list":
        tasks = manager.get_task_history(args.limit)
        if tasks:
            print(f"最近{len(tasks)}个任务:")
            for task in tasks:
                print(f"  {task['date']} | {task['task_id']} | {task['status']} | {task['best_solution']}")
        else:
            print("暂无任务记录")

    elif args.command == "solutions":
        result = manager.generate_three_solutions(args.task)
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            print("生成的三个方案:")
            for i, sol in enumerate(result["solutions"], 1):
                print(f"\n方案{i} - {sol['name']}:")
                print(f"  描述: {sol['description']}")
                print(f"  效率: {sol['efficiency']}/10")
                print(f"  可维护性: {sol['maintainability']}/10")
                print(f"  风险: {sol['risk']}/10")
                print(f"  历史一致性: {sol['history_consistency']}/10")
                print(f"  预估时间: {sol['estimated_time']}")

    elif args.command == "compare":
        solutions = manager.generate_three_solutions(args.task)
        if "error" in solutions:
            print(f"错误: {solutions['error']}")
        else:
            comparison = manager.compare_solutions(solutions)
            print("方案对比结果:")
            print(f"最优方案: {comparison['best_solution']['name']}")
            print(f"总分: {comparison['best_solution']['total_score']}")

            print("\n对比矩阵:")
            for row in comparison["comparison_matrix"]:
                print(" | ".join(str(cell) for cell in row))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()