# 后端执行架构设计

最后更新：2026-04-06
状态：active

## 2026-04-06 Replay / Timeline Retry 恢复点接线补记

- 当前 `Persistence Audit Replay Plane` 已把 retry 子链的压缩与恢复点合同接到 run snapshot metadata：
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
- 当前这些字段的来源仍是 `memory_bus.summary`，也就是：
  - 先在上下文总线层聚合
  - 再在 replay 平面做落盘与回放查询
- 当前 `timeline/drilldown.summary` 已能对匹配 snapshots 聚合同一批字段，方便前端把“本轮补充攻击是如何压缩、保留、恢复定位”的解释直接挂到 drilldown 视图。
- 当前 replay plane 查询侧已支持：
  - `retry_resume_checkpoint_ref`
  - `retry_resume_input_ref`
  可直接把恢复点 ref 映射回同 run 的 snapshots / events / drilldown scope。
- 这意味着当前 replay plane 已具备：
  - retry 子链恢复点可回看
  - retry 压缩策略可回看
  - retained refs / resume refs 可回看
- 当前仍未具备：
  - 依据这些恢复点自动恢复执行
  - 多轮 retry 的预算调度器
  - 跨 case 的恢复点检索中心

## 2026-04-06 Same-Run Retry 预算执行补记

- 当前执行架构已把 same-run retry 预算分布到三层：
  - API 请求层：`max_same_run_retries`
  - 配置层：`SAME_RUN_RETRY_BUDGET_DEFAULT`
  - Runtime state 层：`same_run_retry_budget`
- 当前 `delivery.attack_loop` 已把运行结果收口为三项稳定指标：
  - `same_run_retry_summary`
  - `same_run_retry_budget`
  - `same_run_retry_used`
  - `same_run_retry_remaining`
- 其中 `same_run_retry_summary` 当前用于表达：
  - 请求是否出现
  - retry flow 是否真正启动
  - 是否被预算阻断
  - 是否在二次 gate 后封顶
  - 最终收口分辨率
- 当前 `same_run_retry_summary.attempt_trace` 还会保留单次尝试的执行轨迹，作为后续多轮预算调度与上下文压缩策略的骨架输入
- 当前这条轨迹还会补上下列可回查引用：
  - retry planning / vulnerability / re-gate projection ref
  - 对应 memory handoff id
- 当前 memory bus 还会把 retry 子链单独汇总为：
  - `retry_window_count`
  - `retry_handoff_count`
  - `retry_projection_refs`
  - `retry_handoff_refs`
  - `retry_lineage_refs`
  - `retry_typed_contract_refs`
- 当前 retry 子链的独立窗口还会显式生成 `retry_context_summary`，作为压缩与 lineage 锚点卡
- 当前 `memory_bus.summary` 也已开始聚合 retry 压缩策略：
  - `retry_compression_stages`
  - `retry_compression_policies`
  - `retry_retained_refs`
  - `retry_resume_checkpoint_refs`
  - `retry_resume_input_refs`
- 当前控制平面也会把这份解释合同透传到：
  - `control_plane.summary.same_run_retry`
  - `patch_reflection` / `delivery` 阶段 metadata
- 这意味着当前控制平面与执行平面已经能区分：
  - “被允许的一次 retry”
  - “预算为 0 的直接收口”
  - “二次 gate 再次请求 retry 但预算已耗尽的 capped 收口”
- 当前 `loop_status` 也会同步区分：
  - `retry_blocked_by_budget`
  - `retry_capped`
- 当前边界：
  - 还没有进入真正的多轮递归攻击/评估/修补子图
  - 还没有实现按预算驱动的容器池、远程 worker 或上下文分层淘汰

## 1. 适用范围

本文聚焦当前项目后端主线里最关键的四个平面，以及它们在当前仓库中的第一批落地方式：

- `Agent Control Plane`
- `Context And Memory Bus`
- `Sandbox Execution Plane`
- `Persistence Audit Replay Plane`

适用范围包括：

- `src/cipher_genius/core/langgraph_mas.py`
- `src/cipher_genius/core/mas_runtime_support.py`
- `src/cipher_genius/api/schemas.py`
- `src/cipher_genius/sandbox/`
- `docs/modules/mas_workflow.md`
- `docs/modules/case_memory.md`

本文不负责定义前端页面长什么样，也不负责描述答辩展示文案。本文的目标是先把后端真正要完成的架构蓝图和已落地骨架固定下来。

## 2. 为什么现在先做后端架构

当前项目已经有：

- LangGraph 主链
- 检索与证据主线
- 项目级记忆骨架
- 本地受限进程壳子的攻击闭环第一版
- `context_projections` / `memory_handoffs` 的第一版运行时输出

但还没有真正完成的，是“后端如何稳定地把这些对象收口成可持续演进的执行架构”。

如果这个阶段先把主要精力放到前端展示上，会出现 3 个问题：

- 前端会提前消费不稳定字段
- 后端会被展示需求反向牵引，难以继续收口
- 团队容易把“有可视化”误判成“架构已经完成”

因此当前更合理的推进顺序应是：

1. 先固化后端执行架构
2. 再按该架构补运行时收口
3. 最后让前端按稳定对象做展示

## 3. 当前真实状态

### 3.1 已完成

- LangGraph 是唯一主线
- 已新增第一批后端架构骨架代码：
  - `src/cipher_genius/core/control_plane.py`
  - `src/cipher_genius/core/context_bus.py`
  - `src/cipher_genius/sandbox/execution_plane.py`
  - `src/cipher_genius/memory/replay_service.py`
- `generation / audit / attack_planning / vulnerability_evaluation / patch / reflection` 已生成独立 projection
- `delivery.context_projections` 与 `delivery.memory_handoffs` 已可用于联调
- `delivery.backend_architecture` 已开始增量返回：
  - `control_plane`
  - `memory_bus`
  - `execution_plane`
  - `replay_plane`
- `execution_plane` 当前已不再只有 `stages[*]`，还开始显式返回：
  - `summary.contract_version = "v1"`
  - `summary.operation_count`
  - `summary.operation_kind_counts`
  - `plan.operation_kinds`
  - `operations[*]`
- `reflection_cards -> case_memory.recent_reflections -> next-run generation/audit reflection_memory` 的项目级回灌第一版已接入
- `generation / audit` 已开始在执行层消费 `reflection_memory`，不再只停留在 projection 展示层
- `generation / audit` projection 已新增 `generation_runtime_input / audit_runtime_input`，前半段开始按“先 projection、再恢复运行时输入”的方式收口
- `audit` 当前已新增候选方案级 `audit_decision_input`，并由 `AuditEvaluationAgent` 在独立窗口里输出最终裁决
- 当前 `audit` 更准确的定位是“工具增强的独立 LLM 裁决层”，而不是单纯规则拼装
- `vulnerability_verdict -> expert_gate_decision -> patch_spec` 已形成独立认知层接线：
  - `ExpertGateAgent` 负责漏洞裁决后的独立放行 / 修补决策
  - `PatchPlanningAgent` 再消费专家闸门结果生成修补规划
- 本地受限进程壳子已支持：
  - 目标服务部署
  - 基线攻击执行
  - 漏洞评估
  - 补丁版本壳子重部署
  - 正式回归探测
- `AttackPlanningAgent` 已可通过动作分支真实控制执行面：
  - `execute / continue / replan` 会继续进入 dispatch
  - `handoff_to_vulnerability / stop` 会跳过新的 attack dispatch
- `delivery.sandbox_dispatcher.*attack` 已能在未执行场景返回 planner-controlled synthetic dispatch，供审计、前端和后续 handoff 统一消费
- run 级 replay snapshot 已可写入：
  - `.cache/case_timelines/`

### 3.2 未完成

- agent 仍未彻底改成只消费 projection
- `graph state` 仍保留较多兼容字段
- 还没有完整 `Sandbox Dispatcher`
- `artifact_summarizer` 已完成第一版主链接入，但还未覆盖全部工件类型
- 还没有完整的 handoff policy
- 还没有容器级隔离或远程执行平面
- 还没有完整事件化 replay center
- `Expert Gate` 仍未扩展为完整多分支路由子图

## 4. 目标架构

推荐把后端执行架构分成 4 层：

### 4.1 Orchestration Layer

由 LangGraph 主图负责：

- 节点编排
- 路由决策
- 阶段状态推进
- 持久化 / checkpoint 边界

这层只负责“流程控制”，不负责直接拼 prompt，也不负责直接发起攻击执行。

### 4.2 Context Projection Layer

这层负责：

