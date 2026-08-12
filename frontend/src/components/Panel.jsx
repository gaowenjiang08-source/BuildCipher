import { formatBooleanDisplayValue, formatDisplayValue } from "./DisplayValue";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function IconBadge({ icon: Icon }) {
  if (!Icon) return null;

  return (
    <span className="cg-icon-badge">
      <Icon size={16} />
    </span>
  );
}

export function Panel({ title, subtitle, right, children, className = "", icon }) {
  return (
    <section className={cn("panel-shell", className)}>
      <div className="relative mb-6 flex flex-wrap items-start justify-between gap-4 border-b border-[color:var(--cg-border)]/70 pb-5">
        <div className="min-w-0">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[color:var(--cg-accent-border)] bg-[color:var(--cg-accent-fog)]/90 px-3 py-1 text-[11px] font-semibold tracking-[0.16em] text-[color:var(--cg-accent-strong)]">
            <span className="inline-flex h-1.5 w-1.5 rounded-full bg-[color:var(--cg-accent-soft)]" />
            模块概览
          </div>
          <div className="flex items-center gap-3">
            <IconBadge icon={icon} />
            <h2 className="text-[1.05rem] font-extrabold tracking-[-0.02em] text-[color:var(--cg-text)] md:text-[1.22rem]">{title}</h2>
          </div>
          {subtitle ? (
            <p className={cn("mt-2 max-w-4xl text-[0.98rem] leading-7 text-[color:var(--cg-text-soft)]", icon ? "pl-11" : "")}>{subtitle}</p>
          ) : null}
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

export function MetricCard({
  label,
  value,
  hint,
  valueLabel,
  valueBoolean = false,
  icon,
  tone = "neutral",
  className = "",
}) {
  const resolvedValue = valueBoolean
    ? formatBooleanDisplayValue({ label: valueLabel, value })
    : formatDisplayValue({ label: valueLabel, value });

  const toneClass = {
    neutral: "bg-[linear-gradient(180deg,rgba(248,251,255,0.88)_0%,rgba(255,255,255,0.96)_100%)] border-[color:var(--cg-border)]",
    accent: "bg-[linear-gradient(180deg,rgba(235,244,255,0.92)_0%,rgba(255,255,255,0.98)_100%)] border-[color:var(--cg-accent-border)]",
    success: "bg-[linear-gradient(180deg,rgba(237,252,245,0.92)_0%,rgba(255,255,255,0.98)_100%)] border-[color:var(--cg-success-border)]",
    danger: "bg-[linear-gradient(180deg,rgba(255,242,242,0.92)_0%,rgba(255,255,255,0.98)_100%)] border-[color:var(--cg-danger-border)]",
  };

  return (
    <div className={cn("cg-bouncy-card rounded-[24px] border p-5 shadow-[var(--cg-shadow-soft)]", toneClass[tone] || toneClass.neutral, className)}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11px] font-extrabold uppercase tracking-[0.12em] text-[color:var(--cg-text-soft)]">{label}</p>
        <IconBadge icon={icon} />
      </div>
      <p className="mt-3 text-[1.7rem] font-extrabold tracking-[-0.035em] text-[color:var(--cg-text)]">{resolvedValue}</p>
      {hint ? <p className="mt-2 text-[0.92rem] leading-6 text-[color:var(--cg-text-soft)]">{hint}</p> : null}
    </div>
  );
}
