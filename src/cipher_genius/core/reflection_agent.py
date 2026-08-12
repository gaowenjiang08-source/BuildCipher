"""LLM-driven reflection agent for closed-loop prompt and policy optimization."""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cipher_genius.api.schemas import ContextProjectionPayload, TargetServiceSpecPayload
from cipher_genius.core.llm_interface import get_llm_interface
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class _ReflectionStructuredOutput(BaseModel):
    """Strict structured output contract for next-round reflection cards."""

    model_config = ConfigDict(extra="forbid")

    reflection_summary: str = ""
    regression_summary: str = ""
    prompt_changes: list[str] = Field(default_factory=list)
    audit_focus: list[str] = Field(default_factory=list)
    residual_risks: list[str] = Field(default_factory=list)
    changed_artifacts: list[str] = Field(default_factory=list)


class ReflectionAgent:
    """Generate reflection cards from an isolated reflection projection window."""

    def __init__(self, llm_provider: Optional[str] = None, llm: Optional[Any] = None):
        self.llm_provider = llm_provider
        self.llm = llm
        if self.llm is None and llm_provider:
            try:
                self.llm = get_llm_interface(llm_provider)
            except Exception as exc:
                logger.warning("ReflectionAgent LLM unavailable, fallback enabled: %s", exc)
                self.llm = None

    def reflect(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
        fallback_workspace: str = "",
    ) -> list[dict[str, Any]]:
        """Generate stable reflection cards for the next optimization round."""

        target_service = self._extract_target_service(projection)
        reflection_context = self._extract_reflection_context(projection)
        if self.llm is None:
            return self._fallback_cards(
                target_service=target_service,
                reflection_context=reflection_context,
                fallback_workspace=fallback_workspace,
                reason="已回退到内置反思策略。",
            )

        try:
            schema = _ReflectionStructuredOutput.model_json_schema()
            response = self.llm.generate_structured(
                prompt=self._build_user_prompt(projection, target_service, reflection_context),
                schema=schema,
                system_prompt=self._build_system_prompt(),
                temperature=0.2,
                schema_name="reflection_cards_output",
            )
            structured = _ReflectionStructuredOutput.model_validate(response)
            return self._coerce_structured_output(
                structured=structured,
                target_service=target_service,
                reflection_context=reflection_context,
                fallback_workspace=fallback_workspace,
                run_id=run_id,
            )
        except (ValidationError, Exception) as exc:
            logger.warning("ReflectionAgent structured reflection failed, using fallback: %s", exc)
            return self._fallback_cards(
                target_service=target_service,
                reflection_context=reflection_context,
                fallback_workspace=fallback_workspace,
                reason=f"结构化反思失败，已回退到内置策略：{exc}",
            )

    def _coerce_structured_output(
        self,
        *,
        structured: _ReflectionStructuredOutput,
        target_service: TargetServiceSpecPayload,
        reflection_context: dict[str, Any],
        fallback_workspace: str,
        run_id: str,
    ) -> list[dict[str, Any]]:
        changed_artifacts = self._sanitize_list(
            structured.changed_artifacts or reflection_context.get("changed_artifacts") or [],
            limit=4,
        )
        if not changed_artifacts:
            changed_artifacts = self._sanitize_list(
                reflection_context.get("changed_artifacts") or ["核心实现文件"],
                limit=4,
            )
        prompt_changes = self._sanitize_list(
            structured.prompt_changes,
            limit=4,
        ) or self._default_prompt_changes(
            severity=str(reflection_context.get("severity") or "medium"),
            changed_artifacts=changed_artifacts,
            regression_focus=reflection_context.get("regression_focus") or [],
            reflection_context=reflection_context,
        )
        audit_focus = self._sanitize_list(
            structured.audit_focus,
            limit=4,
        ) or self._default_audit_focus(
            regression_focus=reflection_context.get("regression_focus") or [],
            changed_artifacts=changed_artifacts,
            validation_steps=reflection_context.get("validation_steps") or [],
            validation_results=reflection_context.get("validation_results") or [],
        )
        residual_risks = self._sanitize_list(
            structured.residual_risks,
            limit=4,
        ) or self._default_residual_risks(reflection_context=reflection_context)

        reflection_summary = str(structured.reflection_summary or "").strip() or self._default_reflection_summary(
            target_service=target_service,
            reflection_context=reflection_context,
            changed_artifacts=changed_artifacts,
        )
        regression_summary = str(structured.regression_summary or "").strip() or self._default_regression_summary(
            target_service=target_service,
            reflection_context=reflection_context,
            changed_artifacts=changed_artifacts,
        )
        patch_spec = dict(reflection_context.get("patch_spec") or {})
        severity = str(reflection_context.get("severity") or "medium")
        patch_strategy = str(patch_spec.get("strategy") or "hardening-and-validation")
        next_version = str(patch_spec.get("next_version") or "")
        target_service_ref = str(patch_spec.get("target_service_ref") or target_service.service_id)

        return [
            {
                "card_type": "reflection",
                "target_service_ref": target_service_ref,
                "summary": reflection_summary,
                "severity": severity,
                "patch_strategy": patch_strategy,
                "changed_artifacts": changed_artifacts,
                "prompt_changes": prompt_changes,
                "audit_focus": audit_focus,
                "next_version": next_version,
                "reflection_run_id": run_id,
            },
            {
                "card_type": "regression_summary",
                "target_service_ref": target_service_ref,
                "summary": regression_summary,
                "severity": severity,
                "patch_strategy": patch_strategy,
                "workspace": fallback_workspace,
                "changed_artifacts": changed_artifacts,
                "residual_risks": residual_risks,
                "validation_focus": audit_focus,
                "next_version": next_version,
            },
        ]

    def _fallback_cards(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        reflection_context: dict[str, Any],
        fallback_workspace: str,
        reason: str,
    ) -> list[dict[str, Any]]:
        patch_spec = dict(reflection_context.get("patch_spec") or {})
        changed_artifacts = self._sanitize_list(reflection_context.get("changed_artifacts") or [], limit=4)
        if not changed_artifacts:
            changed_artifacts = ["核心实现文件"]
        prompt_changes = self._default_prompt_changes(
            severity=str(reflection_context.get("severity") or "medium"),
            changed_artifacts=changed_artifacts,
            regression_focus=reflection_context.get("regression_focus") or [],
            reflection_context=reflection_context,
        )
        audit_focus = self._default_audit_focus(
            regression_focus=reflection_context.get("regression_focus") or [],
            changed_artifacts=changed_artifacts,
            validation_steps=reflection_context.get("validation_steps") or [],
            validation_results=reflection_context.get("validation_results") or [],
        )
        residual_risks = self._default_residual_risks(reflection_context=reflection_context)
        reflection_summary = self._default_reflection_summary(
            target_service=target_service,
            reflection_context=reflection_context,
            changed_artifacts=changed_artifacts,
        )
        regression_summary = self._default_regression_summary(
            target_service=target_service,
            reflection_context=reflection_context,
            changed_artifacts=changed_artifacts,
        )
        if reason:
            reflection_summary = f"{reflection_summary} {reason}"
            regression_summary = f"{regression_summary} {reason}"

        return [
            {
                "card_type": "reflection",
                "target_service_ref": str(patch_spec.get("target_service_ref") or target_service.service_id),
                "summary": reflection_summary,
                "severity": str(reflection_context.get("severity") or "medium"),
                "patch_strategy": str(patch_spec.get("strategy") or "hardening-and-validation"),
                "changed_artifacts": changed_artifacts,
                "prompt_changes": prompt_changes,
                "audit_focus": audit_focus,
                "next_version": str(patch_spec.get("next_version") or ""),
            },
            {
                "card_type": "regression_summary",
                "target_service_ref": str(patch_spec.get("target_service_ref") or target_service.service_id),
                "summary": regression_summary,
                "severity": str(reflection_context.get("severity") or "medium"),
                "patch_strategy": str(patch_spec.get("strategy") or "hardening-and-validation"),
                "workspace": fallback_workspace,
                "changed_artifacts": changed_artifacts,
                "residual_risks": residual_risks,
                "validation_focus": audit_focus,
                "next_version": str(patch_spec.get("next_version") or ""),
            },
        ]

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
        raise ValueError("Reflection projection missing target_service artifact")

    def _extract_reflection_context(self, projection: ContextProjectionPayload) -> dict[str, Any]:
        context: dict[str, Any] = {
            "patch_spec": {},
            "patch_execution": {},
            "severity": "medium",
            "severity_label": "中",
            "affected_components": [],
            "regression_focus": [],
            "changed_artifacts": [],
            "diff_preview": [],
            "regression_attack_result_summaries": [],
            "evidence_refs": [],
            "implementation_notes": [],
            "validation_steps": [],
            "validation_results": [],
            "validation_summary": {},
            "artifact_inventory": {},
            "supporting_artifacts": [],
            "rollback_notes": [],
        }
        for card in projection.cards:
            payload = card.payload or {}
            if card.card_type == "reflection_summary":
                patch_spec = dict(payload.get("patch_spec") or {})
                context["patch_spec"] = patch_spec
                context["regression_attack_result_summaries"] = [
                    dict(item)
                    for item in payload.get("regression_attack_result_summaries") or []
                    if isinstance(item, dict)
                ][:4]
                verdict = dict(payload.get("regression_vulnerability_verdict") or {})
                context["severity_label"] = str(payload.get("regression_severity") or verdict.get("severity_label") or "中")
                context["severity"] = str(verdict.get("severity") or context["severity"])
                context["affected_components"] = [
                    str(item).strip()
                    for item in verdict.get("affected_components") or []
                    if str(item).strip()
                ][:4]
                context["evidence_refs"] = [
                    str(item).strip() for item in verdict.get("evidence_refs") or [] if str(item).strip()
                ][:4]
                context["implementation_notes"] = [
                    str(item).strip()
                    for item in patch_spec.get("implementation_notes") or []
                    if str(item).strip()
                ][:4]
                context["validation_steps"] = [
                    str(item).strip()
                    for item in patch_spec.get("validation_steps") or []
                    if str(item).strip()
                ][:4]
                context["rollback_notes"] = [
                    str(item).strip()
                    for item in patch_spec.get("rollback_notes") or []
                    if str(item).strip()
                ][:4]
            elif card.card_type == "patch_execution":
                patch_execution = dict(payload or {})
                context["patch_execution"] = patch_execution
                if not context["validation_steps"]:
                    context["validation_steps"] = [
                        str(item).strip()
                        for item in patch_execution.get("validation_steps") or []
                        if str(item).strip()
                    ][:4]
                context["validation_results"] = [
                    dict(item)
                    for item in patch_execution.get("validation_results") or []
                    if isinstance(item, dict)
                ][:4]
                context["validation_summary"] = dict(patch_execution.get("validation_summary") or {})
                context["artifact_inventory"] = dict(patch_execution.get("artifact_inventory") or {})
                context["supporting_artifacts"] = [
                    dict(item)
                    for item in patch_execution.get("supporting_artifact_summaries") or []
                    if isinstance(item, dict)
                ][:4]
                if not context["changed_artifacts"]:
                    changed_summaries = [
                        dict(item)
                        for item in patch_execution.get("changed_artifact_summaries") or []
                        if isinstance(item, dict)
                    ][:4]
                    context["changed_artifacts"] = [
                        str(item.get("relative_name") or item.get("artifact_key") or "").strip()
                        for item in changed_summaries
                        if str(item.get("relative_name") or item.get("artifact_key") or "").strip()
                    ]
                if not context["diff_preview"]:
                    context["diff_preview"] = self._sanitize_list(
                        patch_execution.get("diff_preview") or [],
                        limit=6,
                    )
            elif card.card_type == "regression_verdict_input":
                context["severity"] = str(payload.get("severity") or context["severity"])
                context["severity_label"] = str(payload.get("severity_label") or context["severity_label"])
                context["affected_components"] = [
                    str(item).strip()
                    for item in payload.get("affected_components") or context["affected_components"]
                    if str(item).strip()
                ][:4]
            elif card.card_type == "patch_artifact_summary":
                context["regression_focus"] = [
                    str(item).strip() for item in payload.get("regression_focus") or [] if str(item).strip()
                ][:4]
                changed_summaries = [
                    dict(item)
                    for item in payload.get("changed_artifact_summaries") or []
                    if isinstance(item, dict)
                ][:4]
                context["changed_artifacts"] = [
                    str(item.get("relative_name") or item.get("artifact_key") or "").strip()
                    for item in changed_summaries
                    if str(item.get("relative_name") or item.get("artifact_key") or "").strip()
                ]
                diff_preview: list[str] = []
                for item in changed_summaries:
                    for line in item.get("diff_preview") or []:
                        text = str(line or "").strip()
                        if text and text not in diff_preview:
                            diff_preview.append(text)
                        if len(diff_preview) >= 6:
                            break
                    if len(diff_preview) >= 6:
                        break
                context["diff_preview"] = diff_preview
        return context

    def _default_prompt_changes(
        self,
        *,
        severity: str,
        changed_artifacts: list[str],
        regression_focus: list[str],
        reflection_context: dict[str, Any],
    ) -> list[str]:
        changed_hint = "、".join(changed_artifacts[:2]) if changed_artifacts else "核心实现文件"
        focus_hint = "、".join(regression_focus[:2]) if regression_focus else "错误处理、接口边界与密钥治理"
        if severity == "high":
            return [
                f"generation 必须显式说明 {changed_hint} 的输入输出约束、错误掩码和安全边界。",
                f"audit 必须把 {focus_hint} 作为高优先级核查项，并要求证据引用。",
                "generation 需要把补丁理由、攻击面收敛方式和剩余风险假设写清楚。",
            ]
        prompt_changes = [
            f"generation 需要继续解释 {changed_hint} 的修补理由与接口契约。",
            f"audit 需要围绕 {focus_hint} 做定向回归核查。",
            "交付摘要中继续保留证据引用与残余风险说明。",
        ]
        implementation_notes = self._sanitize_list(
            reflection_context.get("implementation_notes") or [],
            limit=2,
        )
        if implementation_notes:
            prompt_changes.append(f"generation 需吸收修补实现要点：{implementation_notes[0]}")
        return prompt_changes[:4]

    def _default_audit_focus(
        self,
        *,
        regression_focus: list[str],
        changed_artifacts: list[str],
        validation_steps: list[str] | None = None,
        validation_results: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        unresolved_steps = [
            str(item.get("step") or "").strip()
            for item in validation_results or []
            if str(item.get("status") or "") in {"failed", "skipped"}
            and str(item.get("step") or "").strip()
        ][:3]
        if unresolved_steps:
            return [f"优先复核：{item}" for item in unresolved_steps]
        focus = self._sanitize_list(regression_focus, limit=4)
        if focus:
            return focus
        validation_focus = self._sanitize_list(validation_steps or [], limit=2)
        if validation_focus:
            return validation_focus
        changed_hint = "、".join(changed_artifacts[:2]) if changed_artifacts else "核心实现文件"
        return [
            f"核查 {changed_hint} 的输入边界与错误处理是否一致。",
            "核查密钥治理与回归探测证据是否闭环。",
        ]

    def _default_residual_risks(self, *, reflection_context: dict[str, Any]) -> list[str]:
        unresolved = [
            f"{str(item.get('step') or '').strip()}：{str(item.get('details') or '').strip()}"
            for item in reflection_context.get("validation_results") or []
            if str(item.get("status") or "") in {"failed", "skipped"}
            and str(item.get("step") or "").strip()
        ][:3]
        if unresolved:
            return unresolved
        risks = self._sanitize_list(reflection_context.get("affected_components") or [], limit=4)
        if risks:
            return risks
        diff_preview = self._sanitize_list(reflection_context.get("diff_preview") or [], limit=3)
        if diff_preview:
            return diff_preview
        rollback_notes = self._sanitize_list(reflection_context.get("rollback_notes") or [], limit=2)
        if rollback_notes:
            return rollback_notes
        return ["仍需继续关注错误处理边界、接口契约和密钥治理。"]

    def _default_reflection_summary(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        reflection_context: dict[str, Any],
        changed_artifacts: list[str],
    ) -> str:
        changed_hint = "、".join(changed_artifacts[:2]) if changed_artifacts else "核心实现文件"
        severity_label = str(reflection_context.get("severity_label") or "中")
        return (
            f"下一轮 generation 应继续围绕目标服务 {target_service.service_name} 输出带接口约束、"
            f"错误处理掩码与密钥治理边界的实现说明，并显式解释 {changed_hint} 的修补依据。"
            f"当前残余风险等级为 {severity_label}。"
        )

    def _default_regression_summary(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        reflection_context: dict[str, Any],
        changed_artifacts: list[str],
    ) -> str:
        changed_hint = "、".join(changed_artifacts[:2]) if changed_artifacts else "核心实现文件"
        severity_label = str(reflection_context.get("severity_label") or "中")
        return (
            f"补丁版本目标服务 {target_service.service_name} 已完成正式回归探测，"
            f"当前残余严重度为 {severity_label}，后续仍需围绕 {changed_hint} 持续验证实现收敛效果。"
        )

    def _build_system_prompt(self) -> str:
        return (
            "你是 BuildTrust Studio 的 Reflection Agent。\n"
            "你的职责是基于独立上下文窗口，把补丁结果、回归攻击摘要和残余风险裁决沉淀成下一轮生成与审计可复用的反思卡。\n"
            "你只能输出中文反思摘要、提示词优化建议、审计关注点和残余风险，不得输出新的攻击步骤、脱离沙盒边界的操作或外网入侵建议。\n"
            "稳定字段名保持英文契约，用户可见内容保持中文。"
        )

    def _build_user_prompt(
        self,
        projection: ContextProjectionPayload,
        target_service: TargetServiceSpecPayload,
        reflection_context: dict[str, Any],
    ) -> str:
        projection_payload = projection.model_dump(mode="json")
        compact_payload = {
            "objective": projection.objective,
            "reflection_context": {
                "severity": reflection_context.get("severity"),
                "severity_label": reflection_context.get("severity_label"),
                "affected_components": reflection_context.get("affected_components"),
                "regression_focus": reflection_context.get("regression_focus"),
                "changed_artifacts": reflection_context.get("changed_artifacts"),
                "diff_preview": reflection_context.get("diff_preview"),
                "patch_execution": reflection_context.get("patch_execution"),
                "regression_attack_result_summaries": reflection_context.get("regression_attack_result_summaries"),
                "patch_spec": reflection_context.get("patch_spec"),
            },
            "constraints": projection_payload.get("constraints", []),
            "cards": projection_payload.get("cards", []),
            "artifact_refs": projection_payload.get("artifact_refs", []),
            "evidence_refs": projection_payload.get("evidence_refs", []),
            "target_service": target_service.model_dump(mode="json"),
        }
        return (
            "请根据以下反思投影，输出一组结构化 reflection cards 输入。\n"
            "要求：\n"
            "1. reflection_summary、regression_summary、prompt_changes、audit_focus、residual_risks 使用中文。\n"
            "2. changed_artifacts 只列本轮真正需要后续 generation / audit 关注的核心实现文件。\n"
            "3. prompt_changes 控制在 2-4 条，强调下一轮 generation / audit 要如何调整。\n"
            "4. residual_risks 优先引用残余风险组件、回归重点或 patch diff 线索。\n\n"
            f"{json.dumps(compact_payload, ensure_ascii=False, indent=2)}"
        )

    def _sanitize_list(self, values: Any, *, limit: int) -> list[str]:
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
