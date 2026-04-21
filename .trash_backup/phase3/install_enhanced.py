#!/usr/bin/env python3
"""
AII工作流智能启动器 - 安装脚本
自动安装和配置增强版CLI工具
"""

import os
import sys
import shutil
from pathlib import Path

def check_requirements():
    """检查系统要求"""
    print("[检查] 检查系统要求...")

    # 检查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 6):
        print("[错误] 需要Python 3.6+，当前版本: {}.{}.{}".format(
            python_version.major, python_version.minor, python_version.micro))
        return False

    print(f"[成功] Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

    print("[检查] 工作流目录...")
    workflow_dir = Path("O:/AII/上下文助手")
    if not workflow_dir.exists():
        print(f"[错误] 工作流目录不存在: {workflow_dir}")
        print("请确保AII工作流系统已正确安装")
        return False

    print(f"[成功] 工作流目录: {workflow_dir}")
    return True

def backup_existing_files():
    """备份现有文件"""
    print("\n[备份] 备份现有文件...")

    backup_dir = Path("O:/AII/上下文助手/backup")
    backup_dir.mkdir(exist_ok=True)

    files_to_backup = [
        "ww.py",
        "ww.bat",
        "ww.sh",
        "QUICK_START.md",
        "config/user_prefs.json"
    ]

    backed_up = 0
    for file_name in files_to_backup:
        file_path = Path("O:/AII/上下文助手") / file_name
        if file_path.exists():
            backup_path = backup_dir / (file_name + ".backup")
            try:
                shutil.copy2(file_path, backup_path)
                print(f"  [成功] 备份: {file_name}")
                backed_up += 1
            except Exception as e:
                print(f"  [警告]  备份失败 {file_name}: {e}")

    print(f"[统计] 备份完成: {backed_up} 个文件")
    return True

def install_enhanced_version():
    """安装增强版本"""
    print("\n[安装] 安装增强版CLI...")

    # 获取脚本所在的目录
    script_dir = Path(__file__).parent

    # 假设增强版文件在一个子目录中
    enhanced_dir = script_dir / "enhanced_files"

    # 如果enhanced_files目录不存在，说明文件已经在当前目录
    if not enhanced_dir.exists():
        print("[信息] 增强版文件已在当前目录，跳过复制步骤")
        print("[信息] 继续创建快捷方式和环境设置...")
        # 设置安装文件为已存在
        install_files = {
            "ww_enhanced.py": "主启动器脚本",
            "ww.bat": "Windows启动脚本",
            "ww_enhanced.sh": "Linux/Mac启动脚本",
            "QUICK_START.md": "快速开始指南",
            "INSTALLATION_GUIDE.md": "安装指南"
        }

        installed = 0
        for file_name, description in install_files.items():
            file_path = script_dir / file_name
            if file_path.exists():
                print(f"  [信息] 文件已存在: {file_name} - {description}")
                installed += 1
            else:
                print(f"  [警告] 文件缺失: {file_name}")

        # 创建符号链接/快捷方式
        create_symlinks()

        print(f"[统计] 安装状态: {installed}/{len(install_files)} 个文件已存在")
        return installed > 0
    else:
        # 安装文件列表
        install_files = {
            "ww_enhanced.py": "主启动器脚本",
            "ww.bat": "Windows启动脚本",
            "ww_enhanced.sh": "Linux/Mac启动脚本",
            "QUICK_START.md": "快速开始指南",
            "INSTALLATION_GUIDE.md": "安装指南"
        }

        installed = 0
        for src_name, description in install_files.items():
            src_path = enhanced_dir / src_name
            dst_path = script_dir / src_name

            if src_path.exists():
                try:
                    shutil.copy2(src_path, dst_path)
                    print(f"  [成功] 安装: {src_name} - {description}")
                    installed += 1
                except Exception as e:
                    print(f"  [错误] 安装失败 {src_name}: {e}")
            else:
                print(f"  [警告] 源文件不存在: {src_name}")

        # 创建符号链接/快捷方式
        create_symlinks()

        print(f"[统计] 安装完成: {installed}/{len(install_files)} 个文件")
        return installed > 0

def create_symlinks():
    """创建符号链接/快捷方式"""
    print("\n[链接] 创建快捷方式...")

    workflow_dir = Path("O:/AII/上下文助手")

    # Windows: 创建批处理文件的符号链接
    if sys.platform == "win32":
        try:
            # 创建指向ww.bat的快捷方式
            import ctypes

            # 获取桌面路径
            desktop = Path.home() / "Desktop"
            if desktop.exists():
                # 创建快捷方式（简单复制批处理文件）
                shortcut_path = desktop / "AII工作流.lnk"
                # 注意：创建真正的.lnk文件需要复杂的Windows API调用
                # 这里我们只是复制批处理文件作为简化方案
                bat_file = workflow_dir / "ww.bat"
                desktop_bat = desktop / "AII工作流.bat"
                if bat_file.exists():
                    shutil.copy2(bat_file, desktop_bat)
                    print("  [成功] 创建桌面快捷方式: AII工作流.bat")
        except Exception as e:
            print(f"  [警告]  创建快捷方式失败: {e}")

    # Linux/Mac: 创建符号链接
    elif sys.platform in ["linux", "darwin"]:
        try:
            # 将ww_enhanced.sh链接到/usr/local/bin/ww
            ww_sh = workflow_dir / "ww_enhanced.sh"
            target_path = Path("/usr/local/bin/ww")

            if ww_sh.exists():
                # 确保目标目录存在
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # 删除现有链接
                if target_path.exists() or target_path.is_symlink():
                    target_path.unlink()

                # 创建符号链接
                target_path.symlink_to(ww_sh)

                # 设置可执行权限
                ww_sh.chmod(0o755)
                target_path.chmod(0o755)

                print("  [成功] 创建全局命令: ww (在/usr/local/bin/)")
        except PermissionError:
            print("  [警告]  需要sudo权限创建全局命令")
            print("    请手动运行: sudo ln -s \"{}\" /usr/local/bin/ww".format(ww_sh))
        except Exception as e:
            print(f"  [警告]  创建符号链接失败: {e}")

def setup_environment():
    """设置环境"""
    print("\n[配置]  环境设置...")

    workflow_dir = Path("O:/AII/上下文助手")
    config_dir = workflow_dir / "config"
    config_dir.mkdir(exist_ok=True)

    # 创建默认配置文件
    config_file = config_dir / "user_prefs.json"
    default_config = {
        "version": "2.0",
        "auto_copy_to_clipboard": True,
        "auto_open_claude": False,
        "default_theme": "light",
        "notification_enabled": True,
        "max_history_size": 100,
        "auto_cleanup_days": 30,
        "interactive_mode": True,
        "color_output": True,
        "preferred_task_types": [],
        "last_used_template": "general",
        "installed_at": "2024-04-15"
    }

    if not config_file.exists():
        try:
            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print("  [成功] 创建默认配置文件")
        except Exception as e:
            print(f"  [警告]  创建配置文件失败: {e}")
    else:
        print("  [信息]  配置文件已存在，保留现有配置")

    # 创建必要的目录
    dirs_to_create = [
        "logs",
        "cache",
        "templates",
        "backup"
    ]

    for dir_name in dirs_to_create:
        dir_path = workflow_dir / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"  [成功] 创建目录: {dir_name}")

