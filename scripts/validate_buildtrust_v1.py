"""Validate the frozen BuildTrust V1 competition demonstration contract."""

from __future__ import annotations

import argparse
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from cipher_genius.integrations.construction import (
    CredentialNotUsableError,
    LocalReferenceHMACProvider,
    SQLiteCredentialGovernanceStore,
    inspect_ifc_bytes,
)
from cipher_genius.models.construction import (
    CertificateLifecycleState,
    ConstructionCertificateGovernanceRecord,
    ConstructionCredentialGovernanceRecord,
    CredentialLifecycleState,
)
from cipher_genius.sandbox.construction_runtime import ConstructionTrustDemoRunner


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPOSITORY_ROOT / "data" / "demo" / "buildtrust_v1" / "manifest.json"


def validate(manifest_path: Path, output_path: Path | None = None) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    input_path = (manifest_path.parent / manifest["input_file"]).resolve()
    inspection = inspect_ifc_bytes(
        input_path.read_bytes(),
        source_ref=f"release:{input_path.name}",
    )
    failures: list[str] = []
    expected_ifc = manifest["expected_ifc"]
    if inspection.content_sha256 != manifest["input_sha256"]:
        failures.append("input_sha256")
    if not inspection.valid:
        failures.append("ifc_valid")
    if inspection.schema_identifiers != expected_ifc["schema_identifiers"]:
        failures.append("ifc_schema")
    if inspection.entity_count != expected_ifc["entity_count"]:
        failures.append("ifc_entity_count")

    with TemporaryDirectory(prefix="buildtrust-v1-") as workspace:
        demo_store = SQLiteCredentialGovernanceStore(
            Path(workspace) / "demo-governance.sqlite3"
        )
        demo_provider = LocalReferenceHMACProvider(
            provider_id="buildtrust-localhost-provider",
            governance_store=demo_store,
        )
        fixed_time = "2026-08-11T00:00:00+00:00"
        demo_credentials = (
            (
                "local://buildtrust/design-signing-001",
                "design-cert-001",
                "bim_manifest_signing",
                secrets.token_bytes(32),
            ),
            (
                "local://buildtrust/device-mac-001",
                "sensor-concrete-001",
                "construction_iot_authentication",
                secrets.token_bytes(32),
            ),
        )
        for credential_ref, owner_ref, purpose, key_material in demo_credentials:
            demo_provider.register_key(
                record=ConstructionCredentialGovernanceRecord(
                    credential_ref=credential_ref,
                    project_id=manifest["project_id"],
                    owner_ref=owner_ref,
                    purpose=purpose,
                    algorithm="HMAC-SHA256",
                    provider_id="buildtrust-localhost-provider",
                    provider_kind="local_reference",
                    key_version="v1",
                    created_at=fixed_time,
                    activated_at=fixed_time,
                ),
                key_material=key_material,
            )
        runner = ConstructionTrustDemoRunner(
            workspace,
            mac_provider=demo_provider,
            signature_provider=demo_provider,
            device_credential_ref="local://buildtrust/device-mac-001",
            design_signing_credential_ref="local://buildtrust/design-signing-001",
        )
        baseline = runner.run(
            project_id=manifest["project_id"],
            run_id="buildtrust-v1-baseline",
            security_profile="baseline",
        )
        hardened = runner.run(
            project_id=manifest["project_id"],
            run_id="buildtrust-v1-hardened",
            security_profile="hardened",
        )
        expected_demo = manifest["expected_demo"]
        observed_demo = {
            "attack_count": hardened.attack_count,
            "crypto_provider_mode": hardened.crypto_provider_mode,
            "provider_mac_enabled": hardened.provider_mac_enabled,
            "provider_signature_enabled": hardened.provider_signature_enabled,
            "baseline_blocked_count": baseline.blocked_count,
            "hardened_blocked_count": hardened.blocked_count,
            "hardened_regression_passed_count": hardened.regression_passed_count,
            "evidence_ledger_valid": hardened.evidence_ledger_valid,
        }
        for key, expected_value in expected_demo.items():
            if observed_demo[key] != expected_value:
                failures.append(f"demo:{key}")

        governance_store = SQLiteCredentialGovernanceStore(
            Path(workspace) / "credential-governance.sqlite3"
        )
        provider = LocalReferenceHMACProvider(
            provider_id="buildtrust-reference-provider",
            governance_store=governance_store,
        )
        credential_ref = "hsm://buildtrust/device-001"
        credential = ConstructionCredentialGovernanceRecord(
            credential_ref=credential_ref,
            project_id=manifest["project_id"],
            owner_ref="device-001",
            purpose="construction_iot_authentication",
            algorithm="HMAC-SHA256",
            provider_id="buildtrust-reference-provider",
            provider_kind="local_reference",
            key_version="v1",
            created_at=fixed_time,
            activated_at=fixed_time,
            next_rotation_at="2026-11-01T00:00:00+00:00",
        )
        provider.register_key(record=credential, key_material=b"release-contract-secret")
        operation_payload = b"buildtrust-v1-governance-check"
        mac_value, _ = provider.generate_mac(
            credential_ref=credential_ref,
            payload=operation_payload,
        )
        verified, _ = provider.verify_mac(
            credential_ref=credential_ref,
            payload=operation_payload,
            mac_value=mac_value,
        )
        governance_store.save_credential(
            credential.model_copy(
                update={"lifecycle_state": CredentialLifecycleState.REVOKED}
            )
        )
        rejected = False
        try:
            provider.verify_mac(
                credential_ref=credential_ref,
                payload=operation_payload,
                mac_value=mac_value,
            )
        except CredentialNotUsableError as exc:
            rejected = bool(exc.receipt and exc.receipt.status == "rejected")
        certificate = ConstructionCertificateGovernanceRecord(
            certificate_ref="cert://buildtrust/device-001",
            project_id=manifest["project_id"],
            subject_ref="device-001",
            issuer_ref="ca://buildtrust/reference",
            serial_number="BT-V1-001",
            signature_algorithm="ECDSA-P256-SHA256",
            fingerprint_sha256="ab" * 32,
            provider_id="buildtrust-reference-provider",
            lifecycle_state=CertificateLifecycleState.ACTIVE,
            not_before=fixed_time,
            not_after="2026-11-01T00:00:00+00:00",
            last_checked_at=datetime.now(timezone.utc).isoformat(),
        )
        governance_store.save_certificate(certificate)
        assessment = governance_store.assess(
            assessed_at="2026-12-01T00:00:00+00:00"
        )
        observed_governance = {
            "mac_verified": verified,
            "operation_receipt_count": len(
                governance_store.list_operations(credential_ref=credential_ref)
            ),
            "revoked_operation_rejected": rejected,
            "rotation_due_count": len(assessment.rotation_due_refs),
            "invalid_certificate_count": len(assessment.invalid_certificate_refs),
        }
        for key, expected_value in manifest["expected_governance"].items():
            if observed_governance[key] != expected_value:
                failures.append(f"governance:{key}")

    result = {
        "release_contract": manifest["release_contract"],
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "ifc": inspection.model_dump(mode="json"),
        "demo": observed_demo,
        "governance": observed_governance,
        "capability_boundary": manifest["capability_boundary"],
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.manifest.resolve(), args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
