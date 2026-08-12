function unique(values = []) {
  return [...new Set(values.filter(Boolean))];
}

function toText(value) {
  return String(value || "").trim();
}

function extractSegments(value) {
  const text = toText(value);
  if (!text) return [];
  const chinese = text.match(/[\u4e00-\u9fff]{2,16}/g) || [];
  const ascii = text.toLowerCase().match(/[a-z0-9_.-]{2,24}/g) || [];
  return unique([text, ...chinese, ...ascii]);
}

export function normalizeEvidenceItems(evidencePack) {
  return Array.isArray(evidencePack?.items) ? evidencePack.items.filter(Boolean) : [];
}

export function buildEvidenceSignals(evidenceItem) {
  if (!evidenceItem) return [];
  const metadata = evidenceItem.metadata || {};
  const sources = [
    evidenceItem.title,
    evidenceItem.section,
    evidenceItem.snippet,
    metadata.clause_code,
    ...(Array.isArray(metadata.section_path) ? metadata.section_path : []),
    ...(Array.isArray(metadata.tags) ? metadata.tags : []),
  ];
  return unique(
    sources
      .flatMap((item) => extractSegments(item))
      .filter((item) => item.length >= 2)
      .slice(0, 40)
  );
}

export function getEvidenceMatchScore(text, evidenceItem) {
  const haystack = toText(text).toLowerCase();
  if (!haystack || !evidenceItem) return 0;
  const signals = buildEvidenceSignals(evidenceItem);
  let score = 0;
  signals.forEach((signal) => {
    const normalized = signal.toLowerCase();
    if (normalized && haystack.includes(normalized)) {
      score += normalized.includes(".") ? 3 : normalized.length >= 6 ? 2 : 1;
    }
  });
  return score;
}

function buildRoundText(round = {}) {
  return [
    round?.proposal_id,
    round?.verdict,
    ...(round?.reasons || []),
    ...(round?.key_findings || []),
    ...(round?.recommended_changes || []),
  ].join(" ");
}

export function buildDeliveryFragmentCatalog({
  delivery = {},
  result = {},
  finalScheme = null,
}) {
  return [
    {
      fragmentId: "next_action",
      label: "下一步动作",
      text: delivery?.next_action,
    },
    {
      fragmentId: "scenario_fit",
      label: "场景适配",
      text: delivery?.scenario_fit,
    },
    ...((delivery?.production_guide || []).map((item, index) => ({
      fragmentId: `production_guide_${index + 1}`,
      label: "生产部署建议",
      text: item,
    }))),
    {
      fragmentId: "compliance_summary",
      label: "合规摘要",
      text: result?.compliance_report?.summary_text,
    },
    {
      fragmentId: "vulnerability_summary",
      label: "漏洞摘要",
      text: result?.vulnerability_report?.summary_text,
    },
    {
      fragmentId: "final_scheme_rationale",
      label: "最终方案设计理由",
      text: finalScheme?.design_rationale,
    },
  ].filter((item) => toText(item?.text));
}

export function buildEvidenceLinkage({
  evidenceItem,
  auditorRounds = [],
  auditRecommendations = [],
  delivery = {},
  result = {},
  finalScheme = null,
}) {
  if (!evidenceItem) {
    return {
      linkedRounds: [],
      linkedRecommendations: [],
      linkedDeliveryFragments: [],
    };
  }

  const linkedRounds = auditorRounds
    .map((round) => ({ round, score: getEvidenceMatchScore(buildRoundText(round), evidenceItem) }))
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 3)
    .map((item) => item.round);

  const linkedRecommendations = auditRecommendations
    .map((item) => ({ text: item, score: getEvidenceMatchScore(item, evidenceItem) }))
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 6)
    .map((item) => item.text);

  const linkedDeliveryFragments = buildDeliveryFragmentCatalog({ delivery, result, finalScheme })
    .map((item) => ({ ...item, score: getEvidenceMatchScore(item.text, evidenceItem) }))
    .filter((item) => item.text && item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 5);

  return {
    linkedRounds,
    linkedRecommendations,
    linkedDeliveryFragments,
  };
}

function buildCandidateText(candidate = {}) {
  return [
    candidate?.proposal_id,
    candidate?.name,
    candidate?.scheme_type,
    candidate?.architecture_pattern,
    candidate?.design_rationale,
    ...((candidate?.components || []).flatMap((item) => [item?.name, item?.category])),
  ].join(" ");
}

function buildCandidateSignals(candidate = {}) {
  return unique(extractSegments(buildCandidateText(candidate))).slice(0, 40);
}

