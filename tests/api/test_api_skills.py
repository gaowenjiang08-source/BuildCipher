from fastapi.testclient import TestClient

from cipher_genius.api.main import app


client = TestClient(app)


def test_skill_list_endpoint():
    response = client.get("/api/v1/skills")
    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] >= 3
    assert any(item["id"] == "trusted_crypto_reviewer" for item in payload["items"])
    assert all("version" in item for item in payload["items"])
    assert all("status" in item for item in payload["items"])


def test_skill_route_endpoint():
    response = client.post(
        "/api/v1/skills/route",
        json={
            "requirement": "请为 IFC 模型交付设计内容哈希、签名清单和批准版本验证方案。",
            "max_candidates": 3,
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["recommended_skill"]["id"] == "bim_model_exchange_guard"
    assert payload["candidates"]
    assert payload["candidates"][0]["matched_keywords"]


def test_skill_execute_endpoint():
    response = client.post(
        "/api/v1/skills/execute",
        json={
            "skill_id": "pqc_migration_advisor",
            "requirement": "请为长期保存的归档与签名验证系统设计兼顾当前兼容性和后量子迁移的方案。",
            "llm_provider": None,
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["skill"]["id"] == "pqc_migration_advisor"
    assert payload["skill"]["version"] == "2.0.0"
    assert "[已启用专家模式]" in payload["enhanced_requirement"]
    assert payload["result"]["delivery"]["applied_skill"]["id"] == "pqc_migration_advisor"
    assert payload["result"]["request_id"]


def test_skill_execute_endpoint_with_langgraph():
    response = client.post(
        "/api/v1/skills/execute",
        json={
            "skill_id": "pqc_migration_advisor",
            "requirement": "请为长期保存的归档与签名验证系统设计兼顾当前兼容性和后量子迁移的方案。",
            "llm_provider": None,
            "use_langgraph": True,
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["skill"]["id"] == "pqc_migration_advisor"
    assert payload["result"]["delivery"]["engine"] == "langgraph"
    assert payload["result"]["delivery"]["engine_mode"] == "graph-native"


def test_skill_execute_endpoint_accepts_deprecated_use_langgraph_flag():
    response = client.post(
        "/api/v1/skills/execute",
        json={
            "skill_id": "pqc_migration_advisor",
            "requirement": "请为长期保存的归档与签名验证系统设计兼顾当前兼容性和后量子迁移的方案。",
            "llm_provider": None,
            "use_langgraph": False,
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["skill"]["id"] == "pqc_migration_advisor"
    assert payload["result"]["delivery"]["engine"] == "langgraph"
    assert payload["result"]["delivery"]["engine_mode"] == "graph-native"


def test_skill_stream_endpoint():
    with client.stream(
        "POST",
        "/api/v1/skills/stream",
        json={
            "skill_id": "trusted_crypto_reviewer",
            "requirement": "请为企业跨部门文件共享设计来源可信且便于审计汇报的密码方案。",
        },
    ) as response:
        assert response.status_code == 200
        lines = [line for line in response.iter_lines() if line]

    assert any('"type": "progress"' in line for line in lines)
    assert any('"type": "final"' in line for line in lines)


def test_skill_stream_endpoint_with_langgraph():
    with client.stream(
        "POST",
        "/api/v1/skills/stream",
        json={
            "skill_id": "trusted_crypto_reviewer",
            "requirement": "请为企业跨部门文件共享设计来源可信且便于审计汇报的密码方案。",
            "use_langgraph": True,
        },
    ) as response:
        assert response.status_code == 200
        lines = [line for line in response.iter_lines() if line]

    assert any('"type": "run"' in line and '"engine": "langgraph"' in line for line in lines)
    assert any('"type": "final"' in line and '"engine": "langgraph"' in line for line in lines)
