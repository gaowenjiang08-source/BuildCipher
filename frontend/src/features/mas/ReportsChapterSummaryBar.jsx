import { TagPill } from "../../components/SemanticPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function ChapterCard({
  step,
  title,
  detail,
  active = false,
  statusLabel,
  accent = "slate",
  onClick,
}) {
  const accentStyles = {
    slate: active
      ? "border-slate-900 bg-slate-950 text-white"
      : "border-slate-200 bg-white text-slate-900 hover:border-slate-300",
    sky: active
      ? "border-sky-500 bg-sky-950 text-white"
      : "border-sky-100 bg-[linear-gradient(135deg,#ffffff_0%,#f0f9ff_100%)] text-slate-900 hover:border-sky-300",
    rose: active
      ? "border-rose-500 bg-rose-950 text-white"
      : "border-rose-100 bg-[linear-gradient(135deg,#ffffff_0%,#fff1f2_100%)] text-slate-900 hover:border-rose-300",
    emerald: active
      ? "border-emerald-500 bg-emerald-950 text-white"
      : "border-emerald-100 bg-[linear-gradient(135deg,#ffffff_0%,#ecfdf5_100%)] text-slate-900 hover:border-emerald-300",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-[22px] border px-4 py-4 text-left transition hover:-translate-y-0.5 hover:shadow-md",
        accentStyles[accent] || accentStyles.slate
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <span
          className={cn(
            "inline-flex h-8 w-8 items-center justify-center rounded-full border text-xs font-black",
            active ? "border-white/30 bg-white/10 text-white" : "border-slate-200 bg-white/90 text-slate-700"
          )}
        >
          {step}
        </span>
        <TagPill tone={active ? "ok" : "neutral"}>{statusLabel}</TagPill>
      </div>
      <p className={cn("mt-3 text-sm font-black", active ? "text-white" : "text-slate-950")}>{title}</p>
      <p className={cn("mt-2 text-xs leading-5", active ? "text-white/80" : "text-slate-600")}>{detail}</p>
    </button>
  );
}

export default function ReportsChapterSummaryBar({
  overviewActive = false,
  mainlineActive = false,
  attackActive = false,
  deliveryActive = false,
  onJumpToOverview,
  onJumpToMainline,
  onJumpToAttack,
  onJumpToDelivery,
}) {
  return (
    <section className="xl:col-span-2 rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fbff_48%,#f0fdf4_100%)] p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <TagPill tone="ok">四段阅读总览</TagPill>
        <TagPill tone="neutral">专家模式阅读地图</TagPill>
      </div>
      <p className="mt-3 text-xl font-black text-slate-950">查看全局、主线、攻防和交付。</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        这条章节总览条用于把长报告页分成四段。
      </p>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-4">
        <ChapterCard
          step="0"
          title="总览摘要"
          detail="项目背景、结构化需求和审计起点。"
          active={overviewActive}
          statusLabel={overviewActive ? "当前所在" : "起始段"}
          accent="slate"
          onClick={onJumpToOverview}
        />
        <ChapterCard
          step="1"
          title="主线透视"
          detail="流程、回放与上下文。"
          active={mainlineActive}
          statusLabel={mainlineActive ? "当前所在" : "建议第二段"}
          accent="sky"
          onClick={onJumpToMainline}
        />
        <ChapterCard
          step="2"
          title="攻防闭环"
          detail="攻击轮次、漏洞评估、修补与执行治理。"
          active={attackActive}
          statusLabel={attackActive ? "当前所在" : "技术核心段"}
          accent="rose"
          onClick={onJumpToAttack}
        />
        <ChapterCard
          step="3"
          title="证据与交付"
          detail="证据来源、可信度、交付物与历史记录。"
          active={deliveryActive}
          statusLabel={deliveryActive ? "当前所在" : "收尾段"}
          accent="emerald"
          onClick={onJumpToDelivery}
        />
      </div>
    </section>
  );
}
