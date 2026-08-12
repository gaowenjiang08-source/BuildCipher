# 代码闲置/未接入审计报告

最后更新：2026-03-17

本报告用于回答两个维护问题：

- 当前仓库是否存在“闲置代码/未接入运行路径”的模块？
- 这些模块对后续维护与按需加载有什么影响，应该如何处理？

## 1. 审计口径（务实版）

这里的“闲置”不等同于“应当删除”。我们按风险分 3 类：

1. **明确下线/替代**：已经有维护入口替代，且明确不再走运行路径（适合迁移到 `deprecated/` 或删除）。
2. **未接入运行路径**：模块存在，但不被当前入口引用（API/CLI/Celery/Streamlit/React），属于实验/未来能力（适合标注为 experimental，或延后再接入）。
3. **契约失配**：代码或测试仍使用旧 schema/旧字段名，导致维护中踩坑（优先修复）。

本轮重点处理了第 3 类（LangGraph 引擎返回契约漂移）。

## 2. 当前运行入口（用于“是否接入”的判断）

- FastAPI：`src/cipher_genius/api/main.py`
- CLI：`src/cipher_genius/cli/main.py`
- Celery：`src/cipher_genius/tasks/celery_tasks.py`
- Streamlit v3：`streamlit/web_app_v3.py`（UI：`src/cipher_genius/ui/web_v3/`）
- React：`frontend/`

## 3. 发现的“未接入运行路径”候选（基于静态引用）

以下模块在当前主入口链路中**没有被静态 import 引用**（不代表未来不需要，只代表“现在不在默认执行链路里”）：

- `src/cipher_genius/features/attack_simulator.py`
- `src/cipher_genius/features/benchmark_runner.py`
- `src/cipher_genius/features/cost_estimator.py`
- `src/cipher_genius/features/recommender.py`
- `src/cipher_genius/features/threat_modeler.py`
- `src/cipher_genius/features/tutorials.py`
- `src/cipher_genius/features/tutorials_enhanced.py`

同类候选（基础设施/辅助模块，当前入口未直接引用）：

- `src/cipher_genius/utils/monitoring.py`
- `src/cipher_genius/utils/rate_limiter.py`
- `src/cipher_genius/utils/security.py`
- `src/cipher_genius/core/scheme_detector.py`
- `src/cipher_genius/core/validator.py`

说明：

- `features/*` 中实际被运行链路引用的模块主要是：
  - `compliance_reporter.py`
  - `performance_estimator.py`
  - `security_assessor.py`
  - `scheme_comparator.py`
  - `vulnerability_scanner.py`
- `streamlit/legacy/*` 已明确为历史版本（见 `deprecated/README.md` 与 `streamlit/legacy/`）。

## 4. 建议的处理策略（按维护收益排序）

1. **先标注，再重构**：对“未接入运行路径”的模块加一句 docstring 或 README 说明其状态（experimental / draft / not wired）。
2. **按需加载而不是全量导入**：保持这些模块不在默认 import 链路里，避免启动时加载大量上下文。
3. **分目录收敛（可选）**：如果确认短期不会接入，可考虑把上述模块迁移到：
   - `src/cipher_genius/features/experimental/`（保留但降低心智负担）
   - 或 `deprecated/`（明确下线）
4. **删除前置条件**：删除前建议先跑：
   - `python -m compileall src`
   - `poetry run pytest tests/unit -q`
   - 以及一次前端联调（避免隐藏依赖）

## 5. 本轮已处理的“契约失配”

- `use_langgraph=true` 的引擎实现曾与 `src/cipher_genius/api/schemas.py` 不一致，导致：
  - 返回字段名漂移（例如旧的 `analyst_report`/`architect_report`）
  - LangGraph 引擎内部类型使用错误（字符串 requirement 直接喂给生成器等）
- 已修复为 contract-parity 模式，确保返回 `MASResponse` 与前端契约一致，并新增：
  - `delivery.engine`
  - `delivery.cache_hit`
