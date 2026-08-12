from datetime import datetime, timezone

from cipher_genius.api.schemas import (
    ArtifactRefPayload,
    ContextConstraintPayload,
    ContextProjectionPayload,
    EvidenceRefPayload,
    MemoryCardPayload,
    MemoryHandoffPayload,
)


def test_context_projection_payload_accepts_nested_cards_and_refs():
    projection = ContextProjectionPayload(
        agent_id="generation_agent",
        case_id="case-demo-001",
        run_id="run-demo-001",
        round_id="round-2",
        objective="生成下一版候选方案",
        constraints=[
            ContextConstraintPayload(
                constraint_id="constraint-quantum",
                constraint_kind="security_requirement",
                value="必须支持后量子迁移",
                source="human_confirmed",
            )
        ],
        cards=[
            MemoryCardPayload(
                card_id="card-reflect-001",
                card_type="reflection",
                case_id="case-demo-001",
                run_id="run-demo-001",
                round_id="round-1",
                source_agent="reflection_agent",
                summary="下一轮 generation 需要补齐错误处理边界。",
                created_at=datetime.now(timezone.utc),
            )
        ],
        artifact_refs=[
            ArtifactRefPayload(
                artifact_id="artifact-trace-001",
                artifact_type="trace",
                path=".cache/sandbox/run-demo-001/svc-demo/attack_01/trace.jsonl",
                summary="首轮攻击 trace 摘要",
            )
        ],
        evidence_refs=[
            EvidenceRefPayload(
                doc_id="doc-001",
                chunk_id="chunk-001",
                title="企业密码改造规范",
                snippet="错误处理信息不应泄露内部上下文。",
                score=0.92,
            )
        ],
        token_budget_hint=6000,
    )

    assert projection.agent_id == "generation_agent"
    assert projection.constraints[0].value == "必须支持后量子迁移"
    assert projection.cards[0].card_type == "reflection"
    assert projection.artifact_refs[0].artifact_type == "trace"
    assert projection.evidence_refs[0].chunk_id == "chunk-001"
    assert projection.token_budget_hint == 6000


def test_memory_handoff_payload_can_embed_projection():
    projection = ContextProjectionPayload(
        agent_id="patch_agent",
        case_id="case-demo-002",
        objective="针对高优先级漏洞生成补丁方案",
    )
    handoff = MemoryHandoffPayload(
        handoff_id="handoff-001",
        from_agent="vulnerability_evaluation_agent",
        to_agent="patch_agent",
        case_id="case-demo-002",
        round_id="round-3",
        objective="把漏洞裁决交给 patch agent",
        cards=[
            MemoryCardPayload(
                card_id="card-find-001",
                card_type="finding",
                case_id="case-demo-002",
                round_id="round-3",
                source_agent="vulnerability_evaluation_agent",
                summary="错误处理泄露内部状态。",
            )
        ],
        projection=projection,
    )

    assert handoff.status == "ready"
    assert handoff.status_label == "已就绪"
    assert handoff.cards[0].card_type == "finding"
    assert handoff.projection is not None
    assert handoff.projection.agent_id == "patch_agent"
