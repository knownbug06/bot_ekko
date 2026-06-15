"""
Thread-safe ring buffer for audio RMS values.
SttService writes to it; handle_LISTENING reads from it.
"""
import collections
import threading

_BUFFER_SIZE = 40

_lock = threading.Lock()
_rms_buffer: collections.deque = collections.deque([0.0] * _BUFFER_SIZE, maxlen=_BUFFER_SIZE)


def push_rms(value: float) -> None:
    with _lock:
        _rms_buffer.append(max(0.0, min(1.0, value)))


def get_snapshot() -> list:
    with _lock:
        return list(_rms_buffer)


def clear() -> None:
    with _lock:
        for _ in range(_BUFFER_SIZE):
            _rms_buffer.append(0.0)
