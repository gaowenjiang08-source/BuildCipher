"""Request and response schemas for the BuildTrust API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Input payload for scheme generation."""

    requirement: str = Field(min_length=8, description="Natural-language cryptographic requirement")
    num_variants: int = Field(default=2, ge=1, le=5)
    generate_code: bool = Field(default=True)
    llm_provider: Optional[str] = Field(default=None, description="openai / anthropic / gemini / zhipuai / deepseek / qwen / baidu / relay")


class ParsedRequirementPayload(BaseModel):
    """Serialized parser output."""

    requirement: Dict[str, Any]
    confidence: float
    ambiguities: List[str]
    assumptions: List[str]


class EvidenceItemPayload(BaseModel):
    """Single retrieved evidence item."""

    doc_id: str
    chunk_id: str
    doc_type: str
    title: str
    section: Optional[str] = None
    snippet: str = ""
    score: float = 0.0
    source_path: Optional[str] = None
    source_page: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidencePackPayload(BaseModel):
    """Retrieved evidence bundle used by MAS."""

    query: str = ""
    backend: str = "local"
    retrieval_mode: str = "keyword"
    applied_filters: Dict[str, Any] = Field(default_factory=dict)
    items: List[EvidenceItemPayload] = Field(default_factory=list)


class ArtifactRefPayload(BaseModel):
    """Lightweight artifact reference passed between agents."""

    artifact_id: str
    artifact_type: str = "generic"
    title: str = ""
    path: Optional[str] = None
    summary: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceRefPayload(BaseModel):
    """Compact evidence reference used in role-aware context projection."""

    doc_id: str
    chunk_id: str
    title: str = ""
    section: Optional[str] = None
    snippet: str = ""
    source_page: Optional[int] = None
    score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextConstraintPayload(BaseModel):
    """Constraint slice projected into a specific agent window."""

    constraint_id: str = ""
    constraint_kind: str = "requirement"
    value: str
    priority: str = "high"
    priority_label: str = "高"
    confirmed: bool = True
    source: str = "case_memory"


class MemoryCardPayload(BaseModel):
    """Structured memory card used as the agent-to-agent handoff unit."""

    card_id: str
    card_type: str
    card_family: str = ""
    card_family_label: str = ""
    card_contract_version: str = "v1"
    case_id: str
    run_id: Optional[str] = None
    round_id: Optional[str] = None
    version_id: Optional[str] = None
    lineage_ref: str = ""
    replay_index_ref: str = ""
    source_agent: str = ""
    priority: str = "medium"
    priority_label: str = "中"
    summary: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    artifact_refs: List[ArtifactRefPayload] = Field(default_factory=list)
    evidence_refs: List[EvidenceRefPayload] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class ContextProjectionPayload(BaseModel):
    """Role-aware context window built for a single agent invocation."""

    agent_id: str
    case_id: str
    run_id: Optional[str] = None
    round_id: Optional[str] = None
    window_version: str = "v1"
    objective: str = ""
    constraints: List[ContextConstraintPayload] = Field(default_factory=list)
    cards: List[MemoryCardPayload] = Field(default_factory=list)
    artifact_refs: List[ArtifactRefPayload] = Field(default_factory=list)
    evidence_refs: List[EvidenceRefPayload] = Field(default_factory=list)
    token_budget_hint: int = Field(default=4000, ge=256, le=64000)


class MemoryHandoffPayload(BaseModel):
    """Structured package passed from one agent or module to another."""

    handoff_id: str
    from_agent: str
    to_agent: Optional[str] = None
    case_id: str
    run_id: Optional[str] = None
    round_id: Optional[str] = None
    objective: str = ""
    status: str = "ready"
    status_label: str = "已就绪"
    cards: List[MemoryCardPayload] = Field(default_factory=list)
    artifact_refs: List[ArtifactRefPayload] = Field(default_factory=list)
    evidence_refs: List[EvidenceRefPayload] = Field(default_factory=list)
    projection: Optional[ContextProjectionPayload] = None


class ExecutorArtifactSyncManifestPayload(BaseModel):
    """Typed artifact-sync manifest used by executor handoff adapters."""

    sync_id: str
    dispatch_id: str
    direction: str = "bidirectional"
    artifact_refs: List[str] = Field(default_factory=list)
    required_artifact_kinds: List[str] = Field(default_factory=list)
    integrity_hashes: Dict[str, str] = Field(default_factory=dict)
    retention_policy: str = "run_scope"
    materialization_mode: str = "reference_only"
    sync_status: str = "planned"


class ExecutorHandoffReceiptPayload(BaseModel):
    """Lightweight receipt placeholder returned by executor handoff adapters."""

    receipt_id: str
    handoff_ref: str
    dispatch_id: str
    executor_kind: str
    executor_backend: str = ""
    accepted: bool = False
    receipt_status: str = "pending_handoff"
    remote_job_ref: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_artifact_refs: List[str] = Field(default_factory=list)
    telemetry_refs: List[str] = Field(default_factory=list)
    failure_category: str = ""
    failure_summary: str = ""
    retryable: bool = False


class ExecutorHandoffTracePayload(BaseModel):
    """Replay-friendly trace summary for one executor handoff lifecycle."""

    handoff_ref: str
    dispatch_id: str
    executor_kind: str
    executor_backend: str = ""
    routing_mode: str = ""
    adapter_stage: str = "dispatcher_plan"
    trace_status: str = "pending_handoff"
    summary: str = ""
    receipt_ref: str = ""
    artifact_sync_ref: str = ""
    failure_category: str = ""


