# [已废弃] 优化方案二：流水线执行引擎重构 — 优先级队列 + 图调度 + 快照恢复

> **优先级**: P1（直接影响 V1→V2 演进路径，V1 可局部采纳）
> **影响范围**: 执行流水线第一阶段、V2 依赖图并发调度、检查点/断点续跑
> **参考来源**: Haystack `PipelineBase` + `FIFOPriorityQueue` + `PipelineSnapshot` + `AsyncPipeline`

---

## 一、当前设计问题诊断

### 问题 1：V1 顺序执行效率低，V2 依赖图设计有结构性缺陷

**当前 V1 实现**（设计文档 L1193-1262）：
```python
async def _execute_skills_phase(self, tool_calls, state):
    results = {}
    for call in tool_calls:  # 严格顺序执行
        if call.name != "invoke_skill":
            continue
        skill_name = call.input["skill"]
        # ... 白名单检查 → 执行 → 写结果 → 更新检查点
```

**问题**：
- 所有 Skill 严格顺序执行，即使它们之间无依赖关系
- `security-review`（180s）和 `simplify`（60s）如果无依赖，顺序执行需 240s，并发仅需 180s

**当前 V2 设计**（设计文档 L5197-5363）：
```python
class SkillDependencyGraph:
    def topological_sort_with_levels(self) -> List[List[str]]:
        # 返回 [[L0], [L1], [L2]]，同层可并发
```

**V2 设计缺陷**：
1. **入度计算错误**：`in_degree` 计算的是"有多少技能依赖于我"（反向），但拓扑排序需要的是"我依赖多少技能"（正向入度）
2. **并发执行无优先级**：同层 Skill 无优先级区分，关键 Skill 应优先执行
3. **部分失败处理缺失**：同层并发时一个 Skill 失败，其他 Skill 的结果如何处理？
4. **无死锁检测**：循环依赖检测只有 DFS，缺少资源死锁检测

**Haystack 的做法**（`haystack/core/pipeline/base.py` + `pipeline.py`）：
```python
class ComponentPriority(IntEnum):
    HIGHEST = 1    # 最高优先级
    READY = 2      # 就绪
    DEFER = 3      # 延迟
    DEFER_LAST = 4 # 最后执行
    BLOCKED = 5    # 阻塞

# 优先级队列驱动执行
priority_queue = self._fill_queue(ordered_component_names, inputs, component_visits)
while True:
    candidate = self._get_next_runnable_component(priority_queue, component_visits)
    if candidate is None:
        break
    priority, component_name, component = candidate
    # 按优先级执行
```

**关键差异**：Haystack 用优先级队列替代固定拓扑层级，支持动态调度和优先级调整。

### 问题 2：检查点机制过于粗糙 — 无法保存/恢复流水线中间状态

**当前实现**（设计文档 L1196-1245）：
```python
checkpoint = ExecutionCheckpoint(state["task_dir"])
completed = checkpoint.load_checkpoint()["completed_skills"]
# 仅记录已完成的 Skill 名称列表
```

**问题**：
- 只记录"哪些 Skill 已完成"，不记录每个 Skill 的输入/输出状态
- 无法恢复到流水线的精确中间状态（如：3 个 Skill 中完成了 2 个，第 3 个执行到一半）
- 进程崩溃后，恢复逻辑只能"重新执行未完成的 Skill"，无法恢复已完成的中间结果

**Haystack 的做法**（`haystack/core/pipeline/pipeline.py` L237-284）：
```python
def run(self, data, *, pipeline_snapshot=None, snapshot_callback=None):
    if pipeline_snapshot:
        # 从快照恢复
        component_visits = pipeline_snapshot.pipeline_state.component_visits
        ordered_component_names = pipeline_snapshot.ordered_component_names
        data = _deserialize_value_with_schema(pipeline_snapshot.pipeline_state.inputs)
        pipeline_outputs = _deserialize_value_with_schema(pipeline_snapshot.pipeline_state.pipeline_outputs)
    else:
        # 正常初始化
        component_visits = dict.fromkeys(ordered_component_names, 0)
```

**关键差异**：Haystack 的 `PipelineSnapshot` 保存了完整的流水线状态（输入、输出、组件访问计数），支持精确恢复。

