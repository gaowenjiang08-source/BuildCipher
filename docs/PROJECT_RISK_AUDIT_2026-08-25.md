# BuildCipher 项目风险与问题审计报告

**审计日期：** 2026-08-25  
**审计对象：** `D:\BC total\BuildCipher`  
**审计范围：** 后端运行机制、前端消费契约、本地沙盒、代码生成、知识检索、报告与记忆持久化、配置与安全、冗余及未接入模块  
**审计方式：** 源码静态阅读、调用链追踪、前后端字段核对、文档对照、Python 编译检查、前端生产构建检查  
**审计结论：** 项目已具备可运行的 BuildTrust localhost 演示主线，但通用密码实现执行、补丁回归真实性、运行时配置刷新和前后端契约一致性仍存在需要优先处理的问题。当前系统不应将通用场景的本地攻击结果直接解释为真实密码实现已经通过安全验证。

## 1. 项目运行机制概览

### 1.1 前端

- 技术栈：React + Vite。
- 入口：[frontend/src/main.jsx](../frontend/src/main.jsx)。
- 主要业务状态集中在 `App.jsx` 和 MAS 相关 hooks。
- Zustand 同时保留了早期 MAS、Skill、Settings、UI store，以及当前 runtime/session/attack loop store。
- 前端默认访问：
  - React/Vite：`http://127.0.0.1:5173`
  - FastAPI：`http://127.0.0.1:8000`

### 1.2 后端

- 技术栈：FastAPI + Pydantic + LangGraph。
- 主入口：[src/cipher_genius/api/main.py](../src/cipher_genius/api/main.py)。
- MAS 接口：
  - `POST /api/v1/mas/execute`
  - `POST /api/v1/mas/stream`
- 其他主要接口：
  - `POST /api/v1/generate`
  - `POST /api/v1/skills/execute`
  - `POST /api/v1/knowledge/ingest`
  - `GET /api/v1/cases/{case_id}/timeline`
  - `POST /api/v1/construction/demo/run`

### 1.3 MAS 主执行链

当前主链为：

```text
analyst
  -> context_builder
  -> architect
  -> audit
  -> engineer
  -> target_deployer
  -> attack_executor
  -> vulnerability_evaluation
  -> patch_reflection
  -> delivery
```

`/mas/execute` 和 `/mas/stream` 当前都会强制走 LangGraph 主线，`use_langgraph` 主要作为兼容字段保留。

### 1.4 执行与证据层

- 通用目标：使用 `LocalSandboxRuntime` 创建本地 HTTP 服务壳子。
- 建筑目标：使用建筑领域确定性 runtime，执行 BIM、IoT、证据账本相关的五类攻击。
- 沙盒执行通过 `LocalSandboxDispatcher` 统一记录：
  - 部署
  - 攻击
  - 补丁应用
  - 回滚
  - 回归重放
- case memory 与 timeline/replay 以本地 JSON 文件保存。
- 知识导入结果保存为本地 JSONL，并可选写入 Qdrant。

## 2. 严重风险总览

| 编号 | 严重性 | 问题 | 主要位置 |
|---|---|---|---|
| R-001 | 高 | 通用攻击回归没有真正执行生成代码 | `sandbox/local_runtime.py` |
| R-002 | 高 | 回归风险分数存在固定下降逻辑 | `core/langgraph_mas.py` |
| R-003 | 高 | 回滚后交付状态可能仍沿用补丁前或补丁中的验证结论 | `core/langgraph_mas.py` |
| R-004 | 中高 | 运行时设置刷新不完整 | `utils/redis_client.py`、`api/settings_service.py` |
| R-005 | 中 | 前后端响应字段漂移 | `frontend/src/features/mas/*`、`core/langgraph_mas.py` |
| R-006 | 中 | ErrorBoundary 已实现但没有接入应用根节点 | `frontend/src/main.jsx` |
| R-007 | 中 | 代码生成成功不代表生成了可运行的密码实现 | `codegen/generator.py`、`core/mas_runtime_support.py` |
| R-008 | 中 | Qdrant 当前主要保存 payload，未形成真正的向量检索闭环 | `retrieval/qdrant_store.py`、`retrieval/service.py` |
| R-009 | 中 | 本地 manifest、case memory、timeline 存在多进程并发写入边界 | `api/knowledge_ingestion_service.py`、`memory/*` |
| R-010 | 中 | 默认安全配置仍明显偏开发态 | `api/main.py`、`utils/config.py` |