class ExecutorHandoffRequestPayload(BaseModel):
    """Typed execution handoff request for container/remote-worker adapters."""

    handoff_ref: str
    handoff_contract_version: str = "v1"
    case_id: str = ""
    run_id: str = ""
    round_id: Optional[str] = None
    dispatch_id: str
    dispatch_key: str = ""
    stage: str = ""
    operation_kind: str = ""
    executor_kind: str
    executor_backend: str = ""
    target_service_ref: str = ""
    workspace_ref: str = ""
    input_artifact_refs: List[str] = Field(default_factory=list)
    required_capabilities: List[str] = Field(default_factory=list)
    governance_mode: str = "dispatcher"
    timeout_seconds: int = 0
    budget_hint: Dict[str, Any] = Field(default_factory=dict)
    callback_contract: Dict[str, Any] = Field(default_factory=dict)
    artifact_sync_contract: Dict[str, Any] = Field(default_factory=dict)
    telemetry_contract: Dict[str, Any] = Field(default_factory=dict)


class SandboxPolicyPayload(BaseModel):
    """Execution guardrails enforced by the sandbox dispatcher."""

    policy_id: str = "local-sandbox-default"
    runtime_whitelist: List[str] = Field(
        default_factory=lambda: ["python", "c", "pseudocode"]
    )
    attack_family_whitelist: List[str] = Field(
        default_factory=lambda: [
            "oracle_probe",
            "misuse_case",
            "regression_check",
            "ifc_content_tamper",
            "signed_old_version_rollback",
            "full_model_overprivilege",
            "unregistered_device_impersonation",
            "valid_signed_telemetry_replay",
        ]
    )
    max_attack_tasks: int = Field(default=5, ge=1, le=64)
    max_probe_count: int = Field(default=12, ge=1, le=512)
    max_timeout_seconds: int = Field(default=180, ge=1, le=3600)
    max_memory_mb: int = Field(default=512, ge=64, le=65536)


class SandboxDispatchRequestPayload(BaseModel):
    """Structured dispatcher request before runtime execution."""

    dispatch_id: str
    run_id: str
    round_id: Optional[str] = None
    stage: str
    operation_kind: str = ""
    executor_backend: str = "local-sandbox"
    executor_kind: str = "local_process"
    executor_label: str = ""
    executor_readiness: str = "active"
    executor_contract_version: str = "v1"
    routing_mode: str = "in_process"
    governance_mode: str = "dispatcher"
    handoff_required: bool = False
    handoff_contract_version: str = ""
    handoff_fields: List[str] = Field(default_factory=list)
    handoff_ref: str = ""
    artifact_refs: List[str] = Field(default_factory=list)
    handoff_request: Optional[ExecutorHandoffRequestPayload] = None
    artifact_sync_manifest: Optional[ExecutorArtifactSyncManifestPayload] = None
    target_service_ref: str
    runtime: str
    required_capabilities: List[str] = Field(default_factory=list)
    attack_families: List[str] = Field(default_factory=list)
    requested_attack_count: int = 0
    requested_probe_count: int = 0
    requested_budget: Dict[str, Any] = Field(default_factory=dict)
    signature: str = ""


class SandboxFailurePayload(BaseModel):
    """Structured failure item emitted by the dispatcher."""

    reason_code: str
    reason_label: str = ""
    category: str = "policy_rejection"
    category_label: str = "策略拒绝"
    scope: str = "request"
    scope_label: str = "请求"
    blocking: bool = True
    details: Dict[str, Any] = Field(default_factory=dict)


class SandboxAuditEventPayload(BaseModel):
    """Audit-trail event emitted during dispatch planning/execution."""

    event_id: str
    stage: str
    event_kind: str
    event_kind_label: str = ""
    summary: str = ""
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SandboxDispatchResultPayload(BaseModel):
    """Dispatcher decision and execution summary."""

    dispatch_id: str
    run_id: str
    round_id: Optional[str] = None
    stage: str
    operation_kind: str = ""
    executor_backend: str = "local-sandbox"
    executor_kind: str = "local_process"
    executor_label: str = ""
    executor_readiness: str = "active"
    executor_contract_version: str = "v1"
    routing_mode: str = "in_process"
    governance_mode: str = "dispatcher"
    handoff_required: bool = False
    handoff_contract_version: str = ""
    handoff_fields: List[str] = Field(default_factory=list)
    handoff_ref: str = ""
    handoff_request: Optional[ExecutorHandoffRequestPayload] = None
    artifact_sync_manifest: Optional[ExecutorArtifactSyncManifestPayload] = None
    handoff_receipt: Optional[ExecutorHandoffReceiptPayload] = None
    handoff_trace: Optional[ExecutorHandoffTracePayload] = None
    target_service_ref: str
    decision: str = "approved"
    decision_label: str = "已批准"
    status: str = "planned"
    status_label: str = "待执行"
    requested_attack_count: int = 0
    approved_attack_count: int = 0
    requested_probe_count: int = 0
    approved_probe_count: int = 0
    rejection_reasons: List[str] = Field(default_factory=list)
    failure_category: str = ""
    failure_category_label: str = ""
    failure_items: List[SandboxFailurePayload] = Field(default_factory=list)
    signature: str = ""
    policy: SandboxPolicyPayload = Field(default_factory=SandboxPolicyPayload)
    audit_trail: List[SandboxAuditEventPayload] = Field(default_factory=list)
    capability_flags: List[str] = Field(default_factory=list)
    backend_capability_flags: List[str] = Field(default_factory=list)
    supported_operation_kinds: List[str] = Field(default_factory=list)
    artifact_refs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CaseRejectedOptionPayload(BaseModel):
    """Previously rejected proposal recorded in case memory."""

    proposal_id: str
    component_signature: str = ""
    reasons: List[str] = Field(default_factory=list)
    compliance_score: Optional[float] = None
    risk_score: Optional[int] = None
    recorded_at: datetime


class CaseDecisionPayload(BaseModel):
    """High-level decision log entry for a persisted case."""

    time: datetime
    action: str
    action_label: str = "未知"
    summary: str
    proposal_id: Optional[str] = None


