from cipher_genius.api.schemas import (
    ArtifactRefPayload,
    ContextProjectionPayload,
    ExpertGateDecisionPayload,
    MemoryCardPayload,
    VulnerabilityVerdictPayload,
)
from cipher_genius.core.expert_gate_agent import ExpertGateAgent


class FakeStructuredLLM:
    def generate_structured(self, prompt, schema, system_prompt=None, temperature=0.2, schema_name="structured_output"):
        return {
            "action": "patch_required_with_regression",
            "action_label": "进入修补并强制回归",
            "rationale": "当前攻击证据已能稳定指向高风险问题，需要先进入修补并保留正式回归验证。",
            "confidence": 0.91,
            "residual_risk_summary": "decrypt 与错误处理分支仍有较高残余风险，需要补丁收口。",
            "follow_up_actions": ["进入补丁规划窗口", "保留正式回归攻击验证"],
        }


def build_projection() -> ContextProjectionPayload:
    verdict = VulnerabilityVerdictPayload(
        verdict_id="verdict-1",
        target_service_ref="svc-1",
        severity="high",
        severity_label="高",
        exploitability="moderate",
        exploitability_label="中等",
        summary="目标服务仍存在错误处理与接口边界问题。",
        affected_components=["decrypt", "error handler"],
        remediation_priority="high",
        remediation_priority_label="高",
        evidence_refs=["attack-1"],
    )
    return ContextProjectionPayload(
        agent_id="expert_gate_agent",
        case_id="case-test",
        run_id="run-gate-001",
        round_id="expert-gate-r1",
        objective="在独立窗口内完成漏洞放行裁决，并决定是否进入修补收口。",
        cards=[
            MemoryCardPayload(
                card_id="card-expert-gate-input",
                card_type="expert_gate_input",
                case_id="case-test",
                run_id="run-gate-001",
                round_id="expert-gate-r1",
                source_agent="vulnerability_agent",
                summary="专家闸门输入卡",
                payload={
                    "severity": "high",
                    "severity_label": "高",
                    "exploitability": "moderate",
                    "remediation_priority": "high",
                    "vulnerability_summary": verdict.summary,
                    "affected_components": verdict.affected_components,
                    "evidence_refs": verdict.evidence_refs,
                    "audit_reasons": ["审计认为错误处理边界不够稳定"],
                    "audit_recommended_changes": ["统一错误返回", "补齐 decrypt 输入校验"],
                    "top_findings": ["错误返回存在可区分差异", "decrypt 接口缺少边界约束"],
                    "attack_result_summaries": [
                        {
                            "attack_id": "attack-1",
                            "status": "executed",
                            "summary": "攻击命中并收集到 metrics 与 finding 摘要。",
                            "top_findings": ["错误返回存在可区分差异"],
                        }
                    ],
                    "artifact_refs": ["workspace/finding.json"],
                },
            ),
            MemoryCardPayload(
                card_id="card-verdict",
                card_type="vulnerability_verdict",
                case_id="case-test",
                run_id="run-gate-001",
                round_id="expert-gate-r1",
                source_agent="vulnerability_agent",
                summary=verdict.summary,
                payload={"verdict": verdict.model_dump(mode="json")},
            ),
            MemoryCardPayload(
                card_id="card-audit",
                card_type="audit_decision",
                case_id="case-test",
                run_id="run-gate-001",
                round_id="audit-r1",
                source_agent="audit_agent",
                summary="审计意见摘要",
                payload={
                    "proposal_id": "proposal-1",
                    "reasons": ["错误处理边界不够稳定"],
                    "recommended_changes": ["统一错误返回", "补齐 decrypt 输入校验"],
                },
            ),
            MemoryCardPayload(
                card_id="card-artifacts",
                card_type="attack_artifact_summary",
                case_id="case-test",
                run_id="run-gate-001",
                round_id="expert-gate-r1",
                source_agent="attack_planning_agent",
                summary="攻击工件摘要",
                payload={
                    "attack_results": [
                        {
                            "attack_id": "attack-1",
                            "target_service_ref": "svc-1",
                            "status": "executed",
                            "status_label": "已执行",
                            "summary": "攻击命中并收集到工件。",
                            "findings": ["错误返回存在可区分差异"],
                            "metrics": {"traffic_series": [1, 2]},
                            "artifact_refs": ["workspace/finding.json"],
                        }
                    ],
                    "top_findings": ["错误返回存在可区分差异", "decrypt 接口缺少边界约束"],
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
                summary="待专家闸门裁决的目标服务。",
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
                    "status_label": "已部署",
                },
            )
        ],
    )


def test_expert_gate_agent_returns_structured_decision():
    agent = ExpertGateAgent(llm=FakeStructuredLLM())

    decision = agent.decide(build_projection(), run_id="run-gate-001")

    assert isinstance(decision, ExpertGateDecisionPayload)
    assert decision.decision_family == "patch_flow"
    assert decision.decision_family_label
    assert decision.action == "patch_required_with_regression"
    assert decision.route_target == "patch_agent"
    assert decision.route_target_label
    assert decision.rationale
    assert decision.confidence == 0.91
    assert decision.residual_risk_summary
    assert decision.follow_up_actions[:2] == ["进入补丁规划窗口", "保留正式回归攻击验证"]


def test_expert_gate_agent_falls_back_without_llm():
    agent = ExpertGateAgent()

    decision = agent.decide(build_projection(), run_id="run-gate-002")

    assert decision.decision_family == "patch_flow"
    assert decision.route_target == "patch_agent"
    assert decision.action in {"patch_required", "patch_required_with_regression"}
    assert "回退" in decision.rationale or "规则" in decision.rationale
    assert decision.residual_risk_summary
    assert decision.follow_up_actions
