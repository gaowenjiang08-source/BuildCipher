const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const SETTINGS_STORAGE_KEY = "buildtrust.mas.settings";

export function loadClientSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) return getDefaultSettings();
    return { ...getDefaultSettings(), ...JSON.parse(raw), useLangGraph: true };
  } catch {
    return getDefaultSettings();
  }
}

export function saveClientSettings(settings) {
  const safeSettings = Object.fromEntries(
    Object.entries(settings || {}).filter(([key]) => !key.toLowerCase().endsWith("apikey"))
  );
  localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify({ ...safeSettings, useLangGraph: true }));
}

export function getDefaultSettings() {
  return {
    apiBaseUrl: DEFAULT_API_BASE,
    apiKeyHeader: "X-API-Key",
    apiKeyValue: "",
    provider: "openai",
    timeoutMs: 120000,
    openaiApiKey: "",
    anthropicApiKey: "",
    zhipuaiApiKey: "",
    geminiApiKey: "",
    deepseekApiKey: "",
    qwenApiKey: "",
    baiduApiKey: "",
    relayApiKey: "",
    openaiModel: "gpt-4-turbo-preview",
    anthropicModel: "claude-3-opus-20240229",
    zhipuaiModel: "glm-4",
    geminiModel: "gemini-1.5-pro",
    deepseekModel: "deepseek-chat",
    qwenModel: "qwen-plus",
    baiduModel: "ernie-4.0-turbo-8k",
    relayModel: "gpt-4o-mini",
    openaiBaseUrl: "",
    anthropicBaseUrl: "",
    zhipuaiBaseUrl: "",
    geminiBaseUrl: "",
    deepseekBaseUrl: "https://api.deepseek.com",
    qwenBaseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    baiduBaseUrl: "",
    relayBaseUrl: "",
    useLangGraph: true,
  };
}

function buildHeaders(settings = {}) {
  const headers = { "Content-Type": "application/json" };
  const keyHeader = settings.apiKeyHeader?.trim();
  const keyValue = settings.apiKeyValue?.trim();
  if (keyHeader && keyValue) headers[keyHeader] = keyValue;
  return headers;
}

function buildApiBase(settings = {}) {
  return (settings.apiBaseUrl || DEFAULT_API_BASE).replace(/\/+$/, "");
}

async function requestJson(path, options = {}, settings = {}) {
  const controller = new AbortController();
  const externalSignal = options.signal;
  const abortFromExternal = () => controller.abort();
  if (externalSignal) {
    if (externalSignal.aborted) controller.abort();
    else externalSignal.addEventListener("abort", abortFromExternal, { once: true });
  }
  const timeout = setTimeout(() => controller.abort(), Number(settings.timeoutMs || 120000));
  try {
    const headers = {
      ...buildHeaders(settings),
      ...(options.headers || {}),
    };
    if (options.body instanceof FormData) delete headers["Content-Type"];
    const response = await fetch(`${buildApiBase(settings)}${path}`, {
      ...options,
      signal: controller.signal,
      headers,
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail || `Request failed with ${response.status}`);
    }
    return response.json();
  } finally {
    clearTimeout(timeout);
    if (externalSignal) externalSignal.removeEventListener("abort", abortFromExternal);
  }
}

function buildQuerySuffix(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") return;
    query.set(key, String(value));
  });
  const text = query.toString();
  return text ? `?${text}` : "";
}

export function getHealth(settings = {}) {
  return requestJson("/api/v1/health", { method: "GET" }, settings);
}

export function runConstructionDemo(payload = {}, settings = {}) {
  return requestJson(
    "/api/v1/construction/demo/run",
    { method: "POST", body: JSON.stringify(payload) },
    settings
  );
}

export function importConstructionIfc(payload = {}, settings = {}) {
  const form = new FormData();
  form.append("file", payload.file);
  form.append("project_id", payload.projectId);
  form.append("asset_id", payload.assetId || "ifc-main-model");
  form.append("version", payload.version || "v3");
  form.append("parent_version", payload.parentVersion || "v2");
  form.append("approval_state", payload.approvalState || "approved");
  return requestJson(
    "/api/v1/construction/assets/import",
    { method: "POST", body: form },
    settings
  );
}

