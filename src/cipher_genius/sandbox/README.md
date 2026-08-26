# Sandbox 模块说明

## 2026-08-11 BuildTrust Construction Runtime

- `construction_runtime.py` 新增本地 IFC manifest/版本验证、角色授权、IoT 防重放和项目证据链。
- `ConstructionTrustDemoRunner` 可复现 IFC 篡改、版本回滚、分包越权、设备冒充和遥测重放。
- 每类攻击产生 JSON artifact、SHA-256 evidence、修补建议和回归结果。
- 默认演示仍采用 `HMAC-SHA256-DEMO` 与进程内状态；建筑 IoT 路径可选接入 SQLite 防重放和非导出式 MAC provider 合同。`LocalReferenceHMACProvider` 仍是进程内参考实现，不是生产 PKI、KMS/HSM 或商用密码模块。
- LangGraph 已按建筑需求选择三类目标模板，并在 baseline、retry、regression 路径执行五类建筑 attack spec。
- 结果会映射成主链统一的 `AttackResultPayload`；当前执行仍是确定性本地协议演示，不是生产系统渗透测试。
- 建筑 MAS 基线使用 `baseline` 控制配置，补丁应用写入 `hardened` 配置并保留补丁前快照；dispatcher 可显式执行配置回滚并校验 SHA-256。
- 当前不会根据回归失败自动触发回滚，生产状态存储与事务恢复也不在本地 runtime 范围内。

最后更新：2026-03-29
状态：active

## 1. 目录职责

本目录负责 BuildCipher Studio 的演示级执行平面实现，当前聚焦 BuildTrust 建筑可信交付能力：

- 目标服务本地部署工件生成
- 受限攻击执行所需的本地沙盒
- 调度审批、预算约束与失败分类
- telemetry / finding / trace 工件落盘
- execution-plane 摘要对象构建

这里不直接负责：

- LangGraph 主流程编排
- 前端可视化渲染
- 容器级隔离、远程执行或生产发布系统

## 2. 当前关键入口

- `local_runtime.py`
  - `LocalSandboxRuntime`
  - 负责本地目标服务壳子部署、探测执行与工件落盘
- `dispatcher.py`
  - `LocalSandboxDispatcher`
  - 负责白名单、预算、签名、失败分类与审批轨迹
- `execution_plane.py`
  - `ExecutionPlaneBuilder`
  - 负责把 dispatcher/runtime 结果收口为统一 execution-plane 摘要
- `target_templates.py`
  - 负责生成稳定 `target service template` 及 manifest 物化

## 3. 当前工件与输出

当前 `.cache/sandbox/<run_id>/<service_id>/` 下会生成：

- `service_manifest.json`
- `service_runtime.py`
- `runtime_info.json`
- `service_stdout.log`
- `implementation.py`
- `implementation.c`
- `implementation.pseudo.txt`
- `attack_*/trace.jsonl`
- `attack_*/metrics.json`
- `attack_*/finding.json`

## 4. 当前主链接线

### 4.1 Dispatcher / Runtime

当前调用关系已稳定为：

- orchestration
- `LocalSandboxDispatcher`
- `LocalSandboxRuntime`

baseline 与 regression 两轮的 deployment / attack 都先走 dispatcher，再进入 runtime。

### 4.2 Execution Plane Summary

当前已新增 `execution_plane.py` 中的 `ExecutionPlaneBuilder`，会构建：

- `ExecutionPlan`
- `ExecutionStage`
- `ExecutionArtifactBundle`
- `ExecutionTelemetry`
- `ExecutionFailure`
- `ExecutionRun`

当前该摘要已作为 additive 字段返回到：

- `delivery.backend_architecture.execution_plane`

它的定位是“统一执行平面摘要”，不是说本目录已经完成完整生产级 execution plane。

## 5. 与 Patch Execution 的关系

当前 sandbox 侧虽然还不是自动 patch 应用器，但已经成为 `patch_execution` 的重要数据来源。

当前会参与 `patch_execution` 收口的 sandbox 信息包括：

- patched deployment 的 `workspace`
- baseline / regression dispatch id
- regression probe 的执行状态
- baseline / patched workspace 的工件差异输入
- supporting artifacts：
  - `service_manifest.json`
  - `runtime_info.json`
  - `service_stdout.log`
  - `service_runtime.py`

## 6. 当前边界

当前这套 sandbox 的真实定位是：

- 演示级、本地受限进程执行面
- 可部署、可探测、可落盘、可回归
- 可为前端透明化和回放提供稳定结构化数据

当前还不是：

- 容器级隔离沙盒
- 远程攻击执行平面
- 生产级 patch sandbox
- 远程服务端补丁发布系统

## 7. 当前推荐口径

更准确的对外描述应保持为：

