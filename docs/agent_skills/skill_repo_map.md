# Skill: Repo Map (代码架构与目录梳理)

## When To Use

- 你需要快速理解仓库结构、入口与核心模块边界
- 你要做“整理文件夹/模块归类/改动面拆分”的维护性改动

## Top-Level Layout

- `src/cipher_genius/`: Python 后端与核心库（FastAPI、MAS、Skill、知识库、工具）
- `frontend/`: React 前端（Vite + Zustand）
- `streamlit/`: Streamlit 兼容入口（v3 维护，`legacy/` 为历史版本）
- `data/`: 静态数据资产（组件库、Skill manifest、report templates、benchmarks）
- `docs/`: 技术文档与说明（含本目录 `agent_skills/`）
- `scripts/`: 评估/实验脚本（离线指标、A/B 等）
- `tests/`: 单元测试与集成测试
- `deprecated/`: 已下线/迁移代码的索引说明（非运行路径）

## Runtime Entrypoints

- FastAPI 后端：`src/cipher_genius/api/main.py`（CLI: `poetry run cipher-genius-api`）
- Typer CLI：`src/cipher_genius/cli/main.py`（CLI: `poetry run cipher-genius ...`）
- Celery Worker：`src/cipher_genius/tasks/celery_tasks.py`
- Streamlit v3：`streamlit/web_app_v3.py`（UI 实现：`src/cipher_genius/ui/web_v3/`）
- React 前端入口：`frontend/src/main.jsx` / `frontend/src/App.jsx`

## Core Module Map (Python)

- `cipher_genius/api/`
  - `main.py`: 路由入口（含 MAS/Skill 流式 NDJSON）
  - `schemas.py`: API 请求/响应 Pydantic 模型（前后端契约）
  - `mas_service.py`: Legacy MAS（业务逻辑最完整的实现）
  - `skill_service.py`: Skill 执行（manifest 加载 + MAS 增强）
  - `report_service.py`: 报告聚合与导出
- `cipher_genius/reporting/`
  - `templates.py`: 企业交付模板注册表与解析顺序
- `cipher_genius/testing/`
  - `construction_benchmark.py`: 建筑 benchmark 数据集与 runner
- `cipher_genius/core/`
  - `parser.py`: 需求解析（LLM + 回退启发式）
  - `generator.py`: 方案生成（LLM + 组件库）
  - `langgraph_mas.py`: LangGraph MAS（实验性引擎，需与 `schemas.py` 对齐）
  - `trust_assessor.py`: 可信度/算法实力评分
- `cipher_genius/skills/`: 运行时 Skill V2（manifest、路由）
- `cipher_genius/features/`: 合规/性能/漏洞/对比等能力（并非全部被运行链路使用）
- `cipher_genius/knowledge/`: 组件知识库（由 `data/components/` 驱动）
- `cipher_genius/ingestion/`: 企业 PDF / `.docx` 文档 ingestion（parser、chunker、pipeline、JSONL 导出前置层）
- `cipher_genius/retrieval/qdrant_store.py`: Qdrant collection 管理与知识 payload 正式入库层
- `cipher_genius/utils/`: 配置、日志、缓存、Redis 等基础设施

## Common Change Routes

- 新增/修改后端 API：
  - 先看 `docs/agent_skills/skill_backend_api.md`
- 调整 MAS 执行链路（审计轮次、候选策略、交付字段）：
  - 先看 `docs/agent_skills/skill_mas_workflows.md`
- 增强攻击 agent 的知识来源、论文/benchmark 接线或 planner 策略：
  - 先看 `docs/agent_skills/skill_attack_agent_enhancement.md`
- 新增/调整运行时 Skill V2（manifest/路由/执行）：
  - 先看 `docs/agent_skills/skill_skill_v2.md`
- 新增/调整企业交付模板或 benchmark：
  - 先看 `docs/agent_skills/skill_benchmark_reporting.md`
- 新增/调整企业知识入库、PDF / Word ingestion、chunk schema：
  - 先看 `docs/modules/knowledge_ingestion.md`
- 改 React 交互、流式展示、状态管理：
  - 先看 `docs/agent_skills/skill_frontend_react.md`

## Verification

- 语法检查：`python -m compileall src streamlit scripts tests`
- 单测：`poetry run pytest tests/unit -q`
- 后端联调：`poetry run cipher-genius-api` 后用前端或 curl 验证
