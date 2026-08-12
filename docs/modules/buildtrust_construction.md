# MedCipher BuildTrust 建筑领域底座

状态：第一版已落地；P2 IFC/CDE 合同与单主机 IoT 持久化基础已完成  
最后更新：2026-08-12

## 定位

BuildTrust 将现有密码策略与多 Agent 攻防闭环用于建筑数字资产可信协同。第一阶段场景是 BIM/IFC 可信交付与一条工地 IoT 验收证据链。当前代码提供领域数据合同、Skill/模板/Benchmark、三类目标服务合同和五攻击本地演示运行时；尚未把本地演示等同于生产部署。

最新逐项状态见 `BUILDTRUST_CAPABILITY_STATUS.md`。

## 已实现合同

- `src/cipher_genius/models/construction.py`
  - 参与方、项目角色、资产类型、生命周期、敏感度、批准状态、访问授权和项目上下文；
- `data/skills/`
  - `bim_model_exchange_guard`
  - `construction_iot_trust_architect`
  - `construction_collaboration_ip_guard`
  - `inspection_evidence_chain_designer`
  - `built_asset_pqc_migration_advisor`
  - `trusted_construction_crypto_reviewer`
- `data/report_templates/`
  - `construction_trusted_delivery`
  - `construction_iot_evidence_delivery`
  - `built_asset_pqc_transition_delivery`
- `data/benchmarks/construction_trusted_delivery.yaml`
  - 7 个建筑路由与模板回归案例；
- `src/cipher_genius/sandbox/target_templates.py`
  - `bim_package_exchange_v1`
  - `construction_iot_gateway_v1`
  - `project_evidence_ledger_v1`

## API

`GET /api/v1/benchmarks/construction` 返回建筑 Benchmark 的 Skill 命中率、模板命中率、章节覆盖率和逐案例结果。

`POST /api/v1/construction/demo/run` 执行 IFC 篡改、版本回滚、分包越权、设备冒充和遥测重放，输出 artifact、evidence、修补建议和回归结果。

LangGraph 对三类建筑目标的 baseline、retry、regression 路径统一生成五条领域 attack spec。结果进入现有漏洞裁决、补丁规划与 reflection 合同；完整结果保存在 delivery/replay，证据引用同步到 case memory。

MAS 基线工作区默认使用 `baseline` 控制配置，五类攻击可成功；补丁应用将工作区切换到 `hardened`，回归应阻断五类攻击。补丁前配置保存在独立快照中。若建筑回归缺少结果、结果未执行或任一 `regression_passed` 不为真，LangGraph 会调用 dispatcher 恢复补丁前配置并验证摘要一致性。独立 demo API 默认运行 `hardened` 参考实现，因此仍返回五类阻断结果。

`frontend/src/features/construction/` 提供第一版建筑业务 View Model 与五个业务视图：工程总览、项目工作台、可信协同、安全验证、可信交付。该界面展示本地证据闭环，不代表已连接生产 CDE/BIM 或 IoT 平台。

`data/demo/buildtrust_v1/` 与 `scripts/validate_buildtrust_v1.py` 固定赛事第一版的 IFC 输入摘要、`baseline 0/5 -> hardened 5/5`、密码操作回执、撤销门禁、轮换到期和证书失效验收合同，便于比赛现场无外部服务复验。

P2 localhost 路径通过 `LocalReferenceHMACProvider` 统一执行 BIM manifest 签名/验签与 IoT MAC，API 返回本地 provider 模式，证据对象保留 SQLite 操作回执。LLM 接口继续独立保留。

无外部 LLM 的完整 LangGraph 验收已通过：建筑领域与 BIM 模板路由正确，baseline 为 0/5 阻断，hardened 回归为 5/5 阻断，证据引用进入 case memory。外部 LLM 模式仍待凭据可用时验证。

```json
{
  "project_id": "buildtrust-demo-project",
  "run_id": "optional-stable-run-id"
}
```

响应中的 `capability_boundary` 是强制能力边界说明，前端和报告不应隐藏。

## 解析与检索

解析 fallback 和 MAS 结构化摘要会识别 BIM、IFC、建筑、施工、工地、工程验收和图纸信号，并将领域标记为 `construction`。检索过滤也优先选择建筑 Skill、报告模板和 Benchmark 案例。`ISO_19650` 在当前结构化摘要中是建筑信息管理参考口径，不代表自动合规认证。

## 密码组件元数据

`Component` 新增可选的 `security_profile`、`standard` 和 `implementation_sources`：

- `security_profile` 区分经典安全位数、原像/碰撞强度、NIST PQC 类别和证明模型；
- `standard` 保存标准机构、编号、标准名称、状态和复核时间；
- `implementation_sources` 指向成熟 SDK 或托管密码服务，并保留验证状态。

AES、ML-KEM（历史文件名 `kyber.yaml`）和 ML-DSA 已作为首批结构化样例。知识记录只用于检索、选型和证据引用，不能替代经过验证的生产密码实现。

## P0-B 已实现的本地演示能力

- IFC 文件字节摘要、manifest 验真和当前批准版本检查；
- 完整交付包角色授权；
- IoT 设备注册、HMAC 消息认证、计数器/nonce/时间窗口；
- 追加式签名哈希链；
- 五类攻击 artifact 和修补后回归。

## 尚未实现

- IFC 几何、属性关系、MVD/IDS、完整 EXPRESS schema 和模型视图验证；
- 人员 PKI/设备证书与真实 KMS/HSM/商密供应商适配器；
- 跨地域分布式防重放状态；
- 数据库事务、WORM、外部时间戳和证据外部锚定；
- 专家拒绝触发的跨领域通用自动回滚；
- 完整 LangGraph 建筑案例的外部 LLM 模式验收；
- 商业 CDE/BIM、IoT 和统一身份系统的供应商适配器。

上述能力属于 P0-B/P1，不能在演示或文档中描述为已生产化。
