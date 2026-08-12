"""PDF parser for enterprise knowledge ingestion."""

from __future__ import annotations

import re
from pathlib import Path

from cipher_genius.ingestion.models import DocumentBlock, ParsedDocument

_HEADING_PATTERN = re.compile(r"^(?:\d+(?:\.\d+){0,4}|第[一二三四五六七八九十百]+[章节条]|[一二三四五六七八九十]+、)")
_SHORT_HEADING_KEYWORDS = (
    "概述",
    "背景",
    "范围",
    "要求",
    "说明",
    "流程",
    "架构",
    "附录",
    "风险",
    "审计",
)


class PDFDocumentParser:
    """Parse text-first PDFs into ordered blocks with page references."""

    def parse(self, path: str | Path) -> ParsedDocument:
        source_path = Path(path)
        if source_path.suffix.lower() != ".pdf":
            raise ValueError(f"Unsupported PDF source: {source_path}")

        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF parsing requires pypdf. Install project dependencies first.") from exc

        reader = PdfReader(str(source_path))
        table_blocks = self._extract_table_blocks(source_path)
        blocks: list[DocumentBlock] = []
        order = 0
        empty_pages = 0

        for page_index, page in enumerate(reader.pages, start=1):
            raw_text = (page.extract_text() or "").strip()
            if not raw_text:
                empty_pages += 1
            for block_type, text in self._split_text_blocks(raw_text):
                if not text:
                    continue
                order += 1
                blocks.append(
                    DocumentBlock(
                        block_id=f"{source_path.stem}-p{page_index}-{order}",
                        block_type=block_type,
                        text=text,
                        order=order,
                        page_index=page_index,
                        section_hint=text if block_type == "heading" else None,
                    )
                )

            for table_text in table_blocks.get(page_index, []):
                order += 1
                blocks.append(
                    DocumentBlock(
                        block_id=f"{source_path.stem}-p{page_index}-table-{order}",
                        block_type="table",
                        text=table_text,
                        order=order,
                        page_index=page_index,
                    )
                )

        return ParsedDocument(
            doc_id=f"pdf::{source_path.stem}",
            title=source_path.stem,
            source_path=str(source_path),
            source_type="pdf",
            blocks=blocks,
            metadata={
                "page_count": len(reader.pages),
                "empty_page_count": empty_pages,
                "table_count": sum(len(items) for items in table_blocks.values()),
                "extraction_backend": "pypdf+pdfplumber" if table_blocks else "pypdf",
            },
        )

    def _split_text_blocks(self, raw_text: str) -> list[tuple[str, str]]:
        if not raw_text:
            return []

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        blocks: list[tuple[str, str]] = []
        paragraph_parts: list[str] = []

        def flush_paragraph() -> None:
            if paragraph_parts:
                blocks.append(("paragraph", " ".join(paragraph_parts).strip()))
                paragraph_parts.clear()

        for line in lines:
            if self._looks_like_heading(line):
                flush_paragraph()
                blocks.append(("heading", line))
                continue

            paragraph_parts.append(line)
            if line.endswith((".", "。", "；", ";", "!", "！", "?", "？", ":")):
                flush_paragraph()

        flush_paragraph()
        return blocks

    def _looks_like_heading(self, line: str) -> bool:
        if len(line) <= 80 and _HEADING_PATTERN.match(line):
            return True
        normalized = line.strip()
        if len(normalized) > 24:
            return False
        return any(normalized == keyword or normalized.endswith(keyword) for keyword in _SHORT_HEADING_KEYWORDS)

    def _extract_table_blocks(self, source_path: Path) -> dict[int, list[str]]:
        try:
            import pdfplumber
        except ImportError:
            return {}

        tables_by_page: dict[int, list[str]] = {}
        try:
            with pdfplumber.open(str(source_path)) as pdf:
                for page_index, page in enumerate(pdf.pages, start=1):
                    page_tables: list[str] = []
                    for table in page.extract_tables() or []:
                        rows = []
                        for row in table:
                            normalized = [str(cell or "").strip() for cell in row]
                            if any(normalized):
                                rows.append(" | ".join(normalized))
                        if rows:
                            page_tables.append("\n".join(rows))
                    if page_tables:
                        tables_by_page[page_index] = page_tables
        except Exception:
            return {}
        return tables_by_page
