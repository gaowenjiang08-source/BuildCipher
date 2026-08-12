from datetime import datetime, timezone

from cipher_genius.api.schemas import (
    AttackDecisionPayload,
    ContextConstraintPayload,
    ContextProjectionPayload,
    ExpertGateDecisionPayload,
    MemoryCardPayload,
    MemoryHandoffPayload,
    PatchExecutionPayload,
    SandboxDispatchResultPayload,
)
from cipher_genius.core.control_plane import ControlPlaneBuilder


def test_control_plane_builder_emits_contract_fields():
    builder = ControlPlaneBuilder()
    generation_projection = ContextProjectionPayload(
        agent_id="generation_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="generation-r1",
        objective="生成候选方案",
        constraints=[ContextConstraintPayload(value="必须满足审计留痕")],
        cards=[
            MemoryCardPayload(
                card_id="card-001",
                card_type="generation_runtime_input",
                case_id="case-001",
                run_id="run-001",
                source_agent="analyst",
                summary="已恢复 generation 运行时输入。",
                created_at=datetime.now(timezone.utc),
            )
        ],
    )
    attack_projection = ContextProjectionPayload(
        agent_id="attack_planning_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="attack-plan-r1",
        objective="生成攻击计划",
    )
    reflection_projection = ContextProjectionPayload(
        agent_id="reflection_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="reflection-r1",
        objective="形成闭环反思",
    )
    memory_handoff = MemoryHandoffPayload(
        handoff_id="handoff-001",
        from_agent="generation_agent",
        to_agent="attack_planning_agent",
        case_id="case-001",
        run_id="run-001",
        objective="把关键候选传给攻击规划层。",
        projection=attack_projection,
    )
    baseline_attack_dispatch = SandboxDispatchResultPayload(
        dispatch_id="dispatch-attack-001",
        run_id="run-001",
        stage="attack_execution",
        target_service_ref="svc-001",
        decision="handoff_to_vulnerability",
        decision_label="转交漏洞评估",
        status="skipped",
        status_label="已跳过",
    )
    baseline_deployment_dispatch = SandboxDispatchResultPayload(
        dispatch_id="dispatch-deploy-001",
        run_id="run-001",
        stage="target_deployment",
        target_service_ref="svc-001",
        decision="approved",
        decision_label="已批准",
        status="executed",
        status_label="已执行",
    )
    patch_execution = PatchExecutionPayload(
        execution_id="patch-exec-001",
        patch_id="patch-001",
        target_service_ref="svc-001",
        target_service_version="v2",
        status="validated",
        status_label="已验证",
        summary="补丁执行与回归验证已完成。",
        workspace="F:/workspace",
    )
    control_plane = builder.build(
        run_id="run-001",
        case_id="case-001",
        workflow_trace=["analyst", "architect", "attack_executor", "patch_reflection", "delivery"],
        projections={
            "generation": generation_projection,
            "attack_planning": attack_projection,
            "reflection": reflection_projection,
        },
        memory_handoffs=[memory_handoff],
        runtime_context={
            "audit_passed": True,
            "delivery_status": "approved",
            "attack_results": [],
            "attack_decision": AttackDecisionPayload(
                decision_id="attack-decision-001",
                target_service_ref="svc-001",
                action="handoff_to_vulnerability",
                action_label="转交漏洞评估",
                rationale="当前证据已足够。",
                selected_attack_family="oracle_probe",
                next_step="handoff_to_vulnerability",
            ),
            "baseline_deployment_dispatch": baseline_deployment_dispatch,
            "baseline_attack_dispatch": baseline_attack_dispatch,
            "patch_execution": patch_execution,
            "regression_attack_decision": AttackDecisionPayload(
                decision_id="attack-decision-002",
                target_service_ref="svc-001",
                action="replan",
                action_label="重新规划",
                rationale="需要基于补丁结果重新规划。",
                selected_attack_family="regression_check",
                next_step="dispatch_attack",
            ),
        },
    )

    assert control_plane.summary["contract_version"] == "v1"
    assert control_plane.summary["blocking_stage_count"] == 4
    assert control_plane.summary["retryable_stage_count"] >= 3
    attack_invocation = next(item for item in control_plane.invocations if item.stage == "attack_executor")
    assert attack_invocation.checkpoint_ref
    assert attack_invocation.result_ref
    assert attack_invocation.retryable is True
    assert attack_invocation.retry_strategy == "replan_or_handoff_before_skip"
    assert attack_invocation.termination_mode == "handoff_to_vulnerability"
    assert attack_invocation.decision_source == "attack_decision.action"
    assert attack_invocation.contract is not None
    assert attack_invocation.contract.failure_action == "skip_dispatch_or_handoff"
    assert attack_invocation.contract.next_stages == ["vulnerability_evaluation"]
    assert attack_invocation.contract.depends_on == ["target_service", "attack_planning_projection"]
    assert attack_invocation.contract.retryable is True
    assert attack_invocation.contract.termination_conditions
    assert attack_invocation.contract.decision_source == "attack_decision.action"
    attack_checkpoint = next(item for item in control_plane.checkpoints if item.stage == "attack_executor")
    assert "delivery.attack_loop.attack_decision" in attack_checkpoint.output_refs
    assert "dispatch:dispatch-attack-001" in attack_checkpoint.output_refs
    assert attack_checkpoint.status == "skipped"
    assert attack_checkpoint.retryable is True
    assert attack_checkpoint.failure_action == "skip_dispatch_or_handoff"
    assert attack_checkpoint.termination_signal == "handoff_to_vulnerability"
    assert attack_checkpoint.decision_source == "attack_decision.action"
    patch_result = next(item for item in control_plane.results if item.stage == "patch_reflection")
    assert patch_result.decision_signal == "replan"
    assert patch_result.decision_source == "regression_attack_decision.action_or_patch_execution.status"
    assert patch_result.termination_signal == "replan"
    assert patch_result.failure_action == "emit_patch_report_with_residual_risk"
    assert patch_result.primary_output_ref == "delivery.attack_loop.patch_spec"
    delivery_invocation = next(item for item in control_plane.invocations if item.stage == "delivery")
    assert delivery_invocation.terminal is True
    assert delivery_invocation.retryable is False


