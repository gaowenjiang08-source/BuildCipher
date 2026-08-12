"""Application service for skill-driven execution."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from cipher_genius.api.schemas import (
    MASRequest,
    SkillExecuteRequest,
    SkillExecutionResponse,
    SkillListResponse,
    SkillRouteRequest,
    SkillRouteResponse,
    SkillSummaryPayload,
)
from cipher_genius.core.langgraph_mas import LangGraphMASService
from cipher_genius.skills import SkillManifest, get_skill_registry
from cipher_genius.skills.router import SkillRouter
from cipher_genius.utils.config import get_settings
from cipher_genius.utils.redis_client import get_redis_client


class SkillExecutionService:
    """Resolve manifests into executable skill runs."""

    def __init__(self, llm_provider: str | None = None):
        self.llm_provider = llm_provider
        self.settings = get_settings()
        self.registry = get_skill_registry()
        self.router = SkillRouter(self.registry, settings=self.settings)

    def list_skills(self) -> SkillListResponse:
        items = [self._serialize_skill(skill) for skill in self.registry.list_all()]
        return SkillListResponse(total=len(items), items=items)

    def route(self, payload: SkillRouteRequest) -> SkillRouteResponse:
        requirement = payload.requirement
        requested_max = max(1, payload.max_candidates)

        cache_key = self._skill_route_cache_key(requirement)
        if cache_key:
            cached = get_redis_client().get_json(cache_key)
            if cached:
                response = SkillRouteResponse.model_validate(cached)
                return response.model_copy(update={"candidates": response.candidates[:requested_max]})

        response = self.router.route(requirement, max_candidates=8)

        if cache_key:
            get_redis_client().set_json(
                cache_key,
                response.model_dump(mode="json"),
                ttl=self.settings.skill_route_cache_ttl,
            )

        return response.model_copy(update={"candidates": response.candidates[:requested_max]})

    def execute(
        self,
        payload: SkillExecuteRequest,
        *,
        progress_callback=None,
        request_id: str | None = None,
        cancel_check=None,
    ) -> SkillExecutionResponse:
        skill = self.registry.get(payload.skill_id)
        if skill is None:
            raise ValueError(f"Unknown skill: {payload.skill_id}")

        effective_requirement = self._build_requirement(skill, payload.requirement)
        applied_overrides = self._build_overrides(skill, payload, effective_requirement)
        mas_payload = MASRequest(**applied_overrides)
        skill_summary = self._serialize_skill(skill)
        mas_service = LangGraphMASService(mas_payload.llm_provider)
        result = mas_service.execute(
            payload=mas_payload,
            progress_callback=progress_callback,
            request_id=request_id or mas_payload.run_id,
            cancel_check=cancel_check,
        )
        result.delivery = {
            **(result.delivery or {}),
            "applied_skill": skill_summary.model_dump(),
            "engine": "langgraph",
        }

        return SkillExecutionResponse(
            skill=skill_summary,
            enhanced_requirement=effective_requirement,
            applied_overrides=applied_overrides,
            result=result,
        )

    def _serialize_skill(self, skill: SkillManifest) -> SkillSummaryPayload:
        return SkillSummaryPayload(
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
        )

    def _build_requirement(self, skill: SkillManifest, requirement: str) -> str:
        parts: List[str] = [f"[已启用专家模式] {skill.name}"]
        if skill.description:
            parts.append(f"专家模式意图：{skill.description}")
        if skill.output_focus:
            parts.append("输出重点：\n- " + "\n- ".join(skill.output_focus))
        if skill.prompt_preamble:
            parts.append(skill.prompt_preamble.strip())
        parts.append("原始需求：\n" + requirement.strip())
        if skill.prompt_appendix:
            parts.append(skill.prompt_appendix.strip())
        return "\n\n".join(part for part in parts if part).strip()

    def _build_overrides(
        self,
        skill: SkillManifest,
        payload: SkillExecuteRequest,
        effective_requirement: str,
    ) -> Dict[str, Any]:
        return {
            "requirement": effective_requirement,
            "num_variants": payload.num_variants or skill.recommended_num_variants,
            "generate_code": payload.generate_code
            if payload.generate_code is not None
            else skill.generate_code_default,
            "llm_provider": payload.llm_provider or self.llm_provider,
            "run_id": payload.run_id,
            "case_id": payload.case_id,
            "max_audit_rounds": payload.max_audit_rounds or skill.recommended_max_audit_rounds,
            "max_same_run_retries": (
                payload.max_same_run_retries
                if payload.max_same_run_retries is not None
                else self.settings.same_run_retry_budget_default
            ),
            "strict_clarification": payload.strict_clarification
            if payload.strict_clarification is not None
            else skill.strict_clarification_default,
        }

    def _skill_route_cache_key(self, requirement: str) -> str | None:
        """Build Redis key for skill routing responses.

        We include routing-relevant settings and a skill-catalog fingerprint in the digest so
        config/manifest changes won't reuse stale results.
        """
        if not self.settings.enable_caching:
            return None
        if not self.settings.redis_enabled:
            return None

        catalog = []
        for skill in self.registry.list_all():
            catalog.append(
                {
                    "id": skill.id,
                    "version": skill.version,
                    "status": skill.status,
                    "auto_route_enabled": bool(skill.auto_route_enabled),
                    "route_priority": int(skill.route_priority),
                    "tags": list(skill.tags),
                    "route_keywords": list(skill.route_keywords),
                }
            )
        catalog.sort(key=lambda item: item["id"])

        signature = {
            "requirement": str(requirement or "").strip(),
            "enable_embeddings": bool(self.settings.skill_router_enable_embeddings),
            "embedding_model": str(self.settings.skill_router_embedding_model),
            "min_similarity": float(self.settings.skill_router_embedding_min_similarity),
            "embedding_weight": float(self.settings.skill_router_embedding_weight),
            "skill_catalog": catalog,
        }
        encoded = json.dumps(signature, ensure_ascii=False, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return f"skill:route:{digest[:24]}"
