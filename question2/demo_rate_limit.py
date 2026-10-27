"""Send more than 5 requests through the Kong route and print every status."""

from __future__ import annotations

import json
import os
import sys

import requests

URL = os.environ.get("KONG_ORDERS_URL", "http://127.0.0.1:8000/api/orders")
COUNT = int(os.environ.get("RATE_LIMIT_REQUESTS", "7"))


def main() -> int:
    print(f"POST {URL}")
    print(f"Sending {COUNT} requests. The limit is 5 per minute.")
    limited = 0
    for number in range(1, COUNT + 1):
        response = requests.post(
            URL,
            json={"item": f"item-{number}", "quantity": 1},
            timeout=5,
        )
        remaining = response.headers.get("X-RateLimit-Remaining-Minute")
        limit = response.headers.get("X-RateLimit-Limit-Minute")
        retry_after = response.headers.get("Retry-After")
        print(
            f"request {number}: HTTP {response.status_code} "
            f"limit={limit} remaining={remaining} retry_after={retry_after}"
        )
        body = response.text.strip()
        if body:
            try:
                print("  body:", json.dumps(response.json()))
            except ValueError:
                print("  body:", body)
        if response.status_code == 429:
            limited += 1
    print(f"Rate-limited responses: {limited}")
    if limited == 0:
        print("Expected at least one HTTP 429 after the fifth request.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
