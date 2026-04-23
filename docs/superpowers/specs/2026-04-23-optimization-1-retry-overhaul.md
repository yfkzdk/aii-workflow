# 优化方案一：重试系统重构 — Poisson 抖动 + 不可重试错误类型 + 心跳检查点

> **优先级**: P0（直接影响生产稳定性）
> **影响范围**: 执行流水线第一阶段、失败处理与重试策略、幂等性判定
> **参考来源**: Prefect `exponential_backoff_with_jitter` + Temporal `RetryPolicy` + Temporal `heartbeat`

---

## 一、当前设计问题诊断

### 问题 1：抖动算法不安全 — 简单随机抖动无法防止雷群效应

**当前实现**（设计文档 L2991-2995）：
```python
def calculate_backoff(self, attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = delay * 0.2 * (random.random() - 0.5)  # ±20% 均匀随机
    return max(0.1, delay + jitter)
```

**问题**：
- 均匀随机抖动（`random.random() - 0.5`）在多 Skill 同时重试时，退避时间高度集中在均值附近，无法有效分散重试请求
- 当 N 个 Skill 同时超时重试，±20% 的抖动范围太窄，大量请求仍会在相近时刻集中发起
- `random.random()` 无种子控制，不可复现，调试困难

**Prefect 的做法**（`prefect/_internal/retries.py` + `prefect/utilities/math.py`）：
```python
def exponential_backoff_with_jitter(attempt: int, base_delay: float, max_delay: float) -> float:
    average_interval = min(base_delay * (2**attempt), max_delay)
    return clamped_poisson_interval(average_interval, clamping_factor=0.3)

def clamped_poisson_interval(average_interval: float, clamping_factor: float = 0.3) -> float:
    """用泊松分布生成抖动间隔，数学上保证平均间隔不变的同时大幅分散重试时间"""
    upper_clamp_multiple = 1 + clamping_factor
    upper_bound = average_interval * upper_clamp_multiple
    lower_bound = max(0, average_interval * lower_clamp_multiple(upper_clamp_multiple))
    upper_rv = exponential_cdf(upper_bound, average_interval)
    lower_rv = exponential_cdf(lower_bound, average_interval)
    return poisson_interval(average_interval, lower_rv, upper_rv)
```

**关键差异**：泊松分布是重试场景的自然分布（事件到达间隔），其长尾特性天然分散重试请求，而均匀分布则集中在均值附近。

### 问题 2：幂等性判定与重试决策耦合过紧 — 缺少不可重试错误类型声明

**当前实现**（设计文档 L2786-2791）：
```python
# 非幂等操作禁止自动重试
if not self.is_idempotent() and self.on_fail == "retry":
    raise ValueError(
        f"非幂等操作（{self.side_effect.value}）禁止自动重试，"
        f"请设置 on_fail=block 或 on_fail=warn"
    )
```

**问题**：
- 用 `side_effect` 类型（`external_api`/`db_write`/`stateful`）一刀切禁止重试，过于粗暴
- 实际场景中，`db_write` 可能是 UPSERT（幂等），`external_api` 可能是 GET（幂等），但当前设计无法区分
- 缺少 **按错误类型** 决定是否重试的机制 — 某些错误（如权限不足）即使操作幂等也不应重试

**Temporal 的做法**（`temporalio/common.py` L37-60）：
```python
@dataclass
class RetryPolicy:
    initial_interval: timedelta = timedelta(seconds=1)
    backoff_coefficient: float = 2.0
    maximum_interval: timedelta | None = None  # 默认 100x initial_interval
    maximum_attempts: int = 0  # 0 = 无限
    non_retryable_error_types: Sequence[str] | None = None  # 关键：声明不可重试的错误类型
```

**关键差异**：Temporal 将"是否可重试"从操作类型解耦到错误类型，允许同一操作在不同错误下做出不同重试决策。

### 问题 3：检查点机制脆弱 — 文件写入无心跳，崩溃后恢复不可靠

**当前实现**（设计文档 L1196-1245）：
```python
checkpoint = ExecutionCheckpoint(state["task_dir"])
completed = checkpoint.load_checkpoint()["completed_skills"]

# 执行后更新检查点
completed.append(skill_name)
checkpoint.save_checkpoint(completed)
```

