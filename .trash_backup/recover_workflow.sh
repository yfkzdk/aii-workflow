#!/bin/bash
# AII工作流中断恢复脚本
# 用于在API 400错误中断后，在新的Claude Code窗口中恢复工作流

echo "🔄 AII工作流中断恢复工具"
echo "============================="
echo "检测到中断的工作流状态："
echo ""

# 1. 查找所有正在执行的工作流
INTERRUPTED_WORKFLOWS=()

for workflow_dir in workflows/*/; do
    if [[ -f "${workflow_dir}state.json" ]]; then
        status=$(grep -o '"status":"[^"]*"' "${workflow_dir}state.json" | cut -d'"' -f4)
        if [[ "$status" != "completed" ]] && [[ "$status" != "failed" ]]; then
            task_id=$(grep -o '"task_id":"[^"]*"' "${workflow_dir}state.json" | cut -d'"' -f4)
            retry_count=$(grep -o '"retry_count":[0-9]*' "${workflow_dir}state.json" | cut -d':' -f2)
            max_retries=$(grep -o '"max_retries":[0-9]*' "${workflow_dir}state.json" | cut -d':' -f2)
            echo "📌 工作流: $task_id"
            echo "  状态: $status"
            echo "  重试次数: $retry_count/$max_retries"
            echo "  目录: $workflow_dir"
            echo ""
            INTERRUPTED_WORKFLOWS+=("$task_id:$workflow_dir:$retry_count")
        fi
    fi
done

if [ ${#INTERRUPTED_WORKFLOWS[@]} -eq 0 ]; then
    echo "✅ 没有检测到中断的工作流"
    exit 0
fi

echo "请选择要恢复的工作流："
echo ""

for i in "${!INTERRUPTED_WORKFLOWS[@]}"; do
    IFS=':' read -r task_id workflow_dir retry_count <<< "${INTERRUPTED_WORKFLOWS[$i]}"
    echo "$((i+1)). $task_id (重试: $retry_count/3)"
done

echo ""

read -p "请输入编号 (1-${#INTERRUPTED_WORKFLOWS[@]}) 或 'a' 全部恢复: " choice

if [[ "$choice" == "a" ]]; then
    echo "🔄 恢复所有中断的工作流..."
    for workflow_info in "${INTERRUPTED_WORKFLOWS[@]}"; do
        IFS=':' read -r task_id workflow_dir retry_count <<< "$workflow_info"
        recover_single_workflow "$task_id" "$workflow_dir" "$retry_count"
    done
else
    if [[ $choice -ge 1 ]] && [[ $choice -le ${#INTERRUPTED_WORKFLOWS[@]} ]]; then
        index=$((choice-1))
        IFS=':' read -r task_id workflow_dir retry_count <<< "${INTERRUPTED_WORKFLOWS[$index]}"
        recover_single_workflow "$task_id" "$workflow_dir" "$retry_count"
    else
        echo "❌ 无效的选择"
        exit 1
    fi
fi

recover_single_workflow() {
    local task_id=$1
    local workflow_dir=$2
    local retry_count=$3

    echo ""
    echo "🔄 恢复工作流: $task_id"
    echo "================================="

    # 2. 检查是否需要重置重试次数
    if [[ $retry_count -ge 3 ]]; then
        echo "⚠️  警告：此工作流已重试3次，已达到最大重试限制"
        echo "建议重新创建任务，或手动修复问题"

        # 生成故障报告
        generate_failure_report "$task_id" "$workflow_dir"
        return 1
    fi

    # 3. 读取当前状态
    status_file="$workflow_dir/state.json"
    if [[ ! -f "$status_file" ]]; then
        echo "❌ 状态文件不存在: $status_file"
        return 1
    fi

    # 4. 提取关键信息
    status=$(grep -o '"status":"[^"]*"' "$status_file" | cut -d'"' -f4)
    next_agent=$(grep -o '"next_agent":"[^"]*"' "$status_file" | cut -d'"' -f4)

    echo "📊 状态信息："
    echo "  - 当前状态: $status"
    echo "  - 下一步Agent: ${next_agent:-未设置}"
    echo "  - 重试次数: $retry_count/3"

    # 5. 创建恢复指令
    create_recovery_instructions "$task_id" "$status" "$next_agent"

    # 6. 更新重试计数
    update_retry_count "$task_id" "$workflow_dir" "$retry_count"

    echo "✅ 恢复指令已生成"
    echo ""
}

generate_failure_report() {
    local task_id=$1
    local workflow_dir=$2

    echo "📋 生成故障报告..."

    cat > "failure_report_${task_id}.md" << EOF
# ⛔ 工作流故障报告

## 任务ID
${task_id}

## 故障原因
已达到最大重试次数（3次），可能是由于：
1. API 400错误（上下文过长）
2. 任务描述过于复杂
3. 系统资源限制
4. 网络问题

## 故障位置
${workflow_dir}

## 建议解决方案
1. **拆分任务**：将大任务拆分成多个小任务
2. **简化描述**：减少不必要的上下文信息
3. **手动修复**：手动完成以下步骤：

## 恢复步骤
请根据当前状态手动完成：

### 当前状态信息：
\`\`\`json
$(cat "${workflow_dir}/state.json" | python -m json.tool)
\`\`\`

### 建议的恢复流程：
1. 清理临时文件
2. 简化任务描述
3. 重新启动工作流
4. 或手动完成剩余工作

## 归档建议
将此工作流标记为失败，并在日志中记录：

\`\`\`bash
python scripts/log_manager.py "❌ ${task_id} 因API 400错误中断，已达到最大重试次数，建议手动处理"
\`\`\`
EOF

    echo "📄 故障报告已生成: failure_report_${task_id}.md"
}

create_recovery_instructions() {
    local task_id=$1
    local status=$2
    local next_agent=$3

    echo "📝 创建恢复指令..."

    cat > "recovery_instructions_${task_id}.md" << EOF
# 🔄 工作流恢复指令

## 任务ID
${task_id}

## 当前状态
${status}

## 恢复步骤
请在**新的Claude Code窗口**中执行以下步骤：

### 第1步：检查中断点
查看以下文件了解中断位置：
1. \`${workflow_dir}/state.json\` - 当前工作流状态
2. \`${workflow_dir}/artifacts/\` - 已生成的中间文件
3. \`AI_WORKFLOW_LOG.md\` - 工作流历史记录

### 第2步：重置工作流
1. 复制以下恢复指令到新的Claude Code窗口
2. 等待系统自动从断点继续

### 第3步：恢复指令（复制到新的Claude Code窗口）
\`\`\`markdown
🤖 **恢复AII工作流 - 从断点继续**

工作流路径：O:\AII\上下文助手

任务ID：${task_id}
当前状态：${status}
下一步Agent：${next_agent:-需要检查state.json}

恢复指令：
1. 读取中断点状态文件：workflows/${task_id}/state.json
2. 检查重试次数：当前 ${retry_count}/3 次重试
3. 清空当前Claude Code对话历史（避免400错误）
4. 从断点处继续执行工作流
5. 使用简化的上下文重新开始

特别注意：
- 新的对话窗口开始
- 只加载必要的状态文件
- 输出保持简洁（≤1200 tokens）
- 如遇400错误，系统会自动重试

现在请从断点继续执行...
\`\`\`

### 第4步：执行恢复
1. 在新的Claude Code窗口中粘贴上面的恢复指令
2. 系统会自动检测中断点并从那里继续
3. 如果继续遇到400错误，会再次重试（最多总共3次）

### 第5步：验证结果
1. 检查 \`tasks/output_result.md\` 是否生成
2. 查看 \`AI_WORKFLOW_LOG.md\` 中的恢复记录
3. 确认工作流状态变为 "completed"

## 故障排除
如继续遇到问题：
1. 手动检查状态文件：\`cat ${workflow_dir}/state.json\`
2. 查看中间文件：\`ls ${workflow_dir}/artifacts/\`
3. 清理并重新开始：
   \`\`\`bash
   # 清理中断的工作流
   rm -rf ${workflow_dir}
   \`\`\`
4. 使用简化版本重新启动任务
EOF

    echo "📄 恢复指令已生成: recovery_instructions_${task_id}.md"
}

update_retry_count() {
    local task_id=$1
    local workflow_dir=$2
    local current_retry=$3

    # 增加重试计数
    new_retry=$((current_retry + 1))

    echo "📈 更新重试次数: $current_retry → $new_retry"

    # 更新日志
    python scripts/log_manager.py "🔄 ${task_id} 从中断恢复，重试次数: $new_retry/3"

    # 更新状态文件
    if [[ -f "$workflow_dir/state.json" ]]; then
        python -c "
import json
import sys
import os

workflow_dir = sys.argv[1]
new_retry = int(sys.argv[2])

state_file = os.path.join(workflow_dir, 'state.json')
with open(state_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

data['retry_count'] = new_retry
data['last_error'] = 'API 400错误中断 - 恢复中'

with open(state_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'✅ 状态文件已更新: retry_count = {new_retry}')
" "$workflow_dir" "$new_retry"
    fi
}

echo ""
echo "🎯 恢复完成！请在新的Claude Code窗口中："
echo "1. 打开 'recovery_instructions_${task_id}.md'"
echo "2. 复制恢复指令部分"
echo "3. 粘贴到新的Claude Code对话中"
echo "4. 按回车发送"
echo ""
echo "📋 工作流会从中断点继续执行，已重试次数: $((retry_count+1))/3"