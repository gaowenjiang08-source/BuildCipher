"""Enterprise retrieval service with Qdrant-first fallback behavior."""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml
from qdrant_client import QdrantClient
from qdrant_client import models as qdrant_models

from cipher_genius.api.schemas import (
    EvidenceItemPayload,
    EvidencePackPayload,
    TargetServiceSpecPayload,
)
from cipher_genius.ingestion.models import KnowledgeChunk
from cipher_genius.retrieval.qdrant_store import QdrantKnowledgeStore
from cipher_genius.utils.config import get_settings
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)
INGESTED_KNOWLEDGE_DIR_ENV = "CIPHER_GENIUS_INGESTED_KNOWLEDGE_DIR"

_CHINESE_KEYWORDS = [
    "中国",
    "建筑",
    "施工",
    "工地",
    "BIM",
    "IFC",
    "工程验收",
    "图纸",
    "竣工模型",
    "合规",
    "审计",
    "静态加密",
    "传输加密",
    "密钥托管",
    "密钥轮换",
    "后量子",
    "国产化",
    "最小权限",
    "证据链",
]
_CLAUSE_CODE_PATTERN = re.compile(r"\b\d+(?:\.\d+){0,6}\b")


class KnowledgeRetrievalService:
    """Build and query enterprise knowledge cards."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.project_root = Path(__file__).resolve().parents[3]
        self._documents = self._load_documents()
        self._qdrant_client: Optional[QdrantClient] = None
        self._qdrant_checked = False
        self._qdrant_seeded = False
        self._semantic_embedder: Any | None = None
        self._document_embeddings: dict[str, list[float]] = {}

    def retrieve(
        self,
        requirement_text: str,
        structured_spec: Optional[dict[str, Any]] = None,
        top_k: int = 6,
    ) -> EvidencePackPayload:
        structured_spec = structured_spec or {}
        filters = self._build_filters(requirement_text, structured_spec)
        documents, backend = self._get_candidate_documents(filters)
        ranked = self._rank_documents(requirement_text, documents, top_k=top_k)

        return EvidencePackPayload(
            query=requirement_text,
            backend=backend,
            retrieval_mode="keyword+semantic" if self._semantic_enabled() else "keyword",
            applied_filters=filters,
            items=[self._to_payload(item, score) for item, score in ranked],
        )

    def retrieve_attack_planning_evidence(
        self,
        *,
        requirement_text: str,
        target_service: TargetServiceSpecPayload,
        structured_spec: Optional[dict[str, Any]] = None,
        planning_mode: str = "baseline",
        prior_findings: Optional[list[str]] = None,
        regression_focus: Optional[list[str]] = None,
        top_k: int = 4,
    ) -> EvidencePackPayload:
        """Retrieve planner-scoped evidence for the attack planning window."""

        structured_spec = dict(structured_spec or {})
        structured_spec["doc_types"] = list(
            structured_spec.get("doc_types")
            or ["standard", "policy", "template", "case", "attack_lesson"]
        )
        query = self._build_attack_planning_query(
            requirement_text=requirement_text,
            target_service=target_service,
            planning_mode=planning_mode,
            prior_findings=prior_findings or [],
            regression_focus=regression_focus or [],
        )
        evidence_pack = self.retrieve(
            query,
            structured_spec=structured_spec,
            top_k=top_k,
        )
        fallback_mode = "planner_specific"
        if not evidence_pack.items:
            fallback_structured_spec = dict(structured_spec)
            fallback_structured_spec["doc_types"] = [
                "standard",
                "policy",
                "component",
                "template",
                "case",
                "attack_lesson",
            ]
            evidence_pack = self.retrieve(
                requirement_text or query,
                structured_spec=fallback_structured_spec,
                top_k=top_k,
            )
            fallback_mode = "global_fallback"
        applied_filters = dict(evidence_pack.applied_filters or {})
        applied_filters.update(
            {
                "planner_mode": planning_mode,
                "target_template_id": target_service.template_id,
                "attack_surface_kind": target_service.attack_surface_kind,
                "service_kind": target_service.service_kind,
                "planner_retrieval_fallback": fallback_mode,
            }
        )
        return evidence_pack.model_copy(
            update={
                "query": query,
                "applied_filters": applied_filters,
            }
        )

    def _build_attack_planning_query(
        self,
        *,
        requirement_text: str,
        target_service: TargetServiceSpecPayload,
        planning_mode: str,
        prior_findings: list[str],
        regression_focus: list[str],
    ) -> str:
        """Build a retrieval query tailored to the planner's target service and mode."""

        query_parts = [
            requirement_text.strip(),
            f"target template: {target_service.template_id}",
            f"template label: {target_service.template_label}",
            f"service kind: {target_service.service_kind}",
            f"attack surface kind: {target_service.attack_surface_kind}",
        ]
        if target_service.attack_surface:
            query_parts.append("attack surface: " + ", ".join(target_service.attack_surface))
        if target_service.planner_skill_hints:
            query_parts.append("planner skill hints: " + ", ".join(target_service.planner_skill_hints))
        if target_service.planner_retrieval_hints:
            query_parts.append(
                "planner retrieval hints: " + ", ".join(target_service.planner_retrieval_hints)
            )
        if planning_mode == "regression":
            query_parts.append("planning mode: regression validation after patch")
        else:
            query_parts.append("planning mode: baseline attack validation")
        if prior_findings:
            query_parts.append("prior findings: " + "；".join(prior_findings[:4]))
        if regression_focus:
            query_parts.append("regression focus: " + "；".join(regression_focus[:4]))
        return "\n".join(part for part in query_parts if part)

    def _load_documents(self) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        documents.extend(self._load_component_documents())
        documents.extend(self._load_report_template_documents())
        documents.extend(self._load_benchmark_case_documents())
        documents.extend(self._load_attack_paper_documents())
        documents.extend(self._load_ingested_documents())
        return documents

    def _load_component_documents(self) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        base_dir = self.project_root / "data" / "components"
        for yaml_path in base_dir.rglob("*.yaml"):
            try:
                with open(yaml_path, "r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or {}
            except Exception as exc:
                logger.warning("Failed to read component card %s: %s", yaml_path, exc)
                continue

            name = str(data.get("name") or yaml_path.stem).strip()
            description = str(data.get("description") or "").strip()
            implementation_notes = str(data.get("implementation_notes") or "").strip()
            refs = data.get("references") or []
            ref_titles = [str(item.get("title")) for item in refs if isinstance(item, dict) and item.get("title")]
            properties = [str(item) for item in (data.get("properties") or [])]
            use_cases = [str(item) for item in (data.get("use_cases") or [])]
            category = str(data.get("category") or yaml_path.parent.name)

            content_parts = [
                name,
                str(data.get("full_name") or ""),
                description,
                f"类别: {category}",
                f"安全属性: {', '.join(properties)}" if properties else "",
                f"适用场景: {', '.join(use_cases)}" if use_cases else "",
                f"实现说明: {implementation_notes}" if implementation_notes else "",
                f"参考资料: {', '.join(ref_titles)}" if ref_titles else "",
            ]

            docs.append(
                self._build_document(
                    doc_id=f"component::{yaml_path.stem}",
                    chunk_id=f"component::{yaml_path.stem}#overview",
                    doc_type="component",
                    title=name,
                    section="组件能力卡",
                    content="\n".join(item for item in content_parts if item),
                    citation_snippet=implementation_notes or description or name,
                    source_path=yaml_path,
                    metadata={
                        "category": category,
                        "standardized": bool(((data.get("security") or {}).get("standardized"))),
                        "proven_security": bool(((data.get("security") or {}).get("proven_security"))),
                        "security_level": int(((data.get("security") or {}).get("security_level")) or 0),
                        "use_cases": use_cases,
                        "tags": [category, *properties, *use_cases, *ref_titles],
                    },
                )
            )
        return docs

    def _load_report_template_documents(self) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        base_dir = self.project_root / "data" / "report_templates"
        for yaml_path in base_dir.glob("*.yaml"):
            try:
                with open(yaml_path, "r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or {}
            except Exception as exc:
                logger.warning("Failed to read report template %s: %s", yaml_path, exc)
                continue

            template_id = str(data.get("id") or yaml_path.stem)
            template_name = str(data.get("name") or template_id)
            summary = str(data.get("summary") or "").strip()
            scenario = str(data.get("scenario") or "general").strip().lower()
            control_focus = [str(item) for item in (data.get("control_focus") or [])]
            for section in data.get("sections") or []:
                if not isinstance(section, dict):
                    continue
                section_id = str(section.get("id") or "section")
                section_title = str(section.get("title") or section_id)
                section_purpose = str(section.get("purpose") or "").strip()
                content = "\n".join(
                    item
                    for item in [
                        template_name,
                        summary,
                        f"场景: {scenario}",
                        f"章节: {section_title}",
                        f"目的: {section_purpose}",
                        f"控制焦点: {', '.join(control_focus)}" if control_focus else "",
                    ]
                    if item
                )
                docs.append(
                    self._build_document(
                        doc_id=f"template::{template_id}",
                        chunk_id=f"template::{template_id}#{section_id}",
                        doc_type="template",
                        title=template_name,
                        section=section_title,
                        content=content,
                        citation_snippet=section_purpose or summary or section_title,
                        source_path=yaml_path,
                        metadata={
                            "scenario": scenario,
                            "template_id": template_id,
                            "section_id": section_id,
                            "tags": [scenario, *control_focus, section_title],
                        },
                    )
                )
        return docs

    def _load_benchmark_case_documents(self) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        base_dir = self.project_root / "data" / "benchmarks"
        for yaml_path in base_dir.glob("*.yaml"):
            try:
                with open(yaml_path, "r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or {}
            except Exception as exc:
                logger.warning("Failed to read benchmark file %s: %s", yaml_path, exc)
                continue

            for case in data.get("cases") or []:
                if not isinstance(case, dict):
                    continue
                case_id = str(case.get("case_id") or "case")
                scenario = str(case.get("scenario") or "general").strip().lower()
                requirement = str(case.get("requirement") or "").strip()
                expected_skill_id = str(case.get("expected_skill_id") or "").strip()
                expected_template_id = str(case.get("expected_template_id") or "").strip()
                required_sections = [str(item) for item in (case.get("required_sections") or [])]
                attack_focus = self._infer_attack_focus_terms(requirement, required_sections)
                regression_focus = self._infer_regression_focus_terms(requirement, required_sections)
                content = "\n".join(
                    item
                    for item in [
                        requirement,
                        f"场景: {scenario}",
                        f"期望 Skill: {expected_skill_id}" if expected_skill_id else "",
                        f"期望模板: {expected_template_id}" if expected_template_id else "",
                        f"必备章节: {', '.join(required_sections)}" if required_sections else "",
                    ]
                    if item
                )
                docs.append(
                    self._build_document(
                        doc_id=f"case::{case_id}",
                        chunk_id=f"case::{case_id}#summary",
                        doc_type="case",
                        title=case_id,
                        section="基准案例",
                        content=content,
                        citation_snippet=requirement[:180],
                        source_path=yaml_path,
                        metadata={
                            "scenario": scenario,
                            "expected_skill_id": expected_skill_id,
                            "expected_template_id": expected_template_id,
                            "required_sections": required_sections,
                            "tags": [scenario, expected_skill_id, expected_template_id, *required_sections],
                        },
                    )
                )
                lesson_content = "\n".join(
                    item
                    for item in [
                        f"benchmark case: {case_id}",
                        requirement,
                        f"attack focus: {', '.join(attack_focus)}" if attack_focus else "",
                        f"regression focus: {', '.join(regression_focus)}" if regression_focus else "",
                        f"expected skill: {expected_skill_id}" if expected_skill_id else "",
                        f"expected template: {expected_template_id}" if expected_template_id else "",
                        f"required sections: {', '.join(required_sections)}" if required_sections else "",
                    ]
                    if item
                )
                docs.append(
                    self._build_document(
                        doc_id=f"attack_lesson::{case_id}",
                        chunk_id=f"attack_lesson::{case_id}#planner",
                        doc_type="attack_lesson",
                        title=f"{case_id} 攻击经验",
                        section="攻击规划经验",
                        content=lesson_content,
                        citation_snippet=(
                            "围绕 benchmark 案例沉淀的攻击焦点、回归重点与交付约束。"
                        ),
                        source_path=yaml_path,
                        metadata={
                            "scenario": scenario,
                            "expected_skill_id": expected_skill_id,
                            "expected_template_id": expected_template_id,
                            "required_sections": required_sections,
                            "attack_focus": attack_focus,
                            "regression_focus": regression_focus,
                            "lesson_kind": "benchmark_attack_planning",
                            "tags": [
                                scenario,
                                "attack_planning",
                                "benchmark",
                                expected_skill_id,
                                expected_template_id,
                                *attack_focus,
                                *regression_focus,
                            ],
                        },
                    )
                )
        return docs

    def _load_attack_paper_documents(self) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        base_dir = self.project_root / "data" / "attack_lessons"
        if not base_dir.exists():
            return docs

        for yaml_path in base_dir.glob("*.yaml"):
            try:
                with open(yaml_path, "r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or {}
            except Exception as exc:
                logger.warning("Failed to read attack lesson file %s: %s", yaml_path, exc)
                continue

            for lesson in data.get("lessons") or []:
                if not isinstance(lesson, dict):
                    continue

                lesson_id = str(lesson.get("lesson_id") or "paper-lesson").strip()
                lesson_kind = str(lesson.get("lesson_kind") or "paper_attack_planning").strip()
                title = str(lesson.get("title") or lesson_id).strip()
                summary = str(lesson.get("summary") or "").strip()
                source_title = str(lesson.get("source_title") or "").strip()
                source_year = lesson.get("source_year")
                attack_focus = [str(item).strip() for item in (lesson.get("attack_focus") or []) if str(item).strip()]
                regression_focus = [
                    str(item).strip() for item in (lesson.get("regression_focus") or []) if str(item).strip()
                ]
                applicable_templates = [
                    str(item).strip() for item in (lesson.get("applicable_templates") or []) if str(item).strip()
                ]
                attack_surface_kinds = [
                    str(item).strip() for item in (lesson.get("attack_surface_kinds") or []) if str(item).strip()
                ]
                service_kinds = [
                    str(item).strip() for item in (lesson.get("service_kinds") or []) if str(item).strip()
                ]
                planner_skill_hints = [
                    str(item).strip() for item in (lesson.get("planner_skill_hints") or []) if str(item).strip()
                ]
                boundary_conditions = [
                    str(item).strip() for item in (lesson.get("boundary_conditions") or []) if str(item).strip()
                ]
                scenario_value = lesson.get("scenario") or data.get("default_scenario") or ["general"]
                if isinstance(scenario_value, str):
                    scenario = [scenario_value.strip().lower()] if scenario_value.strip() else ["general"]
                else:
                    scenario = [str(item).strip().lower() for item in scenario_value if str(item).strip()] or ["general"]

                extra_tags = [str(item).strip() for item in (lesson.get("tags") or []) if str(item).strip()]
                tags = list(
                    dict.fromkeys(
                        item
                        for item in [
                            *scenario,
                            "attack_planning",
                            "paper",
                            lesson_kind,
                            *attack_focus,
                            *regression_focus,
                            *applicable_templates,
                            *attack_surface_kinds,
                            *service_kinds,
                            *planner_skill_hints,
                            *extra_tags,
                            source_title,
                        ]
                        if item
                    )
                )

                content = "\n".join(
                    item
                    for item in [
                        title,
                        summary,
                        f"source: {source_title}" if source_title else "",
                        f"source year: {source_year}" if source_year else "",
                        f"applicable templates: {', '.join(applicable_templates)}" if applicable_templates else "",
                        f"service kinds: {', '.join(service_kinds)}" if service_kinds else "",
                        f"attack surface kinds: {', '.join(attack_surface_kinds)}" if attack_surface_kinds else "",
                        f"planner skill hints: {', '.join(planner_skill_hints)}" if planner_skill_hints else "",
                        f"attack focus: {', '.join(attack_focus)}" if attack_focus else "",
                        f"regression focus: {', '.join(regression_focus)}" if regression_focus else "",
                        f"boundary conditions: {', '.join(boundary_conditions)}" if boundary_conditions else "",
                    ]
                    if item
                )

                docs.append(
                    self._build_document(
                        doc_id=f"attack_lesson::paper::{lesson_id}",
                        chunk_id=f"attack_lesson::paper::{lesson_id}#planner",
                        doc_type="attack_lesson",
                        title=title,
                        section="攻击论文摘要卡",
                        content=content,
                        citation_snippet=summary or source_title or title,
                        source_path=yaml_path,
                        metadata={
                            "scenario": scenario,
                            "lesson_id": lesson_id,
                            "lesson_kind": lesson_kind,
                            "source_title": source_title,
                            "source_year": source_year,
                            "attack_focus": attack_focus,
                            "regression_focus": regression_focus,
                            "applicable_templates": applicable_templates,
                            "attack_surface_kinds": attack_surface_kinds,
                            "service_kinds": service_kinds,
                            "planner_skill_hints": planner_skill_hints,
                            "boundary_conditions": boundary_conditions,
                            "tags": tags,
                        },
                    )
                )
        return docs

    def _infer_attack_focus_terms(
        self,
        requirement: str,
        required_sections: list[str],
    ) -> list[str]:
        raw = f"{requirement}\n{' '.join(required_sections)}".lower()
        focus: list[str] = []
        if any(token in raw for token in ["audit", "审计", "追踪", "留痕", "part 11", "annex 11"]):
            focus.append("audit trail integrity")
        if any(token in raw for token in ["key", "密钥", "证书", "trust anchor", "证书体系"]):
            focus.append("key isolation boundary")
        if any(token in raw for token in ["share", "共享", "exchange", "跨机构", "对接"]):
            focus.append("data exchange boundary")
        if any(token in raw for token in ["privacy", "隐私", "脱敏", "sensitive", "confidential"]):
            focus.append("privacy leakage boundary")
        if any(token in raw for token in ["archive", "归档", "长期", "csv", "validation"]):
            focus.append("long-term validation path")
        return focus

    def _infer_regression_focus_terms(
        self,
        requirement: str,
        required_sections: list[str],
    ) -> list[str]:
        raw = f"{requirement}\n{' '.join(required_sections)}".lower()
        focus: list[str] = []
        if any(token in raw for token in ["审计", "audit", "留痕", "追踪"]):
            focus.append("audit regression")
        if any(token in raw for token in ["密钥", "key", "证书"]):
            focus.append("key governance regression")
        if any(token in raw for token in ["共享", "exchange", "跨机构", "trust"]):
            focus.append("interface trust regression")
        if any(token in raw for token in ["隐私", "脱敏", "privacy"]):
            focus.append("privacy control regression")
        return focus

    def _load_ingested_documents(self) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        base_dir = self._resolve_ingested_knowledge_dir()
        if base_dir is None or not base_dir.exists():
            return docs

        for jsonl_path in sorted(base_dir.rglob("*.jsonl")):
            try:
                with jsonl_path.open("r", encoding="utf-8") as handle:
                    for line_number, raw_line in enumerate(handle, start=1):
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            chunk = KnowledgeChunk.model_validate(json.loads(line))
                        except Exception as exc:
                            logger.warning(
                                "Failed to parse ingested knowledge chunk %s:%s: %s",
                                jsonl_path,
                                line_number,
                                exc,
                            )
                            continue
                        docs.append(self._document_from_chunk(chunk))
            except Exception as exc:
                logger.warning("Failed to read ingested knowledge file %s: %s", jsonl_path, exc)
        return docs

    def _build_document(
        self,
        *,
        doc_id: str,
        chunk_id: str,
        doc_type: str,
        title: str,
        section: str,
        content: str,
        citation_snippet: str,
        source_path: Path,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return self._with_filter_fields(
            {
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "doc_type": doc_type,
            "title": title,
            "section": section,
            "content": content,
            "citation_snippet": citation_snippet[:240],
            "source_path": str(source_path.relative_to(self.project_root)),
            "source_page": None,
            "metadata": metadata,
            }
        )

    def _document_from_chunk(self, chunk: KnowledgeChunk) -> dict[str, Any]:
        metadata = dict(chunk.metadata or {})
        tags = [str(item) for item in (metadata.get("tags") or []) if item]
        scenario = metadata.get("scenario")
        if isinstance(scenario, str):
            metadata["scenario"] = scenario.strip().lower()
        elif isinstance(scenario, list):
            metadata["scenario"] = [str(item).strip().lower() for item in scenario if item]

        return self._with_filter_fields(
            {
            "doc_id": chunk.doc_id,
            "chunk_id": chunk.chunk_id,
            "doc_type": chunk.doc_type,
            "title": chunk.title,
            "section": chunk.section,
            "content": chunk.content,
            "citation_snippet": chunk.citation_snippet[:240],
            "source_path": self._normalize_source_path(chunk.source_path),
            "source_page": chunk.source_page,
            "metadata": {
                **metadata,
                "tags": tags,
            },
            }
        )

    def _with_filter_fields(self, document: dict[str, Any]) -> dict[str, Any]:
        return QdrantKnowledgeStore.normalize_payload(document)

    def _resolve_ingested_knowledge_dir(self) -> Path | None:
        configured = os.getenv(INGESTED_KNOWLEDGE_DIR_ENV, "").strip()
        if configured:
            return Path(configured)
        return self.project_root / "knowledge" / "processed" / "chunks"

    def _normalize_source_path(self, source_path: str) -> str:
        path = Path(source_path)
        if not path.is_absolute():
            return str(path)
        try:
            return str(path.relative_to(self.project_root))
        except ValueError:
            return str(path)

    def _build_filters(self, requirement_text: str, structured_spec: dict[str, Any]) -> dict[str, Any]:
        raw = f"{requirement_text}\n{structured_spec}".lower()
        scenario = str(structured_spec.get("domain") or "").strip().lower()
        if not scenario:
            if any(token in raw for token in ["建筑", "施工", "工地", "工程验收", "图纸", "bim", "ifc", "openbim", "cde", "construction"]):
                scenario = "construction"
            elif any(token in raw for token in ["金融", "支付", "finance", "payment"]):
                scenario = "finance"
            elif any(token in raw for token in ["物联网", "iot"]):
                scenario = "iot"
            else:
                scenario = "general"

        region = "CN" if re.search(r"[\u4e00-\u9fff]", requirement_text) or "china" in raw or "中国" in raw else None
        compliance = str(structured_spec.get("compliance") or "").strip().upper() or None

        doc_types = [
            str(item).strip()
            for item in (structured_spec.get("doc_types") or ["standard", "policy", "component", "template", "case"])
            if str(item).strip()
        ]

        return {
            "scenario": scenario,
            "region": region,
            "compliance": compliance,
            "doc_types": doc_types,
        }

    def _get_candidate_documents(self, filters: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
        qdrant_docs = self._query_documents_from_qdrant(filters)
        if qdrant_docs:
            return self._apply_filters(qdrant_docs, filters), "qdrant"
        return self._apply_filters(self._documents, filters), "local"

    def _apply_filters(self, documents: Iterable[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        expected_types = set(filters.get("doc_types") or [])
        expected_scenario = str(filters.get("scenario") or "").strip().lower()
        expected_region = str(filters.get("region") or "").strip().upper()
        for doc in documents:
            if expected_types and str(doc.get("doc_type") or "") not in expected_types:
                continue

            metadata = doc.get("metadata") or {}
            doc_scenario = doc.get("scenario_tokens") or metadata.get("scenario")
            if expected_scenario and doc_scenario:
                if isinstance(doc_scenario, list):
                    normalized = {str(item).strip().lower() for item in doc_scenario if item}
                    if expected_scenario not in normalized:
                        continue
                elif str(doc_scenario).strip().lower() != expected_scenario:
                    continue

            doc_region = str(doc.get("region") or metadata.get("region") or "").strip().upper()
            if expected_region and doc_region and doc_region not in {expected_region, "GLOBAL"}:
                continue

            filtered.append(doc)
        return filtered

    def _rank_documents(
        self,
        requirement_text: str,
        documents: list[dict[str, Any]],
        *,
        top_k: int,
    ) -> list[tuple[dict[str, Any], float]]:
        query_tokens = self._extract_query_tokens(requirement_text)
        query_clause_codes = self._extract_clause_codes(requirement_text)
        semantic_query = self._embed_text(requirement_text) if self._semantic_enabled() else None
        scored: list[tuple[dict[str, Any], float]] = []
        for doc in documents:
            keyword_score = self._keyword_score(query_tokens, query_clause_codes, doc)
            semantic_score = 0.0
            if semantic_query is not None:
                semantic_score = self._cosine_similarity(
                    semantic_query,
                    self._document_embedding(doc),
                )
            score = keyword_score * 0.7 + semantic_score * 0.3 if semantic_query is not None else keyword_score
            if score <= 0:
                continue
            scored.append((doc, round(float(score), 4)))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def _keyword_score(
        self,
        query_tokens: set[str],
        query_clause_codes: set[str],
        doc: dict[str, Any],
    ) -> float:
        metadata = doc.get("metadata") or {}
        section_path = self._normalize_section_path(metadata.get("section_path"))
        section_path_text = " ".join(section_path).lower()
        clause_code = str(metadata.get("clause_code") or "").strip().lower()
        haystack = " ".join(
            [
                str(doc.get("title") or ""),
                str(doc.get("section") or ""),
                str(doc.get("content") or ""),
                clause_code,
                section_path_text,
                " ".join(str(item) for item in (metadata.get("tags") or [])),
            ]
        ).lower()
        score = 0.0
        for token in query_tokens:
            if not token:
                continue
            if token in str(doc.get("title") or "").lower():
                score += 3.0
            if token in str(doc.get("section") or "").lower():
                score += 2.0
            if section_path_text and token in section_path_text:
                score += 1.5
            if token in haystack:
                score += 1.0
        if clause_code and query_clause_codes:
            if clause_code in query_clause_codes:
                score += 4.0
            elif any(code in section_path_text for code in query_clause_codes):
                score += 2.0

        if clause_code and section_path and score > 0 and str(doc.get("doc_type") or "") in {"standard", "policy"}:
            # Prefer evidence that can be traced back to a concrete clause when relevance is otherwise comparable.
            score += 0.8
        return score

    def _extract_query_tokens(self, text: str) -> set[str]:
        lowered = text.lower()
        tokens = {item for item in re.findall(r"[a-z0-9_+\-]{2,}", lowered) if len(item) >= 2}
        tokens.update(self._extract_clause_codes(text))
        for token in _CHINESE_KEYWORDS:
            if token in text:
                tokens.add(token.lower())
        return tokens

    def _extract_clause_codes(self, text: str) -> set[str]:
        return {match.group(0).lower() for match in _CLAUSE_CODE_PATTERN.finditer(text)}

    def _normalize_section_path(self, section_path: Any) -> list[str]:
        if isinstance(section_path, list):
            return [str(item).strip() for item in section_path if str(item).strip()]
        if isinstance(section_path, str) and section_path.strip():
            return [section_path.strip()]
        return []

    def _semantic_enabled(self) -> bool:
        return bool(self.settings.skill_router_enable_embeddings)

    def _document_embedding(self, doc: dict[str, Any]) -> list[float]:
        chunk_id = str(doc.get("chunk_id"))
        embedding = self._document_embeddings.get(chunk_id)
        if embedding is not None:
            return embedding
        embedding = self._embed_text(str(doc.get("content") or ""))
        self._document_embeddings[chunk_id] = embedding
        return embedding

    def _embed_text(self, text: str) -> list[float]:
        if not self._semantic_enabled():
            return []
        embedder = self._get_semantic_embedder()
        if embedder is None:
            return []
        vector = embedder.encode(text, show_progress_bar=False, normalize_embeddings=True)
        return [float(item) for item in vector]

    def _get_semantic_embedder(self) -> Any | None:
        if self._semantic_embedder is not None:
            return self._semantic_embedder
        try:
            from sentence_transformers import SentenceTransformer

            self._semantic_embedder = SentenceTransformer(self.settings.skill_router_embedding_model)
        except Exception as exc:
            logger.warning("Semantic retrieval unavailable, fallback to keyword mode: %s", exc)
            self._semantic_embedder = None
        return self._semantic_embedder

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)

    def _to_payload(self, doc: dict[str, Any], score: float) -> EvidenceItemPayload:
        return EvidenceItemPayload(
            doc_id=str(doc.get("doc_id") or ""),
            chunk_id=str(doc.get("chunk_id") or ""),
            doc_type=str(doc.get("doc_type") or ""),
            title=str(doc.get("title") or ""),
            section=str(doc.get("section") or "") or None,
            snippet=str(doc.get("citation_snippet") or doc.get("content") or "")[:240],
            score=round(score, 4),
            source_path=str(doc.get("source_path") or "") or None,
            source_page=doc.get("source_page"),
            metadata=doc.get("metadata") or {},
        )

    def _query_documents_from_qdrant(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        client = self._get_qdrant_client()
        if client is None:
            return []

        self._seed_qdrant(client)
        if not self._qdrant_seeded:
            return []

        try:
            points, _ = client.scroll(
                collection_name=self.settings.qdrant_collection_name,
                limit=max(len(self._documents), 128),
                scroll_filter=self._build_qdrant_filter(filters),
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            logger.warning("Qdrant scroll failed, fallback to local retrieval: %s", exc)
            return []

        documents: list[dict[str, Any]] = []
        for point in points:
            payload = dict(point.payload or {})
            if payload:
                documents.append(payload)
        return documents

    def _build_qdrant_filter(self, filters: dict[str, Any]) -> qdrant_models.Filter | None:
        must_conditions: list[Any] = []
        doc_types = [str(item) for item in (filters.get("doc_types") or []) if item]
        if doc_types:
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key="doc_type",
                    match=qdrant_models.MatchAny(any=doc_types),
                )
            )

        region = str(filters.get("region") or "").strip().upper()
        min_should = None
        if region:
            min_should = qdrant_models.MinShould(
                conditions=[
                    qdrant_models.FieldCondition(
                        key="region",
                        match=qdrant_models.MatchValue(value=region),
                    ),
                    qdrant_models.FieldCondition(
                        key="region",
                        match=qdrant_models.MatchValue(value="GLOBAL"),
                    ),
                ],
                min_count=1,
            )

        if not must_conditions and min_should is None:
            return None
        return qdrant_models.Filter(
            must=must_conditions or None,
            min_should=min_should,
        )

    def _get_qdrant_client(self) -> Optional[QdrantClient]:
        if self._qdrant_checked:
            return self._qdrant_client

        self._qdrant_checked = True
        try:
            client = QdrantClient(
                host=self.settings.qdrant_host,
                port=self.settings.qdrant_port,
                timeout=1.0,
                check_compatibility=False,
            )
            client.get_collections()
            self._qdrant_client = client
        except Exception as exc:
            logger.info("Qdrant unavailable, retrieval will use local fallback: %s", exc)
            self._qdrant_client = None
        return self._qdrant_client

    def _seed_qdrant(self, client: QdrantClient) -> None:
        if self._qdrant_seeded:
            return
        try:
            store = QdrantKnowledgeStore(
                client,
                collection_name=self.settings.qdrant_collection_name,
            )
            store.ensure_collection()
            store.upsert_payloads(self._documents)
            self._qdrant_seeded = True
        except Exception as exc:
            logger.warning("Failed to seed Qdrant collection, fallback to local retrieval: %s", exc)
            self._qdrant_seeded = False
