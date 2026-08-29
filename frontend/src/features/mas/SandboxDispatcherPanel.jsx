import { MetricCard, Panel } from "../../components/Panel";
import { SemanticPill, TagPill } from "../../components/SemanticPill";
import { ReplayFocusPill } from "./ReplayFocusPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function latestAuditEvent(item = {}) {
  const trail = Array.isArray(item?.audit_trail) ? item.audit_trail : [];
  return trail.length ? trail[trail.length - 1] : null;
}

function normalizeRef(value) {
  return String(value || "").trim();
}

function formatDispatchLabel(item = {}) {
  const decision = item?.decision_label || item?.decision || "--";
  const status = item?.status_label || item?.status || "--";
  return `${decision} / ${status}`;
}

function buildFocusedStageSummary(stages = [], focusedServiceRef = "") {
  if (!focusedServiceRef) {
    return {
      tone: "neutral",
      label: "未锁定目标服务",
      summary: "尚未选择目标服务。",
      matchedCount: 0,
    };
  }

  const matched = stages.filter(([, item]) => normalizeRef(item?.target_service_ref) === focusedServiceRef);
  if (matched.length > 0) {
    return {
      tone: "ok",
      label: "已命中执行节点",
      summary: `当前共享焦点为 ${focusedServiceRef}，调度治理面板中共有 ${matched.length} 个审批/执行节点与其对齐，可直接查看该服务在基线轮、回归轮两侧的审批状态。`,
      matchedCount: matched.length,
    };
  }

  return {
    tone: "warn",
    label: "未命中当前审批节点",
    summary: `目标服务 ${focusedServiceRef} 未命中调度摘要。`,
    matchedCount: 0,
  };
}

function buildStageFocusSummary(stages = [], focusedStageRef = "") {
  if (!focusedStageRef) {
    return {
      tone: "neutral",
      label: "未锁定流程阶段",
      summary: "尚未选择阶段。",
      matchedCount: 0,
    };
  }

  const matched = stages.filter(([, item]) => normalizeRef(item?.stage) === focusedStageRef);
  if (matched.length > 0) {
    return {
      tone: "ok",
      label: "已命中执行阶段",
      summary: `当前共享阶段焦点为 ${focusedStageRef}，执行平面中共有 ${matched.length} 个节点与其对齐。`,
      matchedCount: matched.length,
    };
  }

  return {
    tone: "warn",
    label: "当前阶段未映射到执行平面",
    summary: `阶段 ${focusedStageRef} 未命中执行节点。`,
    matchedCount: 0,
  };
}

function summarizeDispatchStatus(stages = []) {
  const items = stages.map(([, item]) => item || {});
  const approvedCount = items.filter((item) => {
    const decision = String(item?.decision || item?.decision_label || "").toLowerCase();
    return decision.includes("approve") || decision.includes("approved") || String(item?.decision_label || "").includes("批准");
  }).length;
  const blockedCount = items.filter((item) => (item?.failure_items || []).length > 0).length;
  const targetRefs = new Set(
    items
      .map((item) => normalizeRef(item?.target_service_ref))
      .filter(Boolean)
  );

  return {
    approvedCount,
    blockedCount,
    targetCount: targetRefs.size,
  };
}

