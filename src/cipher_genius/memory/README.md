# Memory 模块说明

最后更新：2026-04-06
状态：active

## 2026-04-06 Replay / Timeline Retry 恢复点补记

- `ReplaySnapshot.metadata` 当前已新增 retry 恢复点与压缩索引：
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
- `timeline/drilldown.summary` 当前也会聚合同一批字段。
- `CaseTimelineService.query_events/query_snapshots/get_timeline_drilldown` 当前已支持：
  - `retry_resume_checkpoint_ref`
  - `retry_resume_input_ref`
  用于从 replay 索引中按恢复点回看同一 run 的事件与快照。
- 当前定位：
  - 这是本地 JSON replay 索引增强
  - 不是自动恢复执行器
  - 不是跨 case 恢复点中心

## 1. 目录职责

本目录负责项目级记忆与回放持久化，目标不是保存整段聊天历史，而是把一个项目线程在多轮运行中的关键状态稳定沉淀下来。

当前已覆盖两类能力：

- `Case Memory`
  - 面向项目级长期记忆
  - 保存约束、阻塞项、拒绝方案、决策日志、最近反思摘要
- `Replay / Timeline`
  - 面向运行级回放与审计轨迹
  - 保存 run 级 snapshot、execution events 与版本谱系

## 2. 当前入口

- `service.py`
  - `CaseMemoryService`
  - 提供 `load / save / load_or_create / fingerprint`
- `replay_service.py`
  - `CaseTimelineService`
  - 提供 `load / load_or_create / record_run / get_timeline_summary / query_events / query_snapshots / query_version_lineage / get_timeline_drilldown`

## 3. 当前持久化对象

### 3.1 Case Memory

当前仍使用本地 `.cache/case_memory/` 持久化，主要沉淀：

- 已确认约束
- 待澄清问题与阻塞项
- 被拒绝方案及原因
- 决策日志
- 最近一次选中提案、合规分、风险分
- `recent_reflections`

这部分对象的定位是“项目状态摘要”，不是运行日志仓库。

### 3.2 Timeline / Replay

当前 `CaseTimelineService` 会把 run 级快照写入：

- `.cache/case_timelines/`

当前会沉淀的对象包括：

- `CaseTimeline`
- `ReplaySnapshot`
- `ExecutionEvent`
- `VersionLineage`

当前 `record_run(...)` 会消费：

- `delivery`
- `control_plane`
- `execution_plane`
- `memory_bus`

并额外生成：

- `timeline_summary`
- `latest_snapshot`
- `latest_version_lineage`

## 4. 与主链的当前接线方式

- `src/cipher_genius/core/langgraph_mas.py`
  - 在一次 MAS 运行开始时创建 `CaseTimelineService()`
  - 在 `delivery` 收口完成后调用 `record_run(...)`
- `delivery.backend_architecture.replay_plane`
  - 当前会增量返回：
    - `timeline_summary`
    - `latest_snapshot`
- `src/cipher_genius/api/main.py`
  - 当前已新增：
    - `GET /api/v1/cases/{case_id}/timeline`
    - `GET /api/v1/cases/{case_id}/timeline/events`
    - `GET /api/v1/cases/{case_id}/timeline/snapshots`
    - `GET /api/v1/cases/{case_id}/timeline/drilldown`
    - `GET /api/v1/cases/{case_id}/timeline/lineage`

当前 `latest_snapshot` 不再只保存 family 摘要，也开始保存：

- `typed_contract_counts`
- `artifact_lookup_refs`
- `evidence_lookup_refs`

这意味着 memory 层现在不只服务“下一次继续同一个 case”，也开始服务“本轮结束后的回放与审计摘要”。

## 5. 当前边界

- Case Memory 保存的是项目线程级摘要，不是全量消息历史
- Timeline 保存的是演示级 run snapshot 与 execution event，不是完整企业审计中心
- 当前仍是本地 JSON 持久化第一版，不是多租户、分布式、生产级 replay center
- 稳定程序集成字段仍以 `src/cipher_genius/api/schemas.py` 与 `delivery` 返回体为准，不在本目录自行发散协议

## 6. 当前推荐口径

更准确的对外描述应保持为：

- 已完成“项目级记忆 + 运行级回放快照”的第一版骨架
- 已开始把 run 级 timeline 写入 `.cache/case_timelines/`
- 已把 replay 摘要增量接入 `delivery.backend_architecture.replay_plane`
- 已补上单 case 的本地 timeline 查询入口
- 已补上单 case 的本地 version lineage 查询入口
- 仍未完成事件化持久化中心、跨 case replay 检索与生产级审计追踪平台

## 7. 后续扩展方向

- 把 `recent_reflections` 继续收口为更稳定的 typed memory cards
- 为 replay snapshot 增加更清晰的 projection / handoff / artifact 回查索引
- 把 `case_id / run_id / round_id / version_id` 的关系继续收口成稳定 lineage
- 继续扩展 execution events，补齐 patch / rollback / residual risk 的事件化沉淀

## 2026-03-29 Replay Snapshot 索引补记

