"""In-memory gRPC Task Manager server.

Status values are restricted to pending, in_progress, and done.
Task IDs are incremental integers starting at 1.

GetTask honors the metadata key ``x-simulate-delay-seconds``. The deadline
demonstration sets it to 2 so the handler sleeps for two seconds before
responding. Normal fetches do not sleep.
"""

from __future__ import annotations

import os
import threading
import time
from concurrent import futures

import grpc

import task_pb2
import task_pb2_grpc

VALID_STATUSES = ("pending", "in_progress", "done")
DELAY_METADATA_KEY = "x-simulate-delay-seconds"


class TaskRecord:
    def __init__(self, task_id: int, title: str, status: str) -> None:
        self.id = task_id
        self.title = title
        self.status = status

    def to_proto(self) -> task_pb2.Task:
        return task_pb2.Task(id=self.id, title=self.title, status=self.status)


class TaskService(task_pb2_grpc.TaskServiceServicer):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: dict[int, TaskRecord] = {}
        self._next_id = 1

    def CreateTask(self, request, context):
        title = request.title.strip()
        if not title:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "title is required")
        status = request.status.strip() or "pending"
        self._require_valid_status(status, context)
        with self._lock:
            task_id = self._next_id
            self._next_id += 1
            record = TaskRecord(task_id, title, status)
            self._tasks[task_id] = record
            print(f"CreateTask id={record.id} title={record.title!r} status={record.status}", flush=True)
            return record.to_proto()

    def GetTask(self, request, context):
        self._require_positive_id(request.id, context)
        delay = _delay_seconds(context)
        if delay > 0:
            print(f"GetTask id={request.id} sleeping {delay:.1f}s", flush=True)
            time.sleep(delay)
            if not context.is_active():
                return task_pb2.Task()
        record = self._require_task(request.id, context)
        print(f"GetTask id={record.id} status={record.status}", flush=True)
        return record.to_proto()

    def ListTasks(self, request, context):
        with self._lock:
            records = [record.to_proto() for record in self._tasks.values()]
        print(f"ListTasks streaming {len(records)} task(s)", flush=True)
        for task in records:
            if not context.is_active():
                return
            yield task

    def UpdateTask(self, request, context):
        updated = self._update(request.id, request.status, context)
        print(f"UpdateTask id={updated.id} status={updated.status}", flush=True)
        return updated

    def StreamTaskUpdates(self, request_iterator, context):
        for update in request_iterator:
            if not context.is_active():
                return
            updated = self._update(update.id, update.status, context)
            print(
                f"StreamTaskUpdates id={updated.id} status={updated.status}",
                flush=True,
            )
            yield updated

    def _update(self, task_id: int, status: str, context) -> task_pb2.Task:
        self._require_positive_id(task_id, context)
        self._require_valid_status(status, context)
        record = self._require_task(task_id, context)
        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"task {task_id} not found")
            current.status = status.strip()
            return current.to_proto()

    def _require_task(self, task_id: int, context) -> TaskRecord:
        with self._lock:
            record = self._tasks.get(task_id)
        if record is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"task {task_id} not found")
        return record

    @staticmethod
    def _require_positive_id(task_id: int, context) -> None:
        if task_id < 1:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "id must be >= 1")

    @staticmethod
    def _require_valid_status(status: str, context) -> None:
        if status not in VALID_STATUSES:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "status must be one of: pending, in_progress, done",
            )


def _delay_seconds(context) -> float:
    for key, value in context.invocation_metadata():
        if key.lower() == DELAY_METADATA_KEY:
            try:
                return max(0.0, float(value))
            except ValueError:
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "x-simulate-delay-seconds must be a number",
                )
    return 0.0


def serve(port: int = 50051) -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    task_pb2_grpc.add_TaskServiceServicer_to_server(TaskService(), server)
    address = f"127.0.0.1:{port}"
    server.add_insecure_port(address)
    server.start()
    print(f"TaskService listening on {address}", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    serve(int(os.environ.get("GRPC_PORT", "50051")))
