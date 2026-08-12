from datetime import datetime

from cipher_genius.api.schemas import (
    AnalystReportPayload,
    ArtifactRefPayload,
    ContextProjectionPayload,
    EvidenceRefPayload,
    MemoryCardPayload,
    ParsedRequirementPayload,
)
from cipher_genius.core.langgraph_mas import LangGraphMASService
from cipher_genius.models.requirement import (
    PerformanceConstraint,
    PlatformType,
    Requirement,
    ResourceLevel,
    SchemeType,
    SecurityRequirement,
    TargetPlatform,
)
from cipher_genius.models.scheme import (
    CryptographicScheme,
    SchemeArchitecture,
    SchemeMetadata,
    SchemeParameters,
    SecurityAnalysis,
)


def build_requirement(*, quantum_resistant: bool = False, security_level: int = 256) -> Requirement:
    return Requirement(
        description="test",
        scheme_type=SchemeType.AUTHENTICATED_ENCRYPTION,
        target_platform=TargetPlatform(type=PlatformType.SERVER, resource_level=ResourceLevel.MODERATE),
        security=SecurityRequirement(security_level=security_level, quantum_resistant=quantum_resistant),
        performance=PerformanceConstraint(),
    )


def build_scheme(name: str, *, score: float) -> CryptographicScheme:
    return CryptographicScheme(
        metadata=SchemeMetadata(
            name=name,
            scheme_type=SchemeType.AUTHENTICATED_ENCRYPTION,
            generated_at=datetime.now(),
        ),
        requirements=build_requirement(),
        architecture=SchemeArchitecture(
            components=[],
            composition={"pattern": "test"},
            dataflow=["Key agreement", "AEAD encryption"],
        ),
        parameters=SchemeParameters(key_size=256, nonce_size=96, tag_size=128),
        security_analysis=SecurityAnalysis(
            threat_model={"adversary": "adaptive"},
            properties=["confidentiality", "integrity"],
            assumptions=["Unique nonce policy"],
            concerns=[],
        ),
        design_rationale="test rationale",
        score=score,
    )


def test_extract_generation_runtime_inputs_prefers_projection_payload():
    service = LangGraphMASService()
    requirement = build_requirement(quantum_resistant=True)
    projection = ContextProjectionPayload(
        agent_id="generation_agent",
        case_id="case-test",
        run_id="run-test",
        round_id="generation-r1",
        objective="生成候选方案。",
        cards=[
            MemoryCardPayload(
                card_id="card-generation-runtime",
                card_type="generation_runtime_input",
                case_id="case-test",
                run_id="run-test",
                round_id="generation-r1",
                source_agent="context_builder",
                summary="generation 运行时输入",
                payload={
                    "structured_spec": {"domain": "construction", "quantum_safe": True},
                    "parsed_requirement": {
                        "requirement": requirement.model_dump(mode="json"),
                        "confidence": 0.91,
                        "ambiguities": [],
                        "assumptions": [],
                    },
                },
            )
        ],
    )

    restored_requirement, structured_spec, parser_confidence = service._extract_generation_runtime_inputs(
        projection,
        fallback_requirement=build_requirement(quantum_resistant=False, security_level=128),
        fallback_structured_spec={"domain": "fallback"},
        fallback_parser_confidence=0.4,
    )

    assert restored_requirement.security.quantum_resistant is True
    assert structured_spec["domain"] == "construction"
    assert parser_confidence == 0.91


def test_restore_requirement_from_analyst_rebuilds_requirement_without_state_payload():
    service = LangGraphMASService()
    requirement = build_requirement(quantum_resistant=True)
    analyst = AnalystReportPayload(
        structured_spec={"domain": "construction"},
        parsed_requirement=ParsedRequirementPayload(
            requirement=requirement.model_dump(mode="json"),
            confidence=0.88,
            ambiguities=[],
            assumptions=[],
        ),
        clarifications=[],
        assumptions=[],
        case_context={},
    )

    restored = service._restore_requirement_from_analyst(
        analyst,
        raw_requirement="为建筑项目 BIM/IFC 交付设计后量子方案",
    )

    assert restored.security.quantum_resistant is True
    assert restored.target_platform.type == PlatformType.SERVER


