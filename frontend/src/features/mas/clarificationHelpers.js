export const DEFAULT_CLARIFICATION_DETAILS = Object.freeze({
  complianceTarget: "",
  memoryBudget: "",
  latencyTarget: "",
  extraRequirements: "",
});

export const CLARIFICATION_SUGGESTIONS = Object.freeze({
  complianceTargets: ["ISO 19650 参考", "ISO 27001", "GB/T 22239", "项目验收规则"],
  memoryBudgets: ["256KB", "2MB", "256MB"],
  latencyTargets: ["20ms", "100ms", "1s"],
});

const MEMORY_BUDGET_PATTERN = /\b\d+\s*(kb|mb|gb)\b/i;
const LATENCY_PATTERN = /\b\d+\s*(ms|s)\b/i;
const COMPLIANCE_PATTERN = /\b(fips|pci|gdpr|iso|soc2|gb\/t)\b/i;

function normalizeText(value = "") {
  return String(value || "").trim();
}

export function hasClarificationDetails(details = {}) {
  return Object.values(details || {}).some((value) => normalizeText(value));
}

export function buildClarificationAppendix(details = {}) {
  const lines = [];
  const complianceTarget = normalizeText(details.complianceTarget);
  const memoryBudget = normalizeText(details.memoryBudget);
  const latencyTarget = normalizeText(details.latencyTarget);
  const extraRequirements = normalizeText(details.extraRequirements);

  if (complianceTarget) lines.push(`- 主合规目标：${complianceTarget}`);
  if (memoryBudget) lines.push(`- 可用内存预算：${memoryBudget}`);
  if (latencyTarget) lines.push(`- 延迟目标：${latencyTarget}`);
  if (extraRequirements) lines.push(`- 其他硬约束：${extraRequirements}`);

  if (lines.length === 0) return "";
  return ["[关键约束补充]", ...lines].join("\n");
}

export function buildRequirementWithClarifications(requirement = "", details = {}) {
  const baseRequirement = normalizeText(requirement);
  const appendix = buildClarificationAppendix(details);
  if (!appendix) return baseRequirement;
  return baseRequirement ? `${baseRequirement}\n\n${appendix}` : appendix;
}

export function analyzeClarificationCoverage(requirement = "", details = {}) {
  const combined = buildRequirementWithClarifications(requirement, details).toLowerCase();

  return [
    {
      id: "compliance_target",
      label: "主合规目标",
      hint: "例如 ISO 19650 参考 / ISO 27001 / 项目验收规则",
      required: true,
      complete: COMPLIANCE_PATTERN.test(combined) || combined.includes("合规"),
    },
    {
      id: "memory_budget",
      label: "可用内存预算",
      hint: "例如 256KB / 2MB / 256MB",
      required: true,
      complete: MEMORY_BUDGET_PATTERN.test(combined),
    },
    {
      id: "latency_target",
      label: "延迟目标",
      hint: "例如 20ms / 1s",
      required: false,
      complete: LATENCY_PATTERN.test(combined) || combined.includes("latency") || combined.includes("延迟"),
    },
  ];
}

export function listBlockingClarificationLabels(requirement = "", details = {}) {
  return analyzeClarificationCoverage(requirement, details)
    .filter((item) => item.required && !item.complete)
    .map((item) => item.label);
}
