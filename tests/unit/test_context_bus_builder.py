from datetime import datetime, timezone

from cipher_genius.api.schemas import (
    ArtifactRefPayload,
    ContextProjectionPayload,
    EvidenceRefPayload,
    MemoryCardPayload,
    MemoryHandoffPayload,
)
from cipher_genius.core.context_bus import ContextBusBuilder


def test_context_bus_builder_emits_typed_family_summary():
    builder = ContextBusBuilder()
    generation_projection = ContextProjectionPayload(
        agent_id="generation_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="generation-r1",
        objective="生成候选方案",
        cards=[
            MemoryCardPayload(
                card_id="card-runtime",
                card_type="generation_runtime_input",
                case_id="case-001",
                run_id="run-001",
                round_id="generation-r1",
                source_agent="context_builder",
                summary="恢复 generation 运行时输入。",
                created_at=datetime.now(timezone.utc),
            ),
            MemoryCardPayload(
                card_id="card-reflection",
                card_type="reflection_memory",
                case_id="case-001",
                run_id="run-001",
                round_id="generation-r1",
                version_id="v2",
                source_agent="case_memory_service",
                summary="避免重复上一轮失败模式。",
                created_at=datetime.now(timezone.utc),
            ),
        ],
        artifact_refs=[
            ArtifactRefPayload(
                artifact_id="artifact-001",
                artifact_type="proposal",
                title="候选方案摘要",
                path="F:/workspace/proposal.json",
                summary="候选方案结构化摘要。",
            )
        ],
        evidence_refs=[
            EvidenceRefPayload(
                doc_id="doc-001",
                chunk_id="chunk-001",
                title="企业规范片段",
                snippet="必须保留审计留痕。",
            )
        ],
    )
    reflection_projection = ContextProjectionPayload(
        agent_id="reflection_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="reflection-r1",
        objective="形成闭环反思",
        cards=[
            MemoryCardPayload(
                card_id="card-patch",
                card_type="patch_execution",
                case_id="case-001",
                run_id="run-001",
                round_id="regression-r2",
                version_id="v2",
                source_agent="patch_agent",
                summary="补丁执行摘要。",
                created_at=datetime.now(timezone.utc),
            ),
            MemoryCardPayload(
                card_id="card-decision",
                card_type="attack_decision",
                case_id="case-001",
                run_id="run-001",
                round_id="attack-r1",
                source_agent="attack_planning_agent",
                summary="攻击决策卡。",
                created_at=datetime.now(timezone.utc),
            ),
        ],
    )
    handoff = MemoryHandoffPayload(
        handoff_id="handoff-001",
        from_agent="patch_agent",
        to_agent="reflection_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="reflection-r1",
        objective="把补丁执行结果交给 reflection。",
        cards=list(reflection_projection.cards),
        projection=reflection_projection,
    )

    summary = builder.build(
        run_id="run-001",
        case_id="case-001",
        projections={
            "generation": generation_projection,
            "reflection": reflection_projection,
        },
        memory_handoffs=[handoff],
    )

    assert summary.summary["typed_family_count"] >= 4
    assert summary.summary["typed_contract_count"] >= 4
    assert summary.summary["family_counts"]["runtime_input"] == 1
    assert summary.summary["family_counts"]["reflection"] == 1
    assert summary.summary["family_counts"]["patch"] == 1
    assert summary.summary["family_counts"]["decision"] == 1

    generation_window = next(item for item in summary.windows if item.agent_id == "generation_agent")
    assert generation_window.window_ref == "generation_agent:generation-r1"
    assert generation_window.card_family_counts["runtime_input"] == 1
    assert generation_window.card_family_counts["reflection"] == 1
    assert generation_window.typed_contract_counts["runtime_input:generation_runtime_input:v1"] == 1
    assert generation_window.dominant_typed_contract in {
        "runtime_input:generation_runtime_input:v1",
        "reflection:reflection_memory:v1",
    }
    assert "case-001:run-001:generation-r1:v2" in generation_window.lineage_refs
    assert "proposal:artifact-001" in generation_window.artifact_lookup_refs
    assert "doc-001:chunk-001" in generation_window.evidence_lookup_refs

    patch_family = next(item for item in summary.typed_families if item.family == "patch")
    assert patch_family.card_count == 1
    assert patch_family.handoff_count == 1
    assert "patch_execution" in patch_family.card_types
    assert "handoff-001" in patch_family.handoff_refs
    runtime_contract = next(
        item
        for item in summary.typed_contracts
        if item.contract_ref == "runtime_input:generation_runtime_input:v1"
    )
    assert runtime_contract.card_type == "generation_runtime_input"
    assert runtime_contract.family == "runtime_input"
    assert runtime_contract.contract_version == "v1"
    assert runtime_contract.artifact_ref_count == 1
    assert runtime_contract.evidence_ref_count == 1
    assert runtime_contract.window_refs == ["generation_agent:generation-r1"]

    replay_snapshot = summary.replay_snapshot_card
    assert replay_snapshot is not None
    assert replay_snapshot.typed_family_counts["patch"] == 1
    assert replay_snapshot.typed_contract_counts["runtime_input:generation_runtime_input:v1"] == 1
    assert "proposal:artifact-001" in replay_snapshot.artifact_lookup_refs
    assert "doc-001:chunk-001" in replay_snapshot.evidence_lookup_refs
    assert replay_snapshot.metadata["dominant_family"] in {"decision", "patch", "reflection", "runtime_input"}
    assert replay_snapshot.metadata["typed_contract_count"] >= 4