### 问题 3：缺少执行循环保护 — 无限循环风险

**当前设计**：状态机有 `BLOCKED → EXECUTING` 的恢复路径，但无循环计数器。如果审批流反复拒绝又重试，流水线可能无限循环。

**Haystack 的做法**（`haystack/core/pipeline/base.py` L96-98）：
```python
def __init__(self, max_runs_per_component: int = 100):
    self._max_runs_per_component = max_runs_per_component
    # 限制同一组件最多运行 100 次，防止无限循环
```

---

## 二、优化方案

### 2.1 优先级队列执行引擎（替代固定拓扑层级）

```python
from enum import IntEnum
import heapq
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

class SkillPriority(IntEnum):
    """Skill 执行优先级（对齐 Haystack ComponentPriority）"""
    CRITICAL = 1     # 关键 Skill 优先执行
    READY = 2         # 就绪（依赖已满足）
    DEFER = 3         # 延迟（非关键，可稍后执行）
    DEFER_LAST = 4    # 最后执行（如归档类 Skill）
    BLOCKED = 5       # 阻塞（依赖未满足或被阻断）

@dataclass(order=True)
class PrioritizedSkill:
    """优先级队列中的 Skill 条目"""
    priority: SkillPriority
    skill_name: str = field(compare=False)
    context: dict[str, Any] = field(compare=False, default_factory=dict)

class PrioritySkillQueue:
    """优先级队列（替代 V2 的固定拓扑层级）"""

    def __init__(self):
        self._queue: list[PrioritizedSkill] = []
        self._entries: dict[str, PrioritizedSkill] = {}  # 去重

    def push(self, skill_name: str, priority: SkillPriority, context: dict = None):
        """入队（自动去重，更新优先级）"""
        if skill_name in self._entries:
            # 更新优先级
            old = self._entries[skill_name]
            old_priority = old.priority
            if priority != old_priority:
                self._queue.remove(old)
                entry = PrioritizedSkill(priority=priority, skill_name=skill_name, context=context or {})
                self._queue.append(entry)
                self._entries[skill_name] = entry
                heapq.heapify(self._queue)
        else:
            entry = PrioritizedSkill(priority=priority, skill_name=skill_name, context=context or {})
            heapq.heappush(self._queue, entry)
            self._entries[skill_name] = entry

    def pop(self) -> Optional[PrioritizedSkill]:
        """出队（最高优先级优先）"""
        while self._queue:
            entry = heapq.heappop(self._queue)
            self._entries.pop(entry.skill_name, None)
            return entry
        return None

    def peek(self) -> Optional[SkillPriority]:
        """查看最高优先级"""
        return self._queue[0].priority if self._queue else None

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def reprioritize(self, skill_name: str, new_priority: SkillPriority):
        """重新设置优先级（如依赖满足后从 BLOCKED 升级为 READY）"""
        if skill_name in self._entries:
            self.push(skill_name, new_priority, self._entries[skill_name].context)
```

### 2.2 图调度执行引擎（修复 V2 拓扑排序 + 集成优先级队列）

