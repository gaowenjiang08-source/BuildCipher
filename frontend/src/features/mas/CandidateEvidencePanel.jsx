import { Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";
import ClosurePanelLead from "./ClosurePanelLead";
import { PillButton, ReplayFocusButton, ReplayFocusPill } from "./ReplayFocusPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function normalizeRef(value) {
  return String(value || "").trim();
}

function formatScore(score) {
  const value = Number(score);
  return Number.isFinite(value) ? value.toFixed(value >= 10 ? 1 : 2) : "--";
}

export default function CandidateEvidencePanel({
  selectedEvidence,
  candidateLinks,
  selectedProposalId,
  onSelectProposal,
  proposalReplayContext,
  replayScope,
  onFocusReplayEvent,
  onFocusReplaySnapshot,
  onFocusReplayHandoff,
  onFocusReplayRun,
  onFocusReplayStage,
  onFocusReplayArtifact,
  onJumpToSection,
}) {
  const selectedRunId = normalizeRef(replayScope?.runId);
  const selectedStageRef = normalizeRef(replayScope?.stageRef);
  const selectedArtifactRef = normalizeRef(replayScope?.artifactLookupRef);

  return (
    <Panel
      title="证据支持候选方案"
      subtitle="查看证据与候选方案的对应关系。"
      className="xl:col-span-2"
    >
      <ClosurePanelLead
        eyebrow="Closure Block"
        title="查看候选方案"
        detail="查看这条依据对应的 proposal。"
        statusLabel={selectedProposalId ? "当前 proposal 已锁定" : "等待锁定 proposal"}
        statusTone={selectedProposalId ? "ok" : "neutral"}
        nextLabel="下一步建议"
        nextDetail="继续查看最终交付。"
        actionLabel="跳到最终交付"
        onAction={() => onJumpToSection?.("reports-section-delivery")}
        accent="amber"
      />

      {!selectedEvidence ? (
        <div className="rounded-[24px] border border-dashed border-slate-300 bg-white/80 px-4 py-8 text-center text-sm text-slate-500">
          先选择一条证据卡。
        </div>
      ) : candidateLinks.length === 0 ? (
        <div className="rounded-[24px] border border-dashed border-slate-300 bg-white/80 px-4 py-8 text-center text-sm text-slate-500">
          当前证据还没有明显匹配到更受支持的候选方案，通常表示这条依据更偏向通用规范或模板约束。
        </div>
      ) : (
        <>
          <div className="rounded-[24px] border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">Proposal Replay Path</p>
              <TagPill tone="neutral">{selectedProposalId || "未锁定"}</TagPill>
              <TagPill tone="neutral">{`事件 ${proposalReplayContext?.matchedEvents?.length || 0}`}</TagPill>
              <TagPill tone="neutral">{`快照 ${proposalReplayContext?.matchedSnapshots?.length || 0}`}</TagPill>
              <TagPill tone="neutral">{`Handoff ${proposalReplayContext?.matchedHandoffs?.length || 0}`}</TagPill>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {selectedProposalId
                ? proposalReplayContext?.matchedEvents?.length ||
                  proposalReplayContext?.matchedSnapshots?.length ||
                  proposalReplayContext?.matchedHandoffs?.length
                  ? "当前 proposal 已命中 replay 记录。"
                  : "当前 replay 里暂无命中记录。"
                : "先锁定一个 proposal。"}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(proposalReplayContext?.runIds || []).map((item) => (
                <PillButton
                  key={`proposal-replay-run-${item}`}
                  active={selectedRunId === normalizeRef(item)}
                  onClick={() => onFocusReplayRun?.(item)}
                  ringTone="focus:ring-sky-300"
                >
                  <TagPill tone={selectedRunId === normalizeRef(item) ? "ok" : "neutral"}>{item}</TagPill>
                </PillButton>
              ))}
              {(proposalReplayContext?.stageRefs || []).map((item) => (
                <ReplayFocusButton
                  key={`proposal-replay-stage-${item}`}
                  kind="stageRef"
                  value={item}
                  active={selectedStageRef === normalizeRef(item)}
                  onClick={() => onFocusReplayStage?.(item)}
                  ringTone="focus:ring-amber-300"
                />
              ))}
              {(proposalReplayContext?.artifactRefs || []).map((item) => (
                <PillButton
                  key={`proposal-replay-artifact-${item}`}
                  active={selectedArtifactRef === normalizeRef(item)}
                  onClick={() => onFocusReplayArtifact?.(item)}
                  ringTone="focus:ring-emerald-300"
                >
                  <TagPill tone={selectedArtifactRef === normalizeRef(item) ? "ok" : "neutral"}>{item}</TagPill>
                </PillButton>
              ))}
              {!(proposalReplayContext?.runIds || []).length &&
              !(proposalReplayContext?.stageRefs || []).length &&
              !(proposalReplayContext?.artifactRefs || []).length ? (
                <TagPill tone="neutral">当前没有可回跳的 proposal replay 定位线索</TagPill>
              ) : null}
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-3">
              <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-black text-slate-900">事件命中</p>
                  <TagPill tone="neutral">{proposalReplayContext?.matchedEvents?.length || 0}</TagPill>
                </div>
                <div className="mt-3 space-y-2">
                  {(proposalReplayContext?.matchedEvents || []).length === 0 ? (
                    <p className="text-sm text-slate-500">当前没有 replay 事件明显命中这条 proposal。</p>
                  ) : null}
                  {(proposalReplayContext?.matchedEvents || []).map((item) => (
                    <button
                      type="button"
                      key={item?.event_id || item?.created_at}
                      onClick={() => onFocusReplayEvent?.(item)}
                      className="w-full rounded-[16px] border border-white/80 bg-white px-3 py-2 text-left transition-colors hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-300"
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
                      </div>
                      <p className="mt-2 text-sm text-slate-700">{item?.summary || "当前事件没有摘要。"}</p>
                    </button>
                  ))}
                </div>
              </div>
              <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-black text-slate-900">快照命中</p>
                  <TagPill tone="neutral">{proposalReplayContext?.matchedSnapshots?.length || 0}</TagPill>
                </div>
                <div className="mt-3 space-y-2">
                  {(proposalReplayContext?.matchedSnapshots || []).length === 0 ? (
                    <p className="text-sm text-slate-500">当前没有 replay 快照明显命中这条 proposal。</p>
                  ) : null}
                  {(proposalReplayContext?.matchedSnapshots || []).map((item) => (
                    <button
                      type="button"
                      key={item?.snapshot_id || item?.created_at}
                      onClick={() => onFocusReplaySnapshot?.(item)}
                      className="w-full rounded-[16px] border border-white/80 bg-white px-3 py-2 text-left transition-colors hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-300"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        {item?.run_id ? <TagPill tone="neutral">{item.run_id}</TagPill> : null}
                        {item?.selected_proposal ? <TagPill tone="ok">{item.selected_proposal}</TagPill> : null}
                        <TagPill tone="warn">{`${(item?.workflow_trace || []).length} 个阶段片段`}</TagPill>
                      </div>
                      <p className="mt-2 text-sm text-slate-700">{item?.summary || "当前快照没有摘要。"}</p>
                    </button>
                  ))}
                </div>
              </div>
              <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-black text-slate-900">Handoff 命中</p>
                  <TagPill tone="neutral">{proposalReplayContext?.matchedHandoffs?.length || 0}</TagPill>
                </div>
                <div className="mt-3 space-y-2">
                  {(proposalReplayContext?.matchedHandoffs || []).length === 0 ? (
                    <p className="text-sm text-slate-500">当前没有 handoff 明显命中这条 proposal。</p>
                  ) : null}
                  {(proposalReplayContext?.matchedHandoffs || []).map((item) => (
                    <button
                      type="button"
                      key={item?.relation_ref || item?.handoff_projection_ref}
                      onClick={() => onFocusReplayHandoff?.(item)}
                      className="w-full rounded-[16px] border border-white/80 bg-white px-3 py-2 text-left transition-colors hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-300"
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
                      </div>
                      <p className="mt-2 text-sm text-slate-700">{`${item?.upstream_stage || "--"} -> ${item?.downstream_stage || "--"}`}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
            {candidateLinks.map((item) => (
              <button
                type="button"
                key={item.proposalId || item.name}
                onClick={() => onSelectProposal?.(item.proposalId)}
                className={cn(
                  "w-full rounded-[26px] border bg-white p-4 text-left shadow-[0_10px_30px_rgba(15,23,42,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_34px_rgba(15,23,42,0.1)]",
                  item.selected || item.proposalId === selectedProposalId ? "border-emerald-300 ring-1 ring-emerald-200" : "border-slate-200"
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <TagPill tone={item.selected ? "ok" : "neutral"}>{item.proposalId || "proposal"}</TagPill>
                  <TagPill tone="neutral">{`支持度 ${formatScore(item.score)}`}</TagPill>
                  {item.schemeType ? <TagPill tone="neutral">{item.schemeType}</TagPill> : null}
                  {item.selected ? <TagPill tone="ok">当前已选</TagPill> : null}
                  {item.proposalId === selectedProposalId ? <TagPill tone="ok">跨页联动焦点</TagPill> : null}
                </div>

                <h3 className="mt-3 text-base font-black text-slate-900">{item.name}</h3>
                {item.architecturePattern ? <p className="mt-1 text-sm font-semibold text-slate-700">{item.architecturePattern}</p> : null}
                <p className="mt-3 text-sm leading-6 text-slate-700">
                  {item.candidate?.design_rationale || "暂无设计理由。"}
                </p>

                <div className="mt-3 flex flex-wrap gap-2">
                  {(item.componentHits || []).length === 0 ? (
                    <TagPill tone="neutral">当前未匹配到明显组件命中</TagPill>
                  ) : (
                    item.componentHits.map((component) => (
                      <TagPill key={`${item.proposalId}-${component}`} tone="warn">
                        {component}
                      </TagPill>
                    ))
                  )}
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </Panel>
  );
}
