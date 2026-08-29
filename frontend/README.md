# BuildCipher Studio Frontend

`frontend/` 是 BuildCipher Studio 的 React + Vite 前端。界面保留原项目的白蓝企业工作台视觉语言、渐变层级、圆角卡片、状态标签与轻量动效，并统一以 `BuildCipher` 呈现建筑工程可信交付能力。

业务侧边栏提供“业务模式 / 专家模式”直接切换；“专家模式”始终先进入专家总览，组件库保持当前模式不变。一次五攻击对照运行产生的阻断数与证据数会在工程总览、攻防验证和交付中心之间保持一致。

## 页面结构

- `工程总览`：展示五类建筑攻击、基线/加固结果和可信交付主线。
- `项目工作台`：输入建筑需求，并导入 localhost IFC，显示 schema、实体数、版本和 SHA-256。
- `可信协同`：表达建设、设计、总包、分包、监理的责任边界与证据结构。
- `攻防验证`：让同一内置或导入 IFC 运行 baseline/hardened 五攻击对照，并下钻 SHA-256、manifest、版本指针、RBAC、设备凭据、counter、nonce 与时间窗的原始判断字段。
- `交付中心`：汇总结论、证据引用和第一版能力边界；即使尚未生成 MAS 交付包，也能下载当前建筑验证快照的 JSON、Markdown、LaTeX 和 HTML。
- 专家模式继续保留 MAS、LLM provider 配置、报告和运行透明化能力，但不再加载旧行业业务页面。
- 多格式代码页只把具备函数/类/算法结构的 C11、Python 和伪代码标记为完成；单独免责声明不会再显示为“代码已完整生成”。
- MAS 完成后保持用户当前页面，不再强制跳到工作台。代码预览最多渲染前 500 行；完整 JSON/Markdown 只在打开对应标签时生成，复制操作仍使用完整内容。代码结果异常只隔离结果区，不会清空整个工作台。
- MAS 运行历史在浏览器 `localStorage` 中只保存最近 20 条轻量摘要，不再复制完整代码、证据、时间线和沙箱产物；完整结果由当前会话与后端项目证据承载，避免大结果超过浏览器配额后导致白屏。

核心文件：

- `src/features/construction/ConstructionWorkspaceView.jsx`
- `src/features/construction/constructionBusinessState.js`
- `src/features/mas/StudioShell.jsx`
- `src/features/mas/StudioSidebarView.jsx`
- `src/features/mas/WorkbenchView.jsx`

旧行业领域文件已删除；旧行业路由、模板、快捷骨架、合规提示和报告场景也已从前端运行时移除。视觉系统位于共享组件和 `src/index.css`，不依赖旧行业领域模块。

## 本地启动

先在项目根目录启动后端：

```powershell
poetry run buildcipher-api
```

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

浏览器访问 `http://127.0.0.1:5173/`。后端默认连接 `http://127.0.0.1:8000`；LLM 接口仍由设置页和后端 provider 接口管理。

生产构建：

```powershell
cd frontend
npm run build
```

## 当前能力边界

- 前端是 localhost 第一版，不包含 AWS 页面或部署结构。
- IFC 当前检查 STEP 结构、schema、实体计数与候选 GlobalId；不是几何、碰撞、规范或完整模型视图引擎。
- 本地身份与消息认证是参考 HMAC provider，不等同于生产 PKI、人员证书、KMS 或 HSM。
- 权限到角色与交付包级，尚未实现字段、属性或构件级最小披露。
- 证据账本是本地 JSON 哈希链；尚未接入外部可信时间、WORM 或真实 CDE/BIM 平台。
- 刷新页面后可恢复运行摘要，但浏览器本地摘要不是完整交付包；完整历史应从后端 case/evidence 记录读取或导出。

## 2026-08-28 验证

- `npm run build` 通过，共转换 94 个模块。
- 生产构建包含 IFC 导入与 baseline/hardened 对照界面；项目当前没有定义独立 `npm run lint` 脚本。
- 建筑导出按钮由页面直接生成四种文件，并通过 `aria-live` 返回下载成功或失败状态；不再把格式对象误传给 MAS 导出函数。
- 构建产物只生成 `ConstructionWorkspaceView` 业务分包，不生成旧行业分包。
- 桌面端实测工程总览与五个业务入口可见。
- 390 × 844 移动端实测使用横向工程导航；文档宽度与视口宽度一致，无页面级横向溢出。
- 无后端运行时，页面会如实显示“后端服务未连接”；这不影响前端静态结构验证。
