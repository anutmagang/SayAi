from __future__ import annotations


def _split_with_overlap(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        return [text]
    step = max(1, chunk_size - max(0, overlap))
    parts: list[str] = []
    i = 0
    while i < len(text):
        parts.append(text[i : i + chunk_size])
        i += step
    return parts


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: list[str] = []
    buffer = ""
    for p in paragraphs:
        candidate = f"{buffer}\n\n{p}".strip() if buffer else p
        if len(candidate) <= chunk_size:
            buffer = candidate
            continue
        if buffer:
            chunks.extend(_split_with_overlap(buffer, chunk_size, overlap))
        buffer = p

    if buffer:
        chunks.extend(_split_with_overlap(buffer, chunk_size, overlap))

    return [c.strip() for c in chunks if c.strip()]
