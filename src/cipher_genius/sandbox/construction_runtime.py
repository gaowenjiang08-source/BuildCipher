"""Deterministic local runtime for BuildTrust construction-security demonstrations.

The runtime uses HMAC-SHA256 and in-memory state to make domain attacks reproducible.
It is an evidence-producing demo harness, not a production PKI, KMS, HSM, CDE, or
durable IoT gateway.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from cipher_genius.api.schemas import (
    AttackResultPayload,
    AttackSpecPayload,
    ConstructionAttackResultPayload,
    ConstructionDemoRunResponse,
    TargetServiceSpecPayload,
)
from cipher_genius.integrations.construction.iot_state import ConstructionIoTReplayState
from cipher_genius.integrations.construction.crypto_provider import (
    ConstructionMACProvider,
    ConstructionSignatureProvider,
    CredentialNotUsableError,
)


CONSTRUCTION_TARGET_TEMPLATE_IDS = frozenset(
    {
        "bim_package_exchange_v1",
        "construction_iot_gateway_v1",
        "project_evidence_ledger_v1",
    }
)

CONSTRUCTION_SECURITY_PROFILE_FILENAME = "construction_security_profile.json"
CONSTRUCTION_SECURITY_PROFILES = {
    "baseline": {
        "content_hash_enforced": False,
        "current_version_enforced": False,
        "role_scope_enforced": False,
        "device_registration_enforced": False,
        "telemetry_replay_guard_enforced": False,
    },
    "hardened": {
        "content_hash_enforced": True,
        "current_version_enforced": True,
        "role_scope_enforced": True,
        "device_registration_enforced": True,
        "telemetry_replay_guard_enforced": True,
    },
}


def get_construction_security_profile(profile_name: str) -> dict[str, Any]:
    """Return one named demo control set used for before/after validation."""

    return dict(CONSTRUCTION_SECURITY_PROFILES[profile_name])

CONSTRUCTION_ATTACK_CASES = (
    (
        "ifc_content_tamper",
        "验证 IFC 文件内容被修改后，摘要与签名 manifest 的绑定能否阻断交付。",
        ["ifc_upload", "manifest_verify"],
    ),
    (
        "signed_old_version_rollback",
        "验证签名仍有效的旧 IFC 版本能否绕过当前批准版本约束。",
        ["version_approve", "package_download"],
    ),
    (
        "full_model_overprivilege",
        "验证专业分包能否越权获取未经专业过滤的完整模型。",
        ["package_download", "role_authorization"],
    ),
    (
        "unregistered_device_impersonation",
        "验证未注册设备能否伪造身份并写入可信遥测。",
        ["device_register", "telemetry_ingest", "signature_verify"],
    ),
    (
        "valid_signed_telemetry_replay",
        "验证签名有效的历史遥测能否绕过计数器、nonce 与时间窗口。",
        ["telemetry_ingest", "replay_guard"],
    ),
)


def is_construction_target(target_service: TargetServiceSpecPayload) -> bool:
    """Return whether a target uses one of the local BuildTrust templates."""

    return target_service.template_id in CONSTRUCTION_TARGET_TEMPLATE_IDS


def build_construction_attack_specs(
    *,
    run_id: str,
    target_service: TargetServiceSpecPayload,
) -> list[AttackSpecPayload]:
    """Build the five falsifiable attack contracts used by the BuildTrust demo."""

    return [
        AttackSpecPayload(
            attack_id=f"attack-{run_id[:8]}-construction-{index}",
            target_service_ref=target_service.service_id,
            attack_family=attack_family,
            objective=objective,
            attack_surface=attack_surface,
            expected_artifacts=["attack_result.json", "project_evidence_ledger.json"],
            telemetry_fields=["detected", "blocked", "regression_passed", "evidence_refs"],
            budget={"timeout_s": 30, "cpu_cores": 1, "memory_mb": 128, "probe_count_hint": 1},
            status="planned",
            status_label="待执行",
        )
        for index, (attack_family, objective, attack_surface) in enumerate(
            CONSTRUCTION_ATTACK_CASES,
            start=1,
        )
    ]


def map_construction_demo_results(
    *,
    target_service: TargetServiceSpecPayload,
    attack_specs: list[AttackSpecPayload],
    demo: ConstructionDemoRunResponse,
) -> list[AttackResultPayload]:
    """Map domain evidence into the attack result contract consumed by the MAS loop."""

    specs_by_family = {spec.attack_family: spec for spec in attack_specs}
    results: list[AttackResultPayload] = []
    for domain_result in demo.results:
        spec = specs_by_family[domain_result.attack_type]
        results.append(
            AttackResultPayload(
                attack_id=spec.attack_id,
                target_service_ref=target_service.service_id,
                status="executed",
                status_label="已执行",
                summary=domain_result.summary,
                findings=[domain_result.summary, domain_result.remediation],
                metrics={
                    "case_id": domain_result.case_id,
                    "attack_type": domain_result.attack_type,
                    "detected": domain_result.detected,
                    "blocked": domain_result.blocked,
                    "regression_passed": domain_result.regression_passed,
                    "before_state": domain_result.before_state,
                    "after_state": domain_result.after_state,
                    "evidence_refs": domain_result.evidence_refs,
                    "capability_boundary": demo.capability_boundary,
                    "security_profile": demo.security_profile,
                },
                artifact_refs=[*domain_result.artifact_refs, *demo.evidence_refs],
            )
        )
    return results


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac_sha256(secret: bytes, payload: dict[str, Any]) -> str:
    return hmac.new(secret, _canonical_json(payload), hashlib.sha256).hexdigest()


def _file_ref(path: Path) -> str:
    return "file:" + str(path).replace("\\", "/")


class BIMPackageExchangeRuntime:
    """In-memory IFC manifest, signature, version, approval, and role verifier."""

    def __init__(
        self,
        signer_secrets: dict[str, bytes] | None = None,
        *,
        signature_provider: ConstructionSignatureProvider | None = None,
        signer_credential_refs: dict[str, str] | None = None,
        content_hash_enforced: bool = True,
        current_version_enforced: bool = True,
        role_scope_enforced: bool = True,
    ):
        self.signer_secrets = dict(signer_secrets or {})
        self.signature_provider = signature_provider
        self.signer_credential_refs = dict(signer_credential_refs or {})
        self.content_hash_enforced = content_hash_enforced
        self.current_version_enforced = current_version_enforced
        self.role_scope_enforced = role_scope_enforced
        self.manifests: dict[tuple[str, str], dict[str, Any]] = {}
        self.latest_approved: dict[str, str] = {}

    def register_package(
        self,
        *,
        project_id: str,
        asset_id: str,
        version: str,
        parent_version: str | None,
        content: bytes,
        signer_identity: str,
        approval_state: str,
        allowed_roles: list[str],
    ) -> dict[str, Any]:
        credential_ref = self.signer_credential_refs.get(signer_identity)
        manifest_body = {
            "project_id": project_id,
            "asset_id": asset_id,
            "version": version,
            "parent_version": parent_version,
            "content_hash": _sha256_bytes(content),
            "signer_identity": signer_identity,
            "signer_credential_ref": credential_ref,
            "approval_state": approval_state,
            "allowed_roles": sorted(set(allowed_roles)),
        }
        if self.signature_provider is not None and credential_ref:
            signature, receipt = self.signature_provider.sign(
                credential_ref=credential_ref,
                payload=_canonical_json(manifest_body),
            )
            manifest = {
                **manifest_body,
                "signature_algorithm": receipt.algorithm,
                "signature": signature,
                "signature_operation_ref": receipt.audit_ref,
            }
        else:
            secret = self.signer_secrets[signer_identity]
            manifest = {
                **manifest_body,
                "signature_algorithm": "HMAC-SHA256-DEMO",
                "signature": _hmac_sha256(secret, manifest_body),
            }
        self.manifests[(asset_id, version)] = manifest
        if approval_state == "approved":
            self.latest_approved[asset_id] = version
        return dict(manifest)

    def verify_delivery(
        self,
        *,
        manifest: dict[str, Any],
        content: bytes,
        requester_role: str,
    ) -> dict[str, Any]:
        signer_identity = str(manifest.get("signer_identity") or "")
        secret = self.signer_secrets.get(signer_identity)
        credential_ref = str(manifest.get("signer_credential_ref") or "")
        signature = str(manifest.get("signature") or "")
        body = {
            key: manifest.get(key)
            for key in [
                "project_id",
                "asset_id",
                "version",
                "parent_version",
                "content_hash",
                "signer_identity",
                "signer_credential_ref",
                "approval_state",
                "allowed_roles",
            ]
        }
        key_operation = None
        provider_error = None
        expected_credential_ref = self.signer_credential_refs.get(signer_identity)
        if self.signature_provider is not None and expected_credential_ref:
            if credential_ref != expected_credential_ref:
                signature_valid = False
                provider_error = "signer_credential_ref_mismatch"
            else:
                try:
                    signature_valid, receipt = self.signature_provider.verify(
                        credential_ref=credential_ref,
                        payload=_canonical_json(body),
                        signature=signature,
                    )
                    key_operation = receipt.model_dump(mode="json")
                except CredentialNotUsableError:
                    signature_valid = False
                    provider_error = "signature_provider_operation_failed"
        else:
            signature_valid = bool(secret) and hmac.compare_digest(
                signature,
                _hmac_sha256(secret, body),
            )
        content_valid = hmac.compare_digest(
            str(manifest.get("content_hash") or ""),
            _sha256_bytes(content),
        )
        asset_id = str(manifest.get("asset_id") or "")
        current_version = self.latest_approved.get(asset_id)
        is_current_version = bool(current_version) and manifest.get("version") == current_version
        approval_valid = manifest.get("approval_state") == "approved"
        role_allowed = requester_role in (manifest.get("allowed_roles") or [])
        accepted = all(
            [
                signature_valid,
                content_valid or not self.content_hash_enforced,
                is_current_version or not self.current_version_enforced,
                approval_valid,
                role_allowed or not self.role_scope_enforced,
            ]
        )
        failure_reasons = []
        checks = {
            "signature_valid": signature_valid,
            "content_valid": content_valid,
            "is_current_version": is_current_version,
            "approval_valid": approval_valid,
            "role_allowed": role_allowed,
        }
        for check, passed in checks.items():
            if not passed:
                failure_reasons.append(check)
        return {
            "accepted": accepted,
            "checks": checks,
            "failure_reasons": failure_reasons,
            "current_approved_version": current_version,
            "key_operation": key_operation,
            "provider_error": provider_error,
            "enforced_controls": {
                "content_hash": self.content_hash_enforced,
                "current_version": self.current_version_enforced,
                "role_scope": self.role_scope_enforced,
            },
        }


class ConstructionIoTGatewayRuntime:
    """In-memory device registry and authenticated telemetry freshness gate."""

    def __init__(
        self,
        *,
        freshness_window_seconds: int = 300,
        device_registration_enforced: bool = True,
        replay_guard_enforced: bool = True,
        replay_state: ConstructionIoTReplayState | None = None,
        credential_resolver: Callable[[str], bytes] | None = None,
        mac_provider: ConstructionMACProvider | None = None,
    ):
        self.freshness_window_seconds = freshness_window_seconds
        self.device_registration_enforced = device_registration_enforced
        self.replay_guard_enforced = replay_guard_enforced
        self.replay_state = replay_state
        self.credential_resolver = credential_resolver
        self.mac_provider = mac_provider
        self.device_secrets: dict[str, bytes] = {}
        self.device_credential_refs: dict[str, str] = {}
        self.last_counter: dict[str, int] = {}
        self.used_nonces: set[tuple[str, str]] = set()

    def register_device(
        self,
        device_id: str,
        secret: bytes | None,
        *,
        credential_ref: str | None = None,
    ) -> None:
        if secret is None and not (self.mac_provider and credential_ref):
            raise ValueError("device registration requires secret or MAC provider credential_ref")
        if secret is not None:
            self.device_secrets[device_id] = secret
        if credential_ref:
            self.device_credential_refs[device_id] = credential_ref
        self.last_counter.setdefault(device_id, -1)
        if self.replay_state is not None:
            self.replay_state.register_device(
                device_id=device_id,
                credential_ref=credential_ref or f"memory:{device_id}",
            )

    def sign_telemetry(
        self,
        *,
        device_id: str,
        secret: bytes | None = None,
        credential_ref: str | None = None,
        counter: int,
        nonce: str,
        timestamp: int,
        value: float,
    ) -> dict[str, Any]:
        body = {
            "device_id": device_id,
            "counter": counter,
            "nonce": nonce,
            "timestamp": timestamp,
            "value": value,
        }
        if self.mac_provider is not None and credential_ref:
            signature, receipt = self.mac_provider.generate_mac(
                credential_ref=credential_ref,
                payload=_canonical_json(body),
            )
            return {
                **body,
                "signature": signature,
                "key_operation_ref": receipt.audit_ref,
            }
        if secret is None:
            raise ValueError("telemetry signing requires secret or MAC provider credential_ref")
        return {**body, "signature": _hmac_sha256(secret, body)}

    def ingest(self, message: dict[str, Any], *, now: int) -> dict[str, Any]:
        device_id = str(message.get("device_id") or "")
        credential_ref = self.device_credential_refs.get(device_id)
        if credential_ref is None and self.replay_state is not None:
            credential_ref = self.replay_state.credential_ref(device_id=device_id)
        secret = self.device_secrets.get(device_id)
        if secret is None and self.replay_state is not None and self.credential_resolver:
            if credential_ref:
                secret = self.credential_resolver(credential_ref)
        if secret is None and not (self.mac_provider and credential_ref):
            if not self.device_registration_enforced:
                return {
                    "accepted": True,
                    "signature_valid": False,
                    "freshness_valid": True,
                    "reason": "device_registration_not_enforced",
                }
            return {
                "accepted": False,
                "signature_valid": False,
                "freshness_valid": False,
                "reason": "unknown_device",
            }
        body = {
            key: message.get(key)
            for key in ["device_id", "counter", "nonce", "timestamp", "value"]
        }
        key_operation = None
        if self.mac_provider is not None and credential_ref:
            try:
                signature_valid, receipt = self.mac_provider.verify_mac(
                    credential_ref=credential_ref,
                    payload=_canonical_json(body),
                    mac_value=str(message.get("signature") or ""),
                )
                key_operation = receipt.model_dump(mode="json")
            except CredentialNotUsableError as exc:
                return {
                    "accepted": False,
                    "signature_valid": False,
                    "freshness_valid": False,
                    "reason": "credential_not_usable",
                    "key_operation": (
                        exc.receipt.model_dump(mode="json") if exc.receipt else None
                    ),
                }
        else:
            signature_valid = hmac.compare_digest(
                str(message.get("signature") or ""),
                _hmac_sha256(secret, body),
            )
        counter = int(message.get("counter", -1))
        nonce = str(message.get("nonce") or "")
        timestamp = int(message.get("timestamp", 0))
        if self.replay_state is not None:
            counter_valid, nonce_valid = self.replay_state.peek_freshness(
                device_id=device_id,
                counter=counter,
                nonce=nonce,
            )
        else:
            counter_valid = counter > self.last_counter.get(device_id, -1)
            nonce_valid = bool(nonce) and (device_id, nonce) not in self.used_nonces
        time_valid = abs(now - timestamp) <= self.freshness_window_seconds
        freshness_valid = counter_valid and nonce_valid and time_valid
        accepted = signature_valid and (freshness_valid or not self.replay_guard_enforced)
        if accepted and self.replay_state is not None and self.replay_guard_enforced:
            counter_valid, nonce_valid, accepted = self.replay_state.commit_if_fresh(
                device_id=device_id,
                counter=counter,
                nonce=nonce,
            )
            freshness_valid = counter_valid and nonce_valid and time_valid
        elif accepted:
            self.last_counter[device_id] = counter
            self.used_nonces.add((device_id, nonce))
        reason = "accepted"
        if not signature_valid:
            reason = "invalid_signature"
        elif not freshness_valid:
            reason = "replay_or_stale_message"
        return {
            "accepted": accepted,
            "signature_valid": signature_valid,
            "freshness_valid": freshness_valid,
            "counter_valid": counter_valid,
            "nonce_valid": nonce_valid,
            "time_valid": time_valid,
            "reason": reason,
            "key_operation": key_operation,
            "enforced_controls": {
                "device_registration": self.device_registration_enforced,
                "replay_guard": self.replay_guard_enforced,
            },
        }


class ProjectEvidenceLedgerRuntime:
    """Append-only, signed hash chain used for local evidence replay."""

    def __init__(self, signer_secrets: dict[str, bytes]):
        self.signer_secrets = dict(signer_secrets)
        self.entries: list[dict[str, Any]] = []

    def append(
        self,
        *,
        event_type: str,
        subject_ref: str,
        signer_identity: str,
        payload: dict[str, Any],
        timestamp: int,
    ) -> dict[str, Any]:
        previous_hash = self.entries[-1]["entry_hash"] if self.entries else "GENESIS"
        body = {
            "sequence": len(self.entries) + 1,
            "event_type": event_type,
            "subject_ref": subject_ref,
            "signer_identity": signer_identity,
            "timestamp": timestamp,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        entry_hash = _sha256_bytes(_canonical_json(body))
        entry = {
            **body,
            "entry_hash": entry_hash,
            "signature_algorithm": "HMAC-SHA256-DEMO",
            "signature": _hmac_sha256(self.signer_secrets[signer_identity], body),
        }
        self.entries.append(entry)
        return dict(entry)

    def verify(self) -> dict[str, Any]:
        previous_hash = "GENESIS"
        failures: list[str] = []
        for entry in self.entries:
            body = {
                key: entry.get(key)
                for key in [
                    "sequence",
                    "event_type",
                    "subject_ref",
                    "signer_identity",
                    "timestamp",
                    "payload",
                    "previous_hash",
                ]
            }
            if entry.get("previous_hash") != previous_hash:
                failures.append(f"sequence:{entry.get('sequence')}:previous_hash")
            expected_hash = _sha256_bytes(_canonical_json(body))
            if not hmac.compare_digest(str(entry.get("entry_hash") or ""), expected_hash):
                failures.append(f"sequence:{entry.get('sequence')}:entry_hash")
            secret = self.signer_secrets.get(str(entry.get("signer_identity") or ""))
            if not secret or not hmac.compare_digest(
                str(entry.get("signature") or ""),
                _hmac_sha256(secret, body),
            ):
                failures.append(f"sequence:{entry.get('sequence')}:signature")
            previous_hash = str(entry.get("entry_hash") or "")
        return {
            "valid": not failures,
            "entry_count": len(self.entries),
            "failures": failures,
            "head_hash": previous_hash,
        }


class ConstructionTrustDemoRunner:
    """Execute the five mandatory BuildTrust attacks and persist replay artifacts."""

    capability_boundary = (
        "本地内存演示：HMAC-SHA256 仅用于确定性验真；未接入真实 IFC 语义解析、"
        "PKI/KMS/HSM、数据库、CDE/BIM 平台或多实例防重放状态。"
    )

    def __init__(
        self,
        root_dir: str | Path = ".cache/buildtrust",
        *,
        mac_provider: ConstructionMACProvider | None = None,
        signature_provider: ConstructionSignatureProvider | None = None,
        device_credential_ref: str = "hsm://buildtrust/device-001",
        design_signing_credential_ref: str = "hsm://buildtrust/design-signing-001",
    ):
        self.root_dir = Path(root_dir)
        self.mac_provider = mac_provider
        self.signature_provider = signature_provider
        self.device_credential_ref = device_credential_ref
        self.design_signing_credential_ref = design_signing_credential_ref
        if mac_provider or signature_provider:
            self.capability_boundary = (
                "BIM/IoT 密码操作通过 localhost provider 合同执行并生成审计回执；"
                "密钥仍驻留本机进程内存，项目证据账本仍为 HMAC 演示，且未接商业 CDE。"
            )

    def run(
        self,
        *,
        project_id: str,
        run_id: str | None = None,
        security_profile: str = "hardened",
    ) -> ConstructionDemoRunResponse:
        resolved_run_id = run_id or f"buildtrust-{uuid4().hex[:12]}"
        workspace = self.root_dir / resolved_run_id
        workspace.mkdir(parents=True, exist_ok=True)
        now = int(time.time())
        controls = get_construction_security_profile(security_profile)

        design_secret = b"buildtrust-demo-design-signer-v1"
        ledger_secret = b"buildtrust-demo-ledger-signer-v1"
        device_secret = b"buildtrust-demo-device-v1"
        bim = BIMPackageExchangeRuntime(
            ({"design-cert-001": design_secret} if self.signature_provider is None else None),
            signature_provider=self.signature_provider,
            signer_credential_refs=(
                {"design-cert-001": self.design_signing_credential_ref}
                if self.signature_provider
                else None
            ),
            content_hash_enforced=controls["content_hash_enforced"],
            current_version_enforced=controls["current_version_enforced"],
            role_scope_enforced=controls["role_scope_enforced"],
        )
        ledger = ProjectEvidenceLedgerRuntime({"supervisor-cert-001": ledger_secret})
        iot = ConstructionIoTGatewayRuntime(
            freshness_window_seconds=300,
            device_registration_enforced=controls["device_registration_enforced"],
            replay_guard_enforced=controls["telemetry_replay_guard_enforced"],
            mac_provider=self.mac_provider,
        )
        iot.register_device(
            "sensor-concrete-001",
            device_secret if self.mac_provider is None else None,
            credential_ref=(self.device_credential_ref if self.mac_provider else None),
        )

        content_v2 = b"ISO-10303-21;IFC-DEMO;VERSION=2;BEAM=300x500;ENDSEC;"
        content_v3 = b"ISO-10303-21;IFC-DEMO;VERSION=3;BEAM=350x550;ENDSEC;"
        manifest_v2 = bim.register_package(
            project_id=project_id,
            asset_id="ifc-main-model",
            version="v2",
            parent_version="v1",
            content=content_v2,
            signer_identity="design-cert-001",
            approval_state="approved",
            allowed_roles=["general_contractor", "supervisor"],
        )
        manifest_v3 = bim.register_package(
            project_id=project_id,
            asset_id="ifc-main-model",
            version="v3",
            parent_version="v2",
            content=content_v3,
            signer_identity="design-cert-001",
            approval_state="approved",
            allowed_roles=["general_contractor", "supervisor"],
        )

        results: list[ConstructionAttackResultPayload] = []
        tampered = content_v3.replace(b"350x550", b"250x400")
        tamper_check = bim.verify_delivery(
            manifest=manifest_v3,
            content=tampered,
            requester_role="general_contractor",
        )
        original_check = bim.verify_delivery(
            manifest=manifest_v3,
            content=content_v3,
            requester_role="general_contractor",
        )
        results.append(
            self._result(
                case_id="bim_ifc_tamper",
                attack_type="ifc_content_tamper",
                summary=(
                    "IFC 内容摘要不一致，交付被阻断。"
                    if not tamper_check["accepted"]
                    else "基线未强制内容摘要，篡改后的 IFC 被接受。"
                ),
                before_state={"tampered_delivery": tamper_check},
                after_state={"original_delivery": original_check},
                remediation="仅允许摘要、签名、批准状态和当前版本同时通过的 IFC 进入交付。",
                attack_blocked=not tamper_check["accepted"],
                regression_passed=original_check["accepted"] and not tamper_check["accepted"],
                workspace=workspace,
            )
        )

        rollback_check = bim.verify_delivery(
            manifest=manifest_v2,
            content=content_v2,
            requester_role="general_contractor",
        )
        current_check = bim.verify_delivery(
            manifest=manifest_v3,
            content=content_v3,
            requester_role="general_contractor",
        )
        results.append(
            self._result(
                case_id="bim_version_rollback",
                attack_type="signed_old_version_rollback",
                summary=(
                    "v2 签名有效但不是当前批准版本，旧文件回滚被阻断。"
                    if not rollback_check["accepted"]
                    else "基线未强制当前批准版本，合法旧文件回滚成功。"
                ),
                before_state={"v2_delivery": rollback_check},
                after_state={"v3_delivery": current_check},
                remediation="验签必须同时绑定父版本链、批准状态和当前批准版本指针。",
                attack_blocked=not rollback_check["accepted"],
                regression_passed=current_check["accepted"] and not rollback_check["accepted"],
                workspace=workspace,
            )
        )

        overprivilege_check = bim.verify_delivery(
            manifest=manifest_v3,
            content=content_v3,
            requester_role="specialty_subcontractor",
        )
        results.append(
            self._result(
                case_id="subcontractor_overprivilege",
                attack_type="full_model_overprivilege",
                summary=(
                    "专业分包不在允许角色中，完整模型请求被拒绝。"
                    if not overprivilege_check["accepted"]
                    else "基线未强制角色范围，专业分包获得了完整模型。"
                ),
                before_state={"full_model_request": overprivilege_check},
                after_state={"delivery_action": "generate_discipline_filtered_package"},
                remediation="为专业分包生成独立数据密钥和专业过滤交付包。",
                attack_blocked=not overprivilege_check["accepted"],
                regression_passed=not overprivilege_check["accepted"],
                workspace=workspace,
            )
        )

        fake_message = iot.sign_telemetry(
            device_id="sensor-fake-999",
            secret=b"attacker-secret",
            counter=1,
            nonce="fake-nonce-1",
            timestamp=now,
            value=22.5,
        )
        impersonation_check = iot.ingest(fake_message, now=now)
        valid_message = iot.sign_telemetry(
            device_id="sensor-concrete-001",
            secret=(device_secret if self.mac_provider is None else None),
            credential_ref=(self.device_credential_ref if self.mac_provider else None),
            counter=1,
            nonce="nonce-1",
            timestamp=now,
            value=23.1,
        )
        valid_ingest = iot.ingest(valid_message, now=now)
        results.append(
            self._result(
                case_id="iot_device_impersonation",
                attack_type="unregistered_device_impersonation",
                summary=(
                    "未注册设备无法建立可信身份，遥测被拒绝。"
                    if not impersonation_check["accepted"]
                    else "基线未强制设备注册，冒充设备遥测被接受。"
                ),
                before_state={"fake_device_ingest": impersonation_check},
                after_state={"registered_device_ingest": valid_ingest},
                remediation="要求每台设备独立注册、独立凭据并支持撤销与轮换。",
                attack_blocked=not impersonation_check["accepted"],
                regression_passed=valid_ingest["accepted"] and not impersonation_check["accepted"],
                workspace=workspace,
            )
        )

        replay_check = iot.ingest(valid_message, now=now)
        fresh_message = iot.sign_telemetry(
            device_id="sensor-concrete-001",
            secret=(device_secret if self.mac_provider is None else None),
            credential_ref=(self.device_credential_ref if self.mac_provider else None),
            counter=2,
            nonce="nonce-2",
            timestamp=now + 1,
            value=23.2,
        )
        fresh_ingest = iot.ingest(fresh_message, now=now + 1)
        results.append(
            self._result(
                case_id="iot_telemetry_replay",
                attack_type="valid_signed_telemetry_replay",
                summary=(
                    "历史消息签名仍有效，但新鲜度验证阻断了重放。"
                    if not replay_check["accepted"]
                    else "基线未强制遥测新鲜度，签名有效的历史消息被再次接受。"
                ),
                before_state={"replayed_message": replay_check},
                after_state={"fresh_message": fresh_ingest},
                remediation="持久化每设备计数器、nonce 和时间窗口，并将重放与签名失败分开记录。",
                attack_blocked=not replay_check["accepted"],
                regression_passed=fresh_ingest["accepted"] and not replay_check["accepted"],
                workspace=workspace,
            )
        )

        for result in results:
            ledger.append(
                event_type="attack_validation",
                subject_ref=result.case_id,
                signer_identity="supervisor-cert-001",
                timestamp=now,
                payload={
                    "detected": result.detected,
                    "blocked": result.blocked,
                    "regression_passed": result.regression_passed,
                    "artifact_refs": result.artifact_refs,
                },
            )
        ledger_verification = ledger.verify()
        ledger_path = workspace / "project_evidence_ledger.json"
        ledger_path.write_text(
            json.dumps(
                {"entries": ledger.entries, "verification": ledger_verification},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        summary_path = workspace / "buildtrust_demo_summary.json"
        summary_payload = {
            "run_id": resolved_run_id,
            "project_id": project_id,
            "security_profile": security_profile,
            "crypto_provider_mode": (
                "localhost_provider"
                if self.mac_provider or self.signature_provider
                else "local_demo"
            ),
            "provider_mac_enabled": self.mac_provider is not None,
            "provider_signature_enabled": self.signature_provider is not None,
            "security_controls": controls,
            "capability_boundary": self.capability_boundary,
            "attack_count": len(results),
            "detected_count": sum(item.detected for item in results),
            "blocked_count": sum(item.blocked for item in results),
            "regression_passed_count": sum(item.regression_passed for item in results),
            "ledger_verification": ledger_verification,
            "results": [item.model_dump(mode="json") for item in results],
        }
        summary_path.write_text(
            json.dumps(summary_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return ConstructionDemoRunResponse(
            run_id=resolved_run_id,
            project_id=project_id,
            status="completed",
            security_profile=security_profile,
            crypto_provider_mode=(
                "localhost_provider"
                if self.mac_provider or self.signature_provider
                else "local_demo"
            ),
            provider_mac_enabled=self.mac_provider is not None,
            provider_signature_enabled=self.signature_provider is not None,
            capability_boundary=self.capability_boundary,
            workspace=str(workspace).replace("\\", "/"),
            attack_count=len(results),
            detected_count=sum(item.detected for item in results),
            blocked_count=sum(item.blocked for item in results),
            regression_passed_count=sum(item.regression_passed for item in results),
            evidence_ledger_valid=ledger_verification["valid"],
            evidence_refs=[
                _file_ref(ledger_path),
                _file_ref(summary_path),
            ],
            results=results,
        )

    def _result(
        self,
        *,
        case_id: str,
        attack_type: str,
        summary: str,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        remediation: str,
        attack_blocked: bool,
        regression_passed: bool,
        workspace: Path,
    ) -> ConstructionAttackResultPayload:
        artifact_path = workspace / f"{case_id}.json"
        payload = {
            "case_id": case_id,
            "attack_type": attack_type,
            "summary": summary,
            "before_state": before_state,
            "after_state": after_state,
            "remediation": remediation,
            "attack_blocked": attack_blocked,
            "regression_passed": regression_passed,
        }
        artifact_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        artifact_ref = _file_ref(artifact_path)
        evidence_digest = _sha256_bytes(_canonical_json(payload))
        return ConstructionAttackResultPayload(
            case_id=case_id,
            attack_type=attack_type,
            detected=attack_blocked,
            blocked=attack_blocked,
            severity="high",
            summary=summary,
            before_state=before_state,
            after_state=after_state,
            remediation=remediation,
            regression_passed=regression_passed,
            evidence_refs=[f"sha256:{evidence_digest}"],
            artifact_refs=[artifact_ref],
        )
