# BuildCipher Studio 技术文档

最后更新：2026-08-26

## 1. 系统目标

BuildCipher Studio 将通用密码策略 Agent 内核应用到建筑数字资产可信交付；`BuildTrust` 是建筑可信交付能力与冻结演示合同的名称。第一版只聚焦 BIM/IFC 模型交换与一条工地 IoT 验收证据链。核心判据不是算法名称，而是系统能否证明：谁以什么权限，对哪个版本做了什么，以及结论引用了哪些可复核证据。

## 2. 架构

主链由 LangGraph 编排：

`analyst → context_builder → architect → audit → engineer → target_deployer → attack_executor → vulnerability_evaluation → patch_reflection → delivery`

通用能力：

- `core/`：需求解析、方案生成、审计、攻击规划、漏洞裁决、修补、反思；
- `memory/`：case memory、timeline、snapshot、lineage 与 replay；
- `reporting/`：manifest 驱动的报告模板与本地化；
- `skills/`：manifest 驱动的 Skill 注册、路由与执行；
- `retrieval/`：本地/Qdrant 知识检索和证据包；
- `api/`：FastAPI 合同与服务。

建筑能力：

- `models/construction.py`：参与方、资产、生命周期、权限、证据合同；
- `core/construction_domain.py`：从自然语言推断参与方、资产、阶段、安全不变量和威胁，并映射到类型化建筑合同；兼容读取早期 ZIP 的字段值；
- `sandbox/construction_runtime.py`：五攻击确定性运行时、控制配置与证据账本；
- `integrations/construction/ifc.py`：IFC STEP 文件结构检查；
- `integrations/construction/cde.py`：只读 CDE 合同与本地目录适配器；
- `integrations/construction/iot_state.py`：SQLite 设备凭据引用和防重放状态；
- `integrations/construction/crypto_provider.py`：不可导出式 MAC/签名操作合同、本地参考 provider 与治理记录；
- `api/construction_service.py`：localhost IFC 导入、稳定资产引用解析与 baseline/hardened 对照服务；
- `testing/construction_benchmark.py`：8 案例路由、模板和章节覆盖回归；
- `frontend/src/features/construction/`：五个建筑业务视图。

## 3. 建筑执行合同

五条固定攻击探针：

1. `ifc_content_tamper`：修改 IFC 字节但保留文件身份；
2. `signed_old_version_rollback`：使用签名有效但已过期的旧批准版本；
3. `full_model_overprivilege`：专业分包请求完整模型；
4. `unregistered_device_impersonation`：未注册工地设备冒充；
5. `valid_signed_telemetry_replay`：重放历史有效遥测。

baseline 配置不强制五项控制，预期阻断 `0/5`；hardened 配置启用摘要、当前版本、角色范围、设备注册与防重放，预期阻断 `5/5`。任何探针缺失、未执行或 `regression_passed=false`，建筑主链都会执行本地控制配置回滚并验证恢复文件 SHA-256。

前端“攻防验证”不是单一阻断计数页。每个探针同时说明攻击构造、密码/访问控制机制、安全不变量、控制配置键和通过标准，并展示 baseline/hardened 的原始运行时对象。BIM 检查对象包含预期与实测 SHA-256、请求版本、当前批准版本、请求角色、允许角色、签名身份、凭据引用和签名算法；IoT 检查对象包含设备注册状态、counter、nonce、消息时间、观察时间、时间窗与启用控制。所有字段均不包含密钥材料。

## 4. IFC、CDE 与 IoT

`inspect_ifc_bytes` 读取 STEP physical file，输出 schema、实体类型计数、实体编号、符合 IFC 压缩 GUID 字面约束的候选 GlobalId、重复项、字节数和 SHA-256；候选值必须为 22 位 IFC base64 字符且首字符为 `0`–`3`。它不处理几何、碰撞、MVD/IDS、完整 EXPRESS schema 或项目业务规则。

`POST /api/v1/construction/assets/import` 只接受最大 50 MiB 的 `.ifc`，在 `.cache/buildcipher/construction-imports/` 保存原始字节与 `import.json`，返回 `construction-import://{project_id}/{import_id}`。再次解析引用时会重算 SHA-256，文件变化即拒绝。上传文件不会被执行。

`POST /api/v1/construction/demo/run` 默认 `mode=compare`：同一内置样例或 `asset_ref` 指向的导入 IFC 分别运行 baseline 与 hardened，响应保留加固侧兼容字段，同时返回 `baseline_results`、两侧阻断数、工作区和 `comparison_verified`。`mode=hardened` 保留单侧运行能力。

`ConstructionCDEConnector` 是最小只读合同。`LocalDirectoryCDEConnector` 可以列举、读取和检查项目目录中的 `.ifc` 文件，并阻止引用逃逸根目录。没有上传、签批、锁定、远程身份或供应商 API 语义。

`SQLiteConstructionIoTReplayState` 以事务保存设备凭据引用、最后计数器和已用 nonce。它适用于 localhost 单主机或共享卷，不提供跨地域分布式一致性；SQLite 不保存密钥材料。

## 5. 密码 provider 与治理

`ConstructionMACProvider` 和 `ConstructionSignatureProvider` 只允许调用方请求 MAC、签名或验证操作，不提供导出原始密钥的方法。`LocalReferenceHMACProvider` 用进程内随机密钥验证合同形态，并返回不含密钥的 `ConstructionKeyOperationReceipt`。

SQLite 治理库存储：

- 凭据引用、用途、状态与版本；
- 创建、到期和轮换时间；
- 证书指纹、有效期与吊销状态；
- 密码操作的成功或拒绝回执。

密钥仍驻留 Python 进程内存，进程结束后不持久化。这不是生产 PKI、KMS、HSM 或商用密码模块。

## 6. API

本地启动命令为 `poetry run python -m uvicorn cipher_genius.api.main:app --app-dir src --host 127.0.0.1 --port 8000`；健康端点返回 `service=buildcipher-api`。内部 Python 包路径 `cipher_genius` 作为稳定导入契约保留。旧 `buildtrust` / `buildtrust-api` 命令及 `BUILDTRUST_GOVERNANCE_DATABASE_PATH` 环境变量继续兼容，主运行时命名与默认治理路径已切换到 `BuildCipher` / `.cache/buildcipher/`。

Windows 启动器按 `.buildcipher_runtime`、`.buildcipher_venv`、`.venv` 的顺序发现项目 Python；未发现项目运行时则回退到 Poetry。所有启动分支都通过 Uvicorn `--app-dir` 锁定当前仓库的 `src`，防止加载其他工作区残留的同名 `cipher_genius` 包。共享包明确排除 `.env`、`.env.local` 及其他非示例 `.env.*` 文件。

- `GET /api/v1/benchmarks/construction`
- `POST /api/v1/construction/assets/import`
- `POST /api/v1/construction/demo/run`
- `POST /api/v1/mas/execute`
- `POST /api/v1/mas/stream`
- `POST /api/v1/mas/report`
- `/api/v1/skills/*`
- `/api/v1/cases/*`
- `/api/v1/knowledge/*`
- `/api/v1/settings/*`
- `POST /api/v1/llm/validate`

旧行业 benchmark API 已移除。LLM provider 接口保持独立，没有因 localhost 密码 provider 而收窄。

代码生成主流程通过一次 `generate_structured` 请求取得 `pseudocode`、`python` 与 `c` 三个字段，不再按语言串行调用三次 LLM。任一字段缺少实现形态时只对该字段使用本地模板，不再发起额外补救请求。完成态继续使用 `has_meaningful_artifact` 判断：C 必须包含函数定义，Python 必须包含函数或类，伪代码必须具备算法步骤；只有安全免责声明或普通说明文字不算代码工件。该判断只证明“存在实现形态”，编译、沙箱运行与专业密码评审仍是独立阶段。

前端接收 MAS 结果后保持当前页面，不执行强制工作台跳转。工作台只规范化三种主要代码字段；完整交付 JSON 和 Markdown 延迟到用户打开相应标签时构造。代码与导出预览限制为前 500 行，复制仍使用完整字符串。代码结果区由局部错误边界隔离，避免单个序列化或渲染错误造成整页空白。

运行历史采用“浏览器摘要、后端完整证据”的分层存储。`localStorage` 只保存最近 20 条运行的标识、时间、方案名、状态和有限长度说明，不复制代码、讨论日志、攻击时间线、证据集合或沙箱产物。完整当前结果保留在会话内存，跨刷新复核以后端 case/evidence 记录和导出工件为准。这避免大型 LLM/MAS 响应超过同步浏览器存储配额并中断 React 提交阶段。

建筑交付页不再依赖 MAS `deliveryPackage` 才能导出。页面将当前项目、IFC 导入元数据、baseline/hardened 五攻击结果、证据引用、MAS 交付摘要和能力边界组装为 `construction_trust_validation` 快照，并在浏览器本地生成 JSON、Markdown、LaTeX 与自包含 HTML；HTML 导出不调用外部服务。

## 7. 数据资产

- `data/skills/`：6 个建筑 Skill，以及通用密码审查/迁移 Skill；
- `data/report_templates/`：3 个建筑模板和通用模板；
- `data/benchmarks/construction_trusted_delivery.yaml`：8 个建筑回归案例，包含密码组件与密钥证书治理评审；
- `data/demo/buildtrust_v1/`：赛事冻结 IFC 与预期合同；
- `data/components/`：通用密码组件知识库，不是生产密码实现库。

## 8. 验证

当前默认 API、集成、记忆、摄取、检索和方案生成测试使用 construction / BIM / IFC / CDE 样例。旧行业名称只存在退役端点和模板的断言，以及通用合规内核的独立能力测试中。

冻结合同：

```powershell
$env:PYTHONPATH='src'
python scripts/validate_buildtrust_v1.py --output .cache/buildtrust-v1-validation.json
```

领域回归：

```powershell
poetry run pytest -o addopts='' tests/api/test_api_benchmarks.py tests/unit/test_construction_benchmark.py tests/unit/test_construction_import_service.py tests/unit/test_safety_notice.py tests/unit/test_skill_router.py tests/unit/test_report_templates.py -q
```

前端：

```powershell
cd frontend
npm run build
```

2026-08-26 P0 结果：排除需要另行启动 8000 端口服务的 `tests/integration/test_mas_api.py` 后，localhost 确定性测试为 `190 passed, 4 skipped`；P0 定向测试 20 项和建筑 API 4 项通过；前端生产构建转换 91 个模块；冻结演示为 baseline `0/5`、hardened `5/5`。外部 API 集成模块会连接用户后台进程，本轮观察到该进程连接重置，因此不把它混入可重复回归数字。生产 LLM provider 代码未移除。

## 9. 能力边界与下一步

当前不包含 AWS、商业 CDE、正式 PKI/KMS/HSM、多租户、分布式 IoT、外部可信时间、WORM 或正式认证。下一步优先完成一次可用外部 LLM 的建筑主链验收，再根据比赛需要决定是否接入商业平台；不提前铺设供应商结构。
