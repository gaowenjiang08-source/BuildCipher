from datetime import datetime, timezone

from cipher_genius.api.schemas import (
    AttackResultPayload,
    PatchSpecPayload,
    SandboxDispatchResultPayload,
    TargetServiceSpecPayload,
    VulnerabilityVerdictPayload,
)
from cipher_genius.core.artifact_summarizer import ArtifactSummarizer
from cipher_genius.core.langgraph_mas import LangGraphMASService


def _build_dispatch(
    *,
    dispatch_id: str,
    decision: str,
    status: str,
    status_label: str,
    stage: str = "attack_executor",
    artifact_refs: list[str] | None = None,
    metadata: dict | None = None,
) -> SandboxDispatchResultPayload:
    operation_kind = (
        "patch_apply"
        if stage == "patch_executor"
        else "rollback"
        if stage == "rollback_executor"
        else "attack"
        if "attack" in stage
        else "deploy"
    )
    return SandboxDispatchResultPayload(
        dispatch_id=dispatch_id,
        run_id="run-test-001",
        round_id="regression",
        stage=stage,
        operation_kind=operation_kind,
        executor_kind="local_process",
        target_service_ref="svc-1-reg",
        decision=decision,
        decision_label=decision,
        status=status,
        status_label=status_label,
        artifact_refs=artifact_refs or [],
        metadata={"runtime": "python", "requested_budget": {}, **(metadata or {})},
    )


