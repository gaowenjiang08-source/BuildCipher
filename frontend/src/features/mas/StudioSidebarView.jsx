import {
  BriefcaseIcon,
  CompassIcon,
  CpuIcon,
  GridIcon,
  HomeIcon,
  LayersIcon,
  SettingsIcon,
  ShieldIcon,
  SparkIcon,
} from "../../components/Icons";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

const BUSINESS_NAV_ITEMS = [
  { id: "overview", label: "工程总览", icon: HomeIcon },
  { id: "workbench", label: "项目工作台", icon: BriefcaseIcon },
  { id: "context", label: "可信协同", icon: LayersIcon },
  { id: "validation", label: "攻防验证", icon: ShieldIcon },
  { id: "delivery", label: "交付中心", icon: SparkIcon },
];

const EXPERT_NAV_ITEMS = [
  { id: "mission", label: "专家总览", icon: CompassIcon },
  { id: "runtime", label: "运行控制台", icon: CpuIcon },
  { id: "reports", label: "专家报告", icon: LayersIcon },
  { id: "workbench", label: "执行工作台", icon: BriefcaseIcon },
  { id: "ops", label: "资产与运维", icon: SettingsIcon },
];

export default function StudioSidebarView({
  mode,
  view,
  setView,
  settingsOpen,
  setSettingsOpen,
  onOpenOverview,
  onOpenProject,
  onOpenContext,
  onOpenValidation,
  onOpenDelivery,
  onOpenComponents,
  onSwitchToBusiness,
  onSwitchToExpert,
  onReturnToBusinessContext,
  businessReturnContext,
  currentCaseSummary,
}) {
  const navItems = mode === "expert" ? EXPERT_NAV_ITEMS : BUSINESS_NAV_ITEMS;
  const scenario = currentCaseSummary?.scenario || "建筑工程可信交付方案";
  const caseId = currentCaseSummary?.case_id || "未锁定项目";
  const stageLabel = currentCaseSummary?.status_label || currentCaseSummary?.stage || "待启动";

  return (
    <div className="min-w-0 space-y-4">
      <aside className="min-w-0 rounded-[30px] border border-[color:var(--cg-border)] bg-[color:var(--cg-surface-strong)] p-4 shadow-[var(--cg-shadow-soft)] backdrop-blur">
        <div className="hidden px-2 pb-4 lg:block">
          <p className="text-[11px] font-black uppercase tracking-[0.22em] text-[color:var(--cg-text-soft)]">Workspace</p>
          <p className="mt-2 text-xl font-black tracking-[-0.04em] text-[color:var(--cg-text)]">
            {mode === "business" ? "业务控制台" : "专家控制台"}
          </p>
          <p className="mt-2 text-sm leading-6 text-[color:var(--cg-text-soft)]">
            {mode === "business"
              ? "面向企业客户的项目推进视图。"
              : "面向研发与审计的透明化执行视图。"}
          </p>
        </div>

        <nav aria-label={mode === "business" ? "工程业务导航" : "专家导航"} className="flex max-w-full gap-2 overflow-x-auto pb-1 lg:block lg:space-y-2 lg:overflow-visible lg:pb-0">
          {navItems.map(({ id, label, icon: Icon }) => {
            const active = !settingsOpen && view === id;
            const handleNavClick = () => {
              setSettingsOpen?.(false);

              if (mode === "business") {
                if (id === "overview") {
                  onOpenOverview?.();
                  return;
                }
                if (id === "workbench") {
                  onOpenProject?.();
                  return;
                }
                if (id === "context") {
                  onOpenContext?.();
                  return;
                }
                if (id === "validation") {
                  onOpenValidation?.();
                  return;
                }
                if (id === "delivery") {
                  onOpenDelivery?.();
                  return;
                }
              }

              setView?.(id);
            };

            return (
              <button
                key={id}
                type="button"
                onClick={handleNavClick}
                className={cn(
                  "flex shrink-0 items-center gap-3 rounded-[18px] border px-3 py-2.5 text-left transition lg:w-full lg:px-4 lg:py-3",
                  active
                    ? "border-[color:var(--cg-accent-border)] bg-[color:var(--cg-accent-fog)] text-[color:var(--cg-accent-strong)] shadow-[var(--cg-shadow-soft)]"
                    : "border-transparent bg-transparent text-[color:var(--cg-text-soft)] hover:border-[color:var(--cg-border)] hover:bg-white hover:text-[color:var(--cg-text)]"
                )}
              >
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-[12px] border border-[color:var(--cg-border)] bg-white text-[color:var(--cg-accent-strong)] lg:h-9 lg:w-9 lg:rounded-[14px]">
                  <Icon size={17} />
                </span>
                <span className="text-sm font-semibold">{label}</span>
              </button>
            );
          })}
        </nav>

        <div className="mt-4 hidden border-t border-[color:var(--cg-border)] pt-4 lg:block">
          <button
            type="button"
            onClick={() => setSettingsOpen?.((prev) => !prev)}
            className={cn(
              "flex w-full items-center gap-3 rounded-[18px] border px-4 py-3 text-left transition",
              settingsOpen
                ? "border-[color:var(--cg-accent-border)] bg-[color:var(--cg-accent-fog)] text-[color:var(--cg-accent-strong)] shadow-[var(--cg-shadow-soft)]"
                : "border-transparent text-[color:var(--cg-text-soft)] hover:border-[color:var(--cg-border)] hover:bg-white hover:text-[color:var(--cg-text)]"
            )}
          >
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] border border-[color:var(--cg-border)] bg-white text-[color:var(--cg-accent-strong)]">
              <SettingsIcon size={17} />
            </span>
            <span className="text-sm font-semibold">{settingsOpen ? "收起系统设置" : "系统设置"}</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setSettingsOpen?.(false);
              if (onOpenComponents) {
                onOpenComponents();
                return;
              }
              setView?.("components");
            }}
            className={cn(
              "mt-3 flex w-full items-center gap-3 rounded-[18px] border px-4 py-3 text-left transition",
              !settingsOpen && view === "components"
                ? "border-[color:var(--cg-accent-border)] bg-[color:var(--cg-accent-fog)] text-[color:var(--cg-accent-strong)] shadow-[var(--cg-shadow-soft)]"
                : "border-transparent text-[color:var(--cg-text-soft)] hover:border-[color:var(--cg-border)] hover:bg-white hover:text-[color:var(--cg-text)]"
            )}
          >
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] border border-[color:var(--cg-border)] bg-white text-[color:var(--cg-accent-strong)]">
              <GridIcon size={17} />
            </span>
            <span className="text-sm font-semibold">组件库</span>
          </button>
        </div>
      </aside>

      <section className="hidden rounded-[28px] border border-[color:var(--cg-border)] bg-[color:var(--cg-surface-strong)] p-4 shadow-[var(--cg-shadow-soft)] lg:block">
        <p className="text-[11px] font-black uppercase tracking-[0.22em] text-[color:var(--cg-text-soft)]">当前项目</p>
        <p className="mt-3 text-base font-black text-[color:var(--cg-text)]">{scenario}</p>
        <p className="mt-2 text-xs leading-6 text-[color:var(--cg-text-soft)]">{caseId}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="rounded-full border border-[color:var(--cg-border)] bg-white px-3 py-1 text-xs font-semibold text-[color:var(--cg-text-soft)]">
            阶段 {stageLabel}
          </span>
          <span className="rounded-full border border-[color:var(--cg-border)] bg-white px-3 py-1 text-xs font-semibold text-[color:var(--cg-text-soft)]">
            {mode === "business" ? "业务视角" : "专家视角"}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2" role="group" aria-label="工作台模式">
          <button
            type="button"
            onClick={() => onSwitchToBusiness?.()}
            className={cn("cg-sidebar-switch w-full", mode === "business" && "cg-sidebar-switch--active")}
            aria-pressed={mode === "business"}
          >
            业务模式
          </button>
          <button
            type="button"
            onClick={() => onSwitchToExpert?.()}
            className={cn("cg-sidebar-switch w-full", mode === "expert" && "cg-sidebar-switch--active")}
            aria-pressed={mode === "expert"}
          >
            专家模式
          </button>
        </div>

        {mode === "expert" && businessReturnContext?.viewLabel ? (
          <button
            type="button"
            onClick={() => onReturnToBusinessContext?.()}
            className="mt-4 flex w-full items-center justify-center rounded-[18px] border border-[color:var(--cg-accent-border)] bg-[color:var(--cg-accent-fog)] px-4 py-3 text-sm font-semibold text-[color:var(--cg-accent-strong)] transition hover:translate-y-[-1px]"
          >
            返回业务上下文
          </button>
        ) : null}
      </section>
    </div>
  );
}
