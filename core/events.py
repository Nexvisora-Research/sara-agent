"""In-process asynchronexvisora event bus used by Phase A services."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator

from .models import Event, EventType


class EventBus:
    """Fan-out event bus with bounded subscriber queues.

    Slow subscribers do not block agents. When a queue is full the oldest
    event is discarded, ensuring current progress remains observable.
    """

    def __init__(self, queue_size: int = 256) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be positive")
        self._queue_size = queue_size
        self._subscribers: dict[EventType | None, set[asyncio.Queue[Event]]] = (
            defaultdict(set)
        )
        self._lock = asyncio.Lock()

    async def subscribe(
        self, event_type: EventType | None = None
    ) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            self._subscribers[event_type].add(queue)
        return queue

    async def unsubscribe(
        self, queue: asyncio.Queue[Event], event_type: EventType | None = None
    ) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(event_type)
            if subscribers is not None:
                subscribers.discard(queue)
                if not subscribers:
                    self._subscribers.pop(event_type, None)

    async def publish(self, event: Event) -> None:
        async with self._lock:
            queues = set(self._subscribers.get(None, set()))
            queues.update(self._subscribers.get(event.type, set()))
        for queue in queues:
            if queue.full():
                queue.get_nowait()
                queue.task_done()
            queue.put_nowait(event)

    async def stream(
        self, event_type: EventType | None = None
    ) -> AsyncIterator[Event]:
        queue = await self.subscribe(event_type)
        try:
            while True:
                yield await queue.get()
                queue.task_done()
        finally:
            await self.unsubscribe(queue, event_type)

