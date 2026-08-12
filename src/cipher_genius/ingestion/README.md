# Ingestion 模块说明

最后更新：2026-03-25
状态：active

## 1. 目录职责

本目录负责把企业原始文档读成统一的结构化对象，再切成可检索、可引用、可入库的知识块。

它解决的是：

- PDF / Word 如何被稳定读取
- 文档如何变成统一 block / chunk schema
- 后续 retrieval / embedding / citation 如何复用这套标准化输出

本目录当前不直接负责：

- Qdrant 写入
- 向量召回
- 报告引用渲染

说明：

- 当前 `KnowledgeChunk` JSONL 已可被 `retrieval/` 运行时直接加载
- 现在既可以显式运行脚本，也可以通过 `POST /api/v1/knowledge/ingest` 触发上传式 ingestion
- 如果要把 chunk 正式写入 Qdrant，可继续使用 `scripts/knowledge/upsert_qdrant.py`

## 2. 当前关键入口

- `models.py`
  - 定义 `DocumentBlock`、`ParsedDocument`、`KnowledgeChunk`
- `parsers/pdf_parser.py`
  - PDF 文本块与表格的首版解析
- `parsers/word_parser.py`
  - `.docx` 段落 / 标题 / 表格解析
- `chunkers/semantic_chunker.py`
  - 按章节 / 条款标题和内容上限切 chunk，而不是粗暴固定长度切片
  - 输出 `section_path`、`heading_level`、`clause_code` 等条款 metadata
- `pipeline.py`
  - 串联 parser 与 chunker

## 3. 当前边界

当前第一版已经具备：

- 文本型 PDF 读取
- `.docx` 读取
- 表格文本提取
- 页码 / section / snippet 保留
- 条款级标题路径与条款号 metadata 保留
- JSONL 导出入口

当前还没有完整做完的部分：

- 扫描 PDF OCR
- `.doc` 自动转换
- 自动 embedding / rerank 流水线
- 原始文档自动触发 ingestion

## 4. 当前 chunk 规则

当前 `SemanticChunker` 的规则重点是：

- 维护标题层级栈，而不是只记住“最近一个标题”
- 识别数字章节号、中文章 / 节 / 条和常见列表标题
- 把标题与正文绑定到同一个 chunk 中
- `chunk_id` 优先使用条款号，例如 `doc-id#3.2.1`
- 同一条款过长时，继续拆分为 `doc-id#3.2.1-part-2` 这类唯一 id

这样做的目的不是“让切块看起来更聪明”，而是让后续 retrieval、引用和报告交付都能稳定回指到具体条款。

## 5. 脚本入口

- `scripts/knowledge/ingest_documents.py`
- `src/cipher_genius/api/knowledge_ingestion_service.py`

示例：

```bash
poetry run python scripts/knowledge/ingest_documents.py \
  --source knowledge/raw/standards \
  --doc-type standard \
  --output knowledge/processed/chunks/standards.jsonl \
  --metadata "{\"region\":\"CN\",\"industry\":\"construction\"}"
```

## 6. 联动影响

修改本目录时，通常还需要同步检查：

- `docs/modules/retrieval_knowledge_base.md`
- `docs/modules/knowledge_ingestion.md`
- `src/cipher_genius/retrieval/README.md`
- `docs/TECHNICAL_DOCUMENTATION.md`

## 7. 验证方式

至少应完成：

- `python -m compileall src/cipher_genius/ingestion scripts/knowledge tests/unit/test_ingestion_pipeline.py`
- `poetry run pytest tests/unit/test_ingestion_pipeline.py -q`
- 若改动影响 retrieval / Qdrant 接线，补跑 `tests/unit/test_retrieval_service.py`、`tests/unit/test_qdrant_knowledge_store.py` 与 `tests/unit/test_qdrant_upsert_script.py`
