"""WebSocket endpoint for real-time task progress updates."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.deps import get_event_bus, get_task_manager
from app.services.event_bus import PipelineEvent

logger = logging.getLogger("app.ws")

router = APIRouter()


@router.websocket("/ws/tasks/{task_id}")
async def ws_task(websocket: WebSocket, task_id: str):
    await websocket.accept()

    # 获取依赖
    eb = get_event_bus()
    tm = get_task_manager()

    # 先发送当前状态
    try:
        task = tm.get_task(task_id)
        if task:
            await websocket.send_json({"type": "state", "data": task})
    except Exception as e:
        logger.warning(f"Failed to send initial state: {e}")

    # 订阅事件
    event_queue = eb.subscribe(task_id)

    try:
        while True:
            try:
                # 等待事件，带超时以发送心跳
                event: PipelineEvent = await asyncio.wait_for(
                    event_queue.get(), timeout=25.0
                )
                await websocket.send_json({
                    "type": event.type,
                    "task_id": event.task_id,
                    "stage": event.stage,
                    "data": event.data,
                    "timestamp": event.timestamp,
                })
            except asyncio.TimeoutError:
                # 发送心跳保活
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for {task_id}: {e}")
    finally:
        eb.unsubscribe(task_id, event_queue)
        try:
            await websocket.close()
        except Exception:
            pass