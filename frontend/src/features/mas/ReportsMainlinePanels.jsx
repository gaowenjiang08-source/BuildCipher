import { Panel } from "../../components/Panel";
import { SemanticPill, TagPill } from "../../components/SemanticPill";
import { ReplayFocusPill } from "./ReplayFocusPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function normalizeRef(value) {
  return String(value || "").trim();
}

function getAttackLoopTargetService(target = {}, fallbackRef = "") {
  return {
    ref: normalizeRef(target?.service_id || target?.service_ref || fallbackRef),
    label: target?.service_name || target?.service_label || normalizeRef(target?.service_id || target?.service_ref || fallbackRef) || "--",
    version: target?.service_version || "",
  };
}

function getLaunchDecision(delivery = {}, auditorRounds = []) {
  const status = String(delivery?.status || "").toLowerCase();
  const latestRound = [...(auditorRounds || [])].reverse()[0] || null;
  const compliance = Number(delivery?.compliance_score ?? latestRound?.compliance_score);
  const risk = Number(delivery?.risk_score ?? latestRound?.risk_score);

  if (["approved", "accept", "accepted", "pass", "passed", "ready"].some((item) => status.includes(item))) {
    return {
      label: "建议进入上线评审",
      tone: "ok",
      summary: "当前交付已达到可进入人工复核与上线评审的状态，下一步应聚焦部署检查、密钥治理和审计留痕落地。",
    };
  }

  if (["reject", "rejected", "fail", "failed", "blocked"].some((item) => status.includes(item))) {
    return {
      label: "暂不建议上线",
      tone: "bad",
      summary: "当前方案仍被审计门槛拦截，应优先解决最新审计轮次中的合规、风险与后量子要求后再继续推进。",
    };
  }

  if (Number.isFinite(compliance) && compliance >= 80 && Number.isFinite(risk) && risk <= 30) {
    return {
      label: "建议进入人工复核",
      tone: "warn",
      summary: "关键分数已接近可交付区间，但仍建议保留人工密码学复核与上线前检查，不直接视为可投产。",
    };
  }

  return {
    label: "需要继续整改",
    tone: "warn",
    summary: "交付处于整改阶段，请处理阻塞项后再进入上线评审。",
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
      summary: `当前共享阶段焦点为 ${focusedStageRef}，它属于攻击闭环主链，因此本面板已经成为该阶段的主要解释视图。`,
    };
  }

  return {
    tone: "warn",
    label: "当前阶段偏离攻击闭环主链",
    summary: `当前共享阶段焦点为 ${focusedStageRef}，但它更偏控制/上下文阶段，因此攻击闭环面板此时只作为辅助观察视图。`,
  };
}

const MAINLINE_STORY_TONES = {
  case: {
    card: "border-slate-200 bg-white/92",
    chip: "border-slate-200 bg-slate-50 text-slate-700",
    activeCard: "border-slate-900 bg-slate-950 text-white shadow-[0_18px_40px_-26px_rgba(15,23,42,0.48)]",
    activeChip: "border-white/20 bg-white/10 text-white",
  },
  decision: {
    card: "border-emerald-200 bg-emerald-50/92",
    chip: "border-emerald-200 bg-emerald-100 text-emerald-700",
    activeCard: "border-emerald-400 bg-emerald-950 text-white shadow-[0_18px_40px_-26px_rgba(5,150,105,0.48)]",
    activeChip: "border-white/20 bg-white/10 text-white",
  },
  focus: {
    card: "border-sky-200 bg-sky-50/92",
    chip: "border-sky-200 bg-sky-100 text-sky-700",
    activeCard: "border-sky-400 bg-sky-950 text-white shadow-[0_18px_40px_-26px_rgba(2,132,199,0.48)]",
    activeChip: "border-white/20 bg-white/10 text-white",
  },
  attack: {
    card: "border-rose-200 bg-rose-50/92",
    chip: "border-rose-200 bg-rose-100 text-rose-700",
    activeCard: "border-rose-400 bg-rose-950 text-white shadow-[0_18px_40px_-26px_rgba(225,29,72,0.45)]",
    activeChip: "border-white/20 bg-white/10 text-white",
  },
  delivery: {
    card: "border-violet-200 bg-violet-50/92",
    chip: "border-violet-200 bg-violet-100 text-violet-700",
    activeCard: "border-violet-400 bg-violet-950 text-white shadow-[0_18px_40px_-26px_rgba(109,40,217,0.45)]",
    activeChip: "border-white/20 bg-white/10 text-white",
  },
};

