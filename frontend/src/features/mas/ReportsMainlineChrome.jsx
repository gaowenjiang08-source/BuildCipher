import { Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";
import { ReplayFocusPill } from "./ReplayFocusPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function normalizeRef(value) {
  return String(value || "").trim();
}

const ACCENT_META = {
  sky: {
    frameActive: "border-sky-300 bg-sky-50/65 shadow-[0_20px_44px_-28px_rgba(14,165,233,0.55)]",
    frameIdle: "border-slate-200 bg-white/72",
    halo: "from-sky-300/70 via-sky-200/45 to-white/0",
    chapterBg: "bg-[linear-gradient(135deg,rgba(14,165,233,0.16),rgba(240,249,255,0.96),rgba(255,255,255,0.92))]",
    chapterBorder: "border-sky-200/80",
    number: "border-sky-200 bg-sky-100 text-sky-800",
    chapterPill: "border-sky-200 bg-sky-50 text-sky-700",
    progress: "from-sky-500 via-cyan-400 to-sky-200",
    railActive: "border-sky-400 bg-sky-950 text-white shadow-[0_18px_40px_-26px_rgba(2,132,199,0.52)]",
    railIdle: "border-sky-100 bg-[linear-gradient(135deg,#ffffff_0%,#f0f9ff_100%)] text-slate-900",
  },
  cyan: {
    frameActive: "border-cyan-300 bg-cyan-50/65 shadow-[0_20px_44px_-28px_rgba(6,182,212,0.45)]",
    frameIdle: "border-slate-200 bg-white/72",
    halo: "from-cyan-300/70 via-cyan-200/45 to-white/0",
    chapterBg: "bg-[linear-gradient(135deg,rgba(34,211,238,0.16),rgba(236,254,255,0.96),rgba(255,255,255,0.92))]",
    chapterBorder: "border-cyan-200/80",
    number: "border-cyan-200 bg-cyan-100 text-cyan-800",
    chapterPill: "border-cyan-200 bg-cyan-50 text-cyan-700",
    progress: "from-cyan-500 via-sky-400 to-cyan-200",
    railActive: "border-cyan-400 bg-cyan-950 text-white shadow-[0_18px_40px_-26px_rgba(8,145,178,0.5)]",
    railIdle: "border-cyan-100 bg-[linear-gradient(135deg,#ffffff_0%,#ecfeff_100%)] text-slate-900",
  },
  rose: {
    frameActive: "border-rose-300 bg-rose-50/65 shadow-[0_20px_44px_-28px_rgba(244,63,94,0.42)]",
    frameIdle: "border-slate-200 bg-white/72",
    halo: "from-rose-300/70 via-rose-200/45 to-white/0",
    chapterBg: "bg-[linear-gradient(135deg,rgba(251,113,133,0.16),rgba(255,241,242,0.96),rgba(255,255,255,0.92))]",
    chapterBorder: "border-rose-200/80",
    number: "border-rose-200 bg-rose-100 text-rose-800",
    chapterPill: "border-rose-200 bg-rose-50 text-rose-700",
    progress: "from-rose-500 via-pink-400 to-rose-200",
    railActive: "border-rose-400 bg-rose-950 text-white shadow-[0_18px_40px_-26px_rgba(225,29,72,0.48)]",
    railIdle: "border-rose-100 bg-[linear-gradient(135deg,#ffffff_0%,#fff1f2_100%)] text-slate-900",
  },
  amber: {
    frameActive: "border-amber-300 bg-amber-50/70 shadow-[0_20px_44px_-28px_rgba(245,158,11,0.4)]",
    frameIdle: "border-slate-200 bg-white/72",
    halo: "from-amber-300/70 via-amber-200/45 to-white/0",
    chapterBg: "bg-[linear-gradient(135deg,rgba(251,191,36,0.18),rgba(255,251,235,0.96),rgba(255,255,255,0.92))]",
    chapterBorder: "border-amber-200/80",
    number: "border-amber-200 bg-amber-100 text-amber-800",
    chapterPill: "border-amber-200 bg-amber-50 text-amber-700",
    progress: "from-amber-500 via-orange-400 to-amber-200",
    railActive: "border-amber-400 bg-amber-950 text-white shadow-[0_18px_40px_-26px_rgba(180,83,9,0.48)]",
    railIdle: "border-amber-100 bg-[linear-gradient(135deg,#ffffff_0%,#fffbeb_100%)] text-slate-900",
  },
};

function getAccentMeta(accent = "sky") {
  return ACCENT_META[accent] || ACCENT_META.sky;
}

