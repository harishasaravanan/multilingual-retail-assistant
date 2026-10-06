"""Server-Sent Events plumbing for GET /kiosk/events (no web framework needed)."""
import asyncio
import json


def sse_format(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class Broker:
    """Fan-out of events to every connected kiosk screen."""

    def __init__(self):
        self._subs = set()

    def subscribe(self):
        q = asyncio.Queue(maxsize=100)
        self._subs.add(q)
        return q

    def unsubscribe(self, q):
        self._subs.discard(q)

    def publish(self, event, data):
        for q in list(self._subs):
            try:
                q.put_nowait((event, data))
            except asyncio.QueueFull:
                pass  # a stuck screen must not block the others


async def event_stream(broker, heartbeat=15.0):
    """Yield SSE text. Sends a comment line every `heartbeat` seconds when idle."""
    q = broker.subscribe()
    try:
        while True:
            try:
                event, data = await asyncio.wait_for(q.get(), timeout=heartbeat)
                yield sse_format(event, data)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    finally:
        broker.unsubscribe(q)
