from cipher_genius.api.schemas import (
    AttackResultPayload,
    PatchExecutionPayload,
    PatchValidationResultPayload,
    SandboxDispatchResultPayload,
    TargetServiceSpecPayload,
)
from cipher_genius.sandbox.execution_plane import ExecutionPlaneBuilder


def build_target_service() -> TargetServiceSpecPayload:
    return TargetServiceSpecPayload(
        service_id="svc-demo-001",
        artifact_id="artifact-demo-001",
        template_id="mock_crypto_http_v1",
        template_label="Mock Crypto HTTP",
        service_kind="crypto_api",
        attack_surface_kind="http-json",
        service_name="demo-service",
        deployment_profile="sandbox-http",
        service_interface="http-json",
        attack_surface=["encrypt", "health"],
        service_version="v1",
        runtime="python",
        entrypoint="/encrypt",
        supported_versions=["baseline", "patched", "regression"],
        status="ready",
        status_label="Ready",
    )


def build_dispatch(
    *,
    dispatch_id: str,
    round_id: str,
    stage: str,
    target_service_ref: str,
    status: str = "executed",
    status_label: str = "已执行",
    workspace: str = "",
    entrypoint: str = "",
    rollback_plan_path: str = "",
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
    metadata = {
        "workspace": workspace,
        "entrypoint": entrypoint,
    }
    if rollback_plan_path:
        metadata["rollback_plan_path"] = rollback_plan_path
    return SandboxDispatchResultPayload(
        dispatch_id=dispatch_id,
        run_id="run-demo-001",
        round_id=round_id,
        stage=stage,
        operation_kind=operation_kind,
        executor_backend="local-dispatcher",
        executor_kind="local_process",
        executor_label="本地受限进程",
        executor_readiness="active",
        executor_contract_version="v1",
        routing_mode="in_process",
        handoff_required=False,
        target_service_ref=target_service_ref,
        decision="approved",
        decision_label="已批准",
        status=status,
        status_label=status_label,
        requested_attack_count=1 if "attack" in stage else 0,
        approved_attack_count=1 if "attack" in stage else 0,
        requested_probe_count=3 if "attack" in stage else 0,
        approved_probe_count=3 if "attack" in stage else 0,
        capability_flags=["execute_probe"] if "attack" in stage else ["materialize_workspace"],
        backend_capability_flags=(
            ["collect_telemetry", "execute_probe", "emit_attack_artifacts"]
            if "attack" in stage
            else ["materialize_workspace", "prepare_runtime_manifest"]
        ),
        supported_operation_kinds=["deploy", "attack", "patch_apply", "rollback", "regression_replay"],
        artifact_refs=[value for value in [workspace, entrypoint, rollback_plan_path] if value],
        metadata=metadata,
    )


def test_execution_plane_builder_emits_unified_operation_contract():
    builder = ExecutionPlaneBuilder()
    target_service = build_target_service()
    baseline_deployment = build_dispatch(
        dispatch_id="dispatch-baseline-deploy",
        round_id="baseline",
        stage="target_deployer",
        target_service_ref=target_service.service_id,
        workspace="F:/sandbox/run-demo-001/baseline",
        entrypoint="/encrypt",
    )
    baseline_attack = build_dispatch(
        dispatch_id="dispatch-baseline-attack",
        round_id="baseline",
        stage="attack_executor",
        target_service_ref=target_service.service_id,
    )
    patch_apply = build_dispatch(
        dispatch_id="dispatch-regression-patch",
        round_id="regression",
        stage="patch_executor",
        target_service_ref=target_service.service_id,
        workspace="F:/sandbox/run-demo-001/regression",
    )
    regression_deployment = build_dispatch(
        dispatch_id="dispatch-regression-deploy",
        round_id="regression",
        stage="target_deployer",
        target_service_ref=target_service.service_id,
        workspace="F:/sandbox/run-demo-001/regression",
        entrypoint="/encrypt",
    )
    regression_attack = build_dispatch(
        dispatch_id="dispatch-regression-attack",
        round_id="regression",
        stage="attack_executor",
        target_service_ref=target_service.service_id,
    )
    rollback_dispatch = build_dispatch(
        dispatch_id="dispatch-regression-rollback",
        round_id="regression",
        stage="rollback_executor",
        target_service_ref=target_service.service_id,
        rollback_plan_path="F:/sandbox/run-demo-001/regression/rollback_plan.json",
    )
    patch_execution = PatchExecutionPayload(
        execution_id="patch-exec-001",
        patch_id="patch-001",
        execution_contract_version="v1",
        target_service_ref=target_service.service_id,
        target_service_version="v2",
        status="validated",
        status_label="已验证",
        summary="补丁已应用并完成回归验证。",
        workspace="F:/sandbox/run-demo-001/regression",
        patch_dispatch_id=patch_apply.dispatch_id,
        deployment_dispatch_id=regression_deployment.dispatch_id,
        regression_dispatch_id=regression_attack.dispatch_id,
        rollback_dispatch_id=rollback_dispatch.dispatch_id,
        applied_artifacts=["F:/sandbox/run-demo-001/regression/service_runtime.py"],
        patch_artifact_refs=[
            "F:/sandbox/run-demo-001/regression/patch_manifest.json",
            "F:/sandbox/run-demo-001/regression/patch_metadata.json",
        ],
        rollback_artifact_refs=[
            "F:/sandbox/run-demo-001/regression/rollback_plan.json",
            "F:/sandbox/run-demo-001/regression/rollback_manifest.json",
        ],
        regression_artifact_refs=[
            "F:/sandbox/run-demo-001/regression/finding.json",
        ],
        rollback_notes=["回滚到 v1 工件并重新部署。"],
        changed_artifact_summaries=[
            {
                "relative_name": "service_runtime.py",
                "patched_path": "F:/sandbox/run-demo-001/regression/service_runtime.py",
            }
        ],
        supporting_artifact_summaries=[
            {
                "relative_name": "validation.log",
                "path": "F:/sandbox/run-demo-001/regression/validation.log",
            }
        ],
        validation_results=[
            PatchValidationResultPayload(
                step_id="validation-1",
                step_kind="regression_probe",
                step="Run regression probes",
                status="passed",
                status_label="已通过",
                artifact_refs=["F:/sandbox/run-demo-001/regression/metrics.json"],
            )
        ],
        validation_summary={"passed": 1, "failed": 0},
        artifact_inventory={"changed_code_artifact_count": 1},
    )

    execution_run = builder.build(
        run_id="run-demo-001",
        case_id="case-demo-001",
        target_service=target_service,
        baseline_deployment=baseline_deployment,
        baseline_attack=baseline_attack,
        patch_apply_dispatch=patch_apply,
        regression_deployment=regression_deployment,
        regression_attack=regression_attack,
        rollback_dispatch=rollback_dispatch,
        attack_results=[
            AttackResultPayload(
                attack_id="attack-001",
                target_service_ref=target_service.service_id,
                status="executed",
                status_label="已执行",
                summary="基线攻击完成。",
                artifact_refs=["F:/sandbox/run-demo-001/baseline/finding.json"],
            )
        ],
        regression_attack_results=[
            AttackResultPayload(
                attack_id="attack-002",
                target_service_ref=target_service.service_id,
                status="executed",
                status_label="已执行",
                summary="回归回放完成。",
                artifact_refs=["F:/sandbox/run-demo-001/regression/finding.json"],
            )
        ],
        patch_execution=patch_execution,
    )

    assert execution_run.plan.contract_version == "v1"
    assert execution_run.summary["contract_version"] == "v1"
    assert execution_run.summary["operation_count"] >= 6
    assert execution_run.summary["operation_kind_counts"]["deploy"] == 2
    assert execution_run.summary["operation_kind_counts"]["attack"] == 1
    assert execution_run.summary["operation_kind_counts"]["patch_apply"] == 1
    assert execution_run.summary["operation_kind_counts"]["regression_replay"] == 1
    assert execution_run.summary["operation_kind_counts"]["rollback"] == 1
    assert "rollback" in execution_run.plan.operation_kinds
    assert "local_process" in execution_run.plan.executor_kinds
    assert "local-dispatcher" in execution_run.plan.executor_backends
    assert "local_process" in execution_run.plan.active_executor_kinds
    assert "container" in execution_run.plan.planned_executor_kinds
    assert execution_run.plan.capability_flags
    assert execution_run.plan.executor_matrix
    assert execution_run.summary["capability_flag_count"] >= 1
    assert execution_run.summary["executor_matrix_count"] >= 3
    assert execution_run.summary["active_executor_kind_count"] >= 1
    assert execution_run.summary["planned_executor_kind_count"] >= 1

    patch_apply_operation = next(
        item for item in execution_run.operations if item.operation_kind == "patch_apply"
    )
    assert patch_apply_operation.governance_mode == "dispatcher"
    assert patch_apply_operation.executor_kind == "local_process"
    assert patch_apply_operation.executor_label == "本地受限进程"
    assert patch_apply_operation.routing_mode == "in_process"
    assert f"patch:{patch_execution.patch_id}" in patch_apply_operation.input_refs
    assert f"dispatch:{patch_apply.dispatch_id}" in patch_apply_operation.output_refs
    assert "F:/sandbox/run-demo-001/regression/service_runtime.py" in patch_apply_operation.output_refs
    assert "F:/sandbox/run-demo-001/regression/patch_manifest.json" in patch_apply_operation.output_refs
    assert patch_apply_operation.metadata["validation_summary"]["passed"] == 1

    regression_replay = next(
        item for item in execution_run.operations if item.operation_kind == "regression_replay"
    )
    assert regression_replay.round_id == "regression"
    assert f"dispatch:{regression_deployment.dispatch_id}" in regression_replay.depends_on
    assert "F:/sandbox/run-demo-001/regression/finding.json" in regression_replay.output_refs

    rollback = next(item for item in execution_run.operations if item.operation_kind == "rollback")
    assert rollback.status == "executed"
    assert rollback.metadata["rollback_notes"] == ["回滚到 v1 工件并重新部署。"]
    assert "F:/sandbox/run-demo-001/regression/rollback_plan.json" in rollback.output_refs
    assert "F:/sandbox/run-demo-001/regression/rollback_manifest.json" in rollback.input_refs

    remote_worker_entry = next(
        item for item in execution_run.plan.executor_matrix if item.executor_kind == "remote_worker"
    )
    assert remote_worker_entry.selected_for_run is False
    assert remote_worker_entry.handoff_required is True
    assert remote_worker_entry.handoff_contract_version == "v1"
