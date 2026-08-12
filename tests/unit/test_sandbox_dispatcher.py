import pytest

from cipher_genius.api.schemas import (
    AttackSpecPayload,
    EngineerReportPayload,
    PatchSpecPayload,
    SandboxPolicyPayload,
    TargetServiceSpecPayload,
)
from cipher_genius.sandbox.dispatcher import (
    LocalSandboxDispatcher,
    SandboxDispatchExecutionError,
)
from cipher_genius.sandbox.local_runtime import LocalSandboxRuntime


def build_target_service() -> TargetServiceSpecPayload:
    return TargetServiceSpecPayload(
        service_id="svc-demo-001",
        artifact_id="artifact-demo-001",
        template_id="mock_crypto_http_v1",
        template_label="模拟加密 HTTP 服务",
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
        planner_skill_hints=["attack_surface_analysis"],
        planner_retrieval_hints=["http-json crypto api misuse"],
        status="ready",
        status_label="已部署描述",
    )


def build_engineer(*, python_suffix: str = "") -> EngineerReportPayload:
    return EngineerReportPayload(
        sandbox_backend="local-sandbox",
        python_passed=True,
        corrected_python=(
            "def encrypt(value):\n"
            "    return value[::-1]\n"
            f"{python_suffix}"
        ),
    )


def build_patch_spec(target_service: TargetServiceSpecPayload) -> PatchSpecPayload:
    return PatchSpecPayload(
        patch_id="patch-001",
        target_service_ref=target_service.service_id,
        strategy="input-contract-hardening",
        summary="加固输入契约与错误处理。",
        rationale="避免错误处理路径泄露接口边界。",
        changed_artifacts=[f"{target_service.service_id}:python"],
        implementation_notes=["统一错误返回", "补齐输入校验"],
        validation_steps=["完成补丁物化", "执行回归验证"],
        rollback_notes=["恢复 baseline workspace 并重新部署 v1"],
        next_version="v2",
    )


def test_dispatcher_plans_approved_attack_execution():
    dispatcher = LocalSandboxDispatcher(runtime=LocalSandboxRuntime())
    target_service = build_target_service()
    attack_specs = [
        AttackSpecPayload(
            attack_id="attack-001",
            target_service_ref=target_service.service_id,
            attack_family="oracle_probe",
            objective="验证错误处理与接口边界。",
            attack_surface=["encrypt"],
            telemetry_fields=["latency_p95"],
            budget={"timeout_s": 60, "memory_mb": 256, "probe_count_hint": 3},
        )
    ]

    request, result = dispatcher.plan_attack_execution(
        run_id="run-demo-001",
        round_id="baseline",
        target_service=target_service,
        attack_specs=attack_specs,
    )

    assert request.signature
    assert result.decision == "approved"
    assert result.status == "planned"
    assert result.approved_attack_count == 1
    assert result.approved_probe_count == 3
    assert result.rejection_reasons == []
    assert result.failure_category == ""
    assert result.failure_items == []
    assert request.operation_kind == "attack"
    assert result.operation_kind == "attack"
    assert result.executor_kind == "local_process"
    assert "collect_telemetry" in result.capability_flags
    assert [item.event_kind for item in result.audit_trail] == ["requested", "signed", "approved"]


def test_dispatcher_blocks_disallowed_attack_family():
    dispatcher = LocalSandboxDispatcher(
        runtime=LocalSandboxRuntime(),
        policy=SandboxPolicyPayload(
            attack_family_whitelist=["oracle_probe"],
            max_attack_tasks=2,
            max_probe_count=6,
            max_timeout_seconds=120,
            max_memory_mb=512,
        ),
    )
    target_service = build_target_service()
    attack_specs = [
        AttackSpecPayload(
            attack_id="attack-002",
            target_service_ref=target_service.service_id,
            attack_family="regression_check",
            objective="执行未授权攻击族。",
            attack_surface=["encrypt"],
            telemetry_fields=["latency_p95"],
            budget={"timeout_s": 60, "memory_mb": 128, "probe_count_hint": 2},
        )
    ]

    _, result = dispatcher.plan_attack_execution(
        run_id="run-demo-002",
        round_id="regression",
        target_service=target_service,
        attack_specs=attack_specs,
    )

    assert result.decision == "blocked"
    assert result.status == "blocked"
    assert "attack_family_not_allowed:regression_check" in result.rejection_reasons
    assert result.failure_category == "policy_rejection"
    assert result.failure_category_label == "策略拒绝"
    assert result.failure_items[0].reason_label == "存在未授权的攻击族"
    assert result.failure_items[0].details["attack_families"] == ["regression_check"]
    assert [item.event_kind for item in result.audit_trail] == ["requested", "signed", "blocked"]


