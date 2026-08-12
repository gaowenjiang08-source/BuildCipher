# Reporting 模块说明

最后更新：2026-03-24
状态：active

## 1. 目录职责

本目录负责企业交付与用户可见报告层的文本本地化、模板组织和交付内容收口。

这里解决的是：

- 中文优先的显示词与报告标题
- 审计、合规、漏洞、可信度等输出的本地化
- 模板章节与交付结构的注册与组织

这里不负责：

- 主链生成逻辑
- API schema 定义
- 前端具体渲染组件

## 2. 当前关键入口

- `localization.py`
  - 中文优先的状态名、可信度、支持等级、建议文本、本地化替换与交付显示词
- `templates.py`
  - 企业交付模板注册与解析顺序

## 3. 核心流程

当前 reporting 层主要承担两类工作：

1. 接收主链输出的稳定字段
2. 补充中文显示词、模板章节和导出友好结构

也就是说，这一层更适合做“显示层本地化与交付包装”，而不是篡改底层契约字段。

## 4. 稳定约束

- 面向用户的交付默认中文优先
- `actor`、`status`、`trust_level`、`support_level`、`scenario` 等稳定字段不应直接改值
- 需要本地化时，优先通过 `*_label` 或本地化后的显示结构完成
- 报告标题、建议、模板章节、推荐理由应以中文为主，但不破坏现有 benchmark 和接口契约

## 5. 常见改动点

- 改显示词：
  - 优先改 `localization.py`
- 改模板章节：
  - 优先改 `templates.py`
- 改报告建议文案或中文兜底：
  - 同时检查 `report_service.py` 与相关回归测试

## 6. 联动影响

改动本目录时，通常会影响：

- `src/cipher_genius/api/report_service.py`
- `src/cipher_genius/api/schemas.py`
- `frontend/src/features/mas/ReportsView.jsx`
- `frontend/src/components/DisplayValue.jsx`
- `tests/api/test_api_mas.py`

## 7. 验证方式

至少应完成：

- 中文交付相关 API 回归
- 关键报告是否保留中文标题和中文建议
- 页面展示与导出物中的标题、状态词、建议项是否一致

## 8. 相关文档

- `docs/agent_skills/skill_benchmark_reporting.md`
- `docs/TECHNICAL_DOCUMENTATION.md`
- `frontend/README.md`
