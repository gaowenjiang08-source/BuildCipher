"""Structured ingestion objects for PDF/Word knowledge parsing."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class DocumentBlock(BaseModel):
    """A single ordered block extracted from a source document."""

    block_id: str
    block_type: str
    text: str
    order: int
    page_index: Optional[int] = None
    section_hint: Optional[str] = None
    bbox: Optional[List[float]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    """Normalized document representation before chunking."""

    doc_id: str
    title: str
    source_path: str
    source_type: str
    blocks: List[DocumentBlock] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeChunk(BaseModel):
    """Chunk ready for retrieval, embedding, and citation."""

    doc_id: str
    chunk_id: str
    doc_type: str
    title: str
    section: str = ""
    content: str
    citation_snippet: str = ""
    source_path: str
    source_page: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