def test_dispatcher_plans_target_deployment_with_signature():
    dispatcher = LocalSandboxDispatcher(runtime=LocalSandboxRuntime())
    target_service = build_target_service()

    request, result = dispatcher.plan_target_deployment(
        run_id="run-demo-003",
        round_id="baseline",
        target_service=target_service,
    )

    assert request.signature
    assert result.decision == "approved"
    assert result.target_service_ref == target_service.service_id
    assert result.audit_trail[-1].event_kind == "approved"


def test_dispatcher_target_service_keeps_template_metadata():
    dispatcher = LocalSandboxDispatcher(runtime=LocalSandboxRuntime())
    target_service = build_target_service()

    request, result = dispatcher.plan_target_deployment(
        run_id="run-demo-004",
        round_id="baseline",
        target_service=target_service,
    )

    assert target_service.template_id == "mock_crypto_http_v1"
    assert target_service.planner_skill_hints == ["attack_surface_analysis"]
    assert target_service.supported_versions == ["baseline", "patched", "regression"]
    assert request.target_service_ref == target_service.service_id
    assert request.runtime == target_service.runtime
    assert result.target_service_ref == target_service.service_id


def test_dispatcher_executes_patch_application_and_persists_artifacts(tmp_path):
    runtime = LocalSandboxRuntime(root_dir=tmp_path / "sandbox")
    dispatcher = LocalSandboxDispatcher(runtime=runtime)
    baseline_service = build_target_service()
    engineer = build_engineer()
    deployed_service, _, _ = dispatcher.dispatch_target_deployment(
        run_id="run-demo-005",
        round_id="baseline",
        target_service=baseline_service,
        engineer=engineer,
    )
    patch_spec = build_patch_spec(deployed_service)
    regression_service = deployed_service.model_copy(
        update={
            "service_id": f"{deployed_service.service_id}-reg",
            "service_version": "v2",
            "status": "ready",
            "status_label": "待回归部署",
        }
    )

    patched_service, patch_application, dispatch = dispatcher.dispatch_patch_application(
        run_id="run-demo-005",
        round_id="regression",
        baseline_target_service=deployed_service,
        target_service=regression_service,
        engineer=build_engineer(python_suffix="\nPATCH_MARKER = 'applied'\n"),
        patch_spec=patch_spec,
    )

    assert patched_service.artifact_id.endswith(f"{patched_service.service_id}")
    assert patch_application.patch_manifest_path.exists()
    assert patch_application.patch_metadata_path.exists()
    assert patch_application.rollback_plan_path.exists()
    assert patch_application.rollback_manifest_path.exists()
    assert dispatch.stage == "patch_executor"
    assert dispatch.operation_kind == "patch_apply"
    assert dispatch.status == "executed"
    assert dispatch.metadata["patch_id"] == patch_spec.patch_id
    assert dispatch.metadata["applied_artifact_paths"]
    assert any(ref.endswith("patch_manifest.json") for ref in dispatch.artifact_refs)
    assert any(ref.endswith("rollback_manifest.json") for ref in dispatch.artifact_refs)
    assert dispatch.audit_trail[-1].event_kind == "executed"


