# LangGraph MAS 引擎集成指南

## 概述

CipherGenius v3.1 引入了基于 LangGraph 的新 MAS 引擎，与原有的 legacy 引擎并存，用户可以自由选择使用哪个引擎。

### 当前状态（2026-03-17）

为保证前端与 `schemas.py` 的契约稳定，`use_langgraph=true` 当前处于 **contract-parity** 模式：

- 对外仍然通过 `use_langgraph` 开关区分引擎
- LangGraph 引擎内部复用 Legacy MAS 执行链路，避免两套实现导致返回字段漂移
- 返回中会在 `delivery.engine` 标记引擎（`legacy` / `langgraph`），LangGraph 引擎命中 Redis 缓存时会标记 `delivery.cache_hit=true`

后续会逐步把 Legacy 逻辑拆分为 LangGraph 节点并启用检查点/可恢复能力。

## 两种引擎对比

### Legacy Engine (原引擎)
- **架构**: 串行 Prompt 调用
- **状态管理**: 无状态，每次调用独立
- **可恢复性**: 不支持
- **可观测性**: 有限
- **适用场景**: 稳定、经过验证的生产环境

### LangGraph Engine (新引擎)
- **架构**: StateGraph 状态图编排
- **状态管理**: 有状态，支持检查点持久化
- **可恢复性**: 支持中断恢复 (MemorySaver)
- **可观测性**: 完整的节点状态追踪
- **适用场景**: 需要复杂编排、可恢复性的场景

## API 使用

### 1. 同步执行

```bash
# 使用 Legacy 引擎
curl -X POST "http://127.0.0.1:8000/api/v1/mas/execute?use_langgraph=false" \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "Design AES-GCM encryption for IoT devices",
    "llm_provider": "openai",
    "num_variants": 2
  }'

# 使用 LangGraph 引擎
curl -X POST "http://127.0.0.1:8000/api/v1/mas/execute?use_langgraph=true" \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "Design AES-GCM encryption for IoT devices",
    "llm_provider": "openai",
    "num_variants": 2
  }'
```

### 2. 流式执行

```bash
# 使用 Legacy 引擎
curl -X POST "http://127.0.0.1:8000/api/v1/mas/stream?use_langgraph=false" \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "Design RSA-PSS signature scheme",
    "llm_provider": "openai"
  }'

# 使用 LangGraph 引擎
curl -X POST "http://127.0.0.1:8000/api/v1/mas/stream?use_langgraph=true" \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "Design RSA-PSS signature scheme",
    "llm_provider": "openai"
  }'
```

## 前端集成

### 1. 使用 Zustand Store

```javascript
import { useSettingsStore } from './store';

function MASPanel() {
  const { useLangGraph, setUseLangGraph } = useSettingsStore();

  return (
    <div>
      <label>
        <input
          type="checkbox"
          checked={useLangGraph}
          onChange={(e) => setUseLangGraph(e.target.checked)}
        />
        使用 LangGraph 引擎 (实验性)
      </label>
    </div>
  );
}
```

### 2. 调用 API

```javascript
import { executeMas, executeMasStream } from './api/client';
import { useSettingsStore } from './store';

// 同步执行
const { useLangGraph } = useSettingsStore();
const result = await executeMas(payload, settings, useLangGraph);

// 流式执行
await executeMasStream(
  payload,
  settings,
  {
    onRun: (runId, engine) => {
      console.log(`Started with ${engine} engine`);
    },
    onProgress: (data) => console.log('Progress:', data),
    onFinal: (data) => console.log('Final:', data),
  },
  useLangGraph
);
```

## 测试

### 1. 运行集成测试

```bash
# 启动 API 服务
poetry run cipher-genius-api

# 运行集成测试
poetry run pytest tests/integration/test_mas_api.py -v
```

### 2. 运行 A/B 测试

```bash
# 对比两个引擎的性能
poetry run python scripts/run_ab_tests.py
```

A/B 测试会生成 JSON 报告，包含：
- 执行时间对比
- 成功率对比
- 候选方案数量对比
- 加速比 (speedup factor)

### 3. 测试覆盖场景

- 数字签名方案
- 对称加密方案
- 消息认证码
- 密钥交换协议
- 哈希函数
- 密码学哈希

## 性能对比

基于初步测试，LangGraph 引擎在以下方面有优势：

| 指标 | Legacy | LangGraph | 改进 |
|------|--------|-----------|------|
| 状态管理 | 无 | 有 | ✅ |
| 可恢复性 | 不支持 | 支持 | ✅ |
| 可观测性 | 有限 | 完整 | ✅ |
| 并行执行 | 不支持 | 支持 (未来) | 🔄 |
| 执行时间 | 基准 | 相近 | ➖ |

## 已知限制

### LangGraph 引擎当前限制

1. **串行执行**: 当前仍为串行，未启用并行节点
2. **缓存兼容性**: 与 Redis 缓存的集成需要进一步测试
3. **错误恢复**: 检查点恢复功能尚未完全测试
4. **性能优化**: 状态序列化可能带来轻微开销

### 推荐使用场景

**使用 Legacy 引擎**:
- 生产环境稳定性优先
- 不需要状态恢复
- 简单的单次执行

**使用 LangGraph 引擎**:
- 需要状态追踪和调试
- 长时间运行需要可恢复性
- 未来需要并行执行优化
- 实验性功能测试

## 迁移计划

### 短期 (1-2周)
- ✅ 完成 API 集成
- ✅ 完成前端支持
- ✅ 完成集成测试
- ✅ 完成 A/B 测试框架

### 中期 (1个月)
- 🔄 启用 LangGraph 并行节点执行
- 🔄 优化状态序列化性能
- 🔄 完善错误恢复机制
- 🔄 生产环境灰度测试

### 长期 (2-3个月)
- 📋 LangGraph 成为默认引擎
- 📋 Legacy 引擎标记为 deprecated
- 📋 完全移除 Legacy 引擎

## 故障排查

### 问题: LangGraph 引擎执行失败

**检查步骤**:
1. 确认 LangGraph 依赖已安装: `poetry show langgraph`
2. 查看日志: `tail -f logs/cipher-genius.log`
3. 验证 LLM Provider 配置正确
4. 尝试使用 Legacy 引擎对比

### 问题: 性能比 Legacy 慢

**可能原因**:
1. 状态序列化开销
2. 检查点持久化开销
3. 未启用并行执行

**优化建议**:
1. 禁用不必要的检查点
2. 等待并行执行功能上线
3. 使用 Redis 缓存减少重复执行

## 反馈与贡献

如果在使用 LangGraph 引擎时遇到问题或有改进建议，请：

1. 查看 [IMPROVEMENT_ROADMAP.md](IMPROVEMENT_ROADMAP.md)
2. 提交 Issue 到项目仓库
3. 运行 A/B 测试并分享结果

## 参考资料

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [技术文档](docs/TECHNICAL_DOCUMENTATION.md)
- [A/B 测试脚本](scripts/run_ab_tests.py)
- [集成测试](tests/integration/test_mas_api.py)