class CaseMemoryPayload(BaseModel):
    """Project-level memory snapshot reused across MAS runs."""

    case_id: str
    created_at: datetime
    updated_at: datetime
    status: str = "new"
    status_label: str = "新建"
    scenario: str = ""
    requirement_summary: str = ""
    confirmed_constraints: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    blocking_items: List[str] = Field(default_factory=list)
    rejected_options: List[CaseRejectedOptionPayload] = Field(default_factory=list)
    decision_log: List[CaseDecisionPayload] = Field(default_factory=list)
    recent_reflections: List[Dict[str, Any]] = Field(default_factory=list)
    latest_evidence_refs: List[str] = Field(default_factory=list)
    selected_proposal: Optional[str] = None
    latest_compliance_score: Optional[float] = None
    latest_risk_score: Optional[int] = None


class CaseMemorySummaryPayload(BaseModel):
    """Compact case summary for project switching in the frontend."""

    case_id: str
    created_at: datetime
    updated_at: datetime
    status: str = "new"
    status_label: str = "新建"
    scenario: str = ""
    requirement_summary: str = ""
    selected_proposal: Optional[str] = None
    latest_compliance_score: Optional[float] = None
    latest_risk_score: Optional[int] = None
    blocking_count: int = 0
    open_question_count: int = 0
    rejected_count: int = 0
    decision_count: int = 0
    reflection_count: int = 0
    evidence_ref_count: int = 0


class TargetServiceDeploymentManifestPayload(BaseModel):
    """Stable deployment manifest for a mock target service template."""

    entrypoint: str = ""
    bootstrap_script: str = "service_runtime.py"
    healthcheck: str = "/health"
    port: Optional[int] = None
    workspace_dir: str = ""
    artifact_dir: str = ""


class TargetServiceRuntimeProfilePayload(BaseModel):
    """Runtime budget and telemetry contract for a mock target service."""

    timeout_seconds: int = 120
    memory_budget_mb: int = 256
    probe_budget: int = 64
    traffic_sampling_interval_ms: int = 250
    cleanup_policy: str = "stop_and_archive"


class EvidenceSourcePayload(BaseModel):
    """Reference or standard used to support scheme credibility."""

    type: str
    title: str
    year: Optional[int] = None
    url: Optional[str] = None
    component: Optional[str] = None


class SchemeComponentPayload(BaseModel):
    """Compact component info for frontend rendering."""

    name: str
    category: str
    security_level: Optional[int] = None
    software_speed: Optional[str] = None
    standardized: bool = False
    proven_security: bool = False
    reference_count: int = 0
    reference_titles: List[str] = Field(default_factory=list)


class ComponentEvidencePayload(BaseModel):
    """Evidence and support strength for a single component."""

    component: str
    credibility_score: float = 0.0
    support_level: str = "unknown"
    support_level_label: str = "未知"
    standardized: bool = False
    proven_security: bool = False
    reference_count: int = 0
    standards_count: int = 0
    papers_count: int = 0
    documentation_count: int = 0
    reference_titles: List[str] = Field(default_factory=list)


class CredibilityAssessmentPayload(BaseModel):
    """Trust, evidence, and algorithm strength summary."""

    credibility_score: float = 0.0
    algorithm_strength_score: float = 0.0
    evidence_coverage: float = 0.0
    audit_readiness: float = 0.0
    trust_level: str = "unknown"
    trust_level_label: str = "未知"
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    source_summary: Dict[str, Any] = Field(default_factory=dict)
    sources: List[EvidenceSourcePayload] = Field(default_factory=list)
    component_evidence: List[ComponentEvidencePayload] = Field(default_factory=list)


class SchemeImplementationPayload(BaseModel):
    """Generated code payload."""

    pseudocode: str = ""
    python: str = ""
    c: str = ""


class SchemePayload(BaseModel):
    """Serialized scheme response."""

    name: str
    scheme_type: str
    score: float
    generated_at: datetime
    security_level: Optional[int] = None
    components: List[SchemeComponentPayload] = Field(default_factory=list)
    design_rationale: str = ""
    security_analysis: Dict[str, Any] = Field(default_factory=dict)
    credibility_assessment: CredibilityAssessmentPayload = Field(default_factory=CredibilityAssessmentPayload)
    implementation: SchemeImplementationPayload = Field(default_factory=SchemeImplementationPayload)
    raw: Dict[str, Any] = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    """Scheme generation response."""

    request_id: str
    generated_at: datetime
    security_disclaimer: str
    parsed_requirement: ParsedRequirementPayload
    schemes: List[SchemePayload]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    time: datetime


class ComponentsResponse(BaseModel):
    """Lightweight component catalog response."""

    total: int
    items: List[SchemeComponentPayload]


class MASRequest(BaseModel):
    """Input payload for MAS (multi-agent system) execution."""

    requirement: str = Field(min_length=8, description="Natural-language requirement")
    num_variants: int = Field(default=3, ge=1, le=5, description="Architect candidate count")
    generate_code: bool = Field(default=True)
    llm_provider: Optional[str] = Field(default=None, description="openai / anthropic / gemini / zhipuai / deepseek / qwen / baidu / relay")
    run_id: Optional[str] = Field(default=None, description="Client-provided run ID for cancellation")
    case_id: Optional[str] = Field(default=None, description="Stable project/case identifier for cross-run memory")
    max_audit_rounds: int = Field(default=4, ge=1, le=8)
    max_same_run_retries: Optional[int] = Field(
        default=None,
        ge=0,
        le=1,
        description="Same-run retry budget for the Expert Gate attack follow-up path; null uses the backend default",
    )
    strict_clarification: bool = Field(
        default=False,
        description="When true, stop early if analyst finds blocking ambiguities",
    )


class ClarificationPayload(BaseModel):
    """Clarification question produced by analyst agent."""

    id: str
    question: str
    reason: str
    required: bool = False


class AnalystReportPayload(BaseModel):
    """Analyst output."""

    structured_spec: Dict[str, Any] = Field(default_factory=dict)
    parsed_requirement: ParsedRequirementPayload
    clarifications: List[ClarificationPayload] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    case_context: Dict[str, Any] = Field(default_factory=dict)


