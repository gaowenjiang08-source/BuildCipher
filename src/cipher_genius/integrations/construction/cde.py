"""Provider-neutral CDE connector contract and a local directory adapter."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from cipher_genius.integrations.construction.ifc import inspect_ifc_bytes
from cipher_genius.models.construction import (
    CDEConnectorStatus,
    CDEPackageDescriptor,
    IFCInspectionResult,
)


class ConstructionCDEConnector(Protocol):
    """Minimum read-only contract required by BuildTrust ingestion."""

    def status(self) -> CDEConnectorStatus: ...

    def list_packages(self, *, project_id: str) -> list[CDEPackageDescriptor]: ...

    def read_package(self, *, package_id: str) -> bytes: ...

    def inspect_package(self, *, package_id: str) -> IFCInspectionResult: ...


class LocalDirectoryCDEConnector:
    """Read IFC packages from a project-scoped directory using the CDE contract."""

    capability_boundary = (
        "本地只读目录适配器：用于验证 CDE 连接器合同和真实 IFC 文件摄取；"
        "不提供远程认证、签批工作流、锁定、上传或供应商 API 语义。"
    )

    def __init__(self, root_dir: str | Path, *, connector_id: str = "local-cde"):
        self.root_dir = Path(root_dir).resolve()
        self.connector_id = connector_id

    def status(self) -> CDEConnectorStatus:
        return CDEConnectorStatus(
            connector_id=self.connector_id,
            connector_kind="local_directory",
            available=self.root_dir.is_dir(),
            root_ref=str(self.root_dir).replace("\\", "/"),
            capability_boundary=self.capability_boundary,
        )

    def list_packages(self, *, project_id: str) -> list[CDEPackageDescriptor]:
        project_dir = self._resolve_relative(project_id)
        if not project_dir.is_dir():
            return []
        packages = []
        for path in sorted(project_dir.rglob("*.ifc")):
            data = path.read_bytes()
            stat = path.stat()
            relative_path = path.relative_to(self.root_dir).as_posix()
            packages.append(
                CDEPackageDescriptor(
                    package_id=relative_path,
                    project_id=project_id,
                    relative_path=relative_path,
                    connector_id=self.connector_id,
                    connector_kind="local_directory",
                    byte_count=len(data),
                    content_sha256=hashlib.sha256(data).hexdigest(),
                    modified_at=datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=timezone.utc,
                    ).isoformat(),
                )
            )
        return packages

    def read_package(self, *, package_id: str) -> bytes:
        package_path = self._resolve_relative(package_id)
        if package_path.suffix.lower() != ".ifc" or not package_path.is_file():
            raise FileNotFoundError(package_id)
        return package_path.read_bytes()

    def inspect_package(self, *, package_id: str) -> IFCInspectionResult:
        return inspect_ifc_bytes(
            self.read_package(package_id=package_id),
            source_ref=f"cde:{self.connector_id}:{package_id}",
        )

    def _resolve_relative(self, relative_ref: str) -> Path:
        candidate = (self.root_dir / relative_ref).resolve()
        try:
            candidate.relative_to(self.root_dir)
        except ValueError as exc:
            raise ValueError("CDE reference escapes connector root") from exc
        return candidate
