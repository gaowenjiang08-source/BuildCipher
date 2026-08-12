# Executor Handoff Adapter 设计

最后更新：2026-04-03
状态：active

## 1. 适用范围

本文专门说明 `container / remote_worker` 这两类非本地直执行 executor 的交接适配层设计。

适用目录与模块：

- `src/cipher_genius/sandbox/executor_matrix.py`
- `src/cipher_genius/sandbox/dispatcher.py`
- `src/cipher_genius/sandbox/execution_plane.py`
- `src/cipher_genius/api/schemas.py`
- `src/cipher_genius/memory/replay_service.py`
- `docs/modules/backend_execution_architecture.md`

本文不表示真实 `container / remote_worker` 执行器已经落代码。当前它的定位是：

- 先固定后端架构边界
- 先固定 typed handoff contract
- 当前已落第一批 schema skeleton 与 dispatcher 占位输出
- 后续再决定 adapter 实现与 replay 深化顺序

## 2. 为什么要单独设计 handoff adapter

当前 executor backend matrix 已经把三类 executor 固定为：

1. `local_process`
2. `container`
3. `remote_worker`

其中只有 `local_process` 会直接进入本地 `LocalSandboxRuntime`。

`container / remote_worker` 当前虽然已经有：

- `handoff_required`
- `handoff_contract_version`
- `handoff_fields`
- `handoff_ref`

但这些字段仍停留在 matrix 级占位，还没有形成真正可实现、可验证、可 replay 的 typed 交接合同。

如果不先把这层设计清楚，后面很容易出现三类问题：

1. 把远程执行逻辑重新塞回 `langgraph_mas.py` 或 prompt。
2. 把 artifact 上传、回执、失败分类分散到不同模块，导致 replay 无法稳定回看。
3. 把 `memory_handoff` 和 `executor_handoff` 混成一个概念，破坏“认知传递”和“执行交接”的边界。

## 3. 它和 memory handoff 不是一回事

当前项目里已经存在一条稳定主线：

- `context_projections`
- `memory_handoffs`
- `reflection_memory`
- `ReplaySnapshot`

这条链服务的是 agent 之间的认知传递。

而本文定义的 handoff adapter 服务的是执行平面的交接传递。

两者必须强制区分：

- `memory_handoff`
  - 面向 agent
  - 传 card、summary、evidence ref、artifact ref
  - 目标是让下游 agent 拿到最小可判断上下文
- `executor_handoff`
  - 面向 executor backend
  - 传 dispatch contract、artifact bundle、执行预算、回执要求
  - 目标是让非本地执行面安全接管任务

推荐统一口径：

- memory handoff 解决“谁该知道什么”
- executor handoff 解决“谁该执行什么”

## 4. 设计目标

typed handoff adapter 需要同时满足 5 个目标：

1. 不破坏当前 `local_process` 主链。
2. 让 `container / remote_worker` 的未来接入不需要重写 orchestration。
3. 让 dispatch 的输入、回执、artifact 同步、失败分类都可 replay。
4. 让前端和答辩视图能稳定展示“已交接但未本地执行”的状态。
5. 让安全边界前置到 dispatcher，而不是交给 prompt 或执行器自行理解。

## 5. 最小 typed contract

推荐把 handoff adapter 最少拆成 4 个稳定对象。

### 5.1 `ExecutorHandoffRequest`

这是 dispatcher 交给 container adapter 或 remote worker adapter 的最小执行请求。

建议稳定字段：

- `handoff_ref`
- `handoff_contract_version`
- `case_id`
- `run_id`
- `dispatch_id`
- `dispatch_key`
- `operation_kind`
- `executor_kind`
- `executor_backend`
- `target_service_ref`
- `workspace_ref`
- `input_artifact_refs`
- `required_capabilities`
- `governance_mode`
- `timeout_seconds`
- `budget_hint`
- `callback_contract`
- `artifact_sync_contract`
- `telemetry_contract`

字段职责：

- `dispatch_id / dispatch_key`
  - 保证 replay 与 execution plane 可对齐
