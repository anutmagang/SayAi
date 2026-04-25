from __future__ import annotations

import pytest

from sayai.orchestrator.dag import DAGError, DAGExecutor
from sayai.orchestrator.task import Task, tasks_from_plan


class FakePool:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def run(
        self,
        task: Task,
        *,
        dag_results: dict[str, str],
        scratch: dict | None = None,
        retry: bool = False,
    ) -> str:
        self.calls.append(task.id)
        return f"done:{task.id}"


@pytest.mark.asyncio
async def test_dag_parallel_wave() -> None:
    pool = FakePool()
    dag = DAGExecutor(pool)
    tasks = [
        Task("a", "coder", "A", depends_on=[]),
        Task("b", "coder", "B", depends_on=[]),
        Task("c", "coder", "C", depends_on=["a", "b"]),
    ]
    out = await dag.execute(tasks)
    assert out["a"].startswith("done:")
    assert out["b"].startswith("done:")
    assert out["c"].startswith("done:")
    assert set(pool.calls) == {"a", "b", "c"}


def test_tasks_from_plan() -> None:
    t = tasks_from_plan(
        [
            {"id": "x", "agent_type": "searcher", "instruction": "look", "depends_on": []},
        ]
    )
    assert len(t) == 1
    assert t[0].agent_type == "searcher"


@pytest.mark.asyncio
async def test_dag_circular_raises() -> None:
    pool = FakePool()
    dag = DAGExecutor(pool)
    tasks = [
        Task("a", "coder", "A", depends_on=["b"]),
        Task("b", "coder", "B", depends_on=["a"]),
    ]
    with pytest.raises(DAGError):
        await dag.execute(tasks)
