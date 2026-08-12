# 项目级记忆（Case Memory）设计

最后更新：2026-03-27
状态：active
适用范围：后续 `src/cipher_genius/memory/`、`src/cipher_genius/api/schemas.py`、`src/cipher_genius/core/langgraph_mas.py`、前端工作台项目持续状态

## 1. 目标

Case Memory 要解决的不是“让模型记住聊天记录”，而是“让系统记住项目状态”。

本文回答 5 个问题：

1. 为什么当前 `run_id` 不够
2. Case Memory 和聊天历史有什么区别
3. 应该存哪些对象，而不是把所有文本都塞进去
4. 它如何和检索、审计、交付主线配合
5. 适合按什么顺序落地

## 2. 当前现状

当前 MAS 请求/响应里已经有：

- `run_id`
  - 用于一次执行与取消控制

当前还没有稳定进入主线的：

- `case_id`
- case 级持久状态
- 可跨轮继承的约束与整改轨迹

所以目前系统更接近：

- 记住了一次运行

而不是：

- 记住了一个项目

## 3. 为什么不能把聊天历史当成项目记忆

把聊天历史直接当作记忆，听起来简单，但在企业交付里通常不够用。原因有 4 个：

### 3.1 聊天历史是叙事文本，不是项目状态

聊天历史通常只适合“回看说过什么”，不适合稳定表示：

- 已确认约束
- 被拒方案
- 阻断项
- 当前推荐
- 待人工确认项

### 3.2 聊天历史不利于结构化读取

系统下一轮真正需要的不是整段对话，而是：

- 哪些条件已经确定
- 哪些问题已经回答
- 哪些建议已经被否
- 上一轮为什么没过审

这些都更适合结构化对象，而不是连续消息。

### 3.3 聊天历史很难做筛选和复盘

如果没有结构化字段，后续很难问出这类问题：

- 上次被拒的是哪一种方案
- 哪些整改已经做了
- 哪些风险项仍未关闭

### 3.4 聊天历史容易把无关噪声一起带进来

企业项目里经常有临时讨论、解释性话语、非关键信息。把它们原样塞进下一轮，反而会污染状态。

## 4. Case Memory 应该存什么

Case Memory 的核心原则是：

- 记住项目状态
- 不复制整段闲聊
- 优先保存后续决策真正要用的信息

建议至少包含以下几类对象。

### 4.1 Case 主对象

- `case_id`
- `created_at`
- `updated_at`
- `scenario`
- `requirement_summary`
- `status`

### 4.2 约束与澄清对象

- `confirmed_constraints`
- `clarification_answers`
- `open_questions`
- `blocking_items`

### 4.3 决策轨迹对象

- `candidate_history`
- `rejected_options`
- `selected_option`
- `decision_log`

### 4.4 审计轨迹对象

- `audit_findings`
- `risk_scores`
- `compliance_scores`
- `remediation_actions`
- `remediation_status`

### 4.5 人工确认对象

- `required_human_checks`
- `human_approvals`
- `manual_overrides`

## 5. 推荐的数据边界

### 5.1 应该进入 Case Memory 的内容

- 已确认的项目约束
- 上一轮审计结论
- 被明确拒绝的候选
- 已经执行过的整改动作
- 当前推荐方向
- 仍待人工决策的点

### 5.2 不应该原样进入 Case Memory 的内容

- 全量聊天记录
- 大段中间推理文本
- 未结构化的原始模型输出
- 没有确认过的随机猜测

### 5.3 更合理的做法

不是“保存一切”，而是：

- 保存结构化状态
- 必要时补最小可回溯摘要
- 让原始运行日志继续留在运行链或调试链中

## 6. 推荐 schema 方向

下面是一份更贴近项目主线的建议结构：