- `workspace_ref`
  - 指向执行工作区的稳定引用，而不是直接暴露临时本地路径
- `input_artifact_refs`
  - 只传工件引用，不传整段大对象
- `callback_contract`
  - 约束执行完成后如何回写 receipt
- `artifact_sync_contract`
  - 约束输出工件如何归档
- `telemetry_contract`
  - 约束流量、日志、指标如何回传

### 5.2 `ExecutorArtifactSyncManifest`

这是 handoff adapter 在执行前后都需要理解的工件同步合同。

建议稳定字段：

- `sync_id`
- `dispatch_id`
- `direction`
- `artifact_refs`
- `required_artifact_kinds`
- `integrity_hashes`
- `retention_policy`
- `materialization_mode`
- `sync_status`

目标不是做对象存储系统，而是把“哪些 artifact 必须同步”写成稳定对象。

### 5.3 `ExecutorHandoffReceipt`

这是 container / remote worker 接管后的最小回执对象。

建议稳定字段：

- `receipt_id`
- `handoff_ref`
- `dispatch_id`
- `executor_kind`
- `executor_backend`
- `accepted`
- `receipt_status`
- `remote_job_ref`
- `started_at`
- `completed_at`
- `output_artifact_refs`
- `telemetry_refs`
- `failure_category`
- `failure_summary`
- `retryable`

推荐状态枚举：

- `accepted`
- `queued`
- `running`
- `completed`
- `failed`
- `rejected`
- 当前 schema skeleton 阶段还会额外出现：
  - `pending_handoff`
  - `handoff_required`
  - 它们用于明确表达“合同已生成，但尚未由真实 adapter 接管”

### 5.4 `ExecutorHandoffTrace`

这是 replay plane 最终需要消费的轻量交接轨迹对象。

建议稳定字段：

- `handoff_ref`
- `dispatch_id`
- `executor_kind`
- `routing_mode`
- `adapter_stage`
- `trace_status`
- `summary`
- `receipt_ref`
- `artifact_sync_ref`
- `failure_category`

它的目标不是替代完整 receipt，而是给 replay / timeline 提供稳定回查入口。

## 6. 生命周期

推荐把 handoff adapter 生命周期固定为下面 6 步：

1. `dispatcher plan`
   - 根据 executor matrix 判断该 dispatch 是否必须 handoff
2. `handoff request build`
   - 生成 `ExecutorHandoffRequest`
3. `adapter materialize`
   - container adapter 或 remote worker adapter 接收请求并物化执行输入
4. `receipt callback`
   - 回写 `ExecutorHandoffReceipt`
5. `artifact sync`
   - 生成并回写 `ExecutorArtifactSyncManifest`
6. `replay persist`
   - replay plane 落地 `ExecutorHandoffTrace`

当前主线里真正需要先实现的不是 3 和 4，而是先把 2、5、6 的合同写稳。

## 7. 与 execution plane 的关系

当前 execution plane 已经有：

- `operations[*]`
- `plan.executor_backends`
- `plan.executor_matrix`
- `summary.executor_matrix_count`

后续接入 handoff adapter 时，不建议新开一条平行平面，而是继续挂在 execution plane 下。

推荐收口方式：

- `operations[*]`
  - 继续表达这轮想执行什么
- `dispatch_result`
  - 表达这轮是否本地直执行、是否 handoff、是否失败
- `handoff_request`
  - 表达交接给谁、交接了什么
- `handoff_receipt`
  - 表达对方是否接单、是否完成

也就是说：

- execution plane 仍是总平面
- handoff adapter 是 execution plane 的执行分支，不是新的第五平面

## 8. 与 replay plane 的关系

replay plane 当前已经具备：

- `dispatch_refs`
- `failed_dispatch_refs`
- `dispatch_summaries`
- `failed_dispatch_summaries`

后续 handoff adapter 接入后，建议 replay 继续走“typed summary + ref”模式，而不是直接把完整 receipt 塞进 snapshot metadata。

推荐 replay 层优先持久化：

- `handoff_ref`
- `dispatch_id`
- `executor_kind`
- `receipt_status`
- `remote_job_ref`
- `output_artifact_refs`
- `telemetry_refs`
- `failure_category`

