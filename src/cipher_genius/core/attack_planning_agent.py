"""LLM-driven attack planning agent for sandbox-safe execution loops."""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cipher_genius.api.schemas import (
    AttackDecisionPayload,
    AttackSpecPayload,
    ContextProjectionPayload,
    TargetServiceDeploymentManifestPayload,
    TargetServiceRuntimeProfilePayload,
    TargetServiceSpecPayload,
)
from cipher_genius.core.llm_interface import get_llm_interface
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class _AttackDecisionStructuredOutput(BaseModel):
    """Strict structured output contract for attack planning decisions."""

    model_config = ConfigDict(extra="forbid")

    action: str = "execute"
    action_label: str = "执行攻击"
    rationale: str = ""
    selected_attack_family: str = ""
    expected_outcome: str = ""
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    stop_conditions: list[str] = Field(default_factory=list)
    next_step: str = "dispatch_attack"


class _AttackSpecStructuredOutput(BaseModel):
    """Single bounded attack plan item emitted by the planner."""

    model_config = ConfigDict(extra="forbid")

    attack_family: str
    objective: str = ""
    attack_surface: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    telemetry_fields: list[str] = Field(default_factory=list)
    budget: dict[str, Any] = Field(default_factory=dict)


class _AttackPlanningStructuredOutput(BaseModel):
    """Full structured planner output."""

    model_config = ConfigDict(extra="forbid")

    decision: _AttackDecisionStructuredOutput
    attack_specs: list[_AttackSpecStructuredOutput] = Field(default_factory=list)


