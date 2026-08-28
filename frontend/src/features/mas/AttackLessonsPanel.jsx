import { MetricCard, Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";
import { PillButton, ReplayFocusButton, ReplayFocusPill } from "./ReplayFocusPill";

const ATTACK_STAGE_REF = "attack_executor";

function summarizeText(value = "", maxLength = 160) {
  const text = String(value || "").trim();
  if (!text) return "--";
  return text.length <= maxLength ? text : `${text.slice(0, maxLength)}...`;
}

function normalizeRef(value) {
  return String(value || "").trim();
}

function lessonKindLabel(value = "") {
  const normalized = String(value || "").trim();
  if (normalized === "paper_attack_planning") return "论文攻击经验";
  if (normalized === "benchmark_attack_planning") return "Benchmark 攻击经验";
  if (!normalized) return "普通证据";
  return normalized;
}

function buildPlannerEvidenceCards(contextProjections = {}) {
  return (contextProjections?.attack_planning?.cards || []).filter(
    (item) => item?.card_type === "attack_planner_evidence"
  );
}

function uniqueStrings(items = []) {
  return [...new Set((items || []).filter(Boolean).map((item) => String(item).trim()).filter(Boolean))];
}

function deriveProjectionRef(projection = {}, fallbackKey = "") {
  const explicitRef = normalizeRef(projection?.window_ref || projection?.projection_ref);
  if (explicitRef) return explicitRef;

  const agentId = normalizeRef(projection?.agent_id || fallbackKey);
  const roundId = normalizeRef(projection?.round_id || "main");
  if (!agentId) return "";
  return `${agentId}:${roundId || "main"}`;
}

function deriveEvidenceLookupRef(item = {}) {
  return normalizeRef(item?.lookup_ref || item?.evidence_lookup_ref || item?.chunk_id || item?.doc_id);
}

function updateReplayScope(setReplayScope, patch) {
  setReplayScope?.((prev) => ({
    ...(prev || {}),
    ...patch,
  }));
}

function extractLessonRefs(card = {}) {
  const evidenceRefs = Array.isArray(card?.evidence_refs) ? card.evidence_refs : [];
  return evidenceRefs
    .filter((ref) => {
      const metadata = ref?.metadata || {};
      return Boolean(
        metadata?.lesson_kind ||
          String(ref?.chunk_id || "").includes("attack_lesson") ||
          String(ref?.doc_id || "").includes("attack_lesson")
      );
    })
    .map((ref) => {
      const metadata = ref?.metadata || {};
      return {
        ...ref,
        lessonKind: metadata?.lesson_kind || "attack_lesson",
        sourceTitle: metadata?.source_title || "",
        sourceYear: metadata?.source_year,
        attackFocus: Array.isArray(metadata?.attack_focus) ? metadata.attack_focus : [],
        regressionFocus: Array.isArray(metadata?.regression_focus) ? metadata.regression_focus : [],
        applicableTemplates: Array.isArray(metadata?.applicable_templates)
          ? metadata.applicable_templates
          : metadata?.expected_template_id
            ? [metadata.expected_template_id]
            : [],
        plannerSkillHints: Array.isArray(metadata?.planner_skill_hints) ? metadata.planner_skill_hints : [],
        section: ref?.section || metadata?.section_path || "",
      };
    });
}

function LessonRefCard({ item, replayScope, setReplayScope, selectedEvidenceChunkId, setSelectedEvidenceChunkId }) {
  const title = item?.title || item?.chunk_id || "--";
  const evidenceLookupRef = deriveEvidenceLookupRef(item);
  const evidenceActive =
    evidenceLookupRef &&
    (normalizeRef(replayScope?.evidenceLookupRef) === evidenceLookupRef || normalizeRef(selectedEvidenceChunkId) === evidenceLookupRef);
  const sourceLine = [item?.sourceTitle, item?.sourceYear ? String(item.sourceYear) : ""]
    .map((part) => String(part || "").trim())
    .filter(Boolean)
    .join(" · ");

  function focusEvidence() {
    if (!evidenceLookupRef) return;
    setSelectedEvidenceChunkId?.(evidenceLookupRef);
    updateReplayScope(setReplayScope, {
      stageRef: ATTACK_STAGE_REF,
      evidenceLookupRef: normalizeRef(replayScope?.evidenceLookupRef) === evidenceLookupRef ? "" : evidenceLookupRef,
      artifactLookupRef: "",
    });
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold text-slate-900">{title}</p>
        <TagPill tone="warn">{lessonKindLabel(item?.lessonKind)}</TagPill>
        {typeof item?.score === "number" ? <TagPill tone="neutral">{`score ${item.score.toFixed(2)}`}</TagPill> : null}
        {evidenceActive ? <TagPill tone="ok">当前证据焦点</TagPill> : null}
      </div>
      {sourceLine ? <p className="mt-2 text-xs text-slate-500">{sourceLine}</p> : null}
      <p className="mt-2 text-sm leading-6 text-slate-700">{summarizeText(item?.snippet || "当前 lesson 未提供摘要片段。")}</p>

      <div className="mt-2 flex flex-wrap gap-2">
        {item?.section ? <TagPill tone="neutral">{item.section}</TagPill> : null}
        {item?.applicableTemplates?.slice(0, 3).map((templateId) => (
          <TagPill key={`${title}-${templateId}`} tone="neutral">
            {templateId}
          </TagPill>
        ))}
        {evidenceLookupRef ? (
          <PillButton active={Boolean(evidenceActive)} onClick={focusEvidence} ringTone="focus:ring-sky-300">
            <TagPill tone={evidenceActive ? "ok" : "neutral"}>{`证据 ${evidenceLookupRef}`}</TagPill>
          </PillButton>
        ) : null}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 xl:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">攻击关注点</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {item?.attackFocus?.length === 0 ? <TagPill tone="neutral">暂无</TagPill> : null}
            {item?.attackFocus?.slice(0, 4).map((focus) => (
              <TagPill key={`${title}-attack-${focus}`} tone="neutral">
                {focus}
              </TagPill>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">回归关注点</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {item?.regressionFocus?.length === 0 ? <TagPill tone="neutral">暂无</TagPill> : null}
            {item?.regressionFocus?.slice(0, 4).map((focus) => (
              <TagPill key={`${title}-regression-${focus}`} tone="neutral">
                {focus}
              </TagPill>
            ))}
          </div>
        </div>
      </div>

      {item?.plannerSkillHints?.length ? (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Planner Hint</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {item.plannerSkillHints.slice(0, 4).map((hint) => (
              <TagPill key={`${title}-hint-${hint}`} tone="ok">
                {hint}
              </TagPill>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function LessonGroup({
  title,
  items,
  emptyText,
  replayScope,
  setReplayScope,
  selectedEvidenceChunkId,
  setSelectedEvidenceChunkId,
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-black text-slate-900">{title}</p>
        <TagPill tone={items.length ? "ok" : "neutral"}>{items.length}</TagPill>
      </div>
      <div className="mt-3 space-y-3">
        {items.length === 0 ? <p className="text-sm text-slate-500">{emptyText}</p> : null}
        {items.map((item, index) => (
          <LessonRefCard
            key={`${item?.chunk_id || item?.doc_id || title}-${index}`}
            item={item}
            replayScope={replayScope}
            setReplayScope={setReplayScope}
            selectedEvidenceChunkId={selectedEvidenceChunkId}
            setSelectedEvidenceChunkId={setSelectedEvidenceChunkId}
          />
        ))}
      </div>
    </div>
  );
}

function buildImpactChain({ planningMode, memoryHandoffs = [], attackLoop = {}, delivery = {} }) {
  const handoffs = Array.isArray(memoryHandoffs) ? memoryHandoffs : [];
  const normalizedMode = String(planningMode || "baseline").toLowerCase();
  const relatedHandoffs = handoffs.filter((item) => {
    const handoffId = String(item?.handoff_id || "").toLowerCase();
    if (normalizedMode === "regression") {
      return (
        handoffId.includes("attack-replan") ||
        handoffId.includes("vulnerability-regression") ||
        handoffId.includes("reflection")
      );
    }
    return (
      handoffId.includes("attack-planning") ||
      handoffId.includes("vulnerability") ||
      handoffId.includes("patch") ||
      handoffId.includes("reflection")
    );
  });

  const patchSpec = attackLoop?.patch_spec || {};
  const reflectionCards = Array.isArray(attackLoop?.reflection_cards) ? attackLoop.reflection_cards : [];
  const reflectionCard = reflectionCards.find((item) => item?.card_type === "reflection") || {};
  const regressionCard = reflectionCards.find((item) => item?.card_type === "regression_summary") || {};

  return {
    handoffs: relatedHandoffs,
    projectionRefs: uniqueStrings(
      relatedHandoffs
        .map((item) => deriveProjectionRef(item?.projection, item?.to_agent || item?.from_agent || ""))
        .filter(Boolean)
    ).slice(0, 6),
    promptChanges: uniqueStrings(reflectionCard?.prompt_changes || []).slice(0, 4),
    auditFocus: uniqueStrings(reflectionCard?.audit_focus || []).slice(0, 4),
    residualRisks: uniqueStrings(regressionCard?.residual_risks || []).slice(0, 4),
    regressionFocus: uniqueStrings(patchSpec?.regression_focus || []).slice(0, 4),
    patchSummary: patchSpec?.summary || "",
    patchStrategy: patchSpec?.strategy || "",
    nextAction: delivery?.next_action || "",
    productionGuide: uniqueStrings(delivery?.production_guide || []).slice(0, 4),
    selectedProposal: delivery?.selected_proposal || "",
  };
}

function ImpactList({ title, items, tone = "neutral", emptyText }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {items.length === 0 ? <TagPill tone="neutral">{emptyText}</TagPill> : null}
        {items.map((item) => (
          <TagPill key={`${title}-${item}`} tone={tone}>
            {item}
          </TagPill>
        ))}
      </div>
    </div>
  );
}

function ImpactChainPanel({
  planningMode,
  chain,
  replayScope,
  setReplayScope,
  attackPlanningProjectionRef,
}) {
  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const focusedProjectionRef = normalizeRef(replayScope?.projectionRef);
  const focusedHandoffRef = normalizeRef(replayScope?.handoffRef);
  const stageActive = focusedStageRef === ATTACK_STAGE_REF;

  function toggleAttackStage() {
    updateReplayScope(setReplayScope, {
      stageRef: stageActive ? "" : ATTACK_STAGE_REF,
    });
  }

  function toggleProjection(projectionRef) {
    const normalized = normalizeRef(projectionRef);
    if (!normalized) return;
    updateReplayScope(setReplayScope, {
      stageRef: ATTACK_STAGE_REF,
      projectionRef: focusedProjectionRef === normalized ? "" : normalized,
      handoffRef: "",
    });
  }

  function toggleHandoff(handoffRef) {
    const normalized = normalizeRef(handoffRef);
    if (!normalized) return;
    updateReplayScope(setReplayScope, {
      stageRef: ATTACK_STAGE_REF,
      projectionRef: "",
      handoffRef: focusedHandoffRef === normalized ? "" : normalized,
    });
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-black text-slate-900">{`${planningMode} 影响链路`}</p>
        <TagPill tone={chain.handoffs.length ? "ok" : "neutral"}>{`handoff ${chain.handoffs.length}`}</TagPill>
        {chain.selectedProposal ? <TagPill tone="warn">{chain.selectedProposal}</TagPill> : null}
      </div>

      <div className="mt-3 rounded-xl border border-dashed border-slate-300 bg-slate-50/80 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-slate-900">回看联动入口</p>
          <ReplayFocusButton
            kind="stageRef"
            value={ATTACK_STAGE_REF}
            active={stageActive}
            onClick={toggleAttackStage}
            ringTone="focus:ring-amber-300"
          />
          <ReplayFocusButton
            kind="projectionRef"
            value={attackPlanningProjectionRef}
            active={focusedProjectionRef === attackPlanningProjectionRef}
            onClick={() => toggleProjection(attackPlanningProjectionRef)}
            ringTone="focus:ring-emerald-300"
          />
          <ReplayFocusPill kind="handoffRef" value={focusedHandoffRef} active />
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          这组经验卡默认对应攻击规划主链。点击上面的标签，可以把 replay 焦点直接切到攻击规划阶段、窗口或具体 handoff。
        </p>
      </div>

      {chain.projectionRefs.length ? (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">相关 Projection</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {chain.projectionRefs.map((item) => (
              <ReplayFocusButton
                key={`${planningMode}-projection-${item}`}
                kind="projectionRef"
                value={item}
                active={focusedProjectionRef === item}
                onClick={() => toggleProjection(item)}
                ringTone="focus:ring-emerald-300"
              />
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-3 space-y-2">
        {chain.handoffs.length === 0 ? <p className="text-sm text-slate-500">当前没有匹配到可展示的 handoff 链路。</p> : null}
        {chain.handoffs.slice(0, 4).map((item) => {
          const handoffRef = normalizeRef(item?.handoff_id);
          const projectionRef = deriveProjectionRef(item?.projection, item?.to_agent || item?.from_agent || "");
          const handoffActive = focusedHandoffRef === handoffRef;
          const projectionActive = focusedProjectionRef === projectionRef;

          return (
            <div
              key={handoffRef || `${item?.from_agent}-${item?.to_agent}`}
              className={`rounded-xl border px-3 py-3 ${
                handoffActive ? "border-amber-300 bg-amber-50" : "border-slate-200 bg-slate-50"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <TagPill tone="neutral">{item?.from_agent || "--"}</TagPill>
                <span className="text-xs font-semibold text-slate-400">→</span>
                <TagPill tone="warn">{item?.to_agent || "--"}</TagPill>
                {item?.projection?.agent_id ? <TagPill tone="ok">{item.projection.agent_id}</TagPill> : null}
                {handoffRef ? (
                  <ReplayFocusButton
                    kind="handoffRef"
                    value={handoffRef}
                    active={handoffActive}
                    onClick={() => toggleHandoff(handoffRef)}
                    ringTone="focus:ring-amber-300"
                  />
                ) : null}
                {projectionRef ? (
                  <ReplayFocusButton
                    kind="projectionRef"
                    value={projectionRef}
                    active={projectionActive}
                    onClick={() => toggleProjection(projectionRef)}
                    ringTone="focus:ring-emerald-300"
                  />
                ) : null}
              </div>
              <p className="mt-2 text-sm text-slate-700">{summarizeText(item?.objective || "当前 handoff 未提供 objective。", 180)}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <ImpactList
          title="Prompt 改动"
          items={chain.promptChanges}
          tone="ok"
          emptyText="当前反思卡尚未给出 prompt_changes"
        />
        <ImpactList
          title="审计关注点"
          items={chain.auditFocus}
          tone="warn"
          emptyText="当前反思卡尚未给出 audit_focus"
        />
        <ImpactList
          title="回归关注点"
          items={chain.regressionFocus}
          tone="neutral"
          emptyText="当前 patch_spec 尚未给出 regression_focus"
        />
        <ImpactList
          title="残余风险"
          items={chain.residualRisks}
          tone="bad"
          emptyText="当前 regression_summary 尚未给出 residual_risks"
        />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">修补策略</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {chain.patchStrategy ? <TagPill tone="neutral">{chain.patchStrategy}</TagPill> : <TagPill tone="neutral">暂无</TagPill>}
          </div>
          <p className="mt-2 text-sm text-slate-700">{summarizeText(chain.patchSummary || "当前 patch_spec 未提供摘要。", 180)}</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">最终交付牵引</p>
          <p className="mt-2 text-sm text-slate-700">{summarizeText(chain.nextAction || "当前 delivery 未提供 next_action。", 180)}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {chain.productionGuide.length === 0 ? <TagPill tone="neutral">暂无 production_guide</TagPill> : null}
            {chain.productionGuide.map((item) => (
              <TagPill key={`guide-${item}`} tone="ok">
                {item}
              </TagPill>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AttackLessonsPanel({
  contextProjections,
  memoryHandoffs,
  attackLoop,
  delivery,
  replayScope,
  setReplayScope,
  selectedEvidenceChunkId,
  setSelectedEvidenceChunkId,
}) {
  const plannerEvidenceCards = buildPlannerEvidenceCards(contextProjections);
  const attackPlanningProjectionRef = deriveProjectionRef(contextProjections?.attack_planning, "attack_planning");
  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const focusedProjectionRef = normalizeRef(replayScope?.projectionRef);
  const focusedHandoffRef = normalizeRef(replayScope?.handoffRef);

  const plannerGroups = plannerEvidenceCards.map((card, index) => {
    const payload = card?.payload || {};
    const filters = payload?.applied_filters || {};
    const lessons = extractLessonRefs(card);
    return {
      key: `${payload?.planning_mode || "baseline"}-${index}`,
      planningMode: payload?.planning_mode || "baseline",
      query: payload?.query || "",
      targetTemplateId: filters?.target_template_id || "",
      attackSurfaceKind: filters?.attack_surface_kind || "",
      lessons,
      paperLessons: lessons.filter((item) => item.lessonKind === "paper_attack_planning"),
      benchmarkLessons: lessons.filter((item) => item.lessonKind === "benchmark_attack_planning"),
      impactChain: buildImpactChain({
        planningMode: payload?.planning_mode || "baseline",
        memoryHandoffs,
        attackLoop,
        delivery,
      }),
    };
  });

  const allLessons = plannerGroups.flatMap((item) => item.lessons);
  const paperCount = allLessons.filter((item) => item.lessonKind === "paper_attack_planning").length;
  const benchmarkCount = allLessons.filter((item) => item.lessonKind === "benchmark_attack_planning").length;
  const focusedGroupCount = plannerGroups.filter((group) =>
    group.impactChain.handoffs.some((item) => normalizeRef(item?.handoff_id) === focusedHandoffRef)
  ).length;

  return (
    <Panel
      title="攻击经验与来源依据"
      subtitle="查看攻击 agent 的 benchmark 与 paper 增强来源。"
    >
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <MetricCard label="规划轮次" value={plannerGroups.length} />
        <MetricCard label="经验总数" value={allLessons.length} />
        <MetricCard label="论文经验" value={paperCount} />
        <MetricCard label="Benchmark 经验" value={benchmarkCount} />
      </div>

      <div className="mt-4 rounded-[24px] border border-dashed border-slate-300 bg-white/85 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-black text-slate-900">当前与 replay 主线的对齐关系</p>
          <ReplayFocusPill kind="stageRef" value={ATTACK_STAGE_REF} active={focusedStageRef === ATTACK_STAGE_REF} />
          <ReplayFocusPill
            kind="projectionRef"
            value={attackPlanningProjectionRef}
            active={focusedProjectionRef === attackPlanningProjectionRef}
          />
          <ReplayFocusPill kind="handoffRef" value={focusedHandoffRef} active />
          {focusedGroupCount ? <TagPill tone="ok">{`${focusedGroupCount} 个规划轮已命中当前 handoff`}</TagPill> : null}
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          这块面板现在不只解释攻击经验本身，也能把这些经验与攻击规划阶段、攻击规划窗口以及相关 handoff 的回看焦点接起来。
        </p>
      </div>

      <div className="mt-4 space-y-4">
        {plannerGroups.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">当前 attack planning projection 中还没有可用的 lesson 来源数据。</p>
          </div>
        ) : null}

        {plannerGroups.map((group) => (
          <div key={group.key} className="rounded-[28px] border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-black text-slate-900">{`${group.planningMode} 规划轮`}</p>
              {group.targetTemplateId ? <TagPill tone="warn">{group.targetTemplateId}</TagPill> : null}
              {group.attackSurfaceKind ? <TagPill tone="neutral">{group.attackSurfaceKind}</TagPill> : null}
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{summarizeText(group.query || "当前规划轮未提供检索 query。", 220)}</p>

            <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-2">
              <LessonGroup
                title="论文攻击经验"
                items={group.paperLessons}
                emptyText="当前规划轮没有命中论文型攻击经验。"
                replayScope={replayScope}
                setReplayScope={setReplayScope}
                selectedEvidenceChunkId={selectedEvidenceChunkId}
                setSelectedEvidenceChunkId={setSelectedEvidenceChunkId}
              />
              <LessonGroup
                title="Benchmark 攻击经验"
                items={group.benchmarkLessons}
                emptyText="当前规划轮没有命中 benchmark 型攻击经验。"
                replayScope={replayScope}
                setReplayScope={setReplayScope}
                selectedEvidenceChunkId={selectedEvidenceChunkId}
                setSelectedEvidenceChunkId={setSelectedEvidenceChunkId}
              />
            </div>

            <div className="mt-3">
              <ImpactChainPanel
                planningMode={group.planningMode}
                chain={group.impactChain}
                replayScope={replayScope}
                setReplayScope={setReplayScope}
                attackPlanningProjectionRef={attackPlanningProjectionRef}
              />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
