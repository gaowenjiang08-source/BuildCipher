from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from cipher_genius.api import construction_service
from cipher_genius.integrations.construction import (
    LocalDirectoryCDEConnector,
    LocalReferenceHMACProvider,
    SQLiteConstructionIoTReplayState,
    SQLiteCredentialGovernanceStore,
    inspect_ifc_bytes,
)
from cipher_genius.models.construction import (
    CertificateLifecycleState,
    ConstructionCertificateGovernanceRecord,
    ConstructionCredentialGovernanceRecord,
    CredentialLifecycleState,
)
from cipher_genius.sandbox.construction_runtime import (
    BIMPackageExchangeRuntime,
    ConstructionIoTGatewayRuntime,
    ConstructionTrustDemoRunner,
)


VALID_IFC = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('coordination.ifc','2026-08-11T00:00:00',(),(),'BuildTrust','BuildTrust','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('0YvctVUKr0kugbFTf53O9L',$,'Project',$,$,$,$,$,$);
#2=IFCWALL('1YvctVUKr0kugbFTf53O9L',$,
'Wall A',$,$,$,$,$);
ENDSEC;
END-ISO-10303-21;
"""


def test_ifc_inspector_reads_schema_entities_and_global_ids():
    result = inspect_ifc_bytes(VALID_IFC, source_ref="test:coordination.ifc")

    assert result.valid is True
    assert result.file_name == "coordination.ifc"
    assert result.schema_identifiers == ["IFC4"]
    assert result.entity_count == 2
    assert result.entity_type_counts == {"IFCPROJECT": 1, "IFCWALL": 1}
    assert result.global_id_count == 2
    assert result.parse_errors == []


def test_ifc_inspector_does_not_treat_material_and_style_names_as_global_ids():
    payload = b"""ISO-10303-21;