function StoryChip({ label, active = false, tone = "case" }) {
  const toneMeta = MAINLINE_STORY_TONES[tone] || MAINLINE_STORY_TONES.case;
  return (
    <span className={cn("rounded-full border px-3 py-1 text-[11px] font-black uppercase tracking-[0.16em]", active ? toneMeta.activeChip : toneMeta.chip)}>
      {label}
    </span>
  );
}

function StoryCard({ item, compact = false }) {
  const toneMeta = MAINLINE_STORY_TONES[item.tone] || MAINLINE_STORY_TONES.case;
  return (
    <div className={cn("min-w-0 rounded-[24px] border px-4 py-4 shadow-sm transition", item.active ? toneMeta.activeCard : toneMeta.card)}>
      <div className="flex flex-wrap items-center gap-2">
        <StoryChip label={item.step} active={item.active} tone={item.tone} />
        {item.tag ? <StoryChip label={item.tag} active={item.active} tone={item.tone} /> : null}
      </div>
      <p className={cn("mt-3 text-sm font-black", item.active ? "text-white" : "text-slate-900")}>{item.title}</p>
      <p className={cn("mt-2 text-lg font-black", item.active ? "text-white" : "text-slate-950")}>{item.value}</p>
      <p className={cn("mt-2 text-sm leading-6", item.active ? "text-slate-200" : "text-slate-600")}>{item.detail}</p>
      {!compact && item.hint ? (
        <p className={cn("mt-3 text-xs font-semibold uppercase tracking-[0.16em]", item.active ? "text-slate-300" : "text-slate-400")}>
          {item.hint}
        </p>
      ) : null}
    </div>
  );
}

function StoryConnector() {
  return (
    <div className="hidden items-center justify-center xl:flex">
      <div className="flex items-center gap-2 text-slate-400">
        <span className="h-px w-5 bg-slate-300" />
        <span className="rounded-full border border-slate-200 bg-white px-2 py-1 text-xs font-black">-&gt;</span>
        <span className="h-px w-5 bg-slate-300" />
      </div>
    </div>
  );
}