- 为每个 agent 生成独立上下文窗口
- 控制窗口大小
- 从 case memory、evidence、artifact 中抽取最小输入切片
- 生成稳定 `ContextProjectionPayload`

这层的目标不是“让上下文更多”，而是“让上下文刚好够用”。

### 4.3 Memory Handoff Layer

这层负责：

- 把上游结果压缩成 card
- 绑定 artifact / evidence ref
- 生成稳定 `MemoryHandoffPayload`
- 区分短期运行状态与长期项目记忆

这层的关键不是消息转发，而是压缩和治理。

### 4.4 Execution Plane

这层负责：

- 目标服务部署
- 攻击任务调度
- 执行器调用
- 结果采集
- 工件沉淀

Execution Plane 不等于 agent。  
它应主要由 system module 组成，其中 `Sandbox Dispatcher` 是执行面治理的核心。

## 5. 2026-03-27 攻击规划如何控制执行面

当前执行面的一个关键收口已经完成：攻击规划 agent 不再只是返回“给前端展示的决策字段”，而是会真实影响 dispatch。

推荐按下面这条规则理解后端链路：

1. `AttackPlanningAgent` 消费独立 `attack_planning_projection`
2. 输出 `AttackDecisionPayload + AttackSpecPayload[]`
3. Orchestration Layer 判断该动作是否允许继续 dispatch
4. 只有允许 dispatch 的动作才会进入 `Sandbox Dispatcher`
5. `handoff_to_vulnerability / stop` 会构造 synthetic dispatch，并直接把控制流交给漏洞评估层

这样设计的原因：

- 保证“不同 agent 独立上下文窗口”的架构约束不被执行器反向污染
- 保证 `memory_handoff` 可以稳定传递 decision card，而不是依赖运行时隐式状态
- 保证未来替换为容器级隔离或远程执行平面时，不需要把控制逻辑塞回 prompt

当前执行面仍未完成的部分：

- `artifact_summarizer` 第二版扩展
- 失败分类与预算治理的更细粒度收口
- 容器级隔离 / 远程执行 / 多租户安全边界

## 5.1 2026-03-27 Artifact Summarizer 第一版落地

当前 `artifact_summarizer` 已作为独立 system module 进入主链，负责把沙盒执行面产生的大工件压缩后再交给下游 agent。

当前第一版已覆盖：

- `trace.jsonl`
- `metrics.json`
- `finding.json`

当前已接入的窗口：

- `vulnerability_evaluation`
- `patch`
- `reflection`

当前输出口径：

- `attack_result_summaries`
- 富化后的 `artifact_refs[*].summary`
- 富化后的 `artifact_refs[*].metadata`

这一步的核心意义不是“前端多了几个字段”，而是：

- execution plane 终于开始通过稳定 system module 向 context layer 提供压缩结果
- `projection + memory_handoff` 开始摆脱大对象直传
- 后续接入 `patch diff` 与更长日志时，有了统一扩展点

## 5. Projection-Only 执行收口

## 5.1 定义

`projection-only` 的意思不是“系统里只剩 projection 这个对象”，而是：

- 每个 agent 的直接输入只来自 projection
- agent 不再直接读取整段 `graph state`
- 上游信息必须先经过 projection builder / handoff policy 才能进入下游窗口

换句话说，projection 应成为 agent 输入的唯一合法入口，而不是调试附属物。

## 5.2 当前问题

当前虽然已经生成了 projection，但实际执行仍是“双轨”：

- 一边保留旧 state 字段
- 一边额外生成 projection

这对过渡是有帮助的，但不是最终形态。长期问题包括：

- 输入源不唯一
- 很难保证 agent 真正独立
- 无法明确哪些信息是“必需输入”，哪些只是“兼容残留”

## 5.3 目标形态

建议未来收口成下面的模式：

1. 节点前半段只构造 projection / handoff
2. agent 执行器只读取 projection
3. agent 输出先转 card / decision / artifact ref
4. 下游节点只消费 handoff，而不是回头翻全量 state

## 5.3.1 为什么不能只靠“薄 JSON”

当前主线已经明确走结构化传递，但这里必须讲清楚一个边界：

- 问题不在于“是否用 JSON”
- 问题在于“JSON 是否只是过薄摘要”

如果只传一句自然语言 summary，下游 agent 很容易因为信息量不足而失去判断能力。更合理的做法不是回退到共享长上下文，而是坚持三层结构：

1. `structured card / projection payload`
   - 传递目标、约束、决策、finding、verdict、patch strategy
2. `artifact / evidence ref`
   - 传递可回查的大工件引用，而不是把全文塞进窗口
3. `artifact summary`
   - 为下游窗口提供足够做判断的压缩摘要

因此当前推荐口径应固定为：

- JSON 本身是合理的
- 但必须是 `card + summary + ref` 的混合结构
- 不能退化成“只有几个字段的薄 JSON”

这也是当前为什么要继续保留：

- `attack_result_summaries`
- `patch_artifact_summary`
- `reflection_memory`
- `artifact_refs`

未来如果 generation / audit 出现“拿到 reflection_memory 但仍不够做决策”的问题，优先补的是：

- 更丰富的 typed card
- 更好的 artifact summary
- 更清晰的 ref 回查策略

而不是重新把整轮长上下文广播给所有 agent

## 5.3.2 2026-03-28 Patch Cognition Layer 增强

当前执行架构里的 `Patch Agent` 需要更准确地理解为：

- 不是“规则化 patch 结果拼装器”
- 而是“真实 LLM 修补规划层 + 兼容 fallback”

本轮执行面与认知层新增的稳定对象包括：

- `PatchSpecPayload.rationale`
- `PatchSpecPayload.implementation_notes`
- `PatchSpecPayload.validation_steps`
- `PatchSpecPayload.rollback_notes`

这样做的意义是：

- 让 patch cognition layer 不只输出“怎么改”，还输出“为什么这样改、如何验证、失败时如何回滚”
- 让回归重规划与 reflection 能消费更完整的 patch intent，而不只是一个 `strategy + summary`
- 保持执行面仍由 dispatcher / runtime 控制，不让 Patch Agent 直接越过执行边界

当前边界仍应保持诚实：

- 已完成的是“真实 LLM 修补规划层增强”
- 未完成的是“生产级 patch 执行器、容器级隔离与远程执行平面”

## 5.4 推荐收口顺序

不要一次性把所有节点都改成 projection-only，推荐按顺序推进：

1. `attack_planning_agent`
2. `vulnerability_agent`
3. `patch_agent`
4. `reflection_agent`
5. `generation_agent`
6. `audit_agent`

原因是：

- 攻防闭环里的上下文污染成本更高
- 这几段对 artifact / finding / verdict 的结构化依赖最强
- 先收口它们，能更快验证 memory handoff 是否真的成立

## 5.5 Projection Builder 的稳定职责

推荐后续把 projection builder 显式收口成稳定 helper，而不是散落在节点内部。

建议至少分成：

- `build_generation_projection`
- `build_audit_projection`
- `build_attack_planning_projection`
- `build_vulnerability_projection`
- `build_patch_projection`
- `build_reflection_projection`

每个 builder 的输出都应只承担一件事：

- 当前角色必须完成什么
- 当前角色必须遵守什么
- 当前角色必须读取哪些 card
- 当前角色只需知道哪些 artifact / evidence ref

## 6. Sandbox Dispatcher 设计

## 6.1 为什么需要 Dispatcher

如果 `Attack Planning Agent` 直接生成攻击计划，`Attack Executor` 直接执行，中间没有治理层，就会出现：

- 预算不可控
- 白名单不可控
- 输入不稳定
- 审计责任不清
- 后续替换执行器困难

所以 `Sandbox Dispatcher` 的职责不是“多加一层代码”，而是把执行面从“直接调用”变成“受策略治理的调度”。

## 6.2 Dispatcher 的核心职责

推荐 `Sandbox Dispatcher` 只做下面 6 件事：

1. `schema 校验`
   - 校验攻击任务描述是否满足稳定结构
2. `预算校验`
   - 校验 CPU、内存、超时、并发预算
3. `白名单校验`
   - 限制允许访问的目标接口、命令、运行时能力
4. `签名与派发`
   - 生成可追踪 task id，并下发给执行器
5. `失败分类`
   - 区分策略拒绝、部署失败、执行失败、结果不完整
6. `执行后回收`
   - 统一收集结果、状态、日志路径和清理动作

Dispatcher 不负责漏洞判断，不负责补丁设计，也不负责最终交付渲染。

## 6.3 推荐输入输出

### 输入

