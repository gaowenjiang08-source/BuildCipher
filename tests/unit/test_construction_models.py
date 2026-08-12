import pytest
from pydantic import ValidationError

from cipher_genius.models.construction import (
    ApprovalState,
    ConstructionAccessGrant,
    ConstructionAsset,
    ConstructionAssetType,
    ConstructionLifecyclePhase,
    ConstructionParty,
    ConstructionPartyRole,
    ConstructionProjectContext,
)


def test_construction_project_context_keeps_version_and_access_boundaries():
    party = ConstructionParty(
        party_id="party-subcontractor",
        organization_name="机电专业分包",
        role=ConstructionPartyRole.SPECIALTY_SUBCONTRACTOR,
        discipline_scope=["mep"],
        lifecycle_phases=[ConstructionLifecyclePhase.CONSTRUCTION],
    )
    asset = ConstructionAsset(
        asset_id="asset-ifc-v3",
        asset_type=ConstructionAssetType.IFC_MODEL,
        project_id="project-001",
        lifecycle_phase=ConstructionLifecyclePhase.CONSTRUCTION,
        owner_org="设计院",
        version="v3",
        parent_version="v2",
        content_hash="sha256:demo",
        signer_identity="cert:design-001",
        approval_state=ApprovalState.APPROVED,
        allowed_roles=[ConstructionPartyRole.SPECIALTY_SUBCONTRACTOR],
        evidence_refs=["evidence:approval-v3"],
    )
    grant = ConstructionAccessGrant(
        grant_id="grant-001",
        project_id="project-001",
        party_id=party.party_id,
        asset_id=asset.asset_id,
        allowed_actions=["read_filtered_package"],
        discipline_scope=["mep"],
        valid_until="2026-12-31T23:59:59+08:00",
        key_ref="kms:project-001/mep-delivery",
    )

    context = ConstructionProjectContext(
        project_id="project-001",
        project_name="示范项目",
        lifecycle_phase=ConstructionLifecyclePhase.CONSTRUCTION,
        parties=[party],
        assets=[asset],
        access_grants=[grant],
    )

    assert context.assets[0].parent_version == "v2"
    assert context.assets[0].evidence_refs == ["evidence:approval-v3"]
    assert context.access_grants[0].discipline_scope == ["mep"]


def test_construction_contract_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ConstructionParty(
            party_id="party-001",
            organization_name="设计院",
            role=ConstructionPartyRole.DESIGN_INSTITUTE,
            undocumented_permission="all",
        )

