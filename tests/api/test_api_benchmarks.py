from fastapi.testclient import TestClient

from cipher_genius.api.main import app


client = TestClient(app)


def test_construction_benchmark_endpoint():
    response = client.get("/api/v1/benchmarks/construction")
    assert response.status_code == 200

    payload = response.json()
    assert payload["benchmark_id"] == "construction-trusted-delivery-v1"
    assert payload["total_cases"] == 7
    assert payload["skill_hit_rate"] == 1.0
    assert payload["template_hit_rate"] == 1.0
    assert payload["section_hit_rate"] == 1.0


def test_retired_biopharma_benchmark_endpoint_is_not_exposed():
    response = client.get("/api/v1/benchmarks/biopharma")
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
    assert "localhost provider" in payload["capability_boundary"]
    assert len(payload["results"]) == 5
