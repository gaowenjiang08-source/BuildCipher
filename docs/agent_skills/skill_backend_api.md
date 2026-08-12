# Skill: Backend API (FastAPI + Schema)

## When To Use

- 你要新增/修改接口、请求结构、返回字段、流式事件协议
- 前端报错提示“字段不存在/类型不一致”

## Key Files

- `src/cipher_genius/api/main.py`: FastAPI 路由入口（含 MAS/Skill streaming NDJSON）
- `src/cipher_genius/api/schemas.py`: 请求/响应 schema（前后端契约的源头）
- `src/cipher_genius/api/service.py`: `/api/v1/generate` 业务服务
- `src/cipher_genius/api/mas_service.py`: Legacy MAS 服务实现
- `src/cipher_genius/api/skill_service.py`: Skill 执行服务（manifest + 路由 + MAS 增强）
- `src/cipher_genius/api/report_service.py`: MAS 报告聚合与企业交付模板输出
- `src/cipher_genius/api/benchmark_service.py`: 建筑工程 benchmark API 服务
- `src/cipher_genius/api/knowledge_ingestion_service.py`: 上传式知识导入、manifest 记录与知识资产列表
- `frontend/src/api/client.js`: 前端 API 调用路径（需要一起对齐）

## Invariants (不要破坏)

- `schemas.py` 是契约：字段改名/删除必须同步更新前端与文档
- 当前面向中国企业的用户可见文本默认中文优先，但 `template_id` / `skill_id` / `scenario` 等稳定字段仍保持英文标识
- 如果同一字段既要服务程序逻辑又要服务中文展示，优先新增 `*_label` 字段，不要直接把稳定字段值改成本地化文案
- `llm_provider` 输入会被规范化为小写（允许 `OpenAI` / `OPENAI` 等）
- 对于 `/api/v1/generate`、`/api/v1/mas/*`、`/api/v1/skills/execute|stream`：
  - 未知 `llm_provider` 会返回 400
  - 已知 provider 但缺少 key 时，MAS 走回退路径仍可运行（离线/可复现实验）
- `POST /api/v1/mas/execute` 与 `POST /api/v1/mas/stream` 当前默认走 LangGraph 主线，并会额外返回：
  - `delivery.engine = "langgraph"`
  - `delivery.engine_mode = "graph-native"`
  - `delivery.workflow_trace = ["analyst", "context_builder", "architect", "audit", "engineer", "target_deployer", "attack_executor", "vulnerability_evaluation", "patch_reflection", "delivery"]`
  - 顶层 `evidence_pack` 与 `delivery.evidence_pack`
  - `delivery.attack_loop`
    - `target_service`
    - `attack_specs`
    - `attack_results`
    - `vulnerability_verdict`
    - `expert_gate_decision`
    - `patch_spec`
- 对于 replay/timeline 查询接口：
  - `GET /api/v1/cases/{case_id}/timeline/events|snapshots|drilldown`
  - 当前额外支持 `retry_resume_checkpoint_ref / retry_resume_input_ref`
  - 语义是“按恢复点回看同 run replay 数据”，不是自动恢复执行
  - `events` / `snapshots` 若新增了过滤参数，优先同步回显到响应 `scope`，方便前端解释当前查询来源
  - 当前前端 API client 也应保持对 `events / snapshots / drilldown / lineage` 四类查询入口的对齐封装
    - `reflection_cards`
  - `delivery.context_projections.expert_gate`
  - `delivery.code_artifacts`
  - 缓存命中时 `delivery.cache_hit = true`
  - 当前上述 attack-loop 字段已接入本地文件沙盒工件，但仍不应在文档中误写成“真实网络隔离 sandbox 已落地”
- `POST /api/v1/skills/execute|stream` 当前仍保留请求体字段 `use_langgraph`
  - 该字段仅作为兼容字段保留，不再切换到 Legacy 执行路径
  - 嵌套 MAS 统一沿用 LangGraph 主线
  - 最终 `result.delivery.engine` / `result.delivery.engine_mode` 同样可用于前端展示与调试
- Streaming 协议为 NDJSON：每行一个 JSON，对应 `type`:
  - `run`: `{type, run_id, engine?}`
  - `progress`: `{type, data}`
  - `final`: `{type, data}`
  - `error` / `cancelled`

## Common Changes

