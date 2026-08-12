import json

from cipher_genius.api.schemas import AttackResultPayload, PatchSpecPayload
from cipher_genius.core.artifact_summarizer import ArtifactSummarizer


def test_artifact_summarizer_reads_metrics_trace_and_finding(tmp_path):
    attack_dir = tmp_path / "attack_01"
    attack_dir.mkdir(parents=True, exist_ok=True)
    trace_path = attack_dir / "trace.jsonl"
    metrics_path = attack_dir / "metrics.json"
    finding_path = attack_dir / "finding.json"

    trace_path.write_text(
        "\n".join(
            [
                json.dumps({"phase": "prepare", "message": "已启动服务"}, ensure_ascii=False),
                json.dumps({"phase": "probe", "message": "第 1 次探测完成"}, ensure_ascii=False),
                json.dumps({"phase": "collect", "message": "已完成工件采集"}, ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(
            {
                "latency_p95_ms": 11,
                "health_latency_ms": 3,
                "probe_count": 3,
                "tx_bytes": 128,
                "rx_bytes": 256,
                "service_port": 8011,
                "health_status": "ready",
                "traffic_series": [{"sample": 1}, {"sample": 2}, {"sample": 3}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    finding_path.write_text(
        json.dumps(
            {
                "findings": ["错误返回存在可区分差异", "decrypt 接口缺少边界约束"],
                "risk_score": 76,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    attack_result = AttackResultPayload(
        attack_id="attack-1",
        target_service_ref="svc-1",
        status="executed",
        status_label="已执行",
        summary="已生成 trace / metrics / finding 工件。",
        findings=[],
        metrics={"probe_count": 3},
        artifact_refs=[
            str(trace_path).replace("\\", "/"),
            str(metrics_path).replace("\\", "/"),
            str(finding_path).replace("\\", "/"),
        ],
    )

    summarizer = ArtifactSummarizer()
    summary = summarizer.summarize_attack_result(attack_result)

    assert summary["attack_id"] == "attack-1"
    assert summary["artifact_count"] == 3
    assert "错误返回存在可区分差异" in summary["top_findings"]
    assert summary["metrics_summary"]["probe_count"] == 3
    assert summary["artifact_summaries"][0]["artifact_type"] == "attack_trace"
    assert summary["artifact_summaries"][1]["metadata"]["latency_p95_ms"] == 11
    assert summary["artifact_summaries"][2]["metadata"]["risk_score"] == 76


def test_artifact_summarizer_builds_patch_diff_summary(tmp_path):
    baseline_dir = tmp_path / "baseline_service"
    patched_dir = tmp_path / "patched_service"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    patched_dir.mkdir(parents=True, exist_ok=True)

    (baseline_dir / "implementation.py").write_text(
        "def encrypt(data):\n"
        "    return data\n",
        encoding="utf-8",
    )
    (patched_dir / "implementation.py").write_text(
        "def encrypt(data):\n"
        "    masked = data.strip()\n"
        "    return masked\n",
        encoding="utf-8",
    )

    patch_spec = PatchSpecPayload(
        patch_id="patch-1",
        target_service_ref="svc-1",
        strategy="hardening-and-validation",
        summary="补齐输入清洗与输出收敛逻辑。",
        changed_artifacts=[f"{patched_dir}:python"],
        next_version="v2",
        regression_focus=["验证加密接口输入清洗后是否保持正确输出。"],
    )

    summarizer = ArtifactSummarizer()
    summary = summarizer.summarize_patch_artifacts(
        patch_spec=patch_spec,
        baseline_workspace=str(baseline_dir),
        patched_workspace=str(patched_dir),
    )

    assert summary["patch_id"] == "patch-1"
    assert summary["changed_artifact_count"] == 1
    assert summary["regression_focus"] == ["验证加密接口输入清洗后是否保持正确输出。"]

    artifact_summary = summary["changed_artifact_summaries"][0]
    assert artifact_summary["artifact_key"] == "python"
    assert artifact_summary["relative_name"] == "implementation.py"
    assert artifact_summary["baseline_exists"] is True
    assert artifact_summary["patched_exists"] is True
    assert artifact_summary["before_line_count"] == 2
    assert artifact_summary["after_line_count"] == 3
    assert artifact_summary["line_delta"] == 1
    assert artifact_summary["added_line_count"] >= 1
    assert artifact_summary["removed_line_count"] >= 1
    assert any(item.startswith("+ ") for item in artifact_summary["diff_preview"])
    assert "implementation.py" in artifact_summary["summary"]