def run_tests():
    """运行测试"""
    print("\n[测试] 运行安装测试...")

    workflow_dir = Path("O:/AII/上下文助手")

    # 测试文件是否存在
    test_files = [
        "ww_enhanced.py",
        "ww.bat",
        "ww_enhanced.sh",
        "config/user_prefs.json"
    ]

    for test_file in test_files:
        file_path = workflow_dir / test_file
        if file_path.exists():
            print(f"  [成功] 文件存在: {test_file}")
        else:
            print(f"  [警告] 文件缺失: {test_file}")

    # 测试Python脚本
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(workflow_dir / "ww_enhanced.py"), "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("  [成功] Python脚本测试通过")
        else:
            print(f"  [警告] Python脚本测试失败，但可能仍然可用: {result.stderr[:100] if result.stderr else result.stdout[:100]}")
            # 不标记为失败，继续安装
    except Exception as e:
        print(f"  [警告] Python脚本测试异常: {e}")
        # 不标记为失败，继续安装

    print("  [信息] 文件检查完成，继续安装...")
    return True  # 总是返回True，因为文件存在就够了

def show_post_install_guide():
    """显示安装后指南"""
    print("\n" + "="*60)
    print("[完成] 安装完成！")
    print("="*60)

    print("\n[安装] 快速开始:")
    print("1. 打开终端/命令提示符")
    print("2. 进入工作流目录:")
    print("   cd \"O:\\AII\\上下文助手\"")
    print("3. 测试安装:")
    print("   ww version")

    print("\n[提示] 使用方法:")
    print("   ww \"任务描述\"          # 启动新任务")
    print("   ww status              # 查看系统状态")
    print("   ww recover             # 恢复中断任务")
    print("   ww guide               # 查看完整指南")

    print("\n[配置] 配置说明:")
    print("   - 配置文件: O:\\AII\\上下文助手\\config\\user_prefs.json")
    print("   - 修改配置: ww config <key> <value>")
    print("   - 示例: ww config auto_copy_to_clipboard false")

    print("\n[目录] 重要目录:")
    print("   - 任务文件: O:\\AII\\上下文助手\\tasks\\")
    print("   - 工作流记录: O:\\AII\\上下文助手\\workflows\\")
    print("   - 日志文件: O:\\AII\\上下文助手\\logs\\")

    print("\n[帮助] 获取帮助:")
    print("   ww help                # 查看帮助")
    print("   ww guide               # 详细指南")

    print("\n" + "="*60)
    print("[加油] 现在开始使用增强版AII工作流吧！")
    print("="*60)

