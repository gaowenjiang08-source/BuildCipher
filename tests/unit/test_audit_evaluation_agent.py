from cipher_genius.api.schemas import ContextProjectionPayload, MemoryCardPayload
from cipher_genius.core.audit_evaluation_agent import AuditEvaluationAgent


class FakeStructuredLLM:
    def generate_structured(self, prompt, schema, system_prompt=None, temperature=0.2, schema_name="structured_output"):
        return {
            "verdict": "reject",
            "reasons": ["关键风险尚未收敛，需要继续整改。"],
            "key_findings": ["decrypt 接口仍暴露可区分错误路径。"],
            "recommended_changes": ["统一错误处理并补齐 decrypt 输入边界校验。"],
        }


def build_projection() -> ContextProjectionPayload:
    return ContextProjectionPayload(
        agent_id="audit_agent",
        case_id="case-audit-test",
        run_id="run-audit-001",
        round_id="audit-r1",
        objective="在独立审计窗口内裁决 proposal-1 是否通过审计。",
        cards=[
            MemoryCardPayload(
                card_id="card-reflection-memory",
                card_type="reflection_memory",
                case_id="case-audit-test",
                run_id="run-audit-001",
                round_id="audit-r1",
                source_agent="case_memory_service",
                summary="项目级反思记忆",
                payload={
                    "latest_audit_focus": ["优先检查 decrypt 边界与错误处理收敛"],
                    "latest_prompt_changes": ["要求审计结果显式绑定证据与整改建议"],
                    "latest_residual_risks": ["错误路径可能泄露实现差异"],
                    "latest_reflection_summary": "上一轮修补后仍需关注 decrypt 错误处理一致性。",
                },
            ),
            MemoryCardPayload(
                card_id="card-audit-decision-input",
                card_type="audit_decision_input",
                case_id="case-audit-test",
                run_id="run-audit-001",
                round_id="audit-r1",
                source_agent="audit_engine",
                summary="审计决策输入",
                payload={
                    "round": 1,
                    "proposal_id": "proposal-1",
                    "proposal_name": "AES-GCM + Kyber",
                    "architecture_pattern": "hybrid-envelope",
                    "components": ["AES-256-GCM", "Kyber-768", "HKDF"],
                    "audit_input": {
                        "algorithm": "aes-gcm",
                        "mode": "gcm",
                        "key_size": 256,
                    },
                    "standards_checked": ["HIPAA", "NIST"],
                    "compliance_score": 78.0,
                    "risk_score": 72,
                    "critical_count": 1,
                    "quantum_required": True,
                    "quantum_ready": True,
                    "tool_findings": ["[高] decrypt 接口缺少边界约束", "日志中存在错误返回差异"],
                    "tool_recommendations": ["统一错误返回", "补齐 decrypt 输入校验"],
                    "vulnerability_report": {
                        "risk_score": 72,
                        "summary": {"critical": 1},
                    },
                    "compliance_report": {
                        "overall_compliance": 78.0,
                        "gaps": ["缺少对异常路径的合规说明"],
                    },
                    "quantum_eval": {"resistant": True},
                },
            ),
        ],
    )


def test_audit_evaluation_agent_returns_structured_round():
    agent = AuditEvaluationAgent(llm=FakeStructuredLLM())

    audit_round = agent.evaluate(build_projection(), run_id="run-audit-001")

    assert audit_round.proposal_id == "proposal-1"
    assert audit_round.verdict == "reject"
    assert audit_round.reasons
    assert audit_round.key_findings
    assert audit_round.recommended_changes
    assert audit_round.compliance_score == 78.0
    assert audit_round.risk_score == 72


def test_audit_evaluation_agent_falls_back_without_llm():
    agent = AuditEvaluationAgent()

    audit_round = agent.evaluate(build_projection(), run_id="run-audit-002")

    assert audit_round.verdict == "reject"
    assert any("严重漏洞" in item for item in audit_round.reasons)
    assert any("回退" in item or "内置审计裁决规则" in item for item in audit_round.reasons)
    assert audit_round.key_findings
    assert audit_round.recommended_changes