export function getComponents(limit = 200, settings = {}) {
  return requestJson(`/api/v1/components?limit=${limit}`, { method: "GET" }, settings);
}

export function getSkills(settings = {}) {
  return requestJson("/api/v1/skills", { method: "GET" }, settings);
}

export function getCases(limit = 20, settings = {}) {
  return requestJson(`/api/v1/cases?limit=${limit}`, { method: "GET" }, settings);
}

export function getCaseMemory(caseId, settings = {}) {
  return requestJson(`/api/v1/cases/${encodeURIComponent(caseId)}`, { method: "GET" }, settings);
}

export function getCaseTimelineOverview(caseId, settings = {}) {
  return requestJson(`/api/v1/cases/${encodeURIComponent(caseId)}/timeline`, { method: "GET" }, settings);
}

export function getCaseTimelineEvents(caseId, params = {}, settings = {}) {
  return requestJson(
    `/api/v1/cases/${encodeURIComponent(caseId)}/timeline/events${buildQuerySuffix(params)}`,
    { method: "GET" },
    settings
  );
}

export function getCaseTimelineSnapshots(caseId, params = {}, settings = {}) {
  return requestJson(
    `/api/v1/cases/${encodeURIComponent(caseId)}/timeline/snapshots${buildQuerySuffix(params)}`,
    { method: "GET" },
    settings
  );
}

export function getCaseTimelineDrilldown(caseId, params = {}, settings = {}) {
  return requestJson(
    `/api/v1/cases/${encodeURIComponent(caseId)}/timeline/drilldown${buildQuerySuffix(params)}`,
    { method: "GET" },
    settings
  );
}

export function getCaseTimelineLineage(caseId, params = {}, settings = {}) {
  return requestJson(
    `/api/v1/cases/${encodeURIComponent(caseId)}/timeline/lineage${buildQuerySuffix(params)}`,
    { method: "GET" },
    settings
  );
}

export function deleteCaseMemory(caseId, settings = {}) {
  return requestJson(`/api/v1/cases/${encodeURIComponent(caseId)}`, { method: "DELETE" }, settings);
}

export function deleteKnowledgeIngestion(requestId, settings = {}) {
  return requestJson(`/api/v1/knowledge/ingest/${encodeURIComponent(requestId)}`, { method: "DELETE" }, settings);
}

export function deleteKnowledgeIngestionQdrant(requestId, settings = {}) {
  return requestJson(`/api/v1/knowledge/ingest/${encodeURIComponent(requestId)}/qdrant`, { method: "DELETE" }, settings);
}

export function reingestKnowledgeIngestionQdrant(requestId, settings = {}) {
  return requestJson(`/api/v1/knowledge/ingest/${encodeURIComponent(requestId)}/qdrant`, { method: "POST" }, settings);
}

export function getKnowledgeIngestions(limit = 20, settings = {}) {
  return requestJson(`/api/v1/knowledge/ingestions?limit=${limit}`, { method: "GET" }, settings);
}

export async function ingestKnowledgeDocuments(payload, settings = {}) {
  const form = new FormData();
  const files = Array.isArray(payload?.files) ? payload.files : [];
  files.forEach((file) => {
    if (file) form.append("files", file);
  });
  form.append("doc_type", payload?.docType || "standard");
  form.append("title", payload?.title || "");
  form.append("metadata_json", JSON.stringify(payload?.metadata || {}));
  form.append("upsert_qdrant", payload?.upsertQdrant ? "true" : "false");

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Number(settings.timeoutMs || 120000));
  try {
    const response = await fetch(`${buildApiBase(settings)}/api/v1/knowledge/ingest`, {
      method: "POST",
      signal: controller.signal,
      headers: {
        ...Object.fromEntries(
          Object.entries(buildHeaders(settings)).filter(([key]) => key.toLowerCase() !== "content-type")
        ),
      },
      body: form,
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail || `Request failed with ${response.status}`);
    }
    return response.json();
  } finally {
    clearTimeout(timeout);
  }
}

export function routeSkill(payload, settings = {}) {
  return requestJson(
    "/api/v1/skills/route",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    settings
  );
}

export async function validateConnection(settings = {}) {
  const health = await getHealth(settings);
  const components = await getComponents(3, settings);
  return { health, components };
}

