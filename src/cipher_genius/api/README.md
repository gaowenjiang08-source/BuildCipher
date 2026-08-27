# API 模块说明

## 2026-04-06 Replay / Timeline Retry 查询契约补记

- 当前 timeline 总览接口会在 `latest_snapshot.metadata` 中暴露 retry 恢复点摘要：
  - `retry_window_count`
  - `retry_handoff_count`
  - `retry_projection_refs`
  - `retry_handoff_refs`
  - `retry_lineage_refs`
  - `retry_typed_contract_refs`
  - `retry_compression_stages`
  - `retry_compression_policies`
  - `retry_retained_refs`
  - `retry_resume_checkpoint_refs`
  - `retry_resume_input_refs`
- 当前 `GET /api/v1/cases/{case_id}/timeline/drilldown` 的 `summary` schema 也已新增同一批 `retry_*` 字段。
- 当前 `GET /api/v1/cases/{case_id}/timeline/events|snapshots|drilldown` 还支持查询参数：
  - `retry_resume_checkpoint_ref`
  - `retry_resume_input_ref`
  用于按恢复点做 replay scope drilldown。
- 当前 `timeline/events` 与 `timeline/snapshots` 响应已新增：
  - `scope`
  用于回显本次查询实际采用的过滤条件。
- 当前正确口径：
  - 这些字段用于 replay / drilldown 查询
  - 不是 runtime 自动恢复执行接口

## 2026-04-06 Same-Run Retry 预算接口补记

- 当前请求侧新增：
  - `MASRequest.max_same_run_retries`
  - `SkillExecuteRequest.max_same_run_retries`
- 当前参数约束：
  - 默认 `null`，由服务端回退到 `SAME_RUN_RETRY_BUDGET_DEFAULT`
  - 显式传参时当前仅允许 `0` 或 `1`
- 当前响应侧新增稳定字段：
  - `delivery.attack_loop.same_run_retry_summary`
  - `delivery.attack_loop.same_run_retry_budget`
  - `delivery.attack_loop.same_run_retry_used`
  - `delivery.attack_loop.same_run_retry_remaining`
- 当前 `same_run_retry_summary` 会返回：
  - `requested / started / blocked_by_budget / capped_after_regate`
  - `initial_route_target / final_route_target`
  - `final_resolution / final_resolution_label`
  - `attempt_count / attempt_trace`
- 当前 `attempt_trace[*]` 会返回：
  - `budget_before_attempt / budget_after_attempt`
  - `status`
  - `dispatch_status`
  - `termination_reason`
  - `planning_projection_ref / vulnerability_projection_ref / expert_gate_projection_ref`
  - `planning_handoff_id / vulnerability_handoff_id / expert_gate_handoff_id`
- 当前 retry 实际执行时，`delivery.context_projections` 还会新增：
  - `attack_planning_retry`
  - `vulnerability_evaluation_retry`
- 当前 `delivery.backend_architecture.memory_bus.summary` 还会新增：
  - `retry_window_count`
  - `retry_handoff_count`
  - `retry_projection_refs`
  - `retry_handoff_refs`
  - `retry_lineage_refs`
  - `retry_typed_contract_refs`
- 当前 retry 窗口中的 `cards[*]` 还会出现：
  - `retry_context_summary`
- 当前该卡的 `payload` 已包含：
  - `compression_policy`
  - `retained_refs`
  - `dropped_detail_hints`
  - `resume_checkpoint_ref`
  - `resume_inputs`
  - `resume_hint`
- 当前 `delivery.backend_architecture.memory_bus.summary` 还会新增：
  - `retry_compression_stages`
  - `retry_compression_policies`
  - `retry_retained_refs`
  - `retry_resume_checkpoint_refs`
  - `retry_resume_input_refs`
- 当前 `delivery.backend_architecture.control_plane.summary.same_run_retry` 与 `results[*].metadata.same_run_retry` 也会透传同一份解释摘要
- 当前行为解释：
  - `0`：关闭 same-run retry
  - `1`：保留一次 same-run retry follow-up
- 当前若预算关闭且 expert gate 仍请求 retry，`delivery.attack_loop.loop_status` 会返回：
  - `baseline_*_retry_blocked_by_budget`