- `TargetServiceSpec`
- `AttackSpec`
- `ExecutionBudget`
- `SandboxPolicy`
- `RunContext`

### 输出

- `DispatchRecord`
- `ExecutionReceipt`
- `AttackResultSpec`
- `FailureClassification`
- `ArtifactManifest`

如果未来要补 schema，优先沿这个方向新增稳定对象，而不是继续把字段散落在 `dict[str, Any]` 里。

## 6.4 Dispatcher 与 Executor 的边界

推荐严格分层：

- `Sandbox Dispatcher`
  - 负责策略、校验、签名、预算、派发
- `Attack Executor`
  - 负责真正执行任务
- `Result Aggregator`
  - 负责收集 telemetry、finding、artifact ref

这样未来替换本地执行器时，不需要重写整个主链。

## 6.5 当前建议的最小实现

当前项目并不需要马上做成复杂的分布式调度平台。更现实的最小版本是：

- 本地单机 Dispatcher
- 本地受限进程执行器
- 本地 artifact store

## 6.6 模拟服务器端是否可完成

结论是：可以，而且当前已经完成了第一版雏形。

当前本地执行面已经具备：

- 目标服务壳子部署
- 健康检查
- 接口探测
- `trace / metrics / finding` 工件沉淀
- patch 后重部署
- regression 再验证

因此当前更准确的定义不是“真实业务服务器”，而是：

- 可部署
- 可观测
- 可攻击
- 可回归

的 `target service template runtime`

后续建议把“模拟服务器端”继续收口成模板化目标服务体系，而不是临时脚本：

- `service_template`
  - 定义服务暴露接口、加密行为、错误处理模式
- `deployment_manifest`
  - 定义端口、启动命令、健康检查、版本号
- `runtime_profile`
  - 定义 telemetry、预算和清理动作

这样既能支撑比赛演示，也能为未来容器化执行平面保留升级路径。

## 6.7 沙盒可视化是否可完成

结论是：可以完成，而且当前后端已经提供了第一版可视化所需的大部分数据对象。

当前前端或后续可视化层可直接消费的后端对象包括：

- `delivery.attack_loop`
- `delivery.attack_loop.rounds`
- `delivery.sandbox_dispatcher`
- `attack_results[*].metrics.traffic_series`
- `delivery.context_projections`
- `delivery.memory_handoffs`
- `delivery.attack_loop.reflection_cards`

因此当前更推荐的可视化分层是：

1. `流程透明化`
   - 展示 planner 决策、轮次状态、handoff / stop / execute
2. `沙盒态势`
   - 展示目标服务状态、攻击任务状态、流量波动、工件数量
3. `闭环演化`
   - 展示 baseline / regression 对比、patch diff 摘要、reflection lesson

当前必须讲清楚的边界是：

- 这能支撑比赛级、答辩级、演示级可视化
- 这不等于生产级攻击监控平台
- 可视化真实感依赖 telemetry 丰富度，而不是图表组件本身

## 6.8 攻击 Agent 是否需要 Skill / 论文增强

结论是：需要，而且应优先走“skill + retrieval”增强，而不是长 prompt 堆料。

更合理的增强方式分成两层：

### 1. 策略知识层

由 skill 或攻击策略库提供：

- 攻击面分类
- 常见密码部署误用模式
- 密钥托管 / 错误处理 / 接口边界检查框架
- 不同攻击动作的预算与风险边界

### 2. 证据经验层

由论文、benchmark、历史 case 提供：

- 攻击模式总结
- exploitability 判断经验
- 某类算法或协议的高频弱点
- 历史失败模式与修补经验

因此当前推荐设计不是：

- 把论文原文直接塞进攻击 agent 窗口

而是：

1. 把论文和资料转成可检索知识对象
2. 由 skill 把这些知识组织成 planner 可消费的攻击策略框架
3. 由 `AttackPlanningAgent` 在独立 projection 中按需取用

这条路线的好处是：

- 降低上下文膨胀
- 提高攻击规划可重复性
- 更适合 benchmark 与后续评测闭环
- 结构化结果回写主链

也就是说，先把“治理边界”做好，再逐步替换“执行底座”。

## 7. Artifact Summarizer 设计位置

`artifact summarizer` 不建议塞到 agent prompt 里临时完成，更推荐作为 system module 存在。

它的职责应是：

- 读取大日志 / trace / 代码 / diff
- 生成可控长度摘要
- 输出稳定 artifact summary card
- 提供给 projection builder 使用

这样才能避免：

- 每次都把大对象原文塞给 agent
- 上下文无控制地膨胀
- 不同 agent 对同一份 artifact 得到风格不一致的摘要

## 8. 推荐实施顺序

推荐的后端实施顺序如下：

1. 固化本文档中的边界定义
2. 把 `Sandbox Dispatcher` 设计成稳定 system module 接口
3. 让 `attack_planning / vulnerability / patch / reflection` 优先改成 projection-only 输入
4. 接入 `artifact summarizer`
5. 收口 handoff policy
6. 最后再评估是否把 `generation / audit` 也完全收口成 projection-only

这个顺序的核心原则是：

- 先收后端执行面
- 再收上下文治理
- 最后补展示层

## 9. 验证方式

后续实现时，至少按下面 4 类验证：

### 9.1 契约验证

- projection schema 是否稳定
- handoff schema 是否稳定
- `delivery` 增量字段是否保持兼容

### 9.2 执行验证

- Dispatcher 是否能拒绝非法任务
- 合法任务是否能稳定下发到本地执行器
- 结果是否能稳定回写为结构化对象

### 9.3 闭环验证

- patch 后是否能触发正式回归探测
- reflection 是否能形成下一轮可消费 card
- 多轮执行是否仍能保持上下文边界清晰

### 9.4 边界验证

- 文档中是否仍保持“演示级、本地受限进程沙盒”的诚实口径
- 不把当前实现误写成容器级隔离或生产级执行平台

## 10. 当前不应过早承诺的能力

在真正完成下面这些之前，不建议对外承诺：

- 容器级隔离沙盒
- 远程主机攻击执行平面
- 生产网络自动攻击
- 生产级补丁验证
- 所有 agent 已完全只读 projection

更合适的表达应始终保持为：

- 后端架构已进入“projection-only + Dispatcher”收口阶段
- 本地受限进程闭环已打通第一版
- 生产级执行平面仍在后续演进范围内

## 2026-03-26 实现进展补记：Dispatcher Skeleton

当前已落地的不是“完整 Sandbox Dispatcher”，而是第一版 skeleton：

- 已新增 `SandboxPolicyPayload`
- 已新增 `SandboxDispatchRequestPayload`
- 已新增 `SandboxDispatchResultPayload`
- 已新增 `SandboxFailurePayload`
- 已新增 `SandboxAuditEventPayload`
- 已新增 `LocalSandboxDispatcher`
- 已把 baseline / regression 两轮的 deployment 与 attack execution 接到 dispatcher
- 已把 dispatcher 的失败分类与审批轨迹沉淀到返回体

这一步的意义是：

- 先把审批边界从 runtime 中抽出来
- 让预算、白名单、签名进入稳定对象层
- 为未来失败分类、容器 executor、远程 execution plane 预留扩展点

当前仍未完成的，是：

- 更细粒度失败分类
- 更完整的跨模块 task signing / audit trail
- 多 executor 路由
- 容器级或远程执行平面

## 2026-03-26 实现进展补记：Projection-Only Main Path

当前后半段 4 个节点已经不再只是“额外吐一个 projection 给前端看”，而是开始按 projection 主通道执行：

- `attack_planning_agent`
- `vulnerability_agent`
- `patch_agent`
- `reflection_agent`

当前实现策略是：

- projection builder 先产出输入窗口
- handoff 先显式落地
- 节点逻辑优先从 projection 中恢复结构化输入
- 旧 state 仅作兼容回退

这一步意味着：

- 项目已经跨过“projection 只是调试对象”的阶段
- 后续可以沿同一模式继续收口 `generation / audit`

当前仍未完成的，是：

- 前半段节点的 projection-only 彻底收口
- 移除旧 state 回退
- 更完整的 handoff policy、artifact summarizer 与 typed reflection memory

## 2026-03-27 真实 LLM Attack Agent 分层收口

如果当前目标明确升级为“攻击 agent 具备真实 LLM 决策能力”，后端执行架构应进一步收口为下面两层，而不是继续把攻击规划和攻击执行混写在同一个节点里。

### 1. Cognitive Plane

- `Attack Planning LLM Agent`
  - 只消费 `attack_planning_projection`
  - 读取的内容应限制为：
    - `TargetServiceSpec`
    - `AuditFinding / Finding Card`
    - 最近一轮 `Patch Card`
    - 预算、白名单、停止条件等约束
  - 只输出结构化对象：
    - `AttackSpecPayload`
    - `AttackDecisionCard`
    - 后续可扩展 `AttackLoopDirective`

### 2. Execution Plane

- `Sandbox Dispatcher`
  - 负责 schema 校验、预算校验、白名单校验、签名、失败分类
- `Attack Executor / LocalSandboxRuntime`
  - 负责真正部署与执行
- `Result Aggregator / Artifact Summarizer`
  - 负责把 trace、metrics、finding 压缩为下游 agent 可消费的摘要

这里必须保持一个硬约束：

- LLM 负责“计划与判断”
- dispatcher / runtime 负责“批准与执行”
- 不让 LLM 直接输出 shell、docker、远程执行命令

### 3. 最小落地顺序

1. 先把 `_build_attack_specs(...)` 替换为真实 `AttackPlanningLLMAgent`
2. 让攻击 agent 输出 `AttackSpecPayload + AttackDecisionCard`
3. 再补“基于 `AttackResultPayload` 的二次规划”
4. 最后引入 `artifact summarizer`，稳定大工件进入下一轮 agent 窗口的方式

### 4. 验收边界

- 当前可以对外说“真实 LLM 攻击决策已接入”
  - 前提是攻击族选择、预算策略、停止条件已由 LLM 决定
- 当前仍不应对外说“生产级攻击执行平面已完成”
  - 因为容器级隔离、远程执行和生产补丁验证仍未完成
## 2026-03-27 落地状态补记

本轮代码已经把“真实 LLM Attack Agent 分层收口”的第一步正式落地：

- 已落地：
  - `AttackPlanningAgent`
  - `AttackDecisionPayload`
  - `attack_executor` 中“projection -> planner -> dispatcher -> runtime”的执行顺序
  - `delivery.attack_loop.attack_decision`
- 仍未落地：
  - 基于攻击结果的二次重规划
  - artifact summarizer system module
  - 远程或容器级 execution plane

这意味着当前后端架构已经具备：

- LLM 决策层和执行平面的显式边界
- 独立上下文窗口到结构化 handoff 的最小闭环
- 不依赖真实 LLM 可用性的安全 fallback

## 2026-03-27 回归重规划架构补记

当前补丁回归轮已进入同一套“认知层 -> 执行平面”分层：

- 认知层：
  - `AttackPlanningAgent` 基于 `attack-plan-r2` projection 输出 `regression_attack_decision + regression_attack_specs`
- 执行平面：
  - `LocalSandboxDispatcher`
  - `LocalSandboxRuntime`

这意味着当前后端已经不是“首轮 LLM，第二轮规则化”的混合口径，而是：

- 首轮基线攻击规划：LLM
- 补丁回归攻击重规划：LLM
- 实际攻击执行：dispatcher + runtime
## 2026-03-27 漏洞评估层分层补记

当前后端执行架构已经把攻击闭环进一步拆成三层：

- 认知决策层
  - `AttackPlanningAgent`
  - `VulnerabilityEvaluationAgent`
- 治理执行层
  - `LocalSandboxDispatcher`
- 受限执行层
  - `LocalSandboxRuntime`

当前 `VulnerabilityEvaluationAgent` 的职责是：

- 消费独立 `ContextProjectionPayload`
- 输出稳定 `VulnerabilityVerdictPayload`
- 在 baseline 与 regression 两条路径中复用同一套结构化评估逻辑

这意味着当前架构已具备：

- LLM 负责“规划与裁决”
- dispatcher / runtime 负责“批准与执行”
- vulnerability verdict 不再主要依赖散落在 graph 中的规则函数

仍未完成的部分：

- `Expert Gate` 的更完整多分支路由
- `Patch Agent` 的更深执行层 LLM 化
- `artifact summarizer` system module
- 容器级隔离、远程执行平面与生产级补丁验证

## 2026-04-05 Expert Gate 分层补记

当前后端执行架构已经把 `vulnerability_verdict -> patch_spec` 之间的收口再拆成一层独立 cognition layer：

- 认知决策层
  - `VulnerabilityEvaluationAgent`
  - `ExpertGateAgent`
  - `PatchPlanningAgent`
- 治理执行层
  - `LocalSandboxDispatcher`
- 受限执行层
  - `LocalSandboxRuntime`

当前 `ExpertGateAgent` 的职责是：

- 消费独立 `expert_gate_projection`
- 读取漏洞裁决、攻击摘要、审计整改建议
- 输出稳定 `ExpertGateDecisionPayload`
- 为 `PatchPlanningAgent` 提供最小必要的放行 / 修补 / 后续动作信息

当前 `ExpertGateDecisionPayload` 已额外固定 typed route 第一版字段：

- `decision_family / decision_family_label`
- `route_target / route_target_label`

当前 `PatchPlanningAgent` 已开始消费上述 typed route 字段，用来约束 patch window 的规划语义，而不只依赖 `action / rationale`。

这意味着当前架构已进一步形成：

- 漏洞裁决不直接驱动 patch
- 先有独立 expert gate 认知层做中间判断
- patch 规划开始显式消费上游专家闸门结果
- 当 `route_target = "delivery"` 时，执行架构会直接转入 reflection follow-up，而不再误触发 patch dispatcher / regression replay
- 当 `route_target = "attack_planning_agent"` 时，执行架构会在同轮追加一次 `retry attack planning -> retry attack dispatch -> retry vulnerability evaluation -> reflection follow-up`

当前边界仍需保持诚实：

- 已完成“独立 Expert Gate 认知层与 typed route 第一版”
- 已完成“`attack_planning_agent` same-run 单次补充攻击闭环”
- 尚未完成“完整多分支 expert 子图”“递归多轮 same-run 自动重试”和“生产级发布闸门”

## 2026-03-27 Patch Diff 摘要执行面补记

- `artifact_summarizer` 第二阶段首版已把补丁工件比较纳入 execution plane 的压缩治理。
- 当前 `patch_reflection -> reflection_agent` 之间传递的不再只是 `changed_artifacts` 文本，还包括 `changed_artifact_summaries`。
- 这意味着运行时现在会在 baseline / patched workspace 之间生成轻量 diff 统计，再把结果投影到 `reflection` 独立窗口。
- 当前这一层的职责是“压缩与投影”，不是“构建完整 patch 发布记录”；构建日志、回滚计划、制品签名仍属于后续 execution plane 加固项。

## 2026-03-27 Reflection Cognition Layer 补记

- 后端执行面当前已形成：
  - `AttackPlanningAgent` 负责攻击规划
  - `VulnerabilityEvaluationAgent` 负责漏洞裁决
  - `ExpertGateAgent` 负责漏洞裁决之后的独立专家闸门判断
  - `PatchPlanningAgent` 负责修补规划
- `ReflectionAgent` 负责闭环反思与下一轮提示词优化
- 这意味着 `patch_reflection` 现在不只是“补丁重部署 + 回归攻击 + 卡片拼装”，而是“补丁重部署 + 回归攻击 + 独立反思 agent 输出”。
- 当前 `ReflectionAgent` 仍属于 cognition layer，不直接执行补丁、不直接改写 same-run 的 generation / audit prompt，而是先把策略建议稳定沉淀到 delivery、case memory 与 next-run handoff 对象中。

## 2026-03-27 项目级反思回灌补充说明

- 当前执行架构里，`ReflectionAgent` 的输出已经不再只停留在 `delivery.attack_loop.reflection_cards`。
- 最新反思结果会进一步进入：
  - `case_memory.recent_reflections`
  - `delivery.case_memory_summary.reflection_count`
  - 下一次同 `case_id` 运行时的 `generation / audit` projection
- 从 2026-03-29 起，前半段运行时已开始真实消费这些回灌：
  - `generation` 会把 reflection memory 用于候选排序与 `design_rationale`
  - `audit` 会把 reflection memory 用于 `reasons / key_findings / recommended_changes`
- 同时，前半段 projection 已开始承担运行时输入恢复职责：
  - `generation_runtime_input` 用于恢复结构化需求与解析置信度
  - `audit_runtime_input` 用于恢复候选方案原始结构与审计约束
  - `audit_runtime_input.scheme_entries` 用于稳定恢复 `proposal_id + scheme`，避免只靠列表顺序推断方案身份
- `architect_node` 现已优先通过 `analyst + generation_runtime_input` 恢复 requirement，不再把 `state["parsed"]` 当作主输入。
- 这说明当前后端已经形成：
  - `cognition output -> project memory -> next-run projection replay`
- 当前边界也必须讲清楚：
  - 已完成的是跨 run 的 project-level replay、generation / audit 的第一版执行层消费，以及 `audit` 最终裁决的独立 LLM 化
  - 尚未完成的是 same-run prompt rewrite 与更细粒度 typed reflection memory

## 2026-03-27 Target Service Template 接线补充说明

- 当前执行架构里，`target service template runtime` 已不再只停留在设计文档。
- `build_mock_crypto_http_target_service(...)` 现已成为默认模板构造入口，负责生成：
  - `template_id / template_label`
  - `service_kind / attack_surface_kind`
  - `supported_versions`
  - `planner_skill_hints / planner_retrieval_hints`
  - `deployment_manifest / runtime_profile`
- `attack_planning_projection` 当前会把这批模板信息作为 `target_service` artifact metadata 传给 `AttackPlanningAgent`。
- `AttackPlanningAgent` 当前进一步把它收口为 `planner_knowledge`，作为：
  - template 级策略知识入口
  - 后续 retrieval / evidence layer 的稳定挂点
- 当前边界必须继续保持诚实：
  - 已完成的是模板级 hints 接线
  - 尚未完成的是 retrieval service 对 planner hints 的主链召回与重排

## 2026-03-27 攻击规划检索接线补充说明

- 当前执行架构里，`AttackPlanningAgent` 已不再只消费：
  - 模板对象
  - attack plan input
  - case memory
- 现在还会额外消费 planner-scoped retrieval evidence。
- 当前执行面上的顺序是：
  1. retrieval service 生成 planner-scoped evidence
  2. `attack_planning_projection` 挂载 `evidence_refs`
  3. 同步追加 `attack_planner_evidence` card
  4. `AttackPlanningAgent` 在独立窗口内消费
- 当前回退边界也已固化：
  - 专用攻击规划检索优先
  - 若无命中，再退回 broader retrieval
  - 最后退回当前 run 全局 evidence

## 2026-03-29 Patch Execution 执行面补充说明

- 当前后端执行架构里，`Patch Agent` 已形成三层分工：
  - 认知规划层：`PatchPlanningAgent`
  - 演示级执行层：`LocalSandboxDispatcher -> LocalSandboxRuntime`
  - 报告收口层：`_build_patch_execution_report(...)`
- 这意味着 `patch_reflection` 当前不再只是“patched redeploy + regression probe”，而是会把执行过程沉淀成可被下游 agent 消费的结构化报告。

当前 `patch_execution` 的来源组成是：

1. `patch_spec` 中的实现说明、验证步骤、回滚约束
2. patched deployment 返回的目标版本、workspace 与 deployment dispatch
3. regression attack 返回的 dispatch、结果摘要与跳过状态
4. `artifact_summarizer` 生成的 `changed_artifact_summaries / diff_preview`

当前执行面上的定位应写成：

- dispatcher / runtime 负责“部署与验证动作”
- patch execution report 负责“收口这些动作的结构化结果”
- reflection layer 负责“消费执行报告并形成下一轮优化建议”

当前仍未完成的部分：

- 更深的语义修补验证
- 多文件 patch、构建日志、失败工件与回滚工件的统一 artifact pipeline
- 容器级隔离与远程执行平面

## 2026-03-29 Patch Validation 与 Artifact Pipeline 第二阶段

- 当前执行架构里，`patch_execution` 已不再只是一个“补丁已应用/已验证”的薄结果。
- `validation_results` 现在会进一步区分：
  - 部署重部署验证
  - 回归攻击验证
  - 工件差异收口
  - 残余风险复核
- 这意味着执行面向上层暴露的不再只是状态字符串，而是 typed validation evidence。

- 同时，`artifact_summarizer` 当前也开始把 supporting artifacts 一并压缩：
  - `service_manifest.json`
  - `runtime_info.json`
  - `service_stdout.log`
  - `service_runtime.py`
- 这样做的目的，是让 `Patch Agent / Reflection Agent / Evaluation Agent` 在独立窗口里能看到更稳定的执行上下文，而不是只看到少量 diff 行。

## 2026-03-29 后端完整架构补齐 V2

当前需要把“后端继续补细节”与“后端架构已经补齐”明确区分开。

从当前阶段开始，后端主线不应再优先描述为：

- 继续补某个 agent 的局部字段
- 继续补某类 artifact 的展示细节
- 继续补某个单点报告对象

而应统一收口为四个平面：

### A. Agent Control Plane

这一层负责：

- 定义 LangGraph 中哪些节点是真正的 agent invocation
- 定义每个 agent 的进入条件、退出条件、失败分支、重试与终止条件
- 把 “generation / audit / attack / evaluation / patch / reflection” 的认知职责与工程模块职责彻底分开

当前推荐稳定对象：

- `AgentSession`
- `AgentInvocationSpec`
- `AgentResultEnvelope`
- `WorkflowCheckpoint`

当前目标不是把这层写成新框架，而是让 `langgraph_mas.py` 中的节点职责不再混杂“认知决策 + 运行态拼装 + 执行控制”。

### B. Context And Memory Bus

这一层是当前后端最硬的架构工作，不是优化项。

它负责：

- 保证每个 agent 使用独立上下文窗口
- 保证 agent 之间只通过结构化对象传递信息，而不是共享长 prompt
- 区分 run 内临时状态、case 级长期记忆、artifact 级回查对象、evidence 级引用对象

当前推荐稳定对象：

- `ContextProjectionPayload`
- `MemoryHandoffPayload`
- `MemoryCardPayload`
- `ArtifactRefPayload`
- `EvidenceRefPayload`
- 后续应继续补的 typed memory families：
  - `Decision Card`
  - `Finding Card`
  - `Patch Card`
  - `Reflection Card`
  - `Replay Snapshot Card`

这一层的第一优先级不是“再压薄一点 JSON”，而是让 memory bus 足够稳定、可压缩、可回查、可扩展。

### C. Sandbox Execution Plane

这一层负责：

- `target_deploy`
- `attack_execute`
- `evaluate`
- `patch_apply`
- `rollback`
- `regression_replay`

注意这里的重点不是立刻把所有动作都做成真实容器执行，而是先把执行协议收口稳定，使本地 runtime、容器 runtime、远程 executor 未来可以替换。

当前推荐稳定对象：

- `ExecutionPlan`
- `ExecutionStage`
- `ExecutionRun`
- `ExecutionArtifactBundle`
- `ExecutionFailure`
- `ExecutionTelemetry`

当前 `LocalSandboxDispatcher -> LocalSandboxRuntime` 只是这一层的第一版本地实现，不应再被描述成完整 execution plane。

### D. Persistence Audit Replay Plane

这一层是当前后端最容易被低估、但对企业交付最关键的一层。

它负责：

- 持久化每一轮 agent 决策
- 持久化每一次 dispatch / execution / verdict / patch / reflection 事件
- 记录预算消耗、失败原因、artifact 清单、版本关系
- 支持 case 级 replay、审计追踪、交付回放

当前推荐稳定对象：

- `CaseTimeline`
- `ExecutionEvent`
- `VersionLineage`
- `ReplaySnapshot`
- `AuditTrailEnvelope`

没有这一层，系统就很难从“能跑 demo”升级成“可答辩、可交付、可追责”的企业后端。

## 2026-03-29 四平面的最小职责边界

为了避免后续再次把责任写混，建议固定如下口径：

1. `Agent Control Plane`
- 决定谁在何时被调用
- 决定进入哪条控制流
- 不直接执行攻击、不直接执行补丁应用

2. `Context And Memory Bus`
- 决定 agent 看到什么
- 决定哪些信息被压缩、保留、回查
- 不直接决定执行批准

3. `Sandbox Execution Plane`
- 决定如何在受控域中执行部署、攻击、补丁与回归
- 不负责认知层提示词策略

4. `Persistence Audit Replay Plane`
- 决定哪些事件被保留、如何追踪、如何回放
- 不直接替代运行态 state

## 2026-03-29 架构优先级重排

从当前开始，后端优先级建议固定为：

1. `Agent Control Plane` 收口
2. `Context And Memory Bus` 收口
3. `Sandbox Execution Plane` 抽象收口
4. `Persistence Audit Replay Plane` 补齐
5. 在以上四层稳定后，再继续深化 patch validation、artifact pipeline、前端透明化专题视图

也就是说，像 `patch_execution` 这类对象的细节增强仍然有价值，但它们不再是当前第一优先级，只能服务于这四层主线。

这里需要额外强调一条推进原则：

- 这四条都需要做
- 差别只在推进顺序，不在是否属于主线
- 任何单条主线的提前完成，都不能替代其它三条

因此当前“推荐主线”不是：

- 从四条里选一条做

而是：

- 按优先级顺序，把四条都推到稳定完成态

## 2026-03-29 下一阶段推荐落地顺序

如果后续开始写代码，建议按这个顺序推进：

1. 先把 `langgraph_mas.py` 中的控制流对象化
2. 再把 `projection + handoff + replay snapshot` 的 bus 抽象提出来
3. 再把 `dispatcher / runtime / patch apply / rollback / replay` 收口为统一 execution contract
4. 最后再做 timeline / replay / audit persistence

## 2026-03-29 第一批骨架落地说明

当前四平面的第一批代码骨架已经进入主链，但它们的定位必须严格写清楚。

### A. Control Plane

已落地：

- `ControlPlaneBuilder`
- `WorkflowCheckpoint`
- `AgentInvocationSpec`
- `AgentResultEnvelope`
- `AgentSession`

当前作用：

- 把 `workflow_trace`、projection、handoff 汇总成 agent/session 级摘要
- 作为 `delivery.backend_architecture.control_plane` 的来源

本轮新增的第一版运行时合同字段包括：

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

这意味着 control plane 现在开始表达“阶段合同”，而不只是“阶段存在”。

### B. Context And Memory Bus

已落地：

- `ContextBusBuilder`
- `ContextWindowSpec`
- `MemoryHandoffSummary`
- `ReplaySnapshotCard`
- `ContextBusSummary`

当前作用：

- 汇总独立窗口数量、card 类型、handoff 数量
- 作为 `delivery.backend_architecture.memory_bus` 的来源

本轮新增：

- `windows[*].window_ref / card_family_counts / dominant_card_family / lineage_refs`
- `handoffs[*].projection_ref / card_family_counts / dominant_card_family / lineage_refs`
- `typed_families[*]`
- `windows[*].typed_contract_counts / dominant_typed_contract / artifact_lookup_refs / evidence_lookup_refs`
- `handoffs[*].typed_contract_counts / dominant_typed_contract / artifact_lookup_refs / evidence_lookup_refs`
- `typed_contracts[*]`
- `replay_snapshot_card.typed_family_counts / typed_contract_counts / artifact_ref_count / evidence_ref_count / lineage_refs`
- `replay_snapshot_card.artifact_lookup_refs / evidence_lookup_refs`
- `replay_snapshot.metadata.window_catalog[*].window_ref / dominant_typed_contract / artifact_lookup_refs / evidence_lookup_refs`
- `replay_snapshot.metadata.handoff_catalog[*].projection_ref / from_agent / to_agent / dominant_typed_contract / artifact_lookup_refs / evidence_lookup_refs`

这意味着 Context Bus 当前已开始显式表达：

- 每个独立窗口内部主要承载哪类 typed memory
- handoff 到底把哪类 card 传给了下游
- replay 时如何通过 family / contract / ref / lineage 回看这轮记忆传递
- timeline drill-down 如何在不重放整轮 memory bus 的前提下恢复窗口链路与 handoff 链路

同时，`langgraph_mas.py` 当前已让 `generation_runtime_input / audit_runtime_input` cards 稳定带出：

- `payload.typed_contract`
- `payload.typed_contract_ref`
- `payload.ref_lookup_hint`

这一步的意义不是再堆一层展示字段，而是让前半段 `generation / audit` 的运行时恢复逻辑开始真正按 typed contract 收口，减少对旧 graph state 隐式字段的依赖。

### C. Execution Plane

已落地：

- `ExecutionPlaneBuilder`
- `ExecutionPlan`
- `ExecutionStage`
- `ExecutionArtifactBundle`
- `ExecutionFailure`
- `ExecutionTelemetry`
- `ExecutionRun`

当前作用：

- 把 dispatcher/runtime/patch execution 结果收口为统一执行摘要
- 作为 `delivery.backend_architecture.execution_plane` 的来源

### D. Replay Plane

已落地：

- `CaseTimelineService`
- `ExecutionEvent`
- `VersionLineage`
- `ReplaySnapshot`
- `CaseTimeline`

当前作用：

- 在 `delivery` 收口后把 run 级快照写入 `.cache/case_timelines/`
- 作为 `delivery.backend_architecture.replay_plane` 的来源

本轮新增：

- `latest_snapshot.projection_refs`
- `latest_snapshot.handoff_refs`
- `latest_snapshot.typed_family_counts`
- `latest_snapshot.typed_contract_counts`
- `latest_snapshot.artifact_lookup_refs / evidence_lookup_refs`
- `timeline_summary.latest_projection_ref_count`
- `timeline_summary.latest_handoff_ref_count`
- `timeline_summary.latest_typed_family_count`
- `timeline_summary.latest_typed_contract_count`
- `memory_bus_snapshot` timeline event
- `typed_card_contract` timeline event
- `attack_decision` timeline event
- `vulnerability_verdict` timeline event
- `patch_plan` timeline event
- `patch_execution` timeline event
- `reflection_output` timeline event

当前新增事件的目的不是“把所有运行细节都写进时间线”，而是先把 replay 中最关键的认知里程碑稳定沉淀下来：

- 攻击层为什么执行、交接或停止
- 漏洞评估层给出了什么裁决
- 修补层提出了什么补丁策略
- 回归后补丁执行处于什么状态
- 反思层沉淀了哪些下轮可消费的结论

### 当前边界

当前这些都是“第一批可运行骨架 + 摘要接线”：

- 可以用于联调、文档对齐、前端透明化和回放起点
- 不能被写成完整生产级控制平面、执行中心或审计回放平台

## 10.19 后端完成态判定（2026-03-30）

当前需要给“后端什么时候算完成”一个统一判断口径，避免团队内部把“某条线骨架已接线”误判成“后端已完成”。

推荐完成态判定如下：

### A. Agent Control Plane 完成态

- 主要阶段具备稳定 invocation / checkpoint / result / failure / termination contract
- 关键跳转不再依赖隐式 state 推断

### B. Context And Memory Bus 完成态

- 前后半段都以 projection-only 为主通道
- agent 间以 typed cards + refs 为主，而不是共享长上下文
- ref 回查和 lineage 关系足够稳定

### C. Sandbox Execution Plane 完成态

- `deploy / attack / patch / rollback / regression replay` 具备统一执行协议
- dispatcher / runtime / artifact pipeline 边界清晰

### D. Persistence Audit Replay Plane 完成态

- timeline / event / lineage / snapshot 系统化落盘
- replay 具备稳定事件查询与回查入口

在以上四条都没有收口前，当前项目都只能写成：

- 后端完整架构第一批骨架已落地
- 后端主线已打通
- 完整后端架构仍在补齐中

## 10.20 后端主线 P0 落地拆分（2026-03-30）

为了避免“方向清楚但开工粒度过粗”，当前四条后端主线建议继续拆到可直接开工的 P0 级任务。

### P0-1 Agent Control Plane

目标：

- 把主要阶段的 invocation / checkpoint / result / failure / termination contract 做硬

当前重点：

- 扩展 `ControlPlaneBuilder`
- 继续让 `langgraph_mas.py` 把关键控制跳转对象化
- 不再只依赖 `workflow_trace` 表示“阶段走过了”

重点文件：

- `src/cipher_genius/core/control_plane.py`
- `src/cipher_genius/core/langgraph_mas.py`
- `tests/unit/test_control_plane_builder.py`
- `tests/integration/test_langgraph_mas.py`

### P0-2 Context And Memory Bus

目标：

- 让前后半段都以 projection-only + typed cards + refs 为主通道

当前重点：

- 继续推进 `generation / audit` 的 projection-only 收口
- 把 `Decision / Finding / Patch / Reflection / Replay Snapshot` 继续推进为更稳的 typed cards / typed contracts
- 加强 artifact / evidence ref 回查策略
- 让前半段 runtime input 优先按 typed contract + runtime stage 恢复，而不是只靠裸 `card_type`

重点文件：

- `src/cipher_genius/core/context_bus.py`
- `src/cipher_genius/core/langgraph_mas.py`
- `src/cipher_genius/api/schemas.py`
- `tests/unit/test_context_bus_builder.py`
- `tests/unit/test_langgraph_projection_runtime_inputs.py`

### P0-3 Sandbox Execution Plane

目标：

- 把 `deploy / attack / patch / rollback / regression replay` 收口成统一 execution contract

当前重点：

