# Retrieval 模块说明

最后更新：2026-03-25
状态：active

## 1. 目录职责

本目录负责企业知识检索主线的运行时实现，当前重点是把组件、模板、benchmark 案例和 ingestion JSONL 转成统一知识卡，并构建 `evidence_pack`。

## 2. 当前关键入口

- `service.py`
  - 负责知识卡加载、Qdrant 优先存取、本地回退检索与 evidence pack 生成
- `qdrant_store.py`
  - 负责 Qdrant collection 管理、stable point id 与批量 upsert

## 3. 当前实现边界

当前第一版已经具备：

- 组件 YAML -> 组件知识卡
- 企业交付模板 -> 模板章节知识卡
- benchmark case -> 案例知识卡
- ingestion JSONL -> 标准 / policy / case 知识卡
- Qdrant 可用时优先作为正式查询层
- Qdrant 不可用时自动回退本地检索
- 条款级 `clause_code / section_path` 参与标准类证据排序
- 输出统一 `EvidencePackPayload`

当前还没有完全做完的部分：

- 原始 PDF/Word 自动触发 ingestion
- 更完整的案例记忆接入
- claim/source 级的最终交付绑定

## 4. 当前排序规则

当前 retrieval 排序仍以现有 keyword / semantic 主逻辑为主，但已经补上了面向标准规范的条款感知增强：

- query 中出现条款号时
  - 例如 `3.2.1`
  - 会显式匹配 ingestion chunk metadata 中的 `clause_code`
- 标题路径会参与打分
  - `section_path` 不再只是被动保存在 metadata 中，而会参与关键词命中
- 对标准 / policy 类型、且可回指具体条款的知识块
  - 在已具备相关性的前提下会获得适度加权

这层增强的目标不是做“复杂 rerank 系统”，而是优先把真正可引用、可回指条款的规范证据排到前面。

## 5. 修改本目录时要同步检查什么

- `docs/modules/retrieval_knowledge_base.md`
- `docs/modules/mas_workflow.md`
- `src/cipher_genius/core/langgraph_mas.py`
- `src/cipher_genius/api/report_service.py`
- `tests/unit/test_retrieval_service.py`

## 6. 相关文档

- `docs/modules/retrieval_knowledge_base.md`
- `src/cipher_genius/knowledge/README.md`
- `data/components/README.md`
## 增量更新：文档 Ingestion（2026-03-24）

当前 PDF / Word 原始文档读取能力已经独立落到：

- `src/cipher_genius/ingestion/`
- `scripts/knowledge/ingest_documents.py`

`retrieval/` 继续负责运行时检索，不再承担原始文档解析职责。

当前接线方式：

- 默认自动加载 `knowledge/processed/chunks/**/*.jsonl`
- 可通过 `CIPHER_GENIUS_INGESTED_KNOWLEDGE_DIR` 覆盖目录
- 已加载的 ingestion JSONL 会和组件 / 模板 / benchmark 一起参与本地检索与 Qdrant seeding
- 如需正式入库，可使用 `scripts/knowledge/upsert_qdrant.py`
- Qdrant 可用时会优先按 `doc_type` / `region` 过滤正式 collection，再交给当前排序逻辑
- 2026-03-25 起，`clause_code / section_path` 也会参与标准类证据排序，并在报告引用摘要中展示条款号与父级路径

## 2026-03-27 攻击规划检索补记

- `service.py` 当前已新增 `retrieve_attack_planning_evidence(...)`。
- 该入口的定位是：
  - 为 `AttackPlanningAgent` 生成 planner-scoped evidence
  - 不替代全局 `evidence_pack`
- 当前会结合：
  - `template_id / template_label`
  - `service_kind / attack_surface_kind`
  - `planner_skill_hints / planner_retrieval_hints`
  - `planning_mode`
  - `prior_findings / regression_focus`
- 当前回退顺序：
  - planner-scoped retrieval
  - retrieval 内部 global fallback
  - 上层再按需退回当前 run 的全局 `evidence_pack`

## 2026-03-27 Attack Lesson 补记

- benchmark case 当前还会额外派生 `doc_type = "attack_lesson"` 文档。
- 这批文档的目的是给 `AttackPlanningAgent` 提供：
  - attack focus
  - regression focus
  - benchmark-derived lesson
- 当前它们属于 lesson store 的第一版，不等同于完整攻击知识库。

## 2026-03-27 Paper Attack Lesson 补记

- `service.py` 当前还会加载 `data/attack_lessons/*.yaml`。
- 这批论文摘要卡会继续复用 `doc_type = "attack_lesson"`，但通过 `lesson_kind = "paper_attack_planning"` 与 benchmark lesson 区分。
- 当前沉淀的核心字段包括：
  - `applicable_templates / attack_surface_kinds / service_kinds`
  - `planner_skill_hints`
  - `source_title / source_year`
- 当前边界：
  - 已完成 paper lesson 第一版对象化
  - 尚未完成 exploit / patch lesson 扩展与专门 rerank
