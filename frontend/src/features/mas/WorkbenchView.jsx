import { useMemo, useState } from "react";
import { MetricCard, Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";
import {
  AlertCircleIcon,
  CheckBadgeIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  ClockIcon,
  CompassIcon,
  CpuIcon,
  InfoCircleIcon,
  SparkIcon,
} from "../../components/Icons";
import {
  analyzeClarificationCoverage,
  buildClarificationAppendix,
  buildRequirementWithClarifications,
  CLARIFICATION_SUGGESTIONS,
  hasClarificationDetails,
} from "./clarificationHelpers";
import { buildMarkdownExport } from "./exportHelpers";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function pickText(...candidates) {
  for (const candidate of candidates) {
    if (typeof candidate !== "string") continue;
    const value = candidate.trim();
    if (value) return value;
  }
  return "";
}

function summarizeText(value = "", maxChars = 180) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return "";
  return text.length > maxChars ? `${text.slice(0, maxChars)}...` : text;
}

function countLines(value = "") {
  return String(value || "").split(/\r?\n/).filter(Boolean).length;
}

function hasMeaningfulCodeArtifact(value = "", language = "") {
  const content = String(value || "").trim();
  if (!content) return false;

  if (language === "c") {
    const withoutComments = content.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
    return /\b[A-Za-z_]\w*(?:\s+|\s*\*\s*)+[A-Za-z_]\w*\s*\([^;{}]*\)\s*\{/.test(withoutComments);
  }
  if (language === "python") {
    return /^\s*(async\s+def|def|class)\s+[A-Za-z_]\w*/m.test(content);
  }
  if (language === "pseudocode") {
    const lines = content
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#") && !line.startsWith("//"));
    return lines.length >= 3 && /\b(function|procedure|algorithm|encrypt|decrypt|sign|verify)\b/i.test(lines.join("\n"));
  }
  return false;
}

function normalizeCodeOutputs({ finalScheme, result, deliveryPackage, codeArtifacts }) {
  const implementation =
    finalScheme?.implementation ||
    deliveryPackage?.final_scheme?.implementation ||
    result?.final_scheme?.implementation ||
    {};
  const artifacts = codeArtifacts || deliveryPackage?.code_artifacts || result?.delivery?.code_artifacts || {};
  const engineer = result?.engineer || deliveryPackage?.engineer || {};

  const cpp = pickText(
    artifacts.cpp,
    artifacts.cpp_code,
    artifacts.c,
    artifacts.c_code,
    implementation.cpp,
    implementation.cpp_code,
    implementation.c,
    implementation.c_code,
    engineer.corrected_c
  );
  const python = pickText(
    artifacts.python,
    artifacts.python_code,
    implementation.python,
    implementation.python_code,
    engineer.corrected_python
  );
  const pseudocode = pickText(
    artifacts.pseudocode,
    artifacts.pseudocode_text,
    implementation.pseudocode,
    implementation.pseudocode_text
  );
  const json = deliveryPackage ? JSON.stringify(deliveryPackage, null, 2) : "";
  const markdown = deliveryPackage ? buildMarkdownExport(deliveryPackage) : "";

  return {
    cpp,
    python,
    pseudocode,
    json,
    markdown,
    cppReady: hasMeaningfulCodeArtifact(cpp, "c"),
    pythonReady: hasMeaningfulCodeArtifact(python, "python"),
    pseudocodeReady: hasMeaningfulCodeArtifact(pseudocode, "pseudocode"),
  };
}

function QuickFillChips({ options = [], onPick }) {
  if (!options.length) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {options.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onPick(option)}
          className="cg-bouncy-chip min-h-[40px] rounded-full border border-[color:var(--cg-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[color:var(--cg-text-soft)] transition hover:border-[color:var(--cg-accent-border)] hover:text-[color:var(--cg-accent-strong)]"
        >
          {option}
        </button>
      ))}
    </div>
  );
}

function DisclosureSection({
  id,
  title,
  summary,
  icon: Icon,
  open,
  onToggle,
  tone = "neutral",
  children,
}) {
  const toneClass = {
    neutral: "border-[color:var(--cg-border)] bg-white",
    accent:
      "border-[color:var(--cg-accent-border)] bg-[linear-gradient(180deg,rgba(248,251,255,0.96)_0%,rgba(255,255,255,0.98)_100%)]",
    warn: "border-[color:var(--cg-warning-border)] bg-[color:var(--cg-warning-fog)]/70",
  };

  return (
    <section className={cn("rounded-[24px] border shadow-[var(--cg-shadow-soft)]", toneClass[tone] || toneClass.neutral)}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={id}
        className="flex min-h-[56px] w-full items-center justify-between gap-4 px-4 py-4 text-left"
      >
        <div className="flex min-w-0 items-start gap-3">
          <span className="cg-icon-badge mt-0.5">
            <Icon size={15} />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-black text-[color:var(--cg-text)]">{title}</p>
            <p className="mt-1 text-sm leading-6 text-[color:var(--cg-text-soft)]">{summary}</p>
          </div>
        </div>
        <ChevronDownIcon
          size={18}
          className={cn("shrink-0 text-[color:var(--cg-text-soft)] transition-transform", open && "rotate-180")}
        />
      </button>

      {open ? (
        <div id={id} className="border-t border-[color:var(--cg-border)] px-4 pb-4 pt-4">
          {children}
        </div>
      ) : null}
    </section>
  );
}