```python
import networkx as nx  # 对齐 Haystack 使用 networkx

class SkillExecutionEngine:
    """Skill 执行引擎（图调度 + 优先级队列 + 快照恢复）"""

    def __init__(self, max_skill_runs: int = 100):
        # 依赖图（对齐 Haystack 的 networkx.MultiDiGraph）
        self.dependency_graph = nx.DiGraph()
        # 优先级队列
        self.priority_queue = PrioritySkillQueue()
        # 执行计数器（防止无限循环，对齐 Haystack max_runs_per_component）
        self.skill_run_counts: dict[str, int] = {}
        self.max_skill_runs = max_skill_runs

    def register_skill(
        self,
        name: str,
        dependencies: list[str] | None = None,
        critical: bool = False
    ):
        """注册 Skill 及其依赖"""
        self.dependency_graph.add_node(name, critical=critical)
        if dependencies:
            for dep in dependencies:
                self.dependency_graph.add_edge(dep, name)  # dep → name

        # 验证无环
        if not nx.is_directed_acyclic_graph(self.dependency_graph):
            cycles = list(nx.simple_cycles(self.dependency_graph))
            raise ValueError(f"检测到循环依赖: {cycles}")

    def build_execution_plan(self, stage: str, whitelist: dict) -> list[list[str]]:
        """
        构建执行计划（修复 V2 拓扑排序的入度计算错误）

        返回：[[L0_skills], [L1_skills], ...]，同层可并发
        """
        # 过滤当前阶段允许的 Skill
        allowed_skills = set()
        for skill_config in whitelist.get(stage, {}).get("skills", []):
            if skill_config.get("enabled", True):
                allowed_skills.add(skill_config["name"])

        # 构建子图
        subgraph = self.dependency_graph.subgraph(
            [n for n in self.dependency_graph.nodes if n in allowed_skills]
        ).copy()

        # 正确的拓扑排序：按层级分组
        levels = []
        remaining = set(subgraph.nodes)

        while remaining:
            # 当前层：入度为 0 的节点（我依赖的节点都已完成）
            current_level = [
                node for node in remaining
                if all(pred not in remaining for pred in subgraph.predecessors(node))
            ]

            if not current_level:
                # 存在未检测到的环（不应发生，因为前面已验证）
                raise ValueError(f"执行计划构建失败，可能存在未检测的循环依赖: {remaining}")

            # 关键 Skill 排在前面
            current_level.sort(
                key=lambda n: (0 if subgraph.nodes[n].get("critical", False) else 1, n)
            )
            levels.append(current_level)
            remaining -= set(current_level)

        return levels

    def fill_priority_queue(self, levels: list[list[str]], completed: set[str]):
        """根据执行层级和已完成状态填充优先级队列"""
        self.priority_queue = PrioritySkillQueue()

        for level_idx, level in enumerate(levels):
            for skill_name in level:
                # 检查依赖是否已完成
                deps = list(self.dependency_graph.predecessors(skill_name))
                deps_satisfied = all(d in completed for d in deps)

                is_critical = self.dependency_graph.nodes[skill_name].get("critical", False)

                if skill_name in completed:
                    continue  # 已完成，跳过
                elif not deps_satisfied:
                    self.priority_queue.push(skill_name, SkillPriority.BLOCKED)
                elif is_critical:
                    self.priority_queue.push(skill_name, SkillPriority.CRITICAL)
                elif level_idx == len(levels) - 1:
                    self.priority_queue.push(skill_name, SkillPriority.DEFER_LAST)
                else:
                    self.priority_queue.push(skill_name, SkillPriority.READY)

    async def execute_with_priority_queue(
        self,
        levels: list[list[str]],
        completed: set[str],
        engine: 'SkillEngine',
        state: dict[str, Any]
    ) -> dict[str, 'SkillResult']:
        """优先级队列驱动的执行（替代固定顺序执行）"""

        self.fill_priority_queue(levels, completed)
        results = {}

        while not self.priority_queue.is_empty():
            entry = self.priority_queue.pop()
            if entry is None:
                break

            # 跳过阻塞的 Skill
            if entry.priority == SkillPriority.BLOCKED:
                # 检查是否可以解除阻塞
                deps = list(self.dependency_graph.predecessors(entry.skill_name))
                deps_satisfied = all(
                    d in results and results[d].is_success() for d in deps
                )
                if not deps_satisfied:
                    results[entry.skill_name] = SkillResult(
                        status=SkillStatus.FAILED,
                        outputs={},
                        metrics={},
                        errors=[SkillError(code="EXE-106", message="依赖未满足")],
                        metadata={}
                    )
                    continue
                # 依赖已满足，重新入队为 READY
                self.priority_queue.push(entry.skill_name, SkillPriority.READY)
                continue

            # 循环保护（对齐 Haystack max_runs_per_component）
            self.skill_run_counts[entry.skill_name] = \
                self.skill_run_counts.get(entry.skill_name, 0) + 1
            if self.skill_run_counts[entry.skill_name] > self.max_skill_runs:
                raise RuntimeError(
                    f"Skill {entry.skill_name} 执行次数超过限制 ({self.max_skill_runs})"
                )

            # 执行 Skill
            policy = self._get_policy(state, entry.skill_name)
            result = await engine.execute(
                stage=state["status"],
                skill_name=entry.skill_name,
                context=entry.context,
                policy=policy
            )
            results[entry.skill_name] = result

            # 更新下游 Skill 优先级
            for successor in self.dependency_graph.successors(entry.skill_name):
                if successor in self._entries or successor in self.priority_queue._entries:
                    if result.is_success():
                        # 依赖成功，检查是否可以升级为 READY
                        all_deps_done = all(
                            d in results and results[d].is_success()
                            for d in self.dependency_graph.predecessors(successor)
                        )
                        if all_deps_done:
                            self.priority_queue.push(successor, SkillPriority.READY)

        return results
```

