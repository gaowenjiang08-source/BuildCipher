# BuildTrust 架构总览

## 运行入口

- React/Vite：`http://127.0.0.1:5173`
- FastAPI：`http://127.0.0.1:8000`
- 建筑 benchmark：`GET /api/v1/benchmarks/construction`
- 五攻击演示：`POST /api/v1/construction/demo/run`
- MAS：`POST /api/v1/mas/execute` 与 `POST /api/v1/mas/stream`

## 四层结构

1. 体验层：BuildTrust 五个建筑业务视图和专家视图；
2. 编排层：LangGraph 需求、架构、审计、工程、攻击、修补、交付主链；
3. 执行层：建筑目标模板、五攻击 runtime、localhost provider、回滚与证据工件；
4. 证据层：case memory、timeline/replay、知识引用、报告模板、IFC/CDE/IoT 状态。

## 关键数据流

```text
建筑需求
  -> construction structured spec
  -> 建筑 Skill 路由
  -> 候选密码策略与审计
  -> BIM / IoT / 证据账本目标
  -> baseline 五攻击
  -> hardened 控制配置
  -> 五攻击回归或回滚
  -> evidence refs / case memory / report
```

## 边界

当前执行面只验证 localhost 合同，不等同于商业 CDE、生产 PKI/KMS/HSM、分布式 IoT、完整 IFC 语义或正式合规认证。LLM provider 与本地密码 provider 相互独立。
