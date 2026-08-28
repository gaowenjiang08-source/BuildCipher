from cipher_genius.codegen.generator import CodeGenerator
from cipher_genius.models.requirement import (
    PlatformType,
    Requirement,
    ResourceLevel,
    SchemeType,
    SecurityRequirement,
    TargetPlatform,
)
from cipher_genius.models.scheme import CryptographicScheme, SchemeMetadata, SecurityAnalysis


class BundleLLM:
    def __init__(self, bundle: dict[str, str]) -> None:
        self.bundle = bundle
        self.calls = 0

    def generate_structured(self, *args, **kwargs) -> dict[str, str]:
        self.calls += 1
        return self.bundle


def build_scheme() -> CryptographicScheme:
    requirement = Requirement(
        description="Protect a BIM delivery package",
        scheme_type=SchemeType.AUTHENTICATED_ENCRYPTION,
        target_platform=TargetPlatform(
            type=PlatformType.SERVER,
            resource_level=ResourceLevel.MODERATE,
        ),
        security=SecurityRequirement(security_level=128),
    )
    return CryptographicScheme(
        metadata=SchemeMetadata(
            name="BIM Delivery Bundle",
            scheme_type=SchemeType.AUTHENTICATED_ENCRYPTION,
        ),
        requirements=requirement,
        security_analysis=SecurityAnalysis(threat_model={"adversary": "network"}),
    )


def test_generate_all_uses_one_structured_llm_call() -> None:
    llm = BundleLLM(
        {
            "pseudocode": "function encrypt(message)\n  return seal(message)\nend function",
            "python": "def encrypt(message: bytes) -> bytes:\n    return message",
            "c": "int encrypt(const char *input) {\n    return input != 0;\n}",
        }
    )
    generator = CodeGenerator.__new__(CodeGenerator)
    generator.llm = llm

    implementation = generator.generate_all(build_scheme())

    assert llm.calls == 1
    assert "def encrypt" in implementation.python
    assert "int encrypt" in implementation.c
    assert "function encrypt" in implementation.pseudocode


def test_generate_all_falls_back_without_additional_llm_calls() -> None:
    llm = BundleLLM({"pseudocode": "", "python": "", "c": ""})
    generator = CodeGenerator.__new__(CodeGenerator)
    generator.llm = llm

    implementation = generator.generate_all(build_scheme())

    assert llm.calls == 1
    assert "function encrypt" in implementation.pseudocode
    assert "class BIMDeliveryBundle" in implementation.python
    assert "int encrypt" in implementation.c