def test_dispatcher_executes_rollback_plan_dispatch(tmp_path):
    runtime = LocalSandboxRuntime(root_dir=tmp_path / "sandbox")
    dispatcher = LocalSandboxDispatcher(runtime=runtime)
    baseline_service = build_target_service()
    engineer = build_engineer()
    deployed_service, _, _ = dispatcher.dispatch_target_deployment(
        run_id="run-demo-006",
        round_id="baseline",
        target_service=baseline_service,
        engineer=engineer,
    )
    patch_spec = build_patch_spec(deployed_service)
    regression_service = deployed_service.model_copy(
        update={
            "service_id": f"{deployed_service.service_id}-reg",
            "service_version": "v2",
            "artifact_id": str((tmp_path / "sandbox" / "run-demo-006" / f"{deployed_service.service_id}-reg")),
        }
    )
    patched_service, _, _ = dispatcher.dispatch_patch_application(
        run_id="run-demo-006",
        round_id="regression",
        baseline_target_service=deployed_service,
        target_service=regression_service,
        engineer=build_engineer(python_suffix="\nPATCH_MARKER = 'rollbackable'\n"),
        patch_spec=patch_spec,
    )

    rollback_result, dispatch = dispatcher.dispatch_rollback(
        run_id="run-demo-006",
        round_id="regression",
        target_service=patched_service,
        patch_spec=patch_spec,
        baseline_workspace=deployed_service.artifact_id,
    )

    assert rollback_result.rollback_plan_path.exists()
    assert rollback_result.rollback_manifest_path.exists()
    assert dispatch.stage == "rollback_executor"
    assert dispatch.operation_kind == "rollback"
    assert dispatch.status == "executed"
    assert dispatch.metadata["rollback_plan_path"].endswith("rollback_plan.json")
    assert any(ref.endswith("rollback_manifest.json") for ref in dispatch.artifact_refs)
    assert dispatch.audit_trail[-1].event_kind == "executed"


def test_dispatcher_blocks_patch_apply_without_declared_changed_artifacts():
    dispatcher = LocalSandboxDispatcher(runtime=LocalSandboxRuntime())
    target_service = build_target_service()
    patch_spec = PatchSpecPayload(
        patch_id="patch-empty",
        target_service_ref=target_service.service_id,
        strategy="noop",
        summary="no-op",
        changed_artifacts=[],
        rollback_notes=["restore baseline"],
        next_version="v2",
    )

    _, result = dispatcher.plan_patch_application(
        run_id="run-demo-007",
        round_id="regression",
        target_service=target_service,
        patch_spec=patch_spec,
    )

    assert result.decision == "blocked"
    assert result.failure_category == "invalid_request"
    assert result.failure_items[0].reason_code == "patch_artifact_count_missing"
    assert result.failure_items[0].scope == "payload"


def test_dispatcher_blocks_rollback_without_notes():
    dispatcher = LocalSandboxDispatcher(runtime=LocalSandboxRuntime())
    target_service = build_target_service()
    patch_spec = PatchSpecPayload(
        patch_id="patch-no-rollback",
        target_service_ref=target_service.service_id,
        strategy="input-contract-hardening",
        summary="missing rollback notes",
        changed_artifacts=["svc-demo-001:python"],
        rollback_notes=[],
        next_version="v2",
    )

    _, result = dispatcher.plan_rollback(
        run_id="run-demo-008",
        round_id="regression",
        target_service=target_service,
        patch_spec=patch_spec,
    )

    assert result.decision == "blocked"
    assert result.failure_category == "invalid_request"
    assert result.failure_items[0].reason_code == "rollback_notes_missing"
    assert result.failure_items[0].scope == "payload"


def test_dispatcher_wraps_runtime_failure_with_structured_dispatch_result(monkeypatch):
    runtime = LocalSandboxRuntime()
    dispatcher = LocalSandboxDispatcher(runtime=runtime)
    target_service = build_target_service()

    def fail_deploy(*args, **kwargs):
        raise RuntimeError("bootstrap failed")

    monkeypatch.setattr(runtime, "deploy_target_service", fail_deploy)

    with pytest.raises(SandboxDispatchExecutionError) as exc_info:
        dispatcher.dispatch_target_deployment(
            run_id="run-demo-009",
            round_id="baseline",
            target_service=target_service,
            engineer=build_engineer(),
        )

    dispatch_result = exc_info.value.dispatch_result
    assert dispatch_result.status == "failed"
    assert dispatch_result.failure_category == "runtime_execution_failed"
    assert dispatch_result.failure_items[-1].reason_code == "runtime_execution_failed:deploy"
    assert dispatch_result.failure_items[-1].scope == "runtime"
    assert dispatch_result.audit_trail[-1].event_kind == "failed"
    assert dispatch_result.metadata["runtime_error_type"] == "RuntimeError"


