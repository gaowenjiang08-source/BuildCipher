"""Non-exporting cryptographic operation contracts and governance receipts."""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from cipher_genius.models.construction import (
    CertificateLifecycleState,
    ConstructionCertificateGovernanceRecord,
    ConstructionCredentialGovernanceRecord,
    ConstructionCryptoGovernanceAssessment,
    ConstructionKeyOperationReceipt,
    CredentialLifecycleState,
)


class CredentialNotUsableError(RuntimeError):
    """Raised when a credential is missing or not active for an operation."""

    def __init__(
        self,
        message: str,
        *,
        receipt: ConstructionKeyOperationReceipt | None = None,
    ):
        super().__init__(message)
        self.receipt = receipt


class ConstructionMACProvider(Protocol):
    """Provider-side MAC operations; callers never request raw key bytes."""

    def generate_mac(
        self,
        *,
        credential_ref: str,
        payload: bytes,
    ) -> tuple[str, ConstructionKeyOperationReceipt]: ...

    def verify_mac(
        self,
        *,
        credential_ref: str,
        payload: bytes,
        mac_value: str,
    ) -> tuple[bool, ConstructionKeyOperationReceipt]: ...


class ConstructionSignatureProvider(Protocol):
    """Contract for KMS/HSM-backed asymmetric signing without key export."""

    def sign(
        self,
        *,
        credential_ref: str,
        payload: bytes,
    ) -> tuple[str, ConstructionKeyOperationReceipt]: ...

    def verify(
        self,
        *,
        credential_ref: str,
        payload: bytes,
        signature: str,
    ) -> tuple[bool, ConstructionKeyOperationReceipt]: ...


class SQLiteCredentialGovernanceStore:
    """Persist credential metadata and secret-free operation receipts."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS construction_credentials (
                    credential_ref TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS construction_key_operations (
                    operation_id TEXT PRIMARY KEY,
                    credential_ref TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_construction_key_operations_credential
                ON construction_key_operations(credential_ref, occurred_at);
                CREATE TABLE IF NOT EXISTS construction_certificates (
                    certificate_ref TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path, timeout=10)

    def save_credential(self, record: ConstructionCredentialGovernanceRecord) -> None:
        payload_json = json.dumps(record.model_dump(mode="json"), ensure_ascii=False)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO construction_credentials(credential_ref, payload_json)
                VALUES (?, ?)
                ON CONFLICT(credential_ref) DO UPDATE SET payload_json = excluded.payload_json
                """,
                (record.credential_ref, payload_json),
            )
            connection.commit()

    def get_credential(
        self,
        credential_ref: str,
    ) -> ConstructionCredentialGovernanceRecord | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM construction_credentials WHERE credential_ref = ?",
                (credential_ref,),
            ).fetchone()
        if row is None:
            return None
        return ConstructionCredentialGovernanceRecord.model_validate_json(row[0])

    def append_operation(self, receipt: ConstructionKeyOperationReceipt) -> None:
        payload_json = json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO construction_key_operations(
                    operation_id,
                    credential_ref,
                    occurred_at,
                    payload_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    receipt.operation_id,
                    receipt.credential_ref,
                    receipt.occurred_at,
                    payload_json,
                ),
            )
            connection.commit()

    def save_certificate(self, record: ConstructionCertificateGovernanceRecord) -> None:
        payload_json = json.dumps(record.model_dump(mode="json"), ensure_ascii=False)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO construction_certificates(certificate_ref, payload_json)
                VALUES (?, ?)
                ON CONFLICT(certificate_ref) DO UPDATE SET payload_json = excluded.payload_json
                """,
                (record.certificate_ref, payload_json),
            )
            connection.commit()

    def get_certificate(
        self,
        certificate_ref: str,
    ) -> ConstructionCertificateGovernanceRecord | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM construction_certificates WHERE certificate_ref = ?",
                (certificate_ref,),
            ).fetchone()
        if row is None:
            return None
        return ConstructionCertificateGovernanceRecord.model_validate_json(row[0])

    def assess(self, *, assessed_at: str) -> ConstructionCryptoGovernanceAssessment:
        assessment_time = datetime.fromisoformat(assessed_at.replace("Z", "+00:00"))
        with closing(self._connect()) as connection:
            credential_rows = connection.execute(
                "SELECT payload_json FROM construction_credentials"
            ).fetchall()
            certificate_rows = connection.execute(
                "SELECT payload_json FROM construction_certificates"
            ).fetchall()
        credentials = [
            ConstructionCredentialGovernanceRecord.model_validate_json(row[0])
            for row in credential_rows
        ]
        certificates = [
            ConstructionCertificateGovernanceRecord.model_validate_json(row[0])
            for row in certificate_rows
        ]
        rotation_due_refs = sorted(
            record.credential_ref
            for record in credentials
            if record.next_rotation_at
            and datetime.fromisoformat(record.next_rotation_at.replace("Z", "+00:00"))
            <= assessment_time
        )
        inactive_credential_refs = sorted(
            record.credential_ref
            for record in credentials
            if record.lifecycle_state is not CredentialLifecycleState.ACTIVE
        )
        expiring_certificate_refs = sorted(
            record.certificate_ref
            for record in certificates
            if record.lifecycle_state is CertificateLifecycleState.EXPIRING
        )
        invalid_certificate_refs = sorted(
            record.certificate_ref
            for record in certificates
            if record.lifecycle_state
            in {CertificateLifecycleState.EXPIRED, CertificateLifecycleState.REVOKED}
            or datetime.fromisoformat(record.not_after.replace("Z", "+00:00"))
            <= assessment_time
        )
        return ConstructionCryptoGovernanceAssessment(
            assessed_at=assessed_at,
            credential_count=len(credentials),
            rotation_due_refs=rotation_due_refs,
            inactive_credential_refs=inactive_credential_refs,
            certificate_count=len(certificates),
            expiring_certificate_refs=expiring_certificate_refs,
            invalid_certificate_refs=invalid_certificate_refs,
        )

    def list_operations(
        self,
        *,
        credential_ref: str,
    ) -> list[ConstructionKeyOperationReceipt]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM construction_key_operations
                WHERE credential_ref = ?
                ORDER BY occurred_at, operation_id
                """,
                (credential_ref,),
            ).fetchall()
        return [ConstructionKeyOperationReceipt.model_validate_json(row[0]) for row in rows]


