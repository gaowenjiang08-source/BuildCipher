import { MetricCard, Panel } from "../../components/Panel";
import { SemanticPill, TagPill } from "../../components/SemanticPill";
import { ReplayFocusPill } from "./ReplayFocusPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function uniqueStrings(items = []) {
  return [...new Set((items || []).filter(Boolean).map((item) => String(item).trim()).filter(Boolean))];
}

function normalizeRef(value) {
  return String(value || "").trim();
}

function formatBytes(value) {
  const num = Number(value);
  if (!Number.isFinite(num) || num < 0) return "--";
  if (num < 1024) return `${num} B`;
  if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KB`;
  return `${(num / (1024 * 1024)).toFixed(1)} MB`;
}

function getRoundTargetService(round = {}) {
  const service = round?.target_service || {};
  const ref = normalizeRef(service?.service_id || service?.service_ref || round?.target_service_ref);
  return {
    ref,
    label: service?.service_name || service?.service_label || ref || "--",
    version: service?.service_version || "",
  };
}

function summarizeRound(round = {}) {
  const attackResults = Array.isArray(round?.attack_results) ? round.attack_results : [];
  const findings = uniqueStrings(attackResults.flatMap((item) => item?.findings || []));
  const txBytes = attackResults.reduce((sum, item) => sum + Number(item?.metrics?.tx_bytes || 0), 0);
  const rxBytes = attackResults.reduce((sum, item) => sum + Number(item?.metrics?.rx_bytes || 0), 0);
  const probeCount = attackResults.reduce((sum, item) => sum + Number(item?.metrics?.probe_count || 0), 0);
  const artifactCount = attackResults.reduce((sum, item) => sum + (item?.artifact_refs?.length || 0), 0);
  const firstMetrics = attackResults[0]?.metrics || {};
  const verdict = round?.vulnerability_verdict || {};
  const decision = round?.attack_decision || {};
  const targetService = getRoundTargetService(round);
  return {
    round,
    attackResults,
    findings,
    txBytes,
    rxBytes,
    probeCount,
    artifactCount,
    latencyP95: firstMetrics?.latency_p95_ms ?? "--",
    severity: verdict?.severity || "",
    severityLabel: verdict?.severity_label || verdict?.severity || "--",
    verdictSummary: verdict?.summary || "当前轮次暂无漏洞评估摘要。",
    decisionAction: decision?.action || "--",
    decisionLabel: decision?.action_label || decision?.action || "--",
    targetServiceRef: targetService.ref,
    targetServiceLabel: targetService.label,
    targetServiceVersion: targetService.version,
  };
}

function compareFindings(beforeItems = [], afterItems = []) {
  const beforeSet = new Set(beforeItems);
  const afterSet = new Set(afterItems);
  return {
    removed: beforeItems.filter((item) => !afterSet.has(item)),
    added: afterItems.filter((item) => !beforeSet.has(item)),
    retained: afterItems.filter((item) => beforeSet.has(item)),
  };
}

function severityRank(value = "") {
  const normalized = String(value || "").toLowerCase();
  const table = {
    critical: 4,
    high: 3,
    medium: 2,
    low: 1,
    info: 0,
    none: 0,
  };
  return table[normalized] ?? -1;
}

function buildRegressionTone(baseline, regression) {
  const before = severityRank(baseline?.severity);
  const after = severityRank(regression?.severity);
  if (before >= 0 && after >= 0) {
    if (after < before) {
      return {
        tone: "ok",
        label: "残余风险下降",
        summary: "回归严重度低于基线。",
      };
    }
    if (after > before) {
      return {
        tone: "bad",
        label: "残余风险上升",
        summary: "回归严重度高于基线，请复核补丁影响。",
      };
    }
  }
  return {
    tone: "warn",
    label: "仍需人工复核",
    summary: "风险下降信号不足。",
  };
}

function buildTargetFocusSummary(baseline, regression, focusedServiceRef) {
  if (!focusedServiceRef) {
    return {
      tone: "neutral",
      label: "未锁定目标服务",
      summary:
        "默认轮次对比。选中目标服务后显示两轮命中情况。",
    };
  }

  const matchedRounds = [baseline, regression].filter((item) => item?.targetServiceRef === focusedServiceRef);
  if (matchedRounds.length === 2) {
    return {
      tone: "ok",
      label: "已锁定同一目标服务",
      summary: `当前共享焦点为 ${focusedServiceRef}，基线轮与回归轮都命中了这条服务轨迹，适合直接对照修补前后的变化。`,
    };
  }
  if (matchedRounds.length === 1) {
    return {
      tone: "warn",
      label: "仅命中单轮目标服务",
      summary: `当前共享焦点为 ${focusedServiceRef}，但只在 ${matchedRounds[0]?.round?.round_kind_label || matchedRounds[0]?.round?.round_kind || "当前轮次"} 中找到对应服务，说明两轮对比对象还没有完全对齐。`,
    };
  }
  return {
    tone: "bad",
    label: "未命中当前对比轮次",
    summary: `当前共享焦点为 ${focusedServiceRef}，但基线轮与回归轮摘要里都没有该目标服务，建议回到关系回放轨迹面板确认是否切到了别的服务版本。`,
  };
}

function buildStageFocusSummary(focusedStageRef = "") {
  if (!focusedStageRef) {
    return {
      tone: "neutral",
      label: "未锁定流程阶段",
      summary: "默认轮次对比。选中阶段后显示对比归属。",
    };
  }

  if (["attack_executor", "vulnerability_evaluation", "patch_reflection"].includes(focusedStageRef)) {
    return {
      tone: "ok",
      label: "已对齐攻击闭环阶段",
      summary: `当前共享阶段焦点为 ${focusedStageRef}，它属于基线轮 / 回归轮对比的核心闭环阶段，可直接把该面板作为主解释视图。`,
    };
  }

  return {
    tone: "warn",
    label: "当前阶段不属于对比核心段",
    summary: `当前共享阶段焦点为 ${focusedStageRef}，但它更偏控制/上下文阶段，因此轮次对比只作为辅助观察，不是主命中视图。`,
  };
}

function RoundColumn({ title, tone, snapshot, focusedServiceRef, focusedStageRef, setReplayScope }) {
  const { round, findings } = snapshot;
  const active = Boolean(snapshot.targetServiceRef) && snapshot.targetServiceRef === focusedServiceRef;
  const stageActive = ["attack_executor", "vulnerability_evaluation", "patch_reflection"].includes(focusedStageRef);
  const clickable = Boolean(snapshot.targetServiceRef) && typeof setReplayScope === "function";

  function toggleTargetService() {
    if (!clickable) return;
    setReplayScope((prev) => ({
      ...(prev || {}),
      targetServiceRef: prev?.targetServiceRef === snapshot.targetServiceRef ? "" : snapshot.targetServiceRef,
    }));
  }

  return (
    <div
      className={cn(
        "rounded-2xl border bg-white p-4 transition",
        active ? "border-sky-400 bg-sky-50/40 shadow-sm" : "border-slate-200",
        clickable ? "cursor-pointer hover:border-sky-300" : ""
      )}
      onClick={clickable ? toggleTargetService : undefined}
    >
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-black text-slate-900">{title}</p>
        <TagPill tone={tone}>{round?.round_kind_label || round?.round_kind || "--"}</TagPill>
        <SemanticPill kind="status" value={round?.mode} label={round?.mode_label} />
        {active ? <TagPill tone="ok">共享焦点</TagPill> : null}
        {stageActive ? <TagPill tone="warn">{`阶段 ${focusedStageRef}`}</TagPill> : null}
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{round?.summary || "当前轮次暂无摘要。"}</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <MetricCard label="攻击结果" value={snapshot.attackResults.length} />
        <MetricCard label="探测次数" value={snapshot.probeCount} />
        <MetricCard label="工件数量" value={snapshot.artifactCount} />
        <MetricCard label="P95 延迟" value={snapshot.latencyP95} hint="ms" />
        <MetricCard label="上行流量" value={formatBytes(snapshot.txBytes)} />
        <MetricCard label="下行流量" value={formatBytes(snapshot.rxBytes)} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <TagPill tone="neutral">{`攻击决策 ${snapshot.decisionLabel}`}</TagPill>
        {typeof round?.patch_applied === "boolean" ? (
          <TagPill tone={round.patch_applied ? "ok" : "warn"}>
            {round?.patch_applied_label || (round.patch_applied ? "已修补" : "未修补")}
          </TagPill>
        ) : null}
        {snapshot.targetServiceVersion ? <TagPill tone="neutral">{snapshot.targetServiceVersion}</TagPill> : null}
        {snapshot.targetServiceRef ? (
          <TagPill tone={active ? "ok" : "neutral"}>{`目标服务 ${snapshot.targetServiceRef}`}</TagPill>
        ) : null}
      </div>
      {snapshot.targetServiceRef ? (
        <p className="mt-2 text-xs text-slate-500">
          {active
            ? "当前对比列已与共享目标服务焦点对齐。"
            : `点击可把共享焦点切到 ${snapshot.targetServiceRef}。`}
        </p>
      ) : null}
      <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-bold text-slate-900">漏洞裁决</p>
          <SemanticPill kind="status" value={snapshot.severity} label={snapshot.severityLabel} />
        </div>
        <p className="mt-2 text-sm text-slate-700">{snapshot.verdictSummary}</p>
      </div>
      <div className="mt-3 space-y-2">
        <p className="text-sm font-bold text-slate-900">主要发现</p>
        {findings.length === 0 ? <p className="text-sm text-slate-500">当前没有沉淀出主要发现。</p> : null}
        {findings.slice(0, 4).map((item, index) => (
          <p key={`${title}-finding-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            {index + 1}. {item}
          </p>
        ))}
      </div>
    </div>
  );
}