```json
{
  "case_id": "case-buildtrust-2026-001",
  "scenario": "construction",
  "status": "in_progress",
  "requirement_summary": "面向中国企业的研发数据平台密码改造项目",
  "confirmed_constraints": [
    "需满足国产化要求",
    "需保留审计留痕",
    "需要支持静态与传输加密"
  ],
  "clarification_answers": [
    {
      "question": "是否必须使用硬件密钥托管",
      "answer": "是"
    }
  ],
  "blocking_items": [
    "密钥轮换周期尚未明确"
  ],
  "rejected_options": [
    {
      "proposal_id": "proposal-2",
      "reason": "风险得分过高，且未满足后量子要求"
    }
  ],
  "selected_option": "proposal-4",
  "audit_findings": [
    "轮换策略不完整",
    "缺少明确托管边界"
  ],
  "remediation_actions": [
    "补齐轮换周期",
    "补充 HSM/KMS 边界说明"
  ],
  "required_human_checks": [
    "确认企业内部是否允许云托管密钥服务"
  ]
}
```

## 7. 它和检索、交付的关系

Case Memory 不是独立岛。它和另外两条主线要配合：

### 7.1 和检索的关系

检索负责回答：

- 外部或企业知识上，什么是合理依据

Case Memory 负责回答：

- 这个项目之前已经确认过什么

前者是“通用与企业知识”，后者是“本项目状态”，两者不能互相替代。

### 7.2 和交付的关系

最终报告里，很多企业真正关心的是：

- 为什么这个方案现在过了
- 为什么前几个没过
- 哪些整改已经完成

这些问题只有 Case Memory 记录得足够清楚，交付层才能稳定输出决策轨迹。

## 8. 不同 Agent 的独立上下文窗口

Case Memory 后续不应只回答“项目状态存哪里”，还要回答“不同 agent 如何只拿自己该看的那一部分”。

必须明确：

- Case Memory 不是一个给所有 agent 共享的大文本仓库
- Case Memory 应支持按角色投影上下文
- 每个 agent 都应有独立上下文窗口，而不是共享原始长历史

推荐的 role-aware context projection 如下：

- `Generation Agent`
  - 读取：`requirement_summary`、`confirmed_constraints`、`clarification_answers`、最近 `Reflection Card`
- `Audit Agent`
  - 读取：当前 `ProposalSpec`、相关 `EvidencePack`、阻断项与已确认约束
- `Attack Planning Agent`
  - 读取：`TargetServiceSpec`、审计发现摘要、攻击面卡片、版本号
- `Vulnerability Evaluation Agent`
  - 读取：`AttackResultSpec`、高优先级 findings、必要 artifact refs
- `Patch Agent`
  - 读取：`VulnerabilityVerdictSpec`、受影响组件、最近补丁历史
- `Reflection Agent`
  - 读取：轮次摘要、裁决结论、补丁效果、失败模式

这样做的核心不是“省 token”这么简单，而是：

- 让每个 agent 的判断边界更清晰
- 让角色之间的记忆传递更可控
- 让后续评测能准确归因“这个 agent 到底基于什么做了决策”

## 9. Agent 间的记忆传递应该长什么样

后续真正要打磨的不是“更长的共享 prompt”，而是稳定的 memory handoff。

建议把 agent 间传递收口成下面几类对象：

- `Constraint Card`
  - 已确认约束、强制边界、仍待确认问题
- `Decision Card`
  - 当前轮选了什么、拒了什么、为什么
- `Finding Card`
  - 攻击或审计发现了什么、严重度、证据引用
- `Patch Card`
  - 修了什么、影响哪些工件、对应哪个版本
- `Reflection Card`
  - 下一轮生成 / 审计 / 攻击策略要如何改
- `Artifact Ref`
  - 指向代码工件、trace、metrics、finding、diff、报告片段

建议的分层原则：

- graph state 只放卡片摘要和引用
- 大日志、代码全文、trace 原文留在 artifact store
- Case Memory 保留跨轮稳定状态
- 单轮运行的临时推理不默认进入长期记忆

## 10. 推荐的 Context Projection 结构

