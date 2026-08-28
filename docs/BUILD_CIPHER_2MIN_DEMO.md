# BuildCipher 两分钟演示路线

目标：用一份真实 IFC 输入证明 BuildCipher 不是建筑话术模板，而是能够执行“导入—验真—攻击—加固—证据交付”的 localhost Agent 工作流。

## 演示前准备

1. 运行 `start.bat`，确认前端 `http://127.0.0.1:5173` 与 API `http://127.0.0.1:8000/docs` 可访问；
2. 准备仓库内 `data/demo/buildtrust_v1/coordination.ifc`；
3. 打开“项目工作台”，保持浏览器缩放为 100%。

## 0:00—0:15：问题与产品

讲法：建筑模型跨建设、设计、总包、分包和监理流转时，核心问题不是“有没有加密”，而是能否证明文件没被改、版本没回滚、访问没有越权、设备数据没有冒充或重放。BuildCipher 把这些问题变成可执行验证和证据。

## 0:15—0:40：导入真实 IFC

在“项目工作台 → 导入 IFC 工程资产”选择 `coordination.ifc`，版本填 `v3`、父版本填 `v2`，点击“导入并验真”。展示：

- schema 为 `IFC4`；
- 实体数量为 `3`；
- 文件 SHA-256；
- 生成的 localhost `construction-import://...` 引用。

讲法：系统没有执行上传文件，只读取 STEP 结构和字节证据；几何、碰撞与规范校核不在第一版边界内。

## 0:40—1:15：同输入前后对照

进入“攻防验证”，点击“运行前后对照”。同一 IFC 输入分别进入 baseline 与 hardened：

- baseline：`0/5` 阻断；
- hardened：`5/5` 阻断；
- 五项分别是 IFC 篡改、旧版本回滚、分包越权、设备冒充、遥测重放。

讲法：LLM 可参与分析与解释，但这五项结论来自确定性 localhost 运行时，不依赖 LLM 自述。

## 1:15—1:45：证据交付

展示验证表和“交付中心”中的证据引用。说明每项结果保留 before/after 状态、修复建议、JSON 工件、SHA-256 引用和本地哈希链；benchmark 另有 8 个案例验证建筑 Skill、报告模板和必需章节路由。

## 1:45—2:00：能力边界与价值

讲法：第一版只承诺 localhost 的 IFC 结构检查、交付验真、角色级授权、IoT 消息可信和证据链；它不是商业 CDE、BIM 规则引擎、PKI/KMS/HSM 或正式合规认证。价值在于把建筑可信交付从方案文字变成可复核的工程证据。

## 现场备用

如果前端临时不可用，运行：

```powershell
$env:PYTHONPATH='src'
python scripts/validate_buildtrust_v1.py --output .cache/buildtrust-v1-validation.json
```

通过标准：`status=passed`、IFC 合同匹配、baseline `0/5`、hardened `5/5`、治理检查无失败项。
