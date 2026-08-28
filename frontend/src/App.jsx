import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import {
  getCaseTimelineEvents,
  getCaseTimelineDrilldown,
  getCaseTimelineLineage,
  getCaseTimelineOverview,
  getCaseTimelineSnapshots,
  loadClientSettings,
  saveClientSettings,
} from "./api/client";
import { formatDisplayValue } from "./components/DisplayValue";
import StudioHeaderView from "./features/mas/StudioHeaderView";
import StudioShell from "./features/mas/StudioShell";
import StudioSidebarView from "./features/mas/StudioSidebarView";
import WorkspaceStatusBanner from "./features/mas/WorkspaceStatusBanner";
import useMasActions from "./features/mas/useMasActions";
import { DEFAULT_CLARIFICATION_DETAILS } from "./features/mas/clarificationHelpers";
import useMasDerivedState from "./features/mas/useMasDerivedState";
import useMasExport from "./features/mas/useMasExport";
import useMasLocalOps from "./features/mas/useMasLocalOps";
import { SimpleBarChart, SimpleRadarChart, SimpleScatterChart } from "./features/mas/MasCharts";
import { actorMatches, displayOrDash } from "./features/mas/masHelpers";
import {
  useAttackLoopStore,
  useRunDraftStore,
  useRunSessionStore,
  useStageConsoleStore,
} from "./store";
import {
  CONSTRUCTION_INPUT_DIMENSIONS,
  CONSTRUCTION_TEMPLATES,
  getConstructionSectionLabel,
  getConstructionViewLabel,
} from "./features/construction/constructionBusinessState";

const ConstructionWorkspaceView = lazy(() => import("./features/construction/ConstructionWorkspaceView"));
const MissionView = lazy(() => import("./features/mas/MissionView"));
const RuntimeConsoleView = lazy(() => import("./features/mas/RuntimeConsoleView"));
const ReportsView = lazy(() => import("./features/mas/ReportsView"));
const WorkbenchView = lazy(() => import("./features/mas/WorkbenchView"));
const ComponentsView = lazy(() => import("./features/mas/ComponentsView"));
const OpsView = lazy(() => import("./features/mas/OpsView"));
const SettingsView = lazy(() => import("./features/mas/SettingsView"));

const DEFAULT_REQUIREMENT =
  "为建筑工程项目设计 BIM/IFC 可信交付方案：验证模型内容篡改、合法旧版本回滚、专业分包越权、工地传感器设备冒充和遥测重放，绑定建设、设计、总包、分包与监理的身份、签批和验收证据。";

const RUN_HISTORY_KEY = "buildtrust.mas.run_history";
const COMPONENT_CACHE_KEY = "buildtrust.mas.components_cache";
const CURRENT_CASE_KEY = "buildtrust.mas.current_case";
const BUSINESS_READING_CONTEXT_KEY = "buildtrust.ui.business_reading_context";
const BUSINESS_VIEWS = ["overview", "workbench", "context", "validation", "delivery"];
const EXPERT_VIEWS = ["mission", "runtime", "reports", "workbench", "ops"];

const TEAM_MEMBERS = [
  {
    actor: "Requirement Analyst",
    title: "需求分析师",
    icon: "RA",
    mission: "澄清并对齐需求，把自然语言转成结构化约束 JSON。",
    tools: ["缺失信息追问", "规格化参数提取"],
    phases: ["clarify"],
    accent: "from-sky-500/25 via-cyan-400/15 to-white",
    border: "border-sky-300/50",
  },
  {
    actor: "Cryptography Architect",
    title: "密码学架构师",
    icon: "CA",
    mission: "在巨大解空间中组合算法并做性能预估，输出候选方案与取舍说明。",
    tools: ["152 组件 RAG 检索", "跨平台性能估算 API"],
    phases: ["design", "revise"],
    accent: "from-amber-500/25 via-orange-400/15 to-white",
    border: "border-amber-300/50",
  },
  {
    actor: "Security & Compliance Auditor",
    title: "安全与合规审计员",
    icon: "SA",
    mission: "以红队视角审查方案，发现漏洞与不合规点，并驳回高风险设计。",
    tools: ["CVE 查询", "9 项合规检查", "量子抗性评估"],
    phases: ["audit"],
    accent: "from-rose-500/25 via-pink-400/15 to-white",
    border: "border-rose-300/50",
  },
  {
    actor: "Code Engineer",
    title: "研发工程师",
    icon: "CE",
    mission: "生成可交付的 Python/C 代码，并在沙箱中完成编译、测试与自纠错。",
    tools: ["安全沙箱", "编译与测试闭环", "自修复迭代"],
    phases: ["codegen", "python_compile", "c_compile", "sandbox"],
    accent: "from-emerald-500/25 via-teal-400/15 to-white",
    border: "border-emerald-300/50",
  },
];

const EXPORT_FORMATS = [
  { id: "json", label: "导出 JSON", extension: "json", mime: "application/json;charset=utf-8" },
  { id: "md", label: "导出 Markdown", extension: "md", mime: "text/markdown;charset=utf-8" },
  { id: "tex", label: "导出 LaTeX", extension: "tex", mime: "text/plain;charset=utf-8" },
  { id: "html", label: "导出完整 HTML 报告", extension: "html", mime: "text/html;charset=utf-8" },
];

function ViewLoadingState({ view = "workbench" }) {
  const viewLabels = {
    settings: "设置面板",
    overview: "场景首页",
    context: "代码依据",
    validation: "攻防验证实验",
    delivery: "交付中心",
    mission: "专家透明化",
    runtime: "运行控制台",
    workbench: "项目工作台",
    components: "组件库",
    reports: "专家报告",
    ops: "资产与运维",
  };
  const viewLabel = viewLabels[view] || "工作区";

  return (
    <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_45%,#eef6ff_100%)] p-6 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-sky-700">
          正在切换视图
        </span>
        <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {viewLabel}
        </span>
      </div>
      <p className="mt-3 text-lg font-black text-slate-950">正在加载 {viewLabel}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        页面加载中，请稍候。
      </p>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        {[0, 1, 2].map((item) => (
          <div key={item} className="animate-pulse rounded-2xl border border-slate-200 bg-white/80 px-4 py-4 shadow-sm">
            <div className="h-3 w-24 rounded-full bg-slate-200" />
            <div className="mt-3 h-6 w-4/5 rounded-full bg-slate-200" />
            <div className="mt-2 h-3 w-full rounded-full bg-slate-100" />
            <div className="mt-2 h-3 w-3/4 rounded-full bg-slate-100" />
          </div>
        ))}
      </div>
    </div>
  );
}
function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function saveJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function loadStoredCaseId() {
  try {
    return localStorage.getItem(CURRENT_CASE_KEY) || "";
  } catch {
    return "";
  }
}

function saveStoredCaseId(caseId) {
  if (!caseId) {
    localStorage.removeItem(CURRENT_CASE_KEY);
    return;
  }
  localStorage.setItem(CURRENT_CASE_KEY, String(caseId));
}

function createDefaultExpertWorkContext() {
  return {
    selectedProposalId: "",
    selectedEvidenceChunkId: "",
    selectedDeliveryFragmentId: "",
  };
}

function normalizeExpertWorkContext(value) {
  const base = createDefaultExpertWorkContext();
  if (!value || typeof value !== "object" || Array.isArray(value)) return base;
  return {
    selectedProposalId: String(value.selectedProposalId || "").trim(),
    selectedEvidenceChunkId: String(value.selectedEvidenceChunkId || "").trim(),
    selectedDeliveryFragmentId: String(value.selectedDeliveryFragmentId || "").trim(),
  };
}

function isEmptyExpertWorkContext(value) {
  const normalized = normalizeExpertWorkContext(value);
  return !normalized.selectedProposalId && !normalized.selectedEvidenceChunkId && !normalized.selectedDeliveryFragmentId;
}

