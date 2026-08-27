import { useMemo, useState } from "react";
import { importConstructionIfc, runConstructionDemo } from "../../api/client";
import {
  ArrowRightIcon,
  BriefcaseIcon,
  CheckCircleIcon,
  DatabaseIcon,
  FlowIcon,
  LayersIcon,
  PulseIcon,
  ShieldIcon,
  SparkIcon,
} from "../../components/Icons";
import {
  CONSTRUCTION_ATTACKS,
  CONSTRUCTION_VALIDATION_CONTROLS,
  attackResultByType,
  buildConstructionState,
} from "./constructionBusinessState";
import { downloadTextFile, fileSafeName, timestampSlug } from "../mas/exportHelpers";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function unwrapAttackResult(result = {}) {
  return {
    blocked: Boolean(result?.blocked ?? result?.metrics?.blocked),
    detected: Boolean(result?.detected ?? result?.metrics?.detected),
    summary: result?.summary || "",
    beforeState: result?.before_state || result?.metrics?.before_state || {},
    afterState: result?.after_state || result?.metrics?.after_state || {},
    evidenceRefs: result?.evidence_refs || result?.metrics?.evidence_refs || [],
    artifactRefs: result?.artifact_refs || [],
  };
}

function buildConstructionExportPayload({ projectId, state, demo, ifcImport, delivery }) {
  const baseline = demo?.baseline_results || state.baseline;
  const hardened = demo?.results || state.regression;
  return {
    product: "BuildCipher",
    report_type: "construction_trust_validation",
    generated_at: new Date().toISOString(),
    project_id: projectId,
    status: demo?.status || state.statusLabel,
    imported_ifc: ifcImport || null,
    comparison: {
      verified: Boolean(demo?.comparison_verified),
      baseline_blocked_count: demo?.baseline_blocked_count ?? state.baselineBlocked,
      hardened_blocked_count: demo?.hardened_blocked_count ?? state.regressionBlocked,
      attack_count: demo?.attack_count || CONSTRUCTION_ATTACKS.length,
      evidence_ledger_valid: Boolean(demo?.evidence_ledger_valid || state.ledgerValid),
    },
    attacks: CONSTRUCTION_ATTACKS.map((attack) => ({
      ...attack,
      baseline: unwrapAttackResult(attackResultByType(baseline, attack.id)),
      hardened: unwrapAttackResult(attackResultByType(hardened, attack.id)),
    })),
    evidence_refs: demo?.evidence_refs || [],
    mas_delivery: delivery || null,
    capability_boundary:
      demo?.capability_boundary ||
      "localhost IFC 结构与可信交付验证；不等同于几何审查、商业 CDE、PKI、KMS 或 HSM。",
  };
}

function buildConstructionMarkdown(payload) {
  const rows = payload.attacks.map((item) =>
    `| ${item.label} | ${item.baseline.blocked ? "已阻断" : "可利用"} | ${item.hardened.blocked ? "已阻断" : "未阻断"} | ${item.control} |`
  );
  return [
    "# BuildCipher 建筑可信验证报告",
    "",
    `- 项目：${payload.project_id}`,
    `- 生成时间：${payload.generated_at}`,
    `- 对照验证：${payload.comparison.verified ? "通过" : "尚未形成完整对照"}`,
    `- 阻断结果：baseline ${payload.comparison.baseline_blocked_count}/${payload.comparison.attack_count}；hardened ${payload.comparison.hardened_blocked_count}/${payload.comparison.attack_count}`,
    "",
    "## 攻击与控制",
    "",
    "| 攻击 | Baseline | Hardened | 技术控制 |",
    "|---|---:|---:|---|",
    ...rows,
    "",
    "## 能力边界",
    "",
    payload.capability_boundary,
    "",
    "## 完整机器可读结果",
    "",
    "```json",
    JSON.stringify(payload, null, 2),
    "```",
  ].join("\n");
}

function escapeLatex(value = "") {
  return String(value)
    .replace(/\\/g, "\\textbackslash{}")
    .replace(/([&%$#_{}])/g, "\\$1")
    .replace(/~/g, "\\textasciitilde{}")
    .replace(/\^/g, "\\textasciicircum{}");
}

function buildConstructionLatex(payload) {
  const items = payload.attacks
    .map((item) => `\\item ${escapeLatex(item.label)}：baseline ${item.baseline.blocked ? "已阻断" : "可利用"}，hardened ${item.hardened.blocked ? "已阻断" : "未阻断"}；${escapeLatex(item.control)}。`)
    .join("\n");
  return `\\documentclass[UTF8]{ctexart}
\\usepackage[a4paper,margin=2.2cm]{geometry}
\\title{BuildCipher 建筑可信验证报告}
\\date{${escapeLatex(payload.generated_at)}}
\\begin{document}
\\maketitle
\\section*{项目}
${escapeLatex(payload.project_id)}
\\section*{对照结果}
baseline ${payload.comparison.baseline_blocked_count}/${payload.comparison.attack_count}；hardened ${payload.comparison.hardened_blocked_count}/${payload.comparison.attack_count}。
\\section*{攻击与控制}
\\begin{itemize}
${items}
\\end{itemize}
\\section*{能力边界}
${escapeLatex(payload.capability_boundary)}
\\end{document}
`;
}

function escapeHtml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function buildConstructionHtml(payload) {
  const rows = payload.attacks.map((item) => `
    <tr><td>${escapeHtml(item.label)}</td><td>${item.baseline.blocked ? "已阻断" : "可利用"}</td><td>${item.hardened.blocked ? "已阻断" : "未阻断"}</td><td>${escapeHtml(item.control)}</td></tr>`).join("");
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>BuildCipher 建筑可信验证报告</title><style>body{font-family:system-ui,sans-serif;margin:40px;color:#0f172a}main{max-width:1080px;margin:auto}h1{font-size:32px}table{width:100%;border-collapse:collapse;margin:24px 0}th,td{border:1px solid #cbd5e1;padding:12px;text-align:left}th{background:#eaf2ff}pre{overflow:auto;background:#07111f;color:#e2e8f0;padding:20px;border-radius:16px}.metric{display:inline-block;margin:8px 12px 8px 0;padding:12px 16px;background:#eff6ff;border-radius:12px}</style></head><body><main><h1>BuildCipher 建筑可信验证报告</h1><p>项目：${escapeHtml(payload.project_id)}</p><div class="metric">Baseline ${payload.comparison.baseline_blocked_count}/${payload.comparison.attack_count}</div><div class="metric">Hardened ${payload.comparison.hardened_blocked_count}/${payload.comparison.attack_count}</div><h2>攻击与控制</h2><table><thead><tr><th>攻击</th><th>Baseline</th><th>Hardened</th><th>技术控制</th></tr></thead><tbody>${rows}</tbody></table><h2>能力边界</h2><p>${escapeHtml(payload.capability_boundary)}</p><h2>机器可读结果</h2><pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre></main></body></html>`;
}

const VIEW_META = {
  overview: ["工程可信总览", "把模型、设备、参与方和验收证据放进同一条可信交付链。"],
  workbench: ["工程项目工作台", "定义工程资产、参与方、可信目标与交付边界。"],
  context: ["可信协同依据", "解释每项控制保护什么、由谁负责、产生哪些证据。"],
  validation: ["攻防验证实验室", "对同一 IFC 与 IoT 输入执行五类攻击，检查摘要、版本、角色、凭据和消息新鲜度控制。"],
  delivery: ["交付中心", "汇总可交付结论、证据引用和工程复核边界。"],
};

const PARTICIPANTS = [
  ["建设单位", "确认交付目标与最终接收范围"],
  ["设计单位", "签发模型、图纸和版本变更"],
  ["总承包方", "组织专业协同与施工交付"],
  ["专业分包", "仅接收本专业最小必要数据"],
  ["监理单位", "签批验收结论并固化证据"],
];

function Metric({ label, value, note, tone = "blue" }) {
  const tones = {
    blue: "border-blue-200 bg-blue-50/70 text-blue-800",
    green: "border-emerald-200 bg-emerald-50/70 text-emerald-800",
    amber: "border-amber-200 bg-amber-50/70 text-amber-800",
    slate: "border-slate-200 bg-white text-slate-800",
  };
  return (
    <div className={cn("rounded-2xl border p-4", tones[tone])}>
      <p className="text-xs font-bold uppercase tracking-[0.14em] opacity-70">{label}</p>
      <p className="mt-2 text-3xl font-black tracking-[-0.05em]">{value}</p>
      {note ? <p className="mt-2 text-xs leading-5 opacity-75">{note}</p> : null}
    </div>
  );
}

function Section({ title, description, children, id }) {
  return (
    <section id={id} className="rounded-[28px] border border-slate-200 bg-white/95 p-5 shadow-[0_20px_50px_rgba(15,23,42,0.06)] md:p-6">
      <div className="max-w-3xl">
        <h2 className="text-xl font-black tracking-[-0.035em] text-slate-950">{title}</h2>
        {description ? <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p> : null}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function AttackComparison({ state, demo }) {
  const hardenedResults = demo?.results || state.regression;
  const baselineResults = demo?.baseline_results || state.baseline;
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200">
      <div className="grid grid-cols-[1.4fr_0.7fr_0.7fr] gap-3 bg-slate-950 px-4 py-3 text-xs font-bold uppercase tracking-[0.12em] text-slate-300">
        <span>验证场景</span><span>补丁前</span><span>补丁后</span>
      </div>
      {CONSTRUCTION_ATTACKS.map((attack) => {
        const before = attackResultByType(baselineResults, attack.id);
        const after = attackResultByType(hardenedResults, attack.id) || demo?.results?.find((item) => item.attack_type === attack.id);
        const beforeBlocked = Boolean(before?.metrics?.blocked ?? before?.blocked);
        const afterBlocked = Boolean(after?.metrics?.blocked ?? after?.blocked);
        return (
          <div key={attack.id} className="grid grid-cols-[1.4fr_0.7fr_0.7fr] gap-3 border-t border-slate-200 px-4 py-4 text-sm first:border-t-0">
            <div className="min-w-0">
              <p className="font-bold text-slate-900">{attack.label}</p>
              <p className="mt-1 text-xs text-slate-500">{attack.asset} · {attack.control}</p>
            </div>
            <span className={cn("font-bold", before ? (beforeBlocked ? "text-emerald-700" : "text-rose-700") : "text-slate-400")}>
              {before ? (beforeBlocked ? "已阻断" : "可利用") : "待运行"}
            </span>
            <span className={cn("font-bold", after ? (afterBlocked ? "text-emerald-700" : "text-rose-700") : "text-slate-400")}>
              {after ? (afterBlocked ? "已阻断" : "未阻断") : "待回归"}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function primaryObservation(result = {}) {
  const normalized = unwrapAttackResult(result);
  return Object.values(normalized.beforeState).find(
    (value) => value && typeof value === "object" && !Array.isArray(value)
  ) || normalized.beforeState;
}

function TechnicalValidationPanel({ state, demo }) {
  const [selectedAttackId, setSelectedAttackId] = useState(CONSTRUCTION_ATTACKS[0].id);
  const selectedAttack = CONSTRUCTION_ATTACKS.find((item) => item.id === selectedAttackId);
  const control = CONSTRUCTION_VALIDATION_CONTROLS[selectedAttackId];
  const baselineResult = attackResultByType(demo?.baseline_results || state.baseline, selectedAttackId);
  const hardenedResult = attackResultByType(demo?.results || state.regression, selectedAttackId);
  const baseline = baselineResult ? unwrapAttackResult(baselineResult) : null;
  const hardened = hardenedResult ? unwrapAttackResult(hardenedResult) : null;
  const baselineObservation = baselineResult ? primaryObservation(baselineResult) : null;
  const hardenedObservation = hardenedResult ? primaryObservation(hardenedResult) : null;
  const evidenceRefs = Array.from(new Set([
    ...(baseline?.evidenceRefs || []),
    ...(baseline?.artifactRefs || []),
    ...(hardened?.evidenceRefs || []),
    ...(hardened?.artifactRefs || []),
  ]));

  return (
    <div className="mt-5 overflow-hidden rounded-[24px] border border-slate-200 bg-slate-950 text-white">
      <div className="border-b border-white/10 p-5">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-cyan-300">Deterministic control inspection</p>
        <h3 className="mt-2 text-xl font-black">技术控制与原始检查输出</h3>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-300">
          这里验证的不是 Agent 是否“说安全”，而是同一个攻击输入在控制关闭和开启时，具体布尔检查、摘要、版本、角色或消息新鲜度是否发生可复核变化。
        </p>
      </div>

      <div className="grid gap-2 border-b border-white/10 p-4 sm:grid-cols-2 xl:grid-cols-5" role="tablist" aria-label="选择攻击验证项">
        {CONSTRUCTION_ATTACKS.map((attack, index) => {
          const active = attack.id === selectedAttackId;
          const result = attackResultByType(demo?.results || state.regression, attack.id);
          return (
            <button
              key={attack.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setSelectedAttackId(attack.id)}
              className={cn(
                "rounded-xl border px-3 py-3 text-left text-xs transition",
                active
                  ? "border-cyan-300 bg-cyan-300/15 text-white"
                  : "border-white/10 bg-white/5 text-slate-300 hover:border-white/30 hover:bg-white/10"
              )}
            >
              <span className="font-mono text-cyan-300">0{index + 1}</span>
              <span className="mt-1 block font-bold">{attack.label}</span>
              <span className="mt-1 block text-[11px] text-slate-400">
                {result ? (unwrapAttackResult(result).blocked ? "回归已阻断" : "回归未阻断") : "等待运行"}
              </span>
            </button>
          );
        })}
      </div>

      <div className="grid gap-4 p-5 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-3">
          {[
            ["攻击构造", control.attackMethod],
            ["密码与控制", control.primitive],
            ["安全不变量", control.invariant],
            ["通过标准", control.acceptance],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-[11px] font-black uppercase tracking-[0.12em] text-cyan-300">{label}</p>
              <p className="mt-2 text-sm leading-6 text-slate-200">{value}</p>
            </div>
          ))}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-[11px] font-black uppercase tracking-[0.12em] text-cyan-300">控制配置键</p>
            <code className="mt-2 block break-all text-sm text-emerald-300">{control.controlKey}</code>
          </div>
        </div>

        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            {[
              ["Baseline / 控制关闭", baseline, baselineObservation],
              ["Hardened / 控制开启", hardened, hardenedObservation],
            ].map(([label, result, observation]) => (
              <div key={label} className="min-w-0 rounded-2xl border border-white/10 bg-[#081827] p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-black">{label}</p>
                  <span className={cn(
                    "rounded-full px-2.5 py-1 text-[11px] font-bold",
                    result
                      ? result.blocked
                        ? "bg-emerald-400/15 text-emerald-300"
                        : "bg-rose-400/15 text-rose-300"
                      : "bg-white/10 text-slate-400"
                  )}>
                    {result ? (result.blocked ? "攻击被阻断" : "攻击可通过") : "无运行结果"}
                  </span>
                </div>
                <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-all rounded-xl bg-black/30 p-3 text-[11px] leading-5 text-slate-300">
                  {observation ? JSON.stringify(observation, null, 2) : "运行前后对照后显示原始检查字段。"}
                </pre>
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm font-black">证据与工件引用</p>
            {evidenceRefs.length ? (
              <ul className="mt-3 space-y-2 text-xs text-slate-300">
                {evidenceRefs.map((ref) => <li key={ref} className="break-all rounded-lg bg-black/20 px-3 py-2 font-mono">{ref}</li>)}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-slate-400">运行后将显示 SHA-256 证据引用和本地 JSON 工件路径。</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ConstructionWorkspaceView({
  view,
  currentCaseSummary,
  delivery,
  attackLoop,
  settings,
  workbenchContent,
  exportFormats = [],
  onOpenProject,
  onOpenContext,
  onOpenValidation,
  onOpenDelivery,
}) {
  const state = useMemo(
    () => buildConstructionState({ attackLoop, delivery, currentCaseSummary }),
    [attackLoop, delivery, currentCaseSummary]
  );
  const [demo, setDemo] = useState(null);
  const [demoStatus, setDemoStatus] = useState("idle");
  const [demoError, setDemoError] = useState("");
  const [ifcFile, setIfcFile] = useState(null);
  const [ifcVersion, setIfcVersion] = useState("v3");
  const [ifcParentVersion, setIfcParentVersion] = useState("v2");
  const [ifcImport, setIfcImport] = useState(null);
  const [ifcImportStatus, setIfcImportStatus] = useState("idle");
  const [ifcImportError, setIfcImportError] = useState("");
  const [exportNotice, setExportNotice] = useState("");
  const [exportError, setExportError] = useState("");
  const [title, subtitle] = VIEW_META[view] || VIEW_META.overview;
  const projectId = state.caseId === "待创建工程项目" ? "buildtrust-demo-project" : state.caseId;
  const comparisonAttackCount = demo?.attack_count || state.regression.length || state.baseline.length || CONSTRUCTION_ATTACKS.length;
  const baselineBlockedCount = demo?.baseline_blocked_count ?? state.baselineBlocked;
  const hardenedBlockedCount = demo?.hardened_blocked_count ?? demo?.blocked_count ?? state.regressionBlocked;
  const visibleEvidenceCount = demo
    ? new Set(demo.evidence_refs || []).size
    : state.evidenceCount;

  async function executeIfcImport() {
    if (!ifcFile) {
      setIfcImportError("请先选择 .ifc 文件");
      return;
    }
    setIfcImportStatus("loading");
    setIfcImportError("");
    try {
      const result = await importConstructionIfc(
        {
          file: ifcFile,
          projectId,
          version: ifcVersion,
          parentVersion: ifcParentVersion,
        },
        settings
      );
      setIfcImport(result);
      setIfcImportStatus("done");
    } catch (error) {
      setIfcImportError(error?.message || "IFC 导入失败");
      setIfcImportStatus("error");
    }
  }

  async function executeDemo() {
    setDemoStatus("loading");
    setDemoError("");
    try {
      const result = await runConstructionDemo(
        { project_id: projectId, asset_ref: ifcImport?.asset_ref || null, mode: "compare" },
        settings
      );
      setDemo(result);
      setDemoStatus("done");
    } catch (error) {
      setDemoError(error?.message || "演示运行失败");
      setDemoStatus("error");
    }
  }

  function executeConstructionExport(format) {
    setExportNotice("");
    setExportError("");
    try {
      const payload = buildConstructionExportPayload({ projectId, state, demo, ifcImport, delivery });
      const baseName = fileSafeName(`buildcipher_${projectId}_construction_validation`);
      const filename = `${baseName}_${timestampSlug()}.${format.extension}`;
      let content = "";
      if (format.id === "json") content = JSON.stringify(payload, null, 2);
      else if (format.id === "md") content = buildConstructionMarkdown(payload);
      else if (format.id === "tex") content = buildConstructionLatex(payload);
      else if (format.id === "html") content = buildConstructionHtml(payload);
      else throw new Error(`不支持的导出格式：${format.id}`);
      downloadTextFile(filename, content, format.mime);
      setExportNotice(`${format.label}已下载`);
    } catch (error) {
      setExportError(error?.message || "导出失败");
    }
  }

  const header = (
    <div className="relative overflow-hidden rounded-[32px] border border-slate-800 bg-[linear-gradient(135deg,#07111f_0%,#10243b_55%,#12364a_100%)] p-6 text-white shadow-[0_30px_80px_rgba(15,23,42,0.18)] md:p-8">
      <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-cyan-400/10 blur-2xl" />
      <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-100">BuildCipher v1</span>
            <span className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">{state.targetLabel}</span>
          </div>
          <h1 className="mt-4 text-3xl font-black tracking-[-0.055em] md:text-5xl">{title}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300 md:text-base">{subtitle}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm backdrop-blur">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">当前工程</p>
          <p className="mt-1 max-w-sm break-all font-bold text-white">{state.caseId}</p>
          <p className="mt-1 text-xs text-cyan-200">{state.statusLabel}</p>
        </div>
      </div>
    </div>
  );

  if (view === "workbench") {
    return (
      <div className="space-y-5">
        {header}
        <Section
          id="ifc-import"
          title="导入 IFC 工程资产"
          description="文件先在 localhost 完成 STEP 结构、schema、实体数量和 SHA-256 检查，再作为五攻击前后对照的真实输入。"
        >
          <div className="grid gap-4 lg:grid-cols-[1.4fr_0.6fr_0.6fr_auto] lg:items-end">
            <label className="block text-sm font-bold text-slate-800">
              IFC 文件
              <input
                type="file"
                accept=".ifc,application/x-step"
                onChange={(event) => setIfcFile(event.target.files?.[0] || null)}
                className="mt-2 block w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-normal"
              />
            </label>
            <label className="block text-sm font-bold text-slate-800">
              当前版本
              <input value={ifcVersion} onChange={(event) => setIfcVersion(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 font-normal" />
            </label>
            <label className="block text-sm font-bold text-slate-800">
              父版本
              <input value={ifcParentVersion} onChange={(event) => setIfcParentVersion(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 font-normal" />
            </label>
            <button type="button" onClick={executeIfcImport} disabled={ifcImportStatus === "loading"} className="cg-button cg-button-primary disabled:cursor-wait disabled:opacity-60">
              <DatabaseIcon size={16} /> {ifcImportStatus === "loading" ? "正在检查" : "导入并验真"}
            </button>
          </div>
          {ifcImport ? (
            <div className="mt-4 grid gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 md:grid-cols-4">
              <div><p className="text-xs font-bold text-emerald-700">IFC schema</p><p className="mt-1 font-black">{ifcImport.inspection?.schema_identifiers?.join(", ") || "未知"}</p></div>
              <div><p className="text-xs font-bold text-emerald-700">实体数量</p><p className="mt-1 font-black">{ifcImport.inspection?.entity_count ?? 0}</p></div>
              <div><p className="text-xs font-bold text-emerald-700">版本</p><p className="mt-1 font-black">{ifcImport.asset?.version}</p></div>
              <div><p className="text-xs font-bold text-emerald-700">SHA-256</p><p className="mt-1 truncate font-mono text-xs">{ifcImport.inspection?.content_sha256}</p></div>
            </div>
          ) : <p className="mt-4 text-sm text-slate-500">未导入时，验证实验室仍可使用内置最小样例。</p>}
          {ifcImportError ? <p role="alert" className="mt-3 text-sm font-bold text-rose-700">{ifcImportError}</p> : null}
        </Section>
        {workbenchContent}
      </div>
    );
  }

  if (view === "overview") {
    return (
      <div className="space-y-5">
        {header}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Metric label="建筑攻击" value="5" note="模型、权限与设备数据" tone="blue" />
          <Metric label="补丁前阻断" value={`${baselineBlockedCount}/${comparisonAttackCount}`} note="未运行时显示预期基线" tone="amber" />
          <Metric label="补丁后阻断" value={`${hardenedBlockedCount}/${comparisonAttackCount}`} note="hardened 回归状态" tone="green" />
          <Metric label="证据引用" value={visibleEvidenceCount} note="文件工件与摘要引用" tone="slate" />
        </div>
        <Section id="journey" title="第一版场景主线" description="从工程资产开始，经过可信控制与攻击验证，最终形成可复核交付。">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {[
              [BriefcaseIcon, "定义工程项目", "录入模型、参与方与验收边界", onOpenProject],
              [FlowIcon, "建立可信协同", "明确签批、版本和最小权限", onOpenContext],
              [ShieldIcon, "执行五类验证", "比较 baseline 与 hardened", onOpenValidation],
              [SparkIcon, "进入交付中心", "汇总结论、证据和边界", onOpenDelivery],
            ].map(([Icon, itemTitle, note, action]) => (
              <button key={itemTitle} type="button" onClick={action} className="group rounded-2xl border border-slate-200 bg-slate-50/70 p-4 text-left transition hover:-translate-y-0.5 hover:border-blue-300 hover:bg-white hover:shadow-lg">
                <Icon size={20} className="text-blue-700" />
                <p className="mt-4 font-black text-slate-950">{itemTitle}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{note}</p>
                <span className="mt-4 inline-flex items-center gap-2 text-xs font-bold text-blue-700">进入 <ArrowRightIcon size={14} /></span>
              </button>
            ))}
          </div>
        </Section>
      </div>
    );
  }

  if (view === "context") {
    return (
      <div className="space-y-5">{header}
        <Section id="participants" title="参与方责任边界" description="第一版只表达角色与交付包级权限，不宣称构件或属性级授权。">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {PARTICIPANTS.map(([name, duty]) => <div key={name} className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><p className="font-black text-slate-900">{name}</p><p className="mt-2 text-xs leading-5 text-slate-600">{duty}</p></div>)}
          </div>
        </Section>
        <Section id="evidence" title="证据链结构" description="每一次验证结果同时保留业务状态、文件工件和摘要引用。">
          <div className="grid gap-3 lg:grid-cols-3">
            {[[LayersIcon,"工程资产","IFC、版本、角色、设备消息"],[ShieldIcon,"验证结论","检测、阻断、修复、回归"],[DatabaseIcon,"证据引用","JSON 工件、哈希链、SHA-256"]].map(([Icon,name,note])=><div key={name} className="rounded-2xl border border-slate-200 p-5"><Icon size={20} className="text-blue-700"/><p className="mt-3 font-black">{name}</p><p className="mt-2 text-sm text-slate-600">{note}</p></div>)}
          </div>
        </Section>
      </div>
    );
  }

  if (view === "validation") {
    return (
      <div className="space-y-5">{header}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Metric label="基线阻断" value={`${baselineBlockedCount}/${comparisonAttackCount}`} tone="amber" />
          <Metric label="补丁后阻断" value={`${hardenedBlockedCount}/${comparisonAttackCount}`} tone="green" />
          <Metric label="补丁状态" value={state.patchApplied ? "已应用" : "待应用"} tone="blue" />
          <Metric label="证据账本" value={state.ledgerValid || demo?.evidence_ledger_valid ? "有效" : "待验证"} tone="slate" />
        </div>
        <Section id="attacks" title="五类确定性攻击与控制验证" description="一次运行让 baseline 与 hardened 消费同一输入；下方可检查每项攻击构造、控制配置、原始判断字段和证据工件。">
          <AttackComparison state={state} demo={demo} />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={executeDemo} disabled={demoStatus === "loading"} className="cg-button cg-button-primary disabled:cursor-wait disabled:opacity-60">
              <PulseIcon size={16} /> {demoStatus === "loading" ? "正在执行" : "运行前后对照"}
            </button>
            {demoStatus === "done" ? <span className="text-sm font-bold text-emerald-700">完成：{demo.blocked_count}/{demo.attack_count} 已阻断</span> : null}
            {demoError ? <span role="alert" className="text-sm font-bold text-rose-700">{demoError}</span> : null}
          </div>
          <TechnicalValidationPanel state={state} demo={demo} />
        </Section>
      </div>
    );
  }

  return (
    <div className="space-y-5">{header}
      <Section id="conclusion" title="可信交付结论" description="交付内容包含可复核证据，同时明确演示能力与生产能力的边界。">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5"><CheckCircleIcon size={22} className="text-emerald-700"/><p className="mt-3 font-black text-emerald-950">五攻击控制</p><p className="mt-2 text-sm text-emerald-800">{hardenedBlockedCount}/{comparisonAttackCount} 已形成回归阻断证据</p></div>
          <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5"><DatabaseIcon size={22} className="text-blue-700"/><p className="mt-3 font-black text-blue-950">证据材料</p><p className="mt-2 text-sm text-blue-800">{visibleEvidenceCount} 个去重引用进入当前交付</p></div>
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5"><ShieldIcon size={22} className="text-amber-700"/><p className="mt-3 font-black text-amber-950">人工复核</p><p className="mt-2 text-sm text-amber-800">生产接入前仍需 BIM、密码与项目治理专家确认</p></div>
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          {exportFormats.map((format) => (
            <button
              key={format.id}
              type="button"
              onClick={() => executeConstructionExport(format)}
              className="cg-button cg-button-secondary"
            >
              {format.label}
            </button>
          ))}
        </div>
        <div className="mt-3 min-h-6" aria-live="polite">
          {exportNotice ? <p className="text-sm font-bold text-emerald-700">{exportNotice}</p> : null}
          {exportError ? <p role="alert" className="text-sm font-bold text-rose-700">{exportError}</p> : null}
        </div>
      </Section>
      <Section id="boundaries" title="第一版能力边界">
        <ul className="grid gap-3 text-sm leading-6 text-slate-700 md:grid-cols-2">
          {["IFC 只检查 STEP 结构、schema、实体计数与候选 GlobalId；尚未做几何、碰撞或规范校核。","身份认证使用 localhost HMAC provider，不等于生产 PKI、KMS、HSM 或人员证书。","证据账本是本地 JSON 哈希链，不是 WORM、外部可信时间或跨节点账本。","权限控制到角色和完整交付包级，尚未实现字段与构件级最小披露。"].map((item)=><li key={item} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">{item}</li>)}
        </ul>
      </Section>
    </div>
  );
}
