"""MCP server that exposes the Order API as the tool ``order_api``.

The server speaks MCP over stdio using Content-Length framing.
``ORDER_API_BASE`` is the Kong route, defaulting to
http://127.0.0.1:8000/api/orders. Each tool call is validated against
schemas/order_api_tool.json and then routed to POST /orders, GET /orders/{id},
or GET /orders.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import jsonschema
import requests

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "order_api_tool.json"
PROTOCOL_VERSION = "2024-11-05"
DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/orders"

with SCHEMA_PATH.open(encoding="utf-8") as handle:
    TOOL = json.load(handle)

VALIDATOR = jsonschema.Draft202012Validator(TOOL["inputSchema"])


def base_url() -> str:
    return os.environ.get("ORDER_API_BASE", DEFAULT_BASE_URL).rstrip("/")


def validate_arguments(arguments: dict) -> None:
    errors = sorted(VALIDATOR.iter_errors(arguments), key=lambda item: list(item.path))
    if not errors:
        return
    messages = []
    for error in errors:
        location = ".".join(str(part) for part in error.path) or "arguments"
        messages.append(f"{location}: {error.message}")
    raise ValueError("; ".join(messages))


def call_order_api(arguments: dict, api_base: str | None = None) -> dict:
    """Validate arguments and return the upstream JSON response."""
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    validate_arguments(arguments)
    root = (api_base or base_url()).rstrip("/")
    action = arguments["action"]
    if action == "create_order":
        response = requests.post(
            root,
            json={"item": arguments["item"], "quantity": arguments["quantity"]},
            timeout=5,
        )
    elif action == "get_order":
        response = requests.get(f"{root}/{arguments['id']}", timeout=5)
    elif action == "list_orders":
        response = requests.get(root, timeout=5)
    else:
        raise ValueError(f"unsupported action: {action}")

    try:
        body = response.json()
    except ValueError:
        body = {"error": response.text or "upstream returned a non-JSON body"}
    return {"status_code": response.status_code, "body": body}


def _tool_result(payload: dict, is_error: bool) -> dict:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
        "isError": is_error,
    }


def handle_message(message: dict) -> dict | None:
    method = message.get("method")
    message_id = message.get("id")
    params = message.get("params") or {}

    if method == "notifications/initialized":
        return None

    if message_id is None and method and method.startswith("notifications/"):
        return None

    if method == "initialize":
        return _result(
            message_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "order-api-mcp", "version": "1.0.0"},
            },
        )

    if method == "ping":
        return _result(message_id, {})

    if method == "tools/list":
        return _result(message_id, {"tools": [TOOL]})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name != TOOL["name"]:
            return _error(message_id, -32602, f"unknown tool: {name}")
        try:
            payload = call_order_api(arguments)
        except ValueError as error:
            return _result(message_id, _tool_result({"error": str(error)}, True))
        except requests.RequestException as error:
            return _result(
                message_id,
                _tool_result({"error": f"order API request failed: {error}"}, True),
            )
        is_error = payload["status_code"] >= 400
        return _result(message_id, _tool_result(payload, is_error))

    if method is None:
        return _error(message_id, -32600, "invalid request")
    return _error(message_id, -32601, f"method not found: {method}")


def _result(message_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def read_message(stream) -> dict | None:
    headers = {}
    while True:
        line = stream.readline()
        if line == b"":
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("utf-8").strip()
        if ":" not in decoded:
            continue
        name, value = decoded.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    if "content-length" not in headers:
        raise ValueError("missing Content-Length header")
    length = int(headers["content-length"])
    body = stream.read(length)
    if len(body) != length:
        raise ValueError("truncated MCP message")
    return json.loads(body.decode("utf-8"))


def write_message(payload: dict) -> None:
    raw = json.dumps(payload).encode("utf-8")
    header = f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii")
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def serve() -> None:
    print(f"order-api MCP server started, upstream {base_url()}", file=sys.stderr, flush=True)
    while True:
        try:
            message = read_message(sys.stdin.buffer)
        except Exception as error:  # noqa: BLE001 - stdio must stay alive and report the error
            write_message(_error(None, -32700, f"parse error: {error}"))
            continue
        if message is None:
            return
        try:
            response = handle_message(message)
        except Exception as error:  # noqa: BLE001 - report unexpected handler failures to the client
            response = _error(message.get("id"), -32603, str(error))
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    serve()
