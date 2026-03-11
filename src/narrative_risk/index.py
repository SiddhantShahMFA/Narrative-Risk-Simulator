"""Embedding cache and vector search."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Callable

from openai import OpenAI

from narrative_risk.config import CACHE_DIR, INDEX_PATH, get_openai_embedding_model
from narrative_risk.models import Document, DocumentChunk, RetrievedEvidence


Embedder = Callable[[list[str]], list[list[float]]]


class EmbeddingIndex:
    def __init__(
        self,
        *,
        index_path: Path = INDEX_PATH,
        embedding_model: str | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.index_path = index_path
        self.embedding_model = embedding_model or get_openai_embedding_model()
        self._embedder = embedder or self._openai_embed
        self._records = self._load()

    def sync_documents(self, documents: list[Document]) -> int:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        new_records: dict[str, dict[str, object]] = {}
        texts_to_embed: list[str] = []
        keys_to_embed: list[str] = []

        for document in documents:
            for chunk in chunk_document(document):
                text_hash = _hash_text(chunk.text)
                previous = self._records.get(chunk.chunk_id)
                record = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "title": chunk.title,
                    "source_type": chunk.source_type.value,
                    "text": chunk.text,
                    "summary": chunk.summary,
                    "date": chunk.date.isoformat() if chunk.date else None,
                    "tags": chunk.tags,
                    "risk_notes": chunk.risk_notes,
                    "hash": text_hash,
                    "embedding": None,
                }
                if previous and previous.get("hash") == text_hash:
                    record["embedding"] = previous.get("embedding")
                else:
                    texts_to_embed.append(chunk.text)
                    keys_to_embed.append(chunk.chunk_id)
                new_records[chunk.chunk_id] = record

        if texts_to_embed:
            embeddings = self._embedder(texts_to_embed)
            for key, embedding in zip(keys_to_embed, embeddings, strict=True):
                new_records[key]["embedding"] = embedding

        self._records = new_records
        self._persist()
        return len(texts_to_embed)

    def query(self, text: str, limit: int = 8) -> list[RetrievedEvidence]:
        if not self._records:
            return []
        [query_embedding] = self._embedder([text])
        scored: list[tuple[float, dict[str, object]]] = []
        for record in self._records.values():
            embedding = record.get("embedding")
            if not embedding:
                continue
            similarity = cosine_similarity(query_embedding, embedding)
            scored.append((similarity, record))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedEvidence(
                document_id=str(record["document_id"]),
                title=str(record["title"]),
                source_type=str(record["source_type"]),
                snippet=_truncate(str(record["text"]), 320),
                similarity=max(0.0, min(1.0, similarity)),
                summary=str(record.get("summary") or ""),
                risk_notes=str(record.get("risk_notes") or ""),
            )
            for similarity, record in scored[:limit]
        ]

    def _persist(self) -> None:
        payload = {
            "embedding_model": self.embedding_model,
            "records": self._records,
        }
        self.index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load(self) -> dict[str, dict[str, object]]:
        if not self.index_path.exists():
            return {}
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        if payload.get("embedding_model") != self.embedding_model:
            return {}
        return payload.get("records", {})

    def _openai_embed(self, texts: list[str]) -> list[list[float]]:
        client = OpenAI()
        response = client.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in response.data]


def chunk_document(document: Document, chunk_size: int = 700) -> list[DocumentChunk]:
    sections = [part.strip() for part in document.body.split("\n\n") if part.strip()]
    if not sections:
        sections = [document.body.strip()]

    chunks: list[str] = []
    buffer = ""
    for section in sections:
        proposal = f"{buffer}\n\n{section}".strip() if buffer else section
        if len(proposal) <= chunk_size:
            buffer = proposal
            continue
        if buffer:
            chunks.append(buffer)
            buffer = section
        else:
            chunks.append(section[:chunk_size])
            remainder = section[chunk_size:]
            while remainder:
                chunks.append(remainder[:chunk_size])
                remainder = remainder[chunk_size:]
            buffer = ""
    if buffer:
        chunks.append(buffer)

    return [
        DocumentChunk(
            chunk_id=f"{document.id}-chunk-{index}",
            document_id=document.id,
            title=document.title,
            source_type=document.source_type,
            text=_compose_chunk_text(document, chunk),
            summary=document.summary,
            date=document.date,
            tags=document.tags,
            risk_notes=document.risk_notes,
            chunk_index=index,
            total_chunks=len(chunks),
        )
        for index, chunk in enumerate(chunks)
    ]


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    numerator = sum(left * right for left, right in zip(vector_a, vector_b, strict=True))
    norm_a = math.sqrt(sum(value * value for value in vector_a))
    norm_b = math.sqrt(sum(value * value for value in vector_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return numerator / (norm_a * norm_b)


def _compose_chunk_text(document: Document, chunk: str) -> str:
    parts = [
        f"Title: {document.title}",
        f"Type: {document.source_type.value}",
    ]
    if document.summary:
        parts.append(f"Summary: {document.summary}")
    if document.risk_notes:
        parts.append(f"Risk notes: {document.risk_notes}")
    parts.append(f"Body: {chunk}")
    return "\n".join(parts)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
