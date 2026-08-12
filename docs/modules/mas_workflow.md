# MAS 主流程与 LangGraph 编排设计

最后更新：2026-04-06
状态：active
适用范围：`src/cipher_genius/core/langgraph_mas.py`、`src/cipher_genius/core/mas_runtime_support.py`、`src/cipher_genius/api/mas_service.py`、`src/cipher_genius/api/schemas.py`、`frontend/src/features/mas/`

## 2026-04-06 Replay / Timeline Retry 回看补记

- 当前 same-run retry 子链不只停留在 `delivery.attack_loop` 与 `memory_bus.summary`：
  - `replay_plane.latest_snapshot.metadata` 也已显式保存 retry 压缩与恢复点合同
  - `timeline/drilldown.summary` 也已能聚合同一批 retry 字段
- 这让主流程现在可以从三层解释 retry：
  - 工作流层：`delivery.attack_loop.same_run_retry_summary`
  - 记忆层：`delivery.backend_architecture.memory_bus.summary.retry_*`
  - 回放层：`latest_snapshot.metadata.retry_*` 与 `timeline/drilldown.summary.retry_*`
- 当前正确口径：
  - 已完成“retry 子链可回看”
  - 尚未完成“retry 子链自动恢复执行”


## 2026-04-06 Same-Run Retry 预算状态补记

- 当前 `execute(...)` 已在 LangGraph 初始 state 中注入 `same_run_retry_budget`
- 当前预算来源顺序为：
  - 请求显式传入 `max_same_run_retries`
  - 否则回退到 `SAME_RUN_RETRY_BUDGET_DEFAULT`
- 当前 `patch_reflection -> retry follow-up -> second expert gate` 只支持第一步预算控制：
  - `budget = 0`：禁用 same-run retry
  - `budget = 1`：允许一次 retry follow-up
- 当前若 budget 已关闭但第一道 expert gate 仍请求 retry，`loop_status` 会落为：
  - `baseline_*_retry_blocked_by_budget`
- 当前 `delivery.attack_loop` 已把预算态暴露给前端与报告层：
  - `same_run_retry_summary`
  - `same_run_retry_budget`
  - `same_run_retry_used`
  - `same_run_retry_remaining`
- 当前 `same_run_retry_summary.attempt_trace` 已作为“多轮 retry 子图”的第一版轨迹合同：
  - 即使现在只支持一次 retry，也先把尝试轨迹做成可扩展数组
- 当前 retry 子链的独立窗口也已显式接入：
  - `context_projections.attack_planning_retry`
  - `context_projections.vulnerability_evaluation_retry`
- 当前 memory bus 摘要层也已开始按 retry 子链做聚合：
  - `summary.retry_window_count`
  - `summary.retry_handoff_count`
  - `summary.retry_projection_refs`
  - `summary.retry_handoff_refs`
  - `summary.retry_lineage_refs`
  - `summary.retry_typed_contract_refs`
- 当前 retry 子链窗口也已追加 `retry_context_summary` 卡，作为后续多轮压缩骨架
- 当前这张卡已经开始携带压缩策略接口：
  - `compression_policy`
  - `retained_refs`
  - `dropped_detail_hints`
  - `resume_checkpoint_ref`
  - `resume_inputs`
  - `resume_hint`
- 当前 control plane 也会同步暴露：
  - `summary.same_run_retry`
  - `patch_reflection` / `delivery` metadata 下的 `same_run_retry`
- 当前仍未完成：
  - `>1` 的递归多轮 expert 子图
  - 基于预算的多轮上下文压缩与轮次淘汰策略

## 1. 本文目的

本文统一回答 5 个问题：

1. 当前项目主线到底是什么
2. 哪些模块算 agent，哪些模块不算
3. 当前 LangGraph 主流程真实执行到哪一步
4. 后续为什么要走 Spec-Driven Development
5. 为什么这不是“几个 prompt 串起来”

这是一份主流程设计说明，不是营销文案，也不是待办清单。

## 2. 架构口径

### 2.1 LangGraph 是未来唯一主线

当前仓库里仍保留 `src/cipher_genius/api/mas_service.py` 中的 Legacy 兼容路径，但后续新增能力的默认落点应统一为：

- `src/cipher_genius/core/langgraph_mas.py`
- `src/cipher_genius/core/mas_runtime_support.py`

其中 `langgraph_mas.py` 负责 LangGraph 节点编排与状态流转，`mas_runtime_support.py` 负责主线共享的需求解析、候选生成、审计输入归一化、工程校验与中文交付辅助逻辑。Legacy 兼容路径仍保留在 `src/cipher_genius/api/mas_service.py`，但不再是 LangGraph 直接依赖的 helper 源。

因此应统一使用下面的说法：

- 代码现状：仓库仍保留 Legacy 兼容层
- 架构主线：LangGraph 是后续唯一主线

不要再把 Legacy 和 LangGraph 作为并列的未来方向来描述。

### 2.2 Agent 与 System Module 的边界

后续文档、前端、答辩材料都应遵守下面这个定义。

#### LLM Agent

指具备认知职责、需要基于上下文做判断或生成的模型角色。

#### System Module

指负责检索、存储、执行、渲染、调度、校验的工程模块，不因为放在图里就自动成为 agent。

## 3. 当前项目里的角色划分

### 3.1 当前真实存在的 LLM Agents

截至 2026-04-05，当前真正已经接入独立 LLM 决策入口的主要有：

- `Analyst Agent`
  - 负责解析需求、抽约束、识别歧义和澄清问题
- `Generation Agent`
  - 当前主要对应 `architect` 阶段
  - 负责生成候选方案与方案比较
- `Code Authoring Agent`
  - 当前主要对应 `engineer` 阶段中的代码与落地建议生成部分
- `AuditEvaluationAgent`
  - 在 `audit` 阶段读取独立审计窗口，对单个候选方案做最终裁决
- `Attack Planning Agent`
  - 在 `attack_planning_projection` 中做真实攻击规划决策
- `Vulnerability Evaluation Agent`
  - 在独立漏洞评估窗口中做严重度、可利用性与优先级判断
- `ExpertGateAgent`
  - 在漏洞裁决之后做独立放行 / 修补 / 补充验证决策
- `Patch Agent`
  - 在独立修补窗口中生成结构化 `PatchSpec`
- `Reflection Agent`
  - 在独立反思窗口中沉淀下一轮 prompt / policy / audit focus

### 3.2 当前主要的 System Modules

下面这些模块不应继续在架构叙事中被笼统称为 agent：

- `Context Builder`
- `Retrieval / Qdrant`
- `Case Memory`
- `Audit Engine`
- `Delivery Renderer`
- `Cache / Persistence`
- `Sandbox Dispatcher / Executor`

### 3.3 后续需要补齐的 LLM Agents

如果项目要从“可运行工作流”升级到“比赛级多 Agent 系统”，下一步优先要继续补的是：

- `Generation Agent`
  - 继续从“可生成候选”推进到“更强的检索增强、排序与证据绑定”
- `Audit Agent`
  - 当前已具备最终裁决的独立 LLM 入口，但还未完全沉淀成独立 `AuditFindingSpec`
- `Expert Gate` 多分支路由
  - 当前已完成独立认知层接线，但还未扩展到更完整的 `retry / observe / escalate / patch` 子图

### 3.4 当前目标闭环的推荐角色解释

结合当前项目现状与后续目标，建议统一使用下面这套角色口径：

- `Generation Agent`
  - 通过 Skill 提示词、RAG 检索、企业知识图谱或知识库生成候选方案
- `Audit Agent`
  - 对候选方案做结构化审查，判断约束满足情况、合规性和实现薄弱点
- `Attack Planning Agent`
  - 生成面向“已部署目标服务”的攻击计划与攻击 DSL，不直接执行攻击
- `Vulnerability Evaluation Agent`
  - 对攻击结果做漏洞定性、严重度判断、影响解释与利用条件分析
- `ExpertGateAgent`
  - 在漏洞裁决之后做独立放行 / 修补 / 补充验证决策
- `Patch Agent`
  - 基于漏洞证据产出修补动作、补丁 diff、新版本实现建议
- `Reflection Agent`
  - 沉淀失败模式、提示词优化建议和下一轮生成 / 审计策略改进

### 3.5 独立上下文窗口是硬约束，不是实现细节

后续如果要把系统真正做成多 Agent，而不是“几个 prompt 串起来”，必须明确一条约束：

- 不同 agent 应有各自独立的上下文窗口
- 不能把整轮共享长对话原样广播给所有 agent
- agent 之间的信息传递应通过结构化记忆、卡片和工件引用完成

建议默认采用下面这套上下文治理口径：

- `Generation Agent`
  - 只读取：需求摘要、约束卡、检索证据包、历史反思卡
