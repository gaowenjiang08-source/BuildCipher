import { DisplayBooleanValue } from "../../components/DisplayValue";
import { MetricCard, Panel } from "../../components/Panel";
import { SemanticPill, TagPill } from "../../components/SemanticPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function formatScore(value, digits = 1) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return num.toFixed(digits);
}

function getLaunchDecision(delivery = {}, auditorRounds = []) {
  const status = String(delivery?.status || "").toLowerCase();
  const latestRound = [...(auditorRounds || [])].reverse()[0] || null;
  const compliance = Number(delivery?.compliance_score ?? latestRound?.compliance_score);
  const risk = Number(delivery?.risk_score ?? latestRound?.risk_score);

  if (["approved", "accept", "accepted", "pass", "passed", "ready"].some((item) => status.includes(item))) {
    return {
      label: "建议进入上线评审",
      tone: "ok",
      summary: "当前交付已达到可进入人工复核与上线评审的状态，下一步应聚焦部署检查、密钥治理和审计留痕落地。",
    };
  }

  if (["reject", "rejected", "fail", "failed", "blocked"].some((item) => status.includes(item))) {
    return {
      label: "暂不建议上线",
      tone: "bad",
      summary: "当前方案仍被审计门槛拦截，应优先解决最新审计轮次中的合规、风险与后量子要求后再继续推进。",
    };
  }

  if (Number.isFinite(compliance) && compliance >= 80 && Number.isFinite(risk) && risk <= 30) {
    return {
      label: "建议进入人工复核",
      tone: "warn",
      summary: "关键分数已接近可交付区间，但仍建议保留人工密码学复核与上线前检查，不直接视为可投产。",
    };
  }

  return {
    label: "需要继续整改",
    tone: "warn",
    summary: "当前交付仍处于审计整改阶段，建议继续围绕阻塞项迭代候选方案，再决定是否进入上线评审。",
  };
}

function buildTopBlockers(auditorRounds = [], auditFindings = []) {
  const latestRejectRound = [...(auditorRounds || [])]
    .reverse()
    .find((item) => String(item?.verdict || "").toLowerCase() !== "accept");
  const reasons = latestRejectRound?.reasons || [];
  return [...new Set([...reasons, ...auditFindings].filter(Boolean))].slice(0, 5);
}

function buildPassingPath(delivery = {}, auditRecommendations = []) {
  return [
    delivery?.next_action,
    ...(delivery?.production_guide || []).slice(0, 3),
    ...auditRecommendations,
  ]
    .filter(Boolean)
    .filter((item, index, arr) => arr.indexOf(item) === index)
    .slice(0, 6);
}

function buildRequirementReadiness(structuredSpec, clarifications = []) {
  const requiredCount = clarifications.filter((item) => item?.required).length;
  if (structuredSpec && requiredCount === 0) {
    return {
      tone: "ok",
      label: "需求结构已收口",
      summary: "当前已经具备结构化规格，且没有必须补答的问题，可以进入后续审计与验证主线。",
    };
  }

  if (structuredSpec) {
    return {
      tone: "warn",
      label: "规格已形成但仍待补答",
      summary: "当前已经拿到结构化规格，但还有关键问题待澄清，建议先补齐高优先级业务约束。",
    };
  }

  return {
    tone: "neutral",
    label: "需求结构仍待整理",
    summary: "当前还没有形成稳定的结构化规格，适合先补齐输入边界、目标场景和合规约束。",
  };
}

