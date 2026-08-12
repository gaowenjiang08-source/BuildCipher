# 专项模块文档

## 2026-04-11 增量更新

- `buildtrust_construction.md`
  - 建筑领域模型、五攻击、证据合同与能力边界
  - 当前已开始服务业务前台第一版落地，不再只是纯设计占位文档

## 2026-04-05 增量更新

- `mas_workflow.md`
  - 已补“有限 re-gate 第一版”的真实主线、输出字段与边界
- `backend_execution_architecture.md`
  - 已补 `patch_reflection` 在 re-gate 后的控制平面/输出引用优先级说明

最后更新：2026-04-20
状态：active

本目录用于承载“全局总文档之外，但又比单个目录 README 更需要长期维护”的技术说明。

适合放在这里的内容：

- 某一类能力的统一约定
- 为什么这样设计，而不是只记录“现在代码长什么样”
- 数据对象、扩展方式、验证方式
- 多个目录共同遵循的规则

不适合放在这里的内容：

- 对外介绍、启动方式、项目定位
- 某一个目录内部非常局部的实现细节
- 已经失效但没有标注状态的历史方案

## 推荐阅读顺序

1. 先看根目录文档
   - `README.md`
   - `DOC_INDEX.md`
   - `REMAIN.md`
   - `TODO_VIBING.md`
2. 再看本目录中的专项文档
3. 最后按需进入具体目录的 `README.md`

## 当前专项文档

- `retrieval_knowledge_base.md`
  - 企业知识、规范、组件知识卡、历史案例如何进入统一知识库与检索主链
- `mas_workflow.md`
  - 当前 MAS 主线、Legacy / LangGraph 分工、目标节点与编排演进说明
- `case_memory.md`
  - 项目级记忆的对象边界、与聊天历史的区别、推荐 schema 与落地顺序
- `citation_delivery.md`
  - 引用驱动交付的 claim/source 结构、导出保留策略与主线闭环说明
- `backend_execution_architecture.md`
  - 后端执行架构蓝图、projection-only 收口、Sandbox Dispatcher 边界与实施顺序
- `target_service_templates.md`
  - 模拟服务器端 / 目标服务模板的 schema、部署 manifest、runtime profile 与 telemetry 契约
- `executor_handoff_adapter.md`
  - `container / remote_worker` 的 typed handoff adapter、交接回执、artifact sync 与 replay 回查设计
- `buildtrust_construction.md`
  - BuildTrust 建筑业务与执行面设计
- `frontend_runtime_console_architecture.md`
  - 下一阶段前端运行控制台架构、一级页面信息架构、事件模型与组件分层
- `frontend_page_state_architecture.md`
  - 前端页面树、Zustand 状态树、事件接入层与 selector 分层

## 维护原则

- 每篇文档顶部都写清楚“最后更新”和“状态”
- 优先说明“为什么这样设计”“适用范围”“扩展方式”“验证方式”
- 文档必须贴近仓库当前代码和资产，不要脱离现实空谈未来蓝图
- 如果某份文档已经过时，应改为 `status: deprecated` 或 `status: draft`

## 写作模板

新增专项文档时，优先复用：

- `MODULE_DOC_TEMPLATE.md`
## 增量更新（2026-03-24）

- `knowledge_ingestion.md`
  - 面向 PDF / Word 企业文档 ingestion 的 parser、chunk schema、脚本入口与后续 OCR / 向量入库演进路线
## 增量更新（2026-03-26）

- `backend_execution_architecture.md`
  - 后端执行架构蓝图、projection-only 收口、Sandbox Dispatcher 边界与实施顺序

## 增量更新（2026-03-27）

- `backend_execution_architecture.md`
  - 已补充 `AttackPlanningAgent` 如何真实控制 dispatch，以及 planner-controlled synthetic dispatch 的边界说明
- `mas_workflow.md`
  - 已补充 `handoff_to_vulnerability / stop` 如何改变主流程控制流，以及 `delivery.attack_loop.rounds[*].mode` 的稳定口径
  - 已补充 `artifact_summarizer` 如何把 `trace / metrics / finding` 压进主链独立上下文窗口
- `backend_execution_architecture.md`
  - 已补充 `artifact_summarizer` 第二阶段首版如何把 baseline / patched workspace 的实现差异压缩进 execution plane
- `mas_workflow.md`
  - 已补充 `patch_agent -> reflection_agent` 新增 `patch_artifact_summary` card 的契约与使用目的
- `backend_execution_architecture.md`
  - 已补充 `ReflectionAgent` 作为独立 cognition layer 接入后的执行面定位
- `mas_workflow.md`
  - 已补充 `ReflectionAgent` 稳定输出 `reflection / regression_summary` 两张卡的口径
- `case_memory.md`
  - 已补充 `recent_reflections`、`reflection_count`、`reflection_memory` 的项目级回灌第一版，以及“为什么当前是跨 run 回灌而不是 same-run 回灌”的实现边界
- `backend_execution_architecture.md`
  - 已补充 `reflection_cards -> case_memory -> next-run projection replay` 的执行面定位
- `target_service_templates.md`
  - 已新增模拟服务器端如何模板化、如何服务 baseline / patched / regression，以及如何给前端提供稳定 telemetry 契约

## 增量更新（2026-03-29）

- `backend_execution_architecture.md`
  - 已补充 `patch_execution` 在执行架构中的定位，明确 `PatchPlanningAgent -> dispatcher/runtime -> patch execution report -> ReflectionAgent` 的分层关系
- `mas_workflow.md`
  - 已补充 `patch_execution` 如何作为回归轮后的结构化收口进入 `reflection` 独立窗口，以及新增的稳定观测字段
  - 已补充 `patch_execution` 第二阶段如何把 typed validation 与 supporting artifacts 送入独立窗口
  - 已补充“后端完整架构补齐 V2”，明确 `control plane / memory bus / execution plane / replay plane` 为后续第一优先级
