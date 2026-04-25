from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from uuid import UUID

from app.services.run_worker import execute_run
from app.services.workflow_executor import execute_workflow_run

EXECUTOR = ThreadPoolExecutor(max_workers=8)


def submit_run(run_id: UUID) -> None:
    EXECUTOR.submit(execute_run, run_id)


def submit_run_blocking(run_id: UUID, *, timeout_s: float) -> None:
    fut = EXECUTOR.submit(execute_run, run_id)
    _done, not_done = wait([fut], timeout=timeout_s)
    if fut in not_done:
        raise TimeoutError("Run execution timed out")
    fut.result()


def submit_workflow_run(workflow_run_id: UUID) -> None:
    EXECUTOR.submit(execute_workflow_run, workflow_run_id)


def submit_workflow_run_blocking(workflow_run_id: UUID, *, timeout_s: float) -> None:
    fut = EXECUTOR.submit(execute_workflow_run, workflow_run_id)
    _done, not_done = wait([fut], timeout=timeout_s)
    if fut in not_done:
        raise TimeoutError("Workflow execution timed out")
    fut.result()
