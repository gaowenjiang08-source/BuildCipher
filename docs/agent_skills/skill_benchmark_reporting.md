# Skill：建筑 benchmark 与报告回归

适用于修改建筑 Skill、报告模板、路由关键词或 benchmark API。

关键文件：

- `data/benchmarks/construction_trusted_delivery.yaml`
- `src/cipher_genius/testing/construction_benchmark.py`
- `src/cipher_genius/api/benchmark_service.py`
- `data/skills/*.yaml`
- `data/report_templates/*.yaml`
- `tests/unit/test_construction_benchmark.py`
- `tests/api/test_api_benchmarks.py`

验证要求：8 个案例的 Skill、模板和必需章节命中率都必须为 1.0；`GET /api/v1/benchmarks/construction` 必须返回相同结果。

```powershell
poetry run pytest -o addopts='' tests/unit/test_construction_benchmark.py tests/api/test_api_benchmarks.py -q
```

医药 benchmark 已退役，不再作为兼容目标。