- `Audit Agent`
  - 只读取：ProposalSpec、EvidencePack、必要的约束卡，不读取攻击日志全文
- `Attack Planning Agent`
  - 只读取：TargetServiceSpec、AuditFindingSpec、PatchSpec、风险重点
- `Vulnerability Evaluation Agent`
  - 只读取：AttackResultSpec、Finding Card、必要证据引用

## 3.6 2026-03-27 攻击决策已接入真实控制流

当前主流程里，`Attack Planning Agent` 已不再只是生成一个“展示字段”，而是进入真实分支控制：

- `execute / continue / replan`
  - 继续进入 sandbox attack dispatch
- `handoff_to_vulnerability`
  - 跳过新的攻击执行，直接把控制权交给漏洞评估层
- `stop`
  - 跳过新的攻击执行，并以停止态结束本轮攻击分支

这意味着当前 `attack_loop` 的主流程应理解为：

1. `Attack Planning Agent`
2. `Sandbox Dispatcher / Attack Executor` 或 `Vulnerability Evaluation Agent`
3. `Patch Agent`
4. `Reflection Agent / Delivery`

而不是“无论 planner 决策是什么，都一定先执行一轮攻击”。

当前稳定观测对象：

- `delivery.attack_loop.attack_decision`
- `delivery.attack_loop.regression_attack_decision`
- `delivery.attack_loop.rounds[*].attack_decision`
- `delivery.attack_loop.rounds[*].mode`
- `delivery.sandbox_dispatcher.baseline_attack`
- `delivery.sandbox_dispatcher.regression_attack`

其中 `rounds[*].mode` 当前可能出现：

- `executed`
- `handoff`
- `stopped`
- `planned`
- `preview`

## 3.7 2026-03-27 Artifact Summarizer 已接入主链第一版

当前主流程里，攻击执行面产生的 `trace / metrics / finding` 已不再只作为文件路径存在。

现在的推荐理解方式是：

1. sandbox runtime 生成真实工件
2. `artifact_summarizer` 压缩工件
3. projection / memory_handoff 只向下游传递 `attack_result_summaries`
4. 下游 agent 再基于摘要和 artifact ref 做决策

当前已接入：

- `vulnerability_evaluation` 的 `attack_result_summary`
- `patch` 的 `attack_artifact_summary`
- `reflection` 的 `regression_attack_result_summaries`

这意味着“独立上下文窗口”开始真正落到工件层，而不仅仅是 prompt 层。
- `Patch Agent`
  - 只读取：VulnerabilityVerdictSpec、受影响工件摘要、版本差异卡
- `Reflection Agent`
  - 只读取：轮次摘要、失败模式卡、补丁结果卡、最终裁决卡

这条约束的意义在于：

- 避免上下文窗口无限膨胀
- 避免不同 agent 被无关历史污染
- 让“为什么这一轮这么做”可以追溯到明确的输入卡片
- 让后续压缩、回放、评测、权限控制都有稳定边界

建议后续主流程里把这件事明确拆成两层：

- `Context Projection Layer`
  - 负责给每个 agent 构造独立上下文窗口
- `Memory Handoff Layer`
  - 负责把本阶段结果压缩成下一阶段可消费的 card / ref

这样主流程才不会退化成：

- 节点很多
- 但所有节点仍在共享同一坨大上下文

## 4. 当前 LangGraph 主流程

### 4.1 当前实际工作流

当前 `workflow_trace` 的主线为：

1. `analyst`
2. `context_builder`
3. `architect`
4. `audit`
5. `engineer`
6. `target_deployer`
7. `attack_executor`
8. `vulnerability_evaluation`
9. `patch_reflection`
10. `delivery`

这条链条已经能支撑：

- 需求理解
- 证据构建
- 候选生成
- 审计筛选
- 工程建议
- 目标服务描述生成
- 攻击闭环壳子接线
- 最终交付

需要特别说明的是：

- 当前 `target_deployer / attack_executor / vulnerability_evaluation / patch_reflection` 已经进入 LangGraph 主线
- 当前仍属于 attack-loop shell 阶段
- 当前已接入本地文件沙盒：会落盘目标服务 manifest、代码工件、trace / metrics / finding 文件
- `attack_results`、`vulnerability_verdict`、`patch_spec` 当前仍不是“真实网络攻击 + 真实隔离执行”的最终形态，真实 sandbox 执行仍待后续接线

### 4.2 当前每一层的职责

#### `analyst`

- 解析原始需求
- 形成结构化约束
- 识别歧义与待澄清问题

#### `context_builder`

- 根据约束检索企业知识
- 汇总组件知识卡、模板知识卡、benchmark 案例
- 输出统一 `evidence_pack`

#### `architect`

- 生成候选方案
- 组织候选比较
- 给出初步推荐与解释

#### `audit`

- 执行合规、风险、后量子等规则判断
- 生成拒绝原因与整改建议
- 在存在 `reflection_memory` 时，把项目级反思写入本轮 `reasons / key_findings / recommended_changes`

#### `engineer`

- 输出工程落地建议
- 尝试形成代码、伪代码或实施步骤

#### `target_deployer`

- 根据当前候选实现生成目标服务部署描述
- 输出 `TargetServiceSpec`

#### `attack_executor`

- 基于目标服务描述生成受限攻击任务
- 当前输出结构化 `AttackSpec`，并通过本地文件沙盒生成 `trace / metrics / finding` 工件

#### `vulnerability_evaluation`

- 根据攻击结果输出漏洞定性和优先级判断
- 输出 `VulnerabilityVerdictSpec`

#### `patch_reflection`

- 先输出 `ExpertGateDecisionSpec`
- 再输出 `PatchSpec`
- 生成 `PatchExecutionSpec` 与下一轮 generation / audit 可复用的 reflection 卡片

#### `delivery`

- 统一收口最终方案
- 组织交付摘要、审计信息、导出信息和元数据

### 4.3 最省成本的整合方向

结合当前仓库现状，最不建议的做法是“推倒重写一套全新多 Agent 后端”。

更合理的做法是保留当前主链骨架，在 `audit -> engineer -> delivery` 之间插入一条可循环的攻击与修补子链，把系统从“线性工作流”升级为“可回放闭环”：

1. `analyst`
2. `context_builder`
3. `architect`
4. `audit`
5. `engineer`
6. `attack_loop_subgraph`
7. `expert_gate`
8. `patcher` 或 `delivery`
9. `reflection_writer`

这里的关键不是节点数量增加，而是：

- 当前已有的 `case_id`、`workflow_trace`、流式执行、case memory、evidence pack 都可以继续复用
- 攻击、修补、回归与反思以“子图 + 工件 + 状态卡片”的方式接入，而不是把整轮历史继续塞回 prompt
- 系统从“一次跑完的主线”演进为“可暂停、可恢复、可循环的状态机”

### 4.4 当前目标闭环的推荐统一表述

你们当前想要实现的链路，建议统一收口为下面这条闭环：

1. 用 Skill 提示词与企业知识检索驱动 `Generation Agent`
2. 由 `Audit Agent` 审查候选方案
3. 在沙盒中部署目标服务，并由 `Attack Planning Agent` 持续攻击
4. 由 `Vulnerability Evaluation Agent` 评估攻击命中的漏洞
5. 由 `ExpertGateAgent` 决定进入修补、补充攻击还是观察收敛
6. 由 `Patch Agent` 修补漏洞并形成新版本
7. 重新部署并做回归攻击 / 回归审计
8. 由 `Reflection Agent` 优化下一轮 generation / audit 的提示词与工作策略

这条口径的重要意义在于：

- 主链不再只是“生成方案并解释”
- 主链管理的是“生成 -> 审计 -> 攻击 -> 评估 -> 修补 -> 反思”的工程闭环
- 每一轮输出的不只是文本，还有部署产物、攻击结果、漏洞结论、补丁与代码交付物

## 5. 当前主线的主要问题

### 5.1 `audit` 已进入“工具增强的独立 LLM 裁决”阶段

从 2026-04-03 起，`audit` 阶段已经不再只是工具结果后的手写规则拼装，而是新增了独立的 `AuditEvaluationAgent`：

- `vulnerability_scanner / compliance_reporter / security_assessor`
  - 仍然保留，定位为 `Audit Agent` 的工具输入
- `audit_decision_input`
  - 当前每轮会把单个候选方案的审计工具摘要压成结构化卡片，再送入独立审计窗口
- `AuditEvaluationAgent`
  - 基于独立 projection 对单个候选方案输出最终 `AuditorRoundPayload`
- `AuditorRoundPayload`
  - 对外契约保持不变，因此前端、API、benchmark 不需要跟着大改

当前更准确的边界是：

- 已完成的是“审计最终裁决的独立 LLM 化”
- 尚未完成的是“`audit` 前半段彻底 projection-only”与“独立 `AuditFindingSpec` 的完整沉淀”

### 5.2 还没有真正的攻击执行闭环

项目里虽然已经讨论到攻击 agent、漏洞评估、修补闭环，但当前还没有真正意义上的：

- 算法部署沙盒
- 攻击任务执行器
- 攻击结果聚合
- 攻击结果回流主链

所以这一段目前还不能被写成“已实现能力”。

### 5.3 还没有真正的分层状态模型

当前主链有 `run_id`、`discussion_log`、`auditor_rounds` 等运行态信息，但还没有彻底收口成面向长期演进的项目级状态模型。

后续至少要清楚区分：

- `case_id`
- `run_id`
- `round_id`
- `artifact_id`
- `version_id`

### 5.4 还没有真正的“记忆传递总线”

多 Agent 架构里，真正的难点不是“再多加几个节点名”，而是：

- 一个 agent 如何在不读取全部历史的情况下接住上一阶段结论
- 一个 agent 如何把自己的结果压缩成下一阶段可消费的稳定对象
- 哪些信息进长期记忆，哪些只留在本轮工件里

后续必须把 agent 间传递收口为统一的 memory bus，而不是散落在 prompt 文本里。建议至少拆成：

- `Constraint Card`
- `Decision Card`
- `Finding Card`
- `Patch Card`
- `Reflection Card`
- `Artifact Ref`

没有这层 memory bus，所谓“独立上下文窗口”就会退化成“大家还是共享一大段拼接文本”。

## 6. 推荐的 Agent Handoff 链路

如果后续要按你们的目标闭环实现，推荐按下面的 handoff 结构收口：

1. `Generation Agent`
   - 输入：Constraint Card + EvidencePack + Reflection Card
   - 输出：ProposalSpec + Decision Card
2. `Audit Agent`
   - 输入：ProposalSpec + Constraint Card + EvidencePack
   - 输出：AuditFindingSpec + Finding Card
3. `Attack Planning Agent`
   - 输入：TargetServiceSpec + Finding Card + Patch Card
   - 输出：AttackSpec + Attack Plan Card
4. `Vulnerability Evaluation Agent`
   - 输入：AttackResultSpec + Artifact Ref + Evidence Ref
   - 输出：VulnerabilityVerdictSpec + Finding Card
5. `Patch Agent`
   - 输入：VulnerabilityVerdictSpec + Finding Card + Artifact Ref
   - 输出：PatchSpec + Patch Card
6. `Reflection Agent`
   - 输入：Decision Card + Finding Card + Patch Card + 当前轮结果摘要
   - 输出：Reflection Card

这里最重要的不是名字，而是：

- 每一步都有明确输入边界
- 每一步都输出下一步能直接消费的结构化对象
- 每一步都不依赖读取全量历史

否则后面做长期记忆、回放、修补收敛时会越来越乱。

### 5.4 当前缺的不是更多 agent，而是系统层抽象

从整合成本和收益看，当前项目最缺的不是继续增加“听起来像 agent 的节点”，而是把下面两层抽出来：

- `Execution Plane`
  - 负责沙盒调度、预算约束、隔离运行、日志采集、指标回传
- `Artifact / State Plane`
  - 负责项目线程、轮次状态、工件引用、压缩卡片和可回放摘要

如果这两层没有独立出来，即使图里新增更多 agent，系统仍然容易退化成“多段 prompt 串联”。

## 6. 为什么要走 Spec-Driven Development

多 Agent 系统如果只靠自然语言上下文传递，越往后越难维护。

因此主链必须逐步过渡到基于 spec 的阶段通信。

### 6.1 建议优先定义的核心 spec

- `RequirementSpec`
  - 统一需求、约束、澄清状态
- `EvidencePack`
  - 统一检索证据、引用来源、过滤条件
- `ProposalSpec`
  - 统一候选方案、组件组合、推荐理由
- `AuditFindingSpec`
  - 统一审计结论、拒绝理由、整改建议
- `TargetServiceSpec`
  - 统一待测服务接口、部署方式、版本和运行边界
- `AttackSpec`
  - 统一攻击任务、输入样例、沙盒配置
- `AttackResultSpec`
  - 统一攻击结果、异常、漏洞发现、日志摘要
- `ExpertGateDecisionSpec`
  - 统一漏洞裁决后的放行、修补、补充验证决策
- `PatchSpec`
  - 统一修补动作、目标文件、整改优先级
- `DeliverySpec`
  - 统一最终交付、引用、人工确认点

### 6.2 这一步的实际价值

采用 spec 并不是为了形式化而形式化，而是为了：

- 让 agent 之间输入输出稳定
- 让上下文可以压缩，而不丢失关键结构
- 让回归测试可以写在结构层，而不只是看文本
- 让前端可以消费稳定 artifact，而不是临时字符串
- 让后续新增 agent 更容易接入

### 6.3 推荐的主状态 schema 方向

建议后续主图优先收口成 typed state，而不是继续把自由文本作为默认传递介质。

最小建议字段包括：

- `case_id`
- `run_id`
- `round_id`
- `requirement_summary`
- `threat_model`
- `evidence_refs`
- `candidate_plan`
- `audit_report`
- `implementation_ref`
- `target_service_ref`
- `attack_specs`
- `attack_result_refs`
- `vulnerability_summary`
- `expert_gate_decision`
- `patch_plan`
- `patch_ref`
- `decision_cards`
- `reflection_cards`
- `current_summary`
- `stop_reason`
- `status`

其中要特别注意：

- graph state 里保留摘要与引用，不保留大段代码、日志和全文报告
- 原始代码、日志、漏洞 JSON、patch diff、最终报告都进入 artifact store
- 前端和导出链直接消费结构化 spec 与 artifact，而不是从聊天历史里二次拼装

## 7. 推荐的目标主流程

后续推荐的 LangGraph 主线应逐步演进为下面这条链：

1. `Analyst Agent`
2. `Context Builder`
3. `Generation Agent`
4. `Audit Engine`
5. `Audit Agent`
6. `Attack Planning Agent`
7. `Sandbox Dispatcher`
8. `Attack Executor`
9. `Result Aggregator`
10. `Expert Gate`
11. `Patch Agent`
12. `Reflection Agent`
13. `Delivery Renderer`

其中：

- 需要 LLM 判断和生成的放在 agent 层
- 需要检索、执行、调度、收集、渲染的放在 system module 层

### 7.1 Attack Loop 子图的推荐拆法

攻击闭环更适合做成 `attack_loop_subgraph`，而不是在父图里堆很多执行细节节点。

推荐子图职责如下：

1. `Attack Planning Agent`
   - 输出 `AttackSpec` 或攻击 DSL
2. `Target Deployer`
   - 把待测的加密服务部署为独立目标实例
3. `Sandbox Dispatcher`
   - 做 schema 校验、预算校验、白名单校验、任务签名
4. `Attack Executor`
   - 在隔离环境对目标服务发起攻击任务
5. `Result Aggregator`
   - 汇总 telemetry、finding、异常与产物引用
6. `Vulnerability Evaluation Agent`
   - 结合攻击结果做漏洞定性、严重度与利用条件判断
7. `Patch Agent`
   - 基于漏洞证据输出修补方案、补丁 diff 或修复动作
8. `Regression Audit`
   - 对修补后的新版本重新验证，决定是否继续闭环

这样可以把“攻击策划”和“攻击执行”明确分层：

- Agent 负责决定“测什么、为什么测”
- 执行平面负责决定“允不允许执行、怎么安全执行、结果如何落盘”

### 7.1.1 当前目标场景应收口为“攻击已部署的目标服务”

你们当前想要的不是抽象意义上的攻击样例，而是：

- 先把候选实现部署成“承载加密数据处理能力的目标服务”
- 由攻击 agent 对这个目标服务发起受控攻击
- 由服务端对应的漏洞评估 agent 和修补 agent 消费攻击结果
- 所有这些过程都在沙盒环境内完成

因此，后续 `AttackSpec` 不应只描述“攻击什么算法”，还要描述：

- `target_service_ref`
- `deployment_profile`
- `service_interface`
- `attack_surface`
- `expected_artifacts`
- `service_version`
- `traffic_metrics_profile`

换句话说，攻击闭环的对象应从“代码片段”升级为“已部署服务实例”。

### 7.1.2 漏洞评估 agent 与修补 agent 的推荐放置方式

虽然这两个 agent 是“服务端链路”的一部分，但从工程隔离角度，不建议把它们直接塞进目标服务进程本身。

更推荐的做法是让它们运行在同一沙盒域内的相邻执行单元中：

- `target service sandbox`
  - 运行待测加密服务
- `attack worker sandbox`
  - 运行攻击任务
- `evaluation / patch sandbox`
  - 运行漏洞评估 agent、Patch agent、回归校验逻辑

