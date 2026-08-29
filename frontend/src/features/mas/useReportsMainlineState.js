import { useEffect, useState } from "react";

function normalizeRef(value) {
  return String(value || "").trim();
}

const ATTACK_MAINLINE_STAGES = ["attack_executor", "vulnerability_evaluation", "patch_reflection"];

export default function useReportsMainlineState({
  replayScope,
  setReplayScope,
  workflowProgress,
  timelineOverview,
  attackLoop,
}) {
  const [jumpedPanelId, setJumpedPanelId] = useState("");

  useEffect(() => {
    if (!jumpedPanelId) return undefined;
    const timer = window.setTimeout(() => setJumpedPanelId(""), 1800);
    return () => window.clearTimeout(timer);
  }, [jumpedPanelId]);

  const focusedStageRef = normalizeRef(replayScope?.stageRef);
  const focusedServiceRef = normalizeRef(replayScope?.targetServiceRef);
  const attackMainlineStageActive = ATTACK_MAINLINE_STAGES.includes(focusedStageRef);

  const flowPanelActive = Boolean(focusedStageRef || replayScope?.projectionRef || replayScope?.handoffRef);
  const replayPanelActive = Boolean(
    focusedStageRef ||
      focusedServiceRef ||
      replayScope?.runId ||
      replayScope?.projectionRef ||
      replayScope?.handoffRef ||
      replayScope?.artifactLookupRef ||
      replayScope?.evidenceLookupRef ||
      replayScope?.retryResumeCheckpointRef ||
      replayScope?.retryResumeInputRef
  );
  const attackPanelActive = Boolean(attackMainlineStageActive || focusedServiceRef);
  const dispatcherPanelActive = Boolean(attackMainlineStageActive || focusedServiceRef);

  const defaultFlowStageRef = normalizeRef(workflowProgress?.[0]?.phase);
  const defaultReplayRunId = normalizeRef(timelineOverview?.latest_run_id);
  const defaultTargetServiceRef = normalizeRef(
    attackLoop?.current_round?.target_service_ref ||
      attackLoop?.target_service_ref ||
      attackLoop?.target_service?.service_id ||
      attackLoop?.target_service?.service_ref
  );

  const flowSpotlightTitle = flowPanelActive ? "已选择流程焦点" : "未选择流程焦点";
  const flowSpotlightDetail = focusedStageRef
    ? `当前阶段焦点为 ${focusedStageRef}，适合继续查看上下文窗口、memory handoff 与流程节点。`
    : "查看 workflow trace、独立上下文窗口和结构化交接。";

  const replaySpotlightTitle = replayPanelActive ? "当前焦点已进入 Replay 深钻主线" : "当前还未锁定 Replay 深钻焦点";
  const replaySpotlightDetail = normalizeRef(replayScope?.runId)
    ? `当前 run 焦点为 ${normalizeRef(replayScope?.runId)}，并会继续联动事件、快照与目标服务轨迹。`
    : focusedServiceRef
      ? `当前目标服务焦点为 ${focusedServiceRef}，适合继续查看回看事件、快照与 lineage。`
      : "查看事件、快照、handoff 与目标服务轨迹。";

  const attackSpotlightTitle = attackPanelActive ? "当前焦点已进入攻击闭环主线" : "当前还未锁定攻击闭环焦点";
  const attackSpotlightDetail = focusedServiceRef
    ? `当前围绕目标服务 ${focusedServiceRef} 观察攻击轮次、漏洞评估与修补结果。`
    : attackMainlineStageActive
      ? `当前阶段 ${focusedStageRef} 已落在攻击闭环主链。`
      : "查看目标服务、攻击轮次、漏洞评估与代码交付。";

  const dispatchSpotlightTitle = dispatcherPanelActive ? "当前焦点已进入执行平面主线" : "当前还未锁定执行平面焦点";
  const dispatchSpotlightDetail = focusedServiceRef
    ? `当前执行平面会优先围绕目标服务 ${focusedServiceRef} 展示沙盒调度与审批。`
    : attackMainlineStageActive
      ? `当前阶段 ${focusedStageRef} 已命中执行平面相关主链，可继续查看调度、审批与回归动作。`
      : "查看沙盒调度、部署审批与回归治理。";

  function jumpToMainlinePanel(panelId) {
    setJumpedPanelId(panelId);

    if (typeof setReplayScope === "function") {
      setReplayScope((prev) => {
        const next = { ...(prev || {}) };

        if (panelId === "mainline-panel-flow") {
          next.stageRef = prev?.stageRef || defaultFlowStageRef || "";
        }

        if (panelId === "mainline-panel-replay") {
          next.runId = prev?.runId || defaultReplayRunId || "";
          next.targetServiceRef = prev?.targetServiceRef || defaultTargetServiceRef || "";
        }

        if (panelId === "mainline-panel-attack" || panelId === "mainline-panel-dispatch") {
          next.stageRef = attackMainlineStageActive ? prev?.stageRef || focusedStageRef : "attack_executor";
          next.targetServiceRef = prev?.targetServiceRef || defaultTargetServiceRef || "";
        }

        return next;
      });
    }

    if (typeof window !== "undefined") {
      window.requestAnimationFrame(() => {
        const target = document.getElementById(panelId);
        target?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }

  return {
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
  };
}
