"""Cryptographic scheme models"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from cipher_genius.models.component import Component
from cipher_genius.models.requirement import Requirement


class SchemeMetadata(BaseModel):
    """Metadata for a cryptographic scheme"""
    name: str
    scheme_type: str
    version: str = "1.0"
    generated_at: datetime = Field(default_factory=datetime.now)
    generator_version: str = "0.1.0"


class SchemeArchitecture(BaseModel):
    """Architecture of the cryptographic scheme"""
    components: List[Component] = Field(
        default_factory=list,
        description="Components used in the scheme"
    )
    composition: Dict[str, Any] = Field(
        default_factory=dict,
        description="How components are composed"
    )
    dataflow: List[str] = Field(
        default_factory=list,
        description="Data flow description"
    )


class SchemeParameters(BaseModel):
    """Parameters of the cryptographic scheme"""
    key_size: Optional[int] = None
    block_size: Optional[int] = None
    nonce_size: Optional[int] = None
    tag_size: Optional[int] = None
    rounds: Optional[int] = None
    additional_params: Dict[str, Any] = Field(default_factory=dict)


class SecurityAnalysis(BaseModel):
    """Security analysis of the scheme"""
    threat_model: Dict[str, Any] = Field(
        default_factory=dict,
        description="Threat model description"
    )
    properties: List[str] = Field(
        default_factory=list,
        description="Security properties provided (e.g., IND-CCA2)"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Security assumptions"
    )
    proof_outline: Optional[str] = Field(
        None,
        description="Outline of security proof"
    )
    concerns: List[str] = Field(
        default_factory=list,
        description="Security concerns or caveats"
    )


class Implementation(BaseModel):
    """Implementation details"""
    pseudocode: str = ""
    python: str = ""
    c: str = ""
    rust: str = ""


class TestVector(BaseModel):
    """Test vector for validation"""
    name: str
    inputs: Dict[str, str]
    expected_output: str
    description: Optional[str] = None


class TheoreticalAnalysis(BaseModel):
    """Theoretical performance analysis"""
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    computational_cost: Optional[str] = None


class Benchmark(BaseModel):
    """Performance benchmark"""
    platform: str
    throughput: Optional[str] = None
    latency: Optional[str] = None
    memory_usage: Optional[str] = None
    power_consumption: Optional[str] = None


class Evaluation(BaseModel):
    """Evaluation metrics"""
    theoretical: TheoreticalAnalysis = Field(default_factory=TheoreticalAnalysis)
    benchmarks: List[Benchmark] = Field(default_factory=list)


class CryptographicScheme(BaseModel):
    """Complete cryptographic scheme representation"""

    # Metadata
    metadata: SchemeMetadata

    # Original Requirements
    requirements: Requirement

    # Architecture
    architecture: SchemeArchitecture = Field(default_factory=SchemeArchitecture)

    # Parameters
    parameters: SchemeParameters = Field(default_factory=SchemeParameters)

    # Security Analysis
    security_analysis: SecurityAnalysis = Field(default_factory=SecurityAnalysis)

    # Implementation
    implementation: Implementation = Field(default_factory=Implementation)

    # Test Vectors
    test_vectors: List[TestVector] = Field(default_factory=list)

    # Evaluation
    evaluation: Evaluation = Field(default_factory=Evaluation)

    # Design Rationale
    design_rationale: str = ""

    # Score (for ranking multiple schemes)
    score: float = Field(default=0.0, ge=0.0, le=10.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CryptographicScheme":
        """Create from dictionary"""
        return cls(**data)

    def get_component_names(self) -> List[str]:
        """Get names of all components"""
        return [comp.name for comp in self.architecture.components]

    def get_specification(self) -> str:
        """Generate human-readable specification"""
        spec = f"# {self.metadata.name}\n\n"
        spec += f"**Type:** {self.metadata.scheme_type}\n"
        spec += f"**Security Level:** {self.requirements.security.security_level}-bit\n\n"

        spec += "## Components\n"
        for comp in self.architecture.components:
            spec += f"- {comp.name} ({comp.category})\n"
        spec += "\n"

        spec += "## Parameters\n"
        if self.parameters.key_size:
            spec += f"- Key Size: {self.parameters.key_size} bits\n"
        if self.parameters.block_size:
            spec += f"- Block Size: {self.parameters.block_size} bits\n"
        if self.parameters.nonce_size:
            spec += f"- Nonce Size: {self.parameters.nonce_size} bits\n"
        if self.parameters.tag_size:
            spec += f"- Tag Size: {self.parameters.tag_size} bits\n"
        spec += "\n"

        spec += "## Security Properties\n"
        for prop in self.security_analysis.properties:
            spec += f"- {prop}\n"
        spec += "\n"

        if self.security_analysis.concerns:
            spec += "## Security Concerns\n"
            for concern in self.security_analysis.concerns:
                spec += f"⚠ {concern}\n"
            spec += "\n"

        if self.design_rationale:
            spec += "## Design Rationale\n"
            spec += self.design_rationale + "\n\n"

        return spec

    def get_summary(self) -> str:
        """Get a brief summary"""
        summary = f"{self.metadata.name} (Score: {self.score:.1f}/10)\n"
        summary += f"Components: {', '.join(self.get_component_names())}\n"
        summary += f"Security: {self.requirements.security.security_level}-bit\n"
        return summary