HEADER;
FILE_NAME('building.ifc','2026-08-26T00:00:00',(),(),'BuildCipher','BuildCipher','');
FILE_SCHEMA(('IFC4X3_ADD2'));
ENDSEC;
DATA;
#1=IFCPROJECT('0YvctVUKr0kugbFTf53O9L',$,'Project',$,$,$,$,$,$);
#2=IFCMATERIAL('composite_element_roof',$,$);
#3=IFCSURFACESTYLE('composite_element_roof',.BOTH.,());
ENDSEC;
END-ISO-10303-21;
"""

    result = inspect_ifc_bytes(payload, source_ref="test:building.ifc")

    assert result.valid is True
    assert result.global_id_count == 1
    assert result.duplicate_global_ids == []
    assert result.parse_errors == []


def test_ifc_inspector_still_rejects_a_duplicate_valid_global_id():
    payload = VALID_IFC.replace(
        b"1YvctVUKr0kugbFTf53O9L",
        b"0YvctVUKr0kugbFTf53O9L",
    )

    result = inspect_ifc_bytes(payload)

    assert result.valid is False
    assert result.duplicate_global_ids == ["0YvctVUKr0kugbFTf53O9L"]
    assert result.parse_errors == [
        "duplicate_global_id:0YvctVUKr0kugbFTf53O9L"
    ]


def test_ifc_inspector_rejects_non_ifc_payload():
    result = inspect_ifc_bytes(b"not-an-ifc")

    assert result.valid is False
    assert set(result.parse_errors) == {
        "missing_iso_10303_21_header",
        "missing_data_section",
        "missing_file_schema",
        "no_ifc_entities",
    }


def test_local_cde_connector_lists_reads_and_inspects_packages(tmp_path: Path):
    project_dir = tmp_path / "project-001" / "models"
    project_dir.mkdir(parents=True)
    package_path = project_dir / "coordination.ifc"
    package_path.write_bytes(VALID_IFC)
    connector = LocalDirectoryCDEConnector(tmp_path)

    packages = connector.list_packages(project_id="project-001")

    assert connector.status().available is True
    assert len(packages) == 1
    assert packages[0].package_id == "project-001/models/coordination.ifc"
    assert connector.read_package(package_id=packages[0].package_id) == VALID_IFC
    assert connector.inspect_package(package_id=packages[0].package_id).valid is True


def test_local_cde_connector_rejects_reference_outside_root(tmp_path: Path):
    connector = LocalDirectoryCDEConnector(tmp_path)

    with pytest.raises(ValueError, match="escapes connector root"):
        connector.read_package(package_id="../outside.ifc")


def test_sqlite_iot_state_survives_gateway_restart(tmp_path: Path):
    database_path = tmp_path / "iot-state.sqlite3"
    secret = b"persistent-device-secret"

    def resolver(credential_ref: str) -> bytes:
        return {"kms://project/device-001": secret}[credential_ref]

    first_gateway = ConstructionIoTGatewayRuntime(
        replay_state=SQLiteConstructionIoTReplayState(database_path),
        credential_resolver=resolver,
    )
    first_gateway.register_device(
        "device-001",
        secret,
        credential_ref="kms://project/device-001",
    )
    message = first_gateway.sign_telemetry(
        device_id="device-001",
        secret=secret,
        counter=1,
        nonce="nonce-001",
        timestamp=1_000,
        value=20.5,
    )
    assert first_gateway.ingest(message, now=1_000)["accepted"] is True

    restarted_gateway = ConstructionIoTGatewayRuntime(
        replay_state=SQLiteConstructionIoTReplayState(database_path),
        credential_resolver=resolver,
    )
    replay = restarted_gateway.ingest(message, now=1_001)
    next_message = restarted_gateway.sign_telemetry(
        device_id="device-001",
        secret=secret,
        counter=2,
        nonce="nonce-002",
        timestamp=1_002,
        value=20.7,
    )

    assert replay["accepted"] is False
    assert replay["reason"] == "replay_or_stale_message"
    assert restarted_gateway.ingest(next_message, now=1_002)["accepted"] is True


def test_non_exporting_mac_provider_emits_receipts_and_enforces_lifecycle(tmp_path: Path):
    governance_path = tmp_path / "governance.sqlite3"
    replay_path = tmp_path / "replay.sqlite3"
    governance = SQLiteCredentialGovernanceStore(governance_path)
    provider = LocalReferenceHMACProvider(
        provider_id="reference-provider",
        governance_store=governance,
    )
    credential_ref = "hsm://project/device-002"
    now = datetime.now(timezone.utc).isoformat()
    record = ConstructionCredentialGovernanceRecord(
        credential_ref=credential_ref,
        project_id="project-001",
        owner_ref="device-002",
        purpose="construction_iot_authentication",
        algorithm="HMAC-SHA256",
        provider_id="reference-provider",
        provider_kind="local_reference",
        key_version="v1",
        created_at=now,
        activated_at=now,
        next_rotation_at="2026-11-11T00:00:00+00:00",
        policy_refs=["policy:construction-device-90d"],
    )
    provider.register_key(record=record, key_material=b"provider-owned-secret")
    gateway = ConstructionIoTGatewayRuntime(
        replay_state=SQLiteConstructionIoTReplayState(replay_path),
        mac_provider=provider,
    )
    gateway.register_device("device-002", None, credential_ref=credential_ref)
    message = gateway.sign_telemetry(
        device_id="device-002",
        credential_ref=credential_ref,
        counter=1,
        nonce="provider-nonce-001",
        timestamp=2_000,
        value=21.5,
    )
    accepted = gateway.ingest(message, now=2_000)

    assert accepted["accepted"] is True
    assert accepted["key_operation"]["operation"] == "mac_verify"
    assert accepted["key_operation"]["verification_result"] is True
    assert len(governance.list_operations(credential_ref=credential_ref)) == 2
    assert b"provider-owned-secret" not in governance_path.read_bytes()

    governance.save_credential(
        record.model_copy(update={"lifecycle_state": CredentialLifecycleState.REVOKED})
    )
    rejected = gateway.ingest(message, now=2_001)
    assert rejected["accepted"] is False
    assert rejected["reason"] == "credential_not_usable"
    assert rejected["key_operation"]["status"] == "rejected"
    assert len(governance.list_operations(credential_ref=credential_ref)) == 3

    certificate = ConstructionCertificateGovernanceRecord(
        certificate_ref="cert://project/device-002",
        project_id="project-001",
        subject_ref="device-002",
        issuer_ref="ca://construction-root",
        serial_number="1002003",
        signature_algorithm="ECDSA-P256-SHA256",
        fingerprint_sha256="ab" * 32,
        provider_id="reference-provider",
        lifecycle_state=CertificateLifecycleState.ACTIVE,
        not_before="2026-08-11T00:00:00+00:00",
        not_after="2026-11-11T00:00:00+00:00",
        last_checked_at=now,
        policy_refs=["policy:construction-device-certificate"],
    )
    governance.save_certificate(certificate)
    assert governance.get_certificate(certificate.certificate_ref) == certificate
    assessment = governance.assess(assessed_at="2026-12-01T00:00:00+00:00")
    assert assessment.rotation_due_refs == [credential_ref]
    assert assessment.inactive_credential_refs == [credential_ref]
    assert assessment.invalid_certificate_refs == [certificate.certificate_ref]


def test_local_crypto_provider_drives_bim_manifest_signing(tmp_path: Path):
    provider_id = "localhost-provider"
    governance = SQLiteCredentialGovernanceStore(tmp_path / "local-governance.sqlite3")
    provider = LocalReferenceHMACProvider(
        provider_id=provider_id,
        governance_store=governance,
    )
    credential_ref = "local://project/design-signing-key"
    now = datetime.now(timezone.utc).isoformat()
    provider.register_key(
        record=ConstructionCredentialGovernanceRecord(
            credential_ref=credential_ref,
            project_id="project-001",
            owner_ref="design-cert",
            purpose="bim_manifest_signing",
            algorithm="HMAC-SHA256",
            provider_id=provider_id,
            provider_kind="local_reference",
            key_version="v1",
            created_at=now,
            activated_at=now,
        ),
        key_material=b"localhost-design-key",
    )
    device_ref = "local://project/device-key"
    provider.register_key(
        record=ConstructionCredentialGovernanceRecord(
            credential_ref=device_ref,
            project_id="project-001",
            owner_ref="sensor-concrete-001",
            purpose="construction_iot_authentication",
            algorithm="HMAC-SHA256",
            provider_id=provider_id,
            provider_kind="local_reference",
            key_version="v1",
            created_at=now,
            activated_at=now,
        ),
        key_material=b"localhost-device-key",
    )
    bim = BIMPackageExchangeRuntime(
        signature_provider=provider,
        signer_credential_refs={"design-cert": credential_ref},
    )
    content = b"ISO-10303-21;IFC4;END-ISO-10303-21;"
    manifest = bim.register_package(
        project_id="project-001",
        asset_id="ifc-main",
        version="v1",
        parent_version=None,
        content=content,
        signer_identity="design-cert",
        approval_state="approved",
        allowed_roles=["general_contractor"],
    )
    verified = bim.verify_delivery(
        manifest=manifest,
        content=content,
        requester_role="general_contractor",
    )

    assert manifest["signature_algorithm"] == "HMAC-SHA256-REFERENCE"
    assert manifest["signature_operation_ref"].startswith("sqlite:key_operations:")
    assert verified["accepted"] is True
    assert verified["key_operation"]["operation"] == "signature_verify"

    substituted = {**manifest, "signer_credential_ref": "hsm://attacker/key"}
    rejected = bim.verify_delivery(
        manifest=substituted,
        content=content,
        requester_role="general_contractor",
    )
    assert rejected["accepted"] is False
    assert rejected["provider_error"] == "signer_credential_ref_mismatch"

    demo = ConstructionTrustDemoRunner(
        tmp_path / "localhost-demo",
        mac_provider=provider,
        signature_provider=provider,
        device_credential_ref=device_ref,
        design_signing_credential_ref=credential_ref,
    ).run(
        project_id="project-001",
        run_id="localhost-provider-demo",
        security_profile="hardened",
    )
    assert demo.blocked_count == 5
    assert demo.regression_passed_count == 5
    assert demo.crypto_provider_mode == "localhost_provider"
    assert demo.provider_mac_enabled is True
    assert demo.provider_signature_enabled is True
    assert "localhost provider" in demo.capability_boundary
    assert (
        demo.results[0].before_state["tampered_delivery"]["key_operation"]["operation"]
        == "signature_verify"
    )
    assert (
        demo.results[3].after_state["registered_device_ingest"]["key_operation"][
            "operation"
        ]
        == "mac_verify"
    )


def test_construction_demo_service_builds_localhost_provider(monkeypatch, tmp_path: Path):
    settings = SimpleNamespace(
        buildcipher_governance_database_path=str(tmp_path / "service-governance.sqlite3"),
        buildcipher_construction_import_root=str(tmp_path / "construction-imports"),
    )
    monkeypatch.setattr(construction_service, "get_settings", lambda: settings)

    service = construction_service.ConstructionDemoService()

    assert isinstance(service.runner.mac_provider, LocalReferenceHMACProvider)
    assert service.runner.signature_provider is service.runner.mac_provider
    assert service.runner.mac_provider.provider_id == "buildcipher-localhost-provider"
    assert service.runner.device_credential_ref.startswith("local://")
    assert service.runner.design_signing_credential_ref.startswith("local://")
