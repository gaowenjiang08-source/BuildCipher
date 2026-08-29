from pathlib import Path

from fastapi.testclient import TestClient

from cipher_genius.api.main import app

client = TestClient(app)


def test_construction_benchmark_endpoint():
    response = client.get("/api/v1/benchmarks/construction")
    assert response.status_code == 200

    payload = response.json()
    assert payload["benchmark_id"] == "construction-trusted-delivery-v1"
    assert payload["total_cases"] == 8
    assert payload["skill_hit_rate"] == 1.0
    assert payload["template_hit_rate"] == 1.0
    assert payload["section_hit_rate"] == 1.0


def test_retired_benchmark_endpoint_is_not_exposed():
    response = client.get("/api/v1/benchmarks/retired")
    assert response.status_code == 404


def test_construction_demo_endpoint_executes_five_attacks():
    response = client.post(
        "/api/v1/construction/demo/run",
        json={"project_id": "api-demo-project", "run_id": "api-construction-demo"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["attack_count"] == 5
    assert payload["detected_count"] == 5
    assert payload["blocked_count"] == 5
    assert payload["regression_passed_count"] == 5
    assert payload["evidence_ledger_valid"] is True
    assert payload["baseline_blocked_count"] == 0
    assert payload["hardened_blocked_count"] == 5
    assert payload["comparison_verified"] is True
    assert "localhost provider" in payload["capability_boundary"]
    assert len(payload["results"]) == 5


def test_construction_ifc_import_flows_into_comparison_demo():
    ifc_bytes = Path("data/demo/buildtrust_v1/coordination.ifc").read_bytes()
    import_response = client.post(
        "/api/v1/construction/assets/import",
        data={
            "project_id": "api-ifc-project",
            "asset_id": "ifc-main-model",
            "version": "v3",
            "parent_version": "v2",
            "approval_state": "approved",
        },
        files={"file": ("coordination.ifc", ifc_bytes, "application/x-step")},
    )
    assert import_response.status_code == 200
    imported = import_response.json()
    assert imported["inspection"]["valid"] is True
    assert imported["inspection"]["schema_identifiers"] == ["IFC4"]
    assert imported["inspection"]["entity_count"] == 3

    demo_response = client.post(
        "/api/v1/construction/demo/run",
        json={
            "project_id": "api-ifc-project",
            "asset_ref": imported["asset_ref"],
            "mode": "compare",
        },
    )
    assert demo_response.status_code == 200
    demo = demo_response.json()
    assert demo["asset_ref"] == imported["asset_ref"]
    assert demo["asset_inspection"]["content_sha256"] == imported["inspection"]["content_sha256"]
    assert demo["baseline_blocked_count"] == 0
    assert demo["hardened_blocked_count"] == 5
