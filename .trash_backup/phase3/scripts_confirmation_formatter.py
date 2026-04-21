"""确认门格式化器 — 将优化结果转为人类可读格式

此模块提供：
- format_for_user: 生成人类可读的方案摘要
- 支持 skill_auto_matcher 匹配结果展示
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from state_machine import parse_user_response


def load_optimization(task_dir: str) -> Optional[Dict[str, Any]]:
    """加载优化结果"""
    output_file = Path(task_dir) / "artifacts" / "optimized_requirement.json"

    if not output_file.exists():
        return None

    with open(output_file, "r", encoding="utf-8") as f:
        return json.load(f)


def format_skill_match(skill: Dict[str, Any]) -> str:
    """格式化单个 skill 匹配信息"""
    skill_id = skill.get("id", "unknown")
    source = skill.get("source", "unknown")
    match_score = skill.get("match_score")

    if source == "user_specified":
        return f"📌 {skill_id} (用户指定)"
    elif source == "auto_match":
        score_str = f"{match_score:.0%}" if match_score else "自动匹配"
        return f"🔮 {skill_id} ({score_str})"
    else:
        return f"• {skill_id}"


def format_proposal(proposal: Dict[str, Any], index: int, is_recommended: bool = False) -> str:
    """格式化单个方案"""
    pid = proposal.get("id", "?")
    name = proposal.get("name", "未命名方案")
    desc = proposal.get("description", "")
    scope = proposal.get("scope", "")
    tasks = proposal.get("estimated_tasks", "?")
    pros = proposal.get("pros", [])
    cons = proposal.get("cons", [])

    lines = []
    header = f"### 方案 {pid}: {name}"
    if is_recommended:
        header += " ⭐ 推荐"
    lines.append(header)
    lines.append(f"**范围**: {scope}")
    lines.append(f"**预估任务数**: {tasks}")
    lines.append(f"**描述**: {desc}")
    lines.append("")

    # Skills 推荐
    lines.append("**推荐 Skills**:")
    for skill_rec in proposal.get("skills_recommended", []):
        agent_id = skill_rec.get("agent_id", "?")
        skills = skill_rec.get("skills", [])
        skill_strs = [format_skill_match(s) for s in skills]
        lines.append(f"  - {agent_id}: {', '.join(skill_strs)}")
    lines.append("")

    # 优缺点
    if pros:
        lines.append("**优点**:")
        for p in pros:
            lines.append(f"  ✅ {p}")
    if cons:
        lines.append("**缺点**:")
        for c in cons:
            lines.append(f"  ⚠️ {c}")

    return "\n".join(lines)


def format_clarification(clarification: Dict[str, Any], index: int) -> str:
    """格式化单个澄清项"""
    point = clarification.get("point", "?")
    original = clarification.get("original", "")
    inferred = clarification.get("inferred", "")
    reasoning = clarification.get("reasoning", "")
    confidence = clarification.get("confidence", 0)
    needs_confirm = clarification.get("needs_user_confirm", False)
    alternatives = clarification.get("alternatives", [])

    lines = [f"#### {index + 1}. {point}"]
    lines.append(f"**原文**: {original}")
    lines.append(f"**推断**: {inferred}")
    if reasoning:
        lines.append(f"**推理**: {reasoning}")
    lines.append(f"**置信度**: {confidence:.0%}")

    if needs_confirm:
        lines.append("⚠️ **需要确认**")

    if alternatives:
        lines.append(f"**备选方案**: {', '.join(alternatives)}")

    return "\n".join(lines)


def format_agent_assignment(assignment: Dict[str, Any]) -> str:
    """格式化单个 Agent 分配"""
    agent_id = assignment.get("agent_id", "?")
    role = assignment.get("role", "")
    responsibility = assignment.get("responsibility", "")
    parallel_with = assignment.get("parallel_with")

    lines = [f"| {agent_id} | {role} |"]

    if parallel_with:
        lines.append(f"|   ⚡ 与 `{parallel_with}` 并行 |")

    skills = assignment.get("skills", [])
    if skills:
        skill_strs = [format_skill_match(s) for s in skills]
        lines.append(f"|   Skills: {', '.join(skill_strs)} |")

    return "\n".join(lines)


def format_dag_preview(dag: Dict[str, Any]) -> str:
    """格式化 DAG 预览"""
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", [])
    parallel_groups = dag.get("parallel_groups", [])

    lines = ["```mermaid", "graph LR"]

    # 节点
    for node in nodes:
        lines.append(f"  {node}[{node}]")

    # 边
    for edge in edges:
        if len(edge) >= 2:
            lines.append(f"  {edge[0]} --> {edge[1]}")

    lines.append("```")

    if parallel_groups:
        lines.append("")
        lines.append("**并行组**:")
        for group in parallel_groups:
            lines.append(f"  - {', '.join(group)}")

    return "\n".join(lines)


def format_for_user(task_dir: str) -> str:
    """
    生成人类可读的方案摘要

    Args:
        task_dir: 任务目录路径

    Returns:
        Markdown 格式的摘要文本
    """
    optimization = load_optimization(task_dir)

    if not optimization:
        return "❌ 未找到优化结果，请先运行需求优化阶段。"

    sections = []

    # 1. 原始需求摘要
    original = optimization.get("original_requirement", "")
    if len(original) > 200:
        original = original[:200] + "..."
    sections.append("## 📋 需求摘要")
    sections.append(f"> {original}")
    sections.append("")

    # 2. 澄清项
    clarifications = optimization.get("clarifications", [])
    if clarifications:
        sections.append("## 🔍 需求澄清")
        sections.append("")
        sections.append("以下推断需要您的确认：")
        sections.append("")
        for i, c in enumerate(clarifications):
            sections.append(format_clarification(c, i))
            sections.append("")

    # 3. 方案对比表
    proposals = optimization.get("proposals", [])
    sections.append("## 📊 方案对比")
    sections.append("")

    # 简表
    sections.append("| 方案 | 范围 | 任务数 | 推荐度 |")
    sections.append("|------|------|--------|--------|")
    for p in proposals:
        pid = p.get("id", "?")
        scope = p.get("scope", "?")
        tasks = p.get("estimated_tasks", "?")
        rec = "⭐" if pid == "B" else ""
        sections.append(f"| {pid} | {scope} | {tasks} | {rec} |")
    sections.append("")

    # 详细方案
    for i, p in enumerate(proposals):
        is_rec = p.get("id") == "B"
        sections.append(format_proposal(p, i, is_recommended=is_rec))
        sections.append("")

    # 4. Agent 角色分配表
    assignments = optimization.get("agent_assignments", [])
    if assignments:
        sections.append("## 👥 Agent 角色分配")
        sections.append("")
        sections.append("| Agent | 角色 |")
        sections.append("|-------|------|")
        for a in assignments:
            sections.append(format_agent_assignment(a))
        sections.append("")

    # 5. DAG 预览
    dag = optimization.get("task_dag_preview", {})
    if dag.get("nodes"):
        sections.append("## 📐 任务依赖图")
        sections.append("")
        sections.append(format_dag_preview(dag))
        sections.append("")

    # 6. Skill 自动匹配结果
    features = optimization.get("features_detected", {})
    if features:
        sections.append("## 🏷️ 特征检测结果")
        sections.append("")
        for feature in ["has_frontend", "has_backend", "has_ai", "has_network", "has_security", "has_game"]:
            info = features.get(feature, {})
            if isinstance(info, dict) and info.get("detected"):
                evidence = info.get("evidence", "无")
                sections.append(f"- **{feature}**: ✅ ({evidence})")
        sections.append(f"- **复杂度**: {features.get('complexity_score', 0):.1f}")
        tags = features.get("domain_tags", [])
        if tags:
            sections.append(f"- **领域标签**: {', '.join(tags)}")
        sections.append("")

    # 7. 操作提示
    sections.append("## 💡 操作指引")
    sections.append("")
    sections.append("请选择操作：")
    sections.append("")
    sections.append("- **确认方案**: 回复 `confirm A/B/C` 或 `选B`、`方案B`")
    sections.append("- **修改澄清**: 回复 `修改 <澄清项>: <新值>`")
    sections.append("  - 例如: `修改 联机方式: HTTP轮询`")
    sections.append("- **取消任务**: 回复 `取消` 或 `不要了`")
    sections.append("")

    return "\n".join(sections)


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    if len(sys.argv) < 2:
        print("Available commands:")
        print("  format <task_dir>     - Format optimization for user display")
        print("  parse \"<response>\"    - Parse user natural language response")
        sys.exit(0)

    cmd, *args = sys.argv[1:]

    if cmd == "format":
        # format <task_dir>
        if len(args) < 1:
            print("[ERROR] Usage: python confirmation_formatter.py format <task_dir>")
            sys.exit(1)

        output = format_for_user(args[0])
        print(output)

    elif cmd == "parse":
        # parse "<response_str>"
        if len(args) < 1:
            print("[ERROR] Usage: python confirmation_formatter.py parse \"<response>\"")
            sys.exit(1)

        response_str = " ".join(args)
        result = parse_user_response(response_str)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print("[ERROR] Unknown command:", cmd)
        print("Available commands:")
        print("  format <task_dir>     - Format optimization for user display")
        print("  parse \"<response>\"    - Parse user natural language response")
        sys.exit(1)