def test_control_plane_builder_uses_expert_gate_route_when_patch_flow_is_skipped():
    builder = ControlPlaneBuilder()
    reflection_projection = ContextProjectionPayload(
        agent_id="reflection_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="reflection-r1",
        objective="形成观察收口反思卡",
    )

    control_plane = builder.build(
        run_id="run-001",
        case_id="case-001",
        workflow_trace=["attack_executor", "patch_reflection", "delivery"],
        projections={
            "reflection": reflection_projection,
        },
        memory_handoffs=[],
        runtime_context={
            "delivery_status": "approved",
            "attack_decision": AttackDecisionPayload(
                decision_id="attack-decision-001",
                target_service_ref="svc-001",
                action="execute",
                action_label="执行攻击",
                rationale="先完成基线攻击。",
                selected_attack_family="oracle_probe",
                next_step="dispatch_attack",
            ),
            "expert_gate_decision": ExpertGateDecisionPayload(
                decision_id="expert-gate-001",
                target_service_ref="svc-001",
                decision_family="observation_flow",
                decision_family_label="观察收敛",
                action="observe_only",
                action_label="观察收敛",
                route_target="delivery",
                route_target_label="交付观察窗口",
                rationale="当前证据足以先观察收口，不应误进入 patch flow。",
                confidence=0.78,
                residual_risk_summary="残余风险已被约束，可先进入交付观察。",
                follow_up_actions=["保留观察结论", "下一轮按反思卡继续补强"],
            ),
        },
    )

    patch_result = next(item for item in control_plane.results if item.stage == "patch_reflection")
    assert patch_result.decision_signal == "delivery"
    assert patch_result.decision_source == "expert_gate_decision.route_target"
    assert patch_result.termination_signal == "delivery"
    assert patch_result.primary_output_ref == "delivery.attack_loop.expert_gate_decision"


def test_control_plane_builder_prefers_retry_attack_signal_when_same_run_retry_executes():
    builder = ControlPlaneBuilder()
    reflection_projection = ContextProjectionPayload(
        agent_id="reflection_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="reflection-r1",
        objective="形成 retry follow-up 反思卡",
    )
    retry_dispatch = SandboxDispatchResultPayload(
        dispatch_id="dispatch-retry-001",
        run_id="run-001",
        round_id="retry",
        stage="attack_execution",
        target_service_ref="svc-001",
        decision="execute",
        decision_label="执行攻击",
        status="executed",
        status_label="已执行",
    )

    control_plane = builder.build(
        run_id="run-001",
        case_id="case-001",
        workflow_trace=["attack_executor", "patch_reflection", "delivery"],
        projections={"reflection": reflection_projection},
        memory_handoffs=[],
        runtime_context={
            "delivery_status": "approved",
            "attack_decision": AttackDecisionPayload(
                decision_id="attack-decision-001",
                target_service_ref="svc-001",
                action="execute",
                action_label="执行攻击",
                rationale="先完成首轮攻击。",
                selected_attack_family="oracle_probe",
                next_step="dispatch_attack",
            ),
            "expert_gate_decision": ExpertGateDecisionPayload(
                decision_id="expert-gate-001",
                target_service_ref="svc-001",
                decision_family="retry_flow",
                decision_family_label="补充验证",
                action="retry_attack",
                action_label="补充攻击验证",
                route_target="attack_planning_agent",
                route_target_label="攻击重规划窗口",
                rationale="当前证据不足，需要同轮补充攻击验证。",
                confidence=0.81,
                residual_risk_summary="当前残余风险仍需进一步采样确认。",
                follow_up_actions=["补充攻击", "再次评估"],
            ),
            "retry_attack_decision": AttackDecisionPayload(
                decision_id="attack-decision-retry-001",
                target_service_ref="svc-001",
                action="execute",
                action_label="执行补充攻击",
                rationale="专家闸门要求同轮补充验证。",
                selected_attack_family="oracle_probe",
                next_step="dispatch_attack",
            ),
            "retry_attack_dispatch": retry_dispatch,
        },
    )

    patch_result = next(item for item in control_plane.results if item.stage == "patch_reflection")
    assert patch_result.decision_signal == "execute"
    assert patch_result.decision_source == "retry_attack_decision.action_or_retry_vulnerability_verdict.severity"
    assert patch_result.termination_signal == "execute"
    assert patch_result.primary_output_ref == "delivery.attack_loop.retry_attack_decision"


