# BuildCipher Construction Frontend

第一版建筑业务界面统一承载场景总览、项目输入、可信协同依据、攻防验证和可信交付。

- 数据源沿用现有 MAS `delivery.attack_loop`、case memory 与导出合同；
- `baseline` 与 `hardened` 使用同一五攻击列表进行前后对比；
- 工作台调用 `POST /api/v1/construction/assets/import` 导入 IFC，并显示 schema、实体数、版本和 SHA-256；
- 验证按钮调用 `POST /api/v1/construction/demo/run`，默认显示同一 IFC 的 baseline/hardened 真实对照；
- 攻防验证可在五项探针间切换，显示攻击构造、控制配置键、安全不变量、原始检查 JSON 以及 evidence/artifact 引用；
- 可信交付可直接导出当前建筑验证快照的 JSON、Markdown、LaTeX 和 HTML，不要求先生成 MAS 交付包；
- 当前不解析真实 IFC 几何、碰撞或规范，也不连接生产 CDE、IoT 总线或证书基础设施。
