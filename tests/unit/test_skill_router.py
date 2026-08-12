from cipher_genius.skills import SkillManifest, get_skill_registry
from cipher_genius.skills.router import SkillRouter
from cipher_genius.utils.config import Settings


def _assert_route(requirement: str, expected_skill_id: str) -> None:
    result = SkillRouter(get_skill_registry()).route(requirement, max_candidates=3)
    assert result.recommended_skill is not None
    assert result.recommended_skill.id == expected_skill_id
    assert result.candidates[0].matched_keywords


def test_skill_router_prefers_bim_exchange_guard():
    _assert_route(
        "请验证 IFC 模型交付 manifest、内容哈希、签名和批准版本，阻止篡改与旧版本回滚。",
        "bim_model_exchange_guard",
    )


def test_skill_router_prefers_construction_collaboration_guard():
    _assert_route(
        "专业分包尝试下载完整结构模型和造价信息，请生成最小权限、撤销和越权拒绝策略。",
        "construction_collaboration_ip_guard",
    )


def test_skill_router_prefers_construction_iot_architect():
    _assert_route(
        "未注册工地传感器冒充设备并重放历史有效遥测，请验证设备身份、nonce、计数器和时间窗口。",
        "construction_iot_trust_architect",
    )


def test_skill_router_prefers_inspection_evidence_designer():
    _assert_route(
        "监理否认隐蔽工程验收签批，请关联人员、时间、位置、模型版本和现场证据。",
        "inspection_evidence_chain_designer",
    )


def test_skill_router_prefers_built_asset_pqc_advisor():
    _assert_route(
        "请为保存 30 年的竣工模型制定后量子迁移、混合部署、重签和再封装路线。",
        "built_asset_pqc_migration_advisor",
    )


class _DummyRegistry:
    def __init__(self, skills):
        self._skills = skills

    def list_all(self):
        return list(self._skills)


def test_skill_router_semantic_rescues_without_keyword(monkeypatch):
    skills = [
        SkillManifest(id="a", name="Alpha", description="First"),
        SkillManifest(id="b", name="Beta", description="Second"),
    ]
    settings = Settings(
        skill_router_enable_embeddings=True,
        skill_router_embedding_min_similarity=0.35,
        skill_router_embedding_weight=0.35,
    )
    router = SkillRouter(_DummyRegistry(skills), settings=settings)
    monkeypatch.setattr(router, "_semantic_score", lambda requirement, skills: {"a": 0.62, "b": 0.12})

    result = router.route("unrelated requirement that shares no tokens", max_candidates=3)

    assert result.routing_version == "skill-v2-hybrid-router"
    assert result.recommended_skill is not None
    assert result.recommended_skill.id == "a"
    assert any("语义相似度" in reason for reason in result.candidates[0].reasons)
