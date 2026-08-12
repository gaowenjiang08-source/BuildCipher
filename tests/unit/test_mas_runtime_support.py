from cipher_genius.api.schemas import ContextProjectionPayload, MemoryCardPayload
from cipher_genius.core.mas_runtime_support import MASRuntimeSupport


def build_reflection_projection(*, payload: dict) -> ContextProjectionPayload:
    return ContextProjectionPayload(
        agent_id="audit_agent",
        case_id="case-runtime-001",
        run_id="run-runtime-001",
        round_id="audit-r1",
        objective="在独立窗口内消费项目级反思记忆并生成审计结论。",
        cards=[
            MemoryCardPayload(
                card_id="card-reflection-memory",
                card_type="reflection_memory",
                case_id="case-runtime-001",
                run_id="run-runtime-001",
                round_id="audit-r1",
                source_agent="case_memory_service",
                summary="项目级反思记忆",
                payload=payload,
            )
        ],
    )


def test_build_runtime_audit_guidance_falls_back_to_prompt_changes():
    service = MASRuntimeSupport()
    projection = build_reflection_projection(
        payload={
            "latest_prompt_changes": [
                "audit 需要围绕错误处理与接口边界做定向回归核查。",
                "交付摘要中继续保留证据引用与残余风险说明。",
            ],
            "latest_reflection_summary": "上一轮反思指出需要强化接口契约说明。",
        }
    )

    guidance = service._build_runtime_audit_guidance(projection)

    assert guidance["audit_focus"] == [
        "audit 需要围绕错误处理与接口边界做定向回归核查。",
        "交付摘要中继续保留证据引用与残余风险说明。",
    ]
    assert guidance["reflection_summary"] == "上一轮反思指出需要强化接口契约说明。"


def test_augment_audit_results_with_runtime_guidance_marks_project_reflection():
    service = MASRuntimeSupport()

    reasons, key_findings, recommended_changes = service._augment_audit_results_with_runtime_guidance(
        reasons=["整体合规得分过低：50.0%。"],
        key_findings=["[高] Missing Authentication"],
        recommended_changes=["补齐输入校验"],
        audit_guidance={
            "audit_focus": ["核查输入边界与错误处理是否一致。"],
            "residual_risks": ["密钥治理仍需继续验证。"],
            "prompt_changes": ["交付摘要中继续保留证据引用与残余风险说明。"],
            "reflection_summary": "上一轮反思指出需要强化接口契约说明。",
        },
    )

    assert any("项目级反思" in item for item in reasons)
    assert any("项目级反思" in item for item in key_findings)
    assert any("项目级反思" in item for item in recommended_changes)
