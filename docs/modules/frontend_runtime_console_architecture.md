# 前端运行控制台架构设计

最后更新：2026-04-20  
状态：active

## 1. 文档定位

本文档用于定义 MedCipher Studio 下一阶段前端主工作台的正式信息架构。  
重点不是继续修补旧页面，而是把前端收口为一套真正围绕后端稳定对象构建的运行控制台。

本文适用于：

- `frontend/` 新一轮页面与状态架构重构
- 运行中主流程可视化
- 攻击闭环透明化
- replay / 交付 / 证据联动

本文不负责：

- 定义后端新接口
- 夸大当前沙盒或攻击能力
- 把未实现功能写成既成事实

## 2. 当前为什么需要这份文档

当前前端已经完成了一轮大重构，但整体仍偏向：

- 工作台收口
- 报告页收口
- 业务模式页面收口

这些工作是必要的，但还不足以支撑下一阶段的目标。  
下一阶段前端要承接的不只是“展示结果”，而是：

- 让用户发起一次完整运行
- 观察运行中的真实阶段变化
- 理解攻击闭环与沙盒状态
- 回看每一轮补充验证和修补回归
- 把报告、代码、证据和 replay 真正联动起来

因此，前端的核心不应再只是“报告页”或“工作台表单”，而应升级为：

**运行控制台 + 攻击闭环工作台 + 交付与复盘中心**

## 3. 设计原则

### 3.1 以前端消费真实后端对象为中心

前端页面必须围绕下列稳定对象组织，而不是围绕临时卡片组织：

- `workflow_trace`
- `delivery.backend_architecture.*`
- `delivery.attack_loop`
- `delivery.context_projections`
- `delivery.memory_handoffs`
- replay / timeline / snapshots / lineage

### 3.2 对当前能力边界保持诚实

前端文案必须明确：

- 当前攻击执行是受控演示级验证环境
- 当前沙盒不是生产级容器隔离执行平面
- 当前 same-run retry 仍是第一版
- 当前 replay 是本地回放中心第一版

### 3.3 把“运行中”作为第一等公民

前端不应只擅长展示最终报告，也必须擅长展示：

- 现在运行到哪一步
- 当前阶段为什么在做这件事
- 这一轮攻击为什么继续或停止
- 哪一步被跳过
- 哪一步进入 patch / regression

### 3.4 人话解释优先，工程细节折叠

默认展示层应优先回答：

- 系统现在正在做什么
- 为什么这么做
- 结果意味着什么

工程细节、原始日志、原始事件与结构化合同放入折叠区或专家视图。

## 4. 新前端主架构

推荐把前端主架构拆为 6 个一级工作区。

### 4.1 任务发起层

定位：

- 发起一次新的运行
- 预结构化输入需求与约束
- 让后端前半段更稳定地构建 analyst/context 输入

必须包含：

- 自然语言需求输入
- 约束条件输入
  - 标准
  - 性能
  - 语言
  - 交付格式
- 运行模式选择
  - 普通执行
  - 流式观测
- 是否允许自动 patch / regression
- 最大补充验证轮数
- 证据增强选项
- 提交后自动进入 Live Console

设计原则：

- 不能只保留一个大文本框
- 必须做轻结构化输入
- 高级选项放在可展开区域，避免首页过重

### 4.2 主流程实时观测层

定位：

- 作为整个前端的核心控制台
- 承载运行中的阶段观测、解释、日志和指标

推荐布局：

- 左侧：阶段轨道
- 中间：当前阶段详情
- 右侧：解释面板
- 底部：日志与指标页签

阶段轨道需要覆盖真实主线：

1. Analyst
2. Context Builder
3. Architect
4. Audit
5. Engineer
6. Target Deployer
7. Attack Executor
8. Vulnerability Evaluation
9. Patch Reflection
10. Delivery

每个阶段节点至少展示：

- `pending / running / success / failed / skipped`
- 开始时间
- 耗时
- 是否重试
- 是否被 synthetic dispatch 跳过
- 是否进入 patch / regression

当前阶段详情至少展示：

- 当前阶段在做什么
- 输入摘要
- 输出摘要
- evidence / contract 摘要
- 为什么通过、为什么失败
- 是否已移交下一阶段

解释面板默认展示：

- 系统现在正在做什么
- 为什么这么做
- 结果意味着什么

