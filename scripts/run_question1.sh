#!/bin/sh
# Generate Python stubs from task.proto and run the Question 1 demonstration.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/evidence/logs"
cd "$ROOT/question1"
"$ROOT/.venv/bin/python" -m grpc_tools.protoc \
  -I proto \
  --python_out=. \
  --grpc_python_out=. \
  proto/task.proto

"$ROOT/.venv/bin/python" server.py > "$ROOT/evidence/logs/q1_server.log" 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT
sleep 1
"$ROOT/.venv/bin/python" client.py | tee "$ROOT/evidence/logs/q1_client.log"