- `backend_execution_architecture.md`
  - 已补充第一批代码骨架落地状态，明确 `control_plane.py / context_bus.py / execution_plane.py / replay_service.py` 已进入主链摘要接线
- `backend_execution_architecture.md`
  - 已补充 replay plane 第一批关键认知事件，明确 `attack_decision / vulnerability_verdict / patch_plan / patch_execution / reflection_output` 的定位与边界
- `backend_execution_architecture.md`
  - 已把后端四条主线继续拆成 `P0-1 ~ P0-4` 的可执行任务块，明确重点文件与推进边界
- `mas_workflow.md`
  - 已补充 `reflection_memory` 的真实验证边界：首轮新 `case_id` 无历史回灌时，absence 属于正常行为；稳定验证应放在后续同 case 运行
- `src/cipher_genius/memory/README.md`
  - 已补充 `.cache/case_timelines/`、`CaseTimelineService` 与 `delivery.backend_architecture.replay_plane` 的对齐说明

## 增量更新（2026-03-30）

- `backend_execution_architecture.md`
  - 已补充 `Agent Control Plane` 的第二阶段合同字段，新增重试策略、决策来源、终止信号与对应的 P0 落地拆分
  - 已补充 `Context And Memory Bus` 第二阶段摘要，新增 `typed_contracts`、`typed_contract_counts` 与 `artifact/evidence` 回查索引提示
  - 已补充 replay plane 第二阶段索引，新增 `latest_snapshot.typed_contract_counts` 与 lookup refs 的回放口径
  - 已补充单 case 的本地 replay 查询入口，明确 `timeline / events / snapshots / lineage` 的接口定位与边界
  - 已补充 `Sandbox Execution Plane` 第一版统一执行合同，明确 `execution_plane.operations[*]` 如何收口 `deploy / attack / patch_apply / rollback / regression_replay`
  - 已补充 `query_version_lineage(...)` 与 `GET /api/v1/cases/{case_id}/timeline/lineage` 的过滤口径，覆盖 `run_id / target_service_ref / patch_id / baseline_version / patched_version`
  - 已补充沿 `projection_ref / handoff_ref` 做本地 replay drill-down 的查询口径
  - 已补充 `GET /api/v1/cases/{case_id}/timeline/drilldown`，把单个 scope 下的 snapshots / events / lineage 聚合成可直接消费的本地回看视图

## 增量更新（2026-04-05）

- `mas_workflow.md`
  - 已补充 `ExpertGateDecisionPayload` 的 typed decision family / route target 第一版，以及 `PatchPlanningAgent` 的消费边界
  - 已补充 `route_target = "delivery"` 与 `route_target = "attack_planning_agent"` 的真实运行时分支边界
- `backend_execution_architecture.md`
  - 已补充 `ExpertGate` 独立认知层在执行架构中的 typed route 语义与当前未完成边界
  - 已补充 same-run 单次补充攻击闭环在执行架构中的位置与限制
  - 已补充 `projection_relationships / handoff_relationships` 关系摘要，支撑前端多 agent 流程透明化
  - 已补充 `handoff_relationships` 的上下游 agent/stage 字段与 `service_trajectories` 目标服务轨迹口径
  - 已补充 `window_catalog / handoff_catalog` 作为本地关系恢复来源的设计说明
- `case_memory.md`
  - 已补充 `payload.typed_contract / typed_contract_ref / ref_lookup_hint` 的设计口径，解释为什么前半段 projection-only 需要稳定 card 合同与回查提示
## 增量更新（2026-04-01）

## 增量更新（2026-04-02）
- `backend_execution_architecture.md`
  - 已补充 `dispatcher / patch_execution / execution_plane` 第二轮合同加固
  - 已明确 `operation_kind / executor_kind / capability_flags / artifact_refs` 的定位
- `src/cipher_genius/sandbox/README.md`
  - 已补充 patch/rollback artifact refs、失败分类与当前 executor contract 口径
- `src/cipher_genius/core/README.md`
  - 已补充 `patch_execution` 新增 artifact refs 与 execution contract version

- `backend_execution_architecture.md`
  - 已补充 `patch_apply / rollback_plan` 如何从 execution-plane 摘要推进到真实 dispatcher/runtime 边界
  - 已明确 `patch_execution` 与 `patch_apply dispatch / rollback dispatch / regression dispatch` 的分层关系
- `src/cipher_genius/sandbox/README.md`
  - 已补充 `patch_manifest.json / patch_metadata.json / rollback_plan.json / rollback_manifest.json`
  - 已补充 `patch_executor / rollback_executor` 两类新调度入口
## 增量更新（2026-04-02 Executor Backend Matrix）

- `backend_execution_architecture.md`
  - 已补充 executor backend matrix 的设计口径
  - 已明确 `local_process / container / remote_worker` 三类 executor 的合同边界
  - 已补充 `executor_handoff_required` 等 executor 侧失败分类
- 本轮如果继续改 sandbox 执行器扩展路径，优先参考：
  - `backend_execution_architecture.md`
  - `src/cipher_genius/sandbox/README.md`

## 增量更新（2026-04-03）

- `backend_execution_architecture.md`
  - 已补充 replay plane 如何显式沉淀 `dispatch_refs / failed_dispatch_refs`
  - 已补充 `patch_execution_artifact_refs` 与 `artifact_lookup_ref` drill-down 的当前合同

## 增量更新（2026-04-03 Typed Dispatch Summary）

- `backend_execution_architecture.md`
  - 已补充 replay plane 中 typed `dispatch_summaries / failed_dispatch_summaries` 的定位和目的
