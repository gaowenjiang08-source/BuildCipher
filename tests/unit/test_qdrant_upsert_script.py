"""Unit tests for the Qdrant upsert script."""

import importlib.util
import json
from pathlib import Path

from cipher_genius.ingestion.models import KnowledgeChunk


def _load_script_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "knowledge" / "upsert_qdrant.py"
    spec = importlib.util.spec_from_file_location("upsert_qdrant", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_load_chunk_payloads_reads_jsonl(tmp_path):
    upsert_qdrant = _load_script_module()
    source = tmp_path / "chunks.jsonl"
    chunk = KnowledgeChunk(
        doc_id="std-001",
        chunk_id="std-001#1",
        doc_type="standard",
        title="建筑信息模型交付规范",
        section="1.1 总则",
        content="敏感数据应加密。",
        citation_snippet="敏感数据应加密。",
        source_path="knowledge/raw/std.pdf",
        source_page=3,
        metadata={"region": "CN"},
    )
    source.write_text(json.dumps(chunk.model_dump(mode="json"), ensure_ascii=False) + "\n", encoding="utf-8")

    payloads = upsert_qdrant.load_chunk_payloads(source)

    assert len(payloads) == 1
    assert payloads[0]["chunk_id"] == "std-001#1"
    assert payloads[0]["source_page"] == 3
