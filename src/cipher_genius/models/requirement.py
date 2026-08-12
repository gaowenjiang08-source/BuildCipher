"""Requirement models for scheme generation"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SchemeType(str, Enum):
    """Types of cryptographic schemes"""
    ENCRYPTION = "encryption"
    AUTHENTICATED_ENCRYPTION = "authenticated_encryption"
    SIGNATURE = "signature"
    KEY_EXCHANGE = "key_exchange"
    HASH = "hash"
    MAC = "mac"
    KEY_DERIVATION = "key_derivation"
    RANDOM_NUMBER_GENERATION = "random_number_generation"


class PlatformType(str, Enum):
    """Target platform types"""
    IOT_DEVICE = "iot_device"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    SERVER = "server"
    EMBEDDED = "embedded"
    CLOUD = "cloud"
    WEB = "web"


class ResourceLevel(str, Enum):
    """Resource constraint levels"""
    ULTRA_LIGHTWEIGHT = "ultra_lightweight"
    LIGHTWEIGHT = "lightweight"
    MODERATE = "moderate"
    HIGH_PERFORMANCE = "high_performance"


class ThreatType(str, Enum):
    """Types of security threats"""
    EAVESDROPPING = "eavesdropping"
    TAMPERING = "tampering"
    REPLAY = "replay"
    FORGERY = "forgery"
    MAN_IN_THE_MIDDLE = "man_in_the_middle"
    SIDE_CHANNEL = "side_channel"
    QUANTUM = "quantum"


class SecurityRequirement(BaseModel):
    """Security requirements"""
    security_level: int = Field(description="Security level in bits (e.g., 128, 256)")
    threats: List[ThreatType] = Field(default_factory=list, description="Threats to defend against")
    properties: List[str] = Field(
        default_factory=list,
        description="Required security properties (e.g., IND-CCA2, EUF-CMA)"
    )
    quantum_resistant: bool = Field(default=False, description="Require quantum resistance")


class PerformanceConstraint(BaseModel):
    """Performance constraints"""
    max_latency: Optional[str] = Field(None, description="Maximum latency (e.g., '10ms')")
    min_throughput: Optional[str] = Field(None, description="Minimum throughput (e.g., '10KB/s')")
    max_memory: Optional[str] = Field(None, description="Maximum memory (e.g., '2KB')")
    max_power: Optional[str] = Field(None, description="Maximum power consumption")
    max_code_size: Optional[str] = Field(None, description="Maximum code size")


class TargetPlatform(BaseModel):
    """Target platform specification"""
    type: PlatformType
    resource_level: ResourceLevel
    details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional platform details (e.g., CPU type, RAM size)"
    )


class Requirement(BaseModel):
    """Complete requirement specification for scheme generation"""

    # Description
    description: str = Field(description="Natural language description of requirements")

    # Scheme Type
    scheme_type: SchemeType = Field(description="Type of scheme to generate")

    # Target Platform
    target_platform: TargetPlatform

    # Security Requirements
    security: SecurityRequirement

    # Performance Constraints
    performance: PerformanceConstraint = Field(default_factory=PerformanceConstraint)

    # Additional Features
    additional_features: List[str] = Field(
        default_factory=list,
        description="Additional features (e.g., 'key rotation', 'forward secrecy')"
    )

    # Preferences
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences (e.g., 'prefer_standard': True)"
    )

    class Config:
        use_enum_values = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Requirement":
        """Create from dictionary"""
        return cls(**data)

    def get_summary(self) -> str:
        """Get a human-readable summary"""
        summary = f"Scheme Type: {self.scheme_type}\n"
        summary += f"Platform: {self.target_platform.type} ({self.target_platform.resource_level})\n"
        summary += f"Security Level: {self.security.security_level}-bit\n"

        if self.performance.max_latency:
            summary += f"Max Latency: {self.performance.max_latency}\n"
        if self.performance.max_memory:
            summary += f"Max Memory: {self.performance.max_memory}\n"

        if self.security.threats:
            summary += f"Threats: {', '.join(self.security.threats)}\n"

        return summary


class ParsedRequirement(BaseModel):
    """Result of requirement parsing"""
    requirement: Requirement
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in parsing accuracy"
    )
    ambiguities: List[str] = Field(
        default_factory=list,
        description="Identified ambiguities or unclear aspects"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made during parsing"
    )
