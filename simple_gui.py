#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文助手 - 超简易可视化界面
专门为普通用户设计，最简单易用
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import os
import threading

class SimpleAssistantApp:
    """超简易界面，只有一个输入框和显示框"""

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("🤖 智能助手")
        self.window.geometry("500x600")
        self.window.configure(bg="#2c3e50")

        # 设置图标
        try:
            self.window.iconbitmap(default="")
        except:
            pass

        self.setup_ui()

    def setup_ui(self):
        """设置最简单的UI"""

        # 顶部标题
        title_frame = tk.Frame(self.window, bg="#3498db", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        title = tk.Label(title_frame, text="🤖 智能助手",
                        font=("Microsoft YaHei", 20, "bold"),
                        fg="white", bg="#3498db")
        title.pack(expand=True)

        # 副标题
        subtitle = tk.Label(title_frame, text="输入您的需求，我帮您处理",
                          font=("Microsoft YaHei", 10),
                          fg="#ecf0f1", bg="#3498db")
        subtitle.pack(pady=(0, 10))

        # 主内容区
        main_frame = tk.Frame(self.window, bg="#ecf0f1")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 输入区域
        input_label = tk.Label(main_frame, text="请输入：",
                              font=("Microsoft YaHei", 12, "bold"),
                              bg="#ecf0f1", anchor="w")
        input_label.pack(fill=tk.X, pady=(0, 10))

        self.input_text = tk.Text(main_frame, height=4,
                                 font=("Microsoft YaHei", 11),
                                 wrap=tk.WORD, relief=tk.SUNKEN)
        self.input_text.pack(fill=tk.X, pady=(0, 15))
        self.input_text.bind("<Return>", self.on_enter_pressed)

        # 示例提示
        examples = [
            "📝 示例：请帮我分析这个项目",
            "📝 示例：写一个Python脚本读取文件",
            "📝 示例：检查这段代码有什么问题",
        ]

        for example in examples:
            example_label = tk.Label(main_frame, text=example,
                                    font=("Microsoft YaHei", 9),
                                    bg="#ecf0f1", fg="#7f8c8d",
                                    justify=tk.LEFT, anchor="w")
            example_label.pack(fill=tk.X, pady=2)

        # 按钮区域
        button_frame = tk.Frame(main_frame, bg="#ecf0f1")
        button_frame.pack(fill=tk.X, pady=15)

        tk.Button(button_frame, text="🚀 开始处理",
                 command=self.process_input,
                 font=("Microsoft YaHei", 12, "bold"),
                 bg="#2ecc71", fg="white",
                 padx=30, pady=10,
                 relief=tk.FLAT).pack(side=tk.LEFT)

        tk.Button(button_frame, text="🗑️ 清空",
                 command=self.clear_all,
                 font=("Microsoft YaHei", 11),
                 bg="#e74c3c", fg="white",
                 padx=20, pady=10,
                 relief=tk.FLAT).pack(side=tk.RIGHT)

        # 输出区域
        output_label = tk.Label(main_frame, text="处理结果：",
                               font=("Microsoft YaHei", 12, "bold"),
                               bg="#ecf0f1", anchor="w")
        output_label.pack(fill=tk.X, pady=(20, 10))

        self.output_text = scrolledtext.ScrolledText(main_frame,
                                                    height=15,
                                                    font=("Consolas", 10),
                                                    wrap=tk.WORD,
                                                    relief=tk.SUNKEN)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # 底部状态栏
        status_frame = tk.Frame(self.window, bg="#34495e", height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(status_frame, text="就绪",
                                    font=("Microsoft YaHei", 9),
                                    fg="#ecf0f1", bg="#34495e")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # 其他功能按钮
        menu_frame = tk.Frame(status_frame, bg="#34495e")
        menu_frame.pack(side=tk.RIGHT, padx=10)

        tk.Button(menu_frame, text="🔧 系统测试",
                 command=self.run_system_test,
                 font=("Microsoft YaHei", 8),
                 bg="#34495e", fg="white",
                 relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

        tk.Button(menu_frame, text="📊 状态",
                 command=self.check_system_status,
                 font=("Microsoft YaHei", 8),
                 bg="#34495e", fg="white",
                 relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

        tk.Button(menu_frame, text="❓ 帮助",
                 command=self.show_help,
                 font=("Microsoft YaHei", 8),
                 bg="#34495e", fg="white",
                 relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

        # 焦点设置在输入框
        self.input_text.focus_set()

    def on_enter_pressed(self, event):
        """回车键事件"""
        self.process_input()
        return "break"  # 阻止默认行为

    def process_input(self):
        """处理用户输入"""
        user_input = self.input_text.get("1.0", tk.END).strip()

        if not user_input:
            messagebox.showwarning("提示", "请输入您的需求")
            return

        # 清空输入框
        self.input_text.delete("1.0", tk.END)

        # 显示用户输入
        self.append_output(f"🙋 您的需求：{user_input}\n")
        self.append_output("⏳ 正在处理，请稍候...\n")
        self.update_status("处理中...")

        # 在新线程中处理
        thread = threading.Thread(target=self.execute_task,
                                 args=(user_input,),
                                 daemon=True)
        thread.start()

    def execute_task(self, task):
        """执行任务"""

        try:
            # 切换到项目目录
            project_dir = os.path.dirname(os.path.abspath(__file__))
            original_dir = os.getcwd()
            os.chdir(project_dir)

            # 运行任务
            cmd = ["python", "cn_wrapper.py", "ww_simple.py", task]
            result = subprocess.run(cmd, capture_output=True,
                                   text=True, encoding='utf-8')

            # 切回原目录
            os.chdir(original_dir)

            # 在主线程中更新UI
            def update_ui():
                self.append_output("="*50 + "\n")

                if result.stdout:
                    self.append_output("✅ 处理完成：\n")
                    self.append_output(result.stdout + "\n")

                if result.stderr:
                    self.append_output("⚠️  注意：\n")
                    self.append_output(result.stderr + "\n")

                self.append_output("="*50 + "\n")
                self.append_output("💡 您可以继续输入其他需求\n\n")
                self.update_status("就绪")

            self.window.after(0, update_ui)

        except Exception as e:
            def show_error():
                self.append_output(f"❌ 执行失败：{str(e)}\n")
                self.update_status("错误")
            self.window.after(0, show_error)

    def append_output(self, text):
        """添加输出文本"""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.update()

    def clear_all(self):
        """清空所有"""
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        self.update_status("已清空")

    def update_status(self, status):
        """更新状态栏"""
        self.status_label.config(text=f"状态：{status}")

    def run_system_test(self):
        """运行系统测试"""
        response = messagebox.askyesno("系统测试", "运行测试需要一些时间，确定要继续吗？")
        if not response:
            return

        self.append_output("🧪 开始系统测试...\n")
        self.update_status("测试中")

        def test_thread():
            try:
                project_dir = os.path.dirname(os.path.abspath(__file__))
                original_dir = os.getcwd()
                os.chdir(project_dir)

                cmd = ["python", "cn_wrapper.py", "run_full_test_simple.py"]
                result = subprocess.run(cmd, capture_output=True,
                                       text=True, encoding='utf-8')

                os.chdir(original_dir)

                def update_result():
                    if "所有测试通过" in result.stdout:
                        self.append_output("✅ 所有测试通过！\n")
                    elif "测试发现问题" in result.stdout:
                        self.append_output("⚠️  测试发现问题\n")
                    else:
                        self.append_output("📋 测试完成\n")

                    # 显示关键信息
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if "通过率" in line or "测试时间" in line:
                            self.append_output(f"{line}\n")

                    self.update_status("测试完成")

                self.window.after(0, update_result)

            except Exception as e:
                def show_error():
                    self.append_output(f"❌ 测试失败：{str(e)}\n")
                    self.update_status("测试错误")
                self.window.after(0, show_error)

        threading.Thread(target=test_thread, daemon=True).start()

    def check_system_status(self):
        """检查系统状态"""
        self.append_output("📊 正在检查系统状态...\n")

        def status_thread():
            try:
                project_dir = os.path.dirname(os.path.abspath(__file__))
                original_dir = os.getcwd()
                os.chdir(project_dir)

                cmd = ["python", "cn_wrapper.py", "ww_simple.py", "status"]
                result = subprocess.run(cmd, capture_output=True,
                                       text=True, encoding='utf-8')

                os.chdir(original_dir)

                def update_status():
                    self.append_output(result.stdout + "\n")
                    if result.stderr:
                        self.append_output(result.stderr + "\n")

                self.window.after(0, update_status)

            except Exception as e:
                def show_error():
                    self.append_output(f"❌ 检查失败：{str(e)}\n")
                self.window.after(0, show_error)

        threading.Thread(target=status_thread, daemon=True).start()

    def show_help(self):
        """显示帮助"""
        help_text = """
🤖 智能助手 - 使用说明

使用方法：
1. 在上方输入框输入您的需求
2. 点击「开始处理」按钮或按回车键
3. 查看下方的处理结果

示例需求：
• 请帮我分析这个项目
• 写一个Python脚本
• 检查代码问题
• 创建网页设计

其他功能：
• 🔧 系统测试 - 验证功能是否正常
• 📊 状态 - 查看系统状态
• 🗑️ 清空 - 清空输入和输出

提示：描述越具体，处理结果越好！
        """
        messagebox.showinfo("使用帮助", help_text)

    def run(self):
        """运行应用"""
        try:
            self.window.mainloop()
        except Exception as e:
            print(f"程序错误：{e}")

def main():
    """主函数"""
    # 检查必要文件
    if not os.path.exists("ww_simple.py"):
        messagebox.showerror("错误", "请在项目目录中运行此程序")
        return

    if not os.path.exists("cn_wrapper.py"):
        messagebox.showerror("错误", "找不到编码包装器文件")
        return

    # 设置编码
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    app = SimpleAssistantApp()
    app.run()

if __name__ == "__main__":
    main()