class ArchitectCandidatePayload(BaseModel):
    """Architect proposal."""

    proposal_id: str
    name: str
    scheme_type: str
    score: float
    security_level: Optional[int] = None
    components: List[SchemeComponentPayload] = Field(default_factory=list)
    design_rationale: str = ""
    architecture_pattern: str = ""
    estimated_performance: Dict[str, Any] = Field(default_factory=dict)
    credibility_score: Optional[float] = None
    algorithm_strength_score: Optional[float] = None
    evidence_coverage: Optional[float] = None


class ArchitectReportPayload(BaseModel):
    """Architect output."""

    toolbox_services: List[str] = Field(default_factory=list)
    candidates: List[ArchitectCandidatePayload] = Field(default_factory=list)
    evidence_pack: EvidencePackPayload = Field(default_factory=EvidencePackPayload)


class AuditorRoundPayload(BaseModel):
    """Single auditor review round."""

    round: int
    proposal_id: str
    verdict: str
    verdict_label: str = "未知"
    reasons: List[str] = Field(default_factory=list)
    compliance_score: float
    risk_score: int
    quantum_ready: bool
    quantum_ready_label: str = "否"
    standards_checked: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    recommended_changes: List[str] = Field(default_factory=list)


class BuildAttemptPayload(BaseModel):
    """Engineer self-correction attempt."""

    step: str
    status: str
    status_label: str = "未知"
    message: str


class EngineerReportPayload(BaseModel):
    """Engineer output."""

    sandbox_backend: str
    attempts: List[BuildAttemptPayload] = Field(default_factory=list)
    python_passed: bool = False
    c_passed: Optional[bool] = None
    c_compiler: Optional[str] = None
    corrected_python: str = ""
    corrected_c: str = ""


class TargetServiceSpecPayload(BaseModel):
    """Sandbox target service descriptor for attack-loop execution."""

    service_id: str
    artifact_id: str = ""
    template_id: str = "mock_crypto_http_v1"
    template_label: str = "模拟加密 HTTP 服务"
    service_kind: str = "crypto_api"
    attack_surface_kind: str = "http-json"
    service_name: str
    deployment_profile: str = "sandbox"
    service_interface: str = "api"
    attack_surface: List[str] = Field(default_factory=list)
    service_version: str = "v1"
    runtime: str = "python"
    entrypoint: str = ""
    supported_versions: List[str] = Field(default_factory=list)
    planner_skill_hints: List[str] = Field(default_factory=list)
    planner_retrieval_hints: List[str] = Field(default_factory=list)
    deployment_manifest: TargetServiceDeploymentManifestPayload = Field(
        default_factory=TargetServiceDeploymentManifestPayload
    )
    runtime_profile: TargetServiceRuntimeProfilePayload = Field(
        default_factory=TargetServiceRuntimeProfilePayload
    )
    status: str = "planned"
    status_label: str = "待部署"


class AttackSpecPayload(BaseModel):
    """Structured attack plan for a deployed target service."""

    attack_id: str
    target_service_ref: str
    attack_family: str
    objective: str = ""
    attack_surface: List[str] = Field(default_factory=list)
    expected_artifacts: List[str] = Field(default_factory=list)
    telemetry_fields: List[str] = Field(default_factory=list)
    budget: Dict[str, Any] = Field(default_factory=dict)
    status: str = "planned"
    status_label: str = "待执行"


class AttackDecisionPayload(BaseModel):
    """LLM-driven attack planning decision for the current round."""

    decision_id: str
    target_service_ref: str
    action: str = "execute"
    action_label: str = "执行攻击"
    rationale: str = ""
    selected_attack_family: str = ""
    expected_outcome: str = ""
    confidence: float = 0.0
    stop_conditions: List[str] = Field(default_factory=list)
    next_step: str = "dispatch_attack"


class AttackResultPayload(BaseModel):
    """Execution result of one attack plan."""

    attack_id: str
    target_service_ref: str
    status: str = "simulated"
    status_label: str = "已模拟"
    summary: str = ""
    findings: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    artifact_refs: List[str] = Field(default_factory=list)


class VulnerabilityVerdictPayload(BaseModel):
    """Expert-style verdict derived from attack results."""

    verdict_id: str
    target_service_ref: str
    severity: str = "medium"
    severity_label: str = "中"
    exploitability: str = "moderate"
    exploitability_label: str = "中等"
    summary: str = ""
    affected_components: List[str] = Field(default_factory=list)
    remediation_priority: str = "high"
    remediation_priority_label: str = "高"
    evidence_refs: List[str] = Field(default_factory=list)


class ExpertGateDecisionPayload(BaseModel):
    """Expert gate decision emitted between vulnerability verdict and patch planning."""

    decision_id: str
    target_service_ref: str
    decision_family: str = "patch_flow"
    decision_family_label: str = "修补闭环"
    action: str = "patch_required"
    action_label: str = "进入修补"
    route_target: str = "patch_agent"
    route_target_label: str = "修补规划窗口"
    rationale: str = ""
    confidence: float = 0.0
    residual_risk_summary: str = ""
    follow_up_actions: List[str] = Field(default_factory=list)


class PatchSpecPayload(BaseModel):
    """Patch plan emitted after vulnerability evaluation."""

    patch_id: str
    target_service_ref: str
    strategy: str = "hardening"
    summary: str = ""
    rationale: str = ""
    changed_artifacts: List[str] = Field(default_factory=list)
    implementation_notes: List[str] = Field(default_factory=list)
    validation_steps: List[str] = Field(default_factory=list)
    rollback_notes: List[str] = Field(default_factory=list)
    next_version: str = "v2"
    regression_focus: List[str] = Field(default_factory=list)


