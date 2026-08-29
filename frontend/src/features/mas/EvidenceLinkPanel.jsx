import { useMemo } from "react";
import { Panel } from "../../components/Panel";
import { SemanticPill, TagPill } from "../../components/SemanticPill";
import { buildEvidenceSignals } from "./evidenceHelpers";
import ClosurePanelLead from "./ClosurePanelLead";
import { PillButton, ReplayFocusButton, ReplayFocusPill } from "./ReplayFocusPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function normalizeRef(value) {
  return String(value || "").trim();
}

export default function EvidenceLinkPanel({
  selectedEvidence,
  linkedRounds,
  linkedRecommendations,
  linkedDeliveryFragments,
  replayEvidenceContext,
  replayScope,
  onFocusReplayEvent,
  onFocusReplaySnapshot,
  onFocusReplayHandoff,
  onFocusReplayRun,
  onFocusReplayStage,
  onFocusReplayArtifact,
  selectedDeliveryFragmentId,
  onFocusDeliveryFragment,
  onJumpToSection,
}) {
  const evidenceSignals = useMemo(() => buildEvidenceSignals(selectedEvidence).slice(0, 10), [selectedEvidence]);
  const selectedRunId = normalizeRef(replayScope?.runId);
  const selectedStageRef = normalizeRef(replayScope?.stageRef);
  const selectedArtifactRef = normalizeRef(replayScope?.artifactLookupRef);

  return (
    <Panel
      title="证据联动解读"
      subtitle="查看证据影响到的审计轮次、整改建议和交付片段。"
      className="xl:col-span-2"
    >
      <ClosurePanelLead
        eyebrow="收口模块"
        title="查看证据联动"
        detail="查看证据与回放、审计和交付的关联。"
        statusLabel={selectedEvidence ? "当前证据已进入联动区" : "等待选择证据"}
        statusTone={selectedEvidence ? "ok" : "neutral"}
        nextLabel="下一步建议"
        nextDetail="继续查看最终交付。"
        actionLabel="跳到最终交付"
        onAction={() => onJumpToSection?.("reports-section-delivery")}
        accent="emerald"
      />

      {!selectedEvidence ? (
        <div className="rounded-[24px] border border-dashed border-slate-300 bg-white/80 px-4 py-8 text-center text-sm text-slate-500">
          先选择一条证据卡。
        </div>
      ) : (
        <>
          <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,rgba(255,252,245,0.96),rgba(255,255,255,0.96))] p-4 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="ok">{selectedEvidence.doc_type || "证据"}</TagPill>
              {selectedEvidence?.metadata?.clause_code ? (
                <TagPill tone="ok">{`条款 ${selectedEvidence.metadata.clause_code}`}</TagPill>
              ) : null}
              <TagPill tone="neutral">{`相关度 ${selectedEvidence.score ?? "--"}`}</TagPill>
              {replayEvidenceContext?.replayFocused ? <TagPill tone="warn">当前回放焦点</TagPill> : null}
            </div>
            <h3 className="mt-3 text-base font-black text-slate-900">{selectedEvidence.title || "--"}</h3>
            <p className="mt-1 text-sm font-semibold text-slate-700">{selectedEvidence.section || "未命中章节"}</p>
            <p className="mt-3 text-sm leading-6 text-slate-700">{selectedEvidence.snippet || "暂无证据摘要。"}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {evidenceSignals.map((item) => (
                <TagPill key={item} tone="neutral">
                  {item}
                </TagPill>
              ))}
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-4">
            <div className="rounded-[20px] border border-slate-200 bg-white p-4">
              <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">回放命中</p>
              <p className="mt-2 text-lg font-black text-slate-950">
                {(replayEvidenceContext?.matchedEvents?.length || 0) +
                  (replayEvidenceContext?.matchedSnapshots?.length || 0) +
                  (replayEvidenceContext?.matchedHandoffs?.length || 0)}
              </p>
              <p className="mt-2 text-xs leading-5 text-slate-600">查看这条证据进入了多少个回放节点。</p>
            </div>
            <div className="rounded-[20px] border border-slate-200 bg-white p-4">
              <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">审计轮次</p>
              <p className="mt-2 text-lg font-black text-slate-950">{linkedRounds.length}</p>
              <p className="mt-2 text-xs leading-5 text-slate-600">查看这条依据影响了哪些审计判断。</p>
            </div>
            <div className="rounded-[20px] border border-slate-200 bg-white p-4">
              <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">整改建议</p>
              <p className="mt-2 text-lg font-black text-slate-950">{linkedRecommendations.length}</p>
              <p className="mt-2 text-xs leading-5 text-slate-600">查看这条证据影响的整改方向。</p>
            </div>
            <div className="rounded-[20px] border border-slate-200 bg-white p-4">
              <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">交付落点</p>
              <p className="mt-2 text-lg font-black text-slate-950">{linkedDeliveryFragments.length}</p>
              <p className="mt-2 text-xs leading-5 text-slate-600">查看这条依据沉淀到哪些交付片段。</p>
            </div>
          </div>

          <div className="mt-4 rounded-[24px] border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">回放命中路径</p>
              <TagPill tone="neutral">{`事件 ${replayEvidenceContext?.matchedEvents?.length || 0}`}</TagPill>
              <TagPill tone="neutral">{`快照 ${replayEvidenceContext?.matchedSnapshots?.length || 0}`}</TagPill>
              <TagPill tone="neutral">{`交接 ${replayEvidenceContext?.matchedHandoffs?.length || 0}`}</TagPill>
              <TagPill tone="warn">点击卡片可回跳定位</TagPill>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {replayEvidenceContext?.matchedEvents?.length ||
              replayEvidenceContext?.matchedSnapshots?.length ||
              replayEvidenceContext?.matchedHandoffs?.length
                ? "这条证据已进入本地回放链路。"
                : "当前回放深钻里还没有命中这条证据。"}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(replayEvidenceContext?.runIds || []).map((item) => (
                <PillButton
                  key={`replay-run-${item}`}
                  active={selectedRunId === normalizeRef(item)}
                  onClick={() => onFocusReplayRun?.(item)}
                  ringTone="focus:ring-sky-300"
                >
                  <TagPill tone={selectedRunId === normalizeRef(item) ? "ok" : "neutral"}>{item}</TagPill>
                </PillButton>
              ))}
              {(replayEvidenceContext?.stageRefs || []).map((item) => (
                <ReplayFocusButton
                  key={`replay-stage-${item}`}
                  kind="stageRef"
                  value={item}
                  active={selectedStageRef === normalizeRef(item)}
                  onClick={() => onFocusReplayStage?.(item)}
                  ringTone="focus:ring-amber-300"
                />
              ))}
              {(replayEvidenceContext?.artifactRefs || []).map((item) => (
                <PillButton
                  key={`replay-artifact-${item}`}
                  active={selectedArtifactRef === normalizeRef(item)}
                  onClick={() => onFocusReplayArtifact?.(item)}
                  ringTone="focus:ring-emerald-300"
                >
                  <TagPill tone={selectedArtifactRef === normalizeRef(item) ? "ok" : "neutral"}>{item}</TagPill>
                </PillButton>
              ))}
              {!(replayEvidenceContext?.runIds || []).length &&
              !(replayEvidenceContext?.stageRefs || []).length &&
              !(replayEvidenceContext?.artifactRefs || []).length ? (
                <TagPill tone="neutral">当前没有可解释的 replay 命中轨迹</TagPill>
              ) : null}
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-3">
              <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-black text-slate-900">事件命中</p>
                  <TagPill tone="neutral">{replayEvidenceContext?.matchedEvents?.length || 0}</TagPill>
                </div>
                <div className="mt-3 space-y-2">
                  {(replayEvidenceContext?.matchedEvents || []).length === 0 ? (
                    <p className="text-sm text-slate-500">当前没有事件直接引用这条证据。</p>
                  ) : null}
                  {(replayEvidenceContext?.matchedEvents || []).map((item) => (
                    <button
                      type="button"
                      key={item?.event_id || item?.created_at}
                      onClick={() => onFocusReplayEvent?.(item)}
                      className={cn(
                        "w-full rounded-[16px] border px-3 py-2 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-sky-300",
                        normalizeRef(replayScope?.projectionRef) === normalizeRef(item?.metadata?.projection_ref) ||
                          normalizeRef(replayScope?.handoffRef) === normalizeRef(item?.metadata?.handoff_ref)
                          ? "border-sky-300 bg-sky-50"
                          : "border-white/80 bg-white hover:bg-slate-100"
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <TagPill tone="warn">{item?.stage || "--"}</TagPill>
                        <ReplayFocusPill
                          kind="stageRef"
                          value={item?.stage}
                          active={selectedStageRef === normalizeRef(item?.stage)}
                        />
                        <TagPill tone="ok">{item?.event_kind || "--"}</TagPill>
                        {item?.run_id ? <TagPill tone="neutral">{item.run_id}</TagPill> : null}
                        {normalizeRef(replayScope?.projectionRef) === normalizeRef(item?.metadata?.projection_ref) ||
                        normalizeRef(replayScope?.handoffRef) === normalizeRef(item?.metadata?.handoff_ref) ? (
                          <TagPill tone="warn">已定位</TagPill>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm text-slate-700">{item?.summary || "当前事件没有摘要。"}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-black text-slate-900">快照命中</p>
                  <TagPill tone="neutral">{replayEvidenceContext?.matchedSnapshots?.length || 0}</TagPill>
                </div>
                <div className="mt-3 space-y-2">
                  {(replayEvidenceContext?.matchedSnapshots || []).length === 0 ? (
                    <p className="text-sm text-slate-500">当前没有 snapshot 直接带出这条证据。</p>
                  ) : null}
                  {(replayEvidenceContext?.matchedSnapshots || []).map((item) => (
                    <button
                      type="button"
                      key={item?.snapshot_id || item?.created_at}
                      onClick={() => onFocusReplaySnapshot?.(item)}
                      className={cn(
                        "w-full rounded-[16px] border px-3 py-2 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-sky-300",
                        normalizeRef(replayScope?.projectionRef) === normalizeRef(item?.projection_refs?.[0]) ||
                          normalizeRef(replayScope?.handoffRef) === normalizeRef(item?.handoff_refs?.[0])
                          ? "border-sky-300 bg-sky-50"
                          : "border-white/80 bg-white hover:bg-slate-100"
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        {item?.run_id ? <TagPill tone="neutral">{item.run_id}</TagPill> : null}
                        {item?.selected_proposal ? <TagPill tone="ok">{item.selected_proposal}</TagPill> : null}
                        <TagPill tone="warn">{`${(item?.workflow_trace || []).length} 个阶段片段`}</TagPill>
                        {normalizeRef(replayScope?.projectionRef) === normalizeRef(item?.projection_refs?.[0]) ||
                        normalizeRef(replayScope?.handoffRef) === normalizeRef(item?.handoff_refs?.[0]) ? (
                          <TagPill tone="warn">已定位</TagPill>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm text-slate-700">{item?.summary || "当前快照没有摘要。"}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-black text-slate-900">交接命中</p>
                  <TagPill tone="neutral">{replayEvidenceContext?.matchedHandoffs?.length || 0}</TagPill>
                </div>
                <div className="mt-3 space-y-2">
                  {(replayEvidenceContext?.matchedHandoffs || []).length === 0 ? (
                    <p className="text-sm text-slate-500">当前没有交接记录明确引用这条证据。</p>
                  ) : null}
                  {(replayEvidenceContext?.matchedHandoffs || []).map((item) => (
                    <button
                      type="button"
                      key={item?.relation_ref || item?.handoff_projection_ref}
                      onClick={() => onFocusReplayHandoff?.(item)}
                      className={cn(
                        "w-full rounded-[16px] border px-3 py-2 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-sky-300",
                        normalizeRef(replayScope?.handoffRef) === normalizeRef(item?.relation_ref)
                          ? "border-sky-300 bg-sky-50"
                          : "border-white/80 bg-white hover:bg-slate-100"
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <TagPill tone="neutral">{item?.source_agent_id || "--"}</TagPill>
                        <ReplayFocusPill
                          kind="handoffRef"
                          value={item?.relation_ref}
                          active={normalizeRef(replayScope?.handoffRef) === normalizeRef(item?.relation_ref)}
                          label={item?.target_agent_id || "--"}
                          hideWhenEmpty={false}
                        />
                        {normalizeRef(replayScope?.handoffRef) === normalizeRef(item?.relation_ref) ? (
                          <TagPill tone="warn">已定位</TagPill>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm text-slate-700">{`${item?.upstream_stage || "--"} -> ${item?.downstream_stage || "--"}`}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-3">
            <div className="rounded-[24px] border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-black text-slate-900">关联审计轮次</p>
                <TagPill tone="neutral">{linkedRounds.length}</TagPill>
              </div>
              <div className="mt-3 space-y-2">
                {linkedRounds.length === 0 ? <p className="text-sm text-slate-500">当前没有明显关联的审计轮次。</p> : null}
                {linkedRounds.map((round) => (
                  <div key={`${round.round}-${round.proposal_id}`} className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <TagPill tone="neutral">{`第 ${round.round} 轮`}</TagPill>
                      <TagPill tone="neutral">{round.proposal_id}</TagPill>
                      <SemanticPill kind="status" value={round.verdict} label={round.verdict_label} />
                    </div>
                    <p className="mt-2 text-xs leading-5 text-slate-600">
                      {[...(round.reasons || []), ...(round.key_findings || [])].slice(0, 2).join("；") || "暂无摘要。"}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-black text-slate-900">关联整改建议</p>
                <TagPill tone="neutral">{linkedRecommendations.length}</TagPill>
              </div>
              <div className="mt-3 space-y-2">
                {linkedRecommendations.length === 0 ? <p className="text-sm text-slate-500">当前没有明显关联的整改建议。</p> : null}
                {linkedRecommendations.map((item, idx) => (
                  <p key={`${idx}-${item}`} className="rounded-[18px] border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                    {idx + 1}. {item}
                  </p>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-black text-slate-900">关联交付片段</p>
                <TagPill tone="neutral">{linkedDeliveryFragments.length}</TagPill>
              </div>
              <div className="mt-3 space-y-2">
                {linkedDeliveryFragments.length === 0 ? <p className="text-sm text-slate-500">当前没有明显关联的交付片段。</p> : null}
                {linkedDeliveryFragments.map((item, idx) => (
                  <button
                    type="button"
                    key={`${idx}-${item.fragmentId || item.label}-${item.text}`}
                    onClick={() => onFocusDeliveryFragment?.(item)}
                    className={cn(
                      "w-full rounded-[18px] border px-3 py-3 text-left text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-300",
                      normalizeRef(selectedDeliveryFragmentId) === normalizeRef(item?.fragmentId)
                        ? "border-emerald-300 bg-emerald-100 text-emerald-950"
                        : "border-emerald-200 bg-emerald-50 text-emerald-900 hover:bg-emerald-100"
                    )}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <TagPill tone="ok">{item.label}</TagPill>
                      {normalizeRef(selectedDeliveryFragmentId) === normalizeRef(item?.fragmentId) ? (
                        <TagPill tone="warn">已定位</TagPill>
                      ) : null}
                    </div>
                    <p className="mt-2 leading-6">{item.text}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </Panel>
  );
}
