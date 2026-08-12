# Skill: MAS Workflows (LangGraph Mainline)

## When To Use

- 你要改 MAS 执行链路
- 你要改 LangGraph 节点职责、状态对象、`workflow_trace`
- 你要改 agent / system module 边界说明
- 你要补 audit / attack / expert / patch / reflection 等后续主线 agents

## Current Architecture Consensus

- 后续唯一主线是 `LangGraph`
- 仓库中仍保留 Legacy 路径，但仅作为兼容层，不再作为未来主线叙事
- “agent”特指具备 LLM 认知职责的模型角色
- `context_builder`、`retrieval`、`case_memory`、`delivery`、`sandbox runtime` 默认归类为 system modules

## Current LLM Agents

- `Analyst Agent`
- `Generation Agent`
- `Code Authoring Agent`
- `AuditEvaluationAgent`
- `Attack Planning Agent`
- `Vulnerability Evaluation Agent`
- `ExpertGateAgent`
- `Patch Agent`（当前为真实 LLM 修补规划层，执行面仍在继续补齐）
- `Reflection Agent`

## Planned LLM Agents

- `Generation Agent` 的更强检索增强与证据绑定
- `Audit Agent` 的更完整独立审计对象沉淀
- `Expert Gate` 的更完整多分支路由
- `Patch Agent` 的更深 same-run 修补决策与执行验证

## Current System Modules

- `Context Builder`
- `Retrieval / Qdrant`
- `Case Memory`
- `Audit Engine`
- `Delivery Renderer`
- `Sandbox Dispatcher / Executor`

## Key Files

- LangGraph 主线：
  - `src/cipher_genius/core/langgraph_mas.py`
- LangGraph shared runtime support：
  - `src/cipher_genius/core/mas_runtime_support.py`
- Legacy 兼容层：
  - `src/cipher_genius/api/mas_service.py`
- FastAPI 路由与 streaming：
  - `src/cipher_genius/api/main.py`
- Schema 与稳定契约：
  - `src/cipher_genius/api/schemas.py`
- Retrieval / Memory：
  - `src/cipher_genius/retrieval/service.py`
  - `src/cipher_genius/retrieval/qdrant_store.py`
  - `src/cipher_genius/memory/service.py`
- 前端开关与调用：
  - `frontend/src/store/index.js`
  - `frontend/src/api/client.js`
  - `frontend/src/features/mas/useMasActions.js`
  - `frontend/src/features/mas/clarificationHelpers.js`

## Invariants (不要破坏)

- 稳定 API 字段名、`template_id`、`skill_id`、`scenario` 不随意改
- `MASResponse` 契约不能被破坏，否则前端和报告导出会一起受影响
- `/api/v1/mas/execute` 与 `/api/v1/mas/stream` 当前统一走 LangGraph 主线；`use_langgraph` 仅作兼容字段保留
- `discussion_log.actor/status/trust_level/support_level` 等稳定字段不因中文交付漂移；如需中文展示，请补 `*_label`
- `delivery.engine`、`delivery.engine_mode`、`delivery.workflow_trace` 仍是当前主链调试和回归的重要字段
- 当前 `delivery.attack_loop` 也是 LangGraph 主线调试和前端预埋联动的重要字段
- LangGraph 路径当前已包含 `context_builder`，并会返回顶层 `evidence_pack`
- 中文企业需求里的行业、监管、后量子关键词识别不能退化
- 中文企业交付里的标题、建议、报告章节默认保持中文优先

## Common Changes

- 想改主流程阶段：
  - 优先改 `src/cipher_genius/core/langgraph_mas.py`
  - 如果改动涉及需求解析、候选生成、审计输入归一化、工程校验或中文交付辅助逻辑，优先看 `src/cipher_genius/core/mas_runtime_support.py`
  - 同步检查 `workflow_trace`、状态对象、前端展示与回归测试
- 想改 attack-loop 壳子：
  - 先看 `TargetServiceSpec / AttackSpec / AttackResultSpec / VulnerabilityVerdictSpec / PatchSpec`
  - 再看 `target_deployer / attack_executor / vulnerability_evaluation / patch_reflection` 4 个节点
  - 当前不要把“本地文件沙盒”误写成真实网络隔离 sandbox 执行能力
- 想改 agent 定义：
  - 先确认这是 LLM 认知职责，还是工程模块职责
  - 不要把普通节点因为放进图里就命名为 agent
- 想补真正的多 Agent 闭环：
  - 优先从 `Audit Agent`、`Attack Planning Agent`、`Expert Gate`、`Patch Agent`、`Reflection Agent` 的 spec 输入输出开始
  - 再决定在 LangGraph 中如何接线
- 想提升过审率：
  - 先检查 `_scheme_to_audit_input()` 是否正确抽取主算法与模式
  - 再检查 `_prepare_schemes_for_audit()` 是否对量子与行业要求做了预加固和重排
  - 然后检查 `core/generator.py` 是否输出干净、可审计的候选组合
- 想让检索和证据真正影响结果：
  - 优先检查 `context_builder` 是否把同一份 `evidence_pack` 提供给 generation 和 audit
  - 再检查报告导出是否保留了 citation block