**问题**：
- 检查点在 Skill 执行完成后才写入，如果 Skill 在执行中途崩溃，检查点不会更新
- 长时间运行的 Skill（如 `security-review` 180s 超时）中途崩溃后，无法知道执行到哪一步
- 恢复时只能选择"重新执行整个 Skill"或"跳过"，无法从中间状态恢复

**Temporal 的做法**（`temporalio/activity.py` L108-109）：
```python
@dataclass(frozen=True class Info:
    heartbeat_details: Sequence[Any]  # 上次心跳携带的细节，用于断点续跑
    heartbeat_timeout: timedelta | None  # 心跳超时
    attempt: int  # 当前重试次数
```

**关键差异**：Temporal 的心跳机制允许 Activity 在执行过程中定期报告进度（`heartbeat(details)`），崩溃后重启时可以从 `heartbeat_details` 恢复到最近的进度点。

---

## 二、优化方案

### 2.1 替换抖动算法：泊松间隔替代均匀随机

```python
import math
import random
from dataclasses import dataclass
from typing import Optional

@dataclass
class RetryPolicy:
    """重试策略（对齐 Temporal RetryPolicy + Prefect Poisson Jitter）"""

    # 退避参数
    initial_interval_seconds: float = 1.0
    backoff_coefficient: float = 2.0
    maximum_interval_seconds: float = 60.0
    maximum_attempts: int = 3

    # Poisson 抖动参数
    poisson_clamping_factor: float = 0.3  # 泊松间隔钳位因子

    # 不可重试错误类型（对齐 Temporal non_retryable_error_types）
    non_retryable_error_types: list[str] | None = None

    # 可重试错误类型（白名单模式，优先级高于 non_retryable_error_types）
    retryable_error_types: list[str] | None = None

    def calculate_backoff(self, attempt: int) -> float:
        """指数退避 + 泊松抖动（替代简单均匀随机）"""
        average_interval = min(
            self.initial_interval_seconds * (self.backoff_coefficient ** attempt),
            self.maximum_interval_seconds
        )
        return clamped_poisson_interval(
            average_interval,
            clamping_factor=self.poisson_clamping_factor
        )

    def should_retry_error(self, error_code: str) -> bool:
        """基于错误类型判断是否可重试（替代 side_effect 一刀切）"""
        # 1. 白名单优先：如果声明了 retryable_error_types，仅重试列表中的错误
        if self.retryable_error_types is not None:
            return error_code in self.retryable_error_types

        # 2. 黑名单次之：如果声明了 non_retryable_error_types，排除列表中的错误
        if self.non_retryable_error_types is not None:
            return error_code not in self.non_retryable_error_types

        # 3. 默认：按错误码决策树判断
        return error_code in {"EXE-101", "EXE-102", "EXE-104", "EXE-106"}


def clamped_poisson_interval(
    average_interval: float,
    clamping_factor: float = 0.3
) -> float:
    """
    泊松钳位间隔（对齐 Prefect 实现）

    数学特性：
    - 期望值 ≈ average_interval（保持平均退避时间不变）
    - 长尾分布：自然分散重试请求，避免雷群效应
    - 钳位因子控制分散程度：0.3 表示间隔在 [0.7x, 1.3x] 范围内波动
    """
    if clamping_factor <= 0:
        return average_interval

    upper_clamp_multiple = 1 + clamping_factor
    upper_bound = average_interval * upper_clamp_multiple
    lower_bound = max(0, average_interval * _lower_clamp_multiple(upper_clamp_multiple))

    upper_rv = _exponential_cdf(upper_bound, average_interval)
    lower_rv = _exponential_cdf(lower_bound, average_interval)
    return _poisson_interval(average_interval, lower_rv, upper_rv)


def _exponential_cdf(x: float, rate: float) -> float:
    """指数分布 CDF"""
    return 1 - math.exp(-rate * x) if rate > 0 else 0.0


def _lower_clamp_multiple(upper_clamp_multiple: float) -> float:
    """计算下界钳位倍数，使期望值保持为 average_interval"""
    return max(0, 2 - upper_clamp_multiple)


def _poisson_interval(average: float, lower_rv: float, upper_rv: float) -> float:
    """从截断指数分布中采样"""
    if upper_rv <= lower_rv:
        return average
    u = random.uniform(lower_rv, upper_rv)
    rate = 1.0 / average if average > 0 else 1.0
    return -math.log(1 - u) / rate
```

