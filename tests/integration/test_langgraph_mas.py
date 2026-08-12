"""Integration tests for LangGraph MAS service.

The LangGraph engine now executes its own graph-native staged workflow while
keeping stable response contracts and shared business heuristics.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from cipher_genius.api.mas_service import MASOrchestrationService
from cipher_genius.api.schemas import AttackDecisionPayload, ExpertGateDecisionPayload, MASRequest, MASResponse
from cipher_genius.core.langgraph_mas import LangGraphMASService
from cipher_genius.core.mas_runtime_support import MASRuntimeSupport

STABLE_ACTORS = {
    "Supervisor",
    "Requirement Analyst",
    "Cryptography Architect",
    "Architect",
    "Security & Compliance Auditor",
    "Code Engineer",
}

EXPECTED_TRACE = [
    "analyst",
    "context_builder",
    "architect",
    "audit",
    "engineer",
    "target_deployer",
    "attack_executor",
    "vulnerability_evaluation",
    "patch_reflection",
    "delivery",
]


@pytest.fixture
def redis_client():
    """Provide Redis client for testing."""
    from cipher_genius.utils.redis_client import get_redis_client

    return get_redis_client()


@pytest.fixture
def mas_service():
    """Create a LangGraph MAS service with deterministic offline LLM behavior."""
    return LangGraphMASService(llm_provider="zhipuai")


def test_langgraph_mas_basic_execution(mas_service):
    """LangGraph engine should return the canonical MASResponse schema."""
    request = MASRequest(
        requirement="Design a secure password hashing scheme for web applications",
        llm_provider="zhipuai",
        num_variants=1,
        max_audit_rounds=1,
        generate_code=False,
    )

    result = mas_service.execute(request)

    assert isinstance(result, MASResponse)
    assert result.request_id
    assert result.run_id
    assert result.analyst is not None
    assert result.analyst.parsed_requirement is not None
    assert result.architect is not None
    assert result.delivery.get("engine") == "langgraph"
    assert result.delivery.get("engine_mode") == "graph-native"
    assert result.delivery.get("workflow_trace") == EXPECTED_TRACE
    attack_loop = result.delivery.get("attack_loop", {})
    assert attack_loop.get("target_service", {}).get("service_id")
    assert attack_loop.get("target_service", {}).get("status") == "deployed"
    assert attack_loop.get("attack_decision", {}).get("action") == "execute"
    assert attack_loop.get("attack_decision", {}).get("selected_attack_family")
    assert attack_loop.get("attack_results", [{}])[0].get("status") == "executed"
    assert attack_loop.get("vulnerability_verdict", {}).get("summary")
    assert attack_loop.get("vulnerability_verdict", {}).get("severity")
    assert attack_loop.get("vulnerability_verdict", {}).get("remediation_priority")
    assert attack_loop.get("patch_spec", {}).get("strategy")
    assert attack_loop.get("patch_spec", {}).get("summary")
    assert attack_loop.get("patch_spec", {}).get("rationale")
    assert attack_loop.get("patch_spec", {}).get("implementation_notes")
    assert attack_loop.get("patch_spec", {}).get("validation_steps")
    assert attack_loop.get("patch_spec", {}).get("rollback_notes")
    assert attack_loop.get("patch_spec", {}).get("regression_focus")
    assert attack_loop.get("patch_execution", {}).get("patch_id") == attack_loop.get("patch_spec", {}).get("patch_id")
    assert attack_loop.get("patch_execution", {}).get("status") in {"applied", "validated"}
    assert attack_loop.get("patch_execution", {}).get("workspace")
    assert attack_loop.get("patch_execution", {}).get("execution_contract_version") == "v1"
    assert attack_loop.get("patch_execution", {}).get("validation_results")
    assert attack_loop.get("patch_execution", {}).get("validation_summary", {}).get("passed", 0) >= 1
    assert attack_loop.get("patch_execution", {}).get("validation_results", [{}])[0].get("step_kind")
    assert attack_loop.get("patch_execution", {}).get("changed_artifact_summaries")
    assert attack_loop.get("patch_execution", {}).get("artifact_inventory", {}).get("changed_code_artifact_count", 0) >= 1
    assert attack_loop.get("patch_execution", {}).get("patch_artifact_refs")
    assert attack_loop.get("patch_execution", {}).get("rollback_artifact_refs")
    assert len(attack_loop.get("rounds", [])) >= 2
    assert attack_loop.get("rounds", [{}])[0].get("attack_decision", {}).get("action") == "execute"
    assert attack_loop.get("rounds", [{}])[0].get("vulnerability_verdict", {}).get("summary")
    assert attack_loop.get("rounds", [{}])[1].get("round_kind") == "regression"
    assert attack_loop.get("regression_attack_decision", {}).get("action") == "replan"
    assert attack_loop.get("regression_vulnerability_verdict", {}).get("summary")
    assert attack_loop.get("regression_vulnerability_verdict", {}).get("severity")
    assert attack_loop.get("reflection_cards")
    assert attack_loop.get("reflection_cards", [{}])[0].get("card_type") == "reflection"
    assert attack_loop.get("reflection_cards", [{}])[0].get("prompt_changes")
    assert attack_loop.get("reflection_cards", [{}, {}])[1].get("card_type") == "regression_summary"
    assert attack_loop.get("rounds", [{}, {}])[1].get("attack_decision", {}).get("action") == "replan"
    assert attack_loop.get("rounds", [{}, {}])[1].get("vulnerability_verdict", {}).get("summary")
    assert attack_loop.get("rounds", [{}])[1].get("mode") == "executed"
    assert attack_loop.get("rounds", [{}])[1].get("patch_applied") is True
    assert attack_loop.get("rounds", [{}])[1].get("patch_execution", {}).get("status") in {"applied", "validated"}
    assert attack_loop.get("rounds", [{}])[1].get("attack_results")
    assert attack_loop.get("loop_status") == "baseline_executed_regression_executed"
    assert attack_loop.get("regression_attack_results", [{}])[0].get("status") == "executed"
    context_projections = result.delivery.get("context_projections", {})
    assert context_projections.get("generation", {}).get("agent_id") == "generation_agent"
    assert context_projections.get("audit", {}).get("agent_id") == "audit_agent"
    assert context_projections.get("attack_planning", {}).get("agent_id") == "attack_planning_agent"
    assert (
        context_projections.get("vulnerability_evaluation", {}).get("agent_id")
        == "vulnerability_agent"
    )
    assert context_projections.get("expert_gate", {}).get("agent_id") == "expert_gate_agent"
    assert context_projections.get("patch", {}).get("agent_id") == "patch_agent"
    assert context_projections.get("reflection", {}).get("agent_id") == "reflection_agent"
    assert context_projections.get("generation", {}).get("constraints")
    assert any(
        item.get("card_type") == "generation_runtime_input"
        and item.get("payload", {}).get("parsed_requirement", {}).get("requirement")
        and item.get("card_family") == "runtime_input"
        and item.get("card_contract_version") == "v1"
        and item.get("lineage_ref")
        and item.get("payload", {}).get("typed_contract", {}).get("contract_ref")
        == "runtime_input:generation_runtime_input:v1"
        and item.get("payload", {}).get("ref_lookup_hint", {}).get("lookup_strategy")
        == "card_refs_then_projection_then_handoff_then_replay"
        for item in context_projections.get("generation", {}).get("cards", [])
    )
    assert any(
        item.get("card_type") == "audit_runtime_input"
        and item.get("payload", {}).get("schemes")
        for item in context_projections.get("audit", {}).get("cards", [])
    )
    assert any(
        item.get("card_type") == "audit_runtime_input"
        and item.get("payload", {}).get("scheme_entries")
        for item in context_projections.get("audit", {}).get("cards", [])
    )
    assert any(
        item.get("card_type") == "audit_decision_input"
        and item.get("payload", {}).get("proposal_id")
        and item.get("payload", {}).get("compliance_score") is not None
        and item.get("payload", {}).get("risk_score") is not None
        for item in context_projections.get("audit", {}).get("cards", [])
    )
    assert context_projections.get("attack_planning", {}).get("artifact_refs")
    assert any(
        item.get("card_type") == "attack_planner_evidence"
        and item.get("payload", {}).get("hit_count", 0) >= 1
        and item.get("payload", {}).get("applied_filters", {}).get("target_template_id") == "mock_crypto_http_v1"
        for item in context_projections.get("attack_planning", {}).get("cards", [])
    )
    assert context_projections.get("patch", {}).get("cards")
    assert any(
        item.get("card_type") == "attack_decision"
        and item.get("card_family") == "decision"
        for item in context_projections.get("vulnerability_evaluation", {}).get("cards", [])
    )
    assert any(
        item.get("card_type") == "attack_result_summary"
        for item in context_projections.get("vulnerability_evaluation", {}).get("cards", [])
    )
    assert any(
        item.get("card_type") == "attack_result_summary"
        and item.get("payload", {}).get("attack_result_summaries")
        for item in context_projections.get("vulnerability_evaluation", {}).get("cards", [])
    )
    assert any(
        item.get("card_type") == "vulnerability_verdict"
        for item in context_projections.get("patch", {}).get("cards", [])
    )
    assert any(
        item.get("card_type") == "expert_gate_decision"
        and item.get("payload", {}).get("action")
        and item.get("payload", {}).get("decision_family")
        and item.get("payload", {}).get("route_target")
        for item in context_projections.get("patch", {}).get("cards", [])
    )
    assert any(
        item.get("card_type") == "attack_artifact_summary"
        and item.get("payload", {}).get("attack_result_summaries")
        for item in context_projections.get("patch", {}).get("cards", [])
    )
    assert attack_loop.get("expert_gate_decision", {}).get("action") in {
        "patch_required",
        "patch_required_with_regression",
        "retry_attack",
        "observe_only",
    }
    assert attack_loop.get("expert_gate_decision", {}).get("decision_family") in {
        "patch_flow",
        "retry_flow",
        "observation_flow",
    }
    assert attack_loop.get("expert_gate_decision", {}).get("route_target") in {
        "patch_agent",
        "attack_planning_agent",
        "delivery",
    }
    assert attack_loop.get("expert_gate_decision", {}).get("residual_risk_summary")
    assert any(
        item.get("card_type") == "regression_verdict_input"
        for item in context_projections.get("reflection", {}).get("cards", [])
    )
    assert any(
        item.get("card_type") == "patch_execution"
        and item.get("payload", {}).get("validation_results")
        and item.get("payload", {}).get("validation_summary")
        and item.get("card_family") == "patch"
        for item in context_projections.get("reflection", {}).get("cards", [])
    )
    reflection_memory_cards = [
        item
        for item in context_projections.get("generation", {}).get("cards", [])
        if item.get("card_type") == "reflection_memory"
    ]
    if reflection_memory_cards:
        assert any(
            item.get("card_family") == "reflection"
            and item.get("card_contract_version") == "v1"
            and item.get("lineage_ref")
            for item in reflection_memory_cards
        )
    assert any(
        item.get("card_type") == "patch_artifact_summary"
        and item.get("payload", {}).get("changed_artifact_summaries")
        and item.get("payload", {}).get("changed_artifact_summaries", [{}])[0].get("diff_preview")
        for item in context_projections.get("reflection", {}).get("cards", [])
    )
    memory_handoffs = result.delivery.get("memory_handoffs", [])
    assert len(memory_handoffs) >= 6
    assert memory_handoffs[0].get("projection", {}).get("agent_id") == "generation_agent"
    assert memory_handoffs[-1].get("projection", {}).get("agent_id") == "reflection_agent"
    sandbox_dispatcher = result.delivery.get("sandbox_dispatcher", {})
    assert sandbox_dispatcher.get("backend") == "local-dispatcher"
    assert sandbox_dispatcher.get("policy", {}).get("policy_id") == "local-sandbox-default"
    assert sandbox_dispatcher.get("baseline_deployment", {}).get("decision") == "approved"
    assert sandbox_dispatcher.get("baseline_attack", {}).get("status") == "executed"
    assert sandbox_dispatcher.get("patch_apply", {}).get("status") == "executed"
    assert sandbox_dispatcher.get("regression_deployment", {}).get("decision") == "approved"
    assert sandbox_dispatcher.get("regression_attack", {}).get("status") == "executed"
    assert sandbox_dispatcher.get("rollback_plan", {}).get("status") == "executed"
    assert sandbox_dispatcher.get("baseline_attack", {}).get("failure_items") == []
    assert sandbox_dispatcher.get("baseline_attack", {}).get("audit_trail", [{}])[-1].get("event_kind") == "executed"
    assert sandbox_dispatcher.get("regression_attack", {}).get("audit_trail", [{}])[-1].get("event_kind") == "executed"
    assert attack_loop.get("patch_execution", {}).get("patch_dispatch_id") == sandbox_dispatcher.get("patch_apply", {}).get("dispatch_id")
    assert attack_loop.get("patch_execution", {}).get("rollback_dispatch_id") == sandbox_dispatcher.get("rollback_plan", {}).get("dispatch_id")
    backend_architecture = result.delivery.get("backend_architecture", {})
    assert backend_architecture.get("control_plane", {}).get("summary", {}).get("stage_count") == len(EXPECTED_TRACE)
    assert backend_architecture.get("control_plane", {}).get("summary", {}).get("contract_version") == "v1"
    assert backend_architecture.get("control_plane", {}).get("summary", {}).get("retryable_stage_count", 0) >= 1
    attack_control = next(
        item
        for item in backend_architecture.get("control_plane", {}).get("invocations", [])
        if item.get("stage") == "attack_executor"
    )
    assert attack_control.get("checkpoint_ref")
    assert attack_control.get("result_ref")
    assert attack_control.get("retryable") is True
    assert attack_control.get("retry_strategy") == "replan_or_handoff_before_skip"
    assert attack_control.get("termination_mode") == "execute"
    assert attack_control.get("decision_source") == "attack_decision.action"
    assert attack_control.get("contract", {}).get("failure_action") == "skip_dispatch_or_handoff"
    assert attack_control.get("contract", {}).get("next_stages") == ["vulnerability_evaluation"]
    assert attack_control.get("contract", {}).get("retryable") is True
    assert attack_control.get("contract", {}).get("retry_strategy") == "replan_or_handoff_before_skip"
    assert attack_control.get("contract", {}).get("decision_source") == "attack_decision.action"
    assert attack_control.get("contract", {}).get("termination_conditions")
    attack_result_envelope = next(
        item
        for item in backend_architecture.get("control_plane", {}).get("results", [])
        if item.get("stage") == "attack_executor"
    )
    assert attack_result_envelope.get("decision_signal") == "execute"
    assert attack_result_envelope.get("decision_source") == "attack_decision.action"
    assert attack_result_envelope.get("termination_signal") == "execute"
    assert attack_result_envelope.get("failure_action") == "skip_dispatch_or_handoff"
    assert backend_architecture.get("memory_bus", {}).get("projection_count", 0) >= 6
    assert backend_architecture.get("memory_bus", {}).get("summary", {}).get("typed_family_count", 0) >= 4
    assert backend_architecture.get("memory_bus", {}).get("summary", {}).get("typed_contract_count", 0) >= 4
    assert backend_architecture.get("memory_bus", {}).get("summary", {}).get("family_counts", {}).get(
        "reflection", 0
    ) >= 1
    assert backend_architecture.get("memory_bus", {}).get("typed_families", [])
    assert backend_architecture.get("memory_bus", {}).get("typed_contracts", [])
    assert backend_architecture.get("memory_bus", {}).get("replay_snapshot_card", {}).get("typed_contract_counts")
    assert backend_architecture.get("execution_plane", {}).get("summary", {}).get("stage_count", 0) >= 4
    assert backend_architecture.get("execution_plane", {}).get("summary", {}).get("contract_version") == "v1"
    assert backend_architecture.get("execution_plane", {}).get("summary", {}).get("operation_count", 0) >= 6
    assert backend_architecture.get("execution_plane", {}).get("plan", {}).get("executor_kinds")
    assert backend_architecture.get("execution_plane", {}).get("plan", {}).get("executor_matrix")
    assert backend_architecture.get("execution_plane", {}).get("summary", {}).get(
        "executor_matrix_count", 0
    ) >= 3
    assert backend_architecture.get("execution_plane", {}).get("summary", {}).get("operation_kind_counts", {}).get(
        "patch_apply", 0
    ) >= 1
    assert backend_architecture.get("execution_plane", {}).get("plan", {}).get("operation_kinds")
    assert any(
        item.get("operation_kind") == "regression_replay"
        and item.get("depends_on")
        and item.get("output_refs")
        for item in backend_architecture.get("execution_plane", {}).get("operations", [])
    )
    assert any(
        item.get("operation_kind") == "rollback"
        and item.get("status") == "executed"
        for item in backend_architecture.get("execution_plane", {}).get("operations", [])
    )
    assert backend_architecture.get("replay_plane", {}).get("timeline_summary", {}).get("snapshot_count", 0) >= 1
    assert backend_architecture.get("replay_plane", {}).get("timeline_summary", {}).get(
        "latest_typed_family_count", 0
    ) >= 1
    assert backend_architecture.get("replay_plane", {}).get("timeline_summary", {}).get(
        "latest_typed_contract_count", 0
    ) >= 1
    assert backend_architecture.get("replay_plane", {}).get("latest_snapshot", {}).get("projection_refs")
    assert backend_architecture.get("replay_plane", {}).get("latest_snapshot", {}).get("typed_family_counts")
    assert backend_architecture.get("replay_plane", {}).get("latest_snapshot", {}).get("typed_contract_counts")
    for artifact_ref in attack_loop.get("attack_results", [{}])[0].get("artifact_refs", []):
        assert Path(artifact_ref).exists()
    assert result.discussion_log
    assert result.discussion_log[0].actor in STABLE_ACTORS
    assert result.discussion_log[0].actor_label
    assert result.credibility_assessment.trust_level
    assert result.credibility_assessment.trust_level_label


def test_langgraph_mas_observe_only_route_skips_patch_flow(monkeypatch, mas_service):
    def fake_expert_gate(self, projection, *, run_id):  # noqa: ANN001
        target_service_ref = ""
        for artifact in projection.artifact_refs:
            metadata = artifact.metadata or {}
            target_service_ref = str(metadata.get("service_id") or "").strip()
            if target_service_ref:
                break
        return ExpertGateDecisionPayload(
            decision_id=f"expert-gate-{run_id[:8]}",
            target_service_ref=target_service_ref or "svc-observe",
            decision_family="observation_flow",
            decision_family_label="观察收敛",
            action="observe_only",
            action_label="观察收敛",
            route_target="delivery",
            route_target_label="交付观察窗口",
            rationale="当前攻击证据已足够沉淀观察结论，本轮不应进入 patch flow。",
            confidence=0.82,
            residual_risk_summary="当前残余风险可先通过观察收口与后续提示词优化继续跟进。",
            follow_up_actions=["记录观察结论", "下一轮按反思卡继续补强"],
        )

    monkeypatch.setattr(MASRuntimeSupport, "_decide_expert_gate_from_projection", fake_expert_gate)

    request = MASRequest(
        requirement="Design a secure password hashing scheme for web applications",
        llm_provider="zhipuai",
        num_variants=1,
        max_audit_rounds=1,
        generate_code=False,
    )

    result = mas_service.execute(request)

    attack_loop = result.delivery.get("attack_loop", {})
    assert attack_loop.get("expert_gate_decision", {}).get("route_target") == "delivery"
    assert attack_loop.get("patch_spec") == {}
    assert attack_loop.get("patch_execution") == {}
    assert attack_loop.get("regression_target_service") == {}
    assert attack_loop.get("regression_attack_decision") == {}
    assert attack_loop.get("loop_status") == "baseline_executed_delivery_observation"
    assert attack_loop.get("reflection_cards")
    assert attack_loop.get("reflection_cards", [{}])[0].get("card_type") == "reflection"
    assert attack_loop.get("reflection_cards", [{}, {}])[1].get("card_type") == "regression_summary"
    assert result.delivery.get("context_projections", {}).get("patch") == {}
    assert result.delivery.get("context_projections", {}).get("reflection", {}).get("agent_id") == "reflection_agent"
    patch_result = next(
        item
        for item in result.delivery.get("backend_architecture", {}).get("control_plane", {}).get("results", [])
        if item.get("stage") == "patch_reflection"
    )
    assert patch_result.get("decision_signal") == "delivery"
    assert patch_result.get("decision_source") == "expert_gate_decision.route_target"
    assert patch_result.get("termination_signal") == "delivery"
    assert patch_result.get("primary_output_ref") == "delivery.attack_loop.expert_gate_decision"


def test_langgraph_mas_retry_route_runs_same_run_attack_follow_up(monkeypatch, mas_service):
    original_plan_attack = MASRuntimeSupport._plan_attack_from_projection
    gate_calls = {"count": 0}

    def fake_expert_gate(self, projection, *, run_id):  # noqa: ANN001
        gate_calls["count"] += 1
        target_service_ref = ""
        for artifact in projection.artifact_refs:
            metadata = artifact.metadata or {}
            target_service_ref = str(metadata.get("service_id") or "").strip()
            if target_service_ref:
                break
        if gate_calls["count"] == 1:
            return ExpertGateDecisionPayload(
                decision_id=f"expert-gate-{run_id[:8]}",
                target_service_ref=target_service_ref or "svc-retry",
                decision_family="retry_flow",
                decision_family_label="补充验证",
                action="retry_attack",
                action_label="补充攻击验证",
                route_target="attack_planning_agent",
                route_target_label="攻击重规划窗口",
                rationale="当前基线证据不足，需要同轮补充攻击验证。",
                confidence=0.8,
                residual_risk_summary="当前残余风险仍需要额外采样确认。",
                follow_up_actions=["扩大攻击采样", "重新确认错误路径"],
            )
        return ExpertGateDecisionPayload(
            decision_id=f"expert-gate-{run_id[:8]}",
            target_service_ref=target_service_ref or "svc-retry",
            decision_family="observation_flow",
            decision_family_label="观察收敛",
            action="observe_only",
            action_label="观察收敛",
            route_target="delivery",
            route_target_label="交付观察窗口",
            rationale="补充攻击证据已经足够，本轮先以观察收口。",
            confidence=0.83,
            residual_risk_summary="残余风险可先在下一轮按反思卡继续跟进。",
            follow_up_actions=["沉淀补充攻击结论", "下一轮继续补强攻击策略"],
        )

    def fake_plan_attack(self, projection, *, run_id):  # noqa: ANN001
        if str(run_id).endswith("-retry"):
            return (
                AttackDecisionPayload(
                    decision_id=f"attack-decision-{run_id[:8]}",
                    target_service_ref="svc-retry",
                    action="execute",
                    action_label="执行补充攻击",
                    rationale="专家闸门要求同轮补充验证。",
                    selected_attack_family="oracle_probe",
                    expected_outcome="形成补充漏洞证据。",
                    confidence=0.79,
                    stop_conditions=["补充证据达到阈值"],
                    next_step="dispatch_attack",
                ),
                [
                    item.model_copy(update={"attack_id": f"{item.attack_id}-retry"})
                    for item in original_plan_attack(self, projection, run_id=run_id)[1]
                ],
            )
        return original_plan_attack(self, projection, run_id=run_id)

    monkeypatch.setattr(MASRuntimeSupport, "_decide_expert_gate_from_projection", fake_expert_gate)
    monkeypatch.setattr(MASRuntimeSupport, "_plan_attack_from_projection", fake_plan_attack)

    request = MASRequest(
        requirement="Design a secure password hashing scheme for web applications",
        llm_provider="zhipuai",
        num_variants=1,
        max_audit_rounds=1,
        generate_code=False,
    )

    result = mas_service.execute(request)

    attack_loop = result.delivery.get("attack_loop", {})
    assert attack_loop.get("expert_gate_decision", {}).get("route_target") == "attack_planning_agent"
    assert attack_loop.get("retry_expert_gate_decision", {}).get("route_target") == "delivery"
    assert attack_loop.get("patch_spec") == {}
    assert attack_loop.get("retry_attack_decision", {}).get("action") == "execute"
    assert attack_loop.get("retry_attack_results")
    assert attack_loop.get("retry_vulnerability_verdict", {}).get("summary")
    assert attack_loop.get("same_run_retry_budget") == 1
    assert attack_loop.get("same_run_retry_used") == 1
    assert attack_loop.get("same_run_retry_remaining") == 0
    assert attack_loop.get("same_run_retry_summary", {}).get("requested") is True
    assert attack_loop.get("same_run_retry_summary", {}).get("started") is True
    assert attack_loop.get("same_run_retry_summary", {}).get("final_resolution") == "observed_after_retry"
    assert attack_loop.get("same_run_retry_summary", {}).get("attempt_count") == 1
    assert attack_loop.get("same_run_retry_summary", {}).get("attempt_trace", [{}])[0].get("status") == "executed"
    assert (
        attack_loop.get("same_run_retry_summary", {}).get("attempt_trace", [{}])[0].get("termination_reason")
        == "observed_after_retry"
    )
    assert (
        attack_loop.get("same_run_retry_summary", {}).get("attempt_trace", [{}])[0].get("planning_projection_ref")
        == "attack_planning_agent:attack-plan-r2"
    )
    assert (
        attack_loop.get("same_run_retry_summary", {}).get("attempt_trace", [{}])[0].get(
            "vulnerability_projection_ref"
        )
        == "vulnerability_agent:vulnerability-r2"
    )
    assert (
        attack_loop.get("same_run_retry_summary", {}).get("attempt_trace", [{}])[0].get(
            "expert_gate_projection_ref"
        )
        == "expert_gate_agent:expert-gate-r2"
    )
    assert result.delivery.get("context_projections", {}).get("attack_planning_retry", {}).get("agent_id") == "attack_planning_agent"
    assert (
        result.delivery.get("context_projections", {}).get("vulnerability_evaluation_retry", {}).get("agent_id")
        == "vulnerability_agent"
    )
    assert any(
        item.get("card_type") == "retry_context_summary"
        for item in result.delivery.get("context_projections", {}).get("attack_planning_retry", {}).get("cards", [])
    )
    retry_summary_card = next(
        item
        for item in result.delivery.get("context_projections", {}).get("attack_planning_retry", {}).get("cards", [])
        if item.get("card_type") == "retry_context_summary"
    )
    assert retry_summary_card.get("payload", {}).get("compression_policy") == "retain_summary_and_refs_drop_raw_details"
    assert retry_summary_card.get("payload", {}).get("retained_refs")
    assert retry_summary_card.get("payload", {}).get("dropped_detail_hints")
    assert retry_summary_card.get("payload", {}).get("resume_checkpoint_ref")
    assert retry_summary_card.get("payload", {}).get("resume_inputs", {}).get("retained_refs")
    assert any(
        item.get("card_type") == "retry_context_summary"
        for item in result.delivery.get("context_projections", {}).get("vulnerability_evaluation_retry", {}).get("cards", [])
    )
    memory_bus = result.delivery.get("backend_architecture", {}).get("memory_bus", {})
    assert memory_bus.get("summary", {}).get("retry_window_count") == 3
    assert memory_bus.get("summary", {}).get("retry_handoff_count", 0) >= 3
    assert "attack_planning_agent:attack-plan-r2" in memory_bus.get("summary", {}).get("retry_projection_refs", [])
    assert "vulnerability_agent:vulnerability-r2" in memory_bus.get("summary", {}).get("retry_projection_refs", [])
    assert "expert_gate_agent:expert-gate-r2" in memory_bus.get("summary", {}).get("retry_projection_refs", [])
    assert memory_bus.get("summary", {}).get("retry_lineage_refs")
    assert memory_bus.get("summary", {}).get("retry_typed_contract_refs")
    assert memory_bus.get("summary", {}).get("retry_compression_stages")
    assert memory_bus.get("summary", {}).get("retry_compression_policies") == [
        "retain_summary_and_refs_drop_raw_details"
    ]
    assert memory_bus.get("summary", {}).get("retry_retained_refs")
    assert memory_bus.get("summary", {}).get("retry_resume_checkpoint_refs")
    assert memory_bus.get("summary", {}).get("retry_resume_input_refs")
    assert len(attack_loop.get("rounds", [])) == 2
    assert attack_loop.get("rounds", [{}, {}])[1].get("round_kind") == "retry"
    assert attack_loop.get("rounds", [{}, {}])[1].get("mode") == "executed"
    assert attack_loop.get("rounds", [{}, {}])[1].get("expert_gate_decision", {}).get("route_target") == "delivery"
    assert attack_loop.get("loop_status") == "baseline_executed_retry_executed_delivery_observation"
    assert attack_loop.get("reflection_cards")
    assert result.delivery.get("sandbox_dispatcher", {}).get("retry_attack", {}).get("status") == "executed"
    patch_result = next(
        item
        for item in result.delivery.get("backend_architecture", {}).get("control_plane", {}).get("results", [])
        if item.get("stage") == "patch_reflection"
    )
    assert (
        result.delivery.get("backend_architecture", {})
        .get("control_plane", {})
        .get("summary", {})
        .get("same_run_retry", {})
        .get("final_resolution")
        == "observed_after_retry"
    )
    assert patch_result.get("metadata", {}).get("same_run_retry", {}).get("final_resolution") == "observed_after_retry"
    assert patch_result.get("decision_signal") == "delivery"
    assert patch_result.get("decision_source") == "retry_expert_gate_decision.route_target"
    assert patch_result.get("primary_output_ref") == "delivery.attack_loop.retry_expert_gate_decision"


def test_langgraph_mas_retry_route_can_be_disabled_by_budget(monkeypatch, mas_service):
    def fake_expert_gate(self, projection, *, run_id):  # noqa: ANN001
        target_service_ref = ""
        for artifact in projection.artifact_refs:
            metadata = artifact.metadata or {}
            target_service_ref = str(metadata.get("service_id") or "").strip()
            if target_service_ref:
                break
        return ExpertGateDecisionPayload(
            decision_id=f"expert-gate-{run_id[:8]}",
            target_service_ref=target_service_ref or "svc-retry-disabled",
            decision_family="retry_flow",
            decision_family_label="补充验证",
            action="retry_attack",
            action_label="补充攻击验证",
            route_target="attack_planning_agent",
            route_target_label="攻击重规划窗口",
            rationale="当前证据不足，理论上应继续补充攻击验证。",
            confidence=0.8,
            residual_risk_summary="当前残余风险仍需要额外采样确认。",
            follow_up_actions=["扩大攻击采样", "重新确认错误路径"],
        )

    monkeypatch.setattr(MASRuntimeSupport, "_decide_expert_gate_from_projection", fake_expert_gate)

    request = MASRequest(
        requirement="Design a secure password hashing scheme for web applications",
        llm_provider="zhipuai",
        num_variants=1,
        max_audit_rounds=1,
        max_same_run_retries=0,
        generate_code=False,
    )

    result = mas_service.execute(request)

    attack_loop = result.delivery.get("attack_loop", {})
    assert attack_loop.get("expert_gate_decision", {}).get("route_target") == "attack_planning_agent"
    assert attack_loop.get("retry_attack_decision") == {}
    assert attack_loop.get("retry_expert_gate_decision") == {}
    assert attack_loop.get("same_run_retry_budget") == 0
    assert attack_loop.get("same_run_retry_used") == 0
    assert attack_loop.get("same_run_retry_remaining") == 0
    assert attack_loop.get("same_run_retry_summary", {}).get("blocked_by_budget") is True
    assert attack_loop.get("same_run_retry_summary", {}).get("final_resolution") == "blocked_by_budget"
    assert attack_loop.get("same_run_retry_summary", {}).get("attempt_count") == 1
    assert attack_loop.get("same_run_retry_summary", {}).get("attempt_trace", [{}])[0].get("status") == "blocked"
    assert result.delivery.get("context_projections", {}).get("attack_planning_retry") == {}
    assert result.delivery.get("context_projections", {}).get("vulnerability_evaluation_retry") == {}
    memory_bus = result.delivery.get("backend_architecture", {}).get("memory_bus", {})
    assert memory_bus.get("summary", {}).get("retry_window_count") == 0
    assert memory_bus.get("summary", {}).get("retry_handoff_count") == 0
    assert len(attack_loop.get("rounds", [])) == 1
    assert attack_loop.get("loop_status") == "baseline_executed_retry_blocked_by_budget"
    assert (
        result.delivery.get("backend_architecture", {})
        .get("control_plane", {})
        .get("summary", {})
        .get("same_run_retry", {})
        .get("final_resolution")
        == "blocked_by_budget"
    )


def test_langgraph_mas_retry_regate_can_enter_patch_flow(monkeypatch, mas_service):
    original_plan_attack = MASRuntimeSupport._plan_attack_from_projection
    gate_calls = {"count": 0}

    def fake_expert_gate(self, projection, *, run_id):  # noqa: ANN001
        gate_calls["count"] += 1
        target_service_ref = ""
        for artifact in projection.artifact_refs:
            metadata = artifact.metadata or {}
            target_service_ref = str(metadata.get("service_id") or "").strip()
            if target_service_ref:
                break
        if gate_calls["count"] == 1:
            return ExpertGateDecisionPayload(
                decision_id=f"expert-gate-{run_id[:8]}",
                target_service_ref=target_service_ref or "svc-retry",
                decision_family="retry_flow",
                decision_family_label="补充验证",
                action="retry_attack",
                action_label="补充攻击验证",
                route_target="attack_planning_agent",
                route_target_label="攻击重规划窗口",
                rationale="当前基线证据不足，需要同轮补充攻击验证。",
                confidence=0.8,
                residual_risk_summary="当前残余风险仍需要额外采样确认。",
                follow_up_actions=["扩大攻击采样", "重新确认错误路径"],
            )
        return ExpertGateDecisionPayload(
            decision_id=f"expert-gate-{run_id[:8]}",
            target_service_ref=target_service_ref or "svc-retry",
            decision_family="patch_flow",
            decision_family_label="进入修补",
            action="plan_patch",
            action_label="进入修补",
            route_target="patch_agent",
            route_target_label="修补窗口",
            rationale="补充攻击证据已经足够支持进入 patch flow。",
            confidence=0.86,
            residual_risk_summary="需要尽快修补当前漏洞并做正式回归验证。",
            follow_up_actions=["生成修补方案", "执行正式回归"],
        )

    def fake_plan_attack(self, projection, *, run_id):  # noqa: ANN001
        if str(run_id).endswith("-retry"):
            _, baseline_specs = original_plan_attack(self, projection, run_id=run_id)
            return (
                AttackDecisionPayload(
                    decision_id=f"attack-decision-{run_id[:8]}",
                    target_service_ref="svc-retry",
                    action="execute",
                    action_label="执行补充攻击",
                    rationale="专家闸门要求同轮补充验证。",
                    selected_attack_family="oracle_probe",
                    expected_outcome="形成补充漏洞证据。",
                    confidence=0.79,
                    stop_conditions=["补充证据达到阈值"],
                    next_step="dispatch_attack",
                ),
                [
                    item.model_copy(update={"attack_id": f"{item.attack_id}-retry"})
                    for item in baseline_specs
                ],
            )
        return original_plan_attack(self, projection, run_id=run_id)

    monkeypatch.setattr(MASRuntimeSupport, "_decide_expert_gate_from_projection", fake_expert_gate)
    monkeypatch.setattr(MASRuntimeSupport, "_plan_attack_from_projection", fake_plan_attack)

    request = MASRequest(
        requirement="Design a secure password hashing scheme for web applications",
        llm_provider="zhipuai",
        num_variants=1,
        max_audit_rounds=1,
        generate_code=False,
    )

    result = mas_service.execute(request)

    attack_loop = result.delivery.get("attack_loop", {})
    assert attack_loop.get("expert_gate_decision", {}).get("route_target") == "attack_planning_agent"
    assert attack_loop.get("retry_expert_gate_decision", {}).get("route_target") == "patch_agent"
    assert attack_loop.get("patch_spec", {}).get("patch_id")
    assert attack_loop.get("patch_execution", {}).get("execution_id")
    assert attack_loop.get("same_run_retry_summary", {}).get("final_resolution") == "patched_after_retry"
    assert attack_loop.get("same_run_retry_summary", {}).get("attempt_count") == 1
    assert attack_loop.get("same_run_retry_summary", {}).get("attempt_trace", [{}])[0].get("status") == "executed"
    assert (
        attack_loop.get("same_run_retry_summary", {}).get("attempt_trace", [{}])[0].get("termination_reason")
        == "patched_after_retry"
    )
    assert result.delivery.get("context_projections", {}).get("attack_planning_retry", {}).get("agent_id") == "attack_planning_agent"
    assert (
        result.delivery.get("context_projections", {}).get("vulnerability_evaluation_retry", {}).get("agent_id")
        == "vulnerability_agent"
    )
    assert any(
        item.get("card_type") == "retry_context_summary"
        for item in result.delivery.get("context_projections", {}).get("attack_planning_retry", {}).get("cards", [])
    )
    memory_bus = result.delivery.get("backend_architecture", {}).get("memory_bus", {})
    assert memory_bus.get("summary", {}).get("retry_window_count") == 3
    assert "expert_gate_agent:expert-gate-r2" in memory_bus.get("summary", {}).get("retry_projection_refs", [])
    assert memory_bus.get("summary", {}).get("retry_typed_contract_refs")
    assert memory_bus.get("summary", {}).get("retry_compression_policies") == [
        "retain_summary_and_refs_drop_raw_details"
    ]
    assert memory_bus.get("summary", {}).get("retry_resume_checkpoint_refs")
    assert len(attack_loop.get("rounds", [])) == 3
    assert attack_loop.get("rounds", [{}, {}, {}])[1].get("round_kind") == "retry"
    assert attack_loop.get("rounds", [{}, {}, {}])[2].get("round_kind") == "regression"
    assert attack_loop.get("loop_status") == "baseline_executed_retry_executed_regression_executed"


def test_langgraph_mas_with_cache(mas_service, redis_client):
    """Second call with the same payload should mark cache hit when Redis is available."""
    if not redis_client.is_available():
        pytest.skip("Redis not available")

    token = uuid4().hex[:8]
    request = MASRequest(
        requirement=f"Design AES-GCM encryption for IoT devices [{token}]",
        llm_provider="zhipuai",
        num_variants=1,
        max_audit_rounds=1,
        generate_code=False,
    )

    result1 = mas_service.execute(request)
    result2 = mas_service.execute(request)

    assert result1.delivery.get("engine") == "langgraph"
    assert result2.delivery.get("engine") == "langgraph"
    assert result1.delivery.get("cache_hit") is False
    assert result2.delivery.get("cache_hit") is True


def test_langgraph_mas_preserves_request_id(mas_service):
    """request_id parameter should be reflected in the output identifiers."""
    run_id = "test-persistence-123"
    request = MASRequest(
        requirement="Design a digital signature scheme",
        llm_provider="zhipuai",
        run_id=run_id,
        num_variants=1,
        max_audit_rounds=1,
        generate_code=False,
    )

    result = mas_service.execute(request, request_id=run_id)
    assert result.request_id == run_id
    assert result.run_id == run_id


def test_langgraph_mas_graph_native_path_does_not_delegate_to_legacy_execute(monkeypatch, mas_service):
    """LangGraph path should no longer depend on MASOrchestrationService.execute()."""

    def fail_execute(*args, **kwargs):
        raise AssertionError("legacy execute() should not be called by LangGraphMASService")

    monkeypatch.setattr(MASOrchestrationService, "execute", fail_execute)
    request = MASRequest(
        requirement="为建筑项目 BIM/IFC 交付设计后量子可迁移的低延迟签名与加密方案",
        llm_provider="zhipuai",
        num_variants=2,
        max_audit_rounds=2,
        generate_code=False,
    )

    result = mas_service.execute(request)

    assert isinstance(result, MASResponse)
    assert result.delivery.get("engine") == "langgraph"
    assert result.delivery.get("engine_mode") == "graph-native"
    assert result.delivery.get("workflow_trace") == EXPECTED_TRACE
    assert result.analyst is not None
    assert result.architect is not None
    assert result.evidence_pack is not None
    assert result.evidence_pack.backend in {"local", "qdrant"}


def test_langgraph_mas_persists_case_memory_across_runs(mas_service):
    case_id = f"case-integration-{uuid4().hex[:8]}"
    request = MASRequest(
        requirement="为建筑项目 CDE 中的 BIM/IFC 交付设计支持后量子迁移的低延迟加密方案，并满足审计留痕。",
        llm_provider="zhipuai",
        case_id=case_id,
        num_variants=2,
        max_audit_rounds=2,
        generate_code=False,
    )

    first = mas_service.execute(request)
    second = mas_service.execute(request)

    assert first.case_id == case_id
    assert first.case_memory is not None
    assert first.case_memory.recent_reflections
    assert first.delivery.get("case_memory_summary", {}).get("case_id") == case_id
    assert first.delivery.get("case_memory_summary", {}).get("reflection_count", 0) >= 1
    assert second.analyst.case_context.get("has_history") is True
    assert second.analyst.case_context.get("prior_decisions", 0) >= 1
    assert second.analyst.case_context.get("recent_reflection_count", 0) >= 1
    assert second.case_memory is not None
    assert len(second.case_memory.decision_log) >= len(first.case_memory.decision_log)
    generation_cards = second.delivery.get("context_projections", {}).get("generation", {}).get("cards", [])
    audit_cards = second.delivery.get("context_projections", {}).get("audit", {}).get("cards", [])
    assert any(
        item.get("card_type") == "reflection_memory"
        and item.get("payload", {}).get("latest_prompt_changes")
        for item in generation_cards
    )
    assert any(
        item.get("card_type") == "reflection_memory"
        and item.get("payload", {}).get("latest_audit_focus")
        for item in audit_cards
    )
    assert any(
        item.get("card_type") == "generation_runtime_input"
        and item.get("payload", {}).get("structured_spec")
        for item in generation_cards
    )
    assert any(
        item.get("card_type") == "audit_runtime_input"
        and item.get("payload", {}).get("schemes")
        for item in audit_cards
    )
    assert any(
        item.get("card_type") == "audit_runtime_input"
        and item.get("payload", {}).get("scheme_entries")
        for item in audit_cards
    )
    assert any(
        "[反思回灌]" in str(candidate.design_rationale or "")
        for candidate in second.architect.candidates
    )
    assert any(
        any("项目级反思" in str(change or "") for change in round_item.recommended_changes)
        for round_item in second.auditor_rounds
    )


def test_langgraph_mas_allows_attack_handoff_without_sandbox_execution(monkeypatch):
    def fake_plan_attack(self, projection, *, run_id):
        return (
            AttackDecisionPayload(
                decision_id=f"attack-decision-{run_id[:8]}",
                target_service_ref="svc-test",
                action="handoff_to_vulnerability",
                action_label="转交漏洞评估",
                rationale="当前证据已经足以进入漏洞评估。",
                selected_attack_family="oracle_probe",
                expected_outcome="直接形成漏洞裁决。",
                confidence=0.82,
                stop_conditions=["不再新增攻击任务"],
                next_step="handoff_to_vulnerability",
            ),
            [],
        )

    monkeypatch.setattr(MASRuntimeSupport, "_plan_attack_from_projection", fake_plan_attack)
    mas_service = LangGraphMASService(llm_provider="zhipuai")
    request = MASRequest(
        requirement="Design a secure password hashing scheme for web applications",
        llm_provider="zhipuai",
        num_variants=1,
        max_audit_rounds=1,
        generate_code=False,
    )

    result = mas_service.execute(request)

    attack_loop = result.delivery.get("attack_loop", {})
    assert attack_loop.get("attack_decision", {}).get("action") == "handoff_to_vulnerability"
    assert attack_loop.get("attack_results") == []
    assert attack_loop.get("rounds", [{}])[0].get("mode") == "handoff"
    assert attack_loop.get("vulnerability_verdict", {}).get("summary")
    route_target = attack_loop.get("expert_gate_decision", {}).get("route_target")
    assert route_target in {"patch_agent", "attack_planning_agent", "delivery"}
    if route_target == "patch_agent":
        assert attack_loop.get("regression_attack_decision", {}).get("action") == "handoff_to_vulnerability"
        assert attack_loop.get("rounds", [{}, {}])[1].get("mode") == "handoff"
        assert attack_loop.get("loop_status") == "baseline_handoff_regression_handoff"
        assert attack_loop.get("regression_vulnerability_verdict", {}).get("summary")
    else:
        assert attack_loop.get("patch_spec") == {}
        assert attack_loop.get("regression_attack_decision") == {}
        assert len(attack_loop.get("rounds", [])) == 1
        assert attack_loop.get("loop_status") in {
            "baseline_handoff_delivery_observation",
            "baseline_handoff_retry_follow_up",
        }
    sandbox_dispatcher = result.delivery.get("sandbox_dispatcher", {})
    assert sandbox_dispatcher.get("baseline_attack", {}).get("status") == "skipped"
    assert sandbox_dispatcher.get("baseline_attack", {}).get("decision") == "handoff_to_vulnerability"
    assert sandbox_dispatcher.get("baseline_attack", {}).get("audit_trail", [{}])[-1].get("event_kind") == "handoff"
    if route_target == "patch_agent":
        assert sandbox_dispatcher.get("regression_attack", {}).get("status") == "skipped"
        assert sandbox_dispatcher.get("regression_attack", {}).get("decision") == "handoff_to_vulnerability"
    else:
        assert sandbox_dispatcher.get("regression_attack", {}) == {}
