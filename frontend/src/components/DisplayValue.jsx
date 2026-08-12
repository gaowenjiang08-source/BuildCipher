const EMPTY_TOKENS = new Set(["", "--", "unknown", "n/a", "na", "none", "null", "undefined"]);

function normalizeDisplayInput(value, emptyText = "--") {
  if (value === null || value === undefined) return emptyText;
  if (typeof value === "boolean") return value;

  const text = String(value).trim();
  if (!text) return emptyText;
  if (EMPTY_TOKENS.has(text.toLowerCase())) return emptyText;
  return text;
}

export function formatDisplayValue({ label, value, emptyText = "--" } = {}) {
  const preferred = normalizeDisplayInput(label, emptyText);
  if (preferred !== emptyText) return preferred;

  const fallback = normalizeDisplayInput(value, emptyText);
  if (fallback === true || fallback === false) return String(fallback);
  return fallback;
}

export function formatBooleanDisplayValue({
  label,
  value,
  trueText = "是",
  falseText = "否",
  emptyText = "--",
} = {}) {
  const preferred = normalizeDisplayInput(label, emptyText);
  if (preferred !== emptyText) return preferred;

  const normalized = normalizeDisplayInput(value, emptyText);
  if (normalized === emptyText) return emptyText;
  if (normalized === true) return trueText;
  if (normalized === false) return falseText;

  const lowered = String(normalized).toLowerCase();
  if (["true", "yes", "y", "1"].includes(lowered)) return trueText;
  if (["false", "no", "n", "0"].includes(lowered)) return falseText;
  return normalized;
}

export function DisplayValue(props) {
  return <>{formatDisplayValue(props)}</>;
}

export function DisplayBooleanValue(props) {
  return <>{formatBooleanDisplayValue(props)}</>;
}
