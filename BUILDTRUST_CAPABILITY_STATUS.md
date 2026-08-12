# BuildTrust Studio 能力状态

最后更新：2026-08-12  
当前阶段：localhost 第一版已完成运行时品牌与建筑测试纯化，进入赛事验收

每轮改造结束都应同步更新本文档的“当前位置、已实现、能力边界、待实现”。

## 当前位于哪一步

- P0-A 建筑领域底座：已完成；
- P0-B1 建筑语义运行时：已完成本地演示版；
- P0-B2 五类攻击与证据工件：已完成本地演示版；
- P0-B3 API 与 LangGraph 主链接入：本地第一版已完成；
- P1 建筑业务前端：第一版已完成；
- P2 集成与赛事交付：localhost BIM/IoT provider、IFC/CDE 合同、IoT 持久化、治理记录和赛事冻结包已完成；云和供应商适配暂不开发。
- 领域纯化：前端及活跃后端的医药 benchmark、Skill、报告模板和业务 API 已退役；通用密码与 LLM 内核保留。
- 品牌与测试纯化：外部命令为 `buildtrust` / `buildtrust-api`，API 健康标识、报告、导出器、前端存储键和默认领域测试均已切换为 BuildTrust / construction。
- 完整测试集使用离线 LLM fixture 验证 localhost fallback，结果为 `178 passed, 11 skipped`；生产 LLM provider 接口保留。

## 当前已实现能力

- 建筑参与方、资产、生命周期、权限和证据引用合同；
- 6 个建筑 Skill、3 个报告模板、7 个 Benchmark；
- IFC 内容摘要、manifest 验真、父版本、当前批准版本和角色授权；
- IoT 设备注册、消息认证、单调计数器、nonce 和时间窗口；
- 带签名、前序哈希和链头摘要的项目证据账本；
- IFC 篡改、版本回滚、分包越权、设备冒充、遥测重放五类攻击；
- 每次攻击生成 JSON artifact、SHA-256 evidence、修补建议和回归结果；
- `GET /api/v1/benchmarks/construction`；
- `POST /api/v1/construction/demo/run`；
- LangGraph 根据 `construction` 领域和需求信号选择 BIM、IoT 或证据账本目标模板。
- LangGraph 的基线、同轮补充验证和补丁回归会把建筑目标统一解析为五条领域 attack spec；
- 本地沙箱把五类领域结果映射为现有 `AttackResultPayload`，供漏洞裁决、补丁规划和 reflection 消费；
- 五类攻击的 JSON 工件、证据账本文件和 SHA-256 引用会进入 delivery/replay，并写入 case memory 的 `latest_evidence_refs`。
- LangGraph 建筑基线使用 `baseline` 控制配置，补丁工作区写入 `hardened` 配置；同一五攻击组可证明 0/5 阻断到 5/5 阻断的状态变化；
- 建筑控制配置保留补丁前快照，并可通过 dispatcher 显式执行回滚；恢复文件与快照使用 SHA-256 一致性验证。
- LangGraph 只依据五条客观回归探针判定建筑补丁是否有效；任何探针未执行或 `regression_passed=false` 都会自动恢复补丁前配置，并把实际回滚 dispatch、验证结果和证据文件写入交付结果。
- 已完成一次无外部 LLM 的完整 LangGraph 建筑验收：construction/BIM 路由正确，baseline 0/5 阻断，hardened 回归 5/5 阻断，case memory 收到 12 个证据引用。
- 建筑业务前端第一版提供工程总览、项目工作台、可信协同、安全验证和可信交付五个视图；安全验证可直接调用建筑参考演示 API 展示五类攻击的基线/加固对比。
- IFC 检查器可读取真实 STEP physical file 的文件头、IFC schema、实体编号、实体类型计数、候选 GlobalId、重复编号/GlobalId 和内容 SHA-256；
- 定义了只读 `ConstructionCDEConnector` 合同，并提供项目目录形式的 `LocalDirectoryCDEConnector` 参考适配器；
- SQLite IoT 状态保存设备凭据引用、最后计数器和已用 nonce，进程重启后仍能拒绝历史遥测；密钥材料不写入 SQLite。
- `ConstructionMACProvider` 与 `ConstructionSignatureProvider` 规定调用方只能请求 MAC/签名/验证操作，不能请求原始密钥；IoT 网关已优先使用 MAC provider 路径；
- `LocalReferenceHMACProvider` 验证非导出式调用形态，生成不含密钥的操作回执；凭据撤销、禁用、过期或待轮换时会在操作前拒绝，并记录 rejected 回执；
- SQLite 治理库存储凭据生命周期、版本、轮换时间、证书指纹/有效期/吊销状态和密码操作审计，可生成轮换到期、非活动凭据和无效证书评估。
- 本地 provider 同时提供 BIM manifest 签名/验签和 IoT MAC，并把 `signer_credential_ref` 纳入签名体，阻止攻击者替换合法设计凭据引用；
- `ConstructionDemoService` 默认装配 localhost provider，凭据治理和操作回执写入 SQLite；API 明确返回 `crypto_provider_mode=localhost_provider`、`provider_mac_enabled` 和 `provider_signature_enabled`；
- localhost 演示密钥在进程内随机生成，不写入源码或 SQLite，进程结束后不持久化；
- OpenAI、Anthropic、智谱、Gemini、DeepSeek、通义、百度和 relay LLM 接口保持原状，与 localhost 密码执行边界独立。
- `data/demo/buildtrust_v1/` 已冻结 IFC 输入、SHA-256、预期 schema/实体数和 baseline/hardened 五攻击指标；`scripts/validate_buildtrust_v1.py` 可一键复验并输出机器可读结果。
- `/api/v1/benchmarks/biopharma` 已移除并返回 404；当前唯一行业 benchmark 为 `/api/v1/benchmarks/construction`。

## 当前能力边界

- 参考运行仍是单进程 localhost 演示；SQLite IoT 适配器可保留计数器与 nonce，但默认演示中的 IFC 批准状态和跨服务一致性不是生产持久化合同；
- `LocalReferenceHMACProvider` 只用于验证不可导出式 MAC/签名调用合同，不等于人员数字签名、设备证书或生产 PKI；
- IFC 当前按文件字节处理，没有解析实体、属性、构件 GUID 或模型视图；
- 权限控制当前到角色/完整包级，尚无构件、属性、专业视图和字段级最小披露；
- 证据账本是本地 JSON 哈希链，没有数据库事务、外部时间戳、WORM 或外部锚定；
- LangGraph 已接入建筑五攻击适配器，但尚未在攻击主链调用 P2 IFC 检查器、商业 CDE 或 IoT 消息总线；
- 补丁会真实改写本地演示工作区的控制配置，但不会修改真实 CDE、BIM 平台或 IoT 网关；
- 自动回滚当前只覆盖建筑目标的五条确定性回归探针；通用密码场景及专家拒绝策略仍沿用原流程；
- 前端第一版是本地演示视图，尚未连接真实 CDE/BIM、IoT 平台和统一身份源；
- IFC 检查器不是几何、碰撞、MVD/IDS、完整 EXPRESS schema 或模型规则引擎；
- 本地目录 CDE 适配器不含远程认证、供应商 API、签批、锁定和上传语义；
- SQLite 防重放适用于单主机或共享卷，不提供跨地域分布式一致性；
- localhost provider 的密钥仍驻留应用进程内存，不是 HSM、云 KMS 或商用密码模块；
- 未接入真实 KMS/HSM、商用密码模块、CDE/BIM 平台、IoT 消息总线或多租户环境；
- 当前结果不是 ISO 19650 合规认证，也不是生产安全保证。

## 待实现能力

### 第一版验收剩余

- 使用可用外部 LLM 再运行完整建筑案例，验收裁决、补丁理由与 reflection 文本质量；
- 通用合规枚举及其独立回归测试保留，但不注册成建筑默认路由，也不对外暴露医药业务产品线。

### P2

- 商业 CDE/BIM 平台供应商适配器及其认证/签批语义；
- 分布式设备注册和防重放状态；
- 根据比赛实际要求决定是否开发商业 CDE、PKI/KMS/HSM 或商用密码模块；当前 localhost 版本不预写这些供应商结构；
- 使用已有 LLM 凭据完成一次外部模型建筑主链验收。
- 多租户隔离、证书轮换、外部可信时间和长期归档；
- 后量子混合部署实验与赛事交付材料。
