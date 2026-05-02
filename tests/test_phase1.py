"""Phase 1 验证脚本 — 地基测试。

覆盖：
- StateDB: 初始化、推进、快照回滚、确认门、重试
- Orchestrator: 确认门三种决策
- AgentCaller: mock 模式，不调真实 CLI
"""

import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# 确保项目根目录在 path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from core.db import StateDB
from core.agent_caller import AgentCaller, FallbackCaller
from core.orchestrator import Orchestrator, PIPELINE


class TestStateDB(unittest.TestCase):
    """StateDB 核心功能测试。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="phase1_test_")
        self.db = StateDB(self.tmpdir)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_init(self):
        """初始化任务 → state.db 存在，status=input_collecting。"""
        state = self.db.init_task("test-001")
        db_path = os.path.join(self.tmpdir, "state.db")
        self.assertTrue(os.path.exists(db_path), "state.db 文件应存在")
        self.assertEqual(state["status"], "input_collecting")
        self.assertEqual(state["step_index"], 0)
        self.assertEqual(state["task_id"], "test-001")

    def test_advance(self):
        """推进到 requirement_optimizing → step_index=1。"""
        self.db.init_task("test-002")
        state = self.db.update_status("test-002", "requirement_optimizing",
                                     "requirement_optimizer")
        self.assertEqual(state["status"], "requirement_optimizing")
        self.assertEqual(state["step_index"], 1)

    def test_snapshot_rollback(self):
        """快照→修改状态→回滚→验证恢复。"""
        self.db.init_task("test-003")
        self.db.save_snapshot("test-003", label="initial")

        # 推进状态
        self.db.update_status("test-003", "requirement_optimizing",
                              "requirement_optimizer")
        modified = self.db.get_state("test-003")
        self.assertEqual(modified["status"], "requirement_optimizing")

        # 回滚
        ok = self.db.rollback("test-003", steps=1)
        self.assertTrue(ok, "回滚应成功")
        restored = self.db.get_state("test-003")
        self.assertEqual(restored["status"], "input_collecting",
                         "回滚后应恢复到 input_collecting")

    def test_retry(self):
        """increment_retry 3次 → retry_count=3。"""
        self.db.init_task("test-004")
        for _ in range(3):
            count = self.db.increment_retry("test-004")
        self.assertEqual(count, 3)
        state = self.db.get_state("test-004")
        self.assertEqual(state["retry_count"], 3)

    def test_list_tasks(self):
        """list_tasks 返回已初始化的任务。"""
        self.db.init_task("task-a")
        self.db.init_task("task-b")
        tasks = self.db.list_tasks()
        self.assertEqual(len(tasks), 2)
        task_ids = {t["task_id"] for t in tasks}
        self.assertIn("task-a", task_ids)
        self.assertIn("task-b", task_ids)

    def test_duplicate_init(self):
        """重复 init 同一 task_id 返回现有状态。"""
        s1 = self.db.init_task("test-dup")
        s2 = self.db.init_task("test-dup")
        self.assertEqual(s1["task_id"], s2["task_id"])
        tasks = self.db.list_tasks()
        self.assertEqual(len(tasks), 1)


class TestOrchestrator(unittest.TestCase):
    """Orchestrator 确认门测试。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="phase1_orch_")
        self.project_root = PROJECT_ROOT
        self.orch = Orchestrator(self.tmpdir, "orch-001",
                                project_root=self.project_root)
        self.orch.db.init_task("orch-001")

    def tearDown(self):
        self.orch.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _set_status(self, status: str, step_index: int):
        """手动设置任务状态到指定阶段。"""
        conn = self.orch.db._connect()
        conn.execute(
            "UPDATE task_state SET status=?, step_index=? WHERE task_id=?",
            (status, step_index, "orch-001"),
        )
        conn.commit()

    def test_confirmation_confirm(self):
        """确认门 confirm → 进入 planning。"""
        self._set_status("confirmation", 2)
        result = self.orch.handle_confirmation("confirm")
        self.assertEqual(result["result"], "confirmed")
        self.assertEqual(result["next"], "planning")
        state = self.orch.db.get_state("orch-001")
        self.assertEqual(state["status"], "planning")

    def test_confirmation_revise(self):
        """确认门 revise → 回到 requirement_optimizing。"""
        self._set_status("confirmation", 2)
        result = self.orch.handle_confirmation("revise")
        self.assertEqual(result["result"], "revised")
        self.assertEqual(result["next"], "requirement_optimizing")
        state = self.orch.db.get_state("orch-001")
        self.assertEqual(state["status"], "requirement_optimizing")

    def test_confirmation_reject(self):
        """确认门 reject → cancelled。"""
        self._set_status("confirmation", 2)
        result = self.orch.handle_confirmation("reject")
        self.assertEqual(result["result"], "cancelled")
        self.assertEqual(result["next"], "cancelled")
        state = self.orch.db.get_state("orch-001")
        self.assertEqual(state["status"], "cancelled")

    def test_advance(self):
        """advance 从 input_collecting 推进到 requirement_optimizing。"""
        result = self.orch.advance()
        self.assertEqual(result["status"], "requirement_optimizing")
        self.assertEqual(result["step_index"], 1)

    def test_handle_user_input(self):
        """handle_user_input 追加输入（结构化chunk）。"""
        result = self.orch.handle_user_input("帮我写个排序算法")
        import json
        user_input = json.loads(result["user_input_json"])
        # chunks 现在是字典列表 [{"seq": 0, "content": "..."}]
        chunks = user_input["chunks"]
        self.assertTrue(len(chunks) > 0)
        self.assertEqual(chunks[0]["content"], "帮我写个排序算法")
        self.assertEqual(chunks[0]["seq"], 0)

    def test_run_pause_at_input(self):
        """run 在 input_collecting 阶段暂停。"""
        result = self.orch.run()
        self.assertEqual(result["status"], "input_collecting")
        self.assertEqual(result["waiting_for"], "user_input")

    def test_run_pause_at_confirmation(self):
        """run 在 confirmation 阶段暂停。"""
        # 跳到 confirmation 阶段
        self._set_status("confirmation", 2)
        result = self.orch.run()
        self.assertEqual(result["status"], "confirmation")
        self.assertEqual(result["waiting_for"], "confirmation")


