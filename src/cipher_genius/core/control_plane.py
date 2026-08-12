"""Control-plane contracts and summaries for LangGraph MAS orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from cipher_genius.api.schemas import ContextProjectionPayload, MemoryHandoffPayload
from cipher_genius.reporting import display_status


class StageControlContract(BaseModel):
    """Explicit invocation contract for one stage on the control plane."""

    stage: str
    invocation_kind: str = "agent"
    depends_on: list[str] = Field(default_factory=list)
    entry_conditions: list[str] = Field(default_factory=list)
    success_exit_conditions: list[str] = Field(default_factory=list)
    failure_action: str = "halt_run"
    next_stages: list[str] = Field(default_factory=list)
    blocking: bool = True
    terminal: bool = False
    retryable: bool = False
    retry_strategy: str = "no_retry"
    termination_conditions: list[str] = Field(default_factory=list)
    decision_source: str = ""


class WorkflowCheckpoint(BaseModel):
    """Stable checkpoint record for one orchestration stage."""

    checkpoint_id: str
    stage: str
    checkpoint_kind: str = "stage_exit"
    status: str = "completed"
    status_label: str = "已完成"
    summary: str = ""
    order: int = 0
    created_at: datetime | None = None
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    next_stages: list[str] = Field(default_factory=list)
    blocking: bool = True
    retryable: bool = False
    failure_action: str = ""
    termination_signal: str = ""
    decision_source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentInvocationSpec(BaseModel):
    """Minimal invocation descriptor used by the control plane."""

    invocation_id: str
    agent_id: str
    invocation_kind: str = "agent"
    stage: str
    objective: str = ""
    projection_ref: str = ""
    depends_on: list[str] = Field(default_factory=list)
    handoff_ids: list[str] = Field(default_factory=list)
    checkpoint_ref: str = ""
    result_ref: str = ""
    status: str = "completed"
    status_label: str = "已完成"
    blocking: bool = True
    terminal: bool = False
    retryable: bool = False
    retry_strategy: str = "no_retry"
    termination_mode: str = ""
    decision_source: str = ""
    contract: StageControlContract | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResultEnvelope(BaseModel):
    """Compact output envelope emitted by one invocation."""

    result_id: str = ""
    agent_id: str
    stage: str
    status: str = "completed"
    status_label: str = "已完成"
    summary: str = ""
    primary_output_ref: str = ""
    decision_signal: str = ""
    decision_source: str = ""
    termination_signal: str = ""
    failure_action: str = ""
    next_stages: list[str] = Field(default_factory=list)
    emitted_cards: int = 0
    emitted_artifact_refs: int = 0
    emitted_evidence_refs: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentSession(BaseModel):
    """Control-plane snapshot for one LangGraph MAS run."""

    session_id: str
    run_id: str
    case_id: str
    orchestrator: str = "langgraph"
    control_mode: str = "graph-native"
    workflow_trace: list[str] = Field(default_factory=list)
    invocations: list[AgentInvocationSpec] = Field(default_factory=list)
    checkpoints: list[WorkflowCheckpoint] = Field(default_factory=list)
    results: list[AgentResultEnvelope] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class ControlPlaneBuilder:
    """Build an additive control-plane summary from runtime state."""

    CONTRACT_VERSION = "v1"
    STAGE_AGENT_MAP = {
        "analyst": ("requirement_analyst", "agent"),
        "context_builder": ("context_builder", "system_module"),
        "architect": ("generation_agent", "agent"),
        "audit": ("audit_agent", "agent"),
        "engineer": ("code_engineer", "system_module"),
        "target_deployer": ("target_deployer", "system_module"),
        "attack_executor": ("attack_planning_agent", "agent"),
        "vulnerability_evaluation": ("vulnerability_agent", "agent"),
        "patch_reflection": ("patch_agent", "agent"),
        "delivery": ("delivery_aggregator", "system_module"),
    }
    STAGE_DEPENDENCIES = {
        "analyst": ["payload.requirement"],
        "context_builder": ["analyst.parsed_requirement"],
        "architect": ["analyst.parsed_requirement", "evidence_pack"],
        "audit": ["architect.candidates", "audit_projection"],
        "engineer": ["auditor_rounds", "selected_proposal"],
        "target_deployer": ["final_scheme", "delivery.code_artifacts"],
        "attack_executor": ["target_service", "attack_planning_projection"],
        "vulnerability_evaluation": ["attack_results", "vulnerability_projection"],
        "patch_reflection": ["vulnerability_verdict", "patch_projection", "regression_attack_results"],
        "delivery": ["workflow_trace", "attack_loop", "case_memory"],
    }
    STAGE_ENTRY_CONDITIONS = {
        "analyst": ["请求已进入 LangGraph 主线。", "原始需求文本可用。"],
        "context_builder": ["需求解析已完成。", "可开始构建 evidence pack。"],
        "architect": ["evidence pack 已就绪。", "Generation 窗口已构建。"],
        "audit": ["候选方案已生成。", "Audit 窗口已构建。"],
        "engineer": ["审计轮次已完成。", "已选定候选方案。"],
        "target_deployer": ["工程实现建议已生成。", "目标服务模板可物化。"],
        "attack_executor": ["目标服务已具备部署引用。", "攻击规划窗口已构建。"],
        "vulnerability_evaluation": ["攻击结果或 handoff 已形成。", "漏洞评估窗口已构建。"],
        "patch_reflection": ["漏洞裁决已生成。", "补丁/反思窗口已构建。"],
        "delivery": ["主线阶段均已结束。", "可进入最终交付与摘要收口。"],
    }
    STAGE_SUCCESS_EXIT_CONDITIONS = {
        "analyst": ["输出 `analyst.parsed_requirement` 与澄清约束。"],
        "context_builder": ["输出 `evidence_pack`。"],
        "architect": ["输出 `architect.candidates`。"],
        "audit": ["输出 `auditor_rounds` 与审计结论。"],
        "engineer": ["输出工程实现与代码工件状态。"],
        "target_deployer": ["输出 `delivery.attack_loop.target_service`。"],
        "attack_executor": ["输出 `attack_decision`，并形成 dispatch 或 skip 结果。"],
        "vulnerability_evaluation": ["输出 `vulnerability_verdict`。"],
        "patch_reflection": ["输出 `patch_spec / patch_execution / reflection_cards`。"],
        "delivery": ["输出 `final_result` 与 `delivery`。"],
    }
    STAGE_FAILURE_ACTIONS = {
        "analyst": "halt_run",
        "context_builder": "fallback_to_local_retrieval",
        "architect": "fallback_to_candidate_heuristics",
        "audit": "mark_best_effort",
        "engineer": "fallback_to_pseudocode",
        "target_deployer": "emit_deployment_failure",
        "attack_executor": "skip_dispatch_or_handoff",
        "vulnerability_evaluation": "fallback_to_rule_verdict",
        "patch_reflection": "emit_patch_report_with_residual_risk",
        "delivery": "emit_best_effort_delivery",
    }
    STAGE_NEXT_STAGES = {
        "analyst": ["context_builder"],
        "context_builder": ["architect"],
        "architect": ["audit"],
        "audit": ["engineer"],
        "engineer": ["target_deployer"],
        "target_deployer": ["attack_executor"],
        "attack_executor": ["vulnerability_evaluation"],
        "vulnerability_evaluation": ["patch_reflection"],
        "patch_reflection": ["delivery"],
        "delivery": [],
    }
    STAGE_RETRY_POLICIES = {
        "analyst": (False, "no_retry"),
        "context_builder": (True, "retry_then_fallback_to_local_retrieval"),
        "architect": (True, "retry_then_fallback_to_candidate_heuristics"),
        "audit": (True, "retry_then_mark_best_effort"),
        "engineer": (True, "retry_then_fallback_to_pseudocode"),
        "target_deployer": (True, "retry_deployment_then_emit_failure"),
        "attack_executor": (True, "replan_or_handoff_before_skip"),
        "vulnerability_evaluation": (True, "retry_then_fallback_to_rule_verdict"),
        "patch_reflection": (True, "retry_then_emit_patch_report_with_residual_risk"),
        "delivery": (False, "no_retry"),
    }
    STAGE_TERMINATION_CONDITIONS = {
        "analyst": ["当需求缺失或解析失败且无法恢复时终止运行。"],
        "context_builder": ["当 evidence pack 已构建，或本地回退检索已完成时进入下一阶段。"],
        "architect": ["当候选方案已生成，或降级候选启发式已完成时进入审计阶段。"],
        "audit": ["当审计结论形成后进入工程/执行阶段。"],
        "engineer": ["当代码工件或伪代码交付物形成后进入部署阶段。"],
        "target_deployer": ["当目标服务已部署，或部署失败已形成稳定 failure artifact 时结束本阶段。"],
        "attack_executor": ["当规划器给出 execute / handoff_to_vulnerability / stop 之一时结束本阶段。"],
        "vulnerability_evaluation": ["当漏洞裁决形成后进入 patch/reflection。"],
        "patch_reflection": ["当 patch_execution 与 reflection_cards 已收口，或残余风险已显式输出时结束本阶段。"],
        "delivery": ["当最终交付已生成并写回 response 时终止整轮运行。"],
    }
    STAGE_DECISION_SOURCES = {
        "analyst": "analyst.parsed_requirement",
        "context_builder": "evidence_pack.backend",
        "architect": "architect.candidates",
        "audit": "audit_passed",
        "engineer": "delivery.code_artifacts",
        "target_deployer": "baseline_deployment_dispatch.decision",
        "attack_executor": "attack_decision.action",
        "vulnerability_evaluation": "vulnerability_verdict.severity",
        "patch_reflection": "regression_attack_decision.action_or_patch_execution.status",
        "delivery": "delivery_status",
    }
    STAGE_OUTPUT_REFS = {
        "analyst": ["analyst.parsed_requirement", "analyst.clarifications"],
        "context_builder": ["evidence_pack"],
        "architect": ["architect.candidates"],
        "audit": ["auditor_rounds"],
        "engineer": ["engineer.attempts", "delivery.code_artifacts"],
        "target_deployer": [
            "delivery.attack_loop.target_service",
            "delivery.sandbox_dispatcher.baseline_deployment",
        ],
        "attack_executor": [
            "delivery.attack_loop.attack_decision",
            "delivery.attack_loop.attack_specs",
            "delivery.sandbox_dispatcher.baseline_attack",
        ],
        "vulnerability_evaluation": ["delivery.attack_loop.vulnerability_verdict"],
        "patch_reflection": [
            "delivery.attack_loop.patch_spec",
            "delivery.attack_loop.patch_execution",
            "delivery.attack_loop.reflection_cards",
            "delivery.attack_loop.regression_attack_decision",
            "delivery.attack_loop.regression_vulnerability_verdict",
        ],
        "delivery": ["final_result", "delivery", "delivery.backend_architecture"],
    }

    def build(
        self,
        *,
        run_id: str,
        case_id: str,
        workflow_trace: list[str],
        projections: dict[str, ContextProjectionPayload | None],
        memory_handoffs: list[MemoryHandoffPayload],
        runtime_context: dict[str, Any] | None = None,
    ) -> AgentSession:
        """Build a stable control-plane snapshot for the current run."""

        checkpoints: list[WorkflowCheckpoint] = []
        invocations: list[AgentInvocationSpec] = []
        results: list[AgentResultEnvelope] = []
        runtime_context = runtime_context or {}
        handoff_map = self._group_handoffs_by_target(memory_handoffs)
        projection_ref_map = {
            projection.agent_id: f"{projection.agent_id}:{projection.round_id or 'main'}"
            for projection in projections.values()
            if projection is not None
        }

        for order, stage in enumerate(workflow_trace, start=1):
            agent_id, invocation_kind = self.STAGE_AGENT_MAP.get(stage, (stage, "system_module"))
            projection = self._projection_for_stage(stage, projections)
            matched_handoffs = handoff_map.get(agent_id, [])
            contract = self._build_stage_contract(
                stage=stage,
                invocation_kind=invocation_kind,
                runtime_context=runtime_context,
            )
            stage_status = self._resolve_stage_status(stage=stage, runtime_context=runtime_context)
            input_refs = self._build_input_refs(stage=stage, projection=projection)
            output_refs = self._build_output_refs(
                stage=stage,
                projection=projection,
                runtime_context=runtime_context,
            )
            checkpoint = WorkflowCheckpoint(
                checkpoint_id=f"checkpoint-{run_id[:8]}-{order}",
                stage=stage,
                status=stage_status,
                status_label=display_status(stage_status),
                summary=self._build_stage_summary(stage, projection, matched_handoffs),
                order=order,
                created_at=datetime.now(timezone.utc),
                input_refs=input_refs,
                output_refs=output_refs,
                next_stages=list(contract.next_stages),
                blocking=contract.blocking,
                retryable=contract.retryable,
                failure_action=contract.failure_action,
                termination_signal=self._build_stage_termination_signal(
                    stage=stage,
                    runtime_context=runtime_context,
                ),
                decision_source=contract.decision_source,
                metadata={
                    "agent_id": agent_id,
                    "invocation_kind": invocation_kind,
                    **self._build_runtime_metadata(stage=stage, runtime_context=runtime_context),
                },
            )
            checkpoints.append(checkpoint)
            result_id = f"result-{run_id[:8]}-{order}"
            invocations.append(
                AgentInvocationSpec(
                    invocation_id=f"invoke-{run_id[:8]}-{order}",
                    agent_id=agent_id,
                    invocation_kind=invocation_kind,
                    stage=stage,
                    objective=projection.objective if projection is not None else checkpoint.summary,
                    projection_ref=projection_ref_map.get(agent_id, ""),
                    depends_on=list(contract.depends_on),
                    handoff_ids=[item.handoff_id for item in matched_handoffs[:4]],
                    checkpoint_ref=checkpoint.checkpoint_id,
                    result_ref=result_id,
                    status=stage_status,
                    status_label=display_status(stage_status),
                    blocking=contract.blocking,
                    terminal=contract.terminal,
                    retryable=contract.retryable,
                    retry_strategy=contract.retry_strategy,
                    termination_mode=checkpoint.termination_signal,
                    decision_source=contract.decision_source,
                    contract=contract,
                    metadata={
                        "card_count": len(projection.cards) if projection is not None else 0,
                        "artifact_ref_count": len(projection.artifact_refs) if projection is not None else 0,
                        "evidence_ref_count": len(projection.evidence_refs) if projection is not None else 0,
                        **self._build_runtime_metadata(stage=stage, runtime_context=runtime_context),
                    },
                )
            )
            results.append(
                AgentResultEnvelope(
                    result_id=result_id,
                    agent_id=agent_id,
                    stage=stage,
                    status=stage_status,
                    status_label=display_status(stage_status),
                    summary=checkpoint.summary,
                    primary_output_ref=output_refs[0] if output_refs else "",
                    decision_signal=self._build_stage_decision_signal(
                        stage=stage,
                        runtime_context=runtime_context,
                    ),
                    decision_source=contract.decision_source,
                    termination_signal=checkpoint.termination_signal,
                    failure_action=contract.failure_action,
                    next_stages=list(contract.next_stages),
                    emitted_cards=len(projection.cards) if projection is not None else 0,
                    emitted_artifact_refs=len(projection.artifact_refs) if projection is not None else 0,
                    emitted_evidence_refs=len(projection.evidence_refs) if projection is not None else 0,
                    metadata={
                        "handoff_count": len(matched_handoffs),
                        **self._build_runtime_metadata(stage=stage, runtime_context=runtime_context),
                    },
                )
            )

        return AgentSession(
            session_id=f"control-{run_id[:8]}",
            run_id=run_id,
            case_id=case_id,
            workflow_trace=list(workflow_trace),
            invocations=invocations,
            checkpoints=checkpoints,
            results=results,
            summary={
                "contract_version": self.CONTRACT_VERSION,
                "stage_count": len(workflow_trace),
                "agent_invocation_count": sum(1 for item in invocations if item.invocation_kind == "agent"),
                "system_module_invocation_count": sum(
                    1 for item in invocations if item.invocation_kind == "system_module"
                ),
                "blocking_stage_count": sum(1 for item in invocations if item.blocking),
                "terminal_stage_count": sum(1 for item in invocations if item.terminal),
                "retryable_stage_count": sum(1 for item in invocations if item.retryable),
                "handoff_count": len(memory_handoffs),
                "projection_count": sum(1 for item in projections.values() if item is not None),
                "same_run_retry": dict(runtime_context.get("same_run_retry_summary") or {}),
            },
        )

    def _group_handoffs_by_target(
        self,
        memory_handoffs: list[MemoryHandoffPayload],
    ) -> dict[str, list[MemoryHandoffPayload]]:
        grouped: dict[str, list[MemoryHandoffPayload]] = {}
        for item in memory_handoffs:
            key = str(item.to_agent or "unassigned")
            grouped.setdefault(key, []).append(item)
        return grouped

    def _projection_for_stage(
        self,
        stage: str,
        projections: dict[str, ContextProjectionPayload | None],
    ) -> ContextProjectionPayload | None:
        stage_map = {
            "architect": "generation",
            "audit": "audit",
            "attack_executor": "attack_planning",
            "vulnerability_evaluation": "vulnerability_evaluation",
            "patch_reflection": "reflection",
        }
        key = stage_map.get(stage)
        if key is None:
            return None
        return projections.get(key)

    def _build_stage_contract(
        self,
        *,
        stage: str,
        invocation_kind: str,
        runtime_context: dict[str, Any] | None = None,
    ) -> StageControlContract:
        runtime_context = runtime_context or {}
        return StageControlContract(
            stage=stage,
            invocation_kind=invocation_kind,
            depends_on=list(self.STAGE_DEPENDENCIES.get(stage, [])),
            entry_conditions=list(self.STAGE_ENTRY_CONDITIONS.get(stage, [])),
            success_exit_conditions=list(self.STAGE_SUCCESS_EXIT_CONDITIONS.get(stage, [])),
            failure_action=self.STAGE_FAILURE_ACTIONS.get(stage, "halt_run"),
            next_stages=list(self.STAGE_NEXT_STAGES.get(stage, [])),
            blocking=stage != "delivery",
            terminal=stage == "delivery",
            retryable=self.STAGE_RETRY_POLICIES.get(stage, (False, "no_retry"))[0],
            retry_strategy=self.STAGE_RETRY_POLICIES.get(stage, (False, "no_retry"))[1],
            termination_conditions=list(self.STAGE_TERMINATION_CONDITIONS.get(stage, [])),
            decision_source=self._resolve_stage_decision_source(stage=stage, runtime_context=runtime_context),
        )

    def _build_input_refs(
        self,
        *,
        stage: str,
        projection: ContextProjectionPayload | None,
    ) -> list[str]:
        refs = list(self.STAGE_DEPENDENCIES.get(stage, []))
        if projection is not None:
            refs.append(f"projection:{projection.agent_id}:{projection.round_id or 'main'}")
        return refs

    def _build_output_refs(
        self,
        *,
        stage: str,
        projection: ContextProjectionPayload | None,
        runtime_context: dict[str, Any],
    ) -> list[str]:
        if stage == "patch_reflection":
            patch_execution = runtime_context.get("patch_execution")
            regression_dispatch = runtime_context.get("regression_attack_dispatch")
            retry_dispatch = runtime_context.get("retry_attack_dispatch")
            retry_decision = runtime_context.get("retry_attack_decision")
            retry_expert_gate_decision = runtime_context.get("retry_expert_gate_decision")
            expert_gate_decision = runtime_context.get("expert_gate_decision")
            if (
                patch_execution is None
                and regression_dispatch is None
                and retry_dispatch is None
                and retry_expert_gate_decision is None
                and expert_gate_decision is not None
            ):
                refs = [
                    "delivery.attack_loop.expert_gate_decision",
                    "delivery.attack_loop.reflection_cards",
                ]
            else:
                refs = list(self.STAGE_OUTPUT_REFS.get(stage, []))
                if patch_execution is not None or regression_dispatch is not None:
                    refs = list(self.STAGE_OUTPUT_REFS.get(stage, []))
                elif retry_expert_gate_decision is not None:
                    refs = [
                        "delivery.attack_loop.retry_expert_gate_decision",
                        "delivery.attack_loop.reflection_cards",
                    ]
                elif retry_decision is not None:
                    refs = [
                        "delivery.attack_loop.retry_attack_decision",
                        "delivery.attack_loop.retry_vulnerability_verdict",
                        "delivery.attack_loop.reflection_cards",
                    ]
        else:
            refs = list(self.STAGE_OUTPUT_REFS.get(stage, []))
        if projection is not None:
            refs.append(f"projection:{projection.agent_id}:{projection.round_id or 'main'}")
        if stage == "attack_executor":
            decision = runtime_context.get("attack_decision")
            dispatch = runtime_context.get("baseline_attack_dispatch")
            if decision is not None:
                refs.append(f"attack_decision:{decision.decision_id}")
            if dispatch is not None:
                refs.append(f"dispatch:{dispatch.dispatch_id}")
            if runtime_context.get("attack_results"):
                refs.append("delivery.attack_loop.attack_results")
        elif stage == "patch_reflection":
            patch_execution = runtime_context.get("patch_execution")
            regression_dispatch = runtime_context.get("regression_attack_dispatch")
            retry_dispatch = runtime_context.get("retry_attack_dispatch")
            if patch_execution is not None:
                refs.append(f"patch_execution:{patch_execution.execution_id}")
            if regression_dispatch is not None:
                refs.append(f"dispatch:{regression_dispatch.dispatch_id}")
            if retry_dispatch is not None:
                refs.append(f"dispatch:{retry_dispatch.dispatch_id}")
        elif stage == "delivery":
            refs.append("delivery.backend_architecture")
        return refs

    def _resolve_stage_status(
        self,
        *,
        stage: str,
        runtime_context: dict[str, Any],
    ) -> str:
        if stage == "target_deployer":
            dispatch = runtime_context.get("baseline_deployment_dispatch")
            return str(dispatch.status) if dispatch is not None else "completed"
        if stage == "attack_executor":
            dispatch = runtime_context.get("baseline_attack_dispatch")
            return str(dispatch.status) if dispatch is not None else "completed"
        if stage == "patch_reflection":
            patch_execution = runtime_context.get("patch_execution")
            if patch_execution is not None:
                return str(patch_execution.status or "completed")
            dispatch = runtime_context.get("regression_attack_dispatch")
            if dispatch is not None:
                return str(dispatch.status)
            retry_dispatch = runtime_context.get("retry_attack_dispatch")
            if retry_dispatch is not None:
                return str(retry_dispatch.status)
            retry_expert_gate_decision = runtime_context.get("retry_expert_gate_decision")
            if retry_expert_gate_decision is not None:
                return "completed"
            expert_gate_decision = runtime_context.get("expert_gate_decision")
            if expert_gate_decision is not None:
                return "completed"
            return "completed"
        if stage == "delivery":
            return str(runtime_context.get("delivery_status") or "completed")
        return "completed"

    def _build_stage_decision_signal(
        self,
        *,
        stage: str,
        runtime_context: dict[str, Any],
    ) -> str:
        if stage == "audit":
            return "approved" if runtime_context.get("audit_passed") else "best_effort"
        if stage == "target_deployer":
            dispatch = runtime_context.get("baseline_deployment_dispatch")
            return str(dispatch.decision) if dispatch is not None else ""
        if stage == "attack_executor":
            decision = runtime_context.get("attack_decision")
            return str(decision.action) if decision is not None else ""
        if stage == "patch_reflection":
            decision = runtime_context.get("regression_attack_decision")
            if decision is not None:
                return str(decision.action)
            patch_execution = runtime_context.get("patch_execution")
            if patch_execution is not None:
                return str(patch_execution.status)
            retry_expert_gate_decision = runtime_context.get("retry_expert_gate_decision")
            if retry_expert_gate_decision is not None:
                route_target = str(getattr(retry_expert_gate_decision, "route_target", "") or "").strip()
                action = str(getattr(retry_expert_gate_decision, "action", "") or "").strip()
                return route_target or action
            retry_decision = runtime_context.get("retry_attack_decision")
            if retry_decision is not None:
                return str(retry_decision.action)
            expert_gate_decision = runtime_context.get("expert_gate_decision")
            if expert_gate_decision is not None:
                route_target = str(getattr(expert_gate_decision, "route_target", "") or "").strip()
                action = str(getattr(expert_gate_decision, "action", "") or "").strip()
                return route_target or action
            return ""
        if stage == "delivery":
            return str(runtime_context.get("delivery_status") or "")
        return ""

    def _build_stage_termination_signal(
        self,
        *,
        stage: str,
        runtime_context: dict[str, Any],
    ) -> str:
        if stage == "attack_executor":
            decision = runtime_context.get("attack_decision")
            action = str(getattr(decision, "action", "") or "").strip()
            return action or "continue"
        if stage == "patch_reflection":
            decision = runtime_context.get("regression_attack_decision")
            action = str(getattr(decision, "action", "") or "").strip()
            if action:
                return action
            patch_execution = runtime_context.get("patch_execution")
            if patch_execution is not None:
                return str(getattr(patch_execution, "status", "") or "continue")
            retry_expert_gate_decision = runtime_context.get("retry_expert_gate_decision")
            route_target = str(getattr(retry_expert_gate_decision, "route_target", "") or "").strip()
            if route_target:
                return route_target
            action = str(getattr(retry_expert_gate_decision, "action", "") or "").strip()
            if action:
                return action
            retry_decision = runtime_context.get("retry_attack_decision")
            action = str(getattr(retry_decision, "action", "") or "").strip()
            if action:
                return action
            expert_gate_decision = runtime_context.get("expert_gate_decision")
            route_target = str(getattr(expert_gate_decision, "route_target", "") or "").strip()
            if route_target:
                return route_target
            action = str(getattr(expert_gate_decision, "action", "") or "").strip()
            return action or "continue"
        if stage == "delivery":
            return "complete_run"
        if self.STAGE_NEXT_STAGES.get(stage):
            return "advance_next_stage"
        return "complete_stage"

    def _resolve_stage_decision_source(
        self,
        *,
        stage: str,
        runtime_context: dict[str, Any],
    ) -> str:
        if stage != "patch_reflection":
            return self.STAGE_DECISION_SOURCES.get(stage, "")
        if runtime_context.get("regression_attack_decision") is not None:
            return "regression_attack_decision.action_or_patch_execution.status"
        if runtime_context.get("patch_execution") is not None:
            return "patch_execution.status"
        if runtime_context.get("retry_expert_gate_decision") is not None:
            return "retry_expert_gate_decision.route_target"
        if runtime_context.get("retry_attack_decision") is not None:
            return "retry_attack_decision.action_or_retry_vulnerability_verdict.severity"
        if runtime_context.get("expert_gate_decision") is not None:
            return "expert_gate_decision.route_target"
        return self.STAGE_DECISION_SOURCES.get(stage, "")

    def _build_runtime_metadata(
        self,
        *,
        stage: str,
        runtime_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Attach runtime metadata that helps explain retry-policy outcomes."""

        if stage not in {"patch_reflection", "delivery"}:
            return {}
        same_run_retry_summary = dict(runtime_context.get("same_run_retry_summary") or {})
        if not same_run_retry_summary:
            return {}
        return {"same_run_retry": same_run_retry_summary}

    def _build_stage_summary(
        self,
        stage: str,
        projection: ContextProjectionPayload | None,
        handoffs: list[MemoryHandoffPayload],
    ) -> str:
        if projection is not None:
            return (
                f"{stage} 阶段已完成，当前窗口携带 {len(projection.cards)} 张卡片、"
                f"{len(projection.artifact_refs)} 个工件引用，并接收 {len(handoffs)} 个 handoff。"
            )
        return f"{stage} 阶段已完成，当前由控制平面统一收口。"