class LocalReferenceHMACProvider:
    """In-process reference provider for local MAC and manifest signing contracts."""

    provider_kind = "local_reference"
    algorithm = "HMAC-SHA256-REFERENCE"
    capability_boundary = (
        "本地参考提供者：密钥不通过操作接口导出，但仍驻留应用进程内存；"
        "用于验证 KMS/HSM 合同、生命周期门禁和审计回执，不是生产 HSM。"
    )

    def __init__(
        self,
        *,
        provider_id: str,
        governance_store: SQLiteCredentialGovernanceStore,
    ):
        self.provider_id = provider_id
        self.governance_store = governance_store
        self._key_material: dict[str, bytes] = {}

    def register_key(
        self,
        *,
        record: ConstructionCredentialGovernanceRecord,
        key_material: bytes,
    ) -> None:
        if record.provider_id != self.provider_id:
            raise ValueError("credential provider_id does not match provider")
        if record.algorithm not in {"HMAC-SHA256", self.algorithm}:
            raise ValueError("credential algorithm is not supported by provider")
        if not key_material:
            raise ValueError("HMAC key material must not be empty")
        self._key_material[record.credential_ref] = bytes(key_material)
        self.governance_store.save_credential(record)

    def generate_mac(
        self,
        *,
        credential_ref: str,
        payload: bytes,
    ) -> tuple[str, ConstructionKeyOperationReceipt]:
        record, key_material = self._active_material(
            credential_ref,
            operation="mac_generate",
            payload=payload,
        )
        mac_value = hmac.new(key_material, payload, hashlib.sha256).hexdigest()
        receipt = self._receipt(
            operation="mac_generate",
            record=record,
            payload=payload,
        )
        return mac_value, receipt

    def verify_mac(
        self,
        *,
        credential_ref: str,
        payload: bytes,
        mac_value: str,
    ) -> tuple[bool, ConstructionKeyOperationReceipt]:
        record, key_material = self._active_material(
            credential_ref,
            operation="mac_verify",
            payload=payload,
        )
        expected = hmac.new(key_material, payload, hashlib.sha256).hexdigest()
        verified = hmac.compare_digest(mac_value, expected)
        receipt = self._receipt(
            operation="mac_verify",
            record=record,
            payload=payload,
            verification_result=verified,
        )
        return verified, receipt

    def sign(
        self,
        *,
        credential_ref: str,
        payload: bytes,
    ) -> tuple[str, ConstructionKeyOperationReceipt]:
        record, key_material = self._active_material(
            credential_ref,
            operation="signature_sign",
            payload=payload,
        )
        signature = hmac.new(key_material, payload, hashlib.sha256).hexdigest()
        receipt = self._receipt(
            operation="signature_sign",
            record=record,
            payload=payload,
        )
        return signature, receipt

    def verify(
        self,
        *,
        credential_ref: str,
        payload: bytes,
        signature: str,
    ) -> tuple[bool, ConstructionKeyOperationReceipt]:
        record, key_material = self._active_material(
            credential_ref,
            operation="signature_verify",
            payload=payload,
        )
        expected = hmac.new(key_material, payload, hashlib.sha256).hexdigest()
        verified = hmac.compare_digest(signature, expected)
        receipt = self._receipt(
            operation="signature_verify",
            record=record,
            payload=payload,
            verification_result=verified,
        )
        return verified, receipt

    def _active_material(
        self,
        credential_ref: str,
        *,
        operation: str,
        payload: bytes,
    ) -> tuple[ConstructionCredentialGovernanceRecord, bytes]:
        record = self.governance_store.get_credential(credential_ref)
        key_material = self._key_material.get(credential_ref)
        if record is None or key_material is None:
            receipt = self._rejected_receipt(
                operation=operation,
                credential_ref=credential_ref,
                payload=payload,
                key_version=record.key_version if record else "unknown",
            )
            raise CredentialNotUsableError(
                "credential is not available in provider",
                receipt=receipt,
            )
        if record.lifecycle_state is not CredentialLifecycleState.ACTIVE:
            receipt = self._rejected_receipt(
                operation=operation,
                credential_ref=credential_ref,
                payload=payload,
                key_version=record.key_version,
            )
            raise CredentialNotUsableError(
                f"credential lifecycle state is {record.lifecycle_state.value}",
                receipt=receipt,
            )
        return record, key_material

    def _rejected_receipt(
        self,
        *,
        operation: str,
        credential_ref: str,
        payload: bytes,
        key_version: str,
    ) -> ConstructionKeyOperationReceipt:
        operation_id = f"keyop-{uuid4().hex}"
        receipt = ConstructionKeyOperationReceipt(
            operation_id=operation_id,
            operation=operation,
            credential_ref=credential_ref,
            provider_id=self.provider_id,
            provider_kind=self.provider_kind,
            algorithm=self.algorithm,
            key_version=key_version,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            input_sha256=hashlib.sha256(payload).hexdigest(),
            status="rejected",
            audit_ref=f"sqlite:key_operations:{operation_id}",
        )
        self.governance_store.append_operation(receipt)
        return receipt

    def _receipt(
        self,
        *,
        operation: str,
        record: ConstructionCredentialGovernanceRecord,
        payload: bytes,
        verification_result: bool | None = None,
    ) -> ConstructionKeyOperationReceipt:
        operation_id = f"keyop-{uuid4().hex}"
        receipt = ConstructionKeyOperationReceipt(
            operation_id=operation_id,
            operation=operation,
            credential_ref=record.credential_ref,
            provider_id=self.provider_id,
            provider_kind=self.provider_kind,
            algorithm=self.algorithm,
            key_version=record.key_version,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            input_sha256=hashlib.sha256(payload).hexdigest(),
            status="executed",
            verification_result=verification_result,
            audit_ref=f"sqlite:key_operations:{operation_id}",
        )
        self.governance_store.append_operation(receipt)
        return receipt
