# Core 模块说明

## 2026-04-06 Replay / Retry 稳定性补记

- `langgraph_mas.py` 当前已修复 `patch_reflection` 在未进入 same-run retry 时的 retry 变量初始化问题。
- 这意味着在 LLM 回退路径、预算关闭路径或直接 patch flow 路径下，主链不会再因为 `retry_attack_decision` 等局部变量未赋值而中断。
- 当前 `replay_service.py` 也已开始把 retry 压缩与恢复点合同落盘到 `latest_snapshot.metadata`，并在 `timeline/drilldown.summary` 聚合同一批字段。

## 2026-04-06 Same-Run Retry 预算状态补记

- `langgraph_mas.py` 当前已把 same-run retry 从“固定一次”推进到“预算可配第一步”
- 当前预算入口包括：
  - `MASRequest.max_same_run_retries`
  - `SkillExecuteRequest.max_same_run_retries`
  - `Settings.same_run_retry_budget_default`
- 当前运行态会显式记录：
  - `LangGraphMASState.same_run_retry_budget`
  - `delivery.attack_loop.same_run_retry_summary`
  - `delivery.attack_loop.same_run_retry_budget / used / remaining`
- 当前 `same_run_retry_summary.attempt_trace` 已作为后续多轮 retry 子图的第一版轨迹数组
- 当前 retry 子链窗口也会进入 `context_projections.attack_planning_retry / vulnerability_evaluation_retry`
- 当前 `memory_bus.summary` 也会单独汇总 retry 子链窗口与 handoff 引用
- 当前 retry 独立窗口已追加 `retry_context_summary` 压缩骨架卡，并可被 memory bus 聚合到 lineage / typed contract 摘要
- 当前 `retry_context_summary` 已开始承载压缩策略与保留引用合同
- 当前它也已开始承载逻辑续跑点合同：`resume_checkpoint_ref / resume_inputs`
- 当前 `control_plane.summary.same_run_retry` 与 `patch_reflection` metadata 也会复用这份解释摘要
- 当前只支持：
  - `0`：关闭 same-run retry
  - `1`：允许一次 retry follow-up
- 当前状态推导也已能区分：
  - `retry_blocked_by_budget`
  - `retry_capped`
- 当前仍未完成：
  - `>1` 的递归多轮 re-gate
  - 多轮预算下的上下文压缩与记忆淘汰

## 2026-04-05 Expert Gate 有限 Re-Gate 第一版

- `langgraph_mas.py` 当前已把 `route_target = "attack_planning_agent"` 从“单次补充攻击后直接收口”推进到“有限 re-gate 第一版”。
- `patch_reflection` 当前会在 same-run 内额外生成：
  - `retry_expert_gate_projection`
  - `retry_expert_gate_decision`
- 当前 patch 分支已支持：
  - `retry -> delivery`
  - `retry -> patch`
- 当前仍未完成：
  - 递归多轮 `re-gate`
  - 完整 expert 子图拆分

最后更新：2026-04-06
状态：active

## 1. 目录职责

本目录负责密码方案生成主链的核心编排与能力实现，包括需求解析、候选生成、LangGraph MAS、攻击闭环认知层，以及后端架构摘要对象的构建。

这里解决的是：

- 如何把自然语言需求转成结构化约束
- 如何生成和筛选候选方案
- 如何组织 LangGraph staged workflow
- 如何构建独立上下文窗口、memory handoff 与补丁执行报告
- 如何输出控制平面、上下文总线与执行摘要

这里不直接负责：

- FastAPI 路由与对外 schema 暴露
- 企业交付模板与中文显示词
- 前端工作台渲染

## 2. 当前关键入口

- `parser.py`
  - 需求解析，负责结构化理解和兼容回退
- `generator.py`
  - 方案生成，结合组件库与业务规则产出候选
- `langgraph_mas.py`
  - LangGraph MAS 主实现，负责主图编排与 delivery 收口
- `mas_runtime_support.py`
  - 主线共享 helper，负责解析、候选生成、审计输入归一化、工程校验与中文交付辅助
- `audit_evaluation_agent.py`
  - 真实 LLM 审计裁决层，消费独立 `audit` projection 并输出稳定 `AuditorRoundPayload`