底部至少有以下 tabs：

- Events
- Logs
- Telemetry
- Findings

### 4.3 攻击可视化层

定位：

- 单独承载 attack loop
- 不与普通日志抽屉混在一起

必须拆成 6 段：

1. Attack Planning
2. Governance Check
3. Sandbox Execution
4. Telemetry
5. Vulnerability Evaluation
6. Expert Gate / Patch Decision

#### Attack Planning

至少展示：

- 本轮动作
  - execute
  - continue
  - replan
  - handoff
  - stop
- 攻击族
  - oracle_probe
  - misuse_case
  - regression_check
- 本轮任务数量
- 为什么这样决定

#### Governance Check

至少展示：

- runtime 白名单是否通过
- attack family 是否允许
- task 数量是否超预算
- probe / timeout 是否超预算

#### Sandbox Execution

至少展示：

- 目标服务启动状态
- 健康检查状态
- probe 发送进度
- 当前样本数
- 轨迹工件是否生成
- 指标工件是否生成

#### Telemetry

至少可视化：

- latency
- tx_bytes
- rx_bytes
- cpu
- memory
- traffic_series

#### Vulnerability Evaluation

至少展示：

- 风险信号
- 置信度
- 风险等级
- 是否建议 patch
- 残余风险

#### Expert Gate / Patch Decision

至少展示：

- 直接交付
- 补充攻击
- 进入 patch
- 回归攻击

这一块推荐使用回合制视图，不应只做成单次状态卡。

### 4.4 服务器 / 沙盒实时监控层

定位：

- 作为 attack loop 的支撑视图
- 不是普通 DevOps 面板

必须围绕当前运行上下文展示：

- 当前 sandbox 实例状态
- CPU / Memory
- 请求速率
- 响应延迟
- 网络吞吐
- 当前 probe 数
- error count / timeout count

推荐实现：

- 折线图 + 时间窗滚动
- 与当前 round / 当前 attack task 联动
- 图表变化应能被解释为“当前攻击动作的一部分”

### 4.5 交付工作区

定位：

- 统一查看代码、伪代码、报告与证据
- 承接最终企业交付

推荐四栏联动：

- 代码
- 伪代码
- 报告
- 证据 / 结论

至少支持：

- 查看最终代码
- 查看 patch diff
- 查看伪代码
- 查看最终报告
- 下载 artifact
- 下载审计包
- 下载 replay 包

理想联动：

- 点击报告中的结论，联动到对应代码段或 finding

### 4.6 Replay / 复盘层

定位：

- 作为系统差异化页面之一
- 承载 timeline、事件、快照与 lineage

至少要有：

- Timeline
- Event Explorer
- Snapshots
- Drilldown
- Lineage

推荐阅读顺序：

1. 先看 Timeline
2. 再看关键事件
3. 再看关键快照
4. 最后钻 lineage

## 5. 推荐实时事件模型

前端不应直接吞原始文本流，而应尽量消费稳定事件模型。

推荐至少支持以下类型：

```ts
type StreamEvent =
  | { type: 'run_started'; runId: string }
  | { type: 'stage_started'; stage: string; ts: number }
  | { type: 'stage_status'; stage: string; status: 'pending' | 'running' | 'success' | 'failed' | 'skipped' }
  | { type: 'stage_finished'; stage: string; ts: number; status: string }
  | { type: 'stage_summary'; stage: string; summary: string }
  | { type: 'stage_explanation'; stage: string; doing: string; why: string; meaning: string }
  | { type: 'handoff_emitted'; from: string; to: string; contract: unknown }
  | { type: 'artifact_summary'; stage: string; kind: string; summary: string }
  | { type: 'attack_plan'; action: string; family: string; specsCount: number }
  | { type: 'dispatch_decision'; mode: 'real' | 'synthetic'; reason: string }
  | { type: 'telemetry_sample'; ts: number; latency: number; cpu: number; memory: number; tx: number; rx: number }
  | { type: 'finding'; severity: string; title: string; detail: string }
  | { type: 'gate_decision'; decision: string; rationale: string }
  | { type: 'retry_state'; stage: string; round: number; budgetUsed: number; budgetRemaining: number }
  | { type: 'run_snapshot'; snapshotId: string; label: string; stage: string }
  | { type: 'artifact_ready'; kind: string; url: string }
  | { type: 'run_finished'; status: string }
```

