"""Stable target service template builders for the local sandbox."""

from __future__ import annotations

from pathlib import Path

from cipher_genius.api.schemas import (
    TargetServiceDeploymentManifestPayload,
    TargetServiceRuntimeProfilePayload,
    TargetServiceSpecPayload,
)


def build_mock_crypto_http_target_service(
    *,
    run_id: str,
    service_name: str,
    runtime: str,
    attack_surface: list[str],
    service_version: str = "v1",
) -> TargetServiceSpecPayload:
    """Build the default mock HTTP target service template for attack-loop demos."""

    service_id = f"svc-{run_id[:8]}"
    attack_surface = list(attack_surface or ["encrypt", "decrypt", "key_rotation", "service_api"])
    runtime_profile = TargetServiceRuntimeProfilePayload(
        timeout_seconds=120,
        memory_budget_mb=256,
        probe_budget=64,
        traffic_sampling_interval_ms=250,
        cleanup_policy="stop_and_archive",
    )
    manifest = TargetServiceDeploymentManifestPayload(
        entrypoint="/encrypt" if runtime == "python" else "sandbox://service/main",
        bootstrap_script="service_runtime.py",
        healthcheck="/health",
        workspace_dir=f".cache/sandbox/{run_id}/{service_id}",
        artifact_dir=f".cache/sandbox/{run_id}/{service_id}/artifacts",
    )
    return TargetServiceSpecPayload(
        service_id=service_id,
        artifact_id=f"artifact-service-{run_id[:8]}",
        template_id="mock_crypto_http_v1",
        template_label="模拟加密 HTTP 服务",
        service_kind="crypto_api",
        attack_surface_kind="http-json",
        service_name=service_name,
        deployment_profile="sandbox-http",
        service_interface="http-json",
        attack_surface=attack_surface,
        service_version=service_version,
        runtime=runtime,
        entrypoint=manifest.entrypoint,
        supported_versions=["baseline", "patched", "regression"],
        planner_skill_hints=["attack_surface_analysis", "crypto_deployment_review"],
        planner_retrieval_hints=[
            "http-json crypto api misuse",
            "error handling leakage",
            "key rotation boundary",
        ],
        deployment_manifest=manifest,
        runtime_profile=runtime_profile,
        status="ready",
        status_label="已部署描述",
    )


def _build_construction_target_service(
    *,
    run_id: str,
    service_name: str,
    template_id: str,
    template_label: str,
    service_kind: str,
    attack_surface_kind: str,
    attack_surface: list[str],
    planner_skill_hints: list[str],
    planner_retrieval_hints: list[str],
) -> TargetServiceSpecPayload:
    """Build a domain-specific, local-demo target contract for BuildTrust."""

    service_id = f"svc-{template_id.removesuffix('_v1')}-{run_id[:8]}"
    runtime_profile = TargetServiceRuntimeProfilePayload(
        timeout_seconds=120,
        memory_budget_mb=256,
        probe_budget=64,
        traffic_sampling_interval_ms=250,
        cleanup_policy="stop_and_archive",
    )
    manifest = TargetServiceDeploymentManifestPayload(
        entrypoint="/health",
        bootstrap_script="service_runtime.py",
        healthcheck="/health",
        workspace_dir=f".cache/sandbox/{run_id}/{service_id}",
        artifact_dir=f".cache/sandbox/{run_id}/{service_id}/artifacts",
    )
    return TargetServiceSpecPayload(
        service_id=service_id,
        artifact_id=f"artifact-{service_id}",
        template_id=template_id,
        template_label=template_label,
        service_kind=service_kind,
        attack_surface_kind=attack_surface_kind,
        service_name=service_name,
        deployment_profile="sandbox-construction-demo",
        service_interface="http-json",
        attack_surface=attack_surface,
        service_version="v1",
        runtime="python",
        entrypoint=manifest.entrypoint,
        supported_versions=["baseline", "patched", "regression"],
        planner_skill_hints=planner_skill_hints,
        planner_retrieval_hints=planner_retrieval_hints,
        deployment_manifest=manifest,
        runtime_profile=runtime_profile,
        status="ready",
        status_label="建筑演示目标已就绪",
    )