- 当前仍不应写成：
  - 已支持 `>1` 的递归多轮 retry
  - 已完成多轮 expert 子图编排

## 2026-04-05 Expert Gate 有限 Re-Gate 契约补记

- 当前 `MASResponse.delivery.context_projections` 新增：
  - `expert_gate_retry`
- 当前 `MASResponse.delivery.attack_loop` 新增稳定字段：
  - `retry_expert_gate_decision`
- 当前 `delivery.attack_loop.rounds` 在 re-gate 成功进入 patch flow 时，可稳定出现三轮：
  - `baseline`
  - `retry`
  - `regression`
- 当前同轮重试相关状态建议按如下理解：
  - `baseline_executed_retry_executed_delivery_observation`
  - `baseline_executed_retry_executed_regression_executed`
  - `baseline_executed_retry_executed_retry_capped`
- 当前仍不应写成：
  - 已完成递归多轮 re-gate
  - 已完成生产级远程执行平面

最后更新：2026-04-06
状态：active

## 1. 目录职责

本目录负责 BuildCipher Studio 的 FastAPI 接口层、请求与响应 schema，以及对前端和外部调用方暴露的稳定契约。

这里解决的是：

- 请求如何进入系统
- 请求体和返回体长什么样
- LangGraph 主线、Skill 执行、报告导出、benchmark、项目线程与知识导入如何对外暴露

这里不直接负责：

- LangGraph 图内节点实现细节
- 沙盒执行逻辑本体
- 前端展示层

## 2. 当前关键入口

- `main.py`
  - FastAPI 路由入口，包含普通接口与流式 NDJSON 输出
- `schemas.py`
  - 请求/响应 Pydantic 模型，是前后端契约源头
- `service.py`
  - 通用生成接口服务
- `mas_service.py`
  - Legacy MAS 兼容服务实现
- `skill_service.py`
  - Skill 执行服务，负责 manifest、路由与嵌套 MAS 增强
- `report_service.py`
  - 报告聚合、企业交付模板输出与导出
- `benchmark_service.py`
  - benchmark 相关 API 服务
  - `GET /api/v1/benchmarks/construction`
  - `POST /api/v1/construction/assets/import`
  - `POST /api/v1/construction/demo/run`
  - `GET /api/v1/benchmarks/construction`：返回 8 个建筑案例的 Skill 路由、报告模板和章节覆盖回归结果
  - `POST /api/v1/construction/assets/import`：检查并落盘 localhost IFC，返回稳定 `asset_ref`
  - `POST /api/v1/construction/demo/run`：对内置或导入 IFC 执行 baseline/hardened 五攻击对照，返回 evidence、artifact、修补和回归摘要
    - 返回中的 `security_profile` 当前为 `hardened`；该接口展示参考控制效果，不是 MAS 的未修补基线
  - MAS 建筑目标的五攻击结果继续沿用 `AttackResultPayload`，其 `metrics` 提供 `attack_type/detected/blocked/regression_passed/evidence_refs`，`artifact_refs` 提供结果文件和证据账本路径
- `knowledge_ingestion_service.py`
  - 上传式知识导入、manifest 记录与资产列表

## 3. 核心稳定契约

- `schemas.py` 是前后端契约源头，字段改名、删除或类型变化都必须同步前端与文档
- 用户可见文本默认中文优先，但 `template_id`、`skill_id`、`scenario`、API 字段名等稳定标识不要随意改
- 如需同时支持稳定值与中文展示，优先新增 `*_label` 字段
- `/api/v1/mas/execute` 与 `/api/v1/mas/stream` 当前统一走 LangGraph 主线
- `use_langgraph` query / body 字段仅作兼容保留，不再切换到 Legacy 执行路径
- 流式接口协议为 NDJSON，事件类型与结构要保持兼容

## 4. 当前 MAS 返回体重点

当前 `MASResponse` 除既有主结构外，还会稳定返回：

- 顶层 `evidence_pack`
- `delivery.evidence_pack`
- `delivery.workflow_trace`
- `delivery.context_projections`
- `delivery.context_projections.expert_gate`
- `delivery.memory_handoffs`
- `delivery.sandbox_dispatcher`
- `delivery.attack_loop`
- `delivery.code_artifacts`