function getProviderRuntimeConfig(provider, settings = {}) {
  const normalized = String(provider || settings.provider || "openai").toLowerCase();
  const aliases = {
    claude: "anthropic",
    google: "gemini",
    glm: "zhipuai",
    tongyi: "qwen",
    dashscope: "qwen",
    wenxin: "baidu",
    qianfan: "baidu",
    openai_compatible: "relay",
    custom: "relay",
  };
  const id = aliases[normalized] || normalized;
  const prefix = id === "openai" ? "openai" : id;
  const keyName = `${prefix}ApiKey`;
  const modelName = `${prefix}Model`;
  const baseUrlName = `${prefix}BaseUrl`;
  return {
    api_key: settings[keyName] || null,
    model: settings[modelName] || null,
    base_url: settings[baseUrlName] || null,
  };
}

export function validateLlmConnection(provider, prompt, settings = {}) {
  const runtimeConfig = getProviderRuntimeConfig(provider, settings);
  return requestJson(
    "/api/v1/llm/validate",
    {
      method: "POST",
      body: JSON.stringify({
        provider,
        prompt: prompt || "Return only the word OK.",
        ...runtimeConfig,
      }),
    },
    settings
  );
}

export function getBackendEnvSettings(settings = {}) {
  return requestJson("/api/v1/settings/env", { method: "GET" }, settings);
}

export function syncBackendEnvSettings(payload, settings = {}) {
  return requestJson(
    "/api/v1/settings/env",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    settings
  );
}

export function executeMas(payload, settings = {}, options = {}) {
  return requestJson(
    "/api/v1/mas/execute",
    {
      method: "POST",
      body: JSON.stringify(payload),
      signal: options.signal,
    },
    settings
  );
}

export function executeSkill(payload, settings = {}, options = {}) {
  return requestJson(
    "/api/v1/skills/execute",
    {
      method: "POST",
      body: JSON.stringify(payload),
      signal: options.signal,
    },
    settings
  );
}

export function cancelMasRun(runId, settings = {}) {
  return requestJson(`/api/v1/mas/cancel/${encodeURIComponent(runId)}`, { method: "POST" }, settings);
}

export function generateMasReport(payload, settings = {}) {
  return requestJson(
    "/api/v1/mas/report",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    settings
  );
}

export async function executeMasStream(payload, settings = {}, handlers = {}) {
  const url = `${buildApiBase(settings)}/api/v1/mas/stream`;
  const response = await fetch(url, {
    method: "POST",
    headers: buildHeaders(settings),
    body: JSON.stringify(payload),
    signal: handlers.signal,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Stream request failed with ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Streaming is not supported in this environment.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      let parsed = null;
      try {
        parsed = JSON.parse(trimmed);
      } catch {
        continue;
      }
      if (parsed.type === "progress" && handlers.onProgress) handlers.onProgress(parsed.data);
      if (parsed.type === "run" && handlers.onRun) {
        handlers.onRun(parsed.run_id, parsed.engine);
      }
      if (parsed.type === "final" && handlers.onFinal) handlers.onFinal(parsed.data);
      if (parsed.type === "cancelled" && handlers.onCancelled) handlers.onCancelled(parsed);
      if (parsed.type === "error" && handlers.onError) handlers.onError(parsed.message || "Stream error");
    }
  }
}

export async function executeSkillStream(payload, settings = {}, handlers = {}) {
  const response = await fetch(`${buildApiBase(settings)}/api/v1/skills/stream`, {
    method: "POST",
    headers: buildHeaders(settings),
    body: JSON.stringify(payload),
    signal: handlers.signal,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Skill stream request failed with ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Streaming is not supported in this environment.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      let parsed = null;
      try {
        parsed = JSON.parse(trimmed);
      } catch {
        continue;
      }
      if (parsed.type === "progress" && handlers.onProgress) handlers.onProgress(parsed.data);
      if (parsed.type === "run" && handlers.onRun) handlers.onRun(parsed.run_id, parsed.engine);
      if (parsed.type === "final" && handlers.onFinal) handlers.onFinal(parsed.data);
      if (parsed.type === "cancelled" && handlers.onCancelled) handlers.onCancelled(parsed);
      if (parsed.type === "error" && handlers.onError) handlers.onError(parsed.message || "Skill stream error");
    }
  }
}
