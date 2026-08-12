"""Structured context-bus summaries for independent agent windows."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from cipher_genius.api.schemas import ContextProjectionPayload, MemoryCardPayload, MemoryHandoffPayload


class ContextWindowSpec(BaseModel):
    """Compact summary of one agent window on the context bus."""

    agent_id: str
    round_id: str = ""
    window_ref: str = ""
    objective: str = ""
    token_budget_hint: int = 0
    constraint_count: int = 0
    card_count: int = 0
    artifact_ref_count: int = 0
    evidence_ref_count: int = 0
    card_types: list[str] = Field(default_factory=list)
    card_family_counts: dict[str, int] = Field(default_factory=dict)
    dominant_card_family: str = "generic"
    typed_contract_counts: dict[str, int] = Field(default_factory=dict)
    dominant_typed_contract: str = ""
    lineage_refs: list[str] = Field(default_factory=list)
    artifact_lookup_refs: list[str] = Field(default_factory=list)
    evidence_lookup_refs: list[str] = Field(default_factory=list)


class MemoryHandoffSummary(BaseModel):
    """Compact summary of one structured handoff package."""

    handoff_id: str
    from_agent: str
    to_agent: str = ""
    status: str = "ready"
    card_count: int = 0
    artifact_ref_count: int = 0
    evidence_ref_count: int = 0
    has_projection: bool = False
    projection_ref: str = ""
    card_family_counts: dict[str, int] = Field(default_factory=dict)
    dominant_card_family: str = "generic"
    typed_contract_counts: dict[str, int] = Field(default_factory=dict)
    dominant_typed_contract: str = ""
    lineage_refs: list[str] = Field(default_factory=list)
    artifact_lookup_refs: list[str] = Field(default_factory=list)
    evidence_lookup_refs: list[str] = Field(default_factory=list)


class TypedMemoryFamilySummary(BaseModel):
    """Stable typed-memory family summary used by the context bus."""

    family: str
    family_label: str = ""
    card_count: int = 0
    handoff_count: int = 0
    card_types: list[str] = Field(default_factory=list)
    window_refs: list[str] = Field(default_factory=list)
    handoff_refs: list[str] = Field(default_factory=list)


class TypedCardContractSummary(BaseModel):
    """Stable typed-card contract summary used for projection-only replay."""

    contract_ref: str
    card_type: str
    family: str
    family_label: str = ""
    contract_version: str = "v1"
    card_count: int = 0
    handoff_count: int = 0
    window_refs: list[str] = Field(default_factory=list)
    handoff_refs: list[str] = Field(default_factory=list)
    lineage_refs: list[str] = Field(default_factory=list)
    artifact_ref_count: int = 0
    evidence_ref_count: int = 0
    lookup_strategy: str = "card_refs_then_projection_then_handoff_then_replay"
    replay_index_refs: list[str] = Field(default_factory=list)


class ReplaySnapshotCard(BaseModel):
    """Replay-facing snapshot summary emitted by the context bus."""

    snapshot_id: str
    case_id: str
    run_id: str
    summary: str = ""
    projection_refs: list[str] = Field(default_factory=list)
    handoff_refs: list[str] = Field(default_factory=list)
    typed_family_counts: dict[str, int] = Field(default_factory=dict)
    typed_contract_counts: dict[str, int] = Field(default_factory=dict)
    artifact_ref_count: int = 0
    evidence_ref_count: int = 0
    lineage_refs: list[str] = Field(default_factory=list)
    artifact_lookup_refs: list[str] = Field(default_factory=list)
    evidence_lookup_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextBusSummary(BaseModel):
    """Top-level context-bus summary for one run."""

    run_id: str
    case_id: str
    projection_count: int = 0
    handoff_count: int = 0
    windows: list[ContextWindowSpec] = Field(default_factory=list)
    handoffs: list[MemoryHandoffSummary] = Field(default_factory=list)
    typed_families: list[TypedMemoryFamilySummary] = Field(default_factory=list)
    typed_contracts: list[TypedCardContractSummary] = Field(default_factory=list)
    replay_snapshot_card: ReplaySnapshotCard | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class ContextBusBuilder:
    """Build additive context-bus summaries from runtime projections and handoffs."""

    FAMILY_LABELS = {
        "runtime_input": "运行时输入",
        "decision": "决策卡",
        "finding": "发现卡",
        "patch": "修补卡",
        "reflection": "反思卡",
        "evidence": "证据卡",
        "replay_snapshot": "回放快照卡",
        "generic": "通用卡",
    }

    def build(
        self,
        *,
        run_id: str,
        case_id: str,
        projections: dict[str, ContextProjectionPayload | None],
        memory_handoffs: list[MemoryHandoffPayload],
    ) -> ContextBusSummary:
        """Build a stable context-bus summary."""

        windows = [
            self._build_window_spec(projection)
            for projection in projections.values()
            if projection is not None
        ]
        handoffs = [self._build_handoff_summary(item) for item in memory_handoffs]
        typed_families = self._build_typed_family_summaries(windows=windows, handoffs=handoffs)
        typed_contracts = self._build_typed_contract_summaries(
            projections=projections,
            memory_handoffs=memory_handoffs,
        )

        total_artifact_refs = sum(item.artifact_ref_count for item in windows)
        total_evidence_refs = sum(item.evidence_ref_count for item in windows)
        family_counts = {
            item.family: item.card_count
            for item in typed_families
            if item.card_count > 0
        }
        contract_counts = {
            item.contract_ref: item.card_count
            for item in typed_contracts
            if item.card_count > 0
        }
        dominant_family = self._pick_dominant_family(family_counts)
        dominant_contract = self._pick_dominant_key(contract_counts)
        lineage_refs = sorted(
            {
                ref
                for item in windows
                for ref in item.lineage_refs
                if str(ref).strip()
            }
        )[:16]
        artifact_lookup_refs = sorted(
            {
                ref
                for item in windows
                for ref in item.artifact_lookup_refs
                if str(ref).strip()
            }
        )[:16]
        evidence_lookup_refs = sorted(
            {
                ref
                for item in windows
                for ref in item.evidence_lookup_refs
                if str(ref).strip()
            }
        )[:16]
        retry_windows = [item for item in windows if self._is_retry_window(item)]
        retry_handoffs = [item for item in handoffs if self._is_retry_handoff(item)]
        retry_projection_refs = [item.window_ref for item in retry_windows[:8] if item.window_ref]
        retry_handoff_refs = [item.handoff_id for item in retry_handoffs[:8] if item.handoff_id]
        retry_lineage_refs = sorted(
            {
                ref
                for item in retry_windows
                for ref in item.lineage_refs
                if str(ref).strip()
            }
        )[:16]
        retry_typed_contract_refs = sorted(
            {
                item.contract_ref
                for item in typed_contracts
                if any(window_ref in retry_projection_refs for window_ref in item.window_refs)
            }
        )[:16]
        retry_compression_stages = sorted(
            {
                str(card.payload.get("compression_stage") or "").strip()
                for projection in projections.values()
                if projection is not None and self._projection_ref(projection) in retry_projection_refs
                for card in projection.cards
                if str(card.card_type or "").strip() == "retry_context_summary"
                and str(card.payload.get("compression_stage") or "").strip()
            }
        )[:16]
        retry_compression_policies = sorted(
            {
                str(card.payload.get("compression_policy") or "").strip()
                for projection in projections.values()
                if projection is not None and self._projection_ref(projection) in retry_projection_refs
                for card in projection.cards
                if str(card.card_type or "").strip() == "retry_context_summary"
                and str(card.payload.get("compression_policy") or "").strip()
            }
        )[:16]
        retry_retained_refs = sorted(
            {
                str(ref).strip()
                for projection in projections.values()
                if projection is not None and self._projection_ref(projection) in retry_projection_refs
                for card in projection.cards
                if str(card.card_type or "").strip() == "retry_context_summary"
                for ref in list(card.payload.get("retained_refs") or [])
                if str(ref).strip()
            }
        )[:16]
        retry_resume_checkpoint_refs = sorted(
            {
                str(card.payload.get("resume_checkpoint_ref") or "").strip()
                for projection in projections.values()
                if projection is not None and self._projection_ref(projection) in retry_projection_refs
                for card in projection.cards
                if str(card.card_type or "").strip() == "retry_context_summary"
                and str(card.payload.get("resume_checkpoint_ref") or "").strip()
            }
        )[:16]
        retry_resume_input_refs = sorted(
            {
                str(ref).strip()
                for projection in projections.values()
                if projection is not None and self._projection_ref(projection) in retry_projection_refs
                for card in projection.cards
                if str(card.card_type or "").strip() == "retry_context_summary"
                for ref in list((card.payload.get("resume_inputs") or {}).get("retained_refs") or [])
                if str(ref).strip()
            }
        )[:16]
        replay_snapshot_card = ReplaySnapshotCard(
            snapshot_id=f"snapshot-{run_id[:8]}",
            case_id=case_id,
            run_id=run_id,
            summary=(
                f"本轮共构建 {len(windows)} 个独立上下文窗口，"
                f"通过 {len(handoffs)} 个结构化 handoff 传递 {sum(family_counts.values())} 张 typed cards。"
            ),
            projection_refs=[item.window_ref for item in windows[:8] if item.window_ref],
            handoff_refs=[item.handoff_id for item in handoffs[:8]],
            typed_family_counts=family_counts,
            typed_contract_counts=contract_counts,
            artifact_ref_count=total_artifact_refs,
            evidence_ref_count=total_evidence_refs,
            lineage_refs=lineage_refs,
            artifact_lookup_refs=artifact_lookup_refs,
            evidence_lookup_refs=evidence_lookup_refs,
            metadata={
                "window_agents": [item.agent_id for item in windows[:8]],
                "dominant_family": dominant_family,
                "typed_family_count": len(typed_families),
                "dominant_contract": dominant_contract,
                "typed_contract_count": len(typed_contracts),
                "retry_window_count": len(retry_windows),
                "retry_handoff_count": len(retry_handoffs),
                "retry_projection_refs": retry_projection_refs,
                "retry_handoff_refs": retry_handoff_refs,
                "retry_lineage_refs": retry_lineage_refs,
                "retry_typed_contract_refs": retry_typed_contract_refs,
                "retry_compression_stages": retry_compression_stages,
                "retry_compression_policies": retry_compression_policies,
                "retry_retained_refs": retry_retained_refs,
                "retry_resume_checkpoint_refs": retry_resume_checkpoint_refs,
                "retry_resume_input_refs": retry_resume_input_refs,
            },
        )
        return ContextBusSummary(
            run_id=run_id,
            case_id=case_id,
            projection_count=len(windows),
            handoff_count=len(handoffs),
            windows=windows,
            handoffs=handoffs,
            typed_families=typed_families,
            typed_contracts=typed_contracts,
            replay_snapshot_card=replay_snapshot_card,
            summary={
                "total_cards": sum(item.card_count for item in windows),
                "total_artifact_refs": total_artifact_refs,
                "total_evidence_refs": total_evidence_refs,
                "typed_family_count": len(typed_families),
                "typed_contract_count": len(typed_contracts),
                "family_counts": family_counts,
                "contract_counts": contract_counts,
                "dominant_family": dominant_family,
                "dominant_contract": dominant_contract,
                "lineage_ref_count": len(lineage_refs),
                "retry_window_count": len(retry_windows),
                "retry_handoff_count": len(retry_handoffs),
                "retry_projection_refs": retry_projection_refs,
                "retry_handoff_refs": retry_handoff_refs,
                "retry_lineage_refs": retry_lineage_refs,
                "retry_typed_contract_refs": retry_typed_contract_refs,
                "retry_compression_stages": retry_compression_stages,
                "retry_compression_policies": retry_compression_policies,
                "retry_retained_refs": retry_retained_refs,
                "retry_resume_checkpoint_refs": retry_resume_checkpoint_refs,
                "retry_resume_input_refs": retry_resume_input_refs,
            },
        )

    def _build_window_spec(self, projection: ContextProjectionPayload) -> ContextWindowSpec:
        family_counts = self._count_card_families(projection.cards)
        contract_counts = self._count_typed_contracts(projection.cards)
        return ContextWindowSpec(
            agent_id=projection.agent_id,
            round_id=str(projection.round_id or ""),
            window_ref=self._projection_ref(projection),
            objective=projection.objective,
            token_budget_hint=projection.token_budget_hint,
            constraint_count=len(projection.constraints),
            card_count=len(projection.cards),
            artifact_ref_count=len(projection.artifact_refs),
            evidence_ref_count=len(projection.evidence_refs),
            card_types=sorted({str(card.card_type) for card in projection.cards})[:8],
            card_family_counts=family_counts,
            dominant_card_family=self._pick_dominant_family(family_counts),
            typed_contract_counts=contract_counts,
            dominant_typed_contract=self._pick_dominant_key(contract_counts),
            lineage_refs=self._collect_lineage_refs(projection.cards),
            artifact_lookup_refs=self._collect_artifact_lookup_refs(
                projection.artifact_refs,
                cards=projection.cards,
            ),
            evidence_lookup_refs=self._collect_evidence_lookup_refs(
                projection.evidence_refs,
                cards=projection.cards,
            ),
        )

    def _build_handoff_summary(self, handoff: MemoryHandoffPayload) -> MemoryHandoffSummary:
        family_counts = self._count_card_families(handoff.cards)
        contract_counts = self._count_typed_contracts(handoff.cards)
        return MemoryHandoffSummary(
            handoff_id=handoff.handoff_id,
            from_agent=handoff.from_agent,
            to_agent=str(handoff.to_agent or ""),
            status=handoff.status,
            card_count=len(handoff.cards),
            artifact_ref_count=len(handoff.artifact_refs),
            evidence_ref_count=len(handoff.evidence_refs),
            has_projection=handoff.projection is not None,
            projection_ref=self._projection_ref(handoff.projection) if handoff.projection is not None else "",
            card_family_counts=family_counts,
            dominant_card_family=self._pick_dominant_family(family_counts),
            typed_contract_counts=contract_counts,
            dominant_typed_contract=self._pick_dominant_key(contract_counts),
            lineage_refs=self._collect_lineage_refs(handoff.cards),
            artifact_lookup_refs=self._collect_artifact_lookup_refs(
                handoff.artifact_refs,
                cards=handoff.cards,
            ),
            evidence_lookup_refs=self._collect_evidence_lookup_refs(
                handoff.evidence_refs,
                cards=handoff.cards,
            ),
        )

    def _build_typed_family_summaries(
        self,
        *,
        windows: list[ContextWindowSpec],
        handoffs: list[MemoryHandoffSummary],
    ) -> list[TypedMemoryFamilySummary]:
        families: dict[str, TypedMemoryFamilySummary] = {}
        for window in windows:
            for family, count in window.card_family_counts.items():
                if count <= 0:
                    continue
                item = families.setdefault(
                    family,
                    TypedMemoryFamilySummary(
                        family=family,
                        family_label=self.FAMILY_LABELS.get(family, family),
                    ),
                )
                item.card_count += count
                if window.window_ref and window.window_ref not in item.window_refs:
                    item.window_refs.append(window.window_ref)
                for card_type in window.card_types:
                    if self._classify_card_family_from_type(card_type) == family and card_type not in item.card_types:
                        item.card_types.append(card_type)

        for handoff in handoffs:
            for family, count in handoff.card_family_counts.items():
                if count <= 0:
                    continue
                item = families.setdefault(
                    family,
                    TypedMemoryFamilySummary(
                        family=family,
                        family_label=self.FAMILY_LABELS.get(family, family),
                    ),
                )
                item.handoff_count += 1
                if handoff.handoff_id not in item.handoff_refs:
                    item.handoff_refs.append(handoff.handoff_id)

        return sorted(
            families.values(),
            key=lambda item: (-item.card_count, -item.handoff_count, item.family),
        )

    def _build_typed_contract_summaries(
        self,
        *,
        projections: dict[str, ContextProjectionPayload | None],
        memory_handoffs: list[MemoryHandoffPayload],
    ) -> list[TypedCardContractSummary]:
        contracts: dict[str, TypedCardContractSummary] = {}
        contract_artifact_refs: dict[str, set[str]] = {}
        contract_evidence_refs: dict[str, set[str]] = {}
        contract_lineage_refs: dict[str, set[str]] = {}
        contract_replay_refs: dict[str, set[str]] = {}

        for projection in projections.values():
            if projection is None:
                continue
            window_ref = self._projection_ref(projection)
            fallback_artifact_refs = list(projection.artifact_refs or [])
            fallback_evidence_refs = list(projection.evidence_refs or [])
            for card in projection.cards:
                contract_ref = self._build_typed_contract_ref(card)
                item = contracts.setdefault(
                    contract_ref,
                    TypedCardContractSummary(
                        contract_ref=contract_ref,
                        card_type=str(card.card_type or ""),
                        family=self._classify_card_family(card),
                        family_label=self.FAMILY_LABELS.get(self._classify_card_family(card), self._classify_card_family(card)),
                        contract_version=self._extract_card_contract_version(card),
                    ),
                )
                item.card_count += 1
                if window_ref and window_ref not in item.window_refs:
                    item.window_refs.append(window_ref)
                self._merge_contract_lookup_refs(
                    contract_artifact_refs,
                    contract_evidence_refs,
                    contract_lineage_refs,
                    contract_replay_refs,
                    contract_ref=contract_ref,
                    card=card,
                    fallback_artifact_refs=fallback_artifact_refs,
                    fallback_evidence_refs=fallback_evidence_refs,
                )

        for handoff in memory_handoffs:
            fallback_artifact_refs = list(handoff.artifact_refs or [])
            fallback_evidence_refs = list(handoff.evidence_refs or [])
            for card in handoff.cards:
                contract_ref = self._build_typed_contract_ref(card)
                item = contracts.setdefault(
                    contract_ref,
                    TypedCardContractSummary(
                        contract_ref=contract_ref,
                        card_type=str(card.card_type or ""),
                        family=self._classify_card_family(card),
                        family_label=self.FAMILY_LABELS.get(self._classify_card_family(card), self._classify_card_family(card)),
                        contract_version=self._extract_card_contract_version(card),
                    ),
                )
                if handoff.handoff_id and handoff.handoff_id not in item.handoff_refs:
                    item.handoff_refs.append(handoff.handoff_id)
                self._merge_contract_lookup_refs(
                    contract_artifact_refs,
                    contract_evidence_refs,
                    contract_lineage_refs,
                    contract_replay_refs,
                    contract_ref=contract_ref,
                    card=card,
                    fallback_artifact_refs=fallback_artifact_refs,
                    fallback_evidence_refs=fallback_evidence_refs,
                )

        for contract_ref, item in contracts.items():
            item.handoff_count = len(item.handoff_refs)
            item.lineage_refs = sorted(contract_lineage_refs.get(contract_ref, set()))[:12]
            item.replay_index_refs = sorted(contract_replay_refs.get(contract_ref, set()))[:12]
            item.artifact_ref_count = len(contract_artifact_refs.get(contract_ref, set()))
            item.evidence_ref_count = len(contract_evidence_refs.get(contract_ref, set()))

        return sorted(
            contracts.values(),
            key=lambda item: (-item.card_count, -item.handoff_count, item.contract_ref),
        )

    def _count_card_families(self, cards: list[MemoryCardPayload]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for card in cards:
            family = self._classify_card_family(card)
            counts[family] = counts.get(family, 0) + 1
        return counts

    def _count_typed_contracts(self, cards: list[MemoryCardPayload]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for card in cards:
            contract_ref = self._build_typed_contract_ref(card)
            counts[contract_ref] = counts.get(contract_ref, 0) + 1
        return counts

    def _classify_card_family(self, card: MemoryCardPayload) -> str:
        explicit_family = str(card.card_family or "").strip()
        if explicit_family:
            return explicit_family
        payload_family = str((card.payload or {}).get("card_family") or "").strip()
        if payload_family:
            return payload_family
        return self._classify_card_family_from_type(card.card_type)

    def _classify_card_family_from_type(self, card_type: str) -> str:
        value = str(card_type or "").strip().lower()
        if not value:
            return "generic"
        if value.endswith("_runtime_input"):
            return "runtime_input"
        if value in {"attack_decision", "proposal_decision", "delivery_decision"} or "decision" in value:
            return "decision"
        if value in {"patch_execution", "patch_artifact_summary", "patch_spec"} or value.startswith("patch_"):
            return "patch"
        if value in {"reflection_memory", "reflection", "regression_summary"} or "reflection" in value:
            return "reflection"
        if "evidence" in value:
            return "evidence"
        if value in {
            "vulnerability_verdict",
            "regression_verdict_input",
            "attack_result_summary",
            "attack_artifact_summary",
            "audit_finding",
        } or "verdict" in value or "finding" in value:
            return "finding"
        if value == "replay_snapshot":
            return "replay_snapshot"
        return "generic"

    def _build_typed_contract_ref(self, card: MemoryCardPayload) -> str:
        payload = dict(card.payload or {})
        explicit = str(payload.get("typed_contract_ref") or "").strip()
        if explicit:
            return explicit
        typed_contract = dict(payload.get("typed_contract") or {})
        if str(typed_contract.get("contract_ref") or "").strip():
            return str(typed_contract.get("contract_ref") or "").strip()
        family = self._classify_card_family(card)
        contract_version = self._extract_card_contract_version(card)
        return f"{family}:{card.card_type}:{contract_version}"

    def _extract_card_contract_version(self, card: MemoryCardPayload) -> str:
        payload = dict(card.payload or {})
        typed_contract = dict(payload.get("typed_contract") or {})
        return str(
            typed_contract.get("contract_version")
            or payload.get("card_contract_version")
            or card.card_contract_version
            or "v1"
        ).strip() or "v1"

    def _projection_ref(self, projection: ContextProjectionPayload | None) -> str:
        if projection is None:
            return ""
        round_id = str(projection.round_id or "main")
        return f"{projection.agent_id}:{round_id}"

    def _is_retry_window(self, window: ContextWindowSpec) -> bool:
        """Return whether a context window belongs to the same-run retry subchain."""

        window_ref = str(window.window_ref or "")
        round_id = str(window.round_id or "")
        return (
            window_ref.endswith(":attack-plan-r2")
            or window_ref.endswith(":vulnerability-r2")
            or window_ref.endswith(":expert-gate-r2")
            or "retry" in round_id
        )

    def _is_retry_handoff(self, handoff: MemoryHandoffSummary) -> bool:
        """Return whether a handoff belongs to the same-run retry subchain."""

        handoff_id = str(handoff.handoff_id or "")
        projection_ref = str(handoff.projection_ref or "")
        return "retry" in handoff_id or projection_ref.endswith(
            (":attack-plan-r2", ":vulnerability-r2", ":expert-gate-r2")
        )

    def _collect_artifact_lookup_refs(
        self,
        artifact_refs: list[Any],
        *,
        cards: list[MemoryCardPayload] | None = None,
    ) -> list[str]:
        refs = {
            self._build_artifact_lookup_ref(ref)
            for ref in list(artifact_refs or [])
            if self._build_artifact_lookup_ref(ref)
        }
        for card in cards or []:
            refs.update(
                {
                    self._build_artifact_lookup_ref(ref)
                    for ref in list(card.artifact_refs or [])
                    if self._build_artifact_lookup_ref(ref)
                }
            )
        return sorted(refs)[:12]

    def _collect_evidence_lookup_refs(
        self,
        evidence_refs: list[Any],
        *,
        cards: list[MemoryCardPayload] | None = None,
    ) -> list[str]:
        refs = {
            self._build_evidence_lookup_ref(ref)
            for ref in list(evidence_refs or [])
            if self._build_evidence_lookup_ref(ref)
        }
        for card in cards or []:
            refs.update(
                {
                    self._build_evidence_lookup_ref(ref)
                    for ref in list(card.evidence_refs or [])
                    if self._build_evidence_lookup_ref(ref)
                }
            )
        return sorted(refs)[:12]

    def _merge_contract_lookup_refs(
        self,
        contract_artifact_refs: dict[str, set[str]],
        contract_evidence_refs: dict[str, set[str]],
        contract_lineage_refs: dict[str, set[str]],
        contract_replay_refs: dict[str, set[str]],
        *,
        contract_ref: str,
        card: MemoryCardPayload,
        fallback_artifact_refs: list[Any],
        fallback_evidence_refs: list[Any],
    ) -> None:
        artifact_refs = list(card.artifact_refs or []) or list(fallback_artifact_refs or [])
        evidence_refs = list(card.evidence_refs or []) or list(fallback_evidence_refs or [])
        for ref in artifact_refs:
            lookup_ref = self._build_artifact_lookup_ref(ref)
            if lookup_ref:
                contract_artifact_refs.setdefault(contract_ref, set()).add(lookup_ref)
        for ref in evidence_refs:
            lookup_ref = self._build_evidence_lookup_ref(ref)
            if lookup_ref:
                contract_evidence_refs.setdefault(contract_ref, set()).add(lookup_ref)
        lineage_ref = self._build_lineage_ref(card)
        if lineage_ref:
            contract_lineage_refs.setdefault(contract_ref, set()).add(lineage_ref)
        replay_index_ref = self._extract_replay_index_ref(card)
        if replay_index_ref:
            contract_replay_refs.setdefault(contract_ref, set()).add(replay_index_ref)

    def _build_artifact_lookup_ref(self, ref: Any) -> str:
        artifact_id = str(getattr(ref, "artifact_id", "") or "").strip()
        artifact_type = str(getattr(ref, "artifact_type", "") or "").strip()
        if not artifact_id:
            return ""
        return f"{artifact_type or 'generic'}:{artifact_id}"

    def _build_evidence_lookup_ref(self, ref: Any) -> str:
        doc_id = str(getattr(ref, "doc_id", "") or "").strip()
        chunk_id = str(getattr(ref, "chunk_id", "") or "").strip()
        if not doc_id or not chunk_id:
            return ""
        return f"{doc_id}:{chunk_id}"

    def _extract_replay_index_ref(self, card: MemoryCardPayload) -> str:
        explicit_ref = str(card.replay_index_ref or "").strip()
        if explicit_ref:
            return explicit_ref
        payload = dict(card.payload or {})
        return str(payload.get("replay_index_ref") or "").strip()

    def _collect_lineage_refs(self, cards: list[MemoryCardPayload]) -> list[str]:
        refs = {
            self._build_lineage_ref(card)
            for card in cards
            if self._build_lineage_ref(card)
        }
        return sorted(refs)[:12]

    def _build_lineage_ref(self, card: MemoryCardPayload) -> str:
        explicit_ref = str(card.lineage_ref or "").strip()
        if explicit_ref:
            return explicit_ref
        case_id = str(card.case_id or "").strip()
        run_id = str(card.run_id or "").strip()
        round_id = str(card.round_id or "").strip()
        version_id = str(card.version_id or "").strip()
        if not case_id:
            return ""
        parts = [case_id]
        if run_id:
            parts.append(run_id)
        if round_id:
            parts.append(round_id)
        if version_id:
            parts.append(version_id)
        return ":".join(parts)

    def _pick_dominant_family(self, counts: dict[str, int]) -> str:
        if not counts:
            return "generic"
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]

    def _pick_dominant_key(self, counts: dict[str, int]) -> str:
        if not counts:
            return ""
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
