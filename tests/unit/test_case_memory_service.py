from datetime import datetime, timezone

from cipher_genius.api.schemas import CaseMemoryPayload
from cipher_genius.memory import CaseMemoryService


def test_case_memory_service_roundtrip(tmp_path):
    service = CaseMemoryService(storage_dir=tmp_path)
    snapshot = CaseMemoryPayload(
        case_id="case-test-001",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        status="best_effort",
        status_label="尽力交付",
        scenario="construction",
        requirement_summary="面向建筑项目 BIM/IFC 可信交付的密码改造需求",
        confirmed_constraints=["后量子要求：是"],
        blocking_items=["需补充密钥轮换周期"],
        latest_evidence_refs=["file:attack_result.json", "sha256:demo"],
        recent_reflections=[
            {
                "time": datetime.now(timezone.utc),
                "run_id": "run-001",
                "reflection_summary": "下一轮 generation 需要显式写清错误处理与接口边界。",
                "regression_summary": "补丁版本仍需继续做 decrypt 接口回归。",
                "prompt_changes": ["generation 强化错误处理说明"],
                "audit_focus": ["decrypt 接口边界"],
                "residual_risks": ["decrypt"],
                "changed_artifacts": ["implementation.py"],
                "patch_strategy": "error-boundary-hardening",
                "severity": "medium",
                "next_version": "v2",
            }
        ],
    )

    service.save(snapshot)
    loaded = service.get("case-test-001")

    assert loaded.case_id == "case-test-001"
    assert loaded.scenario == "construction"
    assert loaded.blocking_items == ["需补充密钥轮换周期"]
    assert loaded.recent_reflections[0]["run_id"] == "run-001"
    assert loaded.latest_evidence_refs == ["file:attack_result.json", "sha256:demo"]
    assert service.summarize(loaded).evidence_ref_count == 2
    assert service.fingerprint(loaded)


def test_case_memory_service_delete(tmp_path):
    service = CaseMemoryService(storage_dir=tmp_path)
    snapshot = CaseMemoryPayload(
        case_id="case-delete-001",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service.save(snapshot)
    service.delete("case-delete-001")

    assert service.load("case-delete-001") is None