当前 `delivery.attack_loop` 相关的关键 additive 字段包括：

- `attack_decision`
- `expert_gate_decision`
- `regression_attack_decision`
- `patch_execution`
- `rounds[*].attack_decision`
- `rounds[0].expert_gate_decision`
- `rounds[1].patch_execution`

当前 `patch_execution` 相关 additive schema 包括：

- `PatchValidationResultPayload`
- `PatchExecutionPayload`

其第二阶段增强字段包括：

- `validation_results[*].step_id`
- `validation_results[*].step_kind`
- `validation_results[*].evidence`
- `validation_results[*].artifact_refs`
- `validation_results[*].metadata`
- `validation_summary`
- `supporting_artifact_summaries`
- `artifact_inventory`

## 5. 后端架构摘要字段

本轮已新增一组面向“后端完整架构第一批骨架”的 additive delivery 字段：

- `delivery.backend_architecture.control_plane`
- `delivery.backend_architecture.memory_bus`
- `delivery.backend_architecture.execution_plane`
- `delivery.backend_architecture.replay_plane`

当前这些字段的定位是：

- 给前端、联调与文档提供统一的后端架构摘要
- 暴露第一批控制平面、上下文总线、执行平面、回放平面的最小可观测对象
- 不改变既有 benchmark、报告接口和主消费路径

当前 `control_plane` 这一层还新增了第一版合同字段：

- `summary.contract_version`
- `summary.retryable_stage_count`
- `invocations[*].depends_on / checkpoint_ref / result_ref / contract`
- `invocations[*].retryable / retry_strategy / termination_mode / decision_source`
- `checkpoints[*].input_refs / output_refs / next_stages`
- `checkpoints[*].retryable / failure_action / termination_signal / decision_source`
- `results[*].primary_output_ref / decision_signal`
- `results[*].decision_source / termination_signal / failure_action`

当前仍不能把它们写成：

- “完整生产级 control plane 已完成”
- “完整 replay center 已完成”
- “生产级 execution plane 已完成”

## 6. 当前已落地的相关 schema / 摘要对象

### 6.1 独立上下文窗口与 handoff

当前已落地：

- `ArtifactRefPayload`
- `EvidenceRefPayload`
- `ContextConstraintPayload`
- `MemoryCardPayload`
- `ContextProjectionPayload`
- `MemoryHandoffPayload`

### 6.2 调度与执行

当前已落地：

- `SandboxPolicyPayload`
- `SandboxDispatchRequestPayload`
- `SandboxDispatchResultPayload`
- `SandboxFailurePayload`
- `SandboxAuditEventPayload`

### 6.3 攻击闭环认知对象

当前已落地：

- `AttackDecisionPayload`
- `VulnerabilityVerdictPayload`
- `ExpertGateDecisionPayload`
- `PatchSpecPayload`
- `PatchExecutionPayload`

其中 `ExpertGateDecisionPayload` 当前的定位是：

- 作为 `vulnerability_verdict -> patch_spec` 之间的稳定中间裁决对象
- 通过 additive 方式暴露给 `delivery.attack_loop`、`delivery.context_projections` 与 `PatchPlanningAgent`
- 不改变既有 `MASResponse` 主契约和 `workflow_trace`
- 当前第一版已固定：
  - `decision_family / decision_family_label`
  - `route_target / route_target_label`
- 这组字段当前用于表达 typed route 语义，但不代表完整多分支 orchestration contract 已完成
- 当前 `delivery.attack_loop` 还已新增同轮补充验证对象：
  - `retry_attack_decision / retry_attack_specs / retry_attack_results / retry_vulnerability_verdict`
- 当前 `delivery.sandbox_dispatcher` 还会在 retry 分支下新增：
  - `retry_attack`

### 6.4 补丁执行

当前已落地：

- `PatchValidationResultPayload`
- `PatchExecutionPayload`

### 6.5 Executor Handoff Skeleton

当前已落地：

- `ExecutorHandoffRequestPayload`
- `ExecutorArtifactSyncManifestPayload`
- `ExecutorHandoffReceiptPayload`
- `ExecutorHandoffTracePayload`

当前 `SandboxDispatchRequestPayload / SandboxDispatchResultPayload` 已继续增量带出：

