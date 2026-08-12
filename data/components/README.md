# 组件资产说明

最后更新：2026-03-24
状态：active

## 1. 目录职责

本目录存放密码组件的静态 YAML 资产，是当前项目最核心的领域知识来源之一。

这些资产既服务当前运行时组件库，也会是后续统一知识库建设的第一批原始材料。

## 2. 当前目录结构

当前按组件类型组织，例如：

- `primitives/`
  - 原语、基础算法等
- `modes/`
  - 模式、AEAD、分组模式等
- `protocols/`
  - 协议或更高层组合能力

新增子目录时，应保证其语义清晰，并且不会与现有类别混淆。

## 3. 单个 YAML 应表达什么

当前 `src/cipher_genius/knowledge/components.py` 会从 YAML 中解析出：

- 基本标识
  - `name`
  - `full_name`
  - `category`
  - `description`
- 参数信息
  - `key_size`
  - `block_size`
  - `output_size`
  - `rounds`
  - `nonce_size`
  - `tag_size`
- 性能信息
  - `software_speed`
  - `hardware_speed`
  - `memory`
  - `power`
- 安全信息
  - `security_level`
  - `best_attack`
  - `attack_complexity`
  - `status`
  - `standardized`
  - `proven_security`
- 关系与适用性
  - `compatible_with`
  - `not_compatible_with`
  - `use_cases`
  - `not_recommended_for`
- 引用与备注
  - `references`
  - `implementation_notes`

## 4. 为什么这里要维护得足够结构化

组件资产不是只给模型看的自然语言文本，它至少承担三层价值：

1. 当前生成器和规则判断的运行时输入
2. 后续知识库中的“组件知识卡”原始来源
3. 报告与审计中可引用的能力边界说明

如果 YAML 只写简介、不写结构化字段，后面会同时影响：

- 组件筛选
- 审计判断
- 检索过滤
- 报告引用

## 5. 与统一知识库的关系

后续接入企业知识库时，不建议抛弃这批 YAML，而建议做“双轨复用”：

- 一条轨：继续作为运行时组件对象的加载源
- 一条轨：转换成统一知识对象 schema 中的 `component` 文档

推荐映射方向：

- 一个 YAML 文件
  - 对应一个或多个组件知识卡
- `description` / `implementation_notes`
  - 作为可引用说明内容
- `security` / `performance` / `compatibility`
  - 作为 metadata 和过滤条件

## 6. 新增或修改 YAML 时的建议

- 优先补结构化字段，不要只加自然语言说明
- 兼容关系要显式写出，不要完全依赖推断
- 如涉及企业常见限制，优先写在 `not_recommended_for` 或 `implementation_notes`
- 如存在标准、论文或官方文档依据，尽量补到 `references`

## 7. 修改后要同步检查什么

- `src/cipher_genius/knowledge/components.py`
- `src/cipher_genius/core/generator.py`
- `tests/unit/test_scheme_generator.py`
- `src/cipher_genius/knowledge/README.md`
- `docs/modules/retrieval_knowledge_base.md`