def test_control_plane_builder_prefers_retry_expert_gate_after_same_run_regate():
    builder = ControlPlaneBuilder()
    reflection_projection = ContextProjectionPayload(
        agent_id="reflection_agent",
        case_id="case-001",
        run_id="run-001",
        round_id="reflection-r1",
        objective="形成 retry re-gate 收口卡",
    )
    retry_dispatch = SandboxDispatchResultPayload(
        dispatch_id="dispatch-retry-001",
        run_id="run-001",
        round_id="retry",
        stage="attack_execution",
        target_service_ref="svc-001",
        decision="execute",
        decision_label="执行攻击",
        status="executed",
        status_label="已执行",
    )

    control_plane = builder.build(
        run_id="run-001",
        case_id="case-001",
        workflow_trace=["attack_executor", "patch_reflection", "delivery"],
        projections={"reflection": reflection_projection},
        memory_handoffs=[],
        runtime_context={
            "delivery_status": "approved",
            "attack_decision": AttackDecisionPayload(
                decision_id="attack-decision-001",
                target_service_ref="svc-001",
                action="execute",
                action_label="执行攻击",
                rationale="先完成首轮攻击。",
                selected_attack_family="oracle_probe",
                next_step="dispatch_attack",
            ),
            "expert_gate_decision": ExpertGateDecisionPayload(
                decision_id="expert-gate-001",
                target_service_ref="svc-001",
                decision_family="retry_flow",
                decision_family_label="补充验证",
                action="retry_attack",
                action_label="补充攻击验证",
                route_target="attack_planning_agent",
                route_target_label="攻击重规划窗口",
                rationale="当前证据不足，需要同轮补充攻击验证。",
                confidence=0.81,
                residual_risk_summary="当前残余风险仍需进一步采样确认。",
                follow_up_actions=["补充攻击", "再次评估"],
            ),
            "retry_attack_decision": AttackDecisionPayload(
                decision_id="attack-decision-retry-001",
                target_service_ref="svc-001",
                action="execute",
                action_label="执行补充攻击",
                rationale="专家闸门要求同轮补充验证。",
                selected_attack_family="oracle_probe",
                next_step="dispatch_attack",
            ),
            "retry_attack_dispatch": retry_dispatch,
            "retry_expert_gate_decision": ExpertGateDecisionPayload(
                decision_id="expert-gate-002",
                target_service_ref="svc-001",
                decision_family="observation_flow",
                decision_family_label="观察收敛",
                action="observe_only",
                action_label="观察收敛",
                route_target="delivery",
                route_target_label="交付观察窗口",
                rationale="补充攻击后证据已经足够，本轮转入观察收口。",
                confidence=0.84,
                residual_risk_summary="残余风险可留给下一轮反思优化继续跟进。",
                follow_up_actions=["沉淀补充攻击结论", "下一轮继续补强攻击策略"],
            ),
            "same_run_retry_summary": {
                "requested": True,
                "started": True,
                "blocked_by_budget": False,
                "capped_after_regate": False,
                "initial_route_target": "attack_planning_agent",
                "final_route_target": "delivery",
                "max_supported_budget": 1,
                "final_resolution": "observed_after_retry",
                "final_resolution_label": "补充攻击后转观察收口",
                "attempt_count": 1,
                "attempt_trace": [
                    {
                        "attempt_index": 1,
                        "budget_before_attempt": 1,
                        "budget_after_attempt": 0,
                        "status": "executed",
                        "requested_route_target": "attack_planning_agent",
                        "retry_action": "execute",
                        "dispatch_status": "executed",
                        "verdict_severity": "",
                        "final_route_target": "delivery",
                        "termination_reason": "observed_after_retry",
                    }
                ],
            },
        },
    )

    patch_result = next(item for item in control_plane.results if item.stage == "patch_reflection")
    assert control_plane.summary["same_run_retry"]["final_resolution"] == "observed_after_retry"
    assert control_plane.summary["same_run_retry"]["attempt_count"] == 1
    assert patch_result.metadata["same_run_retry"]["final_resolution"] == "observed_after_retry"
    assert patch_result.decision_signal == "delivery"
    assert patch_result.decision_source == "retry_expert_gate_decision.route_target"
    assert patch_result.termination_signal == "delivery"
    assert patch_result.primary_output_ref == "delivery.attack_loop.retry_expert_gate_decision"