export default function RoundComparisonPanel({ attackLoop, replayScope, setReplayScope }) {
  const rounds = Array.isArray(attackLoop?.rounds) ? attackLoop.rounds : [];
  const baselineRound = rounds.find((item) => item?.round_kind === "baseline") || rounds[0] || null;
  const regressionRound =
    rounds.find((item) => item?.round_kind === "regression") || attackLoop?.current_round || rounds[1] || null;

  if (!baselineRound || !regressionRound) {
    return (
        <Panel
          title="基线轮与回归轮对比"
          subtitle="用于解释补丁前后是否真的产生了效果；如果当前没有两轮数据，就先诚实显示为空。"
        >
        <p className="text-sm text-slate-500">基线轮 / 回归轮数据不足。</p>
        </Panel>
      );
  }

  const baseline = summarizeRound(baselineRound);
  const regression = summarizeRound(regressionRound);
  const findingDiff = compareFindings(baseline.findings, regression.findings);
  const verdictDiff = buildRegressionTone(baseline, regression);
  const focusedServiceRef = normalizeRef(replayScope?.targetServiceRef);
  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const focusSummary = buildTargetFocusSummary(baseline, regression, focusedServiceRef);
  const stageFocusSummary = buildStageFocusSummary(focusedStageRef);
  const serviceAligned = Boolean(baseline.targetServiceRef) && baseline.targetServiceRef === regression.targetServiceRef;
  const differenceSummary = findingDiff.added.length
    ? `回归轮新增 ${findingDiff.added.length} 项关注点`
    : findingDiff.removed.length
      ? `已压下 ${findingDiff.removed.length} 项发现`
      : "修补前后差异仍需人工复核";

  return (
    <Panel
      title="基线轮与回归轮对比"
      subtitle="把基线轮与回归轮放到同一层看，直接回答“补丁之后到底有没有变好”。"
    >
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="基线发现" value={baseline.findings.length} />
        <MetricCard label="回归发现" value={regression.findings.length} />
        <MetricCard label="已消除发现" value={findingDiff.removed.length} />
        <MetricCard label="新增发现" value={findingDiff.added.length} />
      </div>

      <div className="mt-4 overflow-hidden rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_50%,#ecfeff_100%)] p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.26em] text-sky-700">轮次对比总览</p>
            <h3 className="mt-2 text-xl font-black text-slate-950">修补前后对比总览</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
              查看修补前后差异和目标服务对齐情况。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 xl:max-w-[380px] xl:justify-end">
            <SemanticPill kind="status" value={verdictDiff.tone} label={verdictDiff.label} />
            <TagPill tone={serviceAligned ? "ok" : "warn"}>{serviceAligned ? "同一服务已对齐" : "对比对象待校准"}</TagPill>
            <TagPill tone={findingDiff.added.length ? "warn" : "ok"}>{differenceSummary}</TagPill>
            <TagPill tone="neutral">{attackLoop?.loop_status || "loop_status 未提供"}</TagPill>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-3">
          <div className="rounded-2xl border border-white/80 bg-white/90 p-4 shadow-sm">
            <p className="text-sm font-black text-slate-900">风险结论</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">{verdictDiff.summary}</p>
          </div>

          <div className="rounded-2xl border border-white/80 bg-white/90 p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">共享目标服务焦点</p>
              <SemanticPill kind="status" value={focusSummary.tone} label={focusSummary.label} />
              <ReplayFocusPill kind="targetServiceRef" value={focusedServiceRef} active />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{focusSummary.summary}</p>
          </div>

          <div className="rounded-2xl border border-white/80 bg-white/90 p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">共享阶段焦点</p>
              <SemanticPill kind="status" value={stageFocusSummary.tone} label={stageFocusSummary.label} />
              <ReplayFocusPill kind="stageRef" value={focusedStageRef} active />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{stageFocusSummary.summary}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <RoundColumn
          title="基线轮"
          tone="warn"
          snapshot={baseline}
          focusedServiceRef={focusedServiceRef}
          focusedStageRef={focusedStageRef}
          setReplayScope={setReplayScope}
        />
        <RoundColumn
          title="回归轮"
          tone="ok"
          snapshot={regression}
          focusedServiceRef={focusedServiceRef}
          focusedStageRef={focusedStageRef}
          setReplayScope={setReplayScope}
        />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-3">
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-sm font-black text-slate-900">已被压下的发现</p>
          <div className="mt-3 space-y-2">
            {findingDiff.removed.length === 0 ? <p className="text-sm text-slate-500">暂无已降低风险。</p> : null}
            {findingDiff.removed.slice(0, 5).map((item, index) => (
              <p key={`removed-${index}`} className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm text-emerald-800">
                {index + 1}. {item}
              </p>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-black text-slate-900">仍然保留的发现</p>
          <div className="mt-3 space-y-2">
            {findingDiff.retained.length === 0 ? <p className="text-sm text-slate-500">当前没有跨轮保留的发现。</p> : null}
            {findingDiff.retained.slice(0, 5).map((item, index) => (
              <p key={`retained-${index}`} className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm text-amber-900">
                {index + 1}. {item}
              </p>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
          <p className="text-sm font-black text-slate-900">回归轮新增关注点</p>
          <div className="mt-3 space-y-2">
            {findingDiff.added.length === 0 ? <p className="text-sm text-slate-500">当前没有新增关注点。</p> : null}
            {findingDiff.added.slice(0, 5).map((item, index) => (
              <p key={`added-${index}`} className="rounded-lg border border-rose-200 bg-white px-3 py-2 text-sm text-rose-800">
                {index + 1}. {item}
              </p>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}
