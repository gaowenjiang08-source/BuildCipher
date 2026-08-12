# Skill: Runtime Skill V2 (manifest / 路由 / 执行)

## When To Use

- 你要新增/修改运行时 Skill（manifest YAML）
- 你要调整自动推荐/路由逻辑（keywords / priority / 可解释推荐）

## Key Files

- Skill manifests：
  - `data/skills/*.yaml`
- Skill registry（加载 manifest）：
  - `src/cipher_genius/skills/registry.py`
- Skill router（推荐逻辑）：
  - `src/cipher_genius/skills/router.py`
- Skill API 服务（对前端暴露）：
  - `src/cipher_genius/api/skill_service.py`
  - `src/cipher_genius/api/main.py`
- 前端调用：
  - `frontend/src/api/client.js`（`getSkills` / `routeSkill` / `executeSkill`）

## Invariants

- manifest 字段变更必须同步更新：
  - `schemas.py` 中的 `SkillSummaryPayload`
  - 前端 Skill 卡片展示
  - 文档（`docs/TECHNICAL_DOCUMENTATION.md`、`README.md`）
- 面向中国企业客户时，Skill 路由理由与 `enhanced_requirement` 中的用户可见说明默认中文优先
- Skill 执行链当前允许通过 `SkillExecuteRequest.use_langgraph` 控制嵌套 MAS 引擎；新增或调整相关字段时要同步前端设置页与 API 文档

## Common Changes

- 新增 Skill：
  - 在 `data/skills/` 新增一个 `*.yaml`
  - 至少配置：`id/name/description/version/status/route_keywords`
  - 跑单测：`poetry run pytest tests/unit/test_skill_router.py -q`

## Routing Notes (Skill Router)

- Default router is keyword-based and explainable: `skill-v2-keyword-router`
- Optional semantic fallback (SentenceTransformers) for enterprise:
  - `SKILL_ROUTER_ENABLE_EMBEDDINGS=true` (default false)
  - `SKILL_ROUTER_EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2`
  - `SKILL_ROUTER_EMBEDDING_MIN_SIMILARITY=0.35`
  - `SKILL_ROUTER_EMBEDDING_WEIGHT=0.35`
  - Candidates may include a reason like: `Semantic similarity: 0.xx (model)`
- `/api/v1/skills/route` caching (Redis):
  - key: `skill:route:{sha256(signature)[:24]}` (signature includes requirement + routing settings + skill catalog fingerprint)
  - TTL: `SKILL_ROUTE_CACHE_TTL` (default 1800s)

## Verification

- 单测：
  - `poetry run pytest tests/unit/test_skill_registry.py -q`
  - `poetry run pytest tests/unit/test_skill_router.py -q`
- API：
  - `GET /api/v1/skills`
  - `POST /api/v1/skills/route`
  - `POST /api/v1/skills/execute`（可带 `use_langgraph=true`）
  - `POST /api/v1/skills/stream`（可带 `use_langgraph=true`）

## Docs To Update (按 AGENTS.md)

- `docs/TECHNICAL_DOCUMENTATION.md`
- `DOC_INDEX.md`
- 必要时：`README.md`、`QUICK_START_V3.md`、`frontend/README.md`
