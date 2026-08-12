"""Application service for the localhost BuildTrust demonstration."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from cipher_genius.api.schemas import ConstructionDemoRunRequest, ConstructionDemoRunResponse
from cipher_genius.integrations.construction import (
    LocalReferenceHMACProvider,
    SQLiteCredentialGovernanceStore,
)
from cipher_genius.models.construction import ConstructionCredentialGovernanceRecord
from cipher_genius.sandbox.construction_runtime import ConstructionTrustDemoRunner
from cipher_genius.utils.config import get_settings


LOCAL_PROVIDER_ID = "buildtrust-localhost-provider"
DESIGN_CREDENTIAL_REF = "local://buildtrust/design-signing-001"
DEVICE_CREDENTIAL_REF = "local://buildtrust/device-mac-001"


class ConstructionDemoService:
    def __init__(self, runner: ConstructionTrustDemoRunner | None = None):
        self.runner = runner or self._build_localhost_runner()

    @staticmethod
    def _build_localhost_runner() -> ConstructionTrustDemoRunner:
        settings = get_settings()
        governance_store = SQLiteCredentialGovernanceStore(
            settings.buildtrust_governance_database_path
        )
        provider = LocalReferenceHMACProvider(
            provider_id=LOCAL_PROVIDER_ID,
            governance_store=governance_store,
        )
        now = datetime.now(timezone.utc).isoformat()
        credentials = (
            (
                DESIGN_CREDENTIAL_REF,
                "design-cert-001",
                "bim_manifest_signing",
                secrets.token_bytes(32),
            ),
            (
                DEVICE_CREDENTIAL_REF,
                "sensor-concrete-001",
                "construction_iot_authentication",
                secrets.token_bytes(32),
            ),
        )
        for credential_ref, owner_ref, purpose, key_material in credentials:
            provider.register_key(
                record=ConstructionCredentialGovernanceRecord(
                    credential_ref=credential_ref,
                    project_id="buildtrust-localhost",
                    owner_ref=owner_ref,
                    purpose=purpose,
                    algorithm="HMAC-SHA256",
                    provider_id=LOCAL_PROVIDER_ID,
                    provider_kind="local_reference",
                    key_version="v1",
                    created_at=now,
                    activated_at=now,
                    policy_refs=["policy:buildtrust-localhost-demo"],
                ),
                key_material=key_material,
            )
        return ConstructionTrustDemoRunner(
            mac_provider=provider,
            signature_provider=provider,
            device_credential_ref=DEVICE_CREDENTIAL_REF,
            design_signing_credential_ref=DESIGN_CREDENTIAL_REF,
        )

    def run(self, payload: ConstructionDemoRunRequest) -> ConstructionDemoRunResponse:
        return self.runner.run(project_id=payload.project_id, run_id=payload.run_id)