- `attack_planning_agent.py`
  - 真实 LLM 攻击规划层
- `vulnerability_evaluation_agent.py`
  - 真实 LLM 漏洞评估层
- `expert_gate_agent.py`
  - 真实 LLM 专家闸门层，负责在漏洞裁决后决定是否进入修补收口
- `patch_planning_agent.py`
  - 真实 LLM 修补规划层
- `reflection_agent.py`
  - 真实 LLM 反思层
- `artifact_summarizer.py`
  - 把攻击工件、patch diff 与 supporting artifacts 压缩成下游窗口可消费摘要
- `control_plane.py`
  - 构建 `delivery.backend_architecture.control_plane`
- `context_bus.py`
  - 构建 `delivery.backend_architecture.memory_bus`

## 3. 当前主链状态

当前 LangGraph 主线已收口为：

- `analyst`
- `context_builder`
- `architect`
- `audit`
- `engineer`
- `target_deployer`
- `attack_executor`
- `vulnerability_evaluation`
- `patch_reflection`
- `delivery`

其中：

- LLM 认知层已覆盖审计裁决、攻击规划、漏洞评估、专家闸门、修补规划、反思
- `generation / audit` 已开始消费项目级 `reflection_memory`
- `audit` 当前会构造候选方案级 `audit_decision_input`，再由 `AuditEvaluationAgent` 在独立窗口中输出最终裁决
- 后半段多个节点已优先从 projection 恢复运行时输入

## 4. 本轮新增的后端架构骨架

当前 core 层已新增第一批“后端完整架构补齐”骨架文件：

- `control_plane.py`
  - 提供 `WorkflowCheckpoint`
  - `AgentInvocationSpec`
  - `AgentResultEnvelope`
  - `AgentSession`
  - `ControlPlaneBuilder`
- `context_bus.py`
  - 提供 `ContextWindowSpec`
  - `MemoryHandoffSummary`
  - `ReplaySnapshotCard`
  - `ContextBusSummary`
  - `ContextBusBuilder`

当前这些 builder 已在 `langgraph_mas.py` 的 `delivery` 阶段接线，并以 additive 方式输出到：

- `delivery.backend_architecture.control_plane`
- `delivery.backend_architecture.memory_bus`

其中 `control_plane` 本轮已继续推进到“第一版运行时合同摘要”，开始显式表达：

- `depends_on`
- `checkpoint_ref / result_ref`
- `retryable / retry_strategy / termination_mode`
- `decision_source`
- `contract.failure_action / next_stages`
- `checkpoints[*].input_refs / output_refs / termination_signal`
- `results[*].decision_signal / decision_source / termination_signal`

它们的当前定位仍然是“可联调架构摘要 + 第一版合同层”，不是完整生产级 orchestration/control framework。

## 5. 与执行平面 / 回放平面的接线

虽然 `execution_plane.py` 与 `replay_service.py` 分别位于 `sandbox/` 和 `memory/` 目录，但当前 core 层负责把它们接入主链。

当前 `langgraph_mas.py` 会：

- 创建 `ExecutionPlaneBuilder`
- 创建 `CaseTimelineService`
- 在 delivery 收口时生成：
  - `delivery.backend_architecture.execution_plane`
  - `delivery.backend_architecture.replay_plane`
- 当前 `execution_plane` 不再只有阶段摘要，还会显式带出：
  - `summary.contract_version = "v1"`
  - `plan.operation_kinds`
  - `operations[*]`
- `operations[*]` 当前会把 `deploy / attack / patch_apply / rollback / regression_replay` 统一成结构化操作合同，便于后续执行面、回放面和前端透明化共用同一套执行语义。

当前 replay plane 依赖：

- `.cache/case_timelines/`

## 6. 当前稳定约束

- `langgraph_mas.py` 最终必须返回与既有主契约兼容的 `MASResponse`
- 中文企业场景关键词识别不能退化
- 不同 agent 的上下文窗口必须保持独立
- 跨阶段信息传递优先通过 `context_projection + memory_handoff + artifact/evidence refs`
- `artifact_summarizer` 已进入主链，不要回退为大对象直塞下游窗口
- 当前 attack-loop、patch execution 与 backend_architecture 都属于 additive 输出
- 当前沙盒仍是演示级、本地受限进程执行面，不要把 core 层写成生产级远程执行平台

