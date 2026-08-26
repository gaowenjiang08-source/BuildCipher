# BuildCipher Studio

BuildCipher Studio 是面向建筑工程数字资产的可信协同与密码策略 Agent。`BuildTrust` 是其中的建筑可信交付能力名，第一版聚焦 **BIM/IFC 可信交付 + 工地 IoT 验收证据链**，把需求分析、方案生成、安全审计、攻击验证、修补回归和证据交付组织成一条 LangGraph 主线。

项目保留原系统的通用密码组件、MAS 编排、LLM provider、报告、记忆与回放内核；医药专属前端、benchmark、Skill、报告模板和 API 已退役。

## 第一版能力

- 建筑参与方、资产、生命周期、权限和证据引用合同；
- 6 个建筑 Skill、3 个建筑报告模板、7 个建筑 benchmark；
- IFC 内容摘要、manifest 验真、父版本、批准版本和交付包级角色授权；
- 工地设备注册、消息认证、单调计数器、nonce 与时间窗口；
- IFC 篡改、旧版本回滚、分包越权、设备冒充、遥测重放五类确定性攻击；
- baseline `0/5` 到 hardened `5/5` 回归，以及失败时的本地配置回滚；
- 本地 JSON 证据工件、SHA-256 引用、哈希链账本和 SQLite 治理记录；
- React 前端五个业务视图：工程总览、项目工作台、可信协同、安全验证、可信交付；
- OpenAI、Anthropic、Gemini、智谱、DeepSeek、通义、百度和兼容 relay 的 LLM 接口继续保留。

## 本地启动

Windows 可运行：

```text
start.bat
```

或分别启动：

```powershell
poetry install
poetry run buildcipher-api
```

```powershell
cd frontend
npm install
npm run dev
```

- 前端：`http://127.0.0.1:5173`
- API：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`

详细步骤见 [QUICK_START_V3.md](QUICK_START_V3.md)。

Windows 启动器会优先识别 `.buildcipher_runtime`、`.buildcipher_venv` 或 Poetry 的 `.venv`。既有团队分支仍可使用 `poetry run buildtrust` / `poetry run buildtrust-api` 兼容别名；新代码与文档统一使用 `buildcipher` / `buildcipher-api`。

## 建筑 API

- `GET /api/v1/benchmarks/construction`：验证 Skill 路由、模板选择和章节覆盖；
- `POST /api/v1/construction/demo/run`：运行五类确定性攻击；
- `POST /api/v1/mas/execute`：执行完整 LangGraph MAS；
- `POST /api/v1/mas/stream`：流式执行；
- `POST /api/v1/mas/report`：生成报告；
- `/api/v1/skills/*`：建筑 Skill 列表、路由与执行；
- `/api/v1/settings/*` 与 `/api/v1/llm/validate`：本地设置与 LLM provider 验证。

原 `/api/v1/benchmarks/biopharma` 已移除，现在返回 404。

## 验证

本地测试使用离线 LLM fixture 进入现有确定性 fallback，不会消耗外部 API；生产 LLM provider 接口不受影响。

```powershell
$env:PYTHONPATH='src'
python -m pytest -o addopts='' tests -q
```

```powershell
$env:PYTHONPATH='src'
python scripts/validate_buildtrust_v1.py --output .cache/buildtrust-v1-validation.json
```

预期结果：

- IFC schema 为 `IFC4`，冻结文件摘要匹配；
- baseline 阻断 `0/5`；
- hardened 阻断 `5/5`；
- localhost provider 的 MAC/签名合同启用；
- 证据账本有效，撤销、轮换和证书状态检查通过。

前端生产构建：

```powershell
cd frontend
npm run build
```

## 能力边界

- 只提供 localhost 第一版，不包含 AWS 或其他云部署结构；
- LLM 负责分析、规划和解释，不生成可直接宣称生产安全的密码原语；
- localhost HMAC provider 的密钥驻留应用进程内存，不是 PKI、KMS、HSM 或商用密码模块；
- IFC 检查器不是几何、碰撞、MVD/IDS 或完整 EXPRESS 规则引擎；
- 权限目前到角色与完整交付包级，不是构件、属性或字段级最小披露；
- 本地目录 CDE、SQLite 防重放和 JSON 哈希链不等于商业 CDE、分布式 IoT 或 WORM/可信时间服务；
- 结果不构成 ISO 19650、ISO 27001 或其他认证结论。

当前位置、待实现能力和验收状态见 [BUILDTRUST_CAPABILITY_STATUS.md](BUILDTRUST_CAPABILITY_STATUS.md)。
