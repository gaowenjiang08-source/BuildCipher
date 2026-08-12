# 企业文档 Ingestion 设计

最后更新：2026-03-25
状态：active
适用范围：`src/cipher_genius/ingestion/`、`scripts/knowledge/`、后续标准规范 / 企业制度 / 历史案例文档入库主线

## 1. 目标

本模块解决的不是“如何把 PDF/Word 读出一点文本”，而是如何把企业原始文档稳定转成：

- 可切块
- 可过滤
- 可引用
- 可入向量库
- 可被 LangGraph 主链消费

的统一知识对象。

## 2. 当前已落地能力

当前第一阶段已经新增：

- `src/cipher_genius/ingestion/models.py`
  - `DocumentBlock`
  - `ParsedDocument`
  - `KnowledgeChunk`
- `src/cipher_genius/ingestion/parsers/pdf_parser.py`
  - 文本型 PDF 首版解析
  - 可提取页级文本块与表格文本
- `src/cipher_genius/ingestion/parsers/word_parser.py`
  - `.docx` 段落 / 标题 / 表格解析
- `src/cipher_genius/ingestion/chunkers/semantic_chunker.py`
  - 按章节 / 条款标题优先、内容上限受控的方式切 chunk
  - 维护 heading stack，并把条款级 metadata 写入 chunk
- `src/cipher_genius/ingestion/pipeline.py`
  - 串联 parser 与 chunker
- `scripts/knowledge/ingest_documents.py`
  - 命令行入口，可输出 JSONL
- `src/cipher_genius/api/knowledge_ingestion_service.py`
  - 面向前端上传入口的 ingestion service
- `POST /api/v1/knowledge/ingest`
  - 允许从前端上传 PDF / `.docx`，并返回切块预览
- `src/cipher_genius/retrieval/service.py`
  - 运行时加载 ingestion JSONL，并纳入 `evidence_pack`
- `scripts/knowledge/upsert_qdrant.py`
  - 把 JSONL chunk 正式写入 Qdrant collection

## 3. 当前边界

当前这套 ingestion 还没有直接完成：

- 扫描 PDF OCR
- `.doc` 自动转换
- embedding 生成与更完整的语义 / rerank 流水线

也就是说，现在它已经不是纯离线骨架，而是“离线切块 + 运行时检索加载 + 独立 Qdrant 入库脚本”的首版闭环，但还不是“完整企业知识入库平台”。

## 4. 统一对象层

### 4.1 DocumentBlock

原始解析块，服务于“读出来”阶段，关键字段包括：

- `block_id`
- `block_type`
- `text`
- `order`
- `page_index`
- `section_hint`
- `bbox`
- `metadata`

### 4.2 ParsedDocument

标准化文档对象，服务于“切块前”阶段：

- `doc_id`
- `title`
- `source_path`
- `source_type`
- `blocks`
- `metadata`

### 4.3 KnowledgeChunk

检索与引用友好的块对象，服务于“入库前/检索时”阶段：

- `doc_id`
- `chunk_id`
- `doc_type`
- `title`
- `section`
- `content`
- `citation_snippet`
- `source_path`
- `source_page`
- `metadata`

当前首版条款级 metadata 已经包括：

- `section_path`
  - 当前 chunk 对应的标题层级路径，例如 `["3.2 密钥管理", "3.2.1 密钥轮换要求"]`
- `heading_level`
  - 当前标题在 heading stack 中的层级
- `clause_code`
  - 当前条款号或章节号，例如 `3.2.1`

## 5. 为什么这样拆

这层拆分的意义是：

- parser 只负责“读”
- chunker 只负责“切”
- retrieval 只负责“搜”
- report/delivery 只负责“引”

避免把 PDF/Word 读取、检索逻辑和报告引用混写在一个模块里。

## 6. 当前解析策略

### 6.1 PDF

当前实现：

- 主要依赖 `pypdf`
- 如安装了 `pdfplumber`，额外提取表格文本
- 保留页码
- 用轻量标题启发式识别 heading block

适合：

- 文本型 PDF
- 结构相对清晰的规范 / 制度 / 报告

### 6.2 Word

当前实现：

- 依赖 `python-docx`
- 保留段落顺序
- 识别标题样式
- 保留表格文本

当前仅支持：

- `.docx`

不直接支持：

- `.doc`

### 6.3 条款级切块

当前 `SemanticChunker` 已经不再只是“看到标题就切一刀”。它会：

- 维护 heading stack
  - 同时识别数字章节号、中文“第 X 章 / 节 / 条”与常见列表标题
- 把标题和正文绑定在同一个 chunk
  - 避免后续引用时只拿到正文、却丢失条款标题
- 优先使用条款号生成 `chunk_id`
  - 例如 `std-cn-demo#3.2.1`
