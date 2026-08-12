"""Cryptographic component models"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    """Types of cryptographic components"""
    BLOCK_CIPHER = "block_cipher"
    STREAM_CIPHER = "stream_cipher"
    HASH_FUNCTION = "hash_function"
    MAC = "mac"
    AEAD = "aead"
    KEY_EXCHANGE = "key_exchange"
    SIGNATURE = "signature"
    MODE_OF_OPERATION = "mode"
    PROTOCOL = "protocol"
    CONSTRUCTION = "construction"
    PUBLIC_KEY_ENCRYPTION = "public_key_encryption"
    RANDOM_NUMBER_GENERATOR = "random_number_generator"
    HOMOMORPHIC_ENCRYPTION = "homomorphic_encryption"
    COMMITMENT_SCHEME = "commitment_scheme"
    ENCRYPTION_SCHEME = "encryption_scheme"


class Performance(BaseModel):
    """Performance characteristics"""
    software_speed: str = Field(description="Software implementation speed")
    hardware_speed: Optional[str] = Field(None, description="Hardware implementation speed")
    memory: str = Field(description="Memory requirements")
    power: str = Field(description="Power consumption")


class ComponentParameters(BaseModel):
    """Component parameters"""
    key_size: Optional[List[int]] = None
    block_size: Optional[int] = None
    output_size: Optional[int] = None
    rounds: Optional[int] = None
    nonce_size: Optional[int] = None
    tag_size: Optional[int] = None


class SecurityAnalysis(BaseModel):
    """Security analysis information"""
    security_level: int = Field(description="Security level in bits")
    best_attack: Optional[str] = Field(None, description="Best known attack")
    attack_complexity: Optional[str] = Field(None, description="Attack complexity")
    status: str = Field(default="secure", description="Security status")
    standardized: bool = Field(default=False, description="Is standardized")
    proven_security: bool = Field(default=False, description="Has security proof")


class SecurityProfile(BaseModel):
    """Disambiguated security claims for selection and evidence review."""

    classical_security_bits: Optional[int] = None
    preimage_security_bits: Optional[int] = None
    collision_security_bits: Optional[int] = None
    nist_pqc_category: Optional[int] = None
    quantum_resistant: bool = False
    proof_model: Optional[str] = None


class StandardMetadata(BaseModel):
    """Structured standard status; never infer this from an algorithm name."""

    organization: str
    identifier: str
    standardized_name: str
    status: str = "unknown"
    published_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    jurisdictions: List[str] = Field(default_factory=list)


class ImplementationSource(BaseModel):
    """Reference to a mature implementation or managed cryptographic service."""

    name: str
    source_type: str
    url: Optional[str] = None
    validation_status: Optional[str] = None


class Reference(BaseModel):
    """Reference to paper, standard, or documentation"""
    type: str = Field(description="Type of reference: paper, standard, documentation")
    title: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    url: Optional[str] = None


class Component(BaseModel):
    """Cryptographic component model"""

    # Basic Information
    id: Optional[str] = None
    name: str = Field(description="Component name")
    full_name: Optional[str] = Field(None, description="Full name")
    category: ComponentType = Field(description="Component category")
    description: Optional[str] = None

    # Parameters
    parameters: ComponentParameters = Field(default_factory=ComponentParameters)

    # Properties
    properties: List[str] = Field(default_factory=list, description="Security properties")

    # Performance
    performance: Performance

    # Security
    security: SecurityAnalysis
    security_profile: Optional[SecurityProfile] = None
    standard: Optional[StandardMetadata] = None
    implementation_sources: List[ImplementationSource] = Field(default_factory=list)

    # Compatibility
    compatible_with: List[str] = Field(default_factory=list)
    not_compatible_with: List[str] = Field(default_factory=list)

    # Use Cases
    use_cases: List[str] = Field(default_factory=list)
    not_recommended_for: List[str] = Field(default_factory=list)

    # References
    references: List[Reference] = Field(default_factory=list)

    # Implementation Notes
    implementation_notes: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Component":
        """Create from dictionary"""
        return cls(**data)

    def is_compatible_with(self, other: "Component") -> bool:
        """Check if compatible with another component"""
        if other.name in self.not_compatible_with:
            return False
        if self.compatible_with and other.name not in self.compatible_with:
            return False
        return True

    def meets_security_level(self, required_level: int) -> bool:
        """Check if meets required security level"""
        return self.security.security_level >= required_level
