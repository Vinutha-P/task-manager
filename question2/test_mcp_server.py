"""MCP tool validation and routing, against the in-process Order API."""

from __future__ import annotations

import threading
import time
import unittest
from socket import socket
from urllib.error import URLError
from urllib.request import urlopen

from werkzeug.serving import make_server

import order_api
import mcp_server


def _free_port() -> int:
    with socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class McpToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        order_api.reset_store()
        cls.port = _free_port()
        cls.httpd = make_server("127.0.0.1", cls.port, order_api.app, threaded=True)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}/orders"
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                urlopen(f"http://127.0.0.1:{cls.port}/health", timeout=0.2).read()
                break
            except (URLError, TimeoutError, ConnectionError):
                time.sleep(0.05)
        else:
            raise RuntimeError("order API test server did not start")

    def test_schema_rejects_non_positive_quantity(self) -> None:
        with self.assertRaises(ValueError):
            mcp_server.call_order_api(
                {"action": "create_order", "item": "pen", "quantity": 0},
                self.base,
            )

    def test_schema_rejects_unknown_action(self) -> None:
        with self.assertRaises(ValueError):
            mcp_server.call_order_api({"action": "delete_order", "id": 1}, self.base)

    def test_create_get_and_list_round_trip(self) -> None:
        created = mcp_server.call_order_api(
            {"action": "create_order", "item": "stapler", "quantity": 1},
            self.base,
        )
        self.assertEqual(created["status_code"], 201)
        order_id = created["body"]["id"]
        fetched = mcp_server.call_order_api(
            {"action": "get_order", "id": order_id},
            self.base,
        )
        self.assertEqual(fetched["status_code"], 200)
        self.assertEqual(fetched["body"]["status"], "created")
        listed = mcp_server.call_order_api({"action": "list_orders"}, self.base)
        self.assertEqual(listed["status_code"], 200)
        self.assertGreaterEqual(len(listed["body"]), 1)

    def test_missing_order_returns_api_json(self) -> None:
        result = mcp_server.call_order_api({"action": "get_order", "id": 999}, self.base)
        self.assertEqual(result["status_code"], 404)
        self.assertIn("error", result["body"])


if __name__ == "__main__":
    unittest.main()