### 2.2 重试决策重构：错误类型驱动替代操作类型驱动

```python
@dataclass
class SkillPolicy:
    """Skill 策略配置（重构版）"""
    name: str
    on_fail: str
    critical: bool
    timeout_seconds: int
    enabled: bool
    args: dict[str, Any]

    # 重试策略（替代 side_effect + on_fail 耦合）
    retry_policy: RetryPolicy | None = None

    # 保留 side_effect 用于审计和补偿决策，但不再控制重试
    side_effect: str = "none"

    def should_retry(self, error_code: str, attempt: int) -> dict[str, Any]:
        """判断是否应重试（错误类型驱动）"""
        policy = self.retry_policy or RetryPolicy()

        # 1. 尝试次数检查
        if attempt >= policy.maximum_attempts:
            return {"should_retry": False, "reason": "重试次数耗尽", "fallback": "block"}

        # 2. 错误类型检查（核心改进：替代 side_effect 一刀切）
        if not policy.should_retry_error(error_code):
            return {
                "should_retry": False,
                "reason": f"错误 {error_code} 不可重试",
                "fallback": self.on_fail
            }

        # 3. 计算退避时间（泊松抖动）
        delay = policy.calculate_backoff(attempt)

        return {
            "should_retry": True,
            "delay_seconds": delay,
            "next_attempt": attempt + 1,
            "strategy": "exponential_backoff_with_poisson_jitter"
        }
```

**配置示例**：
```json
{
  "name": "security-review",
  "on_fail": "block",
  "critical": true,
  "timeout_seconds": 180,
  "side_effect": "read_only",
  "retry_policy": {
    "initial_interval_seconds": 5,
    "backoff_coefficient": 2.0,
    "maximum_interval_seconds": 120,
    "maximum_attempts": 3,
    "poisson_clamping_factor": 0.3,
    "non_retryable_error_types": ["EXE-103", "EXE-105", "CFG-001", "CFG-002", "CFG-003"],
    "retryable_error_types": null
  }
}
```

```json
{
  "name": "send-notification",
  "on_fail": "block",
  "critical": false,
  "timeout_seconds": 30,
  "side_effect": "external_api",
  "retry_policy": {
    "maximum_attempts": 3,
    "non_retryable_error_types": ["APP-302", "CFG-004"],
    "retryable_error_types": ["EXE-101", "EXE-102"]
  }
}
```

### 2.3 心跳检查点：替代文件级检查点

