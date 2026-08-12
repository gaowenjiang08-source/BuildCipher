import { useEffect, useMemo, useState } from "react";
import { MetricCard, Panel } from "../../components/Panel";
import { SemanticPill, TagPill } from "../../components/SemanticPill";
import { PillButton, ReplayFocusPill } from "./ReplayFocusPill";

function summarizeText(value = "", maxLength = 140) {
  const text = String(value || "").trim();
  if (!text) return "--";
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

function collectProjectionArtifacts(contextProjections = {}) {
  return Object.entries(contextProjections || {}).flatMap(([key, projection]) =>
    (projection?.artifact_refs || []).map((item) => ({
      projectionKey: key,
      projectionRef: deriveProjectionRef(projection, key),
      ...item,
    }))
  );
}

function summarizeEvidenceSource(ref = {}) {
  const metadata = ref?.metadata || {};
  return [
    metadata?.lesson_kind,
    metadata?.source_title,
    metadata?.source_year ? String(metadata.source_year) : "",
    ref?.section,
    ref?.source_page ? `P${ref.source_page}` : "",
  ]
    .map((item) => String(item || "").trim())
    .filter(Boolean);
}

function deriveArtifactLookupRef(item = {}) {
  return String(item?.lookup_ref || item?.artifact_lookup_ref || item?.artifact_id || item?.title || "").trim();
}

function deriveEvidenceLookupRef(item = {}) {
  return String(item?.lookup_ref || item?.evidence_lookup_ref || item?.chunk_id || item?.doc_id || "").trim();
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

export default function HandoffArtifactPanel({
  memoryHandoffs,
  contextProjections,
  replayScope,
  setReplayScope,
}) {
  const handoffs = Array.isArray(memoryHandoffs) ? memoryHandoffs : [];
  const [selectedHandoffId, setSelectedHandoffId] = useState("");

  useEffect(() => {
    const externalFocus = String(replayScope?.handoffRef || "").trim();
    if (!externalFocus) return;
    if (handoffs.some((item) => item?.handoff_id === externalFocus)) {
      setSelectedHandoffId(externalFocus);
    }
  }, [handoffs, replayScope?.handoffRef]);

  useEffect(() => {
    if (handoffs.length === 0) {
      setSelectedHandoffId("");
      return;
    }
    if (!handoffs.some((item) => item?.handoff_id === selectedHandoffId)) {
      setSelectedHandoffId(handoffs[handoffs.length - 1]?.handoff_id || "");
    }
  }, [handoffs, selectedHandoffId]);

  const selectedHandoff = useMemo(() => {
    return handoffs.find((item) => item?.handoff_id === selectedHandoffId) || handoffs[handoffs.length - 1] || null;
  }, [handoffs, selectedHandoffId]);

  const projectionArtifacts = useMemo(() => collectProjectionArtifacts(contextProjections), [contextProjections]);
  const selectedProjectionRef = useMemo(
    () => deriveProjectionRef(selectedHandoff?.projection, selectedHandoff?.to_agent || selectedHandoff?.from_agent || ""),
    [selectedHandoff]
  );

  function selectHandoff(handoffId) {
    const normalized = String(handoffId || "").trim();
    setSelectedHandoffId(normalized);
    updateReplayScope(setReplayScope, {
      projectionRef: "",
      handoffRef: replayScope?.handoffRef === normalized ? "" : normalized,
    });
  }

  function focusProjection(projectionRef) {
    const normalized = String(projectionRef || "").trim();
    if (!normalized) return;
    updateReplayScope(setReplayScope, {
      projectionRef: replayScope?.projectionRef === normalized ? "" : normalized,
      handoffRef: "",
    });
  }

  function focusArtifact(artifactRef) {
    const normalized = String(artifactRef || "").trim();
    if (!normalized) return;
    updateReplayScope(setReplayScope, {
      artifactLookupRef: replayScope?.artifactLookupRef === normalized ? "" : normalized,
      evidenceLookupRef: "",
    });
  }

  function focusEvidence(evidenceRef) {
    const normalized = String(evidenceRef || "").trim();
    if (!normalized) return;
    updateReplayScope(setReplayScope, {
      artifactLookupRef: "",
      evidenceLookupRef: replayScope?.evidenceLookupRef === normalized ? "" : normalized,
    });
  }

  return (
    <Panel
      title="Handoff 与工件深钻"
      subtitle="这一块用于解释独立上下文窗口之间到底传了什么，并把 handoff 与 replay drilldown 选中态联动到同一套 ref。"
    >
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="交接包" value={handoffs.length} />
        <MetricCard label="卡片总量" value={handoffs.reduce((sum, item) => sum + (item?.cards?.length || 0), 0)} />
        <MetricCard label="工件引用" value={projectionArtifacts.length} />
        <MetricCard label="当前窗口" value={selectedHandoff?.projection?.agent_id || "--"} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">交接链路</p>
            <TagPill tone="neutral">{`${handoffs.length} 条`}</TagPill>
            <ReplayFocusPill kind="handoffRef" value={replayScope?.handoffRef} active />
            {replayScope?.artifactLookupRef ? (
              <TagPill tone="neutral">{`工件 ${replayScope.artifactLookupRef}`}</TagPill>
            ) : null}
            {replayScope?.evidenceLookupRef ? <TagPill tone="ok">{`证据 ${replayScope.evidenceLookupRef}`}</TagPill> : null}
          </div>
          <div className="mt-3 space-y-2">
            {handoffs.length === 0 ? <p className="text-sm text-slate-500">当前没有可用的 memory handoff。</p> : null}
            {handoffs.map((item) => {
              const active = item?.handoff_id === selectedHandoff?.handoff_id;
              const replayActive = item?.handoff_id === replayScope?.handoffRef;
              const projectionRef = deriveProjectionRef(item?.projection, item?.to_agent || item?.from_agent || "");
              return (
                <button
                  key={item?.handoff_id || `${item?.from_agent}-${item?.to_agent}`}
                  type="button"
                  onClick={() => selectHandoff(item?.handoff_id || "")}
                  className={`w-full rounded-xl border px-3 py-3 text-left transition focus:outline-none focus:ring-2 focus:ring-sky-300 ${
                    replayActive || active
                      ? "border-sky-300 bg-sky-50"
                      : "border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <TagPill tone="neutral">{item?.from_agent || "--"}</TagPill>
                    <span className="text-xs font-semibold text-slate-400">→</span>
                    <TagPill tone="warn">{item?.to_agent || "--"}</TagPill>
                    <SemanticPill kind="status" value={item?.status} label={item?.status_label} />
                    {replayActive ? <TagPill tone="ok">Replay 对齐</TagPill> : null}
                  </div>
                  <p className="mt-2 text-sm font-semibold text-slate-800">
                    {summarizeText(item?.objective || "当前交接包未提供 objective。", 80)}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <TagPill tone="neutral">{`卡片 ${item?.cards?.length || 0}`}</TagPill>
                    <TagPill tone="neutral">{`工件 ${item?.artifact_refs?.length || 0}`}</TagPill>
                    <TagPill tone="neutral">{`证据 ${item?.evidence_refs?.length || 0}`}</TagPill>
                    <ReplayFocusPill
                      kind="projectionRef"
                      value={projectionRef}
                      active={replayScope?.projectionRef === projectionRef}
                    />
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">当前交接包详情</p>
              {selectedHandoff?.projection?.agent_id ? <TagPill tone="ok">{selectedHandoff.projection.agent_id}</TagPill> : null}
              {selectedHandoff?.handoff_id ? <TagPill tone="neutral">{selectedHandoff.handoff_id}</TagPill> : null}
            </div>
            {selectedHandoff ? (
              <>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  {selectedHandoff.objective || "当前交接包没有额外 objective。"}
                </p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <MetricCard label="约束" value={selectedHandoff?.projection?.constraints?.length || 0} />
                  <MetricCard label="窗口卡片" value={selectedHandoff?.projection?.cards?.length || 0} />
                  <MetricCard label="工件引用" value={selectedHandoff?.artifact_refs?.length || 0} />
                  <MetricCard label="证据引用" value={selectedHandoff?.evidence_refs?.length || 0} />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {selectedProjectionRef ? (
                    <PillButton
                      active={replayScope?.projectionRef === selectedProjectionRef}
                      onClick={() => focusProjection(selectedProjectionRef)}
                      ringTone="focus:ring-emerald-300"
                    >
                      {replayScope?.projectionRef === selectedProjectionRef
                        ? `已按 Projection ${selectedProjectionRef} 深钻`
                        : `按 Projection ${selectedProjectionRef} 深钻`}
                    </PillButton>
                  ) : null}
                </div>
              </>
            ) : (
              <p className="mt-2 text-sm text-slate-500">请选择一条 handoff 查看详情。</p>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-sm font-black text-slate-900">卡片内容</p>
            <div className="mt-3 space-y-2">
              {(selectedHandoff?.cards || []).length === 0 ? <p className="text-sm text-slate-500">当前 handoff 没有附带卡片。</p> : null}
              {(selectedHandoff?.cards || []).slice(0, 6).map((item, index) => (
                <div key={`${item?.card_id || item?.card_type}-${index}`} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <TagPill tone="warn">{item?.card_type || "--"}</TagPill>
                    {item?.source_agent ? <TagPill tone="neutral">{item.source_agent}</TagPill> : null}
                    {item?.priority_label ? <TagPill tone="neutral">{item.priority_label}</TagPill> : null}
                  </div>
                  <p className="mt-2 text-sm text-slate-800">{item?.summary || "当前卡片没有摘要。"}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-sm font-black text-slate-900">工件与证据引用</p>
            <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-2">
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">工件引用</p>
                {(selectedHandoff?.artifact_refs || []).length === 0 ? <p className="text-sm text-slate-500">当前 handoff 没有工件引用。</p> : null}
                {(selectedHandoff?.artifact_refs || []).slice(0, 6).map((item, index) => (
                  <div key={`${item?.artifact_id || item?.title}-${index}`} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-slate-900">{item?.title || item?.artifact_id || "--"}</p>
                      <TagPill tone="neutral">{item?.artifact_type || "generic"}</TagPill>
                      {deriveArtifactLookupRef(item) ? (
                        <PillButton
                          active={replayScope?.artifactLookupRef === deriveArtifactLookupRef(item)}
                          onClick={() => focusArtifact(deriveArtifactLookupRef(item))}
                          ringTone="focus:ring-emerald-300"
                        >
                          <TagPill tone={replayScope?.artifactLookupRef === deriveArtifactLookupRef(item) ? "ok" : "warn"}>
                            {replayScope?.artifactLookupRef === deriveArtifactLookupRef(item)
                              ? "已按工件深钻"
                              : deriveArtifactLookupRef(item)}
                          </TagPill>
                        </PillButton>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm text-slate-700">{summarizeText(item?.summary || "当前工件没有摘要。", 180)}</p>
                    {item?.metadata?.diff_preview ? (
                      <pre className="mt-2 overflow-auto rounded-lg border border-slate-200 bg-white p-2 text-[11px] text-slate-700">
                        {String(item.metadata.diff_preview)}
                      </pre>
                    ) : null}
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">证据引用</p>
                {(selectedHandoff?.evidence_refs || []).length === 0 ? <p className="text-sm text-slate-500">当前 handoff 没有证据引用。</p> : null}
                {(selectedHandoff?.evidence_refs || []).slice(0, 6).map((item, index) => {
                  const sourceTags = summarizeEvidenceSource(item);
                  return (
                    <div key={`${item?.chunk_id || item?.doc_id}-${index}`} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-slate-900">{item?.title || item?.chunk_id || "--"}</p>
                        {deriveEvidenceLookupRef(item) ? (
                          <PillButton
                            active={replayScope?.evidenceLookupRef === deriveEvidenceLookupRef(item)}
                            onClick={() => focusEvidence(deriveEvidenceLookupRef(item))}
                            ringTone="focus:ring-sky-300"
                          >
                            <TagPill tone={replayScope?.evidenceLookupRef === deriveEvidenceLookupRef(item) ? "ok" : "warn"}>
                              {replayScope?.evidenceLookupRef === deriveEvidenceLookupRef(item)
                                ? "已按证据深钻"
                                : deriveEvidenceLookupRef(item)}
                            </TagPill>
                          </PillButton>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm text-slate-700">{summarizeText(item?.snippet || "当前证据没有摘要片段。", 180)}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {sourceTags.length === 0 ? <TagPill tone="neutral">来源摘要待补充</TagPill> : null}
                        {sourceTags.slice(0, 5).map((tag) => (
                          <TagPill key={`${item?.chunk_id || item?.doc_id}-${tag}`} tone="neutral">
                            {tag}
                          </TagPill>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}
