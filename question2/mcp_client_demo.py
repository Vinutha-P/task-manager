"""Small MCP client that drives the order_api tool over stdio.

The client performs the assignment flow:
  create_order, get_order, list_orders
and then shows schema validation failures before any HTTP call is made.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class McpClient:
    def __init__(self, process: subprocess.Popen) -> None:
        self.process = process
        self._next_id = 1

    def request(self, method: str, params: dict | None = None) -> dict:
        message_id = self._next_id
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": message_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)
        while True:
            response = self._read()
            if response.get("id") == message_id:
                return response

    def notify(self, method: str, params: dict | None = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    def _send(self, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii")
        assert self.process.stdin is not None
        self.process.stdin.write(header)
        self.process.stdin.write(raw)
        self.process.stdin.flush()

    def _read(self) -> dict:
        assert self.process.stdout is not None
        headers = {}
        while True:
            line = self.process.stdout.readline()
            if line == b"":
                raise RuntimeError("MCP server closed stdout")
            if line in (b"\r\n", b"\n"):
                break
            decoded = line.decode("utf-8").strip()
            if ":" not in decoded:
                continue
            name, value = decoded.split(":", 1)
            headers[name.strip().lower()] = value.strip()
        length = int(headers["content-length"])
        body = self.process.stdout.read(length)
        return json.loads(body.decode("utf-8"))

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        self.process.wait(timeout=5)


def _print_response(title: str, response: dict) -> None:
    print(f"\n--- {title} ---")
    if "error" in response:
        print(json.dumps(response["error"], indent=2))
        return
    result = response.get("result", {})
    content = result.get("content")
    if content:
        print(f"isError={result.get('isError')}")
        for block in content:
            print(block.get("text", ""))
        return
    print(json.dumps(result, indent=2))


def main() -> int:
    env = os.environ.copy()
    env.setdefault("ORDER_API_BASE", "http://127.0.0.1:8000/api/orders")
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "mcp_server.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
        env=env,
        cwd=str(ROOT),
    )
    client = McpClient(process)
    try:
        print(f"ORDER_API_BASE={env['ORDER_API_BASE']}")
        initialized = client.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "order-api-demo", "version": "1.0.0"},
            },
        )
        _print_response("initialize", initialized)
        client.notify("notifications/initialized")

        tools = client.request("tools/list")
        _print_response("tools/list (tool name order_api)", tools)

        _print_response(
            "create_order notebook quantity 2",
            client.request(
                "tools/call",
                {
                    "name": "order_api",
                    "arguments": {
                        "action": "create_order",
                        "item": "notebook",
                        "quantity": 2,
                    },
                },
            ),
        )
        _print_response(
            "create_order pencil quantity 5",
            client.request(
                "tools/call",
                {
                    "name": "order_api",
                    "arguments": {
                        "action": "create_order",
                        "item": "pencil",
                        "quantity": 5,
                    },
                },
            ),
        )
        _print_response(
            "get_order id 1",
            client.request(
                "tools/call",
                {"name": "order_api", "arguments": {"action": "get_order", "id": 1}},
            ),
        )
        _print_response(
            "list_orders",
            client.request(
                "tools/call",
                {"name": "order_api", "arguments": {"action": "list_orders"}},
            ),
        )
        _print_response(
            "schema rejection: quantity must be > 0",
            client.request(
                "tools/call",
                {
                    "name": "order_api",
                    "arguments": {
                        "action": "create_order",
                        "item": "eraser",
                        "quantity": 0,
                    },
                },
            ),
        )
        _print_response(
            "schema rejection: get_order requires id",
            client.request(
                "tools/call",
                {"name": "order_api", "arguments": {"action": "get_order"}},
            ),
        )
        _print_response(
            "API 404 through the tool",
            client.request(
                "tools/call",
                {"name": "order_api", "arguments": {"action": "get_order", "id": 999}},
            ),
        )
    finally:
        client.close()
    print("\nMCP demo finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
