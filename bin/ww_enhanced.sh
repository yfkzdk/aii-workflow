#!/bin/bash
# 🚀 AII工作流智能启动器 - Linux/Mac版
# 📖 使用方法: ww "你的任务描述"
# 🔧 增强版: 智能任务分类、自动恢复、彩色输出

WORKFLOW_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$WORKFLOW_DIR/ww_enhanced.py"

# 颜色定义
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
MAGENTA='\033[95m'
CYAN='\033[96m'
WHITE='\033[97m'
BOLD='\033[1m'
RESET='\033[0m'

# 颜色输出函数
print_success() {
    echo -e "${GREEN}✅ $1${RESET}"
}

print_error() {
    echo -e "${RED}❌ $1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${RESET}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${RESET}"
}

print_title() {
    echo -e "${CYAN}${BOLD}📌 $1${RESET}"
}

print_header() {
    echo
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${RESET}"
    echo -e "${CYAN}${BOLD}  $1${RESET}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${RESET}"
}

# 检查Python脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    print_error "Python脚本不存在: $PYTHON_SCRIPT"
    print_info "请确保 ww_enhanced.py 文件存在"
    exit 1
fi

# 检查Python是否可用
if ! command -v python3 &> /dev/null; then
    print_error "Python3未安装或不在PATH中"
    print_info "请安装Python 3.6+ 并添加到系统PATH"
    exit 1
fi

# 显示欢迎信息（无参数时）
if [ $# -eq 0 ]; then
    print_header "AII工作流智能启动器 v2.0"

    echo "使用方式:"
    echo "  ww \"任务描述\"         启动新任务"
    echo "  ww status             查看系统状态"
    echo "  ww recover            恢复中断任务"
    echo "  ww clean [天数]       清理旧数据"
    echo "  ww config 键 值       修改配置"
    echo "  ww guide              使用指南"
    echo "  ww version            版本信息"
    echo "  ww help               完整帮助"
    echo
    echo "示例:"
    echo "  ww \"帮我写一个Python脚本\""
    echo "  ww status"
    echo "  ww recover"
    echo "  ww clean 30"
    echo "  ww config auto_copy_to_clipboard false"
    echo
    echo "💡 提示: 直接输入任务描述即可，不需要\"start\""
    echo

    read -p "📝 请输入任务描述 (或按回车查看交互菜单): " task_desc

    if [ -z "$task_desc" ]; then
        # 进入交互模式
        echo
        python3 "$PYTHON_SCRIPT"
    else
        # 直接启动任务
        echo
        python3 "$PYTHON_SCRIPT" "$task_desc"
    fi

    exit 0
fi

# 检查第一个参数是否是命令
ARG1="$1"
IS_COMMAND=0

case "$ARG1" in
    status|recover|clean|config|guide|version|help)
        IS_COMMAND=1
        ;;
esac

# 处理命令
if [ $IS_COMMAND -eq 1 ]; then
    # 如果是命令，直接传递所有参数
    python3 "$PYTHON_SCRIPT" "$@"
else
    # 如果不是命令，则视为任务描述
    TASK_DESC="$*"

    print_header "启动新工作流任务"
    echo
    python3 "$PYTHON_SCRIPT" "$TASK_DESC"
fi

# 检查执行结果
if [ $? -eq 0 ]; then
    echo
    print_success "操作完成"
else
    echo
    print_error "操作失败"
fi

# 如果不是静默模式，等待用户按键
if [ "$1" != "-q" ] && [ "$1" != "--quiet" ]; then
    echo
    read -n 1 -s -r -p "按任意键继续..."
    echo
fi