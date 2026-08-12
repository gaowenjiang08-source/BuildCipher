# MAS Frontend Module

最后更新：2026-04-20
状态：active

## 2026-04-20 运行控制台第一版

本目录已新增 `RuntimeConsoleView.jsx`，作为专家模式下新的“运行控制台”入口。

第一版落地范围：

- `RunCreator`
  - 自然语言需求输入
  - 标准 / 性能 / 语言 / 交付格式约束
  - `stream / execute` 运行模式桥接
  - 最大回归轮数与代码生成策略展示
- `Live Console`
  - 阶段轨道
  - 当前阶段详情
  - “当前阶段在做什么 / 为什么这么做 / 结果意味着什么”的人话解释面板
  - 结构化 handoff、projection 与流式事件摘要桥接
- `Attack Loop`
  - Attack Planning
  - Governance Check
  - Sandbox Execution
  - Telemetry 轻量图表
  - Vulnerability Evaluation
  - Expert Gate / Patch 决策摘要
- `Events / Delivery / Replay` 底部预览
  - 最近事件
  - 代码 / 报告 / replay 准备度
  - 后续拆分 `Delivery Workspace` 与 `Replay / 复盘` 的承载位

同步新增的状态域：

- `useRunDraftStore`
- `useRunSessionStore`
- `useStageConsoleStore`
- `useAttackLoopStore`

当前实现方式：

- 由 `App.jsx` 把现有 MAS 状态桥接进新 store
- `RuntimeConsoleView.jsx` 同时消费 store 与现有派生数据
- 不新增后端接口
- 不修改 `delivery.attack_loop`、`delivery.sandbox_dispatcher`、`replayScope`、MAS 执行参数等既有契约

当前边界：

- 这不是完整替换 `WorkbenchView.jsx` 和 `ReportsView.jsx`
- 这不是最终 ECharts 沙盒监控页
- 这不是生产级容器隔离沙盒说明
- 这是新运行控制台架构的第一版可见入口和状态骨架

验证方式：

- `cd frontend`
- `npm run build`

## 模块职责

`frontend/src/features/mas/` 负责专家模式相关前端能力，主要服务于：

- MAS 流程透明化展示
- 报告与回放深挖
- 执行工作台
- 组件库与知识资产
- 资产运维与系统设置

## 下一阶段架构定位

本目录后续将逐步从“专家模式页面集合”演进为“运行控制台相关页面与组件主目录”。

下一阶段重点不再只是补报告页和局部面板，而是围绕以下一级工作区继续收口：

- 任务发起层
- 主流程实时观测层
- 攻击可视化层
- 服务器 / 沙盒监控层
- 交付工作区
- Replay / 复盘层

正式设计蓝图见：

- `docs/modules/frontend_runtime_console_architecture.md`
- `docs/modules/frontend_page_state_architecture.md`

当前推荐的 P0 页面 / 组件优先级：

- `RunCreator`
- `RunConsoleLayout`
- `StageRail`
- `StageInspector`
- `ExplanationPanel`
- `AttackLoopBoard`
- `TelemetryChart`
- `DeliveryWorkspace`
- `ReplayTimeline`

当前推荐的状态架构优先级：

- 先拆 `runDraftStore`
- 再拆 `runSessionStore`
- 再拆 `stageConsoleStore`
- 再拆 `attackLoopStore`
- 然后补 `deliveryStore`
- 最后补 `replayStore`

## 本轮重构重点

### 1. 顶部壳层重做

- `StudioHeaderView.jsx`
  - 已重写为干净中文版本
  - 强化模式切换、导航、项目状态、系统状态和业务回跳锚点展示

### 2. 共享壳层升级

- `StudioShell.jsx`
  - 继续作为专家模式与业务模式共享的页面外壳
  - 提供更稳定的页面宽度、留白和背景氛围

### 3. 状态反馈修复

- `useMasActions.js`
  - 已修复连接检测、LLM 验证、项目切换、知识导入、Qdrant 操作和 MAS 执行等用户可见提示文本

### 4. 交互稳态补齐

- `WorkbenchView.jsx`
  - 已统一补齐工作台核心按钮的 `type="button"`
- `ComponentsView.jsx`
  - 已补齐资产刷新按钮的 `type="button"`
- `ReportsOutcomePanels.jsx`
  - 已补齐交付导出按钮的 `type="button"`
- `App.jsx`
  - 已修复设置页与当前业务页同时渲染的问题
  - 已修复加载态卡片中的多余闭合标签

### 5. 报告页章节总览条

- `ReportsChapterSummaryBar.jsx`
  - 作为专家报告页新的“四段阅读地图”组件
  - 将长报告收敛为“总览摘要 / 主线透视 / 攻防闭环 / 证据与交付”四段
  - 提供一键跳转到总览、主线、攻击闭环和证据交付段的入口
- `ReportsView.jsx`
  - 已接入章节总览条，并将激活态绑定到主线命中、证据焦点和交付焦点
  - 让报告页在答辩演示时更适合先讲目录，再按层展开技术细节

