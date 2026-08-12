"""Word parser for enterprise knowledge ingestion."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from cipher_genius.ingestion.models import DocumentBlock, ParsedDocument

_HEADING_PATTERN = re.compile(r"^(?:\d+(?:\.\d+){0,4}|第[一二三四五六七八九十百]+[章节条]|[一二三四五六七八九十]+、)")


class WordDocumentParser:
    """Parse `.docx` files into ordered blocks while preserving document order."""

    def parse(self, path: str | Path) -> ParsedDocument:
        source_path = Path(path)
        suffix = source_path.suffix.lower()
        if suffix == ".doc":
            raise ValueError(f"Legacy .doc is not supported directly: {source_path}. Convert it to .docx first.")
        if suffix != ".docx":
            raise ValueError(f"Unsupported Word source: {source_path}")

        try:
            from docx import Document
            from docx.table import Table
            from docx.text.paragraph import Paragraph
        except ImportError as exc:
            raise RuntimeError("Word parsing requires python-docx. Install project dependencies first.") from exc

        document = Document(str(source_path))
        blocks: list[DocumentBlock] = []
        order = 0
        heading_count = 0
        table_count = 0

        for item in self._iter_block_items(document, Paragraph, Table):
            if isinstance(item, Paragraph):
                text = str(item.text or "").strip()
                if not text:
                    continue
                block_type = "heading" if self._looks_like_heading(text, style_name=item.style.name if item.style else "") else "paragraph"
                if block_type == "heading":
                    heading_count += 1
                order += 1
                blocks.append(
                    DocumentBlock(
                        block_id=f"{source_path.stem}-{order}",
                        block_type=block_type,
                        text=text,
                        order=order,
                        section_hint=text if block_type == "heading" else None,
                        metadata={"style_name": item.style.name if item.style else ""},
                    )
                )
                continue

            rows: list[str] = []
            for row in item.rows:
                cells = [str(cell.text or "").strip() for cell in row.cells]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                table_count += 1
                order += 1
                blocks.append(
                    DocumentBlock(
                        block_id=f"{source_path.stem}-table-{order}",
                        block_type="table",
                        text="\n".join(rows),
                        order=order,
                    )
                )

        return ParsedDocument(
            doc_id=f"word::{source_path.stem}",
            title=source_path.stem,
            source_path=str(source_path),
            source_type="docx",
            blocks=blocks,
            metadata={
                "heading_count": heading_count,
                "table_count": table_count,
                "paragraph_count": len([item for item in blocks if item.block_type == "paragraph"]),
                "extraction_backend": "python-docx",
            },
        )

    def _iter_block_items(self, document, paragraph_cls, table_cls) -> Iterable[object]:
        for child in document.element.body.iterchildren():
            tag = str(child.tag)
            if tag.endswith("}p"):
                yield paragraph_cls(child, document)
            elif tag.endswith("}tbl"):
                yield table_cls(child, document)

    def _looks_like_heading(self, text: str, style_name: str = "") -> bool:
        normalized_style = str(style_name or "").lower()
        if normalized_style.startswith("heading"):
            return True
        if len(text) <= 80 and _HEADING_PATTERN.match(text):
            return True
        return len(text) <= 40 and not text.endswith((".", "。", "；", ";"))
