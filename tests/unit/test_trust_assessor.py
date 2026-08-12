from cipher_genius.core.trust_assessor import TrustAssessor
from cipher_genius.models.component import Component, ComponentType, Performance, Reference, SecurityAnalysis
from cipher_genius.models.requirement import PlatformType, Requirement, ResourceLevel, SchemeType, SecurityRequirement, TargetPlatform
from cipher_genius.models.scheme import CryptographicScheme, SchemeArchitecture, SchemeMetadata, SchemeParameters


def contains_chinese(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(text))


def build_component(
    name: str,
    category: ComponentType,
    *,
    standardized: bool,
    proven_security: bool,
    references: list[Reference],
) -> Component:
    return Component(
        name=name,
        category=category,
        performance=Performance(software_speed="high", memory="low", power="medium"),
        security=SecurityAnalysis(
            security_level=256 if "AES" in name.upper() else 128,
            standardized=standardized,
            proven_security=proven_security,
            status="secure",
        ),
        references=references,
    )


def build_scheme(*components: Component, quantum_resistant: bool = False) -> CryptographicScheme:
    requirement = Requirement(
        description="Enterprise-grade authenticated encryption",
        scheme_type=SchemeType.AUTHENTICATED_ENCRYPTION,
        target_platform=TargetPlatform(
            type=PlatformType.SERVER,
            resource_level=ResourceLevel.HIGH_PERFORMANCE,
        ),
        security=SecurityRequirement(
            security_level=256,
            quantum_resistant=quantum_resistant,
        ),
    )
    return CryptographicScheme(
        metadata=SchemeMetadata(name="AES-GCM", scheme_type=SchemeType.AUTHENTICATED_ENCRYPTION),
        requirements=requirement,
        architecture=SchemeArchitecture(components=list(components), composition={"pattern": "aead"}),
        parameters=SchemeParameters(key_size=256, nonce_size=96, tag_size=128),
        score=8.8,
    )


def test_trust_assessor_rewards_supported_components():
    assessor = TrustAssessor()
    aes = build_component(
        "AES",
        ComponentType.BLOCK_CIPHER,
        standardized=True,
        proven_security=True,
        references=[
            Reference(type="standard", title="FIPS 197", year=2001, url="https://example.com/fips197"),
            Reference(type="paper", title="The Design of Rijndael", year=2002),
        ],
    )
    gcm = build_component(
        "GCM",
        ComponentType.MODE_OF_OPERATION,
        standardized=True,
        proven_security=False,
        references=[
            Reference(type="standard", title="NIST SP 800-38D", year=2007, url="https://example.com/38d"),
        ],
    )

    scheme = build_scheme(aes, gcm)
    assessment = assessor.assess(
        scheme,
        parser_confidence=0.91,
        compliance_score=92,
        risk_score=18,
        audit_passed=True,
        quantum_ready=True,
    )

    assert assessment["credibility_score"] >= 80
    assert assessment["algorithm_strength_score"] >= 80
    assert assessment["evidence_coverage"] == 100.0
    assert assessment["trust_level"] == "high"
    assert assessment["trust_level_label"] == "高"
    assert assessment["sources"]
    assert assessment["component_evidence"][0]["reference_count"] >= 1
    assert assessment["component_evidence"][0]["support_level"] in {"high", "medium", "low", "unknown"}
    assert contains_chinese(assessment["component_evidence"][0]["support_level_label"])
    assert assessment["strengths"]
    assert all(contains_chinese(item) for item in assessment["strengths"])


def test_trust_assessor_flags_gaps_for_weak_evidence():
    assessor = TrustAssessor()
    custom = build_component(
        "CustomCipher",
        ComponentType.BLOCK_CIPHER,
        standardized=False,
        proven_security=False,
        references=[],
    )

    scheme = build_scheme(custom, quantum_resistant=True)
    assessment = assessor.assess(
        scheme,
        parser_confidence=0.55,
        compliance_score=60,
        risk_score=75,
        audit_passed=False,
        quantum_ready=False,
    )

    assert assessment["credibility_score"] < 65
    assert assessment["trust_level"] in {"low", "medium"}
    assert assessment["trust_level_label"] in {"低", "中"}
    assert assessment["gaps"]
    assert any(any(keyword in item for keyword in ["后量子", "证据", "风险", "合规"]) for item in assessment["gaps"])
    assert all(contains_chinese(item) for item in assessment["gaps"])
