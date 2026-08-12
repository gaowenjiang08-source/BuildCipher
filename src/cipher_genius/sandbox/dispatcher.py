"""Dispatcher layer for bounded sandbox execution.

The dispatcher sits between orchestration and the concrete runtime. Its job is
to make approval rules explicit before we enter the local sandbox runtime.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cipher_genius.api.schemas import (
    AttackResultPayload,
    AttackSpecPayload,
    EngineerReportPayload,
    ExecutorArtifactSyncManifestPayload,
    ExecutorHandoffReceiptPayload,
    ExecutorHandoffRequestPayload,
    ExecutorHandoffTracePayload,
    PatchSpecPayload,
    SandboxAuditEventPayload,
    SandboxDispatchRequestPayload,
    SandboxDispatchResultPayload,
    SandboxFailurePayload,
    SandboxPolicyPayload,
    TargetServiceSpecPayload,
)
from cipher_genius.models.scheme import CryptographicScheme
from cipher_genius.sandbox.executor_matrix import get_executor_backend_spec
from cipher_genius.sandbox.local_runtime import (
    LocalDeploymentResult,
    LocalPatchApplicationResult,
    LocalRollbackPlanResult,
    LocalSandboxRuntime,
)


class SandboxDispatchExecutionError(RuntimeError):
    """Runtime execution failed after dispatcher approval."""

    def __init__(
        self,
        *,
        message: str,
        dispatch_result: SandboxDispatchResultPayload,
        cause: Exception,
    ):
        super().__init__(message)
        self.dispatch_result = dispatch_result
        self.cause = cause


class LocalSandboxDispatcher:
    """Dispatcher that validates bounded local execution before runtime calls."""

    def __init__(
        self,
        runtime: LocalSandboxRuntime,
        policy: SandboxPolicyPayload | None = None,
    ):
        self.runtime = runtime
        self.policy = policy or SandboxPolicyPayload()

    def plan_target_deployment(
        self,
        *,
        run_id: str,
        round_id: str,
        target_service: TargetServiceSpecPayload,
        executor_kind: str = "local_process",
    ) -> tuple[SandboxDispatchRequestPayload, SandboxDispatchResultPayload]:
        request = self._build_request(
            dispatch_id=f"dispatch-{run_id[:8]}-{round_id}-deploy",
            run_id=run_id,
            round_id=round_id,
            stage="target_deployer",
            operation_kind="deploy",
            executor_kind=executor_kind,
            target_service_ref=target_service.service_id,
            runtime=target_service.runtime,
            required_capabilities=["materialize_workspace", "prepare_runtime_manifest"],
            artifact_refs=self._filter_refs([target_service.artifact_id]),
            requested_budget={"timeout_s": 30, "memory_mb": 128},
        )
        return self._finalize_plan(request)

    def dispatch_target_deployment(
        self,
        *,
        run_id: str,
        round_id: str,
        target_service: TargetServiceSpecPayload,
        engineer: EngineerReportPayload,
        final_scheme: CryptographicScheme | None = None,
        executor_kind: str = "local_process",
    ) -> tuple[TargetServiceSpecPayload, LocalDeploymentResult, SandboxDispatchResultPayload]:
        _, dispatch = self.plan_target_deployment(
            run_id=run_id,
            round_id=round_id,
            target_service=target_service,
            executor_kind=executor_kind,
        )
        self._ensure_approved(dispatch)
        try:
            deployed_service, deployment = self.runtime.deploy_target_service(
                run_id=run_id,
                target_service=target_service,
                engineer=engineer,
                final_scheme=final_scheme,
            )
        except Exception as exc:
            raise self._build_execution_error(dispatch=dispatch, exc=exc) from exc
        executed = self._append_audit_event(
            dispatch.model_copy(
                update={
                    "status": "executed",
                    "status_label": "已执行",
                    "artifact_refs": self._filter_refs(
                        [
                            str(deployment.manifest_path).replace("\\", "/"),
                            str(deployment.runtime_info_path or "").replace("\\", "/"),
                            str(deployment.log_path or "").replace("\\", "/"),
                            str(deployment.service_script_path or "").replace("\\", "/"),
                            str(deployment.python_path or "").replace("\\", "/"),
                            str(deployment.c_path or "").replace("\\", "/"),
                            str(deployment.pseudocode_path or "").replace("\\", "/"),
                        ]
                    ),
                    "metadata": {
                        **dispatch.metadata,
                        "workspace": str(deployment.workspace).replace("\\", "/"),
                        "entrypoint": deployed_service.entrypoint,
                    },
                }
            ),
            event_kind="executed",
            event_kind_label="已执行",
            summary="部署任务已通过 dispatcher 审批，并完成本地执行。",
            metadata={
                "workspace": str(deployment.workspace).replace("\\", "/"),
                "entrypoint": deployed_service.entrypoint,
            },
        )
        return deployed_service, deployment, executed

    def plan_attack_execution(
        self,
        *,
        run_id: str,
        round_id: str,
        target_service: TargetServiceSpecPayload,
        attack_specs: list[AttackSpecPayload],
        executor_kind: str = "local_process",
    ) -> tuple[SandboxDispatchRequestPayload, SandboxDispatchResultPayload]:
        request = self._build_request(
            dispatch_id=f"dispatch-{run_id[:8]}-{round_id}-attack",
            run_id=run_id,
            round_id=round_id,
            stage="attack_executor",
            operation_kind="attack",
            executor_kind=executor_kind,
            target_service_ref=target_service.service_id,
            runtime=target_service.runtime,
            required_capabilities=["execute_probe", "collect_telemetry", "emit_attack_artifacts"],
            artifact_refs=self._filter_refs(
                [target_service.artifact_id, *[spec.attack_id for spec in attack_specs]]
            ),
            attack_families=[spec.attack_family for spec in attack_specs],
            requested_attack_count=len(attack_specs),
            requested_probe_count=self._estimate_probe_count(attack_specs),
            requested_budget=self._aggregate_attack_budget(attack_specs),
        )
        return self._finalize_plan(request)

    def plan_patch_application(
        self,
        *,
        run_id: str,
        round_id: str,
        target_service: TargetServiceSpecPayload,
        patch_spec: PatchSpecPayload,
        executor_kind: str = "local_process",
    ) -> tuple[SandboxDispatchRequestPayload, SandboxDispatchResultPayload]:
        request = self._build_request(
            dispatch_id=f"dispatch-{run_id[:8]}-{round_id}-patch",
            run_id=run_id,
            round_id=round_id,
            stage="patch_executor",
            operation_kind="patch_apply",
            executor_kind=executor_kind,
            target_service_ref=target_service.service_id,
            runtime=target_service.runtime,
            required_capabilities=["copy_baseline_workspace", "materialize_patch_artifacts"],
            artifact_refs=self._filter_refs(
                [target_service.artifact_id, *list(patch_spec.changed_artifacts or [])]
            ),
            requested_budget={
                "timeout_s": 30,
                "memory_mb": 128,
                "patch_artifact_count": len(patch_spec.changed_artifacts),
            },
        )
        return self._finalize_plan(request)

    def dispatch_patch_application(
        self,
        *,
        run_id: str,
        round_id: str,
        baseline_target_service: TargetServiceSpecPayload,
        target_service: TargetServiceSpecPayload,
        engineer: EngineerReportPayload,
        patch_spec: PatchSpecPayload,
        final_scheme: CryptographicScheme | None = None,
        executor_kind: str = "local_process",
    ) -> tuple[TargetServiceSpecPayload, LocalPatchApplicationResult, SandboxDispatchResultPayload]:
        _, dispatch = self.plan_patch_application(
            run_id=run_id,
            round_id=round_id,
            target_service=target_service,
            patch_spec=patch_spec,
            executor_kind=executor_kind,
        )
        self._ensure_approved(dispatch)
        try:
            patched_service, patch_application = self.runtime.apply_patch_to_service(
                run_id=run_id,
                baseline_target_service=baseline_target_service,
                patched_target_service=target_service,
                engineer=engineer,
                patch_spec=patch_spec,
                final_scheme=final_scheme,
            )
        except Exception as exc:
            raise self._build_execution_error(dispatch=dispatch, exc=exc) from exc
        executed = self._append_audit_event(
            dispatch.model_copy(
                update={
                    "status": "executed",
                    "status_label": "已执行",
                    "artifact_refs": self._filter_refs(
                        [
                            str(patch_application.patch_manifest_path).replace("\\", "/"),
                            str(patch_application.patch_metadata_path).replace("\\", "/"),
                            str(patch_application.rollback_plan_path).replace("\\", "/"),
                            str(patch_application.rollback_manifest_path).replace("\\", "/"),
                            *[
                                str(path).replace("\\", "/")
                                for path in patch_application.applied_artifact_paths
                            ],
                            *[
                                str(path).replace("\\", "/")
                                for path in patch_application.supporting_artifact_paths
                            ],
                        ]
                    ),
                    "metadata": {
                        **dispatch.metadata,
                        "workspace": str(patch_application.workspace).replace("\\", "/"),
                        "baseline_workspace": str(patch_application.baseline_workspace).replace(
                            "\\",
                            "/",
                        ),
                        "patch_id": patch_spec.patch_id,
                        "patch_strategy": patch_spec.strategy,
                        "patch_manifest_path": str(patch_application.patch_manifest_path).replace(
                            "\\",
                            "/",
                        ),
                        "patch_metadata_path": str(patch_application.patch_metadata_path).replace(
                            "\\",
                            "/",
                        ),
                        "rollback_plan_path": str(patch_application.rollback_plan_path).replace(
                            "\\",
                            "/",
                        ),
                        "rollback_manifest_path": str(
                            patch_application.rollback_manifest_path
                        ).replace("\\", "/"),
                        "applied_artifact_paths": [
                            str(path).replace("\\", "/")
                            for path in patch_application.applied_artifact_paths
                        ],
                    },
                }
            ),
            event_kind="executed",
            event_kind_label="已执行",
            summary="补丁应用请求已通过 dispatcher 审批，并完成本地补丁工作区物化。",
            metadata={
                "workspace": str(patch_application.workspace).replace("\\", "/"),
                "patch_id": patch_spec.patch_id,
                "applied_artifact_count": len(patch_application.applied_artifact_paths),
            },
        )
        return patched_service, patch_application, executed

    def plan_rollback(
        self,
        *,
        run_id: str,
        round_id: str,
        target_service: TargetServiceSpecPayload,
        patch_spec: PatchSpecPayload,
        executor_kind: str = "local_process",
    ) -> tuple[SandboxDispatchRequestPayload, SandboxDispatchResultPayload]:
        request = self._build_request(
            dispatch_id=f"dispatch-{run_id[:8]}-{round_id}-rollback",
            run_id=run_id,
            round_id=round_id,
            stage="rollback_executor",
            operation_kind="rollback",
            executor_kind=executor_kind,
            target_service_ref=target_service.service_id,
            runtime=target_service.runtime,
            required_capabilities=["materialize_rollback_plan", "emit_rollback_manifest"],
            artifact_refs=self._filter_refs(
                [target_service.artifact_id, *list(patch_spec.changed_artifacts or [])]
            ),
            requested_budget={
                "timeout_s": 15,
                "memory_mb": 64,
                "rollback_note_count": len(patch_spec.rollback_notes),
            },
        )
        return self._finalize_plan(request)

    def dispatch_rollback(
        self,
        *,
        run_id: str,
        round_id: str,
        target_service: TargetServiceSpecPayload,
        patch_spec: PatchSpecPayload,
        baseline_workspace: str | None = None,
        executor_kind: str = "local_process",
    ) -> tuple[LocalRollbackPlanResult, SandboxDispatchResultPayload]:
        _, dispatch = self.plan_rollback(
            run_id=run_id,
            round_id=round_id,
            target_service=target_service,
            patch_spec=patch_spec,
            executor_kind=executor_kind,
        )
        self._ensure_approved(dispatch)
        try:
            rollback_result = self.runtime.materialize_rollback_plan(
                target_service=target_service,
                patch_spec=patch_spec,
                baseline_workspace=baseline_workspace,
            )
        except Exception as exc:
            raise self._build_execution_error(dispatch=dispatch, exc=exc) from exc
        executed = self._append_audit_event(
            dispatch.model_copy(
                update={
                    "status": "executed",
                    "status_label": "已执行",
                    "artifact_refs": self._filter_refs(
                        [
                            str(rollback_result.rollback_plan_path).replace("\\", "/"),
                            str(rollback_result.rollback_manifest_path).replace("\\", "/"),
                        ]
                    ),
                    "metadata": {
                        **dispatch.metadata,
                        "workspace": str(rollback_result.workspace).replace("\\", "/"),
                        "patch_id": patch_spec.patch_id,
                        "rollback_plan_path": str(rollback_result.rollback_plan_path).replace(
                            "\\",
                            "/",
                        ),
                        "rollback_manifest_path": str(
                            rollback_result.rollback_manifest_path
                        ).replace("\\", "/"),
                    },
                }
            ),
            event_kind="executed",
            event_kind_label="已执行",
            summary="回滚预案请求已通过 dispatcher 审批，并完成本地回滚计划落盘。",
            metadata={
                "workspace": str(rollback_result.workspace).replace("\\", "/"),
                "patch_id": patch_spec.patch_id,
                "rollback_plan_path": str(rollback_result.rollback_plan_path).replace(
                    "\\",
                    "/",
                ),
            },
        )
        return rollback_result, executed

    def dispatch_construction_rollback_execution(
        self,
        *,
        run_id: str,
        round_id: str,
        target_service: TargetServiceSpecPayload,
        patch_spec: PatchSpecPayload,
        executor_kind: str = "local_process",
    ) -> tuple[Path, SandboxDispatchResultPayload]:
        """Execute and verify a previously materialized BuildTrust profile rollback."""

        _, dispatch = self.plan_rollback(
            run_id=run_id,
            round_id=round_id,
            target_service=target_service,
            patch_spec=patch_spec,
            executor_kind=executor_kind,
        )
        self._ensure_approved(dispatch)
        try:
            execution_path = self.runtime.execute_construction_profile_rollback(
                target_service=target_service,
                patch_spec=patch_spec,
            )
            execution_payload = json.loads(execution_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise self._build_execution_error(dispatch=dispatch, exc=exc) from exc
        profile_path = Path(target_service.artifact_id) / "construction_security_profile.json"
        executed = self._append_audit_event(
            dispatch.model_copy(
                update={
                    "status": "executed",
                    "status_label": "已执行",
                    "artifact_refs": self._filter_refs(
                        [
                            str(execution_path).replace("\\", "/"),
                            str(profile_path).replace("\\", "/"),
                        ]
                    ),
                    "metadata": {
                        **dispatch.metadata,
                        "rollback_mode": "construction_profile_restore",
                        "rollback_execution_path": str(execution_path).replace("\\", "/"),
                        "verified": bool(execution_payload["verified"]),
                    },
                }
            ),
            event_kind="executed",
            event_kind_label="已执行",
            summary="建筑控制配置已恢复到补丁前快照，并完成摘要一致性验证。",
            metadata={
                "patch_id": patch_spec.patch_id,
                "verified": bool(execution_payload["verified"]),
            },
        )
        return execution_path, executed

    def dispatch_attack_execution(
        self,
        *,
        run_id: str,
        round_id: str,
        target_service: TargetServiceSpecPayload,
        attack_specs: list[AttackSpecPayload],
        vulnerability_report: dict[str, Any],
        telemetry_callback: Callable[[dict[str, Any]], None] | None = None,
        executor_kind: str = "local_process",
    ) -> tuple[list[AttackResultPayload], SandboxDispatchResultPayload]:
        _, dispatch = self.plan_attack_execution(
            run_id=run_id,
            round_id=round_id,
            target_service=target_service,
            attack_specs=attack_specs,
            executor_kind=executor_kind,
        )
        self._ensure_approved(dispatch)
        try:
            results = self.runtime.execute_attack_specs(
                target_service=target_service,
                attack_specs=attack_specs,
                vulnerability_report=vulnerability_report,
                telemetry_callback=telemetry_callback,
            )
        except Exception as exc:
            raise self._build_execution_error(dispatch=dispatch, exc=exc) from exc
        executed = self._append_audit_event(
            dispatch.model_copy(
                update={
                    "status": "executed",
                    "status_label": "已执行",
                    "artifact_refs": self._filter_refs(
                        [
                            artifact_ref
                            for result in results
                            for artifact_ref in result.artifact_refs
                        ]
                    ),
                    "metadata": {
                        **dispatch.metadata,
                        "result_count": len(results),
                        "artifact_refs": [
                            artifact_ref
                            for result in results
                            for artifact_ref in result.artifact_refs
                        ],
                    },
                }
            ),
            event_kind="executed",
            event_kind_label="已执行",
            summary="攻击任务已通过 dispatcher 审批并完成本地执行。",
            metadata={
                "result_count": len(results),
                "artifact_ref_count": sum(len(result.artifact_refs) for result in results),
            },
        )
        return results, executed

    def _finalize_plan(
        self,
        request: SandboxDispatchRequestPayload,
    ) -> tuple[SandboxDispatchRequestPayload, SandboxDispatchResultPayload]:
        executor_spec = get_executor_backend_spec(request.executor_kind) or {}
        signature = self._sign_request(request)
        handoff_ref = self._build_handoff_ref(request) if request.handoff_required else ""
        signed_request = request.model_copy(
            update={
                "signature": signature,
                "handoff_ref": handoff_ref,
            }
        )
        if signed_request.handoff_required:
            artifact_sync_manifest = self._build_handoff_artifact_sync_manifest(signed_request)
            handoff_request = self._build_handoff_request(
                signed_request,
                artifact_sync_manifest=artifact_sync_manifest,
            )
            signed_request = signed_request.model_copy(
                update={
                    "handoff_request": handoff_request,
                    "artifact_sync_manifest": artifact_sync_manifest,
                }
            )
        failure_items = self._collect_failure_items(signed_request)
        rejection_reasons = [item.reason_code for item in failure_items]
        handoff_receipt = self._build_handoff_receipt(
            signed_request,
            failure_items=failure_items,
        )
        handoff_trace = self._build_handoff_trace(
            signed_request,
            failure_items=failure_items,
            receipt=handoff_receipt,
        )
        audit_trail = [
            self._build_audit_event(
                request=signed_request,
                event_kind="requested",
                event_kind_label="已请求",
                summary="dispatcher 已收到执行请求。",
                metadata={
                    "requested_attack_count": signed_request.requested_attack_count,
                    "requested_probe_count": signed_request.requested_probe_count,
                },
            ),
            self._build_audit_event(
                request=signed_request,
                event_kind="signed",
                event_kind_label="已签名",
                summary="dispatcher 已生成调度签名。",
                metadata={"signature": signature},
            ),
        ]
        if failure_items:
            audit_trail.append(
                self._build_audit_event(
                    request=signed_request,
                    event_kind="blocked",
                    event_kind_label="已阻断",
                    summary="dispatcher 因策略校验未通过而阻断执行。",
                    metadata={"reason_codes": rejection_reasons},
                )
            )
        else:
            audit_trail.append(
                self._build_audit_event(
                    request=signed_request,
                    event_kind="approved",
                    event_kind_label="已批准",
                    summary="dispatcher 已批准执行请求。",
                    metadata={
                        "approved_attack_count": signed_request.requested_attack_count,
                        "approved_probe_count": signed_request.requested_probe_count,
                    },
                )
            )

        result = SandboxDispatchResultPayload(
            dispatch_id=signed_request.dispatch_id,
            run_id=signed_request.run_id,
            round_id=signed_request.round_id,
            stage=signed_request.stage,
            operation_kind=signed_request.operation_kind,
            executor_backend=signed_request.executor_backend,
            executor_kind=signed_request.executor_kind,
            executor_label=signed_request.executor_label,
            executor_readiness=signed_request.executor_readiness,
            executor_contract_version=signed_request.executor_contract_version,
            routing_mode=signed_request.routing_mode,
            governance_mode=signed_request.governance_mode,
            handoff_required=signed_request.handoff_required,
            handoff_contract_version=signed_request.handoff_contract_version,
            handoff_fields=list(signed_request.handoff_fields),
            handoff_ref=signed_request.handoff_ref,
            handoff_request=signed_request.handoff_request,
            artifact_sync_manifest=signed_request.artifact_sync_manifest,
            handoff_receipt=handoff_receipt,
            handoff_trace=handoff_trace,
            target_service_ref=signed_request.target_service_ref,
            decision="approved" if not rejection_reasons else "blocked",
            decision_label="已批准" if not rejection_reasons else "已阻断",
            status="planned" if not rejection_reasons else "blocked",
            status_label="待执行" if not rejection_reasons else "已阻断",
            requested_attack_count=signed_request.requested_attack_count,
            approved_attack_count=(
                signed_request.requested_attack_count if not rejection_reasons else 0
            ),
            requested_probe_count=signed_request.requested_probe_count,
            approved_probe_count=(
                signed_request.requested_probe_count if not rejection_reasons else 0
            ),
            rejection_reasons=rejection_reasons,
            failure_category=(failure_items[0].category if failure_items else ""),
            failure_category_label=(failure_items[0].category_label if failure_items else ""),
            failure_items=failure_items,
            signature=signature,
            policy=self.policy,
            audit_trail=audit_trail,
            capability_flags=list(signed_request.required_capabilities),
            backend_capability_flags=list(executor_spec.get("capability_flags", [])),
            supported_operation_kinds=list(executor_spec.get("supported_operation_kinds", [])),
            artifact_refs=list(signed_request.artifact_refs),
            metadata={
                "runtime": signed_request.runtime,
                "attack_families": list(signed_request.attack_families),
                "requested_budget": dict(signed_request.requested_budget),
            },
        )
        return signed_request, result

    def _collect_failure_items(
        self,
        request: SandboxDispatchRequestPayload,
    ) -> list[SandboxFailurePayload]:
        failures: list[SandboxFailurePayload] = []
        executor_spec = get_executor_backend_spec(request.executor_kind)
        if executor_spec is None:
            failures.append(
                SandboxFailurePayload(
                    reason_code=f"executor_kind_unknown:{request.executor_kind or 'unknown'}",
                    reason_label="未识别的执行器类型",
                    category="invalid_request",
                    category_label="请求不合法",
                    scope="executor",
                    scope_label="执行器",
                    details={"executor_kind": request.executor_kind},
                )
            )
        else:
            supported_operation_kinds = set(executor_spec.get("supported_operation_kinds", []))
            if request.operation_kind and request.operation_kind not in supported_operation_kinds:
                failures.append(
                    SandboxFailurePayload(
                        reason_code=(
                            f"executor_operation_not_supported:{request.executor_kind}:"
                            f"{request.operation_kind}"
                        ),
                        reason_label="执行器不支持当前操作类型",
                        category="executor_unavailable",
                        category_label="执行器不可用",
                        scope="executor",
                        scope_label="执行器",
                        details={
                            "executor_kind": request.executor_kind,
                            "operation_kind": request.operation_kind,
                            "supported_operation_kinds": sorted(supported_operation_kinds),
                        },
                    )
                )
            missing_capabilities = sorted(
                set(request.required_capabilities)
                - set(executor_spec.get("capability_flags", []))
            )
            if missing_capabilities:
                failures.append(
                    SandboxFailurePayload(
                        reason_code=(
                            "executor_capability_missing:"
                            f"{request.executor_kind}:{','.join(missing_capabilities)}"
                        ),
                        reason_label="执行器缺少所需能力",
                        category="executor_capability_missing",
                        category_label="执行器能力不足",
                        scope="executor",
                        scope_label="执行器",
                        details={
                            "executor_kind": request.executor_kind,
                            "missing_capabilities": missing_capabilities,
                        },
                    )
                )
            if executor_spec.get("handoff_required"):
                failures.append(
                    SandboxFailurePayload(
                        reason_code=f"executor_handoff_required:{request.executor_kind}",
                        reason_label="当前执行器需要走容器或远程交接，不能直接在本地 runtime 执行",
                        category="executor_handoff_required",
                        category_label="执行器需交接",
                        scope="executor",
                        scope_label="执行器",
                        details={
                            "executor_kind": request.executor_kind,
                            "executor_backend": executor_spec.get("executor_backend", ""),
                            "routing_mode": executor_spec.get("routing_mode", ""),
                            "handoff_contract_version": executor_spec.get(
                                "handoff_contract_version",
                                "",
                            ),
                            "handoff_fields": list(executor_spec.get("handoff_fields", [])),
                            "executor_readiness": executor_spec.get("executor_readiness", ""),
                        },
                    )
                )
        if request.runtime not in self.policy.runtime_whitelist:
            failures.append(
                SandboxFailurePayload(
                    reason_code=f"runtime_not_allowed:{request.runtime}",
                    reason_label=f"runtime {request.runtime} 不在白名单内",
                    scope="policy",
                    scope_label="策略",
                    details={"runtime": request.runtime},
                )
            )
        unknown_families = [
            family
            for family in request.attack_families
            if family not in self.policy.attack_family_whitelist
        ]
        if unknown_families:
            failures.append(
                SandboxFailurePayload(
                    reason_code=(
                        f"attack_family_not_allowed:{','.join(sorted(set(unknown_families)))}"
                    ),
                    reason_label="存在未授权的攻击族",
                    scope="policy",
                    scope_label="策略",
                    details={"attack_families": sorted(set(unknown_families))},
                )
            )
        if request.requested_attack_count > self.policy.max_attack_tasks:
            failures.append(
                SandboxFailurePayload(
                    reason_code="attack_count_exceeded",
                    reason_label="攻击任务数量超出预算",
                    scope="budget",
                    scope_label="预算",
                    details={
                        "requested_attack_count": request.requested_attack_count,
                        "max_attack_tasks": self.policy.max_attack_tasks,
                    },
                )
            )
        if request.requested_probe_count > self.policy.max_probe_count:
            failures.append(
                SandboxFailurePayload(
                    reason_code="probe_count_exceeded",
                    reason_label="探测次数超出预算",
                    scope="budget",
                    scope_label="预算",
                    details={
                        "requested_probe_count": request.requested_probe_count,
                        "max_probe_count": self.policy.max_probe_count,
                    },
                )
            )
        timeout_s = int(request.requested_budget.get("timeout_s", 0) or 0)
        if timeout_s > self.policy.max_timeout_seconds:
            failures.append(
                SandboxFailurePayload(
                    reason_code="timeout_exceeded",
                    reason_label="超时时间超出预算",
                    scope="budget",
                    scope_label="预算",
                    details={
                        "requested_timeout_s": timeout_s,
                        "max_timeout_seconds": self.policy.max_timeout_seconds,
                    },
                )
            )
        memory_mb = int(request.requested_budget.get("memory_mb", 0) or 0)
        if memory_mb > self.policy.max_memory_mb:
            failures.append(
                SandboxFailurePayload(
                    reason_code="memory_budget_exceeded",
                    reason_label="内存预算超出限制",
                    scope="budget",
                    scope_label="预算",
                    details={
                        "requested_memory_mb": memory_mb,
                        "max_memory_mb": self.policy.max_memory_mb,
                    },
                )
            )

        patch_artifact_count = int(request.requested_budget.get("patch_artifact_count", 0) or 0)
        if request.operation_kind == "patch_apply" and patch_artifact_count <= 0:
            failures.append(
                SandboxFailurePayload(
                    reason_code="patch_artifact_count_missing",
                    reason_label="补丁请求未声明变更工件",
                    category="invalid_request",
                    category_label="请求不合法",
                    scope="payload",
                    scope_label="载荷",
                    details={"patch_artifact_count": patch_artifact_count},
                )
            )

        rollback_note_count = int(request.requested_budget.get("rollback_note_count", 0) or 0)
        if request.operation_kind == "rollback" and rollback_note_count <= 0:
            failures.append(
                SandboxFailurePayload(
                    reason_code="rollback_notes_missing",
                    reason_label="回滚请求未声明回滚指引",
                    category="invalid_request",
                    category_label="请求不合法",
                    scope="payload",
                    scope_label="载荷",
                    details={"rollback_note_count": rollback_note_count},
                )
            )

        return failures

    def _aggregate_attack_budget(self, attack_specs: list[AttackSpecPayload]) -> dict[str, Any]:
        timeout_s = 0
        memory_mb = 0
        cpu_cores = 0
        for spec in attack_specs:
            timeout_s = max(timeout_s, int(spec.budget.get("timeout_s", 0) or 0))
            memory_mb = max(memory_mb, int(spec.budget.get("memory_mb", 0) or 0))
            cpu_cores = max(cpu_cores, int(spec.budget.get("cpu_cores", 0) or 0))
        return {
            "timeout_s": timeout_s,
            "memory_mb": memory_mb,
            "cpu_cores": cpu_cores,
        }

    def _estimate_probe_count(self, attack_specs: list[AttackSpecPayload]) -> int:
        return sum(int(spec.budget.get("probe_count_hint", 3) or 3) for spec in attack_specs)

    def _ensure_approved(self, result: SandboxDispatchResultPayload) -> None:
        if result.decision == "approved":
            return
        joined = ", ".join(result.rejection_reasons) or "unknown"
        raise RuntimeError(f"Sandbox dispatch blocked: {joined}")

    def _build_execution_error(
        self,
        *,
        dispatch: SandboxDispatchResultPayload,
        exc: Exception,
    ) -> SandboxDispatchExecutionError:
        failed_item = SandboxFailurePayload(
            reason_code=f"runtime_execution_failed:{dispatch.operation_kind or dispatch.stage}",
            reason_label="执行器在本地运行时阶段失败",
            category="runtime_execution_failed",
            category_label="运行时执行失败",
            scope="runtime",
            scope_label="执行器",
            details={
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "operation_kind": dispatch.operation_kind,
                "stage": dispatch.stage,
            },
        )
        failed_dispatch = dispatch.model_copy(
            update={
                "status": "failed",
                "status_label": "执行失败",
                "failure_category": failed_item.category,
                "failure_category_label": failed_item.category_label,
                "failure_items": [*list(dispatch.failure_items or []), failed_item],
                "rejection_reasons": [
                    *list(dispatch.rejection_reasons or []),
                    failed_item.reason_code,
                ],
                "metadata": {
                    **dict(dispatch.metadata or {}),
                    "runtime_error_type": exc.__class__.__name__,
                    "runtime_error_message": str(exc),
                },
            }
        )
        failed_dispatch = self._append_audit_event(
            failed_dispatch,
            event_kind="failed",
            event_kind_label="执行失败",
            summary=f"{dispatch.operation_kind or dispatch.stage} 在本地运行时阶段执行失败。",
            metadata={
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )
        return SandboxDispatchExecutionError(
            message=(
                f"Sandbox execution failed for "
                f"{dispatch.operation_kind or dispatch.stage}: {exc.__class__.__name__}: {exc}"
            ),
            dispatch_result=failed_dispatch,
            cause=exc,
        )

    def _sign_request(self, request: SandboxDispatchRequestPayload) -> str:
        payload = request.model_dump(mode="json")
        payload["signature"] = ""
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return digest[:24]

    def _build_audit_event(
        self,
        *,
        request: SandboxDispatchRequestPayload,
        event_kind: str,
        event_kind_label: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> SandboxAuditEventPayload:
        return SandboxAuditEventPayload(
            event_id=f"{request.dispatch_id}-{event_kind}",
            stage=request.stage,
            event_kind=event_kind,
            event_kind_label=event_kind_label,
            summary=summary,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

    def _append_audit_event(
        self,
        result: SandboxDispatchResultPayload,
        *,
        event_kind: str,
        event_kind_label: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> SandboxDispatchResultPayload:
        request = SandboxDispatchRequestPayload(
            dispatch_id=result.dispatch_id,
            run_id=result.run_id,
            round_id=result.round_id,
            stage=result.stage,
            operation_kind=result.operation_kind,
            executor_backend=result.executor_backend,
            executor_kind=result.executor_kind,
            executor_label=result.executor_label,
            executor_readiness=result.executor_readiness,
            executor_contract_version=result.executor_contract_version,
            routing_mode=result.routing_mode,
            governance_mode=result.governance_mode,
            handoff_required=result.handoff_required,
            handoff_contract_version=result.handoff_contract_version,
            handoff_fields=list(result.handoff_fields),
            handoff_ref=result.handoff_ref,
            artifact_refs=list(result.artifact_refs),
            handoff_request=result.handoff_request,
            artifact_sync_manifest=result.artifact_sync_manifest,
            target_service_ref=result.target_service_ref,
            runtime=str(result.metadata.get("runtime", "")),
            required_capabilities=list(result.capability_flags),
            attack_families=list(result.metadata.get("attack_families", [])),
            requested_attack_count=result.requested_attack_count,
            requested_probe_count=result.requested_probe_count,
            requested_budget=dict(result.metadata.get("requested_budget", {})),
            signature=result.signature,
        )
        return result.model_copy(
            update={
                "audit_trail": [
                    *result.audit_trail,
                    self._build_audit_event(
                        request=request,
                        event_kind=event_kind,
                        event_kind_label=event_kind_label,
                        summary=summary,
                        metadata=metadata,
                    ),
                ]
            }
        )

    def _build_request(
        self,
        *,
        dispatch_id: str,
        run_id: str,
        round_id: str,
        stage: str,
        operation_kind: str,
        executor_kind: str,
        target_service_ref: str,
        runtime: str,
        required_capabilities: list[str],
        artifact_refs: list[str] | None = None,
        attack_families: list[str] | None = None,
        requested_attack_count: int = 0,
        requested_probe_count: int = 0,
        requested_budget: dict[str, Any] | None = None,
    ) -> SandboxDispatchRequestPayload:
        executor_spec = get_executor_backend_spec(executor_kind) or {}
        return SandboxDispatchRequestPayload(
            dispatch_id=dispatch_id,
            run_id=run_id,
            round_id=round_id,
            stage=stage,
            operation_kind=operation_kind,
            executor_backend=str(executor_spec.get("executor_backend", "local-sandbox")),
            executor_kind=executor_kind,
            executor_label=str(executor_spec.get("executor_label", "")),
            executor_readiness=str(executor_spec.get("executor_readiness", "active")),
            executor_contract_version="v1",
            routing_mode=str(executor_spec.get("routing_mode", "in_process")),
            governance_mode="dispatcher",
            handoff_required=bool(executor_spec.get("handoff_required", False)),
            handoff_contract_version=str(executor_spec.get("handoff_contract_version", "")),
            handoff_fields=list(executor_spec.get("handoff_fields", [])),
            artifact_refs=self._filter_refs(list(artifact_refs or [])),
            target_service_ref=target_service_ref,
            runtime=runtime,
            required_capabilities=list(required_capabilities),
            attack_families=list(attack_families or []),
            requested_attack_count=requested_attack_count,
            requested_probe_count=requested_probe_count,
            requested_budget=dict(requested_budget or {}),
        )

    def _build_handoff_ref(self, request: SandboxDispatchRequestPayload) -> str:
        return f"handoff:{request.dispatch_id}:{request.executor_kind}"

    def _build_dispatch_key(self, request: SandboxDispatchRequestPayload) -> str:
        return request.signature or request.dispatch_id

    def _build_workspace_ref(self, request: SandboxDispatchRequestPayload) -> str:
        round_ref = request.round_id or request.stage or "default"
        return f"workspace:{request.run_id}:{request.target_service_ref}:{round_ref}"

    def _build_handoff_artifact_sync_manifest(
        self,
        request: SandboxDispatchRequestPayload,
    ) -> ExecutorArtifactSyncManifestPayload:
        return ExecutorArtifactSyncManifestPayload(
            sync_id=f"sync:{request.dispatch_id}",
            dispatch_id=request.dispatch_id,
            direction="bidirectional",
            artifact_refs=list(request.artifact_refs),
            required_artifact_kinds=self._required_artifact_kinds_for_operation(
                request.operation_kind
            ),
            integrity_hashes={},
            retention_policy="run_scope",
            materialization_mode="reference_only",
            sync_status="planned",
        )

    def _build_handoff_request(
        self,
        request: SandboxDispatchRequestPayload,
        *,
        artifact_sync_manifest: ExecutorArtifactSyncManifestPayload,
    ) -> ExecutorHandoffRequestPayload:
        timeout_seconds = int(request.requested_budget.get("timeout_s", 0) or 0)
        return ExecutorHandoffRequestPayload(
            handoff_ref=request.handoff_ref,
            handoff_contract_version=request.handoff_contract_version or "v1",
            case_id="",
            run_id=request.run_id,
            round_id=request.round_id,
            dispatch_id=request.dispatch_id,
            dispatch_key=self._build_dispatch_key(request),
            stage=request.stage,
            operation_kind=request.operation_kind,
            executor_kind=request.executor_kind,
            executor_backend=request.executor_backend,
            target_service_ref=request.target_service_ref,
            workspace_ref=self._build_workspace_ref(request),
            input_artifact_refs=list(request.artifact_refs),
            required_capabilities=list(request.required_capabilities),
            governance_mode=request.governance_mode,
            timeout_seconds=timeout_seconds,
            budget_hint=dict(request.requested_budget),
            callback_contract={
                "mode": "placeholder",
                "receipt_ref": f"receipt:{request.dispatch_id}",
                "result_field": "handoff_receipt",
            },
            artifact_sync_contract={
                "sync_ref": artifact_sync_manifest.sync_id,
                "direction": artifact_sync_manifest.direction,
                "required_artifact_kinds": list(
                    artifact_sync_manifest.required_artifact_kinds
                ),
            },
            telemetry_contract={
                "mode": "artifact_refs",
                "expected_artifact_kinds": self._telemetry_artifact_kinds_for_operation(
                    request.operation_kind
                ),
                "audit_event_ref": f"dispatch:{request.dispatch_id}",
            },
        )

    def _build_handoff_receipt(
        self,
        request: SandboxDispatchRequestPayload,
        *,
        failure_items: list[SandboxFailurePayload],
    ) -> ExecutorHandoffReceiptPayload | None:
        if not request.handoff_required:
            return None
        handoff_failure = next(
            (
                item
                for item in failure_items
                if item.reason_code.startswith("executor_handoff_required:")
            ),
            None,
        )
        receipt_status = "pending_handoff"
        if handoff_failure is not None:
            receipt_status = "handoff_required"
        return ExecutorHandoffReceiptPayload(
            receipt_id=f"receipt:{request.dispatch_id}",
            handoff_ref=request.handoff_ref,
            dispatch_id=request.dispatch_id,
            executor_kind=request.executor_kind,
            executor_backend=request.executor_backend,
            accepted=False,
            receipt_status=receipt_status,
            remote_job_ref="",
            output_artifact_refs=[],
            telemetry_refs=[],
            failure_category=handoff_failure.category if handoff_failure is not None else "",
            failure_summary=(
                handoff_failure.reason_label
                if handoff_failure is not None
                else "等待 executor handoff adapter 接管。"
            ),
            retryable=True,
        )

    def _build_handoff_trace(
        self,
        request: SandboxDispatchRequestPayload,
        *,
        failure_items: list[SandboxFailurePayload],
        receipt: ExecutorHandoffReceiptPayload | None,
    ) -> ExecutorHandoffTracePayload | None:
        if not request.handoff_required:
            return None
        handoff_failure = next(
            (
                item
                for item in failure_items
                if item.reason_code.startswith("executor_handoff_required:")
            ),
            None,
        )
        trace_status = "pending_handoff"
        summary = "等待 handoff adapter 将调度请求转交给非本地执行面。"
        failure_category = ""
        if handoff_failure is not None:
            trace_status = "handoff_required"
            summary = "当前 executor 需要 handoff adapter 接管，dispatcher 不会直接进入本地 runtime。"
            failure_category = handoff_failure.category
        artifact_sync_ref = (
            request.artifact_sync_manifest.sync_id
            if request.artifact_sync_manifest is not None
            else ""
        )
        receipt_ref = receipt.receipt_id if receipt is not None else ""
        return ExecutorHandoffTracePayload(
            handoff_ref=request.handoff_ref,
            dispatch_id=request.dispatch_id,
            executor_kind=request.executor_kind,
            executor_backend=request.executor_backend,
            routing_mode=request.routing_mode,
            adapter_stage="dispatcher_plan",
            trace_status=trace_status,
            summary=summary,
            receipt_ref=receipt_ref,
            artifact_sync_ref=artifact_sync_ref,
            failure_category=failure_category,
        )

    def _required_artifact_kinds_for_operation(self, operation_kind: str) -> list[str]:
        mapping = {
            "deploy": ["service_manifest", "runtime_info", "service_stdout"],
            "attack": ["trace", "metrics", "finding"],
            "patch_apply": [
                "patch_manifest",
                "patch_metadata",
                "rollback_plan",
                "rollback_manifest",
            ],
            "rollback": ["rollback_plan", "rollback_manifest"],
            "regression_replay": ["metrics", "finding"],
        }
        return list(mapping.get(operation_kind, []))

    def _telemetry_artifact_kinds_for_operation(self, operation_kind: str) -> list[str]:
        mapping = {
            "deploy": ["runtime_info", "service_stdout"],
            "attack": ["trace", "metrics"],
            "patch_apply": ["patch_metadata"],
            "rollback": ["rollback_plan"],
            "regression_replay": ["metrics"],
        }
        return list(mapping.get(operation_kind, []))

    def _filter_refs(self, refs: list[str]) -> list[str]:
        clean: list[str] = []
        seen: set[str] = set()
        for item in refs:
            ref = str(item or "").strip()
            if not ref or ref in seen:
                continue
            seen.add(ref)
            clean.append(ref)
        return clean