def build_bim_package_exchange_target_service(*, run_id: str) -> TargetServiceSpecPayload:
    return _build_construction_target_service(
        run_id=run_id,
        service_name="BIM/IFC 可信交付服务",
        template_id="bim_package_exchange_v1",
        template_label="BIM/IFC 可信交付目标",
        service_kind="bim_package_exchange",
        attack_surface_kind="ifc-manifest-http",
        attack_surface=["ifc_upload", "manifest_verify", "version_approve", "package_download"],
        planner_skill_hints=["bim_model_exchange_guard", "construction_collaboration_ip_guard"],
        planner_retrieval_hints=[
            "ifc tamper",
            "signed old version rollback",
            "subcontractor overprivilege",
        ],
    )


def build_construction_iot_gateway_target_service(*, run_id: str) -> TargetServiceSpecPayload:
    return _build_construction_target_service(
        run_id=run_id,
        service_name="工地 IoT 可信网关",
        template_id="construction_iot_gateway_v1",
        template_label="工地 IoT 可信网关目标",
        service_kind="construction_iot_gateway",
        attack_surface_kind="signed-telemetry-http",
        attack_surface=["device_register", "telemetry_ingest", "signature_verify", "replay_guard"],
        planner_skill_hints=["construction_iot_trust_architect"],
        planner_retrieval_hints=[
            "device impersonation",
            "valid telemetry replay",
            "counter nonce time window",
        ],
    )


def build_project_evidence_ledger_target_service(*, run_id: str) -> TargetServiceSpecPayload:
    return _build_construction_target_service(
        run_id=run_id,
        service_name="项目签批与验收证据账本",
        template_id="project_evidence_ledger_v1",
        template_label="项目证据链目标",
        service_kind="project_evidence_ledger",
        attack_surface_kind="signed-evidence-http",
        attack_surface=["approval_append", "evidence_link", "chain_verify", "timeline_query"],
        planner_skill_hints=[
            "inspection_evidence_chain_designer",
            "trusted_construction_crypto_reviewer",
        ],
        planner_retrieval_hints=["approval repudiation", "evidence hash chain", "trusted timestamp"],
    )


def build_target_service_for_requirement(
    *,
    run_id: str,
    requirement_text: str,
    domain: str,
    service_name: str,
    runtime: str,
    attack_surface: list[str],
) -> TargetServiceSpecPayload:
    """Select a stable target template without hiding execution capability boundaries."""

    normalized_domain = str(domain or "").strip().lower()
    normalized_requirement = str(requirement_text or "").strip().lower()
    if normalized_domain == "construction":
        bim_signals = ["bim", "ifc", "模型", "图纸", "版本", "交付"]
        iot_signals = ["iot", "传感器", "遥测", "设备", "重放", "数字孪生"]
        evidence_signals = ["验收", "签批", "证据链", "隐蔽工程", "检测报告"]
        has_bim = any(item in normalized_requirement for item in bim_signals)
        has_iot = any(item in normalized_requirement for item in iot_signals)
        has_evidence = any(item in normalized_requirement for item in evidence_signals)
        if has_iot and not has_bim:
            return build_construction_iot_gateway_target_service(run_id=run_id)
        if has_evidence and not has_bim and not has_iot:
            return build_project_evidence_ledger_target_service(run_id=run_id)
        return build_bim_package_exchange_target_service(run_id=run_id)
    return build_mock_crypto_http_target_service(
        run_id=run_id,
        service_name=service_name,
        runtime=runtime,
        attack_surface=attack_surface,
        service_version="v1",
    )


def materialize_deployment_manifest(
    target_service: TargetServiceSpecPayload,
    *,
    workspace: Path,
    service_script_path: Path,
) -> TargetServiceSpecPayload:
    """Update a target service spec with concrete local workspace paths."""

    artifact_dir = workspace / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    manifest = target_service.deployment_manifest.model_copy(
        update={
            "entrypoint": str(service_script_path).replace("\\", "/"),
            "bootstrap_script": service_script_path.name,
            "workspace_dir": str(workspace).replace("\\", "/"),
            "artifact_dir": str(artifact_dir).replace("\\", "/"),
        }
    )
    return target_service.model_copy(
        update={
            "artifact_id": str(workspace).replace("\\", "/"),
            "entrypoint": str(service_script_path).replace("\\", "/"),
            "deployment_manifest": manifest,
            "status": "deployed",
            "status_label": "已部署",
        }
    )
