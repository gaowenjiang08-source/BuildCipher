# BuildTrust Construction Frontend

第一版建筑业务界面统一承载场景总览、项目输入、可信协同依据、安全验证和可信交付。

- 数据源沿用现有 MAS `delivery.attack_loop`、case memory 与导出合同；
- `baseline` 与 `hardened` 使用同一五攻击列表进行前后对比；
- 独立演示按钮调用 `POST /api/v1/construction/demo/run`；
- 当前不解析真实 IFC 几何，也不连接生产 CDE、IoT 总线或证书基础设施。
