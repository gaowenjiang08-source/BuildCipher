# 前端页面树与状态架构设计

最后更新：2026-04-20  
状态：active

## 1. 文档定位

本文档是对“前端运行控制台架构设计”的进一步落地。  
上一份文档回答的是“前端应该有哪些一级工作区”；本文回答的是：

- 页面树应该怎么拆
- Zustand 状态树应该怎么拆
- 实时事件如何进入前端状态
- 哪些状态属于全局，哪些状态属于页面，哪些状态只应属于临时 UI

本文适用于：

- 下一阶段 React 页面重构
- Zustand store 规划
- 流式事件消费设计
- Attack Loop、Delivery、Replay 的状态联动

本文不负责：

- 定义新的后端字段
- 把现有页面一次性全部推翻
- 把尚未落地的后端能力假设成已稳定可用

## 2. 为什么还要再补这份文档

只有一级信息架构还不够。  
如果没有页面树和状态树设计，前端真正开工时很容易重新回到以下问题：

- 页面壳层清楚，但状态散落在多个组件里
- 同一份运行数据被多个页面各自加工
- 流式事件直接被组件消费，导致难以复用和回放
- Attack Loop、Delivery、Replay 之间无法共享同一份运行上下文

因此，这一层文档的目标是：

**先把前端“结构”和“状态”固定下来，再开始大规模写页面。**

## 3. 页面树设计

推荐下一阶段以前端“运行控制台”作为核心页面树，而不是继续围绕旧页面名做增量拼接。

### 3.1 一级页面树

推荐一级页面如下：

1. `Run Creator`
2. `Live Console`
3. `Attack Loop`
4. `Delivery Workspace`
5. `Replay Center`
6. `Knowledge Ops`
7. `System Settings`

说明：

- `Run Creator`、`Live Console`、`Attack Loop` 是 P0
- `Delivery Workspace`、`Replay Center` 是 P1 主增强
- `Knowledge Ops`、`System Settings` 可以在现有页面基础上继续维护

### 3.2 推荐页面关系

#### Run Creator

作用：

- 创建一次新的 case / run
- 提交后直接跳转到 `Live Console`

关键子区块：

- 需求输入
- 约束输入
- 执行方式选择
- 攻击/回归高级选项
- 知识增强选项
- 最近一次运行入口

#### Live Console

作用：

- 作为整个系统的主运行台
- 负责主流程阶段观测

关键子区块：

- 阶段轨道
- 当前阶段详情
- 人话解释面板
- 事件 / 日志 / 遥测 / 发现项 tabs

#### Attack Loop

作用：

- 承载攻防闭环
- 单独展示攻击规划、治理、执行、评估、修补和回归

关键子区块：

- 回合导航
- 攻击规划面板
- 治理检查面板
- 沙盒执行面板
- Telemetry 图表面板
- 漏洞评估面板
- Expert Gate / Patch 决策面板

#### Delivery Workspace

作用：

- 统一查看最终交付物

关键子区块：

- 代码视图
- 伪代码视图
- patch diff
- 报告视图
- 证据 / 结论联动
- 导出面板

#### Replay Center

作用：

- 统一复盘一次运行

关键子区块：

- Timeline
- Event Explorer
- Snapshots
- Drilldown
- Lineage

### 3.3 与现有页面的迁移关系

推荐迁移方式：

- 现有 `WorkbenchView`
  - 演进为 `Run Creator + Live Console` 的承载入口
- 现有攻击闭环相关报告面板
  - 抽出为独立 `Attack Loop`
- 现有交付相关区块
  - 抽出为 `Delivery Workspace`
- 现有 replay 相关面板
  - 抽出为 `Replay Center`

结论：

- 不是一次性删旧页面
- 而是分阶段把旧页面能力迁移到新页面树

## 4. Zustand 状态树设计

下一阶段建议不要继续把所有状态堆在一个总 store 中。  
推荐按“状态域”拆成多个 store。

### 4.1 推荐状态域

建议至少拆成 7 个状态域：

1. `appShellStore`
2. `runDraftStore`
3. `runSessionStore`
4. `stageConsoleStore`
5. `attackLoopStore`
6. `deliveryStore`
7. `replayStore`

必要时再保留：

8. `knowledgeOpsStore`
9. `settingsStore`

### 4.2 各状态域职责

#### appShellStore

负责：

- 当前模式
  - 业务模式
  - 专家模式
- 顶层导航状态
- 当前选中的 case / run
- 全局 loading / error banner
- 页面切换时共享的轻量上下文

不负责：

- 某个页面的内部图表状态
- 某轮攻击的详细数据

#### runDraftStore

负责：

- `Run Creator` 页中的草稿状态
- 自然语言需求
- 结构化约束
- 运行模式
- 攻击回归选项
- 证据增强选项

特点：

- 提交前存在
- 提交成功后可以被清空或转存

#### runSessionStore

负责：

- 当前运行实例的全局状态
- run 基本信息
- 总体运行状态
- 当前阶段
- 当前阶段开始时间
- 当前运行是否完成
- 当前运行是否失败

这是最核心的跨页面运行状态域。

#### stageConsoleStore

负责：

- 阶段轨道状态
- 每个阶段的状态、耗时、跳过原因、重试信息
- 当前选中的阶段
- 当前阶段摘要
- 当前阶段解释
- 当前事件 tabs 的筛选条件

这部分主要服务 `Live Console`。

#### attackLoopStore

负责：

- 当前攻击轮次
- baseline / retry / regression 轮次集合
- 每轮的 action / family / specsCount
- synthetic / real dispatch 状态
- 沙盒执行状态
- telemetry 序列
- findings
- expert gate 决策
- patch / regression 摘要

