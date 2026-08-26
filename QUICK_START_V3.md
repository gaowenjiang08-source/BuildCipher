# BuildCipher Studio localhost 快速开始

## 1. 环境

- Python 3.11+ 与 Poetry；
- Node.js 18+ 与 npm；
- 可选 LLM API key。没有外部 LLM 时，确定性建筑演示和部分 MAS fallback 仍可运行。

复制 `.env.example` 为 `.env`，按需填写 LLM provider。建筑密码演示默认使用 localhost provider，不需要 AWS。

```env
BUILDCIPHER_GOVERNANCE_DATABASE_PATH=.cache/buildcipher/governance.sqlite3
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
poetry run buildcipher-api
```

测试默认隔离外部 LLM 网络调用；运行时仍可在设置中选择已保留的 LLM provider。

启动器也支持项目级 `.buildcipher_runtime` / `.buildcipher_venv`。检测到其中的 Windows Python 后会直接运行 `uvicorn`；否则使用 Poetry。旧 `buildtrust-api` 命令和 `BUILDTRUST_GOVERNANCE_DATABASE_PATH` 环境变量仍作为兼容入口保留，但不再用于新配置。

```powershell
cd frontend
npm run dev
```

访问：

- `http://127.0.0.1:5173`
- `http://127.0.0.1:8000/docs`

## 4. 推荐演示路径

1. 在“工程总览”理解 BIM、设备、参与方和证据链；
2. 在“项目工作台”使用 BIM/IFC 或工地 IoT 模板补齐需求；
3. 在“可信协同”查看五类参与方责任与证据结构；
4. 在“安全验证”运行参考演示，查看 baseline/hardened 对比；
5. 在“可信交付”查看证据引用、导出入口和能力边界；
6. 需要检查 Agent 过程时切换专家模式，查看运行、报告和 replay。

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

## 6. 冻结合同验证

```powershell
$env:PYTHONPATH='src'
python scripts/validate_buildtrust_v1.py --output .cache/buildtrust-v1-validation.json
```

通过条件是 `status=passed`，baseline 为 `0/5`，hardened 为 `5/5`，IFC 摘要与结构合同匹配，治理检查没有失败项。

## 7. 测试与构建

```powershell
poetry run pytest -o addopts='' tests/api/test_api_benchmarks.py tests/unit/test_construction_benchmark.py tests/unit/test_skill_router.py tests/unit/test_report_templates.py -q
```

```powershell
cd frontend
npm run build
```

## 8. LLM 接口

设置页继续支持 OpenAI、Anthropic、Gemini、智谱、DeepSeek、通义、百度和兼容 relay。LLM provider 与 BIM/IoT 的 localhost 密码 provider 是两个独立边界：前者用于 Agent 推理，后者用于确定性签名/MAC 演示。

## 9. 当前不支持

- AWS 或其他云部署结构；
- 商业 CDE/BIM 写入、远程认证和正式签批；
- 生产 PKI、KMS、HSM、商用密码模块；
- 构件/GUID/属性级 IFC 规则与最小披露；
- 分布式设备注册、防重放和跨地域一致性；
- 外部可信时间、WORM 与正式合规认证。

更多边界见 [BUILDTRUST_CAPABILITY_STATUS.md](BUILDTRUST_CAPABILITY_STATUS.md)。
