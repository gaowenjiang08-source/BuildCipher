"""FastAPI application for BuildCipher Studio."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from queue import Empty, Queue
import threading
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from cipher_genius.api.benchmark_service import BenchmarkService
from cipher_genius.api.construction_service import ConstructionDemoService
from cipher_genius.api.knowledge_ingestion_service import KnowledgeIngestionService
from cipher_genius.core.langgraph_mas import LangGraphMASService
from cipher_genius.api.report_service import MASReportService
from cipher_genius.api.schemas import (
    BenchmarkRunResponse,
    CaseDeleteResponse,
    CaseListResponse,
    CaseMemoryPayload,
    CaseTimelineEventListResponse,
    CaseTimelineEventPayload,
    CaseTimelineDrilldownResponse,
    CaseTimelineRelationPayload,
    CaseTimelineDrilldownScopePayload,
    CaseTimelineDrilldownSummaryPayload,
    CaseTimelineServiceTrajectoryPayload,
    CaseTimelineLineageListResponse,
    CaseTimelineOverviewResponse,
    CaseTimelineSnapshotListResponse,
    CaseTimelineSummaryPayload,
    ComponentsResponse,
    ConstructionDemoRunRequest,
    ConstructionDemoRunResponse,
    EnvSettingsPayload,
    EnvSettingsResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    KnowledgeDeleteResponse,
    KnowledgeIngestionResponse,
    KnowledgeIngestionListResponse,
    KnowledgeQdrantDeleteResponse,
    KnowledgeQdrantReingestResponse,
    LLMValidationRequest,
    LLMValidationResponse,
    MASRequest,
    MASReportRequest,
    MASReportResponse,
    MASResponse,
    ReplaySnapshotSummaryPayload,
    ReplayVersionLineagePayload,
    SchemeComponentPayload,
    SkillExecuteRequest,
    SkillExecutionResponse,
    SkillListResponse,
    SkillRouteRequest,
    SkillRouteResponse,
)
from cipher_genius.memory import CaseMemoryService, CaseTimelineService
from cipher_genius.api.skill_service import SkillExecutionService
from cipher_genius.api.settings_service import get_env_settings, update_env_settings
from cipher_genius.api.service import GenerationService
from cipher_genius.core.llm_interface import get_llm_interface
from cipher_genius.knowledge.components import get_component_library
from cipher_genius.utils.config import get_settings
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)

settings = get_settings()
RUN_CANCEL_EVENTS: dict[str, threading.Event] = {}
RUN_REGISTRY_LOCK = threading.Lock()

SUPPORTED_LLM_PROVIDERS = {
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "google",
    "zhipuai",
    "glm",
    "deepseek",
    "qwen",
    "tongyi",
    "dashscope",
    "baidu",
    "wenxin",
    "qianfan",
    "relay",
    "openai_compatible",
    "custom",
}

app = FastAPI(
    title="BuildTrust API",
    version="1.0.0",
    description="Local API for construction digital-asset trust and cryptographic strategy.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _normalize_text_value(value: Any) -> str | None:
    """Normalize placeholder text values for frontend display."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if text.lower() in {"unknown", "n/a", "na", "none", "null"}:
        return None

    return text


def _normalize_llm_provider(value: str | None) -> str | None:
    """Normalize provider names so APIs accept 'OpenAI'/'OPENAI' etc."""
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


def _validate_llm_provider(value: str | None) -> str | None:
    """Validate provider string without requiring API keys (offline fallback still supported)."""
    normalized = _normalize_llm_provider(value)
    if normalized is None:
        return None
    if normalized not in SUPPORTED_LLM_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
        raise ValueError(f"Unknown llm_provider: {value}. Supported: {supported}")
    return normalized


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", service="buildcipher-api", time=datetime.now(timezone.utc))