- 继续清晰化 dispatcher / runtime / artifact pipeline 的边界
- 让 patch execution、rollback、regression replay 不再只是零散结果对象
- 为后续容器 executor / 远程执行保留稳定接口
- 本轮已完成：
  - `execution_plane.summary.contract_version = "v1"`
  - `execution_plane.summary.operation_count`
  - `execution_plane.summary.operation_kind_counts`
  - `execution_plane.plan.operation_kinds`
  - `execution_plane.operations[*]`
- `operations[*]` 当前会统一表达：
  - `deploy`
  - `attack`
  - `patch_apply`
  - `rollback`
  - `regression_replay`
- 每个 operation 还会显式带出：
  - `depends_on`
  - `input_refs`
  - `output_refs`
  - `replay_refs`
  - `governance_mode`

重点文件：

- `src/cipher_genius/sandbox/execution_plane.py`
- `src/cipher_genius/sandbox/dispatcher.py`
- `src/cipher_genius/core/langgraph_mas.py`
- `tests/unit/test_sandbox_dispatcher.py`
- `tests/unit/test_patch_execution_report.py`
- `tests/unit/test_execution_plane_builder.py`

### P0-4 Persistence Audit Replay Plane

目标：

- 让 timeline / event / lineage / snapshot 形成系统化 replay 面

当前重点：

- 继续扩展 timeline event 体系
- 补 version lineage 与 replay ref 回查索引
- 让 projection / handoff / artifact refs 的 replay 回看更系统

重点文件：

- `src/cipher_genius/memory/replay_service.py`
- `src/cipher_genius/core/langgraph_mas.py`
- `tests/unit/test_case_timeline_service.py`
- `tests/api/test_api_mas.py`

### 当前执行原则

- 这四个 P0 都属于后端完成态的必做项
- 可以按顺序推进
- 不能只做其中两项就把后端写成“已完成”

## 2026-03-30 Replay 查询入口补记

`P0-4 Persistence Audit Replay Plane` 当前又向前推进了一步：

- `CaseTimelineService` 新增：
  - `get_timeline_summary(case_id)`
  - `query_events(...)`
  - `query_snapshots(...)`
  - `query_version_lineage(...)`
  - `get_timeline_drilldown(...)`
- FastAPI 新增：
  - `GET /api/v1/cases/{case_id}/timeline`
  - `GET /api/v1/cases/{case_id}/timeline/events`
  - `GET /api/v1/cases/{case_id}/timeline/snapshots`
  - `GET /api/v1/cases/{case_id}/timeline/drilldown`
  - `GET /api/v1/cases/{case_id}/timeline/lineage`

这一步的设计目的不是把 replay plane 直接做成“大而全的中心”，而是先把下面三件事收口稳定：

- 单 case 的 timeline overview
- 按 `typed_contract / lineage / lookup refs` 做轻量回看
- 按 `target_service_ref / patch_id / baseline_version / patched_version` 做轻量 version lineage 回看
- 按 `projection_ref / handoff_ref / run_id` 做单 case replay drill-down
- 把单个 scope 下的 snapshots / events / lineage 聚合成前端和联调可直接消费的本地视图
- 把 `projection_relationships / handoff_relationships` 聚合出来，服务多 agent 透明流程图与 handoff 深钻
- `handoff_relationships` 现会进一步带出上下游 agent/stage、handoff projection 与 dominant typed contract
- 把 `service_trajectories` 聚合出来，服务目标服务的攻击、评估、修补与回归轨迹视图
- 为前端透明化和后续 drill-down 留出稳定 API 入口

当前仍未跨过的边界也要继续讲清楚：

- 还没有跨 case 的统一 replay 检索
- 还没有完整事件化审计湖
- 还没有生产级 replay center
## 10.21 Patch Apply / Rollback Real Dispatch（2026-04-01）

## 10.22 Patch / Rollback Contract Hardening（2026-04-02）

本轮不是继续加展示字段，而是继续收口 `dispatcher -> runtime -> patch_execution -> execution_plane` 之间的统一执行合同。

当前新增的稳定合同字段：

- `SandboxDispatchRequestPayload.operation_kind`
- `SandboxDispatchRequestPayload.executor_kind`
- `SandboxDispatchRequestPayload.executor_contract_version`
- `SandboxDispatchRequestPayload.required_capabilities`
- `SandboxDispatchResultPayload.operation_kind`
- `SandboxDispatchResultPayload.executor_kind`
- `SandboxDispatchResultPayload.executor_contract_version`
- `SandboxDispatchResultPayload.capability_flags`
- `SandboxDispatchResultPayload.artifact_refs`
- `SandboxFailurePayload.scope`
- `SandboxFailurePayload.scope_label`
- `PatchExecutionPayload.execution_contract_version`
- `PatchExecutionPayload.patch_artifact_refs`
- `PatchExecutionPayload.rollback_artifact_refs`
- `PatchExecutionPayload.regression_artifact_refs`

本轮新增的执行面能力是：

- `execution_plane.plan.executor_kinds`
- `execution_plane.plan.capability_flags`
- `execution_plane.summary.executor_kinds`
- `execution_plane.summary.capability_flag_count`

本轮新增的请求级失败分类是：

- `patch_artifact_count_missing`
- `rollback_notes_missing`

本轮同时新增了运行时失败合同：

- dispatcher 审批通过后，如果 local runtime 执行抛错，不再只保留 Python 异常
- 当前会抛出 `SandboxDispatchExecutionError`
- 其中附带结构化 `dispatch_result`
- `dispatch_result.status = "failed"`
- `dispatch_result.failure_category = "runtime_execution_failed"`
- `dispatch_result.audit_trail[-1].event_kind = "failed"`

`Sandbox Execution Plane` 本轮继续从“统一合同”推进到“真实 dispatcher/runtime 边界”。

当前已经落地的最小闭环是：

- `dispatch_patch_application(...)`
- `apply_patch_to_service(...)`
- `dispatch_rollback(...)`
- `materialize_rollback_plan(...)`
- `regression_deploy`
- `regression_attack`

因此，当前应固定这样理解几类对象：

- `patch_spec`
  - 认知层输出的修补计划
- `patch_apply dispatch`
  - 执行治理层批准并执行补丁工作区物化
- `rollback_plan dispatch`
  - 执行治理层批准并落盘回滚预案
- `patch_execution`
  - 汇总 patch_apply / rollback / regression deploy / regression attack 之后的结构化执行报告

当前新增的本地工件包括：

- `patch_manifest.json`
- `patch_metadata.json`
- `rollback_plan.json`
- `rollback_manifest.json`

当前新增的稳定接口契约包括：

- `delivery.sandbox_dispatcher.patch_apply`
- `delivery.sandbox_dispatcher.rollback_plan`
- `delivery.attack_loop.patch_execution.patch_dispatch_id`
- `delivery.attack_loop.patch_execution.rollback_dispatch_id`

`execution_plane.operations[*]` 本轮的关键变化是：

- `patch_apply` 不再只依赖 `patch_execution` 推导
- `rollback` 不再只是 `rollback_notes` 的 synthetic 占位
- 两者都优先消费真实 dispatcher 结果
- `governance_mode` 当前统一落为 `dispatcher`

当前仍未完成的部分必须继续诚实说明：

- 不是容器级隔离 patch executor
- 不是远程服务器补丁发布系统
- 不是生产级自动回滚平台
## 10.23 Executor Backend Matrix（2026-04-02）

本轮继续收口 `Sandbox Execution Plane`，但重点已经从 “patch/rollback 是否有真实 dispatch” 推进到 “不同 executor backend 的升级路径是否有稳定合同”。

### 10.23.1 为什么现在要先做 matrix

- 当前项目已经有真实的 `local_process` 主链。
- 下一阶段一定会面对：
  - 容器隔离
  - 远程 worker
  - artifact 同步
  - execution receipt / handoff trace
- 如果没有先把 matrix 固定下来，后续很容易把这些能力重新塞回 `langgraph_mas.py` 或 prompt 层，破坏当前已收口的 dispatcher/runtime 边界。

### 10.23.2 当前 matrix 的最小稳定对象

当前已新增 `src/cipher_genius/sandbox/executor_matrix.py`，把 executor backend matrix 固定为三类：

1. `local_process`
2. `container`
3. `remote_worker`

每类 executor 当前至少统一表达：

- `executor_kind`
- `executor_backend`
- `executor_label`
- `executor_readiness`
- `routing_mode`
- `supports_direct_execution`
- `handoff_required`
- `handoff_contract_version`
- `handoff_fields`
- `supported_operation_kinds`
- `capability_flags`

