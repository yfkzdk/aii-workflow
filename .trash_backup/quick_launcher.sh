#!/usr/bin/env bash
# 上下文助手 - 快捷启动器
# 将此文件放在桌面或快捷方式位置，双击即可使用

cd "O:/AII/上下文助手"

echo "=========================================="
echo "          上下文助手启动中..."
echo "=========================================="
echo

# 检查必要文件
if [ ! -f "ww_simple.py" ]; then
    echo "❌ 错误: 找不到 ww_simple.py"
    echo "请确保在正确目录中运行"
    exit 1
fi

if [ ! -f "cn_wrapper.py" ]; then
    echo "❌ 错误: 找不到编码包装器"
    echo "请先运行编码修复"
    exit 1
fi

echo "✅ 系统检查完成"
echo

# 显示简单菜单
echo "选择使用方式:"
echo "1. 命令行模式 (功能最全)"
echo "2. 图形界面模式 (菜单选择)"
echo "3. 快速测试系统"
echo

read -p "请输入选项 (1-3): " choice

case $choice in
    1)
        echo
        echo "🚀 进入命令行模式..."
        echo "常用命令:"
        echo "  python ww_simple.py '任务描述'"
        echo "  python ww_simple.py status"
        echo "  python ww_simple.py recover"
        echo
        echo "提示: 如果有编码问题，使用: python cn_wrapper.py ww_simple.py '任务'"
        echo
        echo "输入 'exit' 返回菜单"
        echo "----------------------------------------"

        while true; do
            read -p "ww> " cmd
            if [ "$cmd" = "exit" ] || [ "$cmd" = "quit" ]; then
                echo "返回主菜单"
                exec "$0"
            fi

            if [ -n "$cmd" ]; then
                python cn_wrapper.py ww_simple.py "$cmd"
            fi
        done
        ;;
    2)
        python cn_wrapper.py user_interface.py
        ;;
    3)
        echo
        echo "🧪 运行系统测试..."
        python cn_wrapper.py run_full_test_simple.py
        echo
        read -p "按回车键继续..."
        exec "$0"
        ;;
    *)
        echo "无效选项"
        ;;
esac