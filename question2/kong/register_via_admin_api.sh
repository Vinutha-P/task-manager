#!/bin/sh
# Optional path: register the Order API with a running Kong Admin API.
# Declarative config in kong.yml is the primary setup.
set -eu

ADMIN="${KONG_ADMIN:-http://127.0.0.1:8001}"
UPSTREAM="${ORDER_API_UPSTREAM:-http://127.0.0.1:5001}"

curl -sS -X POST "$ADMIN/services" \
  --data name=order-api \
  --data url="$UPSTREAM"

curl -sS -X POST "$ADMIN/services/order-api/routes" \
  --data "name=order-api-route" \
  --data "paths[]=/api/orders" \
  --data "strip_path=false"

curl -sS -X POST "$ADMIN/services/order-api/plugins" \
  --data "name=rate-limiting" \
  --data "config.minute=5" \
  --data "config.policy=local" \
  --data "config.limit_by=ip" \
  --data "config.fault_tolerant=true" \
  --data "config.hide_client_headers=false" \
  --data "config.error_code=429" \
  --data "config.error_message=API rate limit exceeded (5 requests per minute)"

echo
echo "Registered order-api at $ADMIN with route /api/orders and a limit of 5 requests per minute."