### 2.3 流水线快照与恢复（替代简单检查点）

```python
from dataclasses import dataclass, field
import json
from pathlib import Path

@dataclass
class PipelineSnapshot:
    """流水线快照（对齐 Haystack PipelineSnapshot）"""

    # 执行状态
    stage: str
    skill_results: dict[str, dict]  # skill_name → serialized SkillResult
    skill_run_counts: dict[str, int]
    completed_skills: list[str]

    # 输入状态
    original_inputs: dict[str, Any]

    # 优先级队列状态
    pending_skills: list[dict]  # [{name, priority, context}]

    # 元数据
    trace_id: str
    config_version: str
    timestamp: str
    snapshot_version: str = "1.0"

    def to_dict(self) -> dict:
        return {
            "snapshot_version": self.snapshot_version,
            "stage": self.stage,
            "skill_results": self.skill_results,
            "skill_run_counts": self.skill_run_counts,
            "completed_skills": self.completed_skills,
            "original_inputs": self.original_inputs,
            "pending_skills": self.pending_skills,
            "trace_id": self.trace_id,
            "config_version": self.config_version,
            "timestamp": self.timestamp,
        }

    def save(self, path: Path):
        """保存快照到文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path) -> 'PipelineSnapshot':
        """从文件加载快照"""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            stage=data["stage"],
            skill_results=data["skill_results"],
            skill_run_counts=data["skill_run_counts"],
            completed_skills=data["completed_skills"],
            original_inputs=data["original_inputs"],
            pending_skills=data["pending_skills"],
            trace_id=data["trace_id"],
            config_version=data["config_version"],
            timestamp=data["timestamp"],
            snapshot_version=data.get("snapshot_version", "1.0"),
        )

    @classmethod
    def from_engine(cls, engine: SkillExecutionEngine, state: dict) -> 'PipelineSnapshot':
        """从执行引擎创建快照"""
        return cls(
            stage=state["status"],
            skill_results={
                name: result.to_json() for name, result in state.get("skill_results", {}).items()
            },
            skill_run_counts=dict(engine.skill_run_counts),
            completed_skills=list(state.get("completed_skills", set())),
            original_inputs=state.get("original_inputs", {}),
            pending_skills=[
                {"name": e.skill_name, "priority": e.priority.value, "context": e.context}
                for e in engine.priority_queue._queue
            ],
            trace_id=state.get("trace_id", ""),
            config_version=state.get("config_version", ""),
            timestamp=datetime.now().isoformat(),
        )


class PipelineSnapshotManager:
    """流水线快照管理器"""

    def __init__(self, snapshot_dir: Path = Path("artifacts/snapshots")):
        self.snapshot_dir = snapshot_dir
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, engine: SkillExecutionEngine, state: dict, reason: str = ""):
        """保存快照（每次状态变更后调用）"""
        snapshot = PipelineSnapshot.from_engine(engine, state)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{state.get('status', 'unknown')}_{timestamp}.json"
        snapshot.save(self.snapshot_dir / filename)

    def load_latest_snapshot(self, trace_id: str = None) -> PipelineSnapshot | None:
        """加载最新快照"""
        snapshots = sorted(
            self.snapshot_dir.glob("snapshot_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        if not snapshots:
            return None

        snapshot = PipelineSnapshot.load(snapshots[0])
        if trace_id and snapshot.trace_id != trace_id:
            return None
        return snapshot

    def restore_from_snapshot(
        self,
        snapshot: PipelineSnapshot,
        engine: SkillExecutionEngine
    ) -> dict[str, Any]:
        """从快照恢复执行状态"""
        # 恢复执行计数器
        engine.skill_run_counts = dict(snapshot.skill_run_counts)

        # 恢复已完成的结果
        restored_results = {}
        for skill_name, result_data in snapshot.skill_results.items():
            restored_results[skill_name] = SkillResult.from_json(result_data)

        # 恢复待执行队列
        for pending in snapshot.pending_skills:
            engine.priority_queue.push(
                pending["name"],
                SkillPriority(pending["priority"]),
                pending.get("context", {})
            )

        return {
            "stage": snapshot.stage,
            "skill_results": restored_results,
            "completed_skills": set(snapshot.completed_skills),
            "original_inputs": snapshot.original_inputs,
        }
```