- 已完成 `LocalSandboxDispatcher -> LocalSandboxRuntime -> ExecutionPlaneBuilder` 的第一版分层
- 已完成 baseline / regression 演示链路与支撑工件规范
- 已能把 execution-plane 摘要增量返回给 `delivery.backend_architecture.execution_plane`
- 尚未完成远程 executor、容器隔离与生产级多阶段执行协议

## 8. 联动影响

改动本目录时，通常还需要同步检查：

- `src/cipher_genius/core/langgraph_mas.py`
- `src/cipher_genius/core/artifact_summarizer.py`
- `src/cipher_genius/api/schemas.py`
- `docs/modules/backend_execution_architecture.md`
- `docs/modules/mas_workflow.md`
- `docs/TECHNICAL_DOCUMENTATION.md`
- `tests/unit/test_sandbox_dispatcher.py`
- `tests/integration/test_langgraph_mas.py`
## 2026-04-01 Patch Apply / Rollback 补记

- 当前 sandbox 目录已不再只覆盖 `deploy_target_service / execute_attack_specs`。
- 新增真实本地执行入口：
  - `apply_patch_to_service(...)`
  - `materialize_rollback_plan(...)`
- 新增 dispatcher 入口：
  - `dispatch_patch_application(...)`
  - `dispatch_rollback(...)`
- 当前新增落盘工件：
  - `patch_manifest.json`
  - `patch_metadata.json`
  - `rollback_plan.json`
  - `rollback_manifest.json`
- 当前新增调度阶段：
  - `patch_executor`
  - `rollback_executor`
- 当前对外应固定描述为：
  - 已完成演示级 patch apply / rollback plan 本地执行面第一版
  - 尚未完成容器级隔离、远程部署与生产级自动回滚

## 2026-04-02 Dispatcher / Runtime Contract 补记

- `LocalSandboxDispatcher` 当前每类 dispatch 都会显式带出：
  - `operation_kind`
  - `executor_kind`
  - `executor_contract_version`
  - `capability_flags`
  - `artifact_refs`
- `LocalSandboxRuntime.apply_patch_to_service(...)` 当前会直接补齐：
  - `rollback_manifest.json`
- 当前新增的请求级失败分类：
  - `patch_artifact_count_missing`
  - `rollback_notes_missing`
- 当前新增的运行时失败合同：
  - `SandboxDispatchExecutionError`
  - `dispatch_result.status = "failed"`
  - `dispatch_result.failure_category = "runtime_execution_failed"`
  - `dispatch_result.audit_trail[-1].event_kind = "failed"`
## 2026-04-02 Executor Backend Matrix 补记

- 当前 sandbox 目录新增：
  - `executor_matrix.py`
- 当前 matrix 中已显式保留三类 executor：
  - `local_process`
  - `container`
  - `remote_worker`
- `LocalSandboxDispatcher` 现已按 matrix 做显式校验与分类：
  - executor 类型是否合法
  - executor 是否支持当前 `operation_kind`
  - executor 是否满足 `required_capabilities`
  - executor 是否必须进入 handoff 流程
- 当前新增的 dispatch 合同字段包括：
  - `executor_label`
  - `executor_readiness`
  - `routing_mode`
  - `handoff_required`
  - `handoff_contract_version`
  - `handoff_fields`
  - `handoff_ref`
  - `backend_capability_flags`
  - `supported_operation_kinds`
- 当前新增的 executor 失败分类包括：
  - `executor_kind_unknown:*`
  - `executor_operation_not_supported:*`
  - `executor_capability_missing:*`
  - `executor_handoff_required:*`
- 当前必须保持诚实的口径：
  - 只有 `local_process` 会直接进入 `LocalSandboxRuntime`
  - `container / remote_worker` 仍是合同占位，不会直接在本地 runtime 执行

## 2026-04-03 Handoff Adapter 设计补记

- 针对 `container / remote_worker`，当前已先补设计文档而非直接写执行器：
  - `docs/modules/executor_handoff_adapter.md`
- 当前推荐的收口顺序是：
  1. 先固定 typed handoff contract
  2. 先固定 receipt / artifact sync / replay trace
  3. 再决定是否写 schema skeleton 与 adapter 占位实现
- 当前这一步已经继续落到代码：
  - `ExecutorHandoffRequestPayload`
  - `ExecutorArtifactSyncManifestPayload`
  - `ExecutorHandoffReceiptPayload`
  - `ExecutorHandoffTracePayload`
  - `SandboxDispatchRequestPayload.handoff_request / artifact_sync_manifest`
  - `SandboxDispatchResultPayload.handoff_request / artifact_sync_manifest / handoff_receipt / handoff_trace`
- `LocalSandboxDispatcher` 当前对 handoff-required executor 会构造 typed skeleton，但仍不会直接越过本地 runtime 去执行远程任务。
