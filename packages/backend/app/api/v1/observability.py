from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.run import Run
from app.db.models.user import User
from app.db.models.workflow_run import WorkflowRun
from app.db.session import get_db

router = APIRouter(prefix="/observability")


@router.get("/summary")
def observability_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    window_hours: int = Query(default=24, ge=1, le=24 * 30),
) -> dict[str, Any]:
    since = datetime.now(tz=UTC) - timedelta(hours=window_hours)

    runs_count = db.scalar(
        select(func.count(Run.id)).where(Run.user_id == user.id, Run.created_at >= since)
    )
    pt_sum = db.scalar(
        select(func.coalesce(func.sum(Run.prompt_tokens), 0)).where(
            Run.user_id == user.id,
            Run.created_at >= since,
        )
    )
    ct_sum = db.scalar(
        select(func.coalesce(func.sum(Run.completion_tokens), 0)).where(
            Run.user_id == user.id,
            Run.created_at >= since,
        )
    )

    wf_count = db.scalar(
        select(func.count(WorkflowRun.id)).where(
            WorkflowRun.user_id == user.id,
            WorkflowRun.created_at >= since,
        )
    )

    return {
        "window_hours": window_hours,
        "since": since.isoformat(),
        "runs": {
            "count": int(runs_count or 0),
            "prompt_tokens": int(pt_sum or 0),
            "completion_tokens": int(ct_sum or 0),
        },
        "workflow_runs": {
            "count": int(wf_count or 0),
        },
    }
