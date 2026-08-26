"""LLM-driven audit evaluation agent for proposal review rounds."""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cipher_genius.api.schemas import AuditorRoundPayload, ContextProjectionPayload
from cipher_genius.core.llm_interface import get_llm_interface
from cipher_genius.reporting import display_bool, display_status
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class _AuditStructuredOutput(BaseModel):
    """Strict structured verdict contract produced by the audit agent."""

    model_config = ConfigDict(extra="forbid")

    verdict: str = "reject"
    reasons: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    recommended_changes: list[str] = Field(default_factory=list)


class AuditEvaluationAgent:
    """Produce a stable audit verdict from an isolated projection window."""

    def __init__(self, llm_provider: Optional[str] = None, llm: Optional[Any] = None):
        self.llm_provider = llm_provider
        self.llm = llm
        if self.llm is None and llm_provider:
            try:
                self.llm = get_llm_interface(llm_provider)
            except Exception as exc:
                logger.warning("AuditEvaluationAgent LLM unavailable, fallback enabled: %s", exc)
                self.llm = None

    def evaluate(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
    ) -> AuditorRoundPayload:
        """Evaluate a single proposal review round from the audit projection."""

        audit_context = self._extract_audit_context(projection)
        if self.llm is None:
            return self._fallback_round(
                audit_context=audit_context,
                reason="LLM 不可用，已回退到内置审计裁决规则。",
            )

        try:
            schema = _AuditStructuredOutput.model_json_schema()
            response = self.llm.generate_structured(
                prompt=self._build_user_prompt(projection, audit_context),
                schema=schema,
                system_prompt=self._build_system_prompt(),
                temperature=0.2,
                schema_name="audit_round_output",
            )
            structured = _AuditStructuredOutput.model_validate(response)
            return self._coerce_structured_output(
                structured=structured,
                audit_context=audit_context,
            )
        except (ValidationError, Exception) as exc:
            logger.warning("AuditEvaluationAgent structured evaluation failed, using fallback: %s", exc)
            return self._fallback_round(
                audit_context=audit_context,
                reason=f"结构化审计裁决失败，已回退到内置规则：{exc}",
            )

    def _extract_audit_context(self, projection: ContextProjectionPayload) -> dict[str, Any]:
        context: dict[str, Any] = {
            "round": 1,
            "proposal_id": "proposal-1",
            "proposal_name": "",
            "architecture_pattern": "",
            "components": [],
            "compliance_score": 0.0,
            "risk_score": 0,
            "critical_count": 0,
            "quantum_ready": False,
            "quantum_required": False,
            "standards_checked": [],
            "audit_input": {},
            "vulnerability_report": {},
            "compliance_report": {},
            "quantum_eval": {},
            "tool_findings": [],
            "tool_recommendations": [],
            "projection_evidence_refs": [],
            "reflection_focus": [],
            "reflection_prompt_changes": [],
            "reflection_residual_risks": [],
            "reflection_summary": "",
        }

        context["projection_evidence_refs"] = self._extract_projection_evidence_refs(projection)
        context.update(self._extract_reflection_hints(projection))

        for card in projection.cards:
            if card.card_type != "audit_decision_input":
                continue
            payload = dict(card.payload or {})
            if payload.get("round") is not None:
                try:
                    context["round"] = int(payload["round"])
                except (TypeError, ValueError):
                    pass
            proposal_id = str(payload.get("proposal_id") or "").strip()
            if proposal_id:
                context["proposal_id"] = proposal_id
            context["proposal_name"] = str(payload.get("proposal_name") or "").strip()
            context["architecture_pattern"] = str(payload.get("architecture_pattern") or "").strip()
            context["components"] = self._sanitize_text_list(payload.get("components") or [], limit=6)
            context["standards_checked"] = self._sanitize_text_list(
                payload.get("standards_checked") or [],
                limit=8,
            )
            context["tool_findings"] = self._sanitize_text_list(payload.get("tool_findings") or [], limit=8)
            context["tool_recommendations"] = self._sanitize_text_list(
                payload.get("tool_recommendations") or [],
                limit=8,
            )
            if payload.get("compliance_score") is not None:
                try:
                    context["compliance_score"] = float(payload["compliance_score"])
                except (TypeError, ValueError):
                    pass
            if payload.get("risk_score") is not None:
                try:
                    context["risk_score"] = int(payload["risk_score"])
                except (TypeError, ValueError):
                    pass
            if payload.get("critical_count") is not None:
                try:
                    context["critical_count"] = int(payload["critical_count"])
                except (TypeError, ValueError):
                    pass
            context["quantum_ready"] = bool(payload.get("quantum_ready"))
            context["quantum_required"] = bool(payload.get("quantum_required"))
            if isinstance(payload.get("audit_input"), dict):
                context["audit_input"] = dict(payload["audit_input"])
            if isinstance(payload.get("vulnerability_report"), dict):
                context["vulnerability_report"] = dict(payload["vulnerability_report"])
            if isinstance(payload.get("compliance_report"), dict):
                context["compliance_report"] = dict(payload["compliance_report"])
            if isinstance(payload.get("quantum_eval"), dict):
                context["quantum_eval"] = dict(payload["quantum_eval"])
            return context

        raise ValueError("Audit evaluation projection missing audit_decision_input card")

    def _extract_projection_evidence_refs(self, projection: ContextProjectionPayload) -> list[str]:
        refs: list[str] = []
        seen: set[str] = set()
        for item in projection.evidence_refs:
            chunk_id = str(getattr(item, "chunk_id", "") or "").strip()
            doc_id = str(getattr(item, "doc_id", "") or "").strip()
            ref = chunk_id or doc_id
            if not ref or ref in seen:
                continue
            seen.add(ref)
            refs.append(ref)
        return refs[:8]

    def _extract_reflection_hints(self, projection: ContextProjectionPayload) -> dict[str, Any]:
        hints = {
            "reflection_focus": [],
            "reflection_prompt_changes": [],
            "reflection_residual_risks": [],
            "reflection_summary": "",
        }
        for card in projection.cards:
            if card.card_type != "reflection_memory":
                continue
            payload = dict(card.payload or {})
            hints["reflection_focus"] = self._sanitize_text_list(
                payload.get("latest_audit_focus") or [],
                limit=4,
            )
            hints["reflection_prompt_changes"] = self._sanitize_text_list(
                payload.get("latest_prompt_changes") or [],
                limit=4,
            )
            hints["reflection_residual_risks"] = self._sanitize_text_list(
                payload.get("latest_residual_risks") or [],
                limit=4,
            )
            hints["reflection_summary"] = str(payload.get("latest_reflection_summary") or "").strip()
            break
        return hints

    def _coerce_structured_output(
        self,
        *,
        structured: _AuditStructuredOutput,
        audit_context: dict[str, Any],
    ) -> AuditorRoundPayload:
        heuristic_reasons = self._build_heuristic_reasons(audit_context)
        reasons = self._sanitize_text_list(structured.reasons, limit=6)
        key_findings = self._sanitize_text_list(structured.key_findings, limit=8)
        recommended_changes = self._sanitize_text_list(structured.recommended_changes, limit=8)

        guardrail_reject = bool(heuristic_reasons)
        verdict = self._normalize_verdict(
            structured.verdict,
            reasons=reasons,
            guardrail_reject=guardrail_reject,
        )
        if guardrail_reject:
            reasons = self._merge_unique_texts(heuristic_reasons, reasons, limit=6)
        if not key_findings:
            key_findings = list(audit_context.get("tool_findings") or [])
        if not recommended_changes:
            recommended_changes = list(audit_context.get("tool_recommendations") or [])

        return AuditorRoundPayload(
            round=int(audit_context.get("round", 1) or 1),
            proposal_id=str(audit_context.get("proposal_id") or "proposal-1"),
            verdict=verdict,
            verdict_label=display_status(verdict),
            reasons=reasons,
            compliance_score=round(float(audit_context.get("compliance_score", 0.0) or 0.0), 2),
            risk_score=int(audit_context.get("risk_score", 0) or 0),
            quantum_ready=bool(audit_context.get("quantum_ready")),
            quantum_ready_label=display_bool(bool(audit_context.get("quantum_ready"))),
            standards_checked=list(audit_context.get("standards_checked") or []),
            key_findings=key_findings,
            recommended_changes=recommended_changes,
        )

    def _fallback_round(
        self,
        *,
        audit_context: dict[str, Any],
        reason: str,
    ) -> AuditorRoundPayload:
        reasons = self._build_heuristic_reasons(audit_context)
        if reason:
            reasons = self._merge_unique_texts(reasons, [reason], limit=6)
        verdict = "pass" if not reasons else "reject"
        key_findings = list(audit_context.get("tool_findings") or [])
        recommended_changes = list(audit_context.get("tool_recommendations") or [])
        return AuditorRoundPayload(
            round=int(audit_context.get("round", 1) or 1),
            proposal_id=str(audit_context.get("proposal_id") or "proposal-1"),
            verdict=verdict,
            verdict_label=display_status(verdict),
            reasons=reasons,
            compliance_score=round(float(audit_context.get("compliance_score", 0.0) or 0.0), 2),
            risk_score=int(audit_context.get("risk_score", 0) or 0),
            quantum_ready=bool(audit_context.get("quantum_ready")),
            quantum_ready_label=display_bool(bool(audit_context.get("quantum_ready"))),
            standards_checked=list(audit_context.get("standards_checked") or []),
            key_findings=key_findings,
            recommended_changes=recommended_changes,
        )

    def _build_heuristic_reasons(self, audit_context: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        critical_count = int(audit_context.get("critical_count", 0) or 0)
        compliance_score = float(audit_context.get("compliance_score", 0.0) or 0.0)
        risk_score = int(audit_context.get("risk_score", 0) or 0)
        quantum_required = bool(audit_context.get("quantum_required"))
        quantum_ready = bool(audit_context.get("quantum_ready"))
        if critical_count > 0:
            reasons.append(f"检测到 {critical_count} 个严重漏洞。")
        if compliance_score < 80:
            reasons.append(f"整体合规得分过低：{compliance_score:.1f}%。")
        if risk_score > 60:
            reasons.append(f"风险得分过高：{risk_score}/100。")
        if quantum_required and not quantum_ready:
            reasons.append("未满足后量子安全要求。")
        return reasons

    def _normalize_verdict(
        self,
        raw_verdict: str,
        *,
        reasons: list[str],
        guardrail_reject: bool,
    ) -> str:
        value = str(raw_verdict or "").strip().lower()
        if guardrail_reject:
            return "reject"
        if value in {"pass", "approve", "approved"}:
            return "pass"
        if value in {"reject", "fail", "failed"}:
            return "reject"
        return "reject" if reasons else "pass"

    def _build_system_prompt(self) -> str:
        return (
            "你是 BuildCipher Studio 的审计评估 Agent。"
            "你只在独立审计窗口内工作，需要结合合规工具、漏洞扫描、量子安全评估、"
            "约束卡与历史反思，对单个候选方案给出稳定的结构化裁决。"
            "必须优先遵守结构化事实，不要编造不存在的标准、漏洞或证据。"
            "输出中若建议通过，应确保与工具分数和风险事实一致；若存在明显未达标项，应明确拒绝理由。"
        )

    def _build_user_prompt(
        self,
        projection: ContextProjectionPayload,
        audit_context: dict[str, Any],
    ) -> str:
        prompt_payload = {
            "objective": projection.objective,
            "constraints": [
                {
                    "kind": item.constraint_kind,
                    "value": item.value,
                    "priority": item.priority,
                    "confirmed": item.confirmed,
                }
                for item in projection.constraints[:8]
            ],
            "proposal": {
                "proposal_id": audit_context.get("proposal_id"),
                "proposal_name": audit_context.get("proposal_name"),
                "architecture_pattern": audit_context.get("architecture_pattern"),
                "components": audit_context.get("components") or [],
            },
            "audit_summary": {
                "round": audit_context.get("round"),
                "compliance_score": audit_context.get("compliance_score"),
                "risk_score": audit_context.get("risk_score"),
                "critical_count": audit_context.get("critical_count"),
                "quantum_ready": audit_context.get("quantum_ready"),
                "quantum_required": audit_context.get("quantum_required"),
                "standards_checked": audit_context.get("standards_checked") or [],
            },
            "audit_input": audit_context.get("audit_input") or {},
            "tool_findings": audit_context.get("tool_findings") or [],
            "tool_recommendations": audit_context.get("tool_recommendations") or [],
            "vulnerability_report": audit_context.get("vulnerability_report") or {},
            "compliance_report": audit_context.get("compliance_report") or {},
            "quantum_eval": audit_context.get("quantum_eval") or {},
            "reflection_hints": {
                "audit_focus": audit_context.get("reflection_focus") or [],
                "prompt_changes": audit_context.get("reflection_prompt_changes") or [],
                "residual_risks": audit_context.get("reflection_residual_risks") or [],
                "reflection_summary": audit_context.get("reflection_summary") or "",
            },
            "evidence_refs": audit_context.get("projection_evidence_refs") or [],
        }
        return (
            "请基于下面的独立审计窗口信息，对当前候选方案给出结构化裁决。\n"
            "要求：\n"
            "1. `verdict` 只能输出 `pass` 或 `reject`。\n"
            "2. `reasons` 聚焦最终裁决原因，不要重复堆砌。\n"
            "3. `key_findings` 聚焦审计发现，可结合工具发现与约束缺口。\n"
            "4. `recommended_changes` 给出下一步整改方向。\n"
            "5. 不要输出额外字段。\n\n"
            f"{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
        )

    def _sanitize_text_list(self, items: list[Any], *, limit: int) -> list[str]:
        sanitized: list[str] = []
        seen: set[str] = set()
        for item in items or []:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            sanitized.append(text)
            if len(sanitized) >= limit:
                break
        return sanitized

    def _merge_unique_texts(self, base: list[str], extra: list[str], *, limit: int) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for group in (base or [], extra or []):
            text = str(group or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            merged.append(text)
            if len(merged) >= limit:
                break
        return merged