@app.post("/api/v1/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest) -> GenerateResponse:
    """Generate one or more schemes from natural-language requirements."""
    try:
        llm_provider = _validate_llm_provider(payload.llm_provider)
        service = GenerationService(llm_provider)
        resolved_payload = payload.model_copy(update={"llm_provider": llm_provider})
        return service.generate(resolved_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Generation failed")
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc


@app.post("/api/v1/mas/execute", response_model=MASResponse)
def execute_mas(payload: MASRequest, use_langgraph: bool = Query(default=True, deprecated=True)) -> MASResponse:
    """Run multi-agent orchestration workflow.

    Args:
        payload: MAS request payload
        use_langgraph: Deprecated compatibility flag. The API now always runs the LangGraph mainline.
    """
    try:
        llm_provider = _validate_llm_provider(payload.llm_provider)
        payload = payload.model_copy(update={"llm_provider": llm_provider})
        if not use_langgraph:
            logger.warning("Received deprecated use_langgraph=false on /api/v1/mas/execute; forcing LangGraph mainline")
        logger.info("Using LangGraph MAS engine for run")
        service = LangGraphMASService(payload.llm_provider)

        run_id = payload.run_id or str(uuid4())
        result = service.execute(payload, request_id=run_id)
        result.delivery = {**(result.delivery or {}), "engine": "langgraph"}
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("MAS execution failed")
        raise HTTPException(status_code=500, detail=f"MAS execution failed: {exc}") from exc


@app.get("/api/v1/cases/{case_id}", response_model=CaseMemoryPayload)
def get_case_memory(case_id: str) -> CaseMemoryPayload:
    """Read persisted project-level case memory."""
    try:
        service = CaseMemoryService()
        return service.get(case_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Case memory read failed")
        raise HTTPException(status_code=500, detail=f"Case memory read failed: {exc}") from exc


@app.get("/api/v1/cases", response_model=CaseListResponse)
def list_cases(limit: int = Query(default=20, ge=1, le=100)) -> CaseListResponse:
    """List recent project-level case snapshots for frontend switching."""
    try:
        service = CaseMemoryService()
        items = service.list(limit=limit)
        return CaseListResponse(total=len(items), items=items)
    except Exception as exc:
        logger.exception("Case memory list failed")
        raise HTTPException(status_code=500, detail=f"Case memory list failed: {exc}") from exc


@app.delete("/api/v1/cases/{case_id}", response_model=CaseDeleteResponse)
def delete_case_memory(case_id: str) -> CaseDeleteResponse:
    """Delete a persisted project-level case memory snapshot."""
    try:
        service = CaseMemoryService()
        service.delete(case_id)
        return CaseDeleteResponse(case_id=case_id, deleted=True, message="项目记忆已删除")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Case memory delete failed")
        raise HTTPException(status_code=500, detail=f"Case memory delete failed: {exc}") from exc


@app.get("/api/v1/cases/{case_id}/timeline", response_model=CaseTimelineOverviewResponse)
def get_case_timeline(case_id: str) -> CaseTimelineOverviewResponse:
    """Read the local replay overview for one case."""
    try:
        service = CaseTimelineService()
        payload = service.get_timeline_summary(case_id)
        if payload is None:
            raise FileNotFoundError(f"Case timeline not found: {case_id}")
        return CaseTimelineOverviewResponse(
            case_id=payload["case_id"],
            updated_at=payload["updated_at"],
            latest_run_id=payload.get("latest_run_id") or "",
            latest_status=payload.get("latest_status") or "",
            timeline_summary=CaseTimelineSummaryPayload.model_validate(payload.get("timeline_summary") or {}),
            latest_snapshot=(
                ReplaySnapshotSummaryPayload.model_validate(payload["latest_snapshot"])
                if payload.get("latest_snapshot")
                else None
            ),
            latest_version_lineage=(
                ReplayVersionLineagePayload.model_validate(payload["latest_version_lineage"])
                if payload.get("latest_version_lineage")
                else None
            ),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Case timeline read failed")
        raise HTTPException(status_code=500, detail=f"Case timeline read failed: {exc}") from exc


@app.get("/api/v1/cases/{case_id}/timeline/events", response_model=CaseTimelineEventListResponse)
def list_case_timeline_events(
    case_id: str,
    run_id: str | None = Query(default=None),
    event_kind: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    contract_ref: str | None = Query(default=None),
    lineage_ref: str | None = Query(default=None),
    projection_ref: str | None = Query(default=None),
    handoff_ref: str | None = Query(default=None),
    artifact_lookup_ref: str | None = Query(default=None),
    evidence_lookup_ref: str | None = Query(default=None),
    retry_resume_checkpoint_ref: str | None = Query(default=None),
    retry_resume_input_ref: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> CaseTimelineEventListResponse:
    """Query local replay events for one case."""
    try:
        service = CaseTimelineService()
        if service.load(case_id) is None:
            raise FileNotFoundError(f"Case timeline not found: {case_id}")
        items = service.query_events(
            case_id,
            run_id=run_id,
            event_kind=event_kind,
            stage=stage,
            contract_ref=contract_ref,
            lineage_ref=lineage_ref,
            projection_ref=projection_ref,
            handoff_ref=handoff_ref,
            artifact_lookup_ref=artifact_lookup_ref,
            evidence_lookup_ref=evidence_lookup_ref,
            retry_resume_checkpoint_ref=retry_resume_checkpoint_ref,
            retry_resume_input_ref=retry_resume_input_ref,
            limit=limit,
        )
        return CaseTimelineEventListResponse(
            case_id=case_id,
            scope={
                "run_id": run_id or "",
                "event_kind": event_kind or "",
                "stage": stage or "",
                "contract_ref": contract_ref or "",
                "lineage_ref": lineage_ref or "",
                "projection_ref": projection_ref or "",
                "handoff_ref": handoff_ref or "",
                "artifact_lookup_ref": artifact_lookup_ref or "",
                "evidence_lookup_ref": evidence_lookup_ref or "",
                "retry_resume_checkpoint_ref": retry_resume_checkpoint_ref or "",
                "retry_resume_input_ref": retry_resume_input_ref or "",
            },
            total=len(items),
            items=[CaseTimelineEventPayload.model_validate(item.model_dump(mode="json")) for item in items],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Case timeline event query failed")
        raise HTTPException(status_code=500, detail=f"Case timeline event query failed: {exc}") from exc


@app.get("/api/v1/cases/{case_id}/timeline/snapshots", response_model=CaseTimelineSnapshotListResponse)
def list_case_timeline_snapshots(
    case_id: str,
    run_id: str | None = Query(default=None),
    contract_ref: str | None = Query(default=None),
    projection_ref: str | None = Query(default=None),
    handoff_ref: str | None = Query(default=None),
    artifact_lookup_ref: str | None = Query(default=None),
    evidence_lookup_ref: str | None = Query(default=None),
    retry_resume_checkpoint_ref: str | None = Query(default=None),
    retry_resume_input_ref: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> CaseTimelineSnapshotListResponse:
    """Query local replay snapshots for one case."""
    try:
        service = CaseTimelineService()
        if service.load(case_id) is None:
            raise FileNotFoundError(f"Case timeline not found: {case_id}")
        items = service.query_snapshots(
            case_id,
            run_id=run_id,
            contract_ref=contract_ref,
            projection_ref=projection_ref,
            handoff_ref=handoff_ref,
            artifact_lookup_ref=artifact_lookup_ref,
            evidence_lookup_ref=evidence_lookup_ref,
            retry_resume_checkpoint_ref=retry_resume_checkpoint_ref,
            retry_resume_input_ref=retry_resume_input_ref,
            limit=limit,
        )
        return CaseTimelineSnapshotListResponse(
            case_id=case_id,
            scope={
                "run_id": run_id or "",
                "contract_ref": contract_ref or "",
                "projection_ref": projection_ref or "",
                "handoff_ref": handoff_ref or "",
                "artifact_lookup_ref": artifact_lookup_ref or "",
                "evidence_lookup_ref": evidence_lookup_ref or "",
                "retry_resume_checkpoint_ref": retry_resume_checkpoint_ref or "",
                "retry_resume_input_ref": retry_resume_input_ref or "",
            },
            total=len(items),
            items=[ReplaySnapshotSummaryPayload.model_validate(item.model_dump(mode="json")) for item in items],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Case timeline snapshot query failed")
        raise HTTPException(status_code=500, detail=f"Case timeline snapshot query failed: {exc}") from exc


@app.get("/api/v1/cases/{case_id}/timeline/drilldown", response_model=CaseTimelineDrilldownResponse)
def get_case_timeline_drilldown(
    case_id: str,
    run_id: str | None = Query(default=None),
    projection_ref: str | None = Query(default=None),
    handoff_ref: str | None = Query(default=None),
    artifact_lookup_ref: str | None = Query(default=None),
    evidence_lookup_ref: str | None = Query(default=None),
    retry_resume_checkpoint_ref: str | None = Query(default=None),
    retry_resume_input_ref: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> CaseTimelineDrilldownResponse:
    """Bundle snapshots, events and lineage for one scoped replay drill-down."""
    try:
        service = CaseTimelineService()
        payload = service.get_timeline_drilldown(
            case_id,
            run_id=run_id,
            projection_ref=projection_ref,
            handoff_ref=handoff_ref,
            artifact_lookup_ref=artifact_lookup_ref,
            evidence_lookup_ref=evidence_lookup_ref,
            retry_resume_checkpoint_ref=retry_resume_checkpoint_ref,
            retry_resume_input_ref=retry_resume_input_ref,
            limit=limit,
        )
        if payload is None:
            raise FileNotFoundError(f"Case timeline not found: {case_id}")
        return CaseTimelineDrilldownResponse(
            case_id=payload["case_id"],
            scope=CaseTimelineDrilldownScopePayload.model_validate(payload.get("scope") or {}),
            summary=CaseTimelineDrilldownSummaryPayload.model_validate(payload.get("summary") or {}),
            projection_relationships=[
                CaseTimelineRelationPayload.model_validate(item)
                for item in (payload.get("projection_relationships") or [])
            ],
            handoff_relationships=[
                CaseTimelineRelationPayload.model_validate(item)
                for item in (payload.get("handoff_relationships") or [])
            ],
            service_trajectories=[
                CaseTimelineServiceTrajectoryPayload.model_validate(item)
                for item in (payload.get("service_trajectories") or [])
            ],
            snapshots=[
                ReplaySnapshotSummaryPayload.model_validate(item)
                for item in (payload.get("snapshots") or [])
            ],
            events=[
                CaseTimelineEventPayload.model_validate(item)
                for item in (payload.get("events") or [])
            ],
            version_lineage=[
                ReplayVersionLineagePayload.model_validate(item)
                for item in (payload.get("version_lineage") or [])
            ],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Case timeline drilldown query failed")
        raise HTTPException(status_code=500, detail=f"Case timeline drilldown query failed: {exc}") from exc


@app.get("/api/v1/cases/{case_id}/timeline/lineage", response_model=CaseTimelineLineageListResponse)
def list_case_timeline_lineage(
    case_id: str,
    run_id: str | None = Query(default=None),
    target_service_ref: str | None = Query(default=None),
    patch_id: str | None = Query(default=None),
    baseline_version: str | None = Query(default=None),
    patched_version: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> CaseTimelineLineageListResponse:
    """Query local version-lineage records for one case."""
    try:
        service = CaseTimelineService()
        if service.load(case_id) is None:
            raise FileNotFoundError(f"Case timeline not found: {case_id}")
        items = service.query_version_lineage(
            case_id,
            run_id=run_id,
            target_service_ref=target_service_ref,
            patch_id=patch_id,
            baseline_version=baseline_version,
            patched_version=patched_version,
            limit=limit,
        )
        return CaseTimelineLineageListResponse(
            case_id=case_id,
            total=len(items),
            items=[ReplayVersionLineagePayload.model_validate(item.model_dump(mode="json")) for item in items],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Case timeline lineage query failed")
        raise HTTPException(status_code=500, detail=f"Case timeline lineage query failed: {exc}") from exc


@app.post("/api/v1/knowledge/ingest", response_model=KnowledgeIngestionResponse)
async def ingest_knowledge_documents(
    files: list[UploadFile] = File(...),
    doc_type: str = Form(...),
    title: str = Form(default=""),
    metadata_json: str = Form(default="{}"),
    upsert_qdrant: bool = Form(default=False),
) -> KnowledgeIngestionResponse:
    """Upload PDF/DOCX files, chunk them, and optionally seed Qdrant."""
    try:
        metadata = json.loads(metadata_json or "{}")
        if not isinstance(metadata, dict):
            raise ValueError("metadata_json 必须是 JSON 对象。")
        service = KnowledgeIngestionService()
        return await service.ingest_uploads(
            files=files,
            doc_type=doc_type,
            metadata=metadata,
            title=title,
            upsert_qdrant=upsert_qdrant,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Knowledge ingestion failed")
        raise HTTPException(status_code=500, detail=f"Knowledge ingestion failed: {exc}") from exc


@app.delete("/api/v1/knowledge/ingest/{request_id}", response_model=KnowledgeDeleteResponse)
def delete_knowledge_ingestion(request_id: str) -> KnowledgeDeleteResponse:
    """Delete locally persisted files produced by a knowledge ingestion request."""
    try:
        service = KnowledgeIngestionService()
        return service.delete_ingestion_artifacts(request_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Knowledge ingestion delete failed")
        raise HTTPException(status_code=500, detail=f"Knowledge ingestion delete failed: {exc}") from exc


@app.delete("/api/v1/knowledge/ingest/{request_id}/qdrant", response_model=KnowledgeQdrantDeleteResponse)
def delete_knowledge_ingestion_qdrant(request_id: str) -> KnowledgeQdrantDeleteResponse:
    """Delete Qdrant replicas produced by a knowledge ingestion request."""
    try:
        service = KnowledgeIngestionService()
        return service.delete_qdrant_artifacts(request_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Knowledge ingestion Qdrant cleanup failed")
        raise HTTPException(status_code=500, detail=f"Knowledge ingestion Qdrant cleanup failed: {exc}") from exc


@app.post("/api/v1/knowledge/ingest/{request_id}/qdrant", response_model=KnowledgeQdrantReingestResponse)
def reingest_knowledge_ingestion_qdrant(request_id: str) -> KnowledgeQdrantReingestResponse:
    """Rebuild Qdrant replicas from persisted JSONL artifacts for a knowledge ingestion request."""
    try:
        service = KnowledgeIngestionService()
        return service.reingest_qdrant_artifacts(request_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Knowledge ingestion Qdrant reingest failed")
        raise HTTPException(status_code=500, detail=f"Knowledge ingestion Qdrant reingest failed: {exc}") from exc


@app.get("/api/v1/knowledge/ingestions", response_model=KnowledgeIngestionListResponse)
def list_knowledge_ingestions(limit: int = Query(default=20, ge=1, le=100)) -> KnowledgeIngestionListResponse:
    """List persisted knowledge-ingestion records for the asset-management view."""
    try:
        service = KnowledgeIngestionService()
        return service.list_ingestions(limit=limit)
    except Exception as exc:
        logger.exception("Knowledge ingestion list failed")
        raise HTTPException(status_code=500, detail=f"Knowledge ingestion list failed: {exc}") from exc


@app.get("/api/v1/skills", response_model=SkillListResponse)
def list_skills() -> SkillListResponse:
    """List available manifest-driven skills."""
    service = SkillExecutionService()
    return service.list_skills()


@app.post("/api/v1/skills/execute", response_model=SkillExecutionResponse)
def execute_skill(payload: SkillExecuteRequest) -> SkillExecutionResponse:
    """Run a skill and return the nested MAS result."""
    try:
        run_id = payload.run_id or str(uuid4())
        llm_provider = _validate_llm_provider(payload.llm_provider)
        service = SkillExecutionService(llm_provider)
        resolved_payload = payload.model_copy(update={"run_id": run_id, "llm_provider": llm_provider})
        return service.execute(resolved_payload, request_id=run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Skill execution failed")
        raise HTTPException(status_code=500, detail=f"Skill execution failed: {exc}") from exc


@app.post("/api/v1/skills/route", response_model=SkillRouteResponse)
def route_skill(payload: SkillRouteRequest) -> SkillRouteResponse:
    """Recommend the best matching skills for a requirement."""
    try:
        service = SkillExecutionService()
        return service.route(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Skill routing failed")
        raise HTTPException(status_code=500, detail=f"Skill routing failed: {exc}") from exc


@app.get("/api/v1/benchmarks/construction", response_model=BenchmarkRunResponse)
def run_construction_benchmark() -> BenchmarkRunResponse:
    """Run the built-in construction routing/template regression benchmark."""
    try:
        service = BenchmarkService()
        return service.run_construction_benchmark()
    except Exception as exc:
        logger.exception("Construction benchmark failed")
        raise HTTPException(status_code=500, detail=f"Construction benchmark failed: {exc}") from exc


@app.post("/api/v1/construction/demo/run", response_model=ConstructionDemoRunResponse)
def run_construction_demo(payload: ConstructionDemoRunRequest) -> ConstructionDemoRunResponse:
    """Execute five construction attacks using localhost cryptographic operations."""
    try:
        return ConstructionDemoService().run(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Construction demo failed")
        raise HTTPException(status_code=500, detail=f"Construction demo failed: {exc}") from exc


@app.post("/api/v1/mas/report", response_model=MASReportResponse)
def generate_mas_report(payload: MASReportRequest) -> MASReportResponse:
    """Generate a full report package (Markdown/LaTeX/PDF) from MAS result."""
    try:
        service = MASReportService()
        return service.generate_report(
            mas_result=payload.mas_result,
            scenario=payload.scenario,
            include_code=payload.include_code,
            include_pdf=payload.include_pdf,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("MAS report generation failed")
        raise HTTPException(status_code=500, detail=f"MAS report generation failed: {exc}") from exc


@app.post("/api/v1/mas/stream")
def execute_mas_stream(payload: MASRequest, use_langgraph: bool = Query(default=True, deprecated=True)) -> StreamingResponse:
    """Run MAS workflow and stream progress events (NDJSON).

    Args:
        payload: MAS request payload
        use_langgraph: Deprecated compatibility flag. The API now always runs the LangGraph mainline.
    """
    llm_provider = _validate_llm_provider(payload.llm_provider)
    queue: Queue[dict] = Queue()
    done = threading.Event()
    run_id = payload.run_id or str(uuid4())
    cancel_event = threading.Event()
    resolved_payload = payload.model_copy(update={"llm_provider": llm_provider, "run_id": run_id})

    with RUN_REGISTRY_LOCK:
        RUN_CANCEL_EVENTS[run_id] = cancel_event

    def runner() -> None:
        try:
            if not use_langgraph:
                logger.warning(f"[{run_id}] Received deprecated use_langgraph=false on /api/v1/mas/stream; forcing LangGraph mainline")
            logger.info(f"[{run_id}] Using LangGraph MAS engine for streaming")
            service = LangGraphMASService(llm_provider)

            queue.put({"type": "run", "run_id": run_id, "engine": "langgraph"})

            def on_progress(turn: Any) -> None:
                queue.put({"type": "progress", "data": turn.model_dump(mode="json")})

            result = service.execute(
                resolved_payload,
                progress_callback=on_progress,
                request_id=run_id,
                cancel_check=cancel_event.is_set,
            )
            result.delivery = {**(result.delivery or {}), "engine": "langgraph"}
            queue.put({"type": "final", "data": result.model_dump(mode="json")})
        except Exception as exc:
            message = str(exc)
            if "cancelled" in message.lower():
                queue.put({"type": "cancelled", "run_id": run_id, "message": message})
            else:
                queue.put({"type": "error", "message": message})
        finally:
            done.set()
            with RUN_REGISTRY_LOCK:
                RUN_CANCEL_EVENTS.pop(run_id, None)

    def stream() -> Any:
        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        while not (done.is_set() and queue.empty()):
            try:
                item = queue.get(timeout=0.25)
                yield json.dumps(item, ensure_ascii=False) + "\n"
            except Empty:
                continue

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.post("/api/v1/skills/stream")
def execute_skill_stream(payload: SkillExecuteRequest) -> StreamingResponse:
    """Run skill workflow and stream progress events (NDJSON)."""
    llm_provider = _validate_llm_provider(payload.llm_provider)
    queue: Queue[dict] = Queue()
    done = threading.Event()
    run_id = payload.run_id or str(uuid4())
    cancel_event = threading.Event()
    resolved_payload = payload.model_copy(update={"run_id": run_id, "llm_provider": llm_provider})

    with RUN_REGISTRY_LOCK:
        RUN_CANCEL_EVENTS[run_id] = cancel_event

    def runner() -> None:
        try:
            service = SkillExecutionService(llm_provider)
            queue.put(
                {
                    "type": "run",
                    "run_id": run_id,
                    "engine": "langgraph",
                }
            )

            def on_progress(turn: Any) -> None:
                queue.put({"type": "progress", "data": turn.model_dump(mode="json")})

            result = service.execute(
                resolved_payload,
                progress_callback=on_progress,
                request_id=run_id,
                cancel_check=cancel_event.is_set,
            )
            queue.put({"type": "final", "data": result.model_dump(mode="json")})
        except Exception as exc:
            message = str(exc)
            if "cancelled" in message.lower():
                queue.put({"type": "cancelled", "run_id": run_id, "message": message})
            else:
                queue.put({"type": "error", "message": message})
        finally:
            done.set()
            with RUN_REGISTRY_LOCK:
                RUN_CANCEL_EVENTS.pop(run_id, None)

    def stream() -> Any:
        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        while not (done.is_set() and queue.empty()):
            try:
                item = queue.get(timeout=0.25)
                yield json.dumps(item, ensure_ascii=False) + "\n"
            except Empty:
                continue

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.post("/api/v1/mas/cancel/{run_id}")
def cancel_mas_run(run_id: str) -> dict[str, Any]:
    """Cancel a running MAS stream job."""
    with RUN_REGISTRY_LOCK:
        event = RUN_CANCEL_EVENTS.get(run_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    event.set()
    return {"status": "cancelling", "run_id": run_id}


@app.post("/api/v1/llm/validate", response_model=LLMValidationResponse)
def validate_llm(payload: LLMValidationRequest) -> LLMValidationResponse:
    """Validate real LLM API connectivity for a provider."""
    started = time.perf_counter()
    try:
        provider = _validate_llm_provider(payload.provider)
        llm = get_llm_interface(
            provider,
            api_key=(payload.api_key or None),
            model=(payload.model or None),
            base_url=(payload.base_url or None),
        )
        output = llm.generate(
            prompt=payload.prompt,
            system_prompt="Reply very briefly.",
            temperature=0.0,
            max_tokens=20,
        )
        elapsed = int((time.perf_counter() - started) * 1000)
        return LLMValidationResponse(
            provider=payload.provider,
            success=True,
            message="LLM API connected successfully.",
            latency_ms=elapsed,
            sample_output=(output or "").strip()[:200],
        )
    except Exception as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return LLMValidationResponse(
            provider=payload.provider,
            success=False,
            message=str(exc),
            latency_ms=elapsed,
            sample_output="",
        )


@app.get("/api/v1/settings/env", response_model=EnvSettingsResponse)
def read_env_settings() -> EnvSettingsResponse:
    """Read selected backend env settings."""
    return get_env_settings()


@app.post("/api/v1/settings/env", response_model=EnvSettingsResponse)
def write_env_settings(payload: EnvSettingsPayload) -> EnvSettingsResponse:
    """Persist selected settings into backend .env."""
    return update_env_settings(payload)


@app.get("/api/v1/components", response_model=ComponentsResponse)
def list_components(limit: int = Query(default=200, ge=1, le=1000)) -> ComponentsResponse:
    """List component catalog for frontend selectors."""
    library = get_component_library()
    all_components = library.list_all()
    items = []
    for component in all_components[:limit]:
        items.append(
            SchemeComponentPayload(
                name=component.name,
                category=component.category.value if hasattr(component.category, "value") else str(component.category),
                security_level=component.security.security_level,
                software_speed=_normalize_text_value(component.performance.software_speed),
                standardized=bool(component.security.standardized),
                proven_security=bool(component.security.proven_security),
                reference_count=len(component.references or []),
                reference_titles=[ref.title for ref in (component.references or [])[:3]],
            )
        )

    return ComponentsResponse(total=len(all_components), items=items)


def run() -> None:
    """Run API server."""
    uvicorn.run(
        "cipher_genius.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
