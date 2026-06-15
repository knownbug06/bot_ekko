"""
Thread-safe shared state for the streaming LLM response.
LlmService writes tokens; handle_DISPLAY_TEXT reads each frame.
"""
import threading
import time

_lock = threading.Lock()
_state = {
    "text": "",
    "is_streaming": False,
    "is_done": False,
    "done_time_ms": 0,
    "error": None,
}


def start_stream() -> None:
    with _lock:
        _state.update(text="", is_streaming=True, is_done=False,
                      done_time_ms=0, error=None)


def append_token(token: str) -> None:
    with _lock:
        _state["text"] += token


def mark_done() -> None:
    with _lock:
        _state["is_streaming"] = False
        _state["is_done"] = True
        _state["done_time_ms"] = int(time.time() * 1000)


def mark_error(message: str) -> None:
    with _lock:
        _state["is_streaming"] = False
        _state["is_done"] = True
        _state["error"] = message
        _state["done_time_ms"] = int(time.time() * 1000)


def get_state() -> dict:
    with _lock:
        return dict(_state)


def reset() -> None:
    with _lock:
        _state.update(text="", is_streaming=False, is_done=False,
                      done_time_ms=0, error=None)