- 当同一条款过长被拆成多个 chunk 时，自动追加 `-part-N`
  - 例如 `std-cn-demo#5.4`、`std-cn-demo#5.4-part-2`

这一层的意义是：后续报告引用、Qdrant payload、evidence pack 和 rerank 不再面对“无语义编号的大段文本”，而是可以直接消费“可回指条款”的知识块。

## 7. 推荐演进顺序

### 阶段 1

先把 `.pdf` 与 `.docx` ingestion 跑通，并形成稳定 JSONL 输出。

### 阶段 2

补扫描件 OCR：

- 中文优先推荐 `PaddleOCR`
- 让扫描 PDF 也能落到同一套 `DocumentBlock`

### 阶段 3

增强语义切块：

- 按章节号 / 条款号 / 控制项切
- 在现有条款级切块基础上继续增强控制项识别、表格语义切块与更细粒度引用单元

### 阶段 4

接入向量库：

- embedding
- Qdrant upsert
- metadata filter
- retrieval rerank

## 8. 使用方式

示例：

```bash
poetry run python scripts/knowledge/ingest_documents.py \
  --source knowledge/raw/standards \
  --doc-type standard \
  --output knowledge/processed/chunks/standards.jsonl \
  --metadata "{\"region\":\"CN\",\"industry\":\"construction\"}"
```

默认运行时加载目录：

- `knowledge/processed/chunks/**/*.jsonl`

可选覆盖：

- `CIPHER_GENIUS_INGESTED_KNOWLEDGE_DIR`

## 9. 验证方式

至少验证：

- PDF 能提取出非空 blocks
- DOCX 能提取出 heading / paragraph / table
- pipeline 能稳定输出 `KnowledgeChunk`
- 输出 chunk 能保留 `source_path` / `source_page` / `citation_snippet`
- 条款级标题能够进入 `section_path / clause_code / heading_level`
- 长条款拆分时 `chunk_id` 不发生冲突

相关测试：

- `tests/unit/test_ingestion_pipeline.py`
- `tests/unit/test_retrieval_service.py`

## 10. 关联文档

- `docs/modules/retrieval_knowledge_base.md`
- `src/cipher_genius/ingestion/README.md`
- `src/cipher_genius/retrieval/README.md`
- `DOC_INDEX.md`

## 11. 敏感信息治理补充（2026-03-25）

上传式 ingestion 当前默认应按企业敏感信息处理，原因包括：

- 原始 PDF / DOCX 可能包含企业制度、审计意见、整改记录与部署边界
- chunk 预览与 `citation_snippet` 仍可能暴露内部条款内容
- `stored_path`、`output_path` 与 request 轨迹可暴露本地目录结构和演示痕迹

当前已补充的最小治理闭环：

- `POST /api/v1/knowledge/ingest`
  - 继续负责上传、切块、JSONL 输出与可选 Qdrant 写入
- `DELETE /api/v1/knowledge/ingest/{request_id}`
  - 删除某次上传式 ingestion 产生的本地上传文件与 JSONL
  - 当前不会顺带删除已写入 Qdrant 的副本
- `POST /api/v1/knowledge/ingest/{request_id}/qdrant`
  - 基于该次 ingestion 保留下来的本地 JSONL 重建 Qdrant 副本
  - 当前仅支持单条资产重入库，不自动做批量重建索引
- `DELETE /api/v1/knowledge/ingest/{request_id}/qdrant`
  - 显式删除该次 ingestion 对应的 Qdrant 副本
  - 优先按 payload 中持久化的 `request_id` 删除
  - 如按 `request_id` 未命中且本地 JSONL 仍在，则回退到按 `chunk_id` 计算 point id 删除
- `GET /api/v1/knowledge/ingestions`
  - 返回历史导入记录、文件清单、本地文件状态与 Qdrant 状态
  - 当前由轻量 manifest 驱动，而不是临时扫目录拼结果
- `fresh.bat`
  - 默认清理 `knowledge/raw/uploads` 与 `knowledge/processed/chunks/uploads`
- `.gitignore`
  - 默认忽略上传目录，避免误提交

manifest 当前还会持久化以下治理字段：

- `qdrant_upserted`
- `qdrant_cleanup_required`
- `qdrant_message`
- `qdrant_deleted_at`

前端当前对这份 manifest 的消费方式也已经升级为“列表 + 详情”：
- 列表层负责切换 ingestion 记录
- 详情层负责解释当前知识资产的 metadata、文件清单、chunk 预览与治理状态
- 详情层当前会把“删除本地导入产物”“重入库”和“删除向量副本”分开呈现，避免演示时误以为删掉上传文件就等于彻底清理知识资产
- 因此 `GET /api/v1/knowledge/ingestions` 现在不仅服务于历史记录展示，也服务于知识资产答辩与演示中的可解释性
