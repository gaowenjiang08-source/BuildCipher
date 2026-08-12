# 知识模块说明

最后更新：2026-03-24
状态：active

## 1. 目录职责

本目录负责运行时知识资产的加载与访问，当前重点是组件知识库。

它解决的是：

- 如何把 `data/components/**/*.yaml` 加载成统一运行时对象
- 如何为生成与筛选提供组件级查询能力

它目前不直接负责：

- 向量检索
- 企业标准文档 ingestion
- 案例记忆持久化
- 报告引用输出

这些能力后续建议落在独立的 `retrieval/`、`memory/` 或报告模块中。

## 2. 当前关键入口

- `components.py`
  - 负责定位 `data/components/`、加载 YAML、解析成 `ComponentLibrary`

## 3. 当前数据来源

- 默认资产目录：`data/components/`
- 运行时环境变量：`CIPHER_GENIUS_COMPONENTS_DIR`

当前目录下的组件资产按子类目组织，例如：

- `primitives/`
- `modes/`
- `protocols/`

## 4. 当前运行方式

`ComponentLibrary` 会在初始化时递归读取 YAML 文件，并把每个文件解析成 `Component` 对象，支持：

- 按名称获取
- 按类别筛选
- 按安全等级筛选
- 按 use case 搜索
- 多条件组合搜索

当前实现本质上还是“结构化组件库加载器”，而不是完整的企业知识检索层。

## 5. 为什么要保留这一层

即使后续接入 Qdrant 与统一知识对象 schema，这一层也不应该直接消失。原因是：

- 组件 YAML 是项目最贴近密码领域知识的原生资产
- 生成器和审计器仍然需要结构化、可编程访问的组件对象
- 检索层更适合补充“证据与引用”，不适合完全替代运行时组件模型

更合理的方向是：

- 当前 `ComponentLibrary` 继续服务生成与规则判断
- 同时把同一份组件资产转换成“可检索的组件知识卡”进入知识库主线

## 6. 后续推荐演进

1. 为组件 YAML 定义稳定的知识卡映射规则
2. 让组件知识卡进入统一知识对象 schema
3. 在 LangGraph `context_builder` 中混合检索组件知识卡、标准规范与案例
4. 让报告输出能引用组件能力边界，而不只是口头推荐

## 7. 修改本目录时要同步检查什么

- `data/components/README.md`
- `docs/modules/retrieval_knowledge_base.md`
- 受影响的生成、审计或报告逻辑

如果改动涉及组件字段、兼容关系或加载规则，也应同步检查：

- `src/cipher_genius/core/generator.py`
- `tests/unit/test_scheme_generator.py`

## 8. 相关文档

- `data/components/README.md`
- `docs/modules/retrieval_knowledge_base.md`
- `docs/agent_skills/skill_repo_map.md`
## 增量更新：企业文档 Ingestion（2026-03-24）

当前组件知识仍由 `knowledge/` 负责加载和运行时访问。

新增的 PDF / Word 企业文档读取能力已经拆到独立模块：

- `src/cipher_genius/ingestion/`

这样可以保持：

- `knowledge/` 负责结构化组件资产
- `ingestion/` 负责原始文档解析与 chunk 输出
- `retrieval/` 负责运行时 evidence 检索
