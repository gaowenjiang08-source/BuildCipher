# CipherGenius v3.1 升级说明

## 版本信息

- 版本号: v3.1.0
- 发布日期: 2026-03-10
- 升级类型: 架构升级 (Major Enhancement)

## 核心变更

### 1. 引入 LangGraph Agent 框架

**变更内容**:
- 新增 `src/cipher_genius/core/langgraph_mas.py`
- 使用 LangGraph StateGraph 替代原有的串行 prompt 调用
- 支持状态图编排、检查点持久化、并行执行

**优势**:
- 可恢复性: 通过 MemorySaver 支持中断恢复
- 可观测性: 每个节点状态变化可追踪
- 可扩展性: 轻松添加新节点或条件分支
- 错误隔离: 单个节点失败不影响整体状态

**迁移指南**:
```python
# 旧方式
from cipher_genius.api.mas_service import MASOrchestrationService
service = MASOrchestrationService(llm_provider)

# 新方式 (推荐)
from cipher_genius.core.langgraph_mas import LangGraphMASService
service = LangGraphMASService(llm_provider)
```

### 2. Redis 缓存与任务队列

**新增文件**:
- `src/cipher_genius/utils/redis_client.py`: Redis 客户端封装
- `src/cipher_genius/tasks/celery_tasks.py`: Celery 任务定义

**缓存策略**:
- MAS 结果缓存: `mas:result:{sha256(fingerprint)[:24]}`, TTL 1小时
- Skill 路由缓存: `skill:route:{sha256(requirement)[:24]}`, TTL 30分钟
- 组件库缓存: `component:library:v{version}`, TTL 24小时

**配置**:
```bash
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_CACHE_TTL=3600
```

**Celery 任务**:
- `generate_scheme_async`: 异步方案生成
- `execute_mas_async`: 异步 MAS 执行
- `generate_report_async`: 异步报告生成

### 3. 前端状态管理升级

**新增文件**:
- `frontend/src/store/index.js`: Zustand 状态管理
- `frontend/src/components/ErrorBoundary.jsx`: 错误边界组件

**4个独立 Store**:
- `useMASStore`: MAS 执行状态、结果、历史记录
- `useSkillStore`: Skill 列表、选中状态
- `useSettingsStore`: 用户配置 (持久化)
- `useUIStore`: UI 状态、通知

**错误处理**:
- 全局错误边界: 捕获整个应用错误
- 组件级错误边界: 隔离单个组件错误
- 友好的错误提示界面

### 4. 依赖版本升级

**后端核心依赖**:
- LangGraph: 新增 0.2.60
- LangChain: 0.1 → 0.3
- FastAPI: 0.104 → 0.115
- Pydantic: 2.5 → 2.10
- Redis: 5.0 → 5.2
- Celery: 5.3 → 5.4
- OpenAI SDK: 1.3 → 1.58
- Anthropic SDK: 0.30 → 0.42

**前端核心依赖**:
- Zustand: 新增 5.0
- React Error Boundary: 新增 6.1

**开发依赖**:
- pytest: 7.4 → 8.3
- black: 23.12 → 24.10
- ruff: 0.1 → 0.8
- mypy: 1.7 → 1.13

## 破坏性变更

### 1. 配置文件变更

**新增配置项**:
```bash
# Redis 配置
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_CACHE_TTL=3600
```

**移除配置项**:
```bash
# 旧的 Redis URL 配置已废弃
# REDIS_URL=redis://localhost:6379/0
```

### 2. API 行为变更

**缓存行为**:
- 启用 Redis 后，相同需求的重复请求将返回缓存结果
- 如需强制刷新，需手动清除缓存或等待 TTL 过期

**错误响应**:
- 前端错误边界会捕获并显示友好错误页面
- 不再直接透传后端错误信息

## 升级步骤

### 1. 更新依赖

```bash
# 后端
poetry lock --no-update
poetry install

# 前端
cd frontend
npm install
```

### 2. 更新配置文件

```bash
# 添加 Redis 配置到 .env
echo "REDIS_ENABLED=true" >> .env
echo "REDIS_HOST=localhost" >> .env
echo "REDIS_PORT=6379" >> .env
echo "REDIS_DB=0" >> .env
echo "REDIS_CACHE_TTL=3600" >> .env
```

### 3. 启动 Redis (可选但推荐)

```bash
docker run -d --name redis-ciphergenius -p 6379:6379 redis:7-alpine
```

### 4. 重启服务

```bash
# 后端
poetry run cipher-genius-api

# Celery Worker (可选)
poetry run celery -A cipher_genius.tasks.celery_tasks worker --loglevel=info

# 前端
cd frontend
npm run dev
```

## 兼容性说明

### 向后兼容

- 原有的 `MASOrchestrationService` 仍然可用
- 未启用 Redis 时，系统自动降级为无缓存模式
- 前端未使用 Zustand 的组件仍可正常工作

### 推荐迁移

- 新项目推荐使用 `LangGraphMASService`
- 生产环境推荐启用 Redis 缓存
- 前端组件推荐迁移到 Zustand 状态管理

## 已知问题

1. LangGraph MAS 与现有 API 集成尚未完全测试
2. Redis 缓存命中率需要实际场景验证
3. Celery Worker 长时间运行稳定性待验证
4. 前端状态管理与部分旧组件可能存在兼容性问题

## 维护补丁记录

- 2026-03-17
  - 修复 `use_langgraph=true` 引擎与 `schemas.py` 的返回契约不一致问题
  - Redis 缓存键改为稳定哈希（避免 Python 进程内置 `hash()` 导致跨进程不一致）
  - 返回中增加 `delivery.engine` / `delivery.cache_hit` 辅助排障与联调

## 后续计划

- LangGraph 并行节点执行 (Architect + Auditor)
- 基于向量相似度的 Skill 路由
- Skill 输入输出 schema 化
- 外部标准库集成 (NIST, IETF, ISO)
- 可版本化证据包
- 自动化测试向量验证

## 文档更新

- [README.md](README.md): 更新技术栈和快速启动
- [TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md): 新增架构升级章节
- [QUICK_START_V3.md](QUICK_START_V3.md): 更新为 v3.1 启动指南
- [DOC_INDEX.md](DOC_INDEX.md): 维护文档索引

## 贡献者

- CipherGenius Team
- 升级日期: 2026-03-10
