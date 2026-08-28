# 企业知识库与检索主线设计

最后更新：2026-03-25
状态：active
适用范围：`data/components/`、`src/cipher_genius/knowledge/`、后续 `src/cipher_genius/retrieval/`、LangGraph `context_builder`、报告引用输出

## 1. 目标

要把“企业知识、规范和案例”做成真正有用的知识库，关键不是先上向量库，而是先把它们变成可检索、可过滤、可引用、可维护的知识对象。

在 BuildCipher 里，知识库建设的目标不是“让模型知道更多”，而是让系统能稳定完成下面几件事：

- 在生成候选方案前，拿到企业场景相关的依据
- 在审计和整改时，能回指标准、案例、组件能力边界
- 在最终交付里，输出带来源的建议，而不是只有自然语言总结
- 在多轮项目推进中，积累可复用的案例与决策依据

## 2. 适用范围

这套设计覆盖 4 类知识对象：

- 标准规范
  - 国密、等级保护、行业规范、企业内部安全基线
- 组件知识
  - 算法、库、中间件、HSM、KMS、证书体系、密钥生命周期能力
- 交付模板
  - 报告章节、整改建议模板、上线检查项、审计口径
- 历史案例
  - 某类场景过去怎么做、为什么这么做、踩过什么坑、最后怎么过审

不属于本设计直接负责的内容：

- 前端 UI 的展示风格
- 单轮大模型提示词的润色
- 纯缓存层面的命中优化

## 3. 当前现状

当前仓库已经具备两块可直接复用的基础：

- `data/components/**/*.yaml`
  - 已经存在较完整的组件知识资产
- `src/cipher_genius/knowledge/components.py`
  - 已经能把 YAML 组件资产加载成运行时 `ComponentLibrary`

当前第一版已经落地的能力：

- 统一的知识卡对象
- 组件 YAML、报告模板、benchmark case 进入统一知识卡集合
- `evidence_pack` 进入 LangGraph 主链
- 报告与导出中的“引用依据摘要”
- Qdrant 可用时优先存取，不可用时自动回退本地检索

当前仍缺少的关键能力：

- 原始标准规范 PDF/Word 自动触发 ingestion
- 更强的语义 / 向量召回
- 历史案例与 Case Memory 的真正打通
- claim/source 级的最终交付绑定

## 4. 核心设计

### 4.1 先定义知识对象，不要先把 PDF 全丢进去

每一条知识，不应该只是“一段文本”，而应该是结构化对象。至少建议包含：

- `doc_id`
- `chunk_id`
- `doc_type`
- `title`
- `source`
- `version`
- `effective_date`
- `industry`
- `region`
- `scenario`
- `tags`
- `content`
- `citation_snippet`
- `trust_level`

推荐的 `doc_type`：

- `standard`
- `policy`
- `component`
- `template`
- `case`

这样以后检索出来的不只是“相似文本”，而是“知道自己是什么、从哪来、能不能引用”的知识对象。

### 4.2 切分方式必须按业务语义，而不是按固定长度

构建知识库时，最容易做错的一点，就是把长文档按固定字数切块。对企业场景，更合适的切分方式是按“可引用单元”切：

- 标准规范：按条款、章节、控制项切
- 组件知识：按能力卡切，例如“支持算法”“密钥长度”“性能边界”“部署约束”
- 交付模板：按章节与建议类型切
- 历史案例：按“背景-约束-方案-审计意见-整改-最终结论”切

错误示例：

- 存成“《某规范》全文，第 1 段到第 20 段”

更好的示例：

- 《某规范》3.2.1 数据静态加密要求
- 《某规范》5.4 密钥轮换周期要求
- 《某规范》7.1 审计留痕要求

这会直接决定后续引用质量。

### 4.3 检索必须是结构化字段 + 混合召回

知识库不应等同于“生成 embedding 再丢进 Qdrant”。更推荐的主线是：

- 关键词召回
  - 适合搜标准编号、算法名、组件名、法规术语
- 向量召回
  - 适合搜语义相近需求
- metadata filter
  - 适合限定行业、场景、监管等级、交付阶段
- rerank
  - 适合把真正最相关的证据排到前面

建议的检索流程：

1. analyst 解析需求中的关键约束
2. context_builder 抽取过滤条件
3. 分类型召回标准、组件、模板、案例
4. 合并候选证据并 rerank
5. 形成 `evidence_pack`
6. 将 `evidence_pack` 注入 architect、auditor、delivery

例如输入：

“面向建筑工程项目的协同平台，需要满足合规审计、静态加密、传输加密和密钥托管要求。”

理想的检索过滤应至少包含：

- `industry = construction`
- `region = CN`
- `scenario = data_platform`
- `doc_type in [standard, policy, component, case]`

这样召回的不是泛化知识，而是贴近企业场景的依据。

### 4.4 历史案例不能只存最终方案，要存“为什么”

案例库最有价值的，不是“最后用了 AES + GCM”，而是：

