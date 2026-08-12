import { useEffect, useMemo, useState } from "react";
import { MetricCard, Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";

function buildMetadata({ region, industry, scenario, tags }) {
  const normalizedTags = String(tags || "")
    .split(/[,\uFF0C\u3001]/)
    .map((item) => item.trim())
    .filter(Boolean);

  return {
    region: String(region || "").trim() || undefined,
    industry: String(industry || "").trim() || undefined,
    scenario: String(scenario || "").trim() || undefined,
    tags: normalizedTags,
  };
}

function formatTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("zh-CN", { hour12: false });
}

function countMetadataFields(metadata = {}) {
  return Object.entries(metadata).filter(([, value]) => {
    if (Array.isArray(value)) return value.length > 0;
    return value !== undefined && value !== null && String(value).trim() !== "";
  }).length;
}

function countPreviewBlocks(item = {}) {
  return (item.files || []).reduce((sum, file) => sum + (file.previews || []).length, 0);
}

function buildGovernanceTips(item = {}) {
  const tips = [];

  if (item.local_artifacts_present) {
    tips.push("本地仍保留原始上传文件与 JSONL，演示结束前建议确认是否需要清理。");
  } else {
    tips.push("本地上传文件与 JSONL 已删除，当前这条记录主要用于保留导入轨迹与治理状态。");
  }

  if (item.qdrant_deleted_at) {
    tips.push("这批知识的 Qdrant 副本已经完成治理，当前记录可继续保留为审计轨迹与导入档案。");
  } else if (item.qdrant_upserted && item.qdrant_cleanup_required) {
    tips.push("这批知识块已经写入 Qdrant，若要彻底清理演示痕迹，还需要补做向量副本治理。");
  } else if (item.qdrant_requested) {
    tips.push("本次导入尝试过 Qdrant 写入，但当前结果并未形成需要额外治理的向量副本。");
  } else {
    tips.push("这批资产目前只落在本地 JSONL，可直接用于质检、人工复核或后续正式入库。");
  }

  if ((item.files || []).length > 1) {
    tips.push("当前记录包含多份源文件，适合在答辩时解释这批知识是如何按一次导入任务统一治理的。");
  }

  return tips;
}

function getQdrantSummary(item = {}) {
  if (item.qdrant_deleted_at) return "Qdrant 副本已清理";
  if (item.qdrant_upserted) return "已写入 Qdrant";
  if (item.qdrant_requested) return "已尝试写入 Qdrant";
  return "仅本地 JSONL";
}

function getDocTypeLabel(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (normalized === "standard") return "标准规范";
  if (normalized === "policy") return "制度文件";
  if (normalized === "case") return "历史案例";
  if (normalized === "template") return "交付模板";
  return value || "--";
}

function getMetadataLabel(key) {
  const normalized = String(key || "").trim();
  const labelMap = {
    region: "区域",
    industry: "行业",
    scenario: "场景",
    tags: "标签",
  };
  return labelMap[normalized] || key;
}

function buildOpsInlineMetricTone(value, mode = "count") {
  if (mode === "binary") {
    return value ? "ok" : "neutral";
  }
  return Number(value || 0) > 0 ? "ok" : "neutral";
}

function OpsInlineMetric({ label, value, tone = "neutral" }) {
  const toneMap = {
    neutral: "border-slate-200 bg-white text-slate-900",
    ok: "border-emerald-200 bg-emerald-50 text-emerald-900",
    warn: "border-amber-200 bg-amber-50 text-amber-900",
    info: "border-sky-200 bg-sky-50 text-sky-900",
  };

  return (
    <div className={`rounded-[1.2rem] border px-4 py-3 ${toneMap[tone] || toneMap.neutral}`}>
      <p className="text-[11px] font-bold uppercase tracking-[0.16em] opacity-70">{label}</p>
      <p className="mt-2 text-lg font-black">{value}</p>
    </div>
  );
}