为了让不同 agent 拿到“刚好够用”的上下文，建议把投影结果统一收口成一个轻量对象，而不是每个角色各自拼 prompt。

推荐结构：

```json
{
  "agent_id": "generation_agent",
  "case_id": "case-buildtrust-2026-001",
  "run_id": "run-2026-03-26-001",
  "round_id": "round-2",
  "window_version": "v1",
  "objective": "生成下一版候选方案",
  "constraints": [],
  "cards": [],
  "artifact_refs": [],
  "evidence_refs": [],
  "token_budget_hint": 6000
}
```

字段建议解释：

- `agent_id`
  - 标识这是给哪个 agent 的窗口
- `objective`
  - 本轮单一目标，避免一个窗口里同时塞太多任务
- `constraints`
  - 本轮必须遵守的强约束
- `cards`
  - 经压缩后的结构化记忆卡片
- `artifact_refs`
  - 指向代码、trace、metrics、diff、报告片段
- `evidence_refs`
  - 指向 EvidencePack 中的证据块
- `token_budget_hint`
  - 给调度层一个软预算提示，方便后续上下文裁剪

## 11. 推荐的 Card Schema

建议所有 handoff card 至少共享一层统一包络，便于落库存、筛选和前端展示：

```json
{
  "card_id": "card-find-001",
  "card_type": "finding",
  "case_id": "case-buildtrust-2026-001",
  "run_id": "run-2026-03-26-001",
  "round_id": "round-2",
  "version_id": "svc-v2",
  "source_agent": "vulnerability_evaluation_agent",
  "priority": "high",
  "summary": "错误处理泄露内部细节",
  "payload": {},
  "artifact_refs": [],
  "evidence_refs": [],
  "created_at": "2026-03-26T10:00:00Z"
}
```

### 11.1 Constraint Card

用途：

- 传递“必须遵守什么”

推荐 payload：

```json
{
  "constraint_kind": "security_requirement",
  "value": "必须支持后量子迁移",
  "confirmed": true,
  "source": "human_confirmed"
}
```

### 11.2 Decision Card

用途：

- 传递“选了什么 / 拒了什么 / 为什么”

推荐 payload：

```json
{
  "selected_proposal": "proposal-3",
  "rejected_proposals": ["proposal-1", "proposal-2"],
  "reason": "proposal-3 在合规与后量子要求之间平衡最好"
}
```

### 11.3 Finding Card

用途：

- 传递审计发现或攻击发现

推荐 payload：

```json
{
  "finding_kind": "vulnerability",
  "severity": "high",
  "title": "错误处理泄露密钥上下文",
  "affected_components": ["encrypt_api", "error_handler"],
  "exploitability": "moderate"
}
```

### 11.4 Patch Card

用途：

- 传递补丁动作与版本影响

推荐 payload：

```json
{
  "patch_id": "patch-001",
  "strategy": "hardening-and-validation",
  "changed_artifacts": ["implementation.py", "service_runtime.py"],
  "next_version": "v2"
}
```

### 11.5 Reflection Card

用途：

- 传递下一轮提示词与策略改进

推荐 payload：

```json
{
  "failure_pattern": "生成阶段低估了接口错误处理风险",
  "next_round_hint": "下一轮 generation 必须显式说明错误处理边界与密钥治理策略",
  "applies_to_agents": ["generation_agent", "audit_agent"]
}
```

## 12. 每个 Agent 默认该看什么

建议把“读取范围”直接做成产品和工程上的硬限制，而不是靠提示词提醒。

### 12.1 Generation Agent

- 读取：
  - `Constraint Card`
  - 最近 1 到 3 张 `Reflection Card`
  - 当前 `EvidencePack` 摘要
  - 最近一轮 `Decision Card`
- 不读取：
  - 原始攻击 trace 全文
  - 全量 discussion log

### 12.2 Audit Agent

- 读取：
  - 当前 `ProposalSpec`
  - `Constraint Card`
  - `EvidencePack`
  - 最近相关 `Finding Card`
