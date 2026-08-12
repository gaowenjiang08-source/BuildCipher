"""Requirement parser for natural language processing."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cipher_genius.core.llm_interface import get_llm_interface
from cipher_genius.models.requirement import (
    ParsedRequirement,
    PerformanceConstraint,
    PlatformType,
    Requirement,
    ResourceLevel,
    SchemeType,
    SecurityRequirement,
    TargetPlatform,
)
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class StructuredTargetPlatform(BaseModel):
    """Structured target platform output from LLM."""

    model_config = ConfigDict(extra="forbid")

    type: PlatformType
    resource_level: ResourceLevel
    details: Dict[str, Any] = Field(default_factory=dict)


class StructuredSecurity(BaseModel):
    """Structured security output from LLM."""

    model_config = ConfigDict(extra="forbid")

    security_level: int = 128
    threats: List[str] = Field(default_factory=list)
    properties: List[str] = Field(default_factory=list)
    quantum_resistant: bool = False


class StructuredPerformance(BaseModel):
    """Structured performance constraints from LLM."""

    model_config = ConfigDict(extra="forbid")

    max_latency: Optional[str] = None
    min_throughput: Optional[str] = None
    max_memory: Optional[str] = None
    max_power: Optional[str] = None
    max_code_size: Optional[str] = None


class StructuredRequirementOutput(BaseModel):
    """Structured parser output contract for LLM."""

    model_config = ConfigDict(extra="forbid")

    scheme_type: SchemeType
    target_platform: StructuredTargetPlatform
    security: StructuredSecurity
    performance: StructuredPerformance = Field(default_factory=StructuredPerformance)
    additional_features: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    ambiguities: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class RequirementParser:
    """Parse natural language requirements into structured format."""

    def __init__(self, llm_provider: Optional[str] = None):
        self.llm = get_llm_interface(llm_provider)

    def parse(self, description: str) -> ParsedRequirement:
        """Parse natural language description into structured requirement."""

        system_prompt = """You are an expert cryptographer and requirements analyst.
Your task is to parse natural language descriptions of cryptographic requirements
into structured technical specifications.

Extract the following information:
1. Scheme type (encryption, authenticated_encryption, signature, etc.)
2. Target platform (iot_device, mobile, server, etc.)
3. Resource level (ultra_lightweight, lightweight, moderate, high_performance)
4. Security level in bits (e.g., 128, 256)
5. Specific threats to defend against
6. Performance constraints (latency, memory, throughput, power)
7. Additional features or requirements

Be precise and conservative in your interpretations. If something is ambiguous,
note it in the ambiguities field and make a reasonable assumption."""

        user_prompt = f"""Parse this cryptographic requirement:

\"{description}\"

