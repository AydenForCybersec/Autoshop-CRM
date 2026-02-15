"""Simple in-process login throttling utilities."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import threading
import time


@dataclass
class AttemptState:
    """Track failed auth attempts and lockout windows."""

    failures: deque[float] = field(default_factory=deque)
    locked_until: float = 0.0


_states: dict[str, AttemptState] = {}
_lock = threading.Lock()


def _now() -> float:
    return time.monotonic()


def _prune(state: AttemptState, *, now: float, window_seconds: int) -> None:
    while state.failures and (now - state.failures[0]) > window_seconds:
        state.failures.popleft()


def _key(username: str, client_ip: str) -> str:
    return f"{username.lower()}|{client_ip}"


def get_retry_after_seconds(
    *,
    username: str,
    client_ip: str,
    window_seconds: int,
) -> int:
    """Return remaining lockout seconds if currently locked, else 0."""
    now = _now()
    with _lock:
        state = _states.get(_key(username, client_ip))
        if state is None:
            return 0
        _prune(state, now=now, window_seconds=window_seconds)
        remaining = int(max(0.0, state.locked_until - now))
        if not state.failures and remaining == 0:
            _states.pop(_key(username, client_ip), None)
        return remaining


def record_failed_attempt(
    *,
    username: str,
    client_ip: str,
    max_attempts: int,
    window_seconds: int,
    lockout_seconds: int,
) -> int:
    """Record a failed attempt and return lockout seconds when active."""
    now = _now()
    with _lock:
        state = _states.setdefault(_key(username, client_ip), AttemptState())
        _prune(state, now=now, window_seconds=window_seconds)

        if state.locked_until > now:
            return int(state.locked_until - now)

        state.failures.append(now)
        if len(state.failures) >= max(1, max_attempts):
            state.locked_until = now + max(1, lockout_seconds)
            state.failures.clear()
            return int(lockout_seconds)
        return 0


def clear_attempts(*, username: str, client_ip: str) -> None:
    """Clear throttle state after successful authentication."""
    with _lock:
        _states.pop(_key(username, client_ip), None)
