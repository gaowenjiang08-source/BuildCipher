"""Application service layer for API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from cipher_genius.api.schemas import (
    GenerateRequest,
    GenerateResponse,
    ParsedRequirementPayload,
    SchemeComponentPayload,
    SchemeImplementationPayload,
    SchemePayload,
)
from cipher_genius.codegen.generator import CodeGenerator
from cipher_genius.core.generator import SchemeGenerator
from cipher_genius.core.parser import RequirementParser
from cipher_genius.core.safety_notice import SECURITY_DISCLAIMER_TEXT
from cipher_genius.core.trust_assessor import TrustAssessor
from cipher_genius.models.scheme import CryptographicScheme


class GenerationService:
    """Orchestrates parse -> generate -> codegen pipeline for API callers."""

    def __init__(self, llm_provider: str | None = None):
        self.parser = RequirementParser(llm_provider)
        self.generator = SchemeGenerator(llm_provider)
        self.codegen = CodeGenerator(llm_provider)
        self.trust_assessor = TrustAssessor()

    def generate(self, payload: GenerateRequest) -> GenerateResponse:
        """Generate schemes from a request payload."""
        parsed = self.parser.parse(payload.requirement)
        schemes = self.generator.generate(parsed.requirement, num_variants=payload.num_variants)

        if payload.generate_code:
            for scheme in schemes:
                scheme.implementation = self.codegen.generate_all(scheme)

        serialized_schemes = [
            self._serialize_scheme(scheme, parser_confidence=parsed.confidence) for scheme in schemes
        ]
        parsed_payload = ParsedRequirementPayload(
            requirement=parsed.requirement.model_dump(),
            confidence=parsed.confidence,
            ambiguities=parsed.ambiguities,
            assumptions=parsed.assumptions,
        )

        return GenerateResponse(
            request_id=str(uuid4()),
            generated_at=datetime.now(timezone.utc),
            security_disclaimer=SECURITY_DISCLAIMER_TEXT,
            parsed_requirement=parsed_payload,
            schemes=serialized_schemes,
        )

    def _serialize_scheme(self, scheme: CryptographicScheme, parser_confidence: float | None = None) -> SchemePayload:
        components: List[SchemeComponentPayload] = []
        for component in scheme.architecture.components:
            components.append(
                SchemeComponentPayload(
                    name=component.name,
                    category=str(component.category),
                    security_level=component.security.security_level,
                    software_speed=component.performance.software_speed,
                    standardized=bool(component.security.standardized),
                    proven_security=bool(component.security.proven_security),
                    reference_count=len(component.references or []),
                    reference_titles=[ref.title for ref in (component.references or [])[:3]],
                )
            )

        implementation = SchemeImplementationPayload(
            pseudocode=scheme.implementation.pseudocode,
            python=scheme.implementation.python,
            c=scheme.implementation.c,
        )
        credibility_assessment = self.trust_assessor.assess(
            scheme,
            parser_confidence=parser_confidence,
        )

        return SchemePayload(
            name=scheme.metadata.name,
            scheme_type=str(scheme.metadata.scheme_type),
            score=scheme.score,
            generated_at=scheme.metadata.generated_at,
            security_level=scheme.requirements.security.security_level,
            components=components,
            design_rationale=scheme.design_rationale,
            security_analysis=scheme.security_analysis.model_dump(),
            credibility_assessment=credibility_assessment,
            implementation=implementation,
            raw=scheme.model_dump(),
        )
