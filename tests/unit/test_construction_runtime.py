import json
from pathlib import Path

from cipher_genius.api.schemas import AttackResultPayload, EngineerReportPayload, PatchSpecPayload
from cipher_genius.core.langgraph_mas import LangGraphMASService
from cipher_genius.sandbox.construction_runtime import (
    BIMPackageExchangeRuntime,
    ConstructionIoTGatewayRuntime,
    ConstructionTrustDemoRunner,
    ProjectEvidenceLedgerRuntime,
    build_construction_attack_specs,
)
from cipher_genius.sandbox.local_runtime import LocalSandboxRuntime
from cipher_genius.sandbox.dispatcher import LocalSandboxDispatcher
from cipher_genius.sandbox.target_templates import build_bim_package_exchange_target_service


def test_bim_runtime_rejects_tamper_rollback_and_unauthorized_role():
    runtime = BIMPackageExchangeRuntime({"design-cert": b"demo-secret"})
    v2 = runtime.register_package(
        project_id="project-001",
        asset_id="ifc-main",
        version="v2",
        parent_version="v1",
        content=b"ifc-v2",
        signer_identity="design-cert",
        approval_state="approved",
        allowed_roles=["general_contractor"],
    )
    v3 = runtime.register_package(
        project_id="project-001",
        asset_id="ifc-main",
        version="v3",
        parent_version="v2",
        content=b"ifc-v3",
        signer_identity="design-cert",
        approval_state="approved",
        allowed_roles=["general_contractor"],
    )

    tamper = runtime.verify_delivery(
        manifest=v3,
        content=b"ifc-v3-tampered",
        requester_role="general_contractor",
    )
    rollback = runtime.verify_delivery(
        manifest=v2,
        content=b"ifc-v2",
        requester_role="general_contractor",
    )
    unauthorized = runtime.verify_delivery(
        manifest=v3,
        content=b"ifc-v3",
        requester_role="specialty_subcontractor",
    )

    assert tamper["checks"]["signature_valid"] is True
    assert tamper["checks"]["content_valid"] is False
    assert rollback["checks"]["signature_valid"] is True
    assert rollback["checks"]["is_current_version"] is False
    assert unauthorized["checks"]["role_allowed"] is False


def test_iot_runtime_distinguishes_replay_from_invalid_signature():
    runtime = ConstructionIoTGatewayRuntime(freshness_window_seconds=60)
    secret = b"device-secret"
    runtime.register_device("device-001", secret)
    message = runtime.sign_telemetry(
        device_id="device-001",
        secret=secret,
        counter=1,
        nonce="nonce-001",
        timestamp=1_000,
        value=20.5,
    )

    first = runtime.ingest(message, now=1_000)
    replay = runtime.ingest(message, now=1_001)

    assert first["accepted"] is True
    assert replay["accepted"] is False
    assert replay["signature_valid"] is True
    assert replay["reason"] == "replay_or_stale_message"


def test_evidence_ledger_detects_mutation():
    ledger = ProjectEvidenceLedgerRuntime({"supervisor-cert": b"ledger-secret"})
    ledger.append(
        event_type="approval",
        subject_ref="ifc-main:v3",
        signer_identity="supervisor-cert",
        payload={"state": "approved"},
        timestamp=1_000,
    )
    assert ledger.verify()["valid"] is True

    ledger.entries[0]["payload"]["state"] = "draft"
    assert ledger.verify()["valid"] is False


def test_demo_runner_executes_five_attacks_and_persists_evidence(tmp_path: Path):
    result = ConstructionTrustDemoRunner(tmp_path).run(
        project_id="project-001",
        run_id="run-construction-001",
    )

    assert result.status == "completed"
    assert result.attack_count == 5
    assert result.detected_count == 5
    assert result.blocked_count == 5
    assert result.regression_passed_count == 5
    assert result.evidence_ledger_valid is True
    assert {item.case_id for item in result.results} == {
        "bim_ifc_tamper",
        "bim_version_rollback",
        "subcontractor_overprivilege",
        "iot_device_impersonation",
        "iot_telemetry_replay",
    }
    assert all(item.artifact_refs for item in result.results)
    assert all(item.evidence_refs for item in result.results)

    summary_path = tmp_path / "run-construction-001" / "buildtrust_demo_summary.json"
    ledger_path = tmp_path / "run-construction-001" / "project_evidence_ledger.json"
    assert summary_path.exists()
    assert ledger_path.exists()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["attack_count"] == 5