class AttackPlanningAgent:
    """Generate sandbox-safe attack decisions from a compact projection window."""

    DISPATCH_ACTIONS = {"execute", "continue", "replan"}
    NON_DISPATCH_ACTIONS = {"stop", "handoff_to_vulnerability"}
    ACTION_LABELS = {
        "execute": "执行攻击",
        "continue": "继续攻击",
        "replan": "重规划回归攻击",
        "handoff_to_vulnerability": "转交漏洞评估",
        "stop": "停止攻击",
    }
    NEXT_STEP_BY_ACTION = {
        "execute": "dispatch_attack",
        "continue": "dispatch_attack",
        "replan": "dispatch_attack",
        "handoff_to_vulnerability": "handoff_to_vulnerability",
        "stop": "stop_attack_loop",
    }
    DEFAULT_EXPECTED_ARTIFACTS = ["finding.json", "metrics.json", "trace.jsonl"]
    DEFAULT_TELEMETRY_FIELDS = ["cpu", "memory", "tx_bytes", "rx_bytes", "latency_p95"]
    DEFAULT_BUDGET = {"timeout_s": 180, "cpu_cores": 1, "memory_mb": 512}
    REGRESSION_BUDGET = {"timeout_s": 60, "cpu_cores": 1, "memory_mb": 256}

    def __init__(self, llm_provider: Optional[str] = None, llm: Optional[Any] = None):
        self.llm_provider = llm_provider
        self.llm = llm
        if self.llm is None and llm_provider:
            try:
                self.llm = get_llm_interface(llm_provider)
            except Exception as exc:
                logger.warning("AttackPlanningAgent LLM unavailable, fallback enabled: %s", exc)
                self.llm = None

    def plan(
        self,
        projection: ContextProjectionPayload,
        *,
        run_id: str,
    ) -> tuple[AttackDecisionPayload, list[AttackSpecPayload]]:
        """Plan attack actions from a role-aware context projection."""

        target_service = self._extract_target_service(projection)
        plan_context = self._extract_plan_context(projection)
        if self.llm is None:
            return self._fallback_plan(
                target_service=target_service,
                run_id=run_id,
                plan_context=plan_context,
                reason="LLM 不可用，已回退到内置攻击规划。",
            )

        try:
            schema = _AttackPlanningStructuredOutput.model_json_schema()
            response = self.llm.generate_structured(
                prompt=self._build_user_prompt(projection, target_service, plan_context),
                schema=schema,
                system_prompt=self._build_system_prompt(),
                temperature=0.2,
                schema_name="attack_planning_output",
            )
            structured = _AttackPlanningStructuredOutput.model_validate(response)
            decision, attack_specs = self._coerce_structured_output(
                structured=structured,
                target_service=target_service,
                run_id=run_id,
                plan_context=plan_context,
            )
            if not attack_specs and decision.action not in self.NON_DISPATCH_ACTIONS:
                raise ValueError("Planner returned empty attack_specs")
            return decision, attack_specs
        except (ValidationError, Exception) as exc:
            logger.warning("AttackPlanningAgent structured planning failed, using fallback: %s", exc)
            return self._fallback_plan(
                target_service=target_service,
                run_id=run_id,
                plan_context=plan_context,
                reason=f"结构化攻击规划失败，已回退到内置规划：{exc}",
            )

    def _coerce_structured_output(
        self,
        *,
        structured: _AttackPlanningStructuredOutput,
        target_service: TargetServiceSpecPayload,
        run_id: str,
        plan_context: dict[str, Any],
    ) -> tuple[AttackDecisionPayload, list[AttackSpecPayload]]:
        specs: list[AttackSpecPayload] = []
        default_family = "regression_check" if plan_context["planning_mode"] == "regression" else "misuse_case"
        default_action, default_action_label = self._default_action(plan_context)
        default_budget = self.REGRESSION_BUDGET if plan_context["planning_mode"] == "regression" else self.DEFAULT_BUDGET
        normalized_action = self._normalize_action(
            structured.decision.action,
            default_action=default_action,
        )
        normalized_action_label = self._normalize_action_label(
            normalized_action,
            candidate=structured.decision.action_label,
            default_label=default_action_label,
        )
        normalized_next_step = self._normalize_next_step(
            normalized_action,
            candidate=structured.decision.next_step,
        )

        for index, item in enumerate(structured.attack_specs[:4], start=1):
            attack_surface = item.attack_surface or list(target_service.attack_surface)
            specs.append(
                AttackSpecPayload(
                    attack_id=f"attack-{run_id[:8]}-{index}",
                    target_service_ref=target_service.service_id,
                    attack_family=(item.attack_family or default_family).strip(),
                    objective=(item.objective or self._default_objective(plan_context)).strip(),
                    attack_surface=attack_surface,
                    expected_artifacts=item.expected_artifacts or list(self.DEFAULT_EXPECTED_ARTIFACTS),
                    telemetry_fields=item.telemetry_fields or list(self.DEFAULT_TELEMETRY_FIELDS),
                    budget=self._sanitize_budget(item.budget, default_budget=default_budget),
                    status="planned",
                    status_label="待执行" if plan_context["planning_mode"] != "regression" else "待回归",
                )
            )

        if normalized_action in self.NON_DISPATCH_ACTIONS:
            specs = []

        selected_family = (
            structured.decision.selected_attack_family.strip()
            if structured.decision.selected_attack_family.strip()
            else (specs[0].attack_family if specs else default_family)
        )
        decision = AttackDecisionPayload(
            decision_id=f"attack-decision-{run_id[:8]}",
            target_service_ref=target_service.service_id,
            action=normalized_action,
            action_label=normalized_action_label,
            rationale=(structured.decision.rationale or "").strip(),
            selected_attack_family=selected_family,
            expected_outcome=(structured.decision.expected_outcome or self._default_expected_outcome(plan_context)).strip(),
            confidence=structured.decision.confidence,
            stop_conditions=[item.strip() for item in structured.decision.stop_conditions if str(item).strip()],
            next_step=normalized_next_step,
        )
        return decision, specs

    def _fallback_plan(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        run_id: str,
        plan_context: dict[str, Any],
        reason: str,
    ) -> tuple[AttackDecisionPayload, list[AttackSpecPayload]]:
        planning_mode = plan_context["planning_mode"]
        risk_score = int(plan_context.get("risk_score", 0))
        action, action_label = self._default_action(plan_context)
        attack_surface = list(target_service.attack_surface) or [target_service.service_interface]

        if planning_mode == "regression":
            attack_family = "regression_check"
            focuses = list(plan_context.get("regression_focus") or []) or ["接口约束回归", "错误处理回归", "密钥治理回归"]
            attack_specs = [
                AttackSpecPayload(
                    attack_id=f"attack-{run_id[:8]}-{index}",
                    target_service_ref=target_service.service_id,
                    attack_family=attack_family,
                    objective=f"围绕“{focus}”验证补丁后的残余风险与回归质量。",
                    attack_surface=attack_surface,
                    expected_artifacts=["regression_trace.jsonl", "regression_metrics.json", "finding.json"],
                    telemetry_fields=list(self.DEFAULT_TELEMETRY_FIELDS),
                    budget=dict(self.REGRESSION_BUDGET),
                    status="planned",
                    status_label="待回归",
                )
                for index, focus in enumerate(focuses[:3], start=1)
            ]
        else:
            attack_family = "oracle_probe" if risk_score >= 60 else "misuse_case"
            attack_specs = [
                AttackSpecPayload(
                    attack_id=f"attack-{run_id[:8]}-1",
                    target_service_ref=target_service.service_id,
                    attack_family=attack_family,
                    objective=self._default_objective(plan_context),
                    attack_surface=attack_surface,
                    expected_artifacts=list(self.DEFAULT_EXPECTED_ARTIFACTS),
                    telemetry_fields=list(self.DEFAULT_TELEMETRY_FIELDS),
                    budget=dict(self.DEFAULT_BUDGET),
                    status="planned",
                    status_label="待执行",
                )
            ]

        decision = AttackDecisionPayload(
            decision_id=f"attack-decision-{run_id[:8]}",
            target_service_ref=target_service.service_id,
            action=action,
            action_label=action_label,
            rationale=reason,
            selected_attack_family=attack_family,
            expected_outcome=self._default_expected_outcome(plan_context),
            confidence=0.45 if self.llm is None else 0.55,
            stop_conditions=[
                "超过沙盒预算立即终止",
                "若调度器阻断执行则停止下发",
                "若连续未获得有效证据则转入漏洞评估",
            ],
            next_step="dispatch_attack",
        )
        return decision, attack_specs

    def _extract_target_service(self, projection: ContextProjectionPayload) -> TargetServiceSpecPayload:
        for artifact in projection.artifact_refs:
            if artifact.artifact_type not in {"target_service", "regression_target_service"}:
                continue
            metadata = artifact.metadata or {}
            service_id = str(metadata.get("service_id") or "").strip()
            if not service_id:
                continue
            deployment_manifest = TargetServiceDeploymentManifestPayload.model_validate(
                metadata.get("deployment_manifest") or {}
            )
            runtime_profile = TargetServiceRuntimeProfilePayload.model_validate(
                metadata.get("runtime_profile") or {}
            )
            return TargetServiceSpecPayload(
                service_id=service_id,
                artifact_id=artifact.artifact_id,
                template_id=str(metadata.get("template_id") or "mock_crypto_http_v1"),
                template_label=str(metadata.get("template_label") or "模拟加密 HTTP 服务"),
                service_kind=str(metadata.get("service_kind") or "crypto_api"),
                attack_surface_kind=str(metadata.get("attack_surface_kind") or "http-json"),
                service_name=str(metadata.get("service_name") or artifact.title or service_id),
                deployment_profile=str(metadata.get("deployment_profile") or "sandbox"),
                service_interface=str(metadata.get("service_interface") or "api"),
                attack_surface=list(metadata.get("attack_surface") or []),
                service_version=str(metadata.get("service_version") or "v1"),
                runtime=str(metadata.get("runtime") or "python"),
                entrypoint=str(metadata.get("entrypoint") or artifact.path or ""),
                supported_versions=list(metadata.get("supported_versions") or []),
                planner_skill_hints=list(metadata.get("planner_skill_hints") or []),
                planner_retrieval_hints=list(metadata.get("planner_retrieval_hints") or []),
                deployment_manifest=deployment_manifest,
                runtime_profile=runtime_profile,
                status=str(metadata.get("status") or "deployed"),
                status_label=str(metadata.get("status_label") or "已部署"),
            )
        raise ValueError("Attack planning projection missing target_service artifact")

    def _build_planner_knowledge_context(
        self,
        target_service: TargetServiceSpecPayload,
    ) -> dict[str, Any]:
        """Expose template-scoped planner hints as a stable enhancement entrypoint."""

        return {
            "target_template": {
                "template_id": target_service.template_id,
                "template_label": target_service.template_label,
                "service_kind": target_service.service_kind,
                "attack_surface_kind": target_service.attack_surface_kind,
                "supported_versions": list(target_service.supported_versions),
            },
            "planner_skill_hints": list(target_service.planner_skill_hints),
            "planner_retrieval_hints": list(target_service.planner_retrieval_hints),
            "runtime_profile": {
                "timeout_seconds": target_service.runtime_profile.timeout_seconds,
                "memory_budget_mb": target_service.runtime_profile.memory_budget_mb,
                "probe_budget": target_service.runtime_profile.probe_budget,
                "traffic_sampling_interval_ms": target_service.runtime_profile.traffic_sampling_interval_ms,
                "cleanup_policy": target_service.runtime_profile.cleanup_policy,
            },
            "deployment_manifest": {
                "healthcheck": target_service.deployment_manifest.healthcheck,
                "bootstrap_script": target_service.deployment_manifest.bootstrap_script,
            },
        }

    def _extract_plan_context(self, projection: ContextProjectionPayload) -> dict[str, Any]:
        context: dict[str, Any] = {
            "planning_mode": "baseline",
            "risk_score": 0,
            "regression_focus": [],
            "prior_findings": [],
            "prior_attack_count": 0,
        }
        for card in projection.cards:
            payload = card.payload or {}
            if payload.get("risk_score") is not None:
                try:
                    context["risk_score"] = int(payload["risk_score"])
                except (TypeError, ValueError):
                    pass
            if isinstance(payload.get("regression_focus"), list):
                context["regression_focus"] = [str(item).strip() for item in payload["regression_focus"] if str(item).strip()]
            if isinstance(payload.get("prior_findings"), list):
                context["prior_findings"] = [str(item).strip() for item in payload["prior_findings"] if str(item).strip()]
            if payload.get("prior_attack_count") is not None:
                try:
                    context["prior_attack_count"] = int(payload["prior_attack_count"])
                except (TypeError, ValueError):
                    pass
            planning_mode = str(payload.get("planning_mode") or "").strip()
            if planning_mode:
                context["planning_mode"] = planning_mode
            if card.card_type == "attack_replan_input":
                context["planning_mode"] = "regression"
        return context

    def _default_action(self, plan_context: dict[str, Any]) -> tuple[str, str]:
        if plan_context["planning_mode"] == "regression":
            return "replan", "重规划回归攻击"
        return "execute", "执行攻击"

    def _normalize_action(self, action: str, *, default_action: str) -> str:
        candidate = str(action or "").strip().lower()
        if candidate in self.DISPATCH_ACTIONS or candidate in self.NON_DISPATCH_ACTIONS:
            return candidate
        return default_action

    def _normalize_action_label(
        self,
        action: str,
        *,
        candidate: str,
        default_label: str,
    ) -> str:
        text = str(candidate or "").strip()
        if text:
            return text
        return self.ACTION_LABELS.get(action, default_label)

    def _normalize_next_step(self, action: str, *, candidate: str) -> str:
        text = str(candidate or "").strip()
        if text:
            return text
        return self.NEXT_STEP_BY_ACTION.get(action, "dispatch_attack")

    def _default_objective(self, plan_context: dict[str, Any]) -> str:
        if plan_context["planning_mode"] == "regression":
            return "围绕补丁后的残余风险、错误处理和接口约束进行回归验证。"
        return "模拟对已部署加密服务的错误处理、接口约束和密钥使用边界进行压力验证。"

    def _default_expected_outcome(self, plan_context: dict[str, Any]) -> str:
        if plan_context["planning_mode"] == "regression":
            return "收集补丁版本的残余风险证据、回归遥测和可复现工件。"
        return "收集沙盒内可复现的攻击工件、流量指标和漏洞证据。"

    def _sanitize_budget(self, budget: dict[str, Any], *, default_budget: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(default_budget)
        if isinstance(budget, dict):
            timeout_s = int(budget.get("timeout_s", normalized["timeout_s"]) or normalized["timeout_s"])
            cpu_cores = int(budget.get("cpu_cores", normalized["cpu_cores"]) or normalized["cpu_cores"])
            memory_mb = int(budget.get("memory_mb", normalized["memory_mb"]) or normalized["memory_mb"])
            normalized["timeout_s"] = min(max(timeout_s, 1), 180)
            normalized["cpu_cores"] = min(max(cpu_cores, 1), 1)
            normalized["memory_mb"] = min(max(memory_mb, 64), 512)
        return normalized

    def _build_system_prompt(self) -> str:
        return (
            "你是 BuildCipher Studio 的攻击规划 Agent。\n"
            "你的职责是基于独立上下文窗口，为受限沙盒中的目标加密服务生成可执行但受控的攻击规划。\n"
            "你只能规划在本地沙盒内执行的验证性攻击，不得生成真实外网入侵、横向移动、提权或破坏性步骤。\n"
            "你必须把决策层与执行层分开：只输出攻击决策与结构化计划，不描述如何绕过沙盒或突破预算。\n"
            "当输入包含补丁信息和上一轮攻击结果时，你应把这次任务视为回归重规划，而不是重新做首轮攻击。\n"
            "允许的 action 只有 execute、continue、replan、handoff_to_vulnerability、stop。\n"
            "当现有 evidence 已足以支撑漏洞评估时，优先使用 handoff_to_vulnerability；当新增攻击没有价值时使用 stop。"
        )

    def _build_user_prompt(
        self,
        projection: ContextProjectionPayload,
        target_service: TargetServiceSpecPayload,
        plan_context: dict[str, Any],
    ) -> str:
        projection_payload = projection.model_dump(mode="json")
        planner_knowledge = self._build_planner_knowledge_context(target_service)
        compact_payload = {
            "objective": projection.objective,
            "plan_context": plan_context,
            "planner_knowledge": planner_knowledge,
            "constraints": projection_payload.get("constraints", []),
            "cards": projection_payload.get("cards", []),
            "artifact_refs": projection_payload.get("artifact_refs", []),
            "evidence_refs": projection_payload.get("evidence_refs", []),
            "target_service": target_service.model_dump(mode="json"),
        }
        return (
            "请根据以下攻击规划投影，生成一份受预算约束的结构化攻击决策。\n"
            "要求：\n"
            "1. action 只能是 execute、continue、replan、handoff_to_vulnerability、stop。\n"
            "2. 首轮默认 action=execute；若输入包含补丁信息与上一轮攻击结果，则优先 action=replan。\n"
            "3. 当 action 为 handoff_to_vulnerability 或 stop 时，attack_specs 可以为空。\n"
            "4. 当 action 为 execute、continue 或 replan 时，attack_specs 数量控制在 1-4 条。\n"
            "5. attack_family 仅可使用 oracle_probe、misuse_case、regression_check。\n"
            "6. budget 必须落在本地沙盒安全预算内。\n"
            "7. 优先利用 planner_knowledge 中的 template_id、skill hints 和 retrieval hints，而不是臆造攻击面。\n"
            "8. 输出中文 rationale / expected_outcome / objective。\n\n"
            f"{json.dumps(compact_payload, ensure_ascii=False, indent=2)}"
        )