- 不读取：
  - 无关历史候选全文
  - 大段 patch diff

### 12.3 Attack Planning Agent

- 读取：
  - `TargetServiceSpec`
  - `Finding Card`
  - 当前风险重点
  - 版本信息
- 不读取：
  - generation 过程中的冗长解释文本

### 12.4 Vulnerability Evaluation Agent

- 读取：
  - `AttackResultSpec`
  - `artifact_refs`
  - 关键 `EvidencePack` 引用
- 不读取：
  - 无关的历史澄清记录

### 12.5 Patch Agent

- 读取：
  - `VulnerabilityVerdictSpec`
  - `Finding Card`
  - 最近 `Patch Card`
  - 受影响工件引用
- 不读取：
  - 无关候选比较表全文

### 12.6 Reflection Agent

- 读取：
  - `Decision Card`
  - `Finding Card`
  - `Patch Card`
  - 当前轮结果摘要
- 不读取：
  - 原始攻击 metrics 全量采样点

## 13. 调度层需要负责什么

如果要让独立上下文窗口真正成立，调度层至少要承担这些职责：

- 为每个 agent 构造 context projection
- 控制窗口大小，不够用时按优先级裁剪
- 从 artifact store 拉摘要，而不是直接拉原文
- 把 agent 输出压缩成 card，再交给下一阶段
- 区分“本轮短期状态”和“跨轮长期记忆”

这意味着后续真正需要新增的不是更多 prompt，而是：

- `context projection builder`
- `card serializer`
- `artifact summarizer`
- `memory handoff policy`

## 14. 本文对 TODO 的直接影响

如果后续主线继续推进，多 Agent 记忆治理应至少拆成三条独立任务：

- 独立上下文窗口设计
- role-aware context projection
- memory handoff / card schema 稳定化

否则系统会很快退化成：

- 多节点
- 多消息
- 但本质上还是共享长上下文的单体 prompt chain

## 2026-03-26 Schema 落地补记

- 当前 `src/cipher_genius/api/schemas.py` 已落地：
  - `ContextProjectionPayload`
  - `MemoryHandoffPayload`
  - `MemoryCardPayload`
  - `ArtifactRefPayload`
  - `EvidenceRefPayload`
  - `ContextConstraintPayload`
- 这意味着“独立上下文窗口 + 结构化记忆传递”已经不再只是文档原则，而是有了第一版稳定数据对象。
- 当前尚未完成的部分是：
  - 更完整的 card serializer
  - artifact summarizer
  - 所有 agent 彻底改成只消费 projection

## 2026-03-26 运行时补记

- `langgraph_mas.py` 已把第一版 role-aware projection builder 接入主流程
- 当前已落地的独立窗口：
  - `generation_agent`
  - `audit_agent`
  - `attack_planning_agent`
  - `vulnerability_agent`
  - `patch_agent`
  - `reflection_agent`
- 当前已落地的结构化 handoff：
  - `context_builder -> generation_agent`
  - `generation_agent -> audit_agent`
  - `audit_agent -> attack_planning_agent`
  - `attack_planning_agent -> vulnerability_agent`
  - `vulnerability_agent -> patch_agent`
  - `patch_agent -> reflection_agent`
- 这些对象已通过 `delivery.context_projections` 与 `delivery.memory_handoffs` 暴露，便于前端可视化、联调和后续 memory bus 收口

## 8. 推荐接入主链的方式

Case Memory 更适合这样进入主链：

1. 请求里显式出现 `case_id`
2. 执行开始时按 `case_id` 加载项目状态
3. `analyst` 先吸收已有约束和未解决问题
4. `auditor` 读到历史整改与未关闭风险
5. `delivery` 输出新的决策日志和状态更新
6. 结束时回写 Case Memory

这样它才是真正的“项目持续状态”，而不是执行后顺手存个备份。

## 9. 为什么它比“把上一次结果直接拼进提示词”更强

把上一次结果直接拼进提示词，有 3 个常见问题：