def test_patch_execution_report_marks_validated_when_regression_executes():
    service = LangGraphMASService()
    patch_spec = PatchSpecPayload(
        patch_id="patch-001",
        target_service_ref="svc-1",
        strategy="error-boundary-hardening",
        summary="统一错误处理并补齐接口边界校验。",
        rationale="上一轮攻击发现 decrypt 路径与错误返回仍可区分。",
        changed_artifacts=["svc-1:python", "svc-1:c"],
        implementation_notes=["统一错误返回", "补齐 decrypt 输入校验"],
        validation_steps=["完成补丁版本重部署", "执行回归攻击验证"],
        rollback_notes=["若验证失败则回滚到 v1"],
        next_version="v2",
        regression_focus=["错误处理泄露", "decrypt 接口边界"],
    )
    regression_target = TargetServiceSpecPayload(
        service_id="svc-1-reg",
        artifact_id=".cache/sandbox/run-test-001/svc-1-reg",
        service_name="sandbox-crypto-service",
        service_version="v2",
        runtime="python",
        status="ready",
        status_label="待回归部署",
    )
    patch_artifact_summary = {
        "changed_artifact_summaries": [
            {
                "artifact_key": "python",
                "relative_name": "implementation.py",
                "summary": "implementation.py 已加固",
                "diff_preview": ["+ normalize_error()", "+ validate_decrypt_input()"],
            },
            {
                "artifact_key": "c",
                "relative_name": "implementation.c",
                "summary": "implementation.c 已加固",
                "diff_preview": ["+ secure_fail()", "- printf(error_detail)"],
            },
        ]
    }
    patch_dispatch = _build_dispatch(
        dispatch_id="dispatch-patch-1",
        decision="approved",
        status="executed",
        status_label="已执行",
        stage="patch_executor",
        artifact_refs=[
            "F:/sandbox/run-test-001/svc-1-reg/patch_manifest.json",
            "F:/sandbox/run-test-001/svc-1-reg/patch_metadata.json",
        ],
        metadata={
            "patch_manifest_path": "F:/sandbox/run-test-001/svc-1-reg/patch_manifest.json",
            "patch_metadata_path": "F:/sandbox/run-test-001/svc-1-reg/patch_metadata.json",
            "rollback_plan_path": "F:/sandbox/run-test-001/svc-1-reg/rollback_plan.json",
            "rollback_manifest_path": "F:/sandbox/run-test-001/svc-1-reg/rollback_manifest.json",
        },
    )
    deployment_dispatch = _build_dispatch(
        dispatch_id="dispatch-deploy-1",
        decision="approved",
        status="executed",
        status_label="已执行",
        stage="target_deployer",
        artifact_refs=["F:/sandbox/run-test-001/svc-1-reg/runtime_info.json"],
    )
    regression_dispatch = _build_dispatch(
        dispatch_id="dispatch-attack-1",
        decision="approved",
        status="executed",
        status_label="已执行",
        stage="attack_executor",
        artifact_refs=["F:/sandbox/run-test-001/svc-1-reg/metrics.json"],
    )
    rollback_dispatch = _build_dispatch(
        dispatch_id="dispatch-rollback-1",
        decision="approved",
        status="executed",
        status_label="已执行",
        stage="rollback_executor",
        artifact_refs=[
            "F:/sandbox/run-test-001/svc-1-reg/rollback_plan.json",
            "F:/sandbox/run-test-001/svc-1-reg/rollback_manifest.json",
        ],
        metadata={
            "rollback_plan_path": "F:/sandbox/run-test-001/svc-1-reg/rollback_plan.json",
            "rollback_manifest_path": "F:/sandbox/run-test-001/svc-1-reg/rollback_manifest.json",
        },
    )
    regression_results = [
        AttackResultPayload(
            attack_id="attack-1",
            target_service_ref="svc-1-reg",
            status="executed",
            status_label="已执行",
            summary="完成回归攻击验证。",
            findings=["错误处理泄露已收敛"],
            metrics={"traffic_series": [1, 2, 3]},
            artifact_refs=["trace.jsonl", "metrics.json"],
        )
    ]
    regression_verdict = VulnerabilityVerdictPayload(
        verdict_id="verdict-reg-1",
        target_service_ref="svc-1-reg",
        severity="low",
        severity_label="低",
        confidence=0.81,
        confidence_label="高",
        summary="残余风险已明显收敛。",
        top_findings=["错误处理泄露已收敛"],
        remediation_priority="medium",
        remediation_priority_label="中",
        affected_components=["decrypt_path"],
    )

    execution = service._build_patch_execution_report(
        run_id="run-test-001",
        patch_spec=patch_spec,
        regression_target_service=regression_target,
        patch_apply_dispatch=patch_dispatch,
        regression_deployment_dispatch=deployment_dispatch,
        regression_attack_dispatch=regression_dispatch,
        rollback_dispatch=rollback_dispatch,
        regression_attack_results=regression_results,
        regression_vulnerability_verdict=regression_verdict,
        patch_artifact_summary=patch_artifact_summary,
        workspace=".cache/sandbox/run-test-001/svc-1-reg",
    )

    assert execution.patch_id == "patch-001"
    assert execution.execution_contract_version == "v1"
    assert execution.target_service_ref == "svc-1-reg"
    assert execution.target_service_version == "v2"
    assert execution.status == "validated"
    assert execution.workspace.endswith("svc-1-reg")
    assert execution.patch_dispatch_id == "dispatch-patch-1"
    assert execution.rollback_dispatch_id == "dispatch-rollback-1"
    assert execution.applied_artifacts == ["implementation.py", "implementation.c"]
    assert execution.patch_artifact_refs
    assert execution.rollback_artifact_refs
    assert execution.regression_artifact_refs
    assert execution.validation_results[0].step_kind == "deployment_redeploy"
    assert execution.validation_results[0].status == "passed"
    assert execution.validation_results[1].step_kind == "regression_attack"
    assert execution.validation_results[1].status == "passed"
    assert any(item.step_kind == "artifact_review" for item in execution.validation_results)
    assert any(item.step_kind == "residual_risk_review" for item in execution.validation_results)
    assert execution.validation_summary["passed"] >= 4
    assert execution.validation_summary["all_passed"] is True
    assert execution.artifact_inventory["changed_code_artifact_count"] == 2
    assert execution.diff_preview[:2] == ["+ normalize_error()", "+ validate_decrypt_input()"]
    assert execution.metadata["patch_status"] == "executed"
    assert execution.metadata["regression_result_count"] == 1
    assert execution.metadata["rollback_status"] == "executed"
    assert execution.metadata["residual_severity"] == "low"
    assert execution.metadata["patch_artifact_ref_count"] >= 2
    assert isinstance(execution.applied_at, datetime)
    assert execution.applied_at.tzinfo == timezone.utc


