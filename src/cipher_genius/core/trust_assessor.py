"""Trust and evidence scoring for generated cryptographic schemes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cipher_genius.models.component import Component, Reference
from cipher_genius.models.scheme import CryptographicScheme
from cipher_genius.reporting import display_trust_level


class TrustAssessor:
    """Build an evidence-backed confidence snapshot for a generated scheme."""

    PQ_KEYWORDS = (
        "kyber",
        "dilithium",
        "sphincs",
        "falcon",
        "mceliece",
        "ntru",
        "saber",
        "ml-kem",
        "ml-dsa",
    )

    def assess(
        self,
        scheme: Optional[CryptographicScheme],
        *,
        parser_confidence: Optional[float] = None,
        compliance_score: Optional[float] = None,
        risk_score: Optional[int] = None,
        audit_passed: Optional[bool] = None,
        quantum_ready: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Return a structured trust assessment for a scheme."""
        if scheme is None:
            return self._empty_assessment()

        components = list(scheme.architecture.components or [])
        component_evidence = [self._assess_component(component) for component in components]
        evidence_coverage = round(
            100 * sum(1 for item in component_evidence if item["reference_count"] > 0) / max(1, len(component_evidence)),
            2,
        )
        standardized_ratio = round(
            100 * sum(1 for component in components if component.security.standardized) / max(1, len(components)),
            2,
        )
        proven_ratio = round(
            100 * sum(1 for component in components if component.security.proven_security) / max(1, len(components)),
            2,
        )
        parser_score = self._clamp((parser_confidence if parser_confidence is not None else 0.65) * 100)
        audit_readiness = self._build_audit_readiness(
            evidence_coverage=evidence_coverage,
            standardized_ratio=standardized_ratio,
            proven_ratio=proven_ratio,
            compliance_score=compliance_score,
            risk_score=risk_score,
            audit_passed=audit_passed,
        )
        algorithm_strength_score = self._build_algorithm_strength(
            scheme,
            standardized_ratio=standardized_ratio,
            proven_ratio=proven_ratio,
            quantum_ready=quantum_ready,
        )
        credibility_score = round(
            self._clamp(
                0.32 * evidence_coverage
                + 0.22 * standardized_ratio
                + 0.14 * proven_ratio
                + 0.10 * parser_score
                + 0.22 * audit_readiness
            ),
            2,
        )

        sources = self._collect_sources(components)
        source_summary = {
            "total_references": sum(item["reference_count"] for item in component_evidence),
            "components_with_references": sum(1 for item in component_evidence if item["reference_count"] > 0),
            "standards": sum(item["standards_count"] for item in component_evidence),
            "papers": sum(item["papers_count"] for item in component_evidence),
            "documentation": sum(item["documentation_count"] for item in component_evidence),
        }
        strengths = self._build_strengths(
            scheme=scheme,
            evidence_coverage=evidence_coverage,
            standardized_ratio=standardized_ratio,
            algorithm_strength_score=algorithm_strength_score,
            audit_passed=audit_passed,
            sources=sources,
        )
        gaps = self._build_gaps(
            scheme=scheme,
            evidence_coverage=evidence_coverage,
            parser_confidence=parser_confidence,
            compliance_score=compliance_score,
            risk_score=risk_score,
            quantum_ready=quantum_ready,
            component_evidence=component_evidence,
        )

        return {
            "credibility_score": credibility_score,
            "algorithm_strength_score": algorithm_strength_score,
            "evidence_coverage": evidence_coverage,
            "audit_readiness": audit_readiness,
            "trust_level": self._score_band(credibility_score),
            "trust_level_label": display_trust_level(self._score_band(credibility_score)),
            "strengths": strengths,
            "gaps": gaps,
            "source_summary": source_summary,
            "sources": sources,
            "component_evidence": component_evidence,
        }

    def _empty_assessment(self) -> Dict[str, Any]:
        return {
            "credibility_score": 0.0,
            "algorithm_strength_score": 0.0,
            "evidence_coverage": 0.0,
            "audit_readiness": 0.0,
            "trust_level": "unknown",
            "trust_level_label": display_trust_level("unknown"),
            "strengths": [],
            "gaps": ["未选择方案，暂时无法生成证据可信度评估。"],
            "source_summary": {},
            "sources": [],
            "component_evidence": [],
        }

    def _assess_component(self, component: Component) -> Dict[str, Any]:
        references = list(component.references or [])
        standards_count = sum(1 for ref in references if str(ref.type).lower() == "standard")
        papers_count = sum(1 for ref in references if str(ref.type).lower() == "paper")
        documentation_count = sum(
            1 for ref in references if str(ref.type).lower() in {"documentation", "doc", "spec"}
        )
        urls_count = sum(1 for ref in references if ref.url)

        score = 0.0
        if component.security.standardized:
            score += 32
        if component.security.proven_security:
            score += 24
        score += min(24, len(references) * 8)
        if standards_count:
            score += 10
        if papers_count:
            score += 8
        if urls_count:
            score += min(6, urls_count * 2)

        credibility_score = round(self._clamp(score), 2)
        return {
            "component": component.name,
            "credibility_score": credibility_score,
            "support_level": self._score_band(credibility_score),
            "support_level_label": display_trust_level(self._score_band(credibility_score)),
            "standardized": bool(component.security.standardized),
            "proven_security": bool(component.security.proven_security),
            "reference_count": len(references),
            "standards_count": standards_count,
            "papers_count": papers_count,
            "documentation_count": documentation_count,
            "reference_titles": [ref.title for ref in references[:5]],
        }

    def _build_audit_readiness(
        self,
        *,
        evidence_coverage: float,
        standardized_ratio: float,
        proven_ratio: float,
        compliance_score: Optional[float],
        risk_score: Optional[int],
        audit_passed: Optional[bool],
    ) -> float:
        if compliance_score is None and risk_score is None and audit_passed is None:
            return round(
                self._clamp(0.6 * evidence_coverage + 0.2 * standardized_ratio + 0.2 * proven_ratio),
                2,
            )

        compliance = self._clamp(compliance_score or 0)
        residual_risk = self._clamp(100 - float(risk_score or 0))
        pass_bonus = 10.0 if audit_passed else 0.0
        return round(self._clamp(0.55 * compliance + 0.35 * residual_risk + pass_bonus), 2)

    def _build_algorithm_strength(
        self,
        scheme: CryptographicScheme,
        *,
        standardized_ratio: float,
        proven_ratio: float,
        quantum_ready: Optional[bool],
    ) -> float:
        security_bits = scheme.parameters.key_size or scheme.requirements.security.security_level or 128
        security_score = self._security_bits_score(int(security_bits))
        quantum_score = self._quantum_score(scheme, quantum_ready)
        return round(
            self._clamp(
                0.35 * security_score
                + 0.30 * standardized_ratio
                + 0.20 * proven_ratio
                + 0.15 * quantum_score
            ),
            2,
        )

    def _security_bits_score(self, security_bits: int) -> float:
        if security_bits >= 256:
            return 100.0
        if security_bits >= 192:
            return 88.0
        if security_bits >= 128:
            return 74.0
        if security_bits >= 112:
            return 56.0
        return 28.0

    def _quantum_score(self, scheme: CryptographicScheme, quantum_ready: Optional[bool]) -> float:
        if quantum_ready is True:
            return 100.0

        component_names = " ".join(component.name.lower() for component in scheme.architecture.components)
        contains_pq = any(keyword in component_names for keyword in self.PQ_KEYWORDS)
        if contains_pq:
            return 100.0

        if scheme.requirements.security.quantum_resistant:
            return 30.0

        security_bits = scheme.parameters.key_size or scheme.requirements.security.security_level or 128
        if security_bits >= 256 and any(token in component_names for token in ("aes", "sha")):
            return 78.0
        return 62.0

    def _collect_sources(self, components: List[Component], max_items: int = 8) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for component in components:
            for reference in component.references or []:
                key = (component.name.lower(), reference.title.lower())
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(self._serialize_reference(component.name, reference))

        deduped.sort(
            key=lambda item: (
                0 if item["type"] == "standard" else 1,
                -(item["year"] or 0),
                item["title"].lower(),
            )
        )
        return deduped[:max_items]

    def _serialize_reference(self, component_name: str, reference: Reference) -> Dict[str, Any]:
        return {
            "type": str(reference.type),
            "title": reference.title,
            "year": reference.year,
            "url": reference.url,
            "component": component_name,
        }

    def _build_strengths(
        self,
        *,
        scheme: CryptographicScheme,
        evidence_coverage: float,
        standardized_ratio: float,
        algorithm_strength_score: float,
        audit_passed: Optional[bool],
        sources: List[Dict[str, Any]],
    ) -> List[str]:
        strengths: List[str] = []
        if evidence_coverage >= 75:
            strengths.append("大部分选定组件都附带可追溯的标准或参考资料。")
        if standardized_ratio >= 60:
            strengths.append("该方案主要由标准化密码组件构成。")
        if any(item["type"] == "standard" for item in sources):
            strengths.append("当前证据集中包含正式标准，能够支撑企业评审。")
        if algorithm_strength_score >= 80:
            strengths.append("该算法组合在高保障场景下表现出较强的安全实力。")
        if audit_passed:
            strengths.append("当前已通过 MAS 审计门禁，生产就绪度更高。")
        if scheme.requirements.security.quantum_resistant and self._quantum_score(scheme, None) >= 80:
            strengths.append("当前设计已包含清晰的后量子迁移路径。")
        return strengths[:6]

    def _build_gaps(
        self,
        *,
        scheme: CryptographicScheme,
        evidence_coverage: float,
        parser_confidence: Optional[float],
        compliance_score: Optional[float],
        risk_score: Optional[int],
        quantum_ready: Optional[bool],
        component_evidence: List[Dict[str, Any]],
    ) -> List[str]:
        gaps: List[str] = []
        if evidence_coverage < 50:
            gaps.append("证据覆盖率偏低，部分组件缺少有力的参考依据。")
        elif evidence_coverage < 75:
            gaps.append("证据覆盖仍不完整，建议补充更多标准文档或一手论文。")

        weak_components = [item["component"] for item in component_evidence if item["credibility_score"] < 60]
        if weak_components:
            preview = ", ".join(weak_components[:3])
            gaps.append(f"部分组件的支撑元数据不足：{preview}。")

        if parser_confidence is not None and parser_confidence < 0.7:
            gaps.append("需求解析置信度一般，建议在批准前进一步澄清约束。")

        if compliance_score is not None and compliance_score < 80:
            gaps.append(f"合规得分仍低于企业目标：{round(float(compliance_score), 2)}。")

        if risk_score is not None and risk_score > 50:
            gaps.append(f"剩余风险仍偏高：{int(risk_score)}/100。")

        if scheme.requirements.security.quantum_resistant and not (quantum_ready or self._quantum_score(scheme, None) >= 80):
            gaps.append("需求要求具备后量子安全，但当前技术栈尚未完全满足。")

        return gaps[:6]

    def _score_band(self, score: float) -> str:
        if score >= 85:
            return "high"
        if score >= 65:
            return "medium"
        if score > 0:
            return "low"
        return "unknown"

    def _clamp(self, value: float, lower: float = 0.0, upper: float = 100.0) -> float:
        return max(lower, min(upper, float(value)))