- 信息冗余，很快变成长上下文噪声
- 状态边界不清，已确认和未确认内容混在一起
- 很难做程序级筛选、比较和验证

Case Memory 的优势在于：

- 状态结构清楚
- 便于跨轮继承
- 便于做决策轨迹展示
- 便于评测“澄清收敛”和“整改收敛”

## 10. 推荐落地顺序

### 阶段 1：先定义对象，不急着上复杂存储

先做：

- `case_id`
- `decision_log`
- `confirmed_constraints`
- `blocking_items`
- `rejected_options`

这一阶段哪怕先存本地或轻量存储，也比完全没有项目状态更强。

### 阶段 2：接到 LangGraph 主线

让主链开始：

- 读 case memory
- 写 case memory
- 在 `delivery` 里输出结构化决策轨迹

### 阶段 3：和检索、评测闭环打通

后续再补：

- 案例级相似检索
- 澄清收敛率
- 整改收敛率
- golden case consistency

## 11. 验证与回归

Case Memory 落地后，至少要验证：

- 同一个 `case_id` 第二轮是否能继承前一轮约束
- 已回答的澄清问题是否不会重复提问
- 被拒绝的方案是否会在下一轮被正确回避或修正
- 前端是否能回显跨轮的审计与整改轨迹
- 交付物是否能说明“为什么最终选这个方案”

## 12. 关联代码与文档

- `src/cipher_genius/api/schemas.py`
- `src/cipher_genius/api/main.py`
- `src/cipher_genius/core/langgraph_mas.py`
- `frontend/src/features/mas/README.md`
- `docs/modules/retrieval_knowledge_base.md`
- `docs/modules/mas_workflow.md`
- `REMAIN.md`
- `TODO_VIBING.md`


## 13. ??????2026-03-24?

???????????

- `MASRequest` / `SkillExecuteRequest` ?? `case_id`
- `MASResponse` ?? `case_id`?`case_memory`
- `AnalystReportPayload` ?? `case_context`
- `LangGraphMASService` ??????????? Case Memory
- `GET /api/v1/cases/{case_id}` ?????????
- ????????????????????

?????

- ????? `.cache/case_memory/` JSON ???
- ?????? `use_langgraph=true`
- ????????????????????
## 14. 第二阶段补充：项目切换入口（2026-03-24）

在第一阶段持久化 `case_memory` 之后，当前又补齐了“项目切换入口”这一层，让 Case Memory 能真正进入前端主工作流：

- 新增 `GET /api/v1/cases`
  - 返回最近项目的轻量 summary 列表
  - 供 React 工作台做“切换项目 / 继续项目”
- React 工作台顶部新增“当前项目”卡片
  - 展示 `case_id`、状态、最近合规分、最近风险分、阻塞数、拒绝方案数与决策记录数
  - 可以直接新建项目、切换已有项目，或手动输入 `case_id`
- React 工作台当前还会展开完整 case 快照
  - 展示已确认约束、待确认问题、阻塞项、拒绝方案与决策轨迹
- 新增 `DELETE /api/v1/cases/{case_id}`
  - 用于删除本地持久化的项目快照，清理无效项目线程与演示数据
- 报告页新增“项目连续性”面板
  - 明确当前交付结果属于哪个项目线程

这一步的意义是：

- 不再让 `case_id` 只存在于接口返回里
- 不再要求用户记住并手工复制粘贴 `case_id`
- 让“继续整改”成为工作台里的显式业务动作，而不是隐含约定

## 15. 敏感信息治理补充（2026-03-25）

Case Memory 不只是“项目连续性对象”，也通常是企业敏感信息对象。原因在于它会持续累积：

- 企业需求摘要
- 被拒方案与拒绝原因
- 合规/风险分数
- 阻塞项、待确认问题与整改轨迹
- 人工决策痕迹

因此当前补充了两条最低限度治理约束：

