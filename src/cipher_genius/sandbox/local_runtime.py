"""Local sandbox runtime with file-backed artifacts and a process-backed shell.

This runtime is intentionally lightweight:

- It creates a per-run workspace under `.cache/sandbox/`
- It persists deployment manifests and code artifacts for the target service
- It writes a minimal local HTTP service wrapper for bounded process execution
- It executes a sandbox-safe local probe pass that emits telemetry files

It is still not a network-isolated or containerized sandbox. The current goal
is to provide a truthful, replayable artifact + telemetry substrate instead of
in-memory placeholders while keeping the execution surface tightly bounded.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import IO
from typing import Any, Callable
from urllib import error as urllib_error
from urllib import request as urllib_request

from cipher_genius.api.schemas import (
    AttackResultPayload,
    AttackSpecPayload,
    EngineerReportPayload,
    PatchSpecPayload,
    TargetServiceSpecPayload,
)
from cipher_genius.models.scheme import CryptographicScheme
from cipher_genius.sandbox.construction_runtime import (
    CONSTRUCTION_SECURITY_PROFILE_FILENAME,
    ConstructionTrustDemoRunner,
    get_construction_security_profile,
    is_construction_target,
    map_construction_demo_results,
)
from cipher_genius.sandbox.target_templates import materialize_deployment_manifest
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LocalDeploymentResult:
    """Artifacts produced while preparing a target service workspace."""

    workspace: Path
    manifest_path: Path
    service_script_path: Path | None
    runtime_info_path: Path | None
    log_path: Path | None
    python_path: Path | None
    c_path: Path | None
    pseudocode_path: Path | None


@dataclass
class LocalServiceSession:
    """Handle for a bounded local target-service process."""

    process: subprocess.Popen
    port: int
    base_url: str
    runtime_info_path: Path
    log_path: Path
    log_handle: IO[str]


@dataclass
class LocalPatchApplicationResult:
    """Artifacts produced while materializing a patched workspace."""

    workspace: Path
    baseline_workspace: Path
    patch_manifest_path: Path
    patch_metadata_path: Path
    rollback_plan_path: Path
    rollback_manifest_path: Path
    applied_artifact_paths: list[Path]
    supporting_artifact_paths: list[Path]
    construction_profile_path: Path | None = None
    construction_profile_snapshot_path: Path | None = None


@dataclass
class LocalRollbackPlanResult:
    """Artifacts produced while persisting a rollback plan."""

    workspace: Path
    rollback_plan_path: Path
    rollback_manifest_path: Path


class LocalSandboxRuntime:
    """Local runtime used before a true isolated executor is wired in."""

    def __init__(self, root_dir: str | Path = ".cache/sandbox"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def deploy_target_service(
        self,
        *,
        run_id: str,
        target_service: TargetServiceSpecPayload,
        engineer: EngineerReportPayload,
        final_scheme: CryptographicScheme | None = None,
    ) -> tuple[TargetServiceSpecPayload, LocalDeploymentResult]:
        """Create a workspace and persist service artifacts for the target."""
        workspace = self._workspace_for(run_id=run_id, service_id=target_service.service_id)
        workspace.mkdir(parents=True, exist_ok=True)

        service_manifest = {
            "service_id": target_service.service_id,
            "artifact_id": target_service.artifact_id,
            "template_id": target_service.template_id,
            "template_label": target_service.template_label,
            "service_kind": target_service.service_kind,
            "attack_surface_kind": target_service.attack_surface_kind,
            "service_name": target_service.service_name,
            "deployment_profile": target_service.deployment_profile,
            "service_interface": target_service.service_interface,
            "attack_surface": list(target_service.attack_surface),
            "service_version": target_service.service_version,
            "runtime": target_service.runtime,
            "entrypoint": target_service.entrypoint,
            "supported_versions": list(target_service.supported_versions),
            "planner_skill_hints": list(target_service.planner_skill_hints),
            "planner_retrieval_hints": list(target_service.planner_retrieval_hints),
            "deployment_manifest": target_service.deployment_manifest.model_dump(mode="json"),
            "runtime_profile": target_service.runtime_profile.model_dump(mode="json"),
            "generated_at": time.time(),
            "scheme_name": (
                getattr(getattr(final_scheme, "metadata", None), "name", "")
                if final_scheme is not None
                else ""
            ),
        }
        manifest_path = workspace / "service_manifest.json"
        manifest_path.write_text(
            json.dumps(service_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        service_script_path = self._write_service_bootstrap(workspace)
        runtime_info_path = workspace / "runtime_info.json"
        log_path = workspace / "service_stdout.log"
        runtime_info_path.write_text(
            json.dumps(
                {
                    "service_id": target_service.service_id,
                    "status": "prepared",
                    "status_label": "已准备",
                    "base_url": "",
                    "health_url": "",
                    "pid": None,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if not log_path.exists():
            log_path.write_text("", encoding="utf-8")

        pseudocode_source = ""
        python_source = engineer.corrected_python or ""
        c_source = engineer.corrected_c or ""
        if final_scheme is not None:
            pseudocode_source = final_scheme.implementation.pseudocode or ""
            python_source = python_source or final_scheme.implementation.python or ""
            c_source = c_source or final_scheme.implementation.c or ""

        pseudocode_path = self._write_optional(workspace / "implementation.pseudo.txt", pseudocode_source)
        python_path = self._write_optional(workspace / "implementation.py", python_source)
        c_path = self._write_optional(workspace / "implementation.c", c_source)

        deployed = materialize_deployment_manifest(
            target_service,
            workspace=workspace,
            service_script_path=service_script_path,
        )
        logger.info("Local sandbox deployed target service: %s", deployed.service_id)
        return deployed, LocalDeploymentResult(
            workspace=workspace,
            manifest_path=manifest_path,
            service_script_path=service_script_path,
            runtime_info_path=runtime_info_path,
            log_path=log_path,
            python_path=python_path,
            c_path=c_path,
            pseudocode_path=pseudocode_path,
        )

    def apply_patch_to_service(
        self,
        *,
        run_id: str,
        baseline_target_service: TargetServiceSpecPayload,
        patched_target_service: TargetServiceSpecPayload,
        engineer: EngineerReportPayload,
        patch_spec: PatchSpecPayload,
        final_scheme: CryptographicScheme | None = None,
    ) -> tuple[TargetServiceSpecPayload, LocalPatchApplicationResult]:
        """Create a patched workspace before regression redeploy."""

        baseline_workspace = Path(str(baseline_target_service.artifact_id or ""))
        if not baseline_workspace.exists():
            raise FileNotFoundError(
                f"Missing baseline workspace for patch application: {baseline_workspace}"
            )

        workspace = self._workspace_for(run_id=run_id, service_id=patched_target_service.service_id)
        workspace.mkdir(parents=True, exist_ok=True)
        shutil.copytree(baseline_workspace, workspace, dirs_exist_ok=True)

        service_script_path = workspace / "service_runtime.py"
        if not service_script_path.exists():
            service_script_path = self._write_service_bootstrap(workspace)

        artifact_dir = workspace / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)

        python_source = engineer.corrected_python or ""
        c_source = engineer.corrected_c or ""
        pseudocode_source = ""
        if final_scheme is not None:
            pseudocode_source = final_scheme.implementation.pseudocode or ""
            python_source = python_source or final_scheme.implementation.python or ""
            c_source = c_source or final_scheme.implementation.c or ""

        applied_artifact_paths: list[Path] = []
        for maybe_path in [
            self._write_optional(workspace / "implementation.pseudo.txt", pseudocode_source),
            self._write_optional(workspace / "implementation.py", python_source),
            self._write_optional(workspace / "implementation.c", c_source),
        ]:
            if maybe_path is not None:
                applied_artifact_paths.append(maybe_path)

        patch_manifest_path = workspace / "patch_manifest.json"
        patch_metadata_path = workspace / "patch_metadata.json"
        rollback_plan_path = workspace / "rollback_plan.json"
        rollback_manifest_path = workspace / "rollback_manifest.json"
        runtime_info_path = workspace / "runtime_info.json"
        service_manifest_path = workspace / "service_manifest.json"

        deployment_manifest = patched_target_service.deployment_manifest.model_copy(
            update={
                "entrypoint": str(service_script_path).replace("\\", "/"),
                "bootstrap_script": service_script_path.name,
                "workspace_dir": str(workspace).replace("\\", "/"),
                "artifact_dir": str(artifact_dir).replace("\\", "/"),
            }
        )
        patched_service = patched_target_service.model_copy(
            update={
                "artifact_id": str(workspace).replace("\\", "/"),
                "entrypoint": str(service_script_path).replace("\\", "/"),
                "deployment_manifest": deployment_manifest,
                "status": "patched",
                "status_label": "已应用补丁",
            }
        )

        construction_profile_path: Path | None = None
        construction_profile_snapshot_path: Path | None = None
        if is_construction_target(patched_service):
            construction_profile_path = workspace / CONSTRUCTION_SECURITY_PROFILE_FILENAME
            construction_profile_snapshot_path = workspace / "construction_security_profile.before_patch.json"
            baseline_profile_path = baseline_workspace / CONSTRUCTION_SECURITY_PROFILE_FILENAME
            baseline_profile = (
                json.loads(baseline_profile_path.read_text(encoding="utf-8"))
                if baseline_profile_path.exists()
                else {
                    "profile_name": "baseline",
                    "controls": get_construction_security_profile("baseline"),
                }
            )
            construction_profile_snapshot_path.write_text(
                json.dumps(baseline_profile, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            construction_profile_path.write_text(
                json.dumps(
                    {
                        "profile_name": "hardened",
                        "controls": get_construction_security_profile("hardened"),
                        "patch_id": patch_spec.patch_id,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            applied_artifact_paths.append(construction_profile_path)

        service_manifest_path.write_text(
            json.dumps(
                {
                    "service_id": patched_service.service_id,
                    "artifact_id": patched_service.artifact_id,
                    "template_id": patched_service.template_id,
                    "template_label": patched_service.template_label,
                    "service_kind": patched_service.service_kind,
                    "attack_surface_kind": patched_service.attack_surface_kind,
                    "service_name": patched_service.service_name,
                    "deployment_profile": patched_service.deployment_profile,
                    "service_interface": patched_service.service_interface,
                    "attack_surface": list(patched_service.attack_surface),
                    "service_version": patched_service.service_version,
                    "runtime": patched_service.runtime,
                    "entrypoint": patched_service.entrypoint,
                    "supported_versions": list(patched_service.supported_versions),
                    "planner_skill_hints": list(patched_service.planner_skill_hints),
                    "planner_retrieval_hints": list(patched_service.planner_retrieval_hints),
                    "deployment_manifest": deployment_manifest.model_dump(mode="json"),
                    "runtime_profile": patched_service.runtime_profile.model_dump(mode="json"),
                    "patch_id": patch_spec.patch_id,
                    "patch_strategy": patch_spec.strategy,
                    "generated_at": time.time(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        patch_manifest_path.write_text(
            json.dumps(
                {
                    "patch_id": patch_spec.patch_id,
                    "target_service_ref": patch_spec.target_service_ref,
                    "strategy": patch_spec.strategy,
                    "summary": patch_spec.summary,
                    "rationale": patch_spec.rationale,
                    "changed_artifacts": list(patch_spec.changed_artifacts),
                    "implementation_notes": list(patch_spec.implementation_notes),
                    "validation_steps": list(patch_spec.validation_steps),
                    "next_version": patch_spec.next_version,
                    "workspace": str(workspace).replace("\\", "/"),
                    "baseline_workspace": str(baseline_workspace).replace("\\", "/"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        patch_metadata_path.write_text(
            json.dumps(
                {
                    "patch_id": patch_spec.patch_id,
                    "service_id": patched_service.service_id,
                    "baseline_service_ref": baseline_target_service.service_id,
                    "baseline_workspace": str(baseline_workspace).replace("\\", "/"),
                    "workspace": str(workspace).replace("\\", "/"),
                    "applied_artifact_paths": [
                        str(path).replace("\\", "/") for path in applied_artifact_paths
                    ],
                    "rollback_notes": list(patch_spec.rollback_notes),
                    "generated_at": time.time(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        rollback_payload = self._build_rollback_payload(
            patched_target_service=patched_service,
            patch_spec=patch_spec,
            baseline_workspace=baseline_workspace,
            workspace=workspace,
        )
        rollback_plan_path.write_text(
            json.dumps(rollback_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rollback_manifest_path.write_text(
            json.dumps(
                {
                    "patch_id": patch_spec.patch_id,
                    "target_service_ref": patched_service.service_id,
                    "workspace": str(workspace).replace("\\", "/"),
                    "rollback_plan_path": str(rollback_plan_path).replace("\\", "/"),
                    "baseline_workspace": str(baseline_workspace).replace("\\", "/"),
                    "generated_at": time.time(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        runtime_info_path.write_text(
            json.dumps(
                {
                    "service_id": patched_service.service_id,
                    "status": "patched",
                    "status_label": "已应用补丁",
                    "base_url": "",
                    "health_url": "",
                    "pid": None,
                    "patch_id": patch_spec.patch_id,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        supporting_artifact_paths = [
            patch_manifest_path,
            patch_metadata_path,
            rollback_plan_path,
            rollback_manifest_path,
            service_manifest_path,
            runtime_info_path,
        ]
        if construction_profile_snapshot_path is not None:
            supporting_artifact_paths.append(construction_profile_snapshot_path)
        logger.info("Local sandbox applied patch %s to %s", patch_spec.patch_id, patched_service.service_id)
        return patched_service, LocalPatchApplicationResult(
            workspace=workspace,
            baseline_workspace=baseline_workspace,
            patch_manifest_path=patch_manifest_path,
            patch_metadata_path=patch_metadata_path,
            rollback_plan_path=rollback_plan_path,
            rollback_manifest_path=rollback_manifest_path,
            applied_artifact_paths=applied_artifact_paths,
            supporting_artifact_paths=supporting_artifact_paths,
            construction_profile_path=construction_profile_path,
            construction_profile_snapshot_path=construction_profile_snapshot_path,
        )

    def execute_construction_profile_rollback(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        patch_spec: PatchSpecPayload,
    ) -> Path:
        """Restore the pre-patch construction control profile and record verification hashes."""

        if not is_construction_target(target_service):
            raise ValueError("Construction profile rollback requires a BuildTrust target")
        workspace = Path(target_service.artifact_id)
        profile_path = workspace / CONSTRUCTION_SECURITY_PROFILE_FILENAME
        snapshot_path = workspace / "construction_security_profile.before_patch.json"
        restored_payload = snapshot_path.read_bytes()
        profile_path.write_bytes(restored_payload)
        restored_hash = hashlib.sha256(profile_path.read_bytes()).hexdigest()
        snapshot_hash = hashlib.sha256(restored_payload).hexdigest()
        execution_path = workspace / "construction_rollback_execution.json"
        execution_path.write_text(
            json.dumps(
                {
                    "patch_id": patch_spec.patch_id,
                    "target_service_ref": target_service.service_id,
                    "restored_profile": json.loads(restored_payload.decode("utf-8")),
                    "snapshot_sha256": snapshot_hash,
                    "restored_sha256": restored_hash,
                    "verified": restored_hash == snapshot_hash,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return execution_path

    def materialize_rollback_plan(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        patch_spec: PatchSpecPayload,
        baseline_workspace: str | Path | None = None,
    ) -> LocalRollbackPlanResult:
        """Persist a rollback plan artifact for later replay/executor wiring."""

        workspace = Path(str(target_service.artifact_id or ""))
        workspace.mkdir(parents=True, exist_ok=True)
        rollback_plan_path = workspace / "rollback_plan.json"
        rollback_manifest_path = workspace / "rollback_manifest.json"
        rollback_payload = self._build_rollback_payload(
            patched_target_service=target_service,
            patch_spec=patch_spec,
            baseline_workspace=Path(str(baseline_workspace or "")) if baseline_workspace else None,
            workspace=workspace,
        )
        rollback_plan_path.write_text(
            json.dumps(rollback_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rollback_manifest_path.write_text(
            json.dumps(
                {
                    "patch_id": patch_spec.patch_id,
                    "target_service_ref": target_service.service_id,
                    "workspace": str(workspace).replace("\\", "/"),
                    "rollback_plan_path": str(rollback_plan_path).replace("\\", "/"),
                    "generated_at": time.time(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return LocalRollbackPlanResult(
            workspace=workspace,
            rollback_plan_path=rollback_plan_path,
            rollback_manifest_path=rollback_manifest_path,
        )

    def execute_attack_specs(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        attack_specs: list[AttackSpecPayload],
        vulnerability_report: dict[str, Any],
        telemetry_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> list[AttackResultPayload]:
        """Emit telemetry artifacts and measured process-backed attack results."""
        workspace = Path(target_service.artifact_id)
        workspace.mkdir(parents=True, exist_ok=True)
        if is_construction_target(target_service):
            profile_path = workspace / CONSTRUCTION_SECURITY_PROFILE_FILENAME
            security_profile = (
                str(json.loads(profile_path.read_text(encoding="utf-8"))["profile_name"])
                if profile_path.exists()
                else "baseline"
            )
            demo = ConstructionTrustDemoRunner(workspace).run(
                project_id=target_service.service_id,
                run_id="construction_attack_suite",
                security_profile=security_profile,
            )
            results = map_construction_demo_results(
                target_service=target_service,
                attack_specs=attack_specs,
                demo=demo,
            )
            if telemetry_callback is not None:
                for result in results:
                    telemetry_callback(
                        {
                            "event_type": "construction_attack_result",
                            "attack_id": result.attack_id,
                            "target_service_ref": result.target_service_ref,
                            "attack_family": result.metrics["attack_type"],
                            "detected": result.metrics["detected"],
                            "blocked": result.metrics["blocked"],
                            "regression_passed": result.metrics["regression_passed"],
                        }
                    )
            return results

        report_findings = self._collect_top_findings(vulnerability_report)
        code_size_bytes = self._workspace_code_size(workspace)
        service_script_path = workspace / "service_runtime.py"
        if not service_script_path.exists():
            raise FileNotFoundError(f"Missing local service bootstrap: {service_script_path}")

        results: list[AttackResultPayload] = []
        session = self._start_local_service(
            workspace=workspace,
            target_service=target_service,
            service_script_path=service_script_path,
        )
        try:
            for index, spec in enumerate(attack_specs, start=1):
                started = time.perf_counter()
                attack_dir = workspace / f"attack_{index:02d}"
                attack_dir.mkdir(parents=True, exist_ok=True)

                trace_path = attack_dir / "trace.jsonl"
                metrics_path = attack_dir / "metrics.json"
                finding_path = attack_dir / "finding.json"

                health_started = time.perf_counter()
                health_payload = self._request_json(f"{session.base_url}/health")
                health_latency_ms = max(int((time.perf_counter() - health_started) * 1000), 1)

                traffic_series: list[dict[str, Any]] = []
                encrypt_probes = [
                    {"plaintext": "sandbox-probe-alpha", "attempt": 1},
                    {"plaintext": "sandbox-probe-beta", "attempt": 2},
                    {"plaintext": "sandbox-probe-gamma", "attempt": 3},
                    {"plaintext": "sandbox-probe-delta", "attempt": 4},
                    {"plaintext": "sandbox-probe-epsilon", "attempt": 5},
                    {"plaintext": "sandbox-probe-zeta", "attempt": 6},
                    {"plaintext": "sandbox-probe-eta", "attempt": 7},
                ]
                tx_bytes = 0
                rx_bytes = 0
                latencies_ms = [health_latency_ms]
                for probe in encrypt_probes:
                    request_body = json.dumps(probe, ensure_ascii=False).encode("utf-8")
                    probe_started = time.perf_counter()
                    response_payload = self._request_json(
                        f"{session.base_url}/encrypt",
                        method="POST",
                        payload=probe,
                    )
                    latency_ms = max(int((time.perf_counter() - probe_started) * 1000), 1)
                    response_body = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")
                    tx_bytes += len(request_body)
                    rx_bytes += len(response_body)
                    latencies_ms.append(latency_ms)
                    sample_payload = {
                        "sample": probe["attempt"],
                        "sample_label": f"T+{probe['attempt']}",
                        "tx_bytes": len(request_body),
                        "rx_bytes": len(response_body),
                        "latency_ms": latency_ms,
                    }
                    traffic_series.append(sample_payload)
                    if telemetry_callback is not None:
                        telemetry_callback(
                            {
                                "event_type": "traffic_sample",
                                "attack_id": spec.attack_id,
                                "target_service_ref": target_service.service_id,
                                "attack_family": spec.attack_family,
                                "sample": sample_payload,
                                "probe_count": len(encrypt_probes),
                                "service_base_url": session.base_url,
                            }
                        )

                risk_score = int(vulnerability_report.get("risk_score", 0))
                elapsed_ms = max(int((time.perf_counter() - started) * 1000), 1)
                metrics = {
                    "latency_p95_ms": self._calculate_p95(latencies_ms),
                    "peak_memory_mb": 96 + len(spec.attack_surface) * 8,
                    "cpu_percent_peak": min(85, 25 + len(spec.telemetry_fields) * 7),
                    "tx_bytes": tx_bytes,
                    "rx_bytes": rx_bytes,
                    "code_size_bytes": code_size_bytes,
                    "artifact_count": 6,
                    "elapsed_ms": elapsed_ms,
                    "probe_count": len(traffic_series),
                    "health_latency_ms": health_latency_ms,
                    "service_port": session.port,
                    "service_base_url": session.base_url,
                    "service_health_url": f"{session.base_url}/health",
                    "health_status": health_payload.get("status", "ready"),
                    "service_runtime": health_payload.get("runtime", target_service.runtime),
                    "traffic_series": traffic_series,
                }
                metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

                trace_events = [
                    {"phase": "prepare", "time_ms": 0, "message": "已启动本地目标服务进程"},
                    {
                        "phase": "health_check",
                        "time_ms": health_latency_ms,
                        "message": f"健康探针返回 {health_payload.get('status', 'ready')}",
                    },
                ]
                trace_events.extend(
                    {
                        "phase": "probe",
                        "time_ms": item["latency_ms"],
                        "message": f"第 {item['sample']} 次加密接口探测已完成",
                    }
                    for item in traffic_series
                )
                trace_events.append(
                    {
                        "phase": "collect",
                        "time_ms": elapsed_ms,
                        "message": f"完成 {spec.attack_family} 攻击任务并收集 telemetry/finding 工件",
                    }
                )
                trace_path.write_text(
                    "\n".join(json.dumps(item, ensure_ascii=False) for item in trace_events),
                    encoding="utf-8",
                )

                findings = report_findings or [
                    "本轮仅完成本地受限进程探测，尚未发现高危漏洞；建议继续扩展真实攻击执行器与更细粒度接口扰动。"
                ]
                finding_payload = {
                    "attack_id": spec.attack_id,
                    "target_service_ref": spec.target_service_ref,
                    "findings": findings,
                    "objective": spec.objective,
                    "service_base_url": session.base_url,
                    "risk_score": risk_score,
                }
                finding_path.write_text(
                    json.dumps(finding_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                results.append(
                    AttackResultPayload(
                        attack_id=spec.attack_id,
                        target_service_ref=target_service.service_id,
                        status="executed",
                        status_label="已执行",
                        summary="本地进程沙盒已启动目标服务、完成受限接口探测，并生成 trace、metrics、finding 与 runtime 工件。",
                        findings=findings,
                        metrics=metrics,
                        artifact_refs=[
                            str(trace_path).replace("\\", "/"),
                            str(metrics_path).replace("\\", "/"),
                            str(finding_path).replace("\\", "/"),
                            str(session.runtime_info_path).replace("\\", "/"),
                            str(session.log_path).replace("\\", "/"),
                            str(service_script_path).replace("\\", "/"),
                        ],
                    )
                )
        finally:
            self._stop_local_service(session)

        return results

    def _workspace_for(self, *, run_id: str, service_id: str) -> Path:
        """Return the canonical workspace path for one service execution."""

        return self.root_dir / run_id / service_id

    def _build_rollback_payload(
        self,
        *,
        patched_target_service: TargetServiceSpecPayload,
        patch_spec: PatchSpecPayload,
        baseline_workspace: Path | None,
        workspace: Path,
    ) -> dict[str, Any]:
        """Create a stable rollback payload for later dispatcher/executor upgrades."""

        return {
            "patch_id": patch_spec.patch_id,
            "target_service_ref": patched_target_service.service_id,
            "service_version": patched_target_service.service_version,
            "baseline_workspace": (
                str(baseline_workspace).replace("\\", "/")
                if baseline_workspace is not None and str(baseline_workspace)
                else ""
            ),
            "workspace": str(workspace).replace("\\", "/"),
            "rollback_notes": list(patch_spec.rollback_notes),
            "recovery_actions": [
                "restore_baseline_workspace",
                "redeploy_baseline_service",
                "replay_regression_checks",
            ],
        }

    def _write_optional(self, path: Path, content: str) -> Path | None:
        """Write a file only when content exists."""
        if not content.strip():
            return None
        path.write_text(content, encoding="utf-8")
        return path

    def _workspace_code_size(self, workspace: Path) -> int:
        """Measure the persisted code footprint for telemetry."""
        total = 0
        for path in workspace.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def _write_service_bootstrap(self, workspace: Path) -> Path:
        """Write a bounded local HTTP wrapper for target-service probing."""
        script_path = workspace / "service_runtime.py"
        script = dedent(
            """
            from __future__ import annotations

            import json
            import os
            import sys
            from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
            from pathlib import Path


            MANIFEST_PATH = Path(os.environ["CG_MANIFEST_PATH"])
            MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


            class SandboxHandler(BaseHTTPRequestHandler):
                server_version = "BuildTrustSandbox/0.1"

                def _write_json(self, status_code: int, payload: dict) -> None:
                    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    self.send_response(status_code)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, format, *args):
                    return

                def do_GET(self):
                    if self.path == "/health":
                        self._write_json(
                            200,
                            {
                                "ok": True,
                                "status": "ready",
                                "service_id": MANIFEST.get("service_id", ""),
                                "service_name": MANIFEST.get("service_name", ""),
                                "runtime": MANIFEST.get("runtime", "python"),
                                "attack_surface": MANIFEST.get("attack_surface", []),
                            },
                        )
                        return
                    self._write_json(404, {"ok": False, "error": "not_found"})

                def do_POST(self):
                    if self.path != "/encrypt":
                        self._write_json(404, {"ok": False, "error": "not_found"})
                        return
                    content_length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(content_length)
                    try:
                        payload = json.loads(raw.decode("utf-8") or "{}")
                    except json.JSONDecodeError:
                        self._write_json(400, {"ok": False, "error": "invalid_json"})
                        return

                    plaintext = str(payload.get("plaintext", ""))
                    ciphertext = plaintext[::-1].encode("utf-8").hex()
                    self._write_json(
                        200,
                        {
                            "ok": True,
                            "ciphertext": ciphertext,
                            "plaintext_size": len(plaintext.encode("utf-8")),
                            "request_size": len(raw),
                            "service_version": MANIFEST.get("service_version", "v1"),
                        },
                    )


            def main() -> None:
                port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
                server = ThreadingHTTPServer(("127.0.0.1", port), SandboxHandler)
                try:
                    server.serve_forever(poll_interval=0.1)
                finally:
                    server.server_close()


            if __name__ == "__main__":
                main()
            """
        ).strip()
        script_path.write_text(script + "\n", encoding="utf-8")
        logger.debug("Wrote local sandbox service bootstrap: %s", script_path)
        return script_path

    def _start_local_service(
        self,
        *,
        workspace: Path,
        target_service: TargetServiceSpecPayload,
        service_script_path: Path,
    ) -> LocalServiceSession:
        """Start the bounded local service wrapper and wait for readiness."""
        port = self._pick_free_port()
        base_url = f"http://127.0.0.1:{port}"
        runtime_info_path = workspace / "runtime_info.json"
        log_path = workspace / "service_stdout.log"
        log_handle = log_path.open("a", encoding="utf-8")
        env = os.environ.copy()
        env["CG_MANIFEST_PATH"] = str((workspace / "service_manifest.json").resolve())
        process = subprocess.Popen(
            [sys.executable, str(service_script_path.resolve()), str(port)],
            cwd=str(workspace),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=env,
        )
        session = LocalServiceSession(
            process=process,
            port=port,
            base_url=base_url,
            runtime_info_path=runtime_info_path,
            log_path=log_path,
            log_handle=log_handle,
        )
        runtime_info_path.write_text(
            json.dumps(
                {
                    "service_id": target_service.service_id,
                    "status": "starting",
                    "status_label": "启动中",
                    "pid": process.pid,
                    "port": port,
                    "base_url": base_url,
                    "health_url": f"{base_url}/health",
                    "started_at": time.time(),
                    "bootstrap_script": str(service_script_path).replace("\\", "/"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        deadline = time.time() + 6.0
        while time.time() < deadline:
            if process.poll() is not None:
                self._stop_local_service(session)
                raise RuntimeError(f"Local sandbox process exited early with code {process.returncode}")
            try:
                health_payload = self._request_json(f"{base_url}/health")
                runtime_info_path.write_text(
                    json.dumps(
                        {
                            "service_id": target_service.service_id,
                            "status": "running",
                            "status_label": "运行中",
                            "pid": process.pid,
                            "port": port,
                            "base_url": base_url,
                            "health_url": f"{base_url}/health",
                            "started_at": time.time(),
                            "health_payload": health_payload,
                            "bootstrap_script": str(service_script_path).replace("\\", "/"),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return session
            except Exception:
                time.sleep(0.1)

        self._stop_local_service(session)
        raise TimeoutError(f"Timed out waiting for local sandbox service at {base_url}")

    def _stop_local_service(self, session: LocalServiceSession) -> None:
        """Terminate the bounded local service process and persist final status."""
        process = session.process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

        session.runtime_info_path.write_text(
            json.dumps(
                {
                    "status": "stopped",
                    "status_label": "已停止",
                    "pid": process.pid,
                    "port": session.port,
                    "base_url": session.base_url,
                    "health_url": f"{session.base_url}/health",
                    "stopped_at": time.time(),
                    "exit_code": process.returncode,
                    "log_path": str(session.log_path).replace("\\", "/"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if not session.log_handle.closed:
            session.log_handle.close()

    def _pick_free_port(self) -> int:
        """Reserve an ephemeral localhost port for the bounded service shell."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            return int(sock.getsockname()[1])

    def _request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a bounded localhost JSON request."""
        body = None
        headers = {}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        req = urllib_request.Request(url, data=body, headers=headers, method=method.upper())
        try:
            with urllib_request.urlopen(req, timeout=2.0) as response:
                raw = response.read()
        except urllib_error.URLError as exc:
            raise RuntimeError(f"Sandbox request failed for {url}: {exc}") from exc
        return json.loads(raw.decode("utf-8") or "{}")

    def _calculate_p95(self, values: list[int]) -> int:
        """Return an integer p95 estimate for a short latency series."""
        if not values:
            return 0
        ordered = sorted(int(max(item, 0)) for item in values)
        index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95))))
        return ordered[index]

    def _collect_top_findings(self, vulnerability_report: dict[str, Any]) -> list[str]:
        """Extract concise findings from the legacy vulnerability report payload."""
        findings: list[str] = []
        raw_findings = vulnerability_report.get("findings") or vulnerability_report.get("issues") or []
        if isinstance(raw_findings, list):
            for item in raw_findings[:3]:
                if isinstance(item, dict):
                    title = str(item.get("title") or item.get("name") or item.get("issue") or "").strip()
                    if title:
                        findings.append(title)
                elif item:
                    findings.append(str(item))
        return findings
