from pathlib import Path

from cipher_genius.sandbox.target_templates import (
    build_bim_package_exchange_target_service,
    build_construction_iot_gateway_target_service,
    build_mock_crypto_http_target_service,
    build_project_evidence_ledger_target_service,
    build_target_service_for_requirement,
    materialize_deployment_manifest,
)


def test_build_mock_crypto_http_target_service_populates_template_metadata():
    service = build_mock_crypto_http_target_service(
        run_id="run-template-001",
        service_name="demo-crypto-http",
        runtime="python",
        attack_surface=["encrypt", "decrypt", "key_rotation"],
    )

    assert service.service_id == "svc-run-temp"
    assert service.template_id == "mock_crypto_http_v1"
    assert service.template_label == "模拟加密 HTTP 服务"
    assert service.service_kind == "crypto_api"
    assert service.attack_surface_kind == "http-json"
    assert service.supported_versions == ["baseline", "patched", "regression"]
    assert "attack_surface_analysis" in service.planner_skill_hints
    assert "error handling leakage" in service.planner_retrieval_hints
    assert service.deployment_manifest.bootstrap_script == "service_runtime.py"
    assert service.runtime_profile.probe_budget == 64


def test_materialize_deployment_manifest_updates_workspace_paths(tmp_path: Path):
    service = build_mock_crypto_http_target_service(
        run_id="run-template-002",
        service_name="demo-crypto-http",
        runtime="python",
        attack_surface=["encrypt"],
    )
    workspace = tmp_path / "sandbox" / service.service_id
    script_path = workspace / "service_runtime.py"
    workspace.mkdir(parents=True, exist_ok=True)
    script_path.write_text("print('ok')", encoding="utf-8")

    deployed = materialize_deployment_manifest(
        service,
        workspace=workspace,
        service_script_path=script_path,
    )

    assert deployed.status == "deployed"
    assert deployed.status_label == "已部署"
    assert deployed.artifact_id == str(workspace).replace("\\", "/")
    assert deployed.entrypoint == str(script_path).replace("\\", "/")
    assert deployed.deployment_manifest.workspace_dir == str(workspace).replace("\\", "/")
    assert deployed.deployment_manifest.artifact_dir.endswith("/artifacts")
    assert deployed.deployment_manifest.bootstrap_script == "service_runtime.py"


def test_buildtrust_target_templates_expose_domain_attack_surfaces():
    bim = build_bim_package_exchange_target_service(run_id="run-buildtrust-001")
    iot = build_construction_iot_gateway_target_service(run_id="run-buildtrust-001")
    ledger = build_project_evidence_ledger_target_service(run_id="run-buildtrust-001")

    assert bim.template_id == "bim_package_exchange_v1"
    assert "version_approve" in bim.attack_surface
    assert "bim_model_exchange_guard" in bim.planner_skill_hints
    assert iot.template_id == "construction_iot_gateway_v1"
    assert "replay_guard" in iot.attack_surface
    assert ledger.template_id == "project_evidence_ledger_v1"
    assert "chain_verify" in ledger.attack_surface
    assert all(item.deployment_profile == "sandbox-construction-demo" for item in [bim, iot, ledger])


def test_target_selector_routes_construction_subscenarios_without_affecting_general_requests():
    bim = build_target_service_for_requirement(
        run_id="run-selector-bim",
        requirement_text="请验证 IFC 模型交付、篡改和版本回滚",
        domain="construction",
        service_name="ignored-for-construction",
        runtime="python",
        attack_surface=[],
    )
    iot = build_target_service_for_requirement(
        run_id="run-selector-iot",
        requirement_text="请验证工地传感器遥测的设备冒充和重放",
        domain="construction",
        service_name="ignored-for-construction",
        runtime="python",
        attack_surface=[],
    )
    ledger = build_target_service_for_requirement(
        run_id="run-selector-ledger",
        requirement_text="请为隐蔽工程验收签批建立证据链",
        domain="construction",
        service_name="ignored-for-construction",
        runtime="python",
        attack_surface=[],
    )
    general = build_target_service_for_requirement(
        run_id="run-selector-general",
        requirement_text="通用文件加密服务",
        domain="general",
        service_name="general-service",
        runtime="python",
        attack_surface=["encrypt"],
    )

    assert bim.template_id == "bim_package_exchange_v1"
    assert iot.template_id == "construction_iot_gateway_v1"
    assert ledger.template_id == "project_evidence_ledger_v1"
    assert general.template_id == "mock_crypto_http_v1"
