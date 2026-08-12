import { useMemo } from "react";
import { MetricCard, Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";
import {
  useAttackLoopStore,
  useRunDraftStore,
  useRunSessionStore,
  useStageConsoleStore,
} from "../../store";
import { displayOrDash } from "./masHelpers";

const STAGE_EXPLANATIONS = {
  analyst: {
    what: "把自然语言需求拆成数据对象、安全目标、约束条件和交付边界。",
    why: "先结构化需求，后面的证据检索、方案生成和攻击验证才不会各说各话。",
    result: "如果该阶段通过，系统会把需求摘要交给上下文构建与方案生成阶段。",
  },
  context_builder: {
    what: "检索企业知识、组件知识、规范依据和历史案例，形成证据包。",
    why: "让生成 agent 不只靠通用模型记忆，而是带着可引用证据工作。",
    result: "输出会进入方案生成和审计解释，影响候选方案排序与报告依据。",
  },
  architect: {
    what: "生成候选密码方案，并给出算法组合、性能取舍和适配理由。",
    why: "系统需要先形成可审计的方案对象，后续审计和攻击才有明确目标。",
    result: "候选方案会进入 Audit 和 Engineer，作为攻防闭环的基线版本。",
  },
  audit: {
    what: "从安全、合规、可实施性角度审查候选方案。",
    why: "先用审计 agent 过滤明显风险，可以减少后续沙盒攻击的无效轮次。",
    result: "审计发现会影响是否继续生成代码、是否补充证据和是否进入整改。",
  },
  engineer: {
    what: "把方案落成伪代码、Python 或 C++ 交付片段。",
    why: "攻击 agent 需要有可部署对象，企业交付也需要工程化输出。",
    result: "代码工件会被交给目标部署和攻击执行阶段。",
  },
  target_deployer: {
    what: "把加密数据服务部署成可探测的本地目标服务。",
    why: "攻击 agent 不能只审文本，需要面对一个受控的可执行目标。",
    result: "如果部署成功，系统会拿到健康检查、服务引用和遥测入口。",
  },
  attack_executor: {
    what: "攻击 agent 规划并执行探测任务，观察服务响应和异常信号。",
    why: "真实 LLM 决策需要能够选择攻击族、调整任务并读取执行反馈。",
    result: "攻击 trace、metrics 和发现会移交给漏洞评估与专家闸门。",
  },
  vulnerability_evaluation: {
    what: "评估攻击结果是否构成漏洞、风险等级和修补必要性。",
    why: "避免把普通波动误判成漏洞，也避免漏掉高置信风险。",
    result: "输出会决定继续攻击、进入 patch、回归测试或直接交付。",
  },
  patch_reflection: {
    what: "根据漏洞和专家判断生成修补计划，并沉淀反思结果。",
    why: "闭环价值不只是修 bug，还要把经验反馈给下一次生成与审计。",
    result: "反思可以回灌到提示词、检索策略、记忆卡和后续运行策略。",
  },
  delivery: {
    what: "汇总代码、伪代码、报告、证据和回放入口。",
    why: "企业交付需要可解释、可引用、可复盘，而不是只给一段模型回答。",
    result: "最终形成可下载、可答辩、可复查的交付包。",
  },
};

const STAGE_STATUS_LABELS = {
  pending: "待执行",
  running: "运行中",
  success: "已完成",
  failed: "失败",
  skipped: "跳过",
};

const ATTACK_ACTION_LABELS = {
  execute: "执行攻击",
  continue: "继续探测",
  replan: "重新规划",
  handoff: "移交评估",
  stop: "停止闭环",
};

const ATTACK_FAMILY_LABELS = {
  oracle_probe: "加密接口探测",
  misuse_case: "误用场景验证",
  regression_check: "回归验证",
};

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function toNumber(value, fallback = 0) {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

function summarizeText(value, max = 120) {
  const text = String(value || "").trim();
  if (!text) return "暂无摘要";
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function normalizeStatus(step, activeRunId) {
  if (step?.status) return step.status;
  if (step?.done) return "success";
  return activeRunId ? "pending" : "skipped";
}

function buildTelemetrySeries(attackLoop = {}) {
  const rounds = Array.isArray(attackLoop.rounds) ? attackLoop.rounds : [];
  const resultSeries = (attackLoop.attack_results || []).flatMap((item) => item?.metrics?.traffic_series || []);
  const roundSeries = rounds.flatMap((round) => round?.metrics?.traffic_series || round?.attack_result?.metrics?.traffic_series || []);
  const rawSeries = [...resultSeries, ...roundSeries].filter(Boolean);

  if (rawSeries.length) {
    return rawSeries.slice(-28).map((sample, index) => ({
      ts: sample.ts || sample.timestamp || index,
      latency: toNumber(sample.latency_ms ?? sample.latency ?? sample.response_ms, 0),
      cpu: toNumber(sample.cpu ?? sample.cpu_percent, 0),
      memory: toNumber(sample.memory ?? sample.memory_mb, 0),
      tx: toNumber(sample.tx_bytes ?? sample.tx ?? sample.bytes_sent, 0),
      rx: toNumber(sample.rx_bytes ?? sample.rx ?? sample.bytes_received, 0),
    }));
  }

  const probeCount = toNumber(attackLoop?.target_service?.probe_count || attackLoop?.probe_count, 0);
  return Array.from({ length: 12 }, (_, index) => ({
    ts: index,
    latency: 20 + index * 3 + (probeCount % 7),
    cpu: 18 + ((index * 9) % 31),
    memory: 220 + index * 6,
    tx: 1200 + index * 210,
    rx: 900 + index * 170,
  }));
}

function buildRoundCards(attackLoop = {}) {
  const rounds = Array.isArray(attackLoop.rounds) ? attackLoop.rounds : [];
  if (rounds.length) return rounds;

  const attackResults = Array.isArray(attackLoop.attack_results) ? attackLoop.attack_results : [];
  if (attackResults.length) {
    return attackResults.map((item, index) => ({
      ...item,
      round_id: item.round_id || `attack-${index + 1}`,
      round_label: item.round_label || `攻击轮次 ${index + 1}`,
      mode: item.mode || (index === 0 ? "baseline" : "regression"),
    }));
  }

  return [];
}

function buildFindingCards(attackLoop = {}) {
  const verdict = attackLoop.vulnerability_verdict || {};
  const findings = Array.isArray(verdict.findings) ? verdict.findings : [];
  if (findings.length) return findings;
  if (verdict.summary || verdict.risk_level || verdict.recommend_patch !== undefined) {
    return [
      {
        title: verdict.summary || "漏洞评估结论",
        severity: verdict.risk_level || verdict.risk || "unknown",
        detail: verdict.residual_risk || verdict.rationale || "当前评估结果已生成，但详细发现较少。",
      },
    ];
  }
  return [];
}

function ProgressBar({ value = 0, tone = "sky" }) {
  const width = Math.max(0, Math.min(100, Number(value) || 0));
  const toneClass = tone === "rose" ? "bg-rose-500" : tone === "amber" ? "bg-amber-500" : "bg-sky-500";
  return (
    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
      <div className={cn("h-full rounded-full", toneClass)} style={{ width: `${width}%` }} />
    </div>
  );
}

function RuntimeConsoleHero({ currentCaseSummary, activeRunId, latestEngineLabel, loading, sessionStatus }) {
  const caseLabel = currentCaseSummary?.case_id || "尚未锁定项目";
  const statusLabel = loading ? "运行中" : sessionStatus === "finished" ? "最近已完成" : "待命";

  return (
    <section className="overflow-hidden rounded-[32px] border border-slate-200 bg-[linear-gradient(135deg,#f8fbff_0%,#eef8f3_48%,#fff8e6_100%)] p-6 shadow-sm">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div className="max-w-4xl">
          <div className="flex flex-wrap gap-2">
            <TagPill tone="ok">运行控制台</TagPill>
            <TagPill tone={loading ? "warn" : "neutral"}>{statusLabel}</TagPill>
            <TagPill tone="neutral">{caseLabel}</TagPill>
          </div>
          <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-950 md:text-5xl">
            从任务发起到攻击闭环的一页式运行观察台
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-650 md:text-base">
            这里把需求输入、主流程阶段、攻击沙盒、漏洞评估、patch 决策和交付预览放在同一条主线上，方便外行理解“当前阶段在做什么、为什么这么做、结果意味着什么”。
          </p>
        </div>
        <div className="grid min-w-[18rem] grid-cols-1 gap-3 sm:grid-cols-3 xl:grid-cols-1">
          <MetricCard label="当前任务" value={activeRunId || "--"} hint="运行中任务编号" />
          <MetricCard label="执行引擎" value={latestEngineLabel || "LangGraph 主流程"} hint="不改变后端执行契约" />
          <MetricCard label="控制台状态" value={statusLabel} hint="来自前端运行会话桥接" />
        </div>
      </div>
    </section>
  );
}

function RunCreatorPanel({
  requirement,
  setRequirement,
  numVariants,
  setNumVariants,
  maxAuditRounds,
  setMaxAuditRounds,
  generateCode,
  setGenerateCode,
  streaming,
  setStreaming,
  strictClarification,
  setStrictClarification,
  runMas,
  stopRun,
  loading,
  activeRunId,
}) {
  const draft = useRunDraftStore();
  const syncConstraint = (key) => (event) => draft.setConstraint(key, event.target.value);

  return (
    <Panel
      title="A. 任务发起层"
      subtitle="先把自然语言需求、约束、运行模式和回归策略预结构化，再交给后端 MAS 主流程。"
      right={<TagPill tone="ok">RunCreator</TagPill>}
    >
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="rounded-[24px] border border-slate-200 bg-white/90 p-4">
          <label className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">自然语言需求</label>
          <textarea
            value={requirement}
            onChange={(event) => {
              setRequirement(event.target.value);
              draft.setRequirement(event.target.value);
            }}
            rows={8}
            className="mt-3 w-full rounded-[20px] border border-slate-200 bg-slate-50/70 px-4 py-3 text-sm leading-7 text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-4 focus:ring-sky-100"
            placeholder="描述数据对象、安全目标、合规要求、性能目标和交付格式..."
          />
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="text-sm font-semibold text-slate-700">
              候选方案数
              <input
                type="number"
                min="1"
                max="8"
                value={numVariants}
                onChange={(event) => setNumVariants(Number(event.target.value) || 1)}
                className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2"
              />
            </label>
            <label className="text-sm font-semibold text-slate-700">
              最大审计轮数
              <input
                type="number"
                min="1"
                max="8"
                value={maxAuditRounds}
                onChange={(event) => setMaxAuditRounds(Number(event.target.value) || 1)}
                className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2"
              />
            </label>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-[24px] border border-slate-200 bg-white/90 p-4">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">约束条件</p>
            <div className="mt-3 space-y-3">
              {[
                ["standards", "标准 / 合规"],
                ["performance", "性能约束"],
                ["language", "代码语言"],
                ["deliveryFormat", "交付格式"],
              ].map(([key, label]) => (
                <label key={key} className="block text-sm font-semibold text-slate-700">
                  {label}
                  <input
                    value={draft.constraints?.[key] || ""}
                    onChange={syncConstraint(key)}
                    className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-700"
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-white/90 p-4">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">运行策略</p>
            <div className="mt-3 grid grid-cols-1 gap-3">
              <label className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
                流式运行 stream
                <input
                  type="checkbox"
                  checked={streaming}
                  onChange={(event) => {
                    setStreaming(event.target.checked);
                    draft.setRunMode(event.target.checked ? "stream" : "execute");
                  }}
                />
              </label>
              <label className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
                生成代码工件
                <input type="checkbox" checked={generateCode} onChange={(event) => setGenerateCode(event.target.checked)} />
              </label>
              <label className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
                严格澄清门控
                <input
                  type="checkbox"
                  checked={strictClarification}
                  onChange={(event) => setStrictClarification(event.target.checked)}
                />
              </label>
              <label className="text-sm font-semibold text-slate-700">
                最大回归轮数
                <input
                  type="number"
                  min="0"
                  max="5"
                  value={draft.maxRegressionRounds}
                  onChange={(event) => draft.setMaxRegressionRounds(Number(event.target.value) || 0)}
                  className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2"
                />
              </label>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={runMas}
                disabled={loading}
                className="rounded-full border border-slate-900 bg-slate-900 px-5 py-2 text-sm font-black text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "正在运行" : "提交并进入 Live Console"}
              </button>
              {activeRunId ? (
                <button
                  type="button"
                  onClick={stopRun}
                  className="rounded-full border border-rose-300 bg-rose-50 px-5 py-2 text-sm font-black text-rose-700 transition hover:bg-rose-100"
                >
                  停止当前任务
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function StageRail({ stages, selectedStage, setSelectedStage, activeRunId }) {
  return (
    <div className="space-y-2">
      {stages.map((stage, index) => {
        const status = normalizeStatus(stage, activeRunId);
        const selected = selectedStage === stage.phase;
        return (
          <button
            key={`${stage.phase}-${index}`}
            type="button"
            onClick={() => setSelectedStage(stage.phase)}
            className={cn(
              "w-full rounded-2xl border px-4 py-3 text-left transition",
              selected ? "border-slate-900 bg-slate-900 text-white shadow-md" : "border-slate-200 bg-white/90 text-slate-700 hover:border-slate-300"
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-black">{index + 1}. {stage.label}</span>
              <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-bold", selected ? "bg-white/15" : "bg-slate-100")}>
                {STAGE_STATUS_LABELS[status] || status}
              </span>
            </div>
            <p className={cn("mt-1 text-xs leading-5", selected ? "text-slate-200" : "text-slate-500")}>{stage.owner}</p>
          </button>
        );
      })}
    </div>
  );
}

function StageInspector({ stage, streamLog = [], memoryHandoffs = [], contextProjections = {} }) {
  const explanation = STAGE_EXPLANATIONS[stage?.phase] || {
    what: "当前阶段来自后端 workflow trace，前端正在等待更多结构化摘要。",
    why: "统一阶段对象后，Live Console 可以稳定展示执行过程。",
    result: "该阶段结果会继续交给下游节点或进入交付收口。",
  };
  const relatedLogs = streamLog
    .filter((item) => String(item.phase || "").toLowerCase().includes(String(stage?.phase || "").toLowerCase()))
    .slice(-3);
  const relatedHandoffs = memoryHandoffs
    .filter((item) => [item.source_stage, item.target_stage, item.stage, item.from, item.to].some((value) => String(value || "").includes(stage?.phase || "")))
    .slice(0, 3);
  const projection = contextProjections?.[stage?.phase] || contextProjections?.[stage?.owner] || null;

  return (
    <div className="rounded-[24px] border border-slate-200 bg-white/90 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <TagPill tone="ok">当前阶段详情</TagPill>
        <TagPill tone="neutral">{stage?.owner || "System Module"}</TagPill>
      </div>
      <h3 className="mt-3 text-2xl font-black text-slate-950">{stage?.label || "请选择阶段"}</h3>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-sky-100 bg-sky-50/70 p-4">
          <p className="text-xs font-black text-sky-700">当前阶段在做什么</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{explanation.what}</p>
        </div>
        <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 p-4">
          <p className="text-xs font-black text-emerald-700">为什么这么做</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{explanation.why}</p>
        </div>
        <div className="rounded-2xl border border-amber-100 bg-amber-50/70 p-4">
          <p className="text-xs font-black text-amber-700">结果意味着什么</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{explanation.result}</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">输入摘要</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{summarizeText(projection?.input_summary || projection?.summary || stage?.input_summary)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">输出摘要</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{summarizeText(projection?.output_summary || stage?.summary || relatedLogs[0]?.message)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">交接情况</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {relatedHandoffs.length ? `命中 ${relatedHandoffs.length} 条结构化交接包，可继续在报告页深钻。` : "暂无本阶段交接包摘要，等待后端运行产出。"}
          </p>
        </div>
      </div>
    </div>
  );
}

function LiveConsolePanel({
  workflowProgress,
  streamLog,
  memoryHandoffs,
  contextProjections,
  activeRunId,
  selectedStage,
  setSelectedStage,
}) {
  const stages = workflowProgress?.length ? workflowProgress : [];
  const stage = stages.find((item) => item.phase === selectedStage) || stages[0] || null;

  return (
    <Panel
      title="B. 主流程实时观测"
      subtitle="阶段轨道、当前阶段详情和人话解释面板合并展示，让用户知道系统正在如何推进。"
      right={<TagPill tone="warn">Live Console</TagPill>}
    >
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.72fr_1.28fr]">
        <StageRail stages={stages} selectedStage={stage?.phase || selectedStage} setSelectedStage={setSelectedStage} activeRunId={activeRunId} />
        <StageInspector stage={stage} streamLog={streamLog} memoryHandoffs={memoryHandoffs} contextProjections={contextProjections} />
      </div>
    </Panel>
  );
}

function MiniTelemetryChart({ telemetry }) {
  const maxLatency = Math.max(...telemetry.map((item) => toNumber(item.latency, 0)), 1);
  const maxTraffic = Math.max(...telemetry.map((item) => toNumber(item.tx, 0) + toNumber(item.rx, 0)), 1);
  return (
    <div className="rounded-[24px] border border-slate-200 bg-white/90 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Telemetry</p>
          <h3 className="mt-1 text-lg font-black text-slate-950">沙盒态势时间窗</h3>
        </div>
        <TagPill tone="neutral">{telemetry.length} samples</TagPill>
      </div>
      <div className="mt-4 grid h-48 grid-cols-12 items-end gap-1 rounded-2xl border border-slate-100 bg-slate-50/80 p-3">
        {telemetry.slice(-12).map((item, index) => {
          const latencyHeight = Math.max(10, (toNumber(item.latency, 0) / maxLatency) * 100);
          const trafficHeight = Math.max(8, ((toNumber(item.tx, 0) + toNumber(item.rx, 0)) / maxTraffic) * 100);
          return (
            <div key={`${item.ts}-${index}`} className="flex h-full flex-col justify-end gap-1">
              <div className="rounded-t bg-sky-400/80" style={{ height: `${latencyHeight}%` }} title={`latency ${item.latency}`} />
              <div className="rounded-t bg-emerald-400/80" style={{ height: `${trafficHeight}%` }} title={`traffic ${item.tx + item.rx}`} />
            </div>
          );
        })}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard label="latency" value={`${Math.round(telemetry.at(-1)?.latency || 0)} ms`} hint="最近样本延迟" />
        <MetricCard label="cpu" value={`${Math.round(telemetry.at(-1)?.cpu || 0)}%`} hint="本地沙盒模拟值" />
        <MetricCard label="memory" value={`${Math.round(telemetry.at(-1)?.memory || 0)} MB`} hint="执行态势观察" />
        <MetricCard label="traffic" value={`${Math.round((telemetry.at(-1)?.tx || 0) + (telemetry.at(-1)?.rx || 0))} B`} hint="tx + rx" />
      </div>
    </div>
  );
}

function AttackLoopPanel({ attackLoop, sandboxDispatcher, replayScope, setReplayScope }) {
  const rounds = buildRoundCards(attackLoop);
  const telemetry = buildTelemetrySeries(attackLoop);
  const findings = buildFindingCards(attackLoop);
  const attackDecision = attackLoop.attack_decision || {};
  const targetService = attackLoop.target_service || {};
  const governanceItems = [
    ["runtime 白名单", sandboxDispatcher?.backend || sandboxDispatcher?.executor_kind || "local_process"],
    ["attack family", attackDecision.attack_family || attackLoop.attack_family || "--"],
    ["task 数量", (attackLoop.attack_specs || []).length || attackDecision.specs_count || rounds.length || "--"],
    ["probe / timeout", targetService.probe_count || attackLoop.probe_count || "--"],
  ];

  return (
    <Panel
      title="C. 攻击可视化层"
      subtitle="把攻击规划、治理检查、沙盒执行、漏洞评估和 patch 决策拆开看，避免被普通日志淹没。"
      right={<TagPill tone="bad">Attack Loop</TagPill>}
    >
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="space-y-4">
          <div className="rounded-[24px] border border-rose-100 bg-rose-50/60 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="bad">1. Attack Planning</TagPill>
              <TagPill tone="neutral">{ATTACK_ACTION_LABELS[attackDecision.action] || attackDecision.action || "等待规划"}</TagPill>
              <TagPill tone="neutral">
                {ATTACK_FAMILY_LABELS[attackDecision.attack_family] || attackDecision.attack_family || "attack family 待定"}
              </TagPill>
            </div>
            <p className="mt-3 text-sm leading-7 text-slate-700">
              {summarizeText(attackDecision.rationale || attackDecision.reason || "攻击 agent 会根据方案、目标服务和历史发现决定本轮是执行、继续、重规划、移交还是停止。", 180)}
            </p>
          </div>

          <div className="rounded-[24px] border border-amber-100 bg-amber-50/70 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="warn">2. Governance Check</TagPill>
              <TagPill tone={sandboxDispatcher?.failure_items?.length ? "bad" : "ok"}>
                {sandboxDispatcher?.failure_items?.length ? "存在阻断" : "治理通过或待运行"}
              </TagPill>
            </div>
            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {governanceItems.map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-white/80 bg-white/80 px-3 py-2">
                  <p className="text-[11px] font-black text-slate-500">{label}</p>
                  <p className="mt-1 text-sm font-bold text-slate-800">{displayOrDash(value)}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-white/90 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="ok">3. Sandbox Execution</TagPill>
              <TagPill tone={targetService.service_id ? "ok" : "warn"}>{targetService.service_id ? "目标服务已生成" : "等待目标服务"}</TagPill>
            </div>
            <div className="mt-3 space-y-3">
              <MetricCard label="target" value={targetService.service_name || targetService.service_id || "--"} hint="本地受控目标服务" />
              <MetricCard label="health" value={targetService.health_status || targetService.service_health_url || "--"} hint="健康检查与服务状态" />
              <MetricCard label="trace / metrics" value={attackLoop.trace_ref || attackLoop.metrics_ref || "--"} hint="执行产物引用" />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <MiniTelemetryChart telemetry={telemetry} />
          <div className="rounded-[24px] border border-slate-200 bg-white/90 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Attack Rounds</p>
                <h3 className="mt-1 text-lg font-black text-slate-950">回合制攻击观察</h3>
              </div>
              <TagPill tone="neutral">{rounds.length || 0} 轮</TagPill>
            </div>
            <div className="mt-3 space-y-3">
              {rounds.length ? (
                rounds.slice(0, 4).map((round, index) => {
                  const roundId = String(round.round_id || round.id || `round-${index + 1}`);
                  const active = replayScope?.targetServiceRef && replayScope.targetServiceRef === round.target_service_ref;
                  return (
                    <button
                      key={roundId}
                      type="button"
                      onClick={() =>
                        round.target_service_ref
                          ? setReplayScope?.((prev) => ({ ...(prev || {}), targetServiceRef: round.target_service_ref }))
                          : null
                      }
                      className={cn(
                        "w-full rounded-2xl border p-4 text-left transition",
                        active ? "border-emerald-300 bg-emerald-50 shadow-sm" : "border-slate-200 bg-slate-50/80 hover:border-slate-300"
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <TagPill tone={index === 0 ? "warn" : "ok"}>{round.mode || round.round_label || roundId}</TagPill>
                        {round.target_service_ref ? <TagPill tone="neutral">{round.target_service_ref}</TagPill> : null}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-700">{summarizeText(round.summary || round.verdict || round.status || "本轮攻击结果等待摘要。")}</p>
                    </button>
                  );
                })
              ) : (
                <p className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm leading-6 text-slate-500">
                  暂无攻击回合。运行 MAS 后，这里会展示 baseline / regression 等回合。
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-[24px] border border-slate-200 bg-white/90 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <TagPill tone="warn">5. Vulnerability Evaluation</TagPill>
                <TagPill tone={findings.length ? "bad" : "neutral"}>{findings.length ? `${findings.length} 条发现` : "暂无发现"}</TagPill>
              </div>
              <div className="mt-3 space-y-2">
                {findings.length ? (
                  findings.slice(0, 3).map((finding, index) => (
                    <div key={`${finding.title || "finding"}-${index}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <p className="text-sm font-black text-slate-900">{finding.title || finding.summary || "风险信号"}</p>
                      <p className="mt-1 text-xs leading-5 text-slate-600">{summarizeText(finding.detail || finding.description || finding.severity, 130)}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm leading-6 text-slate-600">等待漏洞评估 agent 输出风险信号、置信度、风险等级和残余风险。</p>
                )}
              </div>
            </div>
            <div className="rounded-[24px] border border-slate-200 bg-white/90 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <TagPill tone="ok">6. Expert Gate / Patch</TagPill>
                <TagPill tone="neutral">{attackLoop?.expert_gate?.route_target || attackLoop?.next_action || "等待决策"}</TagPill>
              </div>
              <p className="mt-3 text-sm leading-7 text-slate-700">
                {summarizeText(
                  attackLoop?.expert_gate?.rationale ||
                    attackLoop?.patch_spec?.summary ||
                    "专家闸门会在直接交付、补充攻击、进入 patch、回归攻击之间做路线选择。",
                  180
                )}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function EventsAndDeliveryPanel({ streamLog, deliveryPackage, codeArtifacts, replayDrilldown, result }) {
  const events = Array.isArray(streamLog) ? streamLog.slice(-8).reverse() : [];
  const codeReady = Boolean(codeArtifacts?.python || codeArtifacts?.cpp || result?.final_scheme?.implementation?.python);
  const reportReady = Boolean(deliveryPackage || result?.delivery);
  const replayReady = Boolean(replayDrilldown?.events?.length || replayDrilldown?.snapshots?.length);

  return (
    <Panel
      title="D. 日志、交付与复盘入口"
      subtitle="第一版先把 Events、Findings、Artifacts、Replay 状态放在控制台底部，后续再拆成独立 Delivery Workspace 和 Replay 页面。"
      right={<TagPill tone="neutral">Events / Delivery / Replay</TagPill>}
    >
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-[24px] border border-slate-200 bg-white/90 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-lg font-black text-slate-950">最近事件</h3>
            <TagPill tone="neutral">{events.length} events</TagPill>
          </div>
          <div className="mt-3 space-y-2">
            {events.length ? (
              events.map((event, index) => (
                <div key={`${event.phase || "event"}-${index}`} className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <TagPill tone="neutral">{event.phase || event.actor || "事件"}</TagPill>
                    {event.status ? <TagPill tone="ok">{event.status}</TagPill> : null}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{summarizeText(event.message || event.summary || event.content, 180)}</p>
                </div>
              ))
            ) : (
              <p className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm leading-6 text-slate-500">
                运行开始后，流式事件会在这里形成时间线摘要。
              </p>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-[24px] border border-slate-200 bg-white/90 p-4">
            <h3 className="text-lg font-black text-slate-950">交付工作区预览</h3>
            <div className="mt-4 space-y-3">
              <div>
                <div className="flex justify-between text-sm font-bold text-slate-700">
                  <span>代码工件</span>
                  <span>{codeReady ? "已准备" : "等待生成"}</span>
                </div>
                <ProgressBar value={codeReady ? 100 : 35} tone="sky" />
              </div>
              <div>
                <div className="flex justify-between text-sm font-bold text-slate-700">
                  <span>报告与证据</span>
                  <span>{reportReady ? "可查看" : "等待交付"}</span>
                </div>
                <ProgressBar value={reportReady ? 100 : 45} tone="amber" />
              </div>
              <div>
                <div className="flex justify-between text-sm font-bold text-slate-700">
                  <span>Replay 复盘</span>
                  <span>{replayReady ? "可回看" : "等待事件"}</span>
                </div>
                <ProgressBar value={replayReady ? 100 : 30} tone="rose" />
              </div>
            </div>
          </div>
          <div className="rounded-[24px] border border-slate-200 bg-slate-900 p-4 text-white">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-300">解释面板</p>
            <p className="mt-2 text-sm leading-7 text-slate-100">
              当前控制台是桥接实现：它复用现有 MAS 执行、报告、攻击闭环和 replay 数据，不改后端接口。下一步可以继续把 Delivery Workspace 和 Replay / 复盘拆成更完整的专页。
            </p>
          </div>
        </div>
      </div>
    </Panel>
  );
}

export default function RuntimeConsoleView({
  requirement,
  setRequirement,
  numVariants,
  setNumVariants,
  maxAuditRounds,
  setMaxAuditRounds,
  generateCode,
  setGenerateCode,
  streaming,
  setStreaming,
  strictClarification,
  setStrictClarification,
  loading,
  activeRunId,
  runMas,
  stopRun,
  currentCaseSummary,
  latestEngineLabel,
  workflowProgress,
  streamLog,
  memoryHandoffs,
  contextProjections,
  attackLoop,
  sandboxDispatcher,
  replayScope,
  setReplayScope,
  deliveryPackage,
  codeArtifacts,
  replayDrilldown,
  result,
}) {
  const session = useRunSessionStore();
  const stageConsole = useStageConsoleStore();
  const attackStore = useAttackLoopStore();

  const stageList = workflowProgress?.length ? workflowProgress : stageConsole.stages;
  const selectedStage = stageConsole.selectedStage || stageList[0]?.phase || "analyst";
  const normalizedAttackLoop = attackLoop || {};
  const roundCards = useMemo(() => buildRoundCards(normalizedAttackLoop), [normalizedAttackLoop]);
  const telemetry = useMemo(() => buildTelemetrySeries(normalizedAttackLoop), [normalizedAttackLoop]);

  return (
    <div className="space-y-6">
      <RuntimeConsoleHero
        currentCaseSummary={currentCaseSummary}
        activeRunId={activeRunId}
        latestEngineLabel={latestEngineLabel}
        loading={loading}
        sessionStatus={session.status}
      />

      <RunCreatorPanel
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
        runMas={runMas}
        stopRun={stopRun}
        loading={loading}
        activeRunId={activeRunId}
      />

      <LiveConsolePanel
        workflowProgress={stageList}
        streamLog={streamLog}
        memoryHandoffs={memoryHandoffs}
        contextProjections={contextProjections}
        activeRunId={activeRunId}
        selectedStage={selectedStage}
        setSelectedStage={stageConsole.setSelectedStage}
      />

      <AttackLoopPanel
        attackLoop={{
          ...normalizedAttackLoop,
          rounds: roundCards.length ? roundCards : attackStore.rounds,
          telemetry: telemetry.length ? telemetry : attackStore.telemetry,
        }}
        sandboxDispatcher={sandboxDispatcher}
        replayScope={replayScope}
        setReplayScope={setReplayScope}
      />

      <EventsAndDeliveryPanel
        streamLog={streamLog}
        deliveryPackage={deliveryPackage}
        codeArtifacts={codeArtifacts}
        replayDrilldown={replayDrilldown}
        result={result}
      />
    </div>
  );
}
