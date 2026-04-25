from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.rag_collection import RagCollection
from app.db.models.rag_document import RagDocument
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts
from app.services.qdrant_http import QdrantHttp


def qdrant_name_for_collection(collection_id: UUID) -> str:
    return f"sayai_rag_{str(collection_id).replace('-', '_')}"


def create_collection(
    *,
    db: Session,
    user_id: UUID,
    name: str,
    embedding_model: str | None = None,
) -> RagCollection:
    settings = get_settings()
    model = embedding_model or settings.embedding_model
    vector_size = int(settings.embedding_dimensions)

    new_id = uuid.uuid4()
    qname = qdrant_name_for_collection(new_id)
    row = RagCollection(
        id=new_id,
        user_id=user_id,
        name=name,
        embedding_model=model,
        vector_size=vector_size,
        qdrant_collection=qname,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    if settings.qdrant_url:
        q = QdrantHttp(settings.qdrant_url)
        try:
            q.create_collection(qname, vector_size=vector_size)
        finally:
            q.close()

    return row


def ingest_text_document(
    *,
    db: Session,
    collection: RagCollection,
    title: str,
    text: str,
    source_uri: str | None = None,
) -> RagDocument:
    settings = get_settings()
    doc = RagDocument(
        collection_id=collection.id,
        title=title,
        status="processing",
        chunk_count=0,
        source_uri=source_uri,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    if not settings.qdrant_url:
        doc.status = "failed"
        doc.error = "QDRANT_URL is not configured"
        db.add(doc)
        db.commit()
        return doc

    try:
        chunks = chunk_text(
            text,
            chunk_size=settings.rag_chunk_size,
            overlap=settings.rag_chunk_overlap,
        )
        if not chunks:
            doc.status = "ready"
            doc.chunk_count = 0
            db.add(doc)
            db.commit()
            return doc

        vectors = embed_texts(model=collection.embedding_model, texts=chunks)
        if len(vectors) != len(chunks):
            raise RuntimeError("Embedding batch size mismatch")

        points: list[dict[str, Any]] = []
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors, strict=True)):
            pid = str(uuid.uuid5(doc.id, f"chunk:{idx}"))
            points.append(
                {
                    "id": pid,
                    "vector": vec,
                    "payload": {
                        "document_id": str(doc.id),
                        "chunk_index": idx,
                        "text": chunk,
                        "title": title,
                    },
                }
            )

        q = QdrantHttp(settings.qdrant_url)
        try:
            q.upsert_points(collection.qdrant_collection, points)
        finally:
            q.close()

        doc.status = "ready"
        doc.chunk_count = len(chunks)
        doc.error = None
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc
    except Exception as exc:  # pragma: no cover - integration heavy
        doc.status = "failed"
        doc.error = str(exc)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc


def search_collection(
    *,
    collection: RagCollection,
    query: str,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.qdrant_url:
        return []

    k = int(top_k or settings.rag_default_top_k)
    vec = embed_texts(model=collection.embedding_model, texts=[query])[0]

    q = QdrantHttp(settings.qdrant_url)
    try:
        hits = q.search(collection.qdrant_collection, vector=vec, limit=k)
    finally:
        q.close()

    out: list[dict[str, Any]] = []
    for h in hits:
        payload = h.get("payload") or {}
        out.append(
            {
                "score": h.get("score"),
                "text": payload.get("text"),
                "document_id": payload.get("document_id"),
                "chunk_index": payload.get("chunk_index"),
                "title": payload.get("title"),
            }
        )
    return out


def delete_collection_vectors(*, collection: RagCollection) -> None:
    settings = get_settings()
    if not settings.qdrant_url:
        return
    q = QdrantHttp(settings.qdrant_url)
    try:
        q.delete_collection(collection.qdrant_collection)
    finally:
        q.close()
