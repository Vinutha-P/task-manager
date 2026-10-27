"""Build the assignment PDF from source snippets and captured screenshots."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission" / "Assignment_Report.pdf"
ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
COURIER = "/System/Library/Fonts/Supplemental/Courier New.ttf"
COURIER_BOLD = "/System/Library/Fonts/Supplemental/Courier New Bold.ttf"


class Report(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Arial", size=9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, f"Task Manager assignment  |  Page {self.page_no()}", align="C", new_x="LMARGIN", new_y="NEXT")


def snippet(pdf: Report, title: str, path: Path, start: int | None = None, end: int | None = None) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = 1 if start is None else start
    end = len(lines) if end is None else end
    numbered = []
    for number in range(start, end + 1):
        text = lines[number - 1].replace("\t", "    ")
        numbered.append(f"{number:4d}  {text}")
    body = "\n".join(numbered)
    pdf.ln(2)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("CourierNew", size=8)
    pdf.set_fill_color(245, 245, 245)
    pdf.multi_cell(0, 3.6, body, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def paragraph(pdf: Report, text: str, size: int = 11) -> None:
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=size)
    pdf.multi_cell(0, 5.5, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def heading(pdf: Report, text: str) -> None:
    pdf.ln(2)
    pdf.set_text_color(20, 50, 90)
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def trim(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    background = rgb.getpixel((0, 0))
    pixels = rgb.load()
    width, height = rgb.size
    top, bottom, left, right = height, 0, width, 0
    found = False
    for y in range(height):
        for x in range(0, width, 3):
            pixel = pixels[x, y]
            if any(abs(channel - base) > 18 for channel, base in zip(pixel, background)):
                found = True
                top = min(top, y)
                bottom = max(bottom, y)
                left = min(left, x)
                right = max(right, x)
    if not found:
        return rgb
    pad = 16
    return rgb.crop(
        (
            max(0, left - pad),
            max(0, top - pad),
            min(width, right + pad),
            min(height, bottom + pad),
        )
    )


def add_image(pdf: Report, path: Path, caption: str) -> None:
    pdf.ln(2)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 6, caption, new_x="LMARGIN", new_y="NEXT")
    image = trim(Image.open(path))
    width, height = image.size
    max_w = 180
    max_h = 230
    chunk_height = max(1, int(max_h * width / max_w))
    y = 0
    part = 0
    while y < height:
        piece = image.crop((0, y, width, min(height, y + chunk_height)))
        display_h = max_w * piece.size[1] / piece.size[0]
        if pdf.get_y() + display_h > 275:
            pdf.add_page()
        temp = ROOT / "submission" / f"_piece_{path.stem}_{part}.png"
        piece.save(temp)
        pdf.image(str(temp), w=max_w)
        temp.unlink(missing_ok=True)
        pdf.ln(2)
        y += chunk_height
        part += 1


def build() -> None:
    pdf = Report(format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(15, 15, 15)
    pdf.add_font("Arial", "", ARIAL)
    pdf.add_font("Arial", "B", ARIAL_BOLD)
    pdf.add_font("CourierNew", "", COURIER)
    pdf.add_font("CourierNew", "B", COURIER_BOLD)
    pdf.add_page()

    pdf.set_font("Arial", "B", 20)
    pdf.multi_cell(0, 9, "Assignment report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(
        0,
        6,
        "gRPC Task Manager, Order API with MCP, Kong rate limiting,\n"
        "and token bucket / leaky bucket algorithms.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(2)
    paragraph(
        pdf,
        "Repository: https://github.com/Vinutha-P/task-manager.git\n"
        "Language: Python 3. The same virtual environment builds and runs all three questions.",
    )

    heading(pdf, "How to compile and run")
    paragraph(
        pdf,
        "From the repository root:",
    )
    pdf.set_font("CourierNew", size=9)
    pdf.multi_cell(
        0,
        4.5,
        "python3 -m venv .venv\n"
        "source .venv/bin/activate\n"
        "pip install -r requirements.txt\n"
        "\n"
        "cd question1\n"
        "python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/task.proto\n"
        "python server.py          # terminal 1, listens on 127.0.0.1:50051\n"
        "python client.py          # terminal 2\n"
        "\n"
        "cd ../question3\n"
        "python -m unittest test_rate_limiters.py\n"
        "python demo.py\n"
        "\n"
        "cd ../question2\n"
        "python order_api.py       # terminal 1, http://127.0.0.1:5001\n"
        "docker-compose up         # terminal 2, Kong on http://127.0.0.1:8000\n"
        "ORDER_API_BASE=http://127.0.0.1:8000/api/orders python mcp_client_demo.py\n"
        "python demo_rate_limit.py",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    paragraph(
        pdf,
        "Kong has no maintained native macOS package. question2/docker-compose.yml runs the official kong:3.9 image. "
        "Colima or Docker Desktop can provide the Docker daemon. question2/kong/kong.yml is the same gateway for a local kong binary, "
        "and question2/kong/register_via_admin_api.sh registers the service through the Admin API. "
        "The scripts directory also runs each question end to end: sh scripts/run_question1.sh, "
        "sh scripts/run_question3.sh, and sh scripts/run_question2.sh. "
        "Restart Kong between rate-limit runs. The limit is stored in memory and is 5 requests per minute per IP.",
    )

    heading(pdf, "Question 1 — gRPC Task Manager")
    paragraph(
        pdf,
        "The proto file defines Task, CreateTaskRequest, GetTaskRequest, UpdateTaskRequest, and TaskService. "
        "ListTasksRequest and TaskUpdate are the extra messages required by the streaming RPCs. "
        "The server keeps tasks in a dictionary, assigns incremental ids from 1, and accepts only the statuses "
        "pending, in_progress, and done. id < 1 returns INVALID_ARGUMENT, an unknown id returns NOT_FOUND, "
        "and a bad status returns FAILED_PRECONDITION. Every GetTask call uses a 1-second deadline. "
        "The deadline demonstration sends metadata x-simulate-delay-seconds: 2, the server sleeps for 2 seconds, "
        "and the client prints DEADLINE_EXCEEDED and continues.",
    )
    snippet(pdf, "question1/proto/task.proto", ROOT / "question1/proto/task.proto")
    snippet(pdf, "question1/server.py — handlers and validation", ROOT / "question1/server.py", 48, 137)
    snippet(pdf, "question1/client.py — 1-second deadline and graceful timeout", ROOT / "question1/client.py", 40, 62)
    add_image(pdf, ROOT / "evidence/screenshots/q1_client.png", "Screenshot: client creates three tasks, fetches task 2, streams the list, applies three updates, and shows the three errors plus the timeout.")
    add_image(pdf, ROOT / "evidence/screenshots/q1_server.png", "Screenshot: server log. GetTask for the deadline case sleeps 2.0 seconds.")

    heading(pdf, "Question 2 — Order API, MCP tool, and Kong")
    paragraph(
        pdf,
        "Flow used in the demonstration: MCP client -> MCP server (tool order_api) -> Kong route /api/orders -> Order API. "
        "The API stores orders in memory. Each order has an integer id, item, quantity, and status created. "
        "quantity must be an integer greater than 0. Invalid input returns HTTP 400, a missing order returns HTTP 404, "
        "and a successful create returns HTTP 201. The MCP server validates arguments with the JSON Schema in "
        "question2/schemas/order_api_tool.json before it makes an HTTP call. create_order calls POST /orders, "
        "get_order calls GET /orders/{id}, and list_orders calls GET /orders. "
        "Kong registers service order-api, route /api/orders, and the rate-limiting plugin at 5 requests per minute. "
        "A pre-function plugin rewrites /api/orders to /orders. One nginx worker is used so the local counter is global.",
    )
    snippet(pdf, "question2/order_api.py — validation and endpoints", ROOT / "question2/order_api.py", 44, 92)
    snippet(pdf, "question2/mcp_server.py — schema check and routing", ROOT / "question2/mcp_server.py", 34, 70)
    snippet(pdf, "question2/kong/kong.docker.yml — service, route, and 5/minute limit", ROOT / "question2/kong/kong.docker.yml")
    snippet(pdf, "question2/docker-compose.yml", ROOT / "question2/docker-compose.yml")
    add_image(pdf, ROOT / "evidence/screenshots/q2_backend_orders.png", "Screenshot: browser open on http://127.0.0.1:5001/orders, the Order API backend.")
    add_image(pdf, ROOT / "evidence/screenshots/q2_kong_orders.png", "Screenshot: browser open on http://127.0.0.1:8000/api/orders, the same orders through the Kong route.")
    add_image(pdf, ROOT / "evidence/screenshots/q2_direct_errors.png", "Screenshot: direct API rejects quantity 0 with HTTP 400 and an unknown id with HTTP 404.")
    add_image(pdf, ROOT / "evidence/screenshots/q2_mcp.png", "Screenshot: MCP stdio session. The tool name is order_api. Creates, get, and list go through Kong. Quantity 0 is rejected by the schema, and a missing order returns the API 404 JSON.")
    add_image(pdf, ROOT / "evidence/screenshots/q2_rate_limit_terminal.png", "Screenshot: seven POSTs to the Kong route. Requests 1-5 return HTTP 201 and the remaining-minute counter falls from 4 to 0. Requests 6 and 7 return HTTP 429 from kong/3.9.4.")
    add_image(pdf, ROOT / "evidence/screenshots/q2_kong_rate_limit.png", "Screenshot: browser on http://127.0.0.1:8000/api/orders after the limit is exhausted. Kong responds: API rate limit exceeded (5 requests per minute).")
    add_image(pdf, ROOT / "evidence/screenshots/q2_tests.png", "Screenshot: unit tests for the Order API and the MCP tool.")

    heading(pdf, "Question 3 — Token bucket and leaky bucket")
    paragraph(
        pdf,
        "TokenBucket starts full. It refills continuously at refill_rate tokens per second, capped at capacity. "
        "A request is allowed only when a whole token is available, so the caller can burst up to capacity and is then limited to the refill rate. "
        "LeakyBucket starts empty. Each allowed request adds one unit and the level leaks continuously at leak_rate units per second. "
        "A request that would raise the level above capacity is rejected, which smooths traffic to the leak rate. "
        "Both classes take an injectable clock so the tests advance time without sleeping. The demo prints a virtual-clock timeline and a short real-time burst.",
    )
    snippet(pdf, "question3/rate_limiters.py", ROOT / "question3/rate_limiters.py")
    add_image(pdf, ROOT / "evidence/screenshots/q3_demo.png", "Screenshot: token bucket allows a burst of 5 then denies, and leaky bucket allows a burst of 4 then denies. Later timestamps show refill and leak.")
    add_image(pdf, ROOT / "evidence/screenshots/q3_tests.png", "Screenshot: eight unit tests passed.")

    heading(pdf, "Requirement checklist")
    paragraph(
        pdf,
        "Question 1: CreateTask, GetTask, ListTasks server stream, UpdateTask, and StreamTaskUpdates bidirectional stream are implemented. "
        "Ids are incremental. Status is restricted to pending, in_progress, and done. "
        "The client creates three tasks, fetches task 2, lists every task, and prints three streamed updates. "
        "INVALID_ARGUMENT, NOT_FOUND, FAILED_PRECONDITION, and DEADLINE_EXCEEDED are all visible in the client screenshot.\n\n"
        "Question 2: REST endpoints, in-memory orders, quantity validation, and JSON error codes are implemented. "
        "The MCP tool is named order_api and exposes create_order, get_order, and list_orders. "
        "Kong publishes route /api/orders with rate limiting set to 5 requests per minute. "
        "The terminal screenshot and the browser screenshot both show HTTP 429 after the fifth request.\n\n"
        "Question 3: TokenBucket and LeakyBucket are implemented in Python, with tests and a runnable demo.",
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {pdf.page_no()} pages)")


if __name__ == "__main__":
    build()
