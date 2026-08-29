import {
  cancelMasRun,
  deleteCaseMemory,
  deleteKnowledgeIngestion,
  deleteKnowledgeIngestionQdrant,
  executeMas,
  executeMasStream,
  executeSkill,
  executeSkillStream,
  getBackendEnvSettings,
  getCaseMemory,
  getCases,
  getComponents,
  getDefaultSettings,
  getKnowledgeIngestions,
  getSkills,
  ingestKnowledgeDocuments,
  reingestKnowledgeIngestionQdrant,
  routeSkill,
  saveClientSettings,
  syncBackendEnvSettings,
  validateConnection,
  validateLlmConnection,
} from "../../api/client";
import { useRef } from "react";

import {
  buildRequirementWithClarifications,
  listBlockingClarificationLabels,
} from "./clarificationHelpers";

function normalizeSecretForSync(value) {
  const text = String(value || "").trim();
  if (!text) return null;
  if (text.includes("...") || /^\*+$/.test(text)) return null;
  return text;
}

function buildEnvSyncPayload(settings = {}) {
  return {
    default_llm_provider: settings.provider,
    openai_api_key: normalizeSecretForSync(settings.openaiApiKey),
    anthropic_api_key: normalizeSecretForSync(settings.anthropicApiKey),
    zhipuai_api_key: normalizeSecretForSync(settings.zhipuaiApiKey),
    gemini_api_key: normalizeSecretForSync(settings.geminiApiKey),
    deepseek_api_key: normalizeSecretForSync(settings.deepseekApiKey),
    qwen_api_key: normalizeSecretForSync(settings.qwenApiKey),
    baidu_api_key: normalizeSecretForSync(settings.baiduApiKey),
    relay_api_key: normalizeSecretForSync(settings.relayApiKey),
    openai_model: settings.openaiModel || null,
    anthropic_model: settings.anthropicModel || null,
    zhipuai_model: settings.zhipuaiModel || null,
    gemini_model: settings.geminiModel || null,
    deepseek_model: settings.deepseekModel || null,
    qwen_model: settings.qwenModel || null,
    baidu_model: settings.baiduModel || null,
    relay_model: settings.relayModel || null,
    openai_base_url: settings.openaiBaseUrl || null,
    anthropic_base_url: settings.anthropicBaseUrl || null,
    zhipuai_base_url: settings.zhipuaiBaseUrl || null,
    gemini_base_url: settings.geminiBaseUrl || null,
    deepseek_base_url: settings.deepseekBaseUrl || null,
    qwen_base_url: settings.qwenBaseUrl || null,
    baidu_base_url: settings.baiduBaseUrl || null,
    relay_base_url: settings.relayBaseUrl || null,
  };
}

function applyBackendEnvToClientSettings(env, setSettings) {
  const values = env?.values || {};
  setSettings((prev) => ({
    ...prev,
    provider: values.default_llm_provider || prev.provider,
    openaiModel: values.openai_model || prev.openaiModel,
    anthropicModel: values.anthropic_model || prev.anthropicModel,
    zhipuaiModel: values.zhipuai_model || prev.zhipuaiModel,
    geminiModel: values.gemini_model || prev.geminiModel,
    deepseekModel: values.deepseek_model || prev.deepseekModel,
    qwenModel: values.qwen_model || prev.qwenModel,
    baiduModel: values.baidu_model || prev.baiduModel,
    relayModel: values.relay_model || prev.relayModel,
    openaiBaseUrl: values.openai_base_url ?? prev.openaiBaseUrl,
    anthropicBaseUrl: values.anthropic_base_url ?? prev.anthropicBaseUrl,
    zhipuaiBaseUrl: values.zhipuai_base_url ?? prev.zhipuaiBaseUrl,
    geminiBaseUrl: values.gemini_base_url ?? prev.geminiBaseUrl,
    deepseekBaseUrl: values.deepseek_base_url ?? prev.deepseekBaseUrl,
    qwenBaseUrl: values.qwen_base_url ?? prev.qwenBaseUrl,
    baiduBaseUrl: values.baidu_base_url ?? prev.baiduBaseUrl,
    relayBaseUrl: values.relay_base_url ?? prev.relayBaseUrl,
    openaiApiKey: "",
    anthropicApiKey: "",
    zhipuaiApiKey: "",
    geminiApiKey: "",
    deepseekApiKey: "",
    qwenApiKey: "",
    baiduApiKey: "",
    relayApiKey: "",
  }));
}