- 新增 endpoint：
  - 在 `schemas.py` 先加 Request/Response 模型
  - 在 `api/main.py` 注册路由并指定 `response_model=...`
  - 前端在 `frontend/src/api/client.js` 增加调用
- 知识导入链新增或调整时：
  - 同步检查 `POST /api/v1/knowledge/ingest`
  - 同步检查 `DELETE /api/v1/knowledge/ingest/{request_id}`
  - 同步检查 `POST /api/v1/knowledge/ingest/{request_id}/qdrant`
  - 同步检查 `DELETE /api/v1/knowledge/ingest/{request_id}/qdrant`
  - 同步检查 `GET /api/v1/knowledge/ingestions`
  - 若新增记录字段，保持上传结果与资产列表都能复用同一份稳定 schema
  - 若新增治理字段，优先写入 manifest，而不是只靠前端临时推断状态；当前资产治理已包含 `qdrant_deleted_at`
- 调整报告/benchmark 字段：
  - 优先查看 `docs/agent_skills/skill_benchmark_reporting.md`
  - 保持 `MASReportResponse` / `BenchmarkRunResponse` 与测试同步
- 修改返回字段：
  - 先改 `schemas.py`
  - 再改服务层（`service.py` / `mas_service.py` / `skill_service.py`）
  - 再改前端渲染（通常在 `frontend/src/App.jsx`）
  - 如果涉及 `TargetServiceSpec / AttackSpec / AttackResultSpec / VulnerabilityVerdictSpec / PatchSpec`，同步检查 `tests/api/test_api_mas.py`

## Verification

- 运行后端：`poetry run cipher-genius-api`
- 打开 Swagger：`http://127.0.0.1:8000/docs`
- 单测：`poetry run pytest tests/unit -q`
- 流式接口自测：前端 “Execute Stream” 或用 curl 读 NDJSON

## Docs To Update (按 AGENTS.md)

- `README.md`
- `QUICK_START_V3.md`
- `docs/TECHNICAL_DOCUMENTATION.md`

## 增量更新：Replay / Timeline Retry 恢复点（2026-04-06）

- 当前 `ReplaySnapshotSummaryPayload.metadata` 会带出 retry 恢复点与压缩摘要：
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
- 当前 `CaseTimelineDrilldownSummaryPayload` 也已新增同名 `retry_*` 字段。
- 正确口径：
  - 这是 replay / drilldown 查询契约增强
  - 不是自动恢复执行契约


## Case Memory ???2026-03-24?

- `MASRequest.case_id` / `SkillExecuteRequest.case_id` ????
- `MASResponse` ?????? `case_id`?`case_memory`?
- ?? `GET /api/v1/cases/{case_id}`?
- ???????????????? `tests/api/test_api_mas.py` ? LangGraph ???
## 增量更新：Case Catalog（2026-03-24）

- 当前新增 `GET /api/v1/cases`
- 用途：返回最近项目的轻量 summary，供前端工作台切换项目
- 相关 schema：
  - `CaseMemorySummaryPayload`
  - `CaseListResponse`
- 注意：
  - `GET /api/v1/cases/{case_id}` 仍然返回完整 `CaseMemoryPayload`
  - 前端切换项目优先依赖 summary 列表，不要把完整 case 快照直接塞进列表接口

## 增量更新：Replay Query API（2026-03-30）

- 当前新增：
  - `GET /api/v1/cases/{case_id}/timeline`
  - `GET /api/v1/cases/{case_id}/timeline/events`
  - `GET /api/v1/cases/{case_id}/timeline/snapshots`
  - `GET /api/v1/cases/{case_id}/timeline/drilldown`
  - `GET /api/v1/cases/{case_id}/timeline/lineage`
- 新增 schema：
  - `CaseTimelineSummaryPayload`
  - `ReplaySnapshotSummaryPayload`
  - `ReplayVersionLineagePayload`
  - `CaseTimelineOverviewResponse`
  - `CaseTimelineEventPayload`
  - `CaseTimelineEventListResponse`
  - `CaseTimelineSnapshotListResponse`
  - `CaseTimelineLineageListResponse`
  - `CaseTimelineDrilldownScopePayload`
  - `CaseTimelineDrilldownSummaryPayload`
  - `CaseTimelineRelationPayload`
  - `CaseTimelineDrilldownResponse`
- 其中 `ReplayVersionLineagePayload` 现已稳定带出：
  - `run_id`
  - `created_at`
