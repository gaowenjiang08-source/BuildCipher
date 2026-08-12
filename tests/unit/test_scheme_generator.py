from cipher_genius.core.generator import SchemeGenerator
from cipher_genius.knowledge.components import get_component_library
from cipher_genius.models.requirement import (
    PerformanceConstraint,
    PlatformType,
    Requirement,
    ResourceLevel,
    SchemeType,
    SecurityRequirement,
    TargetPlatform,
)
from cipher_genius.models.scheme import SecurityAnalysis


class DummyLLM:
    def generate_json(self, *args, **kwargs):
        raise RuntimeError("LLM disabled for deterministic generator tests")


def build_generator() -> SchemeGenerator:
    generator = SchemeGenerator.__new__(SchemeGenerator)
    generator.llm = DummyLLM()
    generator.component_lib = get_component_library()
    return generator


def build_regulated_requirement() -> Requirement:
    return Requirement(
        description="建筑项目 BIM/IFC 交付需要低延迟加密并满足 ISO 19650，要求后量子可迁移。",
        scheme_type=SchemeType.AUTHENTICATED_ENCRYPTION,
        target_platform=TargetPlatform(type=PlatformType.SERVER, resource_level=ResourceLevel.MODERATE),
        security=SecurityRequirement(
            security_level=256,
            quantum_resistant=True,
        ),
        performance=PerformanceConstraint(max_latency="low-latency"),
        additional_features=["construction_asset_lineage", "evidence_backed_delivery", "post_quantum_resistant"],
    )


def test_generator_prefers_aes_gcm_for_regulated_chinese_enterprise_requirement():
    generator = build_generator()
    requirement = build_regulated_requirement()

    first = [component.name for component in generator._select_components(requirement, variant_index=0)]
    second = [component.name for component in generator._select_components(requirement, variant_index=1)]

    assert first == ["AES", "GCM"]
    assert second in (["AES", "AES-GCM-SIV"], ["AES", "GCM-SIV"])


def test_generator_refines_mixed_aead_selection_back_to_curated_bundle():
    generator = build_generator()
    requirement = build_regulated_requirement()
    mixed = [
        generator.component_lib.get("ChaCha20-Poly1305"),
        generator.component_lib.get("AES"),
    ]

    refined = generator._refine_component_selection(
        requirement,
        [component for component in mixed if component is not None],
        generator.component_lib.list_all(),
        variant_index=0,
    )

    assert [component.name for component in refined] == ["AES", "GCM"]


def test_generator_scores_clean_regulated_aead_bundle_above_mixed_combo():
    generator = build_generator()
    requirement = build_regulated_requirement()
    security = SecurityAnalysis(
        threat_model={"adversary": "adaptive"},
        properties=["IND-CPA", "INT-CTXT", "forward_secrecy"],
        assumptions=["Secure RNG"],
        concerns=[],
    )
    clean_components = [
        generator.component_lib.get("AES"),
        generator.component_lib.get("GCM"),
    ]
    mixed_components = [
        generator.component_lib.get("ChaCha20-Poly1305"),
        generator.component_lib.get("AES"),
    ]

    clean_score = generator._calculate_score(
        requirement,
        [component for component in clean_components if component is not None],
        security,
    )
    mixed_score = generator._calculate_score(
        requirement,
        [component for component in mixed_components if component is not None],
        security,
    )

    assert clean_score > mixed_score
