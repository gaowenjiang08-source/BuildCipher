from cipher_genius.reporting import get_report_template_registry


def test_report_template_registry_loads_current_templates():
    templates = get_report_template_registry().list_all()

    assert templates
    assert any(template.id == "enterprise_general_delivery" for template in templates)
    assert any(template.id == "construction_trusted_delivery" for template in templates)
    assert all(template.scenario != "biopharma" for template in templates)


def test_report_template_registry_resolves_construction_templates():
    registry = get_report_template_registry()

    default_template = registry.resolve("construction", "bim_model_exchange_guard")
    iot_template = registry.resolve("construction", "construction_iot_trust_architect")
    pqc_template = registry.resolve("construction", "built_asset_pqc_migration_advisor")

    assert default_template is not None
    assert default_template.id == "construction_trusted_delivery"
    assert iot_template is not None
    assert iot_template.id == "construction_iot_evidence_delivery"
    assert pqc_template is not None
    assert pqc_template.id == "built_asset_pqc_transition_delivery"
