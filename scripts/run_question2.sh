#!/bin/sh
# Start the Order API and Kong, then run the MCP and rate-limit demonstrations.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/evidence/logs"
mkdir -p "$LOG_DIR"
cd "$ROOT/question2"
if [ -S "$HOME/.colima/default/docker.sock" ]; then
  export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
fi

"$ROOT/.venv/bin/python" order_api.py > "$LOG_DIR/q2_api.log" 2>&1 &
API_PID=$!
cleanup() {
  kill "$API_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Waiting for the Order API on port 5001"
ready=0
i=0
while [ "$i" -lt 50 ]; do
  if "$ROOT/.venv/bin/python" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/health', timeout=0.5).read()" >/dev/null 2>&1; then
    ready=1
    break
  fi
  i=$((i + 1))
  sleep 0.2
done
if [ "$ready" -ne 1 ]; then
  echo "Order API did not start. See $LOG_DIR/q2_api.log"
  exit 1
fi

if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
elif command -v docker >/dev/null 2>&1; then
  COMPOSE="docker compose"
else
  echo "Docker is not installed. Install Docker or Colima, then re-run this script."
  exit 1
fi

echo "Starting Kong"
$COMPOSE up -d
echo "Waiting for Kong proxy"
ready=0
i=0
while [ "$i" -lt 60 ]; do
  if "$ROOT/.venv/bin/python" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/status', timeout=0.5).read()" >/dev/null 2>&1; then
    ready=1
    break
  fi
  i=$((i + 1))
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "Kong did not become ready. Recent container logs:"
  $COMPOSE logs --tail=80 || true
  exit 1
fi

# A previous run in the same minute would still be counted, so recycle Kong
# before the measured burst and again before the MCP calls.
$COMPOSE restart
i=0
while [ "$i" -lt 60 ]; do
  if "$ROOT/.venv/bin/python" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/status', timeout=0.5).read()" >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 1
done

echo "Rate-limit burst (expect HTTP 429 after 5 requests)"
"$ROOT/.venv/bin/python" demo_rate_limit.py | tee "$LOG_DIR/q2_rate_limit.log"

$COMPOSE restart
i=0
while [ "$i" -lt 60 ]; do
  if "$ROOT/.venv/bin/python" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/status', timeout=0.5).read()" >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 1
done

echo "MCP tool demonstration through Kong"
ORDER_API_BASE="http://127.0.0.1:8000/api/orders" \
  "$ROOT/.venv/bin/python" mcp_client_demo.py | tee "$LOG_DIR/q2_mcp.log"

echo "Question 2 demonstration finished. Kong is still running."
echo "Stop it with: cd \"$ROOT/question2\" && $COMPOSE down"
