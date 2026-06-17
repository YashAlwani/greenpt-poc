"""Pub/sub event bus for SSE streaming."""

import json
import queue
import threading

_lock = threading.Lock()
_subscribers: list[queue.Queue] = []


def subscribe() -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=500)
    with _lock:
        _subscribers.append(q)
    return q


def unsubscribe(q: queue.Queue):
    with _lock:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


def emit(event: dict):
    payload = json.dumps(event)
    with _lock:
        for q in list(_subscribers):
            try:
                q.put_nowait(payload)
            except queue.Full:
                pass
