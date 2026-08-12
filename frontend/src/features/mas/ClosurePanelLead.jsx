import { TagPill } from "../../components/SemanticPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

const ACCENT_META = {
  emerald: {
    shell: "border-emerald-200 bg-[linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.94),rgba(220,252,231,0.92))]",
    badge: "border-emerald-200 bg-emerald-100 text-emerald-800",
    button: "border-emerald-300 bg-emerald-50 text-emerald-900 hover:border-emerald-400",
  },
  sky: {
    shell: "border-sky-200 bg-[linear-gradient(135deg,rgba(240,249,255,0.96),rgba(255,255,255,0.94),rgba(224,242,254,0.92))]",
    badge: "border-sky-200 bg-sky-100 text-sky-800",
    button: "border-sky-300 bg-sky-50 text-sky-900 hover:border-sky-400",
  },
  amber: {
    shell: "border-amber-200 bg-[linear-gradient(135deg,rgba(255,251,235,0.96),rgba(255,255,255,0.94),rgba(254,243,199,0.9))]",
    badge: "border-amber-200 bg-amber-100 text-amber-800",
    button: "border-amber-300 bg-amber-50 text-amber-900 hover:border-amber-400",
  },
  violet: {
    shell: "border-violet-200 bg-[linear-gradient(135deg,rgba(245,243,255,0.96),rgba(255,255,255,0.94),rgba(237,233,254,0.92))]",
    badge: "border-violet-200 bg-violet-100 text-violet-800",
    button: "border-violet-300 bg-violet-50 text-violet-900 hover:border-violet-400",
  },
};

export default function ClosurePanelLead({
  eyebrow = "Closure Block",
  title,
  detail,
  statusLabel = "",
  statusTone = "neutral",
  nextLabel = "",
  nextDetail = "",
  actionLabel = "",
  onAction,
  accent = "emerald",
}) {
  const meta = ACCENT_META[accent] || ACCENT_META.emerald;

  return (
    <div className={cn("rounded-[24px] border px-4 py-4 shadow-sm", meta.shell)}>
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn("rounded-full border px-3 py-1 text-[11px] font-black uppercase tracking-[0.18em]", meta.badge)}>
              {eyebrow}
            </span>
            {statusLabel ? <TagPill tone={statusTone}>{statusLabel}</TagPill> : null}
          </div>
          <p className="mt-3 text-lg font-black tracking-tight text-slate-950">{title}</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{detail}</p>
        </div>
        {(nextDetail || actionLabel) ? (
          <div className="rounded-[20px] border border-white/80 bg-white/88 px-4 py-3 shadow-sm xl:max-w-sm">
            {nextLabel ? <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">{nextLabel}</p> : null}
            {nextDetail ? <p className="mt-2 text-sm leading-6 text-slate-700">{nextDetail}</p> : null}
            {actionLabel ? (
              <button
                type="button"
                onClick={() => onAction?.()}
                className={cn(
                  "mt-4 rounded-full border px-4 py-2 text-sm font-black transition focus:outline-none focus:ring-2 focus:ring-emerald-300",
                  meta.button
                )}
              >
                {actionLabel}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
