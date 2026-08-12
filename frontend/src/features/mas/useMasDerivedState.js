import { useMemo } from "react";
import {
  actorMatches,
  buildWorkflowProgress,
  DEFAULT_WORKFLOW_TRACE,
  displayOrDash,
  getWorkflowStep,
  normalizePhase,
} from "./masHelpers";

export default function useMasDerivedState({
  result,
  streamLog,
  selectedActor,
  skills,
  selectedSkillId,
  componentFilter,
  components,
}) {
  const discussionLog = result?.discussion_log?.length ? result.discussion_log : streamLog;
  const finalScheme = result?.final_scheme || null;
  const architectCandidates = result?.architect?.candidates || [];
  const auditorRounds = result?.auditor_rounds || [];
  const engineerAttempts = result?.engineer?.attempts || [];
  const clarifications = result?.analyst?.clarifications || [];
  const structuredSpec = result?.analyst?.structured_spec || null;

  const delivery = useMemo(() => result?.delivery || {}, [result]);
  const attackLoop = useMemo(() => delivery?.attack_loop || {}, [delivery]);
  const codeArtifacts = useMemo(() => delivery?.code_artifacts || {}, [delivery]);
  const workflowTrace = useMemo(() => {
    return Array.isArray(delivery?.workflow_trace) && delivery.workflow_trace.length
      ? delivery.workflow_trace
      : DEFAULT_WORKFLOW_TRACE;
  }, [delivery]);
  const contextProjections = useMemo(() => delivery?.context_projections || {}, [delivery]);
  const memoryHandoffs = useMemo(() => delivery?.memory_handoffs || [], [delivery]);
  const sandboxDispatcher = useMemo(() => delivery?.sandbox_dispatcher || {}, [delivery]);

  const credibilityAssessment = useMemo(() => {
    return result?.credibility_assessment || delivery?.credibility_assessment || finalScheme?.credibility_assessment || {};
  }, [result, delivery, finalScheme]);

  const credibilitySources = useMemo(() => credibilityAssessment?.sources || [], [credibilityAssessment]);
  const componentEvidence = useMemo(() => credibilityAssessment?.component_evidence || [], [credibilityAssessment]);
  const evidencePack = useMemo(() => result?.evidence_pack || result?.architect?.evidence_pack || {}, [result]);

  const variantComparison = useMemo(() => delivery?.variant_comparison || {}, [delivery]);
  const comparisonTable = useMemo(() => variantComparison?.comparison?.side_by_side_table || [], [variantComparison]);
  const comparisonCharts = useMemo(() => variantComparison?.charts || {}, [variantComparison]);

  const selectedSkill = useMemo(() => {
    return skills.find((item) => item.id === selectedSkillId) || null;
  }, [skills, selectedSkillId]);

  const filteredDiscussionLog = useMemo(() => {
    return discussionLog.filter((item) => actorMatches(item.actor, selectedActor));
  }, [discussionLog, selectedActor]);

  const filteredComponents = useMemo(() => {
    const query = componentFilter.trim().toLowerCase();
    if (!query) return components;
    return components.filter((item) => {
      const name = String(item.name || "").toLowerCase();
      const category = String(item.category || "").toLowerCase();
      return name.includes(query) || category.includes(query);
    });
  }, [components, componentFilter]);

  const workflowProgress = useMemo(() => {
    const reached = new Set(discussionLog.map((item) => normalizePhase(item.phase)));
    return buildWorkflowProgress({
      workflowTrace,
      completed: false,
    }).map((step) => {
      let done = reached.has(step.phase);
      switch (step.phase) {
        case "analyst":
          done = done || Boolean(result?.analyst);
          break;
        case "context_builder":
          done = done || Boolean((result?.evidence_pack?.items || result?.architect?.evidence_pack?.items || []).length);
          break;
        case "architect":
          done = done || architectCandidates.length > 0;
          break;
        case "audit":
          done = done || auditorRounds.length > 0;
          break;
        case "engineer":
          done =
            done ||
            engineerAttempts.length > 0 ||
            Boolean(
              finalScheme?.implementation?.python ||
                finalScheme?.implementation?.pseudocode ||
                finalScheme?.implementation?.c
            );
          break;
        case "target_deployer":
          done = done || Boolean(attackLoop?.target_service?.service_id);
          break;
        case "attack_executor":
          done =
            done ||
            Boolean(attackLoop?.attack_decision?.decision_id) ||
            (attackLoop?.attack_specs || []).length > 0 ||
            (attackLoop?.attack_results || []).length > 0;
          break;
        case "vulnerability_evaluation":
          done = done || Boolean(attackLoop?.vulnerability_verdict?.verdict_id || attackLoop?.vulnerability_verdict?.summary);
          break;
        case "patch_reflection":
          done =
            done ||
            Boolean(attackLoop?.patch_spec?.patch_id || attackLoop?.patch_spec?.summary) ||
            (attackLoop?.reflection_cards || []).length > 0;
          break;
        case "delivery":
          done = done || Boolean(result?.delivery);
          break;
        default:
          break;
      }
      const descriptor = getWorkflowStep(step.phase);
      return { ...descriptor, done };
    });
  }, [discussionLog, workflowTrace, result, architectCandidates, auditorRounds, engineerAttempts, finalScheme, attackLoop]);

  const componentGroups = useMemo(() => {
    const grouped = new Map();
    filteredComponents.forEach((item) => {
      const category = displayOrDash(item.category);
      if (!grouped.has(category)) grouped.set(category, []);
      grouped.get(category).push(item);
    });
    return [...grouped.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([category, items]) => ({
        category,
        items: [...items].sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""))),
      }));
  }, [filteredComponents]);

  const auditFindings = useMemo(() => {
    const merged = auditorRounds.flatMap((round) => round.key_findings || []);
    return [...new Set(merged.filter(Boolean))];
  }, [auditorRounds]);

  const auditRecommendations = useMemo(() => {
    const merged = auditorRounds.flatMap((round) => round.recommended_changes || []);
    return [...new Set(merged.filter(Boolean))];
  }, [auditorRounds]);

  const deliveryPackage = useMemo(() => {
    if (!result) return null;
    return {
      request_id: result.request_id || "--",
      run_id: result.run_id || "--",
      case_id: result.case_id || "--",
      generated_at: result.generated_at || "--",
      security_disclaimer: result.security_disclaimer || "",
      case_memory: result.case_memory || null,
      evidence_pack: result.evidence_pack || result.architect?.evidence_pack || {},
      delivery: result.delivery || {},
      attack_loop: attackLoop,
      code_artifacts: codeArtifacts,
      workflow_trace: workflowTrace,
      context_projections: contextProjections,
      memory_handoffs: memoryHandoffs,
      sandbox_dispatcher: sandboxDispatcher,
      applied_skill: result.delivery?.applied_skill || null,
      credibility_assessment: result.credibility_assessment || {},
      analyst: {
        structured_spec: result.analyst?.structured_spec || {},
        clarifications: result.analyst?.clarifications || [],
      },
      architect: {
        candidates: (result.architect?.candidates || []).map((item) => ({
          proposal_id: item.proposal_id,
          name: item.name,
          score: item.score,
          architecture_pattern: item.architecture_pattern,
          design_rationale: item.design_rationale,
          credibility_score: item.credibility_score,
          algorithm_strength_score: item.algorithm_strength_score,
          evidence_coverage: item.evidence_coverage,
          components: item.components || [],
        })),
      },
      final_scheme: finalScheme
        ? {
            name: finalScheme.name,
            scheme_type: finalScheme.scheme_type,
            score: finalScheme.score,
            security_level: finalScheme.security_level,
            components: finalScheme.components || [],
            design_rationale: finalScheme.design_rationale || "",
            security_analysis: finalScheme.security_analysis || {},
            credibility_assessment: finalScheme.credibility_assessment || {},
            implementation: finalScheme.implementation || {},
          }
        : null,
      compliance_report: result.compliance_report || {},
      vulnerability_report: result.vulnerability_report || {},
      audit: {
        rounds: result.auditor_rounds || [],
        findings: auditFindings,
        recommendations: auditRecommendations,
      },
    };
  }, [
    result,
    finalScheme,
    auditFindings,
    auditRecommendations,
    attackLoop,
    codeArtifacts,
    workflowTrace,
    contextProjections,
    memoryHandoffs,
    sandboxDispatcher,
  ]);

  const metrics = useMemo(() => {
    return {
      toolbox: components.length || 152,
      rounds: auditorRounds.length,
      compliance: delivery.compliance_score ?? "--",
      risk: delivery.risk_score ?? "--",
    };
  }, [components.length, auditorRounds.length, delivery.compliance_score, delivery.risk_score]);

  return {
    discussionLog,
    finalScheme,
    architectCandidates,
    auditorRounds,
    engineerAttempts,
    clarifications,
    structuredSpec,
    delivery,
    attackLoop,
    codeArtifacts,
    workflowTrace,
    contextProjections,
    memoryHandoffs,
    sandboxDispatcher,
    credibilityAssessment,
    credibilitySources,
    componentEvidence,
    evidencePack,
    comparisonTable,
    comparisonCharts,
    selectedSkill,
    filteredDiscussionLog,
    filteredComponents,
    workflowProgress,
    componentGroups,
    auditFindings,
    auditRecommendations,
    deliveryPackage,
    metrics,
  };
}