Return ONLY a JSON object that follows the provided JSON schema exactly."""

        try:
            schema = StructuredRequirementOutput.model_json_schema()
            response = self.llm.generate_structured(
                prompt=user_prompt,
                schema=schema,
                system_prompt=system_prompt,
                temperature=0.2,
                schema_name="requirement_parse_output",
            )
            normalized_response = self._normalize_structured_response(response, description)
            normalized_response = self._refine_structured_defaults(normalized_response, description)
            structured = StructuredRequirementOutput.model_validate(normalized_response)

            security_data = structured.security.model_dump()
            security_data["threats"] = self._normalize_threats(security_data.get("threats", []))

            requirement = Requirement(
                description=description,
                scheme_type=structured.scheme_type,
                target_platform=TargetPlatform(**structured.target_platform.model_dump()),
                security=SecurityRequirement(**security_data),
                performance=PerformanceConstraint(**structured.performance.model_dump()),
                additional_features=structured.additional_features,
                preferences=structured.preferences,
            )

            return ParsedRequirement(
                requirement=requirement,
                confidence=structured.confidence,
                ambiguities=structured.ambiguities,
                assumptions=structured.assumptions,
            )

        except (ValidationError, Exception) as exc:
            logger.error(f"Structured requirement parsing failed: {exc}")
            return self._fallback_parse(description)

    def _normalize_structured_response(self, response: Any, description: str) -> Dict[str, Any]:
        """Coerce provider responses into the parser's strict schema."""

        if not isinstance(response, dict):
            raise ValueError(f"Structured parser response must be a dict, got {type(response).__name__}")

        fallback = self._fallback_parse(description)
        fallback_requirement = fallback.requirement
        raw = description.lower()

        target_platform_raw = response.get("target_platform")
        if isinstance(target_platform_raw, dict):
            target_platform = {
                "type": self._coerce_platform_type(
                    target_platform_raw.get("type"),
                    raw,
                    fallback_requirement.target_platform.type,
                ),
                "resource_level": self._coerce_resource_level(
                    target_platform_raw.get("resource_level"),
                    raw,
                    fallback_requirement.target_platform.resource_level,
                ),
                "details": self._coerce_dict(target_platform_raw.get("details")),
            }
        else:
            target_platform = {
                "type": self._coerce_platform_type(
                    response.get("platform") or response.get("target_platform"),
                    raw,
                    fallback_requirement.target_platform.type,
                ),
                "resource_level": self._coerce_resource_level(
                    response.get("resource_level"),
                    raw,
                    fallback_requirement.target_platform.resource_level,
                ),
                "details": {},
            }

        security_raw = response.get("security")
        quantum_hint = self._infer_quantum_requirement(raw, response, security_raw if isinstance(security_raw, dict) else {})
        if isinstance(security_raw, dict):
            security = {
                "security_level": self._coerce_security_level(
                    security_raw.get("security_level"),
                    raw,
                    fallback_requirement.security.security_level,
                ),
                "threats": self._coerce_list(security_raw.get("threats")),
                "properties": self._coerce_list(security_raw.get("properties")),
                "quantum_resistant": self._coerce_bool(
                    security_raw.get("quantum_resistant"),
                    default=quantum_hint or fallback_requirement.security.quantum_resistant,
                ),
            }
        else:
            security = {
                "security_level": self._coerce_security_level(
                    response.get("security_level"),
                    raw,
                    fallback_requirement.security.security_level,
                ),
                "threats": self._coerce_list(response.get("threats")),
                "properties": self._coerce_list(response.get("properties")),
                "quantum_resistant": self._coerce_bool(
                    response.get("quantum_resistant"),
                    default=quantum_hint or fallback_requirement.security.quantum_resistant,
                ),
            }

        performance_raw = response.get("performance") or response.get("performance_constraints")
        inferred_performance = self._infer_performance_constraints(description)
        if isinstance(performance_raw, dict):
            performance = {
                "max_latency": self._coerce_optional_string(performance_raw.get("max_latency")) or inferred_performance["max_latency"],
                "min_throughput": self._coerce_optional_string(performance_raw.get("min_throughput")),
                "max_memory": self._coerce_optional_string(performance_raw.get("max_memory")) or inferred_performance["max_memory"],
                "max_power": self._coerce_optional_string(performance_raw.get("max_power")),
                "max_code_size": self._coerce_optional_string(performance_raw.get("max_code_size")),
            }
        else:
            performance = {
                "max_latency": self._coerce_optional_string(response.get("max_latency")) or inferred_performance["max_latency"],
                "min_throughput": self._coerce_optional_string(response.get("min_throughput")),
                "max_memory": self._coerce_optional_string(response.get("max_memory")) or inferred_performance["max_memory"],
                "max_power": self._coerce_optional_string(response.get("max_power")),
                "max_code_size": self._coerce_optional_string(response.get("max_code_size")),
            }

        normalized = {
            "scheme_type": self._coerce_scheme_type(
                response.get("scheme_type") or response.get("type"),
                raw,
                fallback_requirement.scheme_type,
            ),
            "target_platform": target_platform,
            "security": security,
            "performance": performance,
            "additional_features": self._coerce_list(response.get("additional_features")),
            "preferences": self._coerce_dict(response.get("preferences")),
            "confidence": self._coerce_confidence(response.get("confidence"), fallback.confidence),
            "ambiguities": self._coerce_list(response.get("ambiguities")),
            "assumptions": self._coerce_list(response.get("assumptions")),
        }

        notes = self._coerce_list(response.get("notes")) + self._coerce_list(response.get("analysis"))
        if notes and not normalized["assumptions"]:
            normalized["assumptions"] = notes

        return normalized

    def _refine_structured_defaults(self, normalized: Dict[str, Any], description: str) -> Dict[str, Any]:
        """Adjust low-information but valid structured outputs toward enterprise-safe defaults."""

        refined = dict(normalized)
        raw = description.lower()
        target_platform = dict(refined.get("target_platform") or {})
        security = dict(refined.get("security") or {})
        performance = dict(refined.get("performance") or {})
        additional_features = list(refined.get("additional_features") or [])

        regulated_data_context = any(
            keyword in description
            for keyword in [
                "数据平台", "支付", "清结算",
                "建筑", "BIM", "IFC", "图纸", "工程验收", "工地", "竣工模型",
            ]
        ) or any(
            keyword in raw
            for keyword in [
                "pci dss", "payment", "settlement",
                "construction", "building", "bim", "ifc", "openbim", "cde",
            ]
        )

        if refined.get("scheme_type") == SchemeType.ENCRYPTION and regulated_data_context:
            refined["scheme_type"] = SchemeType.AUTHENTICATED_ENCRYPTION

        platform_value = target_platform.get("type")
        platform_type = None
        if isinstance(platform_value, PlatformType):
            platform_type = platform_value
        elif isinstance(platform_value, str):
            try:
                platform_type = PlatformType(platform_value)
            except ValueError:
                platform_type = None

        baseline_level = self._infer_baseline_security_level(description, platform_type=platform_type)
        if int(security.get("security_level", 0) or 0) < baseline_level:
            security["security_level"] = baseline_level

        if regulated_data_context and "quantum_resistant" in security:
            security["quantum_resistant"] = bool(security["quantum_resistant"]) or self._infer_quantum_requirement(
                raw,
                {"additional_features": additional_features},
                security,
            )

        if performance.get("max_latency") is None and (
            any(keyword in description for keyword in ["低延迟", "低时延"]) or "low latency" in raw
        ):
            performance["max_latency"] = "low-latency"

        refined["target_platform"] = target_platform
        refined["security"] = security
        refined["performance"] = performance
        refined["additional_features"] = additional_features
        return refined

    def _coerce_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            parts = re.split(r"[\n,;；、]+", text)
            return [item.strip(" -") for item in parts if item.strip(" -")]
        return [str(value).strip()] if str(value).strip() else []

    def _coerce_dict(self, value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _coerce_optional_string(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _coerce_bool(self, value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "1", "required", "needed"}:
                return True
            if lowered in {"false", "no", "0", "not required"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    def _coerce_confidence(self, value: Any, default: float) -> float:
        try:
            if value is None:
                return default
            confidence = float(value)
            return min(1.0, max(0.0, confidence))
        except (TypeError, ValueError):
            return default

    def _coerce_security_level(self, value: Any, raw: str, default: int) -> int:
        if isinstance(value, (int, float)) and int(value) > 0:
            return int(value)
        if isinstance(value, str):
            match = re.search(r"(128|192|256)", value)
            if match:
                return int(match.group(1))
        if "256" in raw and "sha-256" not in raw:
            return 256
        if "192" in raw:
            return 192
        if "128" in raw:
            return 128
        inferred = self._infer_baseline_security_level(raw)
        return inferred or default

    def _coerce_scheme_type(self, value: Any, raw: str, default: SchemeType) -> SchemeType:
        if isinstance(value, SchemeType):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower().replace("-", "_").replace(" ", "_")
            aliases = {
                "aead": SchemeType.AUTHENTICATED_ENCRYPTION,
                "authenticated_encryption": SchemeType.AUTHENTICATED_ENCRYPTION,
                "encryption": SchemeType.ENCRYPTION,
                "signature": SchemeType.SIGNATURE,
                "signing": SchemeType.SIGNATURE,
                "key_exchange": SchemeType.KEY_EXCHANGE,
                "key_agreement": SchemeType.KEY_EXCHANGE,
                "hash": SchemeType.HASH,
                "mac": SchemeType.MAC,
                "key_derivation": SchemeType.KEY_DERIVATION,
                "random_number_generation": SchemeType.RANDOM_NUMBER_GENERATION,
                "rng": SchemeType.RANDOM_NUMBER_GENERATION,
            }
            if lowered in aliases:
                return aliases[lowered]
            try:
                return SchemeType(lowered)
            except ValueError:
                pass

        heuristic = self._fallback_parse(raw).requirement.scheme_type
        return heuristic or default

    def _coerce_platform_type(self, value: Any, raw: str, default: PlatformType) -> PlatformType:
        if isinstance(value, PlatformType):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower().replace("-", "_").replace(" ", "_")
            aliases = {
                "iot": PlatformType.IOT_DEVICE,
                "iot_device": PlatformType.IOT_DEVICE,
                "embedded": PlatformType.EMBEDDED,
                "mobile": PlatformType.MOBILE,
                "desktop": PlatformType.DESKTOP,
                "server": PlatformType.SERVER,
                "cloud": PlatformType.CLOUD,
                "web": PlatformType.WEB,
            }
            if lowered in aliases:
                return aliases[lowered]
            try:
                return PlatformType(lowered)
            except ValueError:
                pass

        return self._fallback_parse(raw).requirement.target_platform.type or default

    def _coerce_resource_level(self, value: Any, raw: str, default: ResourceLevel) -> ResourceLevel:
        if isinstance(value, ResourceLevel):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower().replace("-", "_").replace(" ", "_")
            aliases = {
                "ultra_light": ResourceLevel.ULTRA_LIGHTWEIGHT,
                "ultra_lightweight": ResourceLevel.ULTRA_LIGHTWEIGHT,
                "light": ResourceLevel.LIGHTWEIGHT,
                "lightweight": ResourceLevel.LIGHTWEIGHT,
                "moderate": ResourceLevel.MODERATE,
                "high": ResourceLevel.HIGH_PERFORMANCE,
                "high_performance": ResourceLevel.HIGH_PERFORMANCE,
            }
            if lowered in aliases:
                return aliases[lowered]
            try:
                return ResourceLevel(lowered)
            except ValueError:
                pass

        return self._fallback_parse(raw).requirement.target_platform.resource_level or default

    def _infer_quantum_requirement(
        self,
        raw: str,
        response: Dict[str, Any],
        security_block: Dict[str, Any],
    ) -> bool:
        signal_text = " ".join(
            [
                raw,
                str(response.get("additional_features", "")),
                str(response.get("preferences", "")),
                str(response.get("threats", "")),
                str(security_block.get("threats", "")),
                str(security_block.get("properties", "")),
            ]
        ).lower()
        return any(
            keyword in signal_text
            for keyword in [
                "post_quantum",
                "post-quantum",
                "post quantum",
                "quantum resistant",
                "quantum-safe",
                "后量子",
            ]
        )

    def _infer_performance_constraints(self, description: str) -> Dict[str, Optional[str]]:
        raw = description.lower()
        memory_match = re.search(r"(\d+(?:\.\d+)?)\s*(kb|mb|gb)", raw, re.IGNORECASE)
        latency_match = re.search(r"(\d+(?:\.\d+)?)\s*(ms|s)", raw, re.IGNORECASE)
        return {
            "max_memory": f"{memory_match.group(1)}{memory_match.group(2).upper()}" if memory_match else None,
            "max_latency": f"{latency_match.group(1)}{latency_match.group(2)}" if latency_match else None,
        }

    def _infer_baseline_security_level(self, description: str, platform_type: Optional[PlatformType] = None) -> int:
        raw = description.lower()
        lightweight_context = platform_type == PlatformType.IOT_DEVICE or any(
            keyword in description for keyword in ["物联网", "传感器", "嵌入式"]
        ) or any(keyword in raw for keyword in ["iot", "sensor", "embedded"])
        regulated_or_quantum_context = any(
            keyword in raw
            for keyword in [
                "pci dss",
                "quantum",
                "post-quantum",
                "post quantum",
                "payment",
                "settlement",
                "iso 19650",
                "construction",
                "building",
                "bim",
                "ifc",
            ]
        ) or any(
            keyword in description
            for keyword in ["后量子", "支付", "清结算", "建筑", "施工", "工程验收", "图纸"]
        )
        if lightweight_context and not regulated_or_quantum_context:
            return 128
        if regulated_or_quantum_context:
            return 256
        return 128

    def _normalize_threats(self, threats: List[str]) -> List[str]:
        """Normalize threat strings to match ThreatType enum values."""
        threat_map = {
            "eavesdropping": "eavesdropping",
            "tampering": "tampering",
            "data tampering": "tampering",
            "message tampering": "tampering",
            "replay": "replay",
            "replay attack": "replay",
            "replay attacks": "replay",
            "forgery": "forgery",
            "message forgery": "forgery",
            "man-in-the-middle": "man_in_the_middle",
            "man in the middle": "man_in_the_middle",
            "man-in-the-middle attack": "man_in_the_middle",
            "man-in-the-middle attacks": "man_in_the_middle",
            "mitm": "man_in_the_middle",
            "side-channel": "side_channel",
            "side channel": "side_channel",
            "side-channel attack": "side_channel",
            "side-channel attacks": "side_channel",
            "quantum": "quantum",
            "quantum attack": "quantum",
            "quantum attacks": "quantum",
        }

        normalized: List[str] = []
        for threat in threats:
            threat_lower = threat.lower().strip()
            if threat_lower in threat_map:
                normalized.append(threat_map[threat_lower])
                continue

            matched = False
            for key, value in threat_map.items():
                if key in threat_lower or threat_lower in key:
                    normalized.append(value)
                    matched = True
                    break
            if not matched:
                logger.debug(f"Unknown threat type skipped: {threat}")

        return normalized

    def _fallback_parse(self, description: str) -> ParsedRequirement:
        """Fallback parser with basic heuristics."""

        scheme_type = SchemeType.ENCRYPTION
        platform_type = PlatformType.SERVER
        resource_level = ResourceLevel.MODERATE
        security_level = 128

        desc_lower = description.lower()

        if (
            "authenticated encryption" in desc_lower
            or "aead" in desc_lower
            or "认证加密" in description
            or (
                any(keyword in desc_lower for keyword in ["encryption", "encrypt", "confidentiality"])
                and any(
                    keyword in description for keyword in [
                        "数据平台", "支付", "清结算", "后量子",
                        "建筑", "BIM", "IFC", "图纸", "工程验收", "工地", "竣工模型",
                    ]
                )
            )
            or (
                "加密" in description
                and any(
                    keyword in description for keyword in [
                        "数据平台", "支付", "清结算", "后量子",
                        "传感器", "物联网", "建筑", "BIM", "IFC", "图纸", "工程验收", "工地", "竣工模型",
                    ]
                )
            )
        ):
            scheme_type = SchemeType.AUTHENTICATED_ENCRYPTION
        elif "signature" in desc_lower or "sign" in desc_lower or "签名" in description or "验签" in description:
            scheme_type = SchemeType.SIGNATURE
        elif "key exchange" in desc_lower or "key agreement" in desc_lower or "密钥交换" in description or "密钥协商" in description:
            scheme_type = SchemeType.KEY_EXCHANGE
        elif "hash" in desc_lower or "摘要" in description:
            scheme_type = SchemeType.HASH
        elif "mac" in desc_lower or "消息认证码" in description:
            scheme_type = SchemeType.MAC

        if (
            "iot" in desc_lower
            or "embedded" in desc_lower
            or "物联网" in description
            or "传感器" in description
            or "嵌入式" in description
        ):
            platform_type = PlatformType.IOT_DEVICE
            resource_level = ResourceLevel.LIGHTWEIGHT
        elif "mobile" in desc_lower or "手机" in description:
            platform_type = PlatformType.MOBILE
        elif "cloud" in desc_lower or "server" in desc_lower or "支付" in description or "清结算" in description:
            platform_type = PlatformType.SERVER
            resource_level = ResourceLevel.HIGH_PERFORMANCE

        if (
            "128-bit security" in desc_lower
            or "128 bit security" in desc_lower
            or "with 128-bit" in desc_lower
            or "128-bit 安全" in description
            or "128 位安全" in description
        ):
            security_level = 128
        elif (
            "256-bit security" in desc_lower
            or "256 bit security" in desc_lower
            or "with 256-bit" in desc_lower
            or "256-bit 安全" in description
            or "256 位安全" in description
        ):
            security_level = 256
        elif "128-bit" in desc_lower and "sha-" not in desc_lower:
            security_level = 128
        elif "256-bit" in desc_lower and "sha-256" not in desc_lower and "aes-256" not in desc_lower:
            security_level = 256
        elif re.search(r"\b128\b", description):
            security_level = 128
        elif re.search(r"\b256\b", description) and "sha-256" not in desc_lower:
            security_level = 256
        else:
            security_level = self._infer_baseline_security_level(description, platform_type=platform_type)

        inferred_performance = self._infer_performance_constraints(description)
        threats: List[str] = []
        if "后量子" in description or "quantum" in desc_lower:
            threats.append("quantum")
        if "窃听" in description or "eavesdropping" in desc_lower:
            threats.append("eavesdropping")
        if "中间人" in description or "man-in-the-middle" in desc_lower or "mitm" in desc_lower:
            threats.append("man_in_the_middle")
        if any(item in description for item in ["篡改", "修改", "替换"]):
            threats.append("tampering")
        if "重放" in description or "replay" in desc_lower or "回滚" in description or "rollback" in desc_lower:
            threats.append("replay")
        if any(item in description for item in ["伪造", "冒充", "否认"]):
            threats.append("forgery")

        additional_features: List[str] = []
        if "PCI DSS" in description.upper():
            additional_features.append("pci_dss_compliant")
        if "后量子" in description or "quantum" in desc_lower:
            additional_features.append("post_quantum_resistant")
        if any(item in desc_lower for item in ["bim", "ifc", "openbim", "cde"]) or any(
            item in description for item in ["建筑", "图纸", "工程验收", "工地", "竣工模型"]
        ):
            additional_features.extend(["construction_asset_lineage", "evidence_backed_delivery"])

        requirement = Requirement(
            description=description,
            scheme_type=scheme_type,
            target_platform=TargetPlatform(
                type=platform_type,
                resource_level=resource_level,
            ),
            security=SecurityRequirement(
                security_level=security_level,
                threats=threats,
                quantum_resistant="quantum" in threats,
            ),
            performance=PerformanceConstraint(**inferred_performance),
            additional_features=additional_features,
        )

        return ParsedRequirement(
            requirement=requirement,
            confidence=0.5,
            ambiguities=["Fallback parser used - please review"],
            assumptions=["Default values used for unspecified parameters"],
        )

    def validate(self, requirement: Requirement) -> tuple[bool, List[str]]:
        """Validate a requirement for consistency and completeness."""
        issues: List[str] = []

        if requirement.security.security_level not in [80, 112, 128, 192, 256]:
            issues.append(f"Unusual security level: {requirement.security.security_level}")

        if (
            requirement.target_platform.resource_level == ResourceLevel.ULTRA_LIGHTWEIGHT
            and requirement.security.security_level > 128
        ):
            issues.append("Ultra-lightweight devices may struggle with >128-bit security")

        perf = requirement.performance
        if perf.max_memory and "MB" in perf.max_memory:
            if requirement.target_platform.type == PlatformType.IOT_DEVICE:
                issues.append("IoT devices typically have KB, not MB of RAM")

        return len(issues) == 0, issues
