from cipher_genius.core.parser import RequirementParser
from cipher_genius.models.requirement import PlatformType, ResourceLevel, SchemeType


class FakeLLM:
    def __init__(self, response):
        self.response = response

    def generate_structured(self, **kwargs):
        return self.response


def build_parser(response):
    parser = RequirementParser.__new__(RequirementParser)
    parser.llm = FakeLLM(response)
    return parser


def test_parser_normalizes_flattened_structured_response():
    parser = build_parser(
        {
            "scheme_type": None,
            "target_platform": None,
            "resource_level": "high performance",
            "security_level": 256,
            "threats": ["replay attack", "mitm"],
            "quantum_resistant": True,
            "additional_features": None,
            "ambiguities": "latency target unclear",
            "assumptions": None,
            "analysis": "Assume deployment runs on server-side infrastructure.",
        }
    )

    parsed = parser.parse(
        "Design authenticated encryption for a cloud service with post-quantum migration in mind."
    )

    assert parsed.requirement.scheme_type == SchemeType.AUTHENTICATED_ENCRYPTION
    assert parsed.requirement.target_platform.type == PlatformType.SERVER
    assert parsed.requirement.target_platform.resource_level == ResourceLevel.HIGH_PERFORMANCE
    assert parsed.requirement.security.security_level == 256
    assert parsed.requirement.security.quantum_resistant is True
    assert parsed.requirement.security.threats == ["replay", "man_in_the_middle"]
    assert parsed.ambiguities == ["latency target unclear"]
    assert parsed.assumptions == ["Assume deployment runs on server-side infrastructure."]


def test_parser_accepts_string_lists_and_legacy_performance_block():
    parser = build_parser(
        {
            "scheme_type": "aead",
            "platform": "iot",
            "resource_level": "light",
            "security": {
                "security_level": "128-bit",
                "threats": "side-channel; eavesdropping",
                "properties": "confidentiality, integrity",
                "quantum_resistant": "false",
            },
            "performance_constraints": {
                "max_latency": "10ms",
                "max_memory": "256KB",
            },
            "additional_features": "key rotation, audit logging",
            "confidence": "0.91",
            "ambiguities": "",
            "assumptions": "Battery budget is moderate.",
        }
    )

    parsed = parser.parse("Need AEAD for an IoT sensor with 128-bit security and low latency.")

    assert parsed.requirement.scheme_type == SchemeType.AUTHENTICATED_ENCRYPTION
    assert parsed.requirement.target_platform.type == PlatformType.IOT_DEVICE
    assert parsed.requirement.target_platform.resource_level == ResourceLevel.LIGHTWEIGHT
    assert parsed.requirement.performance.max_latency == "10ms"
    assert parsed.requirement.performance.max_memory == "256KB"
    assert parsed.requirement.additional_features == ["key rotation", "audit logging"]
    assert parsed.requirement.security.properties == ["confidentiality", "integrity"]
    assert parsed.requirement.security.threats == ["side_channel", "eavesdropping"]
    assert parsed.confidence == 0.91
    assert parsed.assumptions == ["Battery budget is moderate."]


def test_parser_refines_conservative_structured_output_for_construction_platform():
    parser = build_parser(
        {
            "scheme_type": "encryption",
            "target_platform": {"type": "server", "resource_level": "moderate"},
            "security": {
                "security_level": 128,
                "threats": ["quantum"],
                "properties": [],
                "quantum_resistant": False,
            },
            "performance": {},
            "additional_features": ["construction_asset_lineage", "evidence_backed_delivery", "post_quantum_resistant"],
            "confidence": 0.72,
            "ambiguities": ["Specific algorithm not provided"],
            "assumptions": [],
        }
    )

    parsed = parser.parse("建筑项目 BIM/IFC 交付需要低延迟加密并满足 ISO 19650，要求后量子可迁移。")

    assert parsed.requirement.scheme_type == SchemeType.AUTHENTICATED_ENCRYPTION
    assert parsed.requirement.security.security_level == 256
    assert parsed.requirement.security.quantum_resistant is True
    assert parsed.requirement.performance.max_latency == "low-latency"


def test_parser_falls_back_when_structured_response_is_not_a_dict():
    parser = build_parser("not-json")

    parsed = parser.parse("Need a digital signature scheme for mobile clients.")

    assert parsed.requirement.scheme_type == SchemeType.SIGNATURE
    assert parsed.requirement.target_platform.type == PlatformType.MOBILE
    assert parsed.confidence == 0.5


def test_parser_fallback_understands_chinese_quantum_iot_constraints():
    parser = build_parser("not-json")

    parsed = parser.parse(
        "为物联网传感器网络设计轻量级认证加密方案，内存预算 256KB，延迟目标 10ms，要求后量子可升级。"
    )

    assert parsed.requirement.scheme_type == SchemeType.AUTHENTICATED_ENCRYPTION
    assert parsed.requirement.target_platform.type == PlatformType.IOT_DEVICE
    assert parsed.requirement.target_platform.resource_level == ResourceLevel.LIGHTWEIGHT
    assert parsed.requirement.security.quantum_resistant is True
    assert parsed.requirement.security.threats == ["quantum"]
    assert parsed.requirement.performance.max_memory == "256KB"
    assert parsed.requirement.performance.max_latency == "10ms"
    assert "post_quantum_resistant" in parsed.requirement.additional_features


def test_parser_fallback_prefers_authenticated_encryption_for_construction_delivery():
    parser = build_parser("not-json")

    parsed = parser.parse(
        "建筑项目 BIM/IFC 交付需要低延迟加密并满足 ISO 19650，要求后量子可迁移。"
    )

    assert parsed.requirement.scheme_type == SchemeType.AUTHENTICATED_ENCRYPTION
    assert parsed.requirement.target_platform.type == PlatformType.SERVER
    assert parsed.requirement.security.security_level == 256
    assert parsed.requirement.security.quantum_resistant is True
    assert "construction_asset_lineage" in parsed.requirement.additional_features
    assert "evidence_backed_delivery" in parsed.requirement.additional_features