function DispatchStageCard({ title, item, focusedServiceRef, focusedStageRef, setReplayScope }) {
  const lastEvent = latestAuditEvent(item);
  const failureItems = Array.isArray(item?.failure_items) ? item.failure_items : [];
  const targetServiceRef = normalizeRef(item?.target_service_ref);
  const active = Boolean(targetServiceRef) && targetServiceRef === focusedServiceRef;
  const stageActive = normalizeRef(item?.stage) === focusedStageRef;
  const clickable = Boolean(targetServiceRef) && typeof setReplayScope === "function";

  function toggleTargetService() {
    if (!clickable) return;
    setReplayScope((prev) => ({
      ...(prev || {}),
      targetServiceRef: prev?.targetServiceRef === targetServiceRef ? "" : targetServiceRef,
    }));
  }

  return (
    <div
      className={cn(
        "rounded-2xl border bg-white p-4 transition",
        active || stageActive ? "border-sky-400 bg-sky-50/40 shadow-sm" : "border-slate-200",
        clickable ? "cursor-pointer hover:border-sky-300" : ""
      )}
      onClick={clickable ? toggleTargetService : undefined}
    >
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-black text-slate-900">{title}</p>
        <SemanticPill kind="status" value={item?.status} label={item?.status_label} />
        <TagPill tone="neutral">{item?.executor_backend || "--"}</TagPill>
        {active ? <TagPill tone="ok">共享焦点</TagPill> : null}
        {stageActive ? <TagPill tone="warn">阶段对齐</TagPill> : null}
      </div>

      <p className="mt-2 text-sm text-slate-700">{formatDispatchLabel(item)}</p>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <MetricCard label="请求任务" value={item?.requested_attack_count ?? 0} />
        <MetricCard label="批准任务" value={item?.approved_attack_count ?? 0} />
        <MetricCard label="请求探测" value={item?.requested_probe_count ?? 0} />
        <MetricCard label="批准探测" value={item?.approved_probe_count ?? 0} />
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {item?.decision ? <TagPill tone="warn">{item.decision}</TagPill> : null}
        {targetServiceRef ? <TagPill tone={active ? "ok" : "neutral"}>{targetServiceRef}</TagPill> : null}
        {lastEvent?.event_kind ? <TagPill tone="ok">{`最后事件 ${lastEvent.event_kind}`}</TagPill> : null}
      </div>

      {targetServiceRef ? (
        <p className="mt-2 text-xs text-slate-500">
          {active ? "当前审批卡片已与共享目标服务焦点对齐。" : `点击可把共享焦点切到 ${targetServiceRef}。`}
        </p>
      ) : null}

      <div className="mt-3 space-y-2">
        {failureItems.length === 0 ? (
          <p className="text-sm text-slate-500">当前没有 failure_items，说明调度层没有记录额外阻断。</p>
        ) : null}
        {failureItems.slice(0, 3).map((failure, index) => (
          <div key={`${title}-failure-${index}`} className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="bad">{failure?.reason_code || "--"}</TagPill>
              <TagPill tone="neutral">{failure?.category_label || failure?.category || "--"}</TagPill>
            </div>
            <p className="mt-2 text-sm text-rose-900">
              {failure?.reason_label || "当前 failure item 未提供中文标签。"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SandboxDispatcherPanel({ sandboxDispatcher, replayScope, setReplayScope }) {
  const policy = sandboxDispatcher?.policy || {};
  const stages = [
    ["基线部署审批", sandboxDispatcher?.baseline_deployment || {}],
    ["基线攻击审批", sandboxDispatcher?.baseline_attack || {}],
    ["回归部署审批", sandboxDispatcher?.regression_deployment || {}],
    ["回归攻击审批", sandboxDispatcher?.regression_attack || {}],
  ];
  const focusedServiceRef = normalizeRef(replayScope?.targetServiceRef);
  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const focusSummary = buildFocusedStageSummary(stages, focusedServiceRef);
  const stageFocusSummary = buildStageFocusSummary(stages, focusedStageRef);
  const dispatchStats = summarizeDispatchStatus(stages);

  return (
    <Panel
      title="沙盒调度与审批治理"
      subtitle="展示沙盒审批、执行与阻断结果。"
    >
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="执行后端" value={sandboxDispatcher?.backend || "--"} />
        <MetricCard label="策略编号" value={policy?.policy_id || "--"} />
        <MetricCard label="最大攻击任务" value={policy?.max_attack_tasks ?? "--"} />
        <MetricCard label="最大探测次数" value={policy?.max_probe_count ?? "--"} />
      </div>

      <div className="mt-4 overflow-hidden rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#eff6ff_48%,#f8fafc_100%)] p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.26em] text-sky-700">沙盒调度治理</p>
            <h3 className="mt-2 text-xl font-black text-slate-950">审批与调度</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
              查看基线部署、基线攻击、回归部署和回归攻击审批。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 xl:max-w-[380px] xl:justify-end">
            <TagPill tone="neutral">{`审批节点 ${stages.length}`}</TagPill>
            <TagPill tone={dispatchStats.approvedCount ? "ok" : "neutral"}>{`已批准 ${dispatchStats.approvedCount}`}</TagPill>
            <TagPill tone={dispatchStats.blockedCount ? "warn" : "ok"}>{`有阻断 ${dispatchStats.blockedCount}`}</TagPill>
            <TagPill tone="neutral">{`目标服务 ${dispatchStats.targetCount}`}</TagPill>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-3">
          <div className="rounded-2xl border border-white/80 bg-white/90 p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">共享目标服务焦点</p>
              <SemanticPill kind="status" value={focusSummary.tone} label={focusSummary.label} />
              <ReplayFocusPill kind="targetServiceRef" value={focusedServiceRef} active />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{focusSummary.summary}</p>
            {focusSummary.matchedCount ? <TagPill tone="ok">{`${focusSummary.matchedCount} 个命中节点`}</TagPill> : null}
          </div>

          <div className="rounded-2xl border border-white/80 bg-white/90 p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">共享阶段焦点</p>
              <SemanticPill kind="status" value={stageFocusSummary.tone} label={stageFocusSummary.label} />
              <ReplayFocusPill kind="stageRef" value={focusedStageRef} active />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{stageFocusSummary.summary}</p>
            {stageFocusSummary.matchedCount ? <TagPill tone="ok">{`${stageFocusSummary.matchedCount} 个命中节点`}</TagPill> : null}
          </div>

          <div className="rounded-2xl border border-slate-200/70 bg-slate-950 px-4 py-4 text-white shadow-[0_18px_40px_-26px_rgba(15,23,42,0.9)]">
            <p className="text-[11px] font-black uppercase tracking-[0.22em] text-sky-200">治理摘要</p>
            <p className="mt-2 text-lg font-black">四段审批已收口到统一视图</p>
            <p className="mt-2 text-sm leading-6 text-slate-200">
              先看是否批准，再看 failure_items 和目标服务命中情况，就能快速判断当前沙盒链路卡在“部署”还是“攻击”。
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        {stages.map(([title, item]) => (
          <DispatchStageCard
            key={title}
            title={title}
            item={item}
            focusedServiceRef={focusedServiceRef}
            focusedStageRef={focusedStageRef}
            setReplayScope={setReplayScope}
          />
        ))}
      </div>
    </Panel>
  );
}