function createDefaultBusinessReadingContext() {
  return {
    lastView: "overview",
    recommendedSectionByView: {},
    manualSectionByView: {},
    lastExpertView: "mission",
    expertSectionByView: {},
    expertWorkContextByView: {},
    returnReason: "",
  };
}

function normalizeBusinessReadingContext(value) {
  const base = createDefaultBusinessReadingContext();
  if (!value || typeof value !== "object" || Array.isArray(value)) return base;

  const lastView = BUSINESS_VIEWS.includes(value.lastView) ? value.lastView : base.lastView;
  const lastExpertView = EXPERT_VIEWS.includes(value.lastExpertView) ? value.lastExpertView : base.lastExpertView;
  const normalizeSectionMap = (input) => {
    const nextMap = {};
    Object.entries(input || {}).forEach(([view, sectionId]) => {
      if (!BUSINESS_VIEWS.includes(view)) return;
      const normalizedSectionId = String(sectionId || "").trim();
      if (!normalizedSectionId) return;
      nextMap[view] = normalizedSectionId;
    });
    return nextMap;
  };

  const legacySectionByView = normalizeSectionMap(value.sectionByView);
  const recommendedSectionByView = {
    ...legacySectionByView,
    ...normalizeSectionMap(value.recommendedSectionByView),
  };
  const manualSectionByView = {
    ...legacySectionByView,
    ...normalizeSectionMap(value.manualSectionByView),
  };
  const expertSectionByView = {};
  Object.entries(value.expertSectionByView || {}).forEach(([view, sectionId]) => {
    if (!EXPERT_VIEWS.includes(view)) return;
    const normalizedSectionId = String(sectionId || "").trim();
    if (!normalizedSectionId) return;
    expertSectionByView[view] = normalizedSectionId;
  });
  const expertWorkContextByView = {};
  Object.entries(value.expertWorkContextByView || {}).forEach(([view, workContext]) => {
    if (!EXPERT_VIEWS.includes(view)) return;
    const normalizedWorkContext = normalizeExpertWorkContext(workContext);
    if (isEmptyExpertWorkContext(normalizedWorkContext)) return;
    expertWorkContextByView[view] = normalizedWorkContext;
  });

  return {
    lastView,
    recommendedSectionByView,
    manualSectionByView,
    lastExpertView,
    expertSectionByView,
    expertWorkContextByView,
    returnReason: String(value.returnReason || "").trim(),
  };
}

function normalizeBusinessReadingContextStore(value) {
  const emptyStore = {
    defaultContext: createDefaultBusinessReadingContext(),
    caseContexts: {},
  };

  if (!value || typeof value !== "object" || Array.isArray(value)) return emptyStore;

  if (!Object.prototype.hasOwnProperty.call(value, "defaultContext") && !Object.prototype.hasOwnProperty.call(value, "caseContexts")) {
    return {
      defaultContext: normalizeBusinessReadingContext(value),
      caseContexts: {},
    };
  }

  const caseContexts = {};
  Object.entries(value.caseContexts || {}).forEach(([caseId, context]) => {
    const normalizedCaseId = String(caseId || "").trim();
    if (!normalizedCaseId) return;
    caseContexts[normalizedCaseId] = normalizeBusinessReadingContext(context);
  });

  return {
    defaultContext: normalizeBusinessReadingContext(value.defaultContext),
    caseContexts,
  };
}

function loadBusinessReadingContextStore() {
  return normalizeBusinessReadingContextStore(loadJson(BUSINESS_READING_CONTEXT_KEY, null));
}

function resolveBusinessReadingContext(caseId = "") {
  const normalizedCaseId = String(caseId || "").trim();
  const store = loadBusinessReadingContextStore();
  if (normalizedCaseId) {
    return store.caseContexts[normalizedCaseId] || createDefaultBusinessReadingContext();
  }
  return store.defaultContext || createDefaultBusinessReadingContext();
}

function saveBusinessReadingContext(caseId, context) {
  const normalizedCaseId = String(caseId || "").trim();
  const normalizedContext = normalizeBusinessReadingContext(context);
  const store = loadBusinessReadingContextStore();
  const nextStore = {
    defaultContext: normalizedCaseId ? store.defaultContext : normalizedContext,
    caseContexts: {
      ...(store.caseContexts || {}),
    },
  };

  if (normalizedCaseId) {
    nextStore.caseContexts[normalizedCaseId] = normalizedContext;
  } else {
    nextStore.defaultContext = normalizedContext;
  }

  saveJson(BUSINESS_READING_CONTEXT_KEY, nextStore);
}

function isSameBusinessReadingContext(left, right) {
  const a = normalizeBusinessReadingContext(left);
  const b = normalizeBusinessReadingContext(right);
  return JSON.stringify(a) === JSON.stringify(b);
}

function formatTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

function toFixed(value, digits = 2) {
  const num = Number(value);
  if (Number.isNaN(num)) return "--";
  return num.toFixed(digits);
}

function summarizeMessage(text = "", maxChars = 260) {
  const raw = String(text || "").trim();
  if (!raw) return "--";
  const firstLine = raw.split("\n")[0];
  if (firstLine.length <= maxChars) return firstLine;
  return `${firstLine.slice(0, maxChars)}...`;
}

const SENSITIVE_KEY_PATTERNS = [
  /(^|_)(api_?key|apikey)($|_)/i,
  /(^|_)(access_?token|token)($|_)/i,
  /(^|_)(secret|password|passphrase)($|_)/i,
  /(^|_)(private_?key)($|_)/i,
];

function isSensitiveKeyName(key = "") {
  const name = String(key || "");
  return SENSITIVE_KEY_PATTERNS.some((pattern) => pattern.test(name));
}

function maskSensitiveValue(value) {
  if (value === null || value === undefined) return value;
  if (typeof value === "string") {
    if (!value) return "";
    return `[HIDDEN: ${value.length} chars]`;
  }
  return "[HIDDEN]";
}

function redactSensitiveObject(input) {
  if (Array.isArray(input)) return input.map((item) => redactSensitiveObject(item));
  if (!input || typeof input !== "object") return input;
  const out = {};
  Object.entries(input).forEach(([key, value]) => {
    if (isSensitiveKeyName(key)) {
      out[key] = maskSensitiveValue(value);
      return;
    }
    out[key] = redactSensitiveObject(value);
  });
  return out;
}

function summarizeCase(caseMemory = {}) {
  return {
    case_id: caseMemory.case_id,
    created_at: caseMemory.created_at,
    updated_at: caseMemory.updated_at,
    status: caseMemory.status || "new",
    status_label: caseMemory.status_label || "新建",
    scenario: caseMemory.scenario || "",
    requirement_summary: caseMemory.requirement_summary || "",
    selected_proposal: caseMemory.selected_proposal || null,
    latest_compliance_score: caseMemory.latest_compliance_score ?? null,
    latest_risk_score: caseMemory.latest_risk_score ?? null,
    blocking_count: (caseMemory.blocking_items || []).length,
    open_question_count: (caseMemory.open_questions || []).length,
    rejected_count: (caseMemory.rejected_options || []).length,
    decision_count: (caseMemory.decision_log || []).length,
  };
}

function mergeCaseSummary(items = [], nextItem) {
  if (!nextItem?.case_id) return items;
  const rest = items.filter((item) => item.case_id !== nextItem.case_id);
  return [nextItem, ...rest].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
}

function buildReplayQueryParams(preferredRunId, replayScope = {}, limit = 12) {
  return {
    run_id: preferredRunId,
    projection_ref: replayScope?.projectionRef,
    handoff_ref: replayScope?.handoffRef,
    artifact_lookup_ref: replayScope?.artifactLookupRef,
    evidence_lookup_ref: replayScope?.evidenceLookupRef,
    retry_resume_checkpoint_ref: replayScope?.retryResumeCheckpointRef,
    retry_resume_input_ref: replayScope?.retryResumeInputRef,
    limit,
  };
}

