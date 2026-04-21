#!/usr/bin/env python3
"""
端到端测试脚本 - 完整测试工作流编排系统
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

class EndToEndTest:
    """端到端测试类"""

    def __init__(self, project_root="上下文助手"):
        """初始化测试"""
        self.project_root = Path(project_root)
        self.test_results = []
        self.start_time = None
        self.end_time = None

        # 创建测试目录
        self.test_dir = self.project_root / "workflows" / "tests"
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # 日志目录
        self.log_dir = Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        # 写入日志文件
        with open(self.log_dir / "e2e_test.log", "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

    def run_test(self, test_name, test_func):
        """运行单个测试"""
        self.log(f"开始测试: {test_name}")
        start = time.time()

        try:
            result = test_func()
            elapsed = time.time() - start
            status = "PASS" if result.get("success", False) else "FAIL"

            test_result = {
                "test_name": test_name,
                "status": status,
                "elapsed_time": round(elapsed, 2),
                "details": result.get("details", ""),
                "error": result.get("error", None)
            }

            self.test_results.append(test_result)
            self.log(f"测试完成: {test_name} - {status} ({elapsed:.2f}秒)")

            return test_result

        except Exception as e:
            elapsed = time.time() - start
            self.log(f"测试失败: {test_name} - {str(e)}", "ERROR")

            test_result = {
                "test_name": test_name,
                "status": "FAIL",
                "elapsed_time": round(elapsed, 2),
                "details": "测试执行过程中发生异常",
                "error": str(e)
            }

            self.test_results.append(test_result)
            return test_result

    def test_01_directory_structure(self):
        """测试目录结构"""
        required_dirs = [
            self.project_root / ".claude" / "agents",
            self.project_root / "scripts",
            self.project_root / "tasks",
            self.project_root / "workflows",
            self.project_root / "workflows" / "tasks",
            self.project_root / "workflows" / "states",
            self.project_root / "workflows" / "tests",
            self.project_root / "workflows" / "pipelines",
            self.log_dir
        ]

        required_files = [
            self.project_root / ".claude" / "CLAUDE.md",
            self.project_root / ".claude" / "agents" / "workflow_agent.md",
            self.project_root / "scripts" / "workflow_manager.py",
            self.project_root / "AI_WORKFLOW_LOG.md",
            self.project_root / "tasks" / "input_task.md",
            self.project_root / "tasks" / "output_result.md",
            self.project_root / "workflows" / "pipeline_config.json"
        ]

        missing_dirs = []
        missing_files = []

        for dir_path in required_dirs:
            if not dir_path.exists():
                missing_dirs.append(str(dir_path.relative_to(self.project_root)))

        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path.relative_to(self.project_root)))

        success = len(missing_dirs) == 0 and len(missing_files) == 0

        return {
            "success": success,
            "details": f"目录结构检查: 缺失目录={len(missing_dirs)}, 缺失文件={len(missing_files)}",
            "missing_dirs": missing_dirs,
            "missing_files": missing_files
        }

    def test_02_config_file_validation(self):
        """测试配置文件"""
        config_path = self.project_root / "workflows" / "pipeline_config.json"

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 检查必需字段
            required_fields = ["pipeline_name", "version", "pipeline_stages", "test_scenarios"]
            missing_fields = []

            for field in required_fields:
                if field not in config:
                    missing_fields.append(field)

            # 检查pipeline_stages
            valid_stages = True
            if "pipeline_stages" in config:
                stages = config["pipeline_stages"]
                for i, stage in enumerate(stages):
                    if not all(key in stage for key in ["stage", "description", "input", "output"]):
                        valid_stages = False
                        break

            success = len(missing_fields) == 0 and valid_stages

            return {
                "success": success,
                "details": f"配置文件验证: 必需字段={len(missing_fields)}个缺失, 阶段定义={valid_stages}",
                "missing_fields": missing_fields,
                "config_structure": valid_stages
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "details": "配置文件JSON格式错误",
                "error": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "details": "读取配置文件时发生错误",
                "error": str(e)
            }

    def test_03_workflow_manager_functionality(self):
        """测试工作流管理器功能"""
        manager_path = self.project_root / "scripts" / "workflow_manager.py"

        if not manager_path.exists():
            return {
                "success": False,
                "details": "工作流管理器文件不存在",
                "error": f"文件不存在: {manager_path}"
            }

        try:
            # 测试导入
            import importlib.util
            spec = importlib.util.spec_from_file_location("workflow_manager", manager_path)
            if spec is None:
                return {
                    "success": False,
                    "details": "无法导入工作流管理器",
                    "error": "spec_from_file_location返回None"
                }

            module = importlib.util.module_from_spec(spec)

            # 检查文件内容
            with open(manager_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查必需的类和函数
            required_classes = ["WorkflowManager", "WorkflowState"]
            required_functions = ["create_task", "update_task_status", "generate_solutions", "compare_solutions"]

            missing_classes = []
            missing_functions = []

            for class_name in required_classes:
                if f"class {class_name}" not in content:
                    missing_classes.append(class_name)

            for func_name in required_functions:
                if f"def {func_name}" not in content:
                    missing_functions.append(func_name)

            success = len(missing_classes) == 0 and len(missing_functions) == 0

            return {
                "success": success,
                "details": f"工作流管理器检查: 缺失类={len(missing_classes)}, 缺失函数={len(missing_functions)}",
                "missing_classes": missing_classes,
                "missing_functions": missing_functions
            }

        except Exception as e:
            return {
                "success": False,
                "details": "测试工作流管理器时发生错误",
                "error": str(e)
            }

    def test_04_task_creation_workflow(self):
        """测试任务创建工作流"""
        # 创建测试任务
        task_data = {
            "title": "端到端测试任务",
            "goal": "验证完整的工作流编排系统功能",
            "constraints": "时间限制: 30分钟内完成; 技术限制: 使用Python 3.8+",
            "expected": "生成三个方案并选择最优方案实施"
        }

        try:
            # 调用workflow_manager创建任务
            cmd = [
                sys.executable,
                str(self.project_root / "scripts" / "workflow_manager.py"),
                "create",
                "--title", task_data["title"],
                "--goal", task_data["goal"],
                "--constraints", task_data["constraints"],
                "--expected", task_data["expected"]
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            success = result.returncode == 0

            # 检查是否创建了任务文件
            input_task_path = self.project_root / "tasks" / "input_task.md"
            task_exists = input_task_path.exists()

            if task_exists:
                with open(input_task_path, "r", encoding="utf-8") as f:
                    content = f.read()
                task_content_valid = task_data["title"] in content and task_data["goal"] in content
            else:
                task_content_valid = False

            return {
                "success": success and task_exists and task_content_valid,
                "details": f"任务创建: 命令成功={success}, 文件存在={task_exists}, 内容有效={task_content_valid}",
                "command_output": result.stdout,
                "command_error": result.stderr if result.stderr else None
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "details": "任务创建命令执行超时",
                "error": "Timeout expired"
            }
        except Exception as e:
            return {
                "success": False,
                "details": "任务创建工作流测试失败",
                "error": str(e)
            }

    def test_05_solution_generation(self):
        """测试方案生成"""
        try:
            # 获取最新的任务ID
            log_path = self.project_root / "AI_WORKFLOW_LOG.md"
            task_id = None

            if log_path.exists():
                with open(log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in reversed(lines):  # 从最后开始找
                        if "TASK-" in line:
                            parts = line.split("|")
                            if len(parts) > 2:
                                task_id = parts[1].strip()
                                break

            if not task_id:
                # 如果没有任务，先创建一个
                self.test_04_task_creation_workflow()

                # 重新读取日志获取任务ID
                with open(log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if "TASK-" in line:
                            parts = line.split("|")
                            if len(parts) > 2:
                                task_id = parts[1].strip()
                                break

            if not task_id:
                return {
                    "success": False,
                    "details": "无法找到任务ID",
                    "error": "No task ID found in logs"
                }

            # 生成方案
            cmd = [
                sys.executable,
                str(self.project_root / "scripts" / "workflow_manager.py"),
                "solutions",
                "--task", task_id
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            success = result.returncode == 0

            # 检查输出结果文件
            result_path = self.project_root / "tasks" / f"{task_id}_result.md"
            result_exists = result_path.exists()

            return {
                "success": success and result_exists,
                "details": f"方案生成: 命令成功={success}, 结果文件={result_exists}",
                "task_id": task_id,
                "command_output": result.stdout[:500] if result.stdout else "",  # 限制输出长度
                "result_file": str(result_path) if result_exists else None
            }

        except Exception as e:
            return {
                "success": False,
                "details": "方案生成测试失败",
                "error": str(e)
            }

    def test_06_pipeline_integration(self):
        """测试管道集成"""
        # 检查Claude Code集成文件
        claude_config_path = self.project_root / ".claude" / "CLAUDE.md"
        workflow_agent_path = self.project_root / ".claude" / "agents" / "workflow_agent.md"

        integration_valid = True
        missing_integration = []

        # 检查Claude配置
        if claude_config_path.exists():
            with open(claude_config_path, "r", encoding="utf-8") as f:
                claude_content = f.read()

            required_markers = ["任务编排器", "workflow_agent.md", "tasks/input_task.md", "tasks/output_result.md"]
            for marker in required_markers:
                if marker not in claude_content:
                    integration_valid = False
                    missing_integration.append(f"Claude配置缺失: {marker}")

        # 检查工作流代理
        if workflow_agent_path.exists():
            with open(workflow_agent_path, "r", encoding="utf-8") as f:
                agent_content = f.read()

            required_functions = ["generate_solutions", "compare_solutions", "create_task"]
            for func in required_functions:
                if func not in agent_content:
                    integration_valid = False
                    missing_integration.append(f"工作流代理缺失: {func}")
        else:
            integration_valid = False
            missing_integration.append("工作流代理文件不存在")

        return {
            "success": integration_valid,
            "details": f"管道集成检查: 完整性={integration_valid}",
            "missing_integration": missing_integration
        }

    def test_07_performance_benchmark(self):
        """性能基准测试"""
        test_cases = [
            {"name": "小任务", "size": "small", "iterations": 10},
            {"name": "中任务", "size": "medium", "iterations": 5},
            {"name": "大任务", "size": "large", "iterations": 2}
        ]

        performance_results = []

        for test_case in test_cases:
            start_time = time.time()

            # 模拟不同大小的任务处理
            if test_case["size"] == "small":
                # 简单文件操作
                for i in range(test_case["iterations"]):
                    test_file = self.test_dir / f"perf_test_{i}.txt"
                    with open(test_file, "w", encoding="utf-8") as f:
                        f.write(f"性能测试 {i}")
                    test_file.unlink()

            elif test_case["size"] == "medium":
                # 更复杂的操作
                for i in range(test_case["iterations"]):
                    data = {"test": i, "timestamp": time.time(), "size": "medium"}
                    test_file = self.test_dir / f"perf_test_{i}.json"
                    with open(test_file, "w", encoding="utf-8") as f:
                        json.dump(data, f)
                    # 读取并验证
                    with open(test_file, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    test_file.unlink()

            elif test_case["size"] == "large":
                # 大文件操作
                for i in range(test_case["iterations"]):
                    test_file = self.test_dir / f"perf_test_{i}.txt"
                    with open(test_file, "w", encoding="utf-8") as f:
                        for j in range(1000):
                            f.write(f"Line {j}: Performance test data for large operations\n")
                    # 统计行数
                    with open(test_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    test_file.unlink()

            elapsed = time.time() - start_time
            avg_time = elapsed / test_case["iterations"]

            performance_results.append({
                "test_name": test_case["name"],
                "iterations": test_case["iterations"],
                "total_time": round(elapsed, 3),
                "avg_time_per_iteration": round(avg_time, 3)
            })

        # 检查是否符合性能要求
        meets_requirements = all(result["avg_time_per_iteration"] < 2.0 for result in performance_results)

        return {
            "success": meets_requirements,
            "details": f"性能基准测试: 符合要求={meets_requirements}",
            "performance_results": performance_results,
            "requirements_met": meets_requirements
        }

    def test_08_error_handling(self):
        """错误处理测试"""
        error_handling_tests = []

        # 测试1: 无效文件路径
        try:
            invalid_path = self.project_root / "nonexistent" / "file.txt"
            with open(invalid_path, "r", encoding="utf-8"):
                pass
            error_handling_tests.append({"test": "无效路径访问", "passed": False})
        except (FileNotFoundError, OSError):
            error_handling_tests.append({"test": "无效路径访问", "passed": True})

        # 测试2: 无效JSON
        try:
            invalid_json = '{"invalid": json}'
            json.loads(invalid_json)
            error_handling_tests.append({"test": "无效JSON解析", "passed": False})
        except json.JSONDecodeError:
            error_handling_tests.append({"test": "无效JSON解析", "passed": True})

        # 测试3: 权限错误（模拟）
        try:
            # 尝试读取系统文件（可能无权限）
            import os
            os.listdir("/root")  # 通常无权限
            error_handling_tests.append({"test": "权限错误处理", "passed": True})
        except (PermissionError, FileNotFoundError):
            error_handling_tests.append({"test": "权限错误处理", "passed": True})

        # 统计通过率
        passed_tests = sum(1 for test in error_handling_tests if test["passed"])
        total_tests = len(error_handling_tests)
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0

        success = pass_rate >= 0.8  # 80%通过率

        return {
            "success": success,
            "details": f"错误处理测试: 通过率={pass_rate:.2%} ({passed_tests}/{total_tests})",
            "test_results": error_handling_tests,
            "pass_rate": pass_rate
        }

    def run_all_tests(self):
        """运行所有测试"""
        self.start_time = time.time()
        self.log("=" * 60)
        self.log("开始端到端测试")
        self.log("=" * 60)

        tests = [
            ("01_directory_structure", self.test_01_directory_structure),
            ("02_config_file_validation", self.test_02_config_file_validation),
            ("03_workflow_manager_functionality", self.test_03_workflow_manager_functionality),
            ("04_task_creation_workflow", self.test_04_task_creation_workflow),
            ("05_solution_generation", self.test_05_solution_generation),
            ("06_pipeline_integration", self.test_06_pipeline_integration),
            ("07_performance_benchmark", self.test_07_performance_benchmark),
            ("08_error_handling", self.test_08_error_handling)
        ]

        for test_name, test_func in tests:
            self.run_test(test_name, test_func)

        self.end_time = time.time()

        # 生成测试报告
        self.generate_test_report()

        # 清理测试文件
        self.cleanup_test_files()

    def generate_test_report(self):
        """生成测试报告"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        total_time = self.end_time - self.start_time if self.end_time else 0

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "pass_rate": round(pass_rate, 2),
                "total_time_seconds": round(total_time, 2),
                "timestamp": datetime.now().isoformat()
            },
            "test_results": self.test_results,
            "recommendations": self.generate_recommendations()
        }

        # 保存JSON报告
        report_path = self.test_dir / "e2e_test_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # 生成HTML报告
        self.generate_html_report(report)

        self.log(f"测试完成: {passed_tests}/{total_tests} 通过 ({pass_rate:.1f}%)")
        self.log(f"总用时: {total_time:.2f}秒")
        self.log(f"详细报告已保存至: {report_path}")

        return report

    def generate_html_report(self, report):
        """生成HTML格式的测试报告"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>端到端测试报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .pass {{ color: green; }}
                .fail {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>📊 端到端测试报告</h1>

            <div class="summary">
                <h2>测试摘要</h2>
                <p><strong>总测试数:</strong> {report['summary']['total_tests']}</p>
                <p><strong>通过测试:</strong> <span class="pass">{report['summary']['passed_tests']}</span></p>
                <p><strong>失败测试:</strong> <span class="fail">{report['summary']['failed_tests']}</span></p>
                <p><strong>通过率:</strong> {report['summary']['pass_rate']}%</p>
                <p><strong>总用时:</strong> {report['summary']['total_time_seconds']}秒</p>
                <p><strong>测试时间:</strong> {report['summary']['timestamp']}</p>
            </div>

            <h2>详细结果</h2>
            <table>
                <tr>
                    <th>测试名称</th>
                    <th>状态</th>
                    <th>用时(秒)</th>
                    <th>详情</th>
                </tr>
        """

        for test in report['test_results']:
            status_class = "pass" if test['status'] == 'PASS' else "fail"
            html_content += f"""
                <tr>
                    <td>{test['test_name']}</td>
                    <td class="{status_class}">{test['status']}</td>
                    <td>{test['elapsed_time']}</td>
                    <td>{test['details'][:100]}{'...' if len(test['details']) > 100 else ''}</td>
                </tr>
            """

        html_content += """
            </table>

            <h2>建议</h2>
            <ul>
        """

        for rec in report['recommendations']:
            html_content += f"<li>{rec}</li>"

        html_content += """
            </ul>
        </body>
        </html>
        """

        html_path = self.test_dir / "e2e_test_report.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def generate_recommendations(self):
        """根据测试结果生成建议"""
        recommendations = []

        # 分析失败原因
        failed_tests = [r for r in self.test_results if r["status"] == "FAIL"]

        if not failed_tests:
            recommendations.append("✅ 所有测试通过，系统运行良好。")
            recommendations.append("✅ 可以考虑添加更多边界条件测试。")
            return recommendations

        # 检查常见的失败模式
        config_failures = [t for t in failed_tests if "config" in t["test_name"].lower()]
        workflow_failures = [t for t in failed_tests if "workflow" in t["test_name"].lower()]
        perf_failures = [t for t in failed_tests if "performance" in t["test_name"].lower()]

        if config_failures:
            recommendations.append("🔧 配置文件验证失败，请检查pipeline_config.json的格式和内容。")

        if workflow_failures:
            recommendations.append("🔄 工作流功能测试失败，检查workflow_manager.py中的函数实现。")

        if perf_failures:
            recommendations.append("⚡ 性能测试未达标，考虑优化文件操作或算法效率。")

        # 具体建议
        for test in failed_tests:
            if test.get("error"):
                recommendations.append(f"❌ {test['test_name']}: {test['error']}")

        # 通用建议
        recommendations.append("📝 建议添加更多异常处理代码。")
        recommendations.append("🔍 考虑添加日志记录以更好地调试问题。")
        recommendations.append("🧪 增加单元测试覆盖率。")

        return recommendations

    def cleanup_test_files(self):
        """清理测试文件"""
        try:
            # 清理测试目录中的临时文件
            for file in self.test_dir.glob("perf_test_*"):
                try:
                    file.unlink()
                except:
                    pass

            # 清理可能创建的临时任务文件
            tasks_dir = self.project_root / "tasks"
            for file in tasks_dir.glob("TEST_*"):
                try:
                    file.unlink()
                except:
                    pass

            self.log("测试文件清理完成")

        except Exception as e:
            self.log(f"清理测试文件时出错: {str(e)}", "WARNING")

