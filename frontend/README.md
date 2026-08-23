# BuildCipher Studio Frontend

`frontend/` 是 BuildCipher Studio 的 React + Vite 前端。界面保留原项目的白蓝企业工作台视觉语言、渐变层级、圆角卡片、状态标签与轻量动效，`BuildTrust` 作为建筑工程可信交付能力呈现。

## 页面结构

- `工程总览`：展示五类建筑攻击、基线/加固结果和可信交付主线。
- `项目工作台`：输入 BIM/IFC、工地 IoT、签批和验收需求，可使用建筑工程模板与快捷维度。
- `可信协同`：表达建设、设计、总包、分包、监理的责任边界与证据结构。
- `安全验证`：比较五类确定性攻击的补丁前后状态，可调用本地参考演示接口。
- `可信交付`：汇总结论、证据引用、导出入口和第一版能力边界。
- 专家模式继续保留 MAS、LLM provider 配置、报告和运行透明化能力，但不再加载医药业务页面。

核心文件：

- `src/features/construction/ConstructionWorkspaceView.jsx`
- `src/features/construction/constructionBusinessState.js`
- `src/features/mas/StudioShell.jsx`
- `src/features/mas/StudioSidebarView.jsx`
- `src/features/mas/WorkbenchView.jsx`

原 `src/features/biopharma/` 领域文件已删除；医药路由、模板、快捷骨架、合规提示和报告场景也已从前端运行时移除。视觉系统位于共享组件和 `src/index.css`，不依赖医药领域模块。

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
- IFC 当前按文件字节做结构与摘要验证，不是实体、GUID 或模型视图级解析器。
- 本地身份与消息认证是参考 HMAC provider，不等同于生产 PKI、人员证书、KMS 或 HSM。
- 权限到角色与交付包级，尚未实现字段、属性或构件级最小披露。
- 证据账本是本地 JSON 哈希链；尚未接入外部可信时间、WORM 或真实 CDE/BIM 平台。

## 2026-08-12 验证

- `npm run build` 通过，共转换 91 个模块。
- 构建产物只生成 `ConstructionWorkspaceView` 业务分包，不生成 Biopharma 分包。
- 桌面端实测工程总览与五个业务入口可见。
- 390 × 844 移动端实测使用横向工程导航；文档宽度与视口宽度一致，无页面级横向溢出。
- 无后端运行时，页面会如实显示“后端服务未连接”；这不影响前端静态结构验证。