def test_dispatcher_wraps_patch_runtime_failure_with_structured_dispatch_result():
    runtime = LocalSandboxRuntime()
    dispatcher = LocalSandboxDispatcher(runtime=runtime)
    target_service = build_target_service()
    patch_spec = build_patch_spec(target_service)
    regression_service = target_service.model_copy(
        update={
            "service_id": f"{target_service.service_id}-reg",
            "service_version": "v2",
        }
    )

    with pytest.raises(SandboxDispatchExecutionError) as exc_info:
        dispatcher.dispatch_patch_application(
            run_id="run-demo-010",
            round_id="regression",
            baseline_target_service=target_service,
            target_service=regression_service,
            engineer=build_engineer(),
            patch_spec=patch_spec,
        )

    dispatch_result = exc_info.value.dispatch_result
    assert dispatch_result.operation_kind == "patch_apply"
    assert dispatch_result.status == "failed"
    assert dispatch_result.failure_items[-1].reason_code == "runtime_execution_failed:patch_apply"
    assert dispatch_result.failure_items[-1].details["error_type"] == "FileNotFoundError"
    assert dispatch_result.audit_trail[-1].event_kind == "failed"


def test_dispatcher_marks_remote_worker_as_handoff_required():
    dispatcher = LocalSandboxDispatcher(runtime=LocalSandboxRuntime())
    target_service = build_target_service()
    attack_specs = [
        AttackSpecPayload(
            attack_id="attack-remote-001",
            target_service_ref=target_service.service_id,
            attack_family="oracle_probe",
            objective="simulate remote handoff",
            attack_surface=["encrypt"],
            telemetry_fields=["latency_p95"],
            budget={"timeout_s": 60, "memory_mb": 128, "probe_count_hint": 2},
        )
    ]

    request, result = dispatcher.plan_attack_execution(
        run_id="run-demo-011",
        round_id="baseline",
        target_service=target_service,
        attack_specs=attack_specs,
        executor_kind="remote_worker",
    )

    assert request.executor_kind == "remote_worker"
    assert request.handoff_required is True
    assert request.routing_mode == "remote_handoff"
    assert result.decision == "blocked"
    assert result.handoff_required is True
    assert result.handoff_contract_version == "v1"
    assert result.handoff_ref == "handoff:dispatch-run-demo-baseline-attack:remote_worker"
    assert request.governance_mode == "dispatcher"
    assert request.handoff_request is not None
    assert request.handoff_request.dispatch_id == request.dispatch_id
    assert request.handoff_request.dispatch_key == request.signature
    assert request.handoff_request.executor_kind == "remote_worker"
    assert request.handoff_request.operation_kind == "attack"
    assert request.handoff_request.callback_contract["result_field"] == "handoff_receipt"
    assert request.artifact_sync_manifest is not None
    assert request.artifact_sync_manifest.direction == "bidirectional"
    assert "trace" in request.artifact_sync_manifest.required_artifact_kinds
    assert result.handoff_request is not None
    assert result.artifact_sync_manifest is not None
    assert result.handoff_receipt is not None
    assert result.handoff_receipt.receipt_status == "handoff_required"
    assert result.handoff_trace is not None
    assert result.handoff_trace.trace_status == "handoff_required"
    assert result.handoff_trace.receipt_ref == result.handoff_receipt.receipt_id
    assert result.failure_items[0].reason_code == "executor_handoff_required:remote_worker"
    assert result.failure_items[0].scope == "executor"
    assert "job_id" in result.failure_items[0].details["handoff_fields"]


def test_dispatcher_builds_container_handoff_contract_for_deployment():
    dispatcher = LocalSandboxDispatcher(runtime=LocalSandboxRuntime())
    target_service = build_target_service()

    request, result = dispatcher.plan_target_deployment(
        run_id="run-demo-012",
        round_id="baseline",
        target_service=target_service,
        executor_kind="container",
    )

    assert request.executor_kind == "container"
    assert request.handoff_required is True
    assert request.handoff_request is not None
    assert request.handoff_request.workspace_ref.startswith("workspace:run-demo-012:")
    assert request.handoff_request.operation_kind == "deploy"
    assert request.handoff_request.artifact_sync_contract["sync_ref"] == "sync:dispatch-run-demo-baseline-deploy"
    assert request.artifact_sync_manifest is not None
    assert "service_manifest" in request.artifact_sync_manifest.required_artifact_kinds
    assert result.handoff_ref == "handoff:dispatch-run-demo-baseline-deploy:container"
    assert result.handoff_trace is not None
    assert result.handoff_trace.adapter_stage == "dispatcher_plan"
    assert result.failure_items[0].reason_code == "executor_handoff_required:container"