- 当前支持的轻量过滤：
  - `event_kind`
  - `stage`
  - `contract_ref`
  - `lineage_ref`
  - `projection_ref`
  - `handoff_ref`
  - `artifact_lookup_ref`
  - `evidence_lookup_ref`
  - `run_id`
  - `target_service_ref`
  - `patch_id`
  - `baseline_version`
  - `patched_version`
- 口径边界：
  - 这是单 case、本地 timeline replay 查询起点
  - 也是单 case、本地 version lineage 查询起点
  - 也是沿独立上下文窗口与 handoff 做单 case drill-down 的查询起点
  - `timeline/drilldown` 只做单 case、本地聚合回看，不代表完整 replay center
  - `timeline/drilldown` 现会额外返回 `projection_relationships / handoff_relationships / service_trajectories`
  - `handoff_relationships` 应按“已落盘 handoff 摘要恢复的上下游关系”理解，包含 `source_agent_id / target_agent_id / upstream_stage / downstream_stage / handoff_projection_ref / dominant_typed_contract`
  - `service_trajectories` 应按“单 case、本地 target service 攻击与修补轨迹摘要”理解
  - 关系视图来自 snapshot metadata 中的 `window_catalog / handoff_catalog`，不要写成跨 case 推理图
  - 不要把它写成完整 replay center API 或跨 case 审计检索平台

## 增量更新：Attack Loop Regression（2026-03-26）

- `delivery.attack_loop` 当前除旧字段外，还会追加：
  - `regression_target_service`
  - `regression_attack_specs`
  - `regression_attack_results`
  - `regression_vulnerability_verdict`
- 当前稳定轮次语义应为：
  - `rounds[0].round_kind = "baseline"`
  - `rounds[1].round_kind = "regression"`
  - `rounds[1].mode = "executed"`
  - `rounds[1].patch_applied = true`
- 若你修改这些字段，记得同步检查：
  - `tests/api/test_api_mas.py`
  - `tests/integration/test_langgraph_mas.py`
  - `frontend/src/features/mas/useMasDerivedState.js`

## Incremental Update: Context Projection Schemas（2026-03-26）

- `schemas.py` now also includes:
  - `ArtifactRefPayload`
  - `EvidenceRefPayload`
  - `ContextConstraintPayload`
  - `MemoryCardPayload`
  - `ContextProjectionPayload`
  - `MemoryHandoffPayload`
- Use these models when you need to formalize:
  - independent agent context windows
  - structured memory handoff between agents
- Current boundary:
  - schema layer is ready
  - runtime orchestration now emits additive `delivery.context_projections` and `delivery.memory_handoffs`
  - full projection-only agent consumption is still pending

## 增量更新：后端执行架构优先级（2026-03-26）

- 当前若任务目标是“先把后端架构完成”，优先阅读：
  - `docs/modules/backend_execution_architecture.md`
  - `docs/modules/mas_workflow.md`
  - `docs/modules/case_memory.md`
- 当前接口与 schema 侧最重要的不是继续堆前端展示字段，而是先把以下边界收口稳定：
  - `ContextProjectionPayload`
  - `MemoryHandoffPayload`
  - `ArtifactRefPayload` / `EvidenceRefPayload`
  - 未来 `Sandbox Dispatcher` 的请求 / 响应 schema
- 推荐顺序：
  - 先保证后端执行架构稳定
  - 再推进 `projection-only`
  - 再设计 `Sandbox Dispatcher` 契约
  - 最后再让前端消费稳定对象

## 增量更新：Sandbox Dispatcher（2026-03-26）

- `schemas.py` 现已新增：
  - `SandboxPolicyPayload`
  - `SandboxDispatchRequestPayload`
  - `SandboxDispatchResultPayload`
  - `SandboxFailurePayload`
  - `SandboxAuditEventPayload`
- `langgraph_mas.py` 当前已把 baseline / regression 两轮的 deployment 与 attack execution 接到 `LocalSandboxDispatcher`
- 当前 MAS 返回体已增量暴露：
  - `delivery.sandbox_dispatcher.policy`
  - `delivery.sandbox_dispatcher.baseline_deployment`
  - `delivery.sandbox_dispatcher.baseline_attack`
  - `delivery.sandbox_dispatcher.regression_deployment`
  - `delivery.sandbox_dispatcher.regression_attack`
- 当前 dispatch 结果还会暴露：
  - `failure_items`
  - `audit_trail`