- `governance_mode`
- `artifact_refs`
- `handoff_request`
- `artifact_sync_manifest`
- `handoff_receipt`
- `handoff_trace`

当前这批字段的定位是：

- 给 `container / remote_worker` 预留 typed handoff contract
- 让 dispatcher 不再只返回散的 `handoff_fields`
- 为后续 adapter / replay / 前端透明化复用同一套交接对象

当前仍不能写成：

- 远程执行 API 已完成
- 容器 handoff callback 服务已完成
- artifact sync 中心已完成

## 7. Case 与 Replay 相关接口口径

当前 case 相关接口包括：

- `GET /api/v1/cases`
  - 返回轻量 `CaseListResponse`
- `GET /api/v1/cases/{case_id}`
  - 返回完整 `CaseMemoryPayload`
- `DELETE /api/v1/cases/{case_id}`
  - 删除本地项目快照
- `GET /api/v1/cases/{case_id}/timeline`
  - 返回 `CaseTimelineOverviewResponse`
- `GET /api/v1/cases/{case_id}/timeline/events`
  - 返回 `CaseTimelineEventListResponse`
- `GET /api/v1/cases/{case_id}/timeline/snapshots`
  - 返回 `CaseTimelineSnapshotListResponse`
- `GET /api/v1/cases/{case_id}/timeline/drilldown`
  - 返回 `CaseTimelineDrilldownResponse`
- `GET /api/v1/cases/{case_id}/timeline/lineage`
  - 返回 `CaseTimelineLineageListResponse`
  - `items[*]` 现会带出 `run_id / created_at`

当前 replay plane 现在有两类对外入口：

- 通过 `delivery.backend_architecture.replay_plane` 增量暴露：

- `timeline_summary`
- `latest_snapshot`
- 通过 case 级 replay 查询 API 暴露单 case 的本地 timeline overview / events / snapshots / lineage
  - 其中 `events / snapshots` 现已支持按 `projection_ref / handoff_ref` 做 drill-down
  - `lineage` 现已支持按 `run_id` 过滤，便于与单轮回放对齐
- `timeline/drilldown` 当前会把单个 scope 下的 `snapshots / events / version_lineage` 与关键 refs 摘要聚合返回
  - 同时会返回 `projection_relationships / handoff_relationships / service_trajectories`
  - `handoff_relationships` 当前会带出 `source_agent_id / target_agent_id / upstream_stage / downstream_stage / handoff_projection_ref / dominant_typed_contract`
  - `service_trajectories` 当前按 `target_service_ref` 聚合攻击、评估、补丁与回归关键事件

底层 run 级快照当前写入：

- `.cache/case_timelines/`

## 8. 当前边界

- 当前 attack-loop、dispatcher、patch execution、backend architecture 都属于 additive contract
- 当前沙盒仍是演示级、本地受限进程执行面
- 当前 replay plane 仍是本地 timeline snapshot + query 第一版
- 当前不应把 API 层新增字段误解为远程执行 API、容器沙盒 API 或生产级审计平台 API

## 9. 常见改动点

- 改接口字段或 schema：
  - 先改 `schemas.py`
  - 再改对应服务层
  - 最后改前端读取路径
- 改 MAS 返回结构：
  - 同时检查 `core/langgraph_mas.py`、`frontend/src/api/client.js` 与相关测试
- 改后端架构摘要字段：
  - 同时检查 `src/cipher_genius/core/control_plane.py`
  - `src/cipher_genius/core/context_bus.py`
  - `src/cipher_genius/sandbox/execution_plane.py`
  - `src/cipher_genius/memory/replay_service.py`
  - `docs/modules/backend_execution_architecture.md`

## 10. 验证方式

至少应完成：

- 启动后端并查看 Swagger：`http://127.0.0.1:8000/docs`
- `poetry run pytest tests/api -q`
- 如涉及 MAS 契约：`poetry run pytest tests/api/test_api_mas.py -q`
- 如涉及 patch execution / replay 摘要：
  - `poetry run pytest tests/unit/test_patch_execution_report.py -q --no-cov`
  - `poetry run pytest tests/unit/test_case_timeline_service.py -q --no-cov`

## 11. 相关文档