- 前端工作台在“当前项目”卡片中显式提示 case 快照可能包含企业敏感信息
- `DELETE /api/v1/cases/{case_id}` 继续作为演示数据与无效项目线程的快速清理入口

这一步的目标不是把敏感信息治理做完，而是避免把 case 当成普通聊天历史随意传播或打包外发。

## 2026-03-26 为什么这里优先用 JSON，而不是共享长 Prompt

- 推荐的传递方式不是“上一个 agent 输出一大段自然语言，下一个 agent 原样继续拼接”。
- 更合适的方式是：`JSON schema + 摘要文本 + 工件引用`。

这样做是因为共享长 prompt 很快会带来：

- 上下文膨胀
- 信息噪声累积
- 状态边界不清
- 难以可视化
- 难以回放和调试

因此这里说的“靠 JSON 传递”，本质上是分三层：

- `ContextProjectionPayload`
  - 定义单个 agent 的最小可见窗口
- `MemoryHandoffPayload`
  - 定义 agent 间的结构化交接包
- `MemoryCardPayload`
  - 定义可沉淀、可压缩、可跨轮复用的记忆单元
- `ArtifactRefPayload / EvidenceRefPayload`
  - 定义大对象的外部引用，而不是把大内容直接带进窗口

当前主线又补了一层更稳定的 card 合同提示：

- `payload.typed_contract`
  - 表达 card 属于什么 family、什么 contract version、对应什么 runtime stage
- `payload.typed_contract_ref`
  - 给 projection-only 恢复逻辑与 replay 索引一个稳定键
- `payload.ref_lookup_hint`
  - 告诉下游窗口与回放层，摘要不足时应该优先从哪些 artifact / evidence / replay 索引回查

这意味着后续真正需要持续打磨的不是“更会写 prompt”，而是：

- handoff schema 是否稳定
- card 压缩是否足够好
- artifact summarizer 是否能把大对象压成 agent 可消费摘要
- 调度层是否能保证不同 agent 只看到各自该看的那一部分

## 2026-03-26 Memory Handoff 示例包

下面给出一个适合前端展示、运行时联调和答辩说明的最小示例。

### 示例 1：`generation_agent` 的窗口对象

```json
{
  "agent_id": "generation_agent",
  "case_id": "case-buildtrust-001",
  "run_id": "run-001",
  "round_id": "generation-r1",
  "window_version": "v1",
  "objective": "结合企业知识、项目级记忆与约束条件生成候选加密方案。",
  "constraints": [
    {
      "constraint_id": "domain-1",
      "constraint_kind": "domain",
      "value": "业务场景：建筑工程可信交付",
      "priority": "high"
    },
    {
      "constraint_id": "quantum-safe-1",
      "constraint_kind": "quantum_safe",
      "value": "后量子安全要求：是",
      "priority": "high"
    }
  ],
  "cards": [
    {
      "card_id": "card-case-memory-001",
      "card_type": "case_memory",
      "summary": "已有一次历史拒绝记录，本轮需优先保证审计留痕。"
    },
    {
      "card_id": "card-analyst-001",
      "card_type": "analyst_summary",
      "summary": "用户面向中国企业，交付语言默认中文。"
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
      "doc_id": "doc-standard-001",
      "chunk_id": "chunk-07",
      "title": "后量子迁移规范摘要"
    }
  ],
  "token_budget_hint": 4600
}
```

### 示例 2：`patch_agent` 的交接包

