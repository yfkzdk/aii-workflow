"""Unit tests for core stability components."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from core.event_sourced_state import (
    EventStore,
    EventSourcedStateMachine,
    EventType,
    StateEvent,
)
from core.heartbeat_checkpoint import HeartbeatCheckpoint, HeartbeatManager
from core.pipeline_snapshot import PipelineSnapshot, PipelineSnapshotManager
from core.priority_queue import PrioritySkillQueue, SkillPriority
from core.retry_policy import RetryPolicy, clamped_poisson_interval
from core.saga_orchestrator import SagaOrchestrator, SagaState
from core.skill_orchestrator import SkillOrchestrator, SkillResult


class TestRetryPolicy:
    """Tests for RetryPolicy"""

    def test_default_policy_retryable_errors(self):
        """Default policy should retry transient errors"""
        policy = RetryPolicy()

        # Transient errors are retryable
        assert policy.should_retry_error("EXE-101") is True
        assert policy.should_retry_error("EXE-102") is True
        assert policy.should_retry_error("EXE-104") is True
        assert policy.should_retry_error("EXE-106") is True

        # Config errors are not retryable
        assert policy.should_retry_error("CFG-001") is False
        assert policy.should_retry_error("CFG-002") is False

    def test_custom_retryable_whitelist(self):
        """Whitelist should override default behavior"""
        policy = RetryPolicy(retryable_error_types=["EXE-101", "EXE-102"])

        assert policy.should_retry_error("EXE-101") is True
        assert policy.should_retry_error("EXE-102") is True
        assert policy.should_retry_error("EXE-104") is False  # Not in whitelist

    def test_custom_non_retryable_blacklist(self):
        """Blacklist should exclude specific errors"""
        policy = RetryPolicy(non_retryable_error_types=["EXE-101"])

        assert policy.should_retry_error("EXE-101") is False
        assert policy.should_retry_error("EXE-102") is True

    def test_backoff_with_poisson_jitter(self):
        """Backoff should use Poisson jitter"""
        policy = RetryPolicy(
            initial_interval_seconds=1.0,
            backoff_coefficient=2.0,
            maximum_interval_seconds=60.0,
        )

        # Test exponential backoff
        delay1 = policy.calculate_backoff(0)
        delay2 = policy.calculate_backoff(1)
        delay3 = policy.calculate_backoff(2)

        # Delays should increase exponentially (with jitter)
        # With clamping_factor=0.3, bounds are [0.7x, 1.3x]
        assert 0.7 <= delay1 <= 1.3  # ~1.0
        assert 1.4 <= delay2 <= 2.6  # ~2.0
        # delay3 = 1.0 * 2^2 = 4.0, with jitter [2.8, 5.2]
        assert 2.8 <= delay3 <= 5.2  # ~4.0

    def test_maximum_interval_cap(self):
        """Backoff should cap at maximum_interval_seconds"""
        policy = RetryPolicy(
            initial_interval_seconds=10.0,
            backoff_coefficient=10.0,
            maximum_interval_seconds=60.0,
        )

        delay = policy.calculate_backoff(10)  # Would be 10^11 without cap
        assert delay <= 60.0 * 1.3  # Cap with jitter


class TestClampedPoissonInterval:
    """Tests for Poisson jitter implementation"""

    def test_average_preserved(self):
        """Average of samples should approximate input"""
        samples = [clamped_poisson_interval(1.0, 0.3) for _ in range(1000)]
        avg = sum(samples) / len(samples)
        assert 0.95 <= avg <= 1.05  # Should be close to 1.0

    def test_clamping_bounds(self):
        """Samples should stay within clamping bounds"""
        for _ in range(100):
            sample = clamped_poisson_interval(1.0, 0.3)
            assert 0.7 <= sample <= 1.3  # [0.7x, 1.3x]

    def test_zero_clamping_returns_average(self):
        """Zero clamping factor should return exact average"""
        sample = clamped_poisson_interval(1.0, 0.0)
        assert sample == 1.0


class TestPriorityQueue:
    """Tests for PrioritySkillQueue"""

    def test_priority_ordering(self):
        """Higher priority skills should execute first"""
        queue = PrioritySkillQueue()
        queue.push("skill-c", SkillPriority.DEFER)
        queue.push("skill-a", SkillPriority.CRITICAL)
        queue.push("skill-b", SkillPriority.READY)

        assert queue.pop().skill_name == "skill-a"
        assert queue.pop().skill_name == "skill-b"
        assert queue.pop().skill_name == "skill-c"

    def test_duplicate_update(self):
        """Pushing duplicate should update priority"""
        queue = PrioritySkillQueue()
        queue.push("skill-1", SkillPriority.DEFER)
        queue.push("skill-1", SkillPriority.CRITICAL)

        assert queue.get_priority("skill-1") == SkillPriority.CRITICAL
        assert len(queue) == 1

    def test_reprioritize(self):
        """Should support dynamic reprioritization"""
        queue = PrioritySkillQueue()
        queue.push("skill-1", SkillPriority.BLOCKED)

        queue.reprioritize("skill-1", SkillPriority.READY)
        assert queue.get_priority("skill-1") == SkillPriority.READY

    def test_serialization(self):
        """Queue should serialize/deserialize correctly"""
        queue = PrioritySkillQueue()
        queue.push("skill-a", SkillPriority.CRITICAL, {"param": 1})
        queue.push("skill-b", SkillPriority.DEFER, {"param": 2})

        data = queue.to_dict()
        restored = PrioritySkillQueue.from_dict(data)

        assert restored.get_priority("skill-a") == SkillPriority.CRITICAL
        assert restored.get_priority("skill-b") == SkillPriority.DEFER


class TestHeartbeatCheckpoint:
    """Tests for HeartbeatCheckpoint"""

    def test_heartbeat_updates(self):
        """Heartbeat should update timestamp and details"""
        checkpoint = HeartbeatCheckpoint(skill_name="test-skill")
        checkpoint.heartbeat({"phase": "processing"})

        assert checkpoint.last_heartbeat_time > 0
        assert checkpoint.heartbeat_details["phase"] == "processing"
        assert checkpoint.missed_heartbeats == 0

    def test_health_check(self):
        """Health check should detect missed heartbeats"""
        checkpoint = HeartbeatCheckpoint(
            skill_name="test-skill",
            heartbeat_interval_seconds=0.1,
            max_missed_heartbeats=2,
        )

        # Initially healthy
        assert checkpoint.check_health() is True

        # Simulate time passing
        checkpoint.last_heartbeat_time = time.time() - 0.5
        assert checkpoint.check_health() is False  # Missed

    def test_persistence(self):
        """Checkpoint should persist and load correctly"""
        with tempfile.TemporaryDirectory() as d:
            checkpoint = HeartbeatCheckpoint(
                skill_name="test-skill",
                artifacts_dir=Path(d),
            )
            checkpoint.heartbeat({"progress": 50})

            # Load from disk
            loaded = HeartbeatCheckpoint.load(Path(d), "test-skill")
            assert loaded is not None
            assert loaded.heartbeat_details["progress"] == 50


class TestPipelineSnapshot:
    """Tests for PipelineSnapshot"""

    def test_snapshot_creation(self):
        """Snapshot should capture pipeline state"""
        snapshot = PipelineSnapshot(
            stage="executing",
            completed_skills=["skill-a", "skill-b"],
            skill_results={"skill-a": {"status": "success"}},
            trace_id="trace-123",
        )

        data = snapshot.to_dict()
        assert data["stage"] == "executing"
        assert len(data["completed_skills"]) == 2

    def test_snapshot_save_load(self):
        """Snapshot should save and load correctly"""
        with tempfile.TemporaryDirectory() as d:
            snapshot = PipelineSnapshot(
                stage="executing",
                trace_id="trace-123",
            )
            path = Path(d) / "snapshot.json"
            snapshot.save(path)

            loaded = PipelineSnapshot.load(path)
            assert loaded is not None
            assert loaded.stage == "executing"
            assert loaded.trace_id == "trace-123"

    def test_snapshot_manager(self):
        """Snapshot manager should handle multiple snapshots"""
        with tempfile.TemporaryDirectory() as d:
            manager = PipelineSnapshotManager(Path(d))

            snapshot1 = PipelineSnapshot(stage="stage-1", trace_id="trace-1")
            snapshot2 = PipelineSnapshot(stage="stage-2", trace_id="trace-2")

            manager.save_snapshot(snapshot1)
            time.sleep(0.01)  # Ensure different timestamp
            manager.save_snapshot(snapshot2)

            latest = manager.load_latest_snapshot()
            assert latest is not None
            assert latest.stage == "stage-2"


class TestEventSourcedState:
    """Tests for EventSourcedStateMachine"""

    def test_event_append_and_replay(self):
        """Events should be appended and replayed correctly"""
        with tempfile.TemporaryDirectory() as d:
            store = EventStore(Path(d) / "events.jsonl")
            sm = EventSourcedStateMachine(trace_id="test", event_store=store)

            sm.enter_stage("executing")
            sm.record_skill_result("skill-a", {"status": "success"})
            sm.block("critical failure")

            # Replay from events
            sm2 = EventSourcedStateMachine.recover("test", Path(d) / "events.jsonl")
            assert sm2.current_stage == "executing"
            assert sm2.blocked_reason == "critical failure"
            assert "skill-a" in sm2.skill_results

    def test_idempotency(self):
        """Events with same idempotency key should not duplicate"""
        with tempfile.TemporaryDirectory() as d:
            store = EventStore(Path(d) / "events.jsonl")

            event = StateEvent(
                event_id=0,
                event_type=EventType.STAGE_ENTERED,
                timestamp="2026-01-01T00:00:00",
                trace_id="test",
                payload={"stage": "init"},
                idempotency_key="unique-key-1",
            )

            store.append(event)
            store.append(event)  # Duplicate

            events = store.read_all()
            assert len(events) == 1  # Only one event

    def test_state_transitions(self):
        """State machine should transition correctly"""
        with tempfile.TemporaryDirectory() as d:
            store = EventStore(Path(d) / "events.jsonl")
            sm = EventSourcedStateMachine(trace_id="test", event_store=store)

            sm.enter_stage("stage-1")
            assert sm.current_stage == "stage-1"

            sm.record_skill_result("skill-a", {"status": "success"})
            assert sm.skill_results["skill-a"]["status"] == "success"

            sm.block("blocked")
            assert sm.blocked_reason == "blocked"

            sm.unblock("stage-2")
            assert sm.blocked_reason is None
            assert sm.current_stage == "stage-2"


class TestSagaOrchestrator:
    """Tests for SagaOrchestrator"""

    def test_saga_completion(self):
        """Completed saga should skip compensation"""
        with tempfile.TemporaryDirectory() as d:
            saga = SagaOrchestrator(
                saga_id="saga-1",
                trace_id="trace-1",
                artifacts_dir=Path(d),
            )
            saga.register_action("action-1")
            saga.mark_completed()

            result = saga.compensate()
            assert result["status"] == "skipped"

    def test_saga_compensation(self):
        """Failed saga should compensate in reverse order"""
        with tempfile.TemporaryDirectory() as d:
            saga = SagaOrchestrator(
                saga_id="saga-2",
                trace_id="trace-2",
                artifacts_dir=Path(d),
            )

            compensation_log = []
            saga.register_action(
                "action-1",
                compensation_func=lambda: compensation_log.append("comp-1"),
            )
            saga.register_action(
                "action-2",
                compensation_func=lambda: compensation_log.append("comp-2"),
            )

            result = saga.compensate()
            assert result["status"] == "completed"
            assert result["actions_compensated"] == 2
            assert compensation_log == ["comp-2", "comp-1"]  # Reverse order

    def test_saga_recovery(self):
        """Saga should recover from persisted state"""
        with tempfile.TemporaryDirectory() as d:
            saga1 = SagaOrchestrator(
                saga_id="saga-3",
                trace_id="trace-3",
                artifacts_dir=Path(d),
            )
            saga1.register_action("action-1")
            saga1.mark_completed()

            # Recover
            saga2 = SagaOrchestrator.recover("saga-3", Path(d))
            assert saga2 is not None
            assert saga2.execution.state == SagaState.COMPLETED


class TestSkillOrchestrator:
    """Tests for SkillOrchestrator"""

    def test_retry_integration(self):
        """Orchestrator should retry with RetryPolicy"""
        with tempfile.TemporaryDirectory() as d:
            orchestrator = SkillOrchestrator(
                trace_id="trace-1",
                artifacts_dir=Path(d),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            call_count = 0
            def flaky_skill():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("EXE-101: transient error")
                return {"output": "success"}

            result = orchestrator.execute_skill("flaky", flaky_skill)
            assert result.status == "success"
            assert result.attempts == 3

    def test_priority_queue_execution(self):
        """Orchestrator should execute skills by priority"""
        with tempfile.TemporaryDirectory() as d:
            orchestrator = SkillOrchestrator(
                trace_id="trace-2",
                artifacts_dir=Path(d),
            )
            orchestrator.enqueue_skill("skill-a", SkillPriority.DEFER)
            orchestrator.enqueue_skill("skill-b", SkillPriority.CRITICAL)

            executed = []
            def executor(name, ctx):
                executed.append(name)
                return {"executed": name}

            results = orchestrator.execute_queue(executor)
            assert len(results) == 2
            assert executed == ["skill-b", "skill-a"]  # CRITICAL first

    def test_saga_integration(self):
        """Orchestrator should integrate Saga compensation"""
        with tempfile.TemporaryDirectory() as d:
            orchestrator = SkillOrchestrator(
                trace_id="trace-3",
                artifacts_dir=Path(d),
            )
            orchestrator.start_saga("saga-test")

            compensation_log = []
            result = orchestrator.execute_skill(
                "compensatable",
                lambda: {"output": "ok"},
                on_failure_compensate=lambda: compensation_log.append("compensated"),
            )

            orchestrator.complete_saga()
            assert orchestrator.saga.execution.state == SagaState.COMPLETED

    def test_state_persistence(self):
        """Orchestrator should persist state via event sourcing"""
        with tempfile.TemporaryDirectory() as d:
            orchestrator = SkillOrchestrator(
                trace_id="trace-4",
                artifacts_dir=Path(d),
            )

            orchestrator.execute_skill(
                "test-skill",
                lambda: {"output": "data"},
            )

            state = orchestrator.get_state()
            assert state["trace_id"] == "trace-4"
            assert "test-skill" in state["skill_results"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
