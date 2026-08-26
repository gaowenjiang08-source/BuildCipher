from cipher_genius.core.construction_domain import (
    build_construction_context_summary,
    get_construction_requirement_profile,
    is_construction_requirement,
)
from cipher_genius.core.langgraph_mas import LangGraphMASService
from cipher_genius.core.mas_runtime_support import MASRuntimeSupport
from cipher_genius.models.construction import (
    ConstructionAssetType,
    ConstructionPartyRole,
    ConstructionPrimaryScenario,
    ConstructionSecurityInvariant,
    ConstructionThreat,
)
from cipher_genius.models.requirement import (
    PlatformType,
    Requirement,
    ResourceLevel,
    SchemeType,
    SecurityRequirement,
    TargetPlatform,
)
from cipher_genius.models.scheme import CryptographicScheme, SchemeMetadata, SecurityAnalysis


def build_requirement(*, quantum_resistant: bool = False) -> Requirement:
    return Requirement(
        description="construction domain test",
        scheme_type=SchemeType.AUTHENTICATED_ENCRYPTION,
        target_platform=TargetPlatform(
            type=PlatformType.SERVER,
            resource_level=ResourceLevel.MODERATE,
        ),
        security=SecurityRequirement(
            security_level=128,
            quantum_resistant=quantum_resistant,
        ),
    )


def build_scheme(requirement: Requirement) -> CryptographicScheme:
    return CryptographicScheme(
        metadata=SchemeMetadata(
            name="Construction Test Scheme",
            scheme_type=SchemeType.AUTHENTICATED_ENCRYPTION,
        ),
        requirements=requirement,
        security_analysis=SecurityAnalysis(threat_model={"adversary": "network"}),
        design_rationale="baseline rationale",
        score=8.0,
    )


def test_construction_detection_rejects_crypto_construction_wording():
    assert is_construction_requirement("Design an AEAD construction with a nonce") is False
    assert is_construction_requirement("Design an AEAD construction for BIM/IFC delivery") is True
    structured_spec = MASRuntimeSupport()._build_structured_spec(
        build_requirement(),
        "Design an AEAD construction with a nonce",
    )
    assert structured_spec["domain"] == "general"


def test_structured_spec_contains_typed_construction_profile():
    service = MASRuntimeSupport()
    raw_text = (
        "请为设计院向总包、监理和专业分包交付 BIM/IFC 模型与工地 IoT 验收证据链设计方案，"
        "要求版本回滚检测、最小权限、设备身份、nonce 防重放和后量子迁移。"
    )

    structured_spec = service._build_structured_spec(build_requirement(), raw_text)
    profile = get_construction_requirement_profile(structured_spec)

    assert profile is not None
    assert structured_spec["domain"] == "construction"
    assert structured_spec["quantum_safe"] is True
    assert profile.primary_scenario == ConstructionPrimaryScenario.IOT_ACCEPTANCE_EVIDENCE
    assert {
        ConstructionPartyRole.DESIGN_INSTITUTE,
        ConstructionPartyRole.GENERAL_CONTRACTOR,
        ConstructionPartyRole.SUPERVISOR,
        ConstructionPartyRole.SPECIALTY_SUBCONTRACTOR,
    }.issubset(set(profile.participants))
    assert {
        ConstructionAssetType.IFC_MODEL,
        ConstructionAssetType.IOT_TELEMETRY,
        ConstructionAssetType.INSPECTION_RECORD,
    }.issubset(set(profile.digital_assets))
    assert ConstructionSecurityInvariant.PQC_MIGRATION in profile.security_invariants
    assert ConstructionThreat.TELEMETRY_REPLAY in profile.threats


def test_legacy_candidate_profile_values_remain_readable():
    profile = get_construction_requirement_profile(
        {
            "domain": "construction",
            "construction_model": {
                "primary_scenario": "bim_trusted_delivery",
                "participants": ["subcontractor", "regulator_or_inspector"],
                "digital_assets": ["bim_ifc_model", "inspection_evidence"],
                "lifecycle_phases": ["inspection_acceptance", "operation"],
                "security_invariants": ["version_integrity"],
                "threats": ["content_tampering"],
            },
        }
    )

    assert profile is not None
    assert profile.participants == [
        ConstructionPartyRole.SPECIALTY_SUBCONTRACTOR,
        ConstructionPartyRole.INSPECTION_BODY,
    ]
    assert profile.digital_assets == [
        ConstructionAssetType.IFC_MODEL,
        ConstructionAssetType.INSPECTION_RECORD,
    ]


def test_scheme_and_langgraph_projection_consume_construction_profile():
    runtime = MASRuntimeSupport()
    requirement = build_requirement()
    structured_spec = runtime._build_structured_spec(
        requirement,
        "BIM/IFC 模型交付涉及分包最小权限、版本回滚和 IoT 设备冒充与 nonce 重放。",
    )

    prepared = runtime._prepare_schemes_for_audit(
        [build_scheme(requirement)],
        requirement,
        structured_spec,
    )[0]
    constraints = LangGraphMASService()._build_context_constraints(
        structured_spec=structured_spec,
        case_memory=None,
    )

    assert "construction_model" in prepared.security_analysis.threat_model
    assert "Construction context:" in prepared.design_rationale
    assert any("BIM/IFC version-chain" in item for item in prepared.security_analysis.concerns)
    assert any(item.constraint_kind == "construction_model" for item in constraints)
    assert "scenario=iot_acceptance_evidence" in build_construction_context_summary(
        structured_spec
    )