## 7. 当前推荐口径

更准确的对外描述应保持为：

- 已完成后端完整架构第一批代码骨架落地
- 已把 control plane / memory bus / execution plane / replay plane 以摘要形式接入 delivery
- 已开始把 run 级 replay snapshot 写入本地 timeline
- 尚未完成完整 invocation contract、typed memory family、统一 execution contract 与事件化 replay center

## 2026-03-29 Memory Bus Typed Family 补记

- `context_bus.py` 当前已从“计数摘要”推进到“typed family + typed contract 摘要”：
  - `ContextWindowSpec.window_ref / card_family_counts / dominant_card_family / lineage_refs`
  - `MemoryHandoffSummary.projection_ref / card_family_counts / dominant_card_family / lineage_refs`
  - `TypedMemoryFamilySummary`
  - `ContextWindowSpec.typed_contract_counts / dominant_typed_contract / artifact_lookup_refs / evidence_lookup_refs`
  - `MemoryHandoffSummary.typed_contract_counts / dominant_typed_contract / artifact_lookup_refs / evidence_lookup_refs`
  - `TypedCardContractSummary`
  - `ReplaySnapshotCard.typed_family_counts / typed_contract_counts / artifact_ref_count / evidence_ref_count / lineage_refs`
- `langgraph_mas.py` 当前会把这批摘要继续传给：
  - `delivery.backend_architecture.memory_bus`
  - `CaseTimelineService.record_run(...)`
- `langgraph_mas.py` 当前还会给 `generation_runtime_input / audit_runtime_input` cards 稳定补上：
  - `payload.typed_contract`
  - `payload.typed_contract_ref`
  - `payload.ref_lookup_hint`
- 当前定位仍需保持诚实：
  - 已完成 typed family 第一版摘要接线，并补到 typed contract / ref lookup 第二阶段
  - 尚未完成完整 typed card contract family

## 8. 常见改动点

- 改主线编排：
  - 优先看 `langgraph_mas.py`
- 改前半段运行时输入恢复：
  - 优先看 `mas_runtime_support.py`
- 改攻击 / 漏洞 / 修补 / 反思认知层：
  - 优先看对应 agent 文件
- 改 control plane / memory bus：
  - 优先看 `control_plane.py`、`context_bus.py`
- 改 patch execution：
  - 同时检查 `artifact_summarizer.py`、`reflection_agent.py`

## 9. 验证方式

至少应完成：

- `python -m compileall src/cipher_genius/core`
- `poetry run pytest tests/unit/test_expert_gate_agent.py -q --no-cov`
- `poetry run pytest tests/integration/test_langgraph_mas.py -q --no-cov`
- `poetry run pytest tests/api/test_api_mas.py -q --no-cov`
- 如涉及 replay / patch execution：
  - `poetry run pytest tests/unit/test_case_timeline_service.py -q --no-cov`
  - `poetry run pytest tests/unit/test_patch_execution_report.py -q --no-cov`

## 10. 相关文档

- `docs/modules/backend_execution_architecture.md`
- `docs/modules/mas_workflow.md`
- `docs/agent_skills/skill_mas_workflows.md`
- `docs/TECHNICAL_DOCUMENTATION.md`
- `TODO_VIBING.md`
- `REMAIN.md`
## 2026-04-01 Patch Reflection 主链补记

- `langgraph_mas.py` 当前在 `patch_reflection` 阶段的执行顺序已显式调整为：
  - `patch_spec`
  - `patch_apply_dispatch`
  - `rollback_dispatch`
  - `regression_deployment_dispatch`
  - `regression_attack_dispatch`
  - `patch_execution`
- 这一步的目的不是增加展示字段，而是让 core 主链真正消费 execution plane 的真实调度结果。
- 当前 `patch_execution` 也已继续增量返回：
  - `patch_dispatch_id`
  - `rollback_dispatch_id`
- 如后续再改这条链路，至少同步检查：
  - `src/cipher_genius/sandbox/dispatcher.py`
  - `src/cipher_genius/sandbox/local_runtime.py`
  - `src/cipher_genius/sandbox/execution_plane.py`
  - `tests/unit/test_patch_execution_report.py`
  - `tests/integration/test_langgraph_mas.py`