### 6. 章节导览卡重做

- `ReportsSectionNavigator.jsx`
  - 已从普通按钮列表升级为三段式章节导览卡
  - 将报告页阅读路径拆成“先讲全貌 / 再讲攻击闭环 / 最后讲证据与交付”三组
  - 为不同组提供独立的色带、章节编号和状态提示，降低长报告页的视觉混乱感
  - 修正了 `flow/replay` 传入 `tone="info"` 但激活态未按主线色显示的问题
  - 同步清理报告页顶部的高可见英文标签与章节眉标，保持中文优先

### 7. 报告首页摘要卡重做

- `ReportsMainlinePanels.jsx`
  - 为 `ReportsHeroBanner` 新增了更适合答辩与汇报的“报告首页摘要”视觉层
  - 将右侧摘要区收口为：
    - 当前判定
    - 当前焦点
    - 攻击闭环
    - 代码交付
  - 将跳转入口重做为顺序化的“推荐讲解路径卡”，支持从首页直接切到主线、攻击或最终交付
  - 同步把高可见抬头改为中文优先，减少首页的中英混杂感

### 8. 专家模式首页重做

- `MissionView.jsx`
  - 已重做为专家模式的统一首页，而不是旧式信息堆叠面板
  - 首页会先展示：
    - 专家模式首页摘要
    - 当前主线推进快照
    - 推荐下一步入口
  - 角色区已升级为“专家席位与职责地图”，更适合向外行解释每个 Agent 的职责边界
  - 推进阶段区与讨论回放区仍保留原有功能，但已统一到新的视觉层级中
  - 首页现在支持直接跳到：
    - 专家报告页
    - 执行工作台
    - 推荐样例模板对应的工作台场景

### 9. 工作台首页摘要层

- `WorkbenchView.jsx`
  - 已新增工作台首页摘要层 `WorkbenchHeroBanner`
  - 将工作台最上方收口为两类信息：
    - 快照卡：当前项目 / 执行状态 / 交付收口
    - 推荐动作卡：启动主流程 / 路由推荐技能 / 套用样例模板
  - 保留原有 `runMas`、`stopRun`、`recommendSkill`、`applyTemplate` 等动作，不改变现有前端到后端的调用方式
  - 目标是让用户进入工作台后先理解“现在是什么状态、下一步最适合做什么”，再继续下钻到项目、参数、需求和审计细节

### 10. 工作台中段摘要层

- `WorkbenchView.jsx`
  - 新增 `WorkbenchInlineMetric`，用于统一中段摘要卡的视觉表达
  - `ControlSummary`
    - 现在会先解释当前执行总览，而不是只显示深色统计块
    - 将交付状态、执行引擎、候选方案、审计轮次统一为可扫读的摘要卡
  - `CurrentProjectSection`
    - 现在会先展示项目主线是否锁定、最近项目数量、待补项与决策记录等摘要
    - 再进入项目详情与项目切换区
  - `ExecutionControls`
    - 现在会先展示执行前摘要，明确“参数是否合适、澄清是否足够”这两个前置判断
    - 再进入运行参数、澄清输入和门控细节

### 11. 工作台后半段交互层

- `WorkbenchView.jsx`
  - `SkillModeSection`
    - 已补充技能锁定摘要、推荐结果摘要和技能模式卡
    - 将 `general` 等高可见类别展示收口为中文优先表达，但不修改底层稳定字段值
  - `RequirementComposer`
    - 已补充三步式需求编排引导，让用户先写需求、再补维度、最后套模板
  - `AuditArena`
    - 已收口候选方案、证据映射、交付落点与审计轮次的统一视图
    - 将 `Round / Compliance / Risk / Delivery Focus` 等高可见英文改为中文优先显示
  - `EngineerDeliveryPanel`
    - 已开始将工程尝试步骤显示改为中文可读标签，降低工作台中部的英文割裂感
  - `FinalDeliverySection`
    - 已升级为更完整的交付中心，集中展示最终方案、代码实现、导出入口、交付摘要和 JSON 概览

### 12. 运维与知识资产页重构

- `OpsView.jsx`
  - 已新增运维页摘要层，先讲清当前知识资产规模、导入任务状态和待治理副本数量
  - 已把企业知识导入区重组为三步式引导：
    - 准备企业资料
    - 补齐导入标签
    - 确认治理方式
  - 已将 `standard / policy / case / template` 等高可见文档类型展示切为中文优先
  - 已强化知识资产详情页的解释层，让单条资产记录可直接用于答辩说明、治理复核和演示讲解
  - 未修改知识导入接口、Qdrant 相关动作接口或资产结构字段，只优化前端展示与交互层

### 13. 设置页系统配置中心

