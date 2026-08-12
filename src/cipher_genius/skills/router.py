"""Skill routing and recommendation logic."""

from __future__ import annotations

import math
import re
from typing import List

from cipher_genius.api.schemas import SkillRouteCandidatePayload, SkillRouteResponse, SkillSummaryPayload
from cipher_genius.skills.registry import SkillManifest, SkillRegistry
from cipher_genius.utils.config import Settings, get_settings
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class SkillRouter:
    """Route requirements to the most suitable skills."""

    def __init__(self, registry: SkillRegistry, settings: Settings | None = None):
        self.registry = registry
        self.settings = settings or get_settings()
        self._semantic_embedder = None
        self._semantic_embedder_error: str | None = None
        self._semantic_skill_text: dict[str, str] = {}
        self._semantic_skill_embeddings: dict[str, list[float]] = {}

    def route(self, requirement: str, max_candidates: int = 3) -> SkillRouteResponse:
        normalized_requirement = self._normalize(requirement)
        skills = [
            skill
            for skill in self.registry.list_all()
            if skill.auto_route_enabled and str(skill.status).lower() == "active"
        ]

        semantic_scores: dict[str, float] = {}
        semantic_available = False
        if self.settings.skill_router_enable_embeddings:
            semantic_scores = self._semantic_score(requirement, skills)
            semantic_available = bool(semantic_scores)

        candidates: List[SkillRouteCandidatePayload] = []

        for skill in skills:
            candidate = self._score_skill(
                skill,
                normalized_requirement,
                semantic_score=semantic_scores.get(skill.id),
                semantic_enabled=semantic_available,
            )
            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(key=lambda item: (-item.score, item.skill.name.lower()))
        trimmed = candidates[:max(1, max_candidates)]
        recommended = trimmed[0].skill if trimmed and trimmed[0].score > 0 else None
        confidence = round(trimmed[0].score / 100, 2) if trimmed else 0.0

        return SkillRouteResponse(
            requirement=requirement,
            routing_version="skill-v2-hybrid-router" if semantic_available else "skill-v2-keyword-router",
            confidence=confidence,
            recommended_skill=recommended,
            candidates=trimmed,
        )

    def _score_skill(
        self,
        skill: SkillManifest,
        requirement: str,
        *,
        semantic_score: float | None = None,
        semantic_enabled: bool = False,
    ) -> SkillRouteCandidatePayload | None:
        matched_keywords: List[str] = []
        raw_score = 0.0

        for keyword in skill.route_keywords:
            normalized_keyword = self._normalize(keyword)
            if normalized_keyword and normalized_keyword in requirement:
                matched_keywords.append(keyword)
                raw_score += 18 if len(normalized_keyword) >= 4 else 12

        for tag in skill.tags:
            normalized_tag = self._normalize(tag)
            if normalized_tag and normalized_tag in requirement:
                if tag not in matched_keywords:
                    matched_keywords.append(tag)
                raw_score += 6

        for token in self._extract_route_tokens(skill):
            if token in requirement:
                raw_score += 2

        priority_bonus = max(0.0, 10 - skill.route_priority * 0.05)
        keyword_score = min(100.0, round(raw_score + priority_bonus, 2))

        had_keyword_signal = bool(matched_keywords) or raw_score > 0
        should_include = had_keyword_signal
        semantic_min = float(self.settings.skill_router_embedding_min_similarity)

        if semantic_enabled and semantic_score is not None and semantic_score >= semantic_min:
            if had_keyword_signal:
                keyword_score = min(
                    100.0,
                    round(
                        keyword_score + (float(self.settings.skill_router_embedding_weight) * semantic_score * 100),
                        2,
                    ),
                )
            else:
                keyword_score = min(100.0, round((semantic_score * 100) + priority_bonus, 2))
            should_include = True

        if not should_include:
            return None

        reasons = [
            f"匹配关键词：{', '.join(matched_keywords[:5])}" if matched_keywords else "命中了上下文路由信号。"
        ]
        if semantic_enabled and semantic_score is not None:
            if (not had_keyword_signal) or semantic_score >= semantic_min:
                reasons.append(
                    f"语义相似度：{semantic_score:.2f}（{self.settings.skill_router_embedding_model}）"
                )
        if skill.target_users:
            reasons.append(f"目标用户：{', '.join(skill.target_users[:3])}")
        if skill.output_focus:
            reasons.append(f"建议重点：{skill.output_focus[0]}")

        return SkillRouteCandidatePayload(
            skill=SkillSummaryPayload(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                version=skill.version,
                status=skill.status,
                category=skill.category,
                execution_mode=skill.execution_mode,
                tags=skill.tags,
                target_users=skill.target_users,
                output_focus=skill.output_focus,
                example_requirement=skill.example_requirement,
                recommended_num_variants=skill.recommended_num_variants,
                recommended_max_audit_rounds=skill.recommended_max_audit_rounds,
                generate_code_default=skill.generate_code_default,
                strict_clarification_default=skill.strict_clarification_default,
            ),
            score=keyword_score,
            matched_keywords=matched_keywords[:8],
            reasons=reasons,
        )

    def _extract_route_tokens(self, skill: SkillManifest) -> List[str]:
        text = " ".join(
            [
                skill.name,
                skill.description,
                skill.category,
                " ".join(skill.tags),
                " ".join(skill.target_users),
                " ".join(skill.output_focus),
                skill.example_requirement,
            ]
        )
        parts = {
            token
            for token in re.split(r"[^0-9a-zA-Z\u4e00-\u9fff\+\-]+", self._normalize(text))
            if len(token) >= 3
        }
        return sorted(parts)

    def _normalize(self, text: str) -> str:
        return str(text or "").strip().lower()

    def _semantic_score(self, requirement: str, skills: List[SkillManifest]) -> dict[str, float]:
        """Compute semantic similarity scores for skills.

        Returns an empty dict when semantic routing is disabled or unavailable.
        """
        embedder = self._get_semantic_embedder()
        if embedder is None:
            return {}

        skill_texts = [self._semantic_document(skill) for skill in skills]
        if not skill_texts:
            return {}

        try:
            req_embedding = embedder.encode(
                [requirement],
                show_progress_bar=False,
                normalize_embeddings=True,
            )[0]
        except TypeError:
            req_embedding = embedder.encode([requirement], show_progress_bar=False)[0]
            req_embedding = self._l2_normalize(req_embedding)
        except Exception as exc:
            logger.warning("Semantic routing disabled for this request (encode requirement failed): %s", exc)
            return {}

        # Cache skill embeddings to avoid recomputing across calls.
        missing_texts: list[str] = []
        missing_ids: list[str] = []
        for skill, text in zip(skills, skill_texts):
            cached_text = self._semantic_skill_text.get(skill.id)
            if cached_text == text and skill.id in self._semantic_skill_embeddings:
                continue
            missing_ids.append(skill.id)
            missing_texts.append(text)
            self._semantic_skill_text[skill.id] = text

        if missing_texts:
            try:
                embeddings = embedder.encode(
                    missing_texts,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )
            except TypeError:
                embeddings = embedder.encode(missing_texts, show_progress_bar=False)
                embeddings = [self._l2_normalize(item) for item in embeddings]
            except Exception as exc:
                logger.warning("Semantic routing disabled for this request (encode skills failed): %s", exc)
                return {}

            for skill_id, embedding in zip(missing_ids, embeddings):
                self._semantic_skill_embeddings[skill_id] = embedding

        scores: dict[str, float] = {}
        for skill in skills:
            embedding = self._semantic_skill_embeddings.get(skill.id)
            if embedding is None:
                continue
            scores[skill.id] = self._dot(req_embedding, embedding)

        return scores

    def _get_semantic_embedder(self):
        if not self.settings.skill_router_enable_embeddings:
            return None
        if self._semantic_embedder_error is not None:
            return None
        if self._semantic_embedder is not None:
            return self._semantic_embedder

        try:
            # Lazy import: do not import SentenceTransformers unless explicitly enabled.
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._semantic_embedder = SentenceTransformer(self.settings.skill_router_embedding_model)
            return self._semantic_embedder
        except Exception as exc:
            self._semantic_embedder_error = str(exc)
            logger.warning(
                "SentenceTransformers unavailable; falling back to keyword routing. Error: %s", exc
            )
            return None

    def _semantic_document(self, skill: SkillManifest) -> str:
        parts = [
            f"专家模式名称：{skill.name}",
            f"说明：{skill.description}",
            f"类别：{skill.category}",
            f"标签：{', '.join(skill.tags)}" if skill.tags else "",
            f"路由关键词：{', '.join(skill.route_keywords)}" if skill.route_keywords else "",
            f"目标用户：{', '.join(skill.target_users)}" if skill.target_users else "",
            f"输出重点：{', '.join(skill.output_focus)}" if skill.output_focus else "",
            f"示例需求：{skill.example_requirement}" if skill.example_requirement else "",
        ]
        return "\n".join(part for part in parts if part).strip()

    def _dot(self, left, right) -> float:
        return float(sum(float(a) * float(b) for a, b in zip(left, right)))

    def _l2_normalize(self, vector):
        values = [float(item) for item in vector]
        norm = math.sqrt(sum(item * item for item in values))
        if norm <= 0:
            return values
        return [item / norm for item in values]