## 2026-04-02 Patch Execution Contract 补记

- `patch_execution` 当前已继续增量返回：
  - `execution_contract_version`
  - `patch_artifact_refs`
  - `rollback_artifact_refs`
  - `regression_artifact_refs`
- 这些字段的目的不是重复已有 `changed_artifact_summaries`，而是给：
  - `execution_plane`
  - `replay plane`
  - 后续容器/远程 executor
  提供稳定的工件引用层。
- 当前如果 sandbox runtime 在执行期失败，core 上游可消费 `SandboxDispatchExecutionError.dispatch_result`，
  而不必只依赖裸异常文本。
## 2026-04-02 Executor Matrix 补记

- `langgraph_mas.py` 当前通过 `execution_plane` 间接向 `delivery.backend_architecture` 暴露 executor backend matrix。
- `core` 层当前新增可稳定向上游返回的执行面字段包括：
  - `execution_plane.plan.executor_backends`
  - `execution_plane.plan.active_executor_kinds`
  - `execution_plane.plan.planned_executor_kinds`
  - `execution_plane.plan.executor_matrix`
  - `execution_plane.summary.executor_matrix_count`
- 这一步的意义不是把 core 写成调度中心，而是让 core 主链能够稳定表达：
  - 本轮到底用了哪个 executor
  - 未来 planned executor 的 handoff contract 长什么样

## 2026-04-05 Expert Gate 主链补记

- `langgraph_mas.py` 当前在 `patch_reflection` 阶段已显式插入：
  - `expert_gate_projection`
  - `ExpertGateAgent`
  - `patch_projection`
- `mas_runtime_support.py` 当前已统一初始化：
  - `self.expert_gate = ExpertGateAgent(llm_provider)`
- `PatchPlanningAgent` 当前开始真实消费：
  - `expert_gate_decision_family`
  - `expert_gate_decision_family_label`
  - `expert_gate_action`
  - `expert_gate_route_target`
  - `expert_gate_route_target_label`
  - `expert_gate_rationale`
  - `expert_gate_residual_risk_summary`
  - `expert_gate_follow_up_actions`
- 这一步的意义不是只增加 delivery 展示字段，而是把漏洞裁决后的独立专家认知层与 typed route 第一版真正接到了 patch 规划主链里。
- `langgraph_mas.py` 当前还已补上一条最小真实分流：
  - 当 `expert_gate_decision.route_target = "delivery"` 时，不再误进入 patch flow
  - 会直接构建 `reflection_projection` 并生成 follow-up reflection cards
  - 当 `expert_gate_decision.route_target = "attack_planning_agent"` 时，已会执行 same-run 单次补充攻击闭环
  - 当前仍未完成的是递归多轮 retry / re-gate 子图

## 2026-04-03 Replay 接线补记

- `langgraph_mas.py` 当前经由 `CaseTimelineService.record_run(...)` 向上游稳定暴露：
  - `delivery.backend_architecture.replay_plane.timeline_summary.latest_dispatch_ref_count`
  - `delivery.backend_architecture.replay_plane.timeline_summary.latest_failed_dispatch_ref_count`
  - `delivery.backend_architecture.replay_plane.latest_snapshot.dispatch_refs`
  - `delivery.backend_architecture.replay_plane.latest_snapshot.failed_dispatch_refs`
- 这意味着 core 收口阶段现在不仅输出 replay snapshot 摘要，也开始稳定表达：
  - 本轮有哪些 dispatch 被记录
  - 哪些 dispatch 属于失败 / 阻断路径
  - patch execution 相关 artifact refs 如何进入 replay 回查面

## 2026-04-03 Replay Typed Dispatch Summary 补记

- `core -> replay_plane` 当前已不再只暴露 `dispatch_refs` 级别摘要，也会稳定透出：
  - `latest_snapshot.dispatch_summaries`
  - `latest_snapshot.failed_dispatch_summaries`
- 这意味着 core 收口后的 replay 输出现在可以直接回答：
  - 某个 dispatch 属于哪一类操作
  - 它由哪个 executor 摘要承接
  - 它为什么失败，是否带有 artifact refs / rejection reasons
