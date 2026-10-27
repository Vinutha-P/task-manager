"""Print a deterministic timeline for both rate limiters, then a short real-time burst."""

from __future__ import annotations

import time

from rate_limiters import LeakyBucket, TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _burst(limiter, count: int) -> str:
    marks = []
    for _ in range(count):
        marks.append("ALLOW" if limiter.allow() else "DENY")
    return " ".join(marks)


def run_virtual() -> None:
    print("=== Token bucket (virtual clock) ===")
    print("capacity=5  refill_rate=1 token/second  starts full")
    clock = FakeClock()
    token_bucket = TokenBucket(capacity=5, refill_rate=1, clock=clock)
    print(f"t={clock.now:.1f}s  7 requests: {_burst(token_bucket, 7)}")
    clock.advance(2)
    print(f"t={clock.now:.1f}s  3 requests: {_burst(token_bucket, 3)}  (2 tokens refilled)")
    clock.advance(10)
    print(f"t={clock.now:.1f}s  6 requests: {_burst(token_bucket, 6)}  (capped at 5 tokens)")

    print("\n=== Leaky bucket (virtual clock) ===")
    print("capacity=4  leak_rate=1 unit/second  starts empty")
    clock = FakeClock()
    leaky_bucket = LeakyBucket(capacity=4, leak_rate=1, clock=clock)
    print(f"t={clock.now:.1f}s  6 requests: {_burst(leaky_bucket, 6)}")
    clock.advance(2)
    print(f"t={clock.now:.1f}s  3 requests: {_burst(leaky_bucket, 3)}  (2 units leaked)")
    clock.advance(10)
    print(f"t={clock.now:.1f}s  5 requests: {_burst(leaky_bucket, 5)}  (bucket drained, then filled)")


def run_realtime() -> None:
    print("\n=== Real-time token bucket ===")
    print("capacity=3  refill_rate=10 tokens/second")
    bucket = TokenBucket(capacity=3, refill_rate=10)
    print(f"immediate burst of 5: {_burst(bucket, 5)}")
    time.sleep(0.25)
    print(f"after 0.25s, burst of 3: {_burst(bucket, 3)}")

    print("\n=== Real-time leaky bucket ===")
    print("capacity=3  leak_rate=10 units/second")
    bucket = LeakyBucket(capacity=3, leak_rate=10)
    print(f"immediate burst of 5: {_burst(bucket, 5)}")
    time.sleep(0.25)
    print(f"after 0.25s, burst of 3: {_burst(bucket, 3)}")


if __name__ == "__main__":
    run_virtual()
    run_realtime()
    print("\nDemo finished.")