function getMainlineEngineLabel(result) {
  const engine = String(result?.delivery?.engine || "").toLowerCase();
  const mode = String(result?.delivery?.engine_mode || "").toLowerCase();
  if (engine === "langgraph") {
    return mode === "graph-native" ? "LangGraph 主线" : "LangGraph";
  }
  if (engine === "legacy") {
    return "历史兼容链路";
  }
  return "LangGraph 主线";
}

function summarizeCase(caseMemory = {}) {
  return {
    case_id: caseMemory.case_id,
    created_at: caseMemory.created_at,
    updated_at: caseMemory.updated_at,
    status: caseMemory.status || "new",
    status_label: caseMemory.status_label || "鏂板缓",
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

function upsertCaseSummary(items = [], nextItem) {
  if (!nextItem?.case_id) return items;
  const rest = items.filter((item) => item.case_id !== nextItem.case_id);
  return [nextItem, ...rest].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
}

function buildKnowledgeAssetFromResponse(data) {
  return {
    request_id: data.request_id,
    created_at: new Date().toISOString(),
    deleted_at: null,
    qdrant_deleted_at: null,
    doc_type: data.doc_type,
    total_files: data.total_files,
    total_chunks: data.total_chunks,
    output_path: data.output_path,
    metadata: data.metadata || {},
    qdrant_requested: Boolean(data.qdrant_requested),
    qdrant_upserted: Boolean(data.qdrant_upserted),
    qdrant_message: data.qdrant_message || "",
    local_artifacts_present: true,
    qdrant_cleanup_required: Boolean(data.qdrant_upserted),
    files: data.files || [],
  };
}

export default function useMasActions({
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
  setConnectionStatus,
  setConnectionMessage,
  setLlmStatus,
  setLlmMessage,
  setStrictClarification,
}) {
  const currentRunAbortRef = useRef(null);

  function isAbortError(err) {
    return err?.name === "AbortError" || /abort/i.test(String(err?.message || ""));
  }

  async function testConnection() {
    setConnectionStatus("checking");
    setConnectionMessage("正在检查 API 健康状态与组件接口...");
    try {
      const check = await validateConnection(settings);
      setConnectionStatus("ok");
      setConnectionMessage(`连接成功：service=${check.health?.service || "BuildCipher"}`);
    } catch (err) {
      setConnectionStatus("bad");
      setConnectionMessage(err.message || "连接失败");
    }
  }

  async function testLlmConnection() {
    setLlmStatus("checking");
    setLlmMessage(`正在验证 ${settings.provider} 连接...`);
    try {
      const data = await validateLlmConnection(settings.provider, "Return only OK.", settings);
      setLlmStatus(data.success ? "ok" : "bad");
      setLlmMessage(data.success ? `验证通过：${data.latency_ms}ms` : data.message || "验证失败");
    } catch (err) {
      setLlmStatus("bad");
      setLlmMessage(err.message || "LLM 验证失败");
    }
  }

  async function refreshEnvSettings() {
    try {
      const env = await getBackendEnvSettings(settings);
      setBackendEnv(env);
      applyBackendEnvToClientSettings(env, setSettings);
    } catch {
      setBackendEnv(null);
    }
  }

  async function syncEnv() {
    try {
      const env = await syncBackendEnvSettings(buildEnvSyncPayload(settings), settings);
      setBackendEnv(env);
      applyBackendEnvToClientSettings(env, setSettings);
      setNotice("模型与第三方 API 配置已保存到后端 .env，密钥已从前端表单中清空。");
    } catch (err) {
      setError(err.message || "同步后端 .env 失败");
    }
  }

  async function fetchComponents() {
    try {
      const data = await getComponents(300, settings);
      setComponents(data.items || []);
    } catch (err) {
      setError(err.message || "加载组件失败");
    }
  }

  async function fetchSkills() {
    try {
      const data = await getSkills(settings);
      setSkills(data.items || []);
    } catch (err) {
      setError(err.message || "加载技能失败");
    }
  }

  async function fetchCases() {
    try {
      const data = await getCases(20, settings);
      setCaseCatalog(data.items || []);
    } catch (err) {
      setError(err.message || "加载项目列表失败");
    }
  }

  async function fetchKnowledgeAssets() {
    try {
      const data = await getKnowledgeIngestions(20, settings);
      setKnowledgeCatalog(data.items || []);
    } catch (err) {
      setError(err.message || "加载知识资产列表失败");
    }
  }

  async function selectCase(caseId) {
    const normalized = String(caseId || "").trim();
    if (!normalized) {
      setCurrentCaseId("");
      setCurrentCaseDetails(null);
      setNotice("已切换为新项目，下一次执行会自动生成 case_id");
      return;
    }

    try {
      setCurrentCaseDetails(null);
      const data = await getCaseMemory(normalized, settings);
      setCurrentCaseId(normalized);
      setCurrentCaseDetails(data);
      setCaseCatalog((prev) => upsertCaseSummary(prev, summarizeCase(data)));
      setNotice(`已切换到项目：${normalized}`);
    } catch (err) {
      setError(err.message || "加载项目详情失败");
    }
  }

  async function removeCase(caseId) {
    const normalized = String(caseId || "").trim();
    if (!normalized) return;

    try {
      await deleteCaseMemory(normalized, settings);
      setCaseCatalog((prev) => prev.filter((item) => item.case_id !== normalized));
      if (currentCaseId === normalized) {
        setCurrentCaseId("");
        setCurrentCaseDetails(null);
      }
      setNotice(`已删除项目：${normalized}`);
    } catch (err) {
      setError(err.message || "删除项目失败");
    }
  }

  async function uploadKnowledgeFiles(payload) {
    try {
      setKnowledgeIngestionRunning(true);
      const data = await ingestKnowledgeDocuments(payload, settings);
      setKnowledgeIngestionResult(data);
      setKnowledgeCatalog((prev) => [
        buildKnowledgeAssetFromResponse(data),
        ...prev.filter((item) => item.request_id !== data.request_id),
      ]);
      setNotice(`知识导入完成：${data.total_files} 个文件，${data.total_chunks} 个知识块`);
      return data;
    } catch (err) {
      setError(err.message || "知识导入失败");
      return null;
    } finally {
      setKnowledgeIngestionRunning(false);
    }
  }

  async function removeKnowledgeArtifacts(requestId) {
    const normalized = String(requestId || "").trim();
    if (!normalized) return null;

    try {
      const data = await deleteKnowledgeIngestion(normalized, settings);
      setKnowledgeIngestionResult((prev) => (prev?.request_id === normalized ? null : prev));
      setKnowledgeCatalog((prev) =>
        prev.map((item) =>
          item.request_id === normalized
            ? {
                ...item,
                local_artifacts_present: false,
                deleted_at: new Date().toISOString(),
              }
            : item
        )
      );
      setNotice(`已删除知识导入产物：${normalized}`);
      return data;
    } catch (err) {
      setError(err.message || "删除知识导入产物失败");
      return null;
    }
  }

  async function removeKnowledgeQdrantArtifacts(requestId) {
    const normalized = String(requestId || "").trim();
    if (!normalized) return null;

    try {
      const data = await deleteKnowledgeIngestionQdrant(normalized, settings);
      setKnowledgeIngestionResult((prev) =>
        prev?.request_id === normalized
          ? {
              ...prev,
              qdrant_upserted: false,
              qdrant_message: data.message || prev.qdrant_message,
            }
          : prev
      );
      setKnowledgeCatalog((prev) =>
        prev.map((item) =>
          item.request_id === normalized
            ? {
                ...item,
                qdrant_upserted: false,
                qdrant_cleanup_required: false,
                qdrant_deleted_at: data.qdrant_deleted_at || new Date().toISOString(),
                qdrant_message: data.message || item.qdrant_message,
              }
            : item
        )
      );
      setNotice(`已删除 Qdrant 产物：${normalized}`);
      return data;
    } catch (err) {
      setError(err.message || "删除 Qdrant 产物失败");
      return null;
    }
  }

  async function reingestKnowledgeQdrantArtifacts(requestId) {
    const normalized = String(requestId || "").trim();
    if (!normalized) return null;

    try {
      const data = await reingestKnowledgeIngestionQdrant(normalized, settings);
      setKnowledgeIngestionResult((prev) =>
        prev?.request_id === normalized
          ? {
              ...prev,
              qdrant_requested: true,
              qdrant_upserted: data.upserted_points > 0,
              qdrant_message: data.message || prev.qdrant_message,
            }
          : prev
      );
      setKnowledgeCatalog((prev) =>
        prev.map((item) =>
          item.request_id === normalized
            ? {
                ...item,
                qdrant_requested: true,
                qdrant_upserted: data.upserted_points > 0,
                qdrant_cleanup_required: data.upserted_points > 0,
                qdrant_deleted_at: null,
                qdrant_message: data.message || item.qdrant_message,
              }
            : item
        )
      );
      setNotice(`已重新写入 Qdrant：${normalized}`);
      return data;
    } catch (err) {
      setError(err.message || "Qdrant 重写入失败");
      return null;
    }
  }

  async function recommendSkill() {
    const trimmed = String(requirement || "").trim();
    if (trimmed.length < 8) {
      setError("请先输入更完整的需求，再进行行业专家推荐。");
      return;
    }

    setRoutingSkill(true);
    setError("");
    try {
      const data = await routeSkill(
        {
          requirement: trimmed,
          max_candidates: 3,
        },
        settings
      );
      setSkillRoute(data);
      if (data?.recommended_skill?.id) {
        setSelectedSkillId(data.recommended_skill.id);
        setNotice(`已自动推荐行业专家：${data.recommended_skill.name}`);
      } else {
        setNotice("当前需求没有明显匹配的行业专家，仍可继续使用通用方案模式。");
      }
    } catch (err) {
      setError(err.message || "行业专家推荐失败");
    } finally {
      setRoutingSkill(false);
    }
  }

  function applySkill(skill) {
    if (!skill) return;
    setSelectedSkillId(skill.id);
    setSkillRoute((prev) => {
      if (prev?.recommended_skill?.id === skill.id) return prev;
      return {
        requirement,
        routing_version: "manual-selection",
        confidence: 1,
        recommended_skill: skill,
        candidates: [],
      };
    });

    if (skill.example_requirement) setRequirement(skill.example_requirement);
    if (skill.recommended_num_variants) setNumVariants(skill.recommended_num_variants);
    if (skill.recommended_max_audit_rounds) setMaxAuditRounds(skill.recommended_max_audit_rounds);
    if (typeof skill.generate_code_default === "boolean") setGenerateCode(skill.generate_code_default);
    if (typeof skill.strict_clarification_default === "boolean") {
      setStrictClarification(skill.strict_clarification_default);
    }

    setNotice(`行业专家已载入：${skill.name}`);
  }

  function persistRunResult(next) {
    if (!next) return;
    setResult(next);
    setHistory((prev) => [next, ...prev].slice(0, 20));
    if (next.case_id) setCurrentCaseId(next.case_id);
    if (next.case_memory) {
      setCurrentCaseDetails(next.case_memory);
      setCaseCatalog((prev) => upsertCaseSummary(prev, summarizeCase(next.case_memory)));
    }
  }

  async function runMas() {
    setError("");

    const runId = `run_${Date.now()}`;
    const runAbortController = new AbortController();
    const effectiveRequirement = buildRequirementWithClarifications(requirement, clarificationDetails);
    const blockingLabels = strictClarification
      ? listBlockingClarificationLabels(requirement, clarificationDetails)
      : [];

    if (blockingLabels.length) {
      setError(`已开启“关键约束补齐后再继续”，请先补充：${blockingLabels.join("、")}`);
      return;
    }

    setLoading(true);
    setResult(null);
    setStreamLog([]);
    setActiveRunId(runId);
    currentRunAbortRef.current = { runId, controller: runAbortController };

    try {
      if (selectedSkill) {
        const payload = {
          skill_id: selectedSkill.id,
          requirement: effectiveRequirement,
          case_id: currentCaseId || null,
          num_variants: Number(numVariants),
          generate_code: generateCode,
          llm_provider: settings.provider || null,
          max_audit_rounds: Number(maxAuditRounds),
          run_id: runId,
          strict_clarification: strictClarification,
          use_langgraph: true,
        };

        if (streaming) {
          await executeSkillStream(payload, settings, {
            signal: runAbortController.signal,
            onRun: (rid) => setActiveRunId(rid || runId),
            onProgress: (turn) => setStreamLog((prev) => [...prev, turn]),
            onFinal: (data) => {
              const next = data?.result || null;
              persistRunResult(next);
              setActiveRunId("");
              setNotice(`行业专家流程已完成交付：${selectedSkill.name} · ${getMainlineEngineLabel(next)}`);
            },
            onCancelled: (event) => {
              setError(event.message || "任务已取消");
              setActiveRunId("");
            },
            onError: (message) => {
              setError(message || "行业专家流式执行发生错误");
              setActiveRunId("");
            },
          });
        } else {
          const data = await executeSkill(payload, settings, { signal: runAbortController.signal });
          const next = data?.result || null;
          persistRunResult(next);
          setActiveRunId("");
          setNotice(`行业专家流程已完成交付：${selectedSkill.name} · ${getMainlineEngineLabel(next)}`);
        }
      } else {
        const payload = {
          requirement: effectiveRequirement,
          case_id: currentCaseId || null,
          num_variants: Number(numVariants),
          generate_code: generateCode,
          llm_provider: settings.provider || null,
          max_audit_rounds: Number(maxAuditRounds),
          run_id: runId,
          strict_clarification: strictClarification,
        };

        if (streaming) {
          await executeMasStream(
            payload,
            settings,
            {
              signal: runAbortController.signal,
              onRun: (rid) => setActiveRunId(rid || runId),
              onProgress: (turn) => setStreamLog((prev) => [...prev, turn]),
              onFinal: (data) => {
                persistRunResult(data);
                setActiveRunId("");
                setNotice(`MAS 已完成交付 · ${getMainlineEngineLabel(data)}`);
              },
              onCancelled: (event) => {
                setError(event.message || "任务已取消");
                setActiveRunId("");
              },
              onError: (message) => {
                setError(message || "流式执行发生错误");
                setActiveRunId("");
              },
            }
          );
        } else {
          const data = await executeMas(payload, settings, { signal: runAbortController.signal });
          persistRunResult(data);
          setActiveRunId("");
          setNotice(`MAS 已完成交付 · ${getMainlineEngineLabel(data)}`);
        }
      }

    } catch (err) {
      if (isAbortError(err)) {
        setNotice(`任务已停止：${runId}`);
      } else {
        setError(err.message || "MAS 执行失败");
      }
      setActiveRunId("");
    } finally {
      if (currentRunAbortRef.current?.runId === runId) {
        currentRunAbortRef.current = null;
      }
      setLoading(false);
    }
  }

  async function stopRun() {
    const runId = activeRunId || currentRunAbortRef.current?.runId;
    if (!runId) return;

    const current = currentRunAbortRef.current;
    if (current?.runId === runId && !current.controller.signal.aborted) {
      current.controller.abort();
    }
    setLoading(false);
    setActiveRunId("");
    setNotice(`已停止运行：${runId}`);

    try {
      await cancelMasRun(runId, settings);
    } catch (err) {
      if (!/404|not found/i.test(String(err?.message || ""))) {
        setError(err.message || "取消失败");
      }
    }
  }

  function resetAllSettings() {
    const defaults = getDefaultSettings();
    setSettings(defaults);
    saveClientSettings(defaults);
    setNotice("设置已恢复默认");
  }

  return {
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
  };
}