- 当时的业务背景是什么
- 有哪些硬约束
- 哪些方案被否了
- 为什么否
- 最后为什么过审
- 哪些建议是人工确认的

因此，案例知识对象建议额外包含：

- `case_id`
- `constraints`
- `rejected_options`
- `accepted_option`
- `audit_findings`
- `remediation_actions`
- `delivery_summary`

这样未来系统在面对类似项目时，才能给出真正有说服力的建议，而不是只做相似话术匹配。

### 4.5 为什么正式入库层是必要的

从第一性原理看，我们真正要解决的问题不是“模型能不能临时看到一段文档”，而是“企业知识能不能被系统稳定调用、持续维护并进入决策主链”。

如果没有正式入库层，项目仍然能运行，但会长期停留在“本地文件检索增强”阶段，主要问题包括：

- 知识量一大，运行时只能依赖本地全量加载与遍历，伸缩性会越来越差
- metadata filter 很难演进成真正可治理的检索层
- 文档版本替换、增量更新、按来源删除会越来越难维护
- 很难向评委或企业解释“这不是几段 prompt 串起来”
- 后续的引用追踪、检索评测、项目隔离、多租户扩展都会被卡住

因此，Qdrant 这层的作用不是“项目里必须有个向量库”，而是把知识从“文件资产”升级成“运行时可管理知识资产”。

它承担的核心职责有 4 个：

- 存储职责：让 `KnowledgeChunk` 不再只停留在 JSONL 文件里
- 检索职责：为 metadata filter、语义召回、rerank 预留正式承载层
- 治理职责：支持 upsert、重建、替换、清点与后续运维
- 分层职责：把 `ingestion -> store -> retrieval -> langgraph -> reporting` 的边界真正做清楚

## 5. 推荐 schema

### 5.1 通用知识对象

```json
{
  "doc_id": "std-cn-health-001",
  "chunk_id": "std-cn-health-001#3.2.1",
  "doc_type": "standard",
  "title": "某建筑工程数据交付规范",
  "section": "3.2.1 静态数据加密要求",
  "content": "......",
  "citation_snippet": "静态存储的敏感数据应采用批准算法进行加密保护。",
  "source_path": "docs/standards/construction_xxx.pdf",
  "source_page": 12,
  "industry": "construction",
  "region": "CN",
  "scenario": ["data_platform", "research_data"],
  "tags": ["静态加密", "审计", "密钥托管"],
  "trust_level": "high",
  "effective_date": "2025-01-01",
  "version": "v1.2"
}
```

### 5.2 历史案例对象

```json
{
  "doc_id": "case-buildtrust-2025-03",
  "doc_type": "case",
  "title": "BIM/IFC 可信交付改造案例",
  "constraints": ["需国产化", "需审计留痕", "跨区部署"],
  "rejected_options": ["纯软件密钥托管"],
  "accepted_option": "HSM + 分层密钥管理",
  "audit_findings": ["密钥轮换策略不完整"],
  "remediation_actions": ["补齐轮换策略与审计日志"],
  "delivery_summary": "......"
}
```

## 6. 在本项目中的落地顺序

### 阶段 1：先把现有仓库资产结构化

优先从仓库里已经存在的内容开始：

- `data/components/**/*.yaml`
  - 转成组件知识卡
- 现有 benchmark 报告模板
  - 转成交付模板知识
- 审计规则、风险规则、中文交付标题
  - 转成规则知识
- 当前 MAS 产出的整改轨迹
  - 沉淀成案例雏形

这一阶段的目标不是做全量企业知识平台，而是先把内部已有资产变成统一知识对象。

### 阶段 2：接入规范和企业文档

建议纳入 ingestion 管道的来源：

- 国家/行业标准 PDF、Word、Markdown
- 企业内部制度文档
- 历史项目报告
- 交付模板和评审清单

统一处理流程建议为：

1. 解析原始文档
2. 清洗格式
3. 按语义切块
4. 加 metadata
5. 生成 embedding
6. 入 Qdrant
7. 保留原文引用定位信息

这里的关键要求是：不要丢掉原始引用位置，例如章节号、页码、段落号。因为后续交付引用一定要回得去。

当前仓库已完成的首版接线是：

- `ingestion/` 负责把 PDF / `.docx` 切成 `KnowledgeChunk`
- `scripts/knowledge/ingest_documents.py` 负责导出 JSONL
- `retrieval/service.py` 默认加载 `knowledge/processed/chunks/**/*.jsonl`
- 加载后的 chunk 会和组件 / 模板 / benchmark 一起参与本地检索与 Qdrant seeding
- `scripts/knowledge/upsert_qdrant.py` 负责把 JSONL chunk 正式 upsert 到 Qdrant collection

建议的下一步构建顺序是：

1. 先把 JSONL upsert 到 Qdrant，形成正式知识存储层
2. 再让 retrieval 优先消费正式 collection，并保留本地 fallback
3. 然后补 metadata filter、语义向量与 rerank
4. 最后把引用块、案例记忆和检索评测串成完整闭环

当前仓库在这一步已经前进到：