function SensitiveNotice({ title, body, tone = "amber" }) {
  const toneMap = {
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    rose: "border-rose-200 bg-rose-50 text-rose-900",
    slate: "border-slate-200 bg-slate-50 text-slate-800",
  };

  return (
    <div className={`rounded-2xl border px-4 py-3 ${toneMap[tone] || toneMap.amber}`}>
      <p className="text-sm font-black">{title}</p>
      <p className="mt-1 text-xs leading-5 opacity-90">{body}</p>
    </div>
  );
}

function AssetStatusPills({ item }) {
  return (
    <div className="flex flex-wrap gap-2">
      <TagPill tone={item.local_artifacts_present ? "ok" : "warn"}>
        {item.local_artifacts_present ? "本地文件仍在" : "本地文件已删除"}
      </TagPill>
      <TagPill tone={item.qdrant_deleted_at ? "neutral" : item.qdrant_upserted ? "ok" : "neutral"}>
        {item.qdrant_deleted_at ? "Qdrant 副本已清理" : item.qdrant_upserted ? "已写入 Qdrant" : "未写入 Qdrant"}
      </TagPill>
      {item.qdrant_cleanup_required ? <TagPill tone="warn">Qdrant 仍需单独治理</TagPill> : null}
    </div>
  );
}

function AssetListCard({ item, selected, onSelect, onDelete, reingestKnowledgeQdrantArtifacts }) {
  const previewCount = countPreviewBlocks(item);

  return (
    <div
      className={`rounded-2xl border p-4 transition ${
        selected
          ? "border-slate-900 bg-slate-900 text-white shadow-lg shadow-slate-900/10"
          : "border-slate-200 bg-slate-50/80 text-slate-900"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-black">{`导入编号 ${item.request_id}`}</p>
          <p className={`mt-1 text-xs ${selected ? "text-slate-200" : "text-slate-500"}`}>
            {item.doc_type || "--"} · {formatTime(item.created_at)}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onSelect?.(item.request_id)}
            className={`rounded-xl px-3 py-2 text-xs font-bold ${
              selected ? "bg-white text-slate-900" : "border border-slate-300 bg-white text-slate-700"
            }`}
          >
            {selected ? "已选中" : "查看详情"}
          </button>
          <button
            type="button"
            disabled={!item.local_artifacts_present}
            onClick={() => onDelete?.(item.request_id)}
            className={`rounded-xl px-3 py-2 text-xs font-bold ${
              selected
                ? "border border-rose-200 bg-rose-100 text-rose-700 disabled:bg-slate-300 disabled:text-slate-500"
                : "border border-rose-300 bg-rose-50 text-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
            }`}
          >
            {item.local_artifacts_present ? "删除本地产物" : "本地产物已删除"}
          </button>
          <button
            type="button"
            disabled={!item.local_artifacts_present}
            onClick={() => reingestKnowledgeQdrantArtifacts?.(item.request_id)}
            className="rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {item.local_artifacts_present ? "重新写入 Qdrant" : "仅剩 JSONL"}
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <TagPill tone="neutral">{`文件 ${item.total_files}`}</TagPill>
        <TagPill tone="neutral">{`知识块 ${item.total_chunks}`}</TagPill>
        <TagPill tone="neutral">{`预览 ${previewCount}`}</TagPill>
      </div>

      <div className={`mt-3 text-xs leading-5 ${selected ? "text-slate-200" : "text-slate-600"}`}>
        <p>{`本地输出：${item.output_path || "--"}`}</p>
        <p>{`Qdrant：${item.qdrant_message || getQdrantSummary(item)}`}</p>
      </div>
    </div>
  );
}

function AssetDetailPanel({
  item,
  copyText,
  removeKnowledgeArtifacts,
  removeKnowledgeQdrantArtifacts,
  reingestKnowledgeQdrantArtifacts,
}) {
  const metadataEntries = Object.entries(item.metadata || {}).filter(([, value]) => {
    if (Array.isArray(value)) return value.length > 0;
    return value !== undefined && value !== null && String(value).trim() !== "";
  });
  const governanceTips = buildGovernanceTips(item);

  return (
    <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">资产详情</p>
          <h3 className="mt-1 text-xl font-black text-slate-900">{`导入编号 ${item.request_id}`}</h3>
          <p className="mt-2 text-sm text-slate-600">
            这不是一条孤立的上传记录，而是一份可解释的知识资产档案。你可以直接回答它包含了什么、来自哪里、是否仍有本地副本，以及是否已经进入
            Qdrant。
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => copyText?.(item.request_id, "导入编号已复制")}
            className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-700"
          >
            复制导入编号
          </button>
          <button
            type="button"
            onClick={() => copyText?.(item.output_path || "", "输出路径已复制")}
            className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-700"
          >
            复制输出路径
          </button>
          <button
            type="button"
            disabled={!item.local_artifacts_present}
            onClick={() => removeKnowledgeArtifacts?.(item.request_id)}
            className="rounded-xl border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-bold text-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {item.local_artifacts_present ? "删除本地导入产物" : "本地导入产物已删除"}
          </button>
          <button
            type="button"
            disabled={!item.qdrant_cleanup_required}
            onClick={() => removeKnowledgeQdrantArtifacts?.(item.request_id)}
            className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {item.qdrant_cleanup_required ? "删除向量副本" : "向量副本已清理"}
          </button>
          <button
            type="button"
            disabled={!item.local_artifacts_present}
            onClick={() => reingestKnowledgeQdrantArtifacts?.(item.request_id)}
            className="rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {item.local_artifacts_present ? "重写 Qdrant" : "仅剩 JSONL"}
          </button>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="文件数" value={item.total_files} />
        <MetricCard label="知识块数" value={item.total_chunks} />
        <MetricCard label="元数据项" value={countMetadataFields(item.metadata)} />
        <MetricCard label="Qdrant 状态" value={getQdrantSummary(item)} />
      </div>

      <div className="mt-4 rounded-[1.4rem] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_48%,#ecfeff_100%)] p-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone={item.local_artifacts_present ? "ok" : "warn"}>
                {item.local_artifacts_present ? "本地副本仍在" : "本地副本已清理"}
              </TagPill>
              <TagPill tone={item.qdrant_upserted ? "ok" : item.qdrant_requested ? "warn" : "neutral"}>
                {getQdrantSummary(item)}
              </TagPill>
            </div>
            <p className="mt-3 text-lg font-black tracking-tight text-slate-950">这条记录既是导入结果，也是可复核的知识资产档案</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              在答辩或企业演示时，可以直接用这里解释这批资料的来源、处理方式、治理状态和是否进入向量检索层，而不需要再翻回日志。
            </p>
          </div>
          <div className="grid min-w-[16rem] grid-cols-2 gap-3 xl:grid-cols-1">
            <OpsInlineMetric label="文件预览" value={(item.files || []).length} tone="info" />
            <OpsInlineMetric label="治理提示" value={governanceTips.length} tone="warn" />
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <TagPill tone="neutral">{getDocTypeLabel(item.doc_type)}</TagPill>
        <TagPill tone="neutral">{`创建于 ${formatTime(item.created_at)}`}</TagPill>
        {item.deleted_at ? <TagPill tone="warn">{`已于 ${formatTime(item.deleted_at)} 删除本地副本`}</TagPill> : null}
        {item.qdrant_deleted_at ? <TagPill tone="neutral">{`已于 ${formatTime(item.qdrant_deleted_at)} 清理 Qdrant 副本`}</TagPill> : null}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-sm font-black text-slate-900">治理状态</p>
            <div className="mt-3">
              <AssetStatusPills item={item} />
            </div>
            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
              <p>{`本地输出：${item.output_path || "--"}`}</p>
              <p>{`Qdrant 说明：${item.qdrant_message || "--"}`}</p>
              {item.qdrant_deleted_at ? <p>{`Qdrant 清理时间：${formatTime(item.qdrant_deleted_at)}`}</p> : null}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-sm font-black text-slate-900">可用于答辩的解释点</p>
            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
              {governanceTips.map((tip) => (
                <p key={tip}>- {tip}</p>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-sm font-black text-slate-900">元数据过滤条件</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {metadataEntries.length === 0 ? <TagPill tone="neutral">未填写元数据</TagPill> : null}
              {metadataEntries.map(([key, value]) => (
                <TagPill key={`${item.request_id}-${key}`} tone="neutral">
                  {`${getMetadataLabel(key)}: ${Array.isArray(value) ? value.join(", ") : value}`}
                </TagPill>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">文件与知识块预览</p>
            <TagPill tone="neutral">{`文件 ${(item.files || []).length}`}</TagPill>
          </div>

          <div className="mt-4 space-y-3">
            {(item.files || []).length === 0 ? (
              <SensitiveNotice
                title="暂无文件明细"
                tone="slate"
                body="当前 manifest 里没有保留文件细节。后续如果要扩展成资产详情页 API，也可以在这里继续接入更丰富的文档结构信息。"
              />
            ) : null}

            {(item.files || []).map((file) => (
              <div key={`${item.request_id}-${file.doc_id}`} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-black text-slate-900">{file.file_name}</p>
                    <p className="mt-1 text-xs text-slate-500">{file.stored_path}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <TagPill tone="neutral">{file.doc_id}</TagPill>
                    <TagPill tone="neutral">{`分块 ${file.block_count}`}</TagPill>
                    <TagPill tone="neutral">{`切片 ${file.chunk_count}`}</TagPill>
                  </div>
                </div>

                <div className="mt-3 space-y-2">
                  {(file.previews || []).slice(0, 3).map((preview) => (
                    <div key={preview.chunk_id} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-slate-900">
                          {preview.section || preview.title || preview.chunk_id}
                        </p>
                        {preview.source_page ? <TagPill tone="neutral">{`页码 ${preview.source_page}`}</TagPill> : null}
                      </div>
                      <p className="mt-2 text-xs leading-5 text-slate-600">{preview.snippet || "--"}</p>
                    </div>
                  ))}

                  {(file.previews || []).length > 3 ? (
                    <p className="text-xs text-slate-500">仅展示前 3 个知识块预览，避免详情面板过长。</p>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function OpsView({
  history,
  components,
  activeRunId,
  clearLocalData,
  fetchComponents,
  copyText,
  settings,
  result,
  knowledgeIngestionResult,
  knowledgeCatalog,
  knowledgeIngestionRunning,
  uploadKnowledgeFiles,
  removeKnowledgeArtifacts,
  removeKnowledgeQdrantArtifacts,
  reingestKnowledgeQdrantArtifacts,
}) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [docType, setDocType] = useState("standard");
  const [title, setTitle] = useState("");
  const [region, setRegion] = useState("CN");
  const [industry, setIndustry] = useState("construction");
  const [scenario, setScenario] = useState("");
  const [tags, setTags] = useState("");
  const [upsertQdrant, setUpsertQdrant] = useState(false);
  const [selectedAssetId, setSelectedAssetId] = useState("");

  const metadata = useMemo(
    () => buildMetadata({ region, industry, scenario, tags }),
    [region, industry, scenario, tags]
  );

  useEffect(() => {
    if (knowledgeIngestionResult?.request_id) {
      setSelectedAssetId(knowledgeIngestionResult.request_id);
    }
  }, [knowledgeIngestionResult?.request_id]);

  useEffect(() => {
    if (knowledgeCatalog.length === 0) {
      setSelectedAssetId("");
      return;
    }

    const exists = knowledgeCatalog.some((item) => item.request_id === selectedAssetId);
    if (!exists) {
      setSelectedAssetId(knowledgeCatalog[0].request_id);
    }
  }, [knowledgeCatalog, selectedAssetId]);

  const selectedAsset = useMemo(
    () => knowledgeCatalog.find((item) => item.request_id === selectedAssetId) || null,
    [knowledgeCatalog, selectedAssetId]
  );
  const qdrantTrackedCount = knowledgeCatalog.filter((item) => item.qdrant_upserted || item.qdrant_requested).length;
  const localRetainedCount = knowledgeCatalog.filter((item) => item.local_artifacts_present).length;
  const previewBlockCount = knowledgeCatalog.reduce((sum, item) => sum + countPreviewBlocks(item), 0);
  const governancePendingCount = knowledgeCatalog.filter((item) => item.qdrant_cleanup_required).length;
  const latestAsset = knowledgeCatalog[0] || knowledgeIngestionResult || null;

  return (
    <Panel
      title="本地数据与资产操作"
      subtitle="管理浏览器缓存、运行摘要、企业知识导入与知识资产状态。"
    >
      <div className="rounded-[1.6rem] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_42%,#ecfeff_100%)] p-4 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone={knowledgeCatalog.length ? "ok" : "neutral"}>{knowledgeCatalog.length ? "已有知识资产" : "等待导入资产"}</TagPill>
              <TagPill tone={knowledgeIngestionRunning ? "warn" : "neutral"}>{knowledgeIngestionRunning ? "导入任务运行中" : "当前无导入任务"}</TagPill>
              <TagPill tone={governancePendingCount ? "warn" : "ok"}>{governancePendingCount ? "存在待治理副本" : "当前治理状态可控"}</TagPill>
            </div>
            <p className="mt-3 text-2xl font-black tracking-tight text-slate-950">企业知识运维页先讲清资产状态，再进入导入和治理动作</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              这页不只是一个“上传文件”的地方，还承担企业知识导入、向量副本治理、资产复核和答辩解释四类职责，所以入口层需要先说明当前资产规模和治理状态。
            </p>
          </div>
          <div className="grid min-w-[18rem] grid-cols-2 gap-3 xl:grid-cols-1">
            <OpsInlineMetric label="资产记录" value={knowledgeCatalog.length} tone={buildOpsInlineMetricTone(knowledgeCatalog.length)} />
            <OpsInlineMetric label="待治理项" value={governancePendingCount} tone={governancePendingCount ? "warn" : "ok"} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <MetricCard label="历史记录" value={history.length} />
        <MetricCard label="组件缓存" value={components.length} />
        <MetricCard label="当前任务" value={activeRunId || "--"} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-4">
        <OpsInlineMetric label="本地副本" value={localRetainedCount} tone={localRetainedCount ? "info" : "neutral"} />
        <OpsInlineMetric label="向量跟踪" value={qdrantTrackedCount} tone={qdrantTrackedCount ? "ok" : "neutral"} />
        <OpsInlineMetric label="预览片段" value={previewBlockCount} tone={previewBlockCount ? "info" : "neutral"} />
        <OpsInlineMetric
          label="最近资产"
          value={latestAsset ? getDocTypeLabel(latestAsset.doc_type || latestAsset.docType) : "暂无"}
          tone={buildOpsInlineMetricTone(Boolean(latestAsset), "binary")}
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={clearLocalData}
          className="rounded-xl border border-rose-300 bg-rose-100 px-4 py-2 text-sm font-bold text-rose-700"
        >
          清理本地缓存
        </button>
        <button
          type="button"
          onClick={fetchComponents}
          className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700"
        >
          重建组件缓存
        </button>
        <button
          type="button"
          onClick={() =>
            copyText(
              JSON.stringify(
                {
                  settings,
                  latestDelivery: result?.delivery || null,
                  historyPreview: history.slice(0, 3),
                },
                null,
                2
              ),
              "运行摘要已复制"
            )
          }
          className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700"
        >
          复制运行摘要
        </button>
      </div>

      <div className="mt-6 rounded-[1.6rem] border border-slate-200 bg-gradient-to-br from-white via-slate-50 to-cyan-50/60 p-4">
        <div className="mb-4 grid grid-cols-1 gap-3 xl:grid-cols-3">
          {[
            {
              title: "第一步",
              heading: "准备企业资料",
              detail: "选择与当前项目强相关的标准、制度或案例文件，避免把无关资料混入导入集。",
            },
            {
              title: "第二步",
              heading: "补齐导入标签",
              detail: "通过文档类型、区域、行业和场景标签，把这批知识纳入可解释的检索上下文。",
            },
            {
              title: "第三步",
              heading: "确认治理方式",
              detail: "决定是否写入 Qdrant，并在导入后通过资产档案继续管理本地副本与向量副本。",
            },
          ].map((item) => (
            <div key={item.title} className="rounded-[1.3rem] border border-white/80 bg-white/80 p-4 shadow-sm">
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">{item.title}</p>
              <p className="mt-3 text-base font-black text-slate-950">{item.heading}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.detail}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">企业知识导入工作台</p>
          <TagPill tone="neutral">支持 PDF / DOCX</TagPill>
          <TagPill tone="warn">默认按企业敏感资料处理</TagPill>
          <TagPill tone={upsertQdrant ? "ok" : "warn"}>
            {upsertQdrant ? "导入后尝试写入 Qdrant" : "仅生成本地 JSONL"}
          </TagPill>
        </div>

        <p className="mt-2 text-xs leading-5 text-slate-500">
          上传企业标准、制度或历史案例后，系统会做条款级切块并生成 JSONL。这些文件通常包含企业内部信息，演示结束后建议及时清理。
        </p>

        <div className="mt-4 space-y-3">
          <SensitiveNotice
            title="导入提醒"
            body="上传文件、切块预览和输出路径会进入知识资产记录，建议只保留当前项目需要的资料。"
          />
          <SensitiveNotice
            title="使用说明"
            tone="rose"
            body="如果写入了 Qdrant，删除本地文件不会同时删除向量副本；相关状态会在知识资产详情中单独显示。"
          />
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
          <label className="block text-sm font-semibold text-slate-700">
            选择文件
            <input
              type="file"
              accept=".pdf,.docx"
              multiple
              onChange={(event) => setSelectedFiles(Array.from(event.target.files || []))}
              className="mt-1 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            />
          </label>

          <label className="block text-sm font-semibold text-slate-700">
            文档类型
            <select
              value={docType}
              onChange={(event) => setDocType(event.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            >
              <option value="standard">标准规范</option>
              <option value="policy">制度文件</option>
              <option value="case">历史案例</option>
              <option value="template">交付模板</option>
            </select>
          </label>

          <label className="block text-sm font-semibold text-slate-700">
            标题覆盖
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="单文件导入时可覆盖文档标题"
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            />
          </label>

          <label className="block text-sm font-semibold text-slate-700">
            场景标签
            <input
              value={scenario}
              onChange={(event) => setScenario(event.target.value)}
              placeholder="例如 BIM 协同 / 隐蔽工程验收 / 竣工交付"
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            />
          </label>

          <label className="block text-sm font-semibold text-slate-700">
            区域
            <input
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            />
          </label>

          <label className="block text-sm font-semibold text-slate-700">
            行业
            <input
              value={industry}
              onChange={(event) => setIndustry(event.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            />
          </label>

          <label className="block text-sm font-semibold text-slate-700 xl:col-span-2">
            标签
            <input
              value={tags}
              onChange={(event) => setTags(event.target.value)}
              placeholder="用逗号分隔，例如 国密, 审计, 密钥轮换"
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="inline-flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={upsertQdrant}
              onChange={(event) => setUpsertQdrant(event.target.checked)}
            />
            导入后尝试写入 Qdrant
          </label>

          <button
            type="button"
            onClick={() =>
              uploadKnowledgeFiles?.({
                files: selectedFiles,
                docType,
                title,
                metadata,
                upsertQdrant,
              })
            }
            disabled={knowledgeIngestionRunning || selectedFiles.length === 0}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-black text-white disabled:opacity-50"
          >
            {knowledgeIngestionRunning ? "导入中..." : "开始导入知识文档"}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {selectedFiles.length === 0 ? <TagPill tone="neutral">尚未选择文件</TagPill> : null}
          {selectedFiles.map((file) => (
            <TagPill key={`${file.name}-${file.size}`} tone="neutral">
              {file.name}
            </TagPill>
          ))}
        </div>

        {knowledgeIngestionResult ? (
          <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">最新导入结果</p>
              <TagPill tone="neutral">{`文件 ${knowledgeIngestionResult.total_files}`}</TagPill>
              <TagPill tone="ok">{`知识块 ${knowledgeIngestionResult.total_chunks}`}</TagPill>
              <TagPill tone="warn">{`request_id ${knowledgeIngestionResult.request_id}`}</TagPill>
            </div>
            <p className="mt-2 text-sm text-slate-700">{`输出路径：${knowledgeIngestionResult.output_path || "--"}`}</p>
            <p className="mt-1 text-sm text-slate-700">{knowledgeIngestionResult.qdrant_message || "--"}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => removeKnowledgeArtifacts?.(knowledgeIngestionResult.request_id)}
                className="rounded-xl border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-bold text-rose-700 hover:border-rose-400"
              >
                删除本次导入文件
              </button>
              <button
                type="button"
                onClick={() => setSelectedAssetId(knowledgeIngestionResult.request_id)}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-700"
              >
                跳转到资产详情
              </button>
              <TagPill tone="warn">删除后将移除本地上传文件和 JSONL</TagPill>
            </div>
          </div>
        ) : null}
      </div>

      <div className="mt-6 rounded-[1.6rem] border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">知识资产列表</p>
          <TagPill tone="neutral">{`记录 ${knowledgeCatalog.length}`}</TagPill>
          {selectedAsset ? <TagPill tone="ok">{`当前查看 ${selectedAsset.request_id}`}</TagPill> : null}
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          这里不只是展示历史导入记录，还把每次导入变成可选中的资产档案。演示时可以直接点开解释这批知识的来源、范围、本地副本状态和
          Qdrant 治理状态。
        </p>

        <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[0.78fr_1.22fr]">
          <div className="space-y-3">
            {knowledgeCatalog.length === 0 ? (
              <SensitiveNotice
                title="暂无知识资产记录"
                tone="slate"
                body="完成一次知识导入后，这里会自动出现资产记录。后续我们还可以继续在这里补“重入库”“重建索引”等动作。"
              />
            ) : null}

            {knowledgeCatalog.map((item) => (
              <AssetListCard
                key={item.request_id}
                item={item}
                selected={item.request_id === selectedAssetId}
                onSelect={setSelectedAssetId}
                onDelete={removeKnowledgeArtifacts}
                reingestKnowledgeQdrantArtifacts={reingestKnowledgeQdrantArtifacts}
              />
            ))}
          </div>

          <div>
            {selectedAsset ? (
              <AssetDetailPanel
                item={selectedAsset}
                copyText={copyText}
                removeKnowledgeArtifacts={removeKnowledgeArtifacts}
                removeKnowledgeQdrantArtifacts={removeKnowledgeQdrantArtifacts}
                reingestKnowledgeQdrantArtifacts={reingestKnowledgeQdrantArtifacts}
              />
            ) : (
              <SensitiveNotice
                title="请选择一条知识资产"
                tone="slate"
                body="选中左侧任意记录后，这里会展示可直接用于答辩和治理操作的资产详情。"
              />
            )}
          </div>
        </div>
      </div>
    </Panel>
  );
}