这部分主要服务 `Attack Loop` 页面。

#### deliveryStore

负责：

- 最终交付摘要
- 代码 / 伪代码 / patch diff 视图状态
- 当前选中的报告章节
- 当前选中的证据 / 结论 / 工件
- 导出动作状态

#### replayStore

负责：

- 当前 replay 查询范围
- timeline 概览
- events 列表
- snapshots 列表
- drilldown 结果
- lineage 结果
- 当前选中的 snapshot / event / relation

### 4.3 推荐状态分层

状态应分三层：

#### A. 领域状态

例如：

- 当前 run
- 当前阶段
- 当前攻击轮次
- 当前 replay 查询范围

这些状态必须进 store。

#### B. 共享展示状态

例如：

- 当前选中的阶段
- 当前打开的日志 tab
- 当前图表窗口范围
- 当前 report / code / finding 联动焦点

这些状态若跨组件共享，也应进 store。

#### C. 局部 UI 状态

例如：

- 某个折叠面板是否展开
- 某个 tooltip 是否显示
- 某个局部筛选器是否展开

这类状态应尽量留在组件内，不要污染全局 store。

## 5. 推荐数据流

下一阶段推荐的数据流如下：

1. 用户在 `Run Creator` 填写运行草稿
2. 提交后创建 run
3. `runSessionStore` 建立当前运行上下文
4. 流式事件进入统一事件入口
5. 事件被解析后分发到：
   - `stageConsoleStore`
   - `attackLoopStore`
   - `deliveryStore`
   - `replayStore`
6. 页面只订阅各自需要的 selector

这个设计的关键是：

**页面不直接吞原始流，而是先进入状态总线。**

## 6. 流式事件进入前端的建议方式

### 6.1 统一事件入口

推荐有一个统一的前端事件接入层，负责：

- 读取流式事件
- 标准化字段
- 容错未知事件
- 分发到各个 store

不要让每个页面自己直接消费流式返回。

### 6.2 事件分发原则

#### 进入 runSessionStore 的事件

- run_started
- run_finished
- 当前阶段切换
- 全局失败 / 取消

#### 进入 stageConsoleStore 的事件

- stage_started
- stage_status
- stage_summary
- stage_explanation
- handoff_emitted

#### 进入 attackLoopStore 的事件

- attack_plan
- dispatch_decision
- telemetry_sample
- finding
- gate_decision
- retry_state

#### 进入 deliveryStore 的事件

- artifact_ready
- stage_summary 中与交付相关部分

#### 进入 replayStore 的事件

- run_snapshot
- 最终 run 完成后触发的 replay 拉取结果

## 7. 推荐 selector 设计

为了防止页面组件过深耦合，建议从一开始就定义 selector，而不是让组件直接拿整个 store。

至少应有：

- `selectCurrentRunMeta`
- `selectCurrentStageRail`
- `selectCurrentStageInspector`
- `selectCurrentStageExplanation`
- `selectAttackCurrentRound`
- `selectAttackTelemetrySeries`
- `selectAttackDecisionSummary`
- `selectDeliveryWorkspaceSummary`
- `selectReplayTimelineSummary`
- `selectReplayCurrentDrilldown`

## 8. 推荐页面与 store 对应关系

### Run Creator

主要消费：

- `runDraftStore`
- `appShellStore`

### Live Console

主要消费：

- `runSessionStore`
- `stageConsoleStore`

### Attack Loop

主要消费：

- `runSessionStore`
- `attackLoopStore`

### Delivery Workspace

主要消费：

- `runSessionStore`
- `deliveryStore`

### Replay Center

主要消费：

- `runSessionStore`
- `replayStore`

## 9. 推荐编码顺序

### 第一步：先搭状态骨架

先做：

- store 文件结构
- 基础 state shape
- 基础 selector
- 统一事件接入层

### 第二步：先落最小可运行页面壳

先做：

- `Run Creator`
- `Live Console`
- `Attack Loop`

这一步只要求：

- 页面结构完整
- 状态联通
- 基本事件能驱动 UI 变化

### 第三步：再补 Delivery 与 Replay

原因：

- 这两页更依赖最终产物和回放对象
- 更适合在主流程跑通后再做

## 10. 推荐目录演进方式

建议前端目录逐步形成如下组织思路：

- `features/runtime/`
  - Run Creator
  - Live Console
- `features/attack/`
  - Attack Loop
  - Telemetry
  - Sandbox Monitor
- `features/delivery/`
  - Delivery Workspace
- `features/replay/`
  - Replay Center
- `store/runtime/`
  - runDraftStore
  - runSessionStore
  - stageConsoleStore
- `store/attack/`
  - attackLoopStore
- `store/delivery/`
  - deliveryStore
- `store/replay/`
  - replayStore

这不是要求立刻重命名所有旧目录，而是后续重构时的目标方向。

## 11. 当前边界提醒

这份状态架构文档必须保持以下诚实边界：

- 当前事件模型仍需真正与后端流式输出对齐
- 当前部分页面仍是旧结构，尚未迁移
- 当前已落地 `useRunDraftStore / useRunSessionStore / useStageConsoleStore / useAttackLoopStore` 的第一版桥接实现
- 当前尚未落地完整 `deliveryStore / replayStore`
- 当前 store 仍通过 `App.jsx` 从现有 MAS 状态桥接，不是最终标准化事件总线
- 当前仍是“结构蓝图 + 第一版状态骨架”，不是完整状态架构全部完成

## 12. 结论

下一阶段前端如果要真正进入“可持续开发”状态，关键不是继续补几个面板，而是先固定：

- 页面树
- 状态树
- 事件接入层
- selector 分层

这份文档的作用，就是把这四件事先钉住。