function scoreTextBySignals(text, signals = []) {
  const haystack = toText(text).toLowerCase();
  if (!haystack || signals.length === 0) return 0;
  let score = 0;
  signals.forEach((signal) => {
    const normalized = toText(signal).toLowerCase();
    if (!normalized || !haystack.includes(normalized)) return;
    score += normalized.includes(".") ? 3 : normalized.length >= 6 ? 2 : 1;
  });
  return score;
}

function buildReplayEventText(item = {}) {
  return [
    item?.run_id,
    item?.stage,
    item?.event_kind,
    item?.status,
    item?.summary,
    item?.metadata?.projection_ref,
    item?.metadata?.handoff_ref,
    item?.metadata?.target_service_ref,
    ...(item?.artifact_lookup_refs || []),
    ...(item?.evidence_lookup_refs || []),
  ].join(" ");
}

function buildReplaySnapshotText(item = {}) {
  return [
    item?.run_id,
    item?.selected_proposal,
    item?.summary,
    ...(item?.workflow_trace || []),
    ...(item?.projection_refs || []),
    ...(item?.handoff_refs || []),
    ...(item?.artifact_lookup_refs || []),
    ...(item?.evidence_lookup_refs || []),
  ].join(" ");
}

function buildReplayHandoffText(item = {}) {
  return [
    item?.relation_ref,
    item?.source_agent_id,
    item?.target_agent_id,
    item?.upstream_stage,
    item?.downstream_stage,
    item?.handoff_projection_ref,
    item?.dominant_typed_contract,
    ...(item?.linked_projection_refs || []),
    ...(item?.target_service_refs || []),
    ...(item?.artifact_lookup_refs || []),
    ...(item?.evidence_lookup_refs || []),
  ].join(" ");
}

export function getCandidateSupportScore(candidate, evidenceItem) {
  if (!candidate || !evidenceItem) return 0;
  return getEvidenceMatchScore(buildCandidateText(candidate), evidenceItem);
}

export function buildCandidateEvidenceLinkage({
  evidenceItem,
  architectCandidates = [],
  delivery = {},
}) {
  if (!evidenceItem) return [];

  return architectCandidates
    .map((candidate) => {
      const componentHits = (candidate?.components || [])
        .map((item) => ({
          name: item?.name,
          score: getEvidenceMatchScore([item?.name, item?.category].join(" "), evidenceItem),
        }))
        .filter((item) => item.score > 0)
        .sort((left, right) => right.score - left.score)
        .slice(0, 3)
        .map((item) => item.name);

      return {
        proposalId: candidate?.proposal_id || "",
        name: candidate?.name || candidate?.proposal_id || "--",
        schemeType: candidate?.scheme_type || "",
        architecturePattern: candidate?.architecture_pattern || "",
        score: getCandidateSupportScore(candidate, evidenceItem),
        selected: (delivery?.selected_proposal || "") === (candidate?.proposal_id || ""),
        componentHits,
        candidate,
      };
    })
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 4);
}

export function buildProposalDeliveryLinkage({
  proposalId,
  architectCandidates = [],
  deliveryFragments = [],
}) {
  if (!proposalId) return [];
  const targetCandidate = architectCandidates.find((candidate) => (candidate?.proposal_id || "") === proposalId);
  if (!targetCandidate) return [];

  const candidateText = buildCandidateText(targetCandidate);
  return deliveryFragments
    .map((fragment) => ({
      ...fragment,
      score: getEvidenceMatchScore(candidateText, { title: fragment?.label, snippet: fragment?.text }),
    }))
    .filter((item) => item?.text && item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 4);
}

export function buildDeliveryProposalLinkage({
  fragmentId,
  architectCandidates = [],
  deliveryFragments = [],
  delivery = {},
}) {
  if (!fragmentId) return [];
  const targetFragment = deliveryFragments.find((fragment) => fragment?.fragmentId === fragmentId);
  if (!targetFragment?.text) return [];

  return architectCandidates
    .map((candidate) => ({
      proposalId: candidate?.proposal_id || "",
      name: candidate?.name || candidate?.proposal_id || "--",
      schemeType: candidate?.scheme_type || "",
      architecturePattern: candidate?.architecture_pattern || "",
      score: getEvidenceMatchScore(buildCandidateText(candidate), {
        title: targetFragment?.label,
        snippet: targetFragment?.text,
      }),
      selected: (delivery?.selected_proposal || "") === (candidate?.proposal_id || ""),
      candidate,
    }))
    .filter((item) => item.proposalId && item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 4);
}

