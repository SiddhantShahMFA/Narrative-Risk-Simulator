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
        """
        Initialize an embedding index and load persisted records if a compatible index file exists.
        
        Parameters:
            index_path (Path): Filesystem path where the index (model name and records) is persisted.
            embedding_model (str | None): Embedding model name to use; when omitted the system default is selected.
            embedder (Embedder | None): Callable that converts a list of texts to embedding vectors; when omitted a default embedder (OpenAI-based) is used.
        
        Notes:
            The constructor sets instance attributes (index_path, embedding_model, _embedder) and populates self._records by loading the existing index only if the stored model matches the selected embedding_model.
        """
        self.index_path = index_path
        self.embedding_model = embedding_model or get_openai_embedding_model()
        self._embedder = embedder or self._openai_embed
        self._records = self._load()

    def sync_documents(self, documents: list[Document]) -> int:
        """
        Synchronize the index with a set of documents by ensuring each document chunk has an up-to-date embedding.
        
        Splits each document into chunks, reuses cached embeddings for chunks whose text hash matches the stored hash, computes embeddings for new or changed chunks using the configured embedder, updates the in-memory records, and persists the index to disk.
        
        Parameters:
            documents (list[Document]): Documents to index; each document will be chunked and processed.
        
        Returns:
            int: The number of text chunks that required new embeddings.
        """
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
        """
        Retrieve the stored document chunks most similar to the provided query text, ranked by cosine similarity of embeddings.
        
        Parameters:
            text (str): Query text to search for.
            limit (int): Maximum number of results to return.
        
        Returns:
            list[RetrievedEvidence]: Up to `limit` retrieved evidence objects in descending similarity order. Each item includes document metadata, a snippet of up to 320 characters, `similarity` clamped to the range [0.0, 1.0], and optional `summary` and `risk_notes`.
        """
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
        """
        Persist the current embedding model and records to the configured index file.
        
        Writes a JSON payload containing `embedding_model` and `records` to `self.index_path`, overwriting any existing file and using UTF-8 encoding.
        """
        payload = {
            "embedding_model": self.embedding_model,
            "records": self._records,
        }
        self.index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load(self) -> dict[str, dict[str, object]]:
        """
        Load persisted index records from the index file if it exists and matches the configured embedding model.
        
        Reads the JSON payload at self.index_path and returns its "records" mapping only when the file exists and the stored "embedding_model" equals self.embedding_model; otherwise returns an empty dictionary.
        
        Returns:
            dict[str, dict[str, object]]: Mapping of chunk IDs to record objects from the persisted index, or an empty dict if the index file is missing or the embedding model does not match.
        """
        if not self.index_path.exists():
            return {}
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        if payload.get("embedding_model") != self.embedding_model:
            return {}
        return payload.get("records", {})

    def _openai_embed(self, texts: list[str]) -> list[list[float]]:
        """
        Obtain embedding vectors for a list of input texts using the instance's configured embedding model.
        
        Parameters:
            texts (list[str]): Input strings to embed. Order is preserved.
        
        Returns:
            list[list[float]]: Embedding vectors corresponding to each input text, in the same order.
        """
        client = OpenAI()
        response = client.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in response.data]


def chunk_document(document: Document, chunk_size: int = 700) -> list[DocumentChunk]:
    """
    Split a Document into sized text chunks while preserving document metadata.
    
    Parameters:
        document (Document): The source document to split into chunks; its body will be partitioned.
        chunk_size (int): Maximum number of characters for each chunk.
    
    Returns:
        list[DocumentChunk]: A list of DocumentChunk objects containing the chunked text (via _compose_chunk_text) and preserved metadata. Each chunk includes `chunk_index` and `total_chunks` to indicate position and count.
    """
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
    """
    Compute the cosine similarity between two float vectors.
    
    Returns:
        float: Cosine similarity in the range [-1.0, 1.0]; returns 0.0 if either vector has zero magnitude.
    
    Raises:
        ValueError: If the input vectors have different lengths.
    """
    numerator = sum(left * right for left, right in zip(vector_a, vector_b, strict=True))
    norm_a = math.sqrt(sum(value * value for value in vector_a))
    norm_b = math.sqrt(sum(value * value for value in vector_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return numerator / (norm_a * norm_b)


def _compose_chunk_text(document: Document, chunk: str) -> str:
    """
    Builds a single text block for a document chunk that includes labeled metadata fields and the chunk body.
    
    Parameters:
    	document (Document): The source document whose metadata will be included (title, source_type, optional summary, optional risk_notes).
    	chunk (str): The chunked portion of the document body to include under the "Body" label.
    
    Returns:
    	composed (str): A single string with labeled sections ("Title", "Type", optional "Summary", optional "Risk notes", and "Body") separated by newlines.
    """
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
    """
    Compute the SHA-256 hash of the given text and return it as a lowercase hex string.
    
    The text is encoded as UTF-8 before hashing.
    
    Returns:
        str: Hex-encoded SHA-256 digest of `text`.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _truncate(text: str, limit: int) -> str:
    """
    Truncates text to a maximum length, appending an ellipsis if truncation occurs.
    
    Parameters:
        text (str): The input string to truncate.
        limit (int): Maximum allowed length of the returned string, including the trailing ellipsis when truncation occurs. Values less than or equal to 3 may return a result consisting only of the ellipsis or be shorter than `limit`.
    
    Returns:
        str: The original `text` if its length is less than or equal to `limit`; otherwise a truncated string of at most `limit` characters that ends with "..." .
    """
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
