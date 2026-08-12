import { useEffect, useMemo, useState } from "react";
import {
  buildCandidateEvidenceLinkage,
  buildDeliveryFragmentCatalog,
  buildDeliveryProposalLinkage,
  buildEvidenceLinkage,
  buildProposalDeliveryLinkage,
  buildProposalReplayLinkage,
  normalizeEvidenceItems,
} from "./evidenceHelpers";

function uniqueStrings(items = []) {
  return [...new Set((items || []).filter(Boolean).map((item) => String(item).trim()).filter(Boolean))];
}

function normalizeRef(value) {
  return String(value || "").trim();
}

function uniqueBy(items = [], keyBuilder = (item, index) => index) {
  const seen = new Set();
  return (items || []).filter((item, index) => {
    const key = keyBuilder(item, index);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function normalizeRefList(...values) {
  return uniqueStrings(
    values.flatMap((value) => {
      if (Array.isArray(value)) return value;
      const normalized = normalizeRef(value);
      return normalized ? [normalized] : [];
    })
  );
}

function extractReplayArtifactRefs(record = {}) {
  return normalizeRefList(
    record?.artifact_lookup_refs,
    record?.metadata?.artifact_lookup_refs,
    record?.metadata?.artifact_lookup_ref
  );
}

function extractReplayEvidenceRefs(record = {}) {
  return normalizeRefList(
    record?.evidence_lookup_refs,
    record?.metadata?.evidence_lookup_refs,
    record?.metadata?.evidence_lookup_ref
  );
}

function buildReplayEvidenceContext({ evidenceItem, replayDrilldown, replayScope }) {
  const evidenceRef = normalizeRef(evidenceItem?.chunk_id);
  if (!evidenceRef) {
    return {
      evidenceRef: "",
      replayFocused: false,
      matchedEvents: [],
      matchedSnapshots: [],
      matchedHandoffs: [],
      artifactRefs: [],
      runIds: [],
      stageRefs: [],
    };
  }

  const replayFocused = normalizeRef(replayScope?.evidenceLookupRef) === evidenceRef;
  const events = Array.isArray(replayDrilldown?.events) ? replayDrilldown.events : [];
  const snapshots = Array.isArray(replayDrilldown?.snapshots) ? replayDrilldown.snapshots : [];
  const handoffs = Array.isArray(replayDrilldown?.handoff_relationships) ? replayDrilldown.handoff_relationships : [];

  const matchedEvents = events.filter((item) => extractReplayEvidenceRefs(item).includes(evidenceRef));
  const matchedSnapshots = snapshots.filter((item) => extractReplayEvidenceRefs(item).includes(evidenceRef));
  const matchedHandoffs = handoffs.filter((item) => normalizeRefList(item?.evidence_lookup_refs).includes(evidenceRef));

  const artifactRefs = uniqueStrings([
    ...matchedEvents.flatMap((item) => extractReplayArtifactRefs(item)),
    ...matchedSnapshots.flatMap((item) => extractReplayArtifactRefs(item)),
    ...matchedHandoffs.flatMap((item) => normalizeRefList(item?.artifact_lookup_refs)),
  ]);
  const runIds = uniqueStrings([
    ...matchedEvents.map((item) => item?.run_id),
    ...matchedSnapshots.map((item) => item?.run_id),
  ]);
  const stageRefs = uniqueStrings([
    ...matchedEvents.map((item) => item?.stage),
    ...matchedHandoffs.flatMap((item) => [item?.upstream_stage, item?.downstream_stage]),
    ...matchedSnapshots.flatMap((item) => item?.workflow_trace || []),
  ]);

  return {
    evidenceRef,
    replayFocused,
    matchedEvents: uniqueBy(matchedEvents, (item) => item?.event_id || item?.created_at).slice(0, 4),
    matchedSnapshots: uniqueBy(matchedSnapshots, (item) => item?.snapshot_id || item?.created_at).slice(0, 3),
    matchedHandoffs: uniqueBy(matchedHandoffs, (item) => item?.relation_ref || item?.handoff_projection_ref).slice(0, 3),
    artifactRefs: artifactRefs.slice(0, 6),
    runIds: runIds.slice(0, 4),
    stageRefs: stageRefs.slice(0, 6),
  };
}

export default function useReportsEvidenceState({
  evidencePack,
  selectedEvidenceChunkId,
  setSelectedEvidenceChunkId,
  selectedDeliveryFragmentId,
  setSelectedDeliveryFragmentId,
  replayScope,
  replayDrilldown,
  auditorRounds,
  auditRecommendations,
  delivery,
  result,
  finalScheme,
  architectCandidates,
  selectedProposalId,
  setSelectedProposalId,
  setReplayScope,
}) {
  const evidenceItems = useMemo(() => normalizeEvidenceItems(evidencePack), [evidencePack]);
  const [localSelectedDeliveryFragmentId, setLocalSelectedDeliveryFragmentId] = useState("");
  const activeSelectedDeliveryFragmentId = normalizeRef(
    typeof selectedDeliveryFragmentId === "string"
      ? selectedDeliveryFragmentId
      : localSelectedDeliveryFragmentId
  );
  const updateSelectedDeliveryFragmentId =
    typeof setSelectedDeliveryFragmentId === "function"
      ? setSelectedDeliveryFragmentId
      : setLocalSelectedDeliveryFragmentId;

  useEffect(() => {
    if (evidenceItems.length === 0) {
      setSelectedEvidenceChunkId?.("");
      return;
    }
    if (!evidenceItems.some((item) => item?.chunk_id === selectedEvidenceChunkId)) {
      setSelectedEvidenceChunkId?.(evidenceItems[0]?.chunk_id || "");
    }
  }, [evidenceItems, selectedEvidenceChunkId, setSelectedEvidenceChunkId]);

  const selectedEvidence = useMemo(() => {
    return evidenceItems.find((item) => item?.chunk_id === selectedEvidenceChunkId) || null;
  }, [evidenceItems, selectedEvidenceChunkId]);

  useEffect(() => {
    const replayEvidenceRef = normalizeRef(replayScope?.evidenceLookupRef);
    if (!replayEvidenceRef) return;
    if (selectedEvidenceChunkId === replayEvidenceRef) return;
    if (evidenceItems.some((item) => item?.chunk_id === replayEvidenceRef)) {
      setSelectedEvidenceChunkId?.(replayEvidenceRef);
    }
  }, [evidenceItems, replayScope?.evidenceLookupRef, selectedEvidenceChunkId, setSelectedEvidenceChunkId]);

  const linkedEvidence = useMemo(() => {
    return buildEvidenceLinkage({
      evidenceItem: selectedEvidence,
      auditorRounds,
      auditRecommendations,
      delivery,
      result,
      finalScheme,
    });
  }, [selectedEvidence, auditorRounds, auditRecommendations, delivery, result, finalScheme]);

  const candidateLinks = useMemo(() => {
    return buildCandidateEvidenceLinkage({
      evidenceItem: selectedEvidence,
      architectCandidates,
      delivery,
    });
  }, [selectedEvidence, architectCandidates, delivery]);

  const deliveryFragments = useMemo(() => {
    return buildDeliveryFragmentCatalog({
      delivery,
      result,
      finalScheme,
    });
  }, [delivery, result, finalScheme]);

  const proposalDeliveryLinks = useMemo(() => {
    return buildProposalDeliveryLinkage({
      proposalId: selectedProposalId,
      architectCandidates,
      deliveryFragments,
    });
  }, [selectedProposalId, architectCandidates, deliveryFragments]);

  const proposalReplayContext = useMemo(() => {
    return buildProposalReplayLinkage({
      proposalId: selectedProposalId,
      architectCandidates,
      replayDrilldown,
    });
  }, [selectedProposalId, architectCandidates, replayDrilldown]);

  const deliveryProposalMap = useMemo(() => {
    return Object.fromEntries(
      deliveryFragments.map((item) => [
        item.fragmentId,
        buildDeliveryProposalLinkage({
          fragmentId: item.fragmentId,
          architectCandidates,
          deliveryFragments,
          delivery,
        }),
      ])
    );
  }, [deliveryFragments, architectCandidates, delivery]);

  const replayEvidenceContext = useMemo(() => {
    return buildReplayEvidenceContext({
      evidenceItem: selectedEvidence,
      replayDrilldown,
      replayScope,
    });
  }, [selectedEvidence, replayDrilldown, replayScope]);

  function focusReplayFromEvent(item) {
    if (typeof setReplayScope !== "function" || !item) return;
    const artifactLookupRef = extractReplayArtifactRefs(item)[0] || "";
    const evidenceLookupRef = extractReplayEvidenceRefs(item)[0] || normalizeRef(selectedEvidence?.chunk_id);
    setReplayScope((prev) => ({
      ...(prev || {}),
      runId: normalizeRef(item?.run_id),
      stageRef: normalizeRef(item?.stage),
      projectionRef: normalizeRef(item?.metadata?.projection_ref),
      handoffRef: normalizeRef(item?.metadata?.handoff_ref),
      targetServiceRef: normalizeRef(item?.metadata?.target_service_ref) || prev?.targetServiceRef || "",
      artifactLookupRef,
      evidenceLookupRef,
    }));
  }

  function focusReplayFromSnapshot(item) {
    if (typeof setReplayScope !== "function" || !item) return;
    const artifactLookupRef = normalizeRef(item?.artifact_lookup_refs?.[0]);
    const evidenceLookupRef = normalizeRef(item?.evidence_lookup_refs?.[0]) || normalizeRef(selectedEvidence?.chunk_id);
    setReplayScope((prev) => ({
      ...(prev || {}),
      runId: normalizeRef(item?.run_id),
      stageRef: normalizeRef(item?.workflow_trace?.[0] || item?.metadata?.stage),
      projectionRef: normalizeRef(item?.projection_refs?.[0]),
      handoffRef: normalizeRef(item?.handoff_refs?.[0]),
      targetServiceRef: prev?.targetServiceRef || "",
      artifactLookupRef,
      evidenceLookupRef,
    }));
  }

  function focusReplayFromHandoff(item) {
    if (typeof setReplayScope !== "function" || !item) return;
    const artifactLookupRef = normalizeRef(item?.artifact_lookup_refs?.[0]);
    const evidenceLookupRef = normalizeRef(item?.evidence_lookup_refs?.[0]) || normalizeRef(selectedEvidence?.chunk_id);
    setReplayScope((prev) => ({
      ...(prev || {}),
      runId: normalizeRef(item?.run_id) || prev?.runId || "",
      stageRef: normalizeRef(item?.downstream_stage || item?.upstream_stage) || prev?.stageRef || "",
      projectionRef: normalizeRef(item?.handoff_projection_ref || item?.linked_projection_refs?.[0]),
      handoffRef: normalizeRef(item?.relation_ref),
      targetServiceRef: normalizeRef(item?.target_service_refs?.[0]) || prev?.targetServiceRef || "",
      artifactLookupRef,
      evidenceLookupRef,
    }));
  }

  function focusReplayFromRun(runId) {
    if (typeof setReplayScope !== "function") return;
    const normalizedRunId = normalizeRef(runId);
    if (!normalizedRunId) return;
    setReplayScope((prev) => ({
      ...(prev || {}),
      runId: prev?.runId === normalizedRunId ? "" : normalizedRunId,
      stageRef: "",
      artifactLookupRef: "",
      evidenceLookupRef: normalizeRef(selectedEvidence?.chunk_id),
    }));
  }

  function focusReplayFromStage(stageRef) {
    if (typeof setReplayScope !== "function") return;
    const normalizedStageRef = normalizeRef(stageRef);
    if (!normalizedStageRef) return;
    setReplayScope((prev) => ({
      ...(prev || {}),
      stageRef: prev?.stageRef === normalizedStageRef ? "" : normalizedStageRef,
      artifactLookupRef: "",
      evidenceLookupRef: normalizeRef(selectedEvidence?.chunk_id),
    }));
  }

  function focusReplayFromArtifact(artifactRef) {
    if (typeof setReplayScope !== "function") return;
    const normalizedArtifactRef = normalizeRef(artifactRef);
    if (!normalizedArtifactRef) return;
    setReplayScope((prev) => ({
      ...(prev || {}),
      artifactLookupRef: prev?.artifactLookupRef === normalizedArtifactRef ? "" : normalizedArtifactRef,
      evidenceLookupRef: normalizeRef(selectedEvidence?.chunk_id),
    }));
  }

  function focusDeliveryFragment(item) {
    const fragmentId = normalizeRef(item?.fragmentId);
    if (!fragmentId) return;
    updateSelectedDeliveryFragmentId((prev) => (normalizeRef(prev) === fragmentId ? "" : fragmentId));
  }

  function selectEvidence(item) {
    const chunkId = item?.chunk_id || "";
    setSelectedEvidenceChunkId?.(chunkId);
    setReplayScope?.((prev) => ({
      ...(prev || {}),
      runId: "",
      stageRef: "",
      projectionRef: "",
      handoffRef: "",
      artifactLookupRef: "",
      evidenceLookupRef: prev?.evidenceLookupRef === chunkId ? "" : chunkId,
    }));
  }

  useEffect(() => {
    if (candidateLinks.length === 0) return;
    if (!selectedProposalId || !candidateLinks.some((item) => item.proposalId === selectedProposalId)) {
      setSelectedProposalId?.(candidateLinks[0]?.proposalId || "");
    }
  }, [candidateLinks, selectedProposalId, setSelectedProposalId]);

  useEffect(() => {
    if (!deliveryFragments.some((item) => item.fragmentId === activeSelectedDeliveryFragmentId)) {
      updateSelectedDeliveryFragmentId("");
    }
  }, [deliveryFragments, activeSelectedDeliveryFragmentId, updateSelectedDeliveryFragmentId]);

  useEffect(() => {
    if (!selectedProposalId || proposalDeliveryLinks.length === 0) return;
    if (proposalDeliveryLinks.some((item) => item.fragmentId === activeSelectedDeliveryFragmentId)) return;
    updateSelectedDeliveryFragmentId(proposalDeliveryLinks[0]?.fragmentId || "");
  }, [selectedProposalId, proposalDeliveryLinks, activeSelectedDeliveryFragmentId, updateSelectedDeliveryFragmentId]);

  return {
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
  };
}
