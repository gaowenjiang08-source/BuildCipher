# BuildCipher Studio localhost 快速开始

## 1. 环境

- Python 3.11+ 与 Poetry；
- Node.js 18+ 与 npm；
- 可选 LLM API key。没有外部 LLM 时，确定性建筑演示和部分 MAS fallback 仍可运行。

复制 `.env.example` 为 `.env`，按需填写 LLM provider。建筑密码演示默认使用 localhost provider，不需要 AWS。

```env
BUILDCIPHER_GOVERNANCE_DATABASE_PATH=.cache/buildcipher/governance.sqlite3
BUILDCIPHER_CONSTRUCTION_IMPORT_ROOT=.cache/buildcipher/construction-imports
```

## 2. 安装

```powershell
poetry install
cd frontend
npm install
cd ..
```

## 3. 启动

一键启动：

```text
start.bat
```

分别启动：

```powershell
poetry run python -m uvicorn cipher_genius.api.main:app --app-dir src --host 127.0.0.1 --port 8000
```

测试默认隔离外部 LLM 网络调用；运行时仍可在设置中选择已保留的 LLM provider。

启动器也支持项目级 `.buildcipher_runtime` / `.buildcipher_venv`。检测到其中的 Windows Python 后会直接运行 `uvicorn`；否则使用 Poetry。两条路径都会将当前仓库的 `src` 显式设为应用目录，避免系统中其他 MedCipher/BuildTrust 工作区的同名 Python 包覆盖当前 BuildCipher。旧 `buildtrust-api` 命令和 `BUILDTRUST_GOVERNANCE_DATABASE_PATH` 环境变量仍作为兼容入口保留，但不再用于新配置。

```powershell
cd frontend
npm run dev
```

访问：

- `http://127.0.0.1:5173`
- `http://127.0.0.1:8000/docs`

## 4. 推荐演示路径

1. 在“工程总览”理解 BIM、设备、参与方和证据链；
2. 在“项目工作台”导入 `data/demo/buildtrust_v1/coordination.ifc`，确认 IFC4、实体数和 SHA-256；
3. 在“可信协同”查看五类参与方责任与证据结构；
4. 在“攻防验证”运行前后对照，让同一 IFC 输入分别进入 baseline/hardened，并点击五个技术探针检查原始摘要、版本、角色和消息新鲜度字段；
5. 在“可信交付”查看证据引用、能力边界，并下载 JSON、Markdown、LaTeX 或 HTML 建筑验证快照；
6. 需要检查 Agent 过程时切换专家模式，查看运行、报告和 replay。

左侧项目卡提供“业务模式 / 专家模式”直接切换；专家模式固定从专家总览开始，组件库不会改变当前模式。五攻击对照完成后，工程总览、攻防验证和可信交付会继续显示同一组阻断与证据指标。

两分钟讲解词和时间分配见 [docs/BUILD_CIPHER_2MIN_DEMO.md](docs/BUILD_CIPHER_2MIN_DEMO.md)。

## 5. 直接调用建筑接口

```powershell
Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/api/v1/benchmarks/construction
```

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/construction/demo/run `
  -ContentType 'application/json' `
  -Body '{"project_id":"buildtrust-demo-project"}'
```

接口默认 `mode=compare`。如已通过工作台导入 IFC，把响应中的 `asset_ref` 与相同 `project_id` 一起提交，即可让 baseline/hardened 消费该文件；`mode=hardened` 只运行加固侧。

## 6. 冻结合同验证

```powershell
$env:PYTHONPATH='src'
python scripts/validate_buildtrust_v1.py --output .cache/buildtrust-v1-validation.json
```

通过条件是 `status=passed`，baseline 为 `0/5`，hardened 为 `5/5`，IFC 摘要与结构合同匹配，治理检查没有失败项。

## 7. 测试与构建

```powershell
poetry run pytest -o addopts='' tests/api/test_api_benchmarks.py tests/unit/test_construction_benchmark.py tests/unit/test_construction_import_service.py tests/unit/test_safety_notice.py tests/unit/test_skill_router.py tests/unit/test_report_templates.py -q
```

```powershell
cd frontend
npm run build
```

## 8. LLM 接口

设置页继续支持 OpenAI、Anthropic、Gemini、智谱、DeepSeek、通义、百度和兼容 relay。LLM provider 与 BIM/IoT 的 localhost 密码 provider 是两个独立边界：前者用于 Agent 推理，后者用于确定性签名/MAC 演示。

如果 LLM 返回空内容或只有解释/免责声明，系统会使用本地实现形态 fallback，前端不会把免责声明单独标记为 C、Python 或伪代码已完成。代码页的“完成”不等于已编译、已通过沙箱或可生产部署。

## 9. 当前不支持

- AWS 或其他云部署结构；
- 商业 CDE/BIM 写入、远程认证和正式签批；
- 生产 PKI、KMS、HSM、商用密码模块；
- IFC 几何、碰撞、规范以及构件/GUID/属性级规则与最小披露；
- 分布式设备注册、防重放和跨地域一致性；
- 外部可信时间、WORM 与正式合规认证。

更多边界见 [BUILDTRUST_CAPABILITY_STATUS.md](BUILDTRUST_CAPABILITY_STATUS.md)。
