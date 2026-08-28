const RUN_HISTORY_LIMIT = 20;
const SUMMARY_TEXT_LIMIT = 600;

function limitedText(value, limit = SUMMARY_TEXT_LIMIT) {
  const text = String(value || "").trim();
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

function compactFinalScheme(finalScheme = {}) {
  const metadata = finalScheme?.metadata || {};
  return {
    id: finalScheme.id || finalScheme.scheme_id || metadata.id || "",
    name: finalScheme.name || metadata.name || "",
    score: finalScheme.score ?? null,
    security_level: finalScheme.security_level ?? finalScheme.parameters?.security_level ?? null,
    scheme_type: finalScheme.scheme_type || metadata.scheme_type || "",
  };
}

function compactDelivery(delivery = {}) {
  return {
    status: delivery.status || "",
    status_label: delivery.status_label || "",
    selected_proposal: delivery.selected_proposal || "",
    next_action: limitedText(delivery.next_action),
    engine: delivery.engine || "",
    engine_mode: delivery.engine_mode || "",
    audit_passed: delivery.audit_passed ?? null,
  };
}

export function toRunHistorySnapshot(result = {}) {
  return {
    history_scope: "summary",
    request_id: result.request_id || "",
    run_id: result.run_id || result.request_id || "",
    case_id: result.case_id || "",
    generated_at: result.generated_at || "",
    requirement_summary: limitedText(
      result.requirement_summary ||
        result.analyst?.requirement_summary ||
        result.analyst?.summary ||
        result.requirement
    ),
    final_scheme: compactFinalScheme(result.final_scheme),
    delivery: compactDelivery(result.delivery),
  };
}

export function compactRunHistory(history = []) {
  if (!Array.isArray(history)) return [];
  return history.slice(0, RUN_HISTORY_LIMIT).map(toRunHistorySnapshot);
}

