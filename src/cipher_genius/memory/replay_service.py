"""Persistence helpers for case timeline, replay snapshots and audit history."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field


class ExecutionEvent(BaseModel):
    """One persisted event on the case timeline."""

    event_id: str
    case_id: str
    run_id: str
    stage: str
    event_kind: str
    status: str = ""
    summary: str = ""
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class VersionLineage(BaseModel):
    """Compact version relationship for replay and audit."""

    run_id: str = ""
    baseline_version: str = ""
    patched_version: str = ""
    patch_id: str = ""
    target_service_ref: str = ""
    created_at: datetime | None = None


class ReplayDispatchSummary(BaseModel):
    """Stable dispatch summary for replay snapshots and drill-down views."""

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
    artifact_refs: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    summary: str = ""


class ReplayExecutorHandoffTraceSummary(BaseModel):
    """Stable executor-handoff trace summary for replay snapshots."""

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
    artifact_refs: list[str] = Field(default_factory=list)
    failure_category: str = ""
    summary: str = ""


class ReplaySnapshot(BaseModel):
    """Persisted replay snapshot for one run."""

    snapshot_id: str
    case_id: str
    run_id: str
    status: str = ""
    selected_proposal: str | None = None
    workflow_trace: list[str] = Field(default_factory=list)
    summary: str = ""
    created_at: datetime
    projection_refs: list[str] = Field(default_factory=list)
    handoff_refs: list[str] = Field(default_factory=list)
    dispatch_refs: list[str] = Field(default_factory=list)
    failed_dispatch_refs: list[str] = Field(default_factory=list)
    dispatch_summaries: list[ReplayDispatchSummary] = Field(default_factory=list)
    failed_dispatch_summaries: list[ReplayDispatchSummary] = Field(default_factory=list)
    executor_handoff_trace_summaries: list[ReplayExecutorHandoffTraceSummary] = Field(
        default_factory=list
    )
    typed_family_counts: dict[str, int] = Field(default_factory=dict)
    typed_contract_counts: dict[str, int] = Field(default_factory=dict)
    artifact_lookup_refs: list[str] = Field(default_factory=list)
    evidence_lookup_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseTimeline(BaseModel):
    """Top-level case timeline persisted on disk."""

    case_id: str
    updated_at: datetime
    latest_run_id: str = ""
    latest_status: str = ""
    events: list[ExecutionEvent] = Field(default_factory=list)
    snapshots: list[ReplaySnapshot] = Field(default_factory=list)
    version_lineage: list[VersionLineage] = Field(default_factory=list)


class CaseTimelineService:
    """Persist and retrieve execution timelines for replay and audit."""

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        if storage_dir is None:
            repo_root = Path(__file__).resolve().parents[3]
            storage_dir = repo_root / ".cache" / "case_timelines"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def load(self, case_id: str) -> CaseTimeline | None:
        """Load a case timeline if present."""

        path = self._path_for(case_id)
        if not path.exists():
            return None
        try:
            return CaseTimeline.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return None

    def load_or_create(self, case_id: str) -> CaseTimeline:
        """Load a persisted timeline or create an empty one."""

        return self.load(case_id) or CaseTimeline(
            case_id=case_id,
            updated_at=datetime.now(timezone.utc),
        )

    def record_run(
        self,
        *,
        case_id: str,
        run_id: str,
        delivery: dict[str, Any],
        control_plane: dict[str, Any],
        execution_plane: dict[str, Any],
        memory_bus: dict[str, Any] | None = None,
    ) -> tuple[ReplaySnapshot, dict[str, Any]]:
        """Persist a run-level replay snapshot and return a lightweight summary."""

        timeline = self.load_or_create(case_id)
        now = datetime.now(timezone.utc)
        memory_bus = memory_bus or {}
        replay_snapshot_card = dict(memory_bus.get("replay_snapshot_card") or {})
        memory_bus_summary = dict(memory_bus.get("summary") or {})
        dispatch_catalog = self._extract_dispatch_catalog(delivery)
        dispatch_refs = [
            item.get("dispatch_id") or ""
            for item in dispatch_catalog
            if str(item.get("dispatch_id") or "").strip()
        ]
        failed_dispatch_refs = [
            item.get("dispatch_id") or ""
            for item in dispatch_catalog
            if str(item.get("status") or "").strip() in {"failed", "blocked"}
        ]
        patch_execution_artifact_refs = self._extract_patch_execution_artifact_refs(delivery)
        dispatch_artifact_refs = self._extract_dispatch_artifact_refs(dispatch_catalog)
        dispatch_summaries = self._build_dispatch_summaries(dispatch_catalog)
        failed_dispatch_summaries = self._build_dispatch_summaries(dispatch_catalog, failed_only=True)
        executor_handoff_trace_summaries = self._build_executor_handoff_trace_summaries(delivery)
        snapshot = ReplaySnapshot(
            snapshot_id=f"snapshot-{run_id[:8]}",
            case_id=case_id,
            run_id=run_id,
            status=str(delivery.get("status") or ""),
            selected_proposal=delivery.get("selected_proposal"),
            workflow_trace=list(delivery.get("workflow_trace") or []),
            summary=(
                f"本轮状态为 {str(delivery.get('status_label') or delivery.get('status') or '未知')}，"
                f"共经过 {len(delivery.get('workflow_trace') or [])} 个主流程阶段。"
            ),
            created_at=now,
            projection_refs=list(replay_snapshot_card.get("projection_refs") or [])[:16],
            handoff_refs=list(replay_snapshot_card.get("handoff_refs") or [])[:16],
            dispatch_refs=self._dedupe_refs(dispatch_refs)[:16],
            failed_dispatch_refs=self._dedupe_refs(failed_dispatch_refs)[:16],
            dispatch_summaries=dispatch_summaries,
            failed_dispatch_summaries=failed_dispatch_summaries,
            executor_handoff_trace_summaries=executor_handoff_trace_summaries,
            typed_family_counts=dict(replay_snapshot_card.get("typed_family_counts") or {}),
            typed_contract_counts=dict(replay_snapshot_card.get("typed_contract_counts") or {}),
            artifact_lookup_refs=self._dedupe_refs(
                [
                    *list(replay_snapshot_card.get("artifact_lookup_refs") or []),
                    *patch_execution_artifact_refs,
                    *dispatch_artifact_refs,
                ]
            )[:24],
            evidence_lookup_refs=list(replay_snapshot_card.get("evidence_lookup_refs") or [])[:16],
            metadata={
                "compliance_score": delivery.get("compliance_score"),
                "risk_score": delivery.get("risk_score"),
                "control_stage_count": (control_plane or {}).get("summary", {}).get("stage_count", 0),
                "execution_stage_count": (execution_plane or {}).get("summary", {}).get("stage_count", 0),
                "memory_projection_count": memory_bus.get("projection_count", 0),
                "memory_handoff_count": memory_bus.get("handoff_count", 0),
                "typed_family_count": memory_bus_summary.get("typed_family_count", 0),
                "typed_contract_count": memory_bus_summary.get("typed_contract_count", 0),
                "dominant_memory_family": memory_bus_summary.get("dominant_family", ""),
                "dominant_memory_contract": memory_bus_summary.get("dominant_contract", ""),
                "artifact_ref_count": max(
                    int(replay_snapshot_card.get("artifact_ref_count", 0) or 0),
                    len(
                        self._dedupe_refs(
                            [
                                *list(replay_snapshot_card.get("artifact_lookup_refs") or []),
                                *patch_execution_artifact_refs,
                                *dispatch_artifact_refs,
                            ]
                        )
                    ),
                ),
                "evidence_ref_count": replay_snapshot_card.get("evidence_ref_count", 0),
                "lineage_ref_count": len(replay_snapshot_card.get("lineage_refs") or []),
                "artifact_lookup_ref_count": len(
                    self._dedupe_refs(
                        [
                            *list(replay_snapshot_card.get("artifact_lookup_refs") or []),
                            *patch_execution_artifact_refs,
                            *dispatch_artifact_refs,
                        ]
                    )
                ),
                "evidence_lookup_ref_count": len(replay_snapshot_card.get("evidence_lookup_refs") or []),
                "dispatch_ref_count": len(self._dedupe_refs(dispatch_refs)),
                "failed_dispatch_ref_count": len(self._dedupe_refs(failed_dispatch_refs)),
                "dispatch_summary_count": len(dispatch_summaries),
                "failed_dispatch_summary_count": len(failed_dispatch_summaries),
                "executor_handoff_trace_count": len(executor_handoff_trace_summaries),
                "patch_execution_artifact_ref_count": len(self._dedupe_refs(patch_execution_artifact_refs)),
                "window_catalog": self._extract_window_catalog(memory_bus),
                "handoff_catalog": self._extract_handoff_catalog(memory_bus),
                "dispatch_catalog": dispatch_catalog,
                "patch_execution_artifact_refs": self._dedupe_refs(patch_execution_artifact_refs)[:24],
                **self._extract_retry_snapshot_metadata(memory_bus_summary),
            },
        )
        timeline.snapshots.append(snapshot)
        timeline.events.extend(
            self._build_run_events(
                case_id=case_id,
                run_id=run_id,
                delivery=delivery,
                execution_plane=execution_plane,
                memory_bus=memory_bus,
                created_at=now,
            )
        )
        lineage = self._build_version_lineage(delivery, run_id=run_id, created_at=now)
        if lineage is not None:
            timeline.version_lineage.append(lineage)
        timeline.updated_at = now
        timeline.latest_run_id = run_id
        timeline.latest_status = str(delivery.get("status") or "")
        self._save(timeline)
        return snapshot, self._build_timeline_summary(timeline)

    def get_timeline_summary(self, case_id: str) -> dict[str, Any] | None:
        """Return a lightweight replay summary for one case."""

        timeline = self.load(case_id)
        if timeline is None:
            return None

        latest_snapshot = timeline.snapshots[-1] if timeline.snapshots else None
        latest_lineage = timeline.version_lineage[-1] if timeline.version_lineage else None
        return {
            "case_id": timeline.case_id,
            "updated_at": timeline.updated_at,
            "latest_run_id": timeline.latest_run_id,
            "latest_status": timeline.latest_status,
            "timeline_summary": self._build_timeline_summary(timeline),
            "latest_snapshot": latest_snapshot.model_dump(mode="json") if latest_snapshot else None,
            "latest_version_lineage": latest_lineage.model_dump(mode="json") if latest_lineage else None,
        }

    def query_events(
        self,
        case_id: str,
        *,
        run_id: str | None = None,
        event_kind: str | None = None,
        stage: str | None = None,
        contract_ref: str | None = None,
        lineage_ref: str | None = None,
        projection_ref: str | None = None,
        handoff_ref: str | None = None,
        artifact_lookup_ref: str | None = None,
        evidence_lookup_ref: str | None = None,
        retry_resume_checkpoint_ref: str | None = None,
        retry_resume_input_ref: str | None = None,
        limit: int = 20,
    ) -> list[ExecutionEvent]:
        """Query persisted timeline events with lightweight filters."""

        timeline = self.load(case_id)
        if timeline is None:
            return []

        allowed_run_ids = self._resolve_snapshot_run_scope(
            timeline,
            run_id=run_id,
            projection_ref=projection_ref,
            handoff_ref=handoff_ref,
            artifact_lookup_ref=artifact_lookup_ref,
            evidence_lookup_ref=evidence_lookup_ref,
            retry_resume_checkpoint_ref=retry_resume_checkpoint_ref,
            retry_resume_input_ref=retry_resume_input_ref,
        )
        direct_items: list[ExecutionEvent] = []
        scoped_items: list[ExecutionEvent] = []
        for event in reversed(timeline.events):
            if run_id and event.run_id != run_id:
                continue
            if event_kind and event.event_kind != event_kind:
                continue
            if stage and event.stage != stage:
                continue
            if contract_ref and not self._event_matches_contract(event, contract_ref):
                continue
            if lineage_ref and not self._event_matches_lineage(event, lineage_ref):
                continue
            projection_hit = not projection_ref or self._event_matches_lookup(
                event,
                lookup_ref=projection_ref,
                metadata_keys=("window_refs", "projection_ref"),
            )
            if not projection_hit and not self._event_is_scoped_to_runs(event, allowed_run_ids):
                continue
            handoff_hit = not handoff_ref or self._event_matches_lookup(
                event,
                lookup_ref=handoff_ref,
                metadata_keys=("handoff_refs", "handoff_id"),
            )
            if not handoff_hit and not self._event_is_scoped_to_runs(event, allowed_run_ids):
                continue
            artifact_hit = not artifact_lookup_ref or self._event_matches_lookup(
                event,
                lookup_ref=artifact_lookup_ref,
                metadata_keys=("artifact_lookup_refs", "artifact_refs", "artifact_id"),
            )
            if not artifact_hit and not self._event_is_scoped_to_runs(event, allowed_run_ids):
                continue
            evidence_hit = not evidence_lookup_ref or self._event_matches_lookup(
                event,
                lookup_ref=evidence_lookup_ref,
                metadata_keys=("evidence_lookup_refs", "evidence_refs", "doc_id", "chunk_id"),
            )
            if not evidence_hit and not self._event_is_scoped_to_runs(event, allowed_run_ids):
                continue
            retry_resume_checkpoint_hit = (
                not retry_resume_checkpoint_ref
                or self._event_matches_lookup(
                    event,
                    lookup_ref=retry_resume_checkpoint_ref,
                    metadata_keys=("retry_resume_checkpoint_refs", "resume_checkpoint_ref"),
                )
            )
            if not retry_resume_checkpoint_hit and not self._event_is_scoped_to_runs(event, allowed_run_ids):
                continue
            retry_resume_input_hit = (
                not retry_resume_input_ref
                or self._event_matches_lookup(
                    event,
                    lookup_ref=retry_resume_input_ref,
                    metadata_keys=("retry_resume_input_refs", "resume_input_ref", "resume_input_refs"),
                )
            )
            if not retry_resume_input_hit and not self._event_is_scoped_to_runs(event, allowed_run_ids):
                continue
            if (
                projection_hit
                and handoff_hit
                and artifact_hit
                and evidence_hit
                and retry_resume_checkpoint_hit
                and retry_resume_input_hit
            ):
                direct_items.append(event)
            elif self._event_is_scoped_to_runs(event, allowed_run_ids):
                scoped_items.append(event)

        combined: list[ExecutionEvent] = []
        seen_event_ids: set[str] = set()
        for event in [*direct_items, *scoped_items]:
            if event.event_id in seen_event_ids:
                continue
            seen_event_ids.add(event.event_id)
            combined.append(event)
            if len(combined) >= max(limit, 1):
                break
        return combined

    def query_snapshots(
        self,
        case_id: str,
        *,
        run_id: str | None = None,
        contract_ref: str | None = None,
        projection_ref: str | None = None,
        handoff_ref: str | None = None,
        artifact_lookup_ref: str | None = None,
        evidence_lookup_ref: str | None = None,
        retry_resume_checkpoint_ref: str | None = None,
        retry_resume_input_ref: str | None = None,
        limit: int = 20,
    ) -> list[ReplaySnapshot]:
        """Query replay snapshots with typed-contract and lookup-ref filters."""

        timeline = self.load(case_id)
        if timeline is None:
            return []

        items: list[ReplaySnapshot] = []
        for snapshot in reversed(timeline.snapshots):
            if run_id and snapshot.run_id != run_id:
                continue
            if contract_ref and not self._snapshot_matches_contract(snapshot, contract_ref):
                continue
            if projection_ref and projection_ref not in set(snapshot.projection_refs or []):
                continue
            if handoff_ref and handoff_ref not in set(snapshot.handoff_refs or []):
                continue
            if artifact_lookup_ref and artifact_lookup_ref not in set(snapshot.artifact_lookup_refs or []):
                continue
            if evidence_lookup_ref and evidence_lookup_ref not in set(snapshot.evidence_lookup_refs or []):
                continue
            if retry_resume_checkpoint_ref and not self._snapshot_matches_retry_lookup(
                snapshot,
                lookup_ref=retry_resume_checkpoint_ref,
                metadata_key="retry_resume_checkpoint_refs",
            ):
                continue
            if retry_resume_input_ref and not self._snapshot_matches_retry_lookup(
                snapshot,
                lookup_ref=retry_resume_input_ref,
                metadata_key="retry_resume_input_refs",
            ):
                continue
            items.append(snapshot)
            if len(items) >= max(limit, 1):
                break
        return items

    def get_timeline_drilldown(
        self,
        case_id: str,
        *,
        run_id: str | None = None,
        projection_ref: str | None = None,
        handoff_ref: str | None = None,
        artifact_lookup_ref: str | None = None,
        evidence_lookup_ref: str | None = None,
        retry_resume_checkpoint_ref: str | None = None,
        retry_resume_input_ref: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any] | None:
        """Return a bundled replay drill-down view for one scoped case query."""

        timeline = self.load(case_id)
        if timeline is None:
            return None
        if not any(
            [
                run_id,
                projection_ref,
                handoff_ref,
                artifact_lookup_ref,
                evidence_lookup_ref,
                retry_resume_checkpoint_ref,
                retry_resume_input_ref,
            ]
        ):
            raise ValueError("At least one drill-down scope is required")

        snapshots = self.query_snapshots(
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
        matched_run_ids = [item.run_id for item in snapshots if item.run_id]
        if run_id and run_id not in matched_run_ids:
            matched_run_ids.insert(0, run_id)
        matched_run_ids = list(dict.fromkeys(matched_run_ids))

        events = self.query_events(
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
        run_events = self._query_events_for_run_ids(
            timeline,
            run_ids=matched_run_ids,
            limit=max(limit * 4, limit),
        )
        lineage_items = self._query_lineage_for_run_ids(
            timeline,
            run_ids=matched_run_ids,
            limit=limit,
        )

        projection_refs = sorted(
            {
                ref
                for snapshot in snapshots
                for ref in snapshot.projection_refs
                if str(ref).strip()
            }
        )[:16]
        handoff_refs = sorted(
            {
                ref
                for snapshot in snapshots
                for ref in snapshot.handoff_refs
                if str(ref).strip()
            }
        )[:16]
        dispatch_refs = sorted(
            {
                ref
                for snapshot in snapshots
                for ref in snapshot.dispatch_refs
                if str(ref).strip()
            }
        )[:16]
        failed_dispatch_refs = sorted(
            {
                ref
                for snapshot in snapshots
                for ref in snapshot.failed_dispatch_refs
                if str(ref).strip()
            }
        )[:16]
        artifact_lookup_refs = sorted(
            {
                ref
                for snapshot in snapshots
                for ref in snapshot.artifact_lookup_refs
                if str(ref).strip()
            }
        )[:16]
        evidence_lookup_refs = sorted(
            {
                ref
                for snapshot in snapshots
                for ref in snapshot.evidence_lookup_refs
                if str(ref).strip()
            }
        )[:16]
        typed_contract_refs = sorted(
            {
                ref
                for snapshot in snapshots
                for ref in (snapshot.typed_contract_counts or {}).keys()
                if str(ref).strip()
            }
        )[:24]
        target_service_refs = sorted(
            {
                item.target_service_ref
                for item in lineage_items
                if str(item.target_service_ref).strip()
            }
        )[:16]
        dispatch_summaries = self._merge_dispatch_summaries(snapshots=snapshots)
        failed_dispatch_summaries = self._merge_dispatch_summaries(snapshots=snapshots, failed_only=True)
        executor_handoff_trace_summaries = self._merge_executor_handoff_trace_summaries(
            snapshots=snapshots
        )
        projection_relation_refs = self._prioritize_relation_ref(
            relation_refs=projection_refs,
            preferred_ref=projection_ref,
        )
        handoff_relation_refs = self._prioritize_relation_ref(
            relation_refs=handoff_refs,
            preferred_ref=handoff_ref,
        )
        projection_relationships = self._build_relation_views(
            relation_kind="projection",
            relation_refs=projection_relation_refs,
            snapshots=snapshots,
            events=events,
            version_lineage=lineage_items,
        )
        handoff_relationships = self._build_relation_views(
            relation_kind="handoff",
            relation_refs=handoff_relation_refs,
            snapshots=snapshots,
            events=events,
            version_lineage=lineage_items,
        )
        service_trajectories = self._build_service_trajectories(
            events=run_events,
            version_lineage=lineage_items,
        )
        retry_summary = self._merge_retry_snapshot_metadata(snapshots=snapshots)

        return {
            "case_id": case_id,
            "scope": {
                "run_id": run_id or "",
                "projection_ref": projection_ref or "",
                "handoff_ref": handoff_ref or "",
                "artifact_lookup_ref": artifact_lookup_ref or "",
                "evidence_lookup_ref": evidence_lookup_ref or "",
                "retry_resume_checkpoint_ref": retry_resume_checkpoint_ref or "",
                "retry_resume_input_ref": retry_resume_input_ref or "",
            },
            "summary": {
                "matched_run_ids": matched_run_ids[:16],
                "snapshot_count": len(snapshots),
                "event_count": len(events),
                "version_lineage_count": len(lineage_items),
                "projection_refs": projection_refs,
                "handoff_refs": handoff_refs,
                "dispatch_refs": dispatch_refs,
                "failed_dispatch_refs": failed_dispatch_refs,
                "dispatch_summaries": dispatch_summaries,
                "failed_dispatch_summaries": failed_dispatch_summaries,
                "executor_handoff_trace_summaries": executor_handoff_trace_summaries,
                "artifact_lookup_refs": artifact_lookup_refs,
                "evidence_lookup_refs": evidence_lookup_refs,
                "typed_contract_refs": typed_contract_refs,
                "target_service_refs": target_service_refs,
                **retry_summary,
            },
            "projection_relationships": projection_relationships,
            "handoff_relationships": handoff_relationships,
            "service_trajectories": service_trajectories,
            "snapshots": [item.model_dump(mode="json") for item in snapshots],
            "events": [item.model_dump(mode="json") for item in events],
            "version_lineage": [item.model_dump(mode="json") for item in lineage_items],
        }

    def query_version_lineage(
        self,
        case_id: str,
        *,
        run_id: str | None = None,
        target_service_ref: str | None = None,
        patch_id: str | None = None,
        baseline_version: str | None = None,
        patched_version: str | None = None,
        limit: int = 20,
    ) -> list[VersionLineage]:
        """Query persisted version lineage records with lightweight filters."""

        timeline = self.load(case_id)
        if timeline is None:
            return []

        items: list[VersionLineage] = []
        for lineage in reversed(timeline.version_lineage):
            if run_id and lineage.run_id != run_id:
                continue
            if target_service_ref and lineage.target_service_ref != target_service_ref:
                continue
            if patch_id and lineage.patch_id != patch_id:
                continue
            if baseline_version and lineage.baseline_version != baseline_version:
                continue
            if patched_version and lineage.patched_version != patched_version:
                continue
            items.append(lineage)
            if len(items) >= max(limit, 1):
                break
        return items

    def _build_run_events(
        self,
        *,
        case_id: str,
        run_id: str,
        delivery: dict[str, Any],
        execution_plane: dict[str, Any],
        memory_bus: dict[str, Any],
        created_at: datetime,
    ) -> list[ExecutionEvent]:
        events: list[ExecutionEvent] = [
            ExecutionEvent(
                event_id=f"event-{run_id[:8]}-delivery",
                case_id=case_id,
                run_id=run_id,
                stage="delivery",
                event_kind="run_completed",
                status=str(delivery.get("status") or ""),
                summary=str(delivery.get("next_action") or "流程已结束。"),
                created_at=created_at,
                metadata={
                    "selected_proposal": delivery.get("selected_proposal"),
                },
            )
        ]
        for index, item in enumerate(execution_plane.get("stages") or [], start=1):
            events.append(
                ExecutionEvent(
                    event_id=f"event-{run_id[:8]}-exec-{index}",
                    case_id=case_id,
                    run_id=run_id,
                    stage=str(item.get("stage_kind") or "execution"),
                    event_kind="execution_stage",
                    status=str(item.get("status") or ""),
                    summary=str(item.get("summary") or ""),
                    created_at=created_at,
                    metadata=dict(item.get("metadata") or {}),
                )
            )
        if memory_bus:
            summary = dict(memory_bus.get("summary") or {})
            events.append(
                ExecutionEvent(
                    event_id=f"event-{run_id[:8]}-memory-bus",
                    case_id=case_id,
                    run_id=run_id,
                    stage="memory_bus",
                    event_kind="memory_bus_snapshot",
                    status="captured",
                    summary=(
                        f"记录 {memory_bus.get('projection_count', 0)} 个窗口、"
                        f"{memory_bus.get('handoff_count', 0)} 个 handoff、"
                        f"{summary.get('typed_family_count', 0)} 个 typed families、"
                        f"{summary.get('typed_contract_count', 0)} 个 typed contracts。"
                    ),
                    created_at=created_at,
                    metadata={
                        "projection_count": memory_bus.get("projection_count", 0),
                        "handoff_count": memory_bus.get("handoff_count", 0),
                        "typed_family_count": summary.get("typed_family_count", 0),
                        "typed_contract_count": summary.get("typed_contract_count", 0),
                        "dominant_family": summary.get("dominant_family", ""),
                        "dominant_contract": summary.get("dominant_contract", ""),
                    },
                )
            )
            for index, family in enumerate(memory_bus.get("typed_families") or [], start=1):
                family_name = str(family.get("family") or "").strip()
                if not family_name:
                    continue
                events.append(
                    ExecutionEvent(
                        event_id=f"event-{run_id[:8]}-memory-family-{index}",
                        case_id=case_id,
                        run_id=run_id,
                        stage="memory_bus",
                        event_kind="typed_memory_family",
                        status="indexed",
                        summary=(
                            f"记录 typed family `{family_name}`，"
                            f"覆盖 {family.get('card_count', 0)} 张 cards 与 {family.get('handoff_count', 0)} 个 handoff。"
                        ),
                        created_at=created_at,
                        metadata={
                            "family": family_name,
                            "family_label": family.get("family_label") or family_name,
                            "card_count": family.get("card_count", 0),
                            "handoff_count": family.get("handoff_count", 0),
                            "window_refs": list(family.get("window_refs") or [])[:8],
                            "handoff_refs": list(family.get("handoff_refs") or [])[:8],
                        },
                    )
                )
            for index, contract in enumerate(memory_bus.get("typed_contracts") or [], start=1):
                contract_ref = str(contract.get("contract_ref") or "").strip()
                if not contract_ref:
                    continue
                events.append(
                    ExecutionEvent(
                        event_id=f"event-{run_id[:8]}-memory-contract-{index}",
                        case_id=case_id,
                        run_id=run_id,
                        stage="memory_bus",
                        event_kind="typed_card_contract",
                        status="indexed",
                        summary=(
                            f"记录 typed contract `{contract_ref}`，"
                            f"覆盖 {contract.get('card_count', 0)} 张 cards 与 {contract.get('handoff_count', 0)} 个 handoff。"
                        ),
                        created_at=created_at,
                        metadata={
                            "contract_ref": contract_ref,
                            "card_type": contract.get("card_type") or "",
                            "family": contract.get("family") or "",
                            "family_label": contract.get("family_label") or "",
                            "contract_version": contract.get("contract_version") or "",
                            "card_count": contract.get("card_count", 0),
                            "handoff_count": contract.get("handoff_count", 0),
                            "artifact_ref_count": contract.get("artifact_ref_count", 0),
                            "evidence_ref_count": contract.get("evidence_ref_count", 0),
                            "lookup_strategy": contract.get("lookup_strategy") or "",
                            "window_refs": list(contract.get("window_refs") or [])[:8],
                            "handoff_refs": list(contract.get("handoff_refs") or [])[:8],
                            "replay_index_refs": list(contract.get("replay_index_refs") or [])[:8],
                        },
                    )
                )
        events.extend(
            self._build_attack_loop_events(
                case_id=case_id,
                run_id=run_id,
                delivery=delivery,
                created_at=created_at,
            )
        )
        events.extend(
            self._build_dispatch_events(
                case_id=case_id,
                run_id=run_id,
                delivery=delivery,
                created_at=created_at,
            )
        )
        events.extend(
            self._build_projection_card_events(
                case_id=case_id,
                run_id=run_id,
                delivery=delivery,
                created_at=created_at,
            )
        )
        return events

    def _build_attack_loop_events(
        self,
        *,
        case_id: str,
        run_id: str,
        delivery: dict[str, Any],
        created_at: datetime,
    ) -> list[ExecutionEvent]:
        attack_loop = dict(delivery.get("attack_loop") or {})
        if not attack_loop:
            return []

        events: list[ExecutionEvent] = []
        index = 1
        baseline_target_service_ref = str(
            dict(attack_loop.get("target_service") or {}).get("service_id") or ""
        ).strip()
        regression_target_service_ref = str(
            dict(attack_loop.get("regression_target_service") or {}).get("service_id") or baseline_target_service_ref
        ).strip()

        decision_specs = [
            ("attack_executor", "baseline", dict(attack_loop.get("attack_decision") or {})),
            (
                "attack_executor",
                "regression",
                dict(attack_loop.get("regression_attack_decision") or {}),
            ),
        ]
        for stage, round_kind, decision in decision_specs:
            action = str(decision.get("action") or "").strip()
            if not action:
                continue
            family = str(decision.get("selected_attack_family") or "").strip()
            events.append(
                ExecutionEvent(
                    event_id=f"event-{run_id[:8]}-decision-{index}",
                    case_id=case_id,
                    run_id=run_id,
                    stage=stage,
                    event_kind="attack_decision",
                    status=action,
                    summary=str(
                        decision.get("rationale")
                        or decision.get("action_label")
                        or f"{round_kind} 攻击决策已生成。"
                    ),
                    created_at=created_at,
                    metadata={
                        "round_kind": round_kind,
                        "decision_id": decision.get("decision_id") or "",
                        "target_service_ref": decision.get("target_service_ref") or "",
                        "selected_attack_family": family,
                        "confidence": decision.get("confidence"),
                        "next_step": decision.get("next_step") or "",
                    },
                )
            )
            index += 1

        verdict_specs = [
            (
                "vulnerability_evaluation",
                "baseline",
                dict(attack_loop.get("vulnerability_verdict") or {}),
            ),
            (
                "vulnerability_evaluation",
                "regression",
                dict(attack_loop.get("regression_vulnerability_verdict") or {}),
            ),
        ]
        for stage, round_kind, verdict in verdict_specs:
            summary = str(verdict.get("summary") or "").strip()
            severity = str(verdict.get("severity") or "").strip()
            if not summary and not severity:
                continue
            target_service_ref = (
                regression_target_service_ref
                if round_kind == "regression"
                else baseline_target_service_ref
            )
            events.append(
                ExecutionEvent(
                    event_id=f"event-{run_id[:8]}-verdict-{index}",
                    case_id=case_id,
                    run_id=run_id,
                    stage=stage,
                    event_kind="vulnerability_verdict",
                    status=severity or "issued",
                    summary=summary or f"{round_kind} 漏洞裁决已生成。",
                    created_at=created_at,
                    metadata={
                        "round_kind": round_kind,
                        "verdict_id": verdict.get("verdict_id") or "",
                        "target_service_ref": target_service_ref,
                        "severity": severity,
                        "remediation_priority": verdict.get("remediation_priority") or "",
                        "exploitable": verdict.get("exploitable"),
                    },
                )
            )
            index += 1

        patch_spec = dict(attack_loop.get("patch_spec") or {})
        if patch_spec:
            events.append(
                ExecutionEvent(
                    event_id=f"event-{run_id[:8]}-patch-plan-{index}",
                    case_id=case_id,
                    run_id=run_id,
                    stage="patch",
                    event_kind="patch_plan",
                    status="planned",
                    summary=str(
                        patch_spec.get("summary")
                        or patch_spec.get("strategy")
                        or "补丁规划已生成。"
                    ),
                    created_at=created_at,
                    metadata={
                        "patch_id": patch_spec.get("patch_id") or "",
                        "target_service_ref": patch_spec.get("target_service_ref") or regression_target_service_ref or baseline_target_service_ref,
                        "strategy": patch_spec.get("strategy") or "",
                        "next_version": patch_spec.get("next_version") or "",
                        "regression_focus": patch_spec.get("regression_focus") or "",
                        "validation_step_count": len(patch_spec.get("validation_steps") or []),
                    },
                )
            )
            index += 1

        patch_execution = dict(attack_loop.get("patch_execution") or {})
        if patch_execution:
            validation_summary = dict(patch_execution.get("validation_summary") or {})
            events.append(
                ExecutionEvent(
                    event_id=f"event-{run_id[:8]}-patch-execution-{index}",
                    case_id=case_id,
                    run_id=run_id,
                    stage="patch_reflection",
                    event_kind="patch_execution",
                    status=str(patch_execution.get("status") or "reported"),
                    summary=str(
                        patch_execution.get("summary")
                        or "补丁执行与验证结果已沉淀。"
                    ),
                    created_at=created_at,
                    metadata={
                        "patch_id": patch_execution.get("patch_id") or "",
                        "target_service_ref": patch_execution.get("target_service_ref") or regression_target_service_ref or baseline_target_service_ref,
                        "workspace": patch_execution.get("workspace") or "",
                        "execution_contract_version": patch_execution.get("execution_contract_version") or "",
                        "patch_dispatch_id": patch_execution.get("patch_dispatch_id") or "",
                        "rollback_dispatch_id": patch_execution.get("rollback_dispatch_id") or "",
                        "deployment_dispatch_id": patch_execution.get("deployment_dispatch_id") or "",
                        "regression_dispatch_id": patch_execution.get("regression_dispatch_id") or "",
                        "artifact_refs": self._dedupe_refs(
                            [
                                *list(patch_execution.get("patch_artifact_refs") or []),
                                *list(patch_execution.get("rollback_artifact_refs") or []),
                                *list(patch_execution.get("regression_artifact_refs") or []),
                            ]
                        )[:24],
                        "patch_artifact_refs": list(patch_execution.get("patch_artifact_refs") or [])[:12],
                        "rollback_artifact_refs": list(patch_execution.get("rollback_artifact_refs") or [])[:12],
                        "regression_artifact_refs": list(
                            patch_execution.get("regression_artifact_refs") or []
                        )[:12],
                        "validation_passed": validation_summary.get("passed", 0),
                        "validation_failed": validation_summary.get("failed", 0),
                    },
                )
            )
            index += 1

        for card in list(attack_loop.get("reflection_cards") or [])[:3]:
            card_type = str(card.get("card_type") or "").strip()
            if not card_type:
                continue
            prompt_changes = list(card.get("prompt_changes") or [])
            audit_focus = list(card.get("audit_focus") or [])
            residual_risks = list(card.get("residual_risks") or [])
            summary = (
                str(card.get("summary") or "").strip()
                or str(card.get("reflection") or "").strip()
                or f"{card_type} 已生成。"
            )
            events.append(
                ExecutionEvent(
                    event_id=f"event-{run_id[:8]}-reflection-{index}",
                    case_id=case_id,
                    run_id=run_id,
                    stage="reflection",
                    event_kind="reflection_output",
                    status=card_type,
                    summary=summary,
                    created_at=created_at,
                    metadata={
                        "card_id": card.get("card_id") or "",
                        "card_type": card_type,
                        "prompt_change_count": len(prompt_changes),
                        "audit_focus_count": len(audit_focus),
                        "residual_risk_count": len(residual_risks),
                    },
                )
            )
            index += 1

        return events

    def _build_projection_card_events(
        self,
        *,
        case_id: str,
        run_id: str,
        delivery: dict[str, Any],
        created_at: datetime,
    ) -> list[ExecutionEvent]:
        projections = dict(delivery.get("context_projections") or {})
        events: list[ExecutionEvent] = []
        index = 1
        for stage, projection in projections.items():
            cards = list((projection or {}).get("cards") or [])
            for card in cards[:3]:
                family = str(card.get("card_family") or "").strip()
                contract_version = str(card.get("card_contract_version") or "").strip()
                if not family and not contract_version:
                    continue
                card_type = str(card.get("card_type") or "").strip()
                payload = dict(card.get("payload") or {})
                typed_contract = dict(payload.get("typed_contract") or {})
                ref_lookup_hint = dict(payload.get("ref_lookup_hint") or {})
                events.append(
                    ExecutionEvent(
                        event_id=f"event-{run_id[:8]}-card-{index}",
                        case_id=case_id,
                        run_id=run_id,
                        stage=str(stage or "projection"),
                        event_kind="memory_card_contract",
                        status="indexed",
                        summary=(
                            f"记录 `{card_type}` 卡片合同，"
                            f"family={family or 'generic'}，"
                            f"contract={str(typed_contract.get('contract_ref') or card.get('replay_index_ref') or '').strip()}。"
                        ),
                        created_at=created_at,
                        metadata={
                            "card_id": card.get("card_id") or "",
                            "card_type": card_type,
                            "card_family": family,
                            "card_family_label": card.get("card_family_label") or "",
                            "card_contract_version": contract_version,
                            "typed_contract_ref": typed_contract.get("contract_ref") or payload.get("typed_contract_ref") or "",
                            "lineage_ref": card.get("lineage_ref") or "",
                            "replay_index_ref": card.get("replay_index_ref") or "",
                            "lookup_strategy": ref_lookup_hint.get("lookup_strategy") or "",
                        },
                    )
                )
                index += 1
                if index > 12:
                    return events
        return events

    def _build_dispatch_events(
        self,
        *,
        case_id: str,
        run_id: str,
        delivery: dict[str, Any],
        created_at: datetime,
    ) -> list[ExecutionEvent]:
        dispatch_catalog = self._extract_dispatch_catalog(delivery)
        events: list[ExecutionEvent] = []
        for index, item in enumerate(dispatch_catalog, start=1):
            dispatch_id = str(item.get("dispatch_id") or "").strip()
            stage = str(item.get("stage") or "sandbox_dispatch").strip()
            status = str(item.get("status") or "").strip()
            artifact_refs = list(item.get("artifact_refs") or [])[:24]
            rejection_reasons = list(item.get("rejection_reasons") or [])[:8]
            event_kind = (
                "sandbox_dispatch_failure"
                if status in {"failed", "blocked"}
                else "sandbox_dispatch"
            )
            summary = str(item.get("summary") or "").strip()
            if not summary:
                summary = (
                    f"{stage} dispatch 未成功完成。"
                    if event_kind == "sandbox_dispatch_failure"
                    else f"{stage} dispatch 已记录。"
                )
            events.append(
                ExecutionEvent(
                    event_id=f"event-{run_id[:8]}-dispatch-{index}",
                    case_id=case_id,
                    run_id=run_id,
                    stage=stage,
                    event_kind=event_kind,
                    status=status,
                    summary=summary,
                    created_at=created_at,
                    metadata={
                        "dispatch_id": dispatch_id,
                        "operation_kind": item.get("operation_kind") or "",
                        "executor_kind": item.get("executor_kind") or "",
                        "executor_backend": item.get("executor_backend") or "",
                        "executor_label": item.get("executor_label") or "",
                        "target_service_ref": item.get("target_service_ref") or "",
                        "decision": item.get("decision") or "",
                        "failure_category": item.get("failure_category") or "",
                        "handoff_ref": item.get("handoff_ref") or "",
                        "artifact_refs": artifact_refs,
                        "rejection_reasons": rejection_reasons,
                    },
                )
            )
        return events

    def _build_version_lineage(
        self,
        delivery: dict[str, Any],
        *,
        run_id: str,
        created_at: datetime,
    ) -> VersionLineage | None:
        attack_loop = dict(delivery.get("attack_loop") or {})
        baseline = dict(attack_loop.get("target_service") or {})
        regression = dict(attack_loop.get("regression_target_service") or {})
        patch_spec = dict(attack_loop.get("patch_spec") or {})
        target_service_ref = str(regression.get("service_id") or baseline.get("service_id") or "").strip()
        if not target_service_ref:
            return None
        return VersionLineage(
            run_id=run_id,
            baseline_version=str(baseline.get("service_version") or ""),
            patched_version=str(regression.get("service_version") or patch_spec.get("next_version") or ""),
            patch_id=str(patch_spec.get("patch_id") or ""),
            target_service_ref=target_service_ref,
            created_at=created_at,
        )

    def _build_timeline_summary(self, timeline: CaseTimeline) -> dict[str, Any]:
        latest_snapshot = timeline.snapshots[-1] if timeline.snapshots else None
        return {
            "case_id": timeline.case_id,
            "latest_run_id": timeline.latest_run_id,
            "latest_status": timeline.latest_status,
            "snapshot_count": len(timeline.snapshots),
            "event_count": len(timeline.events),
            "version_lineage_count": len(timeline.version_lineage),
            "latest_projection_ref_count": len(latest_snapshot.projection_refs) if latest_snapshot else 0,
            "latest_handoff_ref_count": len(latest_snapshot.handoff_refs) if latest_snapshot else 0,
            "latest_dispatch_ref_count": len(latest_snapshot.dispatch_refs) if latest_snapshot else 0,
            "latest_failed_dispatch_ref_count": (
                len(latest_snapshot.failed_dispatch_refs) if latest_snapshot else 0
            ),
            "latest_dispatch_summary_count": len(latest_snapshot.dispatch_summaries) if latest_snapshot else 0,
            "latest_failed_dispatch_summary_count": (
                len(latest_snapshot.failed_dispatch_summaries) if latest_snapshot else 0
            ),
            "latest_executor_handoff_trace_count": (
                len(latest_snapshot.executor_handoff_trace_summaries) if latest_snapshot else 0
            ),
            "latest_typed_family_count": len((latest_snapshot.typed_family_counts or {})) if latest_snapshot else 0,
            "latest_typed_contract_count": len((latest_snapshot.typed_contract_counts or {})) if latest_snapshot else 0,
        }

    def _resolve_snapshot_run_scope(
        self,
        timeline: CaseTimeline,
        *,
        run_id: str | None = None,
        projection_ref: str | None = None,
        handoff_ref: str | None = None,
        artifact_lookup_ref: str | None = None,
        evidence_lookup_ref: str | None = None,
        retry_resume_checkpoint_ref: str | None = None,
        retry_resume_input_ref: str | None = None,
    ) -> set[str] | None:
        if (
            not run_id
            and not projection_ref
            and not handoff_ref
            and not artifact_lookup_ref
            and not evidence_lookup_ref
            and not retry_resume_checkpoint_ref
            and not retry_resume_input_ref
        ):
            return None

        matched_run_ids: set[str] = set()
        for snapshot in timeline.snapshots:
            if run_id and snapshot.run_id != run_id:
                continue
            if projection_ref and projection_ref not in set(snapshot.projection_refs or []):
                continue
            if handoff_ref and handoff_ref not in set(snapshot.handoff_refs or []):
                continue
            if artifact_lookup_ref and artifact_lookup_ref not in set(snapshot.artifact_lookup_refs or []):
                continue
            if evidence_lookup_ref and evidence_lookup_ref not in set(snapshot.evidence_lookup_refs or []):
                continue
            if retry_resume_checkpoint_ref and not self._snapshot_matches_retry_lookup(
                snapshot,
                lookup_ref=retry_resume_checkpoint_ref,
                metadata_key="retry_resume_checkpoint_refs",
            ):
                continue
            if retry_resume_input_ref and not self._snapshot_matches_retry_lookup(
                snapshot,
                lookup_ref=retry_resume_input_ref,
                metadata_key="retry_resume_input_refs",
            ):
                continue
            matched_run_ids.add(snapshot.run_id)
        return matched_run_ids

    def _query_lineage_for_run_ids(
        self,
        timeline: CaseTimeline,
        *,
        run_ids: list[str],
        limit: int,
    ) -> list[VersionLineage]:
        if not run_ids:
            return []
        allowed = set(run_ids)
        items: list[VersionLineage] = []
        for lineage in reversed(timeline.version_lineage):
            if lineage.run_id not in allowed:
                continue
            items.append(lineage)
            if len(items) >= max(limit, 1):
                break
        return items

    def _query_events_for_run_ids(
        self,
        timeline: CaseTimeline,
        *,
        run_ids: list[str],
        limit: int,
    ) -> list[ExecutionEvent]:
        if not run_ids:
            return []
        allowed = set(run_ids)
        items: list[ExecutionEvent] = []
        for event in reversed(timeline.events):
            if event.run_id not in allowed:
                continue
            items.append(event)
            if len(items) >= max(limit, 1):
                break
        return items

    def _build_relation_views(
        self,
        *,
        relation_kind: str,
        relation_refs: list[str],
        snapshots: list[ReplaySnapshot],
        events: list[ExecutionEvent],
        version_lineage: list[VersionLineage],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for relation_ref in relation_refs[:16]:
            matched_snapshots = [
                snapshot
                for snapshot in snapshots
                if self._snapshot_matches_relation(snapshot, relation_kind=relation_kind, relation_ref=relation_ref)
            ]
            matched_events = [
                event
                for event in events
                if self._event_matches_relation(event, relation_kind=relation_kind, relation_ref=relation_ref)
            ]
            matched_run_ids = {
                snapshot.run_id
                for snapshot in matched_snapshots
                if str(snapshot.run_id).strip()
            } | {
                event.run_id
                for event in matched_events
                if str(event.run_id).strip()
            }
            matched_lineage = [
                item
                for item in version_lineage
                if item.run_id in matched_run_ids
            ]
            matched_handoff_catalog = self._collect_handoff_catalog_entries(
                matched_snapshots=matched_snapshots,
                relation_kind=relation_kind,
                relation_ref=relation_ref,
            )
            source_agent_id, target_agent_id, handoff_projection_ref, dominant_typed_contract = (
                self._summarize_handoff_catalog(matched_handoff_catalog)
            )
            items.append(
                {
                    "relation_kind": relation_kind,
                    "relation_ref": relation_ref,
                    "source_agent_id": source_agent_id,
                    "target_agent_id": target_agent_id,
                    "upstream_stage": self._agent_to_stage_name(source_agent_id),
                    "downstream_stage": self._agent_to_stage_name(target_agent_id),
                    "handoff_projection_ref": handoff_projection_ref,
                    "dominant_typed_contract": dominant_typed_contract,
                    "agent_ids": self._collect_agent_ids_from_refs(
                        self._collect_relation_projection_refs(
                            relation_ref=relation_ref,
                            relation_kind=relation_kind,
                            matched_snapshots=matched_snapshots,
                            matched_events=matched_events,
                        )
                    ),
                    "linked_projection_refs": self._collect_relation_projection_refs(
                        relation_ref=relation_ref,
                        relation_kind=relation_kind,
                        matched_snapshots=matched_snapshots,
                        matched_events=matched_events,
                    ),
                    "linked_handoff_refs": self._collect_relation_handoff_refs(
                        relation_ref=relation_ref,
                        relation_kind=relation_kind,
                        matched_snapshots=matched_snapshots,
                        matched_events=matched_events,
                    ),
                    "typed_contract_refs": self._collect_relation_contract_refs(
                        matched_snapshots=matched_snapshots,
                        matched_events=matched_events,
                    ),
                    "artifact_lookup_refs": self._collect_relation_snapshot_lookup_refs(
                        matched_snapshots=matched_snapshots,
                        attr_name="artifact_lookup_refs",
                    ),
                    "evidence_lookup_refs": self._collect_relation_snapshot_lookup_refs(
                        matched_snapshots=matched_snapshots,
                        attr_name="evidence_lookup_refs",
                    ),
                    "target_service_refs": sorted(
                        {
                            item.target_service_ref
                            for item in matched_lineage
                            if str(item.target_service_ref).strip()
                        }
                    )[:16],
                    "stage_counts": self._count_event_field(matched_events, field_name="stage"),
                    "event_kind_counts": self._count_event_field(matched_events, field_name="event_kind"),
                    "snapshot_count": len(matched_snapshots),
                    "event_count": len(matched_events),
                    "version_lineage_count": len(matched_lineage),
                }
            )
        return items

    def _build_service_trajectories(
        self,
        *,
        events: list[ExecutionEvent],
        version_lineage: list[VersionLineage],
    ) -> list[dict[str, Any]]:
        target_service_refs = sorted(
            {
                str(item.target_service_ref).strip()
                for item in version_lineage
                if str(item.target_service_ref).strip()
            }
        )[:16]
        items: list[dict[str, Any]] = []
        for target_service_ref in target_service_refs:
            matched_lineage = [
                item
                for item in version_lineage
                if str(item.target_service_ref).strip() == target_service_ref
            ]
            matched_events = [
                item
                for item in events
                if str((item.metadata or {}).get("target_service_ref") or "").strip() == target_service_ref
            ]
            latest_event = matched_events[-1] if matched_events else None
            items.append(
                {
                    "target_service_ref": target_service_ref,
                    "run_ids": list(
                        dict.fromkeys(
                            [
                                item.run_id
                                for item in matched_lineage
                                if str(item.run_id).strip()
                            ]
                        )
                    )[:16],
                    "baseline_versions": sorted(
                        {
                            item.baseline_version
                            for item in matched_lineage
                            if str(item.baseline_version).strip()
                        }
                    )[:8],
                    "patched_versions": sorted(
                        {
                            item.patched_version
                            for item in matched_lineage
                            if str(item.patched_version).strip()
                        }
                    )[:8],
                    "patch_ids": sorted(
                        {
                            item.patch_id
                            for item in matched_lineage
                            if str(item.patch_id).strip()
                        }
                    )[:8],
                    "stages": sorted(
                        {
                            item.stage
                            for item in matched_events
                            if str(item.stage).strip()
                        }
                    )[:16],
                    "event_kind_counts": self._count_event_field(matched_events, field_name="event_kind"),
                    "latest_status": str(latest_event.status).strip() if latest_event is not None else "",
                    "latest_summary": str(latest_event.summary).strip() if latest_event is not None else "",
                }
            )
        return items

    def _snapshot_matches_relation(
        self,
        snapshot: ReplaySnapshot,
        *,
        relation_kind: str,
        relation_ref: str,
    ) -> bool:
        if relation_kind == "projection":
            return relation_ref in set(snapshot.projection_refs or [])
        if relation_kind == "handoff":
            return relation_ref in set(snapshot.handoff_refs or [])
        return False

    def _event_matches_relation(
        self,
        event: ExecutionEvent,
        *,
        relation_kind: str,
        relation_ref: str,
    ) -> bool:
        metadata_keys = ("window_refs", "projection_ref") if relation_kind == "projection" else ("handoff_refs", "handoff_id")
        return self._event_matches_lookup(
            event,
            lookup_ref=relation_ref,
            metadata_keys=metadata_keys,
        )

    def _collect_relation_projection_refs(
        self,
        *,
        relation_ref: str,
        relation_kind: str,
        matched_snapshots: list[ReplaySnapshot],
        matched_events: list[ExecutionEvent],
    ) -> list[str]:
        refs = {
            ref
            for snapshot in matched_snapshots
            for ref in snapshot.projection_refs
            if str(ref).strip()
        }
        if relation_kind == "projection" and relation_ref:
            refs.add(relation_ref)
        for event in matched_events:
            refs.update(self._collect_event_list_values(event.metadata or {}, ("window_refs",)))
            projection_value = str((event.metadata or {}).get("projection_ref") or "").strip()
            if projection_value:
                refs.add(projection_value)
        return sorted(refs)[:16]

    def _collect_relation_handoff_refs(
        self,
        *,
        relation_ref: str,
        relation_kind: str,
        matched_snapshots: list[ReplaySnapshot],
        matched_events: list[ExecutionEvent],
    ) -> list[str]:
        refs = {
            ref
            for snapshot in matched_snapshots
            for ref in snapshot.handoff_refs
            if str(ref).strip()
        }
        if relation_kind == "handoff" and relation_ref:
            refs.add(relation_ref)
        for event in matched_events:
            refs.update(self._collect_event_list_values(event.metadata or {}, ("handoff_refs",)))
            handoff_value = str((event.metadata or {}).get("handoff_id") or "").strip()
            if handoff_value:
                refs.add(handoff_value)
        return sorted(refs)[:16]

    def _collect_relation_contract_refs(
        self,
        *,
        matched_snapshots: list[ReplaySnapshot],
        matched_events: list[ExecutionEvent],
    ) -> list[str]:
        refs = {
            ref
            for snapshot in matched_snapshots
            for ref in (snapshot.typed_contract_counts or {}).keys()
            if str(ref).strip()
        }
        for event in matched_events:
            metadata = event.metadata or {}
            for key in ("contract_ref", "typed_contract_ref", "replay_index_ref"):
                value = str(metadata.get(key) or "").strip()
                if value:
                    refs.add(value)
        return sorted(refs)[:24]

    def _collect_relation_snapshot_lookup_refs(
        self,
        *,
        matched_snapshots: list[ReplaySnapshot],
        attr_name: str,
    ) -> list[str]:
        refs = {
            ref
            for snapshot in matched_snapshots
            for ref in list(getattr(snapshot, attr_name) or [])
            if str(ref).strip()
        }
        return sorted(refs)[:16]

    def _merge_dispatch_summaries(
        self,
        *,
        snapshots: list[ReplaySnapshot],
        failed_only: bool = False,
        limit: int = 16,
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen_dispatch_ids: set[str] = set()
        for snapshot in snapshots:
            source_items = (
                snapshot.failed_dispatch_summaries if failed_only else snapshot.dispatch_summaries
            )
            for item in source_items:
                dispatch_id = str(item.dispatch_id or "").strip()
                if not dispatch_id or dispatch_id in seen_dispatch_ids:
                    continue
                seen_dispatch_ids.add(dispatch_id)
                merged.append(item.model_dump(mode="json"))
                if len(merged) >= max(limit, 1):
                    return merged
        return merged

    def _merge_executor_handoff_trace_summaries(
        self,
        *,
        snapshots: list[ReplaySnapshot],
        limit: int = 16,
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for snapshot in snapshots:
            for item in snapshot.executor_handoff_trace_summaries:
                merge_key = "::".join(
                    [
                        str(item.dispatch_id or "").strip(),
                        str(item.handoff_ref or "").strip(),
                    ]
                )
                if not merge_key.strip(":") or merge_key in seen_keys:
                    continue
                seen_keys.add(merge_key)
                merged.append(item.model_dump(mode="json"))
                if len(merged) >= max(limit, 1):
                    return merged
        return merged

    def _count_event_field(self, events: list[ExecutionEvent], *, field_name: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in events:
            key = str(getattr(event, field_name, "") or "").strip()
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _collect_event_list_values(
        self,
        metadata: dict[str, Any],
        keys: tuple[str, ...],
    ) -> set[str]:
        values: set[str] = set()
        for key in keys:
            value = metadata.get(key)
            if isinstance(value, list):
                values.update(str(item).strip() for item in value if str(item).strip())
        return values

    def _collect_agent_ids_from_refs(self, projection_refs: list[str]) -> list[str]:
        agent_ids = {
            str(ref).split(":", maxsplit=1)[0].strip()
            for ref in projection_refs
            if ":" in str(ref)
        }
        return sorted(item for item in agent_ids if item)[:16]

    def _collect_handoff_catalog_entries(
        self,
        *,
        matched_snapshots: list[ReplaySnapshot],
        relation_kind: str,
        relation_ref: str,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for snapshot in matched_snapshots:
            for entry in list(snapshot.metadata.get("handoff_catalog") or [])[:16]:
                handoff_id = str((entry or {}).get("handoff_id") or "").strip()
                if relation_kind == "handoff" and handoff_id and handoff_id != relation_ref:
                    continue
                items.append(dict(entry or {}))
        return items

    def _summarize_handoff_catalog(
        self,
        items: list[dict[str, Any]],
    ) -> tuple[str, str, str, str]:
        if not items:
            return "", "", "", ""
        first = items[0]
        source_agent_id = str(first.get("from_agent") or "").strip()
        target_agent_id = str(first.get("to_agent") or "").strip()
        handoff_projection_ref = str(first.get("projection_ref") or "").strip()
        dominant_typed_contract = str(first.get("dominant_typed_contract") or "").strip()
        return source_agent_id, target_agent_id, handoff_projection_ref, dominant_typed_contract

    def _agent_to_stage_name(self, agent_id: str) -> str:
        text = str(agent_id or "").strip()
        if not text:
            return ""
        if text.endswith("_agent"):
            text = text[: -len("_agent")]
        return text

    def _prioritize_relation_ref(
        self,
        *,
        relation_refs: list[str],
        preferred_ref: str | None,
    ) -> list[str]:
        if not preferred_ref:
            return relation_refs
        preferred = str(preferred_ref).strip()
        if not preferred:
            return relation_refs
        ordered = [preferred]
        ordered.extend(item for item in relation_refs if item != preferred)
        return list(dict.fromkeys(ordered))

    def _dedupe_refs(self, refs: list[str]) -> list[str]:
        clean: list[str] = []
        seen: set[str] = set()
        for item in refs:
            ref = str(item or "").strip()
            if not ref or ref in seen:
                continue
            seen.add(ref)
            clean.append(ref)
        return clean

    def _extract_retry_snapshot_metadata(self, memory_bus_summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "retry_window_count": int(memory_bus_summary.get("retry_window_count", 0) or 0),
            "retry_handoff_count": int(memory_bus_summary.get("retry_handoff_count", 0) or 0),
            "retry_projection_refs": self._dedupe_refs(
                list(memory_bus_summary.get("retry_projection_refs") or [])
            )[:24],
            "retry_handoff_refs": self._dedupe_refs(
                list(memory_bus_summary.get("retry_handoff_refs") or [])
            )[:24],
            "retry_lineage_refs": self._dedupe_refs(
                list(memory_bus_summary.get("retry_lineage_refs") or [])
            )[:24],
            "retry_typed_contract_refs": self._dedupe_refs(
                list(memory_bus_summary.get("retry_typed_contract_refs") or [])
            )[:24],
            "retry_compression_stages": self._dedupe_refs(
                list(memory_bus_summary.get("retry_compression_stages") or [])
            )[:12],
            "retry_compression_policies": self._dedupe_refs(
                list(memory_bus_summary.get("retry_compression_policies") or [])
            )[:12],
            "retry_retained_refs": self._dedupe_refs(
                list(memory_bus_summary.get("retry_retained_refs") or [])
            )[:24],
            "retry_resume_checkpoint_refs": self._dedupe_refs(
                list(memory_bus_summary.get("retry_resume_checkpoint_refs") or [])
            )[:24],
            "retry_resume_input_refs": self._dedupe_refs(
                list(memory_bus_summary.get("retry_resume_input_refs") or [])
            )[:24],
        }

    def _merge_retry_snapshot_metadata(self, *, snapshots: list[ReplaySnapshot]) -> dict[str, Any]:
        retry_projection_refs: list[str] = []
        retry_handoff_refs: list[str] = []
        retry_lineage_refs: list[str] = []
        retry_typed_contract_refs: list[str] = []
        retry_compression_stages: list[str] = []
        retry_compression_policies: list[str] = []
        retry_retained_refs: list[str] = []
        retry_resume_checkpoint_refs: list[str] = []
        retry_resume_input_refs: list[str] = []
        retry_window_count = 0
        retry_handoff_count = 0

        for snapshot in snapshots:
            metadata = dict(snapshot.metadata or {})
            retry_window_count += int(metadata.get("retry_window_count", 0) or 0)
            retry_handoff_count += int(metadata.get("retry_handoff_count", 0) or 0)
            retry_projection_refs.extend(list(metadata.get("retry_projection_refs") or []))
            retry_handoff_refs.extend(list(metadata.get("retry_handoff_refs") or []))
            retry_lineage_refs.extend(list(metadata.get("retry_lineage_refs") or []))
            retry_typed_contract_refs.extend(list(metadata.get("retry_typed_contract_refs") or []))
            retry_compression_stages.extend(list(metadata.get("retry_compression_stages") or []))
            retry_compression_policies.extend(list(metadata.get("retry_compression_policies") or []))
            retry_retained_refs.extend(list(metadata.get("retry_retained_refs") or []))
            retry_resume_checkpoint_refs.extend(list(metadata.get("retry_resume_checkpoint_refs") or []))
            retry_resume_input_refs.extend(list(metadata.get("retry_resume_input_refs") or []))

        return {
            "retry_window_count": retry_window_count,
            "retry_handoff_count": retry_handoff_count,
            "retry_projection_refs": self._dedupe_refs(retry_projection_refs)[:24],
            "retry_handoff_refs": self._dedupe_refs(retry_handoff_refs)[:24],
            "retry_lineage_refs": self._dedupe_refs(retry_lineage_refs)[:24],
            "retry_typed_contract_refs": self._dedupe_refs(retry_typed_contract_refs)[:24],
            "retry_compression_stages": self._dedupe_refs(retry_compression_stages)[:12],
            "retry_compression_policies": self._dedupe_refs(retry_compression_policies)[:12],
            "retry_retained_refs": self._dedupe_refs(retry_retained_refs)[:24],
            "retry_resume_checkpoint_refs": self._dedupe_refs(retry_resume_checkpoint_refs)[:24],
            "retry_resume_input_refs": self._dedupe_refs(retry_resume_input_refs)[:24],
        }

    def _build_dispatch_summaries(
        self,
        dispatch_catalog: list[dict[str, Any]],
        *,
        failed_only: bool = False,
        limit: int = 16,
    ) -> list[ReplayDispatchSummary]:
        items: list[ReplayDispatchSummary] = []
        seen_dispatch_ids: set[str] = set()
        for entry in dispatch_catalog:
            status = str(entry.get("status") or "").strip()
            if failed_only and status not in {"failed", "blocked"}:
                continue
            dispatch_id = str(entry.get("dispatch_id") or "").strip()
            if not dispatch_id or dispatch_id in seen_dispatch_ids:
                continue
            seen_dispatch_ids.add(dispatch_id)
            items.append(
                ReplayDispatchSummary(
                    dispatch_key=str(entry.get("dispatch_key") or "").strip(),
                    dispatch_id=dispatch_id,
                    stage=str(entry.get("stage") or "").strip(),
                    operation_kind=str(entry.get("operation_kind") or "").strip(),
                    executor_kind=str(entry.get("executor_kind") or "").strip(),
                    executor_backend=str(entry.get("executor_backend") or "").strip(),
                    executor_label=str(entry.get("executor_label") or "").strip(),
                    target_service_ref=str(entry.get("target_service_ref") or "").strip(),
                    decision=str(entry.get("decision") or "").strip(),
                    status=status,
                    failure_category=str(entry.get("failure_category") or "").strip(),
                    handoff_ref=str(entry.get("handoff_ref") or "").strip(),
                    artifact_refs=self._dedupe_refs(list(entry.get("artifact_refs") or []))[:24],
                    rejection_reasons=self._dedupe_refs(list(entry.get("rejection_reasons") or []))[:8],
                    summary=str(entry.get("summary") or "").strip(),
                )
            )
            if len(items) >= max(limit, 1):
                break
        return items

    def _extract_dispatch_catalog(self, delivery: dict[str, Any]) -> list[dict[str, Any]]:
        sandbox_dispatcher = dict(delivery.get("sandbox_dispatcher") or {})
        entries: list[dict[str, Any]] = []
        for dispatch_key in (
            "baseline_deployment",
            "baseline_attack",
            "patch_apply",
            "regression_deployment",
            "regression_attack",
            "rollback_plan",
        ):
            item = dict(sandbox_dispatcher.get(dispatch_key) or {})
            dispatch_id = str(item.get("dispatch_id") or "").strip()
            if not dispatch_id:
                continue
            audit_trail = list(item.get("audit_trail") or [])
            latest_audit = dict(audit_trail[-1] or {}) if audit_trail else {}
            entries.append(
                {
                    "dispatch_key": dispatch_key,
                    "dispatch_id": dispatch_id,
                    "stage": str(item.get("stage") or dispatch_key).strip(),
                    "operation_kind": str(item.get("operation_kind") or "").strip(),
                    "executor_kind": str(item.get("executor_kind") or "").strip(),
                    "executor_backend": str(item.get("executor_backend") or "").strip(),
                    "executor_label": str(item.get("executor_label") or "").strip(),
                    "target_service_ref": str(item.get("target_service_ref") or "").strip(),
                    "decision": str(item.get("decision") or "").strip(),
                    "status": str(item.get("status") or "").strip(),
                    "failure_category": str(item.get("failure_category") or "").strip(),
                    "handoff_ref": str(item.get("handoff_ref") or "").strip(),
                    "artifact_refs": list(item.get("artifact_refs") or [])[:24],
                    "rejection_reasons": list(item.get("rejection_reasons") or [])[:8],
                    "summary": str(latest_audit.get("summary") or "").strip(),
                }
            )
        return entries

    def _build_executor_handoff_trace_summaries(
        self,
        delivery: dict[str, Any],
        *,
        limit: int = 16,
    ) -> list[ReplayExecutorHandoffTraceSummary]:
        sandbox_dispatcher = dict(delivery.get("sandbox_dispatcher") or {})
        items: list[ReplayExecutorHandoffTraceSummary] = []
        for dispatch_key in (
            "baseline_deployment",
            "baseline_attack",
            "patch_apply",
            "regression_deployment",
            "regression_attack",
            "rollback_plan",
        ):
            dispatch_item = dict(sandbox_dispatcher.get(dispatch_key) or {})
            trace = dict(dispatch_item.get("handoff_trace") or {})
            if not trace:
                continue
            receipt = dict(dispatch_item.get("handoff_receipt") or {})
            artifact_sync_manifest = dict(dispatch_item.get("artifact_sync_manifest") or {})
            items.append(
                ReplayExecutorHandoffTraceSummary(
                    dispatch_key=dispatch_key,
                    dispatch_id=str(dispatch_item.get("dispatch_id") or "").strip(),
                    handoff_ref=str(trace.get("handoff_ref") or dispatch_item.get("handoff_ref") or "").strip(),
                    stage=str(dispatch_item.get("stage") or "").strip(),
                    operation_kind=str(dispatch_item.get("operation_kind") or "").strip(),
                    executor_kind=str(trace.get("executor_kind") or dispatch_item.get("executor_kind") or "").strip(),
                    executor_backend=str(
                        trace.get("executor_backend") or dispatch_item.get("executor_backend") or ""
                    ).strip(),
                    governance_mode=str(dispatch_item.get("governance_mode") or "").strip(),
                    routing_mode=str(trace.get("routing_mode") or dispatch_item.get("routing_mode") or "").strip(),
                    adapter_stage=str(trace.get("adapter_stage") or "").strip(),
                    trace_status=str(trace.get("trace_status") or "").strip(),
                    receipt_ref=str(trace.get("receipt_ref") or "").strip(),
                    receipt_status=str(receipt.get("receipt_status") or "").strip(),
                    accepted=bool(receipt.get("accepted", False)),
                    remote_job_ref=str(receipt.get("remote_job_ref") or "").strip(),
                    artifact_sync_ref=str(
                        trace.get("artifact_sync_ref")
                        or artifact_sync_manifest.get("sync_id")
                        or ""
                    ).strip(),
                    artifact_sync_status=str(artifact_sync_manifest.get("sync_status") or "").strip(),
                    target_service_ref=str(dispatch_item.get("target_service_ref") or "").strip(),
                    artifact_refs=self._dedupe_refs(list(dispatch_item.get("artifact_refs") or []))[:24],
                    failure_category=str(trace.get("failure_category") or "").strip(),
                    summary=str(trace.get("summary") or "").strip(),
                )
            )
            if len(items) >= max(limit, 1):
                break
        return items

    def _extract_patch_execution_artifact_refs(self, delivery: dict[str, Any]) -> list[str]:
        attack_loop = dict(delivery.get("attack_loop") or {})
        patch_execution = dict(attack_loop.get("patch_execution") or {})
        return self._dedupe_refs(
            [
                *list(patch_execution.get("patch_artifact_refs") or []),
                *list(patch_execution.get("rollback_artifact_refs") or []),
                *list(patch_execution.get("regression_artifact_refs") or []),
            ]
        )

    def _extract_dispatch_artifact_refs(self, dispatch_catalog: list[dict[str, Any]]) -> list[str]:
        refs: list[str] = []
        for item in dispatch_catalog:
            refs.extend(list(item.get("artifact_refs") or []))
        return self._dedupe_refs(refs)

    def _extract_window_catalog(self, memory_bus: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for entry in list(memory_bus.get("windows") or [])[:8]:
            item = dict(entry or {})
            items.append(
                {
                    "agent_id": str(item.get("agent_id") or "").strip(),
                    "window_ref": str(item.get("window_ref") or "").strip(),
                    "dominant_card_family": str(item.get("dominant_card_family") or "").strip(),
                    "dominant_typed_contract": str(item.get("dominant_typed_contract") or "").strip(),
                    "artifact_lookup_refs": list(item.get("artifact_lookup_refs") or [])[:8],
                    "evidence_lookup_refs": list(item.get("evidence_lookup_refs") or [])[:8],
                }
            )
        return items

    def _extract_handoff_catalog(self, memory_bus: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for entry in list(memory_bus.get("handoffs") or [])[:8]:
            item = dict(entry or {})
            items.append(
                {
                    "handoff_id": str(item.get("handoff_id") or "").strip(),
                    "from_agent": str(item.get("from_agent") or "").strip(),
                    "to_agent": str(item.get("to_agent") or "").strip(),
                    "projection_ref": str(item.get("projection_ref") or "").strip(),
                    "dominant_card_family": str(item.get("dominant_card_family") or "").strip(),
                    "dominant_typed_contract": str(item.get("dominant_typed_contract") or "").strip(),
                    "artifact_lookup_refs": list(item.get("artifact_lookup_refs") or [])[:8],
                    "evidence_lookup_refs": list(item.get("evidence_lookup_refs") or [])[:8],
                }
            )
        return items

    def _snapshot_matches_contract(self, snapshot: ReplaySnapshot, contract_ref: str) -> bool:
        return contract_ref in set(snapshot.typed_contract_counts or {}) or (
            str(snapshot.metadata.get("dominant_memory_contract") or "").strip() == contract_ref
        )

    def _event_matches_contract(self, event: ExecutionEvent, contract_ref: str) -> bool:
        metadata = event.metadata or {}
        candidate_values = [
            metadata.get("contract_ref"),
            metadata.get("typed_contract_ref"),
            metadata.get("replay_index_ref"),
        ]
        return any(str(value or "").strip() == contract_ref for value in candidate_values)

    def _event_matches_lineage(self, event: ExecutionEvent, lineage_ref: str) -> bool:
        metadata = event.metadata or {}
        direct_values = [
            metadata.get("lineage_ref"),
        ]
        if any(str(value or "").strip() == lineage_ref for value in direct_values):
            return True
        for value in metadata.values():
            if isinstance(value, list) and lineage_ref in {str(item).strip() for item in value}:
                return True
        return False

    def _event_matches_lookup(
        self,
        event: ExecutionEvent,
        *,
        lookup_ref: str,
        metadata_keys: tuple[str, ...],
    ) -> bool:
        metadata = event.metadata or {}
        lookup_parts = [part for part in str(lookup_ref).split(":", maxsplit=1) if part]
        for key in metadata_keys:
            value = metadata.get(key)
            if isinstance(value, list) and lookup_ref in {str(item).strip() for item in value}:
                return True
            if str(value or "").strip() == lookup_ref:
                return True
        if len(lookup_parts) == 2:
            doc_id, chunk_id = lookup_parts
            if (
                str(metadata.get("doc_id") or "").strip() == doc_id
                and str(metadata.get("chunk_id") or "").strip() == chunk_id
            ):
                return True
        return False

    def _snapshot_matches_retry_lookup(
        self,
        snapshot: ReplaySnapshot,
        *,
        lookup_ref: str,
        metadata_key: str,
    ) -> bool:
        return lookup_ref in {
            str(item).strip()
            for item in list((snapshot.metadata or {}).get(metadata_key) or [])
            if str(item).strip()
        }

    def _event_is_scoped_to_runs(
        self,
        event: ExecutionEvent,
        allowed_run_ids: set[str] | None,
    ) -> bool:
        return allowed_run_ids is not None and event.run_id in allowed_run_ids

    def _save(self, timeline: CaseTimeline) -> None:
        path = self._path_for(timeline.case_id)
        temp_path = path.with_suffix(".tmp")
        payload = timeline.model_dump(mode="json")
        with self._lock:
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            temp_path.replace(path)

    def _path_for(self, case_id: str) -> Path:
        safe_case_id = "".join(ch for ch in case_id if ch.isalnum() or ch in {"-", "_"})
        if not safe_case_id:
            raise ValueError("Invalid case_id")
        return self.storage_dir / f"{safe_case_id}.json"
