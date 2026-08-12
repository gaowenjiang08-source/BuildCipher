from cipher_genius.api.schemas import ArtifactRefPayload, ContextProjectionPayload, MemoryCardPayload
from cipher_genius.core.reflection_agent import ReflectionAgent


class FakeStructuredLLM:
    def generate_structured(self, prompt, schema, system_prompt=None, temperature=0.2, schema_name="structured_output"):
        return {
            "reflection_summary": "下一轮 generation 应明确 decrypt 接口的输入契约、错误掩码和密钥治理边界。",
            "regression_summary": "补丁版本已经完成回归攻击，但仍需持续验证 decrypt 与错误处理路径是否完全收敛。",
            "prompt_changes": [
                "generation 需要显式解释 implementation.py 中错误处理分支的修补理由。",
                "audit 需要把 decrypt 接口边界和残余风险证据作为高优先级核查项。",
            ],
            "audit_focus": ["decrypt 接口边界", "错误处理一致性"],
            "residual_risks": ["decrypt", "error handler"],
            "changed_artifacts": ["implementation.py"],
        }


def build_projection() -> ContextProjectionPayload:
    return ContextProjectionPayload(
        agent_id="reflection_agent",
        case_id="case-test",
        run_id="run-reflect-001",
        round_id="reflection-r1",
        objective="在独立窗口内沉淀下一轮生成、审计与修补的优化卡片。",
        cards=[
            MemoryCardPayload(
                card_id="card-reflection-input",
                card_type="reflection_summary",
                case_id="case-test",
                run_id="run-reflect-001",
                round_id="reflection-r1",
                source_agent="patch_agent",
                summary="修补与回归后的反思摘要输入",
                payload={
                    "patch_id": "patch-1",
                    "next_version": "v2",
                    "regression_severity": "中",
                    "patch_spec": {
                        "patch_id": "patch-1",
                        "target_service_ref": "svc-1-reg",
                        "strategy": "error-boundary-hardening",
                        "summary": "统一错误返回并补齐 decrypt 输入边界校验。",
                        "rationale": "需要先收口 decrypt 路径与错误处理分支，再评估残余风险。",
                        "changed_artifacts": ["svc-1-reg:python"],
                        "implementation_notes": ["统一 decrypt 输入清洗。", "收口错误返回格式。"],
                        "validation_steps": ["执行补丁版本重部署。", "围绕 decrypt 路径执行回归探测。"],
                        "rollback_notes": ["若回归失败则回滚到 v1。"],
                        "next_version": "v2",
                        "regression_focus": ["decrypt 接口边界", "错误处理一致性"],
                    },
                    "regression_vulnerability_verdict": {
                        "severity": "medium",
                        "severity_label": "中",
                        "affected_components": ["decrypt", "error handler"],
                        "evidence_refs": ["attack-reg-1"],
                    },
                    "regression_attack_result_summaries": [
                        {
                            "attack_id": "attack-reg-1",
                            "status": "executed",
                            "summary": "回归攻击已生成 finding / metrics 摘要。",
                            "top_findings": ["decrypt 仍存在边界探测面"],
                        }
                    ],
                },
            ),
            MemoryCardPayload(
                card_id="card-regression-verdict",
                card_type="regression_verdict_input",
                case_id="case-test",
                run_id="run-reflect-001",
                round_id="reflection-r1",
                source_agent="vulnerability_agent",
                summary="补丁回归后的残余风险输入",
                payload={
                    "severity": "medium",
                    "severity_label": "中",
                    "affected_components": ["decrypt", "error handler"],
                },
            ),
            MemoryCardPayload(
                card_id="card-patch-artifacts",
                card_type="patch_artifact_summary",
                case_id="case-test",
                run_id="run-reflect-001",
                round_id="reflection-r1",
                source_agent="patch_agent",
                summary="补丁工件摘要",
                payload={
                    "patch_id": "patch-1",
                    "strategy": "error-boundary-hardening",
                    "summary": "implementation.py 增加输入清洗与统一错误返回。",
                    "next_version": "v2",
                    "regression_focus": ["decrypt 接口边界", "错误处理一致性"],
                    "changed_artifact_summaries": [
                        {
                            "artifact_key": "python",
                            "artifact_type": "patch_python",
                            "relative_name": "implementation.py",
                            "before_line_count": 10,
                            "after_line_count": 14,
                            "line_delta": 4,
                            "added_line_count": 5,
                            "removed_line_count": 1,
                            "diff_preview": [
                                "+     masked = payload.strip()",
                                "+     if not masked:",
                                "-     return payload",
                            ],
                            "summary": "implementation.py 行数 10 -> 14，增量预览 3 行。",
                        }
                    ],
                },
            ),
        ],
        artifact_refs=[
            ArtifactRefPayload(
                artifact_id="svc-1-reg",
                artifact_type="regression_target_service",
                title="sandbox-crypto-service",
                path="workspace/implementation.py",
                summary="补丁后的目标服务",
                metadata={
                    "service_id": "svc-1-reg",
                    "service_name": "sandbox-crypto-service",
                    "deployment_profile": "sandbox",
                    "service_interface": "api",
                    "attack_surface": ["encrypt", "decrypt"],
                    "service_version": "v2",
                    "runtime": "python",
                    "entrypoint": "workspace/implementation.py",
                    "status": "deployed",
                    "status_label": "已部署",
                },
            )
        ],
    )


def test_reflection_agent_returns_structured_cards():
    agent = ReflectionAgent(llm=FakeStructuredLLM())

    cards = agent.reflect(build_projection(), run_id="run-reflect-001", fallback_workspace="workspace")

    assert len(cards) == 2
    assert cards[0]["card_type"] == "reflection"
    assert cards[0]["patch_strategy"] == "error-boundary-hardening"
    assert cards[0]["changed_artifacts"] == ["implementation.py"]
    assert cards[0]["prompt_changes"]
    assert cards[1]["card_type"] == "regression_summary"
    assert cards[1]["workspace"] == "workspace"
    assert cards[1]["residual_risks"] == ["decrypt", "error handler"]


def test_reflection_agent_falls_back_without_llm():
    agent = ReflectionAgent()

    cards = agent.reflect(build_projection(), run_id="run-reflect-002", fallback_workspace="workspace")

    assert len(cards) == 2
    assert cards[0]["card_type"] == "reflection"
    assert "回退" in cards[0]["summary"] or "内置反思策略" in cards[0]["summary"]
    assert cards[0]["prompt_changes"]
    assert cards[1]["card_type"] == "regression_summary"
    assert cards[1]["workspace"] == "workspace"
    assert cards[1]["validation_focus"]