export function MainlinePanelFrame({
  step,
  title,
  summary,
  active = false,
  accent = "sky",
  panelId = "",
  recentlyJumped = false,
  spotlightTitle = "",
  spotlightDetail = "",
  spotlightTone = "neutral",
  guideSummary = "",
  guideFocus = "",
  guideNextLabel = "",
  guideNextDetail = "",
  guideActionLabel = "",
  onGuideAction,
  children,
}) {
  const accentMeta = getAccentMeta(accent);
  const spotlightStyles = {
    neutral: "border-slate-200 bg-slate-50/90 text-slate-700",
    info: "border-sky-200 bg-sky-50/85 text-sky-900",
    ok: "border-emerald-200 bg-emerald-50/85 text-emerald-900",
    warn: "border-amber-200 bg-amber-50/85 text-amber-900",
  };
  const guideCards = [
    {
      id: "summary",
      eyebrow: "本段讲什么",
      detail: guideSummary,
      tone: "border-slate-200 bg-white/88 text-slate-700",
    },
    {
      id: "focus",
      eyebrow: active ? "为什么现在看" : "为什么要补看",
      detail: guideFocus,
      tone: active ? "border-emerald-200 bg-emerald-50/88 text-emerald-900" : "border-slate-200 bg-slate-50/88 text-slate-700",
    },
    {
      id: "next",
      eyebrow: guideNextLabel || "下一段去哪",
      detail: guideNextDetail,
      tone: "border-sky-200 bg-sky-50/88 text-sky-900",
      actionLabel: guideActionLabel,
      onAction: onGuideAction,
    },
  ].filter((item) => item.detail || item.actionLabel);

  return (
    <div
      id={panelId || undefined}
      className={cn(
        "cg-scroll-target relative overflow-hidden rounded-[30px] border p-2 transition",
        active ? "cg-focus-block" : "",
        active ? accentMeta.frameActive : accentMeta.frameIdle
      )}
    >
      <div className={cn("pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-r opacity-80", accentMeta.halo)} />
      <div className={cn("relative mx-2 mt-2 rounded-[26px] border px-4 py-4 shadow-sm", accentMeta.chapterBorder, accentMeta.chapterBg)}>
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={cn("rounded-2xl border px-3 py-2 text-sm font-black", accentMeta.number)}>{step}</span>
              <span className={cn("rounded-full border px-3 py-1 text-[11px] font-black uppercase tracking-[0.18em]", accentMeta.chapterPill)}>
                主线章节
              </span>
              <TagPill tone={active ? "ok" : "neutral"}>{active ? "当前联动中" : "等待焦点命中"}</TagPill>
              {recentlyJumped ? <TagPill tone="warn">刚刚定位到这里</TagPill> : null}
            </div>
            <p className="mt-4 text-xl font-black tracking-tight text-slate-950">{title}</p>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{summary}</p>
          </div>

          <div className="min-w-[12rem] rounded-2xl border border-white/80 bg-white/85 px-4 py-3 shadow-sm">
            <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">阅读状态</p>
            <p className="mt-2 text-sm font-black text-slate-950">{active ? "当前建议重点讲这一段" : "当前可作为后续展开段"}</p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/90">
              <div
                className={cn(
                  "h-full rounded-full bg-gradient-to-r transition-all",
                  accentMeta.progress,
                  active ? "w-full" : recentlyJumped ? "w-4/5" : "w-1/3"
                )}
              />
            </div>
          </div>
        </div>
      </div>
      {spotlightTitle || spotlightDetail ? (
        <div className={cn("mx-2 mb-3 rounded-2xl border px-4 py-3 shadow-sm", spotlightStyles[spotlightTone] || spotlightStyles.neutral)}>
          <div className="flex flex-wrap items-center gap-2">
            <TagPill tone={recentlyJumped ? "warn" : active ? "ok" : "neutral"}>
              {recentlyJumped ? "刚刚跳转到此主线段" : active ? "当前焦点正在这里" : "可作为主线入口"}
            </TagPill>
            {panelId ? <TagPill tone="neutral">{panelId.replace("mainline-panel-", "")}</TagPill> : null}
          </div>
          {spotlightTitle ? <p className="mt-2 text-sm font-black">{spotlightTitle}</p> : null}
          {spotlightDetail ? <p className="mt-2 text-sm leading-6">{spotlightDetail}</p> : null}
        </div>
      ) : null}
      <div className="relative">{children}</div>
      {guideCards.length ? (
        <div className="relative mx-2 mb-2 mt-3 rounded-[26px] border border-slate-200 bg-[linear-gradient(135deg,rgba(255,255,255,0.92),rgba(248,250,252,0.92),rgba(241,245,249,0.96))] p-4 shadow-sm">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <TagPill tone={active ? "ok" : "neutral"}>{active ? "主线讲解中" : "主线过渡提示"}</TagPill>
            <TagPill tone="neutral">章节收口条</TagPill>
          </div>
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
            {guideCards.map((item) => (
              <div key={item.id} className={cn("rounded-2xl border px-4 py-4 shadow-sm", item.tone)}>
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">{item.eyebrow}</p>
                {item.detail ? <p className="mt-2 text-sm leading-6">{item.detail}</p> : null}
                {item.actionLabel ? (
                  <button
                    type="button"
                    onClick={() => item.onAction?.()}
                    className={cn(
                      "mt-4 rounded-full border px-4 py-2 text-sm font-black transition focus:outline-none focus:ring-2 focus:ring-sky-300",
                      active
                        ? "border-slate-900 bg-slate-950 text-white hover:bg-slate-900"
                        : "border-slate-300 bg-white text-slate-700 hover:border-slate-400"
                    )}
                  >
                    {item.actionLabel}
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function MainlinePanelRail({
  workflowProgress,
  replayScope,
  attackLoop,
  codeArtifacts,
  flowPanelActive,
  replayPanelActive,
  attackPanelActive,
  dispatcherPanelActive,
  onJumpToPanel,
}) {
  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const focusedServiceRef = normalizeRef(replayScope?.targetServiceRef);
  const stageItem = (workflowProgress || []).find((item) => normalizeRef(item?.phase) === focusedStageRef) || null;
  const currentRound = attackLoop?.current_round || {};
  const currentRoundLabel = currentRound?.round_index ? `第 ${currentRound.round_index} 轮` : "等待攻击轮次";
  const codeReadyCount = [codeArtifacts?.pseudocode_ready, codeArtifacts?.python_ready, codeArtifacts?.c_ready].filter(Boolean).length;
  const railItems = [
    {
      id: "flow",
      step: "01",
      title: "流程透明化",
      detail: stageItem?.label || (focusedStageRef ? focusedStageRef : "默认全流程"),
      active: flowPanelActive,
      accent: "sky",
      panelId: "mainline-panel-flow",
    },
    {
      id: "replay",
      step: "02",
      title: "Replay 深钻",
      detail: focusedServiceRef ? "已锁定目标服务回看" : "等待回看焦点",
      active: replayPanelActive,
      accent: "cyan",
      panelId: "mainline-panel-replay",
    },
    {
      id: "attack",
      step: "03",
      title: "攻击闭环",
      detail: currentRoundLabel,
      active: attackPanelActive,
      accent: "rose",
      panelId: "mainline-panel-attack",
    },
    {
      id: "dispatch",
      step: "04",
      title: "执行平面",
      detail: codeReadyCount ? `${codeReadyCount} 类代码交付已就绪` : "等待交付代码稳定",
      active: dispatcherPanelActive,
      accent: "amber",
      panelId: "mainline-panel-dispatch",
    },
  ];

  return (
    <Panel
      title="主线联动轨道"
      subtitle="这条轨道把最关键的四个面板串起来，当前焦点命中的位置会在整页上一并亮起来。"
      className="xl:col-span-2"
    >
      <div className="rounded-[30px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_40%,#eef6ff_100%)] p-4 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <TagPill tone="neutral">四段主线章节</TagPill>
          <TagPill tone={flowPanelActive || replayPanelActive || attackPanelActive || dispatcherPanelActive ? "ok" : "neutral"}>
            {flowPanelActive || replayPanelActive || attackPanelActive || dispatcherPanelActive ? "当前已命中主线章节" : "当前为全局总览"}
          </TagPill>
        </div>
        <div className="flex flex-col gap-3 xl:flex-row xl:items-stretch">
          {railItems.map((item, index) => {
            const accentMeta = getAccentMeta(item.accent);
            return (
            <div key={item.id} className="flex flex-1 items-stretch gap-3">
              <button
                type="button"
                onClick={() => onJumpToPanel?.(item.panelId)}
                className={cn(
                  "min-w-0 flex-1 rounded-[24px] border px-4 py-4 text-left transition focus:outline-none focus:ring-2 focus:ring-sky-300",
                  item.active ? accentMeta.railActive : accentMeta.railIdle
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={cn(
                      "rounded-2xl border px-3 py-2 text-sm font-black",
                      item.active ? "border-white/20 bg-white/10 text-white" : accentMeta.number
                    )}
                  >
                    {item.step}
                  </span>
                  <p className={cn("text-sm font-black", item.active ? "text-white" : "text-slate-900")}>{item.title}</p>
                </div>
                <p className={cn("mt-2 text-sm leading-6", item.active ? "text-slate-100" : "text-slate-600")}>{item.detail}</p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/70">
                  <div
                    className={cn(
                      "h-full rounded-full bg-gradient-to-r transition-all",
                      accentMeta.progress,
                      item.active ? "w-full" : "w-2/5"
                    )}
                  />
                </div>
                <p className={cn("mt-3 text-xs font-semibold uppercase tracking-[0.16em]", item.active ? "text-slate-300" : "text-slate-400")}>
                  点击跳转到对应主线面板
                </p>
              </button>
              {index < railItems.length - 1 ? (
                <div className="hidden items-center justify-center xl:flex">
                  <div className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-black text-slate-400 shadow-sm">
                    -&gt;
                  </div>
                </div>
              ) : null}
            </div>
          );
          })}
        </div>
      </div>
    </Panel>
  );
}

export function MainlinePositionBar({
  replayScope,
  flowPanelActive,
  replayPanelActive,
  attackPanelActive,
  dispatcherPanelActive,
  onJumpToPanel,
  jumpedPanelId,
}) {
  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const focusedServiceRef = normalizeRef(replayScope?.targetServiceRef);
  const activePanels = [
    flowPanelActive ? "流程透明化" : null,
    replayPanelActive ? "Replay 深钻" : null,
    attackPanelActive ? "攻击闭环" : null,
    dispatcherPanelActive ? "执行平面" : null,
  ].filter(Boolean);
  const positionSummary = focusedStageRef
    ? `当前阶段焦点：${focusedStageRef}`
    : focusedServiceRef
      ? `当前目标服务焦点：${focusedServiceRef}`
      : "当前仍在全局总览模式";
  const navItems = [
    { id: "mainline-panel-flow", label: "流程透明化", active: flowPanelActive },
    { id: "mainline-panel-replay", label: "Replay 深钻", active: replayPanelActive },
    { id: "mainline-panel-attack", label: "攻击闭环", active: attackPanelActive },
    { id: "mainline-panel-dispatch", label: "执行平面", active: dispatcherPanelActive },
  ];
  const jumpedPanelLabel = navItems.find((item) => item.id === jumpedPanelId)?.label || "";
  const activePriorityPanel =
    navItems.find((item) => item.active) ||
    navItems.find((item) => item.id === jumpedPanelId) ||
    navItems[0];
  const readingHint = jumpedPanelLabel
    ? `刚刚已定位到 ${jumpedPanelLabel}，现在可以顺着这一块继续往下讲。`
    : activePriorityPanel?.active
      ? `当前建议优先阅读 ${activePriorityPanel.label}，它已经命中本轮主线焦点。`
      : "当前还在整页总览模式，可先从流程透明化开始，再顺着主线往后阅读。";

  return (
    <div className="xl:col-span-2">
      <div className="sticky top-4 z-10 rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,rgba(255,255,255,0.96),rgba(248,250,252,0.92),rgba(239,246,255,0.95))] px-4 py-4 shadow-[0_18px_40px_-28px_rgba(15,23,42,0.22)] backdrop-blur">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-500">Mainline Position</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">{positionSummary}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {activePanels.length ? (
                activePanels.map((item) => (
                  <TagPill key={`active-panel-${item}`} tone="ok">
                    {item}
                  </TagPill>
                ))
              ) : (
                <TagPill tone="neutral">当前未锁定主线焦点</TagPill>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {focusedStageRef ? <ReplayFocusPill kind="stageRef" value={focusedStageRef} active /> : null}
            {focusedServiceRef ? <ReplayFocusPill kind="targetServiceRef" value={focusedServiceRef} active /> : null}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onJumpToPanel?.(item.id)}
              className={cn(
                "rounded-full border px-4 py-2 text-sm font-bold transition focus:outline-none focus:ring-2 focus:ring-sky-300",
                jumpedPanelId === item.id
                  ? "border-amber-300 bg-amber-50 text-amber-900 shadow-sm"
                  : item.active
                    ? "border-slate-900 bg-slate-950 text-white shadow-sm"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="mt-4 rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <TagPill tone={jumpedPanelLabel ? "warn" : activePriorityPanel?.active ? "ok" : "neutral"}>
              {jumpedPanelLabel ? "最近一次跳转" : activePriorityPanel?.active ? "当前阅读建议" : "默认阅读路径"}
            </TagPill>
            {jumpedPanelLabel ? <TagPill tone="neutral">{jumpedPanelLabel}</TagPill> : null}
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-700">{readingHint}</p>
        </div>
      </div>
    </div>
  );
}
