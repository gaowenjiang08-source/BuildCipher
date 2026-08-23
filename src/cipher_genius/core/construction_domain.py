"""Typed construction intent inference for the BuildCipher MAS runtime."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from cipher_genius.models.construction import (
    ConstructionAssetType,
    ConstructionLifecyclePhase,
    ConstructionPartyRole,
    ConstructionPrimaryScenario,
    ConstructionRequirementProfile,
    ConstructionSecurityInvariant,
    ConstructionThreat,
)

CONSTRUCTION_KEYWORDS = (
    "bim",
    "ifc",
    "openbim",
    "cde",
    "rfi",
    "construction project",
    "building project",
    "jobsite",
    "建筑",
    "建设项目",
    "施工",
    "工地",
    "竣工",
    "总包",
    "监理",
    "设计院",
    "分包",
    "验收",
    "工程量",
    "图纸",
    "隐蔽工程",
    "点云",
)

CRYPTO_CONSTRUCTION_FALSE_POSITIVES = (
    "aead construction",
    "cipher construction",
    "hash construction",
    "mac construction",
    "cryptographic construction",
)

_LEGACY_PARTICIPANTS = {
    "subcontractor": ConstructionPartyRole.SPECIALTY_SUBCONTRACTOR.value,
    "regulator_or_inspector": ConstructionPartyRole.INSPECTION_BODY.value,
}
_LEGACY_ASSETS = {
    "bim_ifc_model": ConstructionAssetType.IFC_MODEL.value,
    "cde_document": ConstructionAssetType.DRAWING.value,
    "inspection_evidence": ConstructionAssetType.INSPECTION_RECORD.value,
    "as_built_archive": ConstructionAssetType.HANDOVER_PACKAGE.value,
    "cost_or_quantity_file": ConstructionAssetType.COST_FILE.value,
}
_LEGACY_PHASES = {
    "inspection_acceptance": ConstructionLifecyclePhase.INSPECTION.value,
    "operation": ConstructionLifecyclePhase.OPERATIONS.value,
}


def is_construction_requirement(raw_text: str) -> bool:
    """Distinguish built-asset requirements from cryptography terminology."""

    lowered = str(raw_text or "").lower()
    if any(phrase in lowered for phrase in CRYPTO_CONSTRUCTION_FALSE_POSITIVES):
        return any(keyword in lowered for keyword in ("bim", "ifc", "cde"))
    return any(keyword in lowered for keyword in CONSTRUCTION_KEYWORDS)


def augment_construction_structured_spec(
    spec: dict[str, Any], raw_text: str
) -> dict[str, Any]:
    """Attach a serialized typed profile while keeping the structured-spec wire shape."""

    if not is_construction_requirement(raw_text):
        lowered = str(raw_text or "").lower()
        if any(phrase in lowered for phrase in CRYPTO_CONSTRUCTION_FALSE_POSITIVES):
            updated = dict(spec)
            updated["domain"] = "general"
            if updated.get("compliance") == "ISO_19650":
                updated["compliance"] = "NIST_CSF"
            return updated
        return spec

    profile = build_construction_requirement_profile(raw_text)
    updated = dict(spec)
    updated["domain"] = "construction"
    updated["construction_model"] = profile.model_dump(mode="json")
    if updated.get("compliance") in (None, "NIST_CSF"):
        updated["compliance"] = "ISO_19650"
    if ConstructionSecurityInvariant.PQC_MIGRATION in profile.security_invariants:
        updated["quantum_safe"] = True
    return updated


def build_construction_requirement_profile(raw_text: str) -> ConstructionRequirementProfile:
    """Infer the minimum construction trust model from explicit requirement evidence."""

    lowered = str(raw_text or "").lower()
    participants = _collect(
        (
            (ConstructionPartyRole.OWNER, ("业主", "建设单位")),
            (ConstructionPartyRole.DESIGN_INSTITUTE, ("设计院", "设计单位", "designer")),
            (ConstructionPartyRole.GENERAL_CONTRACTOR, ("总包", "总承包")),
            (ConstructionPartyRole.SUPERVISOR, ("监理",)),
            (ConstructionPartyRole.SPECIALTY_SUBCONTRACTOR, ("分包", "专业分包")),
            (ConstructionPartyRole.SUPPLIER, ("供应商", "设备供应")),
            (ConstructionPartyRole.OPERATOR, ("运维", "运营维护")),
            (ConstructionPartyRole.INSPECTION_BODY, ("检测机构", "第三方检测")),
            (ConstructionPartyRole.REGULATOR, ("监管", "审查")),
        ),
        lowered,
    )
    digital_assets = _collect(
        (
            (ConstructionAssetType.IFC_MODEL, ("bim", "ifc", "模型")),
            (ConstructionAssetType.DRAWING, ("cde", "协同文件", "图纸", "施工图")),
            (ConstructionAssetType.DESIGN_CHANGE, ("设计变更", "变更单")),
            (ConstructionAssetType.RFI, ("rfi", "技术核定")),
            (ConstructionAssetType.IOT_TELEMETRY, ("iot", "传感器", "遥测", "设备数据")),
            (ConstructionAssetType.INSPECTION_RECORD, ("验收", "隐蔽工程", "检测报告")),
            (ConstructionAssetType.SITE_MEDIA, ("现场照片", "现场影像", "视频")),
            (ConstructionAssetType.POINT_CLOUD, ("点云",)),
            (ConstructionAssetType.HANDOVER_PACKAGE, ("竣工", "归档", "运维交付")),
            (ConstructionAssetType.COST_FILE, ("造价", "工程量", "清单")),
        ),
        lowered,
    )
    lifecycle_phases = _collect(
        (
            (ConstructionLifecyclePhase.DESIGN, ("设计", "设计院")),
            (ConstructionLifecyclePhase.PROCUREMENT, ("招采", "采购", "供应商")),
            (ConstructionLifecyclePhase.CONSTRUCTION, ("施工", "工地", "总包", "分包")),
            (ConstructionLifecyclePhase.INSPECTION, ("验收", "检测", "隐蔽工程")),
            (ConstructionLifecyclePhase.HANDOVER, ("竣工", "交付")),
            (ConstructionLifecyclePhase.OPERATIONS, ("运维", "运营")),
        ),
        lowered,
    )
    security_invariants = _collect(
        (
            (ConstructionSecurityInvariant.IDENTITY_VERIFICATION, ("身份", "证书", "注册")),
            (ConstructionSecurityInvariant.LEAST_PRIVILEGE, ("最小权限", "权限分级", "越权")),
            (ConstructionSecurityInvariant.VERSION_INTEGRITY, ("版本", "哈希", "签名", "完整性")),
            (ConstructionSecurityInvariant.EVIDENCE_TRACEABILITY, ("证据", "追溯", "审计")),
            (
                ConstructionSecurityInvariant.REPLAY_RESISTANCE,
                ("nonce", "重放", "单调计数器", "时间窗口"),
            ),
            (ConstructionSecurityInvariant.PQC_MIGRATION, ("后量子", "pqc", "ml-kem", "迁移")),
        ),
        lowered,
    )
    threats = _collect(
        (
            (ConstructionThreat.CONTENT_TAMPERING, ("篡改", "完整性", "哈希")),
            (ConstructionThreat.VERSION_ROLLBACK, ("回滚", "旧版本")),
            (ConstructionThreat.OVERPRIVILEGED_ACCESS, ("越权", "最小权限", "完整模型")),
            (ConstructionThreat.DEVICE_IMPERSONATION, ("冒充", "设备身份", "未注册设备")),
            (ConstructionThreat.TELEMETRY_REPLAY, ("nonce", "重放", "重复提交")),
            (ConstructionThreat.REPUDIATION, ("否认", "签批", "责任")),
            (ConstructionThreat.LONG_TERM_QUANTUM_HARVEST, ("后量子", "未来解密")),
        ),
        lowered,
    )

    return ConstructionRequirementProfile(
        primary_scenario=_select_primary_scenario(
            digital_assets=digital_assets,
            threats=threats,
            security_invariants=security_invariants,
        ),
        participants=participants,
        digital_assets=digital_assets,
        lifecycle_phases=lifecycle_phases,
        security_invariants=security_invariants,
        threats=threats,
    )


def get_construction_requirement_profile(
    structured_spec: dict[str, Any],
) -> ConstructionRequirementProfile | None:
    """Read current or legacy construction-model values into the typed contract."""

    if str(structured_spec.get("domain") or "").lower() != "construction":
        return None
    raw_model = structured_spec.get("construction_model")
    if isinstance(raw_model, ConstructionRequirementProfile):
        return raw_model
    if not isinstance(raw_model, dict):
        return None

    normalized = dict(raw_model)
    normalized["participants"] = _normalize_values(
        normalized.get("participants"), _LEGACY_PARTICIPANTS
    )
    normalized["digital_assets"] = _normalize_values(
        normalized.get("digital_assets"), _LEGACY_ASSETS
    )
    normalized["lifecycle_phases"] = _normalize_values(
        normalized.get("lifecycle_phases"), _LEGACY_PHASES
    )
    return ConstructionRequirementProfile.model_validate(normalized)


def enrich_scheme_with_construction_context(
    scheme: Any, structured_spec: dict[str, Any]
) -> Any:
    """Project typed construction intent into the scheme consumed by audit."""

    profile = get_construction_requirement_profile(structured_spec)
    if profile is None:
        return scheme

    candidate = scheme.model_copy(deep=True)
    threat_model = dict(candidate.security_analysis.threat_model)
    threat_model["construction_model"] = profile.model_dump(mode="json")
    candidate.security_analysis.threat_model = threat_model

    for concern in build_construction_audit_focus(structured_spec):
        if concern not in candidate.security_analysis.concerns:
            candidate.security_analysis.concerns.append(concern)

    summary = build_construction_context_summary(structured_spec)
    marker = f"Construction context: {summary}"
    if marker not in candidate.design_rationale:
        candidate.design_rationale = "\n".join(
            part for part in (candidate.design_rationale, marker) if part
        ).strip()
    return candidate


def build_construction_context_summary(structured_spec: dict[str, Any]) -> str:
    profile = get_construction_requirement_profile(structured_spec)
    if profile is None:
        return ""
    return "; ".join(
        part
        for part in (
            f"scenario={profile.primary_scenario.value}",
            _format_values("participants", profile.participants),
            _format_values("assets", profile.digital_assets),
            _format_values("threats", profile.threats),
        )
        if part
    )


def build_construction_scenario_fit(
    structured_spec: dict[str, Any], compliance: str, quantum: bool
) -> str:
    summary = build_construction_context_summary(structured_spec)
    if not summary:
        return ""
    return (
        "场景画像：建筑可信交付；"
        f"主要合规目标：{compliance}；"
        f"后量子要求：{'是' if quantum else '否'}；{summary}。"
    )


def build_construction_production_guide(structured_spec: dict[str, Any]) -> list[str]:
    profile = get_construction_requirement_profile(structured_spec)
    if profile is None:
        return []

    guide = [
        "将 BIM/IFC、CDE 文档、IoT 遥测和验收影像纳入同一证据引用表。",
        "为业主、设计院、总包、监理、分包和供应商分别定义身份、授权、密钥域与撤权策略。",
    ]
    threats = set(profile.threats)
    if threats & {ConstructionThreat.VERSION_ROLLBACK, ConstructionThreat.CONTENT_TAMPERING}:
        guide.append("上线前验证模型版本链、内容哈希、签名验真、批准状态和回滚检测。")
    if threats & {ConstructionThreat.DEVICE_IMPERSONATION, ConstructionThreat.TELEMETRY_REPLAY}:
        guide.append("工地 IoT 数据进入验收链前验证设备注册、消息认证、计数器、nonce 和时间窗口。")
    if ConstructionThreat.LONG_TERM_QUANTUM_HARVEST in threats:
        guide.append("长期归档包需记录算法、参数、证书、验签上下文和后量子迁移计划。")
    return guide


def build_construction_audit_focus(structured_spec: dict[str, Any]) -> list[str]:
    profile = get_construction_requirement_profile(structured_spec)
    if profile is None:
        return []

    focus = ["Audit construction trust boundaries, evidence refs, and lifecycle authorization."]
    threats = set(profile.threats)
    if ConstructionThreat.OVERPRIVILEGED_ACCESS in threats:
        focus.append("Check least-privilege sharing across construction participant roles.")
    if ConstructionThreat.VERSION_ROLLBACK in threats:
        focus.append(
            "Check BIM/IFC version-chain continuity, approval state, and rollback detection."
        )
    if threats & {ConstructionThreat.DEVICE_IMPERSONATION, ConstructionThreat.TELEMETRY_REPLAY}:
        focus.append(
            "Check IoT device identity, message authentication, counters, "
            "nonces, and replay windows."
        )
    if ConstructionThreat.REPUDIATION in threats:
        focus.append(
            "Check inspection signer identity, timestamp, organization, "
            "and non-repudiation evidence."
        )
    return focus


def _collect(candidates: Iterable[tuple[Any, tuple[str, ...]]], lowered: str) -> list[Any]:
    return [
        value
        for value, keywords in candidates
        if any(keyword in lowered for keyword in keywords)
    ]


def _normalize_values(values: Any, aliases: dict[str, str]) -> list[str]:
    return [aliases.get(str(value), str(value)) for value in list(values or [])]


def _format_values(label: str, values: Iterable[Any]) -> str:
    items = [getattr(value, "value", str(value)) for value in values]
    return f"{label}={','.join(items[:6])}" if items else ""


def _select_primary_scenario(
    *,
    digital_assets: list[ConstructionAssetType],
    threats: list[ConstructionThreat],
    security_invariants: list[ConstructionSecurityInvariant],
) -> ConstructionPrimaryScenario:
    if (
        ConstructionAssetType.IOT_TELEMETRY in digital_assets
        or ConstructionThreat.TELEMETRY_REPLAY in threats
        or ConstructionThreat.DEVICE_IMPERSONATION in threats
    ):
        return ConstructionPrimaryScenario.IOT_ACCEPTANCE_EVIDENCE
    if (
        ConstructionSecurityInvariant.PQC_MIGRATION in security_invariants
        or ConstructionThreat.LONG_TERM_QUANTUM_HARVEST in threats
    ):
        return ConstructionPrimaryScenario.BUILT_ASSET_PQC_MIGRATION
    if ConstructionThreat.OVERPRIVILEGED_ACCESS in threats:
        return ConstructionPrimaryScenario.COLLABORATION_ACCESS_CONTROL
    return ConstructionPrimaryScenario.BIM_TRUSTED_DELIVERY