- 想补长期记忆：
  - 先分清 `case_id`、`run_id`、`round_id`、`artifact_id`
  - 不要把聊天历史直接当长期记忆

## Recommended Verification

- 语法检查：`python -m compileall src tests`
- 单测：`poetry run pytest tests/unit -q`
- MAS API 回归：`poetry run pytest tests/api/test_api_mas.py -q`
- LangGraph 集成回归：`poetry run pytest tests/integration/test_langgraph_mas.py -q`
- 中文交付回归：
  - 检查关键报告是否仍输出中文标题、中文建议、中文章节
- 手工联调：
  - `POST /api/v1/mas/execute`
  - `POST /api/v1/mas/stream`
  - 如需兼容性验证，可额外确认显式传 `use_langgraph=false` 时仍会被统一收口到 LangGraph 主线

## Docs To Update (按 AGENTS.md)

- `docs/TECHNICAL_DOCUMENTATION.md`
- `DOC_INDEX.md`
- `docs/modules/mas_workflow.md`
- 如果改动影响待办主线，再更新：
  - `REMAIN.md`
  - `TODO_VIBING.md`

## 2026-04-06 Workflow Update: Replay / Timeline Retry 恢复点

- 当前 same-run retry 子链的可解释性已不再只停留在：
  - `delivery.attack_loop.same_run_retry_summary`
  - `delivery.backend_architecture.memory_bus.summary.retry_*`
- 现在还会继续进入：
  - `delivery.backend_architecture.replay_plane.latest_snapshot.metadata.retry_*`
  - `GET /api/v1/cases/{case_id}/timeline/drilldown -> summary.retry_*`
- 当前还顺手修复了 `patch_reflection` 在非 retry 路径下的 retry 局部变量初始化问题。
- 当前正确口径：
  - 已完成 retry 子链 replay 索引第一版
  - 不要写成 runtime 已支持 resume-and-continue

## 2026-03-26 Incremental Update

- `delivery.attack_loop` is no longer backed only by file placeholders.
- Current runtime stage is:
  - local file-backed artifacts
  - local process-backed target-service shell
  - bounded localhost probes
  - structured telemetry via `traffic_series`
- Current wording to keep honest:
  - say `本地受限进程壳子`
  - do not say `真实隔离沙盒` or `远程攻击执行平面`

## 2026-03-26 Round Update

- Current attack-loop is now a two-step structure:
  - executed `baseline`
  - executed `regression`
- If you later wire a real patched redeploy, update the wording and tests together.

## 2026-03-26 Regression Execution Update

- `patch_reflection` now performs a patched-shell redeploy and a formal regression probe pass.
- Current expected round semantics are:
  - `baseline` = executed baseline probe pass
  - `regression` = executed patched-version regression pass
- Current additive delivery fields are:
  - `regression_target_service`
  - `regression_attack_specs`
  - `regression_attack_results`
  - `regression_vulnerability_verdict`
- Context-window additive delivery fields are:
  - `context_projections.generation`
  - `context_projections.audit`
  - `context_projections.attack_planning`
  - `context_projections.vulnerability_evaluation`
  - `context_projections.patch`
  - `context_projections.reflection`
  - `memory_handoffs`
- Keep the wording honest:
  - say `本地受限进程壳子上的补丁回归执行`
  - do not say `真实隔离沙盒中的生产补丁验证`

## 2026-03-28 Patch Agent Update

- `PatchPlanningAgent` 当前已具备真实 LLM 结构化输出入口，不再适合写成“纯规则拼装”
- 当前 `PatchSpecPayload` 在 workflow 中已新增并稳定传递：
  - `rationale`
  - `implementation_notes`
  - `validation_steps`
  - `rollback_notes`
- 当前运行时会把这批字段继续传给：
  - `delivery.attack_loop.patch_spec`
  - `patch_agent -> attack_planning_agent` 的回归重规划输入
  - `reflection_agent` 的完整 `patch_spec`
- 当前仍需保持诚实的边界：
  - say `真实 LLM 修补规划层`
  - do not say `生产级自动修补执行器`

## 2026-03-29 Patch Execution Workflow Update

- 当前 `patch_reflection` 已不再只完成：
  - patched redeploy
  - regression probe
- 现在还会进一步构建：
  - `patch_execution`
- 当前 workflow 中新增的稳定观测点包括：
  - `delivery.attack_loop.patch_execution`
  - `delivery.attack_loop.rounds[1].patch_execution`
  - `delivery.context_projections.reflection.cards[*].card_type = "patch_execution"`
- 当前 `ReflectionAgent` 会显式消费：
  - `patch_spec`
  - `patch_execution`
  - `patch_artifact_summary`
  - `regression_vulnerability_verdict`
  - `regression_attack_result_summaries`
- 当前正确口径：
  - 已完成 patch execution report 第一版
  - 当前仍是演示级、本地受限进程执行面
  - 不要写成生产级自动 patch release pipeline

## 2026-03-29 Patch Execution Workflow 第二阶段