```json
{
  "handoff_id": "handoff-run-001-patch",
  "from_agent": "vulnerability_agent",
  "to_agent": "patch_agent",
  "case_id": "case-buildtrust-001",
  "run_id": "run-001",
  "round_id": "patch-r1",
  "objective": "将漏洞裁决、受影响工件与修补目标投影到修补 Agent。",
  "status": "ready",
  "cards": [
    {
      "card_id": "card-verdict-001",
      "card_type": "vulnerability_verdict",
      "summary": "错误处理暴露内部路径，接口边界缺少限制，当前严重度为中高。"
    },
    {
      "card_id": "card-audit-round-001",
      "card_type": "audit_decision",
      "summary": "补丁必须同时满足错误处理收口、审计留痕和回归验证。"
    }
  ],
  "artifact_refs": [
    {
      "artifact_id": "svc-run-001",
      "artifact_type": "target_service",
      "title": "待修补服务"
    },
    {
      "artifact_id": "trace-attack-001",
      "artifact_type": "attack_artifact",
      "title": "攻击 trace"
    }
  ],
  "projection": {
    "agent_id": "patch_agent",
    "objective": "基于漏洞裁决、攻击工件和审计结论生成修补与回归方案。"
  }
}
```

### 示例 3：前端展示时建议的最小视角

如果前端需要把 handoff 做成流程透明化面板，最小可展示字段建议是：

- `from_agent`
- `to_agent`
- `objective`
- `cards[*].card_type`
- `cards[*].summary`
- `artifact_refs[*].artifact_type`
- `artifact_refs[*].title`

这样既能看清“谁向谁传了什么”，又不会把全量日志和大文件直接塞进页面。

## 2026-03-30 Typed Contract / Ref Lookup 补记

当前 `generation_runtime_input` 与 `audit_runtime_input` 已开始稳定带出：

- `payload.typed_contract`
- `payload.typed_contract_ref`
- `payload.ref_lookup_hint`

这一步的直接作用是：

- 前半段 `generation / audit` 不再只能靠固定 `card_type` 名称恢复输入
- 当摘要过薄时，下游 agent 可以优先按 `artifact_refs / evidence_refs / replay_index_ref` 做受控回查
- memory bus 可以把 family 摘要继续推进到 contract 摘要，而不是只统计大类数量

## 2026-03-27 项目级反思回灌补记

当前 Case Memory 已不只保存约束、阻塞项和决策轨迹，也开始沉淀反思结果：

- `CaseMemoryPayload.recent_reflections`
- `CaseMemorySummaryPayload.reflection_count`

当前第一版运行时接线如下：

1. `ReflectionAgent` 生成 `delivery.attack_loop.reflection_cards`
2. 主线将最新反思压缩为项目级记忆对象
3. 写入 `case_memory.recent_reflections`
4. 下一次同一 `case_id` 再运行时，将最近反思投影为：
   - `delivery.context_projections.generation.cards[*].card_type = "reflection_memory"`
   - `delivery.context_projections.audit.cards[*].card_type = "reflection_memory"`

当前常见的反思记忆字段包括：

- `reflection_summary`
- `regression_summary`
- `prompt_changes`
- `audit_focus`
- `residual_risks`
- `changed_artifacts`
- `next_version`

### 为什么当前是跨 run 回灌，而不是同 run 回灌

原因不是“设计上不想做”，而是当前主线执行时序决定的：

- `generation_projection` 和 `audit_projection` 会在本轮前半段先构建
- `reflection_cards` 会在本轮后半段才生成

因此当前最准确的实现口径是：

- 本轮反思结果会写入 `case_memory`
- 下一次同 `case_id` 运行时，`generation / audit` 才会看到这些 `reflection_memory`

### 当前推荐 JSON 形态

```json
{
  "case_id": "case-buildtrust-2026-001",
  "recent_reflections": [
    {
      "run_id": "run-2026-03-27-001",
      "reflection_summary": "上一轮对错误处理边界描述不足，导致攻击面暴露。",
      "regression_summary": "补丁后高危问题收敛，但仍需加强审计留痕校验。",
      "prompt_changes": [
        "generation 阶段必须显式说明错误处理和密钥托管边界"
      ],
      "audit_focus": [
        "优先核查接口错误返回是否泄露内部路径"
      ],
      "residual_risks": [
        "回归轮仍需补充异常路径覆盖"
      ]
    }
  ]
}
```

这一步的意义不是“多存一个字段”，而是把反思结果从单轮 delivery 提升为项目级连续性资产。