class TestAgentCaller(unittest.TestCase):
    """AgentCaller mock 测试，不调真实 CLI。"""

    def test_get_available_agents(self):
        """扫描 agents 目录返回可用 agent 列表。"""
        caller = FallbackCaller(project_root=PROJECT_ROOT)
        agents = caller.get_available_agents()
        self.assertIsInstance(agents, list)
        # 至少应包含 manifest 中定义的核心 agents
        expected = {"archivist", "coder", "planner", "prompt_optimizer",
                     "requirement_optimizer", "verifier"}
        self.assertTrue(expected.issubset(set(agents)),
                        f"缺少 agents: {expected - set(agents)}")

    def test_call_missing_agent(self):
        """调用不存在的 agent 返回失败。"""
        caller = FallbackCaller(project_root=PROJECT_ROOT)
        result = caller.call("nonexistent_agent", "/tmp/fake")
        self.assertFalse(result["success"])
        self.assertIn("不存在", result["error"])

    @patch("core.agent_caller.subprocess.run")
    def test_call_success(self, mock_run):
        """mock 调用成功场景。"""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="agent 输出", stderr=""
        )
        caller = FallbackCaller(project_root=PROJECT_ROOT)
        # 先确认有 agent 定义
        agents = caller.get_available_agents()
        if not agents:
            self.skipTest("无可用 agent 定义")

        result = caller.call(agents[0], "/tmp/fake", context="测试上下文")
        self.assertTrue(result["success"])
        self.assertEqual(result["output"], "agent 输出")

    @patch("core.agent_caller.subprocess.run")
    def test_call_failure(self, mock_run):
        """mock 调用失败场景。"""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error output"
        )
        caller = FallbackCaller(project_root=PROJECT_ROOT)
        agents = caller.get_available_agents()
        if not agents:
            self.skipTest("无可用 agent 定义")

        result = caller.call(agents[0], "/tmp/fake")
        self.assertFalse(result["success"])

    @patch("core.agent_caller.subprocess.run")
    def test_call_timeout(self, mock_run):
        """mock 超时场景。"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=300)
        caller = FallbackCaller(project_root=PROJECT_ROOT)
        agents = caller.get_available_agents()
        if not agents:
            self.skipTest("无可用 agent 定义")

        result = caller.call(agents[0], "/tmp/fake")
        self.assertFalse(result["success"])
        self.assertIn("超时", result["error"])


class TestPipeline(unittest.TestCase):
    """PIPELINE 常量与 manifest 一致性。"""

    def test_pipeline_stages_match_manifest(self):
        """PIPELINE 中的阶段名应与 manifest.json 一致。"""
        import json
        manifest_path = os.path.join(PROJECT_ROOT, ".claude", "agents", "manifest.json")
        if not os.path.exists(manifest_path):
            self.skipTest("manifest.json 不存在")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        pipeline_stages = [s for s, _, _ in PIPELINE]
        manifest_stages = manifest.get("pipeline", [])
        self.assertEqual(pipeline_stages, manifest_stages,
                         f"PIPELINE {pipeline_stages} 与 manifest {manifest_stages} 不一致")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1 验证: 地基测试")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 按顺序加载
    for cls in [TestStateDB, TestOrchestrator, TestAgentCaller, TestPipeline]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("PHASE 1: ALL TESTS PASSED")
    else:
        print(f"PHASE 1: {len(result.failures)} FAILED, {len(result.errors)} ERRORS")
        for test, traceback in result.failures:
            print(f"  FAIL: {test}")
        for test, traceback in result.errors:
            print(f"  ERROR: {test}")
    print("=" * 60)

    sys.exit(0 if result.wasSuccessful() else 1)