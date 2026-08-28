import EvidencePackPanel from "./EvidencePackPanel";
import EvidenceLinkPanel from "./EvidenceLinkPanel";
import CandidateEvidencePanel from "./CandidateEvidencePanel";
import FlowTransparencyPanel from "./FlowTransparencyPanel";
import SandboxDispatcherPanel from "./SandboxDispatcherPanel";
import RoundComparisonPanel from "./RoundComparisonPanel";
import HandoffArtifactPanel from "./HandoffArtifactPanel";
import AttackLessonsPanel from "./AttackLessonsPanel";
import AttackLoopPanel from "./AttackLoopPanel";
import ReplayTimelinePanel from "./ReplayTimelinePanel";
import ReplayFocusLegendPanel from "./ReplayFocusLegendPanel";
import DeferredPanelMount from "./DeferredPanelMount";
import ReportsQuickMap from "./ReportsQuickMap";
import ReportsChapterSummaryBar from "./ReportsChapterSummaryBar";
import ReportsSectionNavigator from "./ReportsSectionNavigator";
import ReportsSectionDivider from "./ReportsSectionDivider";
import { CredibilityPanel, DeliveryPanel } from "./ReportsOutcomePanels";
import { AuditDecisionPanel, ProjectMemoryPanel, RequirementPanel } from "./ReportsSummaryPanels";
import { MainlinePanelFrame, MainlinePanelRail, MainlinePositionBar } from "./ReportsMainlineChrome";
import {
  ReportsEvidenceDeliveryBridgePanel,
  ReportsHeroBanner,
  ReportsMainlineOverviewPanel,
  WorkflowAttackBridgePanel,
} from "./ReportsMainlinePanels";
import useReportsEvidenceState from "./useReportsEvidenceState";
import { useEffect, useRef } from "react";
import useSectionSpy from "./useSectionSpy";
import useReportsMainlineState from "./useReportsMainlineState";

export default function ReportsView({
  businessReturnContext,
  onReturnToBusinessContext,
  persistedSectionId,
  onSyncActiveSection,
  currentCaseId,
  currentCaseSummary,
  structuredSpec,
  clarifications,
  result,
  auditorRounds,
  auditFindings,
  auditRecommendations,
  delivery,
  attackLoop,
  codeArtifacts,
  workflowTrace,
  workflowProgress,
  contextProjections,
  memoryHandoffs,
  sandboxDispatcher,
  timelineOverview,
  replayDrilldown,
  replayEventsResponse,
  replaySnapshotsResponse,
  replayScope,
  setReplayScope,
  replayLineage,
  replayLoading,
  replayError,
  replayEventsLoading,
  replayEventsError,
  replaySnapshotsLoading,
  replaySnapshotsError,
  replayListLoading,
  replayListError,
  replaySourceUpdatedAt,
  replaySourceParams,
  replaySourceHistory,
  refreshReplaySource,
  replayLineageLoading,
  replayLineageError,
  architectCandidates,
  credibilityAssessment,
  credibilitySources,
  componentEvidence,
  evidencePack,
  comparisonTable,
  comparisonCharts,
  finalScheme,
  deliveryPackage,
  exportFormats,
  exportDelivery,
  history,
  loadFromHistory,
  selectedProposalId,
  setSelectedProposalId,
  selectedEvidenceChunkId,
  setSelectedEvidenceChunkId,
  selectedDeliveryFragmentId,
  setSelectedDeliveryFragmentId,
  formatDisplayValue,
  RadarChartComponent,
  BarChartComponent,
  ScatterChartComponent,
}) {
  const safeClarifications = Array.isArray(clarifications) ? clarifications : [];
  const safeAuditorRounds = Array.isArray(auditorRounds) ? auditorRounds : [];
  const safeAuditFindings = Array.isArray(auditFindings) ? auditFindings : [];
  const safeAuditRecommendations = Array.isArray(auditRecommendations) ? auditRecommendations : [];
  const safeWorkflowTrace = Array.isArray(workflowTrace) ? workflowTrace : [];
  const safeWorkflowProgress = Array.isArray(workflowProgress) ? workflowProgress : [];
  const safeContextProjections =
    contextProjections && typeof contextProjections === "object" && !Array.isArray(contextProjections)
      ? contextProjections
      : {};
  const safeMemoryHandoffs = Array.isArray(memoryHandoffs) ? memoryHandoffs : [];
  const safeArchitectCandidates = Array.isArray(architectCandidates) ? architectCandidates : [];
  const safeCredibilitySources = Array.isArray(credibilitySources) ? credibilitySources : [];
  const safeComponentEvidence = Array.isArray(componentEvidence) ? componentEvidence : [];
  const safeComparisonTable = Array.isArray(comparisonTable) ? comparisonTable : [];
  const safeComparisonCharts =
    comparisonCharts && typeof comparisonCharts === "object" && !Array.isArray(comparisonCharts)
      ? comparisonCharts
      : {};
  const safeHistory = Array.isArray(history) ? history : [];
  const hasRestoredPersistedSectionRef = useRef(false);
  const {
    selectedEvidence,
    linkedEvidence,
    candidateLinks,
    deliveryFragments,
    proposalDeliveryLinks,
    proposalReplayContext,
    deliveryProposalMap,
    replayEvidenceContext,
    selectedDeliveryFragmentId: activeSelectedDeliveryFragmentId,
    focusReplayFromEvent,
    focusReplayFromSnapshot,
    focusReplayFromHandoff,
    focusReplayFromRun,
    focusReplayFromStage,
    focusReplayFromArtifact,
    focusDeliveryFragment,
    selectEvidence,
  } = useReportsEvidenceState({
    evidencePack,
    selectedEvidenceChunkId,
    setSelectedEvidenceChunkId,
    selectedDeliveryFragmentId,
    setSelectedDeliveryFragmentId,
    replayScope,
    replayDrilldown,
    auditorRounds: safeAuditorRounds,
    auditRecommendations: safeAuditRecommendations,
    delivery,
    result,
    finalScheme,
    architectCandidates: safeArchitectCandidates,
    selectedProposalId,
    setSelectedProposalId,
    setReplayScope,
  });
  const {
    jumpedPanelId,
    flowPanelActive,
    replayPanelActive,
    attackPanelActive,
    dispatcherPanelActive,
    flowSpotlightTitle,
    flowSpotlightDetail,
    replaySpotlightTitle,
    replaySpotlightDetail,
    attackSpotlightTitle,
    attackSpotlightDetail,
    dispatchSpotlightTitle,
    dispatchSpotlightDetail,
    jumpToMainlinePanel,
  } = useReportsMainlineState({
    replayScope,
    setReplayScope,
    workflowProgress: safeWorkflowProgress,
    timelineOverview,
    attackLoop,
  });
  const reportSectionItems = [
    {
      id: "reports-section-overview",
      label: "项目与需求摘要",
      detail: "先建立项目背景、需求理解和审计起点。",
      kind: "section",
    },
    {
      id: "mainline-panel-flow",
      label: "流程概览",
      detail: "流程轨迹与结构化交接。",
      kind: "mainline",
    },
    {
      id: "mainline-panel-replay",
      label: "回放深钻",
      detail: "事件、快照与回看路径。",
      kind: "mainline",
    },
    {
      id: "mainline-panel-attack",
      label: "攻击闭环",
      detail: "攻击轮次、漏洞评估与代码交付。",
      kind: "mainline",
    },
    {
      id: "mainline-panel-dispatch",
      label: "执行平面",
      detail: "沙盒调度、审批与回归治理。",
      kind: "mainline",
    },
    {
      id: "reports-section-handoff",
      label: "交接与工件深钻",
      detail: "跨 Agent 的结构化交接与工件引用。",
      kind: "section",
    },
    {
      id: "reports-section-evidence-bridge",
      label: "证据与交付收口",
      detail: "可信度与最终交付。",
      kind: "section",
    },
    {
      id: "reports-section-credibility",
      label: "可信度与整改摘要",
      detail: "对比、可信度与当前整改建议。",
      kind: "section",
    },
    {
      id: "reports-section-evidence-pack",
      label: "证据包与联动解读",
      detail: "证据如何支撑回放、审计与方案选择。",
      kind: "section",
    },
    {
      id: "reports-section-delivery",
      label: "最终交付与历史记录",
      detail: "交付输出、导出物与历史回放。",
      kind: "section",
    },
  ];
  const activeSectionId = useSectionSpy(reportSectionItems.map((item) => item.id));
  const mainlineActive = flowPanelActive || replayPanelActive;
  const attackActive = attackPanelActive || dispatcherPanelActive;
  const deliveryActive =
    [
      "reports-section-handoff",
      "reports-section-evidence-bridge",
      "reports-section-credibility",
      "reports-section-evidence-pack",
      "reports-section-delivery",
    ].includes(activeSectionId) || Boolean(selectedEvidence || activeSelectedDeliveryFragmentId);
  const overviewActive = !mainlineActive && !attackActive && !deliveryActive;
  const currentMainlineLabel =
    (flowPanelActive && "流程概览") ||
    (replayPanelActive && "回放深钻") ||
    (attackPanelActive && "攻击闭环") ||
    (dispatcherPanelActive && "执行平面") ||
    "";

  function jumpToSection(sectionId) {
    if (typeof window === "undefined") return;
    window.requestAnimationFrame(() => {
      const target = document.getElementById(sectionId);
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  useEffect(() => {
    if (!activeSectionId || !onSyncActiveSection) return;
    onSyncActiveSection(activeSectionId);
  }, [activeSectionId, onSyncActiveSection]);

  useEffect(() => {
    if (!persistedSectionId || typeof window === "undefined" || hasRestoredPersistedSectionRef.current) return;
    hasRestoredPersistedSectionRef.current = true;
    const timer = window.requestAnimationFrame(() => {
      const target = document.getElementById(persistedSectionId);
      target?.scrollIntoView?.({ behavior: "smooth", block: "start" });
    });
    return () => window.cancelAnimationFrame(timer);
  }, [persistedSectionId]);

  return (
    <>
      {businessReturnContext?.summary ? (
        <section className="rounded-[24px] border border-amber-200 bg-[linear-gradient(135deg,#fffdf6_0%,#ffffff_58%,#f8fafc_100%)] p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-amber-300 bg-amber-100 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-amber-800">
              业务回跳锚点
            </span>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
              {businessReturnContext.viewLabel}
            </span>
            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
              {businessReturnContext.sectionLabel}
            </span>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
              {businessReturnContext.sectionSource === "manual" ? "手动阅读落点" : "系统推荐落点"}
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{businessReturnContext.summary}</p>
          {onReturnToBusinessContext ? (
            <button
              type="button"
              onClick={() => onReturnToBusinessContext?.()}
              className="mt-3 rounded-xl border border-amber-300 bg-white px-4 py-2 text-sm font-bold text-amber-800 transition hover:bg-amber-100"
            >
              返回业务上下文
            </button>
          ) : null}
        </section>
      ) : null}

      <ReportsQuickMap
        items={reportSectionItems}
        activeSectionId={activeSectionId}
        currentMainlineLabel={currentMainlineLabel}
        selectedEvidence={selectedEvidence}
        selectedDeliveryFragmentId={activeSelectedDeliveryFragmentId}
        onJumpToMainlinePanel={jumpToMainlinePanel}
        onJumpToSection={jumpToSection}
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2 2xl:pr-[20rem]">
        <ReportsChapterSummaryBar
          overviewActive={overviewActive}
          mainlineActive={mainlineActive}
          attackActive={attackActive}
          deliveryActive={deliveryActive}
          onJumpToOverview={() => jumpToSection("reports-section-overview")}
          onJumpToMainline={() => jumpToMainlinePanel("mainline-panel-flow")}
          onJumpToAttack={() => jumpToMainlinePanel("mainline-panel-attack")}
          onJumpToDelivery={() => jumpToSection("reports-section-evidence-bridge")}
        />

        <ReportsHeroBanner
          currentCaseId={currentCaseId}
          currentCaseSummary={currentCaseSummary}
          delivery={delivery}
          auditorRounds={safeAuditorRounds}
          workflowProgress={safeWorkflowProgress}
          replayScope={replayScope}
          attackLoop={attackLoop}
          codeArtifacts={codeArtifacts}
          selectedEvidence={selectedEvidence}
          selectedProposalId={selectedProposalId}
          selectedDeliveryFragmentId={activeSelectedDeliveryFragmentId}
          onJumpToMainlinePanel={jumpToMainlinePanel}
          onJumpToSection={jumpToSection}
        />
        <ReplayFocusLegendPanel replayScope={replayScope} />

        <ReportsMainlineOverviewPanel
          currentCaseId={currentCaseId}
          delivery={delivery}
          auditorRounds={safeAuditorRounds}
          workflowProgress={safeWorkflowProgress}
          replayScope={replayScope}
          attackLoop={attackLoop}
          codeArtifacts={codeArtifacts}
        />

        <MainlinePanelRail
          workflowProgress={safeWorkflowProgress}
          replayScope={replayScope}
          attackLoop={attackLoop}
          codeArtifacts={codeArtifacts}
          flowPanelActive={flowPanelActive}
          replayPanelActive={replayPanelActive}
          attackPanelActive={attackPanelActive}
          dispatcherPanelActive={dispatcherPanelActive}
          onJumpToPanel={jumpToMainlinePanel}
        />

        <MainlinePositionBar
          replayScope={replayScope}
          flowPanelActive={flowPanelActive}
          replayPanelActive={replayPanelActive}
          attackPanelActive={attackPanelActive}
          dispatcherPanelActive={dispatcherPanelActive}
          onJumpToPanel={jumpToMainlinePanel}
          jumpedPanelId={jumpedPanelId}
        />

        <ReportsSectionNavigator
          flowPanelActive={flowPanelActive}
          replayPanelActive={replayPanelActive}
          attackPanelActive={attackPanelActive}
          dispatcherPanelActive={dispatcherPanelActive}
          selectedEvidence={selectedEvidence}
          selectedProposalId={selectedProposalId}
          selectedDeliveryFragmentId={activeSelectedDeliveryFragmentId}
          onJumpToMainlinePanel={jumpToMainlinePanel}
          onJumpToSection={jumpToSection}
        />

      <div id="reports-section-overview" className="cg-scroll-target">
        <ProjectMemoryPanel currentCaseId={currentCaseId} currentCaseSummary={currentCaseSummary} />
      </div>
      <div className="cg-scroll-target">
        <RequirementPanel structuredSpec={structuredSpec} clarifications={safeClarifications} />
      </div>

      <div className="cg-scroll-target">
        <AuditDecisionPanel
          delivery={delivery}
          auditorRounds={safeAuditorRounds}
          auditFindings={safeAuditFindings}
          auditRecommendations={safeAuditRecommendations}
          finalScheme={finalScheme}
          formatDisplayValue={formatDisplayValue}
        />
      </div>

      <ReportsSectionDivider
        eyebrow="第一章"
        title="主线透视层"
        subtitle="查看工作流、上下文与回放路径。"
        hint="查看流程，再看回放。"
        tone="sky"
        chips={[
          { label: flowPanelActive ? "流程段已命中" : "流程概览", tone: flowPanelActive ? "ok" : "neutral" },
          { label: replayPanelActive ? "回看段已命中" : "回放深钻", tone: replayPanelActive ? "ok" : "neutral" },
        ]}
      />

      <MainlinePanelFrame
        step="01"
        title="流程概览"
        summary="查看真实流程轨迹、上下文窗口与结构化交接。"
        active={flowPanelActive}
        accent="sky"
        panelId="mainline-panel-flow"
        recentlyJumped={jumpedPanelId === "mainline-panel-flow"}
        spotlightTitle={flowSpotlightTitle}
        spotlightDetail={flowSpotlightDetail}
        spotlightTone={flowPanelActive ? "info" : "neutral"}
        guideSummary="查看流程轨迹、上下文窗口和结构化交接。"
        guideFocus={
          flowPanelActive
            ? "当前焦点已命中流程或上下文阶段。"
            : "这一段可作为整页起点。"
        }
        guideNextLabel="下一段去哪"
        guideNextDetail="接着查看回放深钻。"
        guideActionLabel="跳到回放深钻"
        onGuideAction={() => jumpToMainlinePanel("mainline-panel-replay")}
      >
        <FlowTransparencyPanel
          workflowTrace={safeWorkflowTrace}
          workflowProgress={safeWorkflowProgress}
          contextProjections={safeContextProjections}
          memoryHandoffs={safeMemoryHandoffs}
          replayScope={replayScope}
          setReplayScope={setReplayScope}
          replaySourceUpdatedAt={replaySourceUpdatedAt}
          replaySourceHistory={replaySourceHistory}
        />
      </MainlinePanelFrame>

      <MainlinePanelFrame
        step="02"
        title="回放深钻"
        summary="这里承接共享焦点，把事件、快照、交接与目标服务轨迹继续往下钻。"
        active={replayPanelActive}
        accent="cyan"
        panelId="mainline-panel-replay"
        recentlyJumped={jumpedPanelId === "mainline-panel-replay"}
        spotlightTitle={replaySpotlightTitle}
        spotlightDetail={replaySpotlightDetail}
        spotlightTone={replayPanelActive ? "info" : "neutral"}
        guideSummary="查看事件、快照、交接和目标服务回看。"
        guideFocus={
          replayPanelActive
            ? "当前共享焦点已经落在某个阶段或目标服务上。"
            : "这一段可继续查看回放轨迹。"
        }
        guideNextLabel="下一段去哪"
        guideNextDetail="接下来查看攻击闭环。"
        guideActionLabel="跳到攻击闭环"
        onGuideAction={() => jumpToMainlinePanel("mainline-panel-attack")}
      >
        <ReplayTimelinePanel
          currentCaseId={currentCaseId}
          timelineOverview={timelineOverview}
          replayDrilldown={replayDrilldown}
          replayEventsResponse={replayEventsResponse}
          replaySnapshotsResponse={replaySnapshotsResponse}
          replayScope={replayScope}
          setReplayScope={setReplayScope}
          selectedProposalId={selectedProposalId}
          proposalReplayContext={proposalReplayContext}
          replayLineage={replayLineage}
          loading={replayLoading}
          error={replayError}
          replayEventsLoading={replayEventsLoading}
          replayEventsError={replayEventsError}
          replaySnapshotsLoading={replaySnapshotsLoading}
          replaySnapshotsError={replaySnapshotsError}
          listLoading={replayListLoading}
          listError={replayListError}
          replaySourceUpdatedAt={replaySourceUpdatedAt}
          replaySourceParams={replaySourceParams}
          replaySourceHistory={replaySourceHistory}
          refreshReplaySource={refreshReplaySource}
          lineageLoading={replayLineageLoading}
          lineageError={replayLineageError}
        />
      </MainlinePanelFrame>

      <div className="xl:col-span-2">
        <WorkflowAttackBridgePanel
          workflowProgress={safeWorkflowProgress}
          replayScope={replayScope}
          attackLoop={attackLoop}
          codeArtifacts={codeArtifacts}
        />
      </div>

      <ReportsSectionDivider
        eyebrow="第二章"
        title="攻防闭环层"
        subtitle="查看攻击轮次、漏洞评估、修补建议与执行治理。"
        hint="查看攻击轮次、目标服务与执行治理。"
        tone="rose"
        chips={[
          { label: attackPanelActive ? "攻击段已命中" : "等待攻击焦点", tone: attackPanelActive ? "ok" : "neutral" },
          { label: dispatcherPanelActive ? "执行段已命中" : "待进入执行治理", tone: dispatcherPanelActive ? "ok" : "neutral" },
        ]}
      />

      <MainlinePanelFrame
        step="03"
        title="攻击闭环"
        summary="目标服务、攻击轮次、漏洞评估与代码交付。"
        active={attackPanelActive}
        accent="rose"
        panelId="mainline-panel-attack"
        recentlyJumped={jumpedPanelId === "mainline-panel-attack"}
        spotlightTitle={attackSpotlightTitle}
        spotlightDetail={attackSpotlightDetail}
        spotlightTone={attackPanelActive ? "warn" : "neutral"}
        guideSummary="查看目标服务、攻击轮次、漏洞评估与修补结果。"
        guideFocus={
          attackPanelActive
            ? "当前焦点已命中攻击主链。"
            : "这里可用于查看攻防结果。"
        }
        guideNextLabel="下一段去哪"
        guideNextDetail="接下来查看执行平面。"
        guideActionLabel="跳到执行平面"
        onGuideAction={() => jumpToMainlinePanel("mainline-panel-dispatch")}
      >
        <AttackLoopPanel
          attackLoop={attackLoop}
          codeArtifacts={codeArtifacts}
          replayScope={replayScope}
          setReplayScope={setReplayScope}
        />
      </MainlinePanelFrame>

      <RoundComparisonPanel attackLoop={attackLoop} replayScope={replayScope} setReplayScope={setReplayScope} />

      <MainlinePanelFrame
        step="04"
        title="执行平面"
        summary="查看沙盒执行审批、部署与回归动作。"
        active={dispatcherPanelActive}
        accent="amber"
        panelId="mainline-panel-dispatch"
        recentlyJumped={jumpedPanelId === "mainline-panel-dispatch"}
        spotlightTitle={dispatchSpotlightTitle}
        spotlightDetail={dispatchSpotlightDetail}
        spotlightTone={dispatcherPanelActive ? "warn" : "neutral"}
        guideSummary="沙盒执行、审批门控、部署动作与回归治理已接入主线。"
        guideFocus={
          dispatcherPanelActive
            ? "当前焦点已经进入执行治理层。"
            : "展示沙盒调度、审批与回归治理。"
        }
        guideNextLabel="下一段去哪"
        guideNextDetail="下一步查看证据与交付层。"
        guideActionLabel="跳到最终交付"
        onGuideAction={() => jumpToSection("reports-section-delivery")}
      >
        <SandboxDispatcherPanel
          sandboxDispatcher={sandboxDispatcher}
          replayScope={replayScope}
          setReplayScope={setReplayScope}
        />
      </MainlinePanelFrame>

      <ReportsSectionDivider
        eyebrow="第三章"
        title="证据与交付层"
        subtitle="查看结构化交接、证据包、可信度解释与最终交付。"
        hint="先看证据来源，再看可信度与整改。"
        tone="emerald"
        chips={[
          { label: selectedEvidence ? "证据已联动" : "证据待展开", tone: selectedEvidence ? "ok" : "neutral" },
          { label: activeSelectedDeliveryFragmentId ? "交付片段已锁定" : "交付待收口", tone: activeSelectedDeliveryFragmentId ? "warn" : "neutral" },
        ]}
      />

      <ReportsEvidenceDeliveryBridgePanel
        selectedEvidence={selectedEvidence}
        evidencePack={evidencePack}
        credibilityAssessment={credibilityAssessment}
        delivery={delivery}
        finalScheme={finalScheme}
        selectedProposalId={selectedProposalId}
        selectedDeliveryFragmentId={activeSelectedDeliveryFragmentId}
        deliveryFragments={deliveryFragments}
        onJumpToSection={jumpToSection}
      />

      <DeferredPanelMount title="交接与工件深钻" className="xl:col-span-2" sectionId="reports-section-handoff">
        <HandoffArtifactPanel
          memoryHandoffs={safeMemoryHandoffs}
          contextProjections={safeContextProjections}
          replayScope={replayScope}
          setReplayScope={setReplayScope}
        />
      </DeferredPanelMount>

      <DeferredPanelMount title="攻击经验与来源依赖" sectionId="reports-section-attack-lessons">
        <AttackLessonsPanel
          contextProjections={safeContextProjections}
          memoryHandoffs={safeMemoryHandoffs}
          attackLoop={attackLoop}
          delivery={delivery}
          replayScope={replayScope}
          setReplayScope={setReplayScope}
          selectedEvidenceChunkId={selectedEvidenceChunkId}
          setSelectedEvidenceChunkId={setSelectedEvidenceChunkId}
        />
      </DeferredPanelMount>

      <DeferredPanelMount title="可信度、对比与整改摘要" sectionId="reports-section-credibility">
        <CredibilityPanel
          credibilityAssessment={credibilityAssessment}
          credibilitySources={safeCredibilitySources}
          componentEvidence={safeComponentEvidence}
          comparisonTable={safeComparisonTable}
          comparisonCharts={safeComparisonCharts}
          RadarChartComponent={RadarChartComponent}
          BarChartComponent={BarChartComponent}
          ScatterChartComponent={ScatterChartComponent}
          auditFindings={safeAuditFindings}
          auditRecommendations={safeAuditRecommendations}
          onJumpToSection={jumpToSection}
        />
      </DeferredPanelMount>

      <DeferredPanelMount title="规范依据与证据包" sectionId="reports-section-evidence-pack">
        <EvidencePackPanel
          evidencePack={evidencePack}
          selectedChunkId={selectedEvidenceChunkId}
          onSelectEvidence={selectEvidence}
          onJumpToSection={jumpToSection}
        />
      </DeferredPanelMount>

      <DeferredPanelMount title="证据联动解读" sectionId="reports-section-evidence-links">
        <EvidenceLinkPanel
          selectedEvidence={selectedEvidence}
          linkedRounds={linkedEvidence.linkedRounds}
          linkedRecommendations={linkedEvidence.linkedRecommendations}
          linkedDeliveryFragments={linkedEvidence.linkedDeliveryFragments}
          replayEvidenceContext={replayEvidenceContext}
          replayScope={replayScope}
          onFocusReplayEvent={focusReplayFromEvent}
          onFocusReplaySnapshot={focusReplayFromSnapshot}
          onFocusReplayHandoff={focusReplayFromHandoff}
          onFocusReplayRun={focusReplayFromRun}
          onFocusReplayStage={focusReplayFromStage}
          onFocusReplayArtifact={focusReplayFromArtifact}
          selectedDeliveryFragmentId={activeSelectedDeliveryFragmentId}
          onFocusDeliveryFragment={focusDeliveryFragment}
          onJumpToSection={jumpToSection}
        />
      </DeferredPanelMount>

      <DeferredPanelMount title="证据支撑候选方案" sectionId="reports-section-candidate-evidence">
        <CandidateEvidencePanel
          selectedEvidence={selectedEvidence}
          candidateLinks={candidateLinks}
          selectedProposalId={selectedProposalId}
          onSelectProposal={setSelectedProposalId}
          proposalReplayContext={proposalReplayContext}
          replayScope={replayScope}
          onFocusReplayEvent={focusReplayFromEvent}
          onFocusReplaySnapshot={focusReplayFromSnapshot}
          onFocusReplayHandoff={focusReplayFromHandoff}
          onFocusReplayRun={focusReplayFromRun}
          onFocusReplayStage={focusReplayFromStage}
          onFocusReplayArtifact={focusReplayFromArtifact}
          onJumpToSection={jumpToSection}
        />
      </DeferredPanelMount>

      <DeferredPanelMount title="最终交付与历史记录" className="xl:col-span-2" sectionId="reports-section-delivery">
        <DeliveryPanel
          delivery={delivery}
          finalScheme={finalScheme}
          deliveryPackage={deliveryPackage}
          exportFormats={exportFormats}
          exportDelivery={exportDelivery}
          history={safeHistory}
          loadFromHistory={loadFromHistory}
          deliveryFragments={deliveryFragments}
          deliveryProposalMap={deliveryProposalMap}
          selectedProposalId={selectedProposalId}
          proposalDeliveryLinks={proposalDeliveryLinks}
          selectedDeliveryFragmentId={activeSelectedDeliveryFragmentId}
          onSelectDeliveryFragment={focusDeliveryFragment}
          onSelectProposal={setSelectedProposalId}
          onJumpToSection={jumpToSection}
        />
      </DeferredPanelMount>
      </div>
    </>
  );
}
