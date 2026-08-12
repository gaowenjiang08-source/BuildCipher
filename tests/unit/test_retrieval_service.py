"""Unit tests for enterprise retrieval service."""

import json
from types import SimpleNamespace

from cipher_genius.api.schemas import TargetServiceSpecPayload
from cipher_genius.ingestion.models import KnowledgeChunk
from cipher_genius.retrieval import KnowledgeRetrievalService


def test_retrieval_service_loads_seed_documents():
    """Knowledge cards should be created from existing repo assets."""
    service = KnowledgeRetrievalService()

    assert service._documents
    doc_types = {item["doc_type"] for item in service._documents}
    assert "component" in doc_types
    assert "template" in doc_types
    assert "case" in doc_types
    assert "attack_lesson" in doc_types


def test_retrieval_service_loads_paper_attack_lessons():
    """Paper-derived attack lessons should be materialized as retrieval objects."""
    service = KnowledgeRetrievalService()

    paper_lessons = [
        item
        for item in service._documents
        if item["doc_type"] == "attack_lesson"
        and item.get("metadata", {}).get("lesson_kind") == "paper_attack_planning"
    ]

    assert paper_lessons
    assert any("mock_crypto_http_v1" in item["metadata"]["applicable_templates"] for item in paper_lessons)
    assert all(item["metadata"]["source_title"] for item in paper_lessons)


def test_retrieval_service_returns_evidence_pack_for_construction_requirement():
    """A construction delivery requirement should retrieve evidence items."""
    service = KnowledgeRetrievalService()

    evidence_pack = service.retrieve(
        "请为建筑项目 BIM/IFC 交付设计满足 ISO 19650 证据审计、静态加密、传输加密和密钥托管要求的方案。",
        structured_spec={"domain": "construction", "compliance": "ISO_19650"},
        top_k=5,
    )

    assert evidence_pack.backend in {"local", "qdrant"}
    assert evidence_pack.items
    assert any(item.doc_type in {"component", "template", "case", "standard"} for item in evidence_pack.items)


