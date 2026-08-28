# Testing utilities

当前业务回归入口是 `construction_benchmark.py`。它读取 `data/benchmarks/construction_trusted_delivery.yaml`，验证 8 个建筑案例的 Skill 路由、报告模板解析和必需章节覆盖。

```powershell
poetry run pytest -o addopts='' tests/unit/test_construction_benchmark.py tests/api/test_api_benchmarks.py -q
```

冻结五攻击合同使用：

```powershell
$env:PYTHONPATH='src'
python scripts/validate_buildtrust_v1.py
```

旧行业 benchmark runner 和数据集已退役。`ab_tester.py` 仍是通用 MAS 引擎比较工具。
