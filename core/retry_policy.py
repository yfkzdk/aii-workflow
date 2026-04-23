"""RetryPolicy — 重试策略模块。

实现泊松抖动重试策略（对齐 Prefect exponential_backoff_with_jitter）。
"""

import math
import random
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass
class RetryPolicy:
    """重试策略（对齐 Temporal RetryPolicy + Prefect Poisson Jitter）"""

    # 退避参数
    initial_interval_seconds: float = 1.0
    backoff_coefficient: float = 2.0
    maximum_interval_seconds: float = 60.0
    maximum_attempts: int = 3

    # Poisson 抖动参数
    poisson_clamping_factor: float = 0.3

    # 不可重试错误类型（对齐 Temporal non_retryable_error_types）
    non_retryable_error_types: Optional[Sequence[str]] = None

    # 可重试错误类型（白名单模式，优先级高于 non_retryable_error_types）
    retryable_error_types: Optional[Sequence[str]] = None

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

        # 3. 默认：按错误码决策树判断（瞬态错误可重试）
        return error_code in {"EXE-101", "EXE-102", "EXE-104", "EXE-106"}

    def get_next_delay(self, attempt: int) -> float:
        """获取下一次重试的延迟时间（秒）"""
        return self.calculate_backoff(attempt)


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

    rate = 1.0 / average_interval if average_interval > 0 else 1.0
    upper_rv = _exponential_cdf(upper_bound, rate)
    lower_rv = _exponential_cdf(lower_bound, rate)
    return _poisson_interval(average_interval, lower_rv, upper_rv)


def _exponential_cdf(x: float, rate: float) -> float:
    """指数分布 CDF"""
    if rate <= 0:
        return 0.0
    return 1 - math.exp(-rate * x)


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


# 默认重试策略
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval_seconds=1.0,
    backoff_coefficient=2.0,
    maximum_interval_seconds=60.0,
    maximum_attempts=3,
    poisson_clamping_factor=0.3,
    non_retryable_error_types=["CFG-001", "CFG-002", "CFG-003", "CFG-004", "CFG-005", "CFG-006",
                                "EXE-103", "EXE-105", "EXE-107", "EXE-108",
                                "QTY-202", "QTY-203", "APP-302", "APP-303", "APP-304"],
)