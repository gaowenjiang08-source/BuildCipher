import {
  BellIcon,
  BriefcaseIcon,
  CheckBadgeIcon,
  ChevronDownIcon,
  CompassIcon,
  CpuIcon,
  ShieldIcon,
  SparkIcon,
  UserCircleIcon,
} from "../../components/Icons";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

const VIEW_TITLES = {
  overview: "工程总览",
  workbench: "项目工作台",
  context: "可信协同",
  validation: "安全验证",
  delivery: "可信交付",
  mission: "专家总览",
  runtime: "运行控制台",
  reports: "专家报告",
  components: "组件库",
  ops: "资产与运维",
  settings: "系统设置",
};

function StatusDot({ tone = "ok" }) {
  const classes = {
    ok: "bg-emerald-500",
    warn: "bg-amber-400",
    bad: "bg-rose-500",
    neutral: "bg-slate-300",
  };

  return <span className={cn("inline-flex h-2.5 w-2.5 rounded-full", classes[tone] || classes.neutral)} />;
}

function resolveTone(value) {
  if (value === "ok") return "ok";
  if (value === "bad") return "bad";
  return "warn";
}

function resolveStatusLabel(value, okLabel) {
  if (value === "ok") return okLabel;
  if (value === "bad") return "异常";
  return "待检查";
}

export default function StudioHeaderView({
  mode,
  view,
  settingsOpen,
  connectionStatus,
  llmStatus,
  activeRunId,
  latestEngineLabel,
  currentCaseSummary,
}) {
  const currentViewTitle = VIEW_TITLES[settingsOpen ? "settings" : view] || "工作台";
  const scenario = currentCaseSummary?.scenario || "面向建筑工程的可信协同、攻防验证与证据化交付平台";
  const owner = currentCaseSummary?.owner || currentCaseSummary?.owner_name || "AC";

  const statusChips = [
    {
      id: "api",
      label: "API",
      value: resolveStatusLabel(connectionStatus, "正常"),
      tone: resolveTone(connectionStatus),
      icon: CheckBadgeIcon,
    },
    {
      id: "llm",
      label: "LLM",
      value: resolveStatusLabel(llmStatus, "正常"),
      tone: resolveTone(llmStatus),
      icon: SparkIcon,
    },
    {
      id: "task",
      label: "任务",
      value: activeRunId ? "运行中" : "待命",
      tone: activeRunId ? "warn" : "ok",
      icon: BriefcaseIcon,
    },
    {
      id: "engine",
      label: "引擎",
      value: latestEngineLabel || "LangGraph 主线",
      tone: "ok",
      icon: CpuIcon,
    },
  ];

  return (
    <header className="overflow-hidden rounded-[32px] border border-[color:var(--cg-border)] bg-[linear-gradient(135deg,rgba(255,255,255,0.95)_0%,rgba(247,250,255,0.95)_52%,rgba(237,245,255,0.92)_100%)] px-5 py-4 shadow-[var(--cg-shadow-panel)] backdrop-blur-xl md:px-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--cg-border)] pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-2 rounded-full border border-[color:var(--cg-accent-border)] bg-[color:var(--cg-accent-fog)] px-3 py-1 text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--cg-accent-strong)]">
            <CompassIcon size={12} />
            Control Surface
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-[color:var(--cg-border)] bg-white/80 px-3 py-1 text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--cg-text-soft)]">
            <StatusDot tone={activeRunId ? "warn" : "ok"} />
            {activeRunId ? "Live Run" : "Ready State"}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold text-[color:var(--cg-text-soft)]">
          <span className="inline-flex items-center gap-2 rounded-full border border-[color:var(--cg-border)] bg-white/80 px-3 py-1.5">
            <BriefcaseIcon size={13} />
            {currentViewTitle}
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-[color:var(--cg-border)] bg-white/80 px-3 py-1.5">
            <SparkIcon size={13} />
            {latestEngineLabel || "LangGraph"}
          </span>
        </div>
      </div>
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-[20px] border border-[color:var(--cg-accent-border)] bg-[linear-gradient(135deg,rgba(37,99,235,0.16)_0%,rgba(186,230,253,0.9)_100%)] text-[color:var(--cg-accent-strong)] shadow-[var(--cg-shadow-glow)]">
            <ShieldIcon size={22} />
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-[1.34rem] font-black tracking-[-0.04em] text-[color:var(--cg-text)] md:text-[1.62rem]">
                BuildTrust Studio
              </p>
              <span className="hidden h-5 w-px bg-[color:var(--cg-border)] md:inline-block" />
              <p className="truncate text-[0.92rem] font-medium text-[color:var(--cg-text-soft)]">{scenario}</p>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-[color:var(--cg-border)] bg-white/90 px-3 py-1 text-xs font-semibold text-[color:var(--cg-text-soft)] shadow-[0_10px_22px_rgba(15,23,42,0.05)]">
                {mode === "business" ? "企业工作台" : "专家工作台"}
              </span>
              <span className="rounded-full border border-[color:var(--cg-border)] bg-white/90 px-3 py-1 text-xs font-semibold text-[color:var(--cg-text-soft)] shadow-[0_10px_22px_rgba(15,23,42,0.05)]">
                当前视图 {currentViewTitle}
              </span>
              <span className="rounded-full border border-[color:var(--cg-border)] bg-white/90 px-3 py-1 text-xs font-semibold text-[color:var(--cg-text-soft)] shadow-[0_10px_22px_rgba(15,23,42,0.05)]">
                负责人 {owner}
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3 xl:items-end">
          <div className="flex flex-wrap items-center gap-2">
            {statusChips.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.id}
                  className="flex items-center gap-2 rounded-full border border-[color:var(--cg-border)] bg-white/90 px-3 py-2 text-xs font-semibold text-[color:var(--cg-text-soft)] shadow-[0_12px_22px_rgba(15,23,42,0.05)]"
                >
                  <StatusDot tone={item.tone} />
                  <Icon size={14} />
                  <span>{item.label}</span>
                  <span className="text-[color:var(--cg-text)]">{item.value}</span>
                </div>
              );
            })}
          </div>

          <div className="flex items-center gap-2 text-[color:var(--cg-text-soft)]">
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[color:var(--cg-border)] bg-white/92 transition hover:translate-y-[-1px] hover:border-[color:var(--cg-border-strong)] hover:shadow-[0_10px_24px_rgba(15,23,42,0.06)]"
            >
              <BellIcon size={18} />
            </button>
            <div className="flex items-center gap-2 rounded-full border border-[color:var(--cg-border)] bg-white/92 px-2 py-1.5 shadow-[0_12px_24px_rgba(15,23,42,0.06)]">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-[linear-gradient(135deg,#1d4ed8_0%,#2563eb_100%)] text-white">
                <UserCircleIcon size={18} />
              </div>
              <div className="pr-1">
                <p className="text-xs font-bold text-[color:var(--cg-text)]">{owner}</p>
                <p className="text-[11px] text-[color:var(--cg-text-soft)]">{mode === "business" ? "业务负责人" : "专家席位"}</p>
              </div>
              <ChevronDownIcon size={16} />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
