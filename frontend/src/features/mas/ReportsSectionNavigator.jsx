import { Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

const GROUP_META = {
  overview: {
    step: "01",
    shell: "border-sky-200 bg-[linear-gradient(135deg,#ffffff_0%,#f0f9ff_100%)]",
    badge: "border-sky-200 bg-sky-100 text-sky-800",
  },
  attack: {
    step: "02",
    shell: "border-rose-200 bg-[linear-gradient(135deg,#ffffff_0%,#fff1f2_100%)]",
    badge: "border-rose-200 bg-rose-100 text-rose-800",
  },
  evidence: {
    step: "03",
    shell: "border-emerald-200 bg-[linear-gradient(135deg,#ffffff_0%,#ecfdf5_100%)]",
    badge: "border-emerald-200 bg-emerald-100 text-emerald-800",
  },
};

const BUTTON_TONE_META = {
  neutral: {
    activeClass: "border-slate-900 bg-slate-950 text-white shadow-[0_18px_36px_-24px_rgba(15,23,42,0.55)]",
    statusTone: "neutral",
  },
  info: {
    activeClass: "border-sky-300 bg-sky-50 text-sky-950 shadow-[0_18px_36px_-24px_rgba(2,132,199,0.35)]",
    statusTone: "ok",
  },
  ok: {
    activeClass: "border-emerald-300 bg-emerald-50 text-emerald-950 shadow-[0_18px_36px_-24px_rgba(5,150,105,0.32)]",
    statusTone: "ok",
  },
  warn: {
    activeClass: "border-amber-300 bg-amber-50 text-amber-950 shadow-[0_18px_36px_-24px_rgba(217,119,6,0.34)]",
    statusTone: "warn",
  },
};

function SectionButton({ label, detail, active = false, tone = "neutral", onClick }) {
  const toneMeta = BUTTON_TONE_META[tone] || BUTTON_TONE_META.neutral;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "min-w-0 rounded-[22px] border px-4 py-4 text-left transition hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-sky-300",
        active ? toneMeta.activeClass : "border-white/80 bg-white/88 text-slate-700 hover:border-slate-300 hover:bg-white"
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <p className={cn("text-sm font-black", active ? "" : "text-slate-900")}>{label}</p>
        <TagPill tone={active ? toneMeta.statusTone : "neutral"}>{active ? "当前命中" : "点击跳转"}</TagPill>
      </div>
      <p className={cn("mt-2 text-sm leading-6", active ? "opacity-90" : "text-slate-600")}>{detail}</p>
    </button>
  );
}

