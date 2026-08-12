import { TagPill } from "../../components/SemanticPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

const TONE_META = {
  sky: {
    shell: "border-sky-200 bg-[linear-gradient(135deg,rgba(240,249,255,0.98),rgba(255,255,255,0.94),rgba(224,242,254,0.92))]",
    line: "from-sky-400 via-cyan-300 to-transparent",
    badge: "border-sky-200 bg-sky-100 text-sky-800",
  },
  rose: {
    shell: "border-rose-200 bg-[linear-gradient(135deg,rgba(255,241,242,0.98),rgba(255,255,255,0.94),rgba(255,228,230,0.92))]",
    line: "from-rose-400 via-pink-300 to-transparent",
    badge: "border-rose-200 bg-rose-100 text-rose-800",
  },
  emerald: {
    shell: "border-emerald-200 bg-[linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.94),rgba(220,252,231,0.92))]",
    line: "from-emerald-400 via-teal-300 to-transparent",
    badge: "border-emerald-200 bg-emerald-100 text-emerald-800",
  },
};

export default function ReportsSectionDivider({
  eyebrow = "Section",
  title,
  subtitle,
  hint,
  tone = "sky",
  chips = [],
}) {
  const meta = TONE_META[tone] || TONE_META.sky;

  return (
    <div className="xl:col-span-2">
      <div className={cn("relative overflow-hidden rounded-[28px] border px-5 py-4 shadow-sm", meta.shell)}>
        <div className={cn("absolute inset-x-0 top-0 h-1 bg-gradient-to-r opacity-90", meta.line)} />
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={cn("rounded-full border px-3 py-1 text-[11px] font-black uppercase tracking-[0.18em]", meta.badge)}>
                {eyebrow}
              </span>
              {chips.map((chip, index) => (
                <TagPill key={`${eyebrow}-chip-${index}`} tone={chip.tone || "neutral"}>
                  {chip.label}
                </TagPill>
              ))}
            </div>
            <p className="mt-3 text-xl font-black tracking-tight text-slate-950">{title}</p>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">{subtitle}</p>
          </div>
          {hint ? (
            <div className="rounded-2xl border border-white/80 bg-white/85 px-4 py-3 shadow-sm xl:max-w-sm">
              <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">讲解提示</p>
              <p className="mt-2 text-sm leading-6 text-slate-700">{hint}</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