- retrieval 会优先从 Qdrant collection 取候选
- 当前已显式使用 `doc_type` 与 `region` 做 Qdrant 侧过滤
- `scenario` 仍会在服务层继续收敛，保持与本地 fallback 一致
- 最终排序仍由现有 keyword / semantic 逻辑负责
- 但标准 / policy 类知识块已经开始利用 `clause_code / section_path` 做条款感知增强

当前这一层的具体收益是：

- 用户在需求里点名 `3.2.1` 这类条款号时，检索不再把它当普通文本
- 标题层级路径会参与打分，而不只是被动塞进 metadata
- 报告中的引用依据摘要可以直接带出条款号与上级路径，更适合企业评审与答辩展示

### 阶段 3：让知识库进入主链，而不是做旁路搜索

知识库建好后，不应只是在页面上提供一个“搜一下”。它应该进入 LangGraph 主流程：

1. `analyst` 抽取需求约束
2. `context_builder` 根据约束检索知识库
3. 输出 `evidence_pack`
4. `architect` 基于 `evidence_pack` 生成候选
5. `auditor` 基于 `evidence_pack` 判定风险和不合规项
6. `delivery` 输出带引用的建议和报告

只有这样，知识库才是真正影响决策，而不是一个摆设。

## 7. 为什么这比“把文档直接塞给模型”更强

本质区别在于：

- 直接塞文档
  - 一次性
  - 上下文临时
  - 不可复用
  - 不可过滤
  - 难引用
- 做成知识库
  - 可复用
  - 可治理
  - 可过滤
  - 可追溯
  - 可评测

换句话说，知识库不是“让模型知道更多”，而是“让系统能有组织地调用企业知识”。

## 8. 用户使用方式会如何变化

表面上，用户仍然是“输入需求，系统给方案”。但内部流程会从：

1. 输入需求
2. 直接出结果

变成：

1. 输入需求
2. 系统自动抽取约束
3. 自动检索规范、案例、组件、模板
4. 生成候选时带依据
5. 审计时带证据
6. 最终报告带引用

也就是说，项目内部会从“单轮生成”升级成“检索增强 + 项目收敛 + 可追溯交付”。

## 9. 验证与回归

这条能力落地后，至少应验证：

- 检索结果是否返回来源、片段、得分和过滤信息
- `use_langgraph=true` 路径下，`evidence_pack` 是否进入主链
- 报告和导出物中是否保留引用块
- 相似需求下，历史案例是否真的影响候选收敛，而不是只影响措辞
- retrieval hit rate、citation coverage 是否可量化输出

## 10. 关联代码与文档

- `data/components/README.md`
- `src/cipher_genius/knowledge/README.md`
- `src/cipher_genius/knowledge/components.py`
- `src/cipher_genius/core/langgraph_mas.py`
- `src/cipher_genius/api/mas_service.py`
- `src/cipher_genius/api/report_service.py`
- `REMAIN.md`
- `TODO_VIBING.md`

## 11. 2026-03-27 攻击规划检索补记

- 当前 retrieval 主线已不只服务 generation / audit / delivery，也开始服务 `AttackPlanningAgent`。
- 新增的做法不是把全局 `evidence_pack` 原样复制给攻击规划层，而是额外构建：
  - planner-scoped query
  - planner-scoped evidence pack
  - `attack_planner_evidence` card
- 当前查询输入会结合：
  - `template_id / template_label`
  - `service_kind / attack_surface_kind`
  - `planner_skill_hints / planner_retrieval_hints`
  - `planning_mode`
  - `prior_findings / regression_focus`
- 当前回退顺序已经固定：
  1. planner-scoped retrieval
  2. retrieval 内部 broader fallback
  3. 当前 run 的全局 `evidence_pack`
- 当前边界：
  - 已完成 retrieval-aware planner 第一版
  - 尚未完成 benchmark lesson / exploit lesson 的专门对象化与专门 rerank

## 11.1 2026-03-27 攻击经验对象化补记

- 当前 benchmark 数据已开始承担 lesson store 职责，而不只承担 route/template 回归。
- retrieval 层现在会从 benchmark case 派生：
  - 通用 `case` 文档
  - planner 专用 `attack_lesson` 文档
- 这意味着当前知识库已经开始从“企业知识检索”走向“决策经验检索”。

## 11.2 2026-03-27 论文摘要卡对象化补记

- 当前 retrieval 还会从 `data/attack_lessons/*.yaml` 派生论文摘要型 `attack_lesson` 文档。
- 这批对象当前显式沉淀：
  - `lesson_kind = paper_attack_planning`
  - `applicable_templates`
  - `attack_surface_kinds`
  - `service_kinds`
  - `planner_skill_hints`
  - `source_title / source_year`
- 这意味着 attack planner 已不再只检索企业规范、模板和 benchmark case，也能检索“压缩后的论文方法边界卡”。
- 当前边界仍要保持诚实：
  - 已完成 benchmark / paper lesson 第一版对象化
  - 尚未完成 exploit / patch lesson 与更强 lesson rerank
