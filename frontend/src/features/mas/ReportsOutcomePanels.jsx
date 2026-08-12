import { useEffect } from "react";
import { MetricCard, Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";
import ClosurePanelLead from "./ClosurePanelLead";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function formatScore(value, digits = 1) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return num.toFixed(digits);
}

function formatTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("zh-CN", { hour12: false });
}

function normalizeRef(value) {
  return String(value || "").trim();
}

export function CredibilityPanel({
  credibilityAssessment,
  credibilitySources,
  componentEvidence,
  comparisonTable,
  comparisonCharts,
  RadarChartComponent,
  BarChartComponent,
  ScatterChartComponent,
  auditFindings,
  auditRecommendations,
  onJumpToSection,
}) {
  const credibilityScore = credibilityAssessment?.credibility_score;
  const credibilitySummary =
    credibilityAssessment?.trust_summary ||
    credibilityAssessment?.summary ||
    "当前可通过可信度评分、证据覆盖和优势缺口来解释这份结果为什么值得采信。";

  return (
    <Panel title="可信度、对比与整改摘要" subtitle="集中展示可信度评分、候选方案对比图，以及本轮关键发现与整改建议。">
      <ClosurePanelLead
        eyebrow="收尾模块"
        title="先回答“为什么可信”，再进入证据或交付收尾"
        detail="这一块负责把可信度评分、优势缺口、对比图和整改建议收成一句可答辩的话，先建立“这份结果为何可采信”的结论。"
        statusLabel={credibilityAssessment?.trust_level_label || credibilityAssessment?.trust_level || "等待可信度摘要"}
        statusTone={credibilityAssessment?.credibility_score != null ? "ok" : "neutral"}
        nextLabel="下一步建议"
        nextDetail="若当前更想强调依据链，可跳到证据包继续讲来源；若已经讲完可信度，可直接进入最终交付完成收尾。"
        actionLabel="跳到最终交付"
        onAction={() => onJumpToSection?.("reports-section-delivery")}
        accent="emerald"
      />

      <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f0fdf4_48%,#eff6ff_100%)] p-4 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone={credibilityScore != null ? "ok" : "neutral"}>
                {credibilityScore != null ? "可信度结论已形成" : "可信度结论待形成"}
              </TagPill>
              <TagPill tone={comparisonTable.length >= 2 ? "ok" : "neutral"}>
                {comparisonTable.length >= 2 ? "候选方案已可对比" : "候选方案对比待补齐"}
              </TagPill>
              <TagPill tone={auditRecommendations.length ? "warn" : "ok"}>
                {auditRecommendations.length ? `${auditRecommendations.length} 条整改建议` : "当前建议已收敛"}
              </TagPill>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{credibilitySummary}</p>
          </div>
          <div className="grid grid-cols-2 gap-2 xl:min-w-[320px]">
            <MetricCard label="可信度得分" value={credibilityScore ?? "--"} />
            <MetricCard label="证据覆盖率" value={credibilityAssessment?.evidence_coverage ?? "--"} />
            <MetricCard label="关键发现" value={auditFindings.length} />
            <MetricCard label="整改建议" value={auditRecommendations.length} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="可信度得分" value={credibilityAssessment?.credibility_score ?? "--"} />
        <MetricCard label="算法实力" value={credibilityAssessment?.algorithm_strength_score ?? "--"} />
        <MetricCard label="证据覆盖率" value={credibilityAssessment?.evidence_coverage ?? "--"} />
        <MetricCard label="可信等级" value={credibilityAssessment?.trust_level} valueLabel={credibilityAssessment?.trust_level_label} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-sm font-black text-slate-900">可信度解读</p>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">优势</p>
              {(credibilityAssessment?.strengths || []).length === 0 ? <p className="text-sm text-slate-500">暂无优势摘要。</p> : null}
              {(credibilityAssessment?.strengths || []).slice(0, 5).map((item, idx) => (
                <p key={`strength-${idx}`} className="mb-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                  {item}
                </p>
              ))}
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">缺口</p>
              {(credibilityAssessment?.gaps || []).length === 0 ? <p className="text-sm text-slate-500">暂无明显缺口。</p> : null}
              {(credibilityAssessment?.gaps || []).slice(0, 5).map((item, idx) => (
                <p key={`gap-${idx}`} className="mb-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
                  {item}
                </p>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-sm font-black text-slate-900">证据来源</p>
          <p className="mt-1 text-xs text-slate-500">用于解释可信度评分的主要证据来源与组件依据。</p>
          <div className="mt-3 space-y-2">
            {credibilitySources.length === 0 ? <p className="text-sm text-slate-500">暂无证据来源。</p> : null}
            {credibilitySources.slice(0, 8).map((item, idx) => (
              <p key={`source-${idx}`} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                {item}
              </p>
            ))}
          </div>
          <div className="mt-4">
            <p className="text-sm font-black text-slate-900">组件证据</p>
            <div className="mt-3 space-y-2">
              {componentEvidence.length === 0 ? <p className="text-sm text-slate-500">暂无组件证据摘要。</p> : null}
              {componentEvidence.slice(0, 8).map((item, idx) => (
                <p key={`component-evidence-${idx}`} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  {typeof item === "string" ? item : JSON.stringify(item)}
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">候选方案对比</p>
          <TagPill tone="neutral">{comparisonTable.length}</TagPill>
        </div>
        {comparisonTable.length < 2 ? (
          <p className="mt-2 text-sm text-slate-500">候选方案数量不足，暂时无法展示完整对比图。</p>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">雷达图</p>
              <RadarChartComponent
                labels={comparisonCharts?.radar_chart?.labels || []}
                datasets={comparisonCharts?.radar_chart?.datasets || []}
              />
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">柱状图</p>
              <BarChartComponent
                labels={comparisonCharts?.bar_chart?.labels || []}
                series={comparisonCharts?.bar_chart?.datasets || []}
              />
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">散点图</p>
              <ScatterChartComponent datasets={comparisonCharts?.scatter_plot?.datasets || []} />
            </div>
          </div>
        )}

        {comparisonTable.length ? (
          <div className="mt-4 overflow-auto rounded-2xl border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left">方案</th>
                  <th className="px-3 py-2 text-left">安全性</th>
                  <th className="px-3 py-2 text-left">性能</th>
                  <th className="px-3 py-2 text-left">复杂度</th>
                  <th className="px-3 py-2 text-left">标准化</th>
                  <th className="px-3 py-2 text-left">综合分</th>
                  <th className="px-3 py-2 text-left">风险</th>
                </tr>
              </thead>
              <tbody>
                {comparisonTable.map((row, idx) => (
                  <tr key={`comparison-row-${idx}`} className="border-t border-slate-200">
                    <td className="px-3 py-2 font-semibold text-slate-800">{row.scheme || row.name || row.proposal_id || "--"}</td>
                    <td className="px-3 py-2 text-slate-700">{row.security ?? "--"}</td>
                    <td className="px-3 py-2 text-slate-700">{row.performance ?? "--"}</td>
                    <td className="px-3 py-2 text-slate-700">{row.complexity ?? "--"}</td>
                    <td className="px-3 py-2 text-slate-700">{row.standardization ?? "--"}</td>
                    <td className="px-3 py-2 text-slate-700">{row.overall ?? row.score ?? "--"}</td>
                    <td className="px-3 py-2 text-slate-700">{row.risk ?? "--"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-sm font-black text-slate-900">关键发现</p>
          <div className="mt-3 space-y-2">
            {auditFindings.length === 0 ? <p className="text-sm text-slate-500">暂无关键发现。</p> : null}
            {auditFindings.slice(0, 12).map((item, idx) => (
              <p key={`finding-${idx}`} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
                {idx + 1}. {item}
              </p>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-sm font-black text-slate-900">整改建议</p>
          <div className="mt-3 space-y-2">
            {auditRecommendations.length === 0 ? <p className="text-sm text-slate-500">暂无整改建议。</p> : null}
            {auditRecommendations.slice(0, 12).map((item, idx) => (
              <p key={`recommendation-${idx}`} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                {idx + 1}. {item}
              </p>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}

export function DeliveryPanel({
  delivery,
  finalScheme,
  deliveryPackage,
  exportFormats,
  exportDelivery,
  history,
  loadFromHistory,
  deliveryFragments = [],
  deliveryProposalMap = {},
  selectedProposalId = "",
  proposalDeliveryLinks = [],
  selectedDeliveryFragmentId = "",
  onSelectDeliveryFragment,
  onSelectProposal,
  onJumpToSection,
}) {
  const selectedFragmentProposalLinks =
    deliveryProposalMap?.[normalizeRef(selectedDeliveryFragmentId)] || [];
  const finalSchemeName = finalScheme?.name || "未形成最终方案";
  const deliveryStatusLabel = String(delivery?.status_label || delivery?.status || "").trim() || "待形成交付结论";
  const exportCount = exportFormats.length;
  const historyCount = history.length;
  const closingCards = [
    {
      id: "scheme",
      eyebrow: "交付结论",
      value: finalSchemeName,
      detail: selectedDeliveryFragmentId
        ? `当前已锁定交付片段：${selectedDeliveryFragmentId}`
        : "当前适合用最终方案名称和交付状态做答辩结尾的一句话总结。",
      toneClass: finalScheme?.name ? "border-violet-200 bg-violet-50/90" : "border-slate-200 bg-white",
      pills: [
        <TagPill key="status" tone={selectedDeliveryFragmentId || finalScheme?.name ? "ok" : "neutral"}>{deliveryStatusLabel}</TagPill>,
      ],
    },
    {
      id: "export",
      eyebrow: "导出能力",
      value: exportCount ? `${exportCount} 类导出可用` : "导出待配置",
      detail: exportCount
        ? "可以直接导出交付摘要、证据包、审计结论和完整交付 JSON。"
        : "当前尚未检测到可用导出格式，适合先完成交付包生成后再演示。", 
      toneClass: exportCount ? "border-emerald-200 bg-emerald-50/90" : "border-slate-200 bg-white",
      pills: [
        <TagPill key="export-count" tone={exportCount ? "ok" : "neutral"}>{`${exportCount} 个导出入口`}</TagPill>,
      ],
    },
    {
      id: "history",
      eyebrow: "复盘能力",
      value: historyCount ? `${historyCount} 条历史可回放` : "暂无历史回放",
      detail: historyCount
        ? "可以在答辩结尾展示不同轮次的结果对比，强调系统具备复盘和持续迭代能力。"
        : "如果当前还没有历史记录，可以把这一块作为后续演示预留区。", 
      toneClass: historyCount ? "border-sky-200 bg-sky-50/90" : "border-slate-200 bg-white",
      pills: [
        <TagPill key="history-count" tone={historyCount ? "ok" : "neutral"}>{`${historyCount} 条历史`}</TagPill>,
      ],
    },
  ];

  useEffect(() => {
    const fragmentId = normalizeRef(selectedDeliveryFragmentId);
    if (!fragmentId) return;
    const target = document.getElementById(`delivery-fragment-${fragmentId}`);
    target?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [selectedDeliveryFragmentId]);

  return (
    <Panel title="最终交付与历史记录" subtitle="集中查看最终方案、导出交付包，并从历史运行中回载完整报告。">
      <ClosurePanelLead
        eyebrow="收口模块"
        title="把方案、交付片段、导出物和历史回放收成最后一页"
        detail="这一块负责把前面的证据、可信度、候选方案和整改结果最终沉淀到交付包，形成可以导出、回放、对外展示的结尾。"
        statusLabel={selectedDeliveryFragmentId ? "交付片段已锁定" : finalScheme?.name ? "最终方案已形成" : "等待交付收口"}
        statusTone={selectedDeliveryFragmentId || finalScheme?.name ? "ok" : "neutral"}
        nextLabel="收尾建议"
        nextDetail="这一页适合做答辩结尾。讲完交付片段和导出包之后，可以顺手回放历史运行，展示系统具备复盘和对比能力。"
        actionLabel="回看可信度摘要"
        onAction={() => onJumpToSection?.("reports-section-credibility")}
        accent="violet"
      />

      <div className="mt-4 rounded-[30px] border border-violet-200 bg-[radial-gradient(circle_at_top_left,rgba(139,92,246,0.16),transparent_24%),radial-gradient(circle_at_88%_10%,rgba(16,185,129,0.14),transparent_28%),linear-gradient(135deg,rgba(255,255,255,0.98),rgba(245,243,255,0.96),rgba(248,250,252,0.98))] p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="warn">交付收口总览</TagPill>
              <TagPill tone={finalScheme?.name ? "ok" : "neutral"}>{finalScheme?.name ? "最终方案已成形" : "等待方案收口"}</TagPill>
              <TagPill tone={selectedDeliveryFragmentId ? "ok" : "neutral"}>{selectedDeliveryFragmentId ? "交付片段已锁定" : "交付片段待锁定"}</TagPill>
            </div>
            <p className="mt-4 text-2xl font-black tracking-tight text-slate-950">把整个系统的结果沉淀成可导出、可回放、可答辩的最后一页</p>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              这里不是单纯的导出按钮区，而是整套多 Agent 审计流程的最终落点。适合用来总结最终方案、交付能力和复盘能力，让答辩在这里完成收尾。
            </p>
          </div>

          <div className="rounded-[24px] border border-white/80 bg-white/88 px-4 py-4 shadow-sm xl:max-w-sm">
            <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">收尾讲解脚本</p>
            <p className="mt-2 text-sm font-black text-slate-950">推荐顺序：先报交付结论，再展示导出物，最后点一下历史回放能力。</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              这样可以把“最终方案是什么”“如何交付”“系统如何复盘”三件事一次讲完，更像完整产品收尾，而不是功能列表。
            </p>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-3">
          {closingCards.map((card) => (
            <div key={card.id} className={cn("rounded-[24px] border px-4 py-4 shadow-sm", card.toneClass)}>
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">{card.eyebrow}</p>
              <p className="mt-2 text-lg font-black text-slate-950">{card.value}</p>
              <p className="mt-2 text-sm leading-6 text-slate-700">{card.detail}</p>
              <div className="mt-3 flex flex-wrap gap-2">{card.pills}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_48%,#f5f3ff_100%)] p-4 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone={finalScheme?.name ? "ok" : "neutral"}>{finalScheme?.name ? "最终方案已形成" : "最终方案待形成"}</TagPill>
              <TagPill tone={exportCount ? "ok" : "neutral"}>{exportCount ? `${exportCount} 个导出入口` : "导出入口待配置"}</TagPill>
              <TagPill tone={historyCount ? "ok" : "neutral"}>{historyCount ? `${historyCount} 条历史可回放` : "历史回放待沉淀"}</TagPill>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">
              这一层先把“最终交付是否已经成形、能不能导出、是否能拿历史结果做复盘”三件事讲清楚，再进入片段级细节。
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 xl:min-w-[320px]">
            <MetricCard label="交付片段" value={deliveryFragments.length} />
            <MetricCard label="导出入口" value={exportCount} />
            <MetricCard label="历史回放" value={historyCount} />
            <MetricCard label="最终方案" value={finalScheme?.name ? "已形成" : "待形成"} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="最终方案" value={finalScheme?.name || "--"} />
        <MetricCard label="安全等级" value={finalScheme?.security_level || "--"} />
        <MetricCard label="合规分" value={delivery?.compliance_score ?? "--"} />
        <MetricCard label="风险分" value={delivery?.risk_score ?? "--"} />
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">交付关键片段</p>
          <TagPill tone="neutral">{deliveryFragments.length}</TagPill>
          {selectedDeliveryFragmentId ? <TagPill tone="ok">已定位</TagPill> : null}
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          这里把下一步动作、场景适配、生产部署建议、合规摘要、漏洞摘要和最终方案设计理由收口成一份交付片段目录，方便从证据解读反向定位到具体交付落点。
        </p>
        <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">方案到交付</p>
            {selectedProposalId ? <TagPill tone="ok">{selectedProposalId}</TagPill> : <TagPill tone="neutral">未锁定</TagPill>}
            {proposalDeliveryLinks.length > 0 ? <TagPill tone="warn">{`${proposalDeliveryLinks.length} 个关联片段`}</TagPill> : null}
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            当前会把跨页共享的方案焦点映射到最相关的交付片段，帮助把“证据支持哪条方案”和“方案最终落在哪段交付”连成一条可见链路。
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {proposalDeliveryLinks.length === 0 ? (
              <TagPill tone="neutral">当前方案还没有命中明显的交付片段</TagPill>
            ) : (
              proposalDeliveryLinks.map((item) => {
                const active = normalizeRef(selectedDeliveryFragmentId) === normalizeRef(item.fragmentId);
                return (
                  <button key={`proposal-delivery-${item.fragmentId}`} type="button" onClick={() => onSelectDeliveryFragment?.(item)}>
                    <TagPill tone={active ? "ok" : "neutral"}>
                      {`${item.label} ${formatScore(item.score, item.score >= 10 ? 1 : 2)}`}
                    </TagPill>
                  </button>
                );
              })
            )}
          </div>
        </div>
        <div className="mt-3 rounded-2xl border border-slate-200 bg-white px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">交付回溯到方案</p>
            {selectedDeliveryFragmentId ? (
              <TagPill tone="ok">{selectedDeliveryFragmentId}</TagPill>
            ) : (
              <TagPill tone="neutral">未选片段</TagPill>
            )}
            {selectedFragmentProposalLinks.length > 0 ? (
              <TagPill tone="warn">{`${selectedFragmentProposalLinks.length} 个关联方案`}</TagPill>
            ) : null}
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            当你先从交付片段出发看报告时，这里会把当前片段反向映射到候选方案，方便继续回跳到工作台和候选方案视角。
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {selectedDeliveryFragmentId && selectedFragmentProposalLinks.length === 0 ? (
              <TagPill tone="neutral">当前片段还没有命中明显的关联方案</TagPill>
            ) : null}
            {!selectedDeliveryFragmentId ? <TagPill tone="neutral">先选中一个交付片段</TagPill> : null}
            {selectedFragmentProposalLinks.map((item) => {
              const active = normalizeRef(selectedProposalId) === normalizeRef(item.proposalId);
              return (
                <button
                  key={`delivery-proposal-${item.proposalId}`}
                  type="button"
                  onClick={() => onSelectProposal?.(item.proposalId)}
                >
                  <TagPill tone={active ? "ok" : item.selected ? "warn" : "neutral"}>
                    {`${item.proposalId} ${formatScore(item.score, item.score >= 10 ? 1 : 2)}`}
                  </TagPill>
                </button>
              );
            })}
          </div>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-2">
          {deliveryFragments.length === 0 ? <p className="text-sm text-slate-500">当前没有可展示的交付片段。</p> : null}
          {deliveryFragments.map((item) => {
            const active = normalizeRef(selectedDeliveryFragmentId) === normalizeRef(item.fragmentId);
            const fragmentProposalLinks = deliveryProposalMap?.[normalizeRef(item.fragmentId)] || [];
            return (
              <div
                key={item.fragmentId}
                id={`delivery-fragment-${item.fragmentId}`}
                onClick={() => onSelectDeliveryFragment?.(item)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectDeliveryFragment?.(item);
                  }
                }}
                role="button"
                tabIndex={0}
                className={cn(
                  "cg-scroll-target rounded-[20px] border px-4 py-3 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-sky-300",
                  active ? "cg-focus-block border-sky-300 bg-sky-50" : "border-slate-200 bg-slate-50 hover:bg-white"
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <TagPill tone={active ? "ok" : "neutral"}>{item.label}</TagPill>
                  {active ? <TagPill tone="warn">已定位</TagPill> : null}
                  {fragmentProposalLinks.length > 0 ? (
                    <TagPill tone="neutral">{`${fragmentProposalLinks.length} 个方案关联`}</TagPill>
                  ) : null}
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{item.text}</p>
                {fragmentProposalLinks.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {fragmentProposalLinks.slice(0, 3).map((proposal) => {
                      const proposalActive = normalizeRef(selectedProposalId) === normalizeRef(proposal.proposalId);
                      return (
                        <button
                          key={`${item.fragmentId}-${proposal.proposalId}`}
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            onSelectProposal?.(proposal.proposalId);
                            onSelectDeliveryFragment?.(item);
                          }}
                        >
                          <TagPill tone={proposalActive ? "ok" : proposal.selected ? "warn" : "neutral"}>
                            {proposal.proposalId}
                          </TagPill>
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-black text-slate-900">交付导出</p>
            <div className="flex flex-wrap gap-2">
              {exportFormats.map((fmt) => (
                <button
                  key={fmt.id}
                  type="button"
                  onClick={() => exportDelivery(fmt.id)}
                  className="rounded-xl border border-slate-300 bg-white px-3 py-1 text-xs font-bold text-slate-700 hover:border-slate-500"
                >
                  {fmt.label}
                </button>
              ))}
            </div>
          </div>
          <p className="mt-2 text-xs text-slate-500">导出内容包含交付摘要、证据包、审计结论、整改建议以及完整交付 JSON。</p>
          <pre className="mt-3 max-h-[22rem] overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
            {JSON.stringify(deliveryPackage || {}, null, 2)}
          </pre>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-sm font-black text-slate-900">历史运行回放</p>
          <p className="mt-1 text-xs text-slate-500">可以回载本地保存的运行结果，快速对比不同轮次的方案和审计变化。</p>
          <div className="mt-3 space-y-2">
            {history.length === 0 ? <p className="text-sm text-slate-500">暂无历史记录。</p> : null}
            {history.slice(0, 8).map((item, idx) => (
              <button
                key={`history-${idx}-${item.run_id || item.request_id || idx}`}
                type="button"
                onClick={() => loadFromHistory(item)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-left transition hover:border-slate-300 hover:bg-white"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <TagPill tone="neutral">{item.case_id || "--"}</TagPill>
                  <TagPill tone="neutral">{item.run_id || item.request_id || "--"}</TagPill>
                  <TagPill tone="neutral">{item.delivery?.status_label || item.delivery?.status || "已完成"}</TagPill>
                </div>
                <p className="mt-2 text-sm font-semibold text-slate-800">
                  {item.final_scheme?.name || item.delivery?.selected_proposal || "未命名方案"}
                </p>
                <p className="mt-1 text-xs text-slate-500">{formatTime(item.generated_at)}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}