def test_extract_audit_runtime_inputs_prefers_scheme_entries_with_proposal_ids():
    service = LangGraphMASService()
    alpha = build_scheme("Alpha", score=8.6)
    beta = build_scheme("Beta", score=7.9)
    projection = ContextProjectionPayload(
        agent_id="audit_agent",
        case_id="case-test",
        run_id="run-test",
        round_id="audit-r1",
        objective="审计候选方案。",
        cards=[
            MemoryCardPayload(
                card_id="card-audit-runtime",
                card_type="audit_runtime_input",
                case_id="case-test",
                run_id="run-test",
                round_id="audit-r1",
                source_agent="generation_agent",
                summary="audit 运行时输入",
                payload={
                    "structured_spec": {"domain": "construction", "quantum_safe": True},
                    "scheme_entries": [
                        {"proposal_id": "proposal-alpha", "scheme": alpha.model_dump(mode="json")},
                        {"proposal_id": "proposal-beta", "scheme": beta.model_dump(mode="json")},
                    ],
                },
            )
        ],
    )

    schemes, structured_spec, proposal_ids = service._extract_audit_runtime_inputs(
        projection,
        fallback_schemes=[],
        fallback_structured_spec={"domain": "fallback"},
    )

    assert [scheme.metadata.name for scheme in schemes] == ["Alpha", "Beta"]
    assert structured_spec["domain"] == "construction"
    assert proposal_ids == ["proposal-alpha", "proposal-beta"]


def test_finalize_projection_cards_attach_typed_contract_and_ref_lookup_hint():
    service = LangGraphMASService()
    finalized = service._finalize_projection_cards(
        [
            MemoryCardPayload(
                card_id="card-runtime",
                card_type="generation_runtime_input",
                case_id="case-test",
                run_id="run-test",
                round_id="generation-r1",
                source_agent="context_builder",
                summary="generation 运行时输入",
                artifact_refs=[
                    ArtifactRefPayload(
                        artifact_id="artifact-001",
                        artifact_type="structured_spec",
                        title="结构化需求",
                    )
                ],
                evidence_refs=[
                    EvidenceRefPayload(
                        doc_id="doc-001",
                        chunk_id="chunk-001",
                        title="规范片段",
                        snippet="必须保留审计留痕。",
                    )
                ],
            )
        ]
    )

    card = finalized[0]
    assert card.card_family == "runtime_input"
    assert card.replay_index_ref == "card-runtime:runtime_input"
    assert card.payload["typed_contract"]["contract_ref"] == "runtime_input:generation_runtime_input:v1"
    assert card.payload["typed_contract"]["runtime_stage"] == "generation"
    assert card.payload["ref_lookup_hint"]["lookup_strategy"] == "card_refs_then_projection_then_handoff_then_replay"
    assert card.payload["ref_lookup_hint"]["artifact_refs"][0]["artifact_id"] == "artifact-001"
    assert card.payload["ref_lookup_hint"]["evidence_refs"][0]["doc_id"] == "doc-001"


def test_extract_generation_runtime_inputs_accepts_typed_contract_runtime_card():
    service = LangGraphMASService()
    requirement = build_requirement(quantum_resistant=True)
    projection = ContextProjectionPayload(
        agent_id="generation_agent",
        case_id="case-test",
        run_id="run-test",
        round_id="generation-r1",
        objective="生成候选方案。",
        cards=[
            MemoryCardPayload(
                card_id="card-generation-runtime",
                card_type="projection_runtime_input",
                card_family="runtime_input",
                case_id="case-test",
                run_id="run-test",
                round_id="generation-r1",
                source_agent="context_builder",
                summary="generation 运行时输入",
                payload={
                    "structured_spec": {"domain": "construction", "quantum_safe": True},
                    "parsed_requirement": {
                        "requirement": requirement.model_dump(mode="json"),
                        "confidence": 0.93,
                        "ambiguities": [],
                        "assumptions": [],
                    },
                    "typed_contract": {
                        "contract_ref": "runtime_input:generation_runtime_input:v1",
                        "card_type": "generation_runtime_input",
                        "family": "runtime_input",
                        "contract_version": "v1",
                        "runtime_stage": "generation",
                    },
                },
            )
        ],
    )

    restored_requirement, structured_spec, parser_confidence = service._extract_generation_runtime_inputs(
        projection,
        fallback_requirement=build_requirement(quantum_resistant=False, security_level=128),
        fallback_structured_spec={"domain": "fallback"},
        fallback_parser_confidence=0.4,
    )

    assert restored_requirement.security.quantum_resistant is True
    assert structured_spec["domain"] == "construction"
    assert parser_confidence == 0.93