export function buildProposalReplayLinkage({
  proposalId,
  architectCandidates = [],
  replayDrilldown = {},
}) {
  if (!proposalId) {
    return {
      matchedEvents: [],
      matchedSnapshots: [],
      matchedHandoffs: [],
      runIds: [],
      stageRefs: [],
      artifactRefs: [],
      handoffRefs: [],
      targetServiceRefs: [],
    };
  }

  const targetCandidate = architectCandidates.find((candidate) => (candidate?.proposal_id || "") === proposalId);
  if (!targetCandidate) {
    return {
      matchedEvents: [],
      matchedSnapshots: [],
      matchedHandoffs: [],
      runIds: [],
      stageRefs: [],
      artifactRefs: [],
      handoffRefs: [],
      targetServiceRefs: [],
    };
  }

  const proposalSignals = buildCandidateSignals(targetCandidate);
  const proposalRef = toText(proposalId);
  const events = Array.isArray(replayDrilldown?.events) ? replayDrilldown.events : [];
  const snapshots = Array.isArray(replayDrilldown?.snapshots) ? replayDrilldown.snapshots : [];
  const handoffs = Array.isArray(replayDrilldown?.handoff_relationships) ? replayDrilldown.handoff_relationships : [];

  const matchedEvents = events
    .map((item) => ({
      item,
      score: scoreTextBySignals(buildReplayEventText(item), proposalSignals),
    }))
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 4)
    .map((item) => item.item);

  const matchedSnapshots = snapshots
    .map((item) => {
      const directMatch = toText(item?.selected_proposal) === proposalRef ? 10 : 0;
      return {
        item,
        score: directMatch + scoreTextBySignals(buildReplaySnapshotText(item), proposalSignals),
      };
    })
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 4)
    .map((item) => item.item);

  const matchedHandoffs = handoffs
    .map((item) => ({
      item,
      score: scoreTextBySignals(buildReplayHandoffText(item), proposalSignals),
    }))
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 4)
    .map((item) => item.item);

  const runIds = unique(
    [
      ...matchedEvents.map((item) => toText(item?.run_id)),
      ...matchedSnapshots.map((item) => toText(item?.run_id)),
      ...matchedHandoffs.map((item) => toText(item?.run_id)),
    ].filter(Boolean)
  );

  const stageRefs = unique(
    [
      ...matchedEvents.map((item) => toText(item?.stage)),
      ...matchedSnapshots.flatMap((item) => (item?.workflow_trace || []).map((entry) => toText(entry))),
      ...matchedHandoffs.map((item) => toText(item?.downstream_stage || item?.upstream_stage)),
    ].filter(Boolean)
  );

  const artifactRefs = unique(
    [
      ...matchedEvents.flatMap((item) => item?.artifact_lookup_refs || []),
      ...matchedSnapshots.flatMap((item) => item?.artifact_lookup_refs || []),
      ...matchedHandoffs.flatMap((item) => item?.artifact_lookup_refs || []),
    ]
      .map((item) => toText(item))
      .filter(Boolean)
  );

  const handoffRefs = unique(matchedHandoffs.map((item) => toText(item?.relation_ref)).filter(Boolean));
  const targetServiceRefs = unique(
    [
      ...matchedEvents.map((item) => toText(item?.metadata?.target_service_ref)),
      ...matchedHandoffs.flatMap((item) => (item?.target_service_refs || []).map((ref) => toText(ref))),
    ].filter(Boolean)
  );

  return {
    matchedEvents,
    matchedSnapshots,
    matchedHandoffs,
    runIds,
    stageRefs,
    artifactRefs,
    handoffRefs,
    targetServiceRefs,
  };
}

export function buildProposalSupportedEvidence({
  proposalId,
  evidenceItems = [],
  architectCandidates = [],
}) {
  if (!proposalId) return [];
  const targetCandidate = architectCandidates.find((candidate) => (candidate?.proposal_id || "") === proposalId);
  if (!targetCandidate) return [];

  return evidenceItems
    .map((evidenceItem) => {
      const componentHits = (targetCandidate?.components || [])
        .map((component) => ({
          name: component?.name,
          score: getEvidenceMatchScore([component?.name, component?.category].join(" "), evidenceItem),
        }))
        .filter((item) => item.score > 0)
        .sort((left, right) => right.score - left.score)
        .slice(0, 3)
        .map((item) => item.name);

      return {
        chunkId: evidenceItem?.chunk_id || "",
        score: getCandidateSupportScore(targetCandidate, evidenceItem),
        componentHits,
        evidenceItem,
      };
    })
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 6);
}
