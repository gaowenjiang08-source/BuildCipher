import { formatBooleanDisplayValue, formatDisplayValue } from "./DisplayValue";

const STATUS_ALIAS = {
  pass: "passed",
  ok: "passed",
  approved: "passed",
  reject: "failed",
  rejected: "failed",
  bad: "failed",
  error: "failed",
};

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function normalizeStatus(status = "") {
  const normalized = String(status || "").toLowerCase();
  return STATUS_ALIAS[normalized] || normalized;
}

export function getSemanticTone({ kind = "status", value, trueTone = "ok", falseTone = "warn" } = {}) {
  if (kind === "boolean") {
    return value ? trueTone : falseTone;
  }

  const normalized = String(value || "").toLowerCase();
  if (kind === "trust" || kind === "support") {
    if (normalized === "high") return "ok";
    if (normalized === "medium") return "warn";
    if (normalized === "low") return "bad";
    return "neutral";
  }

  const status = normalizeStatus(normalized);
  if (["passed", "done", "hardened", "success"].includes(status)) return "ok";
  if (["failed", "cancelled"].includes(status)) return "bad";
  if (["unknown", ""].includes(status)) return "neutral";
  return "warn";
}

export function TagPill({ tone = "warn", children, className = "" }) {
  const styles = {
    ok: "border-[color:var(--cg-success-border)] bg-[color:var(--cg-success-fog)] text-[color:var(--cg-success-text)]",
    bad: "border-[color:var(--cg-danger-border)] bg-[color:var(--cg-danger-fog)] text-[color:var(--cg-danger-text)]",
    warn: "border-[color:var(--cg-warning-border)] bg-[color:var(--cg-warning-fog)] text-[color:var(--cg-warning-text)]",
    neutral: "border-[color:var(--cg-border)] bg-[color:var(--cg-surface-muted)] text-[color:var(--cg-text-soft)]",
  };

  const dotClass = {
    ok: "bg-[color:var(--cg-success-text)]",
    bad: "bg-[color:var(--cg-danger-text)]",
    warn: "bg-[color:var(--cg-warning-text)]",
    neutral: "bg-[color:var(--cg-text-soft)]/70",
  };

  return (
    <span
      className={cn(
        "inline-flex min-h-8 items-center gap-2 rounded-full border px-3.5 py-1.5 text-[0.78rem] font-semibold tracking-[0.02em] shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]",
        styles[tone] || styles.warn,
        className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dotClass[tone] || dotClass.warn)} />
      <span>{children}</span>
    </span>
  );
}

export function SemanticPill({
  kind = "status",
  value,
  label,
  tone,
  emptyText = "--",
  trueText = "是",
  falseText = "否",
  trueTone = "ok",
  falseTone = "warn",
}) {
  const resolvedTone = tone || getSemanticTone({ kind, value, trueTone, falseTone });
  const resolvedText =
    kind === "boolean"
      ? formatBooleanDisplayValue({ label, value, trueText, falseText, emptyText })
      : formatDisplayValue({ label, value, emptyText });

  return <TagPill tone={resolvedTone}>{resolvedText}</TagPill>;
}