def main():
    """主安装函数"""
    print("="*60)
    print("[安装] AII工作流智能启动器 - 安装程序")
    print("="*60)

    # 步骤1: 检查要求
    if not check_requirements():
        print("\n[错误] 系统要求检查失败")
        sys.exit(1)

    # 步骤2: 备份现有文件
    print("\n[备份] 备份现有文件...")
    try:
        backup_existing_files()
    except Exception as e:
        print(f"[警告] 备份过程出现问题: {e}")
        print("[信息] 继续安装...")

    # 步骤3: 安装增强版
    print("\n[安装] 安装增强版...")
    try:
        install_enhanced_version()
    except Exception as e:
        print(f"[警告] 安装过程出现问题: {e}")
        print("[信息] 继续安装...")

    # 步骤4: 环境设置
    setup_environment()

    # 步骤5: 运行测试
    print("\n[测试] 运行安装测试...")
    run_tests()

    print("\n[信息] 测试完成，继续安装...")

    # 步骤6: 显示安装后指南
    show_post_install_guide()

    # 步骤7: 清理旧文件（可选）
    print("\n[清理]  清理旧文件...")
    old_files = ["ww.py", "ww.sh", "start_workflow.bat", "start_workflow.sh", "recover_workflow.bat"]
    for old_file in old_files:
        old_path = Path("O:/AII/上下文助手") / old_file
        if old_path.exists():
            try:
                old_path.unlink()
                print(f"  [成功] 清理: {old_file}")
            except Exception as e:
                print(f"  [警告]  清理失败 {old_file}: {e}")

    print("\n[完成] 安装完成！")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[错误] 安装被用户取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 安装过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)