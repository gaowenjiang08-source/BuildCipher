"""Chunk parsed document blocks into retrieval-ready knowledge chunks."""

from __future__ import annotations

import re

from cipher_genius.ingestion.models import DocumentBlock, KnowledgeChunk, ParsedDocument

_DIGIT_HEADING_PATTERN = re.compile(r"^(?P<code>\d+(?:\.\d+){0,6})")
_CHAPTER_HEADING_PATTERN = re.compile(r"^第(?P<label>[一二三四五六七八九十百千万]+)(?P<kind>[章节条])")
_LIST_HEADING_PATTERN = re.compile(r"^(?P<label>[一二三四五六七八九十]+)、")


class SemanticChunker:
    """Chunk by headings and bounded content size instead of fixed raw slices."""

    def __init__(self, max_chars: int = 1400):
        self.max_chars = max(400, int(max_chars))

    def chunk(
        self,
        parsed_document: ParsedDocument,
        *,
        doc_type: str,
        metadata: dict | None = None,
    ) -> list[KnowledgeChunk]:
        merged_metadata = {**parsed_document.metadata, **(metadata or {})}
        chunks: list[KnowledgeChunk] = []
        heading_stack: list[dict[str, str | int]] = []
        buffer: list[DocumentBlock] = []
        chunk_index = 0
        section_counts: dict[str, int] = {}

        for block in parsed_document.blocks:
            if block.block_type == "heading":
                if buffer:
                    chunk_index += 1
                    chunks.append(
                        self._build_chunk(
                            parsed_document,
                            buffer,
                            doc_type,
                            heading_stack,
                            chunk_index,
                            section_counts,
                            merged_metadata,
                        )
                    )
                    buffer = []
                heading_stack = self._update_heading_stack(heading_stack, block.text.strip())
                continue

            if buffer and self._buffer_length(buffer) + len(block.text) > self.max_chars:
                chunk_index += 1
                chunks.append(
                    self._build_chunk(
                        parsed_document,
                        buffer,
                        doc_type,
                        heading_stack,
                        chunk_index,
                        section_counts,
                        merged_metadata,
                    )
                )
                buffer = []
            buffer.append(block)

        if buffer:
            chunk_index += 1
            chunks.append(
                self._build_chunk(
                    parsed_document,
                    buffer,
                    doc_type,
                    heading_stack,
                    chunk_index,
                    section_counts,
                    merged_metadata,
                )
            )

        return chunks

    def _build_chunk(
        self,
        parsed_document: ParsedDocument,
        buffer: list[DocumentBlock],
        doc_type: str,
        heading_stack: list[dict[str, str | int]],
        chunk_index: int,
        section_counts: dict[str, int],
        metadata: dict,
    ) -> KnowledgeChunk:
        content_lines = [block.text.strip() for block in buffer if block.text.strip()]
        section = self._current_section(parsed_document, heading_stack)
        section_path = self._section_path(parsed_document, heading_stack)
        section_code = self._section_code(heading_stack)
        if section and (not content_lines or content_lines[0] != section):
            content_lines.insert(0, section)
        content = "\n\n".join(content_lines)
        citation = next((block.text.strip() for block in buffer if block.text.strip()), "")[:240]
        page_indexes = [block.page_index for block in buffer if block.page_index is not None]
        block_types = sorted({block.block_type for block in buffer})
        page_span = [min(page_indexes), max(page_indexes)] if page_indexes else []
        chunk_suffix = self._chunk_suffix(section_code, chunk_index, section_counts)

        return KnowledgeChunk(
            doc_id=parsed_document.doc_id,
            chunk_id=f"{parsed_document.doc_id}#{chunk_suffix}",
            doc_type=doc_type,
            title=parsed_document.title,
            section=section,
            content=content,
            citation_snippet=citation,
            source_path=parsed_document.source_path,
            source_page=page_indexes[0] if page_indexes else None,
            metadata={
                **metadata,
                "source_type": parsed_document.source_type,
                "block_types": block_types,
                "page_span": page_span,
                "block_count": len(buffer),
                "section_path": section_path,
                "heading_level": heading_stack[-1]["level"] if heading_stack else 0,
                "clause_code": section_code,
            },
        )

    def _buffer_length(self, buffer: list[DocumentBlock]) -> int:
        return sum(len(block.text or "") for block in buffer)

    def _update_heading_stack(
        self,
        heading_stack: list[dict[str, str | int]],
        heading_text: str,
    ) -> list[dict[str, str | int]]:
        heading = heading_text.strip()
        if not heading:
            return heading_stack

        level, code = self._heading_level_and_code(heading)
        normalized = list(heading_stack)
        while normalized and int(normalized[-1]["level"]) >= level:
            normalized.pop()
        normalized.append({"level": level, "text": heading, "code": code})
        return normalized

    def _heading_level_and_code(self, heading: str) -> tuple[int, str]:
        digit_match = _DIGIT_HEADING_PATTERN.match(heading)
        if digit_match:
            code = digit_match.group("code")
            return code.count(".") + 1, code

        chapter_match = _CHAPTER_HEADING_PATTERN.match(heading)
        if chapter_match:
            kind = chapter_match.group("kind")
            level = {"章": 1, "节": 2, "条": 4}.get(kind, 1)
            return level, chapter_match.group("label")

        list_match = _LIST_HEADING_PATTERN.match(heading)
        if list_match:
            return 5, list_match.group("label")

        return 6, heading[:24]

    def _current_section(
        self,
        parsed_document: ParsedDocument,
        heading_stack: list[dict[str, str | int]],
    ) -> str:
        if not heading_stack:
            return parsed_document.title
        return str(heading_stack[-1]["text"])

    def _section_path(
        self,
        parsed_document: ParsedDocument,
        heading_stack: list[dict[str, str | int]],
    ) -> list[str]:
        if not heading_stack:
            return [parsed_document.title]
        return [str(item["text"]) for item in heading_stack]

    def _section_code(self, heading_stack: list[dict[str, str | int]]) -> str:
        if not heading_stack:
            return ""
        code = str(heading_stack[-1].get("code") or "").strip()
        return code

    def _chunk_suffix(self, section_code: str, chunk_index: int, section_counts: dict[str, int]) -> str:
        normalized = re.sub(r"[^0-9A-Za-z._-]+", "-", section_code).strip("-")
        if normalized:
            section_counts[normalized] = section_counts.get(normalized, 0) + 1
            if section_counts[normalized] == 1:
                return normalized
            return f"{normalized}-part-{section_counts[normalized]}"
        return f"chunk-{chunk_index}"
