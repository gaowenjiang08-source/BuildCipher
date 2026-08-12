import { MetricCard, Panel } from "../../components/Panel";
import { SemanticPill, TagPill } from "../../components/SemanticPill";
import { ReplayFocusPill } from "./ReplayFocusPill";

const PROJECTION_META = {
  generation: { label: "生成窗口", owner: "Generation Agent" },
  audit: { label: "审计窗口", owner: "Audit Agent" },
  attack_planning: { label: "攻击规划窗口", owner: "Attack Planning Agent" },
  vulnerability_evaluation: { label: "漏洞评估窗口", owner: "Vulnerability Agent" },
  patch: { label: "修补窗口", owner: "Patch Agent" },
  reflection: { label: "反思窗口", owner: "Reflection Agent" },
};

function uniqueCardTypes(cards = []) {
  return [...new Set((cards || []).map((item) => item?.card_type).filter(Boolean))];
}

function summarizeObjective(value = "", maxLength = 120) {
  const text = String(value || "").trim();
  if (!text) return "当前窗口暂未提供 objective。";
  return text.length <= maxLength ? text : `${text.slice(0, maxLength)}...`;
}

function deriveProjectionRef(projection = {}, fallbackKey = "") {
  const explicitRef = String(projection?.window_ref || projection?.projection_ref || "").trim();
  if (explicitRef) return explicitRef;

  const agentId = String(projection?.agent_id || fallbackKey || "").trim();
  const roundId = String(projection?.round_id || "main").trim();
  if (!agentId) return "";
  return `${agentId}:${roundId || "main"}`;
}

function buildProjectionRows(contextProjections = {}) {
  return Object.entries(contextProjections || {}).map(([key, projection]) => ({
    key,
    descriptor: PROJECTION_META[key] || {
      label: projection?.agent_id || key,
      owner: "Agent Window",
    },
    projection,
    projectionRef: deriveProjectionRef(projection, key),
  }));
}

function buildPlannerEvidenceCards(contextProjections = {}) {
  return (contextProjections?.attack_planning?.cards || []).filter(
    (item) => item?.card_type === "attack_planner_evidence"
  );
}

function summarizeEvidenceSource(ref = {}) {
  const metadata = ref?.metadata || {};
  const lessonKind = metadata?.lesson_kind || metadata?.doc_type || metadata?.category || "";
  const sourceTitle = metadata?.source_title || "";
  const sourceYear = metadata?.source_year;
  const section = ref?.section || metadata?.section_path || "";
  const sourcePage = ref?.source_page;
  return [lessonKind, sourceTitle, sourceYear ? String(sourceYear) : "", section, sourcePage ? `P${sourcePage}` : ""]
    .map((item) => String(item || "").trim())
    .filter(Boolean);
}

