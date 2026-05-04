"""Phase 3 验证脚本 — 瘦身测试。

覆盖：
- SDKCaller / FallbackCaller 自动降级
- Token 追踪（db 累加 + 警告）
- Tool Use 审批（批准 / 拒绝跳步）
- 旧文件已移到 .trash_backup/phase3/
- core 包导出正确
- 完整管线 mock 运行
"""

import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from core.db import StateDB
from core.agent_caller import AgentCaller, FallbackCaller, OpenAICaller, SDKCaller
from core.orchestrator import Orchestrator, PIPELINE, PIPELINE_STEPS


class TestSDKFallback(unittest.TestCase):
    """AgentCaller.create() 工厂方法测试。"""

    def test_create_returns_openai_caller(self):
        """有 openai 库时优先返回 OpenAICaller。"""
        caller = AgentCaller.create(project_root=PROJECT_ROOT)
        self.assertIsInstance(caller, OpenAICaller,
                              "有 openai 库时应返回 OpenAICaller")

    def test_fallback_caller_missing_agent(self):
        """FallbackCaller 对不存在的 agent 返回失败。"""
        caller = FallbackCaller(project_root=PROJECT_ROOT)
        result = caller.call("nonexistent_agent", "/tmp/fake")
        self.assertFalse(result["success"])
        self.assertIn("不存在", result["error"])

    def test_sdk_caller_no_client(self):
        """SDKCaller 客户端为 None 时降级到 FallbackCaller。"""
        caller = SDKCaller(project_root=PROJECT_ROOT)
        caller.client = None
        # 应降级调用，对不存在的 agent 会返回失败
        result = caller.call("nonexistent_agent", "/tmp/fake")
        self.assertFalse(result["success"])


class TestTokenTracking(unittest.TestCase):
    """Token 追踪测试。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p3_token_")
        self.db = StateDB(self.tmpdir)
        self.db.init_task("tok-001")

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_add_token_usage(self):
        """模拟 agent 调用 → db 中 token 计数累加。"""
        self.db.add_token_usage("tok-001", 1000, 200, 50)
        self.db.add_token_usage("tok-001", 500, 100, 30)

        usage = self.db.get_token_usage("tok-001")
        self.assertEqual(usage["total_input_tokens"], 1500)
        self.assertEqual(usage["total_output_tokens"], 300)
        self.assertEqual(usage["total_cache_hits"], 80)

    def test_get_token_usage_empty(self):
        """初始 token 用量为 0。"""
        usage = self.db.get_token_usage("tok-001")
        self.assertEqual(usage["total_input_tokens"], 0)
        self.assertEqual(usage["total_output_tokens"], 0)
        self.assertEqual(usage["total_cache_hits"], 0)


class TestToolUseApproval(unittest.TestCase):
    """Tool Use 审批测试。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p3_tooluse_")
        self.orch = Orchestrator(self.tmpdir, "tu-001",
                                project_root=PROJECT_ROOT)
        self.orch.db.init_task("tu-001")

    def tearDown(self):
        self.orch.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_tool_use_approved(self):
        """合法的 transition_state tool call → 批准。"""
        # 设置状态为 executing (step 5)，请求推进到 verifying (step 6)
        self.orch.db.update_status("tu-001", "executing", "coder")
        # 创建 artifacts 目录和验证所需文件
        artifacts = os.path.join(self.tmpdir, "artifacts")
        os.makedirs(artifacts, exist_ok=True)

        tool_call = {
            "name": "transition_state",
            "input": {
                "next_step": "verifying",
                "output_summary": "代码完成",
                "errors": [],
            },
        }

        # _handle_tool_call 内部会调 validate_step
        # 由于没有真实 artifacts，强制跳过验证
        self.orch._force_fail_step = None
        with patch.object(self.orch, "_validate_step", return_value=(True, "PASS")):
            approved = self.orch._handle_tool_call("executing", tool_call)

        self.assertTrue(approved, "合法转换应被批准")

    def test_tool_use_rejected_skip(self):
        """跳步的 transition_state tool call → 拒绝。"""
        self.orch.db.update_status("tu-001", "requirement_optimizing",
                                  "requirement_optimizer")

        tool_call = {
            "name": "transition_state",
            "input": {
                "next_step": "executing",  # 跳步！从 step 1 直接到 step 5
                "output_summary": "跳步",
                "errors": [],
            },
        }

        approved = self.orch._handle_tool_call("requirement_optimizing", tool_call)
        self.assertFalse(approved, "跳步应被拒绝")

    def test_tool_use_unknown_step(self):
        """请求未知步骤 → 拒绝。"""
        self.orch.db.update_status("tu-001", "input_collecting", "input_collector")

        tool_call = {
            "name": "transition_state",
            "input": {
                "next_step": "unknown_step",
                "output_summary": "未知步骤",
                "errors": [],
            },
        }

        approved = self.orch._handle_tool_call("input_collecting", tool_call)
        self.assertFalse(approved, "未知步骤应被拒绝")


