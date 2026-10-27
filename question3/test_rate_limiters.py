"""Unit tests for the token bucket and leaky bucket."""

from __future__ import annotations

import unittest

from rate_limiters import LeakyBucket, TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TokenBucketTests(unittest.TestCase):
    def test_burst_then_deny(self) -> None:
        clock = FakeClock()
        bucket = TokenBucket(capacity=5, refill_rate=1, clock=clock)
        self.assertEqual([bucket.allow() for _ in range(5)], [True] * 5)
        self.assertFalse(bucket.allow())

    def test_refill_is_capped_at_capacity(self) -> None:
        clock = FakeClock()
        bucket = TokenBucket(capacity=5, refill_rate=1, clock=clock)
        for _ in range(5):
            bucket.allow()
        clock.advance(2)
        self.assertTrue(bucket.allow())
        self.assertTrue(bucket.allow())
        self.assertFalse(bucket.allow())
        clock.advance(100)
        self.assertAlmostEqual(bucket.tokens, 5)

    def test_partial_token_does_not_allow_a_full_request(self) -> None:
        clock = FakeClock()
        bucket = TokenBucket(capacity=1, refill_rate=0.5, clock=clock)
        self.assertTrue(bucket.allow())
        clock.advance(1)
        self.assertFalse(bucket.allow())
        clock.advance(1)
        self.assertTrue(bucket.allow())

    def test_rejects_invalid_configuration(self) -> None:
        with self.assertRaises(ValueError):
            TokenBucket(capacity=0, refill_rate=1)
        with self.assertRaises(ValueError):
            TokenBucket(capacity=1, refill_rate=0)


class LeakyBucketTests(unittest.TestCase):
    def test_burst_fills_the_bucket(self) -> None:
        clock = FakeClock()
        bucket = LeakyBucket(capacity=4, leak_rate=1, clock=clock)
        self.assertEqual([bucket.allow() for _ in range(4)], [True] * 4)
        self.assertFalse(bucket.allow())

    def test_leak_makes_room_for_new_requests(self) -> None:
        clock = FakeClock()
        bucket = LeakyBucket(capacity=4, leak_rate=1, clock=clock)
        for _ in range(4):
            bucket.allow()
        clock.advance(2)
        self.assertTrue(bucket.allow())
        self.assertTrue(bucket.allow())
        self.assertFalse(bucket.allow())

    def test_bucket_drains_completely(self) -> None:
        clock = FakeClock()
        bucket = LeakyBucket(capacity=2, leak_rate=1, clock=clock)
        bucket.allow()
        bucket.allow()
        clock.advance(10)
        self.assertAlmostEqual(bucket.level, 0)
        self.assertTrue(bucket.allow())

    def test_rejects_invalid_configuration(self) -> None:
        with self.assertRaises(ValueError):
            LeakyBucket(capacity=-1, leak_rate=1)
        with self.assertRaises(ValueError):
            LeakyBucket(capacity=1, leak_rate=-1)


if __name__ == "__main__":
    unittest.main()