function formatObservationTime(value) {
  if (!value) return "尚未观测";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

function latestHistoryStatus(items = []) {
  return String((items || [])[0]?.status || "").trim().toLowerCase();
}

function replayHealthTone(status = "") {
  if (status === "success") return "ok";
  if (status === "error") return "bad";
  return "neutral";
}

function replayHealthLabel(status = "") {
  if (status === "success") return "Replay 正常";
  if (status === "error") return "Replay 抖动";
  return "Replay 待观测";
}

function updateReplayScope(setReplayScope, patch) {
  setReplayScope?.((prev) => ({
    ...(prev || {}),
    projectionRef: "",
    handoffRef: "",
    targetServiceRef: prev?.targetServiceRef || "",
    artifactLookupRef: "",
    evidenceLookupRef: "",
    ...patch,
  }));
}

export default function FlowTransparencyPanel({
  workflowTrace,
  workflowProgress,
  contextProjections,
  memoryHandoffs,
  replayScope,
  setReplayScope,
  replaySourceUpdatedAt,
  replaySourceHistory,
}) {
  const projectionRows = buildProjectionRows(contextProjections);
  const plannerEvidenceCards = buildPlannerEvidenceCards(contextProjections);
  const reflectionReplayCount = ["generation", "audit"].reduce((sum, key) => {
    const cards = contextProjections?.[key]?.cards || [];
    return sum + cards.filter((item) => item?.card_type === "reflection_memory").length;
  }, 0);
  const replayObservationSources = [
    {
      id: "drilldown",
      label: "关系聚合",
      updatedAt: replaySourceUpdatedAt?.drilldown || "",
      status: latestHistoryStatus(replaySourceHistory?.drilldown || []),
    },
    {
      id: "events",
      label: "事件列表",
      updatedAt: replaySourceUpdatedAt?.events || "",
      status: latestHistoryStatus(replaySourceHistory?.events || []),
    },
    {
      id: "snapshots",
      label: "快照列表",
      updatedAt: replaySourceUpdatedAt?.snapshots || "",
      status: latestHistoryStatus(replaySourceHistory?.snapshots || []),
    },
  ];
  const latestReplayObservationAt = replayObservationSources
    .map((item) => String(item.updatedAt || "").trim())
    .filter(Boolean)
    .sort()
    .slice(-1)[0] || "";
  const overallReplayStatus = replayObservationSources.some((item) => item.status === "error")
    ? "error"
    : replayObservationSources.some((item) => item.status === "success")
      ? "success"
      : "";

  function toggleProjection(projectionRef) {
    const normalized = String(projectionRef || "").trim();
    updateReplayScope(setReplayScope, {
      projectionRef: replayScope?.projectionRef === normalized ? "" : normalized,
      handoffRef: "",
    });
  }

  function toggleHandoff(handoffId) {
    const normalized = String(handoffId || "").trim();
    updateReplayScope(setReplayScope, {
      projectionRef: "",
      handoffRef: replayScope?.handoffRef === normalized ? "" : normalized,
    });
  }

  function toggleStage(stageRef) {
    const normalized = String(stageRef || "").trim();
    if (!normalized) return;
    setReplayScope?.((prev) => ({
      ...(prev || {}),
      stageRef: prev?.stageRef === normalized ? "" : normalized,
    }));
  }

  return (
    <Panel
      title="流程透明化与上下文窗口"
      subtitle="这一块直接消费后端的 workflow trace、独立上下文窗口和结构化交接包，并与本地 replay 深钻共享同一套 ref 焦点。"
    >
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="流程节点" value={workflowTrace?.length || 0} />
        <MetricCard label="上下文窗口" value={Object.keys(contextProjections || {}).length} />
        <MetricCard label="交接包" value={(memoryHandoffs || []).length} />
        <MetricCard label="反思回灌卡" value={reflectionReplayCount} />
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">LangGraph 主线</p>
          <TagPill tone="ok">后端真实 workflow_trace</TagPill>
          <TagPill tone={replayHealthTone(overallReplayStatus)}>{replayHealthLabel(overallReplayStatus)}</TagPill>
          <ReplayFocusPill kind="stageRef" value={replayScope?.stageRef} active />
          <ReplayFocusPill kind="projectionRef" value={replayScope?.projectionRef} active />
          <ReplayFocusPill kind="handoffRef" value={replayScope?.handoffRef} active />
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-3">
          {replayObservationSources.map((item) => (
            <div key={`observation-${item.id}`} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-black text-slate-900">{item.label}</p>
                <TagPill tone={replayHealthTone(item.status)}>{replayHealthLabel(item.status)}</TagPill>
              </div>
              <p className="mt-2 text-xs text-slate-500">{`最近观测 ${formatObservationTime(item.updatedAt)}`}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-5">
          {(workflowProgress || []).map((item, index) => {
            const activeStage = replayScope?.stageRef === item.phase;
            return (
            <button
              type="button"
              key={`${item.phase}-${index}`}
              onClick={() => toggleStage(item.phase)}
              className={cn(
                "rounded-xl border px-3 py-3 text-left transition focus:outline-none focus:ring-2 focus:ring-sky-300",
                activeStage ? "border-sky-400 bg-sky-50 shadow-sm" : "border-slate-200 bg-slate-50 hover:bg-white"
              )}
            >
              <div className="flex flex-wrap items-center gap-2">
                <TagPill tone={item.done ? "ok" : "warn"}>{item.done ? "已完成" : "待补齐"}</TagPill>
                <TagPill tone="neutral">{item.owner}</TagPill>
                <TagPill tone={replayHealthTone(overallReplayStatus)}>{replayHealthLabel(overallReplayStatus)}</TagPill>
                {activeStage ? <TagPill tone="ok">Replay 阶段焦点</TagPill> : null}
              </div>
              <p className="mt-2 text-sm font-bold text-slate-900">{item.label}</p>
              <p className="mt-1 text-xs text-slate-500">{item.phase}</p>
              <p className="mt-2 text-xs text-slate-500">{`Replay 观测 ${formatObservationTime(latestReplayObservationAt)}`}</p>
            </button>
          );
          })}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        {projectionRows.map((item) => {
          const projection = item.projection || {};
          const cardTypes = uniqueCardTypes(projection?.cards || []).slice(0, 4);
          const active = Boolean(item.projectionRef) && replayScope?.projectionRef === item.projectionRef;
          return (
            <button
              key={`projection-${item.key}`}
              type="button"
              onClick={() => toggleProjection(item.projectionRef)}
              className={`rounded-2xl border p-4 text-left transition focus:outline-none focus:ring-2 focus:ring-sky-300 ${
                active
                  ? "border-sky-400 bg-sky-50 shadow-sm"
                  : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-black text-slate-900">{item.descriptor.label}</p>
                <TagPill tone={projection?.agent_id ? "ok" : "warn"}>{projection?.agent_id || "窗口未接入"}</TagPill>
                <TagPill tone="neutral">{item.descriptor.owner}</TagPill>
                {active ? <TagPill tone="ok">已联动 Replay</TagPill> : null}
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-700">{summarizeObjective(projection?.objective)}</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <MetricCard label="约束" value={(projection?.constraints || []).length} />
                <MetricCard label="卡片" value={(projection?.cards || []).length} />
                <MetricCard label="工件引用" value={(projection?.artifact_refs || []).length} />
                <MetricCard label="证据引用" value={(projection?.evidence_refs || []).length} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {item.projectionRef ? <TagPill tone={active ? "ok" : "neutral"}>{item.projectionRef}</TagPill> : null}
                {cardTypes.length === 0 ? <TagPill tone="neutral">暂无卡片类型</TagPill> : null}
                {cardTypes.map((cardType) => (
                  <TagPill key={`${item.key}-${cardType}`} tone="neutral">
                    {cardType}
                  </TagPill>
                ))}
                {projection?.token_budget_hint ? <TagPill tone="warn">{`预算 ${projection.token_budget_hint}`}</TagPill> : null}
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">攻击规划证据卡</p>
            <TagPill tone={plannerEvidenceCards.length ? "ok" : "warn"}>
              {plannerEvidenceCards.length ? `${plannerEvidenceCards.length} 张` : "暂无命中"}
            </TagPill>
          </div>
          <div className="mt-3 space-y-3">
            {plannerEvidenceCards.length === 0 ? (
              <p className="text-sm text-slate-500">
                当前 attack_planning projection 中还没有 `attack_planner_evidence` 卡片。
              </p>
            ) : null}
            {plannerEvidenceCards.map((card, index) => {
              const payload = card?.payload || {};
              const filters = payload?.applied_filters || {};
              const evidenceRefs = Array.isArray(card?.evidence_refs) ? card.evidence_refs : [];
              return (
                <div key={`planner-evidence-${index}`} className="rounded-xl border border-sky-200 bg-sky-50 px-3 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <TagPill tone="ok">{payload?.planning_mode || "baseline"}</TagPill>
                    <TagPill tone="neutral">{payload?.backend || "--"}</TagPill>
                    <TagPill tone="neutral">{`命中 ${payload?.hit_count ?? 0}`}</TagPill>
                    {filters?.target_template_id ? <TagPill tone="warn">{filters.target_template_id}</TagPill> : null}
                  </div>
                  <p className="mt-2 text-sm text-slate-800">{summarizeObjective(payload?.query)}</p>
                  <p className="mt-2 text-xs text-slate-500">
                    {`fallback=${filters?.planner_retrieval_fallback || "--"} | attack_surface=${
                      filters?.attack_surface_kind || "--"
                    }`}
                  </p>
                  <div className="mt-3 space-y-2">
                    {evidenceRefs.length === 0 ? (
                      <p className="text-xs text-slate-500">当前卡片没有附带 evidence_refs。</p>
                    ) : null}
                    {evidenceRefs.map((ref) => {
                      const tags = summarizeEvidenceSource(ref);
                      return (
                        <div
                          key={ref?.chunk_id || ref?.doc_id || ref?.title}
                          className="rounded-lg border border-white/80 bg-white/80 px-3 py-2"
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-sm font-semibold text-slate-900">{ref?.title || ref?.chunk_id || "--"}</p>
                            {typeof ref?.score === "number" ? (
                              <TagPill tone="neutral">{`score ${ref.score.toFixed(2)}`}</TagPill>
                            ) : null}
                          </div>
                          <p className="mt-1 text-xs leading-5 text-slate-600">
                            {summarizeObjective(ref?.snippet || "当前证据暂未提供摘要片段。")}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {tags.length === 0 ? <TagPill tone="neutral">来源信息待补充</TagPill> : null}
                            {tags.slice(0, 5).map((tag) => (
                              <TagPill key={`${ref?.chunk_id || ref?.doc_id}-${tag}`} tone="neutral">
                                {tag}
                              </TagPill>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">结构化交接包</p>
            <TagPill tone="ok">{`${(memoryHandoffs || []).length} 条`}</TagPill>
          </div>
          <div className="mt-3 space-y-2">
            {(memoryHandoffs || []).length === 0 ? (
              <p className="text-sm text-slate-500">当前运行尚未返回 memory_handoffs。</p>
            ) : null}
            {(memoryHandoffs || []).slice(0, 8).map((item) => {
              const active = replayScope?.handoffRef === item?.handoff_id;
              const projectionRef = deriveProjectionRef(item?.projection, item?.to_agent || item?.from_agent || "");
              return (
                <button
                  key={item?.handoff_id || `${item?.from_agent}-${item?.to_agent}`}
                  type="button"
                  onClick={() => toggleHandoff(item?.handoff_id)}
                  className={`w-full rounded-xl border px-3 py-3 text-left transition focus:outline-none focus:ring-2 focus:ring-amber-300 ${
                    active
                      ? "border-amber-400 bg-amber-50 shadow-sm"
                      : "border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <TagPill tone="neutral">{item?.from_agent || "--"}</TagPill>
                    <span className="text-xs font-semibold text-slate-400">→</span>
                    <TagPill tone="warn">{item?.to_agent || "--"}</TagPill>
                    <SemanticPill kind="status" value={item?.status} label={item?.status_label} />
                    {active ? <TagPill tone="warn">已联动 Replay</TagPill> : null}
                  </div>
                  <p className="mt-2 text-sm text-slate-800">{summarizeObjective(item?.objective)}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <TagPill tone="neutral">{`卡片 ${(item?.cards || []).length}`}</TagPill>
                    <TagPill tone="neutral">{`工件 ${(item?.artifact_refs || []).length}`}</TagPill>
                    <TagPill tone="neutral">{`证据 ${(item?.evidence_refs || []).length}`}</TagPill>
                    {projectionRef ? <TagPill tone={active ? "warn" : "ok"}>{projectionRef}</TagPill> : null}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </Panel>
  );
}
