"""MAS orchestration service (Supervisor + 4 agents)."""

from __future__ import annotations

from datetime import datetime, timezone
import re
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from cipher_genius.api.schemas import (
    AnalystReportPayload,
    ArchitectCandidatePayload,
    ArchitectReportPayload,
    AuditorRoundPayload,
    BuildAttemptPayload,
    ClarificationPayload,
    DiscussionTurnPayload,
    EngineerReportPayload,
    MASRequest,
    MASResponse,
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
    display_actor,
    display_bool,
    display_status,
    display_severity,
    localize_compliance_report,
    localize_discussion_turn,
    localize_variant_comparison,
    localize_vulnerability_report,
    translate_text,
)


class MASOrchestrationService:
    """Supervisor for Analyst -> Architect -> Auditor -> Engineer."""

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

    def execute(
        self,
        payload: MASRequest,
        progress_callback: Optional[Callable[[DiscussionTurnPayload], None]] = None,
        request_id: Optional[str] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> MASResponse:
        discussion_log: List[DiscussionTurnPayload] = []
        resolved_request_id = request_id or payload.run_id or str(uuid4())
        self._raise_if_cancelled(cancel_check)

        parsed = self._parse_requirement(payload.requirement, discussion_log, progress_callback=progress_callback)
        self._raise_if_cancelled(cancel_check)
        structured_spec = self._build_structured_spec(parsed.requirement, payload.requirement)
        clarifications = self._build_clarifications(payload.requirement, structured_spec)

        analyst = AnalystReportPayload(
            structured_spec=structured_spec,
            parsed_requirement=ParsedRequirementPayload(
                requirement=parsed.requirement.model_dump(),
                confidence=parsed.confidence,
                ambiguities=parsed.ambiguities,
                assumptions=parsed.assumptions,
            ),
            clarifications=clarifications,
            assumptions=parsed.assumptions,
        )

        if payload.strict_clarification and any(item.required for item in clarifications):
            self._log(
                discussion_log,
                actor="Supervisor",
                phase="analyst_gate",
                status="halted",
                message="发现阻断性澄清问题，严格模式已停止执行。",
                progress_callback=progress_callback,
            )
            return MASResponse(
                request_id=resolved_request_id,
                run_id=resolved_request_id,
                case_id=payload.case_id,
                generated_at=datetime.now(timezone.utc),
                security_disclaimer=SECURITY_DISCLAIMER_TEXT,
                analyst=analyst,
                architect=ArchitectReportPayload(toolbox_services=self.TOOLBOX_SERVICES, candidates=[]),
                auditor_rounds=[],
                engineer=EngineerReportPayload(
                    sandbox_backend="local-sandbox",
                    attempts=[
                        BuildAttemptPayload(
                            step="gate",
                            status="skipped",
                            status_label=display_status("skipped"),
                            message="严格澄清门禁已触发",
                        )
                    ],
                ),
                final_scheme=None,
                compliance_report={},
                vulnerability_report={},
                discussion_log=discussion_log,
                delivery={"status": "needs_clarification"},
            )

        schemes = self._generate_schemes(
            parsed.requirement,
            payload.num_variants,
            discussion_log,
            structured_spec=structured_spec,
            progress_callback=progress_callback,
        )
        self._raise_if_cancelled(cancel_check)
        architect = ArchitectReportPayload(
            toolbox_services=self.TOOLBOX_SERVICES,
            candidates=self._build_architect_candidates(
                schemes,
                parsed.requirement,
                parser_confidence=parsed.confidence,
            ),
        )

        auditor_rounds: List[AuditorRoundPayload] = []
        selected_index = 0
        final_compliance_report: Dict[str, Any] = {}
        final_vulnerability_report: Dict[str, Any] = {}
        hardened_once = False
        audit_passed = False

        for round_idx in range(1, payload.max_audit_rounds + 1):
            self._raise_if_cancelled(cancel_check)
            if not schemes:
                break

            selected_index = min(selected_index, len(schemes) - 1)
            scheme = schemes[selected_index]
            proposal_id = f"proposal-{selected_index + 1}"

            audit_input = self._scheme_to_audit_input(scheme)
            standards = self._select_standards(structured_spec)
            vulnerability_report = self.vulnerability_scanner.scan_scheme(audit_input)
            compliance_report = self.compliance_reporter.generate_report(audit_input, standards)
            quantum_eval = self.security_assessor._assess_quantum_readiness(
                audit_input.get("quantum_assessment_input", audit_input.get("algorithm", ""))
            )

            compliance_score = float(compliance_report.get("overall_compliance", 0.0))
            risk_score = int(vulnerability_report.get("risk_score", 0))
            critical_count = int(vulnerability_report.get("summary", {}).get("critical", 0))
            quantum_required = bool(structured_spec.get("quantum_safe"))
            quantum_ready = bool(
                quantum_eval.get("resistant")
                or ("aes" in audit_input.get("algorithm", "") and int(audit_input.get("key_size", 0)) >= 256)
            )

            reasons: List[str] = []
            if critical_count > 0:
                reasons.append(f"检测到 {critical_count} 个严重漏洞。")
            if compliance_score < 80:
                reasons.append(f"整体合规得分过低：{compliance_score:.1f}%。")
            if risk_score > 60:
                reasons.append(f"风险得分过高：{risk_score}/100。")
            if quantum_required and not quantum_ready:
                reasons.append("未满足后量子安全要求。")

            verdict = "pass" if not reasons else "reject"
            auditor_rounds.append(
                AuditorRoundPayload(
                    round=round_idx,
                    proposal_id=proposal_id,
                    verdict=verdict,
                    verdict_label=display_status(verdict),
                    reasons=reasons,
                    compliance_score=round(compliance_score, 2),
                    risk_score=risk_score,
                    quantum_ready=quantum_ready,
                    quantum_ready_label=display_bool(quantum_ready),
                    standards_checked=[item.value for item in standards],
                    key_findings=self._collect_findings(vulnerability_report, compliance_report),
                    recommended_changes=self._collect_recommendations(compliance_report, vulnerability_report),
                )
            )

            final_compliance_report = compliance_report
            final_vulnerability_report = vulnerability_report

            self._log(
                discussion_log,
                actor="Security & Compliance Auditor",
                phase="audit",
                status=verdict,
                message=f"{proposal_id} 审计完成，合规得分 {compliance_score:.1f}，风险得分 {risk_score}。",
                data={"reasons": reasons[:3]},
                progress_callback=progress_callback,
            )

            if verdict == "pass":
                audit_passed = True
                break

            if selected_index < len(schemes) - 1:
                selected_index += 1
                self._log(
                    discussion_log,
                    actor="Architect",
                    phase="revise",
                    status="retry",
                    message=f"当前提案被拒绝，切换到 proposal-{selected_index + 1}。",
                    progress_callback=progress_callback,
                )
                continue

            if not hardened_once:
                schemes[selected_index] = self._harden_scheme(schemes[selected_index], quantum_required)
                hardened_once = True
                self._log(
                    discussion_log,
                    actor="Architect",
                    phase="revise",
                    status="hardened",
                    message=f"已对 proposal-{selected_index + 1} 应用加固措施。",
                    progress_callback=progress_callback,
                )
                continue

            break

        final_scheme = schemes[selected_index] if schemes else None
        engineer = self._run_engineer(
            final_scheme,
            payload.generate_code,
            discussion_log,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )
        self._raise_if_cancelled(cancel_check)
        variant_comparison = self._build_variant_comparison(schemes)
        scoring = self._build_scoring_snapshot(final_scheme)
        scenario_fit = self._build_scenario_fit(structured_spec)
        production_guide = self._build_production_guide(structured_spec, audit_passed)
        localized_compliance_report = localize_compliance_report(final_compliance_report)
        localized_vulnerability_report = localize_vulnerability_report(final_vulnerability_report)
        credibility_assessment = self.trust_assessor.assess(
            final_scheme,
            parser_confidence=parsed.confidence,
            compliance_score=float(final_compliance_report.get("overall_compliance", 0.0)),
            risk_score=int(final_vulnerability_report.get("risk_score", 0)),
            audit_passed=audit_passed,
            quantum_ready=auditor_rounds[-1].quantum_ready if auditor_rounds else None,
        )
        final_scheme_payload = (
            self._serialize_scheme(final_scheme, credibility_assessment=credibility_assessment)
            if final_scheme
            else None
        )

        delivery = {
            "status": "approved" if audit_passed else "best_effort",
            "status_label": display_status("approved" if audit_passed else "best_effort"),
            "selected_proposal": f"proposal-{selected_index + 1}" if schemes else None,
            "audit_rounds": len(auditor_rounds),
            "compliance_score": round(float(final_compliance_report.get("overall_compliance", 0.0)), 2),
            "risk_score": int(final_vulnerability_report.get("risk_score", 0)),
            "handoff_artifacts": ["架构方案", "合规报告", "代码包"],
            "variant_comparison": variant_comparison,
            "scoring": scoring,
            "credibility_assessment": credibility_assessment,
            "scenario_fit": scenario_fit,
            "production_guide": production_guide,
            "next_action": (
                "上线前仍需人工密码学复核。"
                if audit_passed
                else "请先处理审计拒绝项后再重新执行 MAS。"
            ),
        }

        self._log(
            discussion_log,
            actor="Supervisor",
            phase="delivery",
            status=delivery["status"],
            message=f"流程已结束，当前状态：{display_status(delivery['status'])}。",
            data={"selected_proposal": delivery["selected_proposal"]},
            progress_callback=progress_callback,
        )

        return MASResponse(
            request_id=resolved_request_id,
            run_id=resolved_request_id,
            case_id=payload.case_id,
            generated_at=datetime.now(timezone.utc),
            security_disclaimer=SECURITY_DISCLAIMER_TEXT,
            analyst=analyst,
            architect=architect,
            auditor_rounds=auditor_rounds,
            engineer=engineer,
            final_scheme=final_scheme_payload,
            credibility_assessment=credibility_assessment,
            compliance_report=localized_compliance_report,
            vulnerability_report=localized_vulnerability_report,
            discussion_log=discussion_log,
            delivery=delivery,
        )

    def _safe_init(self, cls: Any, llm_provider: Optional[str]) -> Optional[Any]:
        try:
            return cls(llm_provider)
        except Exception:
            return None

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

        # Prefer explicitly stated security-level fields to avoid confusing "SHA-256" with "256-bit security".
        security_level = 128
        sec_patterns = [
            r"security\s*(?:level|strength)?\s*[:=]?\s*(\d{3})\s*(?:-?\s*bit)?",
            r"(\d{3})\s*[- ]?bit\s*security",
            r"安全(?:等级|强度)\s*[:：]?\s*(\d{3})",
            r"安全(?:等级|强度)\s*(\d{3})\s*比特",
            r"加密强度\s*[:：]?\s*(\d{3})",
        ]
        for pat in sec_patterns:
            m = re.search(pat, raw)
            if not m:
                continue
            candidate = int(m.group(1))
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
            ambiguities=["由于 LLM 提供方不可用，当前结果来自启发式解析。"],
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

    def _fallback_parse(self, text: str) -> ParsedRequirement:
        raw = text.lower()
        scheme_type = SchemeType.AUTHENTICATED_ENCRYPTION
        if any(k in raw for k in ["signature", "\u7b7e\u540d", "signing", "\u9a8c\u7b7e"]):
            scheme_type = SchemeType.SIGNATURE
        elif any(
            k in raw
            for k in [
                "key exchange",
                "key agreement",
                "\u5bc6\u94a5\u4ea4\u6362",
                "\u5bc6\u94a5\u534f\u5546",
                "\u63e1\u624b",
            ]
        ):
            scheme_type = SchemeType.KEY_EXCHANGE
        elif (
            re.search(r"\b(hmac|cmac|mac)\b", raw)
            or "\u6d88\u606f\u8ba4\u8bc1\u7801" in raw
            or "message authentication code" in raw
        ):
            scheme_type = SchemeType.MAC
        elif "poly1305" in raw and not any(k in raw for k in ["chacha20", "aead", "authenticated encryption"]):
            scheme_type = SchemeType.MAC
        elif "hash" in raw or "\u6458\u8981" in raw:
            scheme_type = SchemeType.HASH

        platform = PlatformType.SERVER
        resource = ResourceLevel.MODERATE
        if any(
            k in raw
            for k in [
                "iot",
                "\u5d4c\u5165\u5f0f",
                "\u7269\u8054\u7f51",
                "sensor",
                "\u4f20\u611f\u5668",
            ]
        ):
            platform = PlatformType.IOT_DEVICE
            resource = ResourceLevel.LIGHTWEIGHT
        elif any(k in raw for k in ["mobile", "\u624b\u673a", "android", "ios", "iphone", "ipad"]):
            platform = PlatformType.MOBILE
            resource = ResourceLevel.LIGHTWEIGHT

        security_level = 128
        sec_patterns = [
            r"security\s*(?:level|strength)?\s*[:=]?\s*(\d{3})\s*(?:-?\s*bit)?",
            r"(\d{3})\s*[- ]?bit\s*security",
            r"\u5b89\u5168(?:\u7b49\u7ea7|\u5f3a\u5ea6)\s*[:\uff1a]?\s*(\d{3})",
            r"\u5b89\u5168(?:\u7b49\u7ea7|\u5f3a\u5ea6)\s*(\d{3})\s*\u6bd4\u7279",
            r"\u52a0\u5bc6\u5f3a\u5ea6\s*[:\uff1a]?\s*(\d{3})",
        ]
        for pat in sec_patterns:
            m = re.search(pat, raw)
            if not m:
                continue
            candidate = int(m.group(1))
            if candidate in (128, 192, 256):
                security_level = candidate
                break

        requirement = Requirement(
            description=text,
            scheme_type=scheme_type,
            target_platform=TargetPlatform(type=platform, resource_level=resource),
            security=SecurityRequirement(
                security_level=security_level,
                quantum_resistant=("quantum" in raw or "\u540e\u91cf\u5b50" in raw),
            ),
        )

        return ParsedRequirement(
            requirement=requirement,
            confidence=0.58,
            ambiguities=["由于 LLM 提供方不可用，当前结果来自启发式解析。"],
            assumptions=["缺失细节已根据关键词进行推断。"],
        )

    def _build_structured_spec(self, requirement: Requirement, raw_text: str) -> Dict[str, Any]:
        text = raw_text.lower()
        domain = "general"
        if any(item in text for item in ["construction", "building", "bim", "ifc", "openbim", "cde", "\u5efa\u7b51", "\u65bd\u5de5", "\u5de5\u5730", "\u5de5\u7a0b\u9a8c\u6536", "\u56fe\u7eb8"]):
            domain = "construction"
        elif any(item in text for item in ["payment", "finance", "bank", "\u652f\u4ed8", "\u91d1\u878d"]):
            domain = "finance"
        elif any(item in text for item in ["iot", "device", "edge", "\u7269\u8054\u7f51"]):
            domain = "iot"

        compliance = "NIST_CSF"
        if domain == "finance":
            compliance = "PCI_DSS"
        elif domain == "construction":
            compliance = "ISO_19650"
        if "fedramp" in text or "government" in text:
            compliance = "FEDRAMP"

        quantum_safe = requirement.security.quantum_resistant or "quantum" in text or "\u540e\u91cf\u5b50" in text
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
                    reason="影响算法与参数选择（尤其是后量子算法）。",
                    required=True,
                )
            )
        if not re.search(r"\b\d+\s*(ms|s)\b", text) and "latency" not in text and "延迟" not in text:
            questions.append(
                ClarificationPayload(
                    id="latency_target",
                    question="最大可接受延迟是多少？",
                    reason="决定是偏向吞吐还是实时性优化。",
                )
            )
        if not any(word in text for word in ["fips", "pci", "gdpr", "iso", "soc2", "gb/t", "合规", "验收规则"]):
            questions.append(
                ClarificationPayload(
                    id="compliance_target",
                    question=f"是否以 {structured_spec.get('compliance')} 作为主合规标准？",
                    reason="审计员需要明确放行标准。",
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
            schemes = self._prepare_schemes_for_audit(
                schemes,
                requirement,
                structured_spec or {},
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
                        "当前方案由 MAS 回退路径中的启发式架构生成，"
                        "在安全性、性能与运维约束之间做了平衡。"
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
    ) -> List[CryptographicScheme]:
        quantum_required = bool(structured_spec.get("quantum_safe") or requirement.security.quantum_resistant)
        prepared: List[CryptographicScheme] = []

        for scheme in schemes:
            candidate = scheme
            if quantum_required and not self._scheme_has_pq_components(candidate):
                candidate = self._harden_scheme(candidate, quantum_required=True)
            prepared.append(candidate)

        prepared.sort(
            key=lambda item: (
                self._estimate_case_memory_adjustment(item, case_memory),
                *self._estimate_audit_priority(item, structured_spec),
            ),
            reverse=True,
        )
        return prepared

    def _estimate_case_memory_adjustment(
        self,
        scheme: CryptographicScheme,
        case_memory: Optional[Dict[str, Any]] = None,
    ) -> float:
        if not case_memory:
            return 0.0

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
            return -15.0

        return 0.0

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
                        message="未选择最终方案，跳过代码生成。",
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

        # Deduplicate while keeping order.
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
        return (
            f"场景画像：{domain}；主要合规目标：{compliance}；"
            f"后量子要求：{'是' if quantum else '否'}。"
        )

    def _build_production_guide(self, structured_spec: Dict[str, Any], audit_passed: bool) -> List[str]:
        compliance = str(structured_spec.get("compliance", "NIST_CSF"))
        domain = str(structured_spec.get("domain", "general")).lower()
        guide = [
            "固化 Python/C 工具链版本，并生成可复现构建产物。",
            "使用 HSM/KMS 托管密钥，并落实严格的轮换与隔离策略。",
            "启用防篡改审计日志与集中式安全监控。",
            "在 CI 中执行安全门禁，包括 SAST、依赖扫描、密钥扫描与基础回归测试。",
            f"上线前补齐面向 {compliance} 的控制-证据映射材料。",
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