推荐保留在兼容 metadata 的对象：

- 原始 adapter payload
- 大体量 receipt 明细
- 调试用 provider response

## 9. container 与 remote_worker 的差异

虽然两者都要走 handoff adapter，但职责侧重点不同。

### 9.1 `container`

更适合承接：

- 本机或受控节点上的隔离执行
- 需要固定镜像、挂载策略、资源限制的任务

额外建议字段：

- `image_ref`
- `mount_contract`
- `resource_quota`
- `network_policy`

### 9.2 `remote_worker`

更适合承接：

- 跨节点、跨主机、甚至后续多租户 worker 池
- 需要队列接单、异步回执、延迟回收的任务

额外建议字段：

- `worker_pool_ref`
- `queue_ref`
- `remote_endpoint_ref`
- `lease_ttl_seconds`

推荐口径：

- `container` 更像隔离执行适配器
- `remote_worker` 更像异步作业交接适配器

## 10. 当前不该做的事

在 handoff adapter 设计阶段，当前不建议马上做：

1. 直接写完整远程执行器。
2. 直接接入真实容器编排系统。
3. 把 artifact store、job queue、callback server 一次做完。
4. 把 replay center 提前写成多 case 搜索平台。

更合理的顺序应是：

1. 先固定 typed handoff contract
2. 先固定 replay / execution 的回写口径
3. 再补 schema skeleton
4. 最后才写 adapter 实现

## 11. 推荐落地顺序

### 11.1 第一阶段

- 在文档中固定：
  - `ExecutorHandoffRequest`
  - `ExecutorArtifactSyncManifest`
  - `ExecutorHandoffReceipt`
  - `ExecutorHandoffTrace`

### 11.2 第二阶段

- 在 `src/cipher_genius/api/schemas.py` 新增 skeleton payload
- 在 `dispatcher` 中对 `container / remote_worker` 返回 typed handoff payload
- 不接真实执行器，只做结构化回执占位

当前已完成到这一阶段。

### 11.3 第三阶段

- 为 `container` 接入最小本地容器 adapter
- 为 `remote_worker` 接入最小异步 mock adapter
- 把 receipt 与 artifact sync 接入 replay plane

## 12. 验证方式

设计完成后，后续代码落地至少要验证：

### 12.1 合同验证

- handoff request 是否稳定
- receipt 是否稳定
- artifact sync manifest 是否稳定
- replay 是否能按 `handoff_ref / dispatch_id` 回看

### 12.2 执行验证

- `container / remote_worker` 是否不会误走本地 runtime
- handoff-required 是否会稳定返回结构化结果
- callback 缺失时是否能稳定失败分类

### 12.3 回放验证

- timeline 是否能同时表达 dispatch 与 handoff trace
- failed handoff 是否能进入 replay drill-down
- artifact sync 是否能和 patch / rollback / regression artifact refs 对齐

## 13. 2026-04-03 Replay Trace 落地补充

本轮已开始把本文定义的 `ExecutorHandoffTrace` 往 replay/timeline 落地为稳定 typed summary，而不是只停留在 dispatcher 输出层。

当前已落地的 replay 对象：

- `ReplayExecutorHandoffTraceSummary`
- `ReplaySnapshot.executor_handoff_trace_summaries`
- `timeline_summary.latest_executor_handoff_trace_count`
- `drilldown.summary.executor_handoff_trace_summaries`

这说明当前执行顺序已经从：

1. 先定 contract
2. dispatcher 输出 skeleton

推进到了：

3. replay plane 显式消费 handoff trace summary

但仍未推进到：

4. 真实 adapter 执行
5. receipt callback 回写
6. artifact sync 服务化

## 14. 当前结论

当前最合理的推进口径是：

- `local_process` 继续承担真实演示执行
- `container / remote_worker` 先补 typed handoff adapter 设计
- 先把交接合同、回执合同、artifact sync 合同和 replay 合同定稳
- 暂不直接承诺“容器执行器已完成”或“远程 worker 已完成”