- `docs/agent_skills/skill_backend_api.md`
- `docs/agent_skills/skill_mas_workflows.md`
- `docs/modules/backend_execution_architecture.md`
- `docs/modules/mas_workflow.md`
- `docs/TECHNICAL_DOCUMENTATION.md`

## 2026-03-29 Memory Bus / Replay 摘要补记

- `delivery.backend_architecture.memory_bus` 当前已新增：
  - `windows[*].window_ref`
  - `windows[*].card_family_counts`
  - `windows[*].dominant_card_family`
  - `windows[*].typed_contract_counts`
  - `windows[*].dominant_typed_contract`
  - `windows[*].artifact_lookup_refs / evidence_lookup_refs`
  - `handoffs[*].projection_ref`
  - `typed_families[*]`
  - `typed_contracts[*]`
  - `replay_snapshot_card.typed_family_counts`
- `delivery.context_projections.generation.cards[*].payload` 与 `delivery.context_projections.audit.cards[*].payload` 当前还会稳定带出：
  - `typed_contract`
  - `typed_contract_ref`
  - `ref_lookup_hint`
- `delivery.backend_architecture.replay_plane` 当前已新增：
  - `latest_snapshot.projection_refs`
  - `latest_snapshot.handoff_refs`
  - `latest_snapshot.typed_family_counts`
  - `latest_snapshot.typed_contract_counts`
  - `latest_snapshot.artifact_lookup_refs / evidence_lookup_refs`
  - `timeline_summary.latest_projection_ref_count`
  - `timeline_summary.latest_handoff_ref_count`
  - `timeline_summary.latest_typed_family_count`
  - `timeline_summary.latest_typed_contract_count`
- run 级 replay snapshot metadata 当前还会保存：
  - `window_catalog[*]`
  - `handoff_catalog[*]`
  - 供 `timeline/drilldown` 在单 case、本地范围内恢复独立上下文窗口与 handoff 关系
- 兼容边界：
  - 这是 additive 观测字段扩展
  - 不要把它写成完整 memory bus API 或 replay center API

## 2026-04-03 Replay Schema 补记

- `src/cipher_genius/api/schemas.py` 当前已对外补充 replay plane 稳定字段：
  - `ReplaySnapshotSummaryPayload.dispatch_refs`
  - `ReplaySnapshotSummaryPayload.failed_dispatch_refs`
  - `CaseTimelineSummaryPayload.latest_dispatch_ref_count`
  - `CaseTimelineSummaryPayload.latest_failed_dispatch_ref_count`
  - `CaseTimelineDrilldownSummaryPayload.dispatch_refs`
  - `CaseTimelineDrilldownSummaryPayload.failed_dispatch_refs`
- 这些字段属于 additive schema 扩展：
  - 不破坏现有 benchmark / 报告接口契约
  - 也不改变 `template_id` / `skill_id` / `scenario` 等稳定程序集成标识

## 2026-04-03 Replay Dispatch API 合同补记

- timeline 相关 schema 当前继续补充：
  - `ReplayDispatchSummaryPayload`
  - `latest_snapshot.dispatch_summaries`
  - `latest_snapshot.failed_dispatch_summaries`
  - `timeline_summary.latest_dispatch_summary_count`
  - `timeline_summary.latest_failed_dispatch_summary_count`
  - `drilldown.summary.dispatch_summaries`
  - `drilldown.summary.failed_dispatch_summaries`
- 这批字段属于 additive schema 扩展，现阶段不替换原有 `dispatch_refs / failed_dispatch_refs`，而是作为更稳定的 typed 回查层。

## 2026-04-03 Replay Executor Handoff Trace Summary

- 当前新增 replay API schema：
  - `ReplayExecutorHandoffTraceSummaryPayload`
- 当前新增 timeline / drilldown 响应字段：
  - `ReplaySnapshotSummaryPayload.executor_handoff_trace_summaries`
  - `CaseTimelineSummaryPayload.latest_executor_handoff_trace_count`
  - `CaseTimelineDrilldownSummaryPayload.executor_handoff_trace_summaries`
- 当前推荐消费顺序：
  1. 先读 typed `executor_handoff_trace_summaries`
  2. 再按需回看原始 `delivery.sandbox_dispatcher.*.handoff_trace`
  3. 不要把这批字段和 `memory_handoffs` 混成同一个概念