```python
from dataclasses import dataclass, field
from typing import Any, Callable
import time

@dataclass
class HeartbeatCheckpoint:
    """心跳检查点（对齐 Temporal heartbeat_details）"""

    skill_name: str
    last_heartbeat_time: float = 0.0
    heartbeat_details: dict[str, Any] = field(default_factory=dict)
    heartbeat_interval_seconds: float = 30.0  # 心跳间隔
    missed_heartbeats: int = 0
    max_missed_heartbeats: int = 3  # 连续丢失3次心跳视为超时

    def heartbeat(self, details: dict[str, Any] | None = None):
        """报告心跳（Skill 执行过程中定期调用）"""
        self.last_heartbeat_time = time.time()
        if details:
            self.heartbeat_details.update(details)
        self.missed_heartbeats = 0

        # 持久化心跳状态
        self._persist()

    def check_health(self) -> bool:
        """检查心跳是否正常"""
        elapsed = time.time() - self.last_heartbeat_time
        if elapsed > self.heartbeat_interval_seconds * (self.missed_heartbeats + 1):
            self.missed_heartbeats += 1
            if self.missed_heartbeats >= self.max_missed_heartbeats:
                return False  # 心跳超时
        return True

    def get_resume_context(self) -> dict[str, Any]:
        """获取恢复上下文（崩溃后从此处恢复）"""
        return {
            "skill_name": self.skill_name,
            "last_heartbeat_time": self.last_heartbeat_time,
            "heartbeat_details": self.heartbeat_details,
            "can_resume": bool(self.heartbeat_details)
        }

    def _persist(self):
        """持久化心跳状态到文件"""
        import json
        from pathlib import Path
        checkpoint_path = Path(f"artifacts/{self.skill_name}_heartbeat.json")
        checkpoint_path.write_text(
            json.dumps(self.get_resume_context(), ensure_ascii=False),
            encoding="utf-8"
        )


class SkillExecutor:
    """Skill 执行器（集成心跳检查点）"""

    async def execute_with_heartbeat(
        self,
        skill_name: str,
        skill_fn: Callable,
        context: dict[str, Any],
        policy: SkillPolicy
    ) -> SkillResult:
        """带心跳的 Skill 执行"""

        # 1. 检查是否有可恢复的心跳检查点
        checkpoint = self._load_heartbeat_checkpoint(skill_name)
        if checkpoint and checkpoint.can_resume:
            # 注入恢复上下文
            context["resume_from"] = checkpoint.heartbeat_details

        # 2. 创建心跳检查点
        heartbeat = HeartbeatCheckpoint(
            skill_name=skill_name,
            heartbeat_interval_seconds=min(30.0, policy.timeout_seconds / 6)
        )
        heartbeat.heartbeat(details={"phase": "started"})

        # 3. 执行 Skill（Skill 内部可调用 heartbeat 报告进度）
        context["heartbeat_callback"] = heartbeat.heartbeat

        try:
            result = await skill_fn(context)
            heartbeat.heartbeat(details={"phase": "completed"})
            return result
        except Exception as e:
            # 心跳检查点已保存最后进度，下次可从此处恢复
            heartbeat.heartbeat(details={
                "phase": "failed",
                "error": str(e),
                "timestamp": time.time()
            })
            raise
```

**Skill 适配器使用示例**：
```python
class SecurityReviewAdapter(SkillAdapter):
    async def run(self, context: dict) -> SkillResult:
        heartbeat = context.get("heartbeat_callback")
        resume_from = context.get("resume_from")

        # 从断点恢复
        start_file = 0
        if resume_from and "last_file_index" in resume_from:
            start_file = resume_from["last_file_index"]

        files = list(Path("artifacts/code").glob("**/*.py"))
        for i, file in enumerate(files[start_file:], start=start_file):
            # 扫描文件
            result = self._scan_file(file)

            # 每10个文件报告一次心跳
            if heartbeat and i % 10 == 0:
                heartbeat({"last_file_index": i, "scanned_count": i + 1})

        return SkillResult(status=SkillStatus.SUCCESS, ...)
```

---

## 三、变更影响矩阵

| 组件 | 变更类型 | 影响范围 | 向后兼容 |
|------|---------|---------|---------|
| `RetryManager.calculate_backoff` | 替换实现 | 重试策略 | ✅ 接口不变，行为优化 |
| `SkillPolicy` | 新增 `retry_policy` 字段 | 配置契约 | ✅ 可选字段，默认值兼容 |
| `SkillPolicy.is_idempotent()` | 降级为审计用途 | 幂等性判定 | ⚠️ 不再控制重试决策 |
| `ExecutionCheckpoint` | 替换为 `HeartbeatCheckpoint` | 检查点机制 | ❌ 接口变更，需迁移 |
| `skill_whitelist.json` | 新增 `retry_policy` 配置 | 配置文件 | ✅ 可选字段 |
| 错误码决策树 | 新增 `non_retryable_error_types` 检查 | 错误处理 | ✅ 扩展，不破坏现有逻辑 |

---

## 四、迁移路径

1. **Phase 1**（1周）：替换 `calculate_backoff` 为泊松抖动，接口不变
2. **Phase 2**（1周）：新增 `RetryPolicy` 配置字段，`side_effect` 保留但仅用于审计
3. **Phase 3**（1周）：实现 `HeartbeatCheckpoint`，替换 `ExecutionCheckpoint`
4. **Phase 4**（3天）：更新 `skill_whitelist.json` Schema，添加 `retry_policy` 字段