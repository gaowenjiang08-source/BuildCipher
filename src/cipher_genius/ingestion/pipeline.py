"""Pipeline to parse enterprise documents and emit retrieval-ready chunks."""

from __future__ import annotations

import json
from pathlib import Path

from cipher_genius.ingestion.chunkers import SemanticChunker
from cipher_genius.ingestion.models import KnowledgeChunk, ParsedDocument
from cipher_genius.ingestion.parsers import PDFDocumentParser, WordDocumentParser


class KnowledgeIngestionPipeline:
    """Parse PDF/Word inputs into normalized retrieval chunks."""

    def __init__(self, *, chunker: SemanticChunker | None = None):
        self.chunker = chunker or SemanticChunker()
        self._parsers = {
            ".pdf": PDFDocumentParser(),
            ".docx": WordDocumentParser(),
        }

    def ingest_file(
        self,
        source_path: str | Path,
        *,
        doc_type: str,
        metadata: dict | None = None,
        title: str | None = None,
    ) -> tuple[ParsedDocument, list[KnowledgeChunk]]:
        path = Path(source_path)
        parser = self._parsers.get(path.suffix.lower())
        if parser is None:
            raise ValueError(f"Unsupported source file: {path}")

        parsed = parser.parse(path)
        if title:
            parsed = parsed.model_copy(update={"title": title})
        chunks = self.chunker.chunk(parsed, doc_type=doc_type, metadata=metadata)
        return parsed, chunks

    def ingest_directory(
        self,
        source_dir: str | Path,
        *,
        doc_type: str,
        metadata: dict | None = None,
    ) -> list[KnowledgeChunk]:
        root = Path(source_dir)
        chunks: list[KnowledgeChunk] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in self._parsers:
                continue
            _, file_chunks = self.ingest_file(path, doc_type=doc_type, metadata=metadata)
            chunks.extend(file_chunks)
        return chunks

    def write_jsonl(self, chunks: list[KnowledgeChunk], output_path: str | Path) -> Path:
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(json.dumps(chunk.model_dump(mode="json"), ensure_ascii=False) + "\n")
        return target_path
