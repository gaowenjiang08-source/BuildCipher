# BuildTrust Studio 技术文档

最后更新：2026-08-12

## 1. 系统目标

BuildTrust 将通用密码策略 Agent 内核应用到建筑数字资产可信交付。第一版只聚焦 BIM/IFC 模型交换与一条工地 IoT 验收证据链。核心判据不是算法名称，而是系统能否证明：谁以什么权限，对哪个版本做了什么，以及结论引用了哪些可复核证据。

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
- `sandbox/construction_runtime.py`：五攻击确定性运行时、控制配置与证据账本；
- `integrations/construction/ifc.py`：IFC STEP 文件结构检查；
- `integrations/construction/cde.py`：只读 CDE 合同与本地目录适配器；
- `integrations/construction/iot_state.py`：SQLite 设备凭据引用和防重放状态；
- `integrations/construction/crypto_provider.py`：不可导出式 MAC/签名操作合同、本地参考 provider 与治理记录；
- `testing/construction_benchmark.py`：7 案例路由、模板和章节覆盖回归；
- `frontend/src/features/construction/`：五个建筑业务视图。

## 3. 建筑执行合同

五条固定攻击探针：

1. `ifc_content_tamper`：修改 IFC 字节但保留文件身份；
2. `signed_old_version_rollback`：使用签名有效但已过期的旧批准版本；
3. `full_model_overprivilege`：专业分包请求完整模型；
4. `unregistered_device_impersonation`：未注册工地设备冒充；
5. `valid_signed_telemetry_replay`：重放历史有效遥测。

baseline 配置不强制五项控制，预期阻断 `0/5`；hardened 配置启用摘要、当前版本、角色范围、设备注册与防重放，预期阻断 `5/5`。任何探针缺失、未执行或 `regression_passed=false`，建筑主链都会执行本地控制配置回滚并验证恢复文件 SHA-256。

## 4. IFC、CDE 与 IoT

`inspect_ifc_bytes` 读取 STEP physical file，输出 schema、实体类型计数、实体编号、候选 GlobalId、重复项、字节数和 SHA-256。它不处理几何、碰撞、MVD/IDS、完整 EXPRESS schema 或项目业务规则。

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

本地启动命令为 `poetry run buildtrust-api`；健康端点返回 `service=buildtrust-api`。内部 Python 包路径 `cipher_genius` 仅作为稳定导入契约保留。

- `GET /api/v1/benchmarks/construction`
- `POST /api/v1/construction/demo/run`
- `POST /api/v1/mas/execute`
- `POST /api/v1/mas/stream`
- `POST /api/v1/mas/report`
- `/api/v1/skills/*`
- `/api/v1/cases/*`
- `/api/v1/knowledge/*`
- `/api/v1/settings/*`
- `POST /api/v1/llm/validate`

医药 benchmark API 已移除。LLM provider 接口保持独立，没有因 localhost 密码 provider 而收窄。

## 7. 数据资产

- `data/skills/`：6 个建筑 Skill，以及通用密码审查/迁移 Skill；
- `data/report_templates/`：3 个建筑模板和通用模板；
- `data/benchmarks/construction_trusted_delivery.yaml`：7 个建筑回归案例；
- `data/demo/buildtrust_v1/`：赛事冻结 IFC 与预期合同；
- `data/components/`：通用密码组件知识库，不是生产密码实现库。

## 8. 验证

当前默认 API、集成、记忆、摄取、检索和方案生成测试使用 construction / BIM / IFC / CDE 样例。医药名称只存在旧端点和模板的退役断言，以及通用合规内核的独立能力测试中。

冻结合同：

```powershell
$env:PYTHONPATH='src'
python scripts/validate_buildtrust_v1.py --output .cache/buildtrust-v1-validation.json
```

领域回归：

```powershell
poetry run pytest -o addopts='' tests/api/test_api_benchmarks.py tests/unit/test_construction_benchmark.py tests/unit/test_skill_router.py tests/unit/test_report_templates.py -q
```

前端：

```powershell
cd frontend
npm run build
```

2026-08-12 本轮结果：后端完整测试集 `178 passed, 11 skipped`，前端生产构建转换 91 个模块，冻结演示复验为 baseline `0/5` 阻断、hardened `5/5` 阻断。测试层使用 `tests/conftest.py` 的离线 LLM fixture，以确保 localhost 回归不受本机密钥或网络状态影响；生产 provider 代码未改动。

## 9. 能力边界与下一步

当前不包含 AWS、商业 CDE、正式 PKI/KMS/HSM、多租户、分布式 IoT、外部可信时间、WORM 或正式认证。下一步优先完成一次可用外部 LLM 的建筑主链验收，再根据比赛需要决定是否接入商业平台；不提前铺设供应商结构。
