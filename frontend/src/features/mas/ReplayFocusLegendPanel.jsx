import { Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";
import {
  REPLAY_FOCUS_ORDER,
  REPLAY_QUERY_FOCUS_ORDER,
  buildReplayFocusLabel,
  getReplayFocusMeta,
  getReplayFocusTone,
} from "./masHelpers";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function normalizeRef(value) {
  return String(value || "").trim();
}

export default function ReplayFocusLegendPanel({ replayScope = {} }) {
  const focusLegendGroups = [
    {
      id: "primary",
      title: "主线联动焦点",
      description: "查看当前阶段、上下文窗口、交接和目标服务。",
      order: REPLAY_FOCUS_ORDER,
      columns: "lg:grid-cols-2 xl:grid-cols-4",
    },
    {
      id: "query",
      title: "深钻查询焦点",
      description: "查看工件、证据或恢复定位点。",
      order: REPLAY_QUERY_FOCUS_ORDER,
      columns: "lg:grid-cols-2 xl:grid-cols-4",
    },
  ];
  const allFocusKinds = focusLegendGroups.flatMap((group) => group.order);
  const activeFocusItems = allFocusKinds
    .map((kind) => ({
      kind,
      value: normalizeRef(replayScope?.[kind]),
      meta: getReplayFocusMeta(kind),
    }))
    .filter((item) => item.value);

  return (
    <Panel
      title="共享焦点图例与当前状态"
      subtitle="查看主线联动焦点与深钻查询焦点。"
      className="xl:col-span-2"
    >
      <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_45%,#eef6ff_100%)] p-4 shadow-sm">
        <div className="rounded-[24px] border border-white/80 bg-white/88 p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <TagPill tone={activeFocusItems.length ? "ok" : "neutral"}>
              {activeFocusItems.length ? `已锁定 ${activeFocusItems.length} 类焦点` : "当前为全局概览"}
            </TagPill>
            <TagPill tone="neutral">主线 / 深钻</TagPill>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            先看主线联动焦点，再看深钻查询焦点。
          </p>
        </div>

        <div className="mt-4 space-y-4">
          {focusLegendGroups.map((group) => (
            <div key={group.id} className="rounded-[24px] border border-slate-200 bg-white/85 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-black text-slate-900">{group.title}</p>
                <TagPill tone="neutral">{`${group.order.length} 类焦点`}</TagPill>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">{group.description}</p>
              <div className={cn("mt-3 grid gap-3", group.columns)}>
                {group.order.map((kind) => {
                  const meta = getReplayFocusMeta(kind);
                  const currentValue = normalizeRef(replayScope?.[kind]);
                  const active = Boolean(currentValue);
                  return (
                    <div
                      key={kind}
                      className="rounded-[24px] border border-slate-200 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(248,250,252,0.96))] p-4 shadow-[0_10px_24px_rgba(15,23,42,0.05)]"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <TagPill tone={getReplayFocusTone(kind, active)}>{meta.label}</TagPill>
                        <TagPill tone={active ? "ok" : "neutral"}>{active ? "当前激活" : "未锁定"}</TagPill>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-slate-700">{meta.description}</p>
                      <p className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">当前状态</p>
                      <p className="mt-1 text-sm font-semibold text-slate-800">
                        {active ? buildReplayFocusLabel(kind, currentValue) : "当前未锁定该类焦点"}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

      <div className="mt-4 rounded-[24px] border border-dashed border-slate-300 bg-white/85 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">本页当前已激活的联动焦点</p>
          {activeFocusItems.length ? (
            activeFocusItems.map((item) => (
              <TagPill key={`active-focus-${item.kind}`} tone={getReplayFocusTone(item.kind, true)}>
                {buildReplayFocusLabel(item.kind, item.value)}
              </TagPill>
            ))
          ) : (
            <TagPill tone="neutral">当前仍是全局概览视图</TagPill>
          )}
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          当你在流程、回放、交接、沙盒执行平面或轮次对比面板里点选标签时，这里的当前焦点会同步变化。
        </p>
      </div>
      </div>
    </Panel>
  );
}
