import { useEffect, useMemo, useState } from "react";
import { MetricCard, Panel } from "../../components/Panel";
import { SemanticPill, TagPill } from "../../components/SemanticPill";
import { PillButton, ReplayFocusButton, ReplayFocusPill } from "./ReplayFocusPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function summarizeText(value = "", maxLength = 140) {
  const text = String(value || "").trim();
  if (!text) return "当前暂无可展示摘要。";
  return text.length <= maxLength ? text : `${text.slice(0, maxLength)}...`;
}

function renderCountMap(map = {}, limit = 5) {
  const entries = Object.entries(map || {})
    .filter(([, value]) => Number(value) > 0)
    .sort((a, b) => Number(b[1]) - Number(a[1]));
  return entries.slice(0, limit);
}

function uniqueStrings(items = []) {
  return [...new Set((items || []).map((item) => String(item || "").trim()).filter(Boolean))];
}

function metadataEntries(metadata = {}) {
  return Object.entries(metadata || {}).filter(([, value]) => {
    if (value === null || value === undefined) return false;
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === "object") return Object.keys(value).length > 0;
    return String(value).trim() !== "";
  });
}

function pickRetryRecoverySummary(source = {}) {
  const data = source || {};
  return {
    retryWindowCount: Number(data?.retry_window_count || 0),
    retryHandoffCount: Number(data?.retry_handoff_count || 0),
    retryProjectionRefs: uniqueStrings(data?.retry_projection_refs || []),
    retryHandoffRefs: uniqueStrings(data?.retry_handoff_refs || []),
    retryLineageRefs: uniqueStrings(data?.retry_lineage_refs || []),
    retryTypedContractRefs: uniqueStrings(data?.retry_typed_contract_refs || []),
    retryCompressionStages: uniqueStrings(data?.retry_compression_stages || []),
    retryCompressionPolicies: uniqueStrings(data?.retry_compression_policies || []),
    retryRetainedRefs: uniqueStrings(data?.retry_retained_refs || []),
    retryResumeCheckpointRefs: uniqueStrings(data?.retry_resume_checkpoint_refs || []),
    retryResumeInputRefs: uniqueStrings(data?.retry_resume_input_refs || []),
  };
}

function hasRetryRecoveryData(summary = {}) {
  return (
    Number(summary?.retryWindowCount || 0) > 0 ||
    Number(summary?.retryHandoffCount || 0) > 0 ||
    (summary?.retryProjectionRefs || []).length > 0 ||
    (summary?.retryCompressionPolicies || []).length > 0 ||
    (summary?.retryResumeCheckpointRefs || []).length > 0 ||
    (summary?.retryResumeInputRefs || []).length > 0
  );
}

function normalizeRefList(...values) {
  return uniqueStrings(
    values.flatMap((value) => {
      if (Array.isArray(value)) return value;
      const normalized = String(value || "").trim();
      return normalized ? [normalized] : [];
    })
  );
}

function extractArtifactRefs(record = {}) {
  return normalizeRefList(
    record?.artifact_lookup_refs,
    record?.metadata?.artifact_lookup_refs,
    record?.metadata?.artifact_lookup_ref
  );
}

function extractEvidenceRefs(record = {}) {
  return normalizeRefList(
    record?.evidence_lookup_refs,
    record?.metadata?.evidence_lookup_refs,
    record?.metadata?.evidence_lookup_ref
  );
}

function extractTargetServiceRefs(record = {}) {
  return normalizeRefList(
    record?.target_service_refs,
    record?.metadata?.target_service_refs,
    record?.metadata?.target_service_ref
  );
}

function snapshotTouchesStage(snapshot = {}, stage = "") {
  const normalizedStage = String(stage || "").trim();
  if (!normalizedStage) return true;
  const workflowTrace = normalizeRefList(snapshot?.workflow_trace);
  const metadataStage = String(snapshot?.metadata?.stage || "").trim();
  return workflowTrace.includes(normalizedStage) || metadataStage === normalizedStage;
}

function LocalFilterPill({ active = false, tone = "neutral", children, onClick }) {
  const toneStyles = {
    ok: active
      ? "border-emerald-500 bg-emerald-600 text-white shadow-sm"
      : "border-emerald-300 bg-emerald-100 text-emerald-700 hover:bg-emerald-200",
    warn: active
      ? "border-amber-500 bg-amber-500 text-white shadow-sm"
      : "border-amber-300 bg-amber-100 text-amber-700 hover:bg-amber-200",
    bad: active
      ? "border-rose-500 bg-rose-500 text-white shadow-sm"
      : "border-rose-300 bg-rose-100 text-rose-700 hover:bg-rose-200",
    neutral: active
      ? "border-slate-500 bg-slate-700 text-white shadow-sm"
      : "border-slate-300 bg-slate-100 text-slate-700 hover:bg-slate-200",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs font-bold transition-colors",
        "focus:outline-none focus:ring-2 focus:ring-sky-300",
        toneStyles[tone] || toneStyles.neutral
      )}
    >
      {children}
    </button>
  );
}

function formatTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("zh-CN", { hour12: false });
}

function sumCountMap(map = {}) {
  return Object.values(map || {}).reduce((sum, value) => sum + Number(value || 0), 0);
}

function buildLineageKey(item = {}, index = 0) {
  return [
    item?.patch_id || "",
    item?.baseline_version || "",
    item?.patched_version || "",
    item?.run_id || "",
    item?.created_at || "",
    index,
  ].join("::");
}

function countActiveScopeFields(scope = {}) {
  return Object.values(scope || {}).filter((value) => String(value || "").trim()).length;
}

