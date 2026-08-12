from cipher_genius.api.schemas import (
    ArtifactRefPayload,
    ContextProjectionPayload,
    ExpertGateDecisionPayload,
    MemoryCardPayload,
    VulnerabilityVerdictPayload,
)
from cipher_genius.core.patch_planning_agent import PatchPlanningAgent


class FakeStructuredLLM:
    def generate_structured(
        self,
        prompt,
        schema,
        system_prompt=None,
        temperature=0.2,
        schema_name="structured_output",
    ):
        return {
            "strategy": "error-boundary-hardening",
            "summary": "Prioritize a unified error response and stricter decrypt input validation.",
            "rationale": "Attack evidence shows the decrypt path and error handling branch are still distinguishable.",
            "changed_artifacts": ["svc-1:python", "svc-1:c"],
            "implementation_notes": [
                "Normalize decrypt input sanitization.",
                "Standardize error response formatting.",
            ],
            "validation_steps": [
                "Redeploy the patched service version.",
                "Run regression probes around the decrypt boundary.",
            ],
            "rollback_notes": ["Rollback to v1 if regression validation fails."],
            "next_version": "v2",
            "regression_focus": ["error leakage", "decrypt boundary"],
        }


def build_projection() -> ContextProjectionPayload:
    verdict = VulnerabilityVerdictPayload(
        verdict_id="verdict-1",
        target_service_ref="svc-1",
        severity="high",
        severity_label="high",
        exploitability="moderate",
        exploitability_label="moderate",
        summary="The target service still has issues around error handling and interface boundaries.",
        affected_components=["decrypt", "error handler"],
        remediation_priority="high",
        remediation_priority_label="high",
        evidence_refs=["attack-1"],
    )
    return ContextProjectionPayload(
        agent_id="patch_agent",
        case_id="case-test",
        run_id="run-patch-001",
        round_id="patch-r1",
        objective="Generate a patch and regression plan from the verdict, audit advice, and attack artifacts.",
        cards=[
            MemoryCardPayload(
                card_id="card-verdict",
                card_type="vulnerability_verdict",
                case_id="case-test",
                run_id="run-patch-001",
                round_id="patch-r1",
                source_agent="vulnerability_agent",
                summary=verdict.summary,
                payload={
                    "severity": verdict.severity,
                    "severity_label": verdict.severity_label,
                    "affected_components": verdict.affected_components,
                    "evidence_refs": verdict.evidence_refs,
                    "verdict": verdict.model_dump(mode="json"),
                },
            ),
            MemoryCardPayload(
                card_id="card-audit",
                card_type="audit_decision",
                case_id="case-test",
                run_id="run-patch-001",
                round_id="audit-r1",
                source_agent="audit_agent",
                summary="Audit recommendation summary",
                payload={
                    "proposal_id": "proposal-1",
                    "reasons": ["The error handling boundary is not stable enough."],
                    "recommended_changes": ["Unify error responses", "Tighten input validation"],
                },
            ),
            MemoryCardPayload(
                card_id="card-artifacts",
                card_type="attack_artifact_summary",
                case_id="case-test",
                run_id="run-patch-001",
                round_id="patch-r1",
                source_agent="attack_planning_agent",
                summary="Attack artifact summary",
                payload={
                    "attack_results": [
                        {
                            "attack_id": "attack-1",
                            "target_service_ref": "svc-1",
                            "status": "executed",
                            "status_label": "executed",
                            "summary": "The probe hit and produced artifacts.",
                            "findings": ["The error response remains distinguishable."],
                            "metrics": {"traffic_series": [1, 2]},
                            "artifact_refs": ["workspace/finding.json"],
                        }
                    ],
                    "artifact_refs": ["workspace/finding.json"],
                },
            ),
        ],
        artifact_refs=[
            ArtifactRefPayload(
                artifact_id="svc-1",
                artifact_type="target_service",
                title="sandbox-crypto-service",
                path="workspace/service.py",
                summary="Target service pending remediation.",
                metadata={
                    "service_id": "svc-1",
                    "service_name": "sandbox-crypto-service",
                    "deployment_profile": "sandbox",
                    "service_interface": "api",
                    "attack_surface": ["encrypt", "decrypt"],
                    "service_version": "v1",
                    "runtime": "python",
                    "entrypoint": "workspace/service.py",
                    "status": "deployed",
                    "status_label": "deployed",
                },
            )
        ],
    )