def test_construction_attack_specs_and_local_runtime_feed_the_mas_contract(tmp_path: Path):
    target = build_bim_package_exchange_target_service(run_id="run-construction-002")
    target = target.model_copy(update={"artifact_id": str(tmp_path / "target")})
    specs = build_construction_attack_specs(
        run_id="run-construction-002",
        target_service=target,
    )
    dispatcher = LocalSandboxDispatcher(runtime=LocalSandboxRuntime(tmp_path / "sandbox"))
    request, dispatch = dispatcher.plan_attack_execution(
        run_id="run-construction-002",
        round_id="baseline",
        target_service=target,
        attack_specs=specs,
    )

    results = dispatcher.runtime.execute_attack_specs(
        target_service=target,
        attack_specs=specs,
        vulnerability_report={},
    )

    assert len(specs) == 5
    assert request.requested_attack_count == 5
    assert dispatch.decision == "approved"
    assert len(results) == 5
    assert {item.metrics["attack_type"] for item in results} == {
        "ifc_content_tamper",
        "signed_old_version_rollback",
        "full_model_overprivilege",
        "unregistered_device_impersonation",
        "valid_signed_telemetry_replay",
    }
    assert all(item.status == "executed" for item in results)
    assert all(item.metrics["security_profile"] == "baseline" for item in results)
    assert not any(item.metrics["blocked"] for item in results)
    assert not any(item.metrics["regression_passed"] for item in results)
    assert all(item.artifact_refs for item in results)


def test_construction_patch_changes_controls_and_rollback_restores_baseline(tmp_path: Path):
    runtime = LocalSandboxRuntime(tmp_path / "sandbox")
    baseline_workspace = tmp_path / "baseline"
    baseline_workspace.mkdir()
    baseline = build_bim_package_exchange_target_service(run_id="run-patch-001").model_copy(
        update={"artifact_id": str(baseline_workspace)}
    )
    patched_descriptor = baseline.model_copy(
        update={
            "service_id": f"{baseline.service_id}-reg",
            "service_version": "v2",
        }
    )
    patch_spec = PatchSpecPayload(
        patch_id="patch-construction-001",
        target_service_ref=baseline.service_id,
        strategy="construction-trust-controls",
        changed_artifacts=["construction_security_profile.json"],
        rollback_notes=["restore pre-patch construction security profile"],
        next_version="v2",
    )
    patched, application = runtime.apply_patch_to_service(
        run_id="run-patch-001",
        baseline_target_service=baseline,
        patched_target_service=patched_descriptor,
        engineer=EngineerReportPayload(sandbox_backend="local-sandbox"),
        patch_spec=patch_spec,
    )
    specs = build_construction_attack_specs(run_id="run-patch-001-reg", target_service=patched)
    hardened_results = runtime.execute_attack_specs(
        target_service=patched,
        attack_specs=specs,
        vulnerability_report={},
    )

    assert application.construction_profile_path is not None
    assert application.construction_profile_snapshot_path is not None
    assert all(item.metrics["security_profile"] == "hardened" for item in hardened_results)
    assert all(item.metrics["blocked"] for item in hardened_results)
    assert all(item.metrics["regression_passed"] for item in hardened_results)

    rollback_execution, rollback_dispatch = LocalSandboxDispatcher(
        runtime=runtime
    ).dispatch_construction_rollback_execution(
        run_id="run-patch-001",
        round_id="manual-recovery",
        target_service=patched,
        patch_spec=patch_spec,
    )
    restored_results = runtime.execute_attack_specs(
        target_service=patched,
        attack_specs=specs,
        vulnerability_report={},
    )
    rollback_payload = json.loads(rollback_execution.read_text(encoding="utf-8"))

    assert rollback_payload["verified"] is True
    assert rollback_dispatch.status == "executed"
    assert rollback_dispatch.metadata["verified"] is True
    assert all(item.metrics["security_profile"] == "baseline" for item in restored_results)
    assert not any(item.metrics["blocked"] for item in restored_results)


def test_construction_regression_rollback_policy_uses_objective_probe_results():
    construction_target = build_bim_package_exchange_target_service(run_id="run-policy-001")
    passed = AttackResultPayload(
        attack_id="attack-passed",
        target_service_ref=construction_target.service_id,
        status="executed",
        metrics={"regression_passed": True},
    )
    failed = passed.model_copy(
        update={
            "attack_id": "attack-failed",
            "metrics": {"regression_passed": False},
        }
    )

    assert not LangGraphMASService._construction_regression_requires_rollback(
        target_service=construction_target,
        attack_results=[passed],
    )
    assert LangGraphMASService._construction_regression_requires_rollback(
        target_service=construction_target,
        attack_results=[passed, failed],
    )
    assert LangGraphMASService._construction_regression_requires_rollback(
        target_service=construction_target,
        attack_results=[],
    )

    generic_target = construction_target.model_copy(update={"template_id": "mock_crypto_http_v1"})
    assert not LangGraphMASService._construction_regression_requires_rollback(
        target_service=generic_target,
        attack_results=[failed],
    )