### 2.4 异步并发执行（对齐 Haystack AsyncPipeline）

```python
import asyncio

class AsyncSkillExecutionEngine(SkillExecutionEngine):
    """异步执行引擎（对齐 Haystack AsyncPipeline）"""

    async def execute_level_concurrent(
        self,
        level_skills: list[str],
        engine: 'SkillEngine',
        state: dict[str, Any]
    ) -> dict[str, 'SkillResult']:
        """同层 Skill 并发执行"""
        tasks = []
        for skill_name in level_skills:
            policy = self._get_policy(state, skill_name)
            tasks.append(
                engine.execute(
                    stage=state["status"],
                    skill_name=skill_name,
                    context=state.get("skill_context", {}).get(skill_name, {}),
                    policy=policy
                )
            )

        # 并发执行，收集结果（单点错误隔离）
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for skill_name, result in zip(level_skills, results):
            if isinstance(result, Exception):
                output[skill_name] = SkillResult(
                    status=SkillStatus.FAILED,
                    outputs={},
                    metrics={},
                    errors=[SkillError(code="EXE-102", message=str(result))],
                    metadata={}
                )
            else:
                output[skill_name] = result

        return output
```

---

## 三、V2 依赖图拓扑排序修复

**当前 V2 实现的入度计算错误**（设计文档 L5264-5296）：

```python
# 当前实现（错误）
reverse_graph: Dict[str, Set[str]] = {node: set() for node in self.all_nodes}
for skill, deps in self.graph.items():
    for dep in deps:
        reverse_graph[dep].add(skill)  # dep → skill（谁依赖于我）

in_degree = {node: len(reverse_graph[node]) for node in self.all_nodes}
# 这计算的是"有多少节点依赖于我"，不是"我依赖多少节点"
```

**修复**：
```python
# 正确实现
in_degree = {node: len(self.graph.get(node, set())) for node in self.all_nodes}
# in_degree = 我依赖的节点数（正向入度）

# 当前层：入度为 0 的节点（不依赖任何未完成节点）
current_level = [node for node in remaining if in_degree[node] == 0]

# 移除当前层后，减少下游入度
for node in current_level:
    remaining.remove(node)
    for successor in reverse_graph[node]:  # 依赖于我的节点
        if successor in remaining:
            in_degree[successor] -= 1
```

---

## 四、变更影响矩阵

| 组件 | 变更类型 | 影响范围 | 向后兼容 |
|------|---------|---------|---------|
| `_execute_skills_phase` | 替换为优先级队列驱动 | V1 执行引擎 | ⚠️ V1 可保持顺序执行作为默认 |
| `SkillDependencyGraph` | 修复入度计算 + 使用 networkx | V2 依赖图 | ❌ 接口变更 |
| `ExecutionCheckpoint` | 替换为 `PipelineSnapshot` | 检查点机制 | ❌ 接口变更 |
| 新增 `SkillPriority` | 新增枚举 | 优先级调度 | ✅ 新增 |
| 新增 `max_skill_runs` | 新增循环保护 | 执行安全 | ✅ 新增 |

---

## 五、V1 采纳建议

V1 可局部采纳以下改进，无需完整重构：

1. **循环保护**（1天）：在 `_execute_skills_phase` 中添加 `max_skill_runs` 检查
2. **快照保存**（2天）：在状态流转时保存 `PipelineSnapshot`，崩溃后可恢复
3. **关键 Skill 优先**（1天）：在顺序执行中，将 `critical=true` 的 Skill 排到前面

完整优先级队列和并发执行留待 V2。