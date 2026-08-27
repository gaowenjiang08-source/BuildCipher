from pathlib import Path

import pytest

from cipher_genius.api.construction_service import (
    ConstructionDemoService,
    ConstructionIFCImportService,
)
from cipher_genius.api.schemas import ConstructionDemoRunRequest
from cipher_genius.sandbox.construction_runtime import ConstructionTrustDemoRunner


def _demo_ifc_bytes() -> bytes:
    return Path("data/demo/buildtrust_v1/coordination.ifc").read_bytes()


def test_ifc_import_validates_and_resolves_local_asset(tmp_path: Path):
    service = ConstructionIFCImportService(tmp_path / "imports")
    imported = service.import_ifc(
        content=_demo_ifc_bytes(),
        original_filename="coordination.ifc",
        project_id="project-001",
        asset_id="ifc-main-model",
        version="v3",
        parent_version="v2",
    )

    resolved = service.resolve(imported.asset_ref)

    assert imported.inspection.valid is True
    assert imported.inspection.schema_identifiers == ["IFC4"]
    assert imported.inspection.entity_count == 3
    assert resolved.content == _demo_ifc_bytes()
    assert resolved.asset.content_hash == imported.inspection.content_sha256


def test_ifc_import_rejects_non_ifc_structure(tmp_path: Path):
    service = ConstructionIFCImportService(tmp_path / "imports")

    with pytest.raises(ValueError, match="IFC 结构检查失败"):
        service.import_ifc(
            content=b"not an IFC file",
            original_filename="invalid.ifc",
            project_id="project-001",
            asset_id="ifc-main-model",
            version="v3",
        )


def test_compare_demo_consumes_imported_ifc_for_baseline_and_hardened(tmp_path: Path):
    import_service = ConstructionIFCImportService(tmp_path / "imports")
    imported = import_service.import_ifc(
        content=_demo_ifc_bytes(),
        original_filename="coordination.ifc",
        project_id="project-001",
        asset_id="ifc-main-model",
        version="v3",
        parent_version="v2",
    )
    demo_service = ConstructionDemoService(
        runner=ConstructionTrustDemoRunner(tmp_path / "runs"),
        import_service=import_service,
    )

    result = demo_service.run(
        ConstructionDemoRunRequest(
            project_id="project-001",
            run_id="ifc-comparison",
            asset_ref=imported.asset_ref,
            mode="compare",
        )
    )

    assert result.asset_ref == imported.asset_ref
    assert result.asset_inspection is not None
    assert result.asset_inspection.content_sha256 == imported.inspection.content_sha256
    assert result.baseline_blocked_count == 0
    assert result.hardened_blocked_count == 5
    assert result.comparison_verified is True
    assert len(result.baseline_results) == 5
    assert all(not item.blocked for item in result.baseline_results)
    assert all(item.blocked for item in result.results)
