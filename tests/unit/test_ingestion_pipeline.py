from pathlib import Path

import pytest

from cipher_genius.ingestion import KnowledgeIngestionPipeline
from cipher_genius.ingestion.chunkers import SemanticChunker
from cipher_genius.ingestion.models import DocumentBlock, ParsedDocument
from cipher_genius.ingestion.parsers import PDFDocumentParser, WordDocumentParser


def test_word_parser_extracts_headings_paragraphs_and_tables(tmp_path: Path):
    docx = pytest.importorskip("docx")

    source_path = tmp_path / "sample.docx"
    document = docx.Document()
    document.add_heading("3.2.1 静态数据加密要求", level=1)
    document.add_paragraph("敏感数据应采用批准算法进行加密保护。")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "控制项"
    table.cell(0, 1).text = "要求"
    table.cell(1, 0).text = "密钥轮换"
    table.cell(1, 1).text = "至少每年执行一次"
    document.save(source_path)

    parsed = WordDocumentParser().parse(source_path)

    assert parsed.source_type == "docx"
    assert any(block.block_type == "heading" for block in parsed.blocks)
    assert any(block.block_type == "paragraph" for block in parsed.blocks)
    assert any(block.block_type == "table" for block in parsed.blocks)


def test_pdf_parser_and_pipeline_emit_chunks(tmp_path: Path):
    canvas = pytest.importorskip("reportlab.pdfgen.canvas").Canvas

    source_path = tmp_path / "sample.pdf"
    pdf = canvas(str(source_path))
    pdf.drawString(72, 780, "3.2.1 数据静态加密要求")
    pdf.drawString(72, 760, "科研数据平台应支持静态加密、审计留痕和密钥托管。")
    pdf.save()

    parsed = PDFDocumentParser().parse(source_path)
    assert parsed.source_type == "pdf"
    assert parsed.metadata["page_count"] == 1
    assert parsed.blocks

    pipeline = KnowledgeIngestionPipeline()
    _, chunks = pipeline.ingest_file(
        source_path,
        doc_type="standard",
        metadata={"region": "CN", "industry": "construction"},
    )
    assert chunks
    assert chunks[0].doc_type == "standard"
    assert chunks[0].source_page == 1
    assert chunks[0].metadata["region"] == "CN"


def test_semantic_chunker_creates_clause_level_chunks():
    parsed = ParsedDocument(
        doc_id="std::demo",
        title="建筑信息模型交付规范",
        source_path="knowledge/raw/construction_standard.pdf",
        source_type="pdf",
        blocks=[
            DocumentBlock(block_id="b1", block_type="heading", text="3.2 密钥管理", order=1, page_index=1),
            DocumentBlock(block_id="b2", block_type="heading", text="3.2.1 密钥轮换要求", order=2, page_index=1),
            DocumentBlock(
                block_id="b3",
                block_type="paragraph",
                text="平台应至少每年执行一次密钥轮换，并保留轮换记录。",
                order=3,
                page_index=1,
            ),
            DocumentBlock(block_id="b4", block_type="heading", text="3.2.2 密钥托管要求", order=4, page_index=2),
            DocumentBlock(
                block_id="b5",
                block_type="paragraph",
                text="生产密钥应托管在受控设备或 HSM 中，并限制导出。",
                order=5,
                page_index=2,
            ),
        ],
    )

    chunks = SemanticChunker().chunk(
        parsed,
        doc_type="standard",
        metadata={"region": "CN", "industry": "construction"},
    )

    assert len(chunks) == 2
    assert chunks[0].section == "3.2.1 密钥轮换要求"
    assert chunks[0].chunk_id.endswith("#3.2.1")
    assert chunks[0].content.startswith("3.2.1 密钥轮换要求")
    assert chunks[0].metadata["section_path"] == ["3.2 密钥管理", "3.2.1 密钥轮换要求"]
    assert chunks[0].metadata["clause_code"] == "3.2.1"
    assert chunks[1].section == "3.2.2 密钥托管要求"
    assert chunks[1].source_page == 2


def test_semantic_chunker_splits_long_clause_without_chunk_id_collision():
    long_text = "密钥轮换策略说明。" * 200
    parsed = ParsedDocument(
        doc_id="std::demo",
        title="建筑信息模型交付规范",
        source_path="knowledge/raw/construction_standard.pdf",
        source_type="pdf",
        blocks=[
            DocumentBlock(block_id="b1", block_type="heading", text="5.4 密钥轮换周期要求", order=1, page_index=4),
            DocumentBlock(block_id="b2", block_type="paragraph", text=long_text, order=2, page_index=4),
            DocumentBlock(block_id="b3", block_type="paragraph", text=long_text, order=3, page_index=5),
        ],
    )

    chunks = SemanticChunker(max_chars=500).chunk(parsed, doc_type="standard")

    assert len(chunks) >= 2
    assert chunks[0].chunk_id.endswith("#5.4")
    assert chunks[1].chunk_id.endswith("#5.4-part-2")
    assert chunks[0].metadata["clause_code"] == "5.4"