function formatRefreshTime(value) {
  if (!value) return "尚未刷新";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

function historyTone(status = "") {
  const normalized = String(status || "").trim().toLowerCase();
  if (normalized === "success") return "ok";
  if (normalized === "error") return "bad";
  return "neutral";
}

function historyStatusLabel(status = "") {
  const normalized = String(status || "").trim().toLowerCase();
  if (normalized === "success") return "成功";
  if (normalized === "error") return "失败";
  return "未知";
}

function getScopeFieldLabel(key = "") {
  const labels = {
    run_id: "运行",
    event_kind: "事件类型",
    stage: "阶段",
    contract_ref: "Contract",
    lineage_ref: "Lineage",
    projection_ref: "Projection",
    handoff_ref: "Handoff",
    artifact_lookup_ref: "工件",
    evidence_lookup_ref: "证据",
    retry_resume_checkpoint_ref: "恢复点",
    retry_resume_input_ref: "Resume 输入",
    limit: "限制条数",
  };
  return labels[key] || key;
}

export default function ReplayTimelinePanel({
  currentCaseId,
  timelineOverview,
  replayDrilldown,
  replayEventsResponse,
  replaySnapshotsResponse,
  replayScope,
  setReplayScope,
  selectedProposalId,
  proposalReplayContext,
  replayLineage,
  loading,
  error,
  replayEventsLoading,
  replayEventsError,
  replaySnapshotsLoading,
  replaySnapshotsError,
  listLoading,
  listError,
  replaySourceUpdatedAt,
  replaySourceParams,
  replaySourceHistory,
  refreshReplaySource,
  lineageLoading,
  lineageError,
}) {
  const summary = replayDrilldown?.summary || {};
  const drilldownScope = replayDrilldown?.scope || {};
  const snapshotScope = replaySnapshotsResponse?.scope || {};
  const eventScope = replayEventsResponse?.scope || {};
  const scope =
    countActiveScopeFields(drilldownScope) > 0
      ? drilldownScope
      : countActiveScopeFields(snapshotScope) > 0
        ? snapshotScope
        : countActiveScopeFields(eventScope) > 0
          ? eventScope
          : {};
  const handoffRelationships = replayDrilldown?.handoff_relationships || [];
  const projectionRelationships = replayDrilldown?.projection_relationships || [];
  const serviceTrajectories = replayDrilldown?.service_trajectories || [];
  const replayEvents = replayEventsResponse?.items || replayDrilldown?.events || [];
  const replaySnapshots = replaySnapshotsResponse?.items || replayDrilldown?.snapshots || [];
  const drilldownReady = Boolean(replayDrilldown);
  const eventListReady = Boolean(replayEventsResponse);
  const snapshotListReady = Boolean(replaySnapshotsResponse);
  const hasFallbackReplayLists = Boolean((error || listError) && (eventListReady || snapshotListReady));
  const latestSnapshot = timelineOverview?.latest_snapshot || {};
  const latestLineage = timelineOverview?.latest_version_lineage || {};
  const latestSnapshotRetrySummary = useMemo(
    () => pickRetryRecoverySummary(latestSnapshot?.metadata || {}),
    [latestSnapshot]
  );
  const drilldownRetrySummary = useMemo(() => pickRetryRecoverySummary(summary), [summary]);
  const activeRetrySummary = hasRetryRecoveryData(drilldownRetrySummary)
    ? drilldownRetrySummary
    : latestSnapshotRetrySummary;
  const activeRetrySourceLabel = hasRetryRecoveryData(drilldownRetrySummary) ? "当前 drilldown" : "最近快照";
  const matchedRunIds = uniqueStrings(summary?.matched_run_ids || []);
  const targetServiceRefs = uniqueStrings(summary?.target_service_refs || []);
  const lineageItems = replayLineage?.items || [];
  const [selectedEventId, setSelectedEventId] = useState("");
  const [selectedSnapshotId, setSelectedSnapshotId] = useState("");
  const [selectedLineageKey, setSelectedLineageKey] = useState("");
  const [selectedDataSource, setSelectedDataSource] = useState("drilldown");
  const selectedRunId = String(replayScope?.runId || "").trim();
  const selectedStage = String(replayScope?.stageRef || "").trim();
  const selectedArtifactRef = String(replayScope?.artifactLookupRef || "").trim();
  const selectedEvidenceRef = String(replayScope?.evidenceLookupRef || "").trim();
  const selectedRetryResumeCheckpointRef = String(replayScope?.retryResumeCheckpointRef || "").trim();
  const selectedRetryResumeInputRef = String(replayScope?.retryResumeInputRef || "").trim();
  const hasLocalOnlyFilters = Boolean(
    String(replayScope?.runId || "").trim() ||
      String(replayScope?.stageRef || "").trim() ||
      String(replayScope?.targetServiceRef || "").trim()
  );
  const hasQueryBackedReplayFocus = Boolean(
    String(replayScope?.projectionRef || "").trim() ||
      String(replayScope?.handoffRef || "").trim() ||
      String(replayScope?.artifactLookupRef || "").trim() ||
      String(replayScope?.evidenceLookupRef || "").trim() ||
      String(replayScope?.retryResumeCheckpointRef || "").trim() ||
      String(replayScope?.retryResumeInputRef || "").trim()
  );
  const proposalRunIds = uniqueStrings(proposalReplayContext?.runIds || []);
  const proposalStageRefs = uniqueStrings(proposalReplayContext?.stageRefs || []);
  const proposalArtifactRefs = uniqueStrings(proposalReplayContext?.artifactRefs || []);
  const proposalHandoffRefs = uniqueStrings(proposalReplayContext?.handoffRefs || []);
  const proposalTargetServiceRefs = uniqueStrings(proposalReplayContext?.targetServiceRefs || []);
  const replayDataSources = useMemo(
    () => [
      {
        id: "drilldown",
        label: "关系聚合",
        ready: drilldownReady,
        loading: loading,
        error: error,
        tone: drilldownReady ? "ok" : loading ? "warn" : error ? "bad" : "neutral",
        scope: drilldownScope,
        updatedAt: replaySourceUpdatedAt?.drilldown || "",
        requestParams: replaySourceParams?.drilldown || {},
        history: replaySourceHistory?.drilldown || [],
        countLabel: `事件 ${summary?.event_count ?? replayEvents.length} / 快照 ${summary?.snapshot_count ?? replaySnapshots.length}`,
        detail:
          summary?.matched_run_ids?.length > 0
            ? `匹配运行 ${summary.matched_run_ids.length} 个`
            : "用于关系、服务轨迹与聚合摘要",
      },
      {
        id: "events",
        label: "事件列表",
        ready: eventListReady,
        loading: replayEventsLoading,
        error: replayEventsError,
        tone: eventListReady ? "ok" : replayEventsLoading ? "warn" : replayEventsError ? "bad" : "neutral",
        scope: eventScope,
        updatedAt: replaySourceUpdatedAt?.events || "",
        requestParams: replaySourceParams?.events || {},
        history: replaySourceHistory?.events || [],
        countLabel: `共 ${replayEventsResponse?.total ?? replayEvents.length} 条`,
        detail: "用于事件流回看与局部筛选",
      },
      {
        id: "snapshots",
        label: "快照列表",
        ready: snapshotListReady,
        loading: replaySnapshotsLoading,
        error: replaySnapshotsError,
        tone: snapshotListReady ? "ok" : replaySnapshotsLoading ? "warn" : replaySnapshotsError ? "bad" : "neutral",
        scope: snapshotScope,
        updatedAt: replaySourceUpdatedAt?.snapshots || "",
        requestParams: replaySourceParams?.snapshots || {},
        history: replaySourceHistory?.snapshots || [],
        countLabel: `共 ${replaySnapshotsResponse?.total ?? replaySnapshots.length} 条`,
        detail: "用于快照摘要与状态回看",
      },
    ],
    [
      drilldownReady,
      loading,
      error,
      drilldownScope,
      summary,
      replayEvents.length,
      replaySnapshots.length,
      eventListReady,
      replayEventsLoading,
      replayEventsError,
      eventScope,
      replaySourceParams?.events,
      replaySourceHistory?.events,
      replaySourceUpdatedAt?.events,
      replayEventsResponse?.total,
      snapshotListReady,
      replaySnapshotsLoading,
      replaySnapshotsError,
      snapshotScope,
      replaySourceParams?.snapshots,
      replaySourceHistory?.snapshots,
      replaySourceUpdatedAt?.snapshots,
      replaySnapshotsResponse?.total,
      replaySourceParams?.drilldown,
      replaySourceHistory?.drilldown,
      replaySourceUpdatedAt?.drilldown,
    ]
  );
  const activeDataSource =
    replayDataSources.find((item) => item.id === selectedDataSource) || replayDataSources[0];

  const runTopology = useMemo(() => {
    const runMap = new Map();
    const ensureRun = (runId) => {
      const normalizedRunId = String(runId || "").trim() || "--";
      const current = runMap.get(normalizedRunId) || {
        runId: normalizedRunId,
        eventCount: 0,
        snapshotCount: 0,
        stageSet: new Set(),
        eventKinds: {},
        targetServiceRefs: new Set(),
        artifactRefs: new Set(),
        evidenceRefs: new Set(),
        statuses: new Set(),
        latestSummary: "",
        latestCreatedAt: "",
      };
      runMap.set(normalizedRunId, current);
      return current;
    };

    matchedRunIds.forEach((runId) => ensureRun(runId));

    replayEvents.forEach((item) => {
      const current = ensureRun(item?.run_id);
      current.eventCount += 1;
      if (item?.stage) current.stageSet.add(String(item.stage));
      if (item?.event_kind) {
        current.eventKinds[item.event_kind] = Number(current.eventKinds[item.event_kind] || 0) + 1;
      }
      extractTargetServiceRefs(item).forEach((ref) => current.targetServiceRefs.add(ref));
      extractArtifactRefs(item).forEach((ref) => current.artifactRefs.add(ref));
      extractEvidenceRefs(item).forEach((ref) => current.evidenceRefs.add(ref));
      if (item?.status) current.statuses.add(String(item.status));
      if (item?.created_at && String(item.created_at) >= String(current.latestCreatedAt || "")) {
        current.latestCreatedAt = String(item.created_at);
        current.latestSummary = String(item?.summary || "").trim();
      }
    });

    replaySnapshots.forEach((item) => {
      const current = ensureRun(item?.run_id);
      current.snapshotCount += 1;
      normalizeRefList(item?.workflow_trace, item?.metadata?.stage).forEach((stage) => current.stageSet.add(stage));
      extractArtifactRefs(item).forEach((ref) => current.artifactRefs.add(ref));
      extractEvidenceRefs(item).forEach((ref) => current.evidenceRefs.add(ref));
      if (item?.status) current.statuses.add(String(item.status));
      if (item?.created_at && String(item.created_at) >= String(current.latestCreatedAt || "")) {
        current.latestCreatedAt = String(item.created_at);
        current.latestSummary = String(item?.summary || "").trim();
      }
    });

    return Array.from(runMap.values())
      .map((item) => ({
        runId: item.runId,
        eventCount: item.eventCount,
        snapshotCount: item.snapshotCount,
        stageRefs: uniqueStrings([...item.stageSet]),
        eventKinds: item.eventKinds,
        targetServiceRefs: uniqueStrings([...item.targetServiceRefs]),
        artifactRefs: uniqueStrings([...item.artifactRefs]),
        evidenceRefs: uniqueStrings([...item.evidenceRefs]),
        statuses: uniqueStrings([...item.statuses]),
        latestSummary: item.latestSummary,
        latestCreatedAt: item.latestCreatedAt,
      }))
      .sort((a, b) => {
        if (a.runId === scope?.run_id) return -1;
        if (b.runId === scope?.run_id) return 1;
        return b.eventCount - a.eventCount || b.snapshotCount - a.snapshotCount;
      });
  }, [matchedRunIds, replayEvents, replaySnapshots, scope?.run_id]);

  const stageTopology = useMemo(() => {
    const stageMap = new Map();
    const filteredEvents = replayEvents.filter((item) => {
      const runMatch = !selectedRunId || String(item?.run_id || "").trim() === selectedRunId;
      const evidenceMatch = !selectedEvidenceRef || extractEvidenceRefs(item).includes(selectedEvidenceRef);
      return runMatch && evidenceMatch;
    });
    const filteredSnapshots = replaySnapshots.filter((item) => {
      const runMatch = !selectedRunId || String(item?.run_id || "").trim() === selectedRunId;
      const evidenceMatch = !selectedEvidenceRef || extractEvidenceRefs(item).includes(selectedEvidenceRef);
      return runMatch && evidenceMatch;
    });

    filteredEvents.forEach((item) => {
      const stage = String(item?.stage || "--").trim() || "--";
      const current = stageMap.get(stage) || {
        stage,
        eventCount: 0,
        snapshotCount: 0,
        runIds: new Set(),
        eventKinds: {},
        targetServiceRefs: new Set(),
        artifactRefs: new Set(),
        evidenceRefs: new Set(),
      };
      current.eventCount += 1;
      current.runIds.add(String(item?.run_id || "").trim() || "--");
      if (item?.event_kind) {
        current.eventKinds[item.event_kind] = Number(current.eventKinds[item.event_kind] || 0) + 1;
      }
      extractTargetServiceRefs(item).forEach((ref) => current.targetServiceRefs.add(ref));
      extractArtifactRefs(item).forEach((ref) => current.artifactRefs.add(ref));
      extractEvidenceRefs(item).forEach((ref) => current.evidenceRefs.add(ref));
      stageMap.set(stage, current);
    });

    filteredSnapshots.forEach((item) => {
      const stageRefs = normalizeRefList(item?.workflow_trace, item?.metadata?.stage);
      stageRefs.forEach((stage) => {
        const current = stageMap.get(stage) || {
          stage,
          eventCount: 0,
          snapshotCount: 0,
          runIds: new Set(),
          eventKinds: {},
          targetServiceRefs: new Set(),
          artifactRefs: new Set(),
          evidenceRefs: new Set(),
        };
        current.snapshotCount += 1;
        current.runIds.add(String(item?.run_id || "").trim() || "--");
        extractArtifactRefs(item).forEach((ref) => current.artifactRefs.add(ref));
        extractEvidenceRefs(item).forEach((ref) => current.evidenceRefs.add(ref));
        stageMap.set(stage, current);
      });
    });

    return Array.from(stageMap.values())
      .map((item) => ({
        stage: item.stage,
        eventCount: item.eventCount,
        snapshotCount: item.snapshotCount,
        runIds: uniqueStrings([...item.runIds]),
        eventKinds: item.eventKinds,
        targetServiceRefs: uniqueStrings([...item.targetServiceRefs]),
        artifactRefs: uniqueStrings([...item.artifactRefs]),
        evidenceRefs: uniqueStrings([...item.evidenceRefs]),
      }))
      .sort((a, b) => b.eventCount - a.eventCount || b.snapshotCount - a.snapshotCount);
  }, [replayEvents, replaySnapshots, selectedRunId, selectedEvidenceRef]);

  const artifactTopology = useMemo(() => {
    const artifactMap = new Map();
    const filteredEvents = replayEvents.filter((item) => {
      const runMatch = !selectedRunId || String(item?.run_id || "").trim() === selectedRunId;
      const stageMatch = !selectedStage || String(item?.stage || "").trim() === selectedStage;
      const evidenceMatch = !selectedEvidenceRef || extractEvidenceRefs(item).includes(selectedEvidenceRef);
      return runMatch && stageMatch && evidenceMatch;
    });
    const filteredSnapshots = replaySnapshots.filter((item) => {
      const runMatch = !selectedRunId || String(item?.run_id || "").trim() === selectedRunId;
      const stageMatch = !selectedStage || snapshotTouchesStage(item, selectedStage);
      const evidenceMatch = !selectedEvidenceRef || extractEvidenceRefs(item).includes(selectedEvidenceRef);
      return runMatch && stageMatch && evidenceMatch;
    });

    const ensureArtifact = (artifactRef) => {
      const normalizedArtifactRef = String(artifactRef || "").trim();
      if (!normalizedArtifactRef) return null;
      const current = artifactMap.get(normalizedArtifactRef) || {
        artifactRef: normalizedArtifactRef,
        eventCount: 0,
        snapshotCount: 0,
        runIds: new Set(),
        stages: new Set(),
        evidenceRefs: new Set(),
      };
      artifactMap.set(normalizedArtifactRef, current);
      return current;
    };

    filteredEvents.forEach((item) => {
      extractArtifactRefs(item).forEach((artifactRef) => {
        const current = ensureArtifact(artifactRef);
        if (!current) return;
        current.eventCount += 1;
        current.runIds.add(String(item?.run_id || "").trim() || "--");
        if (item?.stage) current.stages.add(String(item.stage));
        extractEvidenceRefs(item).forEach((ref) => current.evidenceRefs.add(ref));
      });
    });

    filteredSnapshots.forEach((item) => {
      const stageRefs = normalizeRefList(item?.workflow_trace, item?.metadata?.stage);
      extractArtifactRefs(item).forEach((artifactRef) => {
        const current = ensureArtifact(artifactRef);
        if (!current) return;
        current.snapshotCount += 1;
        current.runIds.add(String(item?.run_id || "").trim() || "--");
        stageRefs.forEach((stage) => current.stages.add(stage));
        extractEvidenceRefs(item).forEach((ref) => current.evidenceRefs.add(ref));
      });
    });

    return Array.from(artifactMap.values())
      .map((item) => ({
        artifactRef: item.artifactRef,
        eventCount: item.eventCount,
        snapshotCount: item.snapshotCount,
        runIds: uniqueStrings([...item.runIds]),
        stages: uniqueStrings([...item.stages]),
        evidenceRefs: uniqueStrings([...item.evidenceRefs]),
      }))
      .sort((a, b) => b.snapshotCount - a.snapshotCount || b.eventCount - a.eventCount);
  }, [replayEvents, replaySnapshots, selectedRunId, selectedStage, selectedEvidenceRef]);

  const evidenceTopology = useMemo(() => {
    const evidenceMap = new Map();
    const filteredEvents = replayEvents.filter((item) => {
      const runMatch = !selectedRunId || String(item?.run_id || "").trim() === selectedRunId;
      const stageMatch = !selectedStage || String(item?.stage || "").trim() === selectedStage;
      const artifactMatch = !selectedArtifactRef || extractArtifactRefs(item).includes(selectedArtifactRef);
      return runMatch && stageMatch && artifactMatch;
    });
    const filteredSnapshots = replaySnapshots.filter((item) => {
      const runMatch = !selectedRunId || String(item?.run_id || "").trim() === selectedRunId;
      const stageMatch = !selectedStage || snapshotTouchesStage(item, selectedStage);
      const artifactMatch = !selectedArtifactRef || extractArtifactRefs(item).includes(selectedArtifactRef);
      return runMatch && stageMatch && artifactMatch;
    });

    const ensureEvidence = (evidenceRef) => {
      const normalizedEvidenceRef = String(evidenceRef || "").trim();
      if (!normalizedEvidenceRef) return null;
      const current = evidenceMap.get(normalizedEvidenceRef) || {
        evidenceRef: normalizedEvidenceRef,
        eventCount: 0,
        snapshotCount: 0,
        runIds: new Set(),
        stages: new Set(),
        artifactRefs: new Set(),
      };
      evidenceMap.set(normalizedEvidenceRef, current);
      return current;
    };

    filteredEvents.forEach((item) => {
      extractEvidenceRefs(item).forEach((evidenceRef) => {
        const current = ensureEvidence(evidenceRef);
        if (!current) return;
        current.eventCount += 1;
        current.runIds.add(String(item?.run_id || "").trim() || "--");
        if (item?.stage) current.stages.add(String(item.stage));
        extractArtifactRefs(item).forEach((ref) => current.artifactRefs.add(ref));
      });
    });

    filteredSnapshots.forEach((item) => {
      const stageRefs = normalizeRefList(item?.workflow_trace, item?.metadata?.stage);
      extractEvidenceRefs(item).forEach((evidenceRef) => {
        const current = ensureEvidence(evidenceRef);
        if (!current) return;
        current.snapshotCount += 1;
        current.runIds.add(String(item?.run_id || "").trim() || "--");
        stageRefs.forEach((stage) => current.stages.add(stage));
        extractArtifactRefs(item).forEach((ref) => current.artifactRefs.add(ref));
      });
    });

    return Array.from(evidenceMap.values())
      .map((item) => ({
        evidenceRef: item.evidenceRef,
        eventCount: item.eventCount,
        snapshotCount: item.snapshotCount,
        runIds: uniqueStrings([...item.runIds]),
        stages: uniqueStrings([...item.stages]),
        artifactRefs: uniqueStrings([...item.artifactRefs]),
      }))
      .sort((a, b) => b.snapshotCount - a.snapshotCount || b.eventCount - a.eventCount);
  }, [replayEvents, replaySnapshots, selectedRunId, selectedStage, selectedArtifactRef]);

  const filteredReplayEvents = useMemo(
    () =>
      replayEvents.filter((item) => {
        const runMatch = !selectedRunId || String(item?.run_id || "").trim() === selectedRunId;
        const stageMatch = !selectedStage || String(item?.stage || "").trim() === selectedStage;
        const artifactMatch = !selectedArtifactRef || extractArtifactRefs(item).includes(selectedArtifactRef);
        const evidenceMatch = !selectedEvidenceRef || extractEvidenceRefs(item).includes(selectedEvidenceRef);
        return runMatch && stageMatch && artifactMatch && evidenceMatch;
      }),
    [replayEvents, selectedRunId, selectedStage, selectedArtifactRef, selectedEvidenceRef]
  );

  const filteredReplaySnapshots = useMemo(
    () =>
      replaySnapshots.filter((item) => {
        const runMatch = !selectedRunId || String(item?.run_id || "").trim() === selectedRunId;
        const stageMatch = !selectedStage || snapshotTouchesStage(item, selectedStage);
        const artifactMatch = !selectedArtifactRef || extractArtifactRefs(item).includes(selectedArtifactRef);
        const evidenceMatch = !selectedEvidenceRef || extractEvidenceRefs(item).includes(selectedEvidenceRef);
        return runMatch && stageMatch && artifactMatch && evidenceMatch;
      }),
    [replaySnapshots, selectedRunId, selectedStage, selectedArtifactRef, selectedEvidenceRef]
  );

  useEffect(() => {
    if (!filteredReplayEvents.length) {
      setSelectedEventId("");
      return;
    }
    if (!filteredReplayEvents.some((item) => item?.event_id === selectedEventId)) {
      setSelectedEventId(filteredReplayEvents[0]?.event_id || "");
    }
  }, [filteredReplayEvents, selectedEventId]);

  useEffect(() => {
    if (!filteredReplaySnapshots.length) {
      setSelectedSnapshotId("");
      return;
    }
    if (!filteredReplaySnapshots.some((item) => item?.snapshot_id === selectedSnapshotId)) {
      setSelectedSnapshotId(filteredReplaySnapshots[0]?.snapshot_id || "");
    }
  }, [filteredReplaySnapshots, selectedSnapshotId]);

  const selectedEvent = useMemo(
    () => filteredReplayEvents.find((item) => item?.event_id === selectedEventId) || filteredReplayEvents[0] || null,
    [filteredReplayEvents, selectedEventId]
  );
  const selectedSnapshot = useMemo(
    () =>
      filteredReplaySnapshots.find((item) => item?.snapshot_id === selectedSnapshotId) || filteredReplaySnapshots[0] || null,
    [filteredReplaySnapshots, selectedSnapshotId]
  );
  const selectedSnapshotRetrySummary = useMemo(
    () => pickRetryRecoverySummary(selectedSnapshot?.metadata || {}),
    [selectedSnapshot]
  );
  const selectedServiceTrajectory = useMemo(() => {
    if (!serviceTrajectories.length) return null;
    const focused = String(replayScope?.targetServiceRef || "").trim();
    if (focused) {
      return serviceTrajectories.find((item) => String(item?.target_service_ref || "").trim() === focused) || serviceTrajectories[0];
    }
    return serviceTrajectories[0];
  }, [serviceTrajectories, replayScope?.targetServiceRef]);
  const selectedTrajectoryLineage = useMemo(() => {
    const targetServiceRef = String(selectedServiceTrajectory?.target_service_ref || "").trim();
    if (!targetServiceRef) return [];
    return lineageItems.filter((item) => String(item?.target_service_ref || "").trim() === targetServiceRef);
  }, [lineageItems, selectedServiceTrajectory]);
  const selectedLineageEntry = useMemo(
    () =>
      selectedTrajectoryLineage.find((item, index) => buildLineageKey(item, index) === selectedLineageKey) ||
      selectedTrajectoryLineage[0] ||
      null,
    [selectedTrajectoryLineage, selectedLineageKey]
  );
  const selectedHandoffRelationship = useMemo(
    () => handoffRelationships.find((item) => item?.relation_ref === replayScope?.handoffRef) || null,
    [handoffRelationships, replayScope?.handoffRef]
  );
  const handoffTopology = useMemo(() => {
    const laneMap = new Map();
    handoffRelationships.forEach((item) => {
      const sourceAgent = String(item?.source_agent_id || "--").trim() || "--";
      const targetAgent = String(item?.target_agent_id || "--").trim() || "--";
      const laneKey = `${sourceAgent}=>${targetAgent}`;
      const current = laneMap.get(laneKey) || {
        laneKey,
        sourceAgent,
        targetAgent,
        relationRefs: [],
        stagePairs: [],
        targetServiceRefs: [],
        dominantContracts: [],
        eventCount: 0,
        snapshotCount: 0,
      };

      current.relationRefs.push(String(item?.relation_ref || "").trim());
      current.stagePairs.push(`${item?.upstream_stage || "--"}=>${item?.downstream_stage || "--"}`);
      current.targetServiceRefs.push(...uniqueStrings(item?.target_service_refs || []));
      if (item?.dominant_typed_contract) {
        current.dominantContracts.push(String(item.dominant_typed_contract));
      }
      current.eventCount += Number(item?.event_count || 0);
      current.snapshotCount += Number(item?.snapshot_count || 0);
      laneMap.set(laneKey, current);
    });

    return Array.from(laneMap.values())
      .map((item) => ({
        ...item,
        relationRefs: uniqueStrings(item.relationRefs),
        stagePairs: uniqueStrings(item.stagePairs),
        targetServiceRefs: uniqueStrings(item.targetServiceRefs),
        dominantContracts: uniqueStrings(item.dominantContracts),
      }))
      .sort((a, b) => b.eventCount - a.eventCount || b.snapshotCount - a.snapshotCount);
  }, [handoffRelationships]);
  const proposalHandoffLanes = useMemo(
    () => handoffTopology.filter((lane) => lane.relationRefs.some((ref) => proposalHandoffRefs.includes(ref))),
    [handoffTopology, proposalHandoffRefs]
  );

  const proposalReplaySummary = useMemo(
    () => ({
      eventCount: proposalReplayContext?.matchedEvents?.length || 0,
      snapshotCount: proposalReplayContext?.matchedSnapshots?.length || 0,
      handoffCount: proposalReplayContext?.matchedHandoffs?.length || 0,
      runCount: proposalRunIds.length,
      stageCount: proposalStageRefs.length,
      artifactCount: proposalArtifactRefs.length,
      targetServiceCount: proposalTargetServiceRefs.length,
    }),
    [proposalReplayContext, proposalRunIds, proposalStageRefs, proposalArtifactRefs, proposalTargetServiceRefs]
  );

  useEffect(() => {
    if (selectedRunId && !runTopology.some((item) => item.runId === selectedRunId)) {
      setReplayScope?.((prev) => ({
        ...(prev || {}),
        runId: "",
        stageRef: "",
      }));
    }
  }, [runTopology, selectedRunId, setReplayScope]);

  useEffect(() => {
    if (selectedStage && !stageTopology.some((item) => item.stage === selectedStage)) {
      setReplayScope?.((prev) => ({
        ...(prev || {}),
        stageRef: "",
      }));
    }
  }, [stageTopology, selectedStage, setReplayScope]);

  useEffect(() => {
    if (!selectedTrajectoryLineage.length) {
      setSelectedLineageKey("");
      return;
    }
    if (!selectedTrajectoryLineage.some((item, index) => buildLineageKey(item, index) === selectedLineageKey)) {
      setSelectedLineageKey(buildLineageKey(selectedTrajectoryLineage[0], 0));
    }
  }, [selectedTrajectoryLineage, selectedLineageKey]);

  function patchReplayScope(patch) {
    setReplayScope?.((prev) => ({
      ...(prev || {}),
      runId: prev?.runId || "",
      stageRef: prev?.stageRef || "",
      projectionRef: "",
      handoffRef: "",
      targetServiceRef: prev?.targetServiceRef || "",
      artifactLookupRef: "",
      evidenceLookupRef: "",
      retryResumeCheckpointRef: "",
      retryResumeInputRef: "",
      ...patch,
    }));
  }

  function toggleProjection(projectionRef) {
    const normalized = String(projectionRef || "").trim();
    patchReplayScope({
      projectionRef: replayScope?.projectionRef === normalized ? "" : normalized,
      handoffRef: "",
    });
  }

  function toggleHandoff(handoffRef) {
    const normalized = String(handoffRef || "").trim();
    patchReplayScope({
      projectionRef: "",
      handoffRef: replayScope?.handoffRef === normalized ? "" : normalized,
    });
  }

  function toggleTargetService(targetServiceRef) {
    const normalized = String(targetServiceRef || "").trim();
    setReplayScope?.((prev) => ({
      ...(prev || {}),
      targetServiceRef: prev?.targetServiceRef === normalized ? "" : normalized,
    }));
  }

  function focusLineageEntry(item, index = 0) {
    setSelectedLineageKey(buildLineageKey(item, index));
  }

  function focusLineageBy(field, value) {
    const normalized = String(value || "").trim();
    if (!normalized) return;
    const matchIndex = selectedTrajectoryLineage.findIndex((item) => String(item?.[field] || "").trim() === normalized);
    if (matchIndex >= 0) {
      focusLineageEntry(selectedTrajectoryLineage[matchIndex], matchIndex);
    }
  }

  function toggleRunFocus(runId) {
    const normalized = String(runId || "").trim();
    setReplayScope?.((prev) => ({
      ...(prev || {}),
      runId: prev?.runId === normalized ? "" : normalized,
      stageRef: "",
      artifactLookupRef: "",
      evidenceLookupRef: "",
    }));
  }

  function toggleStageFocus(stage) {
    const normalized = String(stage || "").trim();
    setReplayScope?.((prev) => ({
      ...(prev || {}),
      stageRef: prev?.stageRef === normalized ? "" : normalized,
      artifactLookupRef: "",
      evidenceLookupRef: "",
    }));
  }

  function toggleArtifactFocus(artifactRef) {
    const normalized = String(artifactRef || "").trim();
    patchReplayScope({
      artifactLookupRef: selectedArtifactRef === normalized ? "" : normalized,
      evidenceLookupRef: "",
    });
  }

  function toggleEvidenceFocus(evidenceRef) {
    const normalized = String(evidenceRef || "").trim();
    patchReplayScope({
      artifactLookupRef: "",
      evidenceLookupRef: selectedEvidenceRef === normalized ? "" : normalized,
    });
  }

  function toggleRetryResumeCheckpointFocus(checkpointRef) {
    const normalized = String(checkpointRef || "").trim();
    patchReplayScope({
      retryResumeCheckpointRef: selectedRetryResumeCheckpointRef === normalized ? "" : normalized,
      retryResumeInputRef: "",
    });
  }

  function toggleRetryResumeInputFocus(inputRef) {
    const normalized = String(inputRef || "").trim();
    patchReplayScope({
      retryResumeCheckpointRef: "",
      retryResumeInputRef: selectedRetryResumeInputRef === normalized ? "" : normalized,
    });
  }

  function clearReplayQueryFocus() {
    setReplayScope?.((prev) => ({
      ...(prev || {}),
      projectionRef: "",
      handoffRef: "",
      artifactLookupRef: "",
      evidenceLookupRef: "",
      retryResumeCheckpointRef: "",
      retryResumeInputRef: "",
    }));
  }

  function clearReplayLensFocus() {
    setReplayScope?.((prev) => ({
      ...(prev || {}),
      runId: "",
      stageRef: "",
      targetServiceRef: "",
    }));
  }

  function clearAllReplayFocus() {
    setReplayScope?.({
      runId: "",
      stageRef: "",
      projectionRef: "",
      handoffRef: "",
      targetServiceRef: "",
      artifactLookupRef: "",
      evidenceLookupRef: "",
      retryResumeCheckpointRef: "",
      retryResumeInputRef: "",
    });
  }

  return (
    <Panel
      title="本地 Replay 与关系深钻"
      subtitle="这块直接消费单 case 的 replay 概览与 drilldown，支持点选 projection、handoff 与目标服务做本地深钻。"
    >
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="项目编号" value={currentCaseId || "--"} />
        <MetricCard label="最新运行" value={timelineOverview?.latest_run_id || "--"} />
        <MetricCard
          label="回放状态"
          value={timelineOverview?.latest_status || "--"}
          valueLabel={timelineOverview?.latest_status_label}
        />
        <MetricCard label="匹配运行数" value={matchedRunIds.length} />
        <MetricCard label="Snapshot" value={summary?.snapshot_count ?? timelineOverview?.timeline_summary?.snapshot_count ?? 0} />
        <MetricCard label="事件数" value={summary?.event_count ?? timelineOverview?.timeline_summary?.event_count ?? 0} />
        <MetricCard
          label="Version Lineage"
          value={summary?.version_lineage_count ?? timelineOverview?.timeline_summary?.version_lineage_count ?? 0}
        />
        <MetricCard label="目标服务" value={targetServiceRefs.length} />
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">当前查询范围</p>
          <TagPill tone={scope?.run_id ? "ok" : "warn"}>{scope?.run_id ? "按运行收口" : "回落最新运行"}</TagPill>
          <TagPill tone="neutral">单 case / 本地 replay</TagPill>
          {loading ? <TagPill tone="warn">加载中</TagPill> : null}
          {listLoading ? <TagPill tone="warn">列表同步中</TagPill> : null}
          {error ? <TagPill tone="bad">拉取失败</TagPill> : null}
          {listError ? <TagPill tone="bad">列表拉取失败</TagPill> : null}
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-3">
          {replayDataSources.map((item) => {
            const active = activeDataSource?.id === item.id;
            return (
              <button
                type="button"
                key={`source-${item.id}`}
                onClick={() => setSelectedDataSource(item.id)}
                className={cn(
                  "rounded-xl border px-3 py-3 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-sky-300",
                  active ? "border-sky-400 bg-sky-50" : "border-slate-200 bg-slate-50 hover:bg-slate-100"
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-black text-slate-900">{item.label}</p>
                  <TagPill tone={item.tone}>
                    {item.ready
                      ? `就绪 (${countActiveScopeFields(item.scope)} 个 scope 字段)`
                      : item.loading
                        ? "加载中"
                        : item.error
                          ? "失败"
                          : "待加载"}
                  </TagPill>
                  {active ? <TagPill tone="ok">当前查看</TagPill> : null}
                </div>
                <p className="mt-2 text-sm text-slate-700">{item.countLabel}</p>
                <p className="mt-1 text-xs text-slate-500">{`最近刷新 ${formatRefreshTime(item.updatedAt)}`}</p>
                <p className="mt-1 text-xs text-slate-500">{item.detail}</p>
              </button>
            );
          })}
        </div>
        <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">链路健康时间带</p>
            <TagPill tone="neutral">最近 6 次记录</TagPill>
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            这里把 `drilldown / events / snapshots` 三个回放数据面的最近成功/失败压成一条轻量时间带，方便快速判断哪一段链路在抖动。
          </p>
          <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-3">
            {replayDataSources.map((item) => {
              const latestHistory = (item.history || [])[0] || null;
              return (
                <button
                  type="button"
                  key={`health-strip-${item.id}`}
                  onClick={() => setSelectedDataSource(item.id)}
                  className={cn(
                    "rounded-xl border px-3 py-3 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-sky-300",
                    activeDataSource?.id === item.id
                      ? "border-sky-400 bg-sky-50"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-black text-slate-900">{item.label}</p>
                    <TagPill tone={historyTone(latestHistory?.status)}>
                      {latestHistory ? historyStatusLabel(latestHistory.status) : "暂无记录"}
                    </TagPill>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(item.history || []).slice(0, 6).map((historyItem) => (
                      <TagPill key={`history-strip-${item.id}-${historyItem.id}`} tone={historyTone(historyItem.status)}>
                        {`${historyStatusLabel(historyItem.status)} ${formatRefreshTime(historyItem.createdAt)}`}
                      </TagPill>
                    ))}
                    {!(item.history || []).length ? <TagPill tone="neutral">尚未形成健康轨迹</TagPill> : null}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
        {error ? <p className="mt-2 text-sm text-rose-700">{error}</p> : null}
        {listError ? <p className="mt-2 text-sm text-rose-700">{listError}</p> : null}
        {hasFallbackReplayLists ? (
          <p className="mt-2 text-sm text-amber-700">
            当前关系聚合拉取失败，但事件/快照基础列表仍可继续回看；这通常适合先做局部联调，再排查 drilldown 聚合链路。
          </p>
        ) : null}
          <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">{`${activeDataSource?.label || "数据源"} 详情`}</p>
              {activeDataSource?.error ? <TagPill tone="bad">当前源失败</TagPill> : null}
              {activeDataSource?.loading ? <TagPill tone="warn">请求中</TagPill> : null}
            <LocalFilterPill tone="neutral" onClick={() => refreshReplaySource?.(activeDataSource?.id)}>
              重新拉取
            </LocalFilterPill>
          </div>
          <p className="mt-2 text-sm text-slate-700">{activeDataSource?.countLabel || "--"}</p>
          <p className="mt-1 text-xs text-slate-500">{`最近刷新 ${formatRefreshTime(activeDataSource?.updatedAt)}`}</p>
          <div className="mt-3">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">请求参数快照</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(activeDataSource?.requestParams || {})
                .filter(([, value]) => String(value || "").trim())
                .map(([key, value]) => (
                  <TagPill key={`source-param-${activeDataSource?.id}-${key}`} tone="warn">
                    {`${getScopeFieldLabel(key)} ${value}`}
                  </TagPill>
                ))}
              {countActiveScopeFields(activeDataSource?.requestParams || {}) === 0 ? (
                <TagPill tone="neutral">当前源未记录请求参数</TagPill>
              ) : null}
            </div>
          </div>
          <div className="mt-3">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">后端返回 Scope</p>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(activeDataSource?.scope || {})
              .filter(([, value]) => String(value || "").trim())
              .map(([key, value]) => (
                <TagPill key={`source-scope-${activeDataSource?.id}-${key}`} tone="neutral">
                  {`${getScopeFieldLabel(key)} ${value}`}
                </TagPill>
              ))}
            {countActiveScopeFields(activeDataSource?.scope || {}) === 0 ? (
              <TagPill tone="neutral">当前源未返回额外 scope</TagPill>
            ) : null}
          </div>
          <div className="mt-3">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">最近健康历史</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {(activeDataSource?.history || []).map((item) => (
                <TagPill key={item.id} tone={historyTone(item.status)}>
                  {`${item.status === "success" ? "成功" : item.status === "error" ? "失败" : "未知"} ${formatRefreshTime(item.createdAt)}`}
                </TagPill>
              ))}
              {!(activeDataSource?.history || []).length ? (
                <TagPill tone="neutral">当前源还没有健康记录</TagPill>
              ) : null}
            </div>
            {(activeDataSource?.history || []).length ? (
              <div className="mt-2 space-y-2">
                {activeDataSource.history.slice(0, 3).map((item) => (
                  <p key={`${item.id}-message`} className="text-xs text-slate-500">
                    {`${item.status === "success" ? "成功" : item.status === "error" ? "失败" : "未知"} · ${formatRefreshTime(item.createdAt)} · ${item.message || "无附加说明"}`}
                  </p>
                ))}
              </div>
            ) : null}
          </div>
          {activeDataSource?.error ? <p className="mt-3 text-sm text-rose-700">{activeDataSource.error}</p> : null}
        </div>
        <>
          <p className="mt-3 text-xs leading-5 text-slate-500">
            下面这排是后端已经实际应用的 replay 查询范围；如果某个条件没有出现在这里，就说明它目前仍只是前端联动焦点或面板内二次过滤。
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {scope?.run_id ? <TagPill tone="ok">{`run_id ${scope.run_id}`}</TagPill> : null}
            {scope?.projection_ref ? <ReplayFocusPill kind="projectionRef" value={scope.projection_ref} /> : null}
            {scope?.handoff_ref ? <ReplayFocusPill kind="handoffRef" value={scope.handoff_ref} /> : null}
            {scope?.artifact_lookup_ref ? (
              <ReplayFocusPill kind="artifactLookupRef" value={scope.artifact_lookup_ref} />
            ) : null}
            {scope?.evidence_lookup_ref ? (
              <ReplayFocusPill kind="evidenceLookupRef" value={scope.evidence_lookup_ref} />
            ) : null}
            {scope?.retry_resume_checkpoint_ref ? (
              <ReplayFocusPill kind="retryResumeCheckpointRef" value={scope.retry_resume_checkpoint_ref} />
            ) : null}
            {scope?.retry_resume_input_ref ? (
              <ReplayFocusPill kind="retryResumeInputRef" value={scope.retry_resume_input_ref} />
            ) : null}
            {uniqueStrings(summary?.typed_contract_refs || []).slice(0, 4).map((item) => (
              <TagPill key={`typed-contract-${item}`} tone="neutral">
                {item}
              </TagPill>
            ))}
            {matchedRunIds.length === 0 && !loading ? <TagPill tone="neutral">当前暂无 replay drilldown</TagPill> : null}
          </div>
          {(replayEventsResponse?.scope || replaySnapshotsResponse?.scope) ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {replayEventsResponse?.scope ? <TagPill tone="neutral">事件列表已独立拉取</TagPill> : null}
              {replaySnapshotsResponse?.scope ? <TagPill tone="neutral">快照列表已独立拉取</TagPill> : null}
            </div>
          ) : null}

          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">共享 Replay 焦点</p>
              {hasQueryBackedReplayFocus ? <TagPill tone="ok">含后端深钻焦点</TagPill> : null}
              {hasLocalOnlyFilters ? <TagPill tone="warn">含前端联动镜头</TagPill> : null}
              {(hasQueryBackedReplayFocus || hasLocalOnlyFilters) ? (
                <LocalFilterPill
                  tone="bad"
                  onClick={clearAllReplayFocus}
                >
                  清空全部焦点
                </LocalFilterPill>
              ) : null}
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              这里把整页共享的 replay 焦点拆成两类展示：
              `Projection / Handoff / 工件 / 证据 / 恢复点` 会写回后端回看查询；
              `运行 / 阶段 / 目标服务` 更偏向前端联动镜头，其中目标服务还会驱动单服务 lineage 拉取。
            </p>
            <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-2">
              <div className="rounded-xl border border-white/80 bg-white/70 px-3 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">后端深钻焦点</p>
                  {hasQueryBackedReplayFocus ? (
                    <LocalFilterPill tone="bad" onClick={clearReplayQueryFocus}>
                      清空后端深钻
                    </LocalFilterPill>
                  ) : null}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {replayScope?.projectionRef ? (
                    <ReplayFocusPill kind="projectionRef" value={replayScope.projectionRef} active />
                  ) : null}
                  {replayScope?.handoffRef ? (
                    <ReplayFocusPill kind="handoffRef" value={replayScope.handoffRef} active />
                  ) : null}
                  {replayScope?.artifactLookupRef ? (
                    <ReplayFocusPill kind="artifactLookupRef" value={replayScope.artifactLookupRef} active />
                  ) : null}
                  {replayScope?.evidenceLookupRef ? (
                    <ReplayFocusPill kind="evidenceLookupRef" value={replayScope.evidenceLookupRef} active />
                  ) : null}
                  {replayScope?.retryResumeCheckpointRef ? (
                    <ReplayFocusPill
                      kind="retryResumeCheckpointRef"
                      value={replayScope.retryResumeCheckpointRef}
                      active
                    />
                  ) : null}
                  {replayScope?.retryResumeInputRef ? (
                    <ReplayFocusPill kind="retryResumeInputRef" value={replayScope.retryResumeInputRef} active />
                  ) : null}
                  {!hasQueryBackedReplayFocus ? <TagPill tone="neutral">当前未锁定后端深钻焦点</TagPill> : null}
                </div>
              </div>
              <div className="rounded-xl border border-white/80 bg-white/70 px-3 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">前端联动镜头</p>
                  {hasLocalOnlyFilters ? (
                    <LocalFilterPill tone="bad" onClick={clearReplayLensFocus}>
                      清空联动镜头
                    </LocalFilterPill>
                  ) : null}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {replayScope?.runId ? <TagPill tone="ok">{`运行 ${replayScope.runId}`}</TagPill> : null}
                  {replayScope?.stageRef ? (
                    <ReplayFocusPill kind="stageRef" value={replayScope.stageRef} active />
                  ) : null}
                  {replayScope?.targetServiceRef ? (
                    <ReplayFocusPill kind="targetServiceRef" value={replayScope.targetServiceRef} active />
                  ) : null}
                  {!hasLocalOnlyFilters ? <TagPill tone="neutral">当前为默认联动镜头</TagPill> : null}
                </div>
              </div>
            </div>
          </div>
        </>
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">Retry 恢复点</p>
          <TagPill tone={hasRetryRecoveryData(activeRetrySummary) ? "ok" : "neutral"}>
            {hasRetryRecoveryData(activeRetrySummary) ? activeRetrySourceLabel : "当前无 retry"}
          </TagPill>
          <TagPill tone="neutral">{`窗口 ${activeRetrySummary.retryWindowCount}`}</TagPill>
          <TagPill tone="neutral">{`Handoff ${activeRetrySummary.retryHandoffCount}`}</TagPill>
          <TagPill tone="neutral">{`策略 ${activeRetrySummary.retryCompressionPolicies.length}`}</TagPill>
          <TagPill tone="neutral">{`恢复点 ${activeRetrySummary.retryResumeCheckpointRefs.length}`}</TagPill>
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          这里把 same-run retry 的独立窗口、压缩策略和恢复定位点直接翻译成可读视图。当前只是 replay
          查询层可回看，不代表系统已经按这些恢复点自动续跑。
        </p>
        {!hasRetryRecoveryData(activeRetrySummary) ? (
          <p className="mt-3 text-sm text-slate-500">当前范围下还没有 retry 恢复点摘要；若本轮未触发 same-run retry，这是正常现象。</p>
        ) : (
          <>
            <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
              <MetricCard label="Retry 窗口" value={activeRetrySummary.retryWindowCount} />
              <MetricCard label="Retry 交接" value={activeRetrySummary.retryHandoffCount} />
              <MetricCard label="压缩阶段" value={activeRetrySummary.retryCompressionStages.length} />
              <MetricCard label="Resume 输入" value={activeRetrySummary.retryResumeInputRefs.length} />
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-sm font-black text-slate-900">Retry 独立窗口 / 交接包</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {activeRetrySummary.retryProjectionRefs.map((ref) => (
                    <ReplayFocusButton
                      key={`retry-projection-${ref}`}
                      kind="projectionRef"
                      value={ref}
                      active={replayScope?.projectionRef === ref}
                      onClick={() => toggleProjection(ref)}
                      ringTone="focus:ring-sky-300"
                    />
                  ))}
                  {activeRetrySummary.retryHandoffRefs.map((ref) => (
                    <ReplayFocusButton
                      key={`retry-handoff-${ref}`}
                      kind="handoffRef"
                      value={ref}
                      active={replayScope?.handoffRef === ref}
                      onClick={() => toggleHandoff(ref)}
                      ringTone="focus:ring-amber-300"
                    />
                  ))}
                  {!activeRetrySummary.retryProjectionRefs.length && !activeRetrySummary.retryHandoffRefs.length ? (
                    <TagPill tone="neutral">暂无 retry 窗口或交接引用</TagPill>
                  ) : null}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-sm font-black text-slate-900">压缩策略 / 恢复定位</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {activeRetrySummary.retryCompressionPolicies.map((item) => (
                    <TagPill key={`retry-policy-${item}`} tone="neutral">
                      {item}
                    </TagPill>
                  ))}
                  {activeRetrySummary.retryCompressionStages.map((item) => (
                    <TagPill key={`retry-stage-${item}`} tone="warn">
                      {item}
                    </TagPill>
                  ))}
                  {!activeRetrySummary.retryCompressionPolicies.length && !activeRetrySummary.retryCompressionStages.length ? (
                    <TagPill tone="neutral">暂无压缩摘要</TagPill>
                  ) : null}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {activeRetrySummary.retryResumeCheckpointRefs.slice(0, 4).map((item) => (
                    <ReplayFocusButton
                      key={`retry-checkpoint-${item}`}
                      kind="retryResumeCheckpointRef"
                      value={item}
                      active={selectedRetryResumeCheckpointRef === item}
                      onClick={() => toggleRetryResumeCheckpointFocus(item)}
                      ringTone="focus:ring-emerald-300"
                    />
                  ))}
                  {activeRetrySummary.retryResumeInputRefs.slice(0, 4).map((item) => (
                    <ReplayFocusButton
                      key={`retry-input-${item}`}
                      kind="retryResumeInputRef"
                      value={item}
                      active={selectedRetryResumeInputRef === item}
                      onClick={() => toggleRetryResumeInputFocus(item)}
                      ringTone="focus:ring-slate-300"
                    />
                  ))}
                  {!activeRetrySummary.retryResumeCheckpointRefs.length && !activeRetrySummary.retryResumeInputRefs.length ? (
                    <TagPill tone="neutral">暂无恢复定位点</TagPill>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {activeRetrySummary.retryTypedContractRefs.slice(0, 6).map((item) => (
                <TagPill key={`retry-contract-${item}`} tone="neutral">
                  {item}
                </TagPill>
              ))}
              {activeRetrySummary.retryRetainedRefs.slice(0, 6).map((item) => (
                <TagPill key={`retry-retained-${item}`} tone="warn">
                  {item}
                </TagPill>
              ))}
              {activeRetrySummary.retryLineageRefs.slice(0, 4).map((item) => (
                <TagPill key={`retry-lineage-${item}`} tone="ok">
                  {item}
                </TagPill>
              ))}
            </div>
          </>
        )}
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">Proposal Lens</p>
          {selectedProposalId ? <TagPill tone="ok">{selectedProposalId}</TagPill> : <TagPill tone="neutral">未锁定 proposal</TagPill>}
          <TagPill tone="neutral">{`事件 ${proposalReplaySummary.eventCount}`}</TagPill>
          <TagPill tone="neutral">{`快照 ${proposalReplaySummary.snapshotCount}`}</TagPill>
          <TagPill tone="neutral">{`Handoff ${proposalReplaySummary.handoffCount}`}</TagPill>
          <TagPill tone="neutral">{`目标服务 ${proposalReplaySummary.targetServiceCount}`}</TagPill>
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          这里把当前 proposal 已命中的 replay 线索收口成一个专题视角，不新增后端接口，只复用现有 drilldown 结果来解释 proposal 在运行、阶段、handoff 和目标服务上的落点。
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {proposalRunIds.map((item) => (
            <TagPill key={`proposal-lens-run-${item}`} tone={selectedRunId === item ? "ok" : "neutral"}>
              {item}
            </TagPill>
          ))}
          {proposalStageRefs.map((item) => (
            <ReplayFocusPill
              key={`proposal-lens-stage-${item}`}
              kind="stageRef"
              value={item}
              active={selectedStage === item}
            />
          ))}
          {proposalArtifactRefs.map((item) => (
            <TagPill key={`proposal-lens-artifact-${item}`} tone={selectedArtifactRef === item ? "ok" : "neutral"}>
              {item}
            </TagPill>
          ))}
          {proposalTargetServiceRefs.map((item) => (
            <ReplayFocusPill
              key={`proposal-lens-service-${item}`}
              kind="targetServiceRef"
              value={item}
              active={String(replayScope?.targetServiceRef || "").trim() === item}
            />
          ))}
          {!selectedProposalId ? <TagPill tone="neutral">先在候选方案区或工作台锁定 proposal</TagPill> : null}
          {selectedProposalId &&
          !proposalReplaySummary.eventCount &&
          !proposalReplaySummary.snapshotCount &&
          !proposalReplaySummary.handoffCount ? (
            <TagPill tone="neutral">当前 replay 里还没有明显命中这条 proposal</TagPill>
          ) : null}
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">本地导航与后端深钻</p>
          <TagPill tone="neutral">{`${runTopology.length} 个运行`}</TagPill>
          <TagPill tone="neutral">{`${stageTopology.length} 个阶段`}</TagPill>
          <TagPill tone="neutral">{`${artifactTopology.length} 个工件`}</TagPill>
          {(selectedRunId || selectedStage || selectedArtifactRef || selectedEvidenceRef) ? (
            <LocalFilterPill tone="bad" onClick={clearAllReplayFocus}>
              清空全部导航
            </LocalFilterPill>
          ) : null}
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          这里显式拆成两类入口：左侧是当前结果上的本地导航镜头，右侧是会写回共享 replay 焦点的后端深钻入口。这样更容易解释为什么有些按钮只影响当前面板，有些会带动整页一起联动。
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {selectedRunId ? <TagPill tone="ok">{`运行 ${selectedRunId}`}</TagPill> : <TagPill tone="neutral">全部运行</TagPill>}
          {selectedStage ? <TagPill tone="warn">{`阶段 ${selectedStage}`}</TagPill> : <TagPill tone="neutral">全部阶段</TagPill>}
          {selectedArtifactRef ? <TagPill tone="ok">{`工件 ${selectedArtifactRef}`}</TagPill> : <TagPill tone="neutral">全部工件</TagPill>}
          {selectedEvidenceRef ? <TagPill tone="warn">{`证据 ${selectedEvidenceRef}`}</TagPill> : <TagPill tone="neutral">全部证据</TagPill>}
          <TagPill tone="neutral">{`可见事件 ${filteredReplayEvents.length}`}</TagPill>
          <TagPill tone="neutral">{`可见快照 ${filteredReplaySnapshots.length}`}</TagPill>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-12">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 xl:col-span-8">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">本地导航镜头</p>
              <TagPill tone="neutral">仅在当前结果上聚合</TagPill>
              {(selectedRunId || selectedStage) ? (
                <LocalFilterPill
                  tone="bad"
                  onClick={() => {
                    setReplayScope?.((prev) => ({
                      ...(prev || {}),
                      runId: "",
                      stageRef: "",
                    }));
                  }}
                >
                  清空本地导航
                </LocalFilterPill>
              ) : null}
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              这里的 `运行 / 阶段` 用于在当前已经拉回的 replay 结果上快速收口，帮助你先定位主链路，再决定要不要进一步按工件或证据做后端深钻。
            </p>
            <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Run Focus</p>
                  {scope?.run_id ? <TagPill tone="ok">{`scope ${scope.run_id}`}</TagPill> : null}
                </div>
                <div className="mt-3 space-y-2">
                  {runTopology.length === 0 ? <p className="text-sm text-slate-500">当前没有可聚合的运行记录。</p> : null}
                  {runTopology.slice(0, 6).map((item) => {
                    const active = selectedRunId === item.runId;
                    const proposalHit = proposalRunIds.includes(item.runId);
                    return (
                      <PillButton
                        key={`run-topology-${item.runId}`}
                        active={active}
                        onClick={() => toggleRunFocus(item.runId)}
                        ringTone="focus:ring-sky-300"
                        className={cn(
                          "w-full rounded-xl border px-3 py-3 text-left transition-colors",
                          active ? "border-sky-400 bg-sky-100" : proposalHit ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white hover:bg-slate-100"
                        )}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <TagPill tone="ok">{item.runId}</TagPill>
                          {proposalHit ? <TagPill tone="warn">Proposal 命中</TagPill> : null}
                          {active ? <TagPill tone="warn">当前运行焦点</TagPill> : null}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <TagPill tone="neutral">{`${item.eventCount} 个事件`}</TagPill>
                          <TagPill tone="neutral">{`${item.snapshotCount} 个快照`}</TagPill>
                          <TagPill tone="neutral">{`${item.stageRefs.length} 个阶段`}</TagPill>
                          <TagPill tone="neutral">{`${item.artifactRefs.length} 个工件`}</TagPill>
                        </div>
                        <p className="mt-2 text-sm text-slate-700">{summarizeText(item.latestSummary || "当前运行暂无摘要。", 120)}</p>
                      </PillButton>
                    );
                  })}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Stage Focus</p>
                  {selectedRunId ? <TagPill tone="ok">{selectedRunId}</TagPill> : <TagPill tone="neutral">跨运行汇总</TagPill>}
                </div>
                <div className="mt-3 space-y-2">
                  {stageTopology.length === 0 ? <p className="text-sm text-slate-500">当前运行下没有可聚合的阶段。</p> : null}
                  {stageTopology.slice(0, 8).map((item) => {
                    const active = selectedStage === item.stage;
                    const proposalHit = proposalStageRefs.includes(item.stage);
                    const topEventKinds = renderCountMap(item.eventKinds, 2);
                    return (
                      <PillButton
                        key={`stage-topology-${item.stage}`}
                        active={active}
                        onClick={() => toggleStageFocus(item.stage)}
                        ringTone="focus:ring-amber-300"
                        className={cn(
                          "w-full rounded-xl border px-3 py-3 text-left transition-colors",
                          active ? "border-amber-400 bg-amber-50" : proposalHit ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white hover:bg-slate-100"
                        )}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <ReplayFocusPill kind="stageRef" value={item.stage} active={active} />
                          {proposalHit ? <TagPill tone="warn">Proposal 命中</TagPill> : null}
                          {active ? <TagPill tone="ok">当前阶段焦点</TagPill> : null}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <TagPill tone="neutral">{`${item.eventCount} 个事件`}</TagPill>
                          <TagPill tone="neutral">{`${item.snapshotCount} 个快照`}</TagPill>
                          <TagPill tone="neutral">{`${item.targetServiceRefs.length} 个服务`}</TagPill>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {topEventKinds.length === 0 ? <TagPill tone="neutral">暂无事件构成</TagPill> : null}
                          {topEventKinds.map(([eventKind, count]) => (
                            <TagPill key={`stage-topology-kind-${item.stage}-${eventKind}`} tone="neutral">
                              {`${eventKind} x ${count}`}
                            </TagPill>
                          ))}
                        </div>
                      </PillButton>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-3 xl:col-span-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">后端深钻入口</p>
              <TagPill tone="ok">会写回 replay 查询</TagPill>
              {(selectedArtifactRef || selectedEvidenceRef) ? (
                <LocalFilterPill
                  tone="bad"
                  onClick={() => {
                    setReplayScope?.((prev) => ({
                      ...(prev || {}),
                      artifactLookupRef: "",
                      evidenceLookupRef: "",
                    }));
                  }}
                >
                  清空工件/证据
                </LocalFilterPill>
              ) : null}
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-600">
              这里的 `工件 / 证据` 不是单纯的本地标签。点选后会回写共享 replay 焦点，并带动后端 drilldown 以及其他联动面板一起刷新。
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {selectedStage ? <TagPill tone="warn">{`阶段约束 ${selectedStage}`}</TagPill> : <TagPill tone="neutral">未限定阶段</TagPill>}
              {selectedArtifactRef ? <TagPill tone="ok">{`当前工件 ${selectedArtifactRef}`}</TagPill> : null}
              {selectedEvidenceRef ? <TagPill tone="warn">{`当前证据 ${selectedEvidenceRef}`}</TagPill> : null}
            </div>
            <div className="mt-4 rounded-xl border border-emerald-200 bg-white/80 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Artifact Focus</p>
                <TagPill tone="neutral">{`${artifactTopology.length} 个候选工件`}</TagPill>
              </div>
              <div className="mt-3 space-y-2">
                {artifactTopology.length === 0 ? <p className="text-sm text-slate-500">当前范围内还没有工件引用。</p> : null}
                {artifactTopology.slice(0, 8).map((item) => {
                  const active = selectedArtifactRef === item.artifactRef;
                  const proposalHit = proposalArtifactRefs.includes(item.artifactRef);
                  return (
                    <PillButton
                      key={`artifact-topology-${item.artifactRef}`}
                      active={active}
                      onClick={() => toggleArtifactFocus(item.artifactRef)}
                      ringTone="focus:ring-emerald-300"
                      className={cn(
                        "w-full rounded-xl border px-3 py-3 text-left transition-colors",
                        active ? "border-emerald-400 bg-emerald-50" : proposalHit ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white hover:bg-slate-100"
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <TagPill tone="ok">{item.artifactRef}</TagPill>
                        {proposalHit ? <TagPill tone="warn">Proposal 命中</TagPill> : null}
                        {active ? <TagPill tone="warn">当前工件焦点</TagPill> : null}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <TagPill tone="neutral">{`${item.snapshotCount} 个快照命中`}</TagPill>
                        <TagPill tone="neutral">{`${item.eventCount} 个事件命中`}</TagPill>
                        <TagPill tone="neutral">{`${item.evidenceRefs.length} 个证据引用`}</TagPill>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {item.stages.slice(0, 3).map((stage) => (
                          <TagPill key={`artifact-topology-stage-${item.artifactRef}-${stage}`} tone="neutral">
                            {stage}
                          </TagPill>
                        ))}
                        {item.evidenceRefs.slice(0, 2).map((evidenceRef) => (
                          <ReplayFocusButton
                            key={`artifact-topology-evidence-${item.artifactRef}-${evidenceRef}`}
                            kind="evidenceLookupRef"
                            value={evidenceRef}
                            active={selectedEvidenceRef === evidenceRef}
                            onClick={() => toggleEvidenceFocus(evidenceRef)}
                            ringTone="focus:ring-emerald-300"
                          />
                        ))}
                      </div>
                    </PillButton>
                  );
                })}
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-emerald-200 bg-white/80 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Evidence Focus</p>
                <TagPill tone="neutral">{`${evidenceTopology.length} 个候选证据`}</TagPill>
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                这里把证据也提升为独立深钻入口，方便从 replay 侧直接按 evidence 回看，而不是只在工件卡或详情标签里被动点击。
              </p>
              <div className="mt-3 space-y-2">
                {evidenceTopology.length === 0 ? <p className="text-sm text-slate-500">当前范围内还没有证据引用。</p> : null}
                {evidenceTopology.slice(0, 8).map((item) => {
                  const active = selectedEvidenceRef === item.evidenceRef;
                  return (
                    <PillButton
                      key={`evidence-topology-${item.evidenceRef}`}
                      active={active}
                      onClick={() => toggleEvidenceFocus(item.evidenceRef)}
                      ringTone="focus:ring-emerald-300"
                      className={cn(
                        "w-full rounded-xl border px-3 py-3 text-left transition-colors",
                        active ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-white hover:bg-slate-100"
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <TagPill tone="warn">{item.evidenceRef}</TagPill>
                        {active ? <TagPill tone="ok">当前证据焦点</TagPill> : null}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <TagPill tone="neutral">{`${item.snapshotCount} 个快照命中`}</TagPill>
                        <TagPill tone="neutral">{`${item.eventCount} 个事件命中`}</TagPill>
                        <TagPill tone="neutral">{`${item.artifactRefs.length} 个关联工件`}</TagPill>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {item.artifactRefs.slice(0, 2).map((artifactRef) => (
                          <ReplayFocusButton
                            key={`evidence-topology-artifact-${item.evidenceRef}-${artifactRef}`}
                            kind="artifactLookupRef"
                            value={artifactRef}
                            active={selectedArtifactRef === artifactRef}
                            onClick={() => toggleArtifactFocus(artifactRef)}
                            ringTone="focus:ring-slate-300"
                          />
                        ))}
                        {item.stages.slice(0, 2).map((stage) => (
                          <TagPill key={`evidence-topology-stage-${item.evidenceRef}-${stage}`} tone="neutral">
                            {stage}
                          </TagPill>
                        ))}
                      </div>
                    </PillButton>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">Handoff 关系摘要</p>
            <TagPill tone={handoffRelationships.length ? "ok" : "warn"}>
              {handoffRelationships.length ? `${handoffRelationships.length} 条` : "暂无关系"}
            </TagPill>
          </div>
          <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Handoff Topology</p>
              <TagPill tone="neutral">{`${handoffTopology.length} 条泳道`}</TagPill>
              {selectedHandoffRelationship?.relation_ref ? (
                <TagPill tone="warn">{`当前 relation ${selectedHandoffRelationship.relation_ref}`}</TagPill>
              ) : null}
            </div>
            <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
              {handoffTopology.length === 0 ? (
                <p className="text-sm text-slate-500">当前还没有可聚合的 handoff 泳道。</p>
              ) : null}
              {handoffTopology.slice(0, 6).map((lane) => {
                const laneActive = lane.relationRefs.includes(String(replayScope?.handoffRef || "").trim());
                const proposalHit = lane.relationRefs.some((ref) => proposalHandoffRefs.includes(ref));
                const primaryRelationRef = lane.relationRefs[0] || "";
                return (
                  <PillButton
                    key={`handoff-lane-${lane.laneKey}`}
                    active={laneActive}
                    onClick={() => toggleHandoff(primaryRelationRef)}
                    ringTone="focus:ring-amber-300"
                    className={cn(
                      "rounded-xl border px-3 py-3 text-left transition-colors",
                      laneActive ? "border-amber-400 bg-amber-50" : proposalHit ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white hover:bg-slate-50"
                    )}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <TagPill tone="neutral">{lane.sourceAgent}</TagPill>
                      <span className="text-xs font-semibold text-slate-400">→</span>
                      <TagPill tone="warn">{lane.targetAgent}</TagPill>
                      {proposalHit ? <TagPill tone="warn">Proposal 命中</TagPill> : null}
                      {laneActive ? <TagPill tone="ok">当前泳道</TagPill> : null}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <TagPill tone="neutral">{`${lane.relationRefs.length} 条 relation`}</TagPill>
                      <TagPill tone="neutral">{`${lane.eventCount} 个事件`}</TagPill>
                      <TagPill tone="neutral">{`${lane.snapshotCount} 个快照`}</TagPill>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {lane.stagePairs.slice(0, 2).map((stagePair) => (
                        <TagPill key={`handoff-lane-stage-${lane.laneKey}-${stagePair}`} tone="neutral">
                          {stagePair}
                        </TagPill>
                      ))}
                      {lane.dominantContracts.slice(0, 2).map((contract) => (
                        <TagPill key={`handoff-lane-contract-${lane.laneKey}-${contract}`} tone="ok">
                          {contract}
                        </TagPill>
                      ))}
                      {lane.targetServiceRefs.slice(0, 2).map((ref) => (
                        <TagPill key={`handoff-lane-target-${lane.laneKey}-${ref}`} tone="warn">
                          {ref}
                        </TagPill>
                      ))}
                    </div>
                  </PillButton>
                );
              })}
            </div>
          </div>
          {selectedProposalId ? (
            <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50/70 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Proposal Handoff Lens</p>
                <TagPill tone="ok">{selectedProposalId}</TagPill>
                <TagPill tone="neutral">{`${proposalHandoffLanes.length} 条泳道`}</TagPill>
                <TagPill tone="neutral">{`${proposalHandoffRefs.length} 个 relation`}</TagPill>
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-600">
                这里把当前 proposal 命中的 handoff 泳道单独收口出来，方便在答辩时直接说明这条方案穿过了哪些 agent 边界、阶段对与 dominant contract。
              </p>
              <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
                {proposalHandoffLanes.length === 0 ? (
                  <p className="text-sm text-slate-500">当前 proposal 还没有明显命中的 handoff 泳道。</p>
                ) : null}
                {proposalHandoffLanes.slice(0, 4).map((lane) => {
                  const laneActive = lane.relationRefs.includes(String(replayScope?.handoffRef || "").trim());
                  const primaryRelationRef = lane.relationRefs[0] || "";
                  return (
                    <button
                      key={`proposal-handoff-lane-${lane.laneKey}`}
                      type="button"
                      onClick={() => toggleHandoff(primaryRelationRef)}
                      className={cn(
                        "rounded-xl border px-3 py-3 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-300",
                        laneActive ? "border-emerald-400 bg-emerald-100" : "border-emerald-200 bg-white hover:bg-emerald-50"
                      )}
                    >
                      <div className="rounded-xl border border-emerald-200/80 bg-emerald-50/70 px-3 py-3">
                        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-600">
                          <span className="rounded-full border border-slate-200 bg-white px-3 py-1">{lane.sourceAgent}</span>
                          <span className="text-emerald-500">→</span>
                          <span className="rounded-full border border-emerald-300 bg-white px-3 py-1">
                            {lane.dominantContracts[0] || "typed contract"}
                          </span>
                          <span className="text-emerald-500">→</span>
                          <span className="rounded-full border border-amber-200 bg-white px-3 py-1">{lane.targetAgent}</span>
                        </div>
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                          {lane.stagePairs.slice(0, 2).map((stagePair, index) => (
                            <div key={`proposal-handoff-flow-${lane.laneKey}-${stagePair}`} className="flex items-center gap-2">
                              <span className="rounded-full bg-white px-2 py-1">{stagePair}</span>
                              {index < Math.min(lane.stagePairs.length, 2) - 1 ? <span className="text-slate-300">→</span> : null}
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <TagPill tone="neutral">{lane.sourceAgent}</TagPill>
                        <span className="text-xs font-semibold text-slate-400">→</span>
                        <TagPill tone="warn">{lane.targetAgent}</TagPill>
                        {laneActive ? <TagPill tone="ok">当前泳道</TagPill> : null}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <TagPill tone="neutral">{`${lane.relationRefs.length} 条 relation`}</TagPill>
                        <TagPill tone="neutral">{`${lane.eventCount} 个事件`}</TagPill>
                        <TagPill tone="neutral">{`${lane.snapshotCount} 个快照`}</TagPill>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {lane.stagePairs.slice(0, 2).map((stagePair) => (
                          <TagPill key={`proposal-handoff-stage-${lane.laneKey}-${stagePair}`} tone="neutral">
                            {stagePair}
                          </TagPill>
                        ))}
                        {lane.dominantContracts.slice(0, 2).map((contract) => (
                          <TagPill key={`proposal-handoff-contract-${lane.laneKey}-${contract}`} tone="ok">
                            {contract}
                          </TagPill>
                        ))}
                        {lane.targetServiceRefs.slice(0, 2).map((ref) => (
                          <TagPill key={`proposal-handoff-target-${lane.laneKey}-${ref}`} tone="warn">
                            {ref}
                          </TagPill>
                        ))}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}
          {selectedHandoffRelationship ? (
            <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50/70 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Focused Relation</p>
                <TagPill tone="warn">{selectedHandoffRelationship.relation_ref || "--"}</TagPill>
                {selectedHandoffRelationship?.handoff_projection_ref ? (
                  <TagPill tone="neutral">{selectedHandoffRelationship.handoff_projection_ref}</TagPill>
                ) : null}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <TagPill tone="neutral">{`${selectedHandoffRelationship?.source_agent_id || "--"} → ${selectedHandoffRelationship?.target_agent_id || "--"}`}</TagPill>
                <TagPill tone="neutral">{`${selectedHandoffRelationship?.upstream_stage || "--"} → ${selectedHandoffRelationship?.downstream_stage || "--"}`}</TagPill>
                {selectedHandoffRelationship?.dominant_typed_contract ? (
                  <TagPill tone="ok">{selectedHandoffRelationship.dominant_typed_contract}</TagPill>
                ) : null}
              </div>
            </div>
          ) : null}
          <div className="mt-3 space-y-2">
            {handoffRelationships.length === 0 ? (
              <p className="text-sm text-slate-500">当前运行还没有可展示的 handoff 关系摘要。</p>
            ) : null}
            {handoffRelationships.slice(0, 6).map((item) => {
              const active = replayScope?.handoffRef === item?.relation_ref;
              return (
                <div
                  key={`handoff-relation-${item?.relation_ref || item?.handoff_projection_ref}`}
                  className={cn(
                    "rounded-xl border px-3 py-3 transition-colors",
                    active ? "border-amber-400 bg-amber-50" : "border-slate-200 bg-slate-50"
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <TagPill tone="neutral">{item?.source_agent_id || "--"}</TagPill>
                    <span className="text-xs font-semibold text-slate-400">→</span>
                    <TagPill tone="warn">{item?.target_agent_id || "--"}</TagPill>
                    {item?.dominant_typed_contract ? <TagPill tone="ok">{item.dominant_typed_contract}</TagPill> : null}
                  </div>
                  <p className="mt-2 text-sm text-slate-800">
                    {`阶段 ${item?.upstream_stage || "--"} → ${item?.downstream_stage || "--"}`}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <ReplayFocusButton
                      kind="handoffRef"
                      value={item?.relation_ref}
                      active={active}
                      onClick={() => toggleHandoff(item?.relation_ref)}
                      ringTone="focus:ring-amber-300"
                    />
                    {item?.handoff_projection_ref ? <TagPill tone="neutral">{item.handoff_projection_ref}</TagPill> : null}
                    <TagPill tone="neutral">{`事件 ${item?.event_count ?? 0}`}</TagPill>
                    <TagPill tone="neutral">{`快照 ${item?.snapshot_count ?? 0}`}</TagPill>
                    {uniqueStrings(item?.target_service_refs || []).slice(0, 2).map((ref) => (
                      <ReplayFocusButton
                        key={`handoff-target-${item?.relation_ref}-${ref}`}
                        kind="targetServiceRef"
                        value={ref}
                        active={replayScope?.targetServiceRef === ref}
                        onClick={() => toggleTargetService(ref)}
                        ringTone="focus:ring-emerald-300"
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">目标服务轨迹</p>
            <TagPill tone={serviceTrajectories.length ? "ok" : "warn"}>
              {serviceTrajectories.length ? `${serviceTrajectories.length} 条` : "暂无轨迹"}
            </TagPill>
          </div>
          <div className="mt-3 space-y-2">
            {serviceTrajectories.length === 0 ? (
              <p className="text-sm text-slate-500">当前运行还没有 target service 轨迹摘要。</p>
            ) : null}
            {selectedServiceTrajectory ? (
              <div className="rounded-xl border border-sky-200 bg-sky-50/70 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-black text-slate-900">当前目标服务专题</p>
                  <TagPill tone="ok">{selectedServiceTrajectory.target_service_ref || "--"}</TagPill>
                  {selectedServiceTrajectory?.latest_status ? (
                    <SemanticPill
                      kind="status"
                      value={selectedServiceTrajectory.latest_status}
                      label={selectedServiceTrajectory.latest_status_label || selectedServiceTrajectory.latest_status}
                    />
                  ) : null}
                  {replayScope?.targetServiceRef ? <TagPill tone="neutral">已锁定 replay 焦点</TagPill> : null}
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  {summarizeText(
                    selectedServiceTrajectory?.latest_summary ||
                      "当前目标服务已经被收口为单服务轨迹视图，可直接对照它经历过的阶段、版本变化和事件构成。"
                  )}
                </p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <MetricCard label="命中运行" value={(selectedServiceTrajectory?.run_ids || []).length} />
                  <MetricCard label="阶段数量" value={(selectedServiceTrajectory?.stages || []).length} />
                  <MetricCard label="Patch 版本" value={(selectedServiceTrajectory?.patch_ids || []).length} />
                  <MetricCard label="轨迹事件" value={sumCountMap(selectedServiceTrajectory?.event_kind_counts)} />
                  <MetricCard label="基线版本" value={(selectedServiceTrajectory?.baseline_versions || []).length} />
                  <MetricCard label="谱系记录" value={selectedTrajectoryLineage.length} />
                </div>
                <div className="mt-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">阶段路径</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    {uniqueStrings(selectedServiceTrajectory?.stages || []).length === 0 ? (
                      <TagPill tone="neutral">暂无阶段路径</TagPill>
                    ) : null}
                    {uniqueStrings(selectedServiceTrajectory?.stages || []).map((stage, index, arr) => (
                      <div key={`selected-trajectory-stage-${stage}`} className="flex items-center gap-2">
                        <TagPill tone="neutral">{stage}</TagPill>
                        {index < arr.length - 1 ? <span className="text-xs font-semibold text-slate-400">→</span> : null}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">事件构成</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {renderCountMap(selectedServiceTrajectory?.event_kind_counts, 8).length === 0 ? (
                      <TagPill tone="neutral">暂无事件计数</TagPill>
                    ) : null}
                    {renderCountMap(selectedServiceTrajectory?.event_kind_counts, 8).map(([eventKind, count]) => (
                      <TagPill key={`selected-trajectory-event-${eventKind}`} tone="neutral">
                        {`${eventKind} × ${count}`}
                      </TagPill>
                    ))}
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                  <div className="rounded-xl border border-white/70 bg-white/70 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">版本切换</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {uniqueStrings(selectedServiceTrajectory?.baseline_versions || []).slice(0, 4).map((version) => (
                        <LocalFilterPill
                          key={`selected-baseline-${version}`}
                          tone="neutral"
                          active={selectedLineageEntry?.baseline_version === version}
                          onClick={() => focusLineageBy("baseline_version", version)}
                        >
                          {`baseline ${version}`}
                        </LocalFilterPill>
                      ))}
                      {uniqueStrings(selectedServiceTrajectory?.patched_versions || []).slice(0, 4).map((version) => (
                        <LocalFilterPill
                          key={`selected-patched-${version}`}
                          tone="warn"
                          active={selectedLineageEntry?.patched_version === version}
                          onClick={() => focusLineageBy("patched_version", version)}
                        >
                          {`patched ${version}`}
                        </LocalFilterPill>
                      ))}
                      {uniqueStrings(selectedServiceTrajectory?.patch_ids || []).slice(0, 4).map((patchId) => (
                        <LocalFilterPill
                          key={`selected-patch-${patchId}`}
                          tone="neutral"
                          active={selectedLineageEntry?.patch_id === patchId}
                          onClick={() => focusLineageBy("patch_id", patchId)}
                        >
                          {patchId}
                        </LocalFilterPill>
                      ))}
                      {!uniqueStrings(selectedServiceTrajectory?.baseline_versions || []).length &&
                      !uniqueStrings(selectedServiceTrajectory?.patched_versions || []).length &&
                      !uniqueStrings(selectedServiceTrajectory?.patch_ids || []).length ? (
                        <TagPill tone="neutral">暂无版本切换摘要</TagPill>
                      ) : null}
                    </div>
                  </div>
                  <div className="rounded-xl border border-white/70 bg-white/70 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">相关谱系</p>
                    <div className="mt-2 space-y-2">
                      {selectedLineageEntry ? (
                        <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <TagPill tone="ok">当前谱系焦点</TagPill>
                            {selectedLineageEntry?.patch_id ? <TagPill tone="warn">{selectedLineageEntry.patch_id}</TagPill> : null}
                            {selectedLineageEntry?.baseline_version ? (
                              <TagPill tone="neutral">{`baseline ${selectedLineageEntry.baseline_version}`}</TagPill>
                            ) : null}
                            {selectedLineageEntry?.patched_version ? (
                              <TagPill tone="warn">{`patched ${selectedLineageEntry.patched_version}`}</TagPill>
                            ) : null}
                            {selectedLineageEntry?.run_id ? <TagPill tone="neutral">{selectedLineageEntry.run_id}</TagPill> : null}
                          </div>
                          <p className="mt-2 text-xs text-slate-500">{formatTime(selectedLineageEntry?.created_at)}</p>
                        </div>
                      ) : null}
                      {selectedTrajectoryLineage.length === 0 ? (
                        <p className="text-sm text-slate-500">当前服务还没有单独命中的 version lineage 记录。</p>
                      ) : null}
                      {selectedTrajectoryLineage.slice(0, 4).map((item, index) => {
                        const active = buildLineageKey(item, index) === selectedLineageKey;
                        return (
                        <button
                          type="button"
                          key={`selected-lineage-${item?.patch_id || index}`}
                          onClick={() => focusLineageEntry(item, index)}
                          className={cn(
                            "w-full rounded-lg border px-3 py-2 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-sky-300",
                            active ? "border-sky-300 bg-sky-100" : "border-slate-200 bg-slate-50 hover:bg-slate-100"
                          )}
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            {item?.patch_id ? <TagPill tone="warn">{item.patch_id}</TagPill> : null}
                            {item?.baseline_version ? <TagPill tone="neutral">{`baseline ${item.baseline_version}`}</TagPill> : null}
                            {item?.patched_version ? <TagPill tone="warn">{`patched ${item.patched_version}`}</TagPill> : null}
                            {active ? <TagPill tone="ok">当前选中</TagPill> : null}
                          </div>
                          <p className="mt-2 text-xs text-slate-500">{formatTime(item?.created_at)}</p>
                        </button>
                      );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
            {serviceTrajectories.slice(0, 6).map((item) => {
              const topEventKinds = renderCountMap(item?.event_kind_counts, 4);
              const active = replayScope?.targetServiceRef === item?.target_service_ref;
              const selected = selectedServiceTrajectory?.target_service_ref === item?.target_service_ref;
              const proposalHit = proposalTargetServiceRefs.includes(String(item?.target_service_ref || "").trim());
              const stageCount = uniqueStrings(item?.stages || []).length;
              const eventCount = sumCountMap(item?.event_kind_counts);
              return (
                <div
                  key={`service-trajectory-${item?.target_service_ref}`}
                  className={cn(
                    "rounded-xl border px-3 py-3 transition-colors",
                    selected ? "border-sky-400 bg-sky-100" : proposalHit ? "border-emerald-300 bg-emerald-50" : "border-sky-200 bg-sky-50"
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <TagPill tone="ok">{item?.target_service_ref || "--"}</TagPill>
                    {proposalHit ? <TagPill tone="warn">Proposal 命中</TagPill> : null}
                    {selected ? <TagPill tone="neutral">当前专题</TagPill> : null}
                    {item?.latest_status ? (
                      <SemanticPill
                        kind="status"
                        value={item.latest_status}
                        label={item.latest_status_label || item.latest_status}
                      />
                    ) : null}
                    <TagPill tone="neutral">{`${(item?.run_ids || []).length} 次运行`}</TagPill>
                  </div>
                  <p className="mt-2 text-sm text-slate-800">{summarizeText(item?.latest_summary)}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <ReplayFocusButton
                      kind="targetServiceRef"
                      value={item?.target_service_ref}
                      active={active}
                      onClick={() => toggleTargetService(item?.target_service_ref)}
                      ringTone="focus:ring-emerald-300"
                    />
                    <TagPill tone="neutral">{`${eventCount} 个事件`}</TagPill>
                    <TagPill tone="neutral">{`${stageCount} 个阶段`}</TagPill>
                    {uniqueStrings(item?.baseline_versions || []).slice(0, 2).map((version) => (
                      <TagPill key={`baseline-${item?.target_service_ref}-${version}`} tone="neutral">
                        {`baseline ${version}`}
                      </TagPill>
                    ))}
                    {uniqueStrings(item?.patched_versions || []).slice(0, 2).map((version) => (
                      <TagPill key={`patched-${item?.target_service_ref}-${version}`} tone="warn">
                        {`patched ${version}`}
                      </TagPill>
                    ))}
                    {uniqueStrings(item?.patch_ids || []).slice(0, 2).map((patchId) => (
                      <TagPill key={`patch-${item?.target_service_ref}-${patchId}`} tone="neutral">
                        {patchId}
                      </TagPill>
                    ))}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {uniqueStrings(item?.stages || []).slice(0, 4).map((stage) => (
                      <TagPill key={`stage-${item?.target_service_ref}-${stage}`} tone="neutral">
                        {stage}
                      </TagPill>
                    ))}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {topEventKinds.length === 0 ? <TagPill tone="neutral">暂无事件计数</TagPill> : null}
                    {topEventKinds.map(([eventKind, count]) => (
                      <TagPill key={`event-kind-${item?.target_service_ref}-${eventKind}`} tone="neutral">
                        {`${eventKind} × ${count}`}
                      </TagPill>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">事件详情</p>
            {selectedEvent?.event_kind ? <TagPill tone="ok">{selectedEvent.event_kind}</TagPill> : null}
            {selectedEvent?.status ? (
              <SemanticPill kind="status" value={selectedEvent.status} label={selectedEvent.status_label || selectedEvent.status} />
            ) : null}
          </div>
          {!selectedEvent ? <p className="mt-2 text-sm text-slate-500">当前还没有可查看的事件详情。</p> : null}
          {selectedEvent ? (
            <>
              <p className="mt-2 text-sm text-slate-800">{summarizeText(selectedEvent.summary || "当前事件暂无摘要。", 220)}</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <MetricCard label="阶段" value={selectedEvent.stage || "--"} />
                <MetricCard label="运行" value={selectedEvent.run_id || "--"} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {selectedEvent?.metadata?.projection_ref ? (
                  <ReplayFocusButton
                    kind="projectionRef"
                    value={selectedEvent.metadata.projection_ref}
                    active={replayScope?.projectionRef === selectedEvent.metadata.projection_ref}
                    onClick={() => toggleProjection(selectedEvent.metadata.projection_ref)}
                    ringTone="focus:ring-sky-300"
                  />
                ) : null}
                {selectedEvent?.metadata?.handoff_ref ? (
                  <ReplayFocusButton
                    kind="handoffRef"
                    value={selectedEvent.metadata.handoff_ref}
                    active={replayScope?.handoffRef === selectedEvent.metadata.handoff_ref}
                    onClick={() => toggleHandoff(selectedEvent.metadata.handoff_ref)}
                    ringTone="focus:ring-amber-300"
                  />
                ) : null}
                {selectedEvent?.metadata?.target_service_ref ? (
                  <ReplayFocusButton
                    kind="targetServiceRef"
                    value={selectedEvent.metadata.target_service_ref}
                    active={replayScope?.targetServiceRef === selectedEvent.metadata.target_service_ref}
                    onClick={() => toggleTargetService(selectedEvent.metadata.target_service_ref)}
                    ringTone="focus:ring-emerald-300"
                  />
                ) : null}
                  {extractArtifactRefs(selectedEvent).slice(0, 2).map((artifactRef) => (
                  <ReplayFocusButton
                    key={`selected-event-artifact-${artifactRef}`}
                    kind="artifactLookupRef"
                    value={artifactRef}
                    active={selectedArtifactRef === artifactRef}
                    onClick={() => toggleArtifactFocus(artifactRef)}
                    ringTone="focus:ring-slate-300"
                  />
                ))}
                {extractEvidenceRefs(selectedEvent).slice(0, 2).map((evidenceRef) => (
                  <ReplayFocusButton
                    key={`selected-event-evidence-${evidenceRef}`}
                    kind="evidenceLookupRef"
                    value={evidenceRef}
                    active={selectedEvidenceRef === evidenceRef}
                    onClick={() => toggleEvidenceFocus(evidenceRef)}
                    ringTone="focus:ring-emerald-300"
                  />
                ))}
              </div>
              <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-sm font-black text-slate-900">Metadata</p>
                {metadataEntries(selectedEvent.metadata).length === 0 ? (
                  <p className="mt-2 text-sm text-slate-500">当前事件没有额外 metadata。</p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {metadataEntries(selectedEvent.metadata).slice(0, 12).map(([key, value]) => (
                      <div key={`event-meta-${key}`} className="rounded-lg border border-white/80 bg-white/80 px-3 py-2">
                        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{key}</p>
                        <p className="mt-1 text-sm text-slate-800">
                          {typeof value === "string" || typeof value === "number" || typeof value === "boolean"
                            ? String(value)
                            : JSON.stringify(value)}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <p className="mt-3 text-xs text-slate-500">{`事件时间 ${formatTime(selectedEvent.created_at)}`}</p>
            </>
          ) : null}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">Snapshot 详情</p>
            {selectedSnapshot?.status ? (
              <SemanticPill
                kind="status"
                value={selectedSnapshot.status}
                label={selectedSnapshot.status_label || selectedSnapshot.status}
              />
            ) : null}
            {selectedSnapshot?.selected_proposal ? <TagPill tone="neutral">{selectedSnapshot.selected_proposal}</TagPill> : null}
          </div>
          {!selectedSnapshot ? <p className="mt-2 text-sm text-slate-500">当前还没有可查看的 snapshot 详情。</p> : null}
          {selectedSnapshot ? (
            <>
              <p className="mt-2 text-sm text-slate-800">{summarizeText(selectedSnapshot.summary || "当前快照暂无摘要。", 220)}</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <MetricCard label="运行" value={selectedSnapshot.run_id || "--"} />
                <MetricCard label="Workflow" value={(selectedSnapshot.workflow_trace || []).length} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {uniqueStrings(selectedSnapshot.projection_refs || []).slice(0, 4).map((projectionRef) => (
                  <ReplayFocusButton
                    key={`selected-snapshot-proj-${projectionRef}`}
                    kind="projectionRef"
                    value={projectionRef}
                    active={replayScope?.projectionRef === projectionRef}
                    onClick={() => toggleProjection(projectionRef)}
                    ringTone="focus:ring-sky-300"
                  />
                ))}
                {uniqueStrings(selectedSnapshot.handoff_refs || []).slice(0, 4).map((handoffRef) => (
                  <ReplayFocusButton
                    key={`selected-snapshot-handoff-${handoffRef}`}
                    kind="handoffRef"
                    value={handoffRef}
                    active={replayScope?.handoffRef === handoffRef}
                    onClick={() => toggleHandoff(handoffRef)}
                    ringTone="focus:ring-amber-300"
                  />
                ))}
              </div>
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-sm font-black text-slate-900">Typed Contract 计数</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {renderCountMap(selectedSnapshot.typed_contract_counts, 8).length === 0 ? (
                      <TagPill tone="neutral">暂无 typed contract 计数</TagPill>
                    ) : null}
                    {renderCountMap(selectedSnapshot.typed_contract_counts, 8).map(([contractRef, count]) => (
                      <TagPill key={`selected-contract-${contractRef}`} tone="neutral">
                        {`${contractRef} × ${count}`}
                      </TagPill>
                    ))}
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-sm font-black text-slate-900">Artifact / Evidence Refs</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {uniqueStrings(selectedSnapshot.artifact_lookup_refs || []).slice(0, 6).map((ref) => (
                      <ReplayFocusButton
                        key={`selected-artifact-${ref}`}
                        kind="artifactLookupRef"
                        value={ref}
                        active={selectedArtifactRef === ref}
                        onClick={() => toggleArtifactFocus(ref)}
                        ringTone="focus:ring-slate-300"
                      />
                    ))}
                    {uniqueStrings(selectedSnapshot.evidence_lookup_refs || []).slice(0, 6).map((ref) => (
                      <ReplayFocusButton
                        key={`selected-evidence-${ref}`}
                        kind="evidenceLookupRef"
                        value={ref}
                        active={selectedEvidenceRef === ref}
                        onClick={() => toggleEvidenceFocus(ref)}
                        ringTone="focus:ring-emerald-300"
                      />
                    ))}
                    {!uniqueStrings(selectedSnapshot.artifact_lookup_refs || []).length &&
                    !uniqueStrings(selectedSnapshot.evidence_lookup_refs || []).length ? (
                      <TagPill tone="neutral">暂无 refs</TagPill>
                    ) : null}
                  </div>
                </div>
              </div>
              {hasRetryRecoveryData(selectedSnapshotRetrySummary) ? (
                <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-black text-slate-900">Snapshot Retry 恢复点</p>
                    <TagPill tone="ok">{`窗口 ${selectedSnapshotRetrySummary.retryWindowCount}`}</TagPill>
                    <TagPill tone="neutral">{`Handoff ${selectedSnapshotRetrySummary.retryHandoffCount}`}</TagPill>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {selectedSnapshotRetrySummary.retryProjectionRefs.slice(0, 4).map((ref) => (
                      <ReplayFocusButton
                        key={`snapshot-retry-proj-${ref}`}
                        kind="projectionRef"
                        value={ref}
                        active={replayScope?.projectionRef === ref}
                        onClick={() => toggleProjection(ref)}
                        ringTone="focus:ring-sky-300"
                      />
                    ))}
                    {selectedSnapshotRetrySummary.retryHandoffRefs.slice(0, 4).map((ref) => (
                      <ReplayFocusButton
                        key={`snapshot-retry-handoff-${ref}`}
                        kind="handoffRef"
                        value={ref}
                        active={replayScope?.handoffRef === ref}
                        onClick={() => toggleHandoff(ref)}
                        ringTone="focus:ring-amber-300"
                      />
                    ))}
                    {selectedSnapshotRetrySummary.retryCompressionPolicies.slice(0, 3).map((item) => (
                      <TagPill key={`snapshot-retry-policy-${item}`} tone="neutral">
                        {item}
                      </TagPill>
                    ))}
                    {selectedSnapshotRetrySummary.retryResumeCheckpointRefs.slice(0, 2).map((item) => (
                      <ReplayFocusButton
                        key={`snapshot-retry-checkpoint-${item}`}
                        kind="retryResumeCheckpointRef"
                        value={item}
                        active={selectedRetryResumeCheckpointRef === item}
                        onClick={() => toggleRetryResumeCheckpointFocus(item)}
                        ringTone="focus:ring-emerald-300"
                      />
                    ))}
                    {selectedSnapshotRetrySummary.retryResumeInputRefs.slice(0, 2).map((item) => (
                      <ReplayFocusButton
                        key={`snapshot-retry-input-${item}`}
                        kind="retryResumeInputRef"
                        value={item}
                        active={selectedRetryResumeInputRef === item}
                        onClick={() => toggleRetryResumeInputFocus(item)}
                        ringTone="focus:ring-slate-300"
                      />
                    ))}
                  </div>
                </div>
              ) : null}
              <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-sm font-black text-slate-900">Snapshot Metadata</p>
                {metadataEntries(selectedSnapshot.metadata).length === 0 ? (
                  <p className="mt-2 text-sm text-slate-500">当前快照没有额外 metadata。</p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {metadataEntries(selectedSnapshot.metadata).slice(0, 12).map(([key, value]) => (
                      <div key={`snapshot-meta-${key}`} className="rounded-lg border border-white/80 bg-white/80 px-3 py-2">
                        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{key}</p>
                        <p className="mt-1 text-sm text-slate-800">
                          {typeof value === "string" || typeof value === "number" || typeof value === "boolean"
                            ? String(value)
                            : JSON.stringify(value)}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <p className="mt-3 text-xs text-slate-500">{`快照时间 ${formatTime(selectedSnapshot.created_at)}`}</p>
            </>
          ) : null}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">命中事件列表</p>
            <TagPill tone={filteredReplayEvents.length ? "ok" : "warn"}>
              {filteredReplayEvents.length ? `${filteredReplayEvents.length} 条` : "暂无事件"}
            </TagPill>
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            这里展示当前 drilldown 命中的事件，方便确认点击某个 projection 或 handoff 后到底落到了哪些执行节点和事件类型。
          </p>
          <div className="mt-3 space-y-2">
            {filteredReplayEvents.length === 0 ? <p className="text-sm text-slate-500">当前筛选下没有事件。</p> : null}
            {filteredReplayEvents.slice(0, 8).map((item) => {
              const active = selectedEvent?.event_id === item?.event_id;
              return (
              <button
                type="button"
                key={item?.event_id || `${item?.stage}-${item?.event_kind}`}
                onClick={() => setSelectedEventId(item?.event_id || "")}
                className={cn(
                  "w-full rounded-xl border px-3 py-3 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-sky-300",
                  active ? "border-sky-400 bg-sky-50" : "border-slate-200 bg-slate-50 hover:bg-slate-100"
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <TagPill tone="neutral">{item?.stage || "--"}</TagPill>
                  <TagPill tone="ok">{item?.event_kind || "--"}</TagPill>
                  {item?.status ? <SemanticPill kind="status" value={item.status} label={item.status_label || item.status} /> : null}
                  {active ? <TagPill tone="ok">当前查看</TagPill> : null}
                </div>
                <p className="mt-2 text-sm text-slate-800">{summarizeText(item?.summary || "当前事件暂无摘要。", 180)}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {item?.run_id ? <TagPill tone="neutral">{item.run_id}</TagPill> : null}
                  {item?.metadata?.projection_ref ? (
                    <ReplayFocusButton
                      kind="projectionRef"
                      value={item.metadata.projection_ref}
                      active={replayScope?.projectionRef === item.metadata.projection_ref}
                      onClick={() => toggleProjection(item.metadata.projection_ref)}
                      ringTone="focus:ring-sky-300"
                    />
                  ) : null}
                  {item?.metadata?.handoff_ref ? (
                    <ReplayFocusButton
                      kind="handoffRef"
                      value={item.metadata.handoff_ref}
                      active={replayScope?.handoffRef === item.metadata.handoff_ref}
                      onClick={() => toggleHandoff(item.metadata.handoff_ref)}
                      ringTone="focus:ring-amber-300"
                    />
                  ) : null}
                  {item?.metadata?.target_service_ref ? (
                    <ReplayFocusButton
                      kind="targetServiceRef"
                      value={item.metadata.target_service_ref}
                      active={replayScope?.targetServiceRef === item.metadata.target_service_ref}
                      onClick={() => toggleTargetService(item.metadata.target_service_ref)}
                      ringTone="focus:ring-emerald-300"
                    />
                  ) : null}
                  {extractArtifactRefs(item).slice(0, 1).map((artifactRef) => (
                    <ReplayFocusButton
                      key={`event-artifact-${item?.event_id}-${artifactRef}`}
                      kind="artifactLookupRef"
                      value={artifactRef}
                      active={selectedArtifactRef === artifactRef}
                      onClick={() => toggleArtifactFocus(artifactRef)}
                      ringTone="focus:ring-slate-300"
                    />
                  ))}
                  {extractEvidenceRefs(item).slice(0, 1).map((evidenceRef) => (
                    <ReplayFocusButton
                      key={`event-evidence-${item?.event_id}-${evidenceRef}`}
                      kind="evidenceLookupRef"
                      value={evidenceRef}
                      active={selectedEvidenceRef === evidenceRef}
                      onClick={() => toggleEvidenceFocus(evidenceRef)}
                      ringTone="focus:ring-emerald-300"
                    />
                  ))}
                </div>
                <p className="mt-2 text-xs text-slate-500">{`事件时间 ${formatTime(item?.created_at)}`}</p>
              </button>
            );
            })}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">命中 Snapshot 列表</p>
            <TagPill tone={filteredReplaySnapshots.length ? "ok" : "warn"}>
              {filteredReplaySnapshots.length ? `${filteredReplaySnapshots.length} 条` : "暂无快照"}
            </TagPill>
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            这里展示当前筛选下的 replay snapshot，方便确认某个窗口、handoff 或服务过滤后，保留下来的记忆与索引摘要。
          </p>
          <div className="mt-3 space-y-2">
            {filteredReplaySnapshots.length === 0 ? <p className="text-sm text-slate-500">当前筛选下没有 snapshot。</p> : null}
            {filteredReplaySnapshots.slice(0, 6).map((item) => {
              const active = selectedSnapshot?.snapshot_id === item?.snapshot_id;
              return (
              <button
                type="button"
                key={item?.snapshot_id || item?.run_id}
                onClick={() => setSelectedSnapshotId(item?.snapshot_id || "")}
                className={cn(
                  "w-full rounded-xl border px-3 py-3 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-sky-300",
                  active ? "border-sky-400 bg-sky-50" : "border-slate-200 bg-slate-50 hover:bg-slate-100"
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  {item?.status ? <SemanticPill kind="status" value={item.status} label={item.status_label || item.status} /> : null}
                  {item?.selected_proposal ? <TagPill tone="neutral">{item.selected_proposal}</TagPill> : null}
                  {item?.run_id ? <TagPill tone="neutral">{item.run_id}</TagPill> : null}
                  {active ? <TagPill tone="ok">当前查看</TagPill> : null}
                </div>
                <p className="mt-2 text-sm text-slate-800">{summarizeText(item?.summary || "当前快照暂无摘要。", 180)}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {uniqueStrings(item?.projection_refs || []).slice(0, 3).map((projectionRef) => (
                    <ReplayFocusButton
                      key={`snapshot-projection-${item?.snapshot_id}-${projectionRef}`}
                      kind="projectionRef"
                      value={projectionRef}
                      active={replayScope?.projectionRef === projectionRef}
                      onClick={() => toggleProjection(projectionRef)}
                      ringTone="focus:ring-sky-300"
                    />
                  ))}
                  {uniqueStrings(item?.handoff_refs || []).slice(0, 3).map((handoffRef) => (
                    <ReplayFocusButton
                      key={`snapshot-handoff-${item?.snapshot_id}-${handoffRef}`}
                      kind="handoffRef"
                      value={handoffRef}
                      active={replayScope?.handoffRef === handoffRef}
                      onClick={() => toggleHandoff(handoffRef)}
                      ringTone="focus:ring-amber-300"
                    />
                  ))}
                  {uniqueStrings(item?.artifact_lookup_refs || []).slice(0, 2).map((artifactRef) => (
                    <ReplayFocusButton
                      key={`snapshot-artifact-${item?.snapshot_id}-${artifactRef}`}
                      kind="artifactLookupRef"
                      value={artifactRef}
                      active={selectedArtifactRef === artifactRef}
                      onClick={() => toggleArtifactFocus(artifactRef)}
                      ringTone="focus:ring-slate-300"
                    />
                  ))}
                  {uniqueStrings(item?.evidence_lookup_refs || []).slice(0, 2).map((evidenceRef) => (
                    <ReplayFocusButton
                      key={`snapshot-evidence-${item?.snapshot_id}-${evidenceRef}`}
                      kind="evidenceLookupRef"
                      value={evidenceRef}
                      active={selectedEvidenceRef === evidenceRef}
                      onClick={() => toggleEvidenceFocus(evidenceRef)}
                      ringTone="focus:ring-emerald-300"
                    />
                  ))}
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {renderCountMap(item?.typed_contract_counts, 3).map(([contractRef, count]) => (
                    <TagPill key={`snapshot-contract-${item?.snapshot_id}-${contractRef}`} tone="neutral">
                      {`${contractRef} × ${count}`}
                    </TagPill>
                  ))}
                </div>
                <p className="mt-2 text-xs text-slate-500">{`快照时间 ${formatTime(item?.created_at)}`}</p>
              </button>
            );
            })}
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">Projection 关系补充</p>
            <TagPill tone={projectionRelationships.length ? "ok" : "warn"}>
              {projectionRelationships.length ? `${projectionRelationships.length} 条` : "暂无关系"}
            </TagPill>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {projectionRelationships.length === 0 ? <TagPill tone="neutral">当前没有 projection 关系摘要</TagPill> : null}
            {projectionRelationships.slice(0, 8).map((item) => {
              const active = replayScope?.projectionRef === item?.relation_ref;
              return (
                <ReplayFocusButton
                  key={`projection-relation-${item?.relation_ref}`}
                  kind="projectionRef"
                  value={item?.relation_ref}
                  active={active}
                  onClick={() => toggleProjection(item?.relation_ref)}
                  ringTone="focus:ring-sky-300"
                />
              );
            })}
          </div>
          <p className="mt-3 text-xs leading-5 text-slate-500">
            点击 projection 标签后，会重新拉取当前运行下该窗口范围的 drilldown。
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">最近快照与版本信息</p>
            {latestSnapshot?.status ? (
              <SemanticPill kind="status" value={latestSnapshot.status} label={latestSnapshot.status_label || latestSnapshot.status} />
            ) : null}
          </div>
          <p className="mt-2 text-sm text-slate-700">
            {summarizeText(latestSnapshot?.summary || latestLineage?.summary || "当前还没有最新 snapshot / lineage 摘要。")}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {latestSnapshot?.projection_ref ? (
              <ReplayFocusButton
                kind="projectionRef"
                value={latestSnapshot.projection_ref}
                active={replayScope?.projectionRef === latestSnapshot.projection_ref}
                onClick={() => toggleProjection(latestSnapshot.projection_ref)}
                ringTone="focus:ring-sky-300"
              />
            ) : null}
            {latestSnapshot?.handoff_ref ? (
              <ReplayFocusButton
                kind="handoffRef"
                value={latestSnapshot.handoff_ref}
                active={replayScope?.handoffRef === latestSnapshot.handoff_ref}
                onClick={() => toggleHandoff(latestSnapshot.handoff_ref)}
                ringTone="focus:ring-amber-300"
              />
            ) : null}
            {latestLineage?.target_service_ref ? (
              <ReplayFocusButton
                kind="targetServiceRef"
                value={latestLineage.target_service_ref}
                active={replayScope?.targetServiceRef === latestLineage.target_service_ref}
                onClick={() => toggleTargetService(latestLineage.target_service_ref)}
                ringTone="focus:ring-emerald-300"
              />
            ) : null}
            {latestLineage?.patch_id ? <TagPill tone="warn">{latestLineage.patch_id}</TagPill> : null}
            {latestLineage?.baseline_version ? <TagPill tone="neutral">{`baseline ${latestLineage.baseline_version}`}</TagPill> : null}
            {latestLineage?.patched_version ? <TagPill tone="warn">{`patched ${latestLineage.patched_version}`}</TagPill> : null}
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">目标服务版本谱系</p>
          {replayScope?.targetServiceRef ? <TagPill tone="ok">{replayScope.targetServiceRef}</TagPill> : null}
          {lineageLoading ? <TagPill tone="warn">加载中</TagPill> : null}
          {lineageError ? <TagPill tone="bad">拉取失败</TagPill> : null}
        </div>
        {lineageError ? <p className="mt-2 text-sm text-rose-700">{lineageError}</p> : null}
        {!replayScope?.targetServiceRef && !lineageLoading ? (
          <p className="mt-2 text-sm text-slate-500">点击上方目标服务轨迹中的服务标签，可查看该服务在当前运行下的版本谱系。</p>
        ) : null}
        <div className="mt-3 space-y-2">
          {replayScope?.targetServiceRef && !lineageLoading && lineageItems.length === 0 && !lineageError ? (
            <p className="text-sm text-slate-500">当前服务还没有可展示的 version lineage 记录。</p>
          ) : null}
          {lineageItems.slice(0, 8).map((item, index) => (
            <div key={`lineage-${item?.patch_id || index}`} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
              <div className="flex flex-wrap items-center gap-2">
                {item?.patch_id ? <TagPill tone="warn">{item.patch_id}</TagPill> : null}
                {item?.baseline_version ? <TagPill tone="neutral">{`baseline ${item.baseline_version}`}</TagPill> : null}
                {item?.patched_version ? <TagPill tone="warn">{`patched ${item.patched_version}`}</TagPill> : null}
                {item?.run_id ? <TagPill tone="neutral">{item.run_id}</TagPill> : null}
              </div>
              <p className="mt-2 text-xs text-slate-500">{`记录时间 ${formatTime(item?.created_at)}`}</p>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}