export default function ReportsSectionNavigator({
  flowPanelActive,
  replayPanelActive,
  attackPanelActive,
  dispatcherPanelActive,
  selectedEvidence,
  selectedProposalId,
  selectedDeliveryFragmentId,
  onJumpToMainlinePanel,
  onJumpToSection,
}) {
  const activeMainlineLabel =
    (flowPanelActive && "流程概览") ||
    (replayPanelActive && "回放深钻") ||
    (attackPanelActive && "攻击闭环") ||
    (dispatcherPanelActive && "执行平面") ||
    "";

  const overviewActive = !activeMainlineLabel && !selectedEvidence && !selectedDeliveryFragmentId;
  const evidenceActive = Boolean(selectedEvidence || selectedProposalId);
  const deliveryActive = Boolean(selectedDeliveryFragmentId);

  const groups = [
    {
      id: "overview",
      title: "全貌",
      subtitle: "汇总项目、需求、审计结论和多 Agent 主线。",
      pills: [<TagPill key="overview" tone={overviewActive ? "ok" : "neutral"}>{overviewActive ? "当前建议从这里开始" : "总览入口"}</TagPill>],
      items: [
        {
          id: "reports-section-overview",
          label: "项目与需求摘要",
          detail: "项目记忆、结构化需求和审计判定。",
          active: overviewActive,
          onClick: () => onJumpToSection?.("reports-section-overview"),
        },
        {
          id: "mainline-panel-flow",
          label: "流程概览",
          detail: "上下文窗口、流程轨迹和结构化交接。",
          active: flowPanelActive,
          tone: "info",
          onClick: () => onJumpToMainlinePanel?.("mainline-panel-flow"),
        },
        {
          id: "mainline-panel-replay",
          label: "回放深钻",
          detail: "事件、快照、交接与目标服务轨迹。",
          active: replayPanelActive,
          tone: "info",
          onClick: () => onJumpToMainlinePanel?.("mainline-panel-replay"),
        },
      ],
    },
    {
      id: "attack",
      title: "攻击闭环",
      subtitle: "查看攻击、评估、修补与执行治理。",
      pills: [<TagPill key="attack" tone={activeMainlineLabel ? "ok" : "neutral"}>{activeMainlineLabel ? `当前主线：${activeMainlineLabel}` : "等待主线焦点"}</TagPill>],
      items: [
        {
          id: "mainline-panel-attack",
          label: "攻击闭环",
          detail: "目标服务、攻击轮次、漏洞评估与代码交付。",
          active: attackPanelActive,
          tone: "warn",
          onClick: () => onJumpToMainlinePanel?.("mainline-panel-attack"),
        },
        {
          id: "mainline-panel-dispatch",
          label: "执行平面",
          detail: "把沙盒调度、审批与回归动作接回治理主线。",
          active: dispatcherPanelActive,
          tone: "warn",
          onClick: () => onJumpToMainlinePanel?.("mainline-panel-dispatch"),
        },
        {
          id: "reports-section-handoff",
          label: "交接与工件深钻",
          detail: "跨 Agent 结构化交接、工件引用与证据来源。",
          onClick: () => onJumpToSection?.("reports-section-handoff"),
        },
      ],
    },
    {
      id: "evidence",
      title: "证据与交付",
      subtitle: "查看证据闭环、可信度解释和最终交付输出。",
      pills: [
        <TagPill key="evidence" tone={evidenceActive ? "ok" : "neutral"}>{evidenceActive ? "当前已进入证据联动" : "证据区待展开"}</TagPill>,
        <TagPill key="delivery" tone={deliveryActive ? "warn" : "neutral"}>{deliveryActive ? "已锁定交付片段" : "交付区待展开"}</TagPill>,
      ],
      items: [
        {
          id: "reports-section-credibility",
          label: "可信度与整改摘要",
          detail: "当前方案的可信度、对比结果与整改方向。",
          active: evidenceActive && !deliveryActive,
          tone: "ok",
          onClick: () => onJumpToSection?.("reports-section-credibility"),
        },
        {
          id: "reports-section-evidence-pack",
          label: "证据包与联动解读",
          detail: "证据如何支撑审计、候选方案与回放路径。",
          active: evidenceActive,
          tone: "ok",
          onClick: () => onJumpToSection?.("reports-section-evidence-pack"),
        },
        {
          id: "reports-section-delivery",
          label: "最终交付与历史记录",
          detail: "最后回到交付结果、导出物和历史回放。",
          active: deliveryActive,
          tone: "warn",
          onClick: () => onJumpToSection?.("reports-section-delivery"),
        },
      ],
    },
  ];

  return (
    <Panel
      title="章节导航"
      subtitle="查看报告章节，可快速跳到证据或交付。"
      className="xl:col-span-2"
    >
      <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_42%,#eef6ff_100%)] p-4 shadow-sm">
        <div className="rounded-[24px] border border-white/80 bg-white/88 p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <TagPill tone={overviewActive ? "ok" : "neutral"}>{overviewActive ? "当前显示全貌" : "总览段待展开"}</TagPill>
            <TagPill tone={activeMainlineLabel ? "ok" : "neutral"}>
              {activeMainlineLabel ? `主线已命中：${activeMainlineLabel}` : "主线段待定位"}
            </TagPill>
            <TagPill tone={deliveryActive ? "warn" : evidenceActive ? "ok" : "neutral"}>
              {deliveryActive ? "交付段已锁定" : evidenceActive ? "证据段已展开" : "证据与交付段待展开"}
            </TagPill>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            这一层用于切换报告章节。
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          {groups.map((group) => (
            <div
              key={group.id}
              className={cn(
                "rounded-[28px] border p-4 shadow-sm",
                GROUP_META[group.id]?.shell || "border-slate-200 bg-white/90"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={cn(
                      "inline-flex h-9 w-9 items-center justify-center rounded-full border text-xs font-black",
                      GROUP_META[group.id]?.badge || "border-slate-200 bg-slate-100 text-slate-700"
                    )}
                  >
                    {GROUP_META[group.id]?.step || "--"}
                  </span>
                  {group.pills}
                </div>
                <TagPill tone="neutral">路线卡</TagPill>
              </div>
              <p className="mt-3 text-base font-black text-slate-950">{group.title}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{group.subtitle}</p>
              <div className="mt-4 space-y-3">
                {group.items.map((item) => (
                  <SectionButton
                    key={item.id}
                    label={item.label}
                    detail={item.detail}
                    active={Boolean(item.active)}
                    tone={item.tone}
                    onClick={item.onClick}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}