def test_patch_execution_report_marks_validation_skipped_when_regression_not_executed():
    service = LangGraphMASService()
    patch_spec = PatchSpecPayload(
        patch_id="patch-002",
        target_service_ref="svc-2",
        strategy="key-lifecycle-hardening",
        summary="补齐密钥生命周期治理。",
        changed_artifacts=["svc-2:python"],
        validation_steps=["完成补丁版本重部署", "执行回归攻击验证"],
        rollback_notes=["若未通过则回滚到基线版本"],
        next_version="v2",
    )
    regression_target = TargetServiceSpecPayload(
        service_id="svc-2-reg",
        artifact_id=".cache/sandbox/run-test-002/svc-2-reg",
        service_name="sandbox-crypto-service",
        service_version="v2",
        runtime="python",
        status="ready",
        status_label="待回归部署",
    )
    patch_dispatch = _build_dispatch(
        dispatch_id="dispatch-patch-2",
        decision="approved",
        status="executed",
        status_label="已执行",
        stage="patch_executor",
        artifact_refs=["F:/sandbox/run-test-002/svc-2-reg/patch_manifest.json"],
    )
    deployment_dispatch = _build_dispatch(
        dispatch_id="dispatch-deploy-2",
        decision="approved",
        status="executed",
        status_label="已执行",
        stage="target_deployer",
    )
    regression_dispatch = _build_dispatch(
        dispatch_id="dispatch-attack-2",
        decision="handoff_to_vulnerability",
        status="skipped",
        status_label="已跳过",
        stage="attack_executor",
    )
    rollback_dispatch = _build_dispatch(
        dispatch_id="dispatch-rollback-2",
        decision="approved",
        status="executed",
        status_label="已执行",
        stage="rollback_executor",
        artifact_refs=["F:/sandbox/run-test-002/svc-2-reg/rollback_plan.json"],
    )
    regression_verdict = VulnerabilityVerdictPayload(
        verdict_id="verdict-reg-2",
        target_service_ref="svc-2-reg",
        severity="medium",
        severity_label="中",
        confidence=0.74,
        confidence_label="中高",
        summary="当前通过残余风险裁决完成收口，但未执行正式回归攻击。",
        top_findings=["需继续关注密钥生命周期治理"],
        remediation_priority="high",
        remediation_priority_label="高",
        affected_components=["key_lifecycle"],
    )

    execution = service._build_patch_execution_report(
        run_id="run-test-002",
        patch_spec=patch_spec,
        regression_target_service=regression_target,
        patch_apply_dispatch=patch_dispatch,
        regression_deployment_dispatch=deployment_dispatch,
        regression_attack_dispatch=regression_dispatch,
        rollback_dispatch=rollback_dispatch,
        regression_attack_results=[],
        regression_vulnerability_verdict=regression_verdict,
        patch_artifact_summary={
            "changed_artifact_summaries": [
                {
                    "artifact_key": "python",
                    "relative_name": "implementation.py",
                    "summary": "implementation.py 已调整",
                    "diff_preview": ["+ rotate_keys()"],
                }
            ],
            "artifact_inventory": {"changed_code_artifact_count": 1},
        },
        workspace=".cache/sandbox/run-test-002/svc-2-reg",
    )

    assert execution.status == "applied"
    assert execution.validation_results[0].step_kind == "deployment_redeploy"
    assert execution.validation_results[0].status == "passed"
    assert execution.validation_results[1].step_kind == "regression_attack"
    assert execution.validation_results[1].status == "skipped"
    assert any(item.step_kind == "residual_risk_review" for item in execution.validation_results)
    assert execution.validation_summary["skipped"] >= 1
    assert execution.metadata["regression_status"] == "skipped"
    assert execution.metadata["regression_action"] == "handoff_to_vulnerability"
    assert execution.metadata["rollback_status"] == "executed"


def test_patch_artifact_summary_collects_supporting_artifacts(tmp_path):
    baseline = tmp_path / "baseline"
    patched = tmp_path / "patched"
    baseline.mkdir()
    patched.mkdir()
    (baseline / "implementation.py").write_text("def encrypt(x):\n    return x\n", encoding="utf-8")
    (patched / "implementation.py").write_text(
        "def encrypt(x):\n    if x is None:\n        return ''\n    return x\n",
        encoding="utf-8",
    )
    (patched / "service_manifest.json").write_text(
        '{"service_id":"svc-test","runtime":"python","template_id":"mock"}',
        encoding="utf-8",
    )
    (patched / "runtime_info.json").write_text(
        '{"status":"running","port":18080,"health_url":"http://127.0.0.1:18080/health"}',
        encoding="utf-8",
    )
    (patched / "service_stdout.log").write_text("boot ok\nhealth ok\nencrypt ok\n", encoding="utf-8")

    summarizer = ArtifactSummarizer()
    summary = summarizer.summarize_patch_artifacts(
        patch_spec=PatchSpecPayload(
            patch_id="patch-test",
            target_service_ref="svc-test",
            strategy="input-contract-hardening",
            summary="补齐输入契约校验。",
            changed_artifacts=["svc-test:python"],
            next_version="v2",
        ),
        baseline_workspace=str(baseline),
        patched_workspace=str(patched),
    )

    assert summary["artifact_pipeline_version"] == "v2"
    assert summary["artifact_inventory"]["changed_code_artifact_count"] == 1
    assert summary["artifact_inventory"]["supporting_artifact_count"] >= 2
    assert any(
        item.get("artifact_role") == "deployment_manifest"
        for item in summary["supporting_artifact_summaries"]
    )