class PatchValidationResultPayload(BaseModel):
    """Execution status of one validation step after applying a patch."""

    step_id: str = ""
    step_kind: str = "custom"
    step: str
    status: str = "pending"
    status_label: str = "待执行"
    details: str = ""
    evidence: List[str] = Field(default_factory=list)
    artifact_refs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PatchExecutionPayload(BaseModel):
    """Structured execution report for the patch/regression stage."""

    execution_id: str
    patch_id: str
    execution_contract_version: str = "v1"
    target_service_ref: str
    target_service_version: str = ""
    status: str = "applied"
    status_label: str = "已应用"
    summary: str = ""
    workspace: str = ""
    applied_at: Optional[datetime] = None
    patch_dispatch_id: str = ""
    deployment_dispatch_id: str = ""
    regression_dispatch_id: str = ""
    rollback_dispatch_id: str = ""
    applied_artifacts: List[str] = Field(default_factory=list)
    patch_artifact_refs: List[str] = Field(default_factory=list)
    rollback_artifact_refs: List[str] = Field(default_factory=list)
    regression_artifact_refs: List[str] = Field(default_factory=list)
    implementation_notes: List[str] = Field(default_factory=list)
    validation_steps: List[str] = Field(default_factory=list)
    validation_results: List[PatchValidationResultPayload] = Field(default_factory=list)
    validation_summary: Dict[str, Any] = Field(default_factory=dict)
    rollback_notes: List[str] = Field(default_factory=list)
    changed_artifact_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    supporting_artifact_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    artifact_inventory: Dict[str, Any] = Field(default_factory=dict)
    diff_preview: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DiscussionTurnPayload(BaseModel):
    """Conversation turn produced by internal team."""

    actor: str
    actor_label: str = ""
    phase: str
    status: str
    status_label: str = "未知"
    message: str
    time: datetime
    data: Dict[str, Any] = Field(default_factory=dict)


class MASResponse(BaseModel):
    """MAS orchestration response."""

    request_id: str
    run_id: Optional[str] = None
    case_id: Optional[str] = None
    generated_at: datetime
    security_disclaimer: str
    analyst: AnalystReportPayload
    architect: ArchitectReportPayload
    auditor_rounds: List[AuditorRoundPayload]
    engineer: EngineerReportPayload
    final_scheme: Optional[SchemePayload] = None
    credibility_assessment: CredibilityAssessmentPayload = Field(default_factory=CredibilityAssessmentPayload)
    compliance_report: Dict[str, Any] = Field(default_factory=dict)
    vulnerability_report: Dict[str, Any] = Field(default_factory=dict)
    discussion_log: List[DiscussionTurnPayload] = Field(default_factory=list)
    evidence_pack: EvidencePackPayload = Field(default_factory=EvidencePackPayload)
    case_memory: Optional[CaseMemoryPayload] = None
    delivery: Dict[str, Any] = Field(default_factory=dict)


class CaseListResponse(BaseModel):
    """Case list response for frontend project switching."""

    total: int
    items: List[CaseMemorySummaryPayload] = Field(default_factory=list)


class CaseDeleteResponse(BaseModel):
    """Delete response for a persisted case snapshot."""

    case_id: str
    deleted: bool = True
    message: str = "项目已删除"


class ReplayVersionLineagePayload(BaseModel):
    """Lightweight version lineage used by replay overview APIs."""

    run_id: str = ""
    baseline_version: str = ""
    patched_version: str = ""
    patch_id: str = ""
    target_service_ref: str = ""
    created_at: Optional[datetime] = None


class ReplayDispatchSummaryPayload(BaseModel):
    """Stable dispatch summary exposed by replay APIs."""

    dispatch_key: str = ""
    dispatch_id: str = ""
    stage: str = ""
    operation_kind: str = ""
    executor_kind: str = ""
    executor_backend: str = ""
    executor_label: str = ""
    target_service_ref: str = ""
    decision: str = ""
    status: str = ""
    failure_category: str = ""
    handoff_ref: str = ""
    artifact_refs: List[str] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)
    summary: str = ""


class ReplayExecutorHandoffTraceSummaryPayload(BaseModel):
    """Replay-friendly typed summary for executor handoff traces."""

    dispatch_key: str = ""
    dispatch_id: str = ""
    handoff_ref: str = ""
    stage: str = ""
    operation_kind: str = ""
    executor_kind: str = ""
    executor_backend: str = ""
    governance_mode: str = ""
    routing_mode: str = ""
    adapter_stage: str = ""
    trace_status: str = ""
    receipt_ref: str = ""
    receipt_status: str = ""
    accepted: bool = False
    remote_job_ref: str = ""
    artifact_sync_ref: str = ""
    artifact_sync_status: str = ""
    target_service_ref: str = ""
    artifact_refs: List[str] = Field(default_factory=list)
    failure_category: str = ""
    summary: str = ""


class ReplaySnapshotSummaryPayload(BaseModel):
    """Replay snapshot summary exposed by timeline APIs."""

    snapshot_id: str
    run_id: str
    status: str = ""
    selected_proposal: Optional[str] = None
    workflow_trace: List[str] = Field(default_factory=list)
    summary: str = ""
    created_at: datetime
    projection_refs: List[str] = Field(default_factory=list)
    handoff_refs: List[str] = Field(default_factory=list)
    dispatch_refs: List[str] = Field(default_factory=list)
    failed_dispatch_refs: List[str] = Field(default_factory=list)
    dispatch_summaries: List[ReplayDispatchSummaryPayload] = Field(default_factory=list)
    failed_dispatch_summaries: List[ReplayDispatchSummaryPayload] = Field(default_factory=list)
    executor_handoff_trace_summaries: List[ReplayExecutorHandoffTraceSummaryPayload] = Field(
        default_factory=list
    )
    typed_family_counts: Dict[str, int] = Field(default_factory=dict)
    typed_contract_counts: Dict[str, int] = Field(default_factory=dict)
    artifact_lookup_refs: List[str] = Field(default_factory=list)
    evidence_lookup_refs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CaseTimelineSummaryPayload(BaseModel):
    """Compact timeline counts for replay and audit entrypoints."""

    case_id: str
    latest_run_id: str = ""
    latest_status: str = ""
    snapshot_count: int = 0
    event_count: int = 0
    version_lineage_count: int = 0
    latest_projection_ref_count: int = 0
    latest_handoff_ref_count: int = 0
    latest_dispatch_ref_count: int = 0
    latest_failed_dispatch_ref_count: int = 0
    latest_dispatch_summary_count: int = 0
    latest_failed_dispatch_summary_count: int = 0
    latest_executor_handoff_trace_count: int = 0
    latest_typed_family_count: int = 0
    latest_typed_contract_count: int = 0


