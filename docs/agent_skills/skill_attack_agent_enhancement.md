# Skill: Attack Agent Enhancement（攻击 Agent 知识增强）

## When To Use

- 你要增强 `AttackPlanningAgent` 的真实 LLM 决策质量
- 你要把攻击相关论文、案例、benchmark 或策略知识接入主链
- 你要避免“把原始论文长文本直接塞进 prompt”

## Goal

把攻击 agent 的增强收口为两层，而不是一坨大上下文：

1. `skill / policy layer`
   - 攻击面分类
   - 常见误用模式
   - 预算边界
   - 动作约束
2. `retrieval / evidence layer`
   - 论文摘要
   - benchmark case
   - 历史 exploit lesson
   - 修补经验

## Non-Goals

- 不直接定义生产级攻击执行器
- 不把论文全文直接塞进 `attack_planning_projection`
- 不把这个 skill 当成运行时 `Skill V2` manifest

## Key Files

- `src/cipher_genius/core/attack_planning_agent.py`
- `src/cipher_genius/core/langgraph_mas.py`
- `src/cipher_genius/api/schemas.py`
- `src/cipher_genius/retrieval/service.py`
- `docs/modules/backend_execution_architecture.md`
- `docs/modules/mas_workflow.md`
- `docs/modules/target_service_templates.md`

## Recommended Change Route

1. 先明确要增强的是哪一层：
   - planner 策略知识
   - 攻击经验证据
2. 把资料转成可检索对象，而不是原文拼接
3. 让检索层按 `target service + attack focus + patch state` 召回
4. 再让 `AttackPlanningAgent` 消费压缩后的策略卡和证据卡

## Recommended Knowledge Shapes

### 1. Strategy Knowledge

适合沉淀为 skill / policy：

- 攻击面 taxonomy
- 密码部署误用 checklist
- 错误处理 / 密钥托管 / 接口边界 / 轮换策略检查框架
- planner 的允许动作与风险边界

### 2. Evidence Knowledge

适合沉淀为 retrieval object：

- 论文摘要卡
- benchmark failure pattern
- exploitability judgment lesson
- patch / regression lesson

## Recommended Retrieval Inputs

增强 attack agent 时，优先检索这些输入：

- `TargetServiceSpec`
- `AuditFindingSpec`
- `AttackDecisionPayload`
- `PatchSpec`
- `reflection_memory`

这意味着 planner 不是只看“当前服务长什么样”，而是还要看：

- 上一轮为什么这么打
- 上一轮哪里失败
- patch 后该优先回归什么

## Recommended Output Discipline

增强后的 `AttackPlanningAgent` 仍应保持当前结构化输出边界：

- `AttackDecisionPayload`
- `AttackSpecPayload[]`
- decision / finding / patch 相关 memory card

不要因为知识增强而回退成：

- 大段散文决策
- 不可测试的 prompt 输出

## Common Pitfalls

- 把论文全文直接塞进窗口，导致上下文预算爆炸
- 把 skill 写成自然语言建议集合，没有稳定结构
- 让 planner 直接依赖 runtime 原始日志，而不是先过 summarizer
- 增强后忘记同步 benchmark 与 API 文档口径

## Verification

- `AttackPlanningAgent` 的输出是否仍保持 `AttackDecisionPayload + AttackSpecPayload[]`
- planner 是否能说明使用了哪类策略知识或证据经验
- 增强后是否仍保持独立上下文窗口预算可控
- benchmark / 回归测试是否仍可复现

## Documentation Sync

如果这类增强进入代码实现，至少同步检查：

- `README.md`
- `QUICK_START_V3.md`
- `docs/TECHNICAL_DOCUMENTATION.md`
- `DOC_INDEX.md`
- `docs/modules/backend_execution_architecture.md`
- `docs/modules/mas_workflow.md`
- `docs/modules/target_service_templates.md`

## 2026-03-27 增量接线状态

- 当前已落地的第一层增强是 `template-aware planner_knowledge`：
  - `template_id`
  - `template_label`
  - `planner_skill_hints`
  - `planner_retrieval_hints`
  - `runtime_profile`
- 当前已落地的第二层增强是 planner-scoped retrieval：
  - baseline / regression 两轮都会生成攻击规划专用查询
  - 会把结果压成 `attack_planner_evidence` card + `evidence_refs`
  - 空结果会回退到 broader retrieval 与当前 run 全局 evidence
- 当前不应误写成：
  - “攻击论文全文或完整论文库已经主链接入”
  - “planner 已经具备完整 lesson store”

## 2026-03-27 攻击经验对象化状态

- 当前 benchmark case 已开始被对象化为 `attack_lesson`。
- 当前论文摘要卡也已开始被对象化为 `attack_lesson`。
- 这批对象当前适合承载：
  - failure pattern
  - regression focus
  - template / skill route 约束
  - applicable template / attack surface / source metadata
- 当前仍不应误写成：
  - “论文 lesson 已全部接入或自动扩展”
  - “planner 已具备成熟的 attack knowledge base”
