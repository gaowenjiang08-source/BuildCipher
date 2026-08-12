"""Stable domain contracts for construction digital-asset trust workflows."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConstructionLifecyclePhase(str, Enum):
    PLANNING = "planning"
    DESIGN = "design"
    PROCUREMENT = "procurement"
    CONSTRUCTION = "construction"
    INSPECTION = "inspection"
    HANDOVER = "handover"
    OPERATIONS = "operations"
    RENOVATION_OR_DECOMMISSION = "renovation_or_decommission"


class ConstructionPartyRole(str, Enum):
    OWNER = "owner"
    DESIGN_INSTITUTE = "design_institute"
    CONSULTANT = "consultant"
    GENERAL_CONTRACTOR = "general_contractor"
    SPECIALTY_SUBCONTRACTOR = "specialty_subcontractor"
    SUPERVISOR = "supervisor"
    INSPECTION_BODY = "inspection_body"
    SUPPLIER = "supplier"
    OPERATOR = "operator"
    REGULATOR = "regulator"


class ConstructionAssetType(str, Enum):
    IFC_MODEL = "ifc_model"
    DRAWING = "drawing"
    STRUCTURAL_CALCULATION = "structural_calculation"
    COST_FILE = "cost_file"
    DESIGN_CHANGE = "design_change"
    RFI = "rfi"
    METHOD_STATEMENT = "method_statement"
    INSPECTION_RECORD = "inspection_record"
    SITE_MEDIA = "site_media"
    POINT_CLOUD = "point_cloud"
    IOT_TELEMETRY = "iot_telemetry"
    HANDOVER_PACKAGE = "handover_package"


class AssetSensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class ApprovalState(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class CredentialLifecycleState(str, Enum):
    ACTIVE = "active"
    PENDING_ROTATION = "pending_rotation"
    DISABLED = "disabled"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CertificateLifecycleState(str, Enum):
    ISSUED = "issued"
    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ConstructionParty(BaseModel):
    """An organization or device-owning party participating in a project."""

    model_config = ConfigDict(extra="forbid")

    party_id: str
    organization_name: str
    role: ConstructionPartyRole
    discipline_scope: List[str] = Field(default_factory=list)
    lifecycle_phases: List[ConstructionLifecyclePhase] = Field(default_factory=list)
    can_approve: bool = False
    credential_ref: Optional[str] = None
    access_valid_from: Optional[str] = None
    access_valid_until: Optional[str] = None


class ConstructionAsset(BaseModel):
    """Versioned digital asset whose integrity and authorization must be provable."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    asset_type: ConstructionAssetType
    project_id: str
    lifecycle_phase: ConstructionLifecyclePhase
    owner_org: str
    sensitivity: AssetSensitivity = AssetSensitivity.CONFIDENTIAL
    version: str
    parent_version: Optional[str] = None
    content_hash: Optional[str] = None
    signer_identity: Optional[str] = None
    approval_state: ApprovalState = ApprovalState.DRAFT
    retention_years: int = Field(default=10, ge=0, le=200)
    allowed_roles: List[ConstructionPartyRole] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class ConstructionAccessGrant(BaseModel):
    """Least-privilege grant scoped by project, asset, discipline, and time."""

    model_config = ConfigDict(extra="forbid")

    grant_id: str
    project_id: str
    party_id: str
    asset_id: str
    allowed_actions: List[str] = Field(default_factory=list)
    discipline_scope: List[str] = Field(default_factory=list)
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    key_ref: Optional[str] = None


class ConstructionProjectContext(BaseModel):
    """Minimum domain context passed between BuildTrust agents."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    project_name: str
    lifecycle_phase: ConstructionLifecyclePhase
    parties: List[ConstructionParty] = Field(default_factory=list)
    assets: List[ConstructionAsset] = Field(default_factory=list)
    access_grants: List[ConstructionAccessGrant] = Field(default_factory=list)
    requires_commercial_crypto: bool = False
    requires_pqc_migration: bool = False
    open_questions: List[str] = Field(default_factory=list)


class IFCInspectionResult(BaseModel):
    """Stable inspection result produced from one IFC STEP physical file."""

    model_config = ConfigDict(extra="forbid")

    source_ref: str
    file_name: Optional[str] = None
    content_sha256: str
    byte_count: int = Field(ge=0)
    schema_identifiers: List[str] = Field(default_factory=list)
    entity_count: int = Field(ge=0)
    entity_type_counts: Dict[str, int] = Field(default_factory=dict)
    global_id_count: int = Field(ge=0)
    duplicate_global_ids: List[str] = Field(default_factory=list)
    parse_errors: List[str] = Field(default_factory=list)
    valid: bool


class CDEPackageDescriptor(BaseModel):
    """Provider-neutral descriptor for one construction package in a CDE."""

    model_config = ConfigDict(extra="forbid")

    package_id: str
    project_id: str
    relative_path: str
    connector_id: str
    connector_kind: str
    media_type: str = "application/x-step"
    byte_count: int = Field(ge=0)
    content_sha256: str
    version: str = "unversioned"
    modified_at: Optional[str] = None


class CDEConnectorStatus(BaseModel):
    """Observable connector state without exposing credentials."""

    model_config = ConfigDict(extra="forbid")

    connector_id: str
    connector_kind: str
    available: bool
    root_ref: Optional[str] = None
    credential_ref: Optional[str] = None
    capability_boundary: str


class ConstructionCredentialGovernanceRecord(BaseModel):
    """Auditable lifecycle metadata for a non-exportable credential reference."""

    model_config = ConfigDict(extra="forbid")

    credential_ref: str
    project_id: str
    owner_ref: str
    purpose: str
    algorithm: str
    provider_id: str
    provider_kind: str
    key_version: str
    lifecycle_state: CredentialLifecycleState = CredentialLifecycleState.ACTIVE
    created_at: str
    activated_at: Optional[str] = None
    last_rotated_at: Optional[str] = None
    next_rotation_at: Optional[str] = None
    expires_at: Optional[str] = None
    certificate_ref: Optional[str] = None
    policy_refs: List[str] = Field(default_factory=list)


class ConstructionKeyOperationReceipt(BaseModel):
    """Secret-free receipt for one provider-side cryptographic operation."""

    model_config = ConfigDict(extra="forbid")

    operation_id: str
    operation: str
    credential_ref: str
    provider_id: str
    provider_kind: str
    algorithm: str
    key_version: str
    occurred_at: str
    input_sha256: str
    status: str
    verification_result: Optional[bool] = None
    audit_ref: str


class ConstructionCertificateGovernanceRecord(BaseModel):
    """Certificate inventory metadata used for expiry and revocation governance."""

    model_config = ConfigDict(extra="forbid")

    certificate_ref: str
    project_id: str
    subject_ref: str
    issuer_ref: str
    serial_number: str
    signature_algorithm: str
    fingerprint_sha256: str
    provider_id: str
    lifecycle_state: CertificateLifecycleState
    not_before: str
    not_after: str
    last_checked_at: str
    policy_refs: List[str] = Field(default_factory=list)


class ConstructionCryptoGovernanceAssessment(BaseModel):
    """Point-in-time lifecycle assessment for credentials and certificates."""

    model_config = ConfigDict(extra="forbid")

    assessed_at: str
    credential_count: int = Field(ge=0)
    rotation_due_refs: List[str] = Field(default_factory=list)
    inactive_credential_refs: List[str] = Field(default_factory=list)
    certificate_count: int = Field(ge=0)
    expiring_certificate_refs: List[str] = Field(default_factory=list)
    invalid_certificate_refs: List[str] = Field(default_factory=list)