class CaseTimelineOverviewResponse(BaseModel):
    """Overview response for one case timeline."""

    case_id: str
    updated_at: datetime
    latest_run_id: str = ""
    latest_status: str = ""
    timeline_summary: CaseTimelineSummaryPayload
    latest_snapshot: Optional[ReplaySnapshotSummaryPayload] = None
    latest_version_lineage: Optional[ReplayVersionLineagePayload] = None


class CaseTimelineEventPayload(BaseModel):
    """Lightweight execution event returned by timeline queries."""

    event_id: str
    case_id: str
    run_id: str
    stage: str
    event_kind: str
    status: str = ""
    summary: str = ""
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CaseTimelineEventListScopePayload(BaseModel):
    """Filter scope echoed by timeline event queries."""

    run_id: str = ""
    event_kind: str = ""
    stage: str = ""
    contract_ref: str = ""
    lineage_ref: str = ""
    projection_ref: str = ""
    handoff_ref: str = ""
    artifact_lookup_ref: str = ""
    evidence_lookup_ref: str = ""
    retry_resume_checkpoint_ref: str = ""
    retry_resume_input_ref: str = ""


class CaseTimelineEventListResponse(BaseModel):
    """Filtered event list for one case timeline."""

    case_id: str
    scope: CaseTimelineEventListScopePayload
    total: int = 0
    items: List[CaseTimelineEventPayload] = Field(default_factory=list)


class CaseTimelineSnapshotListScopePayload(BaseModel):
    """Filter scope echoed by timeline snapshot queries."""

    run_id: str = ""
    contract_ref: str = ""
    projection_ref: str = ""
    handoff_ref: str = ""
    artifact_lookup_ref: str = ""
    evidence_lookup_ref: str = ""
    retry_resume_checkpoint_ref: str = ""
    retry_resume_input_ref: str = ""


class CaseTimelineSnapshotListResponse(BaseModel):
    """Filtered snapshot list for one case timeline."""

    case_id: str
    scope: CaseTimelineSnapshotListScopePayload
    total: int = 0
    items: List[ReplaySnapshotSummaryPayload] = Field(default_factory=list)


class CaseTimelineLineageListResponse(BaseModel):
    """Filtered version-lineage list for one case timeline."""

    case_id: str
    total: int = 0
    items: List[ReplayVersionLineagePayload] = Field(default_factory=list)


class CaseTimelineDrilldownScopePayload(BaseModel):
    """Single-case drill-down scope for replay aggregation."""

    run_id: str = ""
    projection_ref: str = ""
    handoff_ref: str = ""
    artifact_lookup_ref: str = ""
    evidence_lookup_ref: str = ""
    retry_resume_checkpoint_ref: str = ""
    retry_resume_input_ref: str = ""


class CaseTimelineDrilldownSummaryPayload(BaseModel):
    """Aggregated replay summary for one scoped drill-down query."""

    matched_run_ids: List[str] = Field(default_factory=list)
    snapshot_count: int = 0
    event_count: int = 0
    version_lineage_count: int = 0
    projection_refs: List[str] = Field(default_factory=list)
    handoff_refs: List[str] = Field(default_factory=list)
    dispatch_refs: List[str] = Field(default_factory=list)
    failed_dispatch_refs: List[str] = Field(default_factory=list)
    dispatch_summaries: List[ReplayDispatchSummaryPayload] = Field(default_factory=list)
    failed_dispatch_summaries: List[ReplayDispatchSummaryPayload] = Field(default_factory=list)
    executor_handoff_trace_summaries: List[ReplayExecutorHandoffTraceSummaryPayload] = Field(
        default_factory=list
    )
    artifact_lookup_refs: List[str] = Field(default_factory=list)
    evidence_lookup_refs: List[str] = Field(default_factory=list)
    typed_contract_refs: List[str] = Field(default_factory=list)
    target_service_refs: List[str] = Field(default_factory=list)
    retry_window_count: int = 0
    retry_handoff_count: int = 0
    retry_projection_refs: List[str] = Field(default_factory=list)
    retry_handoff_refs: List[str] = Field(default_factory=list)
    retry_lineage_refs: List[str] = Field(default_factory=list)
    retry_typed_contract_refs: List[str] = Field(default_factory=list)
    retry_compression_stages: List[str] = Field(default_factory=list)
    retry_compression_policies: List[str] = Field(default_factory=list)
    retry_retained_refs: List[str] = Field(default_factory=list)
    retry_resume_checkpoint_refs: List[str] = Field(default_factory=list)
    retry_resume_input_refs: List[str] = Field(default_factory=list)


class CaseTimelineRelationPayload(BaseModel):
    """Lightweight relation view derived from replay drill-down results."""

    relation_kind: str
    relation_ref: str
    source_agent_id: str = ""
    target_agent_id: str = ""
    upstream_stage: str = ""
    downstream_stage: str = ""
    handoff_projection_ref: str = ""
    dominant_typed_contract: str = ""
    agent_ids: List[str] = Field(default_factory=list)
    linked_projection_refs: List[str] = Field(default_factory=list)
    linked_handoff_refs: List[str] = Field(default_factory=list)
    typed_contract_refs: List[str] = Field(default_factory=list)
    artifact_lookup_refs: List[str] = Field(default_factory=list)
    evidence_lookup_refs: List[str] = Field(default_factory=list)
    target_service_refs: List[str] = Field(default_factory=list)
    stage_counts: Dict[str, int] = Field(default_factory=dict)
    event_kind_counts: Dict[str, int] = Field(default_factory=dict)
    snapshot_count: int = 0
    event_count: int = 0
    version_lineage_count: int = 0