这样做的好处是：

- 目标服务保持接近真实部署形态
- 评估与修补逻辑不会直接污染目标服务进程
- patch 可以形成新版本工件，再重新部署成下一轮目标实例
- 更容易表达 `version_id`、`artifact_id`、修补前后对比与回归轨迹

### 7.2 Attack Agent 不直接拿执行权限

后续实现时应明确禁止下面这种耦合：

- Attack agent 直接生成 shell 命令
- Attack agent 直接拼接 `docker run`
- Attack agent 直接拿到宿主机执行权限

更推荐的方式是：

- Attack agent 只输出受限 `AttackSpec`
- `Sandbox Dispatcher` 负责校验与签名下发
- Worker 只消费通过策略检查的任务

这样系统的安全边界、预算边界和治理边界都会清楚很多。

同理，`Patch Agent` 也不应直接修改正在运行的目标服务实例。

更推荐的流程是：

- `Patch Agent` 输出 `PatchSpec`、diff 或修补动作
- builder / executor 生成新的服务版本工件
- `Target Deployer` 把新版本重新部署到下一轮 sandbox
- `Regression Audit` 与下一轮攻击重新验证修补效果

### 7.3 最终交付物不应只是一段摘要

结合当前项目定位，最终交付建议固定包含以下几类产物：

- 结构化审计结论
- 结构化漏洞评估结论
- 修补建议或补丁方案
- 伪代码实现
- Python 参考实现
- C / C++ 参考实现
- 报告与导出工件

这样前端和答辩都能明确说明：

- 系统不仅会“解释”
- 系统还能形成可落地的代码级交付

## 8. Retrieval、Memory、Sandbox 在主链里的位置

### 8.1 Retrieval

检索不是页面旁路功能，而应成为 `Context Builder` 的核心输入层。

它负责：

- 根据行业、场景、约束做过滤
- 混合召回规范、组件、案例、模板知识
- 输出统一证据包给 generation 与 audit 使用

### 8.2 Memory

记忆不是聊天记录堆积，而应是分层治理的状态系统。

建议至少分成：

- `Knowledge Memory`
- `Case Memory`
- `Decision Memory`

此外还建议把“运行态状态”和“工件存储”进一步分开：

- 短期线程状态
  - 当前 run / 当前 round 需要的小型结构化摘要
- 项目长期记忆
  - 已确认约束、被拒方案、修补历史、人工确认点
- 工件仓库
  - 原始代码、完整日志、漏洞 JSON、patch diff、导出报告

推荐的用户视图不是“聊天历史”，而是：

- 项目
- 运行
- 轮次
- 工件

### 8.3 Sandbox

沙盒不是一个独立展示页，而是攻防闭环里的执行平面。

它负责：

- 部署待测目标服务
- 执行攻击任务
- 收集日志、异常、指标与漏洞发现
- 输出稳定的 `AttackResultSpec`

对于你们当前场景，沙盒里至少应明确 3 类运行对象：

- `Target Service`
  - 被攻击的加密数据服务实例
- `Attack Worker`
  - 对目标服务发起受控攻击
- `Evaluation / Patch Worker`
  - 分析漏洞、生成补丁、回归验证

### 8.4 控制平面与执行平面的分层建议

为了避免主后端直接承载高风险执行，建议把 sandbox 体系分成两层：

#### 控制平面

- FastAPI
- LangGraph orchestrator
- 状态更新
- 报告与可视化收口

#### 执行平面

- `Sandbox Manager`
- `Celery attack worker`
- 隔离容器运行时
- 私有工作目录
- 资源预算与网络策略
- telemetry 采集与 artifact 回传

后续即使具体隔离技术从 Docker 演进到更强的运行时，这个分层也不需要推翻。

### 8.5 子图持久化与并行建议

对于后续的攻击子任务，推荐采用下面的状态策略：

- 父图使用项目主线程持久化
- 攻击子任务按 invocation 独立运行
- 聚合节点把结果统一归并回父图

这样更适合并行攻击任务，能减少并行子任务之间的 checkpoint 冲突。

## 9. 前端展示建议

前端不应只展示最终文案，而应让评委和企业用户看见“系统正在做什么”。

推荐至少分 4 个区块：

### 9.1 Multi-Agent 流程透明化

- 主流程 DAG / 阶段流
- 当前节点高亮
- 每个节点输入摘要 / 输出摘要
- `workflow_trace`、耗时、状态、版本号

### 9.2 Sandbox 攻击可视化

- 目标服务运行状态
- 攻击阶段时间轴
- 服务器流量波动图
- CPU / 内存 / 网络指标
- finding 实时列表

### 9.3 版本与工件区

- 当前服务版本
- patch diff
- 修补前后评分与风险对比
- 可下载 artifact

### 9.4 项目记忆区

- case snapshot
- 最近 1-2 轮决策卡片
- 漏洞卡片 / 修补卡片 / 反思卡片
- 下一轮提示词优化建议

## 10. 微调的当前口径

当前阶段不建议把“已经完成模型微调”写成已实现能力，更合理的表述是：

- 当前不做在线权重微调
- 当前优先完成“闭环数据采集 + Reflection Card + Prompt Policy 优化 + 失败模式沉淀”
- 系统预留微调数据出口，但不把“已微调模型”写成当前成果

更适合对外表达为：

- 已具备形成微调语料和偏好数据的闭环基础设施
- 当前先落地提示词级闭环优化与策略改进
- 后续可接 SFT / preference tuning / reward modeling，但不在本阶段承诺为已实现能力

## 11. 为什么这不是“几个 prompt 串起来”

本项目和 prompt chain 的本质区别，不在于节点更多，而在于管理对象不同。

Prompt chain 主要管理的是一次性文本生成。

当前及未来的 LangGraph 主线要管理的是：

- 阶段责任
- 证据上下文
- 项目状态
- 攻防执行 artifact
- 决策归因
- 最终交付契约

因此更准确的说法应该是：

- 我们不是在串 prompt
- 我们是在管理一个可检索、可执行、可回放、可交付的企业决策系统

## 12. 后续实现顺序建议

建议后续实现顺序固定为：

1. 收口 LangGraph-only 架构叙事
2. 明确 agent / system module 边界
3. 落地核心 spec
4. 补齐 sandbox execution plane
5. 增加 audit / attack / expert gate / patch / reflection agents
6. 完善 retrieval 和 layered memory
7. 强化引用驱动交付与中文回归测试

## 12.1 每轮闭环后建议沉淀的 4 类卡片

为了控制上下文体积，并把闭环结果转成稳定资产，建议每轮至少沉淀以下 4 类压缩卡片：

- `Decision Card`
  - 本轮做了什么决策、为什么这样决定
- `Finding Card`
  - 漏洞名称、严重度、证据、影响面、关联 artifact
- `Patch Card`
  - 修补动作、改动范围、回归风险
- `Reflection Card`
  - 下一轮生成、审计或攻击策略要如何调整

后续 generator、audit、patcher 默认优先读取这些卡片与引用，而不是整轮完整聊天历史。

## 13. 每次改动后的回归检查

每次修改主链后，至少检查下面这些点：

- 默认 `/api/v1/mas/execute` 与 `/api/v1/mas/stream` 是否仍返回稳定 `MASResponse`
- `workflow_trace` 是否仍反映真实执行阶段
- 中文标题、中文建议、中文报告摘要是否没有退化
- 新增 spec 或 artifact 是否没有破坏现有接口契约
- benchmark 与报告导出是否仍可用

## 14. 关联文件

- `src/cipher_genius/core/langgraph_mas.py`
- `src/cipher_genius/api/mas_service.py`
- `src/cipher_genius/api/schemas.py`
- `src/cipher_genius/memory/service.py`
- `src/cipher_genius/retrieval/service.py`
- `src/cipher_genius/retrieval/qdrant_store.py`
- `docs/TECHNICAL_DOCUMENTATION.md`
- `REMAIN.md`
- `TODO_VIBING.md`

## 2026-03-26 增量更新：攻击闭环进入“本地进程壳子”阶段

### 当前链路

- `target_deployer`：负责为目标服务生成工作区、代码工件、`service_runtime.py`、`runtime_info.json`。
- `attack_executor`：负责拉起本地受限进程型目标服务，执行健康探针和接口探测，并沉淀 `traffic_series`。
- `vulnerability_evaluation`：继续消费结构化 `attack_results`。
- `patch_reflection`：继续基于 `vulnerability_verdict -> expert_gate_decision -> patch_spec` 生成修补与反思结果。

### 当前工程边界

- 现在已经不是“仅内存模拟”或“仅文件壳子”。
- 现在也还不是“真实隔离执行平面”。
- 更准确的表述应为：“本地文件工件 + 本地受限进程壳子 + 结构化 attack-loop telemetry”。

### 前端联动

- `ReportsView.jsx` 已接入 `delivery.attack_loop`。
- 报告页可直接展示：目标服务状态、流量波动、漏洞评估、修补建议、反思卡片。

## 2026-03-26 多轮闭环补记

- 当前 attack-loop 已从“单轮结果”升级为“首轮基线执行 + 第二轮补丁回归执行”的结构。
- 这一步的价值在于：
  - 把 `patch_spec` 真正接入下一轮攻击计划
  - 为后续 `patch -> regression audit -> reflection` 子图提供稳定对象
- 这一步的边界在于：
  - 第 2 轮现已升级为 `regression`
  - 但仍不是“生产补丁验证已完成”

## 2026-03-26 多轮闭环升级

- 当前 attack-loop 已继续升级为“首轮基线执行 + 第二轮补丁回归执行”的结构。
- 当前 `patch_reflection` 的职责边界为：
  - 构建 `expert_gate_projection`
  - 由 `ExpertGateAgent` 输出 `expert_gate_decision`
  - 生成 `patch_spec`
  - 生成 `reflection_cards`
  - 产出补丁版本目标服务描述
  - 触发补丁版本壳子重部署
  - 执行正式回归探测并形成残余风险裁决
- 这样做的好处是：
  - 不必新增 workflow node，也能保持 `WORKFLOW_TRACE` 稳定
  - `delivery.attack_loop` 可以在不破坏旧字段的前提下承载真实第 2 轮结果
- 仍需保持诚实边界：
  - 这是“补丁版本壳子重部署 + 正式回归探测”
  - 不是“生产补丁验证已完成”

## 2026-03-26 独立上下文窗口接线补记

- 当前 `langgraph_mas.py` 已在主链内部生成六类 role-aware projection：
  - `generation_projection`
  - `audit_projection`
  - `attack_planning_projection`
  - `vulnerability_projection`
  - `patch_projection`
- 当前 `delivery` 已把这些 projection 透传为：
  - `delivery.context_projections.generation`
  - `delivery.context_projections.audit`
  - `delivery.context_projections.attack_planning`
  - `delivery.context_projections.vulnerability_evaluation`
  - `delivery.context_projections.patch`
  - `delivery.context_projections.reflection`
- agent 间记忆传递当前会额外暴露为 `delivery.memory_handoffs`
- 这说明系统已经不再只停留在“schema 设计”，而是有了第一版运行时可观测的 context projection / handoff 链路
- 但这还不是最终态：
  - graph state 里仍保留旧字段以维持兼容
  - 还没有做到所有 agent 完全只读 projection

## 2026-03-26 Agent 间为什么以结构化 JSON Handoff 为主

- 这里说的“靠 JSON 传递”，不是把所有历史、所有代码、所有日志塞进一个大 JSON。
- 更准确地说，是让 agent 间主通道默认传递“受 schema 约束的结构化对象”。
- 自然语言摘要仍然可以存在，但应放在 `summary / payload` 这类结构化字段里。
- 大体积对象默认外置成 artifact / evidence，再通过 ref 引用进入下游窗口。

这样做的目的主要有 5 个：

- 稳定
  - 下游 agent 拿到的是固定字段，而不是每轮措辞都变化的大段自然语言
- 可裁剪
  - 调度层可以按 `constraints / cards / artifact_refs / evidence_refs` 分层压缩，而不是整段 prompt 一起膨胀
- 可审计
  - 可以明确回答“某个 agent 本轮到底看到了什么”
- 可视化
  - 前端可以直接渲染 handoff、card、artifact ref，而不是再拆自然语言
- 可回放
  - 后续 benchmark、失败复盘、提示词优化可以稳定复用这套 handoff 结构

推荐的三层表达是：

- 主通道：结构化 JSON schema
- 内容层：放在 card / summary 字段中的压缩文本
- 大对象层：artifact store / evidence store 中的外部工件

## 2026-03-26 JSON Handoff 的边界

- 传给 agent 的应是“结构化摘要”
- 不应直接传给 agent 的是“全量原文”

推荐进入 handoff 的内容：

- 当前目标
- 已确认约束
- 本轮关键卡片
- 必要的证据引用
- 必要的工件引用

不建议直接塞进 handoff 的内容：

- 全量攻击日志
- 全量 trace
- 大段代码全文
- 知识库原文整块拼接
- 全部历史聊天记录

否则即使外层看起来用了 JSON，也仍会退化成“共享长上下文”的 prompt chain。

## 2026-03-26 端到端 JSON Handoff 示例链

下面给出一条可展示、可实现、可答辩的最小 handoff 示例链。重点不是字段写得多复杂，而是让评审或开发一眼看出：

- 每个 agent 有独立窗口
- 角色间传递的是结构化对象
- 大对象通过 ref 传递，而不是把所有原文塞进 prompt

### 1. `context_builder -> generation_agent`

```json
{
  "handoff_id": "handoff-run-001-generation",
  "from_agent": "context_builder",
  "to_agent": "generation_agent",
  "case_id": "case-buildtrust-001",
  "run_id": "run-001",
  "round_id": "generation-r1",
  "objective": "将需求约束、企业知识与项目级记忆投影到生成 Agent。",
  "status": "ready",
  "cards": [
    {
      "card_id": "card-case-memory-001",
      "card_type": "case_memory",
      "summary": "已有一次历史拒绝记录，当前必须满足审计留痕与后量子迁移要求。"
    },
    {
      "card_id": "card-analyst-001",
      "card_type": "analyst_summary",
      "summary": "业务场景为建筑工程可信交付，优先中文交付。"
    }
  ],
  "artifact_refs": [
    {
      "artifact_id": "artifact-structured-spec-001",
      "artifact_type": "structured_spec",
      "title": "结构化需求说明"
    }
  ],
  "evidence_refs": [
    {
      "doc_id": "doc-pq-standard-001",
      "chunk_id": "chunk-07",
      "title": "后量子迁移建议"
    }
  ]
}
```

### 2. `generation_agent -> audit_agent`

```json
{
  "handoff_id": "handoff-run-001-audit",
  "from_agent": "generation_agent",
  "to_agent": "audit_agent",
  "case_id": "case-buildtrust-001",
  "run_id": "run-001",
  "round_id": "audit-r1",
  "objective": "将候选方案摘要、证据引用与项目约束投影到审计 Agent。",
  "cards": [
    {
      "card_id": "card-candidate-summary-001",
      "card_type": "candidate_summary",
      "summary": "候选方案 2 个，方案 A 偏吞吐，方案 B 偏审计完备。"
    }
  ],
  "artifact_refs": [
    {
      "artifact_id": "proposal-1",
      "artifact_type": "scheme_candidate",
      "title": "方案 A"
    },
    {
      "artifact_id": "proposal-2",
      "artifact_type": "scheme_candidate",
      "title": "方案 B"
    }
  ],
  "evidence_refs": [
    {
      "doc_id": "doc-compliance-001",
      "chunk_id": "chunk-03",
      "title": "企业合规要求摘要"
    }
  ]
}
```

### 3. `audit_agent -> attack_planning_agent`

```json
{
  "handoff_id": "handoff-run-001-attack-planning",
  "from_agent": "audit_agent",
  "to_agent": "attack_planning_agent",
  "case_id": "case-buildtrust-001",
  "run_id": "run-001",
  "round_id": "attack-plan-r1",
  "objective": "基于审计发现生成受预算约束的攻击规划。",
  "cards": [
    {
      "card_id": "card-audit-findings-001",
      "card_type": "decision_card",
      "summary": "发现错误处理暴露内部实现细节，且接口约束不足。"
    }
  ],
  "artifact_refs": [
    {
      "artifact_id": "svc-run-001",
      "artifact_type": "target_service",
      "title": "待测目标服务"
    },
    {
      "artifact_id": "attack-plan-1",
      "artifact_type": "attack_spec",
      "title": "错误处理探测"
    }
  ]
}
```

### 4. `attack_planning_agent -> vulnerability_agent`

```json
{
  "handoff_id": "handoff-run-001-vulnerability",
  "from_agent": "attack_planning_agent",
  "to_agent": "vulnerability_agent",
  "case_id": "case-buildtrust-001",
  "run_id": "run-001",
  "round_id": "vulnerability-r1",
  "objective": "将攻击结果与漏洞证据投影到漏洞评估 Agent。",
  "cards": [
    {
      "card_id": "card-attack-result-001",
      "card_type": "finding_card",
      "summary": "攻击成功触发错误回显，返回体中出现内部参数名与路径信息。"
    }
  ],
  "artifact_refs": [
    {
      "artifact_id": "trace-attack-001",
      "artifact_type": "attack_artifact",
      "title": "攻击 trace"
    },
    {
      "artifact_id": "metrics-attack-001",
      "artifact_type": "attack_artifact",
      "title": "攻击指标文件"
    }
  ]
}
```

### 5. `vulnerability_agent -> patch_agent`

```json
{
  "handoff_id": "handoff-run-001-patch",
  "from_agent": "vulnerability_agent",
  "to_agent": "patch_agent",
  "case_id": "case-buildtrust-001",
  "run_id": "run-001",
  "round_id": "patch-r1",
  "objective": "将漏洞裁决、受影响工件与修补目标投影到修补 Agent。",
  "cards": [
    {
      "card_id": "card-verdict-001",
      "card_type": "vulnerability_verdict",
      "summary": "当前严重度为中高，优先修补错误处理与接口约束。"
    },
    {
      "card_id": "card-audit-round-001",
      "card_type": "audit_decision",
      "summary": "补丁必须同时满足审计留痕、错误处理收口和回归验证。"
    }
  ],
  "artifact_refs": [
    {
      "artifact_id": "svc-run-001",
      "artifact_type": "target_service",
      "title": "待修补服务"
    }
  ]
}
```

### 6. `patch_agent -> reflection_agent`

```json
{
  "handoff_id": "handoff-run-001-reflection",
  "from_agent": "patch_agent",
  "to_agent": "reflection_agent",
  "case_id": "case-buildtrust-001",
  "run_id": "run-001",
  "round_id": "reflection-r1",
  "objective": "将修补结果、回归探测结论与反思卡投影到反思 Agent。",
  "cards": [
    {
      "card_id": "card-patch-plan-001",
      "card_type": "patch_plan",
      "summary": "已为错误处理与接口边界生成补丁计划，下一版本为 v2。"
    },
    {
      "card_id": "card-reflection-001",
      "card_type": "reflection_summary",
      "summary": "下一轮 generation 应优先约束错误处理外露，audit 应强化接口异常返回检查。"
    }
  ],
  "artifact_refs": [
    {
      "artifact_id": "svc-run-001-reg",
      "artifact_type": "regression_target_service",
      "title": "补丁回归版本服务"
    },
    {
      "artifact_id": "trace-regression-001",
      "artifact_type": "attack_artifact",
      "title": "回归攻击 trace"
    }
  ]
}
```
## 2026-03-26 前端展示建议

- 如果后续需要把这条闭环做成“评委看得懂、企业客户也看得懂”的界面，推荐前端默认展示 4 层：
  - `流程透明化`
  - `独立上下文窗口`
  - `沙盒执行态势`
  - `闭环优化`
- 其中建议分别对应：
  - `delivery.memory_handoffs`
  - `delivery.context_projections`
  - `delivery.attack_loop`
  - `reflection_cards / next_action`
- 推荐页面上的诚实口径：
  - 可以说“本地受限进程沙盒演示闭环”
  - 不应说“生产级隔离攻击沙盒已经完成”

## 2026-03-26 Dispatcher 接线补记

- 当前 `Target Deployer` 与 `Attack Executor` 已不再直接裸调 runtime。
- LangGraph 主线现已收口为：
  - orchestration
  - dispatcher approval
  - local runtime execution
  - structured delivery
- 当前新增的稳定返回对象为：
  - `delivery.sandbox_dispatcher.policy`
  - `delivery.sandbox_dispatcher.baseline_deployment`
  - `delivery.sandbox_dispatcher.baseline_attack`
  - `delivery.sandbox_dispatcher.regression_deployment`
  - `delivery.sandbox_dispatcher.regression_attack`
- 当前 dispatcher 结果还会附带：
  - `failure_items`
  - `audit_trail`
- 这一步的定位是“把执行审批边界显式化”，而不是宣布已拥有完整 execution plane。

## 2026-03-26 Projection-Only 主通道补记

- 当前 `attack_planning -> vulnerability -> patch -> reflection` 四段已经开始按“先 projection、再 handoff、再执行”的顺序运行。
- 这意味着 `delivery.context_projections` 中的以下对象，已更接近真实输入窗口：
  - `attack_planning`
  - `vulnerability_evaluation`
  - `patch`
  - `reflection`
- 当前这些 projection 的职责不再只是展示，而是作为节点执行时的主输入边界。
- 但当前仍保留旧 state 回退，因此文档口径应写成：
  - “后半段 projection-only 主通道已接线，前半段 generation / audit 已开始消费 reflection_memory”
  - “前半段已新增 generation_runtime_input / audit_runtime_input，用于从 projection 恢复运行时输入”
  - 而不是“所有 agent 已彻底只读 projection”

## 2026-03-27 攻击 Agent 目标收口

如果当前主线目标明确为“攻击 agent 具备真实 LLM 决策能力”，那么 `Attack Planning Agent` 的定义需要进一步收紧，不能再只停留在“能生成一个结构化攻击计划”。

### 攻击 Agent 现在应该满足的 5 个条件

1. 具备独立上下文窗口
   - 只读取 `attack_planning_projection`
   - 不直接读取全量 `graph state`
2. 具备真实攻击规划能力
   - 能基于目标服务、审计发现、历史攻击结果和补丁状态做攻击族选择
3. 具备结构化输出能力
   - 稳定输出 `AttackSpecPayload`
   - 同时输出 `AttackDecisionCard` 解释“为什么这样打”
4. 具备多轮重规划能力
   - 能基于上一轮 `AttackResultPayload` 决定 `continue / replan / handoff / stop`
5. 具备与执行平面解耦的边界
   - 不直接输出 shell / docker / 远程执行命令
   - 只把决策交给 `Sandbox Dispatcher`

### 当前实现与目标之间的差距

- 当前已经有：
  - `attack_planning_projection`
  - `memory_handoff`
  - `Sandbox Dispatcher`
  - `LocalSandboxRuntime`
- 当前还没有：
  - 真实的 `Attack Planning LLM Agent`
  - 显式 `AttackDecisionCard`
  - 基于攻击结果的二次规划

所以当前 `attack_executor` 更准确的理解应是：

- 已承接攻击闭环执行壳子
- 但认知层仍待替换为真实 LLM planner

### 推荐的最小 handoff 形态

- 输入：
  - `TargetServiceSpec`
  - `Finding Card`
  - `Patch Card`
  - `Execution Budget`
  - `Sandbox Policy Summary`
- 输出：
  - `AttackSpecPayload`
  - `AttackDecisionCard`
  - 后续可扩展 `AttackLoopDirective`

### 实现顺序建议

1. 保持现有 `workflow_trace` 稳定，不急着改外层节点名
2. 先在 `attack_executor` 内部替换攻击计划生成方式
3. 等真实 LLM 攻击决策稳定后，再视需要把规划与执行拆成两个内部子职责

这样做的好处是：

- 不破坏现有 benchmark 与 API 契约
- 能先把“真实 LLM 决策”这件事做实
- 再逐步把攻击子图拆得更清楚

## 2026-03-27 Attack Planning Agent 增强来源补充说明

如果后续要继续增强真实 LLM 攻击能力，推荐优先增强 `Attack Planning Agent` 的知识来源，而不是简单拉长上下文。

推荐增强来源分成两类：

- `skill / policy layer`
  - 提供攻击面分类、常见误用模式、预算边界、动作约束
- `retrieval / evidence layer`
  - 提供论文摘要、benchmark case、历史 exploit lesson、修补经验

推荐做法：

1. 论文和经验资料先转成知识对象
2. 检索层按目标服务和 attack focus 召回
3. skill 把召回结果组织成 planner 可消费的策略框架
4. `AttackPlanningAgent` 在独立窗口内结合当前 target / finding / patch 状态做决策

不推荐做法：

- 直接把整篇论文或大量原始资料塞进 planner prompt

这样做虽然表面上“信息更多”，但会直接破坏独立上下文窗口的预算与稳定性。
## 2026-03-27 工作流落地补记

当前 MAS 主线中与攻击规划相关的真实运行顺序已经更新为：

1. `audit_agent` 产出审计轮次结论
2. `attack_executor` 构建纯输入 `attack_planning_projection`
3. `AttackPlanningAgent` 基于独立窗口输出 `attack_decision + attack_specs`
4. `LocalSandboxDispatcher` 批准或阻断执行
5. `LocalSandboxRuntime` 执行受限攻击任务
6. `vulnerability_agent` 读取 `attack_decision` card 和 `attack_result_summary` card

当前新增的闭环对象有：

- `AttackDecisionPayload`
- `attack_decision` memory card
- `delivery.attack_loop.attack_decision`

因此当前工作流的准确说法应改为：

- 攻击规划阶段已具备真实 LLM 决策入口
- 漏洞评估 / 修补 / 反思仍以规则与结构化对象为主，尚未全部升级为真实 LLM 专家决策

## 2026-03-27 回归轮工作流补记

当前第 2 轮的真实运行顺序已经进一步更新为：

1. `patch_agent` 生成 `PatchSpec`
2. 系统重部署补丁版本目标服务
3. 构建 `attack-plan-r2` projection
4. `AttackPlanningAgent` 基于补丁信息和上一轮攻击结果输出 `regression_attack_decision + regression_attack_specs`
5. dispatcher / runtime 执行正式回归攻击

因此当前攻击子流程更准确的说法是：

- 第 1 轮：基线攻击规划
- 第 2 轮：结果驱动的回归重规划
## 2026-03-27 漏洞评估工作流补记

当前攻击闭环中的漏洞评估阶段已经更新为：

1. `attack_executor` 完成基线攻击并沉淀攻击工件
2. 系统构建独立 `vulnerability-r1` projection
3. `VulnerabilityEvaluationAgent` 输出基线 `VulnerabilityVerdictPayload`
4. `patch_reflection` 完成补丁版本重部署与回归攻击
5. 系统构建独立 `vulnerability-r2` projection
6. 同一个 `VulnerabilityEvaluationAgent` 输出 `regression_vulnerability_verdict`
7. `reflection_agent` 再消费回归 verdict 与 patch 结果沉淀下一轮优化卡

这条链路的意义在于：

- baseline 与 regression 不再是两套认知逻辑
- 不同 agent 继续保持独立上下文窗口
- verdict 的 memory handoff 可以被 patch / reflection 继续稳定消费

当前下一步主线应保持为：

- 继续完成 `Patch Agent` 的真实 LLM 化
- 补齐 `continue / stop / handoff` 分支控制
- 引入 `artifact summarizer` 稳定压缩 `trace / finding / patch diff`

## 2026-03-27 Patch Agent -> Reflection Agent 补充说明

当前 `patch_agent -> reflection_agent` 的 handoff 已新增一张稳定卡片：

- `card_type = "patch_artifact_summary"`

这张卡片的 `payload` 当前至少包含：

- `patch_id`
- `strategy`
- `summary`
- `next_version`
- `changed_artifact_count`
- `changed_artifact_summaries[*].relative_name`
- `changed_artifact_summaries[*].before_line_count`
- `changed_artifact_summaries[*].after_line_count`
- `changed_artifact_summaries[*].line_delta`
- `changed_artifact_summaries[*].diff_preview`

这样做的目的不是把完整 diff 塞回 prompt，而是让 `reflection_agent` 在独立上下文窗口里也能看见“这轮到底改了哪些核心实现、改动量多大、哪些行最值得继续关注”。

## 2026-03-27 Reflection Agent 输出补充说明

当前 `reflection_agent` 的主输出已稳定为两张卡：

- `reflection`
  - 面向下一轮 generation / audit 的策略调整摘要
  - 可附带 `prompt_changes` 与 `audit_focus`
- `regression_summary`
  - 面向回归轮结果总结
  - 可附带 `residual_risks`、`workspace`

这样做的意义是：

- `patch -> regression -> reflection` 终于不再停留在规则拼接层
- 反思阶段开始具备真实 LLM 决策能力
- 同时继续保留 fallback，不把主链稳定性绑定到外部 LLM 可用性

## 2026-03-27 Reflection Card -> Case Memory 回灌补充说明

当前 `patch_reflection` 的输出已不只进入 `delivery.attack_loop.reflection_cards`，还会进一步沉淀到项目级记忆：

- `case_memory.recent_reflections`
- `delivery.case_memory_summary.reflection_count`

下一次同一 `case_id` 再运行时：

- `generation_agent` 的独立窗口会看到 `card_type = "reflection_memory"`
- `audit_agent` 的独立窗口也会看到 `card_type = "reflection_memory"`
- 当前回灌的关键信息包括：
  - `latest_reflection_summary`
  - `latest_regression_summary`
  - `latest_prompt_changes`
  - `latest_audit_focus`
  - `latest_residual_risks`
- 从 2026-03-29 起，这些信息已开始真实作用于运行时：
  - `generation` 会据此调整候选排序，并在 `design_rationale` 中写入 `[反思回灌]`
  - `audit` 会据此增强 `reasons / key_findings / recommended_changes`
- 同期新增的 `generation_runtime_input / audit_runtime_input` 也开始承载前半段运行时输入恢复，不再只依赖旧 state。
- 其中 `audit_runtime_input.scheme_entries` 现在会显式携带 `proposal_id + scheme`，让审计轮次的方案身份不再隐含绑定到列表顺序。
- `architect` 节点也已开始优先通过 `analyst + generation_runtime_input` 恢复 requirement / parser_confidence，而不是继续把 `state["parsed"]` 当作主输入。
- 需要保持的边界是：
  - 首轮新 `case_id` 运行时，如果还没有历史 `recent_reflections`，窗口里没有 `reflection_memory` 属于正常行为
  - `reflection_memory` 的稳定验证场景应放在同一 `case_id` 的后续运行，而不是首轮执行

当前要明确的边界：

- 已完成的是“跨 run 的项目级记忆回灌”
- 已完成的是 generation / audit 对 `reflection_memory` 的第一版执行层消费
- 尚未完成的是“同一 run 内即时改写 generation / audit prompt”

## 10.8 目标服务模板进入攻击规划窗口（2026-03-27）

当前 `AttackPlanningAgent` 的独立窗口里，`target_service` 已不再只是：

- `service_id`
- `runtime`
- `entrypoint`

而是会进一步带入：

- `template_id / template_label`
- `service_kind / attack_surface_kind`
- `supported_versions`
- `planner_skill_hints / planner_retrieval_hints`
- `deployment_manifest / runtime_profile`

这意味着当前 workflow 已具备：

1. 由模板定义服务边界
2. 由 projection 传递模板知识
3. 由 planner 在独立窗口中显式消费模板 hints

当前仍未完成的是：

- 基于这些 hints 的 retrieval evidence 主链召回
- 更复杂模板族的多态路由

## 10.9 攻击规划检索进入独立窗口（2026-03-27）

当前 `attack_planning_projection` 已不再只挂载通用 `evidence_refs`。

现在实际进入窗口的还包括：

- planner-scoped `evidence_refs`
- `card_type = "attack_planner_evidence"`

这张卡当前会沉淀：

- `planning_mode`
- `query`
- `backend / retrieval_mode`
- `hit_count`
- `applied_filters`

这意味着当前 workflow 已形成：

1. target template / planner hints
2. planner-scoped retrieval
3. evidence card + evidence refs
4. LLM attack planning

当前仍未完成的是：

- 更强的 lesson rerank
- 更细粒度 exploit / benchmark pattern store

## 10.10 Patch Agent 输出口径修正（2026-03-28）

当前需要修正一个旧口径：`Patch Agent` 已不应再写成“纯规则化 patch 方案组装”。

更准确的状态是：

- `PatchPlanningAgent` 已具备真实 LLM 结构化输出入口
- 当前仍保留 fallback，避免把主链稳定性完全绑定到外部 LLM 可用性
- 运行时输出对象仍为稳定 `PatchSpecPayload`，但已扩展出更完整的修补决策字段

当前 `PatchSpecPayload` 除旧字段外，还会追加：

- `rationale`
- `implementation_notes`
- `validation_steps`
- `rollback_notes`

这意味着当前 workflow 中的 Patch Agent 已经开始回答四类问题：

1. 为什么要这样修
2. 需要改哪些核心实现要点
3. 回归时重点验证什么
4. 如果补丁失败如何回滚

当前仍未完成的是：

- 更深的 same-run 自动代码改写
- 生产级 patch 执行器
- 容器级隔离与远程执行平面

## 10.10A Expert Gate 独立认知层（2026-04-05）

当前 workflow 中，`patch_reflection` 已不再从 `vulnerability_verdict` 直接跳到 `PatchPlanningAgent`。

现在更准确的顺序是：

1. 构建独立 `expert_gate_projection`
2. `ExpertGateAgent` 输出 `ExpertGateDecisionPayload`
3. `patch_projection` 显式携带 `expert_gate_decision` card
4. `PatchPlanningAgent` 再基于专家闸门输出修补规划

当前稳定新增的工作流观测点包括：

- `delivery.context_projections.expert_gate`
- `delivery.attack_loop.expert_gate_decision`
- `delivery.attack_loop.rounds[0].expert_gate_decision`
- `delivery.context_projections.patch.cards[*].card_type = "expert_gate_decision"`
- `ExpertGateDecisionPayload.decision_family / decision_family_label`
- `ExpertGateDecisionPayload.route_target / route_target_label`

当前第一版已经打通的，不只是“多一个 expert gate 节点”，还包括：

