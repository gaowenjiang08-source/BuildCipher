"""LLM-driven patch planning agent for closed-loop remediation."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cipher_genius.api.schemas import (
    AttackResultPayload,
    ContextProjectionPayload,
    ExpertGateDecisionPayload,
    PatchSpecPayload,
    TargetServiceSpecPayload,
    VulnerabilityVerdictPayload,
)
from cipher_genius.core.llm_interface import get_llm_interface
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class _PatchPlanStructuredOutput(BaseModel):
    """Strict structured output contract for patch planning."""

    model_config = ConfigDict(extra="forbid")

    strategy: str = "hardening-and-validation"
    summary: str = ""
    rationale: str = ""
    changed_artifacts: list[str] = Field(default_factory=list)
    implementation_notes: list[str] = Field(default_factory=list)
    validation_steps: list[str] = Field(default_factory=list)
    rollback_notes: list[str] = Field(default_factory=list)
    next_version: str = "v2"
    regression_focus: list[str] = Field(default_factory=list)


class PatchPlanningAgent:
    """Generate patch plans from a compact remediation projection."""

    ALLOWED_STRATEGIES = {
        "hardening-and-validation",
        "error-boundary-hardening",
        "input-contract-hardening",
        "key-lifecycle-hardening",
    }

    def __init__(self, llm_provider: Optional[str] = None, llm: Optional[Any] = None):
        self.llm_provider = llm_provider
        self.llm = llm
        if self.llm is None and llm_provider:
            try:
                self.llm = get_llm_interface(llm_provider)
            except Exception as exc:
                logger.warning("PatchPlanningAgent LLM unavailable, fallback enabled: %s", exc)
                self.llm = None

    def plan(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
    ) -> PatchSpecPayload:
        """Plan a stable remediation package from a role-aware patch projection."""

        target_service = self._extract_target_service(projection)
        patch_context = self._extract_patch_context(projection)
        if self.llm is None:
            return self._fallback_patch_spec(
                target_service=target_service,
                run_id=run_id,
                patch_context=patch_context,
            )

        try:
            schema = _PatchPlanStructuredOutput.model_json_schema()
            response = self.llm.generate_structured(
                prompt=self._build_user_prompt(projection, target_service, patch_context),
                schema=schema,
                system_prompt=self._build_system_prompt(),
                temperature=0.2,
                schema_name="patch_plan_output",
            )
            structured = _PatchPlanStructuredOutput.model_validate(response)
            return self._coerce_structured_output(
                structured=structured,
                target_service=target_service,
                run_id=run_id,
                patch_context=patch_context,
            )
        except (ValidationError, Exception) as exc:
            logger.warning("PatchPlanningAgent structured planning failed, using fallback: %s", exc)
            return self._fallback_patch_spec(
                target_service=target_service,
                run_id=run_id,
                patch_context=patch_context,
            )

    def _coerce_structured_output(
        self,
        *,
        structured: _PatchPlanStructuredOutput,
        target_service: TargetServiceSpecPayload,
        run_id: str,
        patch_context: dict[str, Any],
    ) -> PatchSpecPayload:
        strategy = self._normalize_strategy(structured.strategy, patch_context=patch_context)
        changed_artifacts = self._sanitize_changed_artifacts(
            structured.changed_artifacts,
            target_service=target_service,
        )
        next_version = self._normalize_next_version(
            structured.next_version,
            current_version=target_service.service_version,
        )
        regression_focus = self._sanitize_regression_focus(
            structured.regression_focus,
            patch_context=patch_context,
        )
        summary = str(structured.summary or "").strip() or self._default_summary(
            target_service=target_service,
            strategy=strategy,
            patch_context=patch_context,
        )
        rationale = str(structured.rationale or "").strip() or self._default_rationale(
            target_service=target_service,
            strategy=strategy,
            patch_context=patch_context,
        )
        implementation_notes = self._sanitize_text_items(
            structured.implementation_notes,
            limit=4,
        ) or self._default_implementation_notes(
            target_service=target_service,
            strategy=strategy,
            patch_context=patch_context,
        )
        validation_steps = self._sanitize_text_items(
            structured.validation_steps,
            limit=4,
        ) or self._default_validation_steps(
            target_service=target_service,
            patch_context=patch_context,
            regression_focus=regression_focus,
        )
        rollback_notes = self._sanitize_text_items(
            structured.rollback_notes,
            limit=4,
        ) or self._default_rollback_notes(
            target_service=target_service,
            next_version=next_version,
        )
        return PatchSpecPayload(
            patch_id=f"patch-{run_id[:8]}",
            target_service_ref=target_service.service_id,
            strategy=strategy,
            summary=summary,
            rationale=rationale,
            changed_artifacts=changed_artifacts,
            implementation_notes=implementation_notes,
            validation_steps=validation_steps,
            rollback_notes=rollback_notes,
            next_version=next_version,
            regression_focus=regression_focus,
        )

    def _fallback_patch_spec(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        run_id: str,
        patch_context: dict[str, Any],
    ) -> PatchSpecPayload:
        strategy = self._normalize_strategy("", patch_context=patch_context)
        return PatchSpecPayload(
            patch_id=f"patch-{run_id[:8]}",
            target_service_ref=target_service.service_id,
            strategy=strategy,
            summary=self._default_summary(
                target_service=target_service,
                strategy=strategy,
                patch_context=patch_context,
            ),
            rationale=self._default_rationale(
                target_service=target_service,
                strategy=strategy,
                patch_context=patch_context,
            ),
            changed_artifacts=self._sanitize_changed_artifacts([], target_service=target_service),
            implementation_notes=self._default_implementation_notes(
                target_service=target_service,
                strategy=strategy,
                patch_context=patch_context,
            ),
            validation_steps=self._default_validation_steps(
                target_service=target_service,
                patch_context=patch_context,
                regression_focus=self._sanitize_regression_focus([], patch_context=patch_context),
            ),
            rollback_notes=self._default_rollback_notes(
                target_service=target_service,
                next_version=self._normalize_next_version("", current_version=target_service.service_version),
            ),
            next_version=self._normalize_next_version("", current_version=target_service.service_version),
            regression_focus=self._sanitize_regression_focus([], patch_context=patch_context),
        )

    def _extract_target_service(self, projection: ContextProjectionPayload) -> TargetServiceSpecPayload:
        for artifact in projection.artifact_refs:
            if artifact.artifact_type not in {"target_service", "regression_target_service"}:
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
        raise ValueError("Patch planning projection missing target_service artifact")

    def _extract_patch_context(self, projection: ContextProjectionPayload) -> dict[str, Any]:
        context: dict[str, Any] = {
            "severity": "medium",
            "severity_label": "中",
            "remediation_priority": "high",
            "affected_components": [],
            "evidence_refs": [],
            "audit_reasons": [],
            "audit_recommended_changes": [],
            "expert_gate_decision_family": "patch_flow",
            "expert_gate_decision_family_label": "修补闭环",
            "expert_gate_action": "patch_required",
            "expert_gate_rationale": "",
            "expert_gate_route_target": "patch_agent",
            "expert_gate_route_target_label": "修补规划窗口",
            "expert_gate_residual_risk_summary": "",
            "expert_gate_follow_up_actions": [],
            "artifact_refs": [],
            "attack_results": [],
            "attack_result_summaries": [],
            "top_findings": [],
        }
        for card in projection.cards:
            payload = card.payload or {}
            if card.card_type == "vulnerability_verdict":
                raw_verdict = payload.get("verdict")
                if isinstance(raw_verdict, dict):
                    try:
                        verdict = VulnerabilityVerdictPayload.model_validate(raw_verdict)
                        context["severity"] = verdict.severity
                        context["severity_label"] = verdict.severity_label
                        context["remediation_priority"] = verdict.remediation_priority
                        context["affected_components"] = list(verdict.affected_components)
                        context["evidence_refs"] = list(verdict.evidence_refs)
                    except Exception:
                        pass
                context["severity"] = str(payload.get("severity") or context["severity"])
                context["severity_label"] = str(payload.get("severity_label") or context["severity_label"])
                context["affected_components"] = list(payload.get("affected_components") or context["affected_components"])
                context["evidence_refs"] = list(payload.get("evidence_refs") or context["evidence_refs"])
            elif card.card_type == "audit_decision":
                context["audit_reasons"] = [
                    str(item).strip() for item in payload.get("reasons") or [] if str(item).strip()
                ]
                context["audit_recommended_changes"] = [
                    str(item).strip()
                    for item in payload.get("recommended_changes") or []
                    if str(item).strip()
                ]
            elif card.card_type == "expert_gate_decision":
                raw_decision = payload.get("decision")
                if isinstance(raw_decision, dict):
                    try:
                        decision = ExpertGateDecisionPayload.model_validate(raw_decision)
                        context["expert_gate_decision_family"] = decision.decision_family
                        context["expert_gate_decision_family_label"] = decision.decision_family_label
                        context["expert_gate_action"] = decision.action
                        context["expert_gate_rationale"] = decision.rationale
                        context["expert_gate_route_target"] = decision.route_target
                        context["expert_gate_route_target_label"] = decision.route_target_label
                        context["expert_gate_residual_risk_summary"] = decision.residual_risk_summary
                        context["expert_gate_follow_up_actions"] = list(decision.follow_up_actions)
                    except Exception:
                        pass
                context["expert_gate_decision_family"] = str(
                    payload.get("decision_family") or context["expert_gate_decision_family"]
                ).strip()
                context["expert_gate_decision_family_label"] = str(
                    payload.get("decision_family_label") or context["expert_gate_decision_family_label"]
                ).strip()
                context["expert_gate_action"] = str(
                    payload.get("action") or context["expert_gate_action"]
                ).strip()
                context["expert_gate_rationale"] = str(
                    payload.get("rationale") or context["expert_gate_rationale"]
                ).strip()
                context["expert_gate_route_target"] = str(
                    payload.get("route_target") or context["expert_gate_route_target"]
                ).strip()
                context["expert_gate_route_target_label"] = str(
                    payload.get("route_target_label") or context["expert_gate_route_target_label"]
                ).strip()
                context["expert_gate_residual_risk_summary"] = str(
                    payload.get("residual_risk_summary") or context["expert_gate_residual_risk_summary"]
                ).strip()
                context["expert_gate_follow_up_actions"] = [
                    str(item).strip()
                    for item in payload.get("follow_up_actions") or context["expert_gate_follow_up_actions"]
                    if str(item).strip()
                ][:4]
            elif card.card_type == "attack_artifact_summary":
                context["artifact_refs"] = [
                    str(item).strip() for item in payload.get("artifact_refs") or [] if str(item).strip()
                ]
                context["attack_result_summaries"] = [
                    dict(item) for item in payload.get("attack_result_summaries") or [] if isinstance(item, dict)
                ][:4]
                context["top_findings"] = [
                    str(item).strip() for item in payload.get("top_findings") or [] if str(item).strip()
                ][:6]
                attack_results: list[AttackResultPayload] = []
                for item in payload.get("attack_results") or []:
                    try:
                        attack_results.append(AttackResultPayload.model_validate(item))
                    except Exception:
                        continue
                context["attack_results"] = attack_results
        return context

    def _normalize_strategy(self, strategy: str, *, patch_context: dict[str, Any]) -> str:
        normalized = str(strategy or "").strip().lower()
        if normalized in self.ALLOWED_STRATEGIES:
            return normalized
        affected = " ".join(str(item) for item in patch_context.get("affected_components") or []).lower()
        if "key" in affected or "密钥" in affected:
            return "key-lifecycle-hardening"
        if "input" in affected or "接口" in affected:
            return "input-contract-hardening"
        if "error" in affected or "错误" in affected:
            return "error-boundary-hardening"
        return "hardening-and-validation"

    def _sanitize_changed_artifacts(
        self,
        changed_artifacts: list[str],
        *,
        target_service: TargetServiceSpecPayload,
    ) -> list[str]:
        clean: list[str] = []
        seen: set[str] = set()
        for item in changed_artifacts:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            clean.append(text)
            seen.add(text)
        if clean:
            return clean[:4]
        artifact_root = target_service.artifact_id or target_service.service_id
        return [f"{artifact_root}:python", f"{artifact_root}:c"]

    def _normalize_next_version(self, next_version: str, *, current_version: str) -> str:
        normalized = str(next_version or "").strip()
        if normalized and normalized != current_version:
            return normalized
        match = re.search(r"(\d+)$", str(current_version or "").strip())
        if match:
            return f"v{int(match.group(1)) + 1}"
        return "v2"

    def _sanitize_regression_focus(
        self,
        regression_focus: list[str],
        *,
        patch_context: dict[str, Any],
    ) -> list[str]:
        clean: list[str] = []
        seen: set[str] = set()
        for item in regression_focus:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            clean.append(text)
            seen.add(text)
        if clean:
            return clean[:4]

        affected_components = [
            str(item).strip() for item in patch_context.get("affected_components") or [] if str(item).strip()
        ]
        if affected_components:
            return affected_components[:3]
        return ["错误处理泄露", "密钥使用边界", "接口滥用防护"]

    def _default_summary(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        strategy: str,
        patch_context: dict[str, Any],
    ) -> str:
        severity_label = str(patch_context.get("severity_label") or "中")
        affected_components = patch_context.get("affected_components") or []
        component_text = "、".join(str(item) for item in affected_components[:3]) or "接口约束、错误处理与密钥治理"
        gate_hint = str(patch_context.get("expert_gate_action") or "").strip()
        route_target = str(patch_context.get("expert_gate_route_target") or "").strip()
        gate_text = ""
        if gate_hint == "patch_required_with_regression":
            gate_text = "，并按专家闸门要求把正式回归验证作为补丁的一部分"
        elif route_target == "attack_planning_agent":
            gate_text = "；当前专家闸门建议先补充攻击验证，因此本修补方案更适合作为预案保留"
        elif route_target == "delivery":
            gate_text = "；当前专家闸门建议先观察收敛，因此本修补方案作为保守预案保留"
        return (
            f"建议针对目标服务 {target_service.service_name} 采用 {strategy} 策略，优先修补"
            f"{component_text}，并围绕当前{severity_label}风险补齐输入校验、错误掩码与回归验证{gate_text}。"
        )

    def _default_rationale(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        strategy: str,
        patch_context: dict[str, Any],
    ) -> str:
        severity_label = str(patch_context.get("severity_label") or "中")
        top_findings = [str(item).strip() for item in patch_context.get("top_findings") or [] if str(item).strip()]
        findings_text = "；".join(top_findings[:2]) or "攻击摘要显示当前实现仍存在稳定可复现的问题路径"
        gate_rationale = str(patch_context.get("expert_gate_rationale") or "").strip()
        route_target_label = str(patch_context.get("expert_gate_route_target_label") or "").strip()
        gate_tail = f" 专家闸门意见：{gate_rationale}" if gate_rationale else ""
        if route_target_label:
            gate_tail += f" 当前推荐路由：{route_target_label}。"
        return (
            f"选择 {strategy} 的原因是：目标服务 {target_service.service_name} 当前处于{severity_label}风险区间，"
            f"{findings_text}，需要先收口接口边界、错误处理和关键实现工件，再做回归验证。{gate_tail}"
        )

    def _default_implementation_notes(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        strategy: str,
        patch_context: dict[str, Any],
    ) -> list[str]:
        components = [
            str(item).strip() for item in patch_context.get("affected_components") or [] if str(item).strip()
        ]
        component_hint = "、".join(components[:2]) if components else "输入边界与错误处理"
        gate_follow_up = [
            str(item).strip()
            for item in patch_context.get("expert_gate_follow_up_actions") or []
            if str(item).strip()
        ]
        route_target_label = str(patch_context.get("expert_gate_route_target_label") or "").strip()
        return [
            f"优先修改 {target_service.service_name} 中与 {component_hint} 相关的核心实现分支。",
            f"按 {strategy} 策略统一错误返回、输入约束与敏感路径掩码。",
            *( [f"记录专家闸门路由建议：{route_target_label}。"] if route_target_label else [] ),
            *(gate_follow_up[:1] or []),
            "补丁交付应保留可回放的代码工件引用，便于后续回归对比。",
        ][:4]

    def _default_validation_steps(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        patch_context: dict[str, Any],
        regression_focus: list[str],
    ) -> list[str]:
        focus = [str(item).strip() for item in regression_focus if str(item).strip()]
        if not focus:
            focus = [
                str(item).strip()
                for item in patch_context.get("affected_components") or []
                if str(item).strip()
            ][:3]
        if not focus:
            focus = ["错误处理一致性", "接口输入边界", "密钥治理路径"]
        return [
            f"对目标服务 {target_service.service_name} 执行补丁版本重部署并完成健康检查。",
            f"围绕 {focus[0]} 做正式回归探测并比对 baseline / regression 差异。",
            "核查日志、finding 与 metrics 摘要，确认高风险问题已收敛且未引入新增回归。",
        ][:4]

    def _default_rollback_notes(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        next_version: str,
    ) -> list[str]:
        return [
            f"如回归探测未通过，回滚到 {target_service.service_version} 并保留失败补丁工件用于复盘。",
            f"仅在 {next_version} 版本的 validation_steps 全部通过后，才将补丁版本视为下一轮候选基线。",
        ]

    def _sanitize_text_items(self, values: list[str], *, limit: int) -> list[str]:
        clean: list[str] = []
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

    def _build_system_prompt(self) -> str:
        return (
            "你是 BuildCipher Studio 的 Patch Agent。\n"
            "你的职责是基于独立上下文窗口，为已在本地受限沙盒中发现问题的目标服务输出结构化修补方案。\n"
            "你只能输出修补策略、修补理由、实现要点、验证步骤、回滚注意事项、变更工件、版本推进和回归重点，不能输出破坏性动作或脱离沙盒边界的操作。\n"
            "请保持中文 summary 与 regression_focus，稳定字段名保持英文契约。"
        )

    def _build_user_prompt(
        self,
        projection: ContextProjectionPayload,
        target_service: TargetServiceSpecPayload,
        patch_context: dict[str, Any],
    ) -> str:
        projection_payload = projection.model_dump(mode="json")
        compact_payload = {
            "objective": projection.objective,
            "patch_context": {
                "severity": patch_context.get("severity"),
                "severity_label": patch_context.get("severity_label"),
                "remediation_priority": patch_context.get("remediation_priority"),
                "affected_components": patch_context.get("affected_components"),
                "evidence_refs": patch_context.get("evidence_refs"),
                "audit_recommended_changes": patch_context.get("audit_recommended_changes"),
                "audit_reasons": patch_context.get("audit_reasons"),
                "expert_gate_decision_family": patch_context.get("expert_gate_decision_family"),
                "expert_gate_decision_family_label": patch_context.get("expert_gate_decision_family_label"),
                "expert_gate_action": patch_context.get("expert_gate_action"),
                "expert_gate_rationale": patch_context.get("expert_gate_rationale"),
                "expert_gate_route_target": patch_context.get("expert_gate_route_target"),
                "expert_gate_route_target_label": patch_context.get("expert_gate_route_target_label"),
                "expert_gate_residual_risk_summary": patch_context.get("expert_gate_residual_risk_summary"),
                "expert_gate_follow_up_actions": patch_context.get("expert_gate_follow_up_actions"),
                "top_findings": patch_context.get("top_findings"),
                "attack_result_summaries": patch_context.get("attack_result_summaries"),
                "artifact_refs": patch_context.get("artifact_refs"),
            },
            "constraints": projection_payload.get("constraints", []),
            "cards": projection_payload.get("cards", []),
            "artifact_refs": projection_payload.get("artifact_refs", []),
            "evidence_refs": projection_payload.get("evidence_refs", []),
            "target_service": target_service.model_dump(mode="json"),
        }
        return (
            "请根据以下修补规划投影，输出一份结构化 PatchSpec。\n"
            "要求：\n"
            "1. strategy 使用英文稳定标识。\n"
            "2. summary、rationale、implementation_notes、validation_steps、rollback_notes、regression_focus 使用中文。\n"
            "3. changed_artifacts 只列修补后需要交付或重建的代码工件。\n"
            "4. next_version 必须是补丁后的新版本号。\n"
            "5. implementation_notes、validation_steps、rollback_notes、regression_focus 各控制在 1-4 条。\n\n"
            f"{json.dumps(compact_payload, ensure_ascii=False, indent=2)}"
        )
