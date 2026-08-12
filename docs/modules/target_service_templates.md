# 目标服务模板（Target Service Template）设计

最后更新：2026-03-27
状态：active
适用范围：`src/cipher_genius/sandbox/`、`src/cipher_genius/core/langgraph_mas.py`、`src/cipher_genius/api/schemas.py`、后续 target service mock / baseline / patched / regression 演示链路

## 1. 本文目的

本文回答 4 个问题：

1. 模拟服务器端在当前项目里到底是什么
2. 为什么不能继续把目标服务写成临时脚本壳子
3. 模板最小 schema 应该长什么样
4. 它如何服务沙盒执行、可视化和回归验证

这不是产品文案，而是后续实现 mock target service 的后端设计入口。

## 2. 定位

当前项目里的“模拟服务器端”不应理解为真实业务服务器，也不应理解为随手生成的一段 demo 脚本。

更准确的定义是：

- 可部署
- 可观测
- 可攻击
- 可回归

的 `target service template runtime`

它的目标是为攻击、评估、修补、回归这条闭环提供一个稳定、可复用的目标实例，而不是追求业务复杂度本身。

## 3. 为什么需要模板化

如果继续依赖临时脚本壳子，会出现 4 个问题：

1. 部署协议不稳定
   - 每个服务的启动方式、健康检查、端口和工件目录都可能不同
2. 回归验证难复现
   - baseline / patched / regression 难以稳定对齐
3. telemetry 不统一
   - 前端和评测层无法依赖稳定字段做可视化和回放
4. 扩展成本高
   - 每加一个新服务都像重新造一个小型 runtime

所以目标服务应被收口成“模板 + manifest + runtime profile”的组合，而不是脚本碎片。

## 4. 推荐对象分层

### 4.1 Service Template

定义目标服务是什么。

建议至少包含：

- `template_id`
- `template_label`
- `service_kind`
- `attack_surface_kind`
- `supported_versions`
- `default_runtime`

### 4.2 Deployment Manifest

定义如何拉起目标服务。

建议至少包含：

- `service_id`
- `template_id`
- `version_id`
- `entrypoint`
- `port`
- `healthcheck`
- `workspace_dir`
- `artifact_dir`

### 4.3 Runtime Profile

定义运行时预算和观测方式。

建议至少包含：

- `timeout_seconds`
- `cpu_budget`
- `memory_budget_mb`
- `probe_budget`
- `traffic_sampling_interval_ms`
- `cleanup_policy`

### 4.4 Telemetry Contract

定义前端和下游 agent 能稳定看到什么。

建议至少包含：

- `service_port`
- `service_base_url`
- `service_health_url`
- `probe_count`
- `traffic_series`
- `runtime_info`
- `service_stdout_log`

## 5. 最小 schema 建议

```json
{
  "template_id": "mock_crypto_http_v1",
  "template_label": "模拟加密 HTTP 服务",
  "service_kind": "crypto_api",
  "attack_surface_kind": "http-json",
  "version_id": "baseline",
  "deployment_manifest": {
    "entrypoint": "service_runtime.py",
    "port": 18080,
    "healthcheck": "/health",
    "workspace_dir": ".cache/sandbox/<run_id>/svc-001/",
    "artifact_dir": ".cache/sandbox/<run_id>/svc-001/artifacts/"
  },
  "runtime_profile": {
    "timeout_seconds": 120,
    "memory_budget_mb": 256,
    "probe_budget": 64,
    "traffic_sampling_interval_ms": 250,
    "cleanup_policy": "stop_and_archive"
  }
}
```

## 6. 推荐模板类型

后续不必一开始做很多种，先做少量高复用模板即可。

建议第一批：

- `mock_crypto_http_v1`
  - 面向 HTTP/JSON 的加密接口服务
- `mock_key_management_v1`
  - 面向密钥托管 / 轮换 / 错误处理边界
- `mock_file_encryption_worker_v1`
  - 面向离线加解密流程与工件回放

第一阶段最值得做的是 `mock_crypto_http_v1`，因为它最适合：

- baseline / patched / regression 三段演示
- telemetry 展示
- 攻击事件流回放

## 7. 与主链的关系

推荐关系如下：

1. `Generation / Engineer`
   - 产出候选实现和代码工件
2. `Target Deployer`
   - 将候选实现映射到 `target service template`
3. `Sandbox Dispatcher`
   - 校验部署与攻击预算
4. `LocalSandboxRuntime`
   - 按 manifest 拉起实例
5. `AttackPlanningAgent`
   - 针对模板暴露面的稳定 contract 做攻击规划
6. `Vulnerability / Patch / Reflection`
   - 消费统一 telemetry 和 artifact

这层的关键意义是：

- planner 面向稳定 target contract 做决策
- 可视化面向稳定 telemetry contract 做展示
- regression 面向稳定 version contract 做对比

## 8. 与可视化的关系

目标服务模板不是只服务执行面，也要服务前端透明化。

推荐前端直接消费以下稳定字段：

- `template_label`
- `version_id`
- `deployment_status`
- `service_port`
- `service_health_url`
- `probe_count`
- `traffic_series`

推荐前端展示 3 层：

1. `服务实例`
   - 当前模板、版本、端口、健康状态
2. `攻击态势`
   - 流量曲线、任务数、finding 数
3. `版本演化`
   - baseline / patched / regression 对比

## 9. 当前边界

当前要讲清楚：

- 已完成的是“本地受限进程目标服务壳子”
- 目标服务模板设计现在已明确
- 还没完成的是“模板化实现 fully productized”

更不能误写成：

- 生产级业务服务编排平台
- 容器级多租户安全执行底座

## 10. 推荐落地顺序

1. 先定义模板 schema
2. 先实现一套 `mock_crypto_http_v1`
3. 让 baseline / patched / regression 都使用同一模板族
4. 再把 telemetry 契约固定给前端
5. 最后再考虑容器化或远程执行

## 11. 验证方式

至少应验证：

- 同一模板能稳定完成 baseline 部署
- patch 后能生成 patched 版本并重部署
- regression 轮能沿同一模板再次探测
- `traffic_series` 等 telemetry 在三轮之间口径一致
- 前端能稳定展示模板名、版本号、运行状态和流量波动

## 12. 关联文档

- `docs/modules/backend_execution_architecture.md`
- `docs/modules/mas_workflow.md`
- `TODO_VIBING.md`
- `REMAIN.md`

## 13. 2026-03-27 落地状态补记

- 当前已落地的代码入口：
  - `src/cipher_genius/sandbox/target_templates.py`
  - `src/cipher_genius/sandbox/local_runtime.py`
  - `src/cipher_genius/core/langgraph_mas.py`
  - `src/cipher_genius/core/attack_planning_agent.py`
- 当前已稳定落地的模板字段：
  - `template_id / template_label`
  - `service_kind / attack_surface_kind`
  - `supported_versions`
  - `planner_skill_hints / planner_retrieval_hints`
  - `deployment_manifest / runtime_profile`
- 当前执行链已形成：
  - 模板构建
  - projection artifact 传递
  - planner 恢复模板上下文
  - runtime 物化部署 manifest
- 当前推荐验证：
  - `poetry run pytest tests/unit/test_target_service_templates.py -q --no-cov`
  - `poetry run pytest tests/unit/test_attack_planning_agent.py -q --no-cov`
- 当前边界：
  - 已完成 `mock_crypto_http_v1` 的稳定模板化
  - 已完成 retrieval-aware planner 第一版接线
  - 尚未完成更多模板族与更强 lesson-aware planner 增强
