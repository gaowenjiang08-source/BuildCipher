from cipher_genius.skills import get_skill_registry


def test_skill_registry_loads_manifests():
    registry = get_skill_registry()
    skills = registry.list_all()

    assert skills
    assert any(skill.id == "trusted_crypto_reviewer" for skill in skills)


def test_skill_registry_get_known_skill():
    registry = get_skill_registry()
    skill = registry.get("bim_model_exchange_guard")

    assert skill is not None
    assert skill.name
    assert skill.version == "1.0.0"
    assert skill.status == "active"
    assert skill.execution_mode == "mas"