function RequirementInputPanel({
  requirement,
  setRequirement,
  generateCode,
  setGenerateCode,
  streaming,
  setStreaming,
  numVariants,
  setNumVariants,
  maxAuditRounds,
  setMaxAuditRounds,
  insertConstructionSkeleton,
  constructionInputDimensions,
  appendRequirementDimension,
  scenarioTemplates,
  applyTemplate,
  loading,
  activeRunId,
  runMas,
  stopRun,
}) {
  const [helpersOpen, setHelpersOpen] = useState(false);
  const canRun = Boolean(String(requirement || "").trim()) && !loading;
  const requirementLength = String(requirement || "").trim().length;
  const helperTextId = "workbench-requirement-helper";

  return (
    <Panel
      title="需求输入窗口"
      subtitle="输入项目需求。"
      right={<TagPill tone={activeRunId ? "warn" : "neutral"}>{activeRunId ? `运行中 ${activeRunId}` : "待启动"}</TagPill>}
      className="h-full"
      icon={CompassIcon}
    >
      <section id="workbench-requirement-panel" className="space-y-5">
        <div className="rounded-[28px] border border-[color:var(--cg-accent-border)] bg-[linear-gradient(180deg,rgba(243,248,255,0.98)_0%,rgba(255,255,255,0.98)_100%)] p-5 shadow-[var(--cg-shadow-soft)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <label htmlFor="workbench-requirement" className="text-sm font-black text-[color:var(--cg-text)]">
              需求描述
            </label>
            <button type="button" onClick={insertConstructionSkeleton} className="cg-button cg-button-ghost">
              插入工程需求骨架
            </button>
          </div>
          <p id={helperTextId} className="mt-3 max-w-[60ch] text-sm leading-7 text-[color:var(--cg-text-soft)]">
            一段清晰的需求通常至少包含四部分：业务场景、数据对象、安全目标、部署或合规边界。
          </p>
          <textarea
            id="workbench-requirement"
            value={requirement}
            onChange={(event) => setRequirement(event.target.value)}
            rows={14}
            aria-describedby={helperTextId}
            placeholder="例如：为 BIM/IFC 交付设计可信方案，说明工程资产、参与方、攻击目标、验收证据和部署边界。"
            className="mt-4 min-h-[320px] w-full rounded-[24px] border border-[color:var(--cg-accent-border)] bg-[linear-gradient(180deg,rgba(239,246,255,0.98)_0%,rgba(219,234,254,0.9)_100%)] px-5 py-5 text-sm leading-7 text-[color:var(--cg-text)] shadow-[inset_0_1px_2px_rgba(15,23,42,0.04)] outline-none transition placeholder:text-slate-400 focus:border-[color:var(--cg-accent-border)] focus:ring-4 focus:ring-[rgba(37,99,235,0.08)]"
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs leading-6 text-[color:var(--cg-text-soft)]">
              请填写核心需求。
            </p>
            <p className="text-xs font-semibold text-[color:var(--cg-text-soft)]">
              {requirementLength > 0 ? `${requirementLength} 字` : "尚未输入"}
            </p>
          </div>
        </div>

        <DisclosureSection
          id="workbench-input-helpers"
          title="辅助输入工具"
          summary="使用快捷补全与场景模板。"
          icon={SparkIcon}
          open={helpersOpen}
          onToggle={() => setHelpersOpen((value) => !value)}
          tone="accent"
        >
          <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
            <div className="rounded-[22px] border border-[color:var(--cg-border)] bg-white p-4">
              <p className="text-sm font-black text-[color:var(--cg-text)]">业务维度快捷补全</p>
              <p className="mt-1 text-sm leading-6 text-[color:var(--cg-text-soft)]">点击即可把常见约束补充到需求文本里。</p>
              <div className="mt-4 space-y-4">
                {(constructionInputDimensions || []).map((group) => (
                  <div key={group.title}>
                    <p className="text-xs font-black uppercase tracking-[0.16em] text-[color:var(--cg-text-soft)]">{group.title}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(group.options || []).map((item) => (
                        <button
                          key={`${group.prefix}-${item}`}
                          type="button"
                          onClick={() => appendRequirementDimension(group.prefix, item)}
                          className="cg-bouncy-chip min-h-[40px] rounded-full border border-[color:var(--cg-border)] bg-[color:var(--cg-surface-muted)] px-3 py-1.5 text-xs font-semibold text-[color:var(--cg-text)] transition hover:border-[color:var(--cg-accent-border)] hover:bg-[color:var(--cg-accent-fog)]"
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[22px] border border-[color:var(--cg-border)] bg-white p-4">
              <p className="text-sm font-black text-[color:var(--cg-text)]">场景模板</p>
              <p className="mt-1 text-sm leading-6 text-[color:var(--cg-text-soft)]">可选择模板快速生成需求。</p>
              <div className="mt-4 space-y-3">
                {(scenarioTemplates || []).slice(0, 4).map((item) => (
                  <button
                    key={item.title}
                    type="button"
                    onClick={() => applyTemplate(item)}
                    className="cg-bouncy-card w-full rounded-[20px] border border-[color:var(--cg-border)] bg-[linear-gradient(180deg,rgba(255,255,255,1)_0%,rgba(246,249,253,0.96)_100%)] px-4 py-4 text-left transition hover:-translate-y-0.5 hover:border-[color:var(--cg-border-strong)]"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-black text-[color:var(--cg-text)]">{item.title}</p>
                      <TagPill tone="neutral">可套用模板</TagPill>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(item.tags || []).slice(0, 3).map((tag) => (
                        <span
                          key={`${item.title}-${tag}`}
                          className="rounded-full border border-[color:var(--cg-border)] bg-white px-2.5 py-1 text-[11px] font-semibold text-[color:var(--cg-text-soft)]"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                    <p className="mt-3 text-xs leading-6 text-[color:var(--cg-text-soft)]">{item.requirement}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </DisclosureSection>

        <div className="rounded-[24px] border border-[color:var(--cg-border)] bg-white px-4 py-4 shadow-[var(--cg-shadow-soft)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-black text-[color:var(--cg-text)]">生成设置</p>
              <p className="mt-1 text-sm leading-6 text-[color:var(--cg-text-soft)]">控制方案数量、审计轮次和代码产物。</p>
            </div>
            <TagPill tone={generateCode ? "ok" : "neutral"}>{generateCode ? "生成代码" : "只生成方案"}</TagPill>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <label className="space-y-2">
              <span className="text-xs font-black uppercase tracking-[0.12em] text-[color:var(--cg-text-soft)]">方案数量</span>
              <input
                type="number"
                min="1"
                max="8"
                value={numVariants}
                onChange={(event) => setNumVariants?.(event.target.value)}
                className="h-11 w-full rounded-xl border border-[color:var(--cg-border)] bg-[color:var(--cg-surface-muted)] px-3 text-sm font-semibold outline-none focus:border-[color:var(--cg-accent-border)] focus:ring-4 focus:ring-[rgba(37,99,235,0.08)]"
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-black uppercase tracking-[0.12em] text-[color:var(--cg-text-soft)]">审计轮次</span>
              <input
                type="number"
                min="1"
                max="8"
                value={maxAuditRounds}
                onChange={(event) => setMaxAuditRounds?.(event.target.value)}
                className="h-11 w-full rounded-xl border border-[color:var(--cg-border)] bg-[color:var(--cg-surface-muted)] px-3 text-sm font-semibold outline-none focus:border-[color:var(--cg-accent-border)] focus:ring-4 focus:ring-[rgba(37,99,235,0.08)]"
              />
            </label>
            <label className="flex min-h-[44px] items-center justify-between gap-3 rounded-xl border border-[color:var(--cg-border)] bg-[color:var(--cg-surface-muted)] px-3 py-2 text-sm font-semibold text-[color:var(--cg-text)]">
              生成代码
              <input
                type="checkbox"
                checked={Boolean(generateCode)}
                onChange={(event) => setGenerateCode?.(event.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
              />
            </label>
            <label className="flex min-h-[44px] items-center justify-between gap-3 rounded-xl border border-[color:var(--cg-border)] bg-[color:var(--cg-surface-muted)] px-3 py-2 text-sm font-semibold text-[color:var(--cg-text)]">
              实时运行
              <input
                type="checkbox"
                checked={Boolean(streaming)}
                onChange={(event) => setStreaming?.(event.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
              />
            </label>
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-[24px] border border-[color:var(--cg-accent-border)] bg-[linear-gradient(180deg,rgba(239,246,255,0.96)_0%,rgba(219,234,254,0.92)_100%)] px-4 py-4 text-[color:var(--cg-text)] lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm font-black">{activeRunId ? "当前已有运行任务" : "确认无误后再启动主流程"}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            {activeRunId ? (
              <button type="button" onClick={stopRun} className="cg-button bg-white text-slate-950 hover:bg-slate-100">
                停止运行
              </button>
            ) : (
              <button
                type="button"
                onClick={runMas}
                disabled={!canRun}
                className="cg-button bg-sky-400 text-slate-950 hover:bg-sky-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "方案生成中..." : "生成方案"}
              </button>
            )}
          </div>
        </div>
      </section>
    </Panel>
  );
}

function ClarificationPanel({
  requirement,
  strictClarification,
  setStrictClarification,
  clarificationDetails,
  setClarificationDetails,
  clarifications,
  delivery,
}) {
  const [coverageOpen, setCoverageOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [questionOpen, setQuestionOpen] = useState(Boolean(clarifications?.length));

  const coverageItems = useMemo(
    () => analyzeClarificationCoverage(requirement, clarificationDetails),
    [requirement, clarificationDetails]
  );
  const missingRequiredCount = coverageItems.filter((item) => item.required && !item.complete).length;
  const appendixPreview = hasClarificationDetails(clarificationDetails)
    ? buildClarificationAppendix(clarificationDetails)
    : "";
  const mergedRequirementPreview = useMemo(
    () => buildRequirementWithClarifications(requirement, clarificationDetails),
    [requirement, clarificationDetails]
  );
  const gateBlocked = String(delivery?.status || "").toLowerCase() === "needs_clarification";

  const updateField = (key, value) => {
    setClarificationDetails((previous) => ({
      ...previous,
      [key]: value,
    }));
  };

  return (
    <Panel
      title="澄清信息补齐"
      subtitle="补充影响执行结果的关键边界。"
      right={
        <TagPill tone={missingRequiredCount > 0 || gateBlocked ? "warn" : "ok"}>
          {missingRequiredCount > 0 || gateBlocked ? "仍有阻塞项" : "基础门槛已满足"}
        </TagPill>
      }
      className="h-full"
      icon={CheckCircleIcon}
    >
      <section id="workbench-clarification-panel" className="space-y-5">
        <div className="rounded-[24px] border border-[color:var(--cg-border)] bg-white p-4 shadow-[var(--cg-shadow-soft)]">
          <label className="flex items-start gap-3 rounded-[18px] border border-[color:var(--cg-border)] bg-[color:var(--cg-surface-muted)] px-4 py-3">
            <input
              type="checkbox"
              checked={strictClarification}
              onChange={(event) => setStrictClarification(event.target.checked)}
              className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
            />
            <span>
              <span className="block text-sm font-semibold text-[color:var(--cg-text)]">开启严格澄清门槛</span>
              <span className="mt-1 block text-xs leading-6 text-[color:var(--cg-text-soft)]">
                缺少关键信息时暂停执行。
              </span>
            </span>
          </label>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <div className="rounded-[24px] border border-[color:var(--cg-border)] bg-white p-4 shadow-[var(--cg-shadow-soft)]">
            <label htmlFor="clarification-compliance" className="text-sm font-black text-[color:var(--cg-text)]">
              合规目标
            </label>
            <input
              id="clarification-compliance"
              value={clarificationDetails.complianceTarget}
              onChange={(event) => updateField("complianceTarget", event.target.value)}
              placeholder="例如 ISO 19650 参考 / ISO 27001 / 项目验收规则"
              className="mt-3 h-12 w-full rounded-[18px] border border-[color:var(--cg-border)] bg-[linear-gradient(180deg,rgba(248,251,255,0.98)_0%,rgba(255,255,255,0.98)_100%)] px-4 text-sm outline-none transition focus:border-[color:var(--cg-accent-border)] focus:ring-4 focus:ring-[rgba(37,99,235,0.08)]"
            />
            <QuickFillChips
              options={CLARIFICATION_SUGGESTIONS.complianceTargets}
              onPick={(value) => updateField("complianceTarget", value)}
            />
          </div>

          <div className="rounded-[24px] border border-[color:var(--cg-border)] bg-white p-4 shadow-[var(--cg-shadow-soft)]">
            <label htmlFor="clarification-memory" className="text-sm font-black text-[color:var(--cg-text)]">
              内存预算
            </label>
            <input
              id="clarification-memory"
              value={clarificationDetails.memoryBudget}
              onChange={(event) => updateField("memoryBudget", event.target.value)}
              placeholder="例如 256KB / 2MB / 256MB"
              className="mt-3 h-12 w-full rounded-[18px] border border-[color:var(--cg-border)] bg-[linear-gradient(180deg,rgba(248,251,255,0.98)_0%,rgba(255,255,255,0.98)_100%)] px-4 text-sm outline-none transition focus:border-[color:var(--cg-accent-border)] focus:ring-4 focus:ring-[rgba(37,99,235,0.08)]"
            />
            <QuickFillChips
              options={CLARIFICATION_SUGGESTIONS.memoryBudgets}
              onPick={(value) => updateField("memoryBudget", value)}
            />
          </div>

          <div className="rounded-[24px] border border-[color:var(--cg-border)] bg-white p-4 shadow-[var(--cg-shadow-soft)]">
            <label htmlFor="clarification-latency" className="text-sm font-black text-[color:var(--cg-text)]">
              延迟目标
            </label>
            <input
              id="clarification-latency"
              value={clarificationDetails.latencyTarget}
              onChange={(event) => updateField("latencyTarget", event.target.value)}
              placeholder="例如 20ms / 100ms / 1s"
              className="mt-3 h-12 w-full rounded-[18px] border border-[color:var(--cg-border)] bg-[linear-gradient(180deg,rgba(248,251,255,0.98)_0%,rgba(255,255,255,0.98)_100%)] px-4 text-sm outline-none transition focus:border-[color:var(--cg-accent-border)] focus:ring-4 focus:ring-[rgba(37,99,235,0.08)]"
            />
            <QuickFillChips
              options={CLARIFICATION_SUGGESTIONS.latencyTargets}
              onPick={(value) => updateField("latencyTarget", value)}
            />
          </div>

          <div className="rounded-[24px] border border-[color:var(--cg-border)] bg-white p-4 shadow-[var(--cg-shadow-soft)]">
            <label htmlFor="clarification-extra" className="text-sm font-black text-[color:var(--cg-text)]">
              其他补充要求
            </label>
            <textarea
              id="clarification-extra"
              value={clarificationDetails.extraRequirements}
              onChange={(event) => updateField("extraRequirements", event.target.value)}
              rows={5}
              placeholder="补充部署方式、访问控制、审计要求或任何必须写入方案的硬性约束。"
              className="mt-3 w-full rounded-[18px] border border-[color:var(--cg-accent-border)] bg-[linear-gradient(180deg,rgba(239,246,255,0.98)_0%,rgba(219,234,254,0.88)_100%)] px-4 py-3 text-sm leading-6 outline-none transition focus:border-[color:var(--cg-accent-border)] focus:ring-4 focus:ring-[rgba(37,99,235,0.08)]"
            />
          </div>
        </div>

        <DisclosureSection
          id="workbench-clarification-coverage"
          title="查看覆盖情况"
          summary="查看覆盖详情与待澄清问题。"
          icon={InfoCircleIcon}
          open={coverageOpen}
          onToggle={() => setCoverageOpen((value) => !value)}
        >
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              {coverageItems.map((item) => (
                <MetricCard
                  key={item.id}
                  label={item.label}
                  value={item.complete ? "已补齐" : "缺失"}
                  hint={item.hint}
                  tone={item.complete ? "success" : item.required ? "danger" : "neutral"}
                />
              ))}
            </div>

            {clarifications?.length ? (
              <DisclosureSection
                id="workbench-pending-questions"
                title="当前待澄清问题"
                summary={`共有 ${clarifications.length} 个待处理问题。`}
                icon={AlertCircleIcon}
                open={questionOpen}
                onToggle={() => setQuestionOpen((value) => !value)}
                tone="warn"
              >
                <div className="space-y-2">
                  {clarifications.slice(0, 6).map((item, index) => (
                    <div
                      key={`${index}-${item}`}
                      className="rounded-[18px] border border-white/70 bg-white/85 px-3 py-3 text-sm leading-6 text-slate-700"
                    >
                      {item}
                    </div>
                  ))}
                </div>
              </DisclosureSection>
            ) : null}
          </div>
        </DisclosureSection>

        <DisclosureSection
          id="workbench-clarification-preview"
          title="查看补齐预览"
          summary="查看补齐内容与提交预览。"
          icon={SparkIcon}
          open={previewOpen}
          onToggle={() => setPreviewOpen((value) => !value)}
          tone="accent"
        >
          <div className="grid gap-4 xl:grid-cols-2">
            <div className="rounded-[24px] border border-[color:var(--cg-border)] bg-[linear-gradient(180deg,rgba(248,251,255,0.96)_0%,rgba(255,255,255,0.98)_100%)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-black text-[color:var(--cg-text)]">补齐内容预览</p>
                <TagPill tone={appendixPreview ? "ok" : "neutral"}>{appendixPreview ? "将写入需求" : "尚未填写"}</TagPill>
              </div>
              <pre className="mt-3 max-h-[14rem] overflow-auto rounded-[18px] border border-[color:var(--cg-accent-border)] bg-[linear-gradient(180deg,rgba(239,246,255,0.96)_0%,rgba(219,234,254,0.92)_100%)] p-4 text-xs leading-6 text-slate-700">
                {appendixPreview || "补齐的信息会在这里汇总展示。"}
              </pre>
            </div>

            <div className="rounded-[24px] border border-[color:var(--cg-border)] bg-[linear-gradient(180deg,rgba(248,251,255,0.96)_0%,rgba(255,255,255,0.98)_100%)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-black text-[color:var(--cg-text)]">最终提交预览</p>
                <TagPill tone={mergedRequirementPreview ? "ok" : "neutral"}>{mergedRequirementPreview ? "已生成预览" : "等待输入"}</TagPill>
              </div>
              <pre className="mt-3 max-h-[14rem] overflow-auto rounded-[18px] border border-[color:var(--cg-border)] bg-white p-4 text-xs leading-6 text-slate-700">
                {mergedRequirementPreview || "先填写需求和澄清信息，这里会展示合并后的最终输入。"}
              </pre>
            </div>
          </div>
        </DisclosureSection>
      </section>
    </Panel>
  );
}

function CodeLivePanel({ streamLog, loading, activeRunId, codeOutputs, copyText }) {
  const events = useMemo(() => {
    return (Array.isArray(streamLog) ? streamLog : [])
      .filter((item) => {
        const phase = String(item?.phase || "").toLowerCase();
        const actor = String(item?.actor || "").toLowerCase();
        return (
          phase.includes("architect") ||
          phase.includes("engineer") ||
          phase.includes("code") ||
          phase.includes("compile") ||
          actor.includes("architect") ||
          actor.includes("engineer")
        );
      })
      .slice(-6)
      .reverse();
  }, [streamLog]);

  const liveCode = useMemo(() => {
    return (
      pickText(codeOutputs.cpp, codeOutputs.python, codeOutputs.pseudocode) ||
      events
        .map((item) => summarizeText(item?.message || item?.summary || item?.content, 120))
        .filter(Boolean)
        .join("\n\n")
    );
  }, [codeOutputs, events]);

  const liveLabel = codeOutputs.cpp
    ? "当前预览：C++"
    : codeOutputs.python
      ? "当前预览：Python"
      : codeOutputs.pseudocode
        ? "当前预览：伪代码"
        : activeRunId || loading
          ? "当前预览：生成日志"
          : "等待生成";

  return (
    <Panel
      title="实时代码生成"
      subtitle="实时查看代码生成结果。"
      right={<TagPill tone={activeRunId || loading ? "warn" : "neutral"}>{activeRunId || loading ? "实时更新中" : "等待运行"}</TagPill>}
      icon={CpuIcon}
    >
      <div className="grid gap-4 xl:grid-cols-[0.92fr_1.08fr]">
        <section className="rounded-[24px] border border-[color:var(--cg-border)] bg-white p-4 shadow-[var(--cg-shadow-soft)]" aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-black text-[color:var(--cg-text)]">最新生成动态</p>
            <TagPill tone="neutral">{events.length ? `${events.length} 条` : "暂无事件"}</TagPill>
          </div>
          <div className="mt-4 space-y-3">
            {events.length ? (
              events.map((item, index) => (
                <div
                  key={`${item?.phase || item?.actor || "event"}-${index}`}
                  className="rounded-[20px] border border-[color:var(--cg-border)] bg-[color:var(--cg-surface-muted)] px-4 py-3"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <TagPill tone="neutral">{item?.phase || item?.actor || "生成事件"}</TagPill>
                    {item?.status ? <TagPill tone="ok">{item.status}</TagPill> : null}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--cg-text-soft)]">
                    {summarizeText(item?.message || item?.summary || item?.content, 160) || "等待新的生成日志。"}
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-[20px] border border-dashed border-[color:var(--cg-border)] bg-[color:var(--cg-surface-muted)] px-4 py-5 text-sm leading-6 text-[color:var(--cg-text-soft)]">
                运行开始后，代码生成相关的 Architect / Engineer 事件会出现在这里。
              </div>
            )}
          </div>
        </section>

        <section className="rounded-[24px] border border-[color:var(--cg-border)] bg-[linear-gradient(180deg,rgba(248,251,255,0.96)_0%,rgba(255,255,255,0.98)_100%)] p-4 shadow-[var(--cg-shadow-soft)]">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-black text-[color:var(--cg-text)]">{liveLabel}</p>
              <p className="mt-1 text-sm leading-6 text-[color:var(--cg-text-soft)]">
                生成内容将实时刷新。
              </p>
            </div>
            {liveCode ? (
              <button
                type="button"
                onClick={() => copyText?.(liveCode, "当前代码预览已复制")}
                className="cg-button cg-button-secondary"
              >
                复制当前预览
              </button>
            ) : null}
          </div>

          <pre className="mt-4 max-h-[26rem] overflow-auto rounded-[20px] border border-slate-900/85 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
            {liveCode || "代码开始生成后，这里会显示最新片段或实时日志。"}
          </pre>
        </section>
      </div>
    </Panel>
  );
}

function CodeProgressPanel({ loading, activeRunId, finalScheme, result, codeOutputs }) {
  const stages = useMemo(() => {
    return [
      {
        id: "spec",
        label: "需求结构化",
        detail: "已形成需求输入",
        done: Boolean(String(result?.analyst?.structured_spec?.domain || "").trim() || finalScheme?.name || result?.analyst?.structured_spec),
      },
      {
        id: "scheme",
        label: "方案成形",
        detail: "已形成候选或最终方案",
        done: Boolean(finalScheme?.name || (result?.architect?.candidates || []).length),
      },
      {
        id: "pseudo",
        label: "伪代码",
        detail: "生成逻辑骨架",
        done: codeOutputs.pseudocodeReady,
      },
      {
        id: "python",
        label: "Python",
        detail: "生成可读实现",
        done: codeOutputs.pythonReady,
      },
      {
        id: "cpp",
        label: "C",
        detail: "生成 C11 实现",
        done: codeOutputs.cppReady,
      },
    ];
  }, [finalScheme, result, codeOutputs]);

  const completedCount = stages.filter((item) => item.done).length;
  const percent = Math.round((completedCount / stages.length) * 100);

  return (
    <Panel
      title="代码生成进度"
      subtitle="这里实时显示代码生成从方案成形到多语言产出的推进情况。"
      right={<TagPill tone={activeRunId || loading ? "warn" : percent === 100 ? "ok" : "neutral"}>{percent}%</TagPill>}
      icon={ClockIcon}
    >
      <div className="space-y-4">
        <div className="rounded-[24px] border border-[color:var(--cg-border)] bg-white p-4 shadow-[var(--cg-shadow-soft)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-black text-[color:var(--cg-text)]">
                {percent === 100 ? "代码生成已完成" : activeRunId || loading ? "代码生成正在推进" : "等待启动生成"}
              </p>
              <p className="mt-1 text-sm leading-6 text-[color:var(--cg-text-soft)]">
                当前已完成 {completedCount} / {stages.length} 个节点。
              </p>
            </div>
            <TagPill tone={percent === 100 ? "ok" : activeRunId || loading ? "warn" : "neutral"}>
              {percent === 100 ? "多格式已齐备" : activeRunId || loading ? "实时刷新" : "待运行"}
            </TagPill>
          </div>

          <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-200">
            <div
              className={cn(
                "h-full rounded-full bg-[linear-gradient(90deg,#2563eb_0%,#38bdf8_55%,#22c55e_100%)] transition-[width] duration-300",
                activeRunId || loading ? "animate-pulse" : ""
              )}
              style={{ width: `${Math.max(percent, activeRunId || loading ? 8 : 0)}%` }}
            />
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-5">
          {stages.map((item) => (
            <div
              key={item.id}
              className={cn(
                "rounded-[20px] border px-4 py-4 shadow-[var(--cg-shadow-soft)]",
                item.done
                  ? "border-[color:var(--cg-success-border)] bg-[color:var(--cg-success-fog)]"
                  : "border-[color:var(--cg-border)] bg-white"
              )}
            >
              <div className="flex items-center gap-2">
                {item.done ? <CheckCircleIcon size={16} /> : <ClockIcon size={16} />}
                <p className="text-sm font-black text-[color:var(--cg-text)]">{item.label}</p>
              </div>
              <p className="mt-2 text-xs leading-6 text-[color:var(--cg-text-soft)]">{item.detail}</p>
              <p className="mt-3 text-xs font-semibold text-[color:var(--cg-text-soft)]">{item.done ? "已完成" : "进行中 / 等待中"}</p>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

function CodeFormatsPanel({
  codeOutputs,
  deliveryPackage,
  codeTab,
  setCodeTab,
  copyText,
}) {
  const tabs = useMemo(() => {
    return [
      { id: "cpp", label: "C", language: "c", content: codeOutputs.cpp, ready: codeOutputs.cppReady },
      { id: "python", label: "Python", language: "python", content: codeOutputs.python, ready: codeOutputs.pythonReady },
      { id: "pseudocode", label: "伪代码", language: "text", content: codeOutputs.pseudocode, ready: codeOutputs.pseudocodeReady },
      { id: "json", label: "JSON", language: "json", content: codeOutputs.json, ready: Boolean(codeOutputs.json) },
      { id: "markdown", label: "Markdown", language: "markdown", content: codeOutputs.markdown, ready: Boolean(codeOutputs.markdown) },
    ];
  }, [codeOutputs]);

  const availableTabs = tabs.filter((item) => item.ready);
  const activeTab = tabs.find((item) => item.id === codeTab && item.ready) || availableTabs[0] || tabs[0];
  const codeGenerationComplete = Boolean(
    codeOutputs.cppReady &&
    codeOutputs.pythonReady &&
    codeOutputs.pseudocodeReady
  );

  return (
    <Panel
      title="多格式代码切换页"
      subtitle="查看 C、Python、伪代码、JSON 与 Markdown。"
      right={<TagPill tone={codeGenerationComplete ? "ok" : "neutral"}>{codeGenerationComplete ? "代码已完整生成" : "仍在等待完整生成"}</TagPill>}
      icon={CheckBadgeIcon}
    >
      <div className="rounded-[24px] border border-[color:var(--cg-border)] bg-white p-4 shadow-[var(--cg-shadow-soft)]">
        {availableTabs.length ? (
          <>
            <div
              className="flex flex-wrap gap-2"
              role="tablist"
              aria-label="代码格式切换"
            >
              {tabs.map((item) => {
                const active = item.id === activeTab.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    aria-controls={`workbench-code-panel-${item.id}`}
                    id={`workbench-code-tab-${item.id}`}
                    disabled={!item.ready}
                    onClick={() => item.ready && setCodeTab?.(item.id)}
                    className={cn(
                      "min-h-[44px] rounded-full border px-4 py-2 text-sm font-semibold transition",
                      active
                        ? "border-[color:var(--cg-accent-border)] bg-[color:var(--cg-accent-fog)] text-[color:var(--cg-accent-strong)]"
                        : item.ready
                          ? "border-[color:var(--cg-border)] bg-white text-[color:var(--cg-text-soft)] hover:border-[color:var(--cg-border-strong)] hover:text-[color:var(--cg-text)]"
                          : "cursor-not-allowed border-[color:var(--cg-border)] bg-slate-100 text-slate-400"
                    )}
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-[20px] border border-[color:var(--cg-border)] bg-[color:var(--cg-surface-muted)] px-4 py-3">
              <div>
                <p className="text-sm font-black text-[color:var(--cg-text)]">{activeTab.label}</p>
                <p className="mt-1 text-xs leading-6 text-[color:var(--cg-text-soft)]">
                  当前内容共 {countLines(activeTab.content)} 行。
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <TagPill tone={activeTab.ready ? "ok" : "neutral"}>{activeTab.ready ? "可查看" : "生成中"}</TagPill>
                <button
                  type="button"
                  onClick={() => copyText?.(activeTab.content, `${activeTab.label} 内容已复制`)}
                  className="cg-button cg-button-secondary"
                >
                  复制当前页
                </button>
              </div>
            </div>

            <div
              role="tabpanel"
              id={`workbench-code-panel-${activeTab.id}`}
              aria-labelledby={`workbench-code-tab-${activeTab.id}`}
              className="mt-4"
            >
              <pre className="max-h-[34rem] overflow-auto rounded-[20px] border border-slate-900/85 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
                {activeTab.content}
              </pre>
            </div>
          </>
        ) : (
          <div className="rounded-[20px] border border-dashed border-[color:var(--cg-border)] bg-[linear-gradient(180deg,rgba(248,251,255,0.96)_0%,rgba(255,255,255,0.98)_100%)] px-4 py-8 text-center">
            <p className="text-sm font-black text-[color:var(--cg-text)]">代码生成完成后，这里会开启多格式切换。</p>
            <p className="mt-2 text-sm leading-7 text-[color:var(--cg-text-soft)]">
              生成代码后可查看多格式结果。
            </p>
            {deliveryPackage ? (
              <p className="mt-3 text-xs font-semibold text-[color:var(--cg-text-soft)]">交付包已存在，等待主要代码工件补齐。</p>
            ) : null}
          </div>
        )}
      </div>
    </Panel>
  );
}

export default function WorkbenchView({
  loading,
  activeRunId,
  runMas,
  stopRun,
  requirement,
  setRequirement,
  generateCode,
  setGenerateCode,
  streaming,
  setStreaming,
  numVariants,
  setNumVariants,
  maxAuditRounds,
  setMaxAuditRounds,
  insertConstructionSkeleton,
  constructionInputDimensions,
  appendRequirementDimension,
  scenarioTemplates,
  applyTemplate,
  strictClarification,
  setStrictClarification,
  clarificationDetails,
  setClarificationDetails,
  clarifications,
  delivery,
  result,
  finalScheme,
  codeTab,
  setCodeTab,
  copyText,
  deliveryPackage,
  streamLog,
  codeArtifacts,
}) {
  const codeOutputs = useMemo(
    () => normalizeCodeOutputs({ finalScheme, result, deliveryPackage, codeArtifacts }),
    [finalScheme, result, deliveryPackage, codeArtifacts]
  );

  return (
    <div className="space-y-4">
      <div className={cn("grid grid-cols-1 gap-4 2xl:grid-cols-[1.08fr_0.92fr]")}>
        <RequirementInputPanel
          requirement={requirement}
          setRequirement={setRequirement}
          generateCode={generateCode}
          setGenerateCode={setGenerateCode}
          streaming={streaming}
          setStreaming={setStreaming}
          numVariants={numVariants}
          setNumVariants={setNumVariants}
          maxAuditRounds={maxAuditRounds}
          setMaxAuditRounds={setMaxAuditRounds}
          insertConstructionSkeleton={insertConstructionSkeleton}
          constructionInputDimensions={constructionInputDimensions}
          appendRequirementDimension={appendRequirementDimension}
          scenarioTemplates={scenarioTemplates}
          applyTemplate={applyTemplate}
          loading={loading}
          activeRunId={activeRunId}
          runMas={runMas}
          stopRun={stopRun}
        />

        <ClarificationPanel
          requirement={requirement}
          strictClarification={strictClarification}
          setStrictClarification={setStrictClarification}
          clarificationDetails={clarificationDetails}
          setClarificationDetails={setClarificationDetails}
          clarifications={clarifications}
          delivery={delivery}
        />
      </div>

      <CodeLivePanel
        streamLog={streamLog}
        loading={loading}
        activeRunId={activeRunId}
        codeOutputs={codeOutputs}
        copyText={copyText}
      />

      <CodeProgressPanel
        loading={loading}
        activeRunId={activeRunId}
        finalScheme={finalScheme}
        result={result}
        codeOutputs={codeOutputs}
      />

      <CodeFormatsPanel
        codeOutputs={codeOutputs}
        deliveryPackage={deliveryPackage}
        codeTab={codeTab}
        setCodeTab={setCodeTab}
        copyText={copyText}
      />
    </div>
  );
}
