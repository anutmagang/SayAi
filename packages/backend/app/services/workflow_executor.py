from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from litellm import completion
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.redis_client import get_sync_redis
from app.db.models.rag_collection import RagCollection
from app.db.models.workflow import Workflow
from app.db.models.workflow_run import WorkflowRun
from app.db.models.workflow_run_step import WorkflowRunStep
from app.db.session import get_session_factory
from app.services.rag_service import search_collection
from app.services.wf_events import emit_wf_event
from app.services.workflow_graph import parse_flow_definition, topo_sort_nodes

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _format_map(template: str, ctx: dict[str, Any]) -> str:
    flat: dict[str, str] = {}
    for k, v in ctx.items():
        key = str(k)
        if isinstance(v, (str, int, float, bool)) or v is None:
            flat[key] = "" if v is None else str(v)
        else:
            flat[key] = json.dumps(v, default=str)

    class _Default(dict):
        def __missing__(self, key: str) -> str:  # noqa: ARG002
            return ""

    try:
        return template.format_map(_Default(flat))
    except Exception:
        return template


def _add_wf_step(
    *,
    db: Session,
    r,
    workflow_run_id: UUID,
    seq_holder: list[int],
    node_id: str,
    step_type: str,
    name: str,
    detail: dict[str, Any] | None,
    status: str = "completed",
    error: str | None = None,
) -> None:
    seq = seq_holder[0]
    seq_holder[0] = seq + 1
    step = WorkflowRunStep(
        workflow_run_id=workflow_run_id,
        seq=seq,
        node_id=node_id,
        step_type=step_type,
        name=name,
        status=status,
        detail=detail,
        error=error,
        ended_at=_now(),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    emit_wf_event(
        r,
        workflow_run_id,
        {
            "type": "step",
            "step": {
                "id": str(step.id),
                "seq": step.seq,
                "node_id": step.node_id,
                "step_type": step.step_type,
                "name": step.name,
                "status": step.status,
                "detail": step.detail,
                "error": step.error,
            },
        },
    )


def execute_workflow_run(workflow_run_id: UUID) -> None:
    settings = get_settings()
    r = get_sync_redis()
    factory = get_session_factory()
    db = factory()
    seq_holder = [1]

    try:
        wf_run = db.get(WorkflowRun, workflow_run_id)
        if wf_run is None:
            return
        if wf_run.status != "pending":
            return

        wf = db.get(Workflow, wf_run.workflow_id)
        if wf is None:
            wf_run.status = "failed"
            wf_run.error = "Workflow missing"
            wf_run.completed_at = _now()
            db.add(wf_run)
            db.commit()
            return

        wf_run.status = "running"
        db.add(wf_run)
        db.commit()

        emit_wf_event(
            r,
            workflow_run_id,
            {"type": "workflow.started", "workflow_run_id": str(workflow_run_id)},
        )

        nodes, edges = parse_flow_definition(wf.definition)
        ordered = topo_sort_nodes(nodes, edges)

        context: dict[str, Any] = dict(wf_run.inputs or {})

        required: list[str] = []
        for n in ordered:
            if str(n.get("type")) == "wfInput":
                data = n.get("data") or {}
                required.extend(list(data.get("required") or []))
        for key in set(required):
            if key not in context:
                raise ValueError(f"Missing required input: {key}")

        outputs: dict[str, Any] = {}

        for node in ordered:
            node_id = str(node["id"])
            ntype = str(node.get("type") or "")
            data = node.get("data") or {}
            label = str(data.get("label") or node_id)

            emit_wf_event(
                r,
                workflow_run_id,
                {"type": "node.started", "node_id": node_id, "node_type": ntype, "label": label},
            )

            if ntype == "wfInput":
                _add_wf_step(
                    db=db,
                    r=r,
                    workflow_run_id=workflow_run_id,
                    seq_holder=seq_holder,
                    node_id=node_id,
                    step_type="input",
                    name=label,
                    detail={"keys": list((wf_run.inputs or {}).keys())},
                )
                continue

            if ntype == "wfLlm":
                prompt_t = str(data.get("prompt") or "")
                prompt = _format_map(prompt_t, context)
                model = str(data.get("model") or settings.default_llm_model)
                resp = completion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
                text = str(resp.choices[0].message.content or "")
                out_key = str(data.get("output_key") or node_id)
                context[out_key] = text
                _add_wf_step(
                    db=db,
                    r=r,
                    workflow_run_id=workflow_run_id,
                    seq_holder=seq_holder,
                    node_id=node_id,
                    step_type="llm",
                    name=label,
                    detail={"model": model, "prompt": prompt, "output_key": out_key},
                )
                continue

            if ntype == "wfRag":
                collection_id = UUID(str(data.get("collection_id")))
                query_t = str(data.get("query") or "")
                query = _format_map(query_t, context)
                top_k = int(data.get("top_k") or settings.rag_default_top_k)
                out_key = str(data.get("output_key") or node_id)

                coll = db.get(RagCollection, collection_id)
                if coll is None or coll.user_id != wf_run.user_id:
                    raise ValueError("RAG collection not found")

                hits = search_collection(collection=coll, query=query, top_k=top_k)
                joined = "\n\n".join([h.get("text") or "" for h in hits if h.get("text")])
                context[out_key] = joined
                _add_wf_step(
                    db=db,
                    r=r,
                    workflow_run_id=workflow_run_id,
                    seq_holder=seq_holder,
                    node_id=node_id,
                    step_type="rag",
                    name=label,
                    detail={
                        "collection_id": str(collection_id),
                        "hits": len(hits),
                        "output_key": out_key,
                    },
                )
                continue

            if ntype == "wfOutput":
                pick = str(data.get("pick") or data.get("output_key") or "")
                if not pick or pick not in context:
                    raise ValueError("wfOutput pick must reference an existing context key")
                out_name = str(data.get("name") or "result")
                outputs[out_name] = context[pick]
                _add_wf_step(
                    db=db,
                    r=r,
                    workflow_run_id=workflow_run_id,
                    seq_holder=seq_holder,
                    node_id=node_id,
                    step_type="output",
                    name=label,
                    detail={"pick": pick, "name": out_name},
                )
                continue

            raise ValueError(f"Unsupported node type: {ntype}")

        wf_run.status = "completed"
        wf_run.outputs = outputs
        wf_run.completed_at = _now()
        wf_run.error = None
        db.add(wf_run)
        db.commit()

        emit_wf_event(
            r,
            workflow_run_id,
            {"type": "workflow.completed", "outputs": outputs},
        )
    except Exception as exc:
        logger.exception("Workflow execution failed")
        try:
            wf_run = db.get(WorkflowRun, workflow_run_id)
            if wf_run is not None:
                wf_run.status = "failed"
                wf_run.error = str(exc)
                wf_run.completed_at = _now()
                db.add(wf_run)
                db.commit()
            emit_wf_event(r, workflow_run_id, {"type": "error", "message": str(exc)})
        except Exception:
            logger.exception("Failed to persist workflow failure")
    finally:
        db.close()
