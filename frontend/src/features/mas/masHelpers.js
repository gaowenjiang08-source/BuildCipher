export const WORKFLOW_STEPS = [
  { phase: "analyst", label: "需求分析", owner: "Analyst Agent" },
  { phase: "context_builder", label: "证据检索", owner: "Context Builder" },
  { phase: "architect", label: "方案生成", owner: "Generation Agent" },
  { phase: "audit", label: "合规审计", owner: "Audit Agent" },
  { phase: "engineer", label: "工程实现", owner: "Engineer Module" },
  { phase: "target_deployer", label: "目标部署", owner: "Target Deployer" },
  { phase: "attack_executor", label: "攻击规划", owner: "Attack Planning Agent" },
  { phase: "vulnerability_evaluation", label: "漏洞评估", owner: "Vulnerability Agent" },
  { phase: "patch_reflection", label: "修补反思", owner: "Patch / Reflection" },
  { phase: "delivery", label: "最终交付", owner: "Delivery Renderer" },
];

export const DEFAULT_WORKFLOW_TRACE = WORKFLOW_STEPS.map((item) => item.phase);

const PHASE_ALIAS = {
  clarify: "analyst",
  design: "architect",
  review: "audit",
  revise: "architect",
  sandbox: "engineer",
  codegen: "engineer",
  python_compile: "engineer",
  c_compile: "engineer",
  vulnerability: "vulnerability_evaluation",
  reflection: "patch_reflection",
};

export function normalizePhase(phase = "") {
  const normalized = String(phase).toLowerCase();
  return PHASE_ALIAS[normalized] || normalized;
}

export function getWorkflowStep(phase = "") {
  const normalized = normalizePhase(phase);
  return (
    WORKFLOW_STEPS.find((item) => item.phase === normalized) || {
      phase: normalized || "unknown",
      label: normalized || "未知阶段",
      owner: "System Module",
    }
  );
}

export function buildWorkflowProgress({ workflowTrace = [], completed = false } = {}) {
  const trace = Array.isArray(workflowTrace) && workflowTrace.length ? workflowTrace : DEFAULT_WORKFLOW_TRACE;
  return trace.map((phase) => ({
    ...getWorkflowStep(phase),
    done: Boolean(completed),
  }));
}

export function actorMatches(logActor = "", target = "") {
  if (!target || target === "all") return true;
  const source = String(logActor || "").toLowerCase();
  const wanted = String(target || "").toLowerCase();
  return source.includes(wanted);
}

export function displayOrDash(value) {
  if (value === null || value === undefined) return "--";
  const text = String(value).trim();
  if (!text) return "--";
  if (["unknown", "n/a", "na", "none", "null"].includes(text.toLowerCase())) return "--";
  return text;
}

export const REPLAY_FOCUS_META = {
  stageRef: {
    label: "阶段",
    tone: "warn",
    activeTone: "warn",
    description: "用于定位当前回看落在哪个 workflow 阶段，适合解释主流程正在看哪一段。",
  },
  projectionRef: {
    label: "Projection",
    tone: "neutral",
    activeTone: "ok",
    description: "用于定位独立上下文窗口或 projection 切片，适合解释记忆压缩、证据聚焦与某条分支视角。",
  },
  handoffRef: {
    label: "Handoff",
    tone: "warn",
    activeTone: "warn",
    description: "用于定位 agent 之间的结构化交接关系，适合解释责任边界、输入输出和下游承接。",
  },
  targetServiceRef: {
    label: "目标服务",
    tone: "ok",
    activeTone: "ok",
    description: "用于定位当前回看的沙盒服务实例，适合联动执行平面、攻击结果和回归对比。",
  },
  artifactLookupRef: {
    label: "工件",
    tone: "neutral",
    activeTone: "ok",
    description: "用于定位具体 artifact 引用，适合从 replay 侧回看某个构建产物、补丁产物或执行产物命中了哪些事件和快照。",
  },
  evidenceLookupRef: {
    label: "证据",
    tone: "warn",
    activeTone: "ok",
    description: "用于定位具体 evidence 引用，适合从 replay 侧解释某条证据如何穿过工件、事件与快照链路。",
  },
  retryResumeCheckpointRef: {
    label: "恢复点",
    tone: "ok",
    activeTone: "ok",
    description: "用于定位 same-run retry 的 resume checkpoint 回看入口，当前语义是回放查询定位，不是自动恢复执行。",
  },
  retryResumeInputRef: {
    label: "Resume 输入",
    tone: "neutral",
    activeTone: "ok",
    description: "用于定位 same-run retry 的 resume input 回看入口，适合解释恢复时保留了哪些输入摘要。",
  },
};

export const REPLAY_FOCUS_ORDER = ["stageRef", "projectionRef", "handoffRef", "targetServiceRef"];
export const REPLAY_QUERY_FOCUS_ORDER = [
  "artifactLookupRef",
  "evidenceLookupRef",
  "retryResumeCheckpointRef",
  "retryResumeInputRef",
];

export function getReplayFocusMeta(kind = "") {
  return REPLAY_FOCUS_META[String(kind || "").trim()] || REPLAY_FOCUS_META.stageRef;
}

export function getReplayFocusTone(kind = "", active = false) {
  const meta = getReplayFocusMeta(kind);
  return active ? meta.activeTone || meta.tone || "neutral" : meta.tone || "neutral";
}

export function buildReplayFocusLabel(kind = "", value = "") {
  const normalized = displayOrDash(value);
  const meta = getReplayFocusMeta(kind);
  return `${meta.label} ${normalized}`;
}