def test_retrieval_service_loads_ingested_jsonl_documents(monkeypatch, tmp_path):
    """Ingested JSONL chunks should become runtime retrieval documents."""
    chunks_dir = tmp_path / "processed" / "chunks"
    chunks_dir.mkdir(parents=True)
    chunk = KnowledgeChunk(
        doc_id="std-cn-construction-001",
        chunk_id="std-cn-construction-001#3.2.1",
        doc_type="standard",
        title="建筑信息模型交付规范",
        section="3.2.1 静态数据加密要求",
        content="BIM/IFC 交付文件应进行签名与加密保护，并保留审计留痕。",
        citation_snippet="敏感静态数据应进行加密保护。",
        source_path=str(tmp_path / "raw" / "construction-standard.pdf"),
        source_page=12,
        metadata={
            "region": "CN",
            "industry": "construction",
            "scenario": ["construction", "bim_delivery", "construction_cde"],
            "tags": ["静态加密", "审计", "BIM"],
        },
    )
    jsonl_path = chunks_dir / "construction_standards.jsonl"
    jsonl_path.write_text(
        json.dumps(chunk.model_dump(mode="json"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CIPHER_GENIUS_INGESTED_KNOWLEDGE_DIR", str(chunks_dir))

    service = KnowledgeRetrievalService()

    assert any(item["chunk_id"] == "std-cn-construction-001#3.2.1" for item in service._documents)

    evidence_pack = service.retrieve(
        "请为建筑项目 BIM/IFC 交付设计满足静态加密和审计留痕要求的方案。",
        structured_spec={"domain": "construction", "compliance": "ISO_19650"},
        top_k=5,
    )

    matched = next((item for item in evidence_pack.items if item.chunk_id == "std-cn-construction-001#3.2.1"), None)
    assert matched is not None
    assert matched.doc_type == "standard"
    assert matched.source_page == 12


def test_retrieval_service_prefers_qdrant_query_when_available():
    """When Qdrant is available, retrieval should query it before local fallback."""

    class _FakeQdrantClient:
        def __init__(self):
            self.scroll_calls = []

        def scroll(self, **kwargs):
            self.scroll_calls.append(kwargs)
            payload = {
                "doc_id": "std-cn-construction-001",
                "chunk_id": "std-cn-construction-001#3.2.1",
                "doc_type": "standard",
                "title": "建筑信息模型交付规范",
                "section": "3.2.1 静态数据加密要求",
                "content": "BIM/IFC 交付文件应进行签名与加密保护，并保留审计留痕。",
                "citation_snippet": "敏感静态数据应进行加密保护。",
                "source_path": "knowledge/raw/std.pdf",
                "source_page": 9,
                "region": "CN",
                "scenario_tokens": ["construction", "bim_delivery"],
                "tags": ["静态加密", "审计"],
                "metadata": {"region": "CN", "scenario": ["construction", "bim_delivery"], "tags": ["静态加密", "审计"]},
            }
            return [SimpleNamespace(payload=payload)], None

    service = KnowledgeRetrievalService()
    fake_client = _FakeQdrantClient()
    service._qdrant_client = fake_client
    service._qdrant_checked = True
    service._qdrant_seeded = True

    evidence_pack = service.retrieve(
        "请为建筑项目 BIM/IFC 交付设计满足静态加密和审计留痕要求的方案。",
        structured_spec={"domain": "construction", "compliance": "ISO_19650"},
        top_k=5,
    )

    assert evidence_pack.backend == "qdrant"
    assert evidence_pack.items
    assert evidence_pack.items[0].chunk_id == "std-cn-construction-001#3.2.1"
    assert fake_client.scroll_calls
    scroll_filter = fake_client.scroll_calls[0]["scroll_filter"]
    assert scroll_filter is not None


def test_retrieval_service_clause_metadata_improves_standard_ranking(monkeypatch, tmp_path):
    """Clause-aware metadata should help standards with exact clause matches rank higher."""
    chunks_dir = tmp_path / "processed" / "chunks"
    chunks_dir.mkdir(parents=True)
    matched_chunk = KnowledgeChunk(
        doc_id="std-cn-construction-001",
        chunk_id="std-cn-construction-001#3.2.1",
        doc_type="standard",
        title="建筑信息模型交付规范",
        section="3.2.1 静态数据加密要求",
        content="敏感静态数据应进行加密保护，并满足审计留痕要求。",
        citation_snippet="敏感静态数据应进行加密保护。",
        source_path=str(tmp_path / "raw" / "construction-standard.pdf"),
        source_page=12,
        metadata={
            "region": "CN",
            "scenario": ["construction", "bim_delivery"],
            "section_path": ["3.2 数据保护要求", "3.2.1 静态数据加密要求"],
            "heading_level": 2,
            "clause_code": "3.2.1",
            "tags": ["静态加密", "审计"],
        },
    )
    nearby_chunk = KnowledgeChunk(
        doc_id="std-cn-construction-001",
        chunk_id="std-cn-construction-001#3.2.2",
        doc_type="standard",
        title="建筑信息模型交付规范",
        section="3.2.2 传输加密要求",
        content="敏感数据在传输过程中应加密保护，并满足审计留痕要求。",
        citation_snippet="敏感数据在传输过程中应加密保护。",
        source_path=str(tmp_path / "raw" / "construction-standard.pdf"),
        source_page=13,
        metadata={
            "region": "CN",
            "scenario": ["construction", "bim_delivery"],
            "section_path": ["3.2 数据保护要求", "3.2.2 传输加密要求"],
            "heading_level": 2,
            "clause_code": "3.2.2",
            "tags": ["传输加密", "审计"],
        },
    )
    jsonl_path = chunks_dir / "construction_standards.jsonl"
    jsonl_path.write_text(
        "\n".join(
            [
                json.dumps(matched_chunk.model_dump(mode="json"), ensure_ascii=False),
                json.dumps(nearby_chunk.model_dump(mode="json"), ensure_ascii=False),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CIPHER_GENIUS_INGESTED_KNOWLEDGE_DIR", str(chunks_dir))

    service = KnowledgeRetrievalService()

    evidence_pack = service.retrieve(
        "请重点参考 3.2.1，给出建筑项目 BIM/IFC 交付的静态加密与审计留痕方案。",
        structured_spec={"domain": "construction", "compliance": "ISO_19650"},
        top_k=2,
    )

    standard_items = [item for item in evidence_pack.items if item.doc_type == "standard"]
    assert standard_items
    assert standard_items[0].chunk_id == "std-cn-construction-001#3.2.1"
    assert standard_items[0].metadata["clause_code"] == "3.2.1"
    assert standard_items[0].metadata["section_path"] == ["3.2 数据保护要求", "3.2.1 静态数据加密要求"]


def test_retrieval_service_builds_attack_planning_evidence_query():
    service = KnowledgeRetrievalService()
    service._documents = [
        {
            "doc_id": "case-attack-001",
            "chunk_id": "case-attack-001#1",
            "doc_type": "case",
            "title": "HTTP 加密接口错误处理案例",
            "section": "攻击复盘",
            "content": "error handling leakage key rotation misuse_case",
            "citation_snippet": "应重点检查错误处理与密钥轮换边界。",
            "metadata": {
                "region": "CN",
                "scenario": ["general"],
                "tags": ["error handling leakage", "key rotation", "misuse_case"],
            },
        },
        {
            "doc_id": "template-attack-001",
            "chunk_id": "template-attack-001#1",
            "doc_type": "template",
            "title": "Mock Crypto HTTP 服务基线模板",
            "section": "模板说明",
            "content": "mock_crypto_http_v1 http-json crypto api baseline",
            "citation_snippet": "模板要求规划器关注 http-json 加密接口误用。",
            "metadata": {
                "region": "CN",
                "scenario": ["general"],
                "tags": ["mock_crypto_http_v1", "http-json", "crypto api"],
            },
        },
    ]
    service._qdrant_client = None
    service._qdrant_checked = True

    target_service = TargetServiceSpecPayload(
        service_id="svc-attack-001",
        service_name="demo-attack-service",
        template_id="mock_crypto_http_v1",
        template_label="模拟加密 HTTP 服务",
        service_kind="crypto_api",
        attack_surface_kind="http-json",
        attack_surface=["encrypt", "key_rotation"],
        planner_skill_hints=["attack_surface_analysis"],
        planner_retrieval_hints=["error handling leakage", "key rotation boundary"],
    )

    evidence_pack = service.retrieve_attack_planning_evidence(
        requirement_text="请规划受控的本地沙盒攻击验证。",
        target_service=target_service,
        structured_spec={"domain": "general"},
        planning_mode="baseline",
        prior_findings=["错误返回可能暴露内部状态"],
        top_k=2,
    )

    assert evidence_pack.items
    assert evidence_pack.applied_filters["planner_mode"] == "baseline"
    assert evidence_pack.applied_filters["target_template_id"] == "mock_crypto_http_v1"
    assert evidence_pack.applied_filters["doc_types"] == ["standard", "policy", "template", "case", "attack_lesson"]
    assert "planner retrieval hints: error handling leakage, key rotation boundary" in evidence_pack.query
    assert "prior findings: 错误返回可能暴露内部状态" in evidence_pack.query


def test_retrieval_service_can_return_attack_lesson_documents():
    service = KnowledgeRetrievalService()
    service._documents = [
        {
            "doc_id": "attack_lesson::bench-1",
            "chunk_id": "attack_lesson::bench-1#planner",
            "doc_type": "attack_lesson",
            "title": "bench-1 攻击经验",
            "section": "攻击规划经验",
            "content": "mock_crypto_http_v1 attack_planning benchmark audit trail integrity key governance regression",
            "citation_snippet": "围绕 benchmark 沉淀的攻击与回归经验。",
            "metadata": {
                "scenario": ["general"],
                "attack_focus": ["audit trail integrity"],
                "regression_focus": ["key governance regression"],
                "tags": [
                    "attack_planning",
                    "benchmark",
                    "mock_crypto_http_v1",
                    "audit trail integrity",
                    "key governance regression",
                ],
            },
        }
    ]
    service._qdrant_client = None
    service._qdrant_checked = True

    target_service = TargetServiceSpecPayload(
        service_id="svc-attack-002",
        service_name="demo-attack-service",
        template_id="mock_crypto_http_v1",
        template_label="模拟加密 HTTP 服务",
        service_kind="crypto_api",
        attack_surface_kind="http-json",
        planner_retrieval_hints=["audit trail integrity", "key governance regression"],
    )

    evidence_pack = service.retrieve_attack_planning_evidence(
        requirement_text="请生成回归攻击规划。",
        target_service=target_service,
        structured_spec={"domain": "general"},
        planning_mode="regression",
        regression_focus=["key governance regression"],
        top_k=2,
    )

    assert evidence_pack.items
    assert evidence_pack.items[0].doc_type == "attack_lesson"
    assert evidence_pack.items[0].metadata["attack_focus"] == ["audit trail integrity"]


def test_retrieval_service_can_return_paper_attack_lesson_documents():
    service = KnowledgeRetrievalService()
    service._documents = [
        {
            "doc_id": "attack_lesson::paper::oracle-boundary",
            "chunk_id": "attack_lesson::paper::oracle-boundary#planner",
            "doc_type": "attack_lesson",
            "title": "自适应错误预言机边界卡",
            "section": "攻击论文摘要卡",
            "content": (
                "mock_crypto_http_v1 crypto_api http-json "
                "error handling leakage adaptive error oracle "
                "uniform error regression key rotation boundary"
            ),
            "citation_snippet": "论文摘要强调统一错误边界与轮换回归检查。",
            "metadata": {
                "scenario": ["general"],
                "lesson_kind": "paper_attack_planning",
                "source_title": "Security Flaws Induced by CBC Padding - Applications to SSL, IPSEC, WTLS...",
                "source_year": 2002,
                "attack_focus": ["error handling leakage", "adaptive error oracle"],
                "regression_focus": ["uniform error regression"],
                "applicable_templates": ["mock_crypto_http_v1"],
                "attack_surface_kinds": ["http-json"],
                "service_kinds": ["crypto_api"],
                "tags": [
                    "attack_planning",
                    "paper",
                    "mock_crypto_http_v1",
                    "http-json",
                    "crypto_api",
                    "error handling leakage",
                    "adaptive error oracle",
                    "uniform error regression",
                    "key rotation boundary",
                ],
            },
        }
    ]
    service._qdrant_client = None
    service._qdrant_checked = True

    target_service = TargetServiceSpecPayload(
        service_id="svc-attack-003",
        service_name="demo-attack-service",
        template_id="mock_crypto_http_v1",
        template_label="Mock Crypto HTTP Service",
        service_kind="crypto_api",
        attack_surface_kind="http-json",
        planner_skill_hints=["attack_surface_analysis"],
        planner_retrieval_hints=["error handling leakage", "key rotation boundary"],
    )

    evidence_pack = service.retrieve_attack_planning_evidence(
        requirement_text="Plan a controlled baseline attack around error handling leakage and key rotation boundary.",
        target_service=target_service,
        structured_spec={"domain": "general"},
        planning_mode="baseline",
        prior_findings=["Error responses may leak internal state."],
        top_k=1,
    )

    assert evidence_pack.items
    assert evidence_pack.items[0].metadata["lesson_kind"] == "paper_attack_planning"
    assert evidence_pack.items[0].metadata["source_year"] == 2002