这套模型的价值是：

- 好做阶段轨道联动
- 好做 Attack Loop 拆段展示
- 好做 Telemetry 图表动态更新
- 好做人话解释面板
- 好做 Replay 快照入口

## 6. 推荐核心组件分层

### 6.1 P0 必需组件

- `RunCreator`
- `RunConsoleLayout`
- `StageRail`
- `StageInspector`
- `ExplanationPanel`
- `AttackLoopBoard`
- `TelemetryChart`
- `DeliveryWorkspace`
- `ReplayTimeline`

### 6.2 P1 增强组件

- `StageNodeCard`
- `AttackRoundCard`
- `SandboxMonitor`
- `FindingsTable`
- `CodePseudoReportView`
- `EventExplorer`
- `SnapshotDiffViewer`
- `ArtifactExportPanel`

## 7. 推荐落地顺序

### 2026-04-20 当前落地状态

当前已完成“运行控制台第一版桥接实现”，入口位于 React 专家模式的 `运行控制台` 页签。

已落地：

- `RunCreator`
  - 自然语言需求输入
  - 轻结构化约束输入
  - `stream / execute` 运行模式桥接
  - 回归轮数、代码生成、澄清门控等运行策略展示
- `Live Console`
  - 阶段轨道
  - 阶段详情
  - 人话解释面板
  - projection / handoff / stream log 摘要桥接
- `Attack Loop`
  - Attack Planning
  - Governance Check
  - Sandbox Execution
  - 轻量 telemetry 图表
  - Vulnerability Evaluation
  - Expert Gate / Patch 摘要
- 底部预览区
  - Events
  - Delivery readiness
  - Replay readiness

同步接入：

- `App.jsx` 专家模式路由
- `StudioHeaderView.jsx` 专家导航
- `useRunDraftStore`
- `useRunSessionStore`
- `useStageConsoleStore`
- `useAttackLoopStore`

当前仍未完成：

- 独立 `Delivery Workspace`
- 独立 `Replay / 复盘` 页面
- ECharts 实时滚动 telemetry
- 后端标准化 `StreamEvent` 全量分发到前端状态总线
- 生产级隔离沙盒展示

当前口径应保持为：这是第一版可见入口和状态骨架，不是完整前端运行控制台架构全部完成。

### 第一步：先稳事件模型

先完成：

- 流式事件类型定义
- 阶段状态统一对象
- attack loop 相关事件统一对象

### 第二步：先做三个核心页面

优先落地：

1. `RunCreator`
2. `Live Console`
3. `Attack Loop`

原因：

- 这三页最能体现“系统正在运行”
- 也最能验证前后端对象是否对齐

### 第三步：再补交付与 replay

继续落地：

1. `Delivery Workspace`
2. `Replay / 复盘`

### 第四步：最后补增强体验

- 更强图表
- 更深 drilldown
- 更细工件联动
- 更强报告联动

## 8. 与现有页面的关系

当前已有页面不应全部废弃，但后续应逐步让它们服从新架构：

- `WorkbenchView`
  - 逐步演进为 `RunCreator + Live Console` 的承载入口
- 报告页相关组件
  - 逐步沉淀到 `Delivery Workspace`
- 攻击闭环相关面板
  - 逐步沉淀到独立 `Attack Loop`
- replay 相关展示
  - 逐步沉淀到独立 `Replay` 页面

目标不是继续堆旧页面，而是：

**让现有页面逐步向新工作台架构迁移**

## 9. 当前边界提醒

前端设计和文案必须保持以下诚实边界：

- 当前攻击执行是本地受控验证，不是公网实战渗透
- 当前沙盒仍不是生产级容器隔离平台
- 当前自动 patch / regression 仍需遵守后端现有预算与闭环边界
- 当前多轮闭环仍是第一阶段，不应在 UI 上误写成“无限自主优化”

## 10. 结论

下一阶段前端的核心，不应再定义为“继续美化页面”，而应定义为：

**构建一套围绕真实后端 pipeline 的运行控制台架构。**

这套架构的价值在于：

- 能让外行看懂系统现在在做什么
- 能让专家追踪系统为什么这样做
- 能让答辩场景展示系统的技术深度
- 能让后续前端重构不再失去主线
