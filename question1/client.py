"""Task Manager client used by the assignment demonstration.

Flow:
1. Create three tasks.
2. Fetch task #2 with a 1-second deadline.
3. Stream every task with ListTasks.
4. Send three updates on StreamTaskUpdates and print each server response.
5. Show INVALID_ARGUMENT, NOT_FOUND, and FAILED_PRECONDITION.
6. Call GetTask again with a 1-second deadline while the server sleeps
   for 2 seconds, and handle DEADLINE_EXCEEDED without a traceback.
"""

from __future__ import annotations

import os
import sys

import grpc

import task_pb2
import task_pb2_grpc

DEADLINE_SECONDS = 1.0


def _status_line(error: grpc.RpcError) -> str:
    details = error.details() or ""
    return f"{error.code().name}: {details}"


def create_task(stub, title: str, status: str = "") -> None:
    try:
        task = stub.CreateTask(task_pb2.CreateTaskRequest(title=title, status=status))
    except grpc.RpcError as error:
        print(f"  CreateTask failed: {_status_line(error)}")
        return
    print(f"  created id={task.id} title={task.title!r} status={task.status!r}")


def get_task(stub, task_id: int, delay_seconds: float = 0.0) -> None:
    metadata = []
    if delay_seconds > 0:
        metadata.append(("x-simulate-delay-seconds", str(delay_seconds)))
    try:
        task = stub.GetTask(
            task_pb2.GetTaskRequest(id=task_id),
            timeout=DEADLINE_SECONDS,
            metadata=metadata,
        )
    except grpc.RpcError as error:
        if error.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            print(
                "  handled gracefully: DEADLINE_EXCEEDED "
                f"(client deadline {DEADLINE_SECONDS:.0f}s, "
                f"server sleep {delay_seconds:.0f}s). "
                "The call was cancelled and the client continued."
            )
            return
        print(f"  GetTask id={task_id} -> {_status_line(error)}")
        return
    print(f"  fetched id={task.id} title={task.title!r} status={task.status!r}")


def list_tasks(stub) -> None:
    count = 0
    try:
        for task in stub.ListTasks(task_pb2.ListTasksRequest()):
            count += 1
            print(f"  streamed id={task.id} title={task.title!r} status={task.status!r}")
    except grpc.RpcError as error:
        print(f"  ListTasks failed: {_status_line(error)}")
        return
    print(f"  ListTasks completed ({count} task(s))")


def stream_updates(stub, updates: list[tuple[int, str]]) -> None:
    def requests():
        for task_id, status in updates:
            print(f"  client update id={task_id} status={status!r}")
            yield task_pb2.TaskUpdate(id=task_id, status=status)

    try:
        for task in stub.StreamTaskUpdates(requests()):
            print(f"  server response id={task.id} title={task.title!r} status={task.status!r}")
    except grpc.RpcError as error:
        print(f"  StreamTaskUpdates -> {_status_line(error)}")


def update_task(stub, task_id: int, status: str) -> None:
    try:
        task = stub.UpdateTask(task_pb2.UpdateTaskRequest(id=task_id, status=status))
    except grpc.RpcError as error:
        print(f"  UpdateTask id={task_id} status={status!r} -> {_status_line(error)}")
        return
    print(f"  updated id={task.id} status={task.status!r}")


def main() -> int:
    target = os.environ.get("GRPC_TARGET", "127.0.0.1:50051")
    channel = grpc.insecure_channel(target)
    stub = task_pb2_grpc.TaskServiceStub(channel)
    print(f"Connected to {target}")
    print(f"GetTask deadline is {DEADLINE_SECONDS:.0f} second(s)")

    print("\n=== Step 1: Create three tasks ===")
    create_task(stub, "Write the design note")
    create_task(stub, "Implement the gRPC server")
    create_task(stub, "Capture the demo evidence")

    print("\n=== Step 2: Fetch task #2 (1-second deadline) ===")
    get_task(stub, 2)

    print("\n=== Step 3: ListTasks server stream ===")
    list_tasks(stub)

    print("\n=== Step 4: StreamTaskUpdates bidirectional stream ===")
    stream_updates(
        stub,
        [
            (1, "in_progress"),
            (2, "done"),
            (3, "in_progress"),
        ],
    )

    print("\n=== Error cases ===")
    print("GetTask with id < 1")
    get_task(stub, 0)
    print("GetTask for a missing id")
    get_task(stub, 999)
    print("UpdateTask with an invalid status")
    update_task(stub, 1, "archived")
    print("StreamTaskUpdates with an invalid status")
    stream_updates(stub, [(1, "cancelled")])
    print("StreamTaskUpdates for a missing id")
    stream_updates(stub, [(50, "done")])

    print("\n=== Deadline demonstration ===")
    print("Server sleeps 2 seconds; client deadline is 1 second.")
    get_task(stub, 2, delay_seconds=2)

    print("\nClient finished.")
    channel.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