- `ExpertGateAgent` 会把决策归并到稳定 `decision_family`
- workflow 会把下游目标显式表达为稳定 `route_target`
- `PatchPlanningAgent` 已开始消费这组 typed route 信号，而不只消费自由文本理由
- 当 `route_target = "delivery"` 时，workflow 已不会误进入 patch / regression，而是直接沉淀 follow-up reflection cards
- 当 `route_target = "attack_planning_agent"` 时，workflow 已会执行同轮一次补充攻击重规划、补充攻击执行与补充漏洞评估

当前边界：

- 已完成“独立 Expert Gate 认知层”
- 已完成“Patch Agent 真实消费 Expert Gate 输出与 typed route 第一版”
- 已完成“`attack_planning_agent` same-run 单次补充攻击闭环”
- 尚未完成“完整多分支 expert 子图”与“递归多轮 same-run 自动重试”

## 10.11 Patch Execution 进入闭环（2026-03-29）

当前 workflow 中，`patch_reflection` 已新增一个关键收口动作：在回归轮结束后构建 `patch_execution`，并把它送入 `reflection` 独立窗口。

当前顺序可以更准确地写成：

1. `PatchPlanningAgent` 输出增强后的 `patch_spec`
2. patched target service 重新部署
3. regression attack 规划与执行
4. 生成 `patch_execution`
5. `ReflectionAgent` 同时消费 `patch_spec + patch_execution + patch_artifact_summary`

当前稳定新增的工作流观测点包括：

- `delivery.attack_loop.patch_execution`
- `delivery.attack_loop.rounds[1].patch_execution`
- `delivery.context_projections.reflection.cards[*].card_type = "patch_execution"`

这意味着当前闭环已经从：

- patch planning -> regression -> reflection

推进为：

- patch planning -> patched redeploy -> regression -> patch execution report -> reflection

当前边界仍应继续保持诚实：

- 已完成“补丁执行报告”第一版
- 尚未完成真实代码 patch 应用器、生产级回滚流水线与远程 patch release 验证

## 10.12 Patch Execution 第二阶段进入独立窗口（2026-03-29）

- 当前 `reflection` 窗口里消费的 `patch_execution` 已不再只是：
  - `validation_steps`
  - `validation_results`
  - `diff_preview`
- 现在还会进一步带入：
  - `validation_summary`
  - `supporting_artifact_summaries`
  - `artifact_inventory`
- 这使得 `ReflectionAgent` 在独立上下文窗口里能更明确地区分：
  - 哪一步验证通过了
  - 哪一步被跳过了
  - 哪些工件是代码变更
  - 哪些工件是部署/运行支撑工件

## 10.13 后端完整架构工作流重排（2026-03-29）

当前工作流需要从“节点串联视角”升级到“控制平面 + 总线 + 执行平面 + 回放平面”的视角。

当前推荐的主流程解释应改为：

1. `Agent Control Plane`
   - 负责驱动 `analyst -> context_builder -> architect -> audit -> engineer -> attack_loop -> delivery`
2. `Context And Memory Bus`
   - 负责为每个 agent 构建独立 projection，并在阶段之间传递 handoff / artifact / evidence / replay snapshot
3. `Sandbox Execution Plane`
   - 负责 `target_deploy / attack_execute / patch_apply / rollback / regression_replay`
4. `Persistence Audit Replay Plane`
   - 负责把上述阶段沉淀成 timeline、审计轨迹与可回放快照

这意味着今后不应再只按“哪个 agent 还没做完”描述工作流，而要先问：

- 控制平面有没有稳定
- 上下文总线有没有稳定
- 执行平面有没有统一协议
- 回放平面有没有事件化沉淀

## 10.14 当前架构主线的推荐统一表述

从本轮开始，后端主线建议统一表述为：

- LangGraph 是唯一 orchestration 主线
- 各 agent 必须拥有独立上下文窗口
- agent 间信息传递依赖 `projection + memory_handoff + artifact/evidence refs`
- sandbox 当前仍是演示级、本地受限进程执行面
- 后续后端第一优先级是补齐完整控制平面、上下文总线、执行平面和回放平面

## 10.15 后端架构摘要已进入主流程返回体（2026-03-29）

当前工作流不只是在文档层面定义四平面，第一批架构摘要已经真正进入 `delivery`。

当前新增的稳定返回对象包括：

- `delivery.backend_architecture.control_plane`
- `delivery.backend_architecture.memory_bus`
- `delivery.backend_architecture.execution_plane`
- `delivery.backend_architecture.replay_plane`

当前主链中的来源关系为：

1. `ControlPlaneBuilder`
   - 汇总 workflow trace、projection、handoff
2. `ContextBusBuilder`
   - 汇总独立上下文窗口与 handoff 总线
3. `ExecutionPlaneBuilder`
   - 汇总 dispatcher、runtime、patch execution 的执行摘要
4. `CaseTimelineService.record_run(...)`
   - 写入 run 级 replay snapshot，并回传 `timeline_summary + latest_snapshot`

这一步的意义是：

- 当前“后端完整架构”不再只是 TODO 叙事
- 前端和联调层已经可以围绕统一摘要对象观察四平面
- replay plane 也开始具备最小落盘起点，而不是只存在运行时内存

当前仍需保持诚实的边界：

- 这些字段是 additive architecture summary
- 当前 replay snapshot 落在 `.cache/case_timelines/`
- 当前仍不是完整生产级 control plane / execution center / replay center

同时，`CaseTimelineService` 已开始把 replay 从“只有 snapshot”推进到“snapshot + cognition milestones”：

- `attack_decision`
- `vulnerability_verdict`
- `patch_plan`
- `patch_execution`
- `reflection_output`

这批事件当前的定位是：

- 服务回放、联调、审计说明与前端透明化
- 不是完整企业级 event lake，也不是细粒度全量 trace 替代

## 10.16 Control Plane 合同如何映射到工作流（2026-03-29）

当前 `delivery.backend_architecture.control_plane` 已开始把工作流中的阶段关系显式对象化。

对主流程来说，最重要的新增口径有三条：

1. `invocations[*].contract`
   - 负责说明阶段依赖、进入条件、成功出口、失败动作与下一跳
2. `checkpoints[*].input_refs / output_refs`
   - 负责说明每个阶段以哪些稳定引用进入、以哪些稳定引用退出
3. `results[*].decision_signal`
   - 负责把关键控制信号显式暴露出来，而不是埋在内部状态里

当前最有代表性的阶段是 `attack_executor`：

- 当前会显式声明：
  - `failure_action = "skip_dispatch_or_handoff"`
  - `next_stages = ["vulnerability_evaluation"]`
- 当前还会在结果层显式带出：
  - `decision_signal = execute / handoff_to_vulnerability / stop`

这意味着当前 workflow 里“规划器真实控制执行流”已经不只是 `attack_loop` 里的业务字段，也开始进入 control plane 合同层。

## 10.17 Context Bus Typed Family 如何映射到工作流（2026-03-29）

当前 `delivery.backend_architecture.memory_bus` 已不再只回答：

- 一共有多少 projection
- 一共有多少 handoff

现在它还会回答：

1. 每个 agent 窗口主要承载什么 family 的记忆
2. 每个 handoff 实际上传了什么 family 的 cards
3. replay 时该从哪些 projection / handoff / lineage refs 回查

当前 workflow 中新增的关键观察口径包括：

- `windows[*].window_ref`
- `windows[*].card_family_counts`
- `handoffs[*].projection_ref`
- `typed_families[*]`
- `replay_snapshot_card.typed_family_counts`

这一步的意义是：

- 让“独立上下文窗口”从抽象原则推进到可回放、可统计、可解释的总线对象
- 让结构化传递不再只是“几段通用 JSON”，而是开始形成稳定 typed family

当前边界仍需保持诚实：

- family 目前是第一版摘要分类，不是完整 typed card registry
- replay plane 当前仍是本地 `.cache/case_timelines/` 起点
# 2026-04-05 Expert Gate 有限 Re-Gate 第一版

- 当前 `patch_reflection` 的真实顺序已经扩展为：
  - `expert_gate`
  - 若命中 `attack_planning_agent`：`retry attack -> retry vulnerability -> second expert gate`
  - 若二次 gate 命中 `delivery`：写入 follow-up reflection cards 并观察收口
  - 若二次 gate 命中 `patch_agent`：继续进入 patch flow 与 regression
- 当前稳定输出新增：
  - `delivery.context_projections.expert_gate_retry`
  - `delivery.attack_loop.retry_expert_gate_decision`
  - `delivery.attack_loop.rounds[1].expert_gate_decision`
- 当前稳定状态新增：
  - `baseline_executed_retry_executed_delivery_observation`
  - `baseline_executed_retry_executed_regression_executed`
  - `baseline_executed_retry_executed_retry_capped`
- 当前仍未完成：
  - 递归多轮 expert 子图
  - 任意深度 same-run re-gate
  - 生产级远程攻击执行平面
