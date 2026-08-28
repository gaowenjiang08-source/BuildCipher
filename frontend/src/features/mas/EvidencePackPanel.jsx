import { MetricCard, Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";
import ClosurePanelLead from "./ClosurePanelLead";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function normalizeItems(evidencePack) {
  return Array.isArray(evidencePack?.items) ? evidencePack.items.filter(Boolean) : [];
}

function classifyDocType(docType = "") {
  const normalized = String(docType || "").toLowerCase();
  const mapping = {
    standard: { label: "标准规范", tone: "ok" },
    policy: { label: "制度政策", tone: "warn" },
    component: { label: "组件能力", tone: "neutral" },
    template: { label: "交付模板", tone: "warn" },
    case: { label: "历史案例", tone: "bad" },
  };
  return mapping[normalized] || { label: docType || "未知类型", tone: "neutral" };
}

function summarizeMetrics(items = []) {
  return {
    total: items.length,
    clauseCount: items.filter((item) => item?.metadata?.clause_code).length,
    sourceTypeCount: new Set(items.map((item) => String(item?.doc_type || ""))).size,
    withPages: items.filter((item) => Number.isFinite(Number(item?.source_page))).length,
  };
}

function renderFilterLabel(filters = {}) {
  const parts = [];
  if (filters?.scenario) parts.push(`场景 ${filters.scenario}`);
  if (filters?.region) parts.push(`区域 ${filters.region}`);
  if (filters?.compliance) parts.push(`合规 ${filters.compliance}`);
  if (Array.isArray(filters?.doc_types) && filters.doc_types.length) parts.push(`类型 ${filters.doc_types.length}`);
  return parts;
}

function formatScore(score) {
  const value = Number(score);
  return Number.isFinite(value) ? value.toFixed(value >= 10 ? 1 : 2) : "--";
}

function formatSourceLine(item = {}) {
  const page = Number(item?.source_page);
  const sourcePath = String(item?.source_path || "").trim();
  const fileName = sourcePath ? sourcePath.split(/[\\/]/).pop() : "";
  if (fileName && Number.isFinite(page)) return `${fileName} · 第 ${page} 页`;
  if (fileName) return fileName;
  if (Number.isFinite(page)) return `第 ${page} 页`;
  return "未提供来源定位";
}

function formatParentPath(metadata = {}) {
  const path = Array.isArray(metadata?.section_path) ? metadata.section_path.filter(Boolean) : [];
  if (path.length <= 1) return "";
  return path.slice(0, -1).join(" > ");
}

export default function EvidencePackPanel({ evidencePack, selectedChunkId, onSelectEvidence, onJumpToSection }) {
  const items = normalizeItems(evidencePack);
  const metrics = summarizeMetrics(items);
  const filterLabels = renderFilterLabel(evidencePack?.applied_filters || {});

  return (
    <Panel
      title="规范依据与证据包"
      subtitle="查看命中的规范、模板、案例与组件能力。"
      className="xl:col-span-2"
      right={
        <div className="flex flex-wrap items-center gap-2">
          <TagPill tone={String(evidencePack?.backend || "").toLowerCase() === "qdrant" ? "ok" : "neutral"}>
            {`检索后端 ${evidencePack?.backend || "--"}`}
          </TagPill>
          <TagPill tone="neutral">{`模式 ${evidencePack?.retrieval_mode || "--"}`}</TagPill>
        </div>
      }
    >
      <ClosurePanelLead
        eyebrow="Closure Block"
        title="查看证据来源与作用"
        detail="查看证据如何支持方案。"
        statusLabel={items.length ? "证据包已形成" : "等待证据命中"}
        statusTone={items.length ? "ok" : "neutral"}
        nextLabel="下一步建议"
        nextDetail="继续查看证据联动解读。"
        actionLabel="跳到证据联动解读"
        onAction={() => onJumpToSection?.("reports-section-evidence-links")}
        accent="sky"
      />

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="命中证据" value={metrics.total} />
        <MetricCard label="可回引条款" value={metrics.clauseCount} />
        <MetricCard label="来源类型" value={metrics.sourceTypeCount} />
        <MetricCard label="带页码定位" value={metrics.withPages} />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {filterLabels.length === 0 ? <TagPill tone="neutral">未附加过滤条件</TagPill> : null}
        {filterLabels.map((item) => (
          <TagPill key={item} tone="neutral">
            {item}
          </TagPill>
        ))}
      </div>

      <div className="mt-4 rounded-[28px] border border-slate-200/90 bg-[linear-gradient(135deg,rgba(255,255,255,0.96),rgba(238,247,255,0.92))] p-4 shadow-[0_12px_40px_rgba(15,23,42,0.06)]">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">检索任务摘要</p>
          <TagPill tone="warn">中文优先</TagPill>
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {evidencePack?.query || "当前尚未形成 evidence pack，通常表示本轮还没有返回可用检索结果。"}
        </p>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        {items.length === 0 ? (
          <div className="rounded-[26px] border border-dashed border-slate-300 bg-white/80 px-4 py-8 text-center text-sm text-slate-500 xl:col-span-2">
            暂无结构化证据卡。请先执行一次流程。
          </div>
        ) : null}

        {items.slice(0, 8).map((item) => {
          const docType = classifyDocType(item?.doc_type);
          const clauseCode = String(item?.metadata?.clause_code || "").trim();
          const parentPath = formatParentPath(item?.metadata);
          const itemKey = item?.chunk_id || `${item?.doc_id || "evidence"}-${item?.section || item?.title || "card"}`;
          const selected = item?.chunk_id === selectedChunkId;
          return (
            <button
              type="button"
              key={itemKey}
              onClick={() => onSelectEvidence?.(item)}
              className={cn(
                "group w-full rounded-[28px] border border-white/80 bg-white/95 p-4 text-left shadow-[0_12px_32px_rgba(15,23,42,0.08)] transition duration-200 hover:-translate-y-0.5 hover:scale-[1.01] hover:shadow-[0_18px_42px_rgba(15,23,42,0.12)]",
                clauseCode ? "ring-1 ring-emerald-100" : "ring-1 ring-slate-100",
                selected ? "border-sky-300 bg-[linear-gradient(135deg,rgba(240,249,255,0.98),rgba(255,255,255,0.96))] ring-2 ring-sky-200" : ""
              )}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <TagPill tone={docType.tone}>{docType.label}</TagPill>
                    {clauseCode ? <TagPill tone="ok">{`条款 ${clauseCode}`}</TagPill> : null}
                    <TagPill tone="neutral">{`相关度 ${formatScore(item?.score)}`}</TagPill>
                    {selected ? <TagPill tone="ok">已联动</TagPill> : null}
                  </div>
                  <h3 className="mt-3 text-base font-black leading-6 text-slate-900">{item?.title || "--"}</h3>
                  <p className="mt-1 text-sm font-semibold text-slate-700">{item?.section || "未命中章节标题"}</p>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                <TagPill tone="neutral">{formatSourceLine(item)}</TagPill>
                {parentPath ? <TagPill tone="neutral">{`上级路径 ${parentPath}`}</TagPill> : null}
              </div>

              <p className="mt-3 rounded-[22px] bg-slate-50 px-3 py-3 text-sm leading-6 text-slate-700">
                {item?.snippet || "暂无摘要片段。"}
              </p>
            </button>
          );
        })}
      </div>
    </Panel>
  );
}
