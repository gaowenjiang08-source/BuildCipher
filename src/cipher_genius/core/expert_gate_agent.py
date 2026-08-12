"""LLM-driven expert gate between vulnerability evaluation and patch planning."""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cipher_genius.api.schemas import (
    AttackResultPayload,
    ContextProjectionPayload,
    ExpertGateDecisionPayload,
    TargetServiceSpecPayload,
    VulnerabilityVerdictPayload,
)
from cipher_genius.core.llm_interface import get_llm_interface
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class _ExpertGateStructuredOutput(BaseModel):
    """Strict expert-gate decision contract."""

    model_config = ConfigDict(extra="forbid")

    action: str = "patch_required"
    action_label: str = "进入修补"
    rationale: str = ""
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    residual_risk_summary: str = ""
    follow_up_actions: list[str] = Field(default_factory=list)


class ExpertGateAgent:
    """Produce a stable expert gate decision from an isolated projection window."""

    ALLOWED_ACTIONS = {
        "patch_required",
        "patch_required_with_regression",
        "retry_attack",
        "observe_only",
    }
    ACTION_LABELS = {
        "patch_required": "进入修补",
        "patch_required_with_regression": "进入修补并强制回归",
        "retry_attack": "补充攻击验证",
        "observe_only": "观察收敛",
    }
    DECISION_FAMILIES = {
        "patch_required": ("patch_flow", "修补闭环"),
        "patch_required_with_regression": ("patch_flow", "修补闭环"),
        "retry_attack": ("retry_flow", "补充验证"),
        "observe_only": ("observation_flow", "观察收敛"),
    }
    ROUTE_TARGETS = {
        "patch_required": ("patch_agent", "修补规划窗口"),
        "patch_required_with_regression": ("patch_agent", "修补规划窗口"),
        "retry_attack": ("attack_planning_agent", "攻击重规划窗口"),
        "observe_only": ("delivery", "交付观察窗口"),
    }

    def __init__(self, llm_provider: Optional[str] = None, llm: Optional[Any] = None):
        self.llm_provider = llm_provider
        self.llm = llm
        if self.llm is None and llm_provider:
            try:
                self.llm = get_llm_interface(llm_provider)
            except Exception as exc:
                logger.warning("ExpertGateAgent LLM unavailable, fallback enabled: %s", exc)
                self.llm = None

    def decide(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
    ) -> ExpertGateDecisionPayload:
        """Make an expert gate decision from a compact projection."""

        target_service = self._extract_target_service(projection)
        gate_context = self._extract_gate_context(projection)
        if self.llm is None:
            return self._fallback_decision(
                target_service=target_service,
                run_id=run_id,
                gate_context=gate_context,
                reason="LLM 不可用，已回退到内置专家闸门规则。",
            )

        try:
            schema = _ExpertGateStructuredOutput.model_json_schema()
            response = self.llm.generate_structured(
                prompt=self._build_user_prompt(projection, target_service, gate_context),
                schema=schema,
                system_prompt=self._build_system_prompt(),
                temperature=0.2,
                schema_name="expert_gate_output",
            )
            structured = _ExpertGateStructuredOutput.model_validate(response)
            return self._coerce_structured_output(
                structured=structured,
                target_service=target_service,
                run_id=run_id,
                gate_context=gate_context,
            )
        except (ValidationError, Exception) as exc:
            logger.warning("ExpertGateAgent structured decision failed, using fallback: %s", exc)
            return self._fallback_decision(
                target_service=target_service,
                run_id=run_id,
                gate_context=gate_context,
                reason=f"结构化专家裁决失败，已回退到内置规则：{exc}",
            )

    def _extract_target_service(self, projection: ContextProjectionPayload) -> TargetServiceSpecPayload:
        for artifact in projection.artifact_refs:
            if artifact.artifact_type != "target_service":
                continue
            metadata = artifact.metadata or {}
            service_id = str(metadata.get("service_id") or "").strip()
            if not service_id:
                continue
            return TargetServiceSpecPayload(
                service_id=service_id,
                artifact_id=artifact.artifact_id,
                service_name=str(metadata.get("service_name") or artifact.title or service_id),
                deployment_profile=str(metadata.get("deployment_profile") or "sandbox"),
                service_interface=str(metadata.get("service_interface") or "api"),
                attack_surface=list(metadata.get("attack_surface") or []),
                service_version=str(metadata.get("service_version") or "v1"),
                runtime=str(metadata.get("runtime") or "python"),
                entrypoint=str(metadata.get("entrypoint") or artifact.path or ""),
                status=str(metadata.get("status") or "deployed"),
                status_label=str(metadata.get("status_label") or "已部署"),
            )
        raise ValueError("Expert gate projection missing target_service artifact")

    def _extract_gate_context(self, projection: ContextProjectionPayload) -> dict[str, Any]:
        context: dict[str, Any] = {
            "severity": "medium",
            "severity_label": "中",
            "exploitability": "moderate",
            "remediation_priority": "high",
            "vulnerability_summary": "",
            "affected_components": [],
            "evidence_refs": [],
            "audit_reasons": [],
            "audit_recommended_changes": [],
            "top_findings": [],
            "attack_result_summaries": [],
            "attack_results": [],
            "artifact_refs": [],
        }

        for card in projection.cards:
            payload = dict(card.payload or {})
            if card.card_type == "expert_gate_input":
                context["severity"] = str(payload.get("severity") or context["severity"])
                context["severity_label"] = str(payload.get("severity_label") or context["severity_label"])
                context["exploitability"] = str(payload.get("exploitability") or context["exploitability"])
                context["remediation_priority"] = str(
                    payload.get("remediation_priority") or context["remediation_priority"]
                )
                context["vulnerability_summary"] = str(
                    payload.get("vulnerability_summary") or context["vulnerability_summary"]
                ).strip()
                context["affected_components"] = self._sanitize_text_list(
                    payload.get("affected_components") or context["affected_components"],
                    limit=6,
                )
                context["evidence_refs"] = self._sanitize_text_list(
                    payload.get("evidence_refs") or context["evidence_refs"],
                    limit=6,
                )
                context["audit_reasons"] = self._sanitize_text_list(
                    payload.get("audit_reasons") or context["audit_reasons"],
                    limit=6,
                )
                context["audit_recommended_changes"] = self._sanitize_text_list(
                    payload.get("audit_recommended_changes") or context["audit_recommended_changes"],
                    limit=6,
                )
                context["top_findings"] = self._sanitize_text_list(
                    payload.get("top_findings") or context["top_findings"],
                    limit=6,
                )
                context["artifact_refs"] = self._sanitize_text_list(
                    payload.get("artifact_refs") or context["artifact_refs"],
                    limit=8,
                )
                context["attack_result_summaries"] = [
                    dict(item)
                    for item in payload.get("attack_result_summaries") or []
                    if isinstance(item, dict)
                ][:4]
                continue

            if card.card_type == "vulnerability_verdict":
                raw_verdict = payload.get("verdict")
                if isinstance(raw_verdict, dict):
                    try:
                        verdict = VulnerabilityVerdictPayload.model_validate(raw_verdict)
                        context["severity"] = verdict.severity
                        context["severity_label"] = verdict.severity_label
                        context["exploitability"] = verdict.exploitability
                        context["remediation_priority"] = verdict.remediation_priority
                        context["vulnerability_summary"] = verdict.summary
                        context["affected_components"] = list(verdict.affected_components)
                        context["evidence_refs"] = list(verdict.evidence_refs)
                    except Exception:
                        pass
            elif card.card_type == "audit_decision":
                context["audit_reasons"] = self._sanitize_text_list(payload.get("reasons") or [], limit=6)
                context["audit_recommended_changes"] = self._sanitize_text_list(
                    payload.get("recommended_changes") or [],
                    limit=6,
                )
            elif card.card_type == "attack_artifact_summary":
                context["top_findings"] = self._sanitize_text_list(payload.get("top_findings") or [], limit=6)
                context["artifact_refs"] = self._sanitize_text_list(payload.get("artifact_refs") or [], limit=8)
                context["attack_result_summaries"] = [
                    dict(item)
                    for item in payload.get("attack_result_summaries") or []
                    if isinstance(item, dict)
                ][:4]
                attack_results: list[AttackResultPayload] = []
                for item in payload.get("attack_results") or []:
                    try:
                        attack_results.append(AttackResultPayload.model_validate(item))
                    except Exception:
                        continue
                context["attack_results"] = attack_results

        return context

    def _coerce_structured_output(
        self,
        *,
        structured: _ExpertGateStructuredOutput,
        target_service: TargetServiceSpecPayload,
        run_id: str,
        gate_context: dict[str, Any],
    ) -> ExpertGateDecisionPayload:
        action = self._normalize_action(
            structured.action,
            gate_context=gate_context,
        )
        rationale = str(structured.rationale or "").strip() or self._default_rationale(
            target_service=target_service,
            gate_context=gate_context,
            action=action,
        )
        residual_risk_summary = str(structured.residual_risk_summary or "").strip() or self._default_residual_summary(
            target_service=target_service,
            gate_context=gate_context,
            action=action,
        )
        follow_up_actions = self._sanitize_text_list(
            structured.follow_up_actions,
            limit=4,
        ) or self._default_follow_up_actions(
            gate_context=gate_context,
            action=action,
        )
        decision_family, decision_family_label = self.DECISION_FAMILIES[action]
        route_target, route_target_label = self.ROUTE_TARGETS[action]
        return ExpertGateDecisionPayload(
            decision_id=f"expert-gate-{run_id[:8]}",
            target_service_ref=target_service.service_id,
            decision_family=decision_family,
            decision_family_label=decision_family_label,
            action=action,
            action_label=self.ACTION_LABELS[action],
            route_target=route_target,
            route_target_label=route_target_label,
            rationale=rationale,
            confidence=max(0.0, min(1.0, float(structured.confidence))),
            residual_risk_summary=residual_risk_summary,
            follow_up_actions=follow_up_actions,
        )

    def _fallback_decision(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        run_id: str,
        gate_context: dict[str, Any],
        reason: str,
    ) -> ExpertGateDecisionPayload:
        action = self._normalize_action("", gate_context=gate_context)
        rationale = self._default_rationale(
            target_service=target_service,
            gate_context=gate_context,
            action=action,
        )
        if reason:
            rationale = f"{rationale} {reason}".strip()
        decision_family, decision_family_label = self.DECISION_FAMILIES[action]
        route_target, route_target_label = self.ROUTE_TARGETS[action]
        return ExpertGateDecisionPayload(
            decision_id=f"expert-gate-{run_id[:8]}",
            target_service_ref=target_service.service_id,
            decision_family=decision_family,
            decision_family_label=decision_family_label,
            action=action,
            action_label=self.ACTION_LABELS[action],
            route_target=route_target,
            route_target_label=route_target_label,
            rationale=rationale,
            confidence=0.72 if action != "observe_only" else 0.64,
            residual_risk_summary=self._default_residual_summary(
                target_service=target_service,
                gate_context=gate_context,
                action=action,
            ),
            follow_up_actions=self._default_follow_up_actions(
                gate_context=gate_context,
                action=action,
            ),
        )

    def _normalize_action(self, action: str, *, gate_context: dict[str, Any]) -> str:
        normalized = str(action or "").strip().lower()
        if normalized in self.ALLOWED_ACTIONS:
            if normalized == "observe_only" and str(gate_context.get("severity") or "medium") == "high":
                return "patch_required_with_regression"
            return normalized

        severity = str(gate_context.get("severity") or "medium").strip().lower()
        exploitability = str(gate_context.get("exploitability") or "moderate").strip().lower()
        top_findings = self._sanitize_text_list(gate_context.get("top_findings") or [], limit=6)
        if severity == "high" or exploitability == "high":
            return "patch_required_with_regression"
        if top_findings or str(gate_context.get("remediation_priority") or "").strip().lower() == "high":
            return "patch_required"
        return "observe_only"

    def _default_rationale(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        gate_context: dict[str, Any],
        action: str,
    ) -> str:
        severity_label = str(gate_context.get("severity_label") or "中")
        findings = self._sanitize_text_list(gate_context.get("top_findings") or [], limit=2)
        findings_text = "；".join(findings) or "当前攻击证据显示实现仍存在可解释的风险路径"
        if action == "retry_attack":
            return (
                f"目标服务 {target_service.service_name} 当前证据仍不足以直接收口，"
                f"建议先补充攻击验证，再决定修补边界。已观察到：{findings_text}。"
            )
        if action == "observe_only":
            return (
                f"目标服务 {target_service.service_name} 当前风险已收敛到可观察区间，"
                f"建议先保持版本稳定并持续监测，当前主要依据为：{findings_text}。"
            )
        return (
            f"目标服务 {target_service.service_name} 当前仍处于{severity_label}风险区间，"
            f"需要把漏洞裁决、攻击证据与审计整改建议汇总后进入修补收口。已观察到：{findings_text}。"
        )

    def _default_residual_summary(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        gate_context: dict[str, Any],
        action: str,
    ) -> str:
        severity_label = str(gate_context.get("severity_label") or "中")
        affected_components = self._sanitize_text_list(gate_context.get("affected_components") or [], limit=3)
        component_text = "、".join(affected_components) or "接口边界、错误处理与密钥治理路径"
        if action == "observe_only":
            return (
                f"{target_service.service_name} 当前残余风险可控，但仍需围绕 {component_text} 做持续观测。"
            )
        return (
            f"{target_service.service_name} 在 {component_text} 上仍有{severity_label}风险残留，"
            "需要通过补丁与回归验证共同收口。"
        )

    def _default_follow_up_actions(self, *, gate_context: dict[str, Any], action: str) -> list[str]:
        recommended_changes = self._sanitize_text_list(
            gate_context.get("audit_recommended_changes") or [],
            limit=3,
        )
        findings = self._sanitize_text_list(gate_context.get("top_findings") or [], limit=2)
        follow_up: list[str] = []
        if action == "retry_attack":
            follow_up.append("补充一次定向攻击验证，确认漏洞利用路径是否稳定可复现。")
        elif action == "observe_only":
            follow_up.append("保留当前版本并对关键指标做连续观测，避免过度修补引入新回归。")
        else:
            follow_up.append("进入补丁规划窗口，优先修补高风险组件并固化回归验证步骤。")
        for item in recommended_changes:
            follow_up.append(item)
        if findings and action != "observe_only":
            follow_up.append(f"回归验证需重点覆盖：{'；'.join(findings)}。")
        return follow_up[:4]

    def _sanitize_text_list(self, values: list[Any], *, limit: int) -> list[str]:
        clean: list[str] = []
        seen: set[str] = set()
        for item in values:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            clean.append(text)
            if len(clean) >= limit:
                break
        return clean

    def _build_system_prompt(self) -> str:
        return (
            "你是多智能体加密攻防闭环中的 Expert Gate Agent。"
            "你的任务不是直接修补代码，而是根据漏洞裁决、攻击证据和审计整改建议，"
            "判断当前目标服务下一步最合理的动作。"
            "请保持结构化、审慎、可复盘，优先输出中文理由，动作标识使用英文稳定值。"
        )

    def _build_user_prompt(
        self,
        projection: ContextProjectionPayload,
        target_service: TargetServiceSpecPayload,
        gate_context: dict[str, Any],
    ) -> str:
        projection_payload = projection.model_dump(mode="json")
        compact_payload = {
            "objective": projection.objective,
            "gate_context": {
                "severity": gate_context.get("severity"),
                "severity_label": gate_context.get("severity_label"),
                "exploitability": gate_context.get("exploitability"),
                "remediation_priority": gate_context.get("remediation_priority"),
                "vulnerability_summary": gate_context.get("vulnerability_summary"),
                "affected_components": gate_context.get("affected_components"),
                "evidence_refs": gate_context.get("evidence_refs"),
                "audit_reasons": gate_context.get("audit_reasons"),
                "audit_recommended_changes": gate_context.get("audit_recommended_changes"),
                "top_findings": gate_context.get("top_findings"),
                "attack_result_summaries": gate_context.get("attack_result_summaries"),
                "artifact_refs": gate_context.get("artifact_refs"),
            },
            "constraints": projection_payload.get("constraints", []),
            "cards": projection_payload.get("cards", []),
            "artifact_refs": projection_payload.get("artifact_refs", []),
            "evidence_refs": projection_payload.get("evidence_refs", []),
            "target_service": target_service.model_dump(mode="json"),
        }
        return (
            "请根据以下 Expert Gate 投影，输出一份结构化专家裁决。\n"
            "要求：\n"
            "1. action 必须是英文稳定标识，只能使用 patch_required / patch_required_with_regression / retry_attack / observe_only。\n"
            "2. decision_family 与 route_target 由系统按 action 自动推导，你只需专注动作本身与理由。\n"
            "3. action_label、rationale、residual_risk_summary、follow_up_actions 使用中文。\n"
            "4. 只有在风险明显收敛且证据充分时才能选择 observe_only。\n"
            "5. follow_up_actions 控制在 1-4 条，聚焦下一步执行动作。\n\n"
            f"{json.dumps(compact_payload, ensure_ascii=False, indent=2)}"
        )