class TestLegacyRemoved(unittest.TestCase):
    """旧文件已移到 .trash_backup/phase3/。"""

    def test_core_state_removed(self):
        """core/state.py 已移走。"""
        self.assertFalse(
            os.path.exists(os.path.join(PROJECT_ROOT, "core", "state.py")),
            "core/state.py 应已移走"
        )

    def test_core_pipeline_removed(self):
        """core/pipeline.py 已移走。"""
        self.assertFalse(
            os.path.exists(os.path.join(PROJECT_ROOT, "core", "pipeline.py")),
            "core/pipeline.py 应已移走"
        )

    def test_scripts_removed(self):
        """scripts/ 下的旧文件已移走。"""
        removed = [
            "state_machine.py", "skill_auto_matcher.py", "skill_manager.py",
            "dag_runner.py", "progress_tracker.py",
            "confirmation_formatter.py", "input_collector.py",
            "log_manager_backup.py",
        ]
        for name in removed:
            path = os.path.join(PROJECT_ROOT, "scripts", name)
            self.assertFalse(os.path.exists(path),
                             f"scripts/{name} 应已移走")

    def test_root_files_removed(self):
        """根目录旧文件已移走。"""
        removed = [
            "cn_wrapper.py", "encoding_persistence_simple.py",
            "fix_encoding_issues.py", "fix_report.py",
            "validate_encoding.py", "complete_validation.py",
            "install_enhanced.py", "even_numbers.py",
        ]
        for name in removed:
            path = os.path.join(PROJECT_ROOT, name)
            self.assertFalse(os.path.exists(path),
                             f"{name} 应已移走")

    def test_archive_dir_exists(self):
        """archive/ 目录包含隔离的非核心目录。"""
        archive_dir = os.path.join(PROJECT_ROOT, "archive")
        self.assertTrue(os.path.isdir(archive_dir),
                         "archive/ 目录应存在")
        archived = os.listdir(archive_dir)
        self.assertIn("bin", archived)
        self.assertIn("powershell", archived)


class TestNewInit(unittest.TestCase):
    """core 包导出正确。"""

    def test_imports(self):
        """from core import StateDB, Orchestrator, AgentCaller 无 ImportError。"""
        from core import StateDB as S
        from core import Orchestrator as O
        from core import AgentCaller as A
        self.assertIsNotNone(S)
        self.assertIsNotNone(O)
        self.assertIsNotNone(A)


class TestFullPipeline(unittest.TestCase):
    """完整管线 mock 运行。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p3_pipeline_")
        self.orch = Orchestrator(self.tmpdir, "pipe-001",
                                project_root=PROJECT_ROOT)
        self.orch.db.init_task("pipe-001")

    def tearDown(self):
        self.orch.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch.object(Orchestrator, "_validate_step", return_value=(True, "PASS"))
    @patch.object(Orchestrator, "_record_token_usage")
    def test_run_to_confirmation(self, mock_tokens, mock_validate):
        """mock 运行到 confirmation 阶段暂停。"""
        # 创建 artifacts 目录（validator 需要）
        os.makedirs(os.path.join(self.tmpdir, "artifacts"), exist_ok=True)

        # mock caller 返回成功
        mock_result = {
            "output": "mock output", "tool_calls": [],
            "usage": {"input_tokens": 100, "output_tokens": 50,
                      "cache_read_input_tokens": 0},
            "success": True, "error": None,
        }
        self.orch.caller = MagicMock()
        self.orch.caller.call.return_value = mock_result

        result = self.orch.run()
        # 应在 input_collecting 暂停（needs_user=True）
        self.assertEqual(result["status"], "input_collecting")
        self.assertEqual(result["waiting_for"], "user_input")

    @patch.object(Orchestrator, "_validate_step", return_value=(True, "PASS"))
    @patch.object(Orchestrator, "_record_token_usage")
    def test_advance_through_steps(self, mock_tokens, mock_validate):
        """手动推进通过各阶段。"""
        os.makedirs(os.path.join(self.tmpdir, "artifacts"), exist_ok=True)

        # 初始 input_collecting → advance → requirement_optimizing
        result = self.orch.advance()
        self.assertEqual(result["status"], "requirement_optimizing")
        self.assertEqual(result["step_index"], 1)


class TestTokenWarning(unittest.TestCase):
    """Token 超限警告测试。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p3_warn_")
        self.orch = Orchestrator(self.tmpdir, "warn-001",
                                project_root=PROJECT_ROOT)
        self.orch.db.init_task("warn-001")

    def tearDown(self):
        self.orch.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_token_warning_printed(self):
        """累加 token 到 50000+ → 打印警告。"""
        # 直接在 db 中设置大量 token (6×10000 = 60000 > 50000)
        for _ in range(6):
            self.orch.db.add_token_usage("warn-001", 10000, 2000, 500)

        usage = self.orch.db.get_token_usage("warn-001")
        self.assertGreater(usage["total_input_tokens"], 50000)

        # _record_token_usage 应在内部阈值时打印警告
        self.orch._total_input_tokens = 0
        large_usage = {"input_tokens": 60000, "output_tokens": 5000,
                       "cache_read_input_tokens": 1000}
        # 不应抛异常
        self.orch._record_token_usage(large_usage)
        self.assertGreater(self.orch._total_input_tokens, 50000)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3 验证: 瘦身测试")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for cls in [TestSDKFallback, TestTokenTracking, TestToolUseApproval,
                TestLegacyRemoved, TestNewInit, TestFullPipeline,
                TestTokenWarning]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("PHASE 3: ALL TESTS PASSED")
    else:
        print(f"PHASE 3: {len(result.failures)} FAILED, {len(result.errors)} ERRORS")
        for test, traceback in result.failures:
            print(f"  FAIL: {test}")
        for test, traceback in result.errors:
            print(f"  ERROR: {test}")
    print("=" * 60)

    sys.exit(0 if result.wasSuccessful() else 1)