import { MetricCard, Panel } from "../../components/Panel";
import { SemanticPill, TagPill } from "../../components/SemanticPill";
import { ReplayFocusButton, ReplayFocusPill } from "./ReplayFocusPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function normalizeRef(value) {
  return String(value || "").trim();
}

function uniqueStrings(items = []) {
  return [...new Set((items || []).filter(Boolean).map((item) => String(item).trim()).filter(Boolean))];
}

function formatBytes(value) {
  const num = Number(value);
  if (!Number.isFinite(num) || num < 0) return "--";
  if (num < 1024) return `${num} B`;
  if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KB`;
  return `${(num / (1024 * 1024)).toFixed(1)} MB`;
}

function getAttackLoopTargetService(target = {}, fallbackRef = "") {
  return {
    ref: normalizeRef(target?.service_id || target?.service_ref || fallbackRef),
    label: target?.service_name || target?.service_label || normalizeRef(target?.service_id || target?.service_ref || fallbackRef) || "--",
    version: target?.service_version || "",
  };
}

function buildAttackStageFocusSummary(focusedStageRef = "") {
  if (!focusedStageRef) {
    return {
      tone: "neutral",
      label: "未锁定攻击闭环阶段",
      summary: "默认查看攻击闭环。选中阶段后显示所属主链。",
    };
  }

  if (["attack_executor", "vulnerability_evaluation", "patch_reflection"].includes(focusedStageRef)) {
    return {
      tone: "ok",
      label: "已对齐攻击闭环阶段",
      summary: `当前 replay 阶段焦点为 ${focusedStageRef}，它属于攻击闭环主链，因此本面板已经成为该阶段的主要解释视图。`,
    };
  }

  return {
    tone: "warn",
    label: "当前阶段偏离攻击闭环主链",
    summary: `当前 replay 阶段焦点为 ${focusedStageRef}，但它更偏控制/上下文阶段，因此攻击闭环面板此时只作为辅助观察视图。`,
  };
}

function buildPatchStatusSummary(patchSpec = {}, reflectionCards = [], currentRound = {}) {
  if (currentRound?.patch_applied) {
    return {
      tone: "ok",
      label: "已进入修补验证",
      summary: "当前轮次已经带着补丁进入验证，可直接对照风险下降、流量变化与残余问题。",
    };
  }

  if (patchSpec?.strategy || patchSpec?.next_version) {
    return {
      tone: "warn",
      label: "已形成修补建议",
      summary: "专家评估已经给出修补方向，但还需要继续观察回归攻击与残余风险是否真正下降。",
    };
  }

  if (reflectionCards.length > 0) {
    return {
      tone: "warn",
      label: "已沉淀反思卡片",
      summary: "当前已经开始复盘攻击闭环，但修补策略还没有完整收口，适合继续补充整改建议。",
    };
  }

  return {
    tone: "neutral",
    label: "修补链路待收口",
    summary: "暂无修补与反思结论。",
  };
}

export default function AttackLoopPanel({
  attackLoop,
  codeArtifacts,
  replayScope,
  setReplayScope,
}) {
  const targetService = attackLoop?.target_service || {};
  const attackSpecs = attackLoop?.attack_specs || [];
  const attackResults = attackLoop?.attack_results || [];
  const attackRounds = attackLoop?.rounds || [];
  const currentRound = attackLoop?.current_round || {};
  const vulnerabilityVerdict = attackLoop?.vulnerability_verdict || {};
  const patchSpec = attackLoop?.patch_spec || {};
  const reflectionCards = attackLoop?.reflection_cards || [];
  const primaryMetrics = attackResults[0]?.metrics || {};
  const trafficSeries = attackResults.flatMap((item) =>
    Array.isArray(item?.metrics?.traffic_series) ? item.metrics.traffic_series : []
  );
  const totalArtifacts = attackResults.reduce((sum, item) => sum + (item?.artifact_refs?.length || 0), 0);
  const findings = uniqueStrings(attackResults.flatMap((item) => item?.findings || [])).slice(0, 6);
  const codeReady = [
    codeArtifacts?.pseudocode_ready ? "伪代码" : null,
    codeArtifacts?.python_ready ? "Python 代码" : null,
    codeArtifacts?.c_ready ? "C/C++" : null,
  ].filter(Boolean);
  const targetServiceInfo = getAttackLoopTargetService(
    targetService,
    currentRound?.target_service_ref || attackLoop?.target_service_ref
  );
  const focusedServiceRef = normalizeRef(replayScope?.targetServiceRef);
  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const serviceFocusActive = Boolean(targetServiceInfo.ref) && targetServiceInfo.ref === focusedServiceRef;
  const stageFocusSummary = buildAttackStageFocusSummary(focusedStageRef);
  const patchStatusSummary = buildPatchStatusSummary(patchSpec, reflectionCards, currentRound);
  const hasReplayFocus = Boolean(focusedServiceRef || focusedStageRef);
  const attackStageFocusActive = ["attack_executor", "vulnerability_evaluation", "patch_reflection"].includes(
    focusedStageRef
  );
  const focusedRoundCount = focusedServiceRef
    ? attackRounds.filter((round) => {
        const roundService = getAttackLoopTargetService(round?.target_service || {}, round?.target_service_ref);
        return Boolean(roundService.ref) && roundService.ref === focusedServiceRef;
      }).length
    : 0;
  const attackStageRoundCount = attackStageFocusActive ? attackRounds.length : 0;
  const observationModeLabel = hasReplayFocus ? "联动观察视角" : "攻击闭环总览";
  const currentRoundLabel = currentRound?.round_kind_label || currentRound?.round_kind || "等待轮次";
  const currentRoundIndexLabel = currentRound?.round_index ? `第 ${currentRound.round_index} 轮` : "尚未进入轮次";
  const serviceAlignmentLabel = serviceFocusActive
    ? "已对齐当前目标服务"
    : focusedServiceRef
      ? "正在跨服务回看"
      : "未锁定目标服务";
  const codeReadyLabel = codeReady.length ? codeReady.join(" / ") : "交付代码仍在准备";
  const loopProgressLabel = attackRounds.length
    ? `${attackRounds.length} 轮攻击闭环已沉淀`
    : "闭环轮次仍在准备";
  const serviceStatusLabel = targetService?.status_label || targetService?.status || "待确认";
  const trafficPeak = Math.max(
    1,
    ...trafficSeries.map((item) => Number(item?.tx_bytes || 0) + Number(item?.rx_bytes || 0))
  );

  function toggleTargetService(targetServiceRef) {
    const normalized = normalizeRef(targetServiceRef);
    if (!normalized || typeof setReplayScope !== "function") return;
    setReplayScope((prev) => ({
      ...(prev || {}),
      targetServiceRef: prev?.targetServiceRef === normalized ? "" : normalized,
    }));
  }

  return (
    <Panel
      title="攻击闭环与沙盒态势"
      subtitle="汇总目标服务、攻击执行、漏洞评估与修补建议。"
    >
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="目标服务" value={targetService?.service_name || "--"} />
        <MetricCard label="部署状态" value={targetService?.status || "--"} valueLabel={targetService?.status_label} />
        <MetricCard label="攻击任务" value={attackSpecs.length} />
        <MetricCard label="闭环轮次" value={attackRounds.length || 1} />
        <MetricCard label="工件数量" value={totalArtifacts} />
      </div>

      <div
        className={cn(
          "mt-4 overflow-hidden rounded-[28px] border p-5 shadow-sm transition",
          hasReplayFocus
            ? "border-sky-200 bg-[linear-gradient(135deg,#eff6ff_0%,#f8fafc_48%,#ecfeff_100%)] shadow-sky-100/80"
            : "border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_55%,#f1f5f9_100%)]"
        )}
      >
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.26em] text-sky-700">攻防闭环总览</p>
            <h3 className="mt-2 text-xl font-black text-slate-950">共享观察焦点总览</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
              {hasReplayFocus
                ? "当前正在跟随共享焦点里被点中的目标服务或阶段，让攻击闭环、轮次摘要与本地沙盒指标对齐到同一条观察线。"
                : "当前展示的是攻击闭环总览。你可以先在关系回放或主线面板里点选目标服务或阶段，这里会立即切换成联动观察视角。"}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 xl:max-w-[360px] xl:justify-end">
            {hasReplayFocus ? (
              <TagPill tone="ok">当前正在跟随共享焦点</TagPill>
            ) : (
              <TagPill tone="neutral">当前是攻击闭环总览</TagPill>
            )}
            <SemanticPill kind="status" value={stageFocusSummary.tone} label={stageFocusSummary.label} />
            <SemanticPill kind="status" value={patchStatusSummary.tone} label={patchStatusSummary.label} />
            {focusedRoundCount ? <TagPill tone="ok">{`命中轮次 ${focusedRoundCount}`}</TagPill> : null}
            {attackStageRoundCount ? <TagPill tone="neutral">{`主链轮次 ${attackStageRoundCount}`}</TagPill> : null}
            {focusedServiceRef ? (
              <ReplayFocusPill kind="targetServiceRef" value={focusedServiceRef} active={serviceFocusActive} />
            ) : null}
            {focusedStageRef ? <ReplayFocusPill kind="stageRef" value={focusedStageRef} active /> : null}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
          <div className="rounded-2xl border border-white/80 bg-white/85 p-4 shadow-sm backdrop-blur">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">目标服务联动</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {focusedServiceRef
                ? serviceFocusActive
                  ? "当前目标服务已经命中这条攻击闭环，可直接围绕同一服务轨迹看版本、攻击轮次和修补状态。"
                  : "目标服务与当前闭环未对齐。"
                : "尚未选择目标服务。"}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <TagPill tone={focusedRoundCount ? "ok" : "neutral"}>{`命中轮次 ${focusedRoundCount}`}</TagPill>
              {serviceFocusActive ? <TagPill tone="ok">当前服务已对齐</TagPill> : null}
            </div>
          </div>
          <div className="rounded-2xl border border-white/80 bg-white/85 p-4 shadow-sm backdrop-blur">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">修补与阶段联动</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">{stageFocusSummary.summary}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <TagPill tone="neutral">{`主链轮次 ${attackStageRoundCount}`}</TagPill>
              {patchSpec?.next_version ? <TagPill tone="warn">{`下一版本 ${patchSpec.next_version}`}</TagPill> : null}
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{patchStatusSummary.summary}</p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200/70 bg-slate-950 px-4 py-4 text-white shadow-[0_18px_40px_-26px_rgba(15,23,42,0.9)]">
            <p className="text-[11px] font-black uppercase tracking-[0.22em] text-sky-200">观察模式</p>
            <p className="mt-2 text-lg font-black">{observationModeLabel}</p>
            <p className="mt-2 text-sm leading-6 text-slate-200">{serviceAlignmentLabel}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 px-4 py-4 shadow-sm">
            <p className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-500">闭环推进</p>
            <p className="mt-2 text-lg font-black text-slate-950">{loopProgressLabel}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <TagPill tone="neutral">{currentRoundLabel}</TagPill>
              <TagPill tone="neutral">{currentRoundIndexLabel}</TagPill>
              {attackLoop?.loop_status ? <TagPill tone="ok">{attackLoop.loop_status}</TagPill> : null}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 px-4 py-4 shadow-sm">
            <p className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-500">修补与交付</p>
            <p className="mt-2 text-lg font-black text-slate-950">{patchStatusSummary.label}</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">{codeReadyLabel}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">本地沙盒目标服务</p>
            <TagPill tone="neutral">{serviceStatusLabel}</TagPill>
            {targetServiceInfo.version ? <TagPill tone="neutral">{targetServiceInfo.version}</TagPill> : null}
            {targetService?.runtime ? <TagPill tone="neutral">{targetService.runtime}</TagPill> : null}
            {primaryMetrics?.service_port ? <TagPill tone="ok">{`127.0.0.1:${primaryMetrics.service_port}`}</TagPill> : null}
            {targetServiceInfo.ref ? (
              <ReplayFocusButton
                kind="targetServiceRef"
                value={targetServiceInfo.ref}
                active={serviceFocusActive}
                onClick={() => toggleTargetService(targetServiceInfo.ref)}
              />
            ) : null}
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            系统会拉起受限目标服务，执行健康探针和加密接口探测，并保存监测工件。
          </p>

          <div className="mt-3 grid grid-cols-2 gap-2">
            <MetricCard label="P95 延迟" value={primaryMetrics?.latency_p95_ms ?? "--"} hint="ms" />
            <MetricCard label="探测次数" value={primaryMetrics?.probe_count ?? 0} />
            <MetricCard label="上行流量" value={formatBytes(primaryMetrics?.tx_bytes)} />
            <MetricCard label="下行流量" value={formatBytes(primaryMetrics?.rx_bytes)} />
          </div>

          <div className="mt-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">轮次视图</p>
              {attackLoop?.loop_status ? <TagPill tone="neutral">{attackLoop.loop_status}</TagPill> : null}
            </div>
            <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
              {attackRounds.length === 0 ? (
                <p className="text-sm text-slate-500">当前尚未沉淀轮次信息。</p>
              ) : (
                attackRounds.map((round) => {
                  const roundService = getAttackLoopTargetService(round?.target_service || {}, round?.target_service_ref);
                  const roundFocused = Boolean(roundService.ref) && roundService.ref === focusedServiceRef;
                  const roundHitsStageFocus = attackStageFocusActive;
                  return (
                    <div
                      key={round?.round_id || round?.round_index}
                      className={cn(
                        "rounded-xl border px-3 py-3 transition",
                        roundFocused
                          ? "border-sky-300 bg-sky-50/80 shadow-[0_18px_40px_-24px_rgba(14,165,233,0.6)]"
                          : roundHitsStageFocus
                            ? "border-cyan-200 bg-cyan-50/70 shadow-[0_18px_40px_-24px_rgba(6,182,212,0.45)]"
                            : "border-slate-200 bg-slate-50"
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <TagPill tone={round?.mode === "executed" ? "ok" : "warn"}>
                          {round?.round_kind_label || round?.round_kind || "--"}
                        </TagPill>
                        <TagPill tone="neutral">{`第 ${round?.round_index || "--"} 轮`}</TagPill>
                        {currentRound?.round_id === round?.round_id ? <TagPill tone="ok">当前轮次</TagPill> : null}
                        {roundFocused ? <TagPill tone="ok">共享焦点已命中</TagPill> : null}
                        {roundHitsStageFocus ? (
                          <ReplayFocusPill kind="stageRef" value={focusedStageRef} active />
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm text-slate-800">{round?.summary || "当前轮次暂无摘要。"}</p>
                      {roundFocused || roundHitsStageFocus ? (
                        <div
                          className={cn(
                            "mt-3 rounded-xl border px-3 py-2 text-sm leading-6",
                            roundFocused
                              ? "border-sky-200 bg-white/90 text-sky-900"
                              : "border-cyan-200 bg-white/80 text-cyan-900"
                          )}
                        >
                          {roundFocused
                            ? "这轮攻击已经命中当前共享目标服务，适合直接对照版本、漏洞命中与修补状态。"
                            : "当前阶段已命中攻击闭环主链。"}
                        </div>
                      ) : null}
                      <div className="mt-2 flex flex-wrap gap-2">
                        {roundService.version ? <TagPill tone="neutral">{roundService.version}</TagPill> : null}
                        {roundService.ref ? (
                          <ReplayFocusButton
                            kind="targetServiceRef"
                            value={roundService.ref}
                            active={roundFocused}
                            onClick={() => toggleTargetService(roundService.ref)}
                          />
                        ) : null}
                        {typeof round?.patch_applied === "boolean" ? (
                          <TagPill tone={round.patch_applied ? "ok" : "warn"}>
                            {round?.patch_applied_label || (round.patch_applied ? "已修补" : "未修补")}
                          </TagPill>
                        ) : null}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="mt-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">流量波动</p>
              {trafficSeries.length ? <TagPill tone="neutral">{`${trafficSeries.length} 个采样点`}</TagPill> : null}
            </div>
            {trafficSeries.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">本轮还没有可用的流量采样点。</p>
            ) : (
              <>
                <div className="mt-3 flex h-28 items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                  {trafficSeries.map((item, index) => {
                    const total = Number(item?.tx_bytes || 0) + Number(item?.rx_bytes || 0);
                    const height = Math.max(18, Math.round((total / trafficPeak) * 84));
                    return (
                      <div key={`traffic-${index}`} className="flex min-w-0 flex-1 flex-col items-center gap-2">
                        <div
                          className="w-full rounded-t-xl bg-gradient-to-t from-cyan-500 to-sky-300"
                          style={{ height: `${height}px` }}
                          title={`采样 ${item?.sample || index + 1}: ${formatBytes(total)}`}
                        />
                        <p className="text-[11px] font-semibold text-slate-500">{item?.sample || index + 1}</p>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-3">
                  {trafficSeries.map((item, index) => (
                    <div key={`traffic-metric-${index}`} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                      <p className="font-semibold text-slate-800">{`采样 ${item?.sample || index + 1}`}</p>
                      <p>{`上行 ${formatBytes(item?.tx_bytes)}`}</p>
                      <p>{`下行 ${formatBytes(item?.rx_bytes)}`}</p>
                      <p>{`延迟 ${item?.latency_ms ?? "--"} ms`}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">漏洞评估与修补</p>
              {vulnerabilityVerdict?.severity ? (
                <SemanticPill kind="status" value={vulnerabilityVerdict.severity} label={vulnerabilityVerdict.severity_label} />
              ) : null}
              {patchSpec?.next_version ? <TagPill tone="warn">{`下一版本 ${patchSpec.next_version}`}</TagPill> : null}
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {vulnerabilityVerdict?.summary || "本轮尚未形成漏洞评估摘要。"}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {patchSpec?.strategy ? <TagPill tone="neutral">{patchSpec.strategy}</TagPill> : null}
              {vulnerabilityVerdict?.exploitability_label ? <TagPill tone="neutral">{vulnerabilityVerdict.exploitability_label}</TagPill> : null}
              {vulnerabilityVerdict?.remediation_priority_label ? (
                <TagPill tone="warn">{`整改优先级 ${vulnerabilityVerdict.remediation_priority_label}`}</TagPill>
              ) : null}
            </div>
            <div className="mt-3 space-y-2">
              {findings.length === 0 ? <p className="text-sm text-slate-500">当前没有沉淀出漏洞发现摘要。</p> : null}
              {findings.map((item, index) => (
                <p key={`attack-finding-${index}`} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
                  {index + 1}. {item}
                </p>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">交付工件与反思卡片</p>
              {codeReady.length ? <TagPill tone="ok">{`${codeReady.length} 类代码交付已就绪`}</TagPill> : null}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {codeReady.length === 0 ? <TagPill tone="neutral">暂无代码工件</TagPill> : null}
              {codeReady.map((item) => (
                <TagPill key={item} tone="neutral">
                  {item}
                </TagPill>
              ))}
            </div>
            <div className="mt-3 space-y-2">
              {reflectionCards.length === 0 ? <p className="text-sm text-slate-500">当前尚未沉淀反思卡片。</p> : null}
              {reflectionCards.slice(0, 3).map((item, index) => (
                <div key={`reflection-card-${index}`} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <TagPill tone="warn">{item?.card_type || "reflection"}</TagPill>
                    {item?.severity ? <TagPill tone="neutral">{item.severity}</TagPill> : null}
                  </div>
                  <p className="mt-2 text-sm text-amber-900">{item?.summary || "本轮暂无摘要。"}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}