def test_context_bus_builder_marks_retry_windows_and_handoffs():
    builder = ContextBusBuilder()
    retry_attack_projection = ContextProjectionPayload(
        agent_id="attack_planning_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="attack-plan-r2",
        objective="同轮补充攻击重规划",
        cards=[
            MemoryCardPayload(
                card_id="card-retry-plan",
                card_type="attack_replan_input",
                case_id="case-001",
                run_id="run-001",
                round_id="attack-plan-r2",
                source_agent="expert_gate_agent",
                summary="专家闸门要求补充攻击。",
                created_at=datetime.now(timezone.utc),
            )
        ],
    )
    retry_vulnerability_projection = ContextProjectionPayload(
        agent_id="vulnerability_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="vulnerability-r2",
        objective="同轮补充漏洞评估",
        cards=[
            MemoryCardPayload(
                card_id="card-retry-verdict",
                card_type="attack_result_summary",
                case_id="case-001",
                run_id="run-001",
                round_id="vulnerability-r2",
                source_agent="attack_planning_agent",
                summary="补充攻击结果摘要。",
                created_at=datetime.now(timezone.utc),
            )
        ],
    )
    retry_handoff = MemoryHandoffPayload(
        handoff_id="handoff-run001-attack-retry",
        from_agent="expert_gate_agent",
        to_agent="attack_planning_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="attack-plan-r2",
        objective="把 retry 规划输入交给攻击规划器。",
        projection=retry_attack_projection,
    )

    summary = builder.build(
        run_id="run-001",
        case_id="case-001",
        projections={
            "attack_planning_retry": retry_attack_projection,
            "vulnerability_evaluation_retry": retry_vulnerability_projection,
        },
        memory_handoffs=[retry_handoff],
    )

    assert summary.summary["retry_window_count"] == 2
    assert summary.summary["retry_handoff_count"] == 1
    assert "attack_planning_agent:attack-plan-r2" in summary.summary["retry_projection_refs"]
    assert "vulnerability_agent:vulnerability-r2" in summary.summary["retry_projection_refs"]
    assert "handoff-run001-attack-retry" in summary.summary["retry_handoff_refs"]
    assert summary.summary["retry_typed_contract_refs"]
    assert summary.replay_snapshot_card is not None
    assert summary.replay_snapshot_card.metadata["retry_window_count"] == 2
