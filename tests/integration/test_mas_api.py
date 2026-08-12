"""Integration tests for LangGraph MAS API endpoints."""

import pytest
import requests
from typing import Dict, Any


BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture(scope="module")
def api_client():
    """Check if API server is running."""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        pytest.skip("API server not running. Start with: poetry run buildtrust-api")
    return False


def test_health_endpoint(api_client):
    """Test health check endpoint."""
    response = requests.get(f"{BASE_URL}/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "buildtrust-api"


def test_mas_execute_compatibility_flag_is_accepted(api_client):
    """Test MAS execution still accepts the deprecated compatibility flag."""
    payload = {
        "requirement": "Design a secure digital signature scheme for document signing",
        "llm_provider": "openai",
        "num_variants": 1,
        "max_audit_rounds": 1,
        "generate_code": False,
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/mas/execute",
        json=payload,
        params={"use_langgraph": False},
        timeout=120,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "request_id" in data
    assert "run_id" in data
    assert "generated_at" in data
    assert "security_disclaimer" in data
    assert "analyst" in data
    assert "architect" in data
    assert "auditor_rounds" in data
    assert "engineer" in data
    assert data["delivery"]["engine"] == "langgraph"


def test_mas_execute_langgraph_engine(api_client):
    """Test MAS execution with LangGraph engine."""
    payload = {
        "requirement": "Design AES-GCM encryption for IoT device communication",
        "llm_provider": "openai",
        "num_variants": 1,
        "max_audit_rounds": 1,
        "generate_code": False,
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/mas/execute",
        json=payload,
        params={"use_langgraph": True},
        timeout=120,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "request_id" in data
    assert "run_id" in data
    assert "generated_at" in data
    assert "security_disclaimer" in data
    assert "analyst" in data
    assert "architect" in data
    assert "auditor_rounds" in data
    assert "engineer" in data


def test_mas_stream_compatibility_flag_is_accepted(api_client):
    """Test MAS streaming still accepts the deprecated compatibility flag."""
    payload = {
        "requirement": "Design HMAC-SHA256 for API authentication",
        "llm_provider": "openai",
        "num_variants": 1,
        "max_audit_rounds": 1,
        "generate_code": False,
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/mas/stream",
        json=payload,
        params={"use_langgraph": False},
        stream=True,
        timeout=120,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"

    events = []
    for line in response.iter_lines():
        if line:
            import json
            event = json.loads(line)
            events.append(event)

    # Verify event sequence
    assert len(events) > 0
    assert events[0]["type"] == "run"
    assert events[0]["engine"] == "langgraph"
    assert events[-1]["type"] in ["final", "error"]


def test_mas_stream_langgraph_engine(api_client):
    """Test MAS streaming with LangGraph engine."""
    payload = {
        "requirement": "Design RSA-PSS signature for code signing",
        "llm_provider": "openai",
        "num_variants": 1,
        "max_audit_rounds": 1,
        "generate_code": False,
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/mas/stream",
        json=payload,
        params={"use_langgraph": True},
        stream=True,
        timeout=120,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"

    events = []
    for line in response.iter_lines():
        if line:
            import json
            event = json.loads(line)
            events.append(event)

    # Verify event sequence
    assert len(events) > 0
    assert events[0]["type"] == "run"
    assert events[0]["engine"] == "langgraph"
    assert events[-1]["type"] in ["final", "error"]


def test_engine_compatibility_flag_preserves_contract(api_client):
    """Compare default and deprecated-flag executions under the LangGraph mainline."""
    requirement = "Design ChaCha20-Poly1305 AEAD for secure messaging"

    payload = {
        "requirement": requirement,
        "llm_provider": "openai",
        "num_variants": 1,
        "max_audit_rounds": 1,
        "generate_code": False,
    }

    # Execute with deprecated compatibility flag.
    response_compat = requests.post(
        f"{BASE_URL}/api/v1/mas/execute",
        json=payload,
        params={"use_langgraph": False},
        timeout=120,
    )
    assert response_compat.status_code == 200
    result_compat = response_compat.json()

    # Execute with LangGraph engine
    response_langgraph = requests.post(
        f"{BASE_URL}/api/v1/mas/execute",
        json=payload,
        params={"use_langgraph": True},
        timeout=120,
    )
    assert response_langgraph.status_code == 200
    result_langgraph = response_langgraph.json()

    # Both should follow the same schema contract
    assert set(result_compat.keys()) == set(result_langgraph.keys())

    # Both should have analyst report
    assert result_compat["analyst"] is not None
    assert result_langgraph["analyst"] is not None

    # Both should have architect report with candidates
    assert result_compat["architect"] is not None
    assert result_langgraph["architect"] is not None
    assert result_compat["delivery"]["engine"] == "langgraph"
    assert result_langgraph["delivery"]["engine"] == "langgraph"

    print("\n=== Engine Comparison ===")
    print(f"Compat-flag run_id: {result_compat['run_id']}")
    print(f"LangGraph run_id: {result_langgraph['run_id']}")
    print("Both runs completed on the LangGraph mainline")


def test_invalid_llm_provider(api_client):
    """Test error handling with invalid LLM provider."""
    payload = {
        "requirement": "Test requirement",
        "llm_provider": "invalid_provider",
        "num_variants": 1,
    }

    # Test deprecated compatibility flag path
    response = requests.post(
        f"{BASE_URL}/api/v1/mas/execute",
        json=payload,
        params={"use_langgraph": False},
        timeout=30,
    )
    assert response.status_code == 400

    # Test LangGraph engine
    response = requests.post(
        f"{BASE_URL}/api/v1/mas/execute",
        json=payload,
        params={"use_langgraph": True},
        timeout=30,
    )
    assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