### 10.23.3 当前真实能力与诚实边界

- 当前真正可直接执行的只有：
  - `local_process`
- `container / remote_worker` 当前是：
  - 合同化占位
  - 可视化与 replay 可消费对象
  - 后续架构扩展入口
- `container / remote_worker` 当前还不是：
  - 已完成容器隔离
  - 已完成远程作业分发
  - 已完成多节点执行回执中心

### 10.23.4 Dispatcher 当前如何消费 matrix

`LocalSandboxDispatcher` 现已按 matrix 做最小治理：

1. 校验 executor 类型是否存在
2. 校验 executor 是否支持当前 `operation_kind`
3. 校验 executor 是否覆盖 `required_capabilities`
4. 对必须走交接的 executor 返回结构化 handoff-required 结果

当前新增的 executor 失败分类：

- `executor_kind_unknown:*`
- `executor_operation_not_supported:*`
- `executor_capability_missing:*`
- `executor_handoff_required:*`

### 10.23.5 Execution Plane 当前新增口径

`execution_plane.plan` 现已显式带出：

- `executor_backends`
- `executor_kinds`
- `active_executor_kinds`
- `planned_executor_kinds`
- `executor_matrix`

`execution_plane.summary` 现已显式带出：

- `executor_backends`
- `active_executor_kind_count`
- `planned_executor_kind_count`
- `executor_matrix_count`

这意味着前端、replay plane、答辩展示层现在可以稳定表达：

- 本轮实际用了哪些 executor
- 当前系统还有哪些 planned executor
- planned executor 未来接入时需要哪些 handoff 字段

### 10.23.6 下一步最合理的收口顺序

在 executor backend matrix 落地后，后续更建议按下面顺序继续推进：

1. 把 `patch_artifact_refs / rollback_artifact_refs / regression_artifact_refs` 写进 replay/timeline 更清晰的事件体系
2. 把 `failed dispatch` 纳入 replay plane 的显式回查对象
3. 再推进 `container / remote_worker` 的真实 handoff adapter，而不是直接跳去做执行器实现

## 10.23.7 2026-04-03 Replay Plane 显式回查增强

本轮执行面的重点，是把 `failed dispatch` 与 `patch / rollback / regression` 工件引用，从 execution 摘要继续推进到 replay 自身的稳定回查对象。

当前已落地：

- `ReplaySnapshot` 显式沉淀：
  - `dispatch_refs`
  - `failed_dispatch_refs`
- `timeline_summary` 显式沉淀：
  - `latest_dispatch_ref_count`
  - `latest_failed_dispatch_ref_count`
- `ReplaySnapshot.metadata` 显式沉淀：
  - `dispatch_catalog`
  - `patch_execution_artifact_refs`
- `patch_execution` event 显式沉淀：
  - `patch_dispatch_id`
  - `rollback_dispatch_id`
  - `deployment_dispatch_id`
  - `regression_dispatch_id`
  - `patch_artifact_refs`
  - `rollback_artifact_refs`
  - `regression_artifact_refs`
- `timeline/events` 当前不再只按 run 粗放返回：
  - 优先返回直接命中 lookup ref 的事件
  - 再补同一 run 的上下文事件

这样做的目的不是增加展示字段，而是让 replay plane 自己具备三种稳定索引能力：

- 按 dispatch 回看
- 按失败 dispatch 回看
- 按 patch 相关 artifact ref 回看

当前边界：

- 已完成的是本地单 case replay / 审计可回查增强
- 未完成的是跨 case replay center、集中索引和生产级事件存储

## 10.23.8 2026-04-03 Typed Dispatch Summary

在 replay plane 已能显式记录 `dispatch_refs / failed_dispatch_refs` 之后，本轮继续把 dispatch 回查看板从自由 metadata 收口为稳定 typed summary。

当前新增：

- `ReplaySnapshot.dispatch_summaries`
- `ReplaySnapshot.failed_dispatch_summaries`
- `timeline_summary.latest_dispatch_summary_count`
- `timeline_summary.latest_failed_dispatch_summary_count`
- `drilldown.summary.dispatch_summaries`
- `drilldown.summary.failed_dispatch_summaries`

这样做的目的：

- 让前端和报告透明化层优先消费稳定 schema
- 让 replay / audit 逻辑不再长期依赖 `metadata.dispatch_catalog`
- 为后续 `container / remote_worker` handoff adapter 预留稳定 dispatch 摘要层

## 10.23.9 2026-04-03 Replay Executor Handoff Trace Summary

在 `dispatcher` 已能返回 typed handoff skeleton 之后，本轮继续把这条链往 `Persistence Audit Replay Plane` 推进一步。

当前已新增：

- `ReplayExecutorHandoffTraceSummary`
- `ReplaySnapshot.executor_handoff_trace_summaries`
- `timeline_summary.latest_executor_handoff_trace_count`
- `drilldown.summary.executor_handoff_trace_summaries`

设计取舍：

1. 不直接把完整 `handoff_receipt` 或 `artifact_sync_manifest` 原样塞进 replay snapshot metadata
2. 继续沿用“typed summary + ref”模式，为前端、答辩与后续 adapter 回写保留稳定接口
3. 显式区分 `memory handoff` 和 `executor handoff`，避免 timeline 语义混淆

当前这一步的价值在于：

- replay plane 已能稳定表达“为什么没有在本地执行，而是转交给非本地执行面”
- timeline/drilldown 已能直接展示 handoff trace 状态，而不必反解 dispatcher 原始嵌套字段
- 后续若补 execution plane 消费同一摘要，路径会更顺

但当前仍不能写成：

- 容器执行平面已经完成
- 远程 worker 回执中心已经完成
- replay 已具备完整 executor handoff 检索中心

## 10.23.10 2026-04-03 Container / Remote Worker Handoff Adapter 设计入口

当前 `executor matrix` 已经能表达：

- `handoff_required`
- `handoff_contract_version`
- `handoff_fields`
- `handoff_ref`

但这仍不足以支撑真实 `container / remote_worker` 接入。

本轮已把后续设计入口单独沉淀到：

- `docs/modules/executor_handoff_adapter.md`

当前推荐口径：

- `memory_handoff` 负责 agent 认知传递
- `executor_handoff` 负责执行平面交接
- `container / remote_worker` 的下一步不是先写执行器，而是先固定：
  - `ExecutorHandoffRequest`
  - `ExecutorArtifactSyncManifest`
  - `ExecutorHandoffReceipt`
  - `ExecutorHandoffTrace`

## 10.23.10 2026-04-03 Executor Handoff Skeleton 落地

在 handoff adapter 设计文档补齐之后，本轮继续把“typed contract”落到了 schema 与 dispatcher skeleton，而不是停留在说明层。

当前已落地：

- `src/cipher_genius/api/schemas.py`
  - `ExecutorHandoffRequestPayload`
  - `ExecutorArtifactSyncManifestPayload`
  - `ExecutorHandoffReceiptPayload`
  - `ExecutorHandoffTracePayload`
- `SandboxDispatchRequestPayload`
  - `governance_mode`
  - `artifact_refs`
  - `handoff_request`
  - `artifact_sync_manifest`
- `SandboxDispatchResultPayload`
  - `handoff_request`
  - `artifact_sync_manifest`
  - `handoff_receipt`
  - `handoff_trace`
- `LocalSandboxDispatcher`
  - 在 `container / remote_worker` 场景返回 typed handoff skeleton
  - 仍不会直接进入真实 container runtime 或 remote worker

这一步的目的：

1. 先把执行平面交接对象从散 `handoff_fields` 升级成稳定 typed contract
2. 让 execution plane、前端透明化和未来 replay trace 有统一输入对象
3. 保持 `local_process` 主链不受未落地执行器影响

当前边界必须继续保持诚实：

- 已落地的是 handoff contract skeleton
- 未落地的仍包括 container adapter、remote worker adapter、artifact sync 服务、receipt callback 服务
# 2026-04-05 Re-Gate 执行架构补记

- `patch_reflection` 当前在 execution/control plane 层已支持有限 re-gate 第一版。
- `retry_expert_gate_decision` 当前只在“未进入 patch flow”时作为 `patch_reflection` 的主输出引用。
- 一旦 same-run re-gate 后进入 patch flow，控制平面主输出会回到：
  - `delivery.attack_loop.patch_spec`
  - `patch_execution / regression_*` 相关执行结果
- 当前执行面边界保持不变：
  - 有限 same-run re-gate 已落地
  - 容器级隔离、远程 worker、无限重试 orchestration 尚未完成
