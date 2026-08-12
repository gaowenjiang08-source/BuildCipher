from cipher_genius.api.schemas import (
    ArtifactRefPayload,
    ContextProjectionPayload,
    MemoryCardPayload,
)
from cipher_genius.core.attack_planning_agent import AttackPlanningAgent


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
            "decision": {
                "action": "execute",
                "action_label": "执行攻击",
                "rationale": "优先验证密钥误用与错误处理边界。",
                "selected_attack_family": "oracle_probe",
                "expected_outcome": "收集可复现的漏洞证据与流量指标。",
                "confidence": 0.88,
                "stop_conditions": ["达到预算上限后立即停止"],
                "next_step": "dispatch_attack",
            },
            "attack_specs": [
                {
                    "attack_family": "oracle_probe",
                    "objective": "验证错误返回是否泄露加密状态差异。",
                    "attack_surface": ["encrypt", "decrypt"],
                    "expected_artifacts": ["finding.json"],
                    "telemetry_fields": ["cpu", "latency_p95"],
                    "budget": {"timeout_s": 90, "cpu_cores": 1, "memory_mb": 256},
                }
            ],
        }


class FakeHandoffLLM:
    def generate_structured(
        self,
        prompt,
        schema,
        system_prompt=None,
        temperature=0.2,
        schema_name="structured_output",
    ):
        return {
            "decision": {
                "action": "handoff_to_vulnerability",
                "action_label": "转交漏洞评估",
                "rationale": "当前证据已经足以支撑漏洞评估，无需继续扩大攻击面。",
                "selected_attack_family": "oracle_probe",
                "expected_outcome": "将现有发现转为结构化漏洞裁决。",
                "confidence": 0.81,
                "stop_conditions": ["保持当前沙盒预算，不再新增探测任务"],
                "next_step": "handoff_to_vulnerability",
            },
            "attack_specs": [],
        }


class CapturePromptLLM:
    def __init__(self):
        self.last_prompt = ""

    def generate_structured(
        self,
        prompt,
        schema,
        system_prompt=None,
        temperature=0.2,
        schema_name="structured_output",
    ):
        self.last_prompt = prompt
        return {
            "decision": {
                "action": "execute",
                "action_label": "执行攻击",
                "rationale": "依据模板提示优先检查错误处理与密钥轮换边界。",
                "selected_attack_family": "oracle_probe",
                "expected_outcome": "收集模板相关误用证据。",
                "confidence": 0.72,
                "stop_conditions": ["达到预算上限后立即停止"],
                "next_step": "dispatch_attack",
            },
            "attack_specs": [
                {
                    "attack_family": "oracle_probe",
                    "objective": "围绕模板提示验证错误处理和轮换接口。",
                    "attack_surface": ["encrypt", "key_rotation"],
                    "expected_artifacts": ["finding.json"],
                    "telemetry_fields": ["latency_p95"],
                    "budget": {"timeout_s": 60, "cpu_cores": 1, "memory_mb": 256},
                }
            ],
        }


def build_projection() -> ContextProjectionPayload:
    return ContextProjectionPayload(
        agent_id="attack_planning_agent",
        case_id="case-test",
        run_id="run-attack-001",
        round_id="attack-plan-r1",
        objective="在独立窗口内生成受预算和边界约束的攻击规划。",
        cards=[
            MemoryCardPayload(
                card_id="card-risk",
                card_type="attack_plan_input",
                case_id="case-test",
                run_id="run-attack-001",
                source_agent="audit_agent",
                summary="最新审计摘要",
                payload={
                    "proposal_id": "proposal-1",
                    "risk_score": 76,
                    "compliance_score": 0.91,
                    "key_findings": ["错误处理差异可能暴露内部状态"],
                },
            )
        ],
        artifact_refs=[
            ArtifactRefPayload(
                artifact_id="svc-1",
                artifact_type="target_service",
                title="sandbox-crypto-service",
                path="workspace/service.py",
                summary="待攻击目标服务",
                metadata={
                    "service_id": "svc-1",
                    "template_id": "mock_crypto_http_v1",
                    "template_label": "模拟加密 HTTP 服务",
                    "service_kind": "crypto_api",
                    "attack_surface_kind": "http-json",
                    "service_name": "sandbox-crypto-service",
                    "deployment_profile": "sandbox",
                    "service_interface": "api",
                    "attack_surface": ["encrypt", "decrypt"],
                    "service_version": "v1",
                    "runtime": "python",
                    "entrypoint": "workspace/service.py",
                    "supported_versions": ["baseline", "patched", "regression"],
                    "planner_skill_hints": [
                        "attack_surface_analysis",
                        "crypto_deployment_review",
                    ],
                    "planner_retrieval_hints": [
                        "http-json crypto api misuse",
                        "error handling leakage",
                    ],
                    "deployment_manifest": {
                        "entrypoint": "/encrypt",
                        "bootstrap_script": "service_runtime.py",
                        "healthcheck": "/health",
                        "workspace_dir": ".cache/sandbox/run-attack-001/svc-1",
                        "artifact_dir": ".cache/sandbox/run-attack-001/svc-1/artifacts",
                    },
                    "runtime_profile": {
                        "timeout_seconds": 120,
                        "memory_budget_mb": 256,
                        "probe_budget": 64,
                        "traffic_sampling_interval_ms": 250,
                        "cleanup_policy": "stop_and_archive",
                    },
                    "status": "deployed",
                    "status_label": "已部署",
                },
            )
        ],
    )