def test_patch_planning_agent_returns_structured_patch_spec():
    agent = PatchPlanningAgent(llm=FakeStructuredLLM())

    patch_spec = agent.plan(build_projection(), run_id="run-patch-001")

    assert patch_spec.strategy == "error-boundary-hardening"
    assert patch_spec.summary
    assert patch_spec.rationale
    assert patch_spec.next_version == "v2"
    assert patch_spec.changed_artifacts == ["svc-1:python", "svc-1:c"]
    assert patch_spec.implementation_notes[:2] == [
        "Normalize decrypt input sanitization.",
        "Standardize error response formatting.",
    ]
    assert patch_spec.validation_steps[:2] == [
        "Redeploy the patched service version.",
        "Run regression probes around the decrypt boundary.",
    ]
    assert patch_spec.rollback_notes == ["Rollback to v1 if regression validation fails."]
    assert patch_spec.regression_focus[:2] == ["error leakage", "decrypt boundary"]


def test_patch_planning_agent_falls_back_without_llm():
    agent = PatchPlanningAgent()

    patch_spec = agent.plan(build_projection(), run_id="run-patch-002")

    assert patch_spec.strategy in {
        "hardening-and-validation",
        "error-boundary-hardening",
        "input-contract-hardening",
        "key-lifecycle-hardening",
    }
    assert patch_spec.summary
    assert patch_spec.rationale
    assert patch_spec.next_version == "v2"
    assert patch_spec.changed_artifacts == ["svc-1:python", "svc-1:c"]
    assert patch_spec.implementation_notes
    assert patch_spec.validation_steps
    assert patch_spec.rollback_notes
    assert patch_spec.regression_focus


def test_patch_planning_agent_accepts_summary_only_attack_artifacts():
    projection = build_projection()
    summary_only_cards = []
    for card in projection.cards:
        if card.card_type != "attack_artifact_summary":
            summary_only_cards.append(card)
            continue
        summary_only_cards.append(
            card.model_copy(
                update={
                    "payload": {
                        "attack_result_summaries": [
                            {
                                "attack_id": "attack-1",
                                "status": "executed",
                                "summary": "The probe completed and produced summary-level findings.",
                                "top_findings": ["The error response remains distinguishable."],
                                "metrics_summary": {"probe_count": 3, "latency_p95_ms": 12},
                                "artifact_summaries": [
                                    {
                                        "artifact_type": "attack_finding",
                                        "path": "workspace/finding.json",
                                        "summary": "Finding summary: the error response is still distinguishable.",
                                    }
                                ],
                            }
                        ],
                        "top_findings": ["The error response remains distinguishable."],
                        "artifact_refs": ["workspace/finding.json"],
                    }
                }
            )
        )
    summary_projection = projection.model_copy(update={"cards": summary_only_cards})

    agent = PatchPlanningAgent()
    patch_spec = agent.plan(summary_projection, run_id="run-patch-003")

    assert patch_spec.summary
    assert patch_spec.rationale
    assert patch_spec.validation_steps
    assert patch_spec.regression_focus


def test_patch_planning_agent_consumes_expert_gate_decision():
    projection = build_projection()
    expert_gate_card = MemoryCardPayload(
        card_id="card-expert-gate",
        card_type="expert_gate_decision",
        case_id="case-test",
        run_id="run-patch-004",
        round_id="expert-gate-r1",
        source_agent="expert_gate_agent",
        summary="Expert gate requires patching before formal regression validation.",
        payload={
            "decision_family": "patch_flow",
            "decision_family_label": "patch flow",
            "action": "patch_required_with_regression",
            "action_label": "patch with regression",
            "route_target": "patch_agent",
            "route_target_label": "patch planning window",
            "rationale": "Current attack evidence is strong enough to patch first and validate in regression.",
            "confidence": 0.88,
            "residual_risk_summary": "The decrypt path and error handling branch still keep meaningful residual risk.",
            "follow_up_actions": ["Enter patch planning", "Keep formal regression validation"],
            "decision": ExpertGateDecisionPayload(
                decision_id="expert-gate-1",
                target_service_ref="svc-1",
                decision_family="patch_flow",
                decision_family_label="patch flow",
                action="patch_required_with_regression",
                action_label="patch with regression",
                route_target="patch_agent",
                route_target_label="patch planning window",
                rationale="Current attack evidence is strong enough to patch first and validate in regression.",
                confidence=0.88,
                residual_risk_summary="The decrypt path and error handling branch still keep meaningful residual risk.",
                follow_up_actions=["Enter patch planning", "Keep formal regression validation"],
            ).model_dump(mode="json"),
        },
    )
    projection = projection.model_copy(update={"cards": [*projection.cards, expert_gate_card]})

    agent = PatchPlanningAgent()
    patch_spec = agent.plan(projection, run_id="run-patch-004")

    assert patch_spec.rationale
    assert "patch planning window" in " ".join(patch_spec.implementation_notes)
    assert any("regression" in item.lower() for item in patch_spec.validation_steps)