function markReplaySourceUpdated(setter, sourceId) {
  setter((prev) => ({
    ...(prev || {}),
    [sourceId]: new Date().toISOString(),
  }));
}

function appendReplaySourceHistory(setter, sourceId, status, message = "") {
  setter((prev) => {
    const current = Array.isArray(prev?.[sourceId]) ? prev[sourceId] : [];
    const nextItem = {
      id: `${sourceId}:${Date.now()}`,
      status: String(status || "unknown"),
      message: String(message || "").trim(),
      createdAt: new Date().toISOString(),
    };
    return {
      ...(prev || {}),
      [sourceId]: [nextItem, ...current].slice(0, 6),
    };
  });
}

function App() {
  const hydrateRunDraft = useRunDraftStore((state) => state.hydrateFromApp);
  const hydrateRunSession = useRunSessionStore((state) => state.hydrateFromApp);
  const hydrateStageConsole = useStageConsoleStore((state) => state.hydrateFromApp);
  const hydrateAttackLoop = useAttackLoopStore((state) => state.hydrateFromApp);
  const [mode, setMode] = useState("business");
  const [view, setView] = useState("overview");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState(() => loadClientSettings());
  const [backendEnv, setBackendEnv] = useState(null);

  const [showSecrets, setShowSecrets] = useState(() => ({
    openai: false,
    anthropic: false,
    zhipuai: false,
    gemini: false,
    deepseek: false,
    qwen: false,
    baidu: false,
    relay: false,
    backendEnv: false,
  }));

  const [connectionStatus, setConnectionStatus] = useState("unknown");
  const [connectionMessage, setConnectionMessage] = useState("");
  const [llmStatus, setLlmStatus] = useState("unknown");
  const [llmMessage, setLlmMessage] = useState("");

  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(true);
  const [activeRunId, setActiveRunId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [requirement, setRequirement] = useState(DEFAULT_REQUIREMENT);
  const [numVariants, setNumVariants] = useState(3);
  const [maxAuditRounds, setMaxAuditRounds] = useState(4);
  const [generateCode, setGenerateCode] = useState(true);
  const [strictClarification, setStrictClarification] = useState(false);
  const [clarificationDetails, setClarificationDetails] = useState(DEFAULT_CLARIFICATION_DETAILS);
  const [codeTab, setCodeTab] = useState("python");
  const [selectedProposalId, setSelectedProposalId] = useState("");
  const [selectedEvidenceChunkId, setSelectedEvidenceChunkId] = useState("");
  const [selectedDeliveryFragmentId, setSelectedDeliveryFragmentId] = useState("");

  const [selectedActor, setSelectedActor] = useState("all");

  const [result, setResult] = useState(null);
  const [streamLog, setStreamLog] = useState([]);
  const [components, setComponents] = useState(() => loadJson(COMPONENT_CACHE_KEY, []));
  const [caseCatalog, setCaseCatalog] = useState([]);
  const [currentCaseId, setCurrentCaseId] = useState(() => loadStoredCaseId());
  const [currentCaseDetails, setCurrentCaseDetails] = useState(null);
  const [timelineOverview, setTimelineOverview] = useState(null);
  const [replayDrilldown, setReplayDrilldown] = useState(null);
  const [replayEventsResponse, setReplayEventsResponse] = useState(null);
  const [replaySnapshotsResponse, setReplaySnapshotsResponse] = useState(null);
  const [replayScope, setReplayScope] = useState({
    runId: "",
    stageRef: "",
    projectionRef: "",
    handoffRef: "",
    targetServiceRef: "",
    artifactLookupRef: "",
    evidenceLookupRef: "",
    retryResumeCheckpointRef: "",
    retryResumeInputRef: "",
  });
  const [replayLineage, setReplayLineage] = useState(null);
  const [replayLoading, setReplayLoading] = useState(false);
  const [replayError, setReplayError] = useState("");
  const [replayEventsLoading, setReplayEventsLoading] = useState(false);
  const [replayEventsError, setReplayEventsError] = useState("");
  const [replaySnapshotsLoading, setReplaySnapshotsLoading] = useState(false);
  const [replaySnapshotsError, setReplaySnapshotsError] = useState("");
  const [replaySourceUpdatedAt, setReplaySourceUpdatedAt] = useState({
    drilldown: "",
    events: "",
    snapshots: "",
  });
  const [replaySourceParams, setReplaySourceParams] = useState({
    drilldown: {},
    events: {},
    snapshots: {},
  });
  const [replaySourceHistory, setReplaySourceHistory] = useState({
    drilldown: [],
    events: [],
    snapshots: [],
  });
  const [replayRefreshNonce, setReplayRefreshNonce] = useState({
    drilldown: 0,
    events: 0,
    snapshots: 0,
  });
  const [replayLineageLoading, setReplayLineageLoading] = useState(false);
  const [replayLineageError, setReplayLineageError] = useState("");
  const [knowledgeCatalog, setKnowledgeCatalog] = useState([]);
  const [knowledgeIngestionResult, setKnowledgeIngestionResult] = useState(null);
  const [knowledgeIngestionRunning, setKnowledgeIngestionRunning] = useState(false);
  const [skills, setSkills] = useState([]);
  const [selectedSkillId, setSelectedSkillId] = useState("");
  const [skillRoute, setSkillRoute] = useState(null);
  const [routingSkill, setRoutingSkill] = useState(false);
  const [componentFilter, setComponentFilter] = useState("");
  const [history, setHistory] = useState(() => loadJson(RUN_HISTORY_KEY, []));
  const [businessReadingContext, setBusinessReadingContext] = useState(() => resolveBusinessReadingContext(loadStoredCaseId()));
  const businessReadingCaseIdRef = useRef(loadStoredCaseId());

  useEffect(() => {
    testConnection();
    refreshEnvSettings();
    fetchComponents();
    fetchSkills();
    fetchCases();
    fetchKnowledgeAssets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    saveClientSettings(settings);
  }, [settings]);

  useEffect(() => {
    saveJson(RUN_HISTORY_KEY, history.slice(0, 50));
  }, [history]);

  useEffect(() => {
    saveJson(COMPONENT_CACHE_KEY, components);
  }, [components]);

  useEffect(() => {
    saveStoredCaseId(currentCaseId);
  }, [currentCaseId]);

  useEffect(() => {
    businessReadingCaseIdRef.current = currentCaseId;
  }, [currentCaseId]);

  useEffect(() => {
    saveBusinessReadingContext(businessReadingCaseIdRef.current, businessReadingContext);
  }, [businessReadingContext]);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(() => setNotice(""), 2400);
    return () => clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    const nextContext = resolveBusinessReadingContext(currentCaseId);
    setBusinessReadingContext((prev) => (isSameBusinessReadingContext(prev, nextContext) ? prev : nextContext));
  }, [currentCaseId]);

  useEffect(() => {
    const storedContext = resolveBusinessReadingContext(currentCaseId);
    const reportsWorkContext = normalizeExpertWorkContext(storedContext.expertWorkContextByView?.reports);
    setSelectedProposalId((prev) => (prev === reportsWorkContext.selectedProposalId ? prev : reportsWorkContext.selectedProposalId));
    setSelectedEvidenceChunkId((prev) =>
      prev === reportsWorkContext.selectedEvidenceChunkId ? prev : reportsWorkContext.selectedEvidenceChunkId
    );
    setSelectedDeliveryFragmentId((prev) =>
      prev === reportsWorkContext.selectedDeliveryFragmentId ? prev : reportsWorkContext.selectedDeliveryFragmentId
    );
  }, [currentCaseId]);

  useEffect(() => {
    if (mode === "business" && EXPERT_VIEWS.includes(view)) {
      setView(businessReadingContext.lastView || "overview");
      return;
    }
    if (mode === "expert" && BUSINESS_VIEWS.includes(view)) {
      setView(businessReadingContext.lastExpertView || "mission");
    }
  }, [businessReadingContext.lastExpertView, businessReadingContext.lastView, mode, view]);

  useEffect(() => {
    if (mode === "business" && BUSINESS_VIEWS.includes(view)) {
      setBusinessReadingContext((prev) => (prev.lastView === view ? prev : { ...prev, lastView: view }));
      return;
    }
    if (mode === "expert" && EXPERT_VIEWS.includes(view)) {
      setBusinessReadingContext((prev) => (prev.lastExpertView === view ? prev : { ...prev, lastExpertView: view }));
    }
  }, [mode, view]);

  useEffect(() => {
    if (!result?.case_id) return;
    setCurrentCaseId(result.case_id);
    if (result.case_memory) {
      setCurrentCaseDetails(result.case_memory);
      setCaseCatalog((prev) => mergeCaseSummary(prev, summarizeCase(result.case_memory)));
    }
  }, [result]);

  useEffect(() => {
    setReplayScope({
      runId: "",
      stageRef: "",
      projectionRef: "",
      handoffRef: "",
      targetServiceRef: "",
      artifactLookupRef: "",
      evidenceLookupRef: "",
      retryResumeCheckpointRef: "",
      retryResumeInputRef: "",
    });
    setReplayEventsResponse(null);
    setReplaySnapshotsResponse(null);
    setReplayEventsError("");
    setReplaySnapshotsError("");
    setReplaySourceUpdatedAt({
      drilldown: "",
      events: "",
      snapshots: "",
    });
    setReplaySourceParams({
      drilldown: {},
      events: {},
      snapshots: {},
    });
    setReplaySourceHistory({
      drilldown: [],
      events: [],
      snapshots: [],
    });
    setReplayLineage(null);
    setReplayLineageError("");
  }, [currentCaseId]);

  useEffect(() => {
    const caseId = String(currentCaseId || "").trim();
    if (!caseId) {
      setTimelineOverview(null);
      return undefined;
    }

    let cancelled = false;
    setTimelineOverview(null);
    (async () => {
      try {
        const data = await getCaseTimelineOverview(caseId, settings);
        if (!cancelled) {
          setTimelineOverview(data);
        }
      } catch (err) {
        if (!cancelled) {
          setTimelineOverview(null);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [currentCaseId, settings, result?.run_id]);

  useEffect(() => {
    const caseId = String(currentCaseId || "").trim();
    if (!caseId) {
      setReplayDrilldown(null);
      setReplayError("");
      setReplayLoading(false);
      return undefined;
    }

    const preferredRunId =
      result?.case_id === caseId && result?.run_id
        ? String(result.run_id || "").trim()
        : String(timelineOverview?.case_id === caseId ? timelineOverview?.latest_run_id || "" : "").trim();

    if (!preferredRunId) {
      setReplayDrilldown(null);
      setReplayError("");
      setReplayLoading(false);
      return undefined;
    }

    let cancelled = false;
    setReplayLoading(true);
    setReplayError("");

    (async () => {
      try {
        const params = buildReplayQueryParams(preferredRunId, replayScope, 12);
        setReplaySourceParams((prev) => ({
          ...(prev || {}),
          drilldown: params,
        }));
        const data = await getCaseTimelineDrilldown(
          caseId,
          params,
          settings
        );
        if (!cancelled) {
          setReplayDrilldown(data);
          markReplaySourceUpdated(setReplaySourceUpdatedAt, "drilldown");
          appendReplaySourceHistory(setReplaySourceHistory, "drilldown", "success", "回放钻取数据拉取成功");
        }
      } catch (err) {
        if (!cancelled) {
          setReplayDrilldown(null);
          setReplayError(err.message || "回放钻取数据拉取失败");
          appendReplaySourceHistory(
            setReplaySourceHistory,
            "drilldown",
            "error",
            err.message || "回放钻取数据拉取失败"
          );
        }
      } finally {
        if (!cancelled) {
          setReplayLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    currentCaseId,
    replayScope.artifactLookupRef,
    replayScope.evidenceLookupRef,
    replayScope.handoffRef,
    replayScope.projectionRef,
    replayScope.retryResumeCheckpointRef,
    replayScope.retryResumeInputRef,
    result?.case_id,
    result?.run_id,
    replayRefreshNonce.drilldown,
    settings,
    timelineOverview?.latest_run_id,
    timelineOverview?.case_id,
  ]);

  useEffect(() => {
    const caseId = String(currentCaseId || "").trim();
    if (!caseId) {
      setReplayEventsResponse(null);
      setReplayEventsError("");
      setReplayEventsLoading(false);
      return undefined;
    }

    const preferredRunId =
      result?.case_id === caseId && result?.run_id
        ? String(result.run_id || "").trim()
        : String(timelineOverview?.case_id === caseId ? timelineOverview?.latest_run_id || "" : "").trim();

    if (!preferredRunId) {
      setReplayEventsResponse(null);
      setReplayEventsError("");
      setReplayEventsLoading(false);
      return undefined;
    }

    let cancelled = false;
    const params = buildReplayQueryParams(preferredRunId, replayScope, 12);
    setReplaySourceParams((prev) => ({
      ...(prev || {}),
      events: params,
    }));
    setReplayEventsLoading(true);
    setReplayEventsError("");

    (async () => {
      try {
        const data = await getCaseTimelineEvents(caseId, params, settings);
        if (!cancelled) {
          setReplayEventsResponse(data);
          markReplaySourceUpdated(setReplaySourceUpdatedAt, "events");
          appendReplaySourceHistory(setReplaySourceHistory, "events", "success", "事件列表拉取成功");
        }
      } catch (err) {
        if (!cancelled) {
          setReplayEventsResponse(null);
          setReplayEventsError(err.message || "回放事件列表拉取失败");
          appendReplaySourceHistory(
            setReplaySourceHistory,
            "events",
            "error",
            err.message || "回放事件列表拉取失败"
          );
        }
      } finally {
        if (!cancelled) {
          setReplayEventsLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    currentCaseId,
    replayScope.artifactLookupRef,
    replayScope.evidenceLookupRef,
    replayScope.handoffRef,
    replayScope.projectionRef,
    replayScope.retryResumeCheckpointRef,
    replayScope.retryResumeInputRef,
    result?.case_id,
    result?.run_id,
    replayRefreshNonce.events,
    settings,
    timelineOverview?.latest_run_id,
    timelineOverview?.case_id,
  ]);

  useEffect(() => {
    const caseId = String(currentCaseId || "").trim();
    if (!caseId) {
      setReplaySnapshotsResponse(null);
      setReplaySnapshotsError("");
      setReplaySnapshotsLoading(false);
      return undefined;
    }

    const preferredRunId =
      result?.case_id === caseId && result?.run_id
        ? String(result.run_id || "").trim()
        : String(timelineOverview?.case_id === caseId ? timelineOverview?.latest_run_id || "" : "").trim();

    if (!preferredRunId) {
      setReplaySnapshotsResponse(null);
      setReplaySnapshotsError("");
      setReplaySnapshotsLoading(false);
      return undefined;
    }

    let cancelled = false;
    const params = buildReplayQueryParams(preferredRunId, replayScope, 12);
    setReplaySourceParams((prev) => ({
      ...(prev || {}),
      snapshots: params,
    }));
    setReplaySnapshotsLoading(true);
    setReplaySnapshotsError("");

    (async () => {
      try {
        const data = await getCaseTimelineSnapshots(caseId, params, settings);
        if (!cancelled) {
          setReplaySnapshotsResponse(data);
          markReplaySourceUpdated(setReplaySourceUpdatedAt, "snapshots");
          appendReplaySourceHistory(setReplaySourceHistory, "snapshots", "success", "快照列表拉取成功");
        }
      } catch (err) {
        if (!cancelled) {
          setReplaySnapshotsResponse(null);
          setReplaySnapshotsError(err.message || "回放快照列表拉取失败");
          appendReplaySourceHistory(
            setReplaySourceHistory,
            "snapshots",
            "error",
            err.message || "回放快照列表拉取失败"
          );
        }
      } finally {
        if (!cancelled) {
          setReplaySnapshotsLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    currentCaseId,
    replayScope.artifactLookupRef,
    replayScope.evidenceLookupRef,
    replayScope.handoffRef,
    replayScope.projectionRef,
    replayScope.retryResumeCheckpointRef,
    replayScope.retryResumeInputRef,
    result?.case_id,
    result?.run_id,
    replayRefreshNonce.snapshots,
    settings,
    timelineOverview?.latest_run_id,
    timelineOverview?.case_id,
  ]);

  useEffect(() => {
    const caseId = String(currentCaseId || "").trim();
    const targetServiceRef = String(replayScope.targetServiceRef || "").trim();
    if (!caseId || !targetServiceRef) {
      setReplayLineage(null);
      setReplayLineageError("");
      setReplayLineageLoading(false);
      return undefined;
    }

    const preferredRunId =
      result?.case_id === caseId && result?.run_id
        ? String(result.run_id || "").trim()
        : String(timelineOverview?.case_id === caseId ? timelineOverview?.latest_run_id || "" : "").trim();

    let cancelled = false;
    setReplayLineageLoading(true);
    setReplayLineageError("");

    (async () => {
      try {
        const data = await getCaseTimelineLineage(
          caseId,
          {
            run_id: preferredRunId,
            target_service_ref: targetServiceRef,
            limit: 12,
          },
          settings
        );
        if (!cancelled) {
          setReplayLineage(data);
        }
      } catch (err) {
        if (!cancelled) {
          setReplayLineage(null);
          setReplayLineageError(err.message || "閻楀牊婀扮拫杈╅兇閹峰褰囨径杈Е");
        }
      } finally {
        if (!cancelled) {
          setReplayLineageLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    currentCaseId,
    replayScope.targetServiceRef,
    result?.case_id,
    result?.run_id,
    settings,
    timelineOverview?.latest_run_id,
    timelineOverview?.case_id,
  ]);

  useEffect(() => {
    const current = result?.delivery?.selected_proposal || "";
    if (current) {
      setSelectedProposalId(current);
    }
  }, [result?.delivery?.selected_proposal]);

  const replayListLoading = replayEventsLoading || replaySnapshotsLoading;
  const replayListError = [replayEventsError, replaySnapshotsError].filter(Boolean).join("；");

  function refreshReplaySource(sourceId) {
    const normalized = String(sourceId || "").trim();
    if (!normalized) return;
    setReplayRefreshNonce((prev) => ({
      ...(prev || {}),
      [normalized]: Number(prev?.[normalized] || 0) + 1,
    }));
  }

  const {
    discussionLog,
    finalScheme,
    architectCandidates,
    auditorRounds,
    engineerAttempts,
    clarifications,
    structuredSpec,
    delivery,
    attackLoop,
    codeArtifacts,
    workflowTrace,
    contextProjections,
    memoryHandoffs,
    sandboxDispatcher,
    credibilityAssessment,
    credibilitySources,
    componentEvidence,
    evidencePack,
    comparisonTable,
    comparisonCharts,
    selectedSkill,
    filteredDiscussionLog,
    filteredComponents,
    workflowProgress,
    componentGroups,
    auditFindings,
    auditRecommendations,
    deliveryPackage,
    metrics,
  } = useMasDerivedState({
    result,
    streamLog,
    selectedActor,
    skills,
    selectedSkillId,
    componentFilter,
    components,
  });

  const latestEngineLabel = useMemo(() => {
    const engine = String(delivery?.engine || "").toLowerCase();
    const mode = String(delivery?.engine_mode || "").toLowerCase();
    if (engine === "langgraph") {
      return mode === "graph-native" ? "最近交付：LangGraph 主流程" : "最近交付：LangGraph";
    }
    if (engine === "legacy") {
      return "最近交付：历史兼容链路";
    }
    return "默认执行：LangGraph 主流程";
  }, [delivery?.engine, delivery?.engine_mode]);

  useEffect(() => {
    hydrateRunDraft({
      requirement,
      streaming,
      maxRegressionRounds: Math.max(0, Number(maxAuditRounds || 1) - 1),
    });
  }, [hydrateRunDraft, requirement, streaming, maxAuditRounds]);

  useEffect(() => {
    hydrateRunSession({
      activeRunId,
      caseId: currentCaseId,
      loading,
      result,
      latestEngineLabel,
    });
  }, [hydrateRunSession, activeRunId, currentCaseId, loading, result, latestEngineLabel]);

  useEffect(() => {
    hydrateStageConsole({
      workflowProgress,
      events: streamLog,
    });
  }, [hydrateStageConsole, workflowProgress, streamLog]);

  useEffect(() => {
    const rounds = Array.isArray(attackLoop?.rounds)
      ? attackLoop.rounds
      : Array.isArray(attackLoop?.attack_results)
        ? attackLoop.attack_results
        : [];
    const telemetry = rounds.flatMap((round) => round?.metrics?.traffic_series || round?.attack_result?.metrics?.traffic_series || []);
    const findings = Array.isArray(attackLoop?.vulnerability_verdict?.findings)
      ? attackLoop.vulnerability_verdict.findings
      : [];
    hydrateAttackLoop({
      rounds,
      telemetry,
      findings,
      loopStatus: attackLoop?.loop_status || attackLoop?.status || "",
    });
  }, [hydrateAttackLoop, attackLoop]);

  const currentCaseSummary = useMemo(() => {
    if (currentCaseDetails?.case_id && currentCaseDetails.case_id === currentCaseId) {
      return summarizeCase(currentCaseDetails);
    }
    if (result?.case_id && result.case_id === currentCaseId && result.case_memory) {
      return summarizeCase(result.case_memory);
    }
    return caseCatalog.find((item) => item.case_id === currentCaseId) || null;
  }, [currentCaseDetails, result, currentCaseId, caseCatalog]);

  function getRecommendedBusinessSection(nextView) {
    const normalizedView = BUSINESS_VIEWS.includes(nextView) ? nextView : businessReadingContext.lastView || "overview";
    const storedSection = String(businessReadingContext.recommendedSectionByView?.[normalizedView] || "").trim();
    if (storedSection) return storedSection;
    return "";
  }

  function getRememberedExpertSection(nextView) {
    const normalizedView = EXPERT_VIEWS.includes(nextView) ? nextView : businessReadingContext.lastExpertView || "mission";
    return String(businessReadingContext.expertSectionByView?.[normalizedView] || "").trim();
  }

  function getRememberedExpertWorkContext(nextView) {
    const normalizedView = EXPERT_VIEWS.includes(nextView) ? nextView : businessReadingContext.lastExpertView || "mission";
    return normalizeExpertWorkContext(businessReadingContext.expertWorkContextByView?.[normalizedView]);
  }

  function getRememberedBusinessSection(nextView) {
    const normalizedView = BUSINESS_VIEWS.includes(nextView) ? nextView : businessReadingContext.lastView || "overview";
    const manualSection = String(businessReadingContext.manualSectionByView?.[normalizedView] || "").trim();
    if (manualSection) {
      return {
        sectionId: manualSection,
        source: "manual",
      };
    }
    return {
      sectionId: getRecommendedBusinessSection(normalizedView),
      source: "recommended",
    };
  }

  function persistBusinessRecommendedSection(nextView, sectionId, reason = "recommended_section_sync") {
    const normalizedView = BUSINESS_VIEWS.includes(nextView) ? nextView : businessReadingContext.lastView || "overview";
    const normalizedSection = String(sectionId || "").trim();
    if (!normalizedSection) return;
    setBusinessReadingContext((prev) => {
      if (
        prev.lastView === normalizedView &&
        prev.recommendedSectionByView?.[normalizedView] === normalizedSection &&
        prev.returnReason === reason
      ) {
        return prev;
      }
      return {
        ...prev,
        lastView: normalizedView,
        recommendedSectionByView: {
          ...(prev.recommendedSectionByView || {}),
          [normalizedView]: normalizedSection,
        },
        returnReason: reason,
      };
    });
  }

  function persistBusinessManualSection(nextView, sectionId, reason = "manual_section_sync") {
    const normalizedView = BUSINESS_VIEWS.includes(nextView) ? nextView : businessReadingContext.lastView || "overview";
    const normalizedSection = String(sectionId || "").trim();
    if (!normalizedSection) return;
    setBusinessReadingContext((prev) => {
      if (
        prev.lastView === normalizedView &&
        prev.manualSectionByView?.[normalizedView] === normalizedSection &&
        prev.returnReason === reason
      ) {
        return prev;
      }
      return {
        ...prev,
        lastView: normalizedView,
        manualSectionByView: {
          ...(prev.manualSectionByView || {}),
          [normalizedView]: normalizedSection,
        },
        returnReason: reason,
      };
    });
  }

  function persistExpertSection(nextView, sectionId, reason = "expert_section_sync") {
    const normalizedView = EXPERT_VIEWS.includes(nextView) ? nextView : businessReadingContext.lastExpertView || "mission";
    const normalizedSection = String(sectionId || "").trim();
    if (!normalizedSection) return;
    setBusinessReadingContext((prev) => {
      if (
        prev.lastExpertView === normalizedView &&
        prev.expertSectionByView?.[normalizedView] === normalizedSection &&
        prev.returnReason === reason
      ) {
        return prev;
      }
      return {
        ...prev,
        lastExpertView: normalizedView,
        expertSectionByView: {
          ...(prev.expertSectionByView || {}),
          [normalizedView]: normalizedSection,
        },
        returnReason: reason,
      };
    });
  }

  function persistExpertWorkContext(nextView, workContext, reason = "expert_work_context_sync") {
    const normalizedView = EXPERT_VIEWS.includes(nextView) ? nextView : businessReadingContext.lastExpertView || "mission";
    const normalizedWorkContext = normalizeExpertWorkContext(workContext);
    setBusinessReadingContext((prev) => {
      const currentWorkContext = normalizeExpertWorkContext(prev.expertWorkContextByView?.[normalizedView]);
      if (
        prev.lastExpertView === normalizedView &&
        JSON.stringify(currentWorkContext) === JSON.stringify(normalizedWorkContext) &&
        prev.returnReason === reason
      ) {
        return prev;
      }

      const expertWorkContextByView = {
        ...(prev.expertWorkContextByView || {}),
      };

      if (isEmptyExpertWorkContext(normalizedWorkContext)) {
        delete expertWorkContextByView[normalizedView];
      } else {
        expertWorkContextByView[normalizedView] = normalizedWorkContext;
      }

      return {
        ...prev,
        lastExpertView: normalizedView,
        expertWorkContextByView,
        returnReason: reason,
      };
    });
  }

  useEffect(() => {
    const activeCaseId = String(businessReadingCaseIdRef.current || "").trim();
    if (!activeCaseId) return;
    persistExpertWorkContext(
      "reports",
      {
        selectedProposalId,
        selectedEvidenceChunkId,
        selectedDeliveryFragmentId,
      },
      "reports_work_context_sync"
    );
  }, [selectedProposalId, selectedEvidenceChunkId, selectedDeliveryFragmentId]);

  const rememberedBusinessView = businessReadingContext.lastView || "overview";
  const rememberedBusinessSection = getRememberedBusinessSection(rememberedBusinessView);
  const rememberedReportsWorkContext = getRememberedExpertWorkContext("reports");
  const businessReturnContext = {
    view: rememberedBusinessView,
    viewLabel: getConstructionViewLabel(rememberedBusinessView),
    sectionId: rememberedBusinessSection.sectionId,
    sectionLabel: getConstructionSectionLabel(rememberedBusinessView, rememberedBusinessSection.sectionId) || "页面顶部",
    sectionSource: rememberedBusinessSection.source,
    summary: `返回后会继续从“${getConstructionViewLabel(rememberedBusinessView)} / ${
      getConstructionSectionLabel(rememberedBusinessView, rememberedBusinessSection.sectionId) || "页面顶部"
    }”开始。${rememberedBusinessSection.source === "manual" ? " 这是你手动选择过的阅读落点。" : " 当前仍优先跟随系统推荐落点。"} `,
  };

  function scrollViewportToTop() {
    if (typeof window === "undefined") return;
    window.requestAnimationFrame(() => {
      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    });
  }

  function openBusinessView(nextView, options = {}) {
    const normalizedView = BUSINESS_VIEWS.includes(nextView) ? nextView : businessReadingContext.lastView || "overview";
    const shouldClearManualSection = Boolean(options.clearManualSection);
    const rememberedSection = shouldClearManualSection ? { sectionId: "", source: "recommended" } : getRememberedBusinessSection(normalizedView);
    const sectionId = String(options.sectionId || "").trim() || rememberedSection.sectionId;
    if (shouldClearManualSection) {
      setBusinessReadingContext((prev) => {
        const nextManualSectionByView = { ...(prev.manualSectionByView || {}) };
        delete nextManualSectionByView[normalizedView];
        return {
          ...prev,
          lastView: normalizedView,
          manualSectionByView: nextManualSectionByView,
          returnReason: options.reason || "business_nav",
        };
      });
    } else if (sectionId) {
      if (options.sectionSource === "manual" || rememberedSection.source === "manual") {
        persistBusinessManualSection(normalizedView, sectionId, options.reason || "business_nav");
      } else {
        persistBusinessRecommendedSection(normalizedView, sectionId, options.reason || "business_nav");
      }
    } else {
      setBusinessReadingContext((prev) => ({
        ...prev,
        lastView: normalizedView,
        returnReason: options.reason || "business_nav",
      }));
    }
    setMode("business");
    setView(normalizedView);
    if (options.scrollToTop !== false) {
      scrollViewportToTop();
    }
  }

  function openBusinessOverviewHome() {
    if (mode === "business" && view === "overview") {
      scrollViewportToTop();
      return;
    }
    openBusinessView("overview", {
      clearManualSection: true,
      reason: "business_overview_home",
    });
  }

  function openExpertView(nextView = "mission", options = {}) {
    const normalizedExpertView = EXPERT_VIEWS.includes(nextView) ? nextView : businessReadingContext.lastExpertView || "mission";
    const sourceView = BUSINESS_VIEWS.includes(options.fromBusinessView)
      ? options.fromBusinessView
      : BUSINESS_VIEWS.includes(view)
        ? view
        : businessReadingContext.lastView || "overview";
    const rememberedSection = getRememberedBusinessSection(sourceView);
    const sectionId = String(options.sectionId || "").trim() || rememberedSection.sectionId;
    if (sectionId) {
      if (options.sectionSource === "manual" || rememberedSection.source === "manual") {
        persistBusinessManualSection(sourceView, sectionId, options.reason || "expert_nav");
      } else {
        persistBusinessRecommendedSection(sourceView, sectionId, options.reason || "expert_nav");
      }
    }
    setBusinessReadingContext((prev) => ({
      ...prev,
      lastView: sourceView,
      lastExpertView: normalizedExpertView,
      returnReason: options.reason || "expert_nav",
    }));
    setMode("expert");
    setView(normalizedExpertView);
  }

  function returnToBusinessContext(reason = "return_to_business_context") {
    const rememberedSection = getRememberedBusinessSection(businessReadingContext.lastView || "overview");
    openBusinessView(businessReadingContext.lastView || "overview", {
      sectionId: rememberedSection.sectionId,
      sectionSource: rememberedSection.source,
      reason,
    });
  }

  const {
    testConnection,
    testLlmConnection,
    refreshEnvSettings,
    syncEnv,
    fetchComponents,
    fetchSkills,
    fetchCases,
    fetchKnowledgeAssets,
    selectCase,
    removeCase,
    uploadKnowledgeFiles,
    removeKnowledgeArtifacts,
    removeKnowledgeQdrantArtifacts,
    reingestKnowledgeQdrantArtifacts,
    recommendSkill,
    applySkill,
    runMas,
    stopRun,
    resetAllSettings,
  } = useMasActions({
    settings,
    requirement,
    currentCaseId,
    selectedSkill,
    numVariants,
    maxAuditRounds,
    generateCode,
    streaming,
    strictClarification,
    clarificationDetails,
    activeRunId,
    setSettings,
    setBackendEnv,
    setComponents,
    setSkills,
    setCurrentCaseId,
    setCurrentCaseDetails,
    setCaseCatalog,
    setKnowledgeCatalog,
    setKnowledgeIngestionResult,
    setKnowledgeIngestionRunning,
    setRoutingSkill,
    setSelectedSkillId,
    setSkillRoute,
    setRequirement,
    setNumVariants,
    setMaxAuditRounds,
    setGenerateCode,
    setLoading,
    setError,
    setResult,
    setStreamLog,
    setActiveRunId,
    setHistory,
    setNotice,
    setView,
    setConnectionStatus,
    setConnectionMessage,
    setLlmStatus,
    setLlmMessage,
    setStrictClarification,
  });

  const {
    copyText,
    clearLocalData,
    loadFromHistory,
    applyTemplate,
    appendRequirementDimension,
    insertConstructionSkeleton,
  } = useMasLocalOps({
    runHistoryKey: RUN_HISTORY_KEY,
    componentCacheKey: COMPONENT_CACHE_KEY,
    businessReadingContextKey: BUSINESS_READING_CONTEXT_KEY,
    resetBusinessReadingContext: () => setBusinessReadingContext(createDefaultBusinessReadingContext()),
    resetReportFocus: () => {
      setSelectedProposalId("");
      setSelectedEvidenceChunkId("");
      setSelectedDeliveryFragmentId("");
    },
    setHistory,
    setComponents,
    setNotice,
    setResult,
    setView,
    setRequirement,
  });

  const { exportDelivery } = useMasExport({
    deliveryPackage,
    result,
    structuredSpec,
    settings,
    setNotice,
    setError,
  });

  const businessViewCallbacks = {
    onOpenOverview: openBusinessOverviewHome,
    onOpenProject: () => openBusinessView("workbench"),
    onOpenContext: () => openBusinessView("context"),
    onOpenValidation: () => openBusinessView("validation"),
    onOpenDelivery: () => openBusinessView("delivery"),
  };

  const workbenchViewNode = (
    <WorkbenchView
      loading={loading}
      activeRunId={activeRunId}
      runMas={runMas}
      stopRun={stopRun}
      currentCaseId={currentCaseId}
      currentCaseSummary={currentCaseSummary}
      currentCaseDetails={currentCaseDetails}
      caseCatalog={caseCatalog}
      selectCase={selectCase}
      removeCase={removeCase}
      refreshCases={fetchCases}
      createNewCase={() => {
        setCurrentCaseId("");
        setCurrentCaseDetails(null);
        setNotice("\u5df2\u5207\u6362\u4e3a\u65b0\u9879\u76ee\uff0c\u4e0b\u4e00\u6b21\u6267\u884c\u4f1a\u751f\u6210\u65b0\u7684 case_id");
      }}
      requirement={requirement}
      setRequirement={setRequirement}
      skills={skills}
      routingSkill={routingSkill}
      recommendSkill={recommendSkill}
      clearSkillSelection={() => {
        setSelectedSkillId("");
        setSkillRoute(null);
        setNotice("\u5df2\u5207\u56de\u666e\u901a MAS \u6a21\u5f0f");
      }}
      selectedSkillId={selectedSkillId}
      applySkill={applySkill}
      selectedSkill={selectedSkill}
      skillRoute={skillRoute}
      insertConstructionSkeleton={insertConstructionSkeleton}
      constructionInputDimensions={CONSTRUCTION_INPUT_DIMENSIONS}
      appendRequirementDimension={appendRequirementDimension}
      scenarioTemplates={CONSTRUCTION_TEMPLATES}
      applyTemplate={applyTemplate}
      numVariants={numVariants}
      setNumVariants={setNumVariants}
      maxAuditRounds={maxAuditRounds}
      setMaxAuditRounds={setMaxAuditRounds}
      generateCode={generateCode}
      setGenerateCode={setGenerateCode}
      strictClarification={strictClarification}
      setStrictClarification={setStrictClarification}
      clarificationDetails={clarificationDetails}
      setClarificationDetails={setClarificationDetails}
      streaming={streaming}
      setStreaming={setStreaming}
      useLangGraph={Boolean(settings.useLangGraph)}
      architectCandidates={architectCandidates}
      evidencePack={evidencePack}
      selectedProposalId={selectedProposalId}
      setSelectedProposalId={setSelectedProposalId}
      selectedEvidenceChunkId={selectedEvidenceChunkId}
      setSelectedEvidenceChunkId={setSelectedEvidenceChunkId}
      auditorRounds={auditorRounds}
      engineerAttempts={engineerAttempts}
      clarifications={clarifications}
      summarizeMessage={summarizeMessage}
      delivery={delivery}
      result={result}
      finalScheme={finalScheme}
      codeTab={codeTab}
      setCodeTab={setCodeTab}
      copyText={copyText}
      streamLog={streamLog}
      codeArtifacts={codeArtifacts}
      exportFormats={EXPORT_FORMATS}
      exportDelivery={exportDelivery}
      deliveryPackage={deliveryPackage}
      toFixed={toFixed}
    />
  );

  return (
    <StudioShell
      header={
        <StudioHeaderView
          mode={mode}
          view={view}
          settingsOpen={settingsOpen}
          connectionStatus={connectionStatus}
          llmStatus={llmStatus}
          activeRunId={activeRunId}
          latestEngineLabel={latestEngineLabel}
          currentCaseSummary={currentCaseSummary}
        />
      }
      sidebar={
        <StudioSidebarView
          mode={mode}
          view={view}
          setView={setView}
          settingsOpen={settingsOpen}
          setSettingsOpen={setSettingsOpen}
          onOpenOverview={businessViewCallbacks.onOpenOverview}
          onOpenProject={businessViewCallbacks.onOpenProject}
          onOpenContext={businessViewCallbacks.onOpenContext}
          onOpenValidation={businessViewCallbacks.onOpenValidation}
          onOpenDelivery={businessViewCallbacks.onOpenDelivery}
          onOpenComponents={() => {
            setSettingsOpen(false);
            setView("components");
            scrollViewportToTop();
          }}
          onSwitchToBusiness={() => returnToBusinessContext("sidebar_return")}
          onSwitchToExpert={() => openExpertView("mission", { reason: "sidebar_expert" })}
          onReturnToBusinessContext={() => returnToBusinessContext("sidebar_context_return")}
          businessReturnContext={businessReturnContext}
          currentCaseSummary={currentCaseSummary}
        />
      }
      notices={
        <>
          <WorkspaceStatusBanner message={notice} tone="success" />
          <WorkspaceStatusBanner message={error} tone="error" />
        </>
      }
    >
      <Suspense fallback={<ViewLoadingState view={settingsOpen ? "settings" : view} />}>
          {settingsOpen ? (
            <SettingsView
              settings={settings}
              setSettings={setSettings}
              showSecrets={showSecrets}
              setShowSecrets={setShowSecrets}
              backendEnv={backendEnv}
              connectionStatus={connectionStatus}
              connectionMessage={connectionMessage}
              llmStatus={llmStatus}
              llmMessage={llmMessage}
              testConnection={testConnection}
              testLlmConnection={testLlmConnection}
              syncEnv={syncEnv}
              refreshEnvSettings={refreshEnvSettings}
              resetAllSettings={resetAllSettings}
              redactSensitiveObject={redactSensitiveObject}
            />
          ) : (
            <>
        {BUSINESS_VIEWS.includes(view) ? (
          <ConstructionWorkspaceView
            view={view}
            currentCaseSummary={currentCaseSummary}
            delivery={delivery}
            attackLoop={attackLoop}
            settings={settings}
            workbenchContent={workbenchViewNode}
            exportFormats={EXPORT_FORMATS}
            onOpenProject={businessViewCallbacks.onOpenProject}
            onOpenContext={businessViewCallbacks.onOpenContext}
            onOpenValidation={businessViewCallbacks.onOpenValidation}
            onOpenDelivery={businessViewCallbacks.onOpenDelivery}
          />
        ) : null}

        {view === "mission" ? (
          <MissionView
            scenarioTemplates={CONSTRUCTION_TEMPLATES}
            applyTemplate={applyTemplate}
            businessReturnContext={businessReturnContext}
            onReturnToBusinessContext={() => returnToBusinessContext("mission_return")}
            setView={(nextView) => {
              if (nextView === "workbench") {
                openBusinessView("workbench");
                return;
              }
              setView(nextView);
            }}
            teamMembers={TEAM_MEMBERS}
            discussionLog={discussionLog}
            selectedActor={selectedActor}
            setSelectedActor={setSelectedActor}
            actorMatches={actorMatches}
            workflowProgress={workflowProgress}
            filteredDiscussionLog={filteredDiscussionLog}
            formatTime={formatTime}
          />
        ) : null}

        {view === "runtime" ? (
          <RuntimeConsoleView
            requirement={requirement}
            setRequirement={setRequirement}
            numVariants={numVariants}
            setNumVariants={setNumVariants}
            maxAuditRounds={maxAuditRounds}
            setMaxAuditRounds={setMaxAuditRounds}
            generateCode={generateCode}
            setGenerateCode={setGenerateCode}
            streaming={streaming}
            setStreaming={setStreaming}
            strictClarification={strictClarification}
            setStrictClarification={setStrictClarification}
            loading={loading}
            activeRunId={activeRunId}
            runMas={runMas}
            stopRun={stopRun}
            currentCaseSummary={currentCaseSummary}
            latestEngineLabel={latestEngineLabel}
            workflowProgress={workflowProgress}
            streamLog={streamLog}
            memoryHandoffs={memoryHandoffs}
            contextProjections={contextProjections}
            attackLoop={attackLoop}
            sandboxDispatcher={sandboxDispatcher}
            replayScope={replayScope}
            setReplayScope={setReplayScope}
            deliveryPackage={deliveryPackage}
            codeArtifacts={codeArtifacts}
            replayDrilldown={replayDrilldown}
            result={result}
          />
        ) : null}

        {view === "workbench" && mode !== "business" ? workbenchViewNode : null}

        {view === "components" ? (
          <ComponentsView
            fetchComponents={fetchComponents}
            componentFilter={componentFilter}
            setComponentFilter={setComponentFilter}
            filteredComponents={filteredComponents}
          />
        ) : null}

        {view === "reports" ? (
          <ReportsView
            businessReturnContext={businessReturnContext}
            onReturnToBusinessContext={() => returnToBusinessContext("reports_return")}
            persistedSectionId={getRememberedExpertSection("reports")}
            onSyncActiveSection={(sectionId) => persistExpertSection("reports", sectionId, "reports_section_sync")}
            currentCaseId={currentCaseId}
            currentCaseSummary={currentCaseSummary}
            structuredSpec={structuredSpec}
            clarifications={clarifications}
            result={result}
            auditorRounds={auditorRounds}
            auditFindings={auditFindings}
            auditRecommendations={auditRecommendations}
            delivery={delivery}
            attackLoop={attackLoop}
            codeArtifacts={codeArtifacts}
            workflowTrace={workflowTrace}
            workflowProgress={workflowProgress}
            contextProjections={contextProjections}
            memoryHandoffs={memoryHandoffs}
            sandboxDispatcher={sandboxDispatcher}
            timelineOverview={timelineOverview}
            replayDrilldown={replayDrilldown}
            replayEventsResponse={replayEventsResponse}
            replaySnapshotsResponse={replaySnapshotsResponse}
            replayScope={replayScope}
            setReplayScope={setReplayScope}
            replayLineage={replayLineage}
            replayLoading={replayLoading}
            replayError={replayError}
            replayEventsLoading={replayEventsLoading}
            replayEventsError={replayEventsError}
            replaySnapshotsLoading={replaySnapshotsLoading}
            replaySnapshotsError={replaySnapshotsError}
            replayListLoading={replayListLoading}
            replayListError={replayListError}
            replaySourceUpdatedAt={replaySourceUpdatedAt}
            replaySourceParams={replaySourceParams}
            replaySourceHistory={replaySourceHistory}
            refreshReplaySource={refreshReplaySource}
            replayLineageLoading={replayLineageLoading}
            replayLineageError={replayLineageError}
            architectCandidates={architectCandidates}
            credibilityAssessment={credibilityAssessment}
            credibilitySources={credibilitySources}
            componentEvidence={componentEvidence}
            evidencePack={evidencePack}
            comparisonTable={comparisonTable}
            comparisonCharts={comparisonCharts}
            finalScheme={finalScheme}
            deliveryPackage={deliveryPackage}
            exportFormats={EXPORT_FORMATS}
            exportDelivery={exportDelivery}
            history={history}
            selectedProposalId={selectedProposalId}
            setSelectedProposalId={setSelectedProposalId}
            selectedEvidenceChunkId={selectedEvidenceChunkId}
            setSelectedEvidenceChunkId={setSelectedEvidenceChunkId}
            selectedDeliveryFragmentId={selectedDeliveryFragmentId || rememberedReportsWorkContext.selectedDeliveryFragmentId}
            setSelectedDeliveryFragmentId={setSelectedDeliveryFragmentId}
            formatDisplayValue={formatDisplayValue}
            RadarChartComponent={SimpleRadarChart}
            BarChartComponent={SimpleBarChart}
            ScatterChartComponent={SimpleScatterChart}
          />
        ) : null}

        {view === "ops" ? (
          <OpsView
            history={history}
            components={components}
            activeRunId={activeRunId}
            clearLocalData={clearLocalData}
            fetchComponents={fetchComponents}
            copyText={copyText}
            settings={settings}
            result={result}
            knowledgeIngestionResult={knowledgeIngestionResult}
            knowledgeCatalog={knowledgeCatalog}
            knowledgeIngestionRunning={knowledgeIngestionRunning}
            uploadKnowledgeFiles={uploadKnowledgeFiles}
            removeKnowledgeArtifacts={removeKnowledgeArtifacts}
            removeKnowledgeQdrantArtifacts={removeKnowledgeQdrantArtifacts}
            reingestKnowledgeQdrantArtifacts={reingestKnowledgeQdrantArtifacts}
          />
        ) : null}
            </>
          )}
      </Suspense>
    </StudioShell>
  );
}

export default App;
