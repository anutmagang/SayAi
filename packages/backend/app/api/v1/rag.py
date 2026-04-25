from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from litellm import completion
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models.rag_collection import RagCollection
from app.db.models.rag_document import RagDocument
from app.db.models.user import User
from app.db.session import get_db
from app.services.rag_service import (
    create_collection,
    delete_collection_vectors,
    ingest_text_document,
    search_collection,
)

router = APIRouter(prefix="/rag")


class RagCollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    embedding_model: str | None = None


class RagCollectionOut(BaseModel):
    id: UUID
    name: str
    embedding_model: str
    vector_size: int
    qdrant_collection: str

    model_config = {"from_attributes": True}


class RagDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1, max_length=2_000_000)
    source_uri: str | None = Field(default=None, max_length=500)


class RagDocumentOut(BaseModel):
    id: UUID
    title: str
    status: str
    chunk_count: int
    source_uri: str | None
    error: str | None

    model_config = {"from_attributes": True}


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    answer: bool = False


@router.post("/collections", response_model=RagCollectionOut)
def rag_create_collection(
    body: RagCollectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RagCollection:
    return create_collection(
        db=db,
        user_id=user.id,
        name=body.name,
        embedding_model=body.embedding_model,
    )


@router.get("/collections", response_model=list[RagCollectionOut])
def rag_list_collections(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RagCollection]:
    rows = db.scalars(
        select(RagCollection)
        .where(RagCollection.user_id == user.id)
        .order_by(RagCollection.created_at.desc())
    ).all()
    return list(rows)


@router.delete(
    "/collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def rag_delete_collection(
    collection_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    coll = db.get(RagCollection, collection_id)
    if coll is None or coll.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    delete_collection_vectors(collection=coll)
    db.delete(coll)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/collections/{collection_id}/documents", response_model=RagDocumentOut)
def rag_add_document(
    collection_id: UUID,
    body: RagDocumentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RagDocument:
    coll = db.get(RagCollection, collection_id)
    if coll is None or coll.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return ingest_text_document(
        db=db,
        collection=coll,
        title=body.title,
        text=body.text,
        source_uri=body.source_uri,
    )


@router.get("/collections/{collection_id}/documents", response_model=list[RagDocumentOut])
def rag_list_documents(
    collection_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RagDocument]:
    coll = db.get(RagCollection, collection_id)
    if coll is None or coll.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    rows = db.scalars(
        select(RagDocument)
        .where(RagDocument.collection_id == collection_id)
        .order_by(RagDocument.created_at.desc())
    ).all()
    return list(rows)


@router.post("/collections/{collection_id}/query")
def rag_query(
    collection_id: UUID,
    body: RagQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    coll = db.get(RagCollection, collection_id)
    if coll is None or coll.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    hits = search_collection(collection=coll, query=body.query, top_k=body.top_k)
    if not body.answer:
        return {"hits": hits}

    settings = get_settings()
    context = "\n\n".join([f"- ({h.get('score')}): {h.get('text')}" for h in hits])
    prompt = (
        "Answer the question using ONLY the provided context snippets.\n\n"
        f"QUESTION:\n{body.query}\n\nCONTEXT:\n{context}\n"
    )
    resp = completion(
        model=settings.default_llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    answer = str(resp.choices[0].message.content or "")
    return {"hits": hits, "answer": answer}
