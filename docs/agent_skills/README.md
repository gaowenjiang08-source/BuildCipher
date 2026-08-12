# Agent Skills (按需加载维护文档)

本目录的 `skill_*.md` 文件用于给维护者与代码 Agent 提供**可按需加载**的上下文切片。

目标：

- 项目变大后，不必一次性加载整仓库文档与源码上下文，减少出错与 Token 消耗
- 让每次改动都能快速定位入口、关键文件、验证方式，提升注意力与修改效率

注意：这里的 **Agent Skill** 是维护文档切片，不是运行时的 `Skill V2`（`data/skills/*.yaml`）。

## 使用方式（推荐）

1. 先打开最匹配的 `skill_*.md`
2. 按 `Key Files` 逐个定位代码
3. 修改后同步更新对应 skill 文档中的：
   - 入口路径/接口/字段名
   - 验证方式（如何确认改动没破）
   - 已知坑与边界
4. 如果改动涉及企业交付模板或评测集，优先加载 `skill_benchmark_reporting.md`

## 编写约定

- 命名：`skill_<topic>.md`
- 粒度：一个 skill 聚焦一个“改动面”，尽量控制在 200 行以内
- 只写“导航与改动点”，不复述大段业务逻辑：
  - 入口、关键文件、关键数据结构/接口（点到为止）
  - 常见修改路径
  - 验证命令与风险清单
- 不写与代码不一致的功能描述；不保留“未实现但写进文档”的能力

## 与 AGENTS.md 对齐（文档同步）

当你修改代码后，除了更新对应 `skill_*.md`，还需按变更类型同步维护文档：

- 后端 API / schema / 返回字段：`README.md`、`QUICK_START_V3.md`、`docs/TECHNICAL_DOCUMENTATION.md`
- MAS / Agent 流程 / Skill 系统：`docs/TECHNICAL_DOCUMENTATION.md`、`DOC_INDEX.md`
- 前端交互与入口：`frontend/README.md`、`QUICK_START_V3.md`

## Skill 清单

- `skill_repo_map.md`：仓库结构与关键入口
- `skill_backend_api.md`：FastAPI 接口、Schema、流式协议
- `skill_mas_workflows.md`：LangGraph 主线、MAS 执行链路、agent 与 system module 分层、主流程改动点
- `skill_attack_agent_enhancement.md`：攻击 Agent 的 skill / policy / retrieval 增强入口，避免把论文长文本直接塞进 planner prompt
- `skill_skill_v2.md`：运行时 Skill V2（manifest、路由、执行）
- `skill_benchmark_reporting.md`：建筑 Skill、模板和 benchmark 回归要点
- `skill_benchmark_reporting.md`：评测集、企业交付模板、报告结构与 benchmark 验证
- `skill_frontend_react.md`：React 前端结构、状态管理与接口调用
- `skill_streamlit_compat.md`：Streamlit 兼容入口与 UI 模块
- `SKILL_TEMPLATE.md`：新建 skill 的模板

## 增量更新（2026-03-29）

- `skill_backend_api.md`
  - 已补充 `PatchExecutionPayload / PatchValidationResultPayload`、新增 API 观测点与回归检查项
- `skill_mas_workflows.md`
  - 已补充 `patch_execution` 进入 `reflection` 独立窗口后的 workflow 口径与边界说明
  - 已补充 `typed validation handoff` 与 supporting artifact pipeline 的第二阶段口径
  - 已补充 replay plane 第一批关键认知事件，以及 `reflection_memory` 应按“后续同 case 运行回灌”理解的测试与文档边界

## 增量更新（2026-03-30）

- `skill_backend_api.md`
  - 已补充 `control_plane` 第二阶段合同字段，覆盖 `retryable / retry_strategy / termination_mode / decision_source / termination_signal`
  - 已补充 `memory_bus` 第二阶段 contract / lookup 摘要，覆盖 `typed_contracts`、`typed_contract_counts` 与 `ref_lookup_hint`
  - 已补充 `replay_plane` 第二阶段 contract / lookup 索引，覆盖 `latest_snapshot.typed_contract_counts` 与 `latest_typed_contract_count`
  - 已补充 replay 查询入口，覆盖 `GET /api/v1/cases/{case_id}/timeline|events|snapshots|lineage` 与对应 schema
  - 已补充 `projection_ref / handoff_ref / run_id` 的 replay drill-down 过滤口径
  - 已补充 `GET /api/v1/cases/{case_id}/timeline/drilldown` 的聚合回看 schema 与边界
  - 已补充 `projection_relationships / handoff_relationships` 关系视图 schema
  - 已补充 `handoff_relationships` 的上下游 agent/stage 字段、`service_trajectories` 轨迹 schema 与 `window_catalog / handoff_catalog` 来源说明
- `skill_mas_workflows.md`
  - 已补充 `Agent Control Plane` 第二阶段工作流提示，强调控制信号来源、重试策略与终止信号
  - 已补充 `generation / audit` 前半段 projection-only 的第二阶段口径，强调 `typed_contract / typed_contract_ref / ref_lookup_hint`
- `skill_frontend_react.md`
  - 已补充报告页对 `timeline / drilldown` 的 replay 深钻适配口径，覆盖 `handoff_relationships / service_trajectories`
  - 已补充点击 `projection_ref / handoff_ref / target_service_ref` 的本地深钻与 version lineage 拉取口径

## 增量更新（2026-04-05）

- `skill_backend_api.md`
  - 已补充 `ExpertGateDecisionPayload` 的 `decision_family / decision_family_label / route_target / route_target_label` 第一版 contract 口径
  - 已补充 `retry_attack_*` 与 `sandbox_dispatcher.retry_attack` 的联调提示
- `skill_mas_workflows.md`
  - 已补充 `Expert Gate` typed route 第一版已落地、`PatchPlanningAgent` 已消费 typed route 信号、完整多分支子图仍未完成的工作流边界
  - 已补充 `attack_planning_agent` same-run 单次补充攻击闭环已落地的工作流口径
