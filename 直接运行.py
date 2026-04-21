#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双击直接运行的智能助手
不需要.bat文件，直接运行这个.py文件
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox

def check_environment():
    """检查环境"""
    checks = []

    # 检查Python
    try:
        import tkinter
        checks.append(("Python环境", "✅ 正常"))
    except ImportError:
        checks.append(("Python环境", "❌ 缺少Tkinter"))
        return False, checks

    # 检查必要文件
    required_files = ["ww_simple.py", "cn_wrapper.py"]
    for file in required_files:
        if os.path.exists(file):
            checks.append((f"文件: {file}", "✅ 存在"))
        else:
            checks.append((f"文件: {file}", "❌ 不存在"))
            return False, checks

    return True, checks

def run_simple_gui():
    """运行简单图形界面"""
    try:
        # 切换到当前目录
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # 运行简单界面
        import subprocess
        result = subprocess.run([sys.executable, "simple_gui.py"],
                              capture_output=True, text=True)

        if result.returncode != 0:
            messagebox.showerror("启动失败",
                               f"无法启动图形界面\n\n错误信息:\n{result.stderr}")
            return False
        return True

    except Exception as e:
        messagebox.showerror("错误", f"启动失败: {str(e)}")
        return False

def create_desktop_shortcut():
    """创建桌面快捷方式（可选）"""
    try:
        import winshell
        from win32com.client import Dispatch

        desktop = winshell.desktop()
        shortcut_path = os.path.join(desktop, "智能助手.lnk")

        target = os.path.abspath(__file__)
        work_dir = os.path.dirname(target)

        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = f'"{target}"'
        shortcut.WorkingDirectory = work_dir
        shortcut.IconLocation = sys.executable
        shortcut.save()

        return True, shortcut_path
    except:
        return False, ""

def main():
    """主函数"""

    # 检查环境
    success, checks = check_environment()

    if not success:
        # 显示环境问题
        error_msg = "环境检查失败:\n\n"
        for name, status in checks:
            error_msg += f"{name}: {status}\n"

        error_msg += "\n请确保:\n1. 安装了Python 3.x\n2. 安装了Tkinter: pip install tk\n3. 所有必要文件存在"
        messagebox.showerror("环境错误", error_msg)
        return

    # 询问用户
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    response = messagebox.askyesno("智能助手",
                                  "欢迎使用智能助手！\n\n" +
                                  "环境检查通过，是否启动图形界面？\n\n" +
                                  "点击'是'启动助手\n" +
                                  "点击'否'查看其他选项")

    if response:
        # 启动图形界面
        if run_simple_gui():
            messagebox.showinfo("成功", "智能助手已启动！")
    else:
        # 显示选项
        option_response = messagebox.askyesno("选项",
                                            "选择操作方式:\n\n" +
                                            "是 → 创建桌面快捷方式\n" +
                                            "否 → 显示命令行使用方法")

        if option_response:
            # 创建桌面快捷方式
            success, shortcut_path = create_desktop_shortcut()
            if success:
                messagebox.showinfo("成功", f"已在桌面创建快捷方式:\n{shortcut_path}")
            else:
                messagebox.showwarning("提示", "无法创建快捷方式，请手动操作")
        else:
            # 显示命令行用法
            cmd_usage = """
📋 命令行使用方法：

1. 打开命令提示符：
   Win + R 输入 "cmd" 回车

2. 切换到项目目录：
   cd O:\\AII\\上下文助手

3. 运行以下命令之一：
   • python simple_gui.py    (图形界面)
   • python ww_simple.py "您的需求"  (命令行)

4. 如果有编码问题：
   python cn_wrapper.py ww_simple.py "您的需求"
            """
            messagebox.showinfo("命令行用法", cmd_usage)

    root.destroy()

if __name__ == "__main__":
    # 设置编码
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    # 检查是否在项目目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(current_dir, "ww_simple.py")):
        # 不在项目目录，尝试查找
        possible_paths = [
            "O:/AII/上下文助手",
            os.path.join(os.path.expanduser("~"), "AII", "上下文助手"),
            "上下文助手"
        ]

        for path in possible_paths:
            if os.path.exists(os.path.join(path, "ww_simple.py")):
                os.chdir(path)
                break

        # 如果还是找不到，显示错误
        if not os.path.exists("ww_simple.py"):
            tk.Tk().withdraw()
            messagebox.showerror("错误",
                               f"找不到项目文件\n当前目录: {current_dir}\n\n请确保在正确目录中运行")
            sys.exit(1)

    main()