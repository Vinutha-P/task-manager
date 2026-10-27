#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT/question3"
"$ROOT/.venv/bin/python" -m unittest test_rate_limiters.py | tee "$ROOT/evidence/logs/q3_tests.log"
"$ROOT/.venv/bin/python" demo.py | tee "$ROOT/evidence/logs/q3_demo.log"