class CaseTimelineServiceTrajectoryPayload(BaseModel):
    """Aggregated target-service trajectory derived from replay drill-down results."""

    target_service_ref: str
    run_ids: List[str] = Field(default_factory=list)
    baseline_versions: List[str] = Field(default_factory=list)
    patched_versions: List[str] = Field(default_factory=list)
    patch_ids: List[str] = Field(default_factory=list)
    stages: List[str] = Field(default_factory=list)
    event_kind_counts: Dict[str, int] = Field(default_factory=dict)
    latest_status: str = ""
    latest_summary: str = ""


class CaseTimelineDrilldownResponse(BaseModel):
    """Bundled replay drill-down response for one case scope."""

    case_id: str
    scope: CaseTimelineDrilldownScopePayload
    summary: CaseTimelineDrilldownSummaryPayload
    projection_relationships: List[CaseTimelineRelationPayload] = Field(default_factory=list)
    handoff_relationships: List[CaseTimelineRelationPayload] = Field(default_factory=list)
    service_trajectories: List[CaseTimelineServiceTrajectoryPayload] = Field(default_factory=list)
    snapshots: List[ReplaySnapshotSummaryPayload] = Field(default_factory=list)
    events: List[CaseTimelineEventPayload] = Field(default_factory=list)
    version_lineage: List[ReplayVersionLineagePayload] = Field(default_factory=list)


class KnowledgeChunkPreviewPayload(BaseModel):
    """Lightweight chunk preview for ingestion feedback."""

    chunk_id: str
    title: str
    section: str = ""
    snippet: str = ""
    source_page: Optional[int] = None


class KnowledgeIngestedFilePayload(BaseModel):
    """Single uploaded document ingestion result."""

    file_name: str
    stored_path: str
    doc_id: str
    title: str
    block_count: int = 0
    chunk_count: int = 0
    previews: List[KnowledgeChunkPreviewPayload] = Field(default_factory=list)


class KnowledgeIngestionResponse(BaseModel):
    """Response returned after uploading and chunking enterprise knowledge."""

    request_id: str
    doc_type: str
    total_files: int = 0
    total_chunks: int = 0
    output_path: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    qdrant_requested: bool = False
    qdrant_upserted: bool = False
    qdrant_message: str = ""
    files: List[KnowledgeIngestedFilePayload] = Field(default_factory=list)


class KnowledgeIngestionRecordPayload(BaseModel):
    """Persisted knowledge ingestion record for asset-management views."""

    request_id: str
    created_at: datetime
    deleted_at: Optional[datetime] = None
    qdrant_deleted_at: Optional[datetime] = None
    doc_type: str
    total_files: int = 0
    total_chunks: int = 0
    output_path: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    qdrant_requested: bool = False
    qdrant_upserted: bool = False
    qdrant_message: str = ""
    local_artifacts_present: bool = True
    qdrant_cleanup_required: bool = False
    files: List[KnowledgeIngestedFilePayload] = Field(default_factory=list)


class KnowledgeIngestionListResponse(BaseModel):
    """List of persisted knowledge ingestion records."""

    total: int = 0
    items: List[KnowledgeIngestionRecordPayload] = Field(default_factory=list)


class KnowledgeDeleteResponse(BaseModel):
    """Delete response for uploaded knowledge artifacts."""

    request_id: str
    deleted: bool = True
    deleted_paths: List[str] = Field(default_factory=list)
    message: str = "知识导入产物已删除"


class KnowledgeQdrantDeleteResponse(BaseModel):
    """Delete response for Qdrant replicas created by uploaded knowledge."""

    request_id: str
    deleted: bool = True
    deleted_points: int = 0
    qdrant_deleted_at: Optional[datetime] = None
    message: str = "Qdrant 副本已删除"


class KnowledgeQdrantReingestResponse(BaseModel):
    """Reingest response for Qdrant replicas rebuilt from local JSONL."""

    request_id: str
    reingested: bool = True
    upserted_points: int = 0
    message: str = "Qdrant 副本已重建"


class MASReportRequest(BaseModel):
    """Input payload to generate a full MAS report package."""

    mas_result: Dict[str, Any]
    scenario: Optional[str] = Field(default=None, description="Optional scenario hint, e.g. construction")
    include_code: bool = True
    include_pdf: bool = False


class MASReportResponse(BaseModel):
    """Full report package generated from MAS result."""

    generated_at: datetime
    scenario: str
    selected_scheme: str
    template_id: str = ""
    template_name: str = ""
    enterprise_delivery: Dict[str, Any] = Field(default_factory=dict)
    html: str
    markdown: str
    latex: str
    comparison: Dict[str, Any] = Field(default_factory=dict)
    charts: Dict[str, Any] = Field(default_factory=dict)
    deployment_guide: List[str] = Field(default_factory=list)
    pdf_base64: Optional[str] = None
    pdf_error: Optional[str] = None


class LLMValidationRequest(BaseModel):
    """Request payload to validate LLM provider connectivity."""

    provider: str = Field(description="openai / anthropic / gemini / zhipuai / deepseek / qwen / baidu / relay")
    prompt: str = Field(default="Return only the word OK.", min_length=2)
    timeout_seconds: int = Field(default=20, ge=5, le=60)
    api_key: Optional[str] = Field(default=None, description="Optional transient API key for validation")
    model: Optional[str] = Field(default=None, description="Optional transient model for validation")
    base_url: Optional[str] = Field(default=None, description="Optional transient provider endpoint")


class LLMValidationResponse(BaseModel):
    """Response payload for LLM validation."""

    provider: str
    success: bool
    message: str
    latency_ms: int
    sample_output: str = ""