function SnapshotMetricCard({ item }) {
  return (
    <div className={cn("rounded-[24px] border px-4 py-4 shadow-sm", item.toneClass)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">{item.eyebrow}</p>
        {item.statusLabel ? <TagPill tone={item.statusTone || "neutral"}>{item.statusLabel}</TagPill> : null}
      </div>
      <p className="mt-2 text-lg font-black text-slate-950">{item.value}</p>
      <p className="mt-2 text-sm leading-6 text-slate-700">{item.detail}</p>
    </div>
  );
}

function PresentationActionCard({ item, index }) {
  return (
    <button
      type="button"
      onClick={item.action}
      className={cn(
        "w-full rounded-[24px] border px-4 py-4 text-left transition hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-sky-300",
        item.toneClass || "border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_100%)] hover:border-slate-300"
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/80 bg-white/90 text-xs font-black text-slate-700">
            {String(index + 1).padStart(2, "0")}
          </span>
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">
              {item.eyebrow || "推荐路径"}
            </p>
            <p className="mt-1 text-sm font-black text-slate-950">{item.label}</p>
          </div>
        </div>
        <TagPill tone={item.statusTone || "neutral"}>{item.statusLabel || "点击跳转"}</TagPill>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600">{item.detail}</p>
      <p className="mt-3 text-xs font-bold text-slate-500">{item.ctaLabel || "进入对应章节"}</p>
    </button>
  );
}

export function ReportsMainlineOverviewPanel({
  currentCaseId,
  delivery,
  auditorRounds,
  workflowProgress,
  replayScope,
  attackLoop,
  codeArtifacts,
}) {
  const launchDecision = getLaunchDecision(delivery, auditorRounds);
  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const focusedServiceRef = normalizeRef(replayScope?.targetServiceRef);
  const stageItem = (workflowProgress || []).find((item) => normalizeRef(item?.phase) === focusedStageRef) || null;
  const currentRound = attackLoop?.current_round || {};
  const targetServiceInfo = getAttackLoopTargetService(
    attackLoop?.target_service || {},
    currentRound?.target_service_ref || attackLoop?.target_service_ref
  );
  const codeReady = [
    codeArtifacts?.pseudocode_ready ? "伪代码" : null,
    codeArtifacts?.python_ready ? "Python 代码" : null,
    codeArtifacts?.c_ready ? "C/C++" : null,
  ].filter(Boolean);
  const attackStageSummary = buildAttackStageFocusSummary(focusedStageRef);
  const currentRoundLabel = currentRound?.round_index ? `第 ${currentRound.round_index} 轮` : "等待进入攻击轮次";
  const overviewCards = [
    {
      id: "case",
      step: "01",
      title: "项目",
      value: currentCaseId || "未绑定项目",
      detail: "当前报告与项目级记忆、回放轨迹和交付历史共用同一条 case 主线。",
      tone: "case",
      active: Boolean(currentCaseId),
      tag: currentCaseId ? "主线已绑定" : "等待项目",
      hint: "项目记忆 / 回放 / 交付历史",
    },
    {
      id: "decision",
      step: "02",
      title: "审计判定",
      value: launchDecision.label,
      detail: launchDecision.summary,
      tone: launchDecision.tone === "bad" ? "attack" : "decision",
      active: true,
      tag: launchDecision.tone === "ok" ? "建议推进" : launchDecision.tone === "bad" ? "需阻断" : "待复核",
      hint: "合规 / 风险 / 上线评审",
    },
    {
      id: "stage",
      step: "03",
      title: "当前焦点",
      value: stageItem?.label || (focusedStageRef ? focusedStageRef : "默认全流程观察"),
      detail: stageItem?.owner || attackStageSummary.summary,
      tone: "focus",
      active: Boolean(focusedStageRef || focusedServiceRef),
      tag: focusedStageRef ? "阶段焦点" : focusedServiceRef ? "服务焦点" : "全局模式",
      hint: "共享观察焦点",
    },
    {
      id: "attack",
      step: "04",
      title: "攻击闭环",
      value: currentRoundLabel,
      detail: targetServiceInfo.label ? `当前目标服务：${targetServiceInfo.label}` : "尚未锁定目标服务",
      tone: "attack",
      active: Boolean(targetServiceInfo.ref || attackLoop?.loop_status),
      tag: attackLoop?.loop_status || "待进入闭环",
      hint: "攻击 / 评估 / 修补",
    },
    {
      id: "delivery",
      step: "05",
      title: "代码交付",
      value: codeReady.length ? "可生成交付代码" : "待补齐交付代码",
      detail: codeReady.length ? codeReady.join(" / ") : "暂无稳定代码交付物。",
      tone: "delivery",
      active: Boolean(codeReady.length),
      tag: codeReady.length ? `${codeReady.length} 类交付` : "尚未就绪",
      hint: "伪代码 / Python / C/C++",
    },
  ];

  return (
    <Panel
      title="整页主线总览"
      subtitle="查看项目主线、审计判定、攻击闭环与交付状态。"
      className="xl:col-span-2"
    >
      <div className="rounded-[30px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_42%,#eef2ff_100%)] p-5 shadow-sm">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-500">报告主线地图</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {focusedStageRef || focusedServiceRef
                ? "当前报告已经进入共享焦点驱动模式，下面各面板会围绕同一条阶段或目标服务主线展开。"
                : "当前报告处于总览模式。"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <TagPill tone={focusedStageRef || focusedServiceRef ? "ok" : "neutral"}>
              {focusedStageRef || focusedServiceRef ? "已进入焦点主线" : "当前为全局总览"}
            </TagPill>
            {focusedStageRef ? <ReplayFocusPill kind="stageRef" value={focusedStageRef} active /> : null}
            {focusedServiceRef ? <ReplayFocusPill kind="targetServiceRef" value={focusedServiceRef} active /> : null}
          </div>
        </div>

        <div className="mt-4 rounded-[26px] border border-white/70 bg-white/65 p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <TagPill tone="neutral">五段路线</TagPill>
            <TagPill tone={focusedStageRef || focusedServiceRef ? "ok" : "neutral"}>
              {focusedStageRef || focusedServiceRef ? "当前已进入焦点模式" : "当前显示整体全貌"}
            </TagPill>
            {focusedStageRef ? <ReplayFocusPill kind="stageRef" value={focusedStageRef} active /> : null}
            {focusedServiceRef ? <ReplayFocusPill kind="targetServiceRef" value={focusedServiceRef} active /> : null}
          </div>
          <div className="mt-4 flex flex-col gap-3 xl:flex-row xl:items-stretch">
            {overviewCards.map((card, index) => (
            <div key={card.id} className="flex flex-1 items-stretch gap-3">
              <StoryCard item={card} />
              {index < overviewCards.length - 1 ? <StoryConnector /> : null}
            </div>
          ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}

export function ReportsHeroBanner({
  currentCaseId,
  currentCaseSummary,
  delivery,
  auditorRounds,
  workflowProgress,
  replayScope,
  attackLoop,
  codeArtifacts,
  selectedEvidence,
  selectedProposalId,
  selectedDeliveryFragmentId,
  onJumpToMainlinePanel,
  onJumpToSection,
}) {
  const launchDecision = getLaunchDecision(delivery, auditorRounds);
  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const focusedServiceRef = normalizeRef(replayScope?.targetServiceRef);
  const stageItem = (workflowProgress || []).find((item) => normalizeRef(item?.phase) === focusedStageRef) || null;
  const currentRound = attackLoop?.current_round || {};
  const targetServiceInfo = getAttackLoopTargetService(
    attackLoop?.target_service || {},
    currentRound?.target_service_ref || attackLoop?.target_service_ref
  );
  const codeReady = [
    codeArtifacts?.pseudocode_ready ? "伪代码" : null,
    codeArtifacts?.python_ready ? "Python 代码" : null,
    codeArtifacts?.c_ready ? "C/C++" : null,
  ].filter(Boolean);
  const currentRoundLabel = currentRound?.round_index ? `第 ${currentRound.round_index} 轮` : "等待进入攻击轮次";
  const caseStatusLabel = currentCaseSummary?.status_label || currentCaseSummary?.status || "进行中";
  const heroSummary = focusedStageRef || focusedServiceRef
    ? "当前报告已经进入焦点驱动模式。"
    : "当前报告处于总览模式。";
  const focusLabel = stageItem?.label || focusedStageRef || (focusedServiceRef ? "目标服务焦点已锁定" : "当前为全局总览");
  const actionItems = [
    {
      id: "mainline-panel-flow",
      eyebrow: "开场路径",
      label: "查看流程",
      detail: "上下文窗口、流程轨迹和结构化交接。",
      toneClass: "border-sky-200 bg-[linear-gradient(135deg,#ffffff_0%,#f0f9ff_100%)] hover:border-sky-300",
      statusTone: "ok",
      statusLabel: "建议第一跳",
      ctaLabel: "查看流程",
      action: () => onJumpToMainlinePanel?.("mainline-panel-flow"),
    },
    {
      id: "mainline-panel-attack",
      eyebrow: "技术核心",
      label: "转到攻击闭环",
      detail: "攻击轮次、漏洞评估与修补结果。",
      toneClass: "border-rose-200 bg-[linear-gradient(135deg,#ffffff_0%,#fff1f2_100%)] hover:border-rose-300",
      statusTone: "warn",
      statusLabel: "主实验段",
      ctaLabel: "跳到攻击闭环",
      action: () => onJumpToMainlinePanel?.("mainline-panel-attack"),
    },
    {
      id: "reports-section-delivery",
      eyebrow: "结尾收口",
      label: "收口到最终交付",
      detail: "最终方案、交付片段、导出物和历史回放。",
      toneClass: "border-emerald-200 bg-[linear-gradient(135deg,#ffffff_0%,#ecfdf5_100%)] hover:border-emerald-300",
      statusTone: "ok",
      statusLabel: "收尾段",
      ctaLabel: "跳到最终交付",
      action: () => onJumpToSection?.("reports-section-delivery"),
    },
  ];
  const metricCards = [
    {
      id: "decision",
      eyebrow: "交付判定",
      value: launchDecision.label,
      detail: launchDecision.summary,
      toneClass:
        launchDecision.tone === "ok"
          ? "border-emerald-300/70 bg-emerald-50/90"
          : launchDecision.tone === "bad"
            ? "border-rose-300/70 bg-rose-50/90"
            : "border-amber-300/70 bg-amber-50/90",
      statusTone: launchDecision.tone === "bad" ? "bad" : launchDecision.tone === "ok" ? "ok" : "warn",
      statusLabel: launchDecision.tone === "ok" ? "可推进" : launchDecision.tone === "bad" ? "需阻断" : "待复核",
    },
    {
      id: "focus",
      eyebrow: "当前焦点",
      value: focusLabel,
      detail: focusedServiceRef
        ? `目标服务：${focusedServiceRef}`
        : focusedStageRef
          ? `阶段标识：${focusedStageRef}`
          : "尚未锁定具体焦点。",
      toneClass: focusedStageRef || focusedServiceRef ? "border-sky-300/70 bg-sky-50/90" : "border-slate-200 bg-white/90",
      statusTone: focusedStageRef || focusedServiceRef ? "ok" : "neutral",
      statusLabel: focusedStageRef || focusedServiceRef ? "已锁定" : "全局模式",
    },
    {
      id: "attack",
      eyebrow: "攻击闭环",
      value: currentRoundLabel,
      detail: targetServiceInfo.label ? `目标服务：${targetServiceInfo.label}` : "当前尚未锁定目标服务",
      toneClass: targetServiceInfo.ref ? "border-cyan-300/70 bg-cyan-50/90" : "border-slate-200 bg-white/90",
      statusTone: targetServiceInfo.ref ? "ok" : "neutral",
      statusLabel: targetServiceInfo.ref ? "目标已锁定" : "待进入闭环",
    },
    {
      id: "delivery",
      eyebrow: "代码交付",
      value: codeReady.length ? `${codeReady.length} 类交付已就绪` : "代码交付待补齐",
      detail: codeReady.length ? codeReady.join(" / ") : "暂无稳定代码交付物。",
      toneClass: codeReady.length ? "border-violet-300/70 bg-violet-50/90" : "border-slate-200 bg-white/90",
      statusTone: codeReady.length ? "ok" : "neutral",
      statusLabel: codeReady.length ? "可导出" : "待生成",
    },
  ];
  const heroStoryCards = [
    {
      id: "case",
      step: "01",
      title: "项目",
      value: currentCaseId || "未绑定项目",
      detail: currentCaseSummary?.scenario || currentCaseSummary?.requirement_summary || "当前报告已对齐项目级记忆、回放轨迹与交付历史。",
      tone: "case",
      active: Boolean(currentCaseId),
      tag: caseStatusLabel,
      hint: "项目背景",
    },
    {
      id: "decision",
      step: "02",
      title: "审计",
      value: launchDecision.label,
      detail: launchDecision.summary,
      tone: launchDecision.tone === "bad" ? "attack" : "decision",
      active: true,
      tag: launchDecision.tone === "ok" ? "建议推进" : launchDecision.tone === "bad" ? "需要阻断" : "待复核",
      hint: "结论判断",
    },
    {
      id: "focus",
      step: "03",
      title: "焦点",
      value: focusLabel,
      detail: heroSummary,
      tone: "focus",
      active: Boolean(focusedStageRef || focusedServiceRef),
      tag: focusedStageRef || focusedServiceRef ? "已锁定" : "全局总览",
      hint: "主线定位",
    },
    {
      id: "attack",
      step: "04",
      title: "攻击",
      value: currentRoundLabel,
      detail: targetServiceInfo.label ? `目标服务：${targetServiceInfo.label}` : "尚未锁定目标服务",
      tone: "attack",
      active: Boolean(targetServiceInfo.ref || attackLoop?.loop_status),
      tag: attackLoop?.loop_status || "待进入闭环",
      hint: "闭环阶段",
    },
    {
      id: "delivery",
      step: "05",
      title: "交付",
      value: codeReady.length ? `${codeReady.length} 类交付已就绪` : "代码交付待补齐",
      detail: codeReady.length ? codeReady.join(" / ") : "暂无稳定代码交付物。",
      tone: "delivery",
      active: Boolean(codeReady.length),
      tag: codeReady.length ? "可导出" : "待生成",
      hint: "交付收口",
    },
  ];

  return (
    <section className="xl:col-span-2">
      <div className="relative overflow-hidden rounded-[36px] border border-slate-200 bg-[radial-gradient(circle_at_top_left,rgba(251,191,36,0.18),transparent_24%),radial-gradient(circle_at_88%_8%,rgba(14,165,233,0.18),transparent_28%),linear-gradient(140deg,rgba(255,255,255,0.98),rgba(248,250,252,0.96),rgba(238,246,255,0.98))] p-6 shadow-[0_28px_60px_-32px_rgba(15,23,42,0.25)]">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-300/70 to-transparent" />
        <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[1.25fr_1fr]">
          <div className="rounded-[28px] border border-white/70 bg-white/82 p-5 shadow-sm backdrop-blur">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="neutral">报告封面入口</TagPill>
              <TagPill tone={focusedStageRef || focusedServiceRef ? "ok" : "neutral"}>
                {focusedStageRef || focusedServiceRef ? "已进入焦点模式" : "当前为全局总览"}
              </TagPill>
              <TagPill tone={selectedEvidence || selectedProposalId ? "ok" : "neutral"}>
                {selectedEvidence || selectedProposalId ? "证据链已联动" : "证据链待展开"}
              </TagPill>
              <TagPill tone={selectedDeliveryFragmentId ? "warn" : "neutral"}>
                {selectedDeliveryFragmentId ? "交付片段已锁定" : "交付片段待锁定"}
              </TagPill>
            </div>

            <div className="mt-5 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div className="max-w-3xl">
                <p className="text-[11px] font-black uppercase tracking-[0.28em] text-slate-500">报告首页摘要</p>
                <h1 className="mt-3 max-w-4xl text-3xl font-black tracking-tight text-slate-950 md:text-4xl">
                  企业密码方案多 Agent 审计报告
                </h1>
                <p className="mt-3 text-sm leading-7 text-slate-600 md:text-base">
                  查看项目背景、主线流程、攻击闭环、证据链和最终交付。
                </p>
              </div>
              <div className="rounded-3xl border border-slate-200 bg-slate-950 px-5 py-4 text-white shadow-sm">
                <p className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-300">项目摘要</p>
                <p className="mt-2 text-lg font-black">{currentCaseId || "未绑定项目"}</p>
                <p className="mt-2 text-sm text-slate-200">
                  {currentCaseSummary?.scenario || currentCaseSummary?.requirement_summary || "当前报告已对齐项目级记忆、回放轨迹与交付历史。"}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <TagPill tone="neutral">{caseStatusLabel}</TagPill>
                  {currentCaseSummary?.decision_count ? <TagPill tone="neutral">{`${currentCaseSummary.decision_count} 条决策记录`}</TagPill> : null}
                </div>
              </div>
            </div>

            <div className="mt-5 rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,rgba(248,250,252,0.94),rgba(255,255,255,0.92),rgba(239,246,255,0.95))] p-4 shadow-sm">
              <div className="flex flex-wrap items-center gap-2">
                <TagPill tone={launchDecision.tone === "bad" ? "bad" : launchDecision.tone === "ok" ? "ok" : "warn"}>
                  {launchDecision.label}
                </TagPill>
                {focusedStageRef ? <ReplayFocusPill kind="stageRef" value={focusedStageRef} active /> : null}
                {focusedServiceRef ? <ReplayFocusPill kind="targetServiceRef" value={focusedServiceRef} active /> : null}
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-700">{heroSummary}</p>
            </div>

            <div className="mt-5 rounded-[28px] border border-slate-200 bg-white/82 p-4 shadow-sm">
              <div className="flex flex-wrap items-center gap-2">
                <TagPill tone="neutral">报告主线</TagPill>
                <TagPill tone={focusedStageRef || focusedServiceRef ? "ok" : "neutral"}>
                  {focusedStageRef || focusedServiceRef ? "当前已进入焦点模式" : "当前显示全貌"}
                </TagPill>
              </div>
              <div className="mt-4 flex flex-col gap-3 xl:flex-row xl:items-stretch">
                {heroStoryCards.map((item, index) => (
                  <div key={item.id} className="flex flex-1 items-stretch gap-3">
                    <StoryCard item={item} compact />
                    {index < heroStoryCards.length - 1 ? <StoryConnector /> : null}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {metricCards.map((item) => (
                <SnapshotMetricCard key={item.id} item={item} />
              ))}
            </div>

            <div className="rounded-[28px] border border-slate-200 bg-white/88 p-4 shadow-sm">
              <div className="flex flex-wrap items-center gap-2">
                <TagPill tone="neutral">推荐路径</TagPill>
                <TagPill tone="neutral">推荐顺序</TagPill>
              </div>
              <div className="mt-4 space-y-3">
                {actionItems.map((item, index) => (
                  <PresentationActionCard key={item.id} item={item} index={index} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function WorkflowAttackBridgePanel({ workflowProgress, replayScope, attackLoop, codeArtifacts }) {
  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const focusedServiceRef = normalizeRef(replayScope?.targetServiceRef);
  const stageSummary = buildAttackStageFocusSummary(focusedStageRef);
  const stageItem = (workflowProgress || []).find((item) => normalizeRef(item?.phase) === focusedStageRef) || null;
  const currentRound = attackLoop?.current_round || {};
  const targetServiceInfo = getAttackLoopTargetService(
    attackLoop?.target_service || {},
    currentRound?.target_service_ref || attackLoop?.target_service_ref
  );
  const codeReady = [
    codeArtifacts?.pseudocode_ready ? "伪代码" : null,
    codeArtifacts?.python_ready ? "Python 代码" : null,
    codeArtifacts?.c_ready ? "C/C++" : null,
  ].filter(Boolean);
  const currentRoundLabel = currentRound?.round_kind_label || currentRound?.round_kind || "等待攻击轮次";
  const currentRoundIndexLabel = currentRound?.round_index ? `第 ${currentRound.round_index} 轮` : "尚未进入轮次";
  const loopStatusLabel = attackLoop?.loop_status || "待进入攻击闭环";
  const observationSummary = focusedStageRef || focusedServiceRef
    ? "当前正沿共享焦点收口主线。"
    : "当前按默认顺序展示主线。";
  const bridgeCards = [
    {
      id: "stage",
      title: "流程阶段",
      value: stageItem?.label || (focusedStageRef ? focusedStageRef : "未锁定阶段"),
      detail: stageItem?.owner || stageSummary.label,
      toneClass:
        stageSummary.tone === "ok"
          ? "border-sky-200 bg-sky-50/80"
          : stageSummary.tone === "warn"
            ? "border-amber-200 bg-amber-50/80"
            : "border-slate-200 bg-white",
      pills: focusedStageRef ? [<ReplayFocusPill key="stage-ref" kind="stageRef" value={focusedStageRef} active />] : [],
    },
    {
      id: "service",
      title: "目标服务",
      value: targetServiceInfo.label || "未锁定目标服务",
      detail: targetServiceInfo.version || (focusedServiceRef ? "正在跟随共享服务焦点" : "当前以闭环默认目标服务为准"),
      toneClass: focusedServiceRef ? "border-cyan-200 bg-cyan-50/80" : "border-slate-200 bg-white",
      pills: focusedServiceRef
        ? [<ReplayFocusPill key="service-ref" kind="targetServiceRef" value={focusedServiceRef} active />]
        : [],
    },
    {
      id: "round",
      title: "攻击轮次",
      value: currentRoundIndexLabel,
      detail: currentRoundLabel,
      toneClass: "border-rose-200 bg-rose-50/80",
      pills: [<TagPill key="loop-status" tone="ok">{loopStatusLabel}</TagPill>],
    },
    {
      id: "delivery",
      title: "代码交付",
      value: codeReady.length ? "可生成交付代码" : "待补齐代码交付",
      detail: codeReady.length ? codeReady.join(" / ") : "暂无稳定代码交付物",
      toneClass: codeReady.length ? "border-emerald-200 bg-emerald-50/80" : "border-slate-200 bg-white",
      pills: codeReady.length ? [<TagPill key="delivery-ready" tone="ok">{`${codeReady.length} 类交付`}</TagPill>] : [],
    },
  ];

  return (
    <Panel
      title="联动主线与当前观察路径"
      subtitle="查看流程阶段、共享焦点、攻击轮次与代码交付。"
    >
      <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_45%,#eff6ff_100%)] p-5 shadow-sm">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-500">主线联动桥</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">{observationSummary}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <TagPill tone={focusedStageRef || focusedServiceRef ? "ok" : "neutral"}>
              {focusedStageRef || focusedServiceRef ? "已进入联动观察" : "当前为默认主线"}
            </TagPill>
            <TagPill tone="neutral">{loopStatusLabel}</TagPill>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 xl:flex-row xl:items-stretch">
          {bridgeCards.map((card, index) => (
            <div key={card.id} className="flex flex-1 items-stretch gap-3">
              <div className={cn("min-w-0 flex-1 rounded-2xl border px-4 py-4 shadow-sm", card.toneClass)}>
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">{card.title}</p>
                <p className="mt-2 text-lg font-black text-slate-950">{card.value}</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">{card.detail}</p>
                {card.pills.length ? <div className="mt-3 flex flex-wrap gap-2">{card.pills}</div> : null}
              </div>
              {index < bridgeCards.length - 1 ? (
                <div className="hidden items-center justify-center xl:flex">
                  <div className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-black text-slate-400">
                    -&gt;
                  </div>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

export function ReportsEvidenceDeliveryBridgePanel({
  selectedEvidence,
  evidencePack,
  credibilityAssessment,
  delivery,
  finalScheme,
  selectedProposalId,
  selectedDeliveryFragmentId,
  deliveryFragments = [],
  onJumpToSection,
}) {
  const evidenceCount = Array.isArray(evidencePack) ? evidencePack.length : 0;
  const credibilityScore = Number(credibilityAssessment?.credibility_score);
  const deliveryStatus = String(delivery?.status_label || delivery?.status || "").trim() || "待形成明确结论";
  const evidenceFocusLabel =
    selectedEvidence?.title ||
    selectedEvidence?.label ||
    selectedEvidence?.chunk_id ||
    "当前尚未锁定证据焦点";
  const deliveryReadiness =
    finalScheme?.name || selectedDeliveryFragmentId || deliveryFragments.length
      ? "已具备交付收口条件"
      : "仍需继续补齐交付收口";
  const closureSummary = selectedDeliveryFragmentId
    ? "当前已经锁定交付片段。"
    : selectedProposalId
      ? "候选方案已锁定，可查看交付片段。"
      : "请先查看证据与可信度。";
  const bridgeCards = [
    {
      id: "evidence",
      eyebrow: "证据焦点",
      value: selectedEvidence ? "证据已联动" : "证据待展开",
      detail: selectedEvidence ? evidenceFocusLabel : `当前证据包共 ${evidenceCount} 条。`,
      toneClass: selectedEvidence ? "border-emerald-200 bg-emerald-50/85" : "border-slate-200 bg-white",
      pills: [
        <TagPill key="evidence-count" tone="neutral">{`${evidenceCount} 条证据`}</TagPill>,
        selectedEvidence ? <TagPill key="evidence-active" tone="ok">当前已锁定</TagPill> : <TagPill key="evidence-idle" tone="neutral">等待选中</TagPill>,
      ],
    },
    {
      id: "credibility",
      eyebrow: "可信度解释",
      value: Number.isFinite(credibilityScore) ? `${credibilityScore.toFixed(1)} 分` : "待生成评分",
      detail:
        credibilityAssessment?.trust_level_label ||
        credibilityAssessment?.trust_level ||
        "查看可信度评分、优势与缺口摘要。",
      toneClass: Number.isFinite(credibilityScore) ? "border-sky-200 bg-sky-50/85" : "border-slate-200 bg-white",
      pills: [
        credibilityAssessment?.evidence_coverage != null ? (
          <TagPill key="coverage" tone="ok">{`覆盖率 ${credibilityAssessment.evidence_coverage}`}</TagPill>
        ) : (
          <TagPill key="coverage-empty" tone="neutral">覆盖率待评估</TagPill>
        ),
      ],
    },
    {
      id: "delivery",
      eyebrow: "交付收口",
      value: deliveryReadiness,
      detail: finalScheme?.name ? `当前最终方案：${finalScheme.name}` : closureSummary,
      toneClass: finalScheme?.name || selectedDeliveryFragmentId ? "border-violet-200 bg-violet-50/85" : "border-slate-200 bg-white",
      pills: [
        <TagPill key="delivery-status" tone={selectedDeliveryFragmentId ? "warn" : "neutral"}>{deliveryStatus}</TagPill>,
        <TagPill key="fragment-count" tone="neutral">{`${deliveryFragments.length} 个交付片段`}</TagPill>,
      ],
    },
  ];
  const actionItems = [
    {
      id: "credibility",
      label: "可信度摘要",
      detail: "评分、对比图与关键整改项。",
      action: () => onJumpToSection?.("reports-section-credibility"),
    },
    {
      id: "evidence",
      label: "证据包联动",
      detail: "证据、回放、方案选择与交付片段。",
      action: () => onJumpToSection?.("reports-section-evidence-pack"),
    },
    {
      id: "delivery",
      label: "最后收口到交付",
      detail: "展示最终方案、交付片段、导出物和历史回放。",
      action: () => onJumpToSection?.("reports-section-delivery"),
    },
  ];

  return (
    <Panel
      title="证据与交付收口总览"
      subtitle="查看证据命中、可信度解释与最终交付。"
      className="xl:col-span-2"
    >
      <div
        id="reports-section-evidence-bridge"
        className="cg-scroll-target rounded-[30px] border border-emerald-200 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_24%),radial-gradient(circle_at_92%_14%,rgba(59,130,246,0.12),transparent_26%),linear-gradient(135deg,rgba(255,255,255,0.98),rgba(240,253,250,0.96),rgba(248,250,252,0.98))] p-5 shadow-sm"
      >
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="ok">第三章收口桥</TagPill>
              <TagPill tone={selectedEvidence ? "ok" : "neutral"}>{selectedEvidence ? "证据已进入讲解状态" : "证据尚未锁定"}</TagPill>
              <TagPill tone={selectedDeliveryFragmentId ? "warn" : "neutral"}>{selectedDeliveryFragmentId ? "交付片段已锁定" : "交付片段待收口"}</TagPill>
            </div>
            <p className="mt-4 text-2xl font-black tracking-tight text-slate-950">查看可信度与最终交付</p>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              查看证据来源、可信度、候选方案与导出物。
            </p>
          </div>

          <div className="rounded-[24px] border border-white/70 bg-white/88 px-4 py-4 shadow-sm xl:max-w-sm">
            <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">收口提示</p>
            <p className="mt-2 text-sm font-black text-slate-950">{deliveryReadiness}</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">{closureSummary}</p>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-3">
          {bridgeCards.map((card) => (
            <div key={card.id} className={cn("rounded-[24px] border px-4 py-4 shadow-sm", card.toneClass)}>
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">{card.eyebrow}</p>
              <p className="mt-2 text-lg font-black text-slate-950">{card.value}</p>
              <p className="mt-2 text-sm leading-6 text-slate-700">{card.detail}</p>
              <div className="mt-3 flex flex-wrap gap-2">{card.pills}</div>
            </div>
          ))}
        </div>

        <div className="mt-5 rounded-[26px] border border-white/70 bg-white/88 p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <TagPill tone="neutral">推荐收尾路径</TagPill>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-3">
            {actionItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={item.action}
                className="rounded-[22px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_100%)] px-4 py-4 text-left transition hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-300"
              >
                <p className="text-sm font-black text-slate-950">{item.label}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{item.detail}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}