export function ProjectMemoryPanel({ currentCaseId, currentCaseSummary }) {
  const hasProjectContext = Boolean(currentCaseId || currentCaseSummary?.requirement_summary);
  const projectStatusLabel = currentCaseSummary?.status_label || currentCaseSummary?.status || "待确认";

  return (
    <Panel
      title="项目连续记录"
      subtitle="把当前报告绑定到项目线上，而不是一次性的孤立运行。后续整改、重跑和审计复盘都围绕这个项目展开。"
    >
      <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_50%,#eef6ff_100%)] p-4 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-500">项目记忆概览</p>
            <p className="mt-2 text-lg font-black text-slate-950">
              {hasProjectContext ? "当前报告已挂到项目主线" : "当前报告仍偏单次运行视角"}
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {hasProjectContext
                ? "你可以把后续整改、复跑、审计结论和交付历史都当成同一项目上的连续动作来讲。"
                : "如果这里还是空的，答辩时就很难解释“为什么这轮结果和之前有关联”，建议优先补齐项目上下文。"}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 xl:max-w-[360px] xl:justify-end">
            <TagPill tone={hasProjectContext ? "ok" : "neutral"}>{hasProjectContext ? "项目主线已绑定" : "项目主线待绑定"}</TagPill>
            <TagPill tone="neutral">{projectStatusLabel}</TagPill>
            <TagPill tone="neutral">{`待确认 ${currentCaseSummary?.open_question_count ?? 0}`}</TagPill>
            <TagPill tone="neutral">{`阻塞 ${currentCaseSummary?.blocking_count ?? 0}`}</TagPill>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="项目编号" value={currentCaseId || "--"} />
        <MetricCard label="项目状态" value={currentCaseSummary?.status || "--"} valueLabel={currentCaseSummary?.status_label} />
        <MetricCard label="决策记录" value={currentCaseSummary?.decision_count ?? 0} />
        <MetricCard label="阻塞项" value={currentCaseSummary?.blocking_count ?? 0} />
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">项目摘要</p>
          {currentCaseSummary?.selected_proposal ? <TagPill tone="neutral">{currentCaseSummary.selected_proposal}</TagPill> : null}
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {currentCaseSummary?.requirement_summary || "当前报告尚未绑定清晰的项目摘要，通常表示这是一次独立运行，或项目记忆尚未完整沉淀。"}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <TagPill tone="neutral">{`待确认 ${currentCaseSummary?.open_question_count ?? 0}`}</TagPill>
          <TagPill tone="neutral">{`被拒方案 ${currentCaseSummary?.rejected_count ?? 0}`}</TagPill>
          <TagPill tone="neutral">{`最近合规 ${currentCaseSummary?.latest_compliance_score ?? "--"}`}</TagPill>
          <TagPill tone="neutral">{`最近风险 ${currentCaseSummary?.latest_risk_score ?? "--"}`}</TagPill>
        </div>
      </div>
    </Panel>
  );
}

export function RequirementPanel({ structuredSpec, clarifications }) {
  const readiness = buildRequirementReadiness(structuredSpec, clarifications);
  const requiredCount = clarifications.filter((item) => item?.required).length;

  return (
    <Panel title="需求理解与澄清清单" subtitle="分析阶段会把自然语言需求转成结构化规格，并列出本轮仍需补充的信息。">
      <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_50%,#fff7ed_100%)] p-4 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <SemanticPill kind="status" value={readiness.tone} label={readiness.label} />
              <TagPill tone={structuredSpec ? "ok" : "neutral"}>{structuredSpec ? "结构化规格已生成" : "结构化规格待生成"}</TagPill>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{readiness.summary}</p>
          </div>
          <div className="grid grid-cols-2 gap-2 xl:min-w-[260px]">
            <MetricCard label="澄清问题" value={clarifications.length} />
            <MetricCard label="必须补答" value={requiredCount} />
            <MetricCard label="建议补答" value={Math.max(0, clarifications.length - requiredCount)} />
            <MetricCard label="规格状态" value={structuredSpec ? "已生成" : "待生成"} />
          </div>
        </div>
      </div>

      {structuredSpec ? (
        <pre className="max-h-[24rem] overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
          {JSON.stringify(structuredSpec, null, 2)}
        </pre>
      ) : (
        <p className="text-sm text-slate-500">暂无结构化规格。</p>
      )}

      <div className="mt-3 space-y-2">
        {clarifications.length === 0 ? <p className="text-sm text-slate-500">暂无待澄清问题。</p> : null}
        {clarifications.map((item) => (
          <article key={item.id} className="rounded-xl border border-slate-200 bg-white p-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-bold text-slate-900">{item.id}</p>
              <TagPill tone={item.required ? "bad" : "warn"}>{item.required ? "必须回答" : "建议回答"}</TagPill>
            </div>
            <p className="mt-1 text-sm text-slate-700">{item.question}</p>
            <p className="mt-1 text-xs text-slate-500">{`原因：${item.reason || "--"}`}</p>
          </article>
        ))}
      </div>
    </Panel>
  );
}

export function AuditDecisionPanel({
  delivery,
  auditorRounds,
  auditFindings,
  auditRecommendations,
  finalScheme,
  formatDisplayValue,
}) {
  const launchDecision = getLaunchDecision(delivery, auditorRounds);
  const topBlockers = buildTopBlockers(auditorRounds, auditFindings);
  const passingPath = buildPassingPath(delivery, auditRecommendations);
  const latestRound = [...(auditorRounds || [])].reverse()[0] || null;
  const complianceScore = delivery.compliance_score ?? latestRound?.compliance_score ?? "--";
  const riskScore = delivery.risk_score ?? latestRound?.risk_score ?? "--";

  return (
    <Panel title="审计结论与推进建议" subtitle="集中展示当前交付是否适合继续推进、主要阻塞项，以及通过门槛后的下一步动作。">
      <div className="rounded-[30px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_48%,#eefbf3_100%)] p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <SemanticPill kind="status" value={launchDecision.tone} label={launchDecision.label} />
              {latestRound ? <TagPill tone="neutral">{`最近审计轮 ${latestRound.round}`}</TagPill> : null}
              <TagPill tone={topBlockers.length ? "warn" : "ok"}>{topBlockers.length ? `${topBlockers.length} 项阻塞待处理` : "当前阻塞已收敛"}</TagPill>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{launchDecision.summary}</p>
          </div>
          <div className="grid grid-cols-2 gap-2 xl:min-w-[320px]">
            <MetricCard label="合规分" value={complianceScore} />
            <MetricCard label="风险分" value={riskScore} />
            <MetricCard label="关键发现" value={auditFindings.length} />
            <MetricCard label="下一步动作" value={passingPath.length ? "已形成" : "待形成"} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="审计轮次" value={auditorRounds.length} />
        <MetricCard label="关键发现" value={auditFindings.length} />
        <MetricCard label="整改建议" value={auditRecommendations.length} />
        <MetricCard label="交付状态" value={delivery.status} valueLabel={delivery.status_label} />
      </div>

      <div className="mt-4 rounded-[28px] border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <SemanticPill kind="status" value={launchDecision.tone} label={launchDecision.label} />
          {latestRound ? <TagPill tone="neutral">{`最近审计轮 ${latestRound.round}`}</TagPill> : null}
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-700">{launchDecision.summary}</p>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">当前交付摘要</p>
            {latestRound ? <TagPill tone="neutral">{`最近审计轮 ${latestRound.round}`}</TagPill> : null}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <MetricCard label="交付合规分" value={complianceScore} />
            <MetricCard label="交付风险分" value={riskScore} />
            <MetricCard label="选中方案" value={delivery.selected_proposal || finalScheme?.name || "--"} />
            <MetricCard
              label="执行主线"
              value={formatDisplayValue({
                label:
                  String(delivery?.engine || "").toLowerCase() === "langgraph"
                    ? "LangGraph 主线"
                    : String(delivery?.engine || "").toLowerCase() === "legacy"
                      ? "历史兼容链路"
                      : "LangGraph 主线",
              })}
            />
          </div>

          <div className="mt-4 space-y-3">
            <div>
              <p className="text-sm font-black text-slate-900">评分区间</p>
              <div className="mt-2 space-y-2">
                <div className="rounded-xl border border-slate-200 bg-white p-3">
                  <div className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-700">
                    <span>合规分</span>
                    <span>{formatScore(delivery.compliance_score ?? latestRound?.compliance_score)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-200">
                    <div
                      className="h-2 rounded-full bg-emerald-500"
                      style={{ width: `${Math.max(0, Math.min(100, Number(delivery.compliance_score ?? latestRound?.compliance_score ?? 0)))}%` }}
                    />
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-3">
                  <div className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-700">
                    <span>风险分</span>
                    <span>{formatScore(delivery.risk_score ?? latestRound?.risk_score, 0)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-200">
                    <div
                      className={cn(
                        "h-2 rounded-full",
                        Number(delivery.risk_score ?? latestRound?.risk_score ?? 0) <= 30
                          ? "bg-emerald-500"
                          : Number(delivery.risk_score ?? latestRound?.risk_score ?? 0) <= 60
                            ? "bg-amber-500"
                            : "bg-rose-500"
                      )}
                      style={{ width: `${Math.max(0, Math.min(100, Number(delivery.risk_score ?? latestRound?.risk_score ?? 0)))}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-sm font-black text-slate-900">生产化判断</p>
              <p className="mt-2 text-sm text-slate-700">
                <DisplayBooleanValue label={delivery?.production_ready_label} value={delivery?.production_ready} />
              </p>
              <p className="mt-2 text-xs leading-5 text-slate-500">{delivery?.scenario_fit || "暂无场景适配说明。"}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <p className="text-sm font-black text-slate-900">当前阻塞项</p>
            <p className="mt-1 text-xs text-slate-500">这些问题会直接影响方案是否能越过审计门槛。</p>
            <div className="mt-3 space-y-2">
              {topBlockers.length === 0 ? <p className="text-sm text-slate-500">暂无新的关键阻塞项。</p> : null}
              {topBlockers.map((item, idx) => (
                <p key={`${idx}-${item}`} className="rounded-lg border border-rose-200 bg-white px-3 py-2 text-sm text-rose-800">
                  {idx + 1}. {item}
                </p>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-sm font-black text-slate-900">通过路径建议</p>
            <p className="mt-1 text-xs text-slate-500">把下一步动作、整改建议和生产指南收成一张清单，方便继续推进。</p>
            <div className="mt-3 space-y-2">
              {passingPath.length === 0 ? <p className="text-sm text-slate-500">暂无推荐的推进动作。</p> : null}
              {passingPath.map((item, idx) => (
                <p key={`${idx}-${item}`} className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm text-emerald-800">
                  {idx + 1}. {item}
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}