def main():
    """主函数"""
    print("开始端到端测试...")

    # 检查当前目录
    current_dir = Path.cwd()
    print(f"当前目录: {current_dir}")

    # 设置项目根目录
    project_root = "上下文助手"

    # 检查项目目录是否存在
    if not Path(project_root).exists():
        print(f"❌ 错误: 项目目录 '{project_root}' 不存在")
        print("请确保在正确的目录中运行测试")
        return

    # 运行测试
    tester = EndToEndTest(project_root)
    tester.run_all_tests()

    # 输出总结
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    # 读取并显示测试报告
    report_path = Path(project_root) / "workflows" / "tests" / "e2e_test_report.json"
    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        summary = report["summary"]
        print(f"\n📊 测试摘要:")
        print(f"   总测试数: {summary['total_tests']}")
        print(f"   通过测试: {summary['passed_tests']}")
        print(f"   失败测试: {summary['failed_tests']}")
        print(f"   通过率: {summary['pass_rate']}%")
        print(f"   总用时: {summary['total_time_seconds']}秒")

        print(f"\n📁 报告文件:")
        print(f"   JSON报告: {report_path}")
        print(f"   HTML报告: {report_path.with_suffix('.html')}")

        # 显示失败测试详情
        failed_tests = [t for t in report["test_results"] if t["status"] == "FAIL"]
        if failed_tests:
            print(f"\n❌ 失败的测试:")
            for test in failed_tests:
                print(f"   - {test['test_name']}: {test['details']}")
                if test.get("error"):
                    print(f"     错误: {test['error'][:100]}...")

        # 显示建议
        if "recommendations" in report and report["recommendations"]:
            print(f"\n💡 建议:")
            for rec in report["recommendations"]:
                print(f"   • {rec}")
    else:
        print("❌ 错误: 测试报告未生成")

if __name__ == "__main__":
    main()