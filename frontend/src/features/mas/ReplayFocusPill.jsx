import { TagPill } from "../../components/SemanticPill";
import { buildReplayFocusLabel, getReplayFocusTone } from "./masHelpers";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function normalizeRef(value) {
  return String(value || "").trim();
}

export function PillButton({
  active = false,
  onClick,
  children,
  ringTone = "focus:ring-sky-300",
  className = "",
  disabled = false,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "rounded-full transition-transform hover:-translate-y-[1px] focus:outline-none focus:ring-2",
        ringTone,
        active ? "ring-2 ring-offset-1 ring-slate-300" : "",
        disabled ? "cursor-not-allowed opacity-60 hover:translate-y-0" : "",
        className
      )}
    >
      {children}
    </button>
  );
}

export function ReplayFocusPill({
  kind,
  value,
  active = false,
  tone,
  label,
  hideWhenEmpty = true,
}) {
  const normalized = normalizeRef(value);
  if (!normalized && hideWhenEmpty) return null;
  return (
    <TagPill tone={tone || getReplayFocusTone(kind, Boolean(active && normalized))}>
      {label || buildReplayFocusLabel(kind, normalized)}
    </TagPill>
  );
}

export function ReplayFocusButton({
  kind,
  value,
  active = false,
  onClick,
  ringTone = "focus:ring-sky-300",
  tone,
  label,
  hideWhenEmpty = true,
  disabled = false,
}) {
  const normalized = normalizeRef(value);
  if (!normalized && hideWhenEmpty) return null;
  return (
    <PillButton active={active} onClick={onClick} ringTone={ringTone} disabled={disabled}>
      <ReplayFocusPill
        kind={kind}
        value={normalized}
        active={active}
        tone={tone}
        label={label}
        hideWhenEmpty={false}
      />
    </PillButton>
  );
}
