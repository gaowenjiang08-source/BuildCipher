# Skills 模块说明

最后更新：2026-03-24
状态：active

## 1. 目录职责

本目录负责运行时 Skill V2 的注册与自动路由，是“专家模式”“按需求推荐合适能力包”的核心实现层。

这里解决的是：

- 如何从 `data/skills/*.yaml` 加载 Skill manifest
- 如何根据需求做可解释的 Skill 推荐
- 如何为 API 与前端提供稳定的 Skill 目录与路由结果

这里不直接负责：

- FastAPI 路由注册
- 前端 Skill 卡片展示
- 具体 MAS 主链执行细节

## 2. 当前关键入口

- `registry.py`
  - 负责加载和管理运行时 Skill manifest
- `router.py`
  - 负责 Skill 自动推荐与路由逻辑，当前支持关键词与可选语义召回

## 3. 核心流程

当前 Skill V2 的主链可以概括为：

1. `registry.py` 从 `data/skills/*.yaml` 加载可用 Skill
2. `router.py` 根据 requirement、关键词、优先级和可选语义相似度做推荐
3. API 层通过 `skill_service.py` 暴露 Skill 列表、路由结果和执行入口
4. 前端消费 Skill 列表与推荐理由，并驱动专家模式执行

## 4. 稳定约束

- Skill manifest 的稳定字段不要随意改名，尤其是 `id`、`version`、`status`、`route_keywords`
- 用户可见的路由理由、增强描述应默认中文优先，但 `skill_id` 仍保持稳定英文标识
- Skill 执行链允许通过 `use_langgraph` 控制嵌套 MAS 引擎，相关字段改动必须同步 API、前端和文档
- 路由结果应保持可解释，不要把“为什么推荐这个 Skill”完全藏进黑盒逻辑

## 5. 常见改动点

- 新增 Skill：
  - 先在 `data/skills/` 增加 manifest
  - 再检查 `registry.py` 是否需要兼容新字段
- 改自动推荐逻辑：
  - 优先看 `router.py`
- 改 Skill 执行入口或返回：
  - 同时检查 `src/cipher_genius/api/skill_service.py` 和 `src/cipher_genius/api/schemas.py`

## 6. 联动影响

改动本目录时，通常还会影响：

- `data/skills/`
- `src/cipher_genius/api/skill_service.py`
- `src/cipher_genius/api/main.py`
- `frontend/src/api/client.js`
- `frontend/src/features/mas/`
- `tests/unit/test_skill_registry.py`
- `tests/unit/test_skill_router.py`

## 7. 验证方式

至少应完成：

- `poetry run pytest tests/unit/test_skill_registry.py -q`
- `poetry run pytest tests/unit/test_skill_router.py -q`
- 手工验证：
  - `GET /api/v1/skills`
  - `POST /api/v1/skills/route`
  - `POST /api/v1/skills/execute`
  - `POST /api/v1/skills/stream`

## 8. 相关文档

- `docs/agent_skills/skill_skill_v2.md`
- `docs/TECHNICAL_DOCUMENTATION.md`
- `frontend/README.md`