def test_attack_planning_agent_returns_structured_decision():
    agent = AttackPlanningAgent(llm=FakeStructuredLLM())

    decision, attack_specs = agent.plan(build_projection(), run_id="run-attack-001")

    assert decision.action == "execute"
    assert decision.selected_attack_family == "oracle_probe"
    assert decision.confidence == 0.88
    assert attack_specs
    assert attack_specs[0].attack_family == "oracle_probe"
    assert attack_specs[0].target_service_ref == "svc-1"
    assert attack_specs[0].budget["timeout_s"] == 90


def test_attack_planning_agent_restores_template_context_and_exposes_planner_hints():
    capture_llm = CapturePromptLLM()
    agent = AttackPlanningAgent(llm=capture_llm)

    decision, attack_specs = agent.plan(build_projection(), run_id="run-attack-001-hints")

    assert decision.action == "execute"
    assert attack_specs[0].target_service_ref == "svc-1"
    assert '"template_id": "mock_crypto_http_v1"' in capture_llm.last_prompt
    assert '"planner_skill_hints": [' in capture_llm.last_prompt
    assert "attack_surface_analysis" in capture_llm.last_prompt
    assert "error handling leakage" in capture_llm.last_prompt
    assert '"probe_budget": 64' in capture_llm.last_prompt


def test_attack_planning_agent_falls_back_without_llm():
    agent = AttackPlanningAgent()

    decision, attack_specs = agent.plan(build_projection(), run_id="run-attack-002")

    assert decision.action == "execute"
    assert decision.selected_attack_family == "oracle_probe"
    assert "回退" in decision.rationale or "内置攻击规划" in decision.rationale
    assert len(attack_specs) == 1
    assert attack_specs[0].attack_family == "oracle_probe"
    assert attack_specs[0].budget["memory_mb"] == 512


def test_attack_planning_agent_builds_regression_replan_without_llm():
    agent = AttackPlanningAgent()
    projection = build_projection().model_copy(
        update={
            "round_id": "attack-plan-r2",
            "cards": [
                MemoryCardPayload(
                    card_id="card-replan",
                    card_type="attack_replan_input",
                    case_id="case-test",
                    run_id="run-attack-003",
                    source_agent="patch_agent",
                    summary="补丁后的回归重规划输入",
                    payload={
                        "planning_mode": "regression",
                        "regression_focus": ["错误处理回归", "密钥治理回归"],
                        "prior_findings": ["错误返回存在可区分差异"],
                        "prior_attack_count": 1,
                        "risk_score": 24,
                    },
                )
            ],
            "artifact_refs": [
                ArtifactRefPayload(
                    artifact_id="svc-1-reg",
                    artifact_type="regression_target_service",
                    title="sandbox-crypto-service-reg",
                    path="workspace/service_reg.py",
                    summary="补丁后的目标服务",
                    metadata={
                        "service_id": "svc-1-reg",
                        "service_name": "sandbox-crypto-service-reg",
                        "deployment_profile": "sandbox",
                        "service_interface": "api",
                        "attack_surface": ["encrypt", "decrypt"],
                        "service_version": "v2",
                        "runtime": "python",
                        "entrypoint": "workspace/service_reg.py",
                        "status": "deployed",
                        "status_label": "已部署",
                    },
                )
            ],
        }
    )

    decision, attack_specs = agent.plan(projection, run_id="run-attack-003-reg")

    assert decision.action == "replan"
    assert decision.selected_attack_family == "regression_check"
    assert len(attack_specs) == 2
    assert attack_specs[0].attack_family == "regression_check"
    assert attack_specs[0].status_label == "待回归"


def test_attack_planning_agent_allows_handoff_without_attack_specs():
    agent = AttackPlanningAgent(llm=FakeHandoffLLM())

    decision, attack_specs = agent.plan(build_projection(), run_id="run-attack-004")

    assert decision.action == "handoff_to_vulnerability"
    assert decision.action_label == "转交漏洞评估"
    assert decision.next_step == "handoff_to_vulnerability"
    assert attack_specs == []