- `record_run(...)` 当前已开始消费 `memory_bus` 摘要，并额外沉淀：
  - `projection_refs`
  - `handoff_refs`
  - `typed_family_counts`
  - `typed_contract_counts`
  - `artifact_lookup_refs`
  - `evidence_lookup_refs`
  - `window_catalog`
  - `handoff_catalog`
- `timeline_summary` 当前也会返回：
  - `latest_projection_ref_count`
  - `latest_handoff_ref_count`
  - `latest_typed_family_count`
  - `latest_typed_contract_count`
- `CaseTimelineService` 当前还支持：
  - `get_timeline_summary(case_id)`
  - `query_events(case_id, ...)`
  - `query_snapshots(case_id, ...)`
  - `query_version_lineage(case_id, ...)`
- `timeline/events` 与 `timeline/snapshots` 当前还支持按以下维度做单 case drill-down：
  - `run_id`
  - `projection_ref`
  - `handoff_ref`
- `timeline/lineage` 当前支持按以下维度做轻量过滤：
  - `run_id`
  - `target_service_ref`
  - `patch_id`
  - `baseline_version`
  - `patched_version`
- `timeline/drilldown` 当前会把一个 scope 下的：
  - `snapshots`
  - `events`
  - `version_lineage`
  - `matched_run_ids / typed_contract_refs / target_service_refs`
  - `projection_relationships / handoff_relationships / service_trajectories`
  聚合成单个本地回看对象
- `handoff_relationships` 当前会进一步带出：
  - `source_agent_id / target_agent_id`
  - `upstream_stage / downstream_stage`
  - `handoff_projection_ref`
  - `dominant_typed_contract`
- `service_trajectories` 当前按 `target_service_ref` 汇总：
  - `run_ids / baseline_versions / patched_versions / patch_ids`
  - `stages / event_kind_counts`
  - `latest_status / latest_summary`
- 关系推导优先依赖 snapshot metadata 中的 `window_catalog / handoff_catalog`，用于恢复独立上下文窗口与 handoff 链路
- timeline 当前还会新增：
  - `event_kind = "memory_bus_snapshot"`
  - `event_kind = "typed_card_contract"`
  - `event_kind = "attack_decision"`
  - `event_kind = "vulnerability_verdict"`
  - `event_kind = "patch_plan"`
  - `event_kind = "patch_execution"`
  - `event_kind = "reflection_output"`
- 为了支撑 `service_trajectories`，关键攻击闭环事件 metadata 当前会补上 `target_service_ref`：
  - `vulnerability_verdict`
  - `patch_plan`
  - `patch_execution`
- 当前定位仍是：
  - 本地 JSON 回放索引第一版
  - 不是完整 replay center / audit lake

## 8. 联动影响

改动本目录时，通常还需要同步检查：

- `src/cipher_genius/core/langgraph_mas.py`
- `src/cipher_genius/api/schemas.py`
- `docs/modules/case_memory.md`
- `docs/modules/backend_execution_architecture.md`
- `docs/modules/mas_workflow.md`
- `docs/TECHNICAL_DOCUMENTATION.md`
- `tests/unit/test_case_memory_service.py`
- `tests/unit/test_case_timeline_service.py`

## 2026-04-03 Replay 索引补记

- `ReplaySnapshot` 当前已继续补充：
  - `dispatch_refs`
  - `failed_dispatch_refs`
- `timeline_summary` 当前已继续补充：
  - `latest_dispatch_ref_count`
  - `latest_failed_dispatch_ref_count`
- `ReplaySnapshot.metadata` 当前已继续补充：
  - `dispatch_catalog`
  - `patch_execution_artifact_refs`
- `timeline/events` / `timeline/snapshots` / `timeline/drilldown` 当前已支持按 `artifact_lookup_ref` 做单 case 回看。
- `query_events(...)` 的当前策略是：
  - 先返回直接命中 lookup ref 的事件
  - 再补同一 run 的上下文事件
- 当前定位仍是本地 JSON replay 索引增强，不应误写成已完成跨 case replay center。

## 2026-04-03 Typed Dispatch Summary 补记

- `replay_service.py` 当前已新增稳定对象：
  - `ReplayDispatchSummary`
- `ReplaySnapshot` 当前已新增：
  - `dispatch_summaries`
  - `failed_dispatch_summaries`
- `get_timeline_drilldown(...)` 当前会汇总 matched snapshots 中的 typed dispatch summaries，而不再只依赖 `metadata.dispatch_catalog`。

## 2026-04-03 Replay Executor Handoff Trace 补记

- `replay_service.py` 当前已新增稳定对象：
  - `ReplayExecutorHandoffTraceSummary`
- `ReplaySnapshot` 当前已新增：
  - `executor_handoff_trace_summaries`
- `timeline_summary` 当前已新增：
  - `latest_executor_handoff_trace_count`
- `get_timeline_drilldown(...)` 当前会继续汇总 matched snapshots 中的：
  - `executor_handoff_trace_summaries`
- 这一步的目标是把 `container / remote_worker` 的 executor handoff 从 dispatcher 占位输出，推进成 replay 可直接消费的 typed 摘要，而不是长期停留在自由嵌套对象解析。
