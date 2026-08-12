# AGENTS.md

本文件约束整个仓库的协作方式，适用于人类开发者与任何代码 Agent。

## 核心要求

每次代码变更，都必须同步检查并更新受影响的 Markdown 文档与技术文档，确保文档与代码保持一致。

## 文档同步规则

1. 如果变更涉及后端接口、请求结构、返回字段或运行方式：
   - 必须同步检查并更新 `README.md`
   - 必须同步检查并更新 `QUICK_START_V3.md`
   - 必须同步检查并更新 `docs/TECHNICAL_DOCUMENTATION.md`

2. 如果变更涉及 Agent 流程、MAS 编排、可信度评分、技能系统、知识库或报告结构：
   - 必须同步检查并更新 `docs/TECHNICAL_DOCUMENTATION.md`
   - 必须同步检查并更新 `DOC_INDEX.md`

3. 如果变更涉及前端界面、交互流程、入口页、操作说明：
   - 必须同步检查并更新 `frontend/README.md`
   - 必须同步检查并更新 `QUICK_START_V3.md`

4. 如果变更涉及 Streamlit 兼容入口：
   - 必须同步检查并更新 `streamlit/README.md`

## 提交前自检

在结束一次代码修改前，必须确认以下事项：

- 文档中出现的启动方式、端口、API 路径与代码一致
- 文档中出现的功能描述、能力边界、限制条件与代码一致
- 不保留已经删除、下线或未实现功能的描述
- 如果本次变更不需要更新文档，必须在交付说明中明确写出原因

## 推荐做法

- 小改动至少更新受影响模块的说明
- 中等以上改动同时更新 `README.md`、`QUICK_START_V3.md` 和 `docs/TECHNICAL_DOCUMENTATION.md`
- 新增能力时，优先在技术文档中补“输入/输出/流程/限制/验证方式”