## 3. 高风险问题

## R-001：通用攻击回归没有真正执行生成代码

**严重性：高**

### 证据

- 目标服务部署时确实写入：
  - `implementation.py`
  - `implementation.c`
  - `implementation.pseudo.txt`
- 相关代码见：
  - [local_runtime.py:177](../src/cipher_genius/sandbox/local_runtime.py#L177)
  - [local_runtime.py:185](../src/cipher_genius/sandbox/local_runtime.py#L185)
  - [local_runtime.py:186](../src/cipher_genius/sandbox/local_runtime.py#L186)
  - [local_runtime.py:187](../src/cipher_genius/sandbox/local_runtime.py#L187)
- 但攻击执行实际固定启动：
  - [local_runtime.py:569](../src/cipher_genius/sandbox/local_runtime.py#L569)
  - [local_runtime.py:574](../src/cipher_genius/sandbox/local_runtime.py#L574)
  - [local_runtime.py:884](../src/cipher_genius/sandbox/local_runtime.py#L884)
- `service_runtime.py` 中的 `/encrypt` 逻辑只是对输入字符串反转后进行十六进制编码：
  - [local_runtime.py:826](../src/cipher_genius/sandbox/local_runtime.py#L826)
  - [local_runtime.py:838](../src/cipher_genius/sandbox/local_runtime.py#L838)

### 实际影响

通用攻击阶段验证的是固定 HTTP 壳子的行为，而不是 MAS 生成或修补后的 Python/C 密码实现。因此：

1. baseline 攻击结果不能证明真实生成代码存在或不存在漏洞。
2. patch 后的 regression 结果不能证明补丁改变了实际密码行为。
3. `implementation.py` 的修改可能只会体现在 artifact 摘要中，不会反映到运行时行为。
4. 用户看到的“攻击已执行”“回归已完成”容易被误解为真实密码实现已经执行过安全测试。

### 建议

1. 将目标服务 runtime 改为根据 `entrypoint` 或 manifest 动态加载 `implementation.py`。
2. 对 Python 实现建立明确的服务适配协议，例如：
   - `encrypt(payload) -> dict`
   - `decrypt(payload) -> dict`
   - `health() -> dict`
3. 对 C 实现明确编译、加载和调用方式；无法执行时应将状态标记为 `not_executed`，不能伪装成已完成回归。
4. 在攻击结果中增加：
   - `executed_artifact`
   - `runtime_entrypoint`
   - `implementation_loaded`
   - `implementation_digest`
5. 将本地固定壳子明确命名为 `demo_shell`，并在前端和报告中显示“仅验证沙盒合同”。

## R-002：回归风险分数存在固定下降逻辑

**严重性：高**

### 证据

在 [langgraph_mas.py:2621](../src/cipher_genius/core/langgraph_mas.py#L2621) 的 `_build_regression_vulnerability_report()` 中：

```python
baseline_risk = int(report.get("risk_score", 0))
residual_risk = max(0, baseline_risk - 15)
```

### 实际影响

风险分数不是根据回归攻击结果、实际 finding 或补丁后的运行行为计算，而是固定减少 15。因此：

- 即使补丁未被加载，也可能得到下降后的风险分数。
- 风险分数可能与 `regression_attack_results` 不一致。
- 报告、前端指标和 case memory 会记录一个看似量化、实则规则推导的“风险收敛”结果。

### 建议

1. 删除固定减分逻辑。
2. 回归风险应由 `VulnerabilityEvaluationAgent` 基于：
   - 回归攻击结果
   - finding 数量与严重性
   - blocked/pass 状态
   - 关键控制项是否通过
   - baseline 与 regression 差异
   统一计算。
3. 如果暂时只能使用演示规则，应将字段命名为：
   - `demo_residual_risk_score`
   - `estimated_risk_score`
4. 正式 `risk_score` 应附带：
   - `score_source`
   - `score_method`
   - `evidence_refs`
   - `measured_at`

## R-003：回滚后交付状态可能仍沿用补丁验证结论

**严重性：高**

### 证据

建筑回归失败时，系统会执行回滚并把目标服务更新为：

- [langgraph_mas.py:1354](../src/cipher_genius/core/langgraph_mas.py#L1354)
- [langgraph_mas.py:1366](../src/cipher_genius/core/langgraph_mas.py#L1366)
- [langgraph_mas.py:1368](../src/cipher_genius/core/langgraph_mas.py#L1368)

补丁执行报告随后更新为 `rolled_back`：

- [langgraph_mas.py:1413](../src/cipher_genius/core/langgraph_mas.py#L1413)
- [langgraph_mas.py:1416](../src/cipher_genius/core/langgraph_mas.py#L1416)

但 `regression_vulnerability_verdict` 和 `regression_attack_results` 已经在此前生成，并继续进入 delivery：

- [langgraph_mas.py:1372](../src/cipher_genius/core/langgraph_mas.py#L1372)
- [langgraph_mas.py:1389](../src/cipher_genius/core/langgraph_mas.py#L1389)
- [langgraph_mas.py:1779](../src/cipher_genius/core/langgraph_mas.py#L1779)

### 实际影响

同一个响应中可能同时出现：

- `patch_execution.status = "rolled_back"`
- `regression_vulnerability_verdict` 显示补丁版本残余风险
- delivery 仍保留补丁版本攻击结果

用户可能无法判断当前系统最终实际运行的是：

- baseline
- patched
- rolled back

### 建议

1. 明确区分：
   - `observed_patched_result`
   - `effective_final_state`
2. 回滚后将最终状态明确设为：

```json
{
  "effective_version": "baseline",
  "patch_effective": false,
  "patch_status": "rolled_back",
  "regression_result_status": "invalidated_after_rollback"
}
```

3. 回滚后重新执行一次 baseline 健康检查或关键探针，确认恢复状态。
4. 前端展示“补丁验证结果”和“当前生效状态”两个独立区域。
5. 报告中不得把已回滚的补丁版本结果直接作为当前生产状态结论。

## 4. 中高风险问题

## R-004：运行时设置刷新不完整

**严重性：中高**

### 证据

- [utils/config.py:94](../src/cipher_genius/utils/config.py#L94) 使用 `lru_cache` 缓存 `Settings`。
- [redis_client.py:17](../src/cipher_genius/utils/redis_client.py#L17) 在模块加载时缓存全局 `settings`。
- [redis_client.py:26](../src/cipher_genius/utils/redis_client.py#L26) 在实例初始化时缓存 `_enabled`。
- [settings_service.py:177](../src/cipher_genius/api/settings_service.py#L177) 只调用：

```python
get_settings.cache_clear()
```

- [langgraph_mas.py:202](../src/cipher_genius/core/langgraph_mas.py#L202) 和 [langgraph_mas.py:236](../src/cipher_genius/core/langgraph_mas.py#L236) 继续使用既有的 Redis client 和模块级 settings。

### 实际影响

运行期间通过设置接口修改 `.env` 后，下列配置可能仍使用旧值：

- Redis 是否启用
- Redis host/port/db/password
- Qdrant 地址
- 缓存开关
- API 配置
- LLM provider 默认值

此外：

- `.env.example` 中 `REDIS_ENABLED=false`
- [utils/config.py:62](../src/cipher_genius/utils/config.py#L62) 中默认 `redis_enabled=True`

两者存在认知不一致。

### 建议

1. 不在模块级缓存完整 settings 对象。
2. `RedisClient` 增加显式 `refresh()` 或按配置版本重新初始化。
3. 设置写入后统一刷新：
   - settings provider
   - Redis client
   - retrieval service
   - MAS runtime service
4. 为每次配置更新增加 `settings_version`。
5. 统一 `.env.example` 与代码默认值。
6. 设置接口返回实际生效状态，而不是只返回写入文件状态。

## 5. 前后端契约与前端问题

## R-005：前后端响应字段漂移

**严重性：中**

### 证据

后端主要输出：

- `delivery.attack_loop.expert_gate_decision`
- `delivery.next_action`
- `delivery.production_guide`

相关位置：

- [langgraph_mas.py:1764](../src/cipher_genius/core/langgraph_mas.py#L1764)
- [langgraph_mas.py:1869](../src/cipher_genius/core/langgraph_mas.py#L1869)
- [langgraph_mas.py:1753](../src/cipher_genius/core/langgraph_mas.py#L1753)

前端仍存在旧字段读取：

- [RuntimeConsoleView.jsx:637](../frontend/src/features/mas/RuntimeConsoleView.jsx#L637) 读取 `attackLoop.expert_gate`
- 同行读取 `attackLoop.next_action`
- [ReportsSummaryPanels.jsx:317](../frontend/src/features/mas/ReportsSummaryPanels.jsx#L317) 读取：
  - `delivery.production_ready`
  - `delivery.production_ready_label`

### 实际影响

部分 UI 会显示空值或 fallback 文案，造成：

- 专家闸门实际有决策，但 UI 显示“等待决策”。
- 下一步动作出现在 delivery，但运行时控制台无法显示。
- 生产化判断组件可能一直显示缺失状态。

### 建议

1. 建立单一前端响应适配层，例如 `normalizeMasResponse.js`。
2. 所有组件只消费标准化后的字段。
3. 后端提供正式 schema，而不是把复杂结构长期放在 `Dict[str, Any]`。
4. 对旧字段设置兼容读取期限，并记录弃用时间。
5. 增加契约测试，至少覆盖：
   - `expert_gate_decision`
   - `next_action`
   - `production_guide`
   - `production_ready`

## R-006：ErrorBoundary 已实现但没有接入应用根节点

**严重性：中**

### 证据

- ErrorBoundary 已实现：
  - [ErrorBoundary.jsx:46](../frontend/src/components/ErrorBoundary.jsx#L46)
- 但应用根节点直接渲染 App：
  - [main.jsx:6](../frontend/src/main.jsx#L6)

### 实际影响

React 运行时异常未被根级边界捕获时，可能导致整个页面白屏。现有 `ComponentErrorBoundary` 也没有证据表明已覆盖所有高风险异步视图。

### 建议

在 `main.jsx` 中将 App 包裹在 `ErrorBoundary` 中，并对以下区域增加局部边界：

- MAS 主工作台
- Runtime Console
- Reports
- Construction Workspace
- Knowledge/Ops 页面

同时避免在生产界面直接展示完整 stack trace，改为：

- 用户可见的简短错误信息
- 可复制的 error id
- 开发模式下才显示 stack trace

## R-007：代码生成成功不代表生成了可运行的密码实现

**严重性：中**

### 证据一：生成器 fallback 未实现加解密

[generator.py:186](../src/cipher_genius/codegen/generator.py#L186) 的 fallback Python 代码包含：

- `TODO: Initialize components`
- `TODO: Implement`
- `raise NotImplementedError`

相关位置：

- [generator.py:220](../src/cipher_genius/codegen/generator.py#L220)
- [generator.py:232](../src/cipher_genius/codegen/generator.py#L232)
- [generator.py:245](../src/cipher_genius/codegen/generator.py#L245)

### 证据二：MAS runtime fallback 是 passthrough

[mas_runtime_support.py:1329](../src/cipher_genius/core/mas_runtime_support.py#L1329) 生成的 fallback Python 实现：

```python
def encrypt(self, data: bytes) -> bytes:
    return data

def decrypt(self, data: bytes) -> bytes:
    return data
```

### 实际影响

系统可能同时显示：

- Python compile passed
- C compile passed
- code artifacts ready

但这些状态只证明代码文本可解析或模板可编译，不证明：

- 加解密正确性
- 密钥长度和 nonce 使用正确
- 认证标签有效
- 解密失败路径安全
- 完整性校验存在
- 密码学组件被实际调用

### 建议

1. 将代码状态拆分为：
   - `syntax_valid`
   - `compile_valid`
   - `functional_test_passed`
   - `cryptographic_test_passed`
   - `runtime_loaded`
2. fallback 不应默默使用明文 passthrough。
3. 如果没有可运行实现，应明确返回 `implementation_pending`。
4. 增加固定离线测试：
   - encrypt/decrypt round trip
   - wrong key
   - wrong nonce
   - tampered ciphertext
   - malformed input
   - empty input
5. 只有功能测试和安全测试通过后，才能将代码标记为“可运行代码”。

## 6. 知识检索与持久化问题

## R-008：Qdrant 当前主要保存 payload，未形成真正向量检索闭环

**严重性：中**

### 证据

- [qdrant_store.py:20](../src/cipher_genius/retrieval/qdrant_store.py#L20) 默认 `vector_size=1`。
- [qdrant_store.py:126](../src/cipher_genius/retrieval/qdrant_store.py#L126) 生成全零向量。
- [retrieval/service.py:861](../src/cipher_genius/retrieval/service.py#L861) 使用 `scroll` 获取 payload。
- [retrieval/service.py:716](../src/cipher_genius/retrieval/service.py#L716) 主要通过关键词分数排序。
- 语义 embedding 只有在配置开启时才会由本地 `SentenceTransformer` 临时计算：
  - [retrieval/service.py:804](../src/cipher_genius/retrieval/service.py#L804)
  - [retrieval/service.py:825](../src/cipher_genius/retrieval/service.py#L825)

### 实际影响

当前 Qdrant 更接近：

```text
结构化 payload 存储 + 过滤 + 本地关键词排序
```

而不是：

```text
真实 embedding 生成 + 向量 upsert + similarity search
```

这会导致文档中“知识库检索”与实际运行机制不完全一致。

### 建议

1. 明确系统的检索模式：
   - `keyword_local`
   - `payload_qdrant`
   - `semantic_qdrant`
2. 若需要真正向量检索：
   - 使用稳定 embedding provider
   - 根据 embedding 维度创建 collection
   - upsert 实际向量
   - 使用 `search` 或 `query_points`
3. 在 evidence pack 中记录：
   - `retrieval_mode`
   - `embedding_model`
   - `vector_dimension`
   - `query_method`
4. Qdrant 不可用时应明确返回降级状态，而不是只静默 fallback。

## R-009：本地 manifest、case memory、timeline 存在多进程并发写入边界

**严重性：中**

### 证据

知识导入 manifest：

- [knowledge_ingestion_service.py:265](../src/cipher_genius/api/knowledge_ingestion_service.py#L265)
- [knowledge_ingestion_service.py:305](../src/cipher_genius/api/knowledge_ingestion_service.py#L305)

case memory：

- [memory/service.py:54](../src/cipher_genius/memory/service.py#L54)
- [memory/service.py:59](../src/cipher_genius/memory/service.py#L59)

timeline：

- [memory/replay_service.py:2067](../src/cipher_genius/memory/replay_service.py#L2067)
- [memory/replay_service.py:2071](../src/cipher_genius/memory/replay_service.py#L2071)

这些锁主要是对象实例级 `threading.Lock`，无法覆盖多 worker、多进程或多个 API 实例之间的并发写入。

### 实际影响

在多 worker 或部署到多个进程时，可能出现：

- manifest 更新互相覆盖
- case memory 丢失后一轮写入
- timeline snapshot 顺序不稳定
- 同一 case 的事件被覆盖
- 临时文件冲突

### 建议

1. localhost 单进程模式下明确声明该限制。
2. 生产或多 worker 模式迁移到：
   - SQLite
   - PostgreSQL
   - 或具备原子条件更新能力的存储
3. 为 timeline 增加：
   - optimistic locking
   - version number
   - conflict retry
4. manifest 记录使用数据库表替代 JSON 数组。
5. 增加多线程、多进程并发测试。

## 7. 安全配置与部署问题

## R-010：默认安全配置仍明显偏开发态

**严重性：中**

### 证据

- [main.py:108](../src/cipher_genius/api/main.py#L108) 使用：

```python
allow_origins=["*"]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

- [utils/config.py:70](../src/cipher_genius/utils/config.py#L70) 默认 `debug=True`。
- [utils/config.py:72](../src/cipher_genius/utils/config.py#L72) 默认监听 `0.0.0.0`。
- [utils/config.py:82](../src/cipher_genius/utils/config.py#L82) 默认关闭 API key。
- `API_KEY_ENABLED` 在配置中存在，但没有确认所有 API 路由都统一执行认证。

### 实际影响

当前配置适合本机演示，不适合作为生产部署默认值。若用户直接暴露端口，可能出现：

- 任意来源跨域访问
- 未认证接口调用
- debug/reload 行为泄露运行信息
- 远程提交耗时 MAS 任务
- 未授权访问知识导入和 case 数据

### 建议

1. 生产默认值：
   - `DEBUG=false`
   - `API_KEY_ENABLED=true`
   - `API_HOST=127.0.0.1` 或明确反向代理部署
2. CORS 改为显式白名单。
3. 使用统一 FastAPI dependency 保护 API。
4. 对上传、MAS 执行、报告生成增加：
   - 请求大小限制
   - 超时
   - 并发限制
   - 速率限制
5. 增加安全响应头 middleware。
6. 将 localhost demo 与 production profile 分离。

## 8. 冗余、未接入和维护问题

## R-011：未接入主运行链的模块较多

**严重性：低到中**

项目已有审计文档 [CODE_AUDIT_UNUSED.md](./CODE_AUDIT_UNUSED.md) 列出以下未被默认主链直接引用的模块：

### Features

- `src/cipher_genius/features/attack_simulator.py`
- `src/cipher_genius/features/benchmark_runner.py`
- `src/cipher_genius/features/cost_estimator.py`
- `src/cipher_genius/features/recommender.py`
- `src/cipher_genius/features/threat_modeler.py`
- `src/cipher_genius/features/tutorials.py`
- `src/cipher_genius/features/tutorials_enhanced.py`

### 基础设施与辅助模块

- `src/cipher_genius/utils/monitoring.py`
- `src/cipher_genius/utils/rate_limiter.py`
- `src/cipher_genius/utils/security.py`
- `src/cipher_genius/core/scheme_detector.py`
- `src/cipher_genius/core/validator.py`

### 影响

- 新成员难以判断哪些代码是真实运行路径。
- 静态分析和测试范围容易被误解。
- 旧模块可能继续产生重复 schema、重复逻辑和依赖。
- 未接入能力看起来像“已经实现”，但实际不可从主入口调用。

### 建议

为每个模块增加明确状态：

```text
active
experimental
not_wired
deprecated
```

并将实验能力迁移到：

```text
src/cipher_genius/features/experimental/
```

或已明确下线的 `deprecated/`。

## R-012：Legacy MAS、Celery、Streamlit 和旧入口仍长期保留

**严重性：低到中**

目前仓库同时存在：

- LangGraph MAS
- legacy MAS
- Celery 相关代码
- Streamlit v3
- Streamlit legacy
- 早期启动文档和旧品牌文案

文档 [LANGGRAPH_INTEGRATION.md](./LANGGRAPH_INTEGRATION.md) 仍描述 LangGraph 与 legacy 可自由选择，但当前 API 已强制 LangGraph 主线，存在文档与实际行为不一致。

### 建议

1. 明确：
   - active mainline
   - compatibility only
   - deprecated
2. legacy 入口增加显式 warning。
3. 在下一次大版本中删除不再需要的旧入口。
4. 将旧文档移入 `docs/archive/`。
5. 为旧 API 提供截止日期和迁移说明。

## R-013：前端存在早期 Zustand store 冗余

**严重性：低**

[frontend/src/store/index.js](../frontend/src/store/index.js) 同时保留：

- `useMASStore`
- `useSkillStore`
- `useSettingsStore`
- `useUIStore`
- `useRunDraftStore`
- `useRunSessionStore`
- `useStageConsoleStore`
- `useAttackLoopStore`

前四个 store 基本没有被当前主应用引用，后四个是当前 runtime 相关状态。

### 建议

1. 确认旧 store 是否仍被外部页面或兼容入口使用。
2. 若无引用，迁移或删除前四个 store。
3. 将当前 store 按领域拆分文件：

```text
store/
  runDraftStore.js
  runSessionStore.js
  stageConsoleStore.js
  attackLoopStore.js
```

4. 删除未使用的 `useLangGraph` 等兼容状态，或明确其生命周期。

## R-014：品牌、端口和启动文档不一致

**严重性：低**

发现的旧内容包括：

- `使用说明.txt` 仍使用 CipherGenius v1.1.0。
- `README_IMPORTANT.txt` 仍描述 Streamlit 8503。
- 多个 HTML/SVG 文档仍使用 MedCipher Studio。
- 当前主 README 使用 BuildTrust Studio。
- 当前前端/API 端口为 5173/8000。
- 部分历史文档仍描述 Streamlit 或旧 MAS 引擎为主入口。

### 实际影响

用户可能按照旧文档启动错误服务、访问错误端口或误解当前产品定位。

### 建议

1. 根目录只保留一份当前快速开始文档。
2. 历史文档移到 `docs/archive/`。
3. 所有启动方式统一引用：
   - `start.bat`
   - `start_api.bat`
   - `start_frontend.bat`
4. 统一品牌为 BuildTrust。
5. 文档头部增加：

```text
status: active | deprecated | archive
last_updated: YYYY-MM-DD
```

## 9. 文档与产品边界问题

## R-015：通用沙盒能力容易被误解为生产级攻击平台

**严重性：中**

项目文档已经说明当前执行面是 localhost 受限进程，但部分 workflow 文案使用“executed regression”“patch validation”等表述，容易使读者误认为已经具备：

- 真实业务服务执行
- 容器隔离
- 生产级补丁部署
- 真实攻击器
- 生产 PKI/KMS/HSM
- 完整 IFC/CDE/IoT 语义

当前真正完成的是：

- 本地受限进程服务壳子
- 建筑领域确定性演示 runtime
- dispatcher 审批和证据工件
- 本地 timeline/replay

### 建议

在 API、前端、报告和文档中统一区分：

```text
demo_shell
local_restricted_process
construction_deterministic_demo
production_runtime
remote_executor
```

避免用同一个“executed/validated”状态覆盖不同真实性等级。

## 10. 已确认的正向设计

本次审查也确认了以下设计基础是合理的：

1. LangGraph 主链是真实 `StateGraph`，不是简单字段兼容层。
2. dispatcher 具备：
   - 执行器能力矩阵
   - 策略校验
   - dispatch id
   - 审计事件
   - handoff contract
3. 建筑场景拥有：
   - BIM/IFC 目标
   - IoT 网关目标
   - 证据账本目标
   - 五类确定性攻击
   - hardened profile 与回滚验证
4. case memory 与 replay timeline 支持：
   - 原子临时文件替换
   - 查询过滤
   - typed memory
   - handoff 摘要
   - dispatch 摘要
5. 已有测试覆盖：
   - 主链
   - 建筑 runtime
   - 记忆
   - dispatcher
   - 报告
   - API

这些能力适合继续作为 localhost 演示和可解释执行底座，但需要补齐真实性标记和生产边界。

## 11. 修复优先级建议

### P0：先修复可信性问题

1. R-001：让通用沙盒真正加载并执行生成实现，或明确标注为 demo shell。
2. R-002：删除固定风险分数下降，改为基于攻击证据计算。
3. R-003：回滚后重新建立最终生效状态，不复用失效的补丁验证结论。

### P1：修复运行稳定性和前后端一致性

4. R-004：完善设置刷新和 Redis client 生命周期。
5. R-005：建立统一响应适配层和契约测试。
6. R-006：接入根级 ErrorBoundary。
7. R-007：区分语法、编译、功能和密码学验证状态。

### P2：完善数据与部署能力

8. R-008：明确 Qdrant 是 payload 检索还是向量检索，并补足真实 vector search。
9. R-009：将多进程持久化迁移到 SQLite/PostgreSQL。
10. R-010：拆分 localhost 与 production 配置 profile。

### P3：降低维护成本

11. R-011：标记未接入模块状态。
12. R-012：整理 legacy/Streamlit/Celery 兼容入口。
13. R-013：清理前端早期 store。
14. R-014：统一品牌、端口和启动文档。
15. R-015：统一演示能力与生产能力的产品边界表述。

## 12. 验证记录与限制

### 已执行

- Python 3.12.13：

```text
python -m compileall -q src tests
结果：通过
```

- 前端：

```text
npm ci
npm run build
结果：通过
Vite 转换模块数：91
```

- Git 工作区：

```text
main 分支
工作区干净
未修改业务代码
```

### 未执行

后端 pytest 未执行，原因：

- 当前可用 Python 3.12 环境没有安装 `pytest`。
- Poetry 不在 PATH 中。
- 系统 `py -3` 指向 Python 3.2.2，不满足项目要求的 Python 3.10+。
- 当前无法确认完整 Poetry 虚拟环境是否已经安装所有项目依赖。

因此，本报告中的问题结论主要来自源码和调用链证据，不能替代完整运行环境下的单元测试、集成测试和端到端测试。

## 13. 建议新增的测试

### 沙盒真实性

- 验证 `implementation.py` 被实际导入。
- 验证 patch 前后运行时 digest 不同。
- 验证 patch 后攻击结果来自 patched artifact。
- 验证回归失败后最终 effective version 为 baseline。

### 风险评分

- 回归攻击未执行时不得生成 validated 风险结论。
- 回归 finding 未减少时风险分数不得自动下降。
- 风险分数必须关联 evidence refs。

### 配置刷新

- 修改 `.env` 后 Redis enabled 状态立即变化。
- 修改 Qdrant 地址后新请求使用新地址。
- 已存在的 client 不得继续使用旧配置。

### 前后端契约

- `expert_gate_decision` 能在控制台显示。
- `delivery.next_action` 能在所有相关页面显示。
- `production_ready` 缺失时前端显示明确的“未提供”而不是空白。

### 并发持久化

- 多线程同时写入同一个 case。
- 多进程同时更新 manifest。
- timeline 事件顺序和 snapshot 数量保持一致。

## 14. 最终结论

BuildCipher 当前已经形成一条结构完整的 BuildTrust localhost 演示系统，架构层面包含编排、执行、证据、回放和交付等主要部件。

但从可信性角度看，最需要优先处理的是：

1. 通用攻击链没有执行真实生成代码。
2. 回归风险分数存在固定算法下降。
3. 回滚后的最终生效状态与验证结论没有完全分离。
4. 前后端字段契约仍有漂移。
5. 代码“编译通过”与密码功能“可运行、可验证”之间仍存在明显差距。

在这些问题修复前，系统适合定位为：

> 面向建筑数字资产可信交付的 localhost 多智能体演示与证据编排平台，具备确定性建筑安全演示能力，但尚不应宣称通用密码实现已完成生产级攻击验证或补丁回归验证。