- 当前 workflow 中，`patch_execution` 的主要新增价值已经从“报告存在”推进到“typed validation handoff”：
  - 让下游窗口知道每一步验证属于什么类型
  - 让下游窗口知道用了哪些证据和工件引用
  - 让反思层拿到 artifact inventory，而不是只看几行 diff

## 2026-04-05 Expert Gate Workflow Update

- 当前 `patch_reflection` 已不再从 `vulnerability_verdict` 直接进入 `PatchPlanningAgent`
- 现在会先经过：
  - `expert_gate_projection`
  - `ExpertGateAgent`
  - `ExpertGateDecisionPayload`
  - `patch_projection`
- 当前 workflow 中新增的稳定观测点包括：
  - `delivery.context_projections.expert_gate`
  - `delivery.attack_loop.expert_gate_decision`
  - `delivery.attack_loop.rounds[0].expert_gate_decision`
  - `delivery.context_projections.patch.cards[*].card_type = "expert_gate_decision"`
- 当前正确口径：
  - 已完成独立 Expert Gate 认知层第一版
  - 已完成 typed decision family / route target 第一版
  - Patch Agent 已真实消费 Expert Gate 输出与 typed route 信号
  - 已完成 `delivery` 观察分支与 `attack_planning_agent` same-run 单次补充攻击闭环
  - 不要写成完整多分支 expert orchestration graph 已完成

## 2026-03-29 后端完整架构工作流提示

- 如果当前任务目标是“先把后端完整架构补齐”，优先阅读：
  - `docs/modules/backend_execution_architecture.md`
  - `docs/modules/mas_workflow.md`
- 当前第一优先级不再是继续补局部 patch/report 细节，而是：
  - `Agent Control Plane`
  - `Context And Memory Bus`
  - `Sandbox Execution Plane`
  - `Persistence Audit Replay Plane`

## 2026-03-29 第一批架构骨架已接入主流程

- 当前不只是“优先级重排”，第一批代码骨架已经落地并接入 `delivery`：
  - `src/cipher_genius/core/control_plane.py`
  - `src/cipher_genius/core/context_bus.py`
  - `src/cipher_genius/sandbox/execution_plane.py`
  - `src/cipher_genius/memory/replay_service.py`
- 当前 workflow 中的稳定观测点新增：
  - `delivery.backend_architecture.control_plane`
  - `delivery.backend_architecture.memory_bus`
  - `delivery.backend_architecture.execution_plane`
  - `delivery.backend_architecture.replay_plane`
- 当前 replay plane 会写入：
  - `.cache/case_timelines/`
- 当前正确口径：
  - 已完成“后端四平面第一批摘要接线”
  - 当前仍是演示级、本地受限进程执行面 + 本地 timeline replay 起点
  - 不要写成完整生产级后端架构已经完成
  - `reflection_memory` 应按“后续同 case 运行回灌”理解，不要把首轮 absence 判成实现缺失
  - replay plane 当前已开始沉淀第一批关键认知事件：
    - `attack_decision`
    - `vulnerability_verdict`
    - `patch_plan`
    - `patch_execution`
    - `reflection_output`

## 2026-03-29 Control Plane Contract 工作流提示

- 如果当前任务继续推进 `Agent Control Plane`，优先关注：
  - `invocations[*].contract`
  - `invocations[*].retry_strategy / termination_mode / decision_source`
  - `checkpoints[*].input_refs / output_refs`
  - `checkpoints[*].termination_signal`
  - `results[*].decision_signal / decision_source / termination_signal`
- 当前 `attack_executor` 是最值得继续扩展的样板阶段，因为它已经具备：
  - planner 决策信号
  - dispatch / skip 分支
  - 明确下一跳为 `vulnerability_evaluation`

## 2026-03-29 Context Bus Typed Family 工作流提示

- 如果当前任务继续推进 `Context And Memory Bus`，优先关注：
  - `windows[*].window_ref / card_family_counts / dominant_card_family`
  - `handoffs[*].projection_ref / card_family_counts / dominant_card_family`
  - `typed_families[*]`
  - `replay_snapshot_card.typed_family_counts / lineage_refs`
- 本轮已继续推进到：
  - `windows[*].typed_contract_counts / dominant_typed_contract`
  - `handoffs[*].typed_contract_counts / dominant_typed_contract`
  - `typed_contracts[*]`
  - `generation_runtime_input / audit_runtime_input` 的 `payload.typed_contract / typed_contract_ref / ref_lookup_hint`
  - `replay_plane.latest_snapshot.typed_contract_counts / artifact_lookup_refs / evidence_lookup_refs`
  - `replay_plane.timeline_summary.latest_typed_contract_count`
  - `replay_snapshot.metadata.window_catalog / handoff_catalog`
  - `timeline/drilldown.projection_relationships / handoff_relationships / service_trajectories`
- 当前这一步的目标不是把所有 card 立刻重写成新 schema，而是：
  - 先把 family / lineage / replay index 做成稳定摘要
  - 再逐步把具体 card 合同收口成更强 typed family / typed contract
  - 让前端与联调侧可以在不共享整轮上下文的前提下恢复多 agent 透明流程与目标服务轨迹
