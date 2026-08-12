"""Executor backend capability matrix for the sandbox execution plane."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_EXECUTOR_BACKEND_MATRIX: dict[str, dict[str, Any]] = {
    "local_process": {
        "executor_kind": "local_process",
        "executor_backend": "local-sandbox",
        "executor_label": "本地受限进程",
        "executor_readiness": "active",
        "routing_mode": "in_process",
        "supports_direct_execution": True,
        "handoff_required": False,
        "handoff_contract_version": "",
        "handoff_fields": [],
        "supported_operation_kinds": [
            "deploy",
            "attack",
            "patch_apply",
            "rollback",
            "regression_replay",
        ],
        "capability_flags": [
            "collect_telemetry",
            "copy_baseline_workspace",
            "emit_attack_artifacts",
            "emit_rollback_manifest",
            "execute_probe",
            "materialize_patch_artifacts",
            "materialize_rollback_plan",
            "materialize_workspace",
            "prepare_runtime_manifest",
        ],
    },
    "container": {
        "executor_kind": "container",
        "executor_backend": "container-sandbox",
        "executor_label": "容器执行器",
        "executor_readiness": "planned",
        "routing_mode": "container_handoff",
        "supports_direct_execution": False,
        "handoff_required": True,
        "handoff_contract_version": "v1",
        "handoff_fields": [
            "image_ref",
            "workspace_bundle_ref",
            "container_policy_ref",
            "receipt_ref",
        ],
        "supported_operation_kinds": [
            "deploy",
            "attack",
            "patch_apply",
            "rollback",
            "regression_replay",
        ],
        "capability_flags": [
            "collect_telemetry",
            "container_snapshot",
            "copy_baseline_workspace",
            "emit_attack_artifacts",
            "emit_rollback_manifest",
            "execute_probe",
            "materialize_patch_artifacts",
            "materialize_rollback_plan",
            "materialize_workspace",
            "network_namespace",
            "prepare_runtime_manifest",
            "process_isolation",
        ],
    },
    "remote_worker": {
        "executor_kind": "remote_worker",
        "executor_backend": "remote-executor",
        "executor_label": "远程工作节点",
        "executor_readiness": "planned",
        "routing_mode": "remote_handoff",
        "supports_direct_execution": False,
        "handoff_required": True,
        "handoff_contract_version": "v1",
        "handoff_fields": [
            "worker_pool",
            "job_id",
            "workspace_bundle_ref",
            "artifact_sync_refs",
            "receipt_ref",
        ],
        "supported_operation_kinds": [
            "deploy",
            "attack",
            "patch_apply",
            "rollback",
            "regression_replay",
        ],
        "capability_flags": [
            "artifact_sync",
            "collect_telemetry",
            "copy_baseline_workspace",
            "emit_attack_artifacts",
            "emit_execution_receipt",
            "emit_remote_receipt",
            "emit_rollback_manifest",
            "execute_probe",
            "materialize_patch_artifacts",
            "materialize_rollback_plan",
            "materialize_workspace",
            "prepare_runtime_manifest",
            "remote_job_dispatch",
            "remote_result_stream",
        ],
    },
}


def get_executor_backend_spec(executor_kind: str) -> dict[str, Any] | None:
    """Return a detached executor spec for the requested executor kind."""

    spec = _EXECUTOR_BACKEND_MATRIX.get(str(executor_kind or "").strip())
    if spec is None:
        return None
    return deepcopy(spec)


def get_executor_backend_matrix() -> list[dict[str, Any]]:
    """Return the full executor backend matrix."""

    return [deepcopy(item) for item in _EXECUTOR_BACKEND_MATRIX.values()]