- `SettingsView.jsx`
  - 已重构为“系统连接与模型配置”页面，而不是单纯的调试表单
  - 已新增入口摘要层与状态卡，用于先展示：
    - 当前模型提供方
    - 已配置密钥数量
    - 后端地址是否已填写
    - 后端环境是否已读取
  - 已补充三步式配置引导：
    - 确认后端地址
    - 选择模型提供方
    - 同步环境配置
  - 已将连接参数、模型密钥、配置动作、执行主线、后端环境快照拆成独立区块
  - 未修改设置数据结构、测试连接动作、环境同步动作或敏感字段脱敏逻辑，只优化前端展示与信息层级

### 14. 报告页证据与交付子面板

- `EvidenceLinkPanel.jsx`
  - 已新增证据联动摘要卡，让用户先看到这条证据影响了多少回放节点、审计轮次、整改建议和交付落点
  - 已将回放命中路径、高可见轮次标签和交接相关标签继续中文化
- `ReportsOutcomePanels.jsx`
  - 已继续收口 `DeliveryPanel` 的交付收尾层
  - 将高可见英文桥接标签改为中文优先表达，同时保留交付片段映射、导出和历史回放能力
  - 未修改交付导出动作、历史回载动作或交付映射数据结构，只优化展示层与答辩表达

### 15. 攻击闭环与审批对比子面板

- `AttackLoopPanel.jsx`
  - 顶部已改为“共享观察焦点总览”，先解释目标服务是否对齐、闭环推进状态、修补与交付成熟度
  - 保留 `ReplayFocusButton / ReplayFocusPill` 组件与现有焦点状态字段，只调整用户可见中文表达与摘要层级
  - 轮次卡、沙盒目标服务卡、修补与反思卡已更适合答辩演示顺序
- `SandboxDispatcherPanel.jsx`
  - 已重构为“沙盒调度与审批治理”面板，强调四段审批链而非调试信息堆叠
  - 已补充治理摘要层，突出审批节点数量、批准情况、阻断情况与焦点命中情况
  - 未修改 `sandbox_dispatcher` 数据结构、节点字段或点击联动动作
- `RoundComparisonPanel.jsx`
  - 已重构为“修补前后对比总览”，突出风险下降判断、同一服务对齐判断与新增关注点
  - 已将高可见 `baseline / regression / Replay` 文案压到中文壳层之下
  - 未修改轮次选择逻辑、漏洞裁决来源或对比差异计算方式

### 16. 报告页顶层讲解壳层

- `ReportsView.jsx`
  - 已同步统一顶层章节标签、章节分隔条和主线外框文案
  - 未修改章节锚点、主线 active 判定或延迟挂载结构
- `ReportsMainlinePanels.jsx`
  - 已继续统一主线总览、封面区、联动桥和证据收口桥的讲解语言
  - 将高可见英文和工程提示词继续收口为中文优先表达
  - 未修改主线数据推导、焦点回显和跳转动作
- `ReplayFocusLegendPanel.jsx`
  - 已升级为“共享焦点图例与当前状态”
  - 新增顶部阅读提示层，帮助先区分主线焦点与深钻焦点
- `ReportsChapterSummaryBar.jsx`
  - 已统一为“四段阅读总览”，更适合作为报告页顶部的答辩导航条
- `ReportsSectionNavigator.jsx`
  - 已继续把章节导航做成讲解路线选择器，而不是偏工程的模块目录
- `ReportsQuickMap.jsx`
  - 已补强右侧小地图的说明语义，降低首次阅读门槛

### 17. 摘要层与专家入口

- `ReportsSummaryPanels.jsx`
  - 已继续收口报告页上半段摘要层
  - 项目、需求、审计三块现在会先回答“当前状态是什么、还差什么、下一步能不能推进”
- `ReportsOutcomePanels.jsx`
  - 已继续收口可信度与最终交付的顶部摘要层
  - 让“为什么可信、能否导出、是否可复盘”在进入细节前先说清楚
- `StudioHeaderView.jsx`
  - 已继续统一专家模式入口头部的中文表达
  - 让专家模式首页与报告页在语言和讲解顺序上更像同一套产品

## 当前模块结构

- `MissionView.jsx`
  - 专家透明化总览
- `RuntimeConsoleView.jsx`
  - 运行控制台第一版，集中承载任务发起、主流程观测、攻击闭环和交付 / replay 预览
- `ReportsView.jsx`
  - 报告与 Replay 深挖
- `WorkbenchView.jsx`
  - 专家执行工作台
- `ComponentsView.jsx`
  - 密码组件与能力资产
- `OpsView.jsx`
  - 资产与运维操作
- `SettingsView.jsx`
  - 前端与后端连接设置
- `useMasActions.js`
  - 前端侧 MAS 操作与消息反馈封装

## 对接原则

- 不修改后端 MAS 接口契约
- 不修改 skill 路由、报告接口和回放接口
- 优先通过前端展示层、适配层和共享组件层完成体验优化

## 下一步建议

- 继续收口 `ReportsView.jsx` 及其子面板里的历史文案与信息层级
- 逐步把 `App.jsx` 中的 MAS 视图配置与常量继续下沉到模块内，减少顶层文件体积
- 继续围绕报告页和工作台做统一视觉规范，避免新旧面板在信息密度和交互风格上割裂
