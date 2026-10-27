"""Token bucket and leaky bucket rate limiters.

Token bucket
  The bucket holds tokens, up to ``capacity``, and refills continuously at
  ``refill_rate`` tokens per second. A request is allowed when at least one
  token is available. The bucket starts full, so a client may burst up to
  ``capacity`` immediately.

Leaky bucket
  The bucket holds the water level of recent requests, up to ``capacity``,
  and leaks continuously at ``leak_rate`` units per second. Each allowed
  request adds one unit. A request is rejected when adding it would overflow
  the bucket. The bucket starts empty. Output is smoothed to the leak rate;
  a burst larger than ``capacity`` is rejected.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


Clock = Callable[[], float]


class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float, clock: Clock = time.monotonic) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be > 0")
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock()
        self._lock = threading.Lock()

    @property
    def tokens(self) -> float:
        with self._lock:
            self._refill(self._clock())
            return self._tokens

    def allow(self, amount: float = 1.0) -> bool:
        if amount <= 0:
            raise ValueError("amount must be > 0")
        with self._lock:
            now = self._clock()
            self._refill(now)
            if self._tokens < amount:
                return False
            self._tokens -= amount
            return True

    def _refill(self, now: float) -> None:
        elapsed = max(0.0, now - self._last)
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last = now


class LeakyBucket:
    def __init__(self, capacity: float, leak_rate: float, clock: Clock = time.monotonic) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if leak_rate <= 0:
            raise ValueError("leak_rate must be > 0")
        self.capacity = float(capacity)
        self.leak_rate = float(leak_rate)
        self._clock = clock
        self._level = 0.0
        self._last = clock()
        self._lock = threading.Lock()

    @property
    def level(self) -> float:
        with self._lock:
            self._leak(self._clock())
            return self._level

    def allow(self, amount: float = 1.0) -> bool:
        if amount <= 0:
            raise ValueError("amount must be > 0")
        with self._lock:
            now = self._clock()
            self._leak(now)
            if self._level + amount > self.capacity:
                return False
            self._level += amount
            return True

    def _leak(self, now: float) -> None:
        elapsed = max(0.0, now - self._last)
        self._level = max(0.0, self._level - elapsed * self.leak_rate)
        self._last = now
