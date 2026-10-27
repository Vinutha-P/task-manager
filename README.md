# Assignment: gRPC Task Manager, MCP Order API, and Rate Limiters

Python 3.10 or newer is required. The commands below were verified with Python 3.14. Create the virtual environment from the repository root.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Question 1 — gRPC Task Manager

Terminal 1:

```bash
cd question1
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/task.proto
python server.py
```

Terminal 2:

```bash
cd question1
python client.py
```

The server listens on `127.0.0.1:50051`. The client creates three tasks, fetches task 2 with a one-second deadline, streams the task list, sends three bidirectional updates, and prints the three required gRPC errors. It then calls `GetTask` again with metadata `x-simulate-delay-seconds: 2`. The server sleeps for two seconds and the client handles `DEADLINE_EXCEEDED`.

Generated files `task_pb2.py` and `task_pb2_grpc.py` are created beside `server.py`. They are safe to regenerate.

## Question 2 — Order API, MCP tool, and Kong

Terminal 1, the API backend:

```bash
cd question2
python order_api.py
```

The API listens on `http://127.0.0.1:5001` and accepts `POST /orders`, `GET /orders/{id}`, and `GET /orders`.

Terminal 2, Kong in DB-less mode. Kong does not publish a maintained native macOS package. Run the official image with Docker Desktop or Colima:

```bash
brew install colima docker docker-compose
colima start
cd question2
docker-compose up
```

`question2/docker-compose.yml` loads `question2/kong/kong.docker.yml`. That file registers the service, the route `/api/orders`, and the rate-limiting plugin at 5 requests per minute. A `pre-function` plugin rewrites `/api/orders` to `/orders` before the request reaches the backend. The backend also accepts `/api/orders` directly.

If the `kong` binary is already installed, the same gateway can be started without Docker:

```bash
mkdir -p question2/kong/prefix
kong start -c question2/kong/kong.conf
```

`question2/kong/kong.yml` is that native configuration. `question2/kong/register_via_admin_api.sh` is the equivalent Admin API registration.

Terminal 3, the MCP demonstration. The server calls Kong, not the backend port:

```bash
cd question2
export ORDER_API_BASE=http://127.0.0.1:8000/api/orders
python mcp_client_demo.py
```

`mcp_client_demo.py` starts `mcp_server.py` over stdio, lists the `order_api` tool, and invokes `create_order`, `get_order`, and `list_orders`.

Rate-limit demonstration (more than 5 requests):

```bash
cd question2
python demo_rate_limit.py
```

Requests 1–5 return HTTP 201. Requests 6 and 7 return HTTP 429. Restart Kong (`kong stop -c question2/kong/kong.conf` and `kong start` again) to clear the in-memory counter.

Direct checks without Kong:

```bash
curl -s -X POST http://127.0.0.1:5001/orders \
  -H 'Content-Type: application/json' \
  -d '{"item":"notebook","quantity":2}'
curl -s http://127.0.0.1:5001/orders/1
curl -s http://127.0.0.1:5001/orders
```

Unit tests:

```bash
cd question2
python -m unittest test_order_api.py test_mcp_server.py
```

## Question 3 — Token bucket and leaky bucket

```bash
cd question3
python -m unittest test_rate_limiters.py
python demo.py
```

`rate_limiters.py` contains `TokenBucket` and `LeakyBucket`. The demo uses a virtual clock so the allow/deny timeline is exact, then a short real-time burst.

## One-shot local run

From the repository root, after setup:

```bash
sh scripts/run_question1.sh
sh scripts/run_question3.sh
sh scripts/run_question2.sh
```

Question 2's script starts the Order API, starts Kong when the `kong` binary is on `PATH`, runs the MCP client, and sends 7 requests to show HTTP 429.

## Submission archive

`submission/Assignment_Submission.zip` contains this run guide, the source tree, and `Assignment_Report.pdf` (screenshots, code snippets, and these instructions).
