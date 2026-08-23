"""LangGraph-powered MAS engine.

This module keeps the public API stable:

- `LangGraphMASService.execute(...)` returns `MASResponse`
- It remains safe to call without LLM API keys because the shared MAS helpers
  still provide fallback parsing / generation paths

Unlike the earlier contract-parity shim, the current implementation uses a
real LangGraph workflow for the main MAS stages while reusing shared runtime
support kept inside `core/`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from cipher_genius.api.schemas import (
    AttackDecisionPayload,
    AttackResultPayload,
    AttackSpecPayload,
    AnalystReportPayload,
    ArchitectReportPayload,
    ArtifactRefPayload,
    AuditorRoundPayload,
    BuildAttemptPayload,
    CaseDecisionPayload,
    CaseMemoryPayload,
    CaseRejectedOptionPayload,
    ContextConstraintPayload,
    ContextProjectionPayload,
    DiscussionTurnPayload,
    EvidenceRefPayload,
    EvidencePackPayload,
    EngineerReportPayload,
    ExpertGateDecisionPayload,
    MASRequest,
    MASResponse,
    MemoryCardPayload,
    MemoryHandoffPayload,
    PatchExecutionPayload,
    PatchSpecPayload,
    ParsedRequirementPayload,
    PatchValidationResultPayload,
    SandboxAuditEventPayload,
    SandboxDispatchResultPayload,
    SandboxPolicyPayload,
    TargetServiceDeploymentManifestPayload,
    TargetServiceRuntimeProfilePayload,
    TargetServiceSpecPayload,
    VulnerabilityVerdictPayload,
)
from cipher_genius.core.artifact_summarizer import ArtifactSummarizer
from cipher_genius.core.context_bus import ContextBusBuilder
from cipher_genius.core.control_plane import ControlPlaneBuilder
from cipher_genius.core.construction_domain import build_construction_context_summary
from cipher_genius.core.mas_runtime_support import MASRuntimeSupport
from cipher_genius.core.safety_notice import SECURITY_DISCLAIMER_TEXT
from cipher_genius.models.requirement import (
    ParsedRequirement,
    PlatformType,
    Requirement,
    ResourceLevel,
    SchemeType,
    SecurityRequirement,
    TargetPlatform,
)
from cipher_genius.models.scheme import CryptographicScheme
from cipher_genius.memory import CaseMemoryService
from cipher_genius.memory import CaseTimelineService
from cipher_genius.retrieval import KnowledgeRetrievalService
from cipher_genius.reporting import (
    display_bool,
    display_scenario,
    display_status,
    localize_compliance_report,
    localize_vulnerability_report,
)
from cipher_genius.sandbox import (
    ExecutionPlaneBuilder,
    LocalSandboxDispatcher,
    LocalSandboxRuntime,
    build_construction_attack_specs,
    build_target_service_for_requirement,
    is_construction_target,
)
from cipher_genius.utils.config import get_settings
from cipher_genius.utils.logger import get_logger
from cipher_genius.utils.redis_client import get_redis_client

logger = get_logger(__name__)
settings = get_settings()

WORKFLOW_TRACE = [
    "analyst",
    "context_builder",
    "architect",
    "audit",
    "engineer",
    "target_deployer",
    "attack_executor",
    "vulnerability_evaluation",
    "patch_reflection",
    "delivery",
]


def _stable_digest(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mas_cache_key(request: MASRequest, memory_signature: str = "") -> str:
    fingerprint = {
        "workflow_version": "langgraph-rag-memory-attackloop-v1",
        "requirement": request.requirement,
        "llm_provider": request.llm_provider,
        "case_id": request.case_id,
        "case_memory": memory_signature,
        "num_variants": request.num_variants,
        "max_audit_rounds": request.max_audit_rounds,
        "max_same_run_retries": request.max_same_run_retries,
        "generate_code": request.generate_code,
        "strict_clarification": request.strict_clarification,
    }
    return f"mas:result:{_stable_digest(fingerprint)[:24]}"


class LangGraphMASState(TypedDict, total=False):
    payload: MASRequest
    run_id: str
    case_id: str
    same_run_retry_budget: int
    discussion_log: list[DiscussionTurnPayload]
    parsed: ParsedRequirement
    structured_spec: dict[str, Any]
    clarifications: list[Any]
    analyst: AnalystReportPayload
    evidence_pack: EvidencePackPayload
    case_memory: CaseMemoryPayload
    needs_clarification: bool
    schemes: list[CryptographicScheme]
    architect: ArchitectReportPayload
    auditor_rounds: list[AuditorRoundPayload]
    selected_index: int
    final_compliance_report: dict[str, Any]
    final_vulnerability_report: dict[str, Any]
    audit_passed: bool
    final_scheme: CryptographicScheme | None
    engineer: EngineerReportPayload
    target_service: TargetServiceSpecPayload
    attack_decision: AttackDecisionPayload
    attack_specs: list[AttackSpecPayload]
    attack_results: list[AttackResultPayload]
    vulnerability_verdict: VulnerabilityVerdictPayload
    expert_gate_decision: ExpertGateDecisionPayload
    patch_spec: PatchSpecPayload
    patch_execution: PatchExecutionPayload
    reflection_cards: list[dict[str, Any]]
    generation_projection: ContextProjectionPayload
    audit_projection: ContextProjectionPayload
    attack_planning_projection: ContextProjectionPayload
    vulnerability_projection: ContextProjectionPayload
    expert_gate_projection: ContextProjectionPayload
    patch_projection: ContextProjectionPayload
    reflection_projection: ContextProjectionPayload
    memory_handoffs: list[MemoryHandoffPayload]
    baseline_deployment_dispatch: SandboxDispatchResultPayload
    baseline_attack_dispatch: SandboxDispatchResultPayload
    patch_apply_dispatch: SandboxDispatchResultPayload
    rollback_dispatch: SandboxDispatchResultPayload
    rollback_execution_dispatch: SandboxDispatchResultPayload
    regression_target_service: TargetServiceSpecPayload
    regression_attack_decision: AttackDecisionPayload
    regression_attack_specs: list[AttackSpecPayload]
    regression_attack_results: list[AttackResultPayload]
    regression_vulnerability_verdict: VulnerabilityVerdictPayload
    regression_deployment_dispatch: SandboxDispatchResultPayload
    regression_attack_dispatch: SandboxDispatchResultPayload
    retry_attack_decision: AttackDecisionPayload
    retry_attack_specs: list[AttackSpecPayload]
    retry_attack_results: list[AttackResultPayload]
    retry_attack_projection: ContextProjectionPayload
    retry_vulnerability_projection: ContextProjectionPayload
    retry_vulnerability_verdict: VulnerabilityVerdictPayload
    retry_attack_dispatch: SandboxDispatchResultPayload
    retry_expert_gate_projection: ContextProjectionPayload
    retry_expert_gate_decision: ExpertGateDecisionPayload
    final_result: MASResponse


class LangGraphMASService:
    """LangGraph MAS engine for the unified mainline execution path."""

    def __init__(self, llm_provider: str | None = None):
        self.llm_provider = llm_provider
        self.redis = get_redis_client()
        self.artifact_summarizer = ArtifactSummarizer()
        self.control_plane_builder = ControlPlaneBuilder()
        self.context_bus_builder = ContextBusBuilder()
        self.execution_plane_builder = ExecutionPlaneBuilder()

    def execute(
        self,
        payload: MASRequest,
        progress_callback: Optional[Callable[[DiscussionTurnPayload], None]] = None,
        request_id: Optional[str] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> MASResponse:
        run_id = request_id or payload.run_id or str(uuid4())
        case_memory_service = CaseMemoryService()
        case_timeline_service = CaseTimelineService()
        case_id = payload.case_id or case_memory_service.build_case_id()
        initial_case_memory = case_memory_service.load_or_create(case_id)
        resolved_same_run_retry_budget = self._resolve_same_run_retry_budget(
            payload.max_same_run_retries
        )
        effective_payload = payload.model_copy(
            update={
                "llm_provider": payload.llm_provider or self.llm_provider,
                "run_id": payload.run_id or run_id,
                "case_id": case_id,
                "max_same_run_retries": resolved_same_run_retry_budget,
            }
        )

        cache_key = _mas_cache_key(
            effective_payload,
            memory_signature=case_memory_service.fingerprint(initial_case_memory),
        )
        if settings.enable_caching and self.redis.is_available():
            cached = self.redis.get_json(cache_key)
            if cached:
                logger.info(f"[{run_id}] LangGraph MAS cache HIT")
                try:
                    parsed = MASResponse.model_validate(cached)
                    now = datetime.now(timezone.utc)
                    delivery = {
                        **(parsed.delivery or {}),
                        "engine": "langgraph",
                        "engine_mode": "graph-native",
                        "cache_hit": True,
                        "workflow_trace": WORKFLOW_TRACE,
                    }
                    return parsed.model_copy(
                        update={
                            "request_id": run_id,
                            "run_id": run_id,
                            "case_id": case_id,
                            "generated_at": now,
                            "delivery": delivery,
                        }
                    )
                except Exception as exc:
                    logger.warning(f"[{run_id}] Ignoring invalid cached MASResponse: {exc}")

        service = MASRuntimeSupport(effective_payload.llm_provider)
        retrieval_service = KnowledgeRetrievalService()
        sandbox_runtime = LocalSandboxRuntime()
        sandbox_dispatcher = LocalSandboxDispatcher(runtime=sandbox_runtime)
        workflow = self._build_workflow(
            service=service,
            retrieval_service=retrieval_service,
            case_memory_service=case_memory_service,
            case_timeline_service=case_timeline_service,
            sandbox_dispatcher=sandbox_dispatcher,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )

        logger.info(f"[{run_id}] LangGraph MAS executing graph-native staged workflow")
        state = workflow.invoke(
            {
                "payload": effective_payload,
                "run_id": run_id,
                "case_id": case_id,
                "same_run_retry_budget": resolved_same_run_retry_budget,
                "discussion_log": [],
                "case_memory": initial_case_memory,
            }
        )
        result = state["final_result"].model_copy(
            update={
                "request_id": run_id,
                "run_id": run_id,
                "case_id": case_id,
                "delivery": {
                    **(state["final_result"].delivery or {}),
                    "engine": "langgraph",
                    "engine_mode": "graph-native",
                    "cache_hit": False,
                },
            }
        )

        if settings.enable_caching and self.redis.is_available():
            ttl = int(getattr(settings, "redis_cache_ttl", 3600) or 3600)
            self.redis.set_json(cache_key, result.model_dump(mode="json"), ttl=ttl)

        return result

    def _build_workflow(
        self,
        *,
        service: MASRuntimeSupport,
        retrieval_service: KnowledgeRetrievalService,
        case_memory_service: CaseMemoryService,
        case_timeline_service: CaseTimelineService,
        sandbox_dispatcher: LocalSandboxDispatcher,
        progress_callback: Optional[Callable[[DiscussionTurnPayload], None]],
        cancel_check: Optional[Callable[[], bool]],
    ):
        def analyst_node(state: LangGraphMASState) -> LangGraphMASState:
            payload = state["payload"]
            discussion_log = list(state.get("discussion_log") or [])
            case_memory = state.get("case_memory") or case_memory_service.create_empty(state["case_id"])
            service._raise_if_cancelled(cancel_check)

            parsed = service._parse_requirement(
                payload.requirement,
                discussion_log,
                progress_callback=progress_callback,
            )
            structured_spec = service._build_structured_spec(parsed.requirement, payload.requirement)
            clarifications = service._build_clarifications(payload.requirement, structured_spec)
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
                case_context=self._build_case_context(case_memory),
            )

            return {
                "discussion_log": discussion_log,
                "parsed": parsed,
                "structured_spec": structured_spec,
                "clarifications": clarifications,
                "analyst": analyst,
                "case_memory": case_memory,
                "needs_clarification": bool(
                    payload.strict_clarification and any(item.required for item in clarifications)
                ),
            }

        def clarification_gate_node(state: LangGraphMASState) -> LangGraphMASState:
            discussion_log = list(state.get("discussion_log") or [])
            case_memory = self._persist_case_memory(
                case_memory_service,
                state=state,
                status="needs_clarification",
                selected_proposal=None,
                compliance_score=None,
                risk_score=None,
            )
            service._raise_if_cancelled(cancel_check)
            service._log(
                discussion_log,
                actor="Supervisor",
                phase="analyst_gate",
                status="halted",
                message="发现阻断性澄清问题，严格模式已停止执行。",
                progress_callback=progress_callback,
            )

            result = MASResponse(
                request_id=state["run_id"],
                run_id=state["run_id"],
                case_id=state["case_id"],
                generated_at=datetime.now(timezone.utc),
                security_disclaimer=SECURITY_DISCLAIMER_TEXT,
                analyst=state["analyst"],
                evidence_pack=EvidencePackPayload(),
                architect=ArchitectReportPayload(toolbox_services=service.TOOLBOX_SERVICES, candidates=[]),
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
                case_memory=case_memory,
                delivery={
                    "status": "needs_clarification",
                    "status_label": display_status("needs_clarification"),
                    "engine_mode": "graph-native",
                    "case_memory_summary": self._build_case_memory_summary(case_memory),
                    "context_projections": {},
                    "memory_handoffs": [],
                },
            )
            return {
                "discussion_log": discussion_log,
                "case_memory": case_memory,
                "final_result": result,
            }

        def context_builder_node(state: LangGraphMASState) -> LangGraphMASState:
            payload = state["payload"]
            structured_spec = state["structured_spec"]
            discussion_log = list(state.get("discussion_log") or [])
            service._raise_if_cancelled(cancel_check)

            evidence_pack = retrieval_service.retrieve(
                payload.requirement,
                structured_spec=structured_spec,
            )
            top_titles = [item.title for item in evidence_pack.items[:3]]
            service._log(
                discussion_log,
                actor="Supervisor",
                phase="context_builder",
                status="done",
                message=(
                    f"已构建证据包，命中 {len(evidence_pack.items)} 条企业知识依据。"
                    if evidence_pack.items
                    else "未命中高相关证据，已继续使用本地规则与候选生成。"
                ),
                data={
                    "backend": evidence_pack.backend,
                    "retrieval_mode": evidence_pack.retrieval_mode,
                    "top_titles": top_titles,
                },
                progress_callback=progress_callback,
            )
            return {
                "discussion_log": discussion_log,
                "evidence_pack": evidence_pack,
            }

        def architect_node(state: LangGraphMASState) -> LangGraphMASState:
            payload = state["payload"]
            analyst = state["analyst"]
            discussion_log = list(state.get("discussion_log") or [])
            memory_handoffs = list(state.get("memory_handoffs") or [])
            service._raise_if_cancelled(cancel_check)
            generation_projection = self._build_generation_projection(state=state)
            fallback_requirement = self._restore_requirement_from_analyst(
                analyst,
                raw_requirement=payload.requirement,
            )
            generation_requirement, generation_structured_spec, parser_confidence = (
                self._extract_generation_runtime_inputs(
                    generation_projection,
                    fallback_requirement=fallback_requirement,
                    fallback_structured_spec=analyst.structured_spec,
                    fallback_parser_confidence=analyst.parsed_requirement.confidence,
                )
            )

            schemes = service._generate_schemes(
                generation_requirement,
                payload.num_variants,
                discussion_log,
                structured_spec=generation_structured_spec,
                generation_projection=generation_projection,
                case_memory=(state["case_memory"].model_dump(mode="json") if state.get("case_memory") else None),
                progress_callback=progress_callback,
            )
            architect = ArchitectReportPayload(
                toolbox_services=service.TOOLBOX_SERVICES,
                candidates=service._build_architect_candidates(
                    schemes,
                    generation_requirement,
                    parser_confidence=parser_confidence,
                ),
                evidence_pack=state.get("evidence_pack") or EvidencePackPayload(),
            )
            memory_handoffs.append(
                self._build_memory_handoff(
                    handoff_id=f"handoff-{state['run_id'][:8]}-generation",
                    from_agent="context_builder",
                    to_agent="generation_agent",
                    objective="将需求约束、企业证据与项目级记忆投影到生成 Agent 的独立窗口。",
                    projection=generation_projection,
                )
            )
            return {
                "discussion_log": discussion_log,
                "schemes": schemes,
                "architect": architect,
                "generation_projection": generation_projection,
                "memory_handoffs": memory_handoffs,
            }

        def audit_node(state: LangGraphMASState) -> LangGraphMASState:
            payload = state["payload"]
            discussion_log = list(state.get("discussion_log") or [])
            memory_handoffs = list(state.get("memory_handoffs") or [])
            base_audit_projection = self._build_audit_projection(state=state)
            schemes, structured_spec, proposal_ids = self._extract_audit_runtime_inputs(
                base_audit_projection,
                fallback_schemes=list(state.get("schemes") or []),
                fallback_structured_spec=state["structured_spec"],
            )
            audit_guidance = service._build_runtime_audit_guidance(base_audit_projection)
            memory_handoffs.append(
                self._build_memory_handoff(
                    handoff_id=f"handoff-{state['run_id'][:8]}-audit",
                    from_agent="generation_agent",
                    to_agent="audit_agent",
                    objective="将候选方案摘要、证据引用和项目约束投影到审计 Agent 的独立窗口。",
                    projection=base_audit_projection,
                )
            )

            audit_projection = base_audit_projection
            auditor_rounds: list[AuditorRoundPayload] = []
            selected_index = 0
            final_compliance_report: dict[str, Any] = {}
            final_vulnerability_report: dict[str, Any] = {}
            hardened_once = False
            audit_passed = False

            for round_idx in range(1, payload.max_audit_rounds + 1):
                service._raise_if_cancelled(cancel_check)
                if not schemes:
                    break

                selected_index = min(selected_index, len(schemes) - 1)
                scheme = schemes[selected_index]
                proposal_id = (
                    proposal_ids[selected_index]
                    if selected_index < len(proposal_ids)
                    else f"proposal-{selected_index + 1}"
                )

                audit_input = service._scheme_to_audit_input(scheme)
                standards = service._select_standards(structured_spec)
                vulnerability_report = service.vulnerability_scanner.scan_scheme(audit_input)
                compliance_report = service.compliance_reporter.generate_report(audit_input, standards)
                quantum_eval = service.security_assessor._assess_quantum_readiness(
                    audit_input.get("quantum_assessment_input", audit_input.get("algorithm", ""))
                )
                quantum_required = bool(structured_spec.get("quantum_safe"))
                tool_findings = service._collect_findings(vulnerability_report, compliance_report)
                tool_recommendations = service._collect_recommendations(
                    compliance_report,
                    vulnerability_report,
                )
                audit_projection = self._build_audit_decision_projection(
                    state=state,
                    base_projection=base_audit_projection,
                    scheme=scheme,
                    proposal_id=proposal_id,
                    round_idx=round_idx,
                    audit_input=audit_input,
                    standards=standards,
                    vulnerability_report=vulnerability_report,
                    compliance_report=compliance_report,
                    quantum_eval=quantum_eval,
                    quantum_required=quantum_required,
                    tool_findings=tool_findings,
                    tool_recommendations=tool_recommendations,
                )
                audit_round = service._evaluate_audit_from_projection(
                    audit_projection,
                    run_id=state["run_id"],
                )
                reasons, key_findings, recommended_changes = (
                    service._augment_audit_results_with_runtime_guidance(
                        reasons=list(audit_round.reasons or []),
                        key_findings=list(audit_round.key_findings or []),
                        recommended_changes=list(audit_round.recommended_changes or []),
                        audit_guidance=audit_guidance,
                    )
                )
                audit_round = audit_round.model_copy(
                    update={
                        "reasons": reasons,
                        "key_findings": key_findings,
                        "recommended_changes": recommended_changes,
                    }
                )

                verdict = audit_round.verdict
                auditor_rounds.append(audit_round)

                final_compliance_report = compliance_report
                final_vulnerability_report = vulnerability_report

                service._log(
                    discussion_log,
                    actor="Security & Compliance Auditor",
                    phase="audit",
                    status=verdict,
                    message=(
                        f"{proposal_id} 审计完成，合规得分 {audit_round.compliance_score:.1f}，"
                        f"风险得分 {audit_round.risk_score}。"
                    ),
                    data={
                        "reasons": reasons[:3],
                        "audit_focus": list((audit_guidance or {}).get("audit_focus") or [])[:2],
                    },
                    progress_callback=progress_callback,
                )

                if verdict == "pass":
                    audit_passed = True
                    break

                if selected_index < len(schemes) - 1:
                    selected_index += 1
                    service._log(
                        discussion_log,
                        actor="Architect",
                        phase="revise",
                        status="retry",
                        message=(
                            f"当前提案被拒绝，切换到 "
                            f"{proposal_ids[selected_index] if selected_index < len(proposal_ids) else f'proposal-{selected_index + 1}'}。"
                        ),
                        progress_callback=progress_callback,
                    )
                    continue

                if not hardened_once:
                    schemes[selected_index] = service._harden_scheme(schemes[selected_index], quantum_required)
                    hardened_once = True
                    service._log(
                        discussion_log,
                        actor="Architect",
                        phase="revise",
                        status="hardened",
                        message=f"已对 proposal-{selected_index + 1} 应用加固措施。",
                        progress_callback=progress_callback,
                    )
                    continue

                break

            return {
                "discussion_log": discussion_log,
                "schemes": schemes,
                "auditor_rounds": auditor_rounds,
                "selected_index": selected_index,
                "final_compliance_report": final_compliance_report,
                "final_vulnerability_report": final_vulnerability_report,
                "audit_passed": audit_passed,
                "audit_projection": audit_projection,
                "memory_handoffs": memory_handoffs,
            }

        def engineer_node(state: LangGraphMASState) -> LangGraphMASState:
            payload = state["payload"]
            discussion_log = list(state.get("discussion_log") or [])
            schemes = list(state.get("schemes") or [])
            selected_index = min(int(state.get("selected_index", 0)), max(len(schemes) - 1, 0))
            final_scheme = schemes[selected_index] if schemes else None

            service._raise_if_cancelled(cancel_check)
            engineer = service._run_engineer(
                final_scheme,
                payload.generate_code,
                discussion_log,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )
            return {
                "discussion_log": discussion_log,
                "final_scheme": final_scheme,
                "engineer": engineer,
            }

        def target_deployer_node(state: LangGraphMASState) -> LangGraphMASState:
            discussion_log = list(state.get("discussion_log") or [])
            final_scheme = state.get("final_scheme")
            engineer = state.get("engineer") or EngineerReportPayload(sandbox_backend="local-sandbox")
            service._raise_if_cancelled(cancel_check)

            target_service = self._build_target_service_spec(
                run_id=state["run_id"],
                final_scheme=final_scheme,
                engineer=engineer,
                structured_spec=state.get("structured_spec") or {},
                requirement_text=state["payload"].requirement,
            )
            target_service, deployment, baseline_deployment_dispatch = (
                sandbox_dispatcher.dispatch_target_deployment(
                run_id=state["run_id"],
                round_id="baseline",
                target_service=target_service,
                engineer=engineer,
                final_scheme=final_scheme,
                )
            )
            service._log(
                discussion_log,
                actor="Code Engineer",
                phase="target_deployer",
                status="deployed",
                message=f"已为 {target_service.service_name} 生成本地沙盒部署工件。",
                data={
                    "service_id": target_service.service_id,
                    "service_version": target_service.service_version,
                    "runtime": target_service.runtime,
                    "workspace": str(deployment.workspace).replace("\\", "/"),
                    "dispatch_id": baseline_deployment_dispatch.dispatch_id,
                },
                progress_callback=progress_callback,
            )
            return {
                "discussion_log": discussion_log,
                "target_service": target_service,
                "baseline_deployment_dispatch": baseline_deployment_dispatch,
            }

        def attack_executor_node(state: LangGraphMASState) -> LangGraphMASState:
            discussion_log = list(state.get("discussion_log") or [])
            memory_handoffs = list(state.get("memory_handoffs") or [])
            final_vulnerability_report = state.get("final_vulnerability_report") or {}
            service._raise_if_cancelled(cancel_check)
            auditor_rounds = list(state.get("auditor_rounds") or [])
            latest_round = auditor_rounds[-1] if auditor_rounds else None
            attack_planning_evidence_pack = self._retrieve_attack_planning_evidence(
                retrieval_service=retrieval_service,
                state=state,
                target_service=state["target_service"],
                planning_mode="baseline",
                prior_findings=(
                    list((latest_round.key_findings or [])[:4]) + list((latest_round.reasons or [])[:2])
                    if latest_round
                    else []
                ),
            )

            attack_planning_input_projection = self._build_attack_planning_projection(
                state=state,
                evidence_pack_override=attack_planning_evidence_pack,
            )
            memory_handoffs.append(
                self._build_memory_handoff(
                    handoff_id=f"handoff-{state['run_id'][:8]}-attack-planning",
                    from_agent="audit_agent",
                    to_agent="attack_planning_agent",
                    objective="将审计结论、攻击面与预算约束投影到攻击规划 Agent 的独立窗口。",
                    projection=attack_planning_input_projection,
                )
            )
            attack_decision, planned_attack_specs = service._plan_attack_from_projection(
                attack_planning_input_projection,
                run_id=state["run_id"],
            )
            attack_decision, planned_attack_specs = self._resolve_domain_attack_plan(
                run_id=state["run_id"],
                target_service=state["target_service"],
                attack_decision=attack_decision,
                attack_specs=planned_attack_specs,
            )
            attack_planning_projection = self._build_attack_planning_projection(
                state=state,
                attack_specs=planned_attack_specs,
                attack_decision=attack_decision,
                evidence_pack_override=attack_planning_evidence_pack,
            )
            target_service = self._extract_target_service_from_projection(
                attack_planning_projection,
                fallback=state.get("target_service"),
            )
            attack_specs = self._extract_attack_specs_from_projection(
                attack_planning_projection,
                fallback=planned_attack_specs,
            )
            if self._should_dispatch_attack(attack_decision):
                baseline_telemetry_callback = self._build_attack_telemetry_callback(
                    service=service,
                    discussion_log=discussion_log,
                    progress_callback=progress_callback,
                    round_kind="baseline",
                )
                attack_results, baseline_attack_dispatch = sandbox_dispatcher.dispatch_attack_execution(
                    run_id=state["run_id"],
                    round_id="baseline",
                    target_service=target_service,
                    attack_specs=attack_specs,
                    vulnerability_report=final_vulnerability_report,
                    telemetry_callback=baseline_telemetry_callback,
                )
                service._log(
                    discussion_log,
                    actor="Security & Compliance Auditor",
                    phase="attack_executor",
                    status="executed",
                    message=f"已在本地文件沙盒执行 {len(attack_specs)} 条针对目标服务的攻击任务。",
                    data={
                        "target_service_ref": target_service.service_id,
                        "dispatch_id": baseline_attack_dispatch.dispatch_id,
                    },
                    progress_callback=progress_callback,
                )
            else:
                attack_results = []
                baseline_attack_dispatch = self._build_non_executed_attack_dispatch(
                    run_id=state["run_id"],
                    round_id="baseline",
                    target_service=target_service,
                    attack_decision=attack_decision,
                    attack_specs=attack_specs,
                )
                service._log(
                    discussion_log,
                    actor="Security & Compliance Auditor",
                    phase="attack_executor",
                    status="skipped",
                    message=self._build_non_executed_attack_message(
                        attack_decision=attack_decision,
                        round_kind="baseline",
                    ),
                    data={
                        "target_service_ref": target_service.service_id,
                        "dispatch_id": baseline_attack_dispatch.dispatch_id,
                        "planner_action": attack_decision.action,
                    },
                    progress_callback=progress_callback,
                )
            return {
                "discussion_log": discussion_log,
                "attack_decision": attack_decision,
                "attack_specs": attack_specs,
                "attack_results": attack_results,
                "attack_planning_projection": attack_planning_projection,
                "memory_handoffs": memory_handoffs,
                "baseline_attack_dispatch": baseline_attack_dispatch,
            }

        def vulnerability_evaluation_node(state: LangGraphMASState) -> LangGraphMASState:
            discussion_log = list(state.get("discussion_log") or [])
            memory_handoffs = list(state.get("memory_handoffs") or [])
            service._raise_if_cancelled(cancel_check)

            vulnerability_projection = self._build_vulnerability_projection(state=state)
            memory_handoffs.append(
                self._build_memory_handoff(
                    handoff_id=f"handoff-{state['run_id'][:8]}-vulnerability",
                    from_agent="attack_planning_agent",
                    to_agent="vulnerability_agent",
                    objective="将攻击执行结果与原始漏洞报告投影到漏洞评估 Agent 的独立窗口。",
                    projection=vulnerability_projection,
                )
            )
            target_service = self._extract_target_service_from_projection(
                vulnerability_projection,
                fallback=state.get("target_service"),
            )
            attack_results = self._extract_attack_results_from_projection(
                vulnerability_projection,
                fallback=list(state.get("attack_results") or []),
            )
            final_vulnerability_report = self._extract_vulnerability_report_from_projection(
                vulnerability_projection,
                fallback=state.get("final_vulnerability_report") or {},
            )
            verdict = service._evaluate_vulnerability_from_projection(
                vulnerability_projection,
                run_id=state["run_id"],
            )
            service._log(
                discussion_log,
                actor="Security & Compliance Auditor",
                phase="vulnerability_evaluation",
                status=verdict.severity,
                message=f"已完成漏洞评估，当前严重度：{verdict.severity_label}。",
                data={"target_service_ref": target_service.service_id},
                progress_callback=progress_callback,
            )
            return {
                "discussion_log": discussion_log,
                "vulnerability_verdict": verdict,
                "vulnerability_projection": vulnerability_projection,
                "memory_handoffs": memory_handoffs,
            }

        def patch_reflection_node(state: LangGraphMASState) -> LangGraphMASState:
            discussion_log = list(state.get("discussion_log") or [])
            memory_handoffs = list(state.get("memory_handoffs") or [])
            final_scheme = state.get("final_scheme")
            engineer = state.get("engineer") or EngineerReportPayload(sandbox_backend="local-sandbox")
            final_vulnerability_report = state.get("final_vulnerability_report") or {}
            same_run_retry_budget = int(state.get("same_run_retry_budget") or 0)
            service._raise_if_cancelled(cancel_check)

            expert_gate_projection = self._build_expert_gate_projection(state=state)
            memory_handoffs.append(
                self._build_memory_handoff(
                    handoff_id=f"handoff-{state['run_id'][:8]}-expert-gate",
                    from_agent="vulnerability_agent",
                    to_agent="expert_gate_agent",
                    objective="将漏洞裁决、攻击工件与审计整改建议投影到 Expert Gate Agent 的独立窗口。",
                    projection=expert_gate_projection,
                )
            )
            expert_gate_decision = service._decide_expert_gate_from_projection(
                expert_gate_projection,
                run_id=state["run_id"],
            )
            service._log(
                discussion_log,
                actor="Security & Compliance Auditor",
                phase="patch_reflection",
                status=expert_gate_decision.action,
                message=f"专家闸门已完成裁决，下一步动作：{expert_gate_decision.action_label}。",
                data={"target_service_ref": expert_gate_decision.target_service_ref},
                progress_callback=progress_callback,
            )
            target_service = state["target_service"]
            verdict = state["vulnerability_verdict"]
            attack_results_for_patch = list(state.get("attack_results") or [])
            attack_decision_for_regression = state.get("attack_decision")
            patch_entry_gate_decision = expert_gate_decision
            retry_attack_decision = None
            retry_attack_specs = []
            retry_attack_results = []
            retry_attack_projection = None
            retry_vulnerability_projection = None
            retry_vulnerability_verdict = None
            retry_attack_dispatch = None
            retry_expert_gate_projection = None
            retry_expert_gate_decision = None
            if not self._should_run_patch_flow(expert_gate_decision):
                if self._should_run_retry_follow_up(
                    expert_gate_decision,
                    remaining_budget=same_run_retry_budget,
                ):
                    retry_attack_projection = self._build_retry_attack_planning_projection(
                        state=state,
                        target_service=target_service,
                        expert_gate_decision=expert_gate_decision,
                        baseline_verdict=verdict,
                        evidence_pack_override=self._retrieve_attack_planning_evidence(
                            retrieval_service=retrieval_service,
                            state=state,
                            target_service=target_service,
                            planning_mode="retry",
                            prior_findings=[
                                finding
                                for item in list(state.get("attack_results") or [])[:3]
                                for finding in item.findings[:2]
                            ][:6],
                            regression_focus=list(expert_gate_decision.follow_up_actions or [])[:4],
                        ),
                    )
                    memory_handoffs.append(
                        self._build_memory_handoff(
                            handoff_id=f"handoff-{state['run_id'][:8]}-attack-retry",
                            from_agent="expert_gate_agent",
                            to_agent="attack_planning_agent",
                            objective="将专家闸门的补充验证建议投影到 Attack Planning Agent，执行同轮补充攻击重规划。",
                            projection=retry_attack_projection,
                        )
                    )
                    retry_attack_decision, retry_attack_specs = service._plan_attack_from_projection(
                        retry_attack_projection,
                        run_id=f"{state['run_id']}-retry",
                    )
                    retry_attack_decision = retry_attack_decision.model_copy(
                        update={"decision_id": f"{expert_gate_decision.decision_id}-retry-decision"}
                    )
                    retry_attack_specs = [
                        spec.model_copy(
                            update={"attack_id": f"{expert_gate_decision.decision_id}-retry-{index}"}
                        )
                        for index, spec in enumerate(retry_attack_specs, start=1)
                    ]
                    retry_attack_decision, retry_attack_specs = self._resolve_domain_attack_plan(
                        run_id=f"{state['run_id']}-retry",
                        target_service=target_service,
                        attack_decision=retry_attack_decision,
                        attack_specs=retry_attack_specs,
                    )
                    if self._should_dispatch_attack(retry_attack_decision):
                        retry_telemetry_callback = self._build_attack_telemetry_callback(
                            service=service,
                            discussion_log=discussion_log,
                            progress_callback=progress_callback,
                            round_kind="retry",
                        )
                        retry_attack_results, retry_attack_dispatch = sandbox_dispatcher.dispatch_attack_execution(
                            run_id=state["run_id"],
                            round_id="retry",
                            target_service=target_service,
                            attack_specs=retry_attack_specs,
                            vulnerability_report=final_vulnerability_report,
                            telemetry_callback=retry_telemetry_callback,
                        )
                    else:
                        retry_attack_results = []
                        retry_attack_dispatch = self._build_non_executed_attack_dispatch(
                            run_id=state["run_id"],
                            round_id="retry",
                            target_service=target_service,
                            attack_decision=retry_attack_decision,
                            attack_specs=retry_attack_specs,
                        )
                    retry_vulnerability_projection = self._build_retry_vulnerability_projection(
                        state=state,
                        target_service=target_service,
                        attack_decision=retry_attack_decision,
                        attack_results=retry_attack_results,
                        vulnerability_report=final_vulnerability_report,
                        baseline_verdict=verdict,
                        expert_gate_decision=expert_gate_decision,
                    )
                    memory_handoffs.append(
                        self._build_memory_handoff(
                            handoff_id=f"handoff-{state['run_id'][:8]}-vulnerability-retry",
                            from_agent="attack_planning_agent",
                            to_agent="vulnerability_agent",
                            objective="将补充攻击结果投影到漏洞评估 Agent，完成同轮补充验证裁决。",
                            projection=retry_vulnerability_projection,
                        )
                    )
                    retry_vulnerability_verdict = service._evaluate_vulnerability_from_projection(
                        retry_vulnerability_projection,
                        run_id=f"{state['run_id']}-retry",
                    )
                    if retry_attack_results:
                        service._log(
                            discussion_log,
                            actor="Security & Compliance Auditor",
                            phase="attack_executor",
                            status="executed",
                            message=f"已按专家闸门建议执行 {len(retry_attack_specs)} 条补充攻击任务。",
                            data={
                                "target_service_ref": target_service.service_id,
                                "dispatch_id": retry_attack_dispatch.dispatch_id,
                            },
                            progress_callback=progress_callback,
                        )
                    else:
                        service._log(
                            discussion_log,
                            actor="Security & Compliance Auditor",
                            phase="attack_executor",
                            status="skipped",
                            message=self._build_non_executed_attack_message(
                                attack_decision=retry_attack_decision,
                                round_kind="retry",
                            ),
                            data={
                                "target_service_ref": target_service.service_id,
                                "dispatch_id": retry_attack_dispatch.dispatch_id,
                                "planner_action": retry_attack_decision.action,
                            },
                            progress_callback=progress_callback,
                        )
                    service._log(
                        discussion_log,
                        actor="Security & Compliance Auditor",
                        phase="vulnerability_evaluation",
                        status=retry_vulnerability_verdict.severity,
                        message=f"已完成同轮补充验证裁决，当前严重度：{retry_vulnerability_verdict.severity_label}。",
                            data={"target_service_ref": target_service.service_id},
                            progress_callback=progress_callback,
                        )
                    retry_expert_gate_projection = self._build_retry_expert_gate_projection(
                        state=state,
                        target_service=target_service,
                        retry_attack_decision=retry_attack_decision,
                        retry_attack_results=retry_attack_results,
                        retry_vulnerability_verdict=retry_vulnerability_verdict,
                        prior_expert_gate_decision=expert_gate_decision,
                    )
                    memory_handoffs.append(
                        self._build_memory_handoff(
                            handoff_id=f"handoff-{state['run_id'][:8]}-expert-gate-retry",
                            from_agent="vulnerability_agent",
                            to_agent="expert_gate_agent",
                            objective="将补充攻击后的漏洞裁决重新投影到 Expert Gate Agent，执行有限 re-gate 二次裁决。",
                            projection=retry_expert_gate_projection,
                        )
                    )
                    retry_expert_gate_decision = service._decide_expert_gate_from_projection(
                        retry_expert_gate_projection,
                        run_id=f"{state['run_id']}-retry-gate",
                    )
                    service._log(
                        discussion_log,
                        actor="Security & Compliance Auditor",
                        phase="patch_reflection",
                        status=retry_expert_gate_decision.action,
                        message=(
                            "同轮补充攻击后的二次专家闸门已完成裁决，"
                            f"下一步动作：{retry_expert_gate_decision.action_label}。"
                        ),
                        data={"target_service_ref": retry_expert_gate_decision.target_service_ref},
                        progress_callback=progress_callback,
                    )
                    if not self._should_run_patch_flow(retry_expert_gate_decision):
                        capped_retry = self._is_retry_follow_up_capped(
                            retry_expert_gate_decision,
                            remaining_budget=same_run_retry_budget - 1,
                        )
                        reflection_projection = self._build_retry_follow_up_reflection_projection(
                            state=state,
                            target_service=target_service,
                            expert_gate_decision=retry_expert_gate_decision,
                            retry_attack_decision=retry_attack_decision,
                            retry_attack_results=retry_attack_results,
                            retry_vulnerability_verdict=retry_vulnerability_verdict,
                            capped_retry=capped_retry,
                        )
                        memory_handoffs.append(
                            self._build_memory_handoff(
                                handoff_id=f"handoff-{state['run_id'][:8]}-reflection-retry",
                                from_agent="vulnerability_agent",
                                to_agent="reflection_agent",
                                objective="将同轮补充攻击、二次专家闸门裁决与补充漏洞裁决结果沉淀为下一轮优化卡片。",
                                projection=reflection_projection,
                            )
                        )
                        reflection_cards = service._reflect_from_projection(
                            reflection_projection,
                            run_id=state["run_id"],
                            fallback_workspace=str(target_service.artifact_id or ""),
                        )
                        follow_up_message = (
                            "二次专家闸门仍建议继续补充攻击，但当前 same-run re-gate 已达到上限，已先沉淀 follow-up reflection cards。"
                            if capped_retry
                            else "二次专家闸门已完成非 patch 收口，并沉淀 follow-up reflection cards。"
                        )
                        service._log(
                            discussion_log,
                            actor="Supervisor",
                            phase="patch_reflection",
                            status="completed",
                            message=follow_up_message,
                            data={
                                "route_target": retry_expert_gate_decision.route_target,
                                "retry_dispatch_id": retry_attack_dispatch.dispatch_id,
                            },
                            progress_callback=progress_callback,
                        )
                        return {
                            "discussion_log": discussion_log,
                            "expert_gate_projection": expert_gate_projection,
                            "expert_gate_decision": expert_gate_decision,
                            "retry_expert_gate_projection": retry_expert_gate_projection,
                            "retry_expert_gate_decision": retry_expert_gate_decision,
                            "reflection_projection": reflection_projection,
                            "reflection_cards": reflection_cards,
                            "retry_attack_projection": retry_attack_projection,
                            "retry_attack_decision": retry_attack_decision,
                            "retry_attack_specs": retry_attack_specs,
                            "retry_attack_results": retry_attack_results,
                            "retry_vulnerability_projection": retry_vulnerability_projection,
                            "retry_vulnerability_verdict": retry_vulnerability_verdict,
                            "retry_attack_dispatch": retry_attack_dispatch,
                            "memory_handoffs": memory_handoffs,
                        }
                    patch_entry_gate_decision = retry_expert_gate_decision
                    verdict = retry_vulnerability_verdict
                    attack_results_for_patch = retry_attack_results
                    attack_decision_for_regression = retry_attack_decision
                else:
                    reflection_projection = self._build_expert_gate_follow_up_reflection_projection(
                    state=state,
                    expert_gate_decision=expert_gate_decision,
                )
                    memory_handoffs.append(
                    self._build_memory_handoff(
                        handoff_id=f"handoff-{state['run_id'][:8]}-reflection-follow-up",
                        from_agent="expert_gate_agent",
                        to_agent="reflection_agent",
                        objective="将专家闸门的观察收口或补充验证建议投影到 Reflection Agent，沉淀下一轮优化卡片。",
                        projection=reflection_projection,
                    )
                )
                    reflection_cards = service._reflect_from_projection(
                    reflection_projection,
                    run_id=state["run_id"],
                    fallback_workspace=str(state["target_service"].artifact_id or ""),
                )
                    service._log(
                    discussion_log,
                    actor="Supervisor",
                    phase="patch_reflection",
                    status="completed",
                    message=self._build_expert_gate_follow_up_message(expert_gate_decision),
                    data={
                        "route_target": expert_gate_decision.route_target,
                        "decision_family": expert_gate_decision.decision_family,
                    },
                    progress_callback=progress_callback,
                )
                    return {
                    "discussion_log": discussion_log,
                    "expert_gate_projection": expert_gate_projection,
                    "expert_gate_decision": expert_gate_decision,
                    "reflection_projection": reflection_projection,
                    "reflection_cards": reflection_cards,
                    "memory_handoffs": memory_handoffs,
                }
            patch_projection = self._build_patch_projection(
                state=state,
                expert_gate_decision=patch_entry_gate_decision,
                target_service_override=target_service,
                verdict_override=verdict,
                attack_results_override=attack_results_for_patch,
                round_id="patch-r2" if retry_expert_gate_decision is not None else "patch-r1",
            )
            memory_handoffs.append(
                self._build_memory_handoff(
                    handoff_id=f"handoff-{state['run_id'][:8]}-patch",
                    from_agent="expert_gate_agent",
                    to_agent="patch_agent",
                    objective="将专家闸门裁决、漏洞结论与攻击工件投影到 Patch Agent 的独立窗口。",
                    projection=patch_projection,
                )
            )
            target_service = self._extract_target_service_from_projection(
                patch_projection,
                fallback=state.get("target_service"),
            )
            verdict = self._extract_vulnerability_verdict_from_projection(
                patch_projection,
                fallback=state.get("vulnerability_verdict"),
            )
            patch_spec = service._plan_patch_from_projection(
                patch_projection,
                run_id=state["run_id"],
            )
            regression_target_service = self._build_regression_target_service(
                target_service=target_service,
                patch_spec=patch_spec,
            )
            patched_engineer = self._build_patched_engineer_report(
                engineer=engineer,
                patch_spec=patch_spec,
            )
            regression_target_service, patch_application, patch_apply_dispatch = (
                sandbox_dispatcher.dispatch_patch_application(
                    run_id=state["run_id"],
                    round_id="regression",
                    baseline_target_service=target_service,
                    target_service=regression_target_service,
                    engineer=patched_engineer,
                    patch_spec=patch_spec,
                    final_scheme=final_scheme,
                )
            )
            rollback_plan, rollback_dispatch = sandbox_dispatcher.dispatch_rollback(
                run_id=state["run_id"],
                round_id="regression",
                target_service=regression_target_service,
                patch_spec=patch_spec,
                baseline_workspace=target_service.artifact_id if target_service is not None else None,
            )
            regression_target_service, regression_deployment, regression_deployment_dispatch = (
                sandbox_dispatcher.dispatch_target_deployment(
                    run_id=state["run_id"],
                    round_id="regression",
                    target_service=regression_target_service,
                    engineer=patched_engineer,
                    final_scheme=final_scheme,
                )
            )
            regression_vulnerability_report = self._build_regression_vulnerability_report(
                vulnerability_report=final_vulnerability_report,
                baseline_verdict=verdict,
                patch_spec=patch_spec,
            )
            regression_attack_projection = self._build_regression_attack_planning_projection(
                state=state,
                target_service=regression_target_service,
                patch_spec=patch_spec,
                regression_vulnerability_report=regression_vulnerability_report,
                evidence_pack_override=self._retrieve_attack_planning_evidence(
                    retrieval_service=retrieval_service,
                    state=state,
                    target_service=regression_target_service,
                    planning_mode="regression",
                    prior_findings=[
                        finding
                        for item in attack_results_for_patch[:3]
                        for finding in item.findings[:2]
                    ][:6],
                    regression_focus=list(patch_spec.regression_focus or [])[:4],
                ),
                prior_attack_results_override=attack_results_for_patch,
                prior_attack_decision_override=attack_decision_for_regression,
            )
            memory_handoffs.append(
                self._build_memory_handoff(
                    handoff_id=f"handoff-{state['run_id'][:8]}-attack-replan",
                    from_agent="patch_agent",
                    to_agent="attack_planning_agent",
                    objective="将补丁信息、上一轮攻击结果与残余风险投影到攻击规划 Agent，用于回归重规划。",
                    projection=regression_attack_projection,
                )
            )
            regression_attack_decision, regression_attack_specs = service._plan_attack_from_projection(
                regression_attack_projection,
                run_id=f"{state['run_id']}-reg",
            )
            regression_attack_decision = regression_attack_decision.model_copy(
                update={"decision_id": f"{patch_spec.patch_id}-reg-decision"}
            )
            regression_attack_specs = [
                spec.model_copy(update={"attack_id": f"{patch_spec.patch_id}-reg-{index}"})
                for index, spec in enumerate(regression_attack_specs, start=1)
            ]
            regression_attack_decision, regression_attack_specs = self._resolve_domain_attack_plan(
                run_id=f"{state['run_id']}-reg",
                target_service=regression_target_service,
                attack_decision=regression_attack_decision,
                attack_specs=regression_attack_specs,
            )
            if self._should_dispatch_attack(regression_attack_decision):
                regression_telemetry_callback = self._build_attack_telemetry_callback(
                    service=service,
                    discussion_log=discussion_log,
                    progress_callback=progress_callback,
                    round_kind="regression",
                )
                regression_attack_results, regression_attack_dispatch = (
                    sandbox_dispatcher.dispatch_attack_execution(
                        run_id=state["run_id"],
                        round_id="regression",
                        target_service=regression_target_service,
                        attack_specs=regression_attack_specs,
                        vulnerability_report=regression_vulnerability_report,
                        telemetry_callback=regression_telemetry_callback,
                    )
                )
            else:
                regression_attack_results = []
                regression_attack_dispatch = self._build_non_executed_attack_dispatch(
                    run_id=state["run_id"],
                    round_id="regression",
                    target_service=regression_target_service,
                    attack_decision=regression_attack_decision,
                    attack_specs=regression_attack_specs,
                )
            rollback_execution_dispatch = None
            if self._construction_regression_requires_rollback(
                target_service=regression_target_service,
                attack_results=regression_attack_results,
            ):
                _, rollback_execution_dispatch = (
                    sandbox_dispatcher.dispatch_construction_rollback_execution(
                        run_id=state["run_id"],
                        round_id="regression-failed",
                        target_service=regression_target_service,
                        patch_spec=patch_spec,
                    )
                )
                regression_target_service = regression_target_service.model_copy(
                    update={
                        "status": "rolled_back",
                        "status_label": "回归失败，已回滚",
                    }
                )
            regression_vulnerability_projection = self._build_regression_vulnerability_projection(
                state=state,
                target_service=regression_target_service,
                attack_decision=regression_attack_decision,
                attack_results=regression_attack_results,
                vulnerability_report=regression_vulnerability_report,
                baseline_verdict=verdict,
            )
            memory_handoffs.append(
                self._build_memory_handoff(
                    handoff_id=f"handoff-{state['run_id'][:8]}-vulnerability-regression",
                    from_agent="patch_agent",
                    to_agent="vulnerability_agent",
                    objective="将补丁版本回归攻击结果与残余风险摘要投影到漏洞评估 Agent 的独立窗口。",
                    projection=regression_vulnerability_projection,
                )
            )
            regression_vulnerability_verdict = service._evaluate_vulnerability_from_projection(
                regression_vulnerability_projection,
                run_id=state["run_id"],
            )
            patch_artifact_summary = self.artifact_summarizer.summarize_patch_artifacts(
                patch_spec=patch_spec,
                baseline_workspace=(
                    target_service.artifact_id if target_service is not None else None
                ),
                patched_workspace=regression_target_service.artifact_id,
            )
            patch_execution = self._build_patch_execution_report(
                run_id=state["run_id"],
                patch_spec=patch_spec,
                regression_target_service=regression_target_service,
                patch_apply_dispatch=patch_apply_dispatch,
                regression_deployment_dispatch=regression_deployment_dispatch,
                regression_attack_dispatch=regression_attack_dispatch,
                rollback_dispatch=rollback_dispatch,
                regression_attack_results=regression_attack_results,
                regression_vulnerability_verdict=regression_vulnerability_verdict,
                patch_artifact_summary=patch_artifact_summary,
                workspace=str(patch_application.workspace).replace("\\", "/"),
            )
            if rollback_execution_dispatch is not None:
                patch_execution = patch_execution.model_copy(
                    update={
                        "status": "rolled_back",
                        "status_label": "已回滚",
                        "summary": "建筑可信控制回归未全部通过，系统已恢复补丁前安全配置。",
                        "rollback_dispatch_id": rollback_execution_dispatch.dispatch_id,
                        "rollback_artifact_refs": self._filter_non_empty_refs(
                            [
                                *patch_execution.rollback_artifact_refs,
                                *rollback_execution_dispatch.artifact_refs,
                            ]
                        ),
                        "metadata": {
                            **patch_execution.metadata,
                            "rollback_executed": True,
                            "rollback_execution_status": rollback_execution_dispatch.status,
                            "rollback_execution_verified": bool(
                                rollback_execution_dispatch.metadata.get("verified")
                            ),
                        },
                    }
                )
            service._log(
                discussion_log,
                actor="Security & Compliance Auditor",
                phase="vulnerability_evaluation",
                status=regression_vulnerability_verdict.severity,
                message=f"已完成补丁版本残余风险评估，当前严重度：{regression_vulnerability_verdict.severity_label}。",
                data={"target_service_ref": regression_target_service.service_id},
                progress_callback=progress_callback,
            )
            if regression_attack_results:
                service._log(
                    discussion_log,
                    actor="Security & Compliance Auditor",
                    phase="attack_executor",
                    status="executed",
                    message=f"已对补丁版本执行 {len(regression_attack_specs)} 条回归攻击任务。",
                    data={
                        "target_service_ref": regression_target_service.service_id,
                        "dispatch_id": regression_attack_dispatch.dispatch_id,
                    },
                    progress_callback=progress_callback,
                )
            else:
                service._log(
                    discussion_log,
                    actor="Security & Compliance Auditor",
                    phase="attack_executor",
                    status="skipped",
                    message=self._build_non_executed_attack_message(
                        attack_decision=regression_attack_decision,
                        round_kind="regression",
                    ),
                    data={
                        "target_service_ref": regression_target_service.service_id,
                        "dispatch_id": regression_attack_dispatch.dispatch_id,
                        "planner_action": regression_attack_decision.action,
                    },
                    progress_callback=progress_callback,
                )
            reflection_projection = self._build_reflection_projection(
                state=state,
                patch_spec=patch_spec,
                patch_execution=patch_execution,
                patch_artifact_summary=patch_artifact_summary,
                regression_target_service=regression_target_service,
                regression_attack_results=regression_attack_results,
                regression_vulnerability_verdict=regression_vulnerability_verdict,
            )
            memory_handoffs.append(
                self._build_memory_handoff(
                    handoff_id=f"handoff-{state['run_id'][:8]}-reflection",
                    from_agent="patch_agent",
                    to_agent="reflection_agent",
                    objective="将修补结果、回归探测结论与反思卡投影到反思 Agent 的独立窗口。",
                    projection=reflection_projection,
                )
            )
            reflection_cards = service._reflect_from_projection(
                reflection_projection,
                run_id=state["run_id"],
                fallback_workspace=str(regression_deployment.workspace).replace("\\", "/"),
            )
            service._log(
                discussion_log,
                actor="Supervisor",
                phase="patch_reflection",
                status="executed",
                message="已生成修补方案与下一轮提示词优化卡片。",
                data={"next_version": patch_spec.next_version},
                progress_callback=progress_callback,
            )
            service._log(
                discussion_log,
                actor="Supervisor",
                phase="patch_reflection",
                status="executed",
                message="已完成补丁版本重部署与正式回归探测。",
                data={
                    "regression_service_id": regression_target_service.service_id,
                    "patch_dispatch_id": patch_apply_dispatch.dispatch_id,
                    "deployment_dispatch_id": regression_deployment_dispatch.dispatch_id,
                    "attack_dispatch_id": regression_attack_dispatch.dispatch_id,
                    "rollback_dispatch_id": rollback_dispatch.dispatch_id,
                    "rollback_plan_path": str(rollback_plan.rollback_plan_path).replace("\\", "/"),
                },
                progress_callback=progress_callback,
            )
            return {
                "discussion_log": discussion_log,
                "expert_gate_projection": expert_gate_projection,
                "expert_gate_decision": expert_gate_decision,
                "retry_attack_projection": retry_attack_projection,
                "retry_attack_decision": retry_attack_decision,
                "retry_attack_specs": retry_attack_specs,
                "retry_attack_results": retry_attack_results,
                "retry_vulnerability_projection": retry_vulnerability_projection,
                "retry_vulnerability_verdict": retry_vulnerability_verdict,
                "retry_attack_dispatch": retry_attack_dispatch,
                "retry_expert_gate_projection": retry_expert_gate_projection,
                "retry_expert_gate_decision": retry_expert_gate_decision,
                "patch_spec": patch_spec,
                "patch_execution": patch_execution,
                "reflection_cards": reflection_cards,
                "patch_apply_dispatch": patch_apply_dispatch,
                "rollback_dispatch": rollback_dispatch,
                "rollback_execution_dispatch": rollback_execution_dispatch,
                "regression_target_service": regression_target_service,
                "regression_attack_decision": regression_attack_decision,
                "regression_attack_specs": regression_attack_specs,
                "regression_attack_results": regression_attack_results,
                "regression_vulnerability_verdict": regression_vulnerability_verdict,
                "expert_gate_projection": expert_gate_projection,
                "patch_projection": patch_projection,
                "reflection_projection": reflection_projection,
                "memory_handoffs": memory_handoffs,
                "regression_deployment_dispatch": regression_deployment_dispatch,
                "regression_attack_dispatch": regression_attack_dispatch,
            }

        def delivery_node(state: LangGraphMASState) -> LangGraphMASState:
            discussion_log = list(state.get("discussion_log") or [])
            parsed = state["parsed"]
            final_scheme = state.get("final_scheme")
            final_compliance_report = state.get("final_compliance_report") or {}
            final_vulnerability_report = state.get("final_vulnerability_report") or {}
            audit_passed = bool(state.get("audit_passed"))
            auditor_rounds = list(state.get("auditor_rounds") or [])
            schemes = list(state.get("schemes") or [])
            selected_index = min(int(state.get("selected_index", 0)), max(len(schemes) - 1, 0))

            service._raise_if_cancelled(cancel_check)
            variant_comparison = service._build_variant_comparison(schemes)
            scoring = service._build_scoring_snapshot(final_scheme)
            scenario_fit = service._build_scenario_fit(state["structured_spec"])
            production_guide = service._build_production_guide(state["structured_spec"], audit_passed)
            evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
            target_service = state.get("target_service")
            attack_decision = state.get("attack_decision")
            attack_specs = list(state.get("attack_specs") or [])
            attack_results = list(state.get("attack_results") or [])
            vulnerability_verdict = state.get("vulnerability_verdict")
            expert_gate_decision = state.get("expert_gate_decision")
            patch_spec = state.get("patch_spec")
            patch_execution = state.get("patch_execution")
            reflection_cards = list(state.get("reflection_cards") or [])
            generation_projection = state.get("generation_projection")
            audit_projection = state.get("audit_projection")
            attack_planning_projection = state.get("attack_planning_projection")
            vulnerability_projection = state.get("vulnerability_projection")
            expert_gate_projection = state.get("expert_gate_projection")
            patch_projection = state.get("patch_projection")
            reflection_projection = state.get("reflection_projection")
            memory_handoffs = list(state.get("memory_handoffs") or [])
            baseline_deployment_dispatch = state.get("baseline_deployment_dispatch")
            baseline_attack_dispatch = state.get("baseline_attack_dispatch")
            patch_apply_dispatch = state.get("patch_apply_dispatch")
            rollback_dispatch = state.get("rollback_dispatch")
            rollback_execution_dispatch = state.get("rollback_execution_dispatch")
            regression_target_service = state.get("regression_target_service")
            regression_attack_decision = state.get("regression_attack_decision")
            regression_attack_specs = list(state.get("regression_attack_specs") or [])
            regression_attack_results = list(state.get("regression_attack_results") or [])
            regression_vulnerability_verdict = state.get("regression_vulnerability_verdict")
            regression_deployment_dispatch = state.get("regression_deployment_dispatch")
            regression_attack_dispatch = state.get("regression_attack_dispatch")
            retry_attack_decision = state.get("retry_attack_decision")
            retry_attack_specs = list(state.get("retry_attack_specs") or [])
            retry_attack_results = list(state.get("retry_attack_results") or [])
            retry_attack_projection = state.get("retry_attack_projection")
            retry_vulnerability_projection = state.get("retry_vulnerability_projection")
            retry_vulnerability_verdict = state.get("retry_vulnerability_verdict")
            retry_attack_dispatch = state.get("retry_attack_dispatch")
            retry_expert_gate_projection = state.get("retry_expert_gate_projection")
            retry_expert_gate_decision = state.get("retry_expert_gate_decision")
            same_run_retry_budget = int(state.get("same_run_retry_budget") or 0)
            same_run_retry_used = int(
                bool(
                    retry_attack_decision is not None
                    or retry_attack_specs
                    or retry_attack_results
                    or retry_vulnerability_verdict is not None
                )
            )
            same_run_retry_remaining = max(0, same_run_retry_budget - same_run_retry_used)
            same_run_retry_summary = self._build_same_run_retry_summary(
                expert_gate_decision=expert_gate_decision,
                retry_attack_decision=retry_attack_decision,
                retry_attack_projection=retry_attack_projection,
                retry_attack_dispatch=retry_attack_dispatch,
                retry_vulnerability_projection=retry_vulnerability_projection,
                retry_vulnerability_verdict=retry_vulnerability_verdict,
                retry_expert_gate_projection=retry_expert_gate_projection,
                retry_expert_gate_decision=retry_expert_gate_decision,
                same_run_retry_budget=same_run_retry_budget,
                same_run_retry_used=same_run_retry_used,
                same_run_retry_remaining=same_run_retry_remaining,
                memory_handoffs=memory_handoffs,
            )
            attack_rounds = self._build_attack_rounds(
                target_service=target_service,
                attack_decision=attack_decision,
                attack_specs=attack_specs,
                attack_results=attack_results,
                vulnerability_verdict=vulnerability_verdict,
                expert_gate_decision=expert_gate_decision,
                patch_spec=patch_spec,
                patch_execution=patch_execution,
                reflection_cards=reflection_cards,
                regression_target_service=regression_target_service,
                regression_attack_decision=regression_attack_decision,
                regression_attack_specs=regression_attack_specs,
                regression_attack_results=regression_attack_results,
                regression_vulnerability_verdict=regression_vulnerability_verdict,
                retry_attack_decision=retry_attack_decision,
                retry_attack_specs=retry_attack_specs,
                retry_attack_results=retry_attack_results,
                retry_vulnerability_verdict=retry_vulnerability_verdict,
                retry_expert_gate_decision=retry_expert_gate_decision,
            )
            localized_compliance_report = localize_compliance_report(final_compliance_report)
            localized_vulnerability_report = localize_vulnerability_report(final_vulnerability_report)
            credibility_assessment = service.trust_assessor.assess(
                final_scheme,
                parser_confidence=parsed.confidence,
                compliance_score=float(final_compliance_report.get("overall_compliance", 0.0)),
                risk_score=int(final_vulnerability_report.get("risk_score", 0)),
                audit_passed=audit_passed,
                quantum_ready=auditor_rounds[-1].quantum_ready if auditor_rounds else None,
            )
            final_scheme_payload = (
                service._serialize_scheme(final_scheme, credibility_assessment=credibility_assessment)
                if final_scheme
                else None
            )
            case_memory = self._persist_case_memory(
                case_memory_service,
                state=state,
                status="approved" if audit_passed else "best_effort",
                selected_proposal=f"proposal-{selected_index + 1}" if schemes else None,
                compliance_score=round(float(final_compliance_report.get("overall_compliance", 0.0)), 2),
                risk_score=int(final_vulnerability_report.get("risk_score", 0)),
            )
            projection_models = {
                "generation": generation_projection,
                "audit": audit_projection,
                "attack_planning": attack_planning_projection,
                "attack_planning_retry": retry_attack_projection,
                "vulnerability_evaluation": vulnerability_projection,
                "vulnerability_evaluation_retry": retry_vulnerability_projection,
                "expert_gate": expert_gate_projection,
                "expert_gate_retry": retry_expert_gate_projection,
                "patch": patch_projection,
                "reflection": reflection_projection,
            }
            projection_payloads = {
                key: value.model_dump(mode="json") if value else {}
                for key, value in projection_models.items()
            }
            control_plane = self.control_plane_builder.build(
                run_id=state["run_id"],
                case_id=state["case_id"],
                workflow_trace=WORKFLOW_TRACE,
                projections=projection_models,
                memory_handoffs=memory_handoffs,
                runtime_context={
                    "audit_passed": audit_passed,
                    "delivery_status": "approved" if audit_passed else "best_effort",
                    "attack_results": attack_results,
                    "attack_decision": attack_decision,
                    "expert_gate_decision": expert_gate_decision,
                    "baseline_deployment_dispatch": baseline_deployment_dispatch,
                    "baseline_attack_dispatch": baseline_attack_dispatch,
                    "patch_apply_dispatch": patch_apply_dispatch,
                    "rollback_dispatch": rollback_dispatch,
                    "rollback_execution_dispatch": rollback_execution_dispatch,
                    "patch_execution": patch_execution,
                    "regression_attack_decision": regression_attack_decision,
                    "regression_attack_dispatch": regression_attack_dispatch,
                    "retry_attack_decision": retry_attack_decision,
                    "retry_attack_dispatch": retry_attack_dispatch,
                    "retry_expert_gate_decision": retry_expert_gate_decision,
                    "same_run_retry_summary": same_run_retry_summary,
                },
            )
            context_bus = self.context_bus_builder.build(
                run_id=state["run_id"],
                case_id=state["case_id"],
                projections=projection_models,
                memory_handoffs=memory_handoffs,
            )
            execution_plane = self.execution_plane_builder.build(
                run_id=state["run_id"],
                case_id=state["case_id"],
                target_service=target_service,
                baseline_deployment=baseline_deployment_dispatch,
                baseline_attack=baseline_attack_dispatch,
                patch_apply_dispatch=patch_apply_dispatch,
                regression_deployment=regression_deployment_dispatch,
                regression_attack=regression_attack_dispatch,
                rollback_dispatch=rollback_dispatch,
                attack_results=attack_results,
                regression_attack_results=regression_attack_results,
                patch_execution=patch_execution,
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
                "evidence_pack": evidence_pack.model_dump(),
                "citation_count": len(evidence_pack.items),
                "attack_loop": {
                    "target_service": target_service.model_dump() if target_service else {},
                    "attack_decision": attack_decision.model_dump() if attack_decision else {},
                    "attack_specs": [item.model_dump() for item in attack_specs],
                    "attack_results": [item.model_dump() for item in attack_results],
                    "vulnerability_verdict": (
                        vulnerability_verdict.model_dump() if vulnerability_verdict else {}
                    ),
                    "expert_gate_decision": (
                        expert_gate_decision.model_dump() if expert_gate_decision else {}
                    ),
                    "patch_spec": patch_spec.model_dump() if patch_spec else {},
                    "patch_execution": (
                        patch_execution.model_dump(mode="json") if patch_execution else {}
                    ),
                    "reflection_cards": reflection_cards,
                    "regression_target_service": (
                        regression_target_service.model_dump() if regression_target_service else {}
                    ),
                    "regression_attack_decision": (
                        regression_attack_decision.model_dump() if regression_attack_decision else {}
                    ),
                    "regression_attack_specs": [item.model_dump() for item in regression_attack_specs],
                    "regression_attack_results": [item.model_dump() for item in regression_attack_results],
                    "regression_vulnerability_verdict": (
                        regression_vulnerability_verdict.model_dump()
                        if regression_vulnerability_verdict
                        else {}
                    ),
                    "retry_attack_decision": (
                        retry_attack_decision.model_dump() if retry_attack_decision else {}
                    ),
                    "retry_attack_specs": [item.model_dump() for item in retry_attack_specs],
                    "retry_attack_results": [item.model_dump() for item in retry_attack_results],
                    "retry_vulnerability_verdict": (
                        retry_vulnerability_verdict.model_dump() if retry_vulnerability_verdict else {}
                    ),
                    "retry_expert_gate_decision": (
                        retry_expert_gate_decision.model_dump()
                        if retry_expert_gate_decision
                        else {}
                    ),
                    "same_run_retry_summary": same_run_retry_summary,
                    "same_run_retry_budget": same_run_retry_budget,
                    "same_run_retry_used": same_run_retry_used,
                    "same_run_retry_remaining": same_run_retry_remaining,
                    "rounds": attack_rounds,
                    "loop_status": self._build_attack_loop_status(
                        attack_rounds=attack_rounds,
                        patch_spec=patch_spec,
                        expert_gate_decision=expert_gate_decision,
                        retry_expert_gate_decision=retry_expert_gate_decision,
                        same_run_retry_summary=same_run_retry_summary,
                    ),
                    "current_round": attack_rounds[-1] if attack_rounds else {},
                    "regression_ready": bool(patch_spec),
                    "retry_ready": bool(retry_attack_decision),
                },
                "context_projections": projection_payloads,
                "memory_handoffs": [item.model_dump(mode="json") for item in memory_handoffs],
                "sandbox_dispatcher": {
                    "backend": "local-dispatcher",
                    "policy": sandbox_dispatcher.policy.model_dump(mode="json"),
                    "baseline_deployment": (
                        baseline_deployment_dispatch.model_dump(mode="json")
                        if baseline_deployment_dispatch
                        else {}
                    ),
                    "baseline_attack": (
                        baseline_attack_dispatch.model_dump(mode="json")
                        if baseline_attack_dispatch
                        else {}
                    ),
                    "patch_apply": (
                        patch_apply_dispatch.model_dump(mode="json")
                        if patch_apply_dispatch
                        else {}
                    ),
                    "regression_deployment": (
                        regression_deployment_dispatch.model_dump(mode="json")
                        if regression_deployment_dispatch
                        else {}
                    ),
                    "regression_attack": (
                        regression_attack_dispatch.model_dump(mode="json")
                        if regression_attack_dispatch
                        else {}
                    ),
                    "retry_attack": (
                        retry_attack_dispatch.model_dump(mode="json") if retry_attack_dispatch else {}
                    ),
                    "rollback_plan": (
                        rollback_dispatch.model_dump(mode="json")
                        if rollback_dispatch
                        else {}
                    ),
                    "rollback_execution": (
                        rollback_execution_dispatch.model_dump(mode="json")
                        if rollback_execution_dispatch
                        else {}
                    ),
                },
                "backend_architecture": {
                    "control_plane": control_plane.model_dump(mode="json"),
                    "memory_bus": context_bus.model_dump(mode="json"),
                    "execution_plane": execution_plane.model_dump(mode="json"),
                },
                "code_artifacts": {
                    "pseudocode_ready": bool(final_scheme_payload and final_scheme_payload.implementation.pseudocode),
                    "python_ready": bool(final_scheme_payload and final_scheme_payload.implementation.python),
                    "c_ready": bool(final_scheme_payload and final_scheme_payload.implementation.c),
                },
                "case_memory_summary": self._build_case_memory_summary(case_memory),
                "next_action": (
                    "上线前仍需人工密码学复核。"
                    if audit_passed
                    else "请先处理审计拒绝项后再重新执行 MAS。"
                ),
                "engine_mode": "graph-native",
                "workflow_trace": WORKFLOW_TRACE,
            }
            replay_snapshot, replay_timeline_summary = case_timeline_service.record_run(
                case_id=state["case_id"],
                run_id=state["run_id"],
                delivery=delivery,
                control_plane=control_plane.model_dump(mode="json"),
                execution_plane=execution_plane.model_dump(mode="json"),
                memory_bus=context_bus.model_dump(mode="json"),
            )
            delivery["backend_architecture"]["replay_plane"] = {
                "timeline_summary": replay_timeline_summary,
                "latest_snapshot": replay_snapshot.model_dump(mode="json"),
            }

            service._log(
                discussion_log,
                actor="Supervisor",
                phase="delivery",
                status=delivery["status"],
                message=f"流程已结束，当前状态：{display_status(delivery['status'])}。",
                data={"selected_proposal": delivery["selected_proposal"]},
                progress_callback=progress_callback,
            )

            result = MASResponse(
                request_id=state["run_id"],
                run_id=state["run_id"],
                case_id=state["case_id"],
                generated_at=datetime.now(timezone.utc),
                security_disclaimer=SECURITY_DISCLAIMER_TEXT,
                analyst=state["analyst"],
                architect=state["architect"],
                auditor_rounds=auditor_rounds,
                engineer=state["engineer"],
                final_scheme=final_scheme_payload,
                credibility_assessment=credibility_assessment,
                compliance_report=localized_compliance_report,
                vulnerability_report=localized_vulnerability_report,
                discussion_log=discussion_log,
                evidence_pack=evidence_pack,
                case_memory=case_memory,
                delivery=delivery,
            )
            return {
                "discussion_log": discussion_log,
                "case_memory": case_memory,
                "final_result": result,
            }

        def route_after_analyst(state: LangGraphMASState) -> str:
            return "clarification_gate_stage" if state.get("needs_clarification") else "context_builder_stage"

        graph = StateGraph(LangGraphMASState)
        graph.add_node("analyst_stage", analyst_node)
        graph.add_node("clarification_gate_stage", clarification_gate_node)
        graph.add_node("context_builder_stage", context_builder_node)
        graph.add_node("architect_stage", architect_node)
        graph.add_node("audit_stage", audit_node)
        graph.add_node("engineer_stage", engineer_node)
        graph.add_node("target_deployer_stage", target_deployer_node)
        graph.add_node("attack_executor_stage", attack_executor_node)
        graph.add_node("vulnerability_evaluation_stage", vulnerability_evaluation_node)
        graph.add_node("patch_reflection_stage", patch_reflection_node)
        graph.add_node("delivery_stage", delivery_node)

        graph.add_edge(START, "analyst_stage")
        graph.add_conditional_edges(
            "analyst_stage",
            route_after_analyst,
            {
                "clarification_gate_stage": "clarification_gate_stage",
                "context_builder_stage": "context_builder_stage",
            },
        )
        graph.add_edge("clarification_gate_stage", END)
        graph.add_edge("context_builder_stage", "architect_stage")
        graph.add_edge("architect_stage", "audit_stage")
        graph.add_edge("audit_stage", "engineer_stage")
        graph.add_edge("engineer_stage", "target_deployer_stage")
        graph.add_edge("target_deployer_stage", "attack_executor_stage")
        graph.add_edge("attack_executor_stage", "vulnerability_evaluation_stage")
        graph.add_edge("vulnerability_evaluation_stage", "patch_reflection_stage")
        graph.add_edge("patch_reflection_stage", "delivery_stage")
        graph.add_edge("delivery_stage", END)
        return graph.compile()

    def _build_target_service_spec(
        self,
        *,
        run_id: str,
        final_scheme: CryptographicScheme | None,
        engineer: EngineerReportPayload,
        structured_spec: dict[str, Any] | None = None,
        requirement_text: str = "",
    ) -> TargetServiceSpecPayload:
        """Create a lightweight deployed-service descriptor for the attack loop."""
        service_name = (
            getattr(getattr(final_scheme, "metadata", None), "name", None)
            or "candidate-crypto-service"
        )
        runtime = "python" if engineer.corrected_python else ("c" if engineer.corrected_c else "pseudocode")
        attack_surface = ["encrypt", "decrypt", "key_rotation", "service_api"]
        return build_target_service_for_requirement(
            run_id=run_id,
            requirement_text=requirement_text,
            domain=str((structured_spec or {}).get("domain") or ""),
            service_name=service_name,
            runtime=runtime,
            attack_surface=attack_surface,
        )

    def _build_attack_specs(
        self,
        *,
        run_id: str,
        target_service: TargetServiceSpecPayload,
        vulnerability_report: dict[str, Any],
    ) -> list[AttackSpecPayload]:
        """Create bounded, sandbox-safe attack plans for the target service."""
        risk_score = int(vulnerability_report.get("risk_score", 0))
        attack_family = "oracle_probe" if risk_score >= 60 else "misuse_case"
        objective = (
            "模拟对已部署加密服务的错误处理、接口约束和密钥使用边界进行压力验证。"
        )
        return [
            AttackSpecPayload(
                attack_id=f"attack-{run_id[:8]}-1",
                target_service_ref=target_service.service_id,
                attack_family=attack_family,
                objective=objective,
                attack_surface=list(target_service.attack_surface),
                expected_artifacts=["finding.json", "metrics.json", "trace.jsonl"],
                telemetry_fields=["cpu", "memory", "tx_bytes", "rx_bytes", "latency_p95"],
                budget={"timeout_s": 180, "cpu_cores": 1, "memory_mb": 512},
                status="planned",
                status_label="待执行",
            )
        ]

    def _resolve_domain_attack_plan(
        self,
        *,
        run_id: str,
        target_service: TargetServiceSpecPayload,
        attack_decision: AttackDecisionPayload,
        attack_specs: list[AttackSpecPayload],
    ) -> tuple[AttackDecisionPayload, list[AttackSpecPayload]]:
        """Use domain attack contracts when the selected target requires them."""

        if not is_construction_target(target_service):
            return attack_decision, attack_specs
        construction_specs = build_construction_attack_specs(
            run_id=run_id,
            target_service=target_service,
        )
        return (
            attack_decision.model_copy(
                update={
                    "action": "execute",
                    "action_label": "执行建筑可信交付攻击组",
                    "rationale": "建筑目标必须以文件篡改、版本回滚、越权、设备冒充和遥测重放的领域证据进行验证。",
                    "selected_attack_family": "construction_trusted_delivery_suite",
                    "expected_outcome": "生成五类建筑攻击的阻断、回归和证据链结果。",
                    "next_step": "dispatch_attack",
                }
            ),
            construction_specs,
        )

    @staticmethod
    def _construction_regression_requires_rollback(
        *,
        target_service: TargetServiceSpecPayload,
        attack_results: list[AttackResultPayload],
    ) -> bool:
        """Rollback a construction patch unless every required regression probe passed."""

        if not is_construction_target(target_service):
            return False
        if not attack_results:
            return True
        return any(
            result.status != "executed"
            or not bool(result.metrics.get("regression_passed"))
            for result in attack_results
        )

    def _simulate_attack_results(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        attack_specs: list[AttackSpecPayload],
        vulnerability_report: dict[str, Any],
    ) -> list[AttackResultPayload]:
        """Build simulated attack results until a real sandbox executor is wired in."""
        risk_score = int(vulnerability_report.get("risk_score", 0))
        summary = "已完成攻击链路壳子模拟，等待真实 sandbox executor 接线。"
        findings = [item for item in self._collect_top_vulnerability_findings(vulnerability_report)]
        if not findings:
            findings = ["未发现可直接复现的严重漏洞，建议继续做接口滥用与错误处理攻击。"]
        metrics = {
            "latency_p95_ms": 42 if risk_score < 60 else 88,
            "tx_bytes": 4096,
            "rx_bytes": 2048,
            "peak_memory_mb": 128,
        }
        return [
            AttackResultPayload(
                attack_id=spec.attack_id,
                target_service_ref=target_service.service_id,
                status="simulated",
                status_label="已模拟",
                summary=summary,
                findings=findings,
                metrics=metrics,
                artifact_refs=[
                    f"{target_service.artifact_id}:trace",
                    f"{target_service.artifact_id}:metrics",
                ],
            )
            for spec in attack_specs
        ]

    def _build_vulnerability_verdict(
        self,
        *,
        run_id: str,
        target_service: TargetServiceSpecPayload,
        attack_results: list[AttackResultPayload],
        vulnerability_report: dict[str, Any],
    ) -> VulnerabilityVerdictPayload:
        """Translate simulated attack results into a stable verdict payload."""
        risk_score = int(vulnerability_report.get("risk_score", 0))
        severity = "high" if risk_score >= 70 else ("medium" if risk_score >= 40 else "low")
        severity_label = {"high": "高", "medium": "中", "low": "低"}[severity]
        exploitability = "moderate" if attack_results else "limited"
        exploitability_label = "中等" if attack_results else "较低"
        findings = attack_results[0].findings if attack_results else []
        return VulnerabilityVerdictPayload(
            verdict_id=f"verdict-{run_id[:8]}",
            target_service_ref=target_service.service_id,
            severity=severity,
            severity_label=severity_label,
            exploitability=exploitability,
            exploitability_label=exploitability_label,
            summary=(
                "基于模拟攻击结果，当前目标服务仍需加强错误处理边界、密钥使用限制和接口约束。"
            ),
            affected_components=findings[:3],
            remediation_priority="high" if severity != "low" else "medium",
            remediation_priority_label="高" if severity != "low" else "中",
            evidence_refs=[result.attack_id for result in attack_results],
        )

    def _build_patch_spec(
        self,
        *,
        run_id: str,
        target_service: TargetServiceSpecPayload,
        verdict: VulnerabilityVerdictPayload,
    ) -> PatchSpecPayload:
        """Create a minimal patch plan that can feed future build/deploy loops."""
        return PatchSpecPayload(
            patch_id=f"patch-{run_id[:8]}",
            target_service_ref=target_service.service_id,
            strategy="hardening-and-validation",
            summary=(
                "建议补齐接口输入校验、错误处理掩码、密钥轮换约束与攻击面最小化策略。"
            ),
            changed_artifacts=[
                f"{target_service.artifact_id}:python",
                f"{target_service.artifact_id}:c",
            ],
            next_version="v2",
            regression_focus=[
                "错误处理泄露",
                "密钥使用边界",
                "接口滥用防护",
            ],
        )

    def _build_reflection_cards(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        verdict: VulnerabilityVerdictPayload,
        patch_spec: PatchSpecPayload,
    ) -> list[dict[str, Any]]:
        """Summaries used for next-round prompt and policy optimization."""
        return [
            {
                "card_type": "reflection",
                "target_service_ref": target_service.service_id,
                "summary": "下一轮 generation 应优先输出带接口约束、错误处理和密钥治理边界的实现。",
                "severity": verdict.severity,
                "patch_strategy": patch_spec.strategy,
            }
        ]

    def _build_regression_target_service(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        patch_spec: PatchSpecPayload,
    ) -> TargetServiceSpecPayload:
        """Create a patched target-service descriptor for regression execution."""
        return target_service.model_copy(
            update={
                "service_id": f"{target_service.service_id}-reg",
                "artifact_id": f"{target_service.artifact_id}-reg",
                "service_version": patch_spec.next_version,
                "status": "ready",
                "status_label": "待回归部署",
            }
        )

    def _build_patched_engineer_report(
        self,
        *,
        engineer: EngineerReportPayload,
        patch_spec: PatchSpecPayload,
    ) -> EngineerReportPayload:
        """Add a lightweight overlay so patched artifacts remain replayable."""
        attempts = list(engineer.attempts or [])
        attempts.append(
            BuildAttemptPayload(
                step="patch",
                status="done",
                status_label=display_status("done"),
                message=f"已按 {patch_spec.strategy} 生成补丁版本交付工件，并附带验证与回滚说明。",
            )
        )
        validation_hint = "；".join(list(patch_spec.validation_steps or [])[:2])
        rollback_hint = "；".join(list(patch_spec.rollback_notes or [])[:2])
        python_overlay = engineer.corrected_python
        if python_overlay:
            python_overlay = (
                f"{python_overlay.rstrip()}\n\n"
                "# Patch hardening overlay\n"
                f"PATCH_STRATEGY = {patch_spec.strategy!r}\n"
                f"PATCH_SUMMARY = {patch_spec.summary!r}\n"
                f"PATCH_RATIONALE = {patch_spec.rationale!r}\n"
                f"PATCH_VALIDATION = {validation_hint!r}\n"
            )
        c_overlay = engineer.corrected_c
        if c_overlay:
            c_overlay = (
                f"{c_overlay.rstrip()}\n\n"
                "/* Patch hardening overlay */\n"
                f"/* strategy: {patch_spec.strategy} */\n"
                f"/* rationale: {patch_spec.rationale} */\n"
                f"/* validation: {validation_hint} */\n"
                f"/* rollback: {rollback_hint} */\n"
            )
        return engineer.model_copy(
            update={
                "attempts": attempts,
                "corrected_python": python_overlay,
                "corrected_c": c_overlay,
            }
        )

    def _build_patch_execution_report(
        self,
        *,
        run_id: str,
        patch_spec: PatchSpecPayload,
        regression_target_service: TargetServiceSpecPayload,
        patch_apply_dispatch: SandboxDispatchResultPayload,
        regression_deployment_dispatch: SandboxDispatchResultPayload,
        regression_attack_dispatch: SandboxDispatchResultPayload,
        rollback_dispatch: SandboxDispatchResultPayload,
        regression_attack_results: list[AttackResultPayload],
        regression_vulnerability_verdict: VulnerabilityVerdictPayload | None,
        patch_artifact_summary: dict[str, Any],
        workspace: str,
    ) -> PatchExecutionPayload:
        """Build a stable structured execution report for the patch stage."""

        changed_artifact_summaries = list(
            patch_artifact_summary.get("changed_artifact_summaries") or []
        )[:4]
        supporting_artifact_summaries = list(
            patch_artifact_summary.get("supporting_artifact_summaries") or []
        )[:6]
        artifact_inventory = dict(patch_artifact_summary.get("artifact_inventory") or {})
        if not artifact_inventory:
            artifact_inventory = self.artifact_summarizer._build_patch_artifact_inventory(
                changed_artifact_summaries=changed_artifact_summaries,
                supporting_artifact_summaries=supporting_artifact_summaries,
            )
        applied_artifacts = [
            str(item.get("relative_name") or item.get("artifact_key") or "").strip()
            for item in changed_artifact_summaries
            if str(item.get("relative_name") or item.get("artifact_key") or "").strip()
        ]
        diff_preview: list[str] = []
        for item in changed_artifact_summaries:
            for line in item.get("diff_preview") or []:
                text = str(line or "").strip()
                if not text or text in diff_preview:
                    continue
                diff_preview.append(text)
                if len(diff_preview) >= 6:
                    break
            if len(diff_preview) >= 6:
                break

        regression_executed = regression_attack_dispatch.status == "executed"
        status = "validated" if regression_executed else "applied"
        status_label = "已验证" if regression_executed else "已应用"
        validation_steps = [
            str(item).strip() for item in patch_spec.validation_steps or [] if str(item).strip()
        ]
        if not validation_steps:
            validation_steps = ["完成补丁版本重部署", "执行回归验证"]
        validation_results = self._build_patch_validation_results(
            validation_steps=validation_steps,
            regression_deployment_dispatch=regression_deployment_dispatch,
            regression_attack_dispatch=regression_attack_dispatch,
            regression_attack_results=regression_attack_results,
            regression_vulnerability_verdict=regression_vulnerability_verdict,
            changed_artifact_summaries=changed_artifact_summaries,
        )
        validation_summary = self._summarize_patch_validation_results(validation_results)
        changed_hint = "、".join(applied_artifacts[:2]) if applied_artifacts else "核心实现工件"
        summary = (
            f"已针对 {regression_target_service.service_name} 应用补丁方案 {patch_spec.strategy}，"
            f"覆盖 {changed_hint}，当前状态为{status_label}。"
        )
        if regression_executed:
            summary += f" 回归阶段已执行 {len(regression_attack_results)} 条验证任务。"
        else:
            summary += " 回归阶段尚未执行正式攻击验证，当前仅完成补丁应用与重部署。"

        patch_artifact_refs = self._filter_non_empty_refs(
            [
                *list(patch_apply_dispatch.artifact_refs or []),
                str(patch_apply_dispatch.metadata.get("patch_manifest_path") or "").strip(),
                str(patch_apply_dispatch.metadata.get("patch_metadata_path") or "").strip(),
                str(patch_apply_dispatch.metadata.get("rollback_plan_path") or "").strip(),
                str(patch_apply_dispatch.metadata.get("rollback_manifest_path") or "").strip(),
            ]
        )
        rollback_artifact_refs = self._filter_non_empty_refs(
            [
                *list(rollback_dispatch.artifact_refs or []),
                str(rollback_dispatch.metadata.get("rollback_plan_path") or "").strip(),
                str(rollback_dispatch.metadata.get("rollback_manifest_path") or "").strip(),
            ]
        )
        regression_artifact_refs = self._filter_non_empty_refs(
            [
                *list(regression_deployment_dispatch.artifact_refs or []),
                *list(regression_attack_dispatch.artifact_refs or []),
                *[
                    artifact_ref
                    for result in regression_attack_results
                    for artifact_ref in result.artifact_refs
                ],
            ]
        )

        return PatchExecutionPayload(
            execution_id=f"patch-exec-{run_id[:8]}",
            patch_id=patch_spec.patch_id,
            execution_contract_version="v1",
            target_service_ref=regression_target_service.service_id,
            target_service_version=regression_target_service.service_version,
            status=status,
            status_label=status_label,
            summary=summary,
            workspace=workspace,
            applied_at=datetime.now(timezone.utc),
            patch_dispatch_id=patch_apply_dispatch.dispatch_id,
            deployment_dispatch_id=regression_deployment_dispatch.dispatch_id,
            regression_dispatch_id=regression_attack_dispatch.dispatch_id,
            rollback_dispatch_id=rollback_dispatch.dispatch_id,
            applied_artifacts=applied_artifacts,
            patch_artifact_refs=patch_artifact_refs,
            rollback_artifact_refs=rollback_artifact_refs,
            regression_artifact_refs=regression_artifact_refs,
            implementation_notes=list(patch_spec.implementation_notes or [])[:6],
            validation_steps=validation_steps,
            validation_results=validation_results,
            validation_summary=validation_summary,
            rollback_notes=list(patch_spec.rollback_notes or [])[:6],
            changed_artifact_summaries=changed_artifact_summaries,
            supporting_artifact_summaries=supporting_artifact_summaries,
            artifact_inventory=artifact_inventory,
            diff_preview=diff_preview,
            metadata={
                "patch_status": patch_apply_dispatch.status,
                "patch_action": patch_apply_dispatch.decision,
                "deployment_status": regression_deployment_dispatch.status,
                "regression_status": regression_attack_dispatch.status,
                "regression_action": regression_attack_dispatch.decision,
                "rollback_status": rollback_dispatch.status,
                "rollback_action": rollback_dispatch.decision,
                "regression_result_count": len(regression_attack_results),
                "changed_artifact_count": len(changed_artifact_summaries),
                "supporting_artifact_count": len(supporting_artifact_summaries),
                "patch_artifact_ref_count": len(patch_artifact_refs),
                "rollback_artifact_ref_count": len(rollback_artifact_refs),
                "regression_artifact_ref_count": len(regression_artifact_refs),
                "artifact_pipeline_version": str(
                    patch_artifact_summary.get("artifact_pipeline_version") or "v1"
                ),
                "validation_summary": validation_summary,
                "residual_severity": (
                    regression_vulnerability_verdict.severity if regression_vulnerability_verdict else ""
                ),
                "residual_severity_label": (
                    regression_vulnerability_verdict.severity_label if regression_vulnerability_verdict else ""
                ),
            },
        )

    def _build_patch_validation_results(
        self,
        *,
        validation_steps: list[str],
        regression_deployment_dispatch: SandboxDispatchResultPayload,
        regression_attack_dispatch: SandboxDispatchResultPayload,
        regression_attack_results: list[AttackResultPayload],
        regression_vulnerability_verdict: VulnerabilityVerdictPayload | None,
        changed_artifact_summaries: list[dict[str, Any]],
    ) -> list[PatchValidationResultPayload]:
        """Translate validation intent into replayable execution results."""

        results: list[PatchValidationResultPayload] = []
        regression_executed = regression_attack_dispatch.status == "executed"
        recorded_kinds: set[str] = set()
        for index, step in enumerate(validation_steps[:6], start=1):
            step_kind = self._classify_patch_validation_step(step)
            recorded_kinds.add(step_kind)
            results.append(
                self._build_patch_validation_result(
                    step_id=f"patch-check-{index}",
                    step=step,
                    step_kind=step_kind,
                    regression_deployment_dispatch=regression_deployment_dispatch,
                    regression_attack_dispatch=regression_attack_dispatch,
                    regression_attack_results=regression_attack_results,
                    regression_vulnerability_verdict=regression_vulnerability_verdict,
                    changed_artifact_summaries=changed_artifact_summaries,
                    regression_executed=regression_executed,
                )
            )
        synthetic_steps: list[tuple[str, str]] = []
        if "deployment_redeploy" not in recorded_kinds:
            synthetic_steps.append(("deployment_redeploy", "确认补丁版本重部署与健康检查结果"))
        if "regression_attack" not in recorded_kinds:
            synthetic_steps.append(("regression_attack", "复核回归攻击执行与调度状态"))
        if "artifact_review" not in recorded_kinds:
            synthetic_steps.append(("artifact_review", "收口补丁工件差异与支撑工件摘要"))
        if "residual_risk_review" not in recorded_kinds and regression_vulnerability_verdict is not None:
            synthetic_steps.append(("residual_risk_review", "复核残余风险裁决与收敛结论"))
        for offset, (step_kind, step) in enumerate(synthetic_steps, start=len(results) + 1):
            results.append(
                self._build_patch_validation_result(
                    step_id=f"patch-check-{offset}",
                    step=step,
                    step_kind=step_kind,
                    regression_deployment_dispatch=regression_deployment_dispatch,
                    regression_attack_dispatch=regression_attack_dispatch,
                    regression_attack_results=regression_attack_results,
                    regression_vulnerability_verdict=regression_vulnerability_verdict,
                    changed_artifact_summaries=changed_artifact_summaries,
                    regression_executed=regression_executed,
                )
            )
        return results

    def _classify_patch_validation_step(self, step: str) -> str:
        """Map a free-form validation step into a stable validation kind."""

        text = str(step or "").strip()
        normalized = text.lower()
        if any(token in text for token in ["部署", "重部署", "健康检查"]) or any(
            token in normalized for token in ["deploy", "redeploy", "health"]
        ):
            return "deployment_redeploy"
        if any(token in text for token in ["回归", "攻击", "探测", "验证"]) or any(
            token in normalized for token in ["regression", "attack", "probe", "validate"]
        ):
            return "regression_attack"
        if any(token in text for token in ["日志", "工件", "diff", "差异", "metrics", "finding"]) or any(
            token in normalized for token in ["artifact", "diff", "metrics", "finding", "log"]
        ):
            return "artifact_review"
        if any(token in text for token in ["风险", "残余", "裁决"]) or any(
            token in normalized for token in ["risk", "severity", "verdict"]
        ):
            return "residual_risk_review"
        return "custom"

    def _build_patch_validation_result(
        self,
        *,
        step_id: str,
        step: str,
        step_kind: str,
        regression_deployment_dispatch: SandboxDispatchResultPayload,
        regression_attack_dispatch: SandboxDispatchResultPayload,
        regression_attack_results: list[AttackResultPayload],
        regression_vulnerability_verdict: VulnerabilityVerdictPayload | None,
        changed_artifact_summaries: list[dict[str, Any]],
        regression_executed: bool,
    ) -> PatchValidationResultPayload:
        """Build one replayable validation result item with typed evidence."""

        if step_kind == "deployment_redeploy":
            status = "passed" if regression_deployment_dispatch.status == "executed" else "failed"
            details = (
                f"部署调度状态：{regression_deployment_dispatch.status_label}"
                f"（dispatch_id={regression_deployment_dispatch.dispatch_id}）"
            )
            evidence = [
                f"deployment_dispatch:{regression_deployment_dispatch.dispatch_id}",
                f"deployment_status:{regression_deployment_dispatch.status}",
            ]
            artifact_refs = [
                str(regression_deployment_dispatch.metadata.get("workspace") or "").strip()
            ]
            metadata = {
                "dispatch_stage": regression_deployment_dispatch.stage,
                "decision": regression_deployment_dispatch.decision,
            }
        elif step_kind == "artifact_review":
            has_artifacts = bool(changed_artifact_summaries)
            status = "passed" if has_artifacts else "pending"
            details = (
                f"已收口 {len(changed_artifact_summaries)} 个变更工件摘要。"
                if has_artifacts
                else "当前尚未收口补丁工件差异摘要。"
            )
            evidence = [
                str(item.get("relative_name") or item.get("artifact_key") or "").strip()
                for item in changed_artifact_summaries[:4]
                if str(item.get("relative_name") or item.get("artifact_key") or "").strip()
            ]
            artifact_refs = [
                str(item.get("patched_path") or "").strip()
                for item in changed_artifact_summaries[:4]
                if str(item.get("patched_path") or "").strip()
            ]
            metadata = {
                "changed_artifact_count": len(changed_artifact_summaries),
                "line_delta_total": sum(int(item.get("line_delta") or 0) for item in changed_artifact_summaries),
            }
        elif step_kind == "residual_risk_review":
            if regression_vulnerability_verdict is not None:
                status = "passed"
                details = (
                    f"残余风险严重度：{regression_vulnerability_verdict.severity_label}，"
                    f"整改优先级：{regression_vulnerability_verdict.remediation_priority_label}。"
                )
                evidence = [
                    f"severity:{regression_vulnerability_verdict.severity}",
                    f"priority:{regression_vulnerability_verdict.remediation_priority}",
                ]
                artifact_refs = []
                metadata = {
                    "affected_components": list(regression_vulnerability_verdict.affected_components[:4]),
                    "summary": regression_vulnerability_verdict.summary,
                }
            else:
                status = "pending"
                details = "当前尚未生成残余风险裁决。"
                evidence = []
                artifact_refs = []
                metadata = {}
        elif regression_executed:
            status = "passed"
            details = (
                f"回归攻击已执行 {len(regression_attack_results)} 条任务，"
                f"调度状态：{regression_attack_dispatch.status_label}"
                f"（dispatch_id={regression_attack_dispatch.dispatch_id}）"
            )
            evidence = [f"regression_dispatch:{regression_attack_dispatch.dispatch_id}"] + [
                f"attack:{item.attack_id}" for item in regression_attack_results[:4]
            ]
            artifact_refs = [
                str(path).strip()
                for item in regression_attack_results[:2]
                for path in item.artifact_refs[:3]
                if str(path).strip()
            ][:6]
            metadata = {
                "result_count": len(regression_attack_results),
                "decision": regression_attack_dispatch.decision,
            }
        elif regression_attack_dispatch.status == "skipped":
            status = "skipped"
            details = (
                f"回归攻击未执行，规划器动作={regression_attack_dispatch.decision}，"
                f"调度状态：{regression_attack_dispatch.status_label}"
            )
            evidence = [
                f"regression_dispatch:{regression_attack_dispatch.dispatch_id}",
                f"planner_action:{regression_attack_dispatch.decision}",
            ]
            artifact_refs = []
            metadata = {
                "decision": regression_attack_dispatch.decision,
                "result_count": len(regression_attack_results),
            }
        else:
            status = "pending"
            details = f"回归调度状态：{regression_attack_dispatch.status_label}"
            evidence = [f"regression_status:{regression_attack_dispatch.status}"]
            artifact_refs = []
            metadata = {"decision": regression_attack_dispatch.decision}
        return PatchValidationResultPayload(
            step_id=step_id,
            step_kind=step_kind,
            step=step,
            status=status,
            status_label=display_status(status),
            details=details,
            evidence=evidence[:6],
            artifact_refs=artifact_refs[:6],
            metadata=metadata,
        )

    def _summarize_patch_validation_results(
        self,
        validation_results: list[PatchValidationResultPayload],
    ) -> dict[str, Any]:
        """Aggregate per-step validation results into a compact summary."""

        counts = {"passed": 0, "failed": 0, "skipped": 0, "pending": 0}
        for item in validation_results:
            status = str(item.status or "pending")
            counts[status] = counts.get(status, 0) + 1
        return {
            "total": len(validation_results),
            "passed": counts.get("passed", 0),
            "failed": counts.get("failed", 0),
            "skipped": counts.get("skipped", 0),
            "pending": counts.get("pending", 0),
            "all_passed": counts.get("failed", 0) == 0 and counts.get("pending", 0) == 0,
        }

    def _build_regression_vulnerability_report(
        self,
        *,
        vulnerability_report: dict[str, Any],
        baseline_verdict: VulnerabilityVerdictPayload,
        patch_spec: PatchSpecPayload,
    ) -> dict[str, Any]:
        """Create a patched-version vulnerability report for regression probes."""
        report = dict(vulnerability_report or {})
        baseline_risk = int(report.get("risk_score", 0))
        residual_risk = max(0, baseline_risk - 15)
        report["baseline_risk_score"] = baseline_risk
        report["risk_score"] = residual_risk
        report["regression_stage"] = "patched_redeploy_executed"
        report["patch_id"] = patch_spec.patch_id
        recommendations = list(report.get("recommendations") or [])
        recommendations.append(
            {
                "action": (
                    f"继续围绕 {baseline_verdict.remediation_priority_label} 优先级问题做残余风险收敛。"
                ),
                "priority": "medium" if residual_risk <= baseline_risk else "high",
            }
        )
        report["recommendations"] = recommendations[:6]
        return report

    def _build_regression_vulnerability_verdict(
        self,
        *,
        run_id: str,
        target_service: TargetServiceSpecPayload,
        attack_results: list[AttackResultPayload],
        vulnerability_report: dict[str, Any],
        baseline_verdict: VulnerabilityVerdictPayload,
    ) -> VulnerabilityVerdictPayload:
        """Summarize residual risk after patched-version regression execution."""
        verdict = self._build_vulnerability_verdict(
            run_id=f"{run_id}-reg",
            target_service=target_service,
            attack_results=attack_results,
            vulnerability_report=vulnerability_report,
        )
        return verdict.model_copy(
            update={
                "verdict_id": f"verdict-{run_id[:8]}-reg",
                "summary": (
                    "补丁版本壳子已完成重部署与正式回归探测，"
                    f"风险严重度从 {baseline_verdict.severity_label} 收敛到 {verdict.severity_label}。"
                ),
            }
        )

    def _build_attack_rounds(
        self,
        *,
        target_service: TargetServiceSpecPayload | None,
        attack_decision: AttackDecisionPayload | None,
        attack_specs: list[AttackSpecPayload],
        attack_results: list[AttackResultPayload],
        vulnerability_verdict: VulnerabilityVerdictPayload | None,
        expert_gate_decision: ExpertGateDecisionPayload | None,
        patch_spec: PatchSpecPayload | None,
        patch_execution: PatchExecutionPayload | None,
        reflection_cards: list[dict[str, Any]],
        regression_target_service: TargetServiceSpecPayload | None,
        regression_attack_decision: AttackDecisionPayload | None,
        regression_attack_specs: list[AttackSpecPayload],
        regression_attack_results: list[AttackResultPayload],
        regression_vulnerability_verdict: VulnerabilityVerdictPayload | None,
        retry_attack_decision: AttackDecisionPayload | None = None,
        retry_attack_specs: list[AttackSpecPayload] | None = None,
        retry_attack_results: list[AttackResultPayload] | None = None,
        retry_vulnerability_verdict: VulnerabilityVerdictPayload | None = None,
        retry_expert_gate_decision: ExpertGateDecisionPayload | None = None,
    ) -> list[dict[str, Any]]:
        """Build a stable multi-round attack loop summary without breaking old fields."""
        if target_service is None:
            return []

        total_artifacts = sum(len(item.artifact_refs) for item in attack_results)
        total_findings = sum(len(item.findings) for item in attack_results)
        traffic_samples = sum(len((item.metrics or {}).get("traffic_series", [])) for item in attack_results)
        baseline_mode = self._resolve_attack_round_mode(
            attack_decision=attack_decision,
            attack_results=attack_results,
            preview=False,
        )
        baseline_round = {
            "round_id": f"{target_service.service_id}-r1",
            "round_index": 1,
            "round_kind": "baseline",
            "round_kind_label": "基线攻击",
            "mode": baseline_mode,
            "mode_label": self._round_mode_label(baseline_mode),
            "patch_applied": False,
            "patch_applied_label": "否",
            "target_service": target_service.model_dump(),
            "attack_decision": attack_decision.model_dump() if attack_decision else {},
            "attack_specs": [item.model_dump() for item in attack_specs],
            "attack_results": [item.model_dump() for item in attack_results],
            "vulnerability_verdict": (
                vulnerability_verdict.model_dump() if vulnerability_verdict else {}
            ),
            "expert_gate_decision": (
                expert_gate_decision.model_dump() if expert_gate_decision else {}
            ),
            "summary": self._build_attack_round_summary(
                round_kind="baseline",
                mode=baseline_mode,
                patch_applied=False,
            ),
            "summary_metrics": {
                "artifact_count": total_artifacts,
                "finding_count": total_findings,
                "traffic_sample_count": traffic_samples,
            },
        }
        rounds = [baseline_round]
        retry_attack_specs = list(retry_attack_specs or [])
        retry_attack_results = list(retry_attack_results or [])
        retry_round_present = (
            retry_attack_decision is not None
            or retry_attack_specs
            or retry_attack_results
            or retry_vulnerability_verdict is not None
        )
        if retry_round_present:
            retry_mode = self._resolve_attack_round_mode(
                attack_decision=retry_attack_decision,
                attack_results=retry_attack_results,
                preview=False,
            )
            rounds.append(
                {
                    "round_id": f"{target_service.service_id}-r2",
                    "round_index": 2,
                    "round_kind": "retry",
                    "round_kind_label": "补充验证",
                    "mode": retry_mode,
                    "mode_label": self._round_mode_label(retry_mode),
                    "patch_applied": False,
                    "patch_applied_label": "否",
                    "target_service": target_service.model_dump(),
                    "attack_decision": (
                        retry_attack_decision.model_dump() if retry_attack_decision else {}
                    ),
                    "attack_specs": [item.model_dump() for item in retry_attack_specs],
                    "attack_results": [item.model_dump() for item in retry_attack_results],
                    "vulnerability_verdict": (
                        retry_vulnerability_verdict.model_dump()
                        if retry_vulnerability_verdict
                        else {}
                    ),
                    "expert_gate_decision": (
                        retry_expert_gate_decision.model_dump()
                        if retry_expert_gate_decision
                        else {}
                    ),
                    "summary": self._build_attack_round_summary(
                        round_kind="retry",
                        mode=retry_mode,
                        patch_applied=False,
                    ),
                    "summary_metrics": {
                        "artifact_count": sum(len(item.artifact_refs) for item in retry_attack_results),
                        "finding_count": sum(len(item.findings) for item in retry_attack_results),
                        "traffic_sample_count": sum(
                            len((item.metrics or {}).get("traffic_series", []))
                            for item in retry_attack_results
                        ),
                    },
                }
            )
        if patch_spec is None:
            return rounds

        regression_round_index = len(rounds) + 1

        regression_mode = self._resolve_attack_round_mode(
            attack_decision=regression_attack_decision,
            attack_results=regression_attack_results,
            preview=regression_target_service is not None and not regression_attack_results,
        )

        if regression_target_service is not None and (
            regression_attack_results or regression_mode in {"handoff", "stopped"}
        ):
            regression_specs = regression_attack_specs or self._build_regression_attack_specs(
                target_service=regression_target_service,
                patch_spec=patch_spec,
            )
            rounds.append(
                {
                    "round_id": f"{regression_target_service.service_id}-r{regression_round_index}",
                    "round_index": regression_round_index,
                    "round_kind": "regression",
                    "round_kind_label": "补丁回归",
                    "mode": regression_mode,
                    "mode_label": self._round_mode_label(regression_mode),
                    "patch_applied": True,
                    "patch_applied_label": "已修补",
                    "target_service": regression_target_service.model_dump(),
                    "attack_decision": (
                        regression_attack_decision.model_dump() if regression_attack_decision else {}
                    ),
                    "attack_specs": [item.model_dump() for item in regression_specs],
                    "attack_results": [item.model_dump() for item in regression_attack_results],
                    "vulnerability_verdict": (
                        regression_vulnerability_verdict.model_dump()
                        if regression_vulnerability_verdict
                        else {}
                    ),
                    "patch_spec": patch_spec.model_dump(),
                    "patch_execution": (
                        patch_execution.model_dump(mode="json") if patch_execution else {}
                    ),
                    "reflection_cards": reflection_cards,
                    "summary": self._build_attack_round_summary(
                        round_kind="regression",
                        mode=regression_mode,
                        patch_applied=True,
                    ),
                    "summary_metrics": {
                        "artifact_count": sum(len(item.artifact_refs) for item in regression_attack_results),
                        "finding_count": sum(len(item.findings) for item in regression_attack_results),
                        "traffic_sample_count": sum(
                            len((item.metrics or {}).get("traffic_series", []))
                            for item in regression_attack_results
                        ),
                    },
                }
            )
            return rounds

        regression_target = target_service.model_copy(
            update={
                "service_id": f"{target_service.service_id}-reg",
                "service_version": patch_spec.next_version,
                "status": "preview",
                "status_label": "待回归",
            }
        )
        regression_specs = self._build_regression_attack_specs(
            target_service=regression_target,
            patch_spec=patch_spec,
        )
        rounds.append(
            {
                "round_id": f"{regression_target.service_id}-r{regression_round_index}",
                "round_index": regression_round_index,
                "round_kind": "regression_preview",
                "round_kind_label": "回归预检",
                "mode": "preview",
                "mode_label": "预检方案",
                "patch_applied": False,
                "patch_applied_label": "否（等待真实补丁落地）",
                "target_service": regression_target.model_dump(),
                "attack_decision": (
                    regression_attack_decision.model_dump() if regression_attack_decision else {}
                ),
                "attack_specs": [item.model_dump() for item in regression_specs],
                "attack_results": [],
                "vulnerability_verdict": {},
                "patch_spec": patch_spec.model_dump(),
                "patch_execution": (
                    patch_execution.model_dump(mode="json") if patch_execution else {}
                ),
                "reflection_cards": reflection_cards,
                "summary": "已基于 patch_spec 生成第二轮回归预检任务，等待真实补丁落地后执行正式回归攻击。",
                "summary_metrics": {
                    "planned_check_count": len(regression_specs),
                    "regression_focus_count": len(patch_spec.regression_focus),
                },
            }
        )
        return rounds

    def _build_regression_attack_specs(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        patch_spec: PatchSpecPayload,
    ) -> list[AttackSpecPayload]:
        """Create the next-round regression preview specs from patch focus areas."""
        focuses = patch_spec.regression_focus or ["接口约束回归", "错误处理回归", "密钥治理回归"]
        specs: list[AttackSpecPayload] = []
        for index, focus in enumerate(focuses[:3], start=1):
            specs.append(
                AttackSpecPayload(
                    attack_id=f"{patch_spec.patch_id}-reg-{index}",
                    target_service_ref=target_service.service_id,
                    attack_family="regression_check",
                    objective=f"针对“{focus}”生成下一轮回归攻击预检任务。",
                    attack_surface=list(target_service.attack_surface),
                    expected_artifacts=["regression_trace.jsonl", "regression_metrics.json"],
                    telemetry_fields=["latency_p95", "tx_bytes", "rx_bytes"],
                    budget={"timeout_s": 60, "cpu_cores": 1, "memory_mb": 256},
                    status="planned",
                    status_label="待回归",
                )
            )
        return specs

    def _build_generation_projection(self, *, state: LangGraphMASState) -> ContextProjectionPayload:
        """Build a minimal role-aware context window for the generation agent."""
        analyst = state.get("analyst")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        case_memory = state.get("case_memory")
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
            clarifications=list(state.get("clarifications") or []),
        )
        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
            cards.extend(
                self._build_reflection_memory_cards(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    round_id="generation-r1",
                    source_agent="case_memory_service",
                    card_type="reflection_memory",
                    summary="项目级反思记忆，供 generation Agent 避免重复上一轮失败模式。",
                )
            )
        if analyst:
            cards.append(
                MemoryCardPayload(
                    card_id=f"card-{state['run_id'][:8]}-analyst",
                    card_type="analyst_summary",
                    case_id=state["case_id"],
                    run_id=state["run_id"],
                    round_id="generation-r1",
                    source_agent="requirement_analyst",
                    priority="high",
                    priority_label=self._priority_label("high"),
                    summary="需求分析摘要，供生成 Agent 在独立窗口内参考。",
                    payload={
                        "assumptions": analyst.assumptions[:4],
                        "ambiguities": analyst.parsed_requirement.ambiguities[:4],
                        "case_context": analyst.case_context,
                    },
                    evidence_refs=self._build_evidence_refs(evidence_pack, limit=3),
                    created_at=datetime.now(timezone.utc),
                )
            )
            cards.append(
                MemoryCardPayload(
                    card_id=f"card-{state['run_id'][:8]}-generation-runtime-input",
                    card_type="generation_runtime_input",
                    case_id=state["case_id"],
                    run_id=state["run_id"],
                    round_id="generation-r1",
                    source_agent="context_builder",
                    priority="high",
                    priority_label=self._priority_label("high"),
                    summary="供 generation 节点恢复结构化需求与解析置信度的运行时输入。",
                    payload={
                        "runtime_stage": "generation",
                        "structured_spec": state.get("structured_spec") or {},
                        "parsed_requirement": analyst.parsed_requirement.model_dump(mode="json"),
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )

        return ContextProjectionPayload(
            agent_id="generation_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="generation-r1",
            objective="结合企业知识、项目级记忆与约束条件生成候选加密方案。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                ArtifactRefPayload(
                    artifact_id=f"artifact-{state['run_id'][:8]}-structured-spec",
                    artifact_type="structured_spec",
                    title="结构化需求说明",
                    summary=self._summarize_requirement(state["payload"].requirement, max_length=120),
                    metadata={
                        "domain": str((state.get("structured_spec") or {}).get("domain") or ""),
                        "platform": str((state.get("structured_spec") or {}).get("platform") or ""),
                    },
                )
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=5),
            token_budget_hint=4600,
        )

    def _build_audit_projection(self, *, state: LangGraphMASState) -> ContextProjectionPayload:
        """Build a minimal role-aware context window for the audit agent."""
        architect = state.get("architect")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        case_memory = state.get("case_memory")
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
            cards.extend(
                self._build_reflection_memory_cards(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    round_id="audit-r1",
                    source_agent="case_memory_service",
                    card_type="reflection_memory",
                    summary="项目级反思记忆，供 audit Agent 优先核查上一轮残余风险与修补经验。",
                )
            )
        if architect:
            cards.append(
                MemoryCardPayload(
                    card_id=f"card-{state['run_id'][:8]}-architect",
                    card_type="candidate_summary",
                    case_id=state["case_id"],
                    run_id=state["run_id"],
                    round_id="audit-r1",
                    source_agent="generation_agent",
                    priority="high",
                    priority_label=self._priority_label("high"),
                    summary="候选方案摘要，供审计 Agent 在独立窗口内进行比较与裁决。",
                    payload={
                        "candidate_count": len(architect.candidates),
                        "candidates": [
                            {
                                "proposal_id": candidate.proposal_id,
                                "name": candidate.name,
                                "score": candidate.score,
                                "components": [item.name for item in candidate.components[:4]],
                                "architecture_pattern": candidate.architecture_pattern,
                            }
                            for candidate in architect.candidates[:3]
                        ],
                    },
                    evidence_refs=self._build_evidence_refs(evidence_pack, limit=3),
                    created_at=datetime.now(timezone.utc),
                )
            )
        if state.get("schemes"):
            cards.append(
                MemoryCardPayload(
                    card_id=f"card-{state['run_id'][:8]}-audit-runtime-input",
                    card_type="audit_runtime_input",
                    case_id=state["case_id"],
                    run_id=state["run_id"],
                    round_id="audit-r1",
                    source_agent="generation_agent",
                    priority="high",
                    priority_label=self._priority_label("high"),
                    summary="供 audit 节点恢复候选方案原始结构与审计约束的运行时输入。",
                    payload={
                        "runtime_stage": "audit",
                        "structured_spec": state.get("structured_spec") or {},
                        "schemes": [
                            scheme.model_dump(mode="json") for scheme in list(state.get("schemes") or [])
                        ],
                        "scheme_entries": [
                            {
                                "proposal_id": candidate.proposal_id,
                                "scheme": scheme.model_dump(mode="json"),
                            }
                            for candidate, scheme in zip(
                                architect.candidates,
                                list(state.get("schemes") or []),
                            )
                        ],
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )

        artifact_refs = [
            ArtifactRefPayload(
                artifact_id=f"artifact-{candidate.proposal_id}",
                artifact_type="scheme_candidate",
                title=candidate.name,
                summary=candidate.design_rationale[:180],
                metadata={
                    "proposal_id": candidate.proposal_id,
                    "score": candidate.score,
                    "security_level": candidate.security_level,
                },
            )
            for candidate in (architect.candidates[:3] if architect else [])
        ]

        return ContextProjectionPayload(
            agent_id="audit_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="audit-r1",
            objective="在独立审计窗口内评估候选方案的合规性、漏洞风险与可交付性。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=artifact_refs,
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=5),
            token_budget_hint=4200,
        )

    def _build_audit_decision_projection(
        self,
        *,
        state: LangGraphMASState,
        base_projection: ContextProjectionPayload,
        scheme: CryptographicScheme,
        proposal_id: str,
        round_idx: int,
        audit_input: dict[str, Any],
        standards: list[Any],
        vulnerability_report: dict[str, Any],
        compliance_report: dict[str, Any],
        quantum_eval: dict[str, Any],
        quantum_required: bool,
        tool_findings: list[str],
        tool_recommendations: list[str],
    ) -> ContextProjectionPayload:
        """Attach a candidate-specific audit decision card for the current round."""

        compliance_score = float(compliance_report.get("overall_compliance", 0.0))
        risk_score = int(vulnerability_report.get("risk_score", 0))
        critical_count = int(vulnerability_report.get("summary", {}).get("critical", 0))
        quantum_ready = bool(
            quantum_eval.get("resistant")
            or ("aes" in audit_input.get("algorithm", "") and int(audit_input.get("key_size", 0)) >= 256)
        )
        architect = state.get("architect")
        candidate = None
        if architect:
            candidate = next(
                (item for item in architect.candidates if item.proposal_id == proposal_id),
                None,
            )
        compact_vulnerability_report = {
            "risk_score": risk_score,
            "summary": dict(vulnerability_report.get("summary") or {}),
            "vulnerabilities": list(vulnerability_report.get("vulnerabilities") or [])[:4],
            "recommendations": list(vulnerability_report.get("recommendations") or [])[:4],
        }
        compact_compliance_report = {
            "overall_compliance": compliance_score,
            "gaps": list(compliance_report.get("gaps") or [])[:4],
            "recommendations": list(compliance_report.get("recommendations") or [])[:4],
            "details": dict(compliance_report.get("details") or {}),
        }
        decision_card = MemoryCardPayload(
            card_id=f"card-{state['run_id'][:8]}-audit-decision-r{round_idx}",
            card_type="audit_decision_input",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id=f"audit-r{round_idx}",
            source_agent="audit_engine",
            priority="high",
            priority_label=self._priority_label("high"),
            summary=f"供 AuditEvaluationAgent 对 {proposal_id} 执行第 {round_idx} 轮独立裁决的结构化审计输入。",
            payload={
                "runtime_stage": "audit_decision",
                "round": round_idx,
                "proposal_id": proposal_id,
                "proposal_name": (
                    str(candidate.name or "").strip()
                    if candidate is not None
                    else str(getattr(getattr(scheme, "metadata", None), "name", "") or "").strip()
                ),
                "architecture_pattern": (
                    str(candidate.architecture_pattern or "").strip() if candidate is not None else ""
                ),
                "components": (
                    [item.name for item in candidate.components[:6]]
                    if candidate is not None
                    else [item.name for item in scheme.architecture.components[:6]]
                ),
                "audit_input": dict(audit_input or {}),
                "standards_checked": [getattr(item, "value", str(item)) for item in standards],
                "compliance_score": compliance_score,
                "risk_score": risk_score,
                "critical_count": critical_count,
                "quantum_required": quantum_required,
                "quantum_ready": quantum_ready,
                "vulnerability_report": compact_vulnerability_report,
                "compliance_report": compact_compliance_report,
                "quantum_eval": dict(quantum_eval or {}),
                "tool_findings": list(tool_findings or [])[:8],
                "tool_recommendations": list(tool_recommendations or [])[:8],
            },
            evidence_refs=list(base_projection.evidence_refs or [])[:4],
            created_at=datetime.now(timezone.utc),
        )
        finalized_cards = self._finalize_projection_cards([decision_card])
        return base_projection.model_copy(
            update={
                "round_id": f"audit-r{round_idx}",
                "objective": f"在独立审计窗口内裁决 {proposal_id} 是否通过审计。",
                "cards": list(base_projection.cards or []) + finalized_cards,
            }
        )

    def _extract_generation_runtime_inputs(
        self,
        projection: ContextProjectionPayload,
        *,
        fallback_requirement: Requirement,
        fallback_structured_spec: dict[str, Any],
        fallback_parser_confidence: float | None,
    ) -> tuple[Requirement, dict[str, Any], float | None]:
        """Recover generation-stage runtime inputs from the projection window."""

        requirement = fallback_requirement
        structured_spec = dict(fallback_structured_spec or {})
        parser_confidence = fallback_parser_confidence

        for card in projection.cards or []:
            if not self._matches_runtime_input_card(
                card,
                expected_card_type="generation_runtime_input",
                expected_stage="generation",
            ):
                continue
            payload = dict(card.payload or {})
            if isinstance(payload.get("structured_spec"), dict):
                structured_spec = dict(payload.get("structured_spec") or {})
            parsed_requirement = payload.get("parsed_requirement") or {}
            if isinstance(parsed_requirement, dict):
                requirement_payload = parsed_requirement.get("requirement") or {}
                try:
                    if isinstance(requirement_payload, dict) and requirement_payload:
                        requirement = Requirement.model_validate(requirement_payload)
                except Exception:
                    requirement = fallback_requirement
                confidence = parsed_requirement.get("confidence")
                if confidence is not None:
                    try:
                        parser_confidence = float(confidence)
                    except (TypeError, ValueError):
                        parser_confidence = fallback_parser_confidence
            break

        return requirement, structured_spec, parser_confidence

    def _restore_requirement_from_analyst(
        self,
        analyst: AnalystReportPayload,
        *,
        raw_requirement: str,
    ) -> Requirement:
        """Rebuild a Requirement object from analyst output without reading graph-state parsed payload."""

        requirement_payload = (
            analyst.parsed_requirement.requirement if analyst and analyst.parsed_requirement else {}
        )
        try:
            if isinstance(requirement_payload, dict) and requirement_payload:
                return Requirement.model_validate(requirement_payload)
        except Exception:
            pass
        return Requirement(
            description=raw_requirement,
            scheme_type=SchemeType.AUTHENTICATED_ENCRYPTION,
            target_platform=TargetPlatform(
                type=PlatformType.SERVER,
                resource_level=ResourceLevel.MODERATE,
            ),
            security=SecurityRequirement(security_level=128),
        )

    def _extract_audit_runtime_inputs(
        self,
        projection: ContextProjectionPayload,
        *,
        fallback_schemes: list[CryptographicScheme],
        fallback_structured_spec: dict[str, Any],
    ) -> tuple[list[CryptographicScheme], dict[str, Any], list[str]]:
        """Recover audit-stage runtime inputs from the projection window."""

        schemes = list(fallback_schemes or [])
        structured_spec = dict(fallback_structured_spec or {})
        proposal_ids = [f"proposal-{idx + 1}" for idx in range(len(schemes))]

        for card in projection.cards or []:
            if not self._matches_runtime_input_card(
                card,
                expected_card_type="audit_runtime_input",
                expected_stage="audit",
            ):
                continue
            payload = dict(card.payload or {})
            if isinstance(payload.get("structured_spec"), dict):
                structured_spec = dict(payload.get("structured_spec") or {})
            scheme_entries = payload.get("scheme_entries") or []
            parsed_schemes: list[CryptographicScheme] = []
            parsed_proposal_ids: list[str] = []
            for item in scheme_entries:
                if not isinstance(item, dict):
                    continue
                proposal_id = str(item.get("proposal_id") or "").strip()
                scheme_payload = item.get("scheme") or {}
                if not isinstance(scheme_payload, dict):
                    continue
                try:
                    parsed_schemes.append(CryptographicScheme.model_validate(scheme_payload))
                    parsed_proposal_ids.append(proposal_id or f"proposal-{len(parsed_proposal_ids) + 1}")
                except Exception:
                    continue
            if parsed_schemes:
                schemes = parsed_schemes
                proposal_ids = parsed_proposal_ids
                break
            raw_schemes = payload.get("schemes") or []
            parsed_schemes = []
            for item in raw_schemes:
                if not isinstance(item, dict):
                    continue
                try:
                    parsed_schemes.append(CryptographicScheme.model_validate(item))
                except Exception:
                    continue
            if parsed_schemes:
                schemes = parsed_schemes
                proposal_ids = [f"proposal-{idx + 1}" for idx in range(len(parsed_schemes))]
            break

        return schemes, structured_spec, proposal_ids

    def _should_dispatch_attack(self, attack_decision: AttackDecisionPayload | None) -> bool:
        """Return whether the planner's decision should reach the sandbox executor."""

        if attack_decision is None:
            return False
        return attack_decision.action in {"execute", "continue", "replan"}

    def _build_attack_telemetry_callback(
        self,
        *,
        service: MASRuntimeSupport,
        discussion_log: list[DiscussionTurnPayload],
        progress_callback: Optional[Callable[[DiscussionTurnPayload], None]],
        round_kind: str,
    ) -> Callable[[dict[str, Any]], None]:
        """Bridge sandbox telemetry into the existing progress stream."""

        def emit(payload: dict[str, Any]) -> None:
            if payload.get("event_type") != "traffic_sample":
                return
            sample = payload.get("sample") or {}
            sample_label = sample.get("sample_label") or f"T+{sample.get('sample') or '?'}"
            probe_count = payload.get("probe_count") or "?"
            service._log(
                discussion_log,
                actor="Sandbox Runtime",
                phase="attack_executor",
                status="running",
                message=f"已写入流量采样 {sample_label}（{sample.get('sample') or '?'} / {probe_count}）。",
                data={
                    **payload,
                    "round_kind": round_kind,
                },
                progress_callback=progress_callback,
            )

        return emit

    def _build_non_executed_attack_dispatch(
        self,
        *,
        run_id: str,
        round_id: str,
        target_service: TargetServiceSpecPayload,
        attack_decision: AttackDecisionPayload,
        attack_specs: list[AttackSpecPayload],
    ) -> SandboxDispatchResultPayload:
        """Create a synthetic dispatcher result when the planner skips sandbox execution."""

        dispatch_id = f"dispatch-{run_id[:8]}-{round_id}-attack-skip"
        attack_families = [spec.attack_family for spec in attack_specs]
        requested_budget = self._aggregate_attack_budget_for_summary(attack_specs)
        decision_label = {
            "handoff_to_vulnerability": "规划器转交评估",
            "stop": "规划器停止攻击",
        }.get(attack_decision.action, "规划器跳过攻击")
        event_kind = {
            "handoff_to_vulnerability": "handoff",
            "stop": "stopped",
        }.get(attack_decision.action, "skipped")

        return SandboxDispatchResultPayload(
            dispatch_id=dispatch_id,
            run_id=run_id,
            round_id=round_id,
            stage="attack_executor",
            executor_backend="planner-controlled",
            target_service_ref=target_service.service_id,
            decision=attack_decision.action,
            decision_label=decision_label,
            status="skipped",
            status_label="已跳过",
            requested_attack_count=len(attack_specs),
            approved_attack_count=0,
            requested_probe_count=sum(max(len(spec.attack_surface), 1) for spec in attack_specs),
            approved_probe_count=0,
            rejection_reasons=[],
            failure_category="planner_controlled_skip",
            failure_category_label="规划器控制跳过",
            failure_items=[],
            signature=f"{dispatch_id[:24]}",
            policy=SandboxPolicyPayload(),
            audit_trail=[
                SandboxAuditEventPayload(
                    event_id=f"{dispatch_id}-planner",
                    stage="attack_executor",
                    event_kind=event_kind,
                    event_kind_label=decision_label,
                    summary=self._build_non_executed_attack_message(
                        attack_decision=attack_decision,
                        round_kind=round_id,
                    ),
                    created_at=datetime.now(timezone.utc),
                    metadata={
                        "planner_action": attack_decision.action,
                        "planner_next_step": attack_decision.next_step,
                    },
                )
            ],
            metadata={
                "runtime": target_service.runtime,
                "attack_families": attack_families,
                "requested_budget": requested_budget,
                "planner_action": attack_decision.action,
                "planner_next_step": attack_decision.next_step,
            },
        )

    def _build_non_executed_attack_message(
        self,
        *,
        attack_decision: AttackDecisionPayload,
        round_kind: str,
    ) -> str:
        """Create a readable skip/handoff message for logs and synthetic dispatch records."""

        if attack_decision.action == "handoff_to_vulnerability":
            return (
                f"{round_kind} 轮攻击规划已判定现有证据足以进入漏洞评估，"
                "本轮不再新增 sandbox 攻击任务。"
            )
        if attack_decision.action == "stop":
            return (
                f"{round_kind} 轮攻击规划已判定新增攻击收益不足，"
                "本轮停止继续向 sandbox 下发攻击任务。"
            )
        return f"{round_kind} 轮攻击任务已被规划器跳过。"

    def _aggregate_attack_budget_for_summary(
        self,
        attack_specs: list[AttackSpecPayload],
    ) -> dict[str, Any]:
        """Summarize requested attack budget for synthetic dispatcher records."""

        timeout_s = sum(int(spec.budget.get("timeout_s", 0) or 0) for spec in attack_specs)
        memory_mb = max([int(spec.budget.get("memory_mb", 0) or 0) for spec in attack_specs] or [0])
        cpu_cores = max([int(spec.budget.get("cpu_cores", 0) or 0) for spec in attack_specs] or [0])
        return {
            "timeout_s": timeout_s,
            "memory_mb": memory_mb,
            "cpu_cores": cpu_cores,
        }

    def _resolve_attack_round_mode(
        self,
        *,
        attack_decision: AttackDecisionPayload | None,
        attack_results: list[AttackResultPayload],
        preview: bool,
    ) -> str:
        """Map planner decisions and execution results to stable round modes."""

        if attack_results:
            return "executed"
        if attack_decision is None:
            return "preview" if preview else "planned"
        if attack_decision.action == "handoff_to_vulnerability":
            return "handoff"
        if attack_decision.action == "stop":
            return "stopped"
        if preview:
            return "preview"
        return "planned"

    def _round_mode_label(self, mode: str) -> str:
        """Localize round mode for user-facing delivery payloads."""

        return {
            "executed": "已执行",
            "preview": "预检方案",
            "planned": "已规划",
            "handoff": "已转交评估",
            "stopped": "已停止",
        }.get(mode, "已规划")

    def _build_attack_round_summary(
        self,
        *,
        round_kind: str,
        mode: str,
        patch_applied: bool,
    ) -> str:
        """Generate concise human-readable summaries for round cards."""

        if round_kind == "baseline":
            if mode == "executed":
                return "首轮基线攻击已经对当前已部署目标服务完成受限探测，并沉淀 telemetry / finding 工件。"
            if mode == "handoff":
                return "首轮基线攻击规划判定现有证据已足以进入漏洞评估，因此未再下发新的 sandbox 攻击任务。"
            if mode == "stopped":
                return "首轮基线攻击规划已停止新增攻击任务，本轮未进入 sandbox 执行。"
            return "首轮基线攻击已完成规划，等待后续执行或进一步决策。"
        if round_kind == "retry":
            if mode == "executed":
                return "同轮补充攻击已完成执行，并已形成补充漏洞裁决。"
            if mode == "handoff":
                return "同轮补充攻击规划认为现有证据已足以形成补充漏洞裁决，因此未继续下发 sandbox 攻击任务。"
            if mode == "stopped":
                return "同轮补充攻击规划已停止新增任务，本轮直接转入 follow-up 收口。"
            return "同轮补充攻击已完成规划，等待进一步执行或后续收口。"

        if mode == "executed":
            return "补丁版本壳子已重部署，并已完成正式回归探测与残余风险评估。"
        if mode == "handoff":
            return "补丁版本已完成重部署，攻击规划判定现有证据足以直接进入残余风险评估。"
        if mode == "stopped":
            return "补丁版本已完成重部署，但攻击规划判定无需继续新增回归攻击任务。"
        if patch_applied:
            return "已基于 patch_spec 生成第二轮回归预检任务，等待真实补丁落地后执行正式回归攻击。"
        return "已生成回归预检任务，等待补丁落地。"

    def _build_attack_loop_status(
        self,
        *,
        attack_rounds: list[dict[str, Any]],
        patch_spec: PatchSpecPayload | None,
        expert_gate_decision: ExpertGateDecisionPayload | None = None,
        retry_expert_gate_decision: ExpertGateDecisionPayload | None = None,
        same_run_retry_summary: dict[str, Any] | None = None,
    ) -> str:
        """Derive a stable loop status string from round summaries."""

        if not attack_rounds:
            return "not_started"

        baseline_mode = str(attack_rounds[0].get("mode") or "planned")
        if len(attack_rounds) >= 2:
            parts = [f"baseline_{baseline_mode}"]
            for round_payload in attack_rounds[1:]:
                round_kind = str(round_payload.get("round_kind") or "regression")
                round_mode = str(round_payload.get("mode") or "planned")
                parts.append(f"{round_kind}_{round_mode}")
            status = "_".join(parts)
            final_gate_decision = retry_expert_gate_decision or expert_gate_decision
            if patch_spec is None and final_gate_decision is not None:
                route_target = str(final_gate_decision.route_target or "").strip()
                if route_target == "delivery":
                    return f"{status}_delivery_observation"
                if route_target == "attack_planning_agent" and retry_expert_gate_decision is not None:
                    return f"{status}_retry_capped"
            return status

        if patch_spec is not None:
            return f"baseline_{baseline_mode}_regression_preview_ready"
        if expert_gate_decision is not None:
            route_target = str(expert_gate_decision.route_target or "").strip()
            if route_target == "delivery":
                return f"baseline_{baseline_mode}_delivery_observation"
            if route_target == "attack_planning_agent":
                if bool((same_run_retry_summary or {}).get("blocked_by_budget")):
                    return f"baseline_{baseline_mode}_retry_blocked_by_budget"
                return f"baseline_{baseline_mode}_retry_follow_up"
        return f"baseline_{baseline_mode}"

    def _should_run_patch_flow(
        self,
        expert_gate_decision: ExpertGateDecisionPayload | None,
    ) -> bool:
        """Return whether the current expert-gate route should enter patch flow."""

        if expert_gate_decision is None:
            return True
        return str(expert_gate_decision.route_target or "").strip() == "patch_agent"

    def _should_run_retry_follow_up(
        self,
        expert_gate_decision: ExpertGateDecisionPayload | None,
        *,
        remaining_budget: int = 1,
    ) -> bool:
        """Return whether the current expert-gate route should trigger same-run retry flow."""

        if expert_gate_decision is None:
            return False
        return (
            str(expert_gate_decision.route_target or "").strip() == "attack_planning_agent"
            and remaining_budget > 0
        )

    def _is_retry_follow_up_capped(
        self,
        expert_gate_decision: ExpertGateDecisionPayload | None,
        *,
        remaining_budget: int,
    ) -> bool:
        """Return whether retry was requested again but the same-run budget is exhausted."""

        if expert_gate_decision is None:
            return False
        return (
            str(expert_gate_decision.route_target or "").strip() == "attack_planning_agent"
            and remaining_budget <= 0
        )

    def _resolve_same_run_retry_budget(self, requested_budget: int | None) -> int:
        """Resolve the same-run retry budget with backend defaults and hard caps."""

        raw_budget = (
            settings.same_run_retry_budget_default
            if requested_budget is None
            else requested_budget
        )
        return max(0, min(int(raw_budget or 0), 1))

    def _build_same_run_retry_summary(
        self,
        *,
        expert_gate_decision: ExpertGateDecisionPayload | None,
        retry_attack_decision: AttackDecisionPayload | None,
        retry_attack_projection: ContextProjectionPayload | None,
        retry_attack_dispatch: SandboxDispatchResultPayload | None,
        retry_vulnerability_projection: ContextProjectionPayload | None,
        retry_vulnerability_verdict: VulnerabilityVerdictPayload | None,
        retry_expert_gate_projection: ContextProjectionPayload | None,
        retry_expert_gate_decision: ExpertGateDecisionPayload | None,
        same_run_retry_budget: int,
        same_run_retry_used: int,
        same_run_retry_remaining: int,
        memory_handoffs: list[MemoryHandoffPayload],
    ) -> dict[str, Any]:
        """Build a compact explanation of same-run retry resolution for downstream consumers."""

        initial_route_target = str(getattr(expert_gate_decision, "route_target", "") or "").strip()
        final_gate_decision = retry_expert_gate_decision or expert_gate_decision
        final_route_target = str(getattr(final_gate_decision, "route_target", "") or "").strip()
        requested = initial_route_target == "attack_planning_agent"
        started = bool(same_run_retry_used or retry_attack_decision is not None)
        blocked_by_budget = requested and not started and same_run_retry_budget <= 0
        capped_after_regate = (
            retry_expert_gate_decision is not None
            and final_route_target == "attack_planning_agent"
            and same_run_retry_remaining <= 0
        )

        if not requested:
            final_resolution = "not_requested"
            final_resolution_label = "未请求同轮补充攻击"
        elif blocked_by_budget:
            final_resolution = "blocked_by_budget"
            final_resolution_label = "已请求但被预算关闭"
        elif capped_after_regate:
            final_resolution = "retry_capped_after_regate"
            final_resolution_label = "补充攻击后再次请求已被预算封顶"
        elif started and final_route_target == "patch_agent":
            final_resolution = "patched_after_retry"
            final_resolution_label = "补充攻击后进入修补闭环"
        elif started and final_route_target == "delivery":
            final_resolution = "observed_after_retry"
            final_resolution_label = "补充攻击后转观察收口"
        elif started:
            final_resolution = "retry_started"
            final_resolution_label = "已进入同轮补充攻击"
        else:
            final_resolution = "requested_without_follow_up"
            final_resolution_label = "已请求但尚未进入补充攻击"

        attempt_trace: list[dict[str, Any]] = []
        if requested:
            attempt_status = "blocked" if blocked_by_budget else ("executed" if started else "planned")
            attempt_trace.append(
                {
                    "attempt_index": 1,
                    "budget_before_attempt": same_run_retry_budget,
                    "budget_after_attempt": same_run_retry_remaining,
                    "status": attempt_status,
                    "requested_route_target": initial_route_target,
                    "retry_action": str(getattr(retry_attack_decision, "action", "") or "").strip(),
                    "dispatch_status": str(getattr(retry_attack_dispatch, "status", "") or "").strip(),
                    "verdict_severity": str(
                        getattr(retry_vulnerability_verdict, "severity", "") or ""
                    ).strip(),
                    "planning_projection_ref": self._projection_ref(retry_attack_projection),
                    "vulnerability_projection_ref": self._projection_ref(retry_vulnerability_projection),
                    "expert_gate_projection_ref": self._projection_ref(retry_expert_gate_projection),
                    "planning_handoff_id": self._find_retry_handoff_id(
                        memory_handoffs,
                        to_agent="attack_planning_agent",
                    ),
                    "vulnerability_handoff_id": self._find_retry_handoff_id(
                        memory_handoffs,
                        to_agent="vulnerability_agent",
                    ),
                    "expert_gate_handoff_id": self._find_retry_handoff_id(
                        memory_handoffs,
                        to_agent="expert_gate_agent",
                    ),
                    "final_route_target": final_route_target,
                    "termination_reason": final_resolution,
                }
            )

        return {
            "requested": requested,
            "started": started,
            "blocked_by_budget": blocked_by_budget,
            "capped_after_regate": capped_after_regate,
            "initial_route_target": initial_route_target,
            "final_route_target": final_route_target,
            "max_supported_budget": 1,
            "final_resolution": final_resolution,
            "final_resolution_label": final_resolution_label,
            "attempt_count": len(attempt_trace),
            "attempt_trace": attempt_trace,
        }

    def _projection_ref(self, projection: ContextProjectionPayload | None) -> str:
        """Build a stable projection ref string for retry tracing."""

        if projection is None:
            return ""
        round_id = str(projection.round_id or "main")
        return f"{projection.agent_id}:{round_id}"

    def _find_retry_handoff_id(
        self,
        memory_handoffs: list[MemoryHandoffPayload],
        *,
        to_agent: str,
    ) -> str:
        """Find the most recent retry-related handoff id for a target agent."""

        for item in reversed(memory_handoffs):
            if str(item.to_agent or "").strip() != to_agent:
                continue
            handoff_id = str(item.handoff_id or "").strip()
            projection_round = str(getattr(item.projection, "round_id", "") or "").strip()
            if "retry" in handoff_id or "retry" in projection_round:
                return handoff_id
        return ""

    def _build_expert_gate_follow_up_strategy(
        self,
        expert_gate_decision: ExpertGateDecisionPayload,
    ) -> str:
        """Convert non-patch expert-gate routes into stable reflection strategy labels."""

        route_target = str(expert_gate_decision.route_target or "").strip()
        if route_target == "delivery":
            return "observation-only"
        if route_target == "attack_planning_agent":
            return "retry-attack-planning"
        return "expert-gate-follow-up"

    def _build_expert_gate_follow_up_message(
        self,
        expert_gate_decision: ExpertGateDecisionPayload,
    ) -> str:
        """Create user-facing summaries for non-patch expert-gate routes."""

        route_target = str(expert_gate_decision.route_target or "").strip()
        if route_target == "delivery":
            return "专家闸门判定本轮进入观察收口，不执行 patch flow，已沉淀下一轮优化卡片。"
        if route_target == "attack_planning_agent":
            return "专家闸门建议补充攻击重规划；当前 same-run 自动重试未开启，已先沉淀 follow-up 反思卡片。"
        return "专家闸门未进入 patch flow，已把 follow-up 建议沉淀为下一轮优化卡片。"

    def _build_attack_planning_projection(
        self,
        *,
        state: LangGraphMASState,
        attack_specs: list[AttackSpecPayload] | None = None,
        attack_decision: AttackDecisionPayload | None = None,
        evidence_pack_override: EvidencePackPayload | None = None,
    ) -> ContextProjectionPayload:
        """Build a minimal role-aware context window for the attack planning agent."""
        case_memory = state.get("case_memory")
        evidence_pack = evidence_pack_override or state.get("evidence_pack") or EvidencePackPayload()
        target_service = state["target_service"]
        auditor_rounds = list(state.get("auditor_rounds") or [])
        latest_round = auditor_rounds[-1] if auditor_rounds else None
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="sandbox-budget-1",
                constraint_kind="sandbox_budget",
                value="攻击任务必须在本地受限沙盒预算内执行，不得越界。",
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="sandbox_policy",
            )
        )

        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        if latest_round:
            cards.append(
                MemoryCardPayload(
                    card_id=f"card-{state['run_id'][:8]}-attack-plan-input",
                    card_type="attack_plan_input",
                    case_id=state["case_id"],
                    run_id=state["run_id"],
                    round_id="attack-plan-r1",
                    source_agent="audit_agent",
                    priority="high",
                    priority_label=self._priority_label("high"),
                    summary=f"基于 {latest_round.proposal_id} 的审计结果生成受限攻击计划。",
                    payload={
                        "proposal_id": latest_round.proposal_id,
                        "reasons": latest_round.reasons[:4],
                        "key_findings": latest_round.key_findings[:4],
                        "recommended_changes": latest_round.recommended_changes[:4],
                        "risk_score": latest_round.risk_score,
                        "compliance_score": latest_round.compliance_score,
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )
        if attack_decision:
            cards.append(self._build_attack_decision_card(state=state, attack_decision=attack_decision))
        if evidence_pack.items:
            cards.append(
                self._build_attack_planner_evidence_card(
                    state=state,
                    evidence_pack=evidence_pack,
                    round_id="attack-plan-r1",
                    planning_mode="baseline",
                )
            )

        artifact_refs = [
            self._build_attack_spec_artifact_ref(spec)
            for spec in (attack_specs or [])
        ]

        return ContextProjectionPayload(
            agent_id="attack_planning_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="attack-plan-r1",
            objective="在独立窗口内生成受预算和边界约束的攻击规划。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=target_service,
                    summary=f"攻击目标服务：{target_service.service_version}",
                ),
                *artifact_refs,
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=3),
            token_budget_hint=3200,
        )

    def _build_regression_attack_planning_projection(
        self,
        *,
        state: LangGraphMASState,
        target_service: TargetServiceSpecPayload,
        patch_spec: PatchSpecPayload,
        regression_vulnerability_report: dict[str, Any],
        evidence_pack_override: EvidencePackPayload | None = None,
        prior_attack_results_override: list[AttackResultPayload] | None = None,
        prior_attack_decision_override: AttackDecisionPayload | None = None,
    ) -> ContextProjectionPayload:
        """Build a replan window for the regression attack round."""

        case_memory = state.get("case_memory")
        evidence_pack = evidence_pack_override or state.get("evidence_pack") or EvidencePackPayload()
        attack_results = list(prior_attack_results_override or state.get("attack_results") or [])
        attack_decision = prior_attack_decision_override or state.get("attack_decision")
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="regression-replan-1",
                constraint_kind="regression_replan",
                value="本轮任务是补丁版本回归攻击重规划，需优先验证残余风险与回归焦点。",
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="patch_spec",
            )
        )

        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        if attack_decision:
            cards.append(
                self._build_attack_decision_card(
                    state=state,
                    attack_decision=attack_decision,
                    round_id="attack-plan-r1",
                    summary="上一轮基线攻击决策摘要，供回归重规划参考。",
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-attack-replan",
                card_type="attack_replan_input",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="attack-plan-r2",
                source_agent="patch_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="补丁已落地，需要基于上一轮攻击结果生成回归攻击重规划。",
                payload={
                    "planning_mode": "regression",
                    "patch_id": patch_spec.patch_id,
                    "patch_summary": patch_spec.summary,
                    "patch_rationale": patch_spec.rationale,
                    "validation_steps": list(patch_spec.validation_steps or []),
                    "regression_focus": list(patch_spec.regression_focus or []),
                    "prior_attack_count": len(attack_results),
                    "prior_findings": [finding for item in attack_results[:3] for finding in item.findings[:2]][:6],
                    "risk_score": int(regression_vulnerability_report.get("risk_score", 0)),
                    "baseline_risk_score": int(regression_vulnerability_report.get("baseline_risk_score", 0)),
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        if evidence_pack.items:
            cards.append(
                self._build_attack_planner_evidence_card(
                    state=state,
                    evidence_pack=evidence_pack,
                    round_id="attack-plan-r2",
                    planning_mode="regression",
                )
            )

        return ContextProjectionPayload(
            agent_id="attack_planning_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="attack-plan-r2",
            objective="在独立窗口内基于补丁信息与上一轮攻击结果生成回归攻击重规划。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=target_service,
                    artifact_type="regression_target_service",
                    summary=f"待回归验证的补丁版本目标服务：{target_service.service_version}",
                ),
                *self._build_attack_artifact_refs(attack_results),
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=3),
            token_budget_hint=3200,
        )

    def _build_vulnerability_projection(
        self,
        *,
        state: LangGraphMASState,
    ) -> ContextProjectionPayload:
        """Build a minimal role-aware context window for the vulnerability agent."""
        case_memory = state.get("case_memory")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        target_service = state["target_service"]
        attack_decision = state.get("attack_decision")
        attack_results = list(state.get("attack_results") or [])
        final_vulnerability_report = state.get("final_vulnerability_report") or {}
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )

        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        if attack_decision:
            cards.append(self._build_attack_decision_card(state=state, attack_decision=attack_decision))
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-attack-result-summary",
                card_type="attack_result_summary",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="vulnerability-r1",
                source_agent="attack_planning_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="攻击执行摘要，供漏洞评估 Agent 进行裁决。",
                payload=self._build_attack_result_summary_payload(
                    attack_results=attack_results,
                    vulnerability_report=final_vulnerability_report,
                ),
                created_at=datetime.now(timezone.utc),
            )
        )

        return ContextProjectionPayload(
            agent_id="vulnerability_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="vulnerability-r1",
            objective="在独立窗口内综合攻击结果与既有漏洞报告形成结构化裁决。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=target_service,
                    summary="待评估的目标服务与攻击工件集合。",
                ),
                *self._build_attack_artifact_refs(attack_results),
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=3),
            token_budget_hint=2800,
        )

    def _build_regression_vulnerability_projection(
        self,
        *,
        state: LangGraphMASState,
        target_service: TargetServiceSpecPayload,
        attack_decision: AttackDecisionPayload | None,
        attack_results: list[AttackResultPayload],
        vulnerability_report: dict[str, Any],
        baseline_verdict: VulnerabilityVerdictPayload,
    ) -> ContextProjectionPayload:
        """Build a dedicated regression-risk window for the vulnerability agent."""

        case_memory = state.get("case_memory")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="regression-residual-risk-1",
                constraint_kind="regression_goal",
                value="需要判断补丁版本的残余风险是否已收敛，并给出回归质量结论。",
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="workflow_policy",
            )
        )

        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        if attack_decision:
            cards.append(
                self._build_attack_decision_card(
                    state=state,
                    attack_decision=attack_decision,
                    round_id="attack-plan-r2",
                    summary="补丁版本回归攻击决策摘要，供漏洞评估 Agent 判断残余风险。",
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-baseline-verdict-reference",
                card_type="baseline_verdict_reference",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="vulnerability-r2",
                source_agent="vulnerability_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="基线漏洞裁决摘要，供回归风险收敛判断参考。",
                payload=baseline_verdict.model_dump(mode="json"),
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-regression-attack-result-summary",
                card_type="attack_result_summary",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="vulnerability-r2",
                source_agent="patch_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="补丁版本回归攻击摘要，供漏洞评估 Agent 判断残余风险与回归质量。",
                payload=self._build_attack_result_summary_payload(
                    attack_results=attack_results,
                    vulnerability_report=vulnerability_report,
                    evaluation_mode="regression",
                    baseline_verdict=baseline_verdict,
                ),
                created_at=datetime.now(timezone.utc),
            )
        )

        return ContextProjectionPayload(
            agent_id="vulnerability_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="vulnerability-r2",
            objective="在独立窗口内评估补丁版本的残余风险与回归质量。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=target_service,
                    artifact_type="regression_target_service",
                    summary="待评估的补丁版本目标服务与回归攻击工件集合。",
                ),
                *self._build_attack_artifact_refs(attack_results),
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=3),
            token_budget_hint=2800,
        )

    def _build_expert_gate_projection(
        self,
        *,
        state: LangGraphMASState,
    ) -> ContextProjectionPayload:
        """Build an isolated cognition window for the expert gate agent."""

        case_memory = state.get("case_memory")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        target_service = state["target_service"]
        verdict = state["vulnerability_verdict"]
        attack_results = list(state.get("attack_results") or [])
        auditor_rounds = list(state.get("auditor_rounds") or [])
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="expert-gate-1",
                constraint_kind="expert_gate",
                value="需要先做漏洞放行裁决，再决定是否进入修补收口。",
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="workflow_policy",
            )
        )

        attack_artifact_summary = self._build_attack_artifact_summary_payload(attack_results)
        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-expert-gate-input",
                card_type="expert_gate_input",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="expert-gate-r1",
                source_agent="vulnerability_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="专家闸门输入卡，汇总漏洞结论、攻击证据与审计整改建议。",
                payload={
                    "target_service_ref": target_service.service_id,
                    "severity": verdict.severity,
                    "severity_label": verdict.severity_label,
                    "exploitability": verdict.exploitability,
                    "remediation_priority": verdict.remediation_priority,
                    "vulnerability_summary": verdict.summary,
                    "affected_components": verdict.affected_components[:4],
                    "evidence_refs": verdict.evidence_refs[:4],
                    "top_findings": list(attack_artifact_summary.get("top_findings") or [])[:6],
                    "attack_result_summaries": list(
                        attack_artifact_summary.get("attack_result_summaries") or []
                    )[:4],
                    "artifact_refs": list(attack_artifact_summary.get("artifact_refs") or [])[:8],
                    "audit_reasons": (
                        list(auditor_rounds[-1].reasons[:4])
                        if auditor_rounds
                        else []
                    ),
                    "audit_recommended_changes": (
                        list(auditor_rounds[-1].recommended_changes[:4])
                        if auditor_rounds
                        else []
                    ),
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-verdict",
                card_type="vulnerability_verdict",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="expert-gate-r1",
                source_agent="vulnerability_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary=verdict.summary,
                payload={
                    "severity": verdict.severity,
                    "severity_label": verdict.severity_label,
                    "affected_components": verdict.affected_components[:4],
                    "evidence_refs": verdict.evidence_refs[:4],
                    "verdict": verdict.model_dump(mode="json"),
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        if auditor_rounds:
            latest_round = auditor_rounds[-1]
            cards.append(
                MemoryCardPayload(
                    card_id=f"card-{state['run_id'][:8]}-audit-round",
                    card_type="audit_decision",
                    case_id=state["case_id"],
                    run_id=state["run_id"],
                    round_id=f"audit-r{latest_round.round}",
                    source_agent="audit_agent",
                    priority="medium",
                    priority_label=self._priority_label("medium"),
                    summary=f"{latest_round.proposal_id} 的最新审计裁决为 {latest_round.verdict_label}。",
                    payload={
                        "proposal_id": latest_round.proposal_id,
                        "reasons": latest_round.reasons[:4],
                        "recommended_changes": latest_round.recommended_changes[:4],
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-attack-artifact-summary",
                card_type="attack_artifact_summary",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="expert-gate-r1",
                source_agent="attack_planning_agent",
                priority="medium",
                priority_label=self._priority_label("medium"),
                summary="攻击工件摘要，供 Expert Gate Agent 判断放行、修补或补充攻击。",
                payload=attack_artifact_summary,
                created_at=datetime.now(timezone.utc),
            )
        )

        return ContextProjectionPayload(
            agent_id="expert_gate_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="expert-gate-r1",
            objective="在独立窗口内完成漏洞放行裁决，并决定是否进入修补收口。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=target_service,
                    summary=f"待专家闸门裁决的目标服务版本：{target_service.service_version}",
                ),
                *self._build_attack_artifact_refs(attack_results),
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=4),
            token_budget_hint=3200,
        )

    def _build_patch_projection(
        self,
        *,
        state: LangGraphMASState,
        expert_gate_decision: ExpertGateDecisionPayload | None = None,
        target_service_override: TargetServiceSpecPayload | None = None,
        verdict_override: VulnerabilityVerdictPayload | None = None,
        attack_results_override: list[AttackResultPayload] | None = None,
        round_id: str = "patch-r1",
    ) -> ContextProjectionPayload:
        """Build a minimal role-aware context window for the patch agent."""
        case_memory = state.get("case_memory")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        target_service = target_service_override or state["target_service"]
        verdict = verdict_override or state["vulnerability_verdict"]
        attack_results = list(attack_results_override or state.get("attack_results") or [])
        auditor_rounds = list(state.get("auditor_rounds") or [])
        gate_decision = expert_gate_decision or state.get("expert_gate_decision")
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="remediation-priority-1",
                constraint_kind="remediation_priority",
                value=f"修补优先级：{verdict.remediation_priority_label}",
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="vulnerability_verdict",
            )
        )
        if gate_decision:
            constraints.append(
                ContextConstraintPayload(
                    constraint_id="expert-gate-action-1",
                    constraint_kind="expert_gate_action",
                    value=f"专家闸门动作：{gate_decision.action_label}",
                    priority="high",
                    priority_label=self._priority_label("high"),
                    confirmed=True,
                    source="expert_gate_decision",
                )
            )

        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-verdict",
                card_type="vulnerability_verdict",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id=round_id,
                source_agent="vulnerability_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary=verdict.summary,
                payload={
                    "severity": verdict.severity,
                    "severity_label": verdict.severity_label,
                    "affected_components": verdict.affected_components[:4],
                    "evidence_refs": verdict.evidence_refs[:4],
                    "verdict": verdict.model_dump(mode="json"),
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        if auditor_rounds:
            latest_round = auditor_rounds[-1]
            cards.append(
                MemoryCardPayload(
                    card_id=f"card-{state['run_id'][:8]}-audit-round",
                    card_type="audit_decision",
                    case_id=state["case_id"],
                    run_id=state["run_id"],
                    round_id=f"audit-r{latest_round.round}",
                    source_agent="audit_agent",
                    priority="medium",
                    priority_label=self._priority_label("medium"),
                    summary=f"{latest_round.proposal_id} 的最新审计裁决为 {latest_round.verdict_label}。",
                    payload={
                        "proposal_id": latest_round.proposal_id,
                        "reasons": latest_round.reasons[:4],
                        "recommended_changes": latest_round.recommended_changes[:4],
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )
        if gate_decision:
            cards.append(
                MemoryCardPayload(
                    card_id=f"card-{state['run_id'][:8]}-expert-gate-decision",
                    card_type="expert_gate_decision",
                    case_id=state["case_id"],
                    run_id=state["run_id"],
                    round_id=round_id,
                    source_agent="expert_gate_agent",
                    priority="high",
                    priority_label=self._priority_label("high"),
                    summary=gate_decision.residual_risk_summary or gate_decision.action_label,
                    payload={
                        "decision_family": gate_decision.decision_family,
                        "decision_family_label": gate_decision.decision_family_label,
                        "action": gate_decision.action,
                        "action_label": gate_decision.action_label,
                        "route_target": gate_decision.route_target,
                        "route_target_label": gate_decision.route_target_label,
                        "rationale": gate_decision.rationale,
                        "confidence": gate_decision.confidence,
                        "residual_risk_summary": gate_decision.residual_risk_summary,
                        "follow_up_actions": gate_decision.follow_up_actions[:4],
                        "decision": gate_decision.model_dump(mode="json"),
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-attack-artifact-summary",
                card_type="attack_artifact_summary",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id=round_id,
                source_agent="attack_planning_agent",
                priority="medium",
                priority_label=self._priority_label("medium"),
                summary="攻击工件摘要，供 patch Agent 规划修补动作与回归重点。",
                payload=self._build_attack_artifact_summary_payload(attack_results),
                created_at=datetime.now(timezone.utc),
            )
        )

        artifact_refs = [
            self._build_target_service_artifact_ref(
                target_service=target_service,
                summary=f"待修补的服务版本：{target_service.service_version}",
            ),
            *self._build_attack_artifact_refs(attack_results),
        ]

        return ContextProjectionPayload(
            agent_id="patch_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id=round_id,
            objective="基于漏洞裁决、攻击工件和审计结论生成修补与回归方案。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=artifact_refs,
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=4),
            token_budget_hint=3600,
        )

    def _build_retry_expert_gate_projection(
        self,
        *,
        state: LangGraphMASState,
        target_service: TargetServiceSpecPayload,
        retry_attack_decision: AttackDecisionPayload | None,
        retry_attack_results: list[AttackResultPayload],
        retry_vulnerability_verdict: VulnerabilityVerdictPayload,
        prior_expert_gate_decision: ExpertGateDecisionPayload,
    ) -> ContextProjectionPayload:
        """Build a second expert-gate window after same-run retry collects new evidence."""

        case_memory = state.get("case_memory")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="expert-gate-2",
                constraint_kind="expert_gate_reentry",
                value="同轮补充攻击已完成，需要基于新增证据执行二次专家闸门裁决。",
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="workflow_policy",
            )
        )

        attack_artifact_summary = self._build_attack_artifact_summary_payload(retry_attack_results)
        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        if retry_attack_decision:
            cards.append(
                self._build_attack_decision_card(
                    state=state,
                    attack_decision=retry_attack_decision,
                    round_id="attack-plan-r2",
                    summary="同轮补充攻击决策摘要，供二次专家闸门判断是否继续补充验证或进入修补收口。",
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-expert-gate-retry-input",
                card_type="expert_gate_input",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="expert-gate-r2",
                source_agent="vulnerability_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="二次专家闸门输入卡，汇总补充攻击后的漏洞结论与新增证据。",
                payload={
                    "target_service_ref": target_service.service_id,
                    "severity": retry_vulnerability_verdict.severity,
                    "severity_label": retry_vulnerability_verdict.severity_label,
                    "exploitability": retry_vulnerability_verdict.exploitability,
                    "remediation_priority": retry_vulnerability_verdict.remediation_priority,
                    "vulnerability_summary": retry_vulnerability_verdict.summary,
                    "affected_components": retry_vulnerability_verdict.affected_components[:4],
                    "evidence_refs": retry_vulnerability_verdict.evidence_refs[:4],
                    "top_findings": list(attack_artifact_summary.get("top_findings") or [])[:6],
                    "attack_result_summaries": list(
                        attack_artifact_summary.get("attack_result_summaries") or []
                    )[:4],
                    "artifact_refs": list(attack_artifact_summary.get("artifact_refs") or [])[:8],
                    "previous_route_target": prior_expert_gate_decision.route_target,
                    "previous_follow_up_actions": list(prior_expert_gate_decision.follow_up_actions or [])[:4],
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-retry-verdict",
                card_type="vulnerability_verdict",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="expert-gate-r2",
                source_agent="vulnerability_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary=retry_vulnerability_verdict.summary,
                payload={
                    "severity": retry_vulnerability_verdict.severity,
                    "severity_label": retry_vulnerability_verdict.severity_label,
                    "affected_components": retry_vulnerability_verdict.affected_components[:4],
                    "evidence_refs": retry_vulnerability_verdict.evidence_refs[:4],
                    "verdict": retry_vulnerability_verdict.model_dump(mode="json"),
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-expert-gate-r1-decision",
                card_type="expert_gate_decision",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="expert-gate-r2",
                source_agent="expert_gate_agent",
                priority="medium",
                priority_label=self._priority_label("medium"),
                summary=prior_expert_gate_decision.residual_risk_summary or prior_expert_gate_decision.action_label,
                payload=prior_expert_gate_decision.model_dump(mode="json"),
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-retry-attack-artifact-summary",
                card_type="attack_artifact_summary",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="expert-gate-r2",
                source_agent="attack_planning_agent",
                priority="medium",
                priority_label=self._priority_label("medium"),
                summary="补充攻击工件摘要，供二次 Expert Gate 判断放行、修补或达到本轮 retry 上限。",
                payload=attack_artifact_summary,
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            self._build_retry_context_summary_card(
                state=state,
                round_id="expert-gate-r2",
                source_agent="vulnerability_agent",
                summary="同轮补充攻击后的二次专家闸门摘要卡，供后续多轮 retry lineage / compression 复用。",
                stage_label="expert_gate_retry",
                upstream_projection_refs=[
                    "attack_planning_agent:attack-plan-r2",
                    "vulnerability_agent:vulnerability-r2",
                ],
                upstream_handoff_ids=[f"handoff-{state['run_id'][:8]}-expert-gate-retry"],
                focus_points=[retry_vulnerability_verdict.summary]
                + list(prior_expert_gate_decision.follow_up_actions or [])[:3],
            )
        )

        return ContextProjectionPayload(
            agent_id="expert_gate_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="expert-gate-r2",
            objective="在独立窗口内基于补充攻击后的新证据完成二次专家闸门裁决。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=target_service,
                    summary=f"待二次专家闸门裁决的目标服务版本：{target_service.service_version}",
                ),
                *self._build_attack_artifact_refs(retry_attack_results),
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=4),
            token_budget_hint=3200,
        )

    def _build_reflection_projection(
        self,
        *,
        state: LangGraphMASState,
        patch_spec: PatchSpecPayload,
        patch_execution: PatchExecutionPayload,
        patch_artifact_summary: dict[str, Any],
        regression_target_service: TargetServiceSpecPayload,
        regression_attack_results: list[AttackResultPayload],
        regression_vulnerability_verdict: VulnerabilityVerdictPayload,
        ) -> ContextProjectionPayload:
        """Build a minimal role-aware context window for the reflection agent."""
        case_memory = state.get("case_memory")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="reflection-loop-1",
                constraint_kind="closed_loop",
                value="需要将本轮修补与回归结果沉淀为下一轮生成与审计可复用的反思卡。",
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="workflow_policy",
            )
        )

        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-reflection",
                card_type="reflection_summary",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="reflection-r1",
                source_agent="patch_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="修补与回归后的反思摘要，供下一轮提示词与策略优化使用。",
                payload={
                    "patch_id": patch_spec.patch_id,
                    "next_version": patch_spec.next_version,
                    "regression_severity": regression_vulnerability_verdict.severity_label,
                    "patch_spec": patch_spec.model_dump(mode="json"),
                    "regression_vulnerability_verdict": regression_vulnerability_verdict.model_dump(mode="json"),
                    "regression_attack_result_summaries": self.artifact_summarizer.summarize_attack_results(
                        regression_attack_results
                    ),
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-regression-verdict",
                card_type="regression_verdict_input",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="reflection-r1",
                source_agent="vulnerability_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary=regression_vulnerability_verdict.summary,
                payload={
                    "severity": regression_vulnerability_verdict.severity,
                    "severity_label": regression_vulnerability_verdict.severity_label,
                    "affected_components": regression_vulnerability_verdict.affected_components[:4],
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-patch-execution",
                card_type="patch_execution",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="reflection-r1",
                source_agent="patch_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary=patch_execution.summary,
                payload=patch_execution.model_dump(mode="json"),
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-patch-artifacts",
                card_type="patch_artifact_summary",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="reflection-r1",
                source_agent="patch_agent",
                priority="medium",
                priority_label=self._priority_label("medium"),
                summary="补丁工件与实现增量摘要，供反思阶段判断修补覆盖范围与下一轮优化方向。",
                payload=patch_artifact_summary,
                created_at=datetime.now(timezone.utc),
            )
        )

        return ContextProjectionPayload(
            agent_id="reflection_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="reflection-r1",
            objective="在独立窗口内沉淀下一轮生成、审计与修补的优化卡片。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=regression_target_service,
                    artifact_type="regression_target_service",
                    summary=regression_vulnerability_verdict.summary,
                ),
                *self._build_patch_artifact_refs(patch_artifact_summary),
                *self._build_attack_artifact_refs(regression_attack_results),
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=2),
            token_budget_hint=2600,
        )

    def _build_expert_gate_follow_up_reflection_projection(
        self,
        *,
        state: LangGraphMASState,
        expert_gate_decision: ExpertGateDecisionPayload,
    ) -> ContextProjectionPayload:
        """Build a reflection window for non-patch expert-gate routes."""

        case_memory = state.get("case_memory")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        target_service = state["target_service"]
        verdict = state["vulnerability_verdict"]
        attack_results = list(state.get("attack_results") or [])
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="expert-gate-follow-up-1",
                constraint_kind="expert_gate_route",
                value=(
                    "本轮未进入 patch flow，需要把专家闸门的"
                    f"{expert_gate_decision.route_target_label}建议沉淀为下一轮优化卡片。"
                ),
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="expert_gate_decision",
            )
        )

        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-follow-up-reflection",
                card_type="reflection_summary",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="reflection-r1",
                source_agent="expert_gate_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="专家闸门未进入 patch flow，需沉淀观察/补充验证结论供下一轮优化复用。",
                payload={
                    "patch_id": "",
                    "next_version": target_service.service_version,
                    "regression_severity": verdict.severity_label,
                    "patch_spec": {
                        "patch_id": "",
                        "target_service_ref": target_service.service_id,
                        "strategy": self._build_expert_gate_follow_up_strategy(expert_gate_decision),
                        "summary": expert_gate_decision.rationale,
                        "rationale": expert_gate_decision.residual_risk_summary,
                        "changed_artifacts": [],
                        "implementation_notes": list(expert_gate_decision.follow_up_actions or [])[:4],
                        "validation_steps": [],
                        "rollback_notes": [],
                        "next_version": target_service.service_version,
                        "regression_focus": [],
                    },
                    "regression_vulnerability_verdict": verdict.model_dump(mode="json"),
                    "regression_attack_result_summaries": self.artifact_summarizer.summarize_attack_results(
                        attack_results
                    ),
                    "expert_gate_decision": expert_gate_decision.model_dump(mode="json"),
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-follow-up-verdict",
                card_type="regression_verdict_input",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="reflection-r1",
                source_agent="vulnerability_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary=verdict.summary,
                payload={
                    "severity": verdict.severity,
                    "severity_label": verdict.severity_label,
                    "affected_components": verdict.affected_components[:4],
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-expert-gate-follow-up",
                card_type="expert_gate_decision",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="reflection-r1",
                source_agent="expert_gate_agent",
                priority="medium",
                priority_label=self._priority_label("medium"),
                summary=expert_gate_decision.residual_risk_summary or expert_gate_decision.action_label,
                payload=expert_gate_decision.model_dump(mode="json"),
                created_at=datetime.now(timezone.utc),
            )
        )

        return ContextProjectionPayload(
            agent_id="reflection_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="reflection-r1",
            objective="在未进入 patch flow 的情况下沉淀下一轮 generation / audit / attack planning 可复用的反思卡片。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=target_service,
                    artifact_type="target_service",
                    summary=expert_gate_decision.rationale or verdict.summary,
                ),
                *self._build_attack_artifact_refs(attack_results),
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=2),
            token_budget_hint=2200,
        )

    def _build_retry_attack_planning_projection(
        self,
        *,
        state: LangGraphMASState,
        target_service: TargetServiceSpecPayload,
        expert_gate_decision: ExpertGateDecisionPayload,
        baseline_verdict: VulnerabilityVerdictPayload,
        evidence_pack_override: EvidencePackPayload | None = None,
    ) -> ContextProjectionPayload:
        """Build a same-run retry planning window after Expert Gate requests more attack validation."""

        case_memory = state.get("case_memory")
        evidence_pack = evidence_pack_override or state.get("evidence_pack") or EvidencePackPayload()
        attack_results = list(state.get("attack_results") or [])
        attack_decision = state.get("attack_decision")
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="same-run-retry-1",
                constraint_kind="retry_goal",
                value="专家闸门要求同轮补充攻击验证，需要围绕残余风险与 follow-up action 继续收口证据。",
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="expert_gate_decision",
            )
        )

        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        if attack_decision:
            cards.append(
                self._build_attack_decision_card(
                    state=state,
                    attack_decision=attack_decision,
                    round_id="attack-plan-r1",
                    summary="上一轮基线攻击决策摘要，供同轮补充攻击规划参考。",
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-retry-attack-input",
                card_type="attack_replan_input",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="attack-plan-r2",
                source_agent="expert_gate_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="专家闸门判定需要补充攻击验证，本轮进入同轮补充攻击重规划。",
                payload={
                    "planning_mode": "retry",
                    "expert_gate_decision_family": expert_gate_decision.decision_family,
                    "expert_gate_action": expert_gate_decision.action,
                    "expert_gate_route_target": expert_gate_decision.route_target,
                    "expert_gate_rationale": expert_gate_decision.rationale,
                    "residual_risk_summary": expert_gate_decision.residual_risk_summary,
                    "follow_up_actions": list(expert_gate_decision.follow_up_actions or [])[:4],
                    "baseline_severity": baseline_verdict.severity,
                    "baseline_severity_label": baseline_verdict.severity_label,
                    "baseline_summary": baseline_verdict.summary,
                    "prior_attack_count": len(attack_results),
                    "prior_findings": [finding for item in attack_results[:3] for finding in item.findings[:2]][:6],
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        if evidence_pack.items:
            cards.append(
                self._build_attack_planner_evidence_card(
                    state=state,
                    evidence_pack=evidence_pack,
                    round_id="attack-plan-r2",
                    planning_mode="retry",
                )
            )
        cards.append(
            self._build_retry_context_summary_card(
                state=state,
                round_id="attack-plan-r2",
                source_agent="expert_gate_agent",
                summary="同轮补充攻击重规划摘要卡，供后续多轮 retry lineage / compression 复用。",
                stage_label="attack_planning_retry",
                upstream_projection_refs=["expert_gate_agent:expert-gate-r1"],
                upstream_handoff_ids=[f"handoff-{state['run_id'][:8]}-attack-retry"],
                focus_points=list(expert_gate_decision.follow_up_actions or [])[:4],
            )
        )

        return ContextProjectionPayload(
            agent_id="attack_planning_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="attack-plan-r2",
            objective="在独立窗口内基于专家闸门 follow-up 建议执行同轮补充攻击重规划。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=target_service,
                    summary=f"同轮补充攻击的目标服务：{target_service.service_version}",
                ),
                *self._build_attack_artifact_refs(attack_results),
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=3),
            token_budget_hint=3000,
        )

    def _build_retry_vulnerability_projection(
        self,
        *,
        state: LangGraphMASState,
        target_service: TargetServiceSpecPayload,
        attack_decision: AttackDecisionPayload | None,
        attack_results: list[AttackResultPayload],
        vulnerability_report: dict[str, Any],
        baseline_verdict: VulnerabilityVerdictPayload,
        expert_gate_decision: ExpertGateDecisionPayload,
    ) -> ContextProjectionPayload:
        """Build a same-run retry vulnerability window after extra attack evidence is collected."""

        case_memory = state.get("case_memory")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="retry-vulnerability-1",
                constraint_kind="retry_validation_goal",
                value="需要基于同轮补充攻击结果重新判断漏洞证据是否足够收敛。",
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="expert_gate_decision",
            )
        )

        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        if attack_decision:
            cards.append(
                self._build_attack_decision_card(
                    state=state,
                    attack_decision=attack_decision,
                    round_id="attack-plan-r2",
                    summary="同轮补充攻击决策摘要，供漏洞评估 Agent 复核。",
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-retry-baseline-verdict-reference",
                card_type="baseline_verdict_reference",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="vulnerability-r2",
                source_agent="expert_gate_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="基线漏洞裁决摘要，供同轮补充验证复核参考。",
                payload={
                    **baseline_verdict.model_dump(mode="json"),
                    "expert_gate_decision": expert_gate_decision.model_dump(mode="json"),
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-retry-attack-result-summary",
                card_type="attack_result_summary",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="vulnerability-r2",
                source_agent="attack_planning_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary="同轮补充攻击摘要，供漏洞评估 Agent 形成补充裁决。",
                payload=self._build_attack_result_summary_payload(
                    attack_results=attack_results,
                    vulnerability_report=vulnerability_report,
                    evaluation_mode="retry",
                    baseline_verdict=baseline_verdict,
                ),
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            self._build_retry_context_summary_card(
                state=state,
                round_id="vulnerability-r2",
                source_agent="attack_planning_agent",
                summary="同轮补充漏洞评估摘要卡，供后续多轮 retry lineage / compression 复用。",
                stage_label="vulnerability_evaluation_retry",
                upstream_projection_refs=["attack_planning_agent:attack-plan-r2"],
                upstream_handoff_ids=[f"handoff-{state['run_id'][:8]}-vulnerability-retry"],
                focus_points=[baseline_verdict.summary] + list(expert_gate_decision.follow_up_actions or [])[:3],
            )
        )

        return ContextProjectionPayload(
            agent_id="vulnerability_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="vulnerability-r2",
            objective="在独立窗口内基于同轮补充攻击结果形成补充漏洞裁决。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=target_service,
                    summary="同轮补充验证的目标服务与攻击工件集合。",
                ),
                *self._build_attack_artifact_refs(attack_results),
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=3),
            token_budget_hint=2600,
        )

    def _build_retry_follow_up_reflection_projection(
        self,
        *,
        state: LangGraphMASState,
        target_service: TargetServiceSpecPayload,
        expert_gate_decision: ExpertGateDecisionPayload,
        retry_attack_decision: AttackDecisionPayload | None,
        retry_attack_results: list[AttackResultPayload],
        retry_vulnerability_verdict: VulnerabilityVerdictPayload,
        capped_retry: bool = False,
    ) -> ContextProjectionPayload:
        """Build a follow-up reflection window after same-run retry finishes."""

        case_memory = state.get("case_memory")
        evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        constraints = self._build_context_constraints(
            structured_spec=state.get("structured_spec") or {},
            case_memory=case_memory,
        )
        constraints.append(
            ContextConstraintPayload(
                constraint_id="retry-reflection-1",
                constraint_kind="retry_follow_up",
                value=(
                    "需要把同轮补充攻击、二次专家闸门裁决与补充漏洞裁决沉淀为下一轮 generation / audit / attack planning 可复用的反思卡片。"
                    if not capped_retry
                    else "二次专家闸门仍建议继续补充攻击，但当前 same-run re-gate 已达到上限，需要先沉淀 follow-up reflection cards。"
                ),
                priority="high",
                priority_label=self._priority_label("high"),
                confirmed=True,
                source="workflow_policy",
            )
        )

        cards: list[MemoryCardPayload] = []
        if case_memory:
            cards.append(
                self._build_case_memory_card(
                    case_memory=case_memory,
                    run_id=state["run_id"],
                    source_agent="case_memory_service",
                )
            )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-retry-reflection-summary",
                card_type="reflection_summary",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="reflection-r1",
                source_agent="vulnerability_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary=(
                    "同轮补充攻击与二次专家闸门已收口，需要沉淀下一轮优化结论。"
                    if not capped_retry
                    else "同轮补充攻击后已达到 re-gate 上限，需要先沉淀下一轮优化结论。"
                ),
                payload={
                    "patch_id": "",
                    "next_version": target_service.service_version,
                    "regression_severity": retry_vulnerability_verdict.severity_label,
                    "patch_spec": {
                        "patch_id": "",
                        "target_service_ref": target_service.service_id,
                        "strategy": self._build_expert_gate_follow_up_strategy(expert_gate_decision),
                        "summary": expert_gate_decision.rationale,
                        "rationale": retry_vulnerability_verdict.summary,
                        "changed_artifacts": [],
                        "implementation_notes": list(expert_gate_decision.follow_up_actions or [])[:4],
                        "validation_steps": [],
                        "rollback_notes": [],
                        "next_version": target_service.service_version,
                        "regression_focus": [],
                    },
                    "regression_vulnerability_verdict": retry_vulnerability_verdict.model_dump(mode="json"),
                    "regression_attack_result_summaries": self.artifact_summarizer.summarize_attack_results(
                        retry_attack_results
                    ),
                    "expert_gate_decision": expert_gate_decision.model_dump(mode="json"),
                    "retry_attack_decision": (
                        retry_attack_decision.model_dump(mode="json") if retry_attack_decision else {}
                    ),
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        cards.append(
            MemoryCardPayload(
                card_id=f"card-{state['run_id'][:8]}-retry-regression-verdict",
                card_type="regression_verdict_input",
                case_id=state["case_id"],
                run_id=state["run_id"],
                round_id="reflection-r1",
                source_agent="vulnerability_agent",
                priority="high",
                priority_label=self._priority_label("high"),
                summary=retry_vulnerability_verdict.summary,
                payload={
                    "severity": retry_vulnerability_verdict.severity,
                    "severity_label": retry_vulnerability_verdict.severity_label,
                    "affected_components": retry_vulnerability_verdict.affected_components[:4],
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        if retry_attack_decision:
            cards.append(
                self._build_attack_decision_card(
                    state=state,
                    attack_decision=retry_attack_decision,
                    round_id="attack-plan-r2",
                    summary="同轮补充攻击决策摘要，供反思 Agent 沉淀后续优化建议。",
                )
            )

        return ContextProjectionPayload(
            agent_id="reflection_agent",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id="reflection-r1",
            objective="在同轮补充攻击后沉淀下一轮 generation / audit / attack planning 可复用的反思卡片。",
            constraints=constraints,
            cards=self._finalize_projection_cards(cards),
            artifact_refs=[
                self._build_target_service_artifact_ref(
                    target_service=target_service,
                    artifact_type="target_service",
                    summary=retry_vulnerability_verdict.summary,
                ),
                *self._build_attack_artifact_refs(retry_attack_results),
            ],
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=2),
            token_budget_hint=2400,
        )

    def _build_context_constraints(
        self,
        *,
        structured_spec: dict[str, Any],
        case_memory: CaseMemoryPayload | None,
        clarifications: list[Any] | None = None,
    ) -> list[ContextConstraintPayload]:
        """Project a compact constraint slice into a single agent window."""
        constraints: list[ContextConstraintPayload] = []

        def append_constraint(
            *,
            kind: str,
            value: str,
            priority: str = "high",
            confirmed: bool = True,
            source: str = "structured_spec",
        ) -> None:
            text = str(value or "").strip()
            if not text:
                return
            constraints.append(
                ContextConstraintPayload(
                    constraint_id=f"{kind}-{len(constraints) + 1}",
                    constraint_kind=kind,
                    value=text,
                    priority=priority,
                    priority_label=self._priority_label(priority),
                    confirmed=confirmed,
                    source=source,
                )
            )

        domain = str(structured_spec.get("domain") or "").strip()
        if domain:
            append_constraint(kind="domain", value=f"业务场景：{display_scenario(domain)}")
        compliance = str(structured_spec.get("compliance") or "").strip()
        if compliance:
            append_constraint(kind="compliance", value=f"合规目标：{compliance}")
        platform = str(structured_spec.get("platform") or "").strip()
        if platform:
            append_constraint(kind="platform", value=f"部署平台：{platform}", priority="medium")
        latency = str(structured_spec.get("max_latency") or "").strip()
        if latency:
            append_constraint(kind="latency", value=f"延迟目标：{latency}")
        if structured_spec.get("quantum_safe") is True:
            append_constraint(kind="quantum_safe", value="后量子安全要求：是")
        construction_summary = build_construction_context_summary(structured_spec)
        if construction_summary:
            append_constraint(kind="construction_model", value=construction_summary)

        for item in (case_memory.confirmed_constraints[:3] if case_memory else []):
            append_constraint(kind="case_memory", value=item, priority="medium", source="case_memory")

        for item in list(clarifications or [])[:2]:
            question = str(getattr(item, "question", "") or "").strip()
            if not question:
                continue
            append_constraint(
                kind="clarification",
                value=f"待关注澄清：{question}",
                priority="medium",
                confirmed=not bool(getattr(item, "required", False)),
                source="clarification",
            )

        return constraints

    def _build_evidence_refs(
        self,
        evidence_pack: EvidencePackPayload,
        *,
        limit: int = 4,
    ) -> list[EvidenceRefPayload]:
        """Convert retrieved evidence into compact refs suitable for agent windows."""
        refs: list[EvidenceRefPayload] = []
        for item in evidence_pack.items[:limit]:
            refs.append(
                EvidenceRefPayload(
                    doc_id=item.doc_id,
                    chunk_id=item.chunk_id,
                    title=item.title,
                    section=item.section,
                    snippet=item.snippet[:240],
                    source_page=item.source_page,
                    score=item.score,
                    metadata=item.metadata,
                )
            )
        return refs

    def _retrieve_attack_planning_evidence(
        self,
        *,
        retrieval_service: KnowledgeRetrievalService,
        state: LangGraphMASState,
        target_service: TargetServiceSpecPayload,
        planning_mode: str,
        prior_findings: list[str] | None = None,
        regression_focus: list[str] | None = None,
    ) -> EvidencePackPayload:
        """Build planner-scoped retrieval evidence without changing the global evidence pack."""

        payload = state["payload"]
        evidence_pack = retrieval_service.retrieve_attack_planning_evidence(
            requirement_text=payload.requirement,
            structured_spec=state.get("structured_spec") or {},
            target_service=target_service,
            planning_mode=planning_mode,
            prior_findings=prior_findings or [],
            regression_focus=regression_focus or [],
            top_k=3,
        )
        if evidence_pack.items:
            return evidence_pack

        global_evidence_pack = state.get("evidence_pack") or EvidencePackPayload()
        if not global_evidence_pack.items:
            return evidence_pack

        applied_filters = dict(global_evidence_pack.applied_filters or {})
        applied_filters.update(
            {
                "planner_mode": planning_mode,
                "target_template_id": target_service.template_id,
                "attack_surface_kind": target_service.attack_surface_kind,
                "service_kind": target_service.service_kind,
                "planner_retrieval_fallback": "state_evidence_pack",
            }
        )
        return global_evidence_pack.model_copy(update={"applied_filters": applied_filters})

    def _build_attack_planner_evidence_card(
        self,
        *,
        state: LangGraphMASState,
        evidence_pack: EvidencePackPayload,
        round_id: str,
        planning_mode: str,
    ) -> MemoryCardPayload:
        """Summarize planner-scoped retrieval hits for the attack planning window."""

        top_titles = [item.title for item in evidence_pack.items[:3] if item.title]
        return MemoryCardPayload(
            card_id=f"card-{state['run_id'][:8]}-{planning_mode}-attack-evidence",
            card_type="attack_planner_evidence",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id=round_id,
            source_agent="retrieval_service",
            priority="medium",
            priority_label=self._priority_label("medium"),
            summary=f"攻击规划检索命中 {len(evidence_pack.items)} 条证据，供 {planning_mode} 规划参考。",
            payload={
                "planning_mode": planning_mode,
                "query": evidence_pack.query,
                "backend": evidence_pack.backend,
                "retrieval_mode": evidence_pack.retrieval_mode,
                "hit_count": len(evidence_pack.items),
                "top_titles": top_titles,
                "applied_filters": dict(evidence_pack.applied_filters or {}),
            },
            evidence_refs=self._build_evidence_refs(evidence_pack, limit=3),
            created_at=datetime.now(timezone.utc),
        )

    def _build_case_memory_card(
        self,
        *,
        case_memory: CaseMemoryPayload,
        run_id: str,
        source_agent: str,
    ) -> MemoryCardPayload:
        """Summarize project-level memory into a reusable card."""
        return MemoryCardPayload(
            card_id=f"card-{run_id[:8]}-case-memory",
            card_type="case_memory",
            case_id=case_memory.case_id,
            run_id=run_id,
            source_agent=source_agent,
            priority="medium",
            priority_label=self._priority_label("medium"),
            summary="项目级历史决策、阻塞项与已确认约束摘要。",
            payload={
                "status": case_memory.status,
                "status_label": case_memory.status_label,
                "selected_proposal": case_memory.selected_proposal,
                "blocking_items": case_memory.blocking_items[:4],
                "recent_decisions": [item.summary for item in case_memory.decision_log[-3:]],
                "reflection_count": len(case_memory.recent_reflections),
                "latest_prompt_changes": list(
                    (case_memory.recent_reflections[-1].get("prompt_changes") or [])[:3]
                )
                if case_memory.recent_reflections
                else [],
            },
            created_at=datetime.now(timezone.utc),
        )

    def _build_reflection_memory_cards(
        self,
        *,
        case_memory: CaseMemoryPayload,
        run_id: str,
        round_id: str,
        source_agent: str,
        card_type: str,
        summary: str,
    ) -> list[MemoryCardPayload]:
        """Project recent reflection lessons into the next generation or audit window."""

        recent_reflections = list(case_memory.recent_reflections or [])[-2:]
        if not recent_reflections:
            return []
        latest = dict(recent_reflections[-1] or {})
        return [
            MemoryCardPayload(
                card_id=f"card-{run_id[:8]}-{round_id}-reflection-memory",
                card_type=card_type,
                case_id=case_memory.case_id,
                run_id=run_id,
                round_id=round_id,
                source_agent=source_agent,
                priority="high",
                priority_label=self._priority_label("high"),
                summary=summary,
                payload={
                    "reflection_count": len(case_memory.recent_reflections),
                    "recent_reflections": recent_reflections,
                    "latest_reflection_summary": str(latest.get("reflection_summary") or ""),
                    "latest_regression_summary": str(latest.get("regression_summary") or ""),
                    "latest_prompt_changes": list(latest.get("prompt_changes") or [])[:4],
                    "latest_audit_focus": list(latest.get("audit_focus") or [])[:4],
                    "latest_residual_risks": list(latest.get("residual_risks") or [])[:4],
                    "latest_changed_artifacts": list(latest.get("changed_artifacts") or [])[:4],
                    "latest_patch_strategy": str(latest.get("patch_strategy") or ""),
                    "latest_severity": str(latest.get("severity") or ""),
                    "latest_next_version": str(latest.get("next_version") or ""),
                },
                created_at=datetime.now(timezone.utc),
            )
        ]

    def _build_retry_context_summary_card(
        self,
        *,
        state: LangGraphMASState,
        round_id: str,
        source_agent: str,
        summary: str,
        stage_label: str,
        upstream_projection_refs: list[str],
        upstream_handoff_ids: list[str],
        focus_points: list[str],
    ) -> MemoryCardPayload:
        """Build a compact retry lineage/compression card for one retry sub-window."""

        return MemoryCardPayload(
            card_id=f"card-{state['run_id'][:8]}-{round_id}-retry-context",
            card_type="retry_context_summary",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id=round_id,
            source_agent=source_agent,
            priority="medium",
            priority_label=self._priority_label("medium"),
            summary=summary,
            payload={
                "compression_scope": "same_run_retry",
                "compression_stage": stage_label,
                "compression_policy": "retain_summary_and_refs_drop_raw_details",
                "upstream_projection_refs": [item for item in upstream_projection_refs if str(item).strip()][:4],
                "upstream_handoff_ids": [item for item in upstream_handoff_ids if str(item).strip()][:4],
                "retained_refs": [
                    *[item for item in upstream_projection_refs if str(item).strip()][:4],
                    *[item for item in upstream_handoff_ids if str(item).strip()][:4],
                ][:8],
                "dropped_detail_hints": [
                    "raw_attack_telemetry_series",
                    "duplicate_attack_findings",
                    "full_artifact_body_content",
                ],
                "focus_points": [item for item in focus_points if str(item).strip()][:4],
                "resume_checkpoint_ref": f"retry-checkpoint:{state['run_id'][:8]}:{stage_label}",
                "resume_inputs": {
                    "required_projection_refs": [
                        item for item in upstream_projection_refs if str(item).strip()
                    ][:4],
                    "required_handoff_ids": [
                        item for item in upstream_handoff_ids if str(item).strip()
                    ][:4],
                    "retained_refs": [
                        *[item for item in upstream_projection_refs if str(item).strip()][:4],
                        *[item for item in upstream_handoff_ids if str(item).strip()][:4],
                    ][:8],
                    "focus_points": [item for item in focus_points if str(item).strip()][:4],
                },
                "resume_hint": f"{stage_label}:resume_from_summary",
            },
            created_at=datetime.now(timezone.utc),
        )

    def _build_memory_handoff(
        self,
        *,
        handoff_id: str,
        from_agent: str,
        to_agent: str,
        objective: str,
        projection: ContextProjectionPayload,
    ) -> MemoryHandoffPayload:
        """Wrap a role-aware projection as a stable handoff package."""
        return MemoryHandoffPayload(
            handoff_id=handoff_id,
            from_agent=from_agent,
            to_agent=to_agent,
            case_id=projection.case_id,
            run_id=projection.run_id,
            round_id=projection.round_id,
            objective=objective,
            status="ready",
            status_label="已就绪",
            cards=list(projection.cards),
            artifact_refs=list(projection.artifact_refs),
            evidence_refs=list(projection.evidence_refs),
            projection=projection,
        )

    def _finalize_projection_cards(
        self,
        cards: list[MemoryCardPayload],
    ) -> list[MemoryCardPayload]:
        """Attach stable typed-contract metadata to projection cards."""

        finalized: list[MemoryCardPayload] = []
        for card in cards:
            family = self._classify_memory_card_family(card.card_type)
            lineage_ref = self._build_memory_card_lineage_ref(card)
            contract_version = str(card.card_contract_version or "v1").strip() or "v1"
            replay_index_ref = str(card.replay_index_ref or "").strip() or f"{card.card_id}:{family}"
            typed_contract_ref = self._build_memory_card_contract_ref(
                card,
                family=family,
                contract_version=contract_version,
            )
            payload = dict(card.payload or {})
            payload.setdefault("card_family", family)
            payload.setdefault("card_contract_version", contract_version)
            payload.setdefault("lineage_ref", lineage_ref)
            payload.setdefault("replay_index_ref", replay_index_ref)
            payload.setdefault(
                "typed_contract",
                self._build_memory_card_typed_contract(
                    card,
                    family=family,
                    contract_version=contract_version,
                    lineage_ref=lineage_ref,
                    replay_index_ref=replay_index_ref,
                    typed_contract_ref=typed_contract_ref,
                ),
            )
            payload.setdefault("typed_contract_ref", typed_contract_ref)
            payload.setdefault(
                "ref_lookup_hint",
                self._build_memory_card_ref_lookup_hint(
                    card,
                    lineage_ref=lineage_ref,
                    replay_index_ref=replay_index_ref,
                ),
            )
            finalized.append(
                card.model_copy(
                    update={
                        "card_family": family,
                        "card_family_label": self._memory_card_family_label(family),
                        "card_contract_version": contract_version,
                        "lineage_ref": lineage_ref,
                        "replay_index_ref": replay_index_ref,
                        "payload": payload,
                    }
                )
            )
        return finalized

    def _matches_runtime_input_card(
        self,
        card: MemoryCardPayload,
        *,
        expected_card_type: str,
        expected_stage: str,
    ) -> bool:
        if str(card.card_type or "").strip() == expected_card_type:
            return True
        payload = dict(card.payload or {})
        typed_contract = dict(payload.get("typed_contract") or {})
        contract_card_type = str(typed_contract.get("card_type") or "").strip()
        runtime_stage = str(
            payload.get("runtime_stage")
            or typed_contract.get("runtime_stage")
            or ""
        ).strip().lower()
        return (
            str(card.card_family or "").strip() == "runtime_input"
            and contract_card_type == expected_card_type
            and runtime_stage == expected_stage
        )

    def _classify_memory_card_family(self, card_type: str) -> str:
        value = str(card_type or "").strip().lower()
        if not value:
            return "generic"
        if value.endswith("_runtime_input"):
            return "runtime_input"
        if value in {"attack_decision", "audit_decision", "proposal_decision"} or "decision" in value:
            return "decision"
        if value in {"patch_execution", "patch_artifact_summary", "patch_spec"} or value.startswith("patch_"):
            return "patch"
        if value in {"reflection_memory", "reflection_summary", "reflection", "regression_summary"} or "reflection" in value:
            return "reflection"
        if value in {
            "attack_result_summary",
            "attack_artifact_summary",
            "vulnerability_verdict",
            "baseline_verdict_reference",
            "regression_verdict_input",
            "candidate_summary",
            "analyst_summary",
            "audit_finding",
        } or "verdict" in value or "finding" in value or value.endswith("_summary"):
            return "finding"
        if "evidence" in value:
            return "evidence"
        if value == "replay_snapshot":
            return "replay_snapshot"
        return "generic"

    def _memory_card_family_label(self, family: str) -> str:
        labels = {
            "runtime_input": "运行时输入",
            "decision": "决策卡",
            "finding": "发现卡",
            "patch": "修补卡",
            "reflection": "反思卡",
            "evidence": "证据卡",
            "replay_snapshot": "回放快照卡",
            "generic": "通用卡",
        }
        return labels.get(family, family)

    def _build_memory_card_lineage_ref(self, card: MemoryCardPayload) -> str:
        parts = [str(card.case_id or "").strip()]
        if str(card.run_id or "").strip():
            parts.append(str(card.run_id or "").strip())
        if str(card.round_id or "").strip():
            parts.append(str(card.round_id or "").strip())
        if str(card.version_id or "").strip():
            parts.append(str(card.version_id or "").strip())
        return ":".join(item for item in parts if item)

    def _build_memory_card_contract_ref(
        self,
        card: MemoryCardPayload,
        *,
        family: str,
        contract_version: str,
    ) -> str:
        return f"{family}:{card.card_type}:{contract_version}"

    def _build_memory_card_typed_contract(
        self,
        card: MemoryCardPayload,
        *,
        family: str,
        contract_version: str,
        lineage_ref: str,
        replay_index_ref: str,
        typed_contract_ref: str,
    ) -> dict[str, Any]:
        runtime_stage = ""
        if str(card.card_type or "").strip().endswith("_runtime_input"):
            runtime_stage = str(card.card_type or "").strip().removesuffix("_runtime_input")
        return {
            "contract_ref": typed_contract_ref,
            "card_type": str(card.card_type or ""),
            "family": family,
            "family_label": self._memory_card_family_label(family),
            "contract_version": contract_version,
            "source_agent": str(card.source_agent or ""),
            "lineage_ref": lineage_ref,
            "replay_index_ref": replay_index_ref,
            "artifact_ref_count": len(card.artifact_refs),
            "evidence_ref_count": len(card.evidence_refs),
            "runtime_stage": runtime_stage,
        }

    def _build_memory_card_ref_lookup_hint(
        self,
        card: MemoryCardPayload,
        *,
        lineage_ref: str,
        replay_index_ref: str,
    ) -> dict[str, Any]:
        artifact_refs = [
            {
                "artifact_id": str(ref.artifact_id or ""),
                "artifact_type": str(ref.artifact_type or "generic"),
            }
            for ref in list(card.artifact_refs or [])[:6]
            if str(ref.artifact_id or "").strip()
        ]
        evidence_refs = [
            {
                "doc_id": str(ref.doc_id or ""),
                "chunk_id": str(ref.chunk_id or ""),
            }
            for ref in list(card.evidence_refs or [])[:6]
            if str(ref.doc_id or "").strip() and str(ref.chunk_id or "").strip()
        ]
        return {
            "lookup_strategy": "card_refs_then_projection_then_handoff_then_replay",
            "lineage_ref": lineage_ref,
            "replay_index_ref": replay_index_ref,
            "artifact_refs": artifact_refs,
            "evidence_refs": evidence_refs,
        }

    def _build_target_service_artifact_ref(
        self,
        *,
        target_service: TargetServiceSpecPayload,
        summary: str,
        artifact_type: str = "target_service",
    ) -> ArtifactRefPayload:
        """Serialize a target service as a reusable artifact ref for projections."""
        return ArtifactRefPayload(
            artifact_id=target_service.artifact_id or target_service.service_id,
            artifact_type=artifact_type,
            title=target_service.service_name,
            path=target_service.entrypoint or None,
            summary=summary,
            metadata={
                "service_id": target_service.service_id,
                "template_id": target_service.template_id,
                "template_label": target_service.template_label,
                "service_kind": target_service.service_kind,
                "attack_surface_kind": target_service.attack_surface_kind,
                "service_name": target_service.service_name,
                "deployment_profile": target_service.deployment_profile,
                "service_interface": target_service.service_interface,
                "attack_surface": list(target_service.attack_surface),
                "service_version": target_service.service_version,
                "runtime": target_service.runtime,
                "entrypoint": target_service.entrypoint,
                "supported_versions": list(target_service.supported_versions),
                "planner_skill_hints": list(target_service.planner_skill_hints),
                "planner_retrieval_hints": list(target_service.planner_retrieval_hints),
                "deployment_manifest": target_service.deployment_manifest.model_dump(mode="json"),
                "runtime_profile": target_service.runtime_profile.model_dump(mode="json"),
                "status": target_service.status,
                "status_label": target_service.status_label,
            },
        )

    def _build_attack_spec_artifact_ref(self, spec: AttackSpecPayload) -> ArtifactRefPayload:
        """Serialize an attack spec into a reusable projection artifact ref."""
        return ArtifactRefPayload(
            artifact_id=f"{spec.attack_id}:plan",
            artifact_type="attack_spec",
            title=spec.attack_family,
            summary=spec.objective,
            metadata={
                "attack_id": spec.attack_id,
                "target_service_ref": spec.target_service_ref,
                "attack_family": spec.attack_family,
                "attack_surface": list(spec.attack_surface),
                "expected_artifacts": list(spec.expected_artifacts),
                "telemetry_fields": list(spec.telemetry_fields),
                "budget": dict(spec.budget),
                "status": spec.status,
                "status_label": spec.status_label,
            },
        )

    def _build_attack_decision_card(
        self,
        *,
        state: LangGraphMASState,
        attack_decision: AttackDecisionPayload,
        round_id: str = "attack-plan-r1",
        summary: str = "攻击规划 Agent 已输出本轮攻击决策与停机条件。",
    ) -> MemoryCardPayload:
        """Serialize the planner's decision into a reusable memory card."""

        return MemoryCardPayload(
            card_id=f"card-{state['run_id'][:8]}-attack-decision",
            card_type="attack_decision",
            case_id=state["case_id"],
            run_id=state["run_id"],
            round_id=round_id,
            source_agent="attack_planning_agent",
            priority="high",
            priority_label=self._priority_label("high"),
            summary=summary,
            payload=attack_decision.model_dump(mode="json"),
            created_at=datetime.now(timezone.utc),
        )

    def _build_attack_artifact_refs(
        self,
        attack_results: list[AttackResultPayload],
    ) -> list[ArtifactRefPayload]:
        """Flatten attack artifacts into lightweight refs for downstream patch windows."""
        refs: list[ArtifactRefPayload] = []
        for attack_result in attack_results[:3]:
            summaries = self.artifact_summarizer.summarize_artifact_paths(
                attack_result.artifact_refs,
                attack_id=attack_result.attack_id,
                status=attack_result.status,
                fallback_summary=attack_result.summary,
            )
            for artifact in summaries:
                refs.append(
                    ArtifactRefPayload(
                        artifact_id=str(artifact.get("artifact_id") or f"{attack_result.attack_id}:artifact"),
                        artifact_type=str(artifact.get("artifact_type") or "attack_artifact"),
                        title=str(artifact.get("title") or ""),
                        path=artifact.get("path"),
                        summary=str(artifact.get("summary") or attack_result.summary),
                        metadata=dict(artifact.get("metadata") or {}),
                    )
                )
        return refs

    def _build_patch_artifact_refs(
        self,
        patch_artifact_summary: dict[str, Any],
    ) -> list[ArtifactRefPayload]:
        """Serialize summarized patch artifacts into reusable refs."""

        refs: list[ArtifactRefPayload] = []
        for item in list(patch_artifact_summary.get("changed_artifact_summaries") or [])[:4]:
            refs.append(
                ArtifactRefPayload(
                    artifact_id=str(item.get("artifact_key") or "patch-artifact"),
                    artifact_type=str(item.get("artifact_type") or "patch_artifact"),
                    title=str(item.get("relative_name") or item.get("artifact_key") or ""),
                    path=item.get("patched_path"),
                    summary=str(item.get("summary") or ""),
                    metadata={
                        "artifact_role": item.get("artifact_role"),
                        "file_size_bytes": item.get("file_size_bytes"),
                        "before_line_count": item.get("before_line_count"),
                        "after_line_count": item.get("after_line_count"),
                        "line_delta": item.get("line_delta"),
                        "added_line_count": item.get("added_line_count"),
                        "removed_line_count": item.get("removed_line_count"),
                        "diff_preview": list(item.get("diff_preview") or [])[:4],
                    },
                )
            )
        return refs

    def _build_attack_result_summary_payload(
        self,
        attack_results: list[AttackResultPayload],
        vulnerability_report: dict[str, Any],
        *,
        evaluation_mode: str = "baseline",
        baseline_verdict: VulnerabilityVerdictPayload | None = None,
    ) -> dict[str, Any]:
        """Build a compact result summary payload for downstream agent windows."""

        attack_result_summaries = self.artifact_summarizer.summarize_attack_results(attack_results)
        payload = {
            "evaluation_mode": evaluation_mode,
            "attack_count": len(attack_results),
            "findings": self.artifact_summarizer.collect_top_findings_from_summaries(
                attack_result_summaries
            ),
            "risk_score": int(vulnerability_report.get("risk_score", 0)),
            "attack_result_summaries": attack_result_summaries,
            "artifact_refs": self.artifact_summarizer.flatten_artifact_paths(attack_result_summaries),
            "vulnerability_report": {
                "risk_score": int(vulnerability_report.get("risk_score", 0)),
                "summary": vulnerability_report.get("summary", {}),
                "recommendations": list(vulnerability_report.get("recommendations") or [])[:4],
            },
        }
        if evaluation_mode == "regression":
            payload["baseline_risk_score"] = int(vulnerability_report.get("baseline_risk_score", 0))
        if baseline_verdict is not None:
            payload["baseline_verdict"] = baseline_verdict.model_dump(mode="json")
        return payload

    def _build_attack_artifact_summary_payload(
        self,
        attack_results: list[AttackResultPayload],
    ) -> dict[str, Any]:
        """Build a compact artifact-summary card for patch planning."""

        attack_result_summaries = self.artifact_summarizer.summarize_attack_results(attack_results)
        return {
            "artifact_summary_version": "v1",
            "attack_count": len(attack_results),
            "top_findings": self.artifact_summarizer.collect_top_findings_from_summaries(
                attack_result_summaries
            ),
            "attack_result_summaries": attack_result_summaries,
            "artifact_refs": self.artifact_summarizer.flatten_artifact_paths(attack_result_summaries),
        }

    def _extract_target_service_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        fallback: TargetServiceSpecPayload | None,
    ) -> TargetServiceSpecPayload:
        """Hydrate the target service from projection artifacts with compatibility fallback."""
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
                status=str(metadata.get("status") or "planned"),
                status_label=str(metadata.get("status_label") or "待处理"),
            )
        if fallback is None:
            raise ValueError("Missing target service in projection and no fallback available.")
        return fallback

    def _extract_attack_specs_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        fallback: list[AttackSpecPayload] | None = None,
    ) -> list[AttackSpecPayload]:
        """Hydrate planned attack specs from projection artifacts."""
        specs: list[AttackSpecPayload] = []
        for artifact in projection.artifact_refs:
            if artifact.artifact_type != "attack_spec":
                continue
            metadata = artifact.metadata or {}
            attack_id = str(metadata.get("attack_id") or "").strip()
            target_service_ref = str(metadata.get("target_service_ref") or "").strip()
            if not attack_id or not target_service_ref:
                continue
            specs.append(
                AttackSpecPayload(
                    attack_id=attack_id,
                    target_service_ref=target_service_ref,
                    attack_family=str(metadata.get("attack_family") or artifact.title or "misuse_case"),
                    objective=artifact.summary,
                    attack_surface=list(metadata.get("attack_surface") or []),
                    expected_artifacts=list(metadata.get("expected_artifacts") or []),
                    telemetry_fields=list(metadata.get("telemetry_fields") or []),
                    budget=dict(metadata.get("budget") or {}),
                    status=str(metadata.get("status") or "planned"),
                    status_label=str(metadata.get("status_label") or "待执行"),
                )
            )
        if specs:
            return specs
        return list(fallback or [])

    def _extract_attack_results_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        fallback: list[AttackResultPayload] | None = None,
    ) -> list[AttackResultPayload]:
        """Hydrate attack execution results from projection cards."""
        for card in projection.cards:
            if card.card_type != "attack_result_summary":
                continue
            raw_results = list(card.payload.get("attack_results") or [])
            hydrated: list[AttackResultPayload] = []
            for item in raw_results:
                try:
                    hydrated.append(AttackResultPayload.model_validate(item))
                except Exception:
                    continue
            if hydrated:
                return hydrated
        return list(fallback or [])

    def _extract_vulnerability_report_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        fallback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Hydrate the compact vulnerability report slice from projection cards."""
        for card in projection.cards:
            if card.card_type != "attack_result_summary":
                continue
            report = card.payload.get("vulnerability_report")
            if isinstance(report, dict):
                return dict(report)
        return dict(fallback or {})

    def _extract_vulnerability_verdict_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        fallback: VulnerabilityVerdictPayload | None,
    ) -> VulnerabilityVerdictPayload:
        """Hydrate the vulnerability verdict from projection cards."""
        for card in projection.cards:
            if card.card_type != "vulnerability_verdict":
                continue
            raw_verdict = card.payload.get("verdict")
            if isinstance(raw_verdict, dict):
                try:
                    return VulnerabilityVerdictPayload.model_validate(raw_verdict)
                except Exception:
                    break
        if fallback is None:
            raise ValueError("Missing vulnerability verdict in projection and no fallback available.")
        return fallback

    def _build_reflection_cards_from_projection(
        self,
        projection: ContextProjectionPayload,
        *,
        fallback_workspace: str,
    ) -> list[dict[str, Any]]:
        """Generate reflection output cards from the reflection input projection."""
        patch_payload: dict[str, Any] = {}
        regression_payload: dict[str, Any] = {}
        patch_execution_payload: dict[str, Any] = {}
        patch_artifact_payload: dict[str, Any] = {}
        for card in projection.cards:
            if card.card_type == "reflection_summary":
                patch_payload = dict(card.payload or {})
            elif card.card_type == "regression_verdict_input":
                regression_payload = dict(card.payload or {})
            elif card.card_type == "patch_execution":
                patch_execution_payload = dict(card.payload or {})
            elif card.card_type == "patch_artifact_summary":
                patch_artifact_payload = dict(card.payload or {})

        patch_spec = patch_payload.get("patch_spec") or {}
        changed_artifacts = list(
            patch_execution_payload.get("changed_artifact_summaries")
            or patch_artifact_payload.get("changed_artifact_summaries")
            or []
        )
        changed_names = [
            str(item.get("relative_name") or item.get("artifact_key") or "").strip()
            for item in changed_artifacts[:3]
            if str(item.get("relative_name") or item.get("artifact_key") or "").strip()
        ]
        changed_hint = "、".join(changed_names) if changed_names else "核心实现文件"
        reflection_cards = [
            {
                "card_type": "reflection",
                "target_service_ref": patch_spec.get("target_service_ref", ""),
                "summary": (
                    "下一轮 generation 应优先输出带接口约束、错误处理和密钥治理边界的实现，"
                    f"并继续显式说明 {changed_hint} 的修补理由。"
                ),
                "severity": str(regression_payload.get("severity") or "medium"),
                "patch_strategy": str(patch_spec.get("strategy") or "hardening-and-validation"),
                "changed_artifacts": changed_names,
            },
            {
                "card_type": "regression_summary",
                "target_service_ref": patch_spec.get("target_service_ref", ""),
                "summary": (
                    "补丁版本壳子已完成重部署并执行正式回归探测，"
                    f"当前残余严重度为 {str(regression_payload.get('severity_label') or '中')}。"
                ),
                "severity": str(regression_payload.get("severity") or "medium"),
                "patch_strategy": str(patch_spec.get("strategy") or "hardening-and-validation"),
                "workspace": str(patch_execution_payload.get("workspace") or fallback_workspace),
                "changed_artifacts": changed_names,
            },
        ]
        return reflection_cards

    def _priority_label(self, priority: str) -> str:
        return {
            "high": "高",
            "medium": "中",
            "low": "低",
        }.get(priority, "中")

    def _collect_top_vulnerability_findings(self, vulnerability_report: dict[str, Any]) -> list[str]:
        """Extract concise findings from the legacy vulnerability report shape."""
        findings: list[str] = []
        raw_findings = vulnerability_report.get("findings") or vulnerability_report.get("issues") or []
        if isinstance(raw_findings, list):
            for item in raw_findings[:3]:
                if isinstance(item, dict):
                    title = str(item.get("title") or item.get("name") or item.get("issue") or "").strip()
                    if title:
                        findings.append(title)
                elif item:
                    findings.append(str(item))
        return findings

    def _filter_non_empty_refs(self, refs: list[str]) -> list[str]:
        """Deduplicate and normalize lightweight artifact refs."""

        clean: list[str] = []
        seen: set[str] = set()
        for item in refs:
            ref = str(item or "").strip()
            if not ref or ref in seen:
                continue
            seen.add(ref)
            clean.append(ref)
        return clean

    def _build_case_context(self, case_memory: CaseMemoryPayload) -> dict[str, Any]:
        """Create a compact analyst-visible summary of historical project state."""
        return {
            "has_history": bool(
                case_memory.decision_log or case_memory.rejected_options or case_memory.recent_reflections
            ),
            "prior_decisions": len(case_memory.decision_log),
            "prior_rejections": len(case_memory.rejected_options),
            "blocking_items": case_memory.blocking_items[:3],
            "selected_proposal": case_memory.selected_proposal,
            "scenario_label": display_scenario(case_memory.scenario) if case_memory.scenario else "",
            "recent_reflection_count": len(case_memory.recent_reflections),
            "latest_reflection_summary": (
                str(case_memory.recent_reflections[-1].get("reflection_summary") or "")
                if case_memory.recent_reflections
                else ""
            ),
        }

    def _build_case_memory_summary(self, case_memory: CaseMemoryPayload) -> dict[str, Any]:
        """Expose compact case memory stats in delivery payloads."""
        return {
            "case_id": case_memory.case_id,
            "status": case_memory.status,
            "status_label": case_memory.status_label,
            "decision_count": len(case_memory.decision_log),
            "rejected_count": len(case_memory.rejected_options),
            "blocking_items": case_memory.blocking_items[:3],
            "selected_proposal": case_memory.selected_proposal,
            "reflection_count": len(case_memory.recent_reflections),
            "evidence_ref_count": len(case_memory.latest_evidence_refs),
        }

    def _persist_case_memory(
        self,
        case_memory_service: CaseMemoryService,
        *,
        state: LangGraphMASState,
        status: str,
        selected_proposal: str | None,
        compliance_score: float | None,
        risk_score: int | None,
    ) -> CaseMemoryPayload:
        """Merge current run state into project-level case memory and persist it."""
        payload = state["payload"]
        case_memory = (state.get("case_memory") or case_memory_service.create_empty(state["case_id"])).model_copy(deep=True)
        structured_spec = state.get("structured_spec") or {}
        clarifications = list(state.get("clarifications") or [])
        auditor_rounds = list(state.get("auditor_rounds") or [])
        schemes = list(state.get("schemes") or [])
        now = datetime.now(timezone.utc)

        constraint_candidates = self._extract_confirmed_constraints(structured_spec)
        open_questions = [item.question for item in clarifications if getattr(item, "question", None)]
        blocking_items = [item.question for item in clarifications if getattr(item, "required", False)]
        if status != "approved" and auditor_rounds:
            blocking_items.extend(auditor_rounds[-1].reasons)

        signature_map = {
            f"proposal-{index + 1}": self._build_scheme_signature(scheme)
            for index, scheme in enumerate(schemes)
        }
        rejected_options = list(case_memory.rejected_options)
        known_rejections = {
            (item.proposal_id, item.component_signature.lower())
            for item in rejected_options
        }
        for round_item in auditor_rounds:
            if round_item.verdict != "reject":
                continue
            component_signature = signature_map.get(round_item.proposal_id, "")
            dedupe_key = (round_item.proposal_id, component_signature.lower())
            if dedupe_key in known_rejections:
                continue
            rejected_options.append(
                CaseRejectedOptionPayload(
                    proposal_id=round_item.proposal_id,
                    component_signature=component_signature,
                    reasons=list(round_item.reasons),
                    compliance_score=round_item.compliance_score,
                    risk_score=round_item.risk_score,
                    recorded_at=now,
                )
            )
            known_rejections.add(dedupe_key)

        decision_log = list(case_memory.decision_log)
        decision_log.append(
            CaseDecisionPayload(
                time=now,
                action=status,
                action_label=display_status(status),
                proposal_id=selected_proposal,
                summary=self._build_case_decision_summary(
                    status=status,
                    selected_proposal=selected_proposal,
                    blocking_items=blocking_items,
                    compliance_score=compliance_score,
                    risk_score=risk_score,
                ),
            )
        )
        recent_reflections = [dict(item) for item in case_memory.recent_reflections]
        latest_reflection = self._build_case_reflection_memory(state=state, created_at=now)
        if latest_reflection:
            recent_reflections = [
                item for item in recent_reflections if str(item.get("run_id") or "").strip() != latest_reflection["run_id"]
            ]
            recent_reflections.append(latest_reflection)

        case_memory.updated_at = now
        case_memory.status = status
        case_memory.status_label = display_status(status)
        case_memory.scenario = str(structured_spec.get("domain") or case_memory.scenario or "")
        case_memory.requirement_summary = self._summarize_requirement(payload.requirement)
        case_memory.confirmed_constraints = self._merge_unique(case_memory.confirmed_constraints, constraint_candidates)
        case_memory.open_questions = self._merge_unique(case_memory.open_questions, open_questions)
        case_memory.blocking_items = self._merge_unique(case_memory.blocking_items, blocking_items)[:8]
        case_memory.rejected_options = rejected_options[-12:]
        case_memory.decision_log = decision_log[-20:]
        case_memory.recent_reflections = recent_reflections[-6:]
        attack_results = list(state.get("attack_results") or [])
        evidence_refs = [
            ref
            for result in attack_results
            for ref in [
                *list(result.artifact_refs or []),
                *list((result.metrics or {}).get("evidence_refs") or []),
            ]
        ]
        case_memory.latest_evidence_refs = self._merge_unique([], evidence_refs)[:24]
        case_memory.selected_proposal = selected_proposal or case_memory.selected_proposal
        case_memory.latest_compliance_score = compliance_score
        case_memory.latest_risk_score = risk_score

        return case_memory_service.save(case_memory)

    def _build_case_reflection_memory(
        self,
        *,
        state: LangGraphMASState,
        created_at: datetime,
    ) -> dict[str, Any] | None:
        """Convert the latest reflection output into project-level reusable memory."""

        reflection_cards = list(state.get("reflection_cards") or [])
        if not reflection_cards:
            return None
        reflection_card = next(
            (dict(item) for item in reflection_cards if str(item.get("card_type") or "") == "reflection"),
            None,
        )
        regression_card = next(
            (dict(item) for item in reflection_cards if str(item.get("card_type") or "") == "regression_summary"),
            None,
        )
        if reflection_card is None and regression_card is None:
            return None
        patch_spec = state.get("patch_spec")
        return {
            "time": created_at,
            "run_id": state["run_id"],
            "reflection_summary": str((reflection_card or {}).get("summary") or ""),
            "regression_summary": str((regression_card or {}).get("summary") or ""),
            "prompt_changes": list((reflection_card or {}).get("prompt_changes") or [])[:4],
            "audit_focus": list((reflection_card or {}).get("audit_focus") or [])[:4],
            "residual_risks": list((regression_card or {}).get("residual_risks") or [])[:4],
            "changed_artifacts": list((reflection_card or {}).get("changed_artifacts") or [])[:4],
            "patch_strategy": str((reflection_card or {}).get("patch_strategy") or ""),
            "severity": str((reflection_card or {}).get("severity") or ""),
            "next_version": str((reflection_card or {}).get("next_version") or (patch_spec.next_version if patch_spec else "")),
        }

    def _extract_confirmed_constraints(self, structured_spec: dict[str, Any]) -> list[str]:
        items: list[str] = []
        domain = str(structured_spec.get("domain") or "").strip()
        if domain:
            items.append(f"业务领域：{display_scenario(domain)}")
        compliance = str(structured_spec.get("compliance") or "").strip()
        if compliance:
            items.append(f"合规目标：{compliance}")
        platform = str(structured_spec.get("platform") or "").strip()
        if platform:
            items.append(f"部署平台：{platform}")
        latency = str(structured_spec.get("max_latency") or "").strip()
        if latency:
            items.append(f"延迟目标：{latency}")
        if structured_spec.get("quantum_safe") is True:
            items.append("后量子要求：是")
        construction_summary = build_construction_context_summary(structured_spec)
        if construction_summary:
            items.append(f"Construction model: {construction_summary}")
        return items

    def _build_case_decision_summary(
        self,
        *,
        status: str,
        selected_proposal: str | None,
        blocking_items: list[str],
        compliance_score: float | None,
        risk_score: int | None,
    ) -> str:
        if status == "needs_clarification":
            return f"本轮在澄清门禁暂停，待补充 {len(blocking_items)} 项关键信息。"
        if selected_proposal:
            return (
                f"本轮输出状态为 {display_status(status)}，当前选中 {selected_proposal}，"
                f"合规分 {compliance_score if compliance_score is not None else '--'}，"
                f"风险分 {risk_score if risk_score is not None else '--'}。"
            )
        return f"本轮输出状态为 {display_status(status)}。"

    def _summarize_requirement(self, requirement: str, max_length: int = 220) -> str:
        normalized = " ".join(str(requirement or "").split())
        if len(normalized) <= max_length:
            return normalized
        return normalized[: max_length - 1].rstrip() + "…"

    def _build_scheme_signature(self, scheme: CryptographicScheme) -> str:
        component_names = sorted({item.name.strip().lower() for item in scheme.architecture.components if item.name})
        return " + ".join(component_names)

    def _merge_unique(self, current: list[str], incoming: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for value in [*current, *incoming]:
            text = str(value or "").strip()
            if not text:
                continue
            if text in seen:
                continue
            seen.add(text)
            merged.append(text)
        return merged
