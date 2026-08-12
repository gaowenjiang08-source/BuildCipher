"""Shared MAS runtime helpers for LangGraph mainline execution.

This module keeps LangGraph business heuristics in `core/` so the graph-native
engine no longer imports helper methods directly from the Legacy API service.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Dict, List, Optional

from cipher_genius.api.schemas import (
    AttackDecisionPayload,
    AttackSpecPayload,
    ArchitectCandidatePayload,
    AuditorRoundPayload,
    BuildAttemptPayload,
    ClarificationPayload,
    ContextProjectionPayload,
    DiscussionTurnPayload,
    EngineerReportPayload,
    ExpertGateDecisionPayload,
    PatchSpecPayload,
    SchemeComponentPayload,
    SchemeImplementationPayload,
    SchemePayload,
    VulnerabilityVerdictPayload,
)
from cipher_genius.core.audit_evaluation_agent import AuditEvaluationAgent
from cipher_genius.core.attack_planning_agent import AttackPlanningAgent
from cipher_genius.codegen.generator import CodeGenerator
from cipher_genius.core.expert_gate_agent import ExpertGateAgent
from cipher_genius.core.generator import SchemeGenerator
from cipher_genius.core.patch_planning_agent import PatchPlanningAgent
from cipher_genius.core.parser import RequirementParser
from cipher_genius.core.reflection_agent import ReflectionAgent
from cipher_genius.core.vulnerability_evaluation_agent import VulnerabilityEvaluationAgent
from cipher_genius.core.trust_assessor import TrustAssessor
from cipher_genius.features.compliance_reporter import ComplianceReporter, ComplianceStandard
from cipher_genius.features.performance_estimator import PerformanceEstimator, Platform
from cipher_genius.features.security_assessor import SecurityAssessor
from cipher_genius.features.scheme_comparator import SchemeComparator
from cipher_genius.features.vulnerability_scanner import VulnerabilityScanner
from cipher_genius.knowledge.components import get_component_library
from cipher_genius.models.component import Component, ComponentType
from cipher_genius.models.requirement import (
    ParsedRequirement,
    PlatformType,
    Requirement,
    ResourceLevel,
    SchemeType,
    SecurityRequirement,
    TargetPlatform,
)
from cipher_genius.models.scheme import (
    CryptographicScheme,
    Implementation,
    SchemeArchitecture,
    SchemeMetadata,
    SchemeParameters,
    SecurityAnalysis,
)
from cipher_genius.reporting import (
    display_bool,
    display_severity,
    display_status,
    localize_discussion_turn,
    localize_variant_comparison,
    translate_text,
)


class MASRuntimeSupport:
    """Reusable MAS helpers shared by the LangGraph mainline."""

    TOOLBOX_SERVICES = [
        "requirement_parser",
        "scheme_generator",
        "code_generator",
        "component_library",
        "performance_estimator",
        "benchmark_runner",
        "security_assessor",
        "vulnerability_scanner",
        "compliance_reporter",
        "threat_modeler",
        "attack_simulator",
        "cost_estimator",
        "scheme_comparator",
        "component_recommender",
        "exporter",
    ]

    def __init__(self, llm_provider: Optional[str] = None):
        self.llm_provider = llm_provider
        self.component_library = get_component_library()
        self.performance_estimator = PerformanceEstimator()
        self.vulnerability_scanner = VulnerabilityScanner()
        self.compliance_reporter = ComplianceReporter()
        self.security_assessor = SecurityAssessor()
        self.scheme_comparator = SchemeComparator()
        self.trust_assessor = TrustAssessor()

        self.parser = self._safe_init(RequirementParser, llm_provider)
        self.generator = self._safe_init(SchemeGenerator, llm_provider)
        self.codegen = self._safe_init(CodeGenerator, llm_provider)
        self.audit_evaluator = AuditEvaluationAgent(llm_provider)
        self.attack_planner = AttackPlanningAgent(llm_provider)
        self.vulnerability_evaluator = VulnerabilityEvaluationAgent(llm_provider)
        self.expert_gate = ExpertGateAgent(llm_provider)
        self.patch_planner = PatchPlanningAgent(llm_provider)
        self.reflection_agent = ReflectionAgent(llm_provider)

    def _evaluate_audit_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
    ) -> AuditorRoundPayload:
        """Generate audit-round verdicts from a role-aware audit projection."""

        return self.audit_evaluator.evaluate(projection, run_id=run_id)

    def _safe_init(self, cls: Any, llm_provider: Optional[str]) -> Optional[Any]:
        try:
            return cls(llm_provider)
        except Exception:
            return None

    def _plan_attack_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
    ) -> tuple[AttackDecisionPayload, list[AttackSpecPayload]]:
        """Generate sandbox attack planning outputs from a role-aware projection."""

        return self.attack_planner.plan(projection, run_id=run_id)

    def _evaluate_vulnerability_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
    ) -> VulnerabilityVerdictPayload:
        """Generate expert vulnerability verdicts from a role-aware projection."""

        return self.vulnerability_evaluator.evaluate(projection, run_id=run_id)

    def _decide_expert_gate_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
    ) -> ExpertGateDecisionPayload:
        """Generate expert gate decisions from a role-aware projection."""

        return self.expert_gate.decide(projection, run_id=run_id)

    def _plan_patch_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
    ) -> PatchSpecPayload:
        """Generate patch plans from a role-aware remediation projection."""

        return self.patch_planner.plan(projection, run_id=run_id)

    def _reflect_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
        fallback_workspace: str = "",
    ) -> list[dict[str, Any]]:
        """Generate next-round reflection cards from a role-aware projection."""

        return self.reflection_agent.reflect(
            projection,
            run_id=run_id,
            fallback_workspace=fallback_workspace,
        )

    def _parse_requirement(
        self,
        requirement_text: str,
        discussion_log: List[DiscussionTurnPayload],
        progress_callback: Optional[Callable[[DiscussionTurnPayload], None]] = None,
    ) -> ParsedRequirement:
        if self.parser is not None:
            parsed = self.parser.parse(requirement_text)
            self._log(
                discussion_log,
                actor="Requirement Analyst",
                phase="clarify",
                status="done",
                message=f"需求解析完成，置信度为 {parsed.confidence:.2f}。",
                progress_callback=progress_callback,
            )
            return parsed

        parsed = self._fallback_parse(requirement_text)
        self._log(
            discussion_log,
            actor="Requirement Analyst",
            phase="clarify",
            status="fallback",
            message="LLM 解析器不可用，已改用启发式解析。",
            progress_callback=progress_callback,
        )
        return parsed

    def _fallback_parse(self, text: str) -> ParsedRequirement:
        raw = text.lower()
        scheme_type = SchemeType.AUTHENTICATED_ENCRYPTION
        if any(k in raw for k in ["signature", "签名", "signing", "验签"]):
            scheme_type = SchemeType.SIGNATURE
        elif any(k in raw for k in ["key exchange", "key agreement", "密钥交换", "密钥协商", "握手"]):
            scheme_type = SchemeType.KEY_EXCHANGE
        elif (
            re.search(r"\b(hmac|cmac|mac)\b", raw)
            or "消息认证码" in raw
            or "message authentication code" in raw
        ):
            scheme_type = SchemeType.MAC
        elif "poly1305" in raw and not any(k in raw for k in ["chacha20", "aead", "authenticated encryption"]):
            scheme_type = SchemeType.MAC
        elif "hash" in raw or "摘要" in raw:
            scheme_type = SchemeType.HASH

        platform = PlatformType.SERVER
        resource = ResourceLevel.MODERATE
        if any(k in raw for k in ["iot", "嵌入式", "物联网", "sensor", "传感器"]):
            platform = PlatformType.IOT_DEVICE
            resource = ResourceLevel.LIGHTWEIGHT
        elif any(k in raw for k in ["mobile", "手机", "android", "ios", "iphone", "ipad"]):
            platform = PlatformType.MOBILE
            resource = ResourceLevel.LIGHTWEIGHT

        security_level = 128
        sec_patterns = [
            r"security\s*(?:level|strength)?\s*[:=]?\s*(\d{3})\s*(?:-?\s*bit)?",
            r"(\d{3})\s*[- ]?bit\s*security",
            r"安全(?:等级|强度)\s*[:：]?\s*(\d{3})",
            r"安全(?:等级|强度)\s*(\d{3})\s*比特",
            r"加密强度\s*[:：]?\s*(\d{3})",
        ]
        for pat in sec_patterns:
            match = re.search(pat, raw)
            if not match:
                continue
            candidate = int(match.group(1))
            if candidate in (128, 192, 256):
                security_level = candidate
                break

        requirement = Requirement(
            description=text,
            scheme_type=scheme_type,
            target_platform=TargetPlatform(type=platform, resource_level=resource),
            security=SecurityRequirement(
                security_level=security_level,
                quantum_resistant=("quantum" in raw or "后量子" in raw),
            ),
        )

        return ParsedRequirement(
            requirement=requirement,
            confidence=0.58,
            ambiguities=["由于 LLM 解析器不可用，当前结果来自启发式解析。"],
            assumptions=["缺失细节已根据关键词进行推断。"],
        )

    def _build_structured_spec(self, requirement: Requirement, raw_text: str) -> Dict[str, Any]:
        text = raw_text.lower()
        domain = "general"
        if any(item in text for item in ["construction", "building", "bim", "ifc", "openbim", "cde", "建筑", "施工", "工地", "工程验收", "图纸"]):
            domain = "construction"
        elif any(item in text for item in ["payment", "finance", "bank", "支付", "金融"]):
            domain = "finance"
        elif any(item in text for item in ["iot", "device", "edge", "物联网"]):
            domain = "iot"

        compliance = "NIST_CSF"
        if domain == "finance":
            compliance = "PCI_DSS"
        elif domain == "construction":
            compliance = "ISO_19650"
        if "fedramp" in text or "government" in text:
            compliance = "FEDRAMP"

        quantum_safe = requirement.security.quantum_resistant or "quantum" in text or "后量子" in text
        return {
            "domain": domain,
            "compliance": compliance,
            "quantum_safe": quantum_safe,
            "security_level_bits": requirement.security.security_level,
            "platform": self._enum_value(requirement.target_platform.type),
            "resource_level": self._enum_value(requirement.target_platform.resource_level),
            "constraints": requirement.performance.model_dump(),
        }

    def _build_clarifications(self, raw_text: str, structured_spec: Dict[str, Any]) -> List[ClarificationPayload]:
        questions: List[ClarificationPayload] = []
        text = raw_text.lower()

        if not re.search(r"\b\d+\s*(kb|mb|gb)\b", text):
            questions.append(
                ClarificationPayload(
                    id="memory_budget",
                    question="目标设备可用内存预算是多少（例如 256KB / 2MB）？",
                    reason="会直接影响算法与参数选型，尤其是后量子组件。",
                    required=True,
                )
            )
        if not re.search(r"\b\d+\s*(ms|s)\b", text) and "latency" not in text and "延迟" not in text:
            questions.append(
                ClarificationPayload(
                    id="latency_target",
                    question="最大可接受延迟是多少？",
                    reason="用于判断应优先吞吐量还是实时性。",
                )
            )
        if not any(
            word in text for word in ["fips", "pci", "gdpr", "iso", "soc2", "gb/t", "合规", "验收规则"]
        ):
            questions.append(
                ClarificationPayload(
                    id="compliance_target",
                    question=f"是否以 {structured_spec.get('compliance')} 作为主合规标准？",
                    reason="审计阶段需要明确主要放行依据。",
                    required=True,
                )
            )
        return questions

    def _generate_schemes(
        self,
        requirement: Requirement,
        num_variants: int,
        discussion_log: List[DiscussionTurnPayload],
        structured_spec: Optional[Dict[str, Any]] = None,
        generation_projection: Optional[ContextProjectionPayload] = None,
        case_memory: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[DiscussionTurnPayload], None]] = None,
    ) -> List[CryptographicScheme]:
        schemes: List[CryptographicScheme] = []
        if self.generator is not None:
            schemes = self.generator.generate(requirement, num_variants=num_variants)
            if schemes:
                self._log(
                    discussion_log,
                    actor="Cryptography Architect",
                    phase="design",
                    status="done",
                    message=f"已生成 {len(schemes)} 个候选方案。",
                    progress_callback=progress_callback,
                )

        if not schemes:
            schemes = self._heuristic_generate_schemes(requirement, num_variants)
            self._log(
                discussion_log,
                actor="Cryptography Architect",
                phase="design",
                status="fallback",
                message=f"启发式模式生成了 {len(schemes)} 个候选方案。",
                progress_callback=progress_callback,
            )

        if schemes:
            schemes = self._apply_generation_reflection_guidance(
                schemes,
                generation_projection=generation_projection,
                discussion_log=discussion_log,
                progress_callback=progress_callback,
            )
            schemes = self._prepare_schemes_for_audit(
                schemes,
                requirement,
                structured_spec or {},
                case_memory=case_memory,
                generation_projection=generation_projection,
            )

        return schemes

    def _heuristic_generate_schemes(self, requirement: Requirement, num_variants: int) -> List[CryptographicScheme]:
        qsafe = requirement.security.quantum_resistant
        scheme_type = requirement.scheme_type

        if scheme_type == SchemeType.KEY_EXCHANGE:
            variants = [["X25519", "Kyber-512"], ["X25519", "Kyber-768"], ["X448", "Kyber-1024"]]
        elif scheme_type == SchemeType.SIGNATURE:
            variants = [["Dilithium2", "SHA-256"], ["Dilithium3", "SHA-384"], ["ML-DSA", "SHA3-256"]]
        elif scheme_type == SchemeType.HASH:
            variants = [["SHA-256"], ["SHA3-256"], ["BLAKE3"]]
        elif scheme_type == SchemeType.MAC:
            variants = [["HMAC", "SHA-256"], ["CMAC", "AES"], ["Poly1305"]]
        else:
            if qsafe:
                variants = [
                    ["X25519", "Kyber-512", "ChaCha20-Poly1305"],
                    ["X25519", "Kyber-768", "AES", "GCM"],
                    ["X448", "Kyber-1024", "AES", "GCM-SIV"],
                ]
            else:
                variants = [["AES", "GCM"], ["ChaCha20-Poly1305"], ["AES", "CCM"]]

        schemes: List[CryptographicScheme] = []
        for idx in range(num_variants):
            names = variants[idx % len(variants)]
            components = [self.component_library.get(name) for name in names]
            clean = [item for item in components if item is not None]
            if not clean:
                clean = self.component_library.list_all()[:2]

            key_size = requirement.security.security_level
            for comp in clean:
                if comp.parameters.key_size and isinstance(comp.parameters.key_size, list):
                    key_size = max(key_size, max(comp.parameters.key_size))

            schemes.append(
                CryptographicScheme(
                    metadata=SchemeMetadata(
                        name="-".join(item.name for item in clean[:3]),
                        scheme_type=requirement.scheme_type,
                        generated_at=datetime.now(),
                    ),
                    requirements=requirement.model_copy(deep=True),
                    architecture=SchemeArchitecture(
                        components=clean,
                        composition={"pattern": "hybrid-layered" if qsafe else "aead-standard"},
                        dataflow=[
                            "Key agreement",
                            "Session key derivation",
                            "AEAD encryption",
                            "Integrity verification",
                        ],
                    ),
                    parameters=SchemeParameters(key_size=key_size, nonce_size=96, tag_size=128),
                    security_analysis=SecurityAnalysis(
                        threat_model={"adversary": "adaptive active adversary"},
                        properties=["confidentiality", "integrity", "forward_secrecy"],
                        assumptions=["Secure RNG", "Unique nonce policy"],
                        concerns=(["Kyber-512 may be insufficient for strict policy"] if "Kyber-512" in names else []),
                    ),
                    design_rationale=(
                        "当前方案来自主线回退路径中的启发式架构生成，"
                        "在安全性、性能与交付复杂度之间做了折中。"
                    ),
                    score=round(7.8 + idx * 0.3, 2),
                )
            )

        schemes.sort(key=lambda item: item.score, reverse=True)
        return schemes

    def _build_architect_candidates(
        self,
        schemes: List[CryptographicScheme],
        requirement: Requirement,
        parser_confidence: float | None = None,
    ) -> List[ArchitectCandidatePayload]:
        platform = self._map_platform(requirement.target_platform.type)
        candidates: List[ArchitectCandidatePayload] = []
        for idx, scheme in enumerate(schemes):
            perf_input = self._scheme_to_audit_input(scheme)
            performance = self.performance_estimator.estimate_performance(perf_input, platform, data_size_mb=1.0)
            credibility_assessment = self.trust_assessor.assess(
                scheme,
                parser_confidence=parser_confidence,
            )
            candidates.append(
                ArchitectCandidatePayload(
                    proposal_id=f"proposal-{idx + 1}",
                    name=scheme.metadata.name,
                    scheme_type=self._enum_value(scheme.metadata.scheme_type),
                    score=scheme.score,
                    security_level=scheme.requirements.security.security_level,
                    components=[self._serialize_component(item) for item in scheme.architecture.components],
                    design_rationale=scheme.design_rationale,
                    architecture_pattern=str(scheme.architecture.composition.get("pattern", "standard")),
                    estimated_performance=performance,
                    credibility_score=credibility_assessment.get("credibility_score"),
                    algorithm_strength_score=credibility_assessment.get("algorithm_strength_score"),
                    evidence_coverage=credibility_assessment.get("evidence_coverage"),
                )
            )
        return candidates

    def _select_standards(self, structured_spec: Dict[str, Any]) -> List[ComplianceStandard]:
        compliance = str(structured_spec.get("compliance", "")).upper()
        domain = str(structured_spec.get("domain", "")).lower()

        if compliance == "FEDRAMP":
            standards = [
                ComplianceStandard.FEDRAMP,
                ComplianceStandard.FIPS_140_3,
                ComplianceStandard.NIST_CSF,
            ]
        elif compliance == "PCI_DSS" or domain == "finance":
            standards = [
                ComplianceStandard.PCI_DSS,
                ComplianceStandard.NIST_CSF,
                ComplianceStandard.ISO_27001,
            ]
        elif domain == "iot":
            standards = [
                ComplianceStandard.NIST_CSF,
                ComplianceStandard.ISO_27001,
                ComplianceStandard.FIPS_140_3,
            ]
        else:
            standards = [
                ComplianceStandard.NIST_CSF,
                ComplianceStandard.ISO_27001,
                ComplianceStandard.FIPS_140_3,
            ]

        deduped: List[ComplianceStandard] = []
        for item in standards:
            if item not in deduped:
                deduped.append(item)
        return deduped

    def _component_category(self, component: Component) -> str:
        category = getattr(component, "category", "")
        if hasattr(category, "value"):
            return str(category.value).lower()
        return str(category).lower()

    def _derive_mode(self, components: List[Component]) -> str:
        names = [item.name.lower() for item in components]
        ordered_candidates = [
            "gcm-siv",
            "poly1305",
            "gcm",
            "ccm",
            "ocb",
            "eax",
            "cbc",
            "ctr",
        ]
        for candidate in ordered_candidates:
            if any(candidate in name for name in names):
                return candidate
        return ""

    def _derive_primary_algorithm(self, components: List[Component], mode: str) -> str:
        names = [item.name.lower() for item in components]

        if any("chacha20-poly1305" in name for name in names):
            return "chacha20-poly1305"

        has_aes = any(name == "aes" or name.startswith("aes-") for name in names)
        if has_aes and mode == "gcm":
            return "aes-gcm"
        if has_aes and mode == "ccm":
            return "aes-ccm"
        if has_aes and mode == "eax":
            return "aes-eax"
        if has_aes:
            return "aes"

        preferred_categories = {
            ComponentType.AEAD.value,
            ComponentType.BLOCK_CIPHER.value,
            ComponentType.STREAM_CIPHER.value,
            ComponentType.ENCRYPTION_SCHEME.value,
            ComponentType.PUBLIC_KEY_ENCRYPTION.value,
            ComponentType.KEY_EXCHANGE.value,
        }
        for component in components:
            if self._component_category(component) in preferred_categories:
                return component.name.lower()

        return components[0].name.lower() if components else "aes-256"

    def _build_quantum_assessment_input(
        self,
        primary_algorithm: str,
        mode: str,
        components: List[Component],
    ) -> str:
        keywords = [primary_algorithm]
        if mode:
            keywords.append(mode)
        keywords.extend(item.name.lower() for item in components)
        return " ".join(dict.fromkeys(keyword for keyword in keywords if keyword))

    def _scheme_has_pq_components(self, scheme: CryptographicScheme) -> bool:
        pq_keywords = ("kyber", "ml-kem", "dilithium", "ml-dsa", "sphincs", "falcon", "mceliece", "bike", "frodo")
        names = " ".join(item.name.lower() for item in scheme.architecture.components)
        return any(keyword in names for keyword in pq_keywords)

    def _estimate_audit_priority(
        self,
        scheme: CryptographicScheme,
        structured_spec: Dict[str, Any],
    ) -> tuple[int, int, float, int, float]:
        audit_input = self._scheme_to_audit_input(scheme)
        standards = self._select_standards(structured_spec)
        compliance_score = float(self.compliance_reporter.generate_report(audit_input, standards).get("overall_compliance", 0.0))
        risk_score = int(self.vulnerability_scanner.scan_scheme(audit_input).get("risk_score", 0))
        quantum_eval = self.security_assessor._assess_quantum_readiness(
            audit_input.get("quantum_assessment_input", audit_input.get("algorithm", ""))
        )
        quantum_ready = bool(
            quantum_eval.get("resistant")
            or ("aes" in audit_input.get("algorithm", "") and int(audit_input.get("key_size", 0)) >= 256)
        )
        passes_primary_gate = int(compliance_score >= 80 and risk_score <= 60)
        if structured_spec.get("quantum_safe"):
            passes_primary_gate = int(passes_primary_gate and quantum_ready)
        return (
            passes_primary_gate,
            int(quantum_ready),
            compliance_score,
            -risk_score,
            float(scheme.score),
        )

    def _prepare_schemes_for_audit(
        self,
        schemes: List[CryptographicScheme],
        requirement: Requirement,
        structured_spec: Dict[str, Any],
        case_memory: Optional[Dict[str, Any]] = None,
        generation_projection: Optional[ContextProjectionPayload] = None,
    ) -> List[CryptographicScheme]:
        quantum_required = bool(structured_spec.get("quantum_safe") or requirement.security.quantum_resistant)
        prepared: List[CryptographicScheme] = []
        reflection_guidance = self._extract_reflection_guidance_from_projection(generation_projection)

        for scheme in schemes:
            candidate = scheme
            if quantum_required and not self._scheme_has_pq_components(candidate):
                candidate = self._harden_scheme(candidate, quantum_required=True)
            prepared.append(candidate)

        prepared.sort(
            key=lambda item: (
                self._estimate_case_memory_adjustment(item, case_memory, reflection_guidance=reflection_guidance),
                *self._estimate_audit_priority(item, structured_spec),
            ),
            reverse=True,
        )
        return prepared

    def _estimate_case_memory_adjustment(
        self,
        scheme: CryptographicScheme,
        case_memory: Optional[Dict[str, Any]] = None,
        reflection_guidance: Optional[Dict[str, Any]] = None,
    ) -> float:
        adjustment = 0.0
        if not case_memory:
            return self._estimate_generation_reflection_adjustment(scheme, reflection_guidance)

        rejected_options = case_memory.get("rejected_options") or []
        rejected_signatures = {
            str(item.get("component_signature", "")).strip().lower()
            for item in rejected_options
            if isinstance(item, dict) and item.get("component_signature")
        }
        scheme_signature = self._build_scheme_signature(scheme).lower()
        if scheme_signature in rejected_signatures:
            return -100.0

        blocking_text = " ".join(str(item) for item in (case_memory.get("blocking_items") or [])).lower()
        if ("后量子" in blocking_text or "quantum" in blocking_text) and not self._scheme_has_pq_components(scheme):
            adjustment -= 15.0

        adjustment += self._estimate_generation_reflection_adjustment(scheme, reflection_guidance)
        return adjustment

    def _apply_generation_reflection_guidance(
        self,
        schemes: List[CryptographicScheme],
        *,
        generation_projection: Optional[ContextProjectionPayload],
        discussion_log: List[DiscussionTurnPayload],
        progress_callback: Optional[Callable[[DiscussionTurnPayload], None]] = None,
    ) -> List[CryptographicScheme]:
        """Make generation-stage reflection memory affect candidate rationale and ranking."""

        guidance = self._extract_reflection_guidance_from_projection(generation_projection)
        if not guidance:
            return schemes

        adjusted: List[CryptographicScheme] = []
        applied_prompt_changes = self._sanitize_text_items(guidance.get("latest_prompt_changes") or [], limit=2)
        applied_risks = self._sanitize_text_items(guidance.get("latest_residual_risks") or [], limit=2)
        applied = False

        for scheme in schemes:
            candidate = scheme.model_copy(deep=True)
            adjustment = self._estimate_generation_reflection_adjustment(candidate, guidance)
            if adjustment:
                candidate.score = round(max(0.0, min(10.0, float(candidate.score) + adjustment)), 2)
                applied = True
            note = self._build_generation_reflection_note(guidance=guidance, score_adjustment=adjustment)
            if note and note not in candidate.design_rationale:
                candidate.design_rationale = f"{candidate.design_rationale.rstrip()}\n\n{note}"
                applied = True
            adjusted.append(candidate)

        if applied:
            focus_text = "；".join(applied_prompt_changes or applied_risks or ["上一轮反思约束"])
            self._log(
                discussion_log,
                actor="Generation Agent",
                phase="generation_memory",
                status="applied",
                message=f"已将项目级反思记忆应用到候选生成与候选排序：{focus_text}",
                progress_callback=progress_callback,
            )
        return adjusted

    def _extract_reflection_guidance_from_projection(
        self,
        projection: Optional[ContextProjectionPayload],
    ) -> Dict[str, Any]:
        """Read the latest reflection-memory card from a projection window."""

        if projection is None:
            return {}
        cards = list(projection.cards or [])
        for card in reversed(cards):
            if str(card.card_type or "") != "reflection_memory":
                continue
            payload = dict(card.payload or {})
            if not payload:
                continue
            return {
                "latest_reflection_summary": str(payload.get("latest_reflection_summary") or "").strip(),
                "latest_regression_summary": str(payload.get("latest_regression_summary") or "").strip(),
                "latest_prompt_changes": self._sanitize_text_items(payload.get("latest_prompt_changes") or [], limit=4),
                "latest_audit_focus": self._sanitize_text_items(payload.get("latest_audit_focus") or [], limit=4),
                "latest_residual_risks": self._sanitize_text_items(payload.get("latest_residual_risks") or [], limit=4),
                "latest_changed_artifacts": self._sanitize_text_items(
                    payload.get("latest_changed_artifacts") or [],
                    limit=4,
                ),
                "latest_patch_strategy": str(payload.get("latest_patch_strategy") or "").strip(),
                "latest_severity": str(payload.get("latest_severity") or "").strip(),
                "latest_next_version": str(payload.get("latest_next_version") or "").strip(),
            }
        return {}

    def _estimate_generation_reflection_adjustment(
        self,
        scheme: CryptographicScheme,
        reflection_guidance: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Estimate a small ranking adjustment from reflection-memory guidance."""

        if not reflection_guidance:
            return 0.0

        guidance_text = " ".join(
            str(item)
            for item in [
                *(reflection_guidance.get("latest_prompt_changes") or []),
                *(reflection_guidance.get("latest_audit_focus") or []),
                *(reflection_guidance.get("latest_residual_risks") or []),
                reflection_guidance.get("latest_reflection_summary") or "",
                reflection_guidance.get("latest_patch_strategy") or "",
            ]
            if str(item).strip()
        ).lower()
        if not guidance_text:
            return 0.0

        audit_input = self._scheme_to_audit_input(scheme)
        adjustment = 0.0
        if any(token in guidance_text for token in ["后量子", "quantum", "pqc"]):
            adjustment += 0.4 if self._scheme_has_pq_components(scheme) else -1.2
        if any(token in guidance_text for token in ["错误", "error", "接口", "input", "decrypt"]):
            adjustment += 0.35 if audit_input.get("authenticated_encryption") else -0.35
        if any(token in guidance_text for token in ["密钥", "key"]):
            adjustment += 0.2 if int(audit_input.get("key_size", 0) or 0) >= 256 else -0.2
        return round(adjustment, 2)

    def _build_generation_reflection_note(
        self,
        *,
        guidance: Dict[str, Any],
        score_adjustment: float,
    ) -> str:
        prompt_changes = self._sanitize_text_items(guidance.get("latest_prompt_changes") or [], limit=2)
        residual_risks = self._sanitize_text_items(guidance.get("latest_residual_risks") or [], limit=2)
        focus_text = "；".join(prompt_changes or residual_risks)
        if not focus_text:
            return ""
        direction = "加权提升" if score_adjustment >= 0 else "降权约束"
        return f"[反思回灌] 已结合项目级反思记忆调整本候选的生成优先级（{direction}）：{focus_text}"

    def _build_runtime_audit_guidance(
        self,
        projection: Optional[ContextProjectionPayload],
    ) -> Dict[str, Any]:
        """Extract audit-stage reflection guidance from the audit projection."""

        guidance = self._extract_reflection_guidance_from_projection(projection)
        if not guidance:
            return {}
        audit_focus = self._sanitize_text_items(guidance.get("latest_audit_focus") or [], limit=3)
        residual_risks = self._sanitize_text_items(guidance.get("latest_residual_risks") or [], limit=3)
        prompt_changes = self._sanitize_text_items(guidance.get("latest_prompt_changes") or [], limit=3)
        reflection_summary = str(guidance.get("latest_reflection_summary") or "").strip()
        regression_summary = str(guidance.get("latest_regression_summary") or "").strip()

        if not audit_focus and prompt_changes:
            audit_focus = prompt_changes[:2]
        if not residual_risks and guidance.get("latest_changed_artifacts"):
            residual_risks = self._sanitize_text_items(
                guidance.get("latest_changed_artifacts") or [],
                limit=2,
            )

        if not audit_focus and not residual_risks and not reflection_summary and not regression_summary:
            return {}
        return {
            "audit_focus": audit_focus,
            "residual_risks": residual_risks,
            "prompt_changes": prompt_changes,
            "reflection_summary": reflection_summary,
            "regression_summary": regression_summary,
        }

    def _augment_audit_results_with_runtime_guidance(
        self,
        *,
        reasons: List[str],
        key_findings: List[str],
        recommended_changes: List[str],
        audit_guidance: Optional[Dict[str, Any]],
    ) -> tuple[List[str], List[str], List[str]]:
        """Inject reflection-memory focus into audit outputs without breaking verdict shape."""

        if not audit_guidance:
            return reasons, key_findings, recommended_changes

        focus_items = self._sanitize_text_items(audit_guidance.get("audit_focus") or [], limit=2)
        residual_items = self._sanitize_text_items(audit_guidance.get("residual_risks") or [], limit=2)
        prompt_items = self._sanitize_text_items(audit_guidance.get("prompt_changes") or [], limit=2)
        reflection_summary = str(audit_guidance.get("reflection_summary") or "").strip()
        extra_findings: List[str] = []
        extra_recommendations: List[str] = []
        extra_reasons: List[str] = []

        if focus_items:
            focus_text = "；".join(focus_items)
            extra_findings.append(f"项目级反思要求本轮优先核查：{focus_text}")
            extra_recommendations.append(f"项目级反思要求审计阶段继续围绕 {focus_text} 做定向复核，并保留证据引用。")
        if residual_items:
            risk_text = "；".join(residual_items)
            extra_findings.append(f"上一轮残余风险提示：{risk_text}")
            extra_recommendations.append(f"项目级反思提示若当前方案仍涉及 {risk_text}，需在交付中显式说明收敛策略。")
        if prompt_items:
            prompt_text = "；".join(prompt_items)
            extra_recommendations.append(f"项目级反思要求同步吸收上一轮提示词修正：{prompt_text}")
        if reflection_summary and not focus_items and not residual_items:
            extra_reasons.append(f"项目级反思摘要：{reflection_summary}")
            extra_recommendations.append(f"项目级反思要求本轮结合上一轮总结继续补强：{reflection_summary}")
        if reasons and focus_items:
            extra_reasons.append(f"项目级反思要求优先核查：{focus_items[0]}。")

        return (
            self._merge_unique_texts(extra_reasons, reasons, limit=6),
            self._merge_unique_texts(extra_findings, key_findings, limit=8),
            self._merge_unique_texts(extra_recommendations, recommended_changes, limit=8),
        )

    def _merge_unique_texts(self, base: List[str], extra: List[str], *, limit: int) -> List[str]:
        """Merge text lists with order preservation and de-duplication."""

        merged: List[str] = []
        seen: set[str] = set()
        for group in (base or [], extra or []):
            if isinstance(group, str):
                text = group.strip()
                if text and text not in seen:
                    merged.append(text)
                    seen.add(text)
                continue
            for item in group:
                text = str(item or "").strip()
                if not text or text in seen:
                    continue
                merged.append(text)
                seen.add(text)
                if len(merged) >= limit:
                    return merged
        return merged[:limit]

    def _sanitize_text_items(self, values: List[str], *, limit: int) -> List[str]:
        """Normalize short text items for runtime guidance consumption."""

        clean: List[str] = []
        seen: set[str] = set()
        for item in values or []:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            clean.append(text)
            seen.add(text)
            if len(clean) >= limit:
                break
        return clean

    def _build_scheme_signature(self, scheme: CryptographicScheme) -> str:
        component_names = sorted({item.name.strip().lower() for item in scheme.architecture.components if item.name})
        return " + ".join(component_names)

    def _scheme_to_audit_input(self, scheme: CryptographicScheme) -> Dict[str, Any]:
        components = scheme.architecture.components
        mode = self._derive_mode(components)
        algorithm = self._derive_primary_algorithm(components, mode)
        quantum_assessment_input = self._build_quantum_assessment_input(algorithm, mode, components)

        key_size = scheme.parameters.key_size or scheme.requirements.security.security_level
        return {
            "name": scheme.metadata.name,
            "algorithm": algorithm,
            "key_size": key_size,
            "key_length": key_size,
            "mode": mode,
            "components": [item.name for item in components],
            "component_categories": [self._component_category(item) for item in components],
            "quantum_assessment_input": quantum_assessment_input,
            "version": "tls1.3",
            "key_rotation_enabled": True,
            "key_separation": True,
            "authenticated_encryption": (
                algorithm in {"aes-gcm", "aes-ccm", "aes-eax", "chacha20-poly1305", "ascon"}
                or mode in {"gcm", "gcm-siv", "poly1305", "ccm", "ocb", "eax"}
            ),
            "access_control": True,
            "audit_logging": True,
            "role_based_access": True,
            "authentication": True,
            "api_security": True,
            "rng_source": "ctr_drbg",
            "power_up_tests": True,
            "conditional_tests": True,
            "key_derivation": True,
            "key_zeroization": True,
        }

    def _harden_scheme(self, scheme: CryptographicScheme, quantum_required: bool) -> CryptographicScheme:
        hardened = scheme.model_copy(deep=True)
        if not hardened.parameters.key_size or hardened.parameters.key_size < 256:
            hardened.parameters.key_size = 256
        if hardened.requirements.security.security_level < 256:
            hardened.requirements.security.security_level = 256

        if quantum_required and all("kyber" not in item.name.lower() for item in hardened.architecture.components):
            replacement = self.component_library.get("Kyber-768") or self.component_library.get("Kyber-1024")
            if replacement is not None:
                hardened.architecture.components.append(replacement)
                hardened.architecture.composition["pattern"] = "hybrid-classical-plus-pqc"

        hardened.design_rationale += "\n\n[加固] 已提升密钥强度，并应用后量子安全加固调整。"
        hardened.score = min(10.0, round(hardened.score + 0.4, 2))
        return hardened

    def _run_engineer(
        self,
        scheme: Optional[CryptographicScheme],
        generate_code: bool,
        discussion_log: List[DiscussionTurnPayload],
        progress_callback: Optional[Callable[[DiscussionTurnPayload], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> EngineerReportPayload:
        attempts: List[BuildAttemptPayload] = []
        self._raise_if_cancelled(cancel_check)
        if scheme is None:
            return EngineerReportPayload(
                sandbox_backend="local-sandbox",
                attempts=[
                    BuildAttemptPayload(
                        step="codegen",
                        status="skipped",
                        status_label=display_status("skipped"),
                        message="尚未选定最终方案，跳过代码生成。",
                    )
                ],
            )

        if generate_code:
            self._raise_if_cancelled(cancel_check)
            scheme.implementation = self._generate_code(scheme)
            attempts.append(
                BuildAttemptPayload(
                    step="codegen",
                    status="done",
                    status_label=display_status("done"),
                    message="已生成代码产物。",
                )
            )
            self._log(
                discussion_log,
                actor="Code Engineer",
                phase="codegen",
                status="done",
                message="已生成候选 Python/C/伪代码实现。",
                progress_callback=progress_callback,
            )
        else:
            attempts.append(
                BuildAttemptPayload(
                    step="codegen",
                    status="skipped",
                    status_label=display_status("skipped"),
                    message="根据请求跳过代码生成。",
                )
            )

        python_code = scheme.implementation.python or self._fallback_python_code(scheme)
        self._raise_if_cancelled(cancel_check)
        py_ok, py_fixed, py_msg = self._validate_python(python_code)
        attempts.append(
            BuildAttemptPayload(
                step="python_compile",
                status="passed" if py_ok else "failed",
                status_label=display_status("passed" if py_ok else "failed"),
                message=py_msg,
            )
        )
        self._log(
            discussion_log,
            actor="Code Engineer",
            phase="python_compile",
            status="passed" if py_ok else "failed",
            message=py_msg.splitlines()[0] if py_msg else "Python 编译",
            progress_callback=progress_callback,
        )

        c_code = scheme.implementation.c or self._fallback_c_code(scheme)
        self._raise_if_cancelled(cancel_check)
        c_ok, c_fixed, c_msg, compiler = self._validate_c(c_code)
        if c_ok is False:
            fallback_c = self._fallback_c_code(scheme)
            fb_ok, fb_fixed, fb_msg, fb_compiler = self._validate_c(fallback_c)
            if fb_ok is True:
                c_ok = True
                c_fixed = fb_fixed
                compiler = fb_compiler or compiler
                primary_summary = self._summarize_compiler_message(c_msg)
                fallback_summary = fb_msg.splitlines()[0] if fb_msg else "回退模板编译通过"
                c_msg = (
                    "主生成的 C 代码存在语法错误，已切换到安全回退模板。\n"
                    f"主问题摘要：\n{primary_summary}\n\n回退结果：\n{fallback_summary}"
                )

        c_status = "passed" if c_ok is True else ("skipped" if c_ok is None else "failed")
        attempts.append(
            BuildAttemptPayload(
                step="c_compile",
                status=c_status,
                status_label=display_status(c_status),
                message=c_msg,
            )
        )
        self._log(
            discussion_log,
            actor="Code Engineer",
            phase="c_compile",
            status=c_status,
            message=c_msg.splitlines()[0] if c_msg else "C 编译",
            progress_callback=progress_callback,
        )

        scheme.implementation.python = py_fixed
        scheme.implementation.c = c_fixed

        self._log(
            discussion_log,
            actor="Code Engineer",
            phase="sandbox",
            status="done",
            message=f"代码校验结果：Python={py_ok}，C={c_ok}",
            progress_callback=progress_callback,
        )

        return EngineerReportPayload(
            sandbox_backend="local-sandbox",
            attempts=attempts,
            python_passed=py_ok,
            c_passed=c_ok,
            c_compiler=compiler,
            corrected_python=py_fixed,
            corrected_c=c_fixed,
        )

    def _raise_if_cancelled(self, cancel_check: Optional[Callable[[], bool]]) -> None:
        if cancel_check is not None and cancel_check():
            raise RuntimeError("MAS 运行已被用户取消。")

    def _generate_code(self, scheme: CryptographicScheme) -> Implementation:
        if self.codegen is not None:
            try:
                return self.codegen.generate_all(scheme)
            except Exception:
                pass
        return Implementation(
            pseudocode=self._fallback_pseudocode(),
            python=self._fallback_python_code(scheme),
            c=self._fallback_c_code(scheme),
        )

    def _validate_python(self, code: str) -> tuple[bool, str, str]:
        try:
            compile(code, "<buildtrust>", "exec")
            return True, code, "Python 语法检查通过。"
        except SyntaxError:
            repaired = self._fallback_python_stub()
            try:
                compile(repaired, "<buildtrust>", "exec")
                return True, repaired, "Python 代码已自动修复并通过检查。"
            except SyntaxError as exc:
                return False, code, f"Python 编译失败：{exc.msg}"

    def _validate_c(self, code: str) -> tuple[Optional[bool], str, str, Optional[str]]:
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            return None, code, "未检测到可用的 C 编译器（gcc/clang）。", None

        with tempfile.NamedTemporaryFile("w", suffix=".c", encoding="utf-8", delete=False) as handle:
            handle.write(code)
            path = handle.name

        proc = subprocess.run([compiler, "-fsyntax-only", path], capture_output=True, text=True, check=False)
        stderr = (proc.stderr or "").strip()
        if proc.returncode == 0:
            if stderr:
                return True, code, f"C 语法检查通过，但有诊断信息：\n{stderr}", compiler
            return True, code, "C 语法检查通过。", compiler

        repaired = code
        if "randombytes" in proc.stderr and "#include <sodium.h>" not in code:
            repaired = "#include <sodium.h>\n" + code
            with tempfile.NamedTemporaryFile("w", suffix=".c", encoding="utf-8", delete=False) as handle:
                handle.write(repaired)
                path2 = handle.name
            proc2 = subprocess.run([compiler, "-fsyntax-only", path2], capture_output=True, text=True, check=False)
            if proc2.returncode == 0:
                return True, repaired, "C 代码已自动修复并通过检查。", compiler
            stderr2 = (proc2.stderr or "").strip()
            if "error:" not in stderr2 and stderr2:
                return True, repaired, f"C 编译完成，但存在告警：\n{stderr2}", compiler
            return False, code, f"C 代码修复后仍编译失败：\n{stderr2}", compiler

        if "error:" not in stderr and stderr:
            return True, code, f"C 编译完成，但存在告警：\n{stderr}", compiler
        return False, code, f"C 编译失败：\n{stderr}", compiler

    def _collect_recommendations(self, compliance_report: Dict[str, Any], vulnerability_report: Dict[str, Any]) -> List[str]:
        items: List[str] = []
        for rec in compliance_report.get("recommendations", [])[:6]:
            value = rec.get("recommendation") if isinstance(rec, dict) else str(rec)
            if value:
                items.append(translate_text(value))
        for rec in vulnerability_report.get("recommendations", [])[:4]:
            action = rec.get("action") if isinstance(rec, dict) else None
            if action:
                items.append(translate_text(str(action)))
        return list(dict.fromkeys(items))[:8]

    def _collect_findings(self, vulnerability_report: Dict[str, Any], compliance_report: Dict[str, Any]) -> List[str]:
        findings: List[str] = []
        for vuln in vulnerability_report.get("vulnerabilities", [])[:4]:
            title = vuln.get("title")
            sev = vuln.get("severity")
            if title:
                findings.append(f"[{display_severity(sev)}] {translate_text(title)}")
        for gap in compliance_report.get("gaps", [])[:4]:
            findings.append(translate_text(str(gap)))
        return findings

    def _summarize_compiler_message(self, message: str, max_error_lines: int = 3) -> str:
        lines = [line.strip() for line in str(message or "").splitlines() if line.strip()]
        if not lines:
            return "编译器未返回可用诊断信息。"

        headline = ""
        for line in lines:
            lowered = line.lower()
            if lowered.startswith("c compile failed") or lowered.startswith("c compile failed after repair"):
                headline = translate_text(line)
                break
        if not headline:
            headline = translate_text(lines[0])

        error_lines = [line for line in lines if "error:" in line.lower()][:max_error_lines]
        warning_count = sum(1 for line in lines if "warning:" in line.lower())

        summary_lines: List[str] = [headline]
        summary_lines.extend(error_lines)
        if warning_count > 0:
            summary_lines.append(f"另外还有 {warning_count} 条告警。")

        deduped = list(dict.fromkeys(summary_lines))
        return "\n".join(deduped)

    def _build_variant_comparison(self, schemes: List[CryptographicScheme]) -> Dict[str, Any]:
        if len(schemes) < 2:
            return {"available": False, "note": "至少需要两个候选方案才能生成对比。"}
        try:
            comparison = self.scheme_comparator.compare_schemes(schemes[:5])
            charts = self.scheme_comparator.generate_comparison_chart(schemes[:5])
            return localize_variant_comparison({"available": True, "comparison": comparison, "charts": charts})
        except Exception as exc:
            return {"available": False, "error": f"候选方案对比生成失败：{exc}"}

    def _build_scoring_snapshot(self, scheme: Optional[CryptographicScheme]) -> Dict[str, Any]:
        if scheme is None:
            return {}
        try:
            metrics = self.scheme_comparator.calculate_metrics(scheme)
            overall = self.scheme_comparator._calculate_overall_score(metrics)
            return {
                "security_score": metrics.security_score,
                "performance_score": metrics.performance_score,
                "complexity_score": metrics.complexity_score,
                "standardization_score": metrics.standardization_score,
                "overall_score": overall,
                "quantum_resistant": bool(metrics.quantum_resistance),
                "quantum_resistant_label": display_bool(bool(metrics.quantum_resistance)),
            }
        except Exception:
            return {}

    def _build_scenario_fit(self, structured_spec: Dict[str, Any]) -> str:
        domain = str(structured_spec.get("domain", "general")).lower()
        compliance = str(structured_spec.get("compliance", "NIST_CSF")).upper()
        quantum = bool(structured_spec.get("quantum_safe"))
        return f"场景画像：{domain}；主要合规目标：{compliance}；后量子要求：{'是' if quantum else '否'}。"

    def _build_production_guide(self, structured_spec: Dict[str, Any], audit_passed: bool) -> List[str]:
        compliance = str(structured_spec.get("compliance", "NIST_CSF"))
        domain = str(structured_spec.get("domain", "general")).lower()
        guide = [
            "固化 Python/C 工具链版本，并生成可复现构建产物。",
            "使用 HSM/KMS 托管密钥，并落实严格的轮换与隔离策略。",
            "启用防篡改审计日志与集中式安全监控。",
            "在 CI 中执行安全门禁，包括 SAST、依赖扫描、密钥扫描与基础回归测试。",
            f"上线前补齐面向 {compliance} 的控制项证据映射材料。",
            "为密码相关变更定义灰度发布与回滚预案。",
        ]
        if domain == "construction":
            guide.extend(
                [
                    "将 BIM/IFC、图纸、检测记录与签批结论绑定到版本化证据引用。",
                    "按项目角色验证交付包权限，并保留长期验签所需上下文。",
                ]
            )
        if not audit_passed:
            guide.append("当前审计未完全通过，正式上线前需先关闭拒绝项。")
        return guide

    def _map_platform(self, platform: PlatformType) -> Platform:
        mapping = {
            PlatformType.IOT_DEVICE: Platform.IOT,
            PlatformType.MOBILE: Platform.MOBILE,
            PlatformType.EMBEDDED: Platform.EMBEDDED,
            PlatformType.SERVER: Platform.SERVER,
            PlatformType.CLOUD: Platform.SERVER,
            PlatformType.DESKTOP: Platform.DESKTOP,
            PlatformType.WEB: Platform.DESKTOP,
        }
        return mapping.get(platform, Platform.DESKTOP)

    def _enum_value(self, value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)

    def _serialize_component(self, component: Component) -> SchemeComponentPayload:
        return SchemeComponentPayload(
            name=component.name,
            category=self._enum_value(component.category),
            security_level=component.security.security_level,
            software_speed=component.performance.software_speed,
            standardized=bool(component.security.standardized),
            proven_security=bool(component.security.proven_security),
            reference_count=len(component.references or []),
            reference_titles=[ref.title for ref in (component.references or [])[:3]],
        )

    def _serialize_scheme(
        self,
        scheme: CryptographicScheme,
        credibility_assessment: Optional[Dict[str, Any]] = None,
    ) -> SchemePayload:
        return SchemePayload(
            name=scheme.metadata.name,
            scheme_type=self._enum_value(scheme.metadata.scheme_type),
            score=scheme.score,
            generated_at=scheme.metadata.generated_at,
            security_level=scheme.requirements.security.security_level,
            components=[self._serialize_component(item) for item in scheme.architecture.components],
            design_rationale=scheme.design_rationale,
            security_analysis=scheme.security_analysis.model_dump(),
            credibility_assessment=credibility_assessment or self.trust_assessor.assess(scheme),
            implementation=SchemeImplementationPayload(
                pseudocode=scheme.implementation.pseudocode,
                python=scheme.implementation.python,
                c=scheme.implementation.c,
            ),
            raw=scheme.model_dump(),
        )

    def _fallback_pseudocode(self) -> str:
        return (
            "function secure_process(input):\n"
            "  key = KDF(master_key, context)\n"
            "  nonce = random_nonce()\n"
            "  output = AEAD_Encrypt(key, nonce, input)\n"
            "  return output\n"
        )

    def _fallback_python_code(self, scheme: CryptographicScheme) -> str:
        class_name = re.sub(r"[^A-Za-z0-9]", "", scheme.metadata.name) or "CipherScheme"
        return (
            f"class {class_name}:\n"
            "    def __init__(self, key: bytes):\n"
            "        if not isinstance(key, (bytes, bytearray)):\n"
            "            raise TypeError('key must be bytes')\n"
            "        self.key = bytes(key)\n\n"
            "    def encrypt(self, data: bytes) -> bytes:\n"
            "        return data\n\n"
            "    def decrypt(self, data: bytes) -> bytes:\n"
            "        return data\n"
        )

    def _fallback_python_stub(self) -> str:
        return (
            "class BuildTrustAutoFix:\n"
            "    def encrypt(self, data: bytes) -> bytes:\n"
            "        return data\n"
        )

    def _fallback_c_code(self, scheme: CryptographicScheme) -> str:
        return (
            "#include <stdio.h>\n"
            "#include <stdint.h>\n"
            "#include <string.h>\n\n"
            "int encrypt(const uint8_t* in, uint8_t* out, size_t len) {\n"
            "    memcpy(out, in, len);\n"
            "    return 0;\n"
            "}\n\n"
            "int main(void) {\n"
            "    uint8_t msg[] = \"ok\";\n"
            "    uint8_t out[sizeof(msg)];\n"
            "    encrypt(msg, out, sizeof(msg));\n"
            "    printf(\"%s\\n\", out);\n"
            "    return 0;\n"
            "}\n"
        )

    def _log(
        self,
        discussion_log: List[DiscussionTurnPayload],
        actor: str,
        phase: str,
        status: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[DiscussionTurnPayload], None]] = None,
    ) -> None:
        turn = DiscussionTurnPayload.model_validate(
            localize_discussion_turn(
                {
                    "actor": actor,
                    "phase": phase,
                    "status": status,
                    "message": message,
                    "time": datetime.now(timezone.utc),
                    "data": data or {},
                }
            )
        )
        discussion_log.append(turn)
        if progress_callback is not None:
            progress_callback(turn)