class EnvSettingsPayload(BaseModel):
    """Editable env settings from frontend."""

    default_llm_provider: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    zhipuai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    baidu_api_key: Optional[str] = None
    relay_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    anthropic_model: Optional[str] = None
    zhipuai_model: Optional[str] = None
    gemini_model: Optional[str] = None
    deepseek_model: Optional[str] = None
    qwen_model: Optional[str] = None
    baidu_model: Optional[str] = None
    relay_model: Optional[str] = None
    openai_base_url: Optional[str] = None
    anthropic_base_url: Optional[str] = None
    zhipuai_base_url: Optional[str] = None
    gemini_base_url: Optional[str] = None
    deepseek_base_url: Optional[str] = None
    qwen_base_url: Optional[str] = None
    baidu_base_url: Optional[str] = None
    relay_base_url: Optional[str] = None


class EnvSettingsResponse(BaseModel):
    """Current env settings snapshot."""

    env_path: str
    values: Dict[str, Any]
    persisted: bool = False


class SkillSummaryPayload(BaseModel):
    """Public skill metadata for frontend selectors."""

    id: str
    name: str
    description: str
    version: str = "1.0.0"
    status: str = "active"
    category: str = "general"
    execution_mode: str = "mas"
    tags: List[str] = Field(default_factory=list)
    target_users: List[str] = Field(default_factory=list)
    output_focus: List[str] = Field(default_factory=list)
    example_requirement: str = ""
    recommended_num_variants: int = 3
    recommended_max_audit_rounds: int = 4
    generate_code_default: bool = True
    strict_clarification_default: bool = False


class SkillListResponse(BaseModel):
    """List of available skills."""

    total: int
    items: List[SkillSummaryPayload] = Field(default_factory=list)


class SkillExecuteRequest(BaseModel):
    """Execute a manifest-driven skill."""

    skill_id: str
    requirement: str = Field(min_length=8)
    llm_provider: Optional[str] = Field(default=None, description="openai / anthropic / gemini / zhipuai / deepseek / qwen / baidu / relay")
    run_id: Optional[str] = None
    case_id: Optional[str] = None
    num_variants: Optional[int] = Field(default=None, ge=1, le=5)
    generate_code: Optional[bool] = None
    max_audit_rounds: Optional[int] = Field(default=None, ge=1, le=8)
    max_same_run_retries: Optional[int] = Field(default=None, ge=0, le=1)
    strict_clarification: Optional[bool] = None
    use_langgraph: bool = Field(
        default=True,
        description="Deprecated compatibility flag retained for stable integrations; nested MAS now always runs the LangGraph mainline",
        json_schema_extra={"deprecated": True},
    )


class SkillRouteRequest(BaseModel):
    """Route a requirement to the best matching skills."""

    requirement: str = Field(min_length=8)
    max_candidates: int = Field(default=3, ge=1, le=8)


class SkillRouteCandidatePayload(BaseModel):
    """Single routed skill recommendation."""

    skill: SkillSummaryPayload
    score: float = 0.0
    matched_keywords: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)


class SkillRouteResponse(BaseModel):
    """Recommended skills for a requirement."""

    requirement: str
    routing_version: str
    confidence: float = 0.0
    recommended_skill: Optional[SkillSummaryPayload] = None
    candidates: List[SkillRouteCandidatePayload] = Field(default_factory=list)


class SkillExecutionResponse(BaseModel):
    """Skill execution result plus generated MAS output."""

    skill: SkillSummaryPayload
    enhanced_requirement: str
    applied_overrides: Dict[str, Any] = Field(default_factory=dict)
    result: MASResponse


class BenchmarkCaseResultPayload(BaseModel):
    """Single benchmark case result."""

    case_id: str
    scenario: str
    requirement: str
    expected_skill_id: str
    recommended_skill_id: Optional[str] = None
    expected_template_id: str
    resolved_template_id: Optional[str] = None
    skill_match: bool = False
    template_match: bool = False
    section_coverage_ok: bool = False
    candidate_ids: List[str] = Field(default_factory=list)
    missing_sections: List[str] = Field(default_factory=list)


class BenchmarkRunResponse(BaseModel):
    """Aggregated benchmark run response."""

    benchmark_id: str
    benchmark_name: str
    scenario: str
    total_cases: int
    skill_hits: int
    template_hits: int
    section_hits: int
    skill_hit_rate: float = 0.0
    template_hit_rate: float = 0.0
    section_hit_rate: float = 0.0
    cases: List[BenchmarkCaseResultPayload] = Field(default_factory=list)


class ConstructionDemoRunRequest(BaseModel):
    """Run the localhost BuildTrust construction attack demonstration."""

    project_id: str = Field(default="buildtrust-demo-project", min_length=3, max_length=120)
    run_id: Optional[str] = Field(default=None, min_length=3, max_length=120)


class ConstructionAttackResultPayload(BaseModel):
    """Single construction-domain attack, remediation, and regression result."""

    case_id: str
    attack_type: str
    detected: bool
    blocked: bool
    severity: str
    summary: str
    before_state: Dict[str, Any] = Field(default_factory=dict)
    after_state: Dict[str, Any] = Field(default_factory=dict)
    remediation: str
    regression_passed: bool
    evidence_refs: List[str] = Field(default_factory=list)
    artifact_refs: List[str] = Field(default_factory=list)


class ConstructionDemoRunResponse(BaseModel):
    """Aggregated five-attack BuildTrust demonstration result."""

    run_id: str
    project_id: str
    status: str
    security_profile: str = "hardened"
    crypto_provider_mode: str = "local_demo"
    provider_mac_enabled: bool = False
    provider_signature_enabled: bool = False
    capability_boundary: str
    workspace: str
    attack_count: int
    detected_count: int
    blocked_count: int
    regression_passed_count: int
    evidence_ledger_valid: bool
    evidence_refs: List[str] = Field(default_factory=list)
    results: List[ConstructionAttackResultPayload] = Field(default_factory=list)