- 如果你修改这些字段，记得同步检查：
  - `tests/unit/test_sandbox_dispatcher.py`
  - `tests/integration/test_langgraph_mas.py`
  - `tests/api/test_api_mas.py`

## 增量更新：Executor Handoff Skeleton（2026-04-03）

- `schemas.py` 当前已新增：
  - `ExecutorHandoffRequestPayload`
  - `ExecutorArtifactSyncManifestPayload`
  - `ExecutorHandoffReceiptPayload`
  - `ExecutorHandoffTracePayload`
- `SandboxDispatchRequestPayload / SandboxDispatchResultPayload` 当前还会继续带出：
  - `governance_mode`
  - `artifact_refs`
  - `handoff_request`
  - `artifact_sync_manifest`
  - `handoff_receipt`
  - `handoff_trace`
- 当前边界：
  - 这是 typed handoff contract skeleton
  - 不是远程执行 API、容器执行 API 或回执中心已经完成
- 如果你修改这些字段，记得同步检查：
  - `tests/unit/test_sandbox_dispatcher.py`
  - `README.md`
  - `QUICK_START_V3.md`
  - `docs/TECHNICAL_DOCUMENTATION.md`
  - `src/cipher_genius/api/README.md`

## 增量更新：Projection-Only Main Path（2026-03-26）

- `langgraph_mas.py` 当前已让后半段 4 个节点优先从 projection 恢复输入：
  - `attack_planning`
  - `vulnerability_evaluation`
  - `patch`
  - `reflection`
- 当前 `delivery.context_projections` 中这 4 个对象，已不只是调试输出，也是在运行时承载主输入边界。
- 若你修改这些对象的 `cards / artifact_refs / metadata`，记得同步检查：
  - `tests/integration/test_langgraph_mas.py`
  - `tests/api/test_api_mas.py`
  - `docs/modules/backend_execution_architecture.md`

## 增量更新：Patch Spec Additive Fields（2026-03-28）

- `PatchSpecPayload` 当前已新增：
  - `rationale`
  - `implementation_notes`
  - `validation_steps`
  - `rollback_notes`
- 当前这些字段会出现在：
  - `delivery.attack_loop.patch_spec`
- 兼容边界：
  - 这是 additive schema update
  - 既有 `strategy / summary / changed_artifacts / next_version / regression_focus` 保持不变
- 如果你修改这些字段，记得同步检查：
  - `tests/unit/test_patch_planning_agent.py`
  - `tests/api/test_api_mas.py`
  - `tests/integration/test_langgraph_mas.py`
  - `README.md`
  - `QUICK_START_V3.md`
  - `docs/TECHNICAL_DOCUMENTATION.md`

## 增量更新：Patch Execution Additive Fields（2026-03-29）

- `schemas.py` 当前已新增：
  - `PatchValidationResultPayload`
  - `PatchExecutionPayload`
- 当前这些字段会出现在：
  - `delivery.attack_loop.patch_execution`
  - `delivery.attack_loop.rounds[1].patch_execution`
  - `delivery.context_projections.reflection.cards[*].payload`
- 当前重点字段包括：
  - `status / status_label / summary`
  - `workspace`
  - `deployment_dispatch_id / regression_dispatch_id`
  - `validation_steps / validation_results`
  - `changed_artifact_summaries / diff_preview`
- 兼容边界：
  - 这是 additive schema update
  - 不要把它写成“完整远程 patch 执行 API”
- 如果你修改这些字段，记得同步检查：
  - `tests/unit/test_patch_execution_report.py`
  - `tests/api/test_api_mas.py`
  - `tests/integration/test_langgraph_mas.py`
  - `README.md`
  - `QUICK_START_V3.md`
  - `docs/TECHNICAL_DOCUMENTATION.md`
  - `src/cipher_genius/api/README.md`

## 增量更新：Patch Execution Typed Validation（2026-03-29）

- `PatchValidationResultPayload` 当前还已新增：
  - `step_id`
  - `step_kind`
  - `evidence`
  - `artifact_refs`
  - `metadata`
- `PatchExecutionPayload` 当前还已新增：
  - `validation_summary`
  - `supporting_artifact_summaries`
  - `artifact_inventory`
- 如果你改这些字段，优先检查：
  - `src/cipher_genius/core/langgraph_mas.py`
  - `src/cipher_genius/core/artifact_summarizer.py`
  - `tests/unit/test_patch_execution_report.py`

## 增量更新：Expert Gate Additive Contract（2026-04-05）

