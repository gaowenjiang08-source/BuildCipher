"""Application service for the localhost BuildCipher construction demonstration."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from cipher_genius.api.schemas import (
    ConstructionDemoRunRequest,
    ConstructionDemoRunResponse,
    ConstructionIFCImportResponse,
)
from cipher_genius.integrations.construction import (
    LocalReferenceHMACProvider,
    SQLiteCredentialGovernanceStore,
    inspect_ifc_bytes,
)
from cipher_genius.models.construction import (
    ApprovalState,
    AssetSensitivity,
    ConstructionAsset,
    ConstructionAssetType,
    ConstructionCredentialGovernanceRecord,
    ConstructionLifecyclePhase,
    ConstructionPartyRole,
    IFCInspectionResult,
)
from cipher_genius.sandbox.construction_runtime import ConstructionTrustDemoRunner
from cipher_genius.utils.config import get_settings

LOCAL_PROVIDER_ID = "buildcipher-localhost-provider"
DESIGN_CREDENTIAL_REF = "local://buildcipher/design-signing-001"
DEVICE_CREDENTIAL_REF = "local://buildcipher/device-mac-001"
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
_MAX_IFC_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class ResolvedConstructionIFCImport:
    asset_ref: str
    asset: ConstructionAsset
    inspection: IFCInspectionResult
    content: bytes


class ConstructionIFCImportService:
    """Validate and persist IFC bytes inside the localhost workspace boundary."""

    capability_boundary = (
        "本地 IFC STEP 文件结构检查与字节级摘要；不执行几何、碰撞、规范或完整 IFC 语义校核。"
    )

    def __init__(self, root_dir: str | Path | None = None):
        settings = get_settings()
        self.root_dir = Path(root_dir or settings.buildcipher_construction_import_root)

    def import_ifc(
        self,
        *,
        content: bytes,
        original_filename: str,
        project_id: str,
        asset_id: str,
        version: str,
        parent_version: str | None = None,
        approval_state: ApprovalState = ApprovalState.APPROVED,
    ) -> ConstructionIFCImportResponse:
        for field_name, value in (
            ("project_id", project_id),
            ("asset_id", asset_id),
            ("version", version),
        ):
            if not _SAFE_IDENTIFIER.fullmatch(value):
                raise ValueError(f"{field_name} 只能包含字母、数字、点、下划线或连字符")
        if parent_version and not _SAFE_IDENTIFIER.fullmatch(parent_version):
            raise ValueError("parent_version 只能包含字母、数字、点、下划线或连字符")
        if parent_version == version:
            raise ValueError("parent_version 不能与当前 version 相同")

        safe_filename = Path(original_filename or "").name
        if not safe_filename.lower().endswith(".ifc"):
            raise ValueError("仅支持 .ifc 文件")
        if not content:
            raise ValueError("IFC 文件为空")
        if len(content) > _MAX_IFC_BYTES:
            raise ValueError("IFC 文件超过 localhost 演示上限 50 MiB")

        import_id = f"ifc-{uuid4().hex[:16]}"
        asset_ref = f"construction-import://{project_id}/{import_id}"
        inspection = inspect_ifc_bytes(content, source_ref=asset_ref)
        if not inspection.valid:
            raise ValueError("IFC 结构检查失败：" + ", ".join(inspection.parse_errors))

        imported_at = datetime.now(timezone.utc).isoformat()
        try:
            normalized_approval_state = ApprovalState(approval_state)
        except ValueError as exc:
            raise ValueError(
                "approval_state 必须是 draft、in_review、approved、rejected 或 superseded"
            ) from exc
        asset = ConstructionAsset(
            asset_id=asset_id,
            asset_type=ConstructionAssetType.IFC_MODEL,
            project_id=project_id,
            lifecycle_phase=ConstructionLifecyclePhase.DESIGN,
            owner_org="localhost-import",
            sensitivity=AssetSensitivity.CONFIDENTIAL,
            version=version,
            parent_version=parent_version,
            content_hash=inspection.content_sha256,
            approval_state=normalized_approval_state,
            allowed_roles=[
                ConstructionPartyRole.GENERAL_CONTRACTOR,
                ConstructionPartyRole.SUPERVISOR,
            ],
        )
        import_dir = self.root_dir / project_id / import_id
        import_dir.mkdir(parents=True, exist_ok=False)
        file_path = import_dir / safe_filename
        file_path.write_bytes(content)
        stored_ref = str(file_path).replace("\\", "/")
        response = ConstructionIFCImportResponse(
            import_id=import_id,
            asset_ref=asset_ref,
            imported_at=imported_at,
            original_filename=safe_filename,
            stored_ref=stored_ref,
            asset=asset,
            inspection=inspection,
            capability_boundary=self.capability_boundary,
        )
        (import_dir / "import.json").write_text(
            json.dumps(response.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return response

    def resolve(self, asset_ref: str) -> ResolvedConstructionIFCImport:
        prefix = "construction-import://"
        if not asset_ref.startswith(prefix):
            raise ValueError("asset_ref 必须是 construction-import:// 本地引用")
        parts = asset_ref[len(prefix) :].split("/")
        if len(parts) != 2 or not all(_SAFE_IDENTIFIER.fullmatch(part) for part in parts):
            raise ValueError("asset_ref 格式无效")
        project_id, import_id = parts
        import_dir = self.root_dir / project_id / import_id
        descriptor_path = import_dir / "import.json"
        if not descriptor_path.is_file():
            raise ValueError("找不到对应的本地 IFC 导入记录")
        descriptor = ConstructionIFCImportResponse.model_validate_json(
            descriptor_path.read_text(encoding="utf-8")
        )
        if descriptor.asset_ref != asset_ref:
            raise ValueError("IFC 导入引用与元数据不一致")
        file_path = Path(descriptor.stored_ref)
        if not file_path.is_file() or file_path.parent.resolve() != import_dir.resolve():
            raise ValueError("IFC 导入文件不存在或不在声明目录中")
        content = file_path.read_bytes()
        inspection = inspect_ifc_bytes(content, source_ref=asset_ref)
        if not inspection.valid or inspection.content_sha256 != descriptor.asset.content_hash:
            raise ValueError("IFC 导入文件在落盘后发生变化")
        return ResolvedConstructionIFCImport(
            asset_ref=asset_ref,
            asset=descriptor.asset,
            inspection=inspection,
            content=content,
        )


class ConstructionDemoService:
    def __init__(
        self,
        runner: ConstructionTrustDemoRunner | None = None,
        import_service: ConstructionIFCImportService | None = None,
    ):
        self.runner = runner or self._build_localhost_runner()
        self.import_service = import_service or ConstructionIFCImportService()

    @staticmethod
    def _build_localhost_runner() -> ConstructionTrustDemoRunner:
        settings = get_settings()
        governance_store = SQLiteCredentialGovernanceStore(
            settings.buildcipher_governance_database_path
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
                    project_id="buildcipher-localhost",
                    owner_ref=owner_ref,
                    purpose=purpose,
                    algorithm="HMAC-SHA256",
                    provider_id=LOCAL_PROVIDER_ID,
                    provider_kind="local_reference",
                    key_version="v1",
                    created_at=now,
                    activated_at=now,
                    policy_refs=["policy:buildcipher-localhost-demo"],
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
        imported = (
            self.import_service.resolve(payload.asset_ref)
            if payload.asset_ref
            else None
        )
        if imported and imported.asset.project_id != payload.project_id:
            raise ValueError("asset_ref 所属项目与 project_id 不一致")
        run_kwargs = {
            "project_id": payload.project_id,
            "ifc_content": imported.content if imported else None,
            "ifc_asset": imported.asset if imported else None,
            "ifc_inspection": imported.inspection if imported else None,
            "asset_ref": imported.asset_ref if imported else None,
        }
        if payload.mode == "hardened":
            return self.runner.run(
                **run_kwargs,
                run_id=payload.run_id,
                security_profile="hardened",
            )

        comparison_run_id = payload.run_id or f"buildcipher-{uuid4().hex[:12]}"
        baseline = self.runner.run(
            **run_kwargs,
            run_id=f"{comparison_run_id}-baseline",
            security_profile="baseline",
        )
        hardened = self.runner.run(
            **run_kwargs,
            run_id=f"{comparison_run_id}-hardened",
            security_profile="hardened",
        )
        comparison_verified = (
            baseline.attack_count == hardened.attack_count == 5
            and baseline.blocked_count < hardened.blocked_count
            and hardened.blocked_count == hardened.attack_count
        )
        return hardened.model_copy(
            update={
                "run_id": comparison_run_id,
                "comparison_verified": comparison_verified,
                "baseline_blocked_count": baseline.blocked_count,
                "hardened_blocked_count": hardened.blocked_count,
                "baseline_workspace": baseline.workspace,
                "hardened_workspace": hardened.workspace,
                "baseline_results": baseline.results,
                "evidence_refs": [*baseline.evidence_refs, *hardened.evidence_refs],
            }
        )
