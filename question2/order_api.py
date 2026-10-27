"""In-memory Order API.

Endpoints:
  POST /orders
  GET  /orders/<id>
  GET  /orders

The same handlers are also mounted at /api/orders so a Kong route of
/api/orders can forward the original path unchanged. Kong's declarative
config still rewrites /api/orders to /orders before the request reaches
this process.
"""

from __future__ import annotations

import os
import socket
import threading

from flask import Flask, jsonify, request

# Werkzeug's HTTP server resolves the bind address with getfqdn(). On machines
# where reverse DNS is slow, that lookup blocks the process before it listens.
socket.getfqdn = lambda name="": name or "localhost"

app = Flask(__name__)
_lock = threading.Lock()
_orders: dict[int, dict] = {}
_next_id = 1


def reset_store() -> None:
    """Clear in-memory orders. Used by tests."""
    global _next_id
    with _lock:
        _orders.clear()
        _next_id = 1


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _parse_order_body():
    if not request.is_json:
        return None, _error("Content-Type must be application/json", 415)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, _error("request body must be a JSON object", 400)
    item = data.get("item")
    quantity = data.get("quantity")
    if not isinstance(item, str) or not item.strip():
        return None, _error("item is required and must be a non-empty string", 400)
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        return None, _error("quantity must be an integer greater than 0", 400)
    if quantity <= 0:
        return None, _error("quantity must be an integer greater than 0", 400)
    return {"item": item.strip(), "quantity": quantity}, None


def create_order():
    global _next_id
    payload, error = _parse_order_body()
    if error is not None:
        return error
    with _lock:
        order_id = _next_id
        _next_id += 1
        order = {
            "id": order_id,
            "item": payload["item"],
            "quantity": payload["quantity"],
            "status": "created",
        }
        _orders[order_id] = order
    print(f"POST order id={order['id']} item={order['item']!r} quantity={order['quantity']}", flush=True)
    return jsonify(order), 201


def get_order(order_id: int):
    with _lock:
        order = _orders.get(order_id)
    if order is None:
        return _error(f"order {order_id} not found", 404)
    return jsonify(order), 200


def list_orders():
    with _lock:
        orders = list(_orders.values())
    return jsonify(orders), 200


def health():
    return jsonify({"status": "ok"}), 200


def _mount(prefix: str) -> None:
    slug = prefix.strip("/").replace("/", "_")
    app.add_url_rule(f"{prefix}", view_func=list_orders, methods=["GET"], endpoint=f"list_{slug}")
    app.add_url_rule(f"{prefix}", view_func=create_order, methods=["POST"], endpoint=f"create_{slug}")
    app.add_url_rule(
        f"{prefix}/<int:order_id>",
        view_func=get_order,
        methods=["GET"],
        endpoint=f"get_{slug}",
    )


_mount("/orders")
_mount("/api/orders")
app.add_url_rule("/health", view_func=health, methods=["GET"])


if __name__ == "__main__":
    port = int(os.environ.get("ORDER_API_PORT", "5001"))
    host = os.environ.get("ORDER_API_HOST", "0.0.0.0")
    print(f"Order API listening on http://127.0.0.1:{port}", flush=True)
    app.run(host=host, port=port, threaded=True)