- `schemas.py` 当前已新增：
  - `ExpertGateDecisionPayload`
- 当前这些字段会出现在：
  - `delivery.context_projections.expert_gate`
  - `delivery.attack_loop.expert_gate_decision`
  - `delivery.attack_loop.rounds[0].expert_gate_decision`
  - `delivery.context_projections.patch.cards[*].card_type = "expert_gate_decision"`
- 当前重点字段包括：
  - `decision_family / decision_family_label`
  - `action / action_label`
  - `route_target / route_target_label`
  - `rationale`
  - `confidence`
  - `residual_risk_summary`
  - `follow_up_actions`
- 兼容边界：
  - 当前已完成 typed decision family / route target 第一版 additive contract
  - 这是 additive schema update
  - 不要把它写成“完整多分支 expert orchestration API”
- 当前如果 workflow 触发 `route_target = "attack_planning_agent"`，`delivery.attack_loop` 还会追加：
  - `retry_attack_decision / retry_attack_specs / retry_attack_results / retry_vulnerability_verdict`
- 当前如果 workflow 触发 same-run retry，`delivery.sandbox_dispatcher.retry_attack` 也应同步联调
- 如果你修改这些字段，记得同步检查：
  - `tests/unit/test_expert_gate_agent.py`
  - `tests/unit/test_patch_planning_agent.py`
  - `tests/integration/test_langgraph_mas.py`
  - `tests/api/test_api_mas.py`
  - `README.md`
  - `QUICK_START_V3.md`
  - `docs/TECHNICAL_DOCUMENTATION.md`
  - `src/cipher_genius/api/README.md`

## 增量更新：Backend Architecture Summary（2026-03-29）

- `delivery` 当前已新增：
  - `backend_architecture.control_plane`
  - `backend_architecture.memory_bus`
  - `backend_architecture.execution_plane`
  - `backend_architecture.replay_plane`
- 当前对应的第一批骨架代码包括：
  - `src/cipher_genius/core/control_plane.py`
  - `src/cipher_genius/core/context_bus.py`
  - `src/cipher_genius/sandbox/execution_plane.py`
  - `src/cipher_genius/memory/replay_service.py`
- 当前 replay plane 会把 run 级 snapshot 写入：
  - `.cache/case_timelines/`
- 兼容边界：
  - 这是 additive 架构摘要
  - 不要把它写成完整生产级 control plane / replay center API
- 如果你修改这些字段，记得同步检查：
  - `src/cipher_genius/api/README.md`
  - `src/cipher_genius/core/README.md`
  - `src/cipher_genius/sandbox/README.md`
  - `src/cipher_genius/memory/README.md`
  - `docs/modules/backend_execution_architecture.md`
  - `tests/unit/test_case_timeline_service.py`

## 增量更新：Control Plane Contract（2026-03-29）

- `delivery.backend_architecture.control_plane` 当前已新增：
  - `summary.contract_version`
  - `summary.retryable_stage_count`
  - `invocations[*].depends_on`
  - `invocations[*].checkpoint_ref`
  - `invocations[*].result_ref`
  - `invocations[*].retryable / retry_strategy / termination_mode / decision_source`
  - `invocations[*].contract`
  - `checkpoints[*].input_refs / output_refs / next_stages`
  - `checkpoints[*].retryable / failure_action / termination_signal / decision_source`
  - `results[*].primary_output_ref / decision_signal`
  - `results[*].decision_source / termination_signal / failure_action`
- 当前这是 additive 的摘要字段扩展，不影响既有主契约。

## 增量更新：Memory Bus Typed Family（2026-03-29）

- `delivery.backend_architecture.memory_bus` 当前已新增：
  - `windows[*].window_ref`
  - `windows[*].card_family_counts`
  - `windows[*].dominant_card_family`
  - `windows[*].lineage_refs`
  - `windows[*].typed_contract_counts`
  - `windows[*].dominant_typed_contract`
  - `windows[*].artifact_lookup_refs / evidence_lookup_refs`
  - `handoffs[*].projection_ref`
  - `handoffs[*].card_family_counts`
  - `handoffs[*].dominant_card_family`
  - `typed_families[*]`
  - `typed_contracts[*]`
  - `replay_snapshot_card.typed_family_counts`
- `delivery.context_projections.generation|audit.cards[*].payload` 当前已稳定附带：
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
- 当前这是 additive 摘要字段扩展，不影响既有主契约。
