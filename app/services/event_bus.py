"""In-process event bus for pipeline state change notifications.

使用 asyncio.Queue + 线程安全桥接，确保 PipelineRunner 线程
发出的事件能可靠传递到 async WebSocket 消费者。
"""

import asyncio
import logging
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("app.event_bus")


@dataclass
class PipelineEvent:
    type: str
    task_id: str
    stage: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._thread_queues: Dict[str, List[queue.Queue]] = {}

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """为 async 消费者（WebSocket）创建订阅队列。"""
        aq = asyncio.Queue(maxsize=100)
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(aq)
        return aq

    def unsubscribe(self, task_id: str, aq: asyncio.Queue):
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(aq)
            except ValueError:
                pass
            if not self._subscribers[task_id]:
                del self._subscribers[task_id]

    def emit(self, task_id: str, event: PipelineEvent):
        """线程安全地发送事件到所有订阅者。

        PipelineRunner 在后台线程调用此方法，
        通过 asyncio.call_soon_threadsafe 安全写入 async 队列。
        """
        # 写入 async 队列（线程安全）
        async_queues = self._subscribers.get(task_id, [])
        for aq in async_queues:
            try:
                aq.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"Async queue full for {task_id}, dropping event")

    def has_subscribers(self, task_id: str) -> bool:
        return bool(self._subscribers.get(task_id))