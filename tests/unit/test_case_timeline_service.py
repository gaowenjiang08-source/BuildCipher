from cipher_genius.memory.replay_service import CaseTimelineService


def test_case_timeline_service_records_snapshot_and_events(tmp_path):
    service = CaseTimelineService(storage_dir=tmp_path)
    snapshot, summary = service.record_run(
        case_id="case-001",
        run_id="run-001",
        delivery={
            "status": "approved",
            "status_label": "已批准",
            "selected_proposal": "proposal-1",
            "workflow_trace": ["analyst", "delivery"],
            "next_action": "继续进入人工复核。",
            "context_projections": {
                "generation": {
                    "cards": [
                        {
                            "card_id": "card-001",
                            "card_type": "reflection_memory",
                            "card_family": "reflection",
                            "card_family_label": "反思卡",
                            "card_contract_version": "v1",
                            "lineage_ref": "case-001:run-001:generation-r1:v2",
                            "replay_index_ref": "card-001:reflection",
                        }
                    ]
                }
            },
            "attack_loop": {
                "attack_decision": {
                    "decision_id": "decision-1",
                    "action": "execute",
                    "rationale": "先执行基线攻击。",
                    "selected_attack_family": "oracle_probe",
                    "target_service_ref": "svc-1",
                },
                "vulnerability_verdict": {
                    "verdict_id": "verdict-1",
                    "summary": "发现基线版本存在口令预言机风险。",
                    "severity": "high",
                    "remediation_priority": "p1",
                    "exploitable": True,
                },
                "target_service": {"service_id": "svc-1", "service_version": "v1"},
                "regression_target_service": {"service_id": "svc-1", "service_version": "v2"},
                "patch_spec": {
                    "patch_id": "patch-1",
                    "target_service_ref": "svc-1",
                    "next_version": "v2",
                    "strategy": "tighten oracle checks",
                    "summary": "收紧错误响应并补充校验。",
                    "validation_steps": ["回归攻击验证", "健康检查"],
                },
                "patch_execution": {
                    "patch_id": "patch-1",
                    "execution_contract_version": "v1",
                    "status": "validated",
                    "summary": "补丁已完成部署与验证。",
                    "target_service_ref": "svc-1",
                    "workspace": "workspace-1",
                    "patch_dispatch_id": "dispatch-patch-001",
                    "rollback_dispatch_id": "dispatch-rollback-001",
                    "deployment_dispatch_id": "dispatch-deploy-001",
                    "regression_dispatch_id": "dispatch-attack-002",
                    "patch_artifact_refs": [
                        "artifact:patch_manifest.json",
                        "artifact:patch_metadata.json",
                    ],
                    "rollback_artifact_refs": [
                        "artifact:rollback_plan.json",
                        "artifact:rollback_manifest.json",
                    ],
                    "regression_artifact_refs": [
                        "artifact:regression_finding.json",
                    ],
                    "validation_summary": {"passed": 2, "failed": 0},
                },
                "reflection_cards": [
                    {
                        "card_id": "reflection-1",
                        "card_type": "reflection",
                        "reflection": "下轮需要更早引入口令错误路径审计。",
                        "prompt_changes": ["加强 oracle 风险识别"],
                        "audit_focus": ["错误响应差异"],
                        "residual_risks": ["侧信道仍需关注"],
                    },
                    {
                        "card_id": "reflection-2",
                        "card_type": "regression_summary",
                        "summary": "回归轮未复现原始漏洞。",
                    },
                ],
            },
            "sandbox_dispatcher": {
                "backend": "local-dispatcher",
                "baseline_deployment": {
                    "dispatch_id": "dispatch-deploy-001",
                    "stage": "target_deployer",
                    "operation_kind": "deploy",
                    "executor_kind": "container",
                    "executor_backend": "container-sandbox",
                    "executor_label": "本地受限进程",
                    "target_service_ref": "svc-1",
                    "governance_mode": "dispatcher",
                    "decision": "approved",
                    "status": "blocked",
                    "failure_category": "executor_handoff_required",
                    "artifact_refs": ["artifact:service_manifest.json"],
                    "rejection_reasons": ["executor_handoff_required:container"],
                    "handoff_ref": "handoff:dispatch-deploy-001",
                    "artifact_sync_manifest": {
                        "sync_id": "sync:dispatch-deploy-001",
                        "dispatch_id": "dispatch-deploy-001",
                        "sync_status": "planned",
                    },
                    "handoff_receipt": {
                        "receipt_id": "receipt:dispatch-deploy-001",
                        "handoff_ref": "handoff:dispatch-deploy-001",
                        "dispatch_id": "dispatch-deploy-001",
                        "executor_kind": "container",
                        "executor_backend": "container-sandbox",
                        "accepted": False,
                        "receipt_status": "handoff_required",
                    },
                    "handoff_trace": {
                        "handoff_ref": "handoff:dispatch-deploy-001",
                        "dispatch_id": "dispatch-deploy-001",
                        "executor_kind": "container",
                        "executor_backend": "container-sandbox",
                        "routing_mode": "handoff",
                        "adapter_stage": "dispatcher_plan",
                        "trace_status": "handoff_required",
                        "receipt_ref": "receipt:dispatch-deploy-001",
                        "artifact_sync_ref": "sync:dispatch-deploy-001",
                        "failure_category": "policy_rejection",
                        "summary": "dispatcher generated container handoff placeholder.",
                    },
                    "audit_trail": [{"summary": "基线部署完成。"}],
                },
                "baseline_attack": {
                    "dispatch_id": "dispatch-attack-001",
                    "stage": "attack_executor",
                    "operation_kind": "attack",
                    "executor_kind": "local_process",
                    "executor_backend": "local-sandbox",
                    "executor_label": "本地受限进程",
                    "target_service_ref": "svc-1",
                    "decision": "approved",
                    "status": "executed",
                    "failure_category": "",
                    "artifact_refs": ["trace:artifact-attack-001"],
                    "rejection_reasons": [],
                    "audit_trail": [{"summary": "基线攻击执行完成。"}],
                },
                "patch_apply": {
                    "dispatch_id": "dispatch-patch-001",
                    "stage": "patch_executor",
                    "operation_kind": "patch_apply",
                    "executor_kind": "local_process",
                    "executor_backend": "local-sandbox",
                    "executor_label": "本地受限进程",
                    "target_service_ref": "svc-1",
                    "decision": "approved",
                    "status": "executed",
                    "failure_category": "",
                    "artifact_refs": ["artifact:patch_manifest.json"],
                    "rejection_reasons": [],
                    "audit_trail": [{"summary": "补丁工作区已物化。"}],
                },
                "regression_deployment": {
                    "dispatch_id": "dispatch-deploy-002",
                    "stage": "target_deployer",
                    "operation_kind": "deploy",
                    "executor_kind": "local_process",
                    "executor_backend": "local-sandbox",
                    "executor_label": "本地受限进程",
                    "target_service_ref": "svc-1",
                    "decision": "approved",
                    "status": "executed",
                    "failure_category": "",
                    "artifact_refs": ["artifact:runtime_info.json"],
                    "rejection_reasons": [],
                    "audit_trail": [{"summary": "回归部署完成。"}],
                },
                "regression_attack": {
                    "dispatch_id": "dispatch-attack-002",
                    "stage": "attack_executor",
                    "operation_kind": "regression_replay",
                    "executor_kind": "local_process",
                    "executor_backend": "local-sandbox",
                    "executor_label": "本地受限进程",
                    "target_service_ref": "svc-1",
                    "decision": "approved",
                    "status": "failed",
                    "failure_category": "runtime_execution_failed",
                    "artifact_refs": ["artifact:regression_finding.json"],
                    "rejection_reasons": ["runtime_execution_failed:attack"],
                    "audit_trail": [{"summary": "回归攻击执行失败。"}],
                },
                "rollback_plan": {
                    "dispatch_id": "dispatch-rollback-001",
                    "stage": "rollback_executor",
                    "operation_kind": "rollback",
                    "executor_kind": "local_process",
                    "executor_backend": "local-sandbox",
                    "executor_label": "本地受限进程",
                    "target_service_ref": "svc-1",
                    "decision": "approved",
                    "status": "executed",
                    "failure_category": "",
                    "artifact_refs": ["artifact:rollback_plan.json"],
                    "rejection_reasons": [],
                    "audit_trail": [{"summary": "回滚预案已落盘。"}],
                },
            },
        },
        control_plane={"summary": {"stage_count": 2}},
        memory_bus={
            "projection_count": 2,
            "handoff_count": 1,
            "summary": {
                "typed_family_count": 3,
                "typed_contract_count": 2,
                "dominant_family": "reflection",
                "dominant_contract": "reflection:reflection_memory:v1",
                "retry_window_count": 3,
                "retry_handoff_count": 3,
                "retry_projection_refs": [
                    "attack_planning_agent:attack-plan-r2",
                    "vulnerability_agent:vulnerability-r2",
                    "expert_gate_agent:expert-gate-r2",
                ],
                "retry_handoff_refs": [
                    "handoff-retry-attack",
                    "handoff-retry-verdict",
                    "handoff-retry-gate",
                ],
                "retry_lineage_refs": [
                    "case-001:run-001:attack-r2",
                    "case-001:run-001:vulnerability-r2",
                ],
                "retry_typed_contract_refs": [
                    "decision:attack_decision:v1",
                    "evaluation:vulnerability_verdict:v1",
                    "governance:expert_gate_decision:v1",
                ],
                "retry_compression_stages": [
                    "attack_planning_retry",
                    "vulnerability_evaluation_retry",
                    "expert_gate_retry",
                ],
                "retry_compression_policies": [
                    "retain_summary_and_refs_drop_raw_details",
                ],
                "retry_retained_refs": [
                    "attack-spec:retry-001",
                    "finding:retry-001",
                ],
                "retry_resume_checkpoint_refs": [
                    "checkpoint:patch_reflection:retry-r1",
                ],
                "retry_resume_input_refs": [
                    "resume-input:attack-planning-r2",
                    "resume-input:vulnerability-r2",
                ],
            },
            "windows": [
                {
                    "agent_id": "generation_agent",
                    "window_ref": "generation_agent:generation-r1",
                    "dominant_card_family": "reflection",
                    "dominant_typed_contract": "reflection:reflection_memory:v1",
                    "artifact_lookup_refs": ["proposal:artifact-001"],
                    "evidence_lookup_refs": ["doc-001:chunk-001"],
                },
                {
                    "agent_id": "vulnerability_agent",
                    "window_ref": "vulnerability_agent:attack-r1",
                    "dominant_card_family": "decision",
                    "dominant_typed_contract": "decision:attack_decision:v1",
                    "artifact_lookup_refs": ["trace:artifact-attack-001"],
                    "evidence_lookup_refs": [],
                },
            ],
            "handoffs": [
                {
                    "handoff_id": "handoff-001",
                    "from_agent": "generation_agent",
                    "to_agent": "audit_agent",
                    "projection_ref": "audit_agent:audit-r1",
                    "dominant_card_family": "reflection",
                    "dominant_typed_contract": "reflection:reflection_memory:v1",
                    "artifact_lookup_refs": ["proposal:artifact-001"],
                    "evidence_lookup_refs": ["doc-001:chunk-001"],
                }
            ],
            "typed_families": [
                {"family": "runtime_input", "family_label": "运行时输入", "card_count": 1, "handoff_count": 0},
                {"family": "reflection", "family_label": "反思卡", "card_count": 1, "handoff_count": 1},
                {"family": "decision", "family_label": "决策卡", "card_count": 1, "handoff_count": 0},
            ],
            "typed_contracts": [
                {
                    "contract_ref": "reflection:reflection_memory:v1",
                    "card_type": "reflection_memory",
                    "family": "reflection",
                    "family_label": "反思卡",
                    "contract_version": "v1",
                    "card_count": 1,
                    "handoff_count": 1,
                    "window_refs": ["generation_agent:generation-r1"],
                    "handoff_refs": ["handoff-001"],
                    "lineage_refs": ["case-001:run-001:generation-r1:v2"],
                    "artifact_ref_count": 1,
                    "evidence_ref_count": 0,
                    "lookup_strategy": "card_refs_then_projection_then_handoff_then_replay",
                    "replay_index_refs": ["card-001:reflection"],
                },
                {
                    "contract_ref": "decision:attack_decision:v1",
                    "card_type": "attack_decision",
                    "family": "decision",
                    "family_label": "决策卡",
                    "contract_version": "v1",
                    "card_count": 1,
                    "handoff_count": 0,
                    "window_refs": ["vulnerability_agent:attack-r1"],
                    "handoff_refs": [],
                    "lineage_refs": ["case-001:run-001:attack-r1"],
                    "artifact_ref_count": 0,
                    "evidence_ref_count": 0,
                    "lookup_strategy": "card_refs_then_projection_then_handoff_then_replay",
                    "replay_index_refs": ["card-attack:decision"],
                },
            ],
            "replay_snapshot_card": {
                "projection_refs": ["generation_agent:generation-r1", "audit_agent:audit-r1"],
                "handoff_refs": ["handoff-001"],
                "typed_family_counts": {
                    "runtime_input": 1,
                    "reflection": 1,
                    "decision": 1,
                },
                "typed_contract_counts": {
                    "reflection:reflection_memory:v1": 1,
                    "decision:attack_decision:v1": 1,
                },
                "artifact_ref_count": 2,
                "evidence_ref_count": 1,
                "lineage_refs": ["case-001:run-001:generation-r1:v2"],
                "artifact_lookup_refs": ["proposal:artifact-001", "trace:artifact-attack-001"],
                "evidence_lookup_refs": ["doc-001:chunk-001"],
            },
        },
        execution_plane={
            "summary": {"stage_count": 1},
            "stages": [
                {
                    "stage_kind": "baseline_attack",
                    "status": "executed",
                    "summary": "baseline attack executed",
                    "metadata": {"approved_attack_count": 1},
                }
            ],
        },
    )

    assert snapshot.snapshot_id == "snapshot-run-001"
    assert summary["snapshot_count"] == 1
    assert summary["event_count"] == 21
    assert summary["latest_projection_ref_count"] == 2
    assert summary["latest_handoff_ref_count"] == 1
    assert summary["latest_dispatch_ref_count"] == 6
    assert summary["latest_failed_dispatch_ref_count"] == 2
    assert summary["latest_dispatch_summary_count"] == 6
    assert summary["latest_failed_dispatch_summary_count"] == 2
    assert summary["latest_executor_handoff_trace_count"] == 1
    assert summary["latest_typed_family_count"] == 3
    assert summary["latest_typed_contract_count"] == 2
    assert snapshot.projection_refs == ["generation_agent:generation-r1", "audit_agent:audit-r1"]
    assert snapshot.handoff_refs == ["handoff-001"]
    assert "dispatch-patch-001" in snapshot.dispatch_refs
    assert snapshot.failed_dispatch_refs == ["dispatch-deploy-001", "dispatch-attack-002"]
    assert len(snapshot.dispatch_summaries) == 6
    assert snapshot.failed_dispatch_summaries[0].dispatch_id == "dispatch-deploy-001"
    assert snapshot.failed_dispatch_summaries[0].failure_category == "executor_handoff_required"
    assert snapshot.executor_handoff_trace_summaries[0].dispatch_id == "dispatch-deploy-001"
    assert snapshot.executor_handoff_trace_summaries[0].trace_status == "handoff_required"
    assert snapshot.executor_handoff_trace_summaries[0].artifact_sync_ref == "sync:dispatch-deploy-001"
    assert snapshot.executor_handoff_trace_summaries[0].receipt_status == "handoff_required"
    assert snapshot.typed_family_counts["reflection"] == 1
    assert snapshot.typed_contract_counts["reflection:reflection_memory:v1"] == 1
    assert "proposal:artifact-001" in snapshot.artifact_lookup_refs
    assert "artifact:patch_manifest.json" in snapshot.artifact_lookup_refs
    assert "artifact:rollback_manifest.json" in snapshot.metadata["patch_execution_artifact_refs"]
    assert snapshot.evidence_lookup_refs == ["doc-001:chunk-001"]
    assert snapshot.metadata["dominant_memory_family"] == "reflection"
    assert snapshot.metadata["dominant_memory_contract"] == "reflection:reflection_memory:v1"
    assert snapshot.metadata["typed_contract_count"] == 2
    assert snapshot.metadata["dispatch_ref_count"] == 6
    assert snapshot.metadata["failed_dispatch_ref_count"] == 2
    assert snapshot.metadata["executor_handoff_trace_count"] == 1
    assert snapshot.metadata["patch_execution_artifact_ref_count"] == 5
    assert snapshot.metadata["dispatch_catalog"]
    assert snapshot.metadata["retry_window_count"] == 3
    assert snapshot.metadata["retry_handoff_count"] == 3
    assert snapshot.metadata["retry_compression_policies"] == [
        "retain_summary_and_refs_drop_raw_details"
    ]
    assert snapshot.metadata["retry_resume_checkpoint_refs"] == [
        "checkpoint:patch_reflection:retry-r1"
    ]
    assert snapshot.metadata["retry_resume_input_refs"] == [
        "resume-input:attack-planning-r2",
        "resume-input:vulnerability-r2",
    ]
    timeline = service.load("case-001")
    assert timeline is not None
    assert timeline.latest_run_id == "run-001"
    assert timeline.version_lineage[0].patched_version == "v2"
    assert any(event.stage == "memory_bus" for event in timeline.events)
    assert any(event.event_kind == "typed_memory_family" for event in timeline.events)
    assert any(event.event_kind == "attack_decision" for event in timeline.events)
    assert any(event.event_kind == "vulnerability_verdict" for event in timeline.events)
    assert any(event.event_kind == "patch_plan" for event in timeline.events)
    assert any(event.event_kind == "patch_execution" for event in timeline.events)
    assert any(event.event_kind == "sandbox_dispatch" for event in timeline.events)
    assert any(event.event_kind == "sandbox_dispatch_failure" for event in timeline.events)
    assert any(event.event_kind == "reflection_output" for event in timeline.events)
    assert any(event.event_kind == "memory_card_contract" for event in timeline.events)
    assert any(event.event_kind == "typed_card_contract" for event in timeline.events)

    patch_execution_event = next(
        event for event in timeline.events if event.event_kind == "patch_execution"
    )
    assert patch_execution_event.metadata["execution_contract_version"] == "v1"
    assert "artifact:patch_manifest.json" in patch_execution_event.metadata["artifact_refs"]
    assert patch_execution_event.metadata["patch_dispatch_id"] == "dispatch-patch-001"

    failed_dispatch_event = next(
        event for event in timeline.events if event.event_kind == "sandbox_dispatch_failure"
    )
    assert failed_dispatch_event.metadata["dispatch_id"] == "dispatch-deploy-001"
    assert failed_dispatch_event.metadata["failure_category"] == "executor_handoff_required"
    assert "artifact:service_manifest.json" in failed_dispatch_event.metadata["artifact_refs"]

    overview = service.get_timeline_summary("case-001")
    assert overview is not None
    assert overview["timeline_summary"]["latest_typed_contract_count"] == 2
    assert overview["timeline_summary"]["latest_dispatch_ref_count"] == 6
    assert overview["timeline_summary"]["latest_failed_dispatch_ref_count"] == 2
    assert overview["timeline_summary"]["latest_dispatch_summary_count"] == 6
    assert overview["timeline_summary"]["latest_failed_dispatch_summary_count"] == 2
    assert overview["timeline_summary"]["latest_executor_handoff_trace_count"] == 1
    assert overview["latest_snapshot"]["snapshot_id"] == "snapshot-run-001"
    assert overview["latest_snapshot"]["dispatch_summaries"]
    assert overview["latest_snapshot"]["failed_dispatch_summaries"][0]["dispatch_id"] == "dispatch-deploy-001"
    assert overview["latest_snapshot"]["executor_handoff_trace_summaries"][0]["handoff_ref"] == "handoff:dispatch-deploy-001"
    assert overview["latest_version_lineage"]["patched_version"] == "v2"

    memory_bus_events = service.query_events("case-001", stage="memory_bus", limit=10)
    assert memory_bus_events
    assert all(item.stage == "memory_bus" for item in memory_bus_events)

    contract_events = service.query_events(
        "case-001",
        contract_ref="reflection:reflection_memory:v1",
        limit=10,
    )
    assert contract_events
    assert all(
        (
            event.metadata.get("contract_ref") == "reflection:reflection_memory:v1"
            or event.metadata.get("typed_contract_ref") == "reflection:reflection_memory:v1"
        )
        for event in contract_events
    )

    artifact_scoped_events = service.query_events(
        "case-001",
        artifact_lookup_ref="artifact:patch_manifest.json",
        limit=5,
    )
    assert artifact_scoped_events
    assert any(event.event_kind == "patch_execution" for event in artifact_scoped_events)

    projection_scoped_events = service.query_events(
        "case-001",
        projection_ref="generation_agent:generation-r1",
        limit=5,
    )
    assert projection_scoped_events
    assert all(event.run_id == "run-001" for event in projection_scoped_events)

    handoff_scoped_events = service.query_events(
        "case-001",
        handoff_ref="handoff-001",
        limit=5,
    )
    assert handoff_scoped_events
    assert all(event.run_id == "run-001" for event in handoff_scoped_events)

    contract_snapshots = service.query_snapshots(
        "case-001",
        contract_ref="decision:attack_decision:v1",
        limit=5,
    )
    assert len(contract_snapshots) == 1
    assert contract_snapshots[0].snapshot_id == "snapshot-run-001"

    artifact_snapshots = service.query_snapshots(
        "case-001",
        artifact_lookup_ref="artifact:patch_manifest.json",
        limit=5,
    )
    assert len(artifact_snapshots) == 1
    assert artifact_snapshots[0].run_id == "run-001"

    projection_snapshots = service.query_snapshots(
        "case-001",
        projection_ref="generation_agent:generation-r1",
        limit=5,
    )
    assert len(projection_snapshots) == 1
    assert projection_snapshots[0].run_id == "run-001"

    handoff_snapshots = service.query_snapshots(
        "case-001",
        handoff_ref="handoff-001",
        limit=5,
    )
    assert len(handoff_snapshots) == 1
    assert handoff_snapshots[0].run_id == "run-001"

    retry_checkpoint_snapshots = service.query_snapshots(
        "case-001",
        retry_resume_checkpoint_ref="checkpoint:patch_reflection:retry-r1",
        limit=5,
    )
    assert retry_checkpoint_snapshots
    assert all(item.run_id == "run-001" for item in retry_checkpoint_snapshots)

    retry_input_snapshots = service.query_snapshots(
        "case-001",
        retry_resume_input_ref="resume-input:attack-planning-r2",
        limit=5,
    )
    assert retry_input_snapshots
    assert all(item.run_id == "run-001" for item in retry_input_snapshots)

    retry_checkpoint_events = service.query_events(
        "case-001",
        retry_resume_checkpoint_ref="checkpoint:patch_reflection:retry-r1",
        limit=10,
    )
    assert retry_checkpoint_events
    assert all(item.run_id == "run-001" for item in retry_checkpoint_events)

    retry_input_events = service.query_events(
        "case-001",
        retry_resume_input_ref="resume-input:attack-planning-r2",
        limit=10,
    )
    assert retry_input_events
    assert all(item.run_id == "run-001" for item in retry_input_events)

    drilldown = service.get_timeline_drilldown(
        "case-001",
        artifact_lookup_ref="artifact:patch_manifest.json",
        limit=10,
    )
    assert drilldown is not None
    assert drilldown["scope"]["artifact_lookup_ref"] == "artifact:patch_manifest.json"
    assert drilldown["summary"]["matched_run_ids"] == ["run-001"]
    assert drilldown["summary"]["snapshot_count"] == 1
    assert drilldown["summary"]["event_count"] >= 1
    assert drilldown["summary"]["version_lineage_count"] == 1
    assert "dispatch-patch-001" in drilldown["summary"]["dispatch_refs"]
    assert "dispatch-attack-002" in drilldown["summary"]["failed_dispatch_refs"]
    assert drilldown["summary"]["dispatch_summaries"]
    assert drilldown["summary"]["failed_dispatch_summaries"][0]["dispatch_id"] == "dispatch-deploy-001"
    assert drilldown["summary"]["executor_handoff_trace_summaries"][0]["dispatch_id"] == "dispatch-deploy-001"
    assert "artifact:patch_manifest.json" in drilldown["summary"]["artifact_lookup_refs"]
    assert drilldown["summary"]["retry_window_count"] == 3
    assert drilldown["summary"]["retry_handoff_count"] == 3
    assert drilldown["summary"]["retry_projection_refs"] == [
        "attack_planning_agent:attack-plan-r2",
        "vulnerability_agent:vulnerability-r2",
        "expert_gate_agent:expert-gate-r2",
    ]
    assert drilldown["summary"]["retry_compression_policies"] == [
        "retain_summary_and_refs_drop_raw_details"
    ]
    assert drilldown["summary"]["retry_resume_checkpoint_refs"] == [
        "checkpoint:patch_reflection:retry-r1"
    ]
    assert drilldown["summary"]["retry_resume_input_refs"] == [
        "resume-input:attack-planning-r2",
        "resume-input:vulnerability-r2",
    ]
    assert drilldown["service_trajectories"]
    assert drilldown["service_trajectories"][0]["target_service_ref"] == "svc-1"
    assert "patch_execution" in drilldown["service_trajectories"][0]["event_kind_counts"]
    assert "sandbox_dispatch_failure" in drilldown["service_trajectories"][0]["event_kind_counts"]
    assert drilldown["snapshots"][0]["run_id"] == "run-001"
    assert drilldown["events"]
    assert drilldown["version_lineage"][0]["run_id"] == "run-001"

    retry_checkpoint_drilldown = service.get_timeline_drilldown(
        "case-001",
        retry_resume_checkpoint_ref="checkpoint:patch_reflection:retry-r1",
        limit=10,
    )
    assert retry_checkpoint_drilldown is not None
    assert (
        retry_checkpoint_drilldown["scope"]["retry_resume_checkpoint_ref"]
        == "checkpoint:patch_reflection:retry-r1"
    )
    assert retry_checkpoint_drilldown["summary"]["matched_run_ids"] == ["run-001"]
    assert retry_checkpoint_drilldown["snapshots"]
    assert retry_checkpoint_drilldown["events"]

    retry_input_drilldown = service.get_timeline_drilldown(
        "case-001",
        retry_resume_input_ref="resume-input:attack-planning-r2",
        limit=10,
    )
    assert retry_input_drilldown is not None
    assert (
        retry_input_drilldown["scope"]["retry_resume_input_ref"]
        == "resume-input:attack-planning-r2"
    )
    assert retry_input_drilldown["summary"]["matched_run_ids"] == ["run-001"]
    assert retry_input_drilldown["snapshots"]
    assert retry_input_drilldown["events"]


def test_case_timeline_service_queries_version_lineage(tmp_path):
    service = CaseTimelineService(storage_dir=tmp_path)

    service.record_run(
        case_id="case-lineage-001",
        run_id="run-101",
        delivery={
            "status": "patched",
            "attack_loop": {
                "target_service": {"service_id": "svc-alpha", "service_version": "v1"},
                "regression_target_service": {"service_id": "svc-alpha", "service_version": "v2"},
                "patch_spec": {
                    "patch_id": "patch-alpha",
                    "next_version": "v2",
                },
            },
        },
        control_plane={"summary": {"stage_count": 1}},
        execution_plane={"summary": {"stage_count": 0}, "stages": []},
        memory_bus={},
    )
    service.record_run(
        case_id="case-lineage-001",
        run_id="run-102",
        delivery={
            "status": "patched",
            "attack_loop": {
                "target_service": {"service_id": "svc-beta", "service_version": "v2"},
                "regression_target_service": {"service_id": "svc-beta", "service_version": "v3"},
                "patch_spec": {
                    "patch_id": "patch-beta",
                    "next_version": "v3",
                },
            },
        },
        control_plane={"summary": {"stage_count": 1}},
        execution_plane={"summary": {"stage_count": 0}, "stages": []},
        memory_bus={},
    )

    all_items = service.query_version_lineage("case-lineage-001", limit=10)
    assert len(all_items) == 2
    assert all_items[0].patch_id == "patch-beta"
    assert all_items[1].patch_id == "patch-alpha"

    filtered = service.query_version_lineage(
        "case-lineage-001",
        run_id="run-101",
        target_service_ref="svc-alpha",
        baseline_version="v1",
        patched_version="v2",
        patch_id="patch-alpha",
        limit=10,
    )
    assert len(filtered) == 1
    assert filtered[0].run_id == "run-101"
    assert filtered[0].target_service_ref == "svc-alpha"
    assert filtered[0].baseline_version == "v1"
    assert filtered[0].patched_version == "v2"
    assert filtered[0].created_at is not None
