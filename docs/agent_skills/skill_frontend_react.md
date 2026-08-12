# Skill: Frontend (React + Zustand)

## 2026-04-20 Incremental Update: Runtime Console First Pass

- `RuntimeConsoleView.jsx` is now the first visible Runtime Console entry in expert mode.
- It currently bridges existing app state instead of replacing the old workbench/report pages.
- First-pass sections:
  - `RunCreator`
  - `Live Console`
  - `Attack Loop`
  - `Events / Delivery / Replay` preview
- New store exports in `frontend/src/store/index.js`:
  - `useRunDraftStore`
  - `useRunSessionStore`
  - `useStageConsoleStore`
  - `useAttackLoopStore`
- `App.jsx` currently hydrates those stores from existing local MAS state:
  - requirement / streaming / audit rounds
  - active run / case / loading / latest engine
  - workflow progress / stream log
  - attack rounds / telemetry / findings
- Keep the wording honest:
  - this is the first bridge implementation of the Runtime Console
  - not a full replacement for `WorkbenchView.jsx` or `ReportsView.jsx`
  - not the final ECharts sandbox monitoring implementation
  - not a production-grade container-isolated sandbox claim
- If changing this layer, update together:
  - `frontend/README.md`
  - `frontend/src/features/mas/README.md`
  - `QUICK_START_V3.md`
  - `docs/modules/frontend_runtime_console_architecture.md`
  - `docs/modules/frontend_page_state_architecture.md`
- Verification:
  - `cd frontend && npm run build`

## 2026-04-10 Incremental Update: Final Delivery Board

- If the delivery section still begins like a utility/control area, prefer adding one visible closing board at the top of the delivery panel before refining smaller details.
- A good pattern in this repo is a `Final Delivery Board` inside `DeliveryPanel` that summarizes:
  - final delivery conclusion
  - export readiness
  - replay/history readiness
- Prefer giving it one short presenter script so the page can be used as a real closing slide.
- Keep the wording honest:
  - this is front-end closing-board presentation
  - not a backend delivery-summary endpoint

## 2026-04-10 Incremental Update: Chapter III Closure Leads

- If Chapter III already has a strong bridge panel but the individual evidence/delivery panels still feel disconnected, prefer adding one shared lead-in component across the core panels before adding more content.
- A good pattern in this repo is a `ClosurePanelLead.jsx` component that standardizes:
  - what this block answers
  - current state label
  - where to go next
  - one direct jump action
- Good targets in this repo:
  - credibility summary
  - evidence pack
  - evidence linkage
  - candidate-evidence panel
  - final delivery
- Prefer wiring the action into existing section anchors with `jumpToSection`.
- Keep the wording honest:
  - this is front-end narration continuity
  - not a backend section router
  - not a new report schema

## 2026-04-10 Incremental Update: Evidence-Delivery Bridge

- If the attack/governance chapter is already clear but the evidence/delivery layer still opens as a wall of drilldown panels, prefer adding one full-width bridge panel at the start of Chapter III.
- A good pattern in this repo is a `ReportsEvidenceDeliveryBridgePanel` that summarizes:
  - current evidence focus
  - credibility interpretation readiness
  - delivery closure readiness
- Prefer giving it three direct CTA paths:
  - credibility summary
  - evidence-pack linkage
  - final delivery
- Prefer registering that bridge as a real long-page section so the desktop quick map and anchor navigation can see it.
- Keep the wording honest:
  - this is front-end closure/narration support
  - not a backend chapter API
  - not a new delivery-template contract

## 2026-04-10 Incremental Update: Mainline Outro Rails

- If the four mainline panels already have clear headers but the long report still feels like stacked cards, prefer adding one shared outro/transition strip inside each framed panel before inventing more top-level sections.
- A good pattern in this repo is extending `MainlinePanelFrame` with one consistent three-part guide rail:
  - what this section explains
  - why it matters right now
  - where to go next
- Prefer wiring the “next” action back into existing navigation:
  - `jumpToMainlinePanel(...)` for the next numbered section
  - stable anchor jumps for the final handoff into delivery/evidence sections
- Keep the copy presenter-friendly and Chinese-first in this repo.
- Keep the wording honest:
  - this is front-end narration scaffolding
  - not a backend routing contract
  - not an auto-presenting agent

## 2026-04-09 Incremental Update: Mainline State Hook

- If `ReportsView.jsx` already finished splitting out the visible mainline panels, and the remaining complexity is mostly jump/highlight/spotlight orchestration, prefer extracting that state into a dedicated hook such as `useReportsMainlineState.js`.
- A good mainline-state hook should own:
  - jumped panel highlight state
  - four mainline active flags
  - spotlight title/detail derivation
  - default `stageRef / runId / targetServiceRef` writeback when the user jumps from the rail or sticky bar
  - smooth scroll positioning
- After this split, keep `ReportsView.jsx` responsible for:
  - page composition
  - shared prop wiring
  - connecting `useReportsEvidenceState.js`
  - connecting `useReportsMainlineState.js`
- Prefer this layering for the report page:
  - `ReportsView.jsx`: composition shell
  - `useReportsEvidenceState.js`: evidence linkage and replay jump logic
  - `useReportsMainlineState.js`: mainline orchestration and reading-path guidance
- Do not introduce a new backend contract just to justify the hook split; this remains front-end orchestration only.

## 2026-04-09 Incremental Update: Deferred Report Panels

- If the report page top half already became the answer-defense mainline, and the lower half contains several heavy drilldown panels, prefer adding viewport-based deferred mounting before doing more micro-optimizations.
- A good pattern in this repo is:
  - `useDeferredMount.js`: `IntersectionObserver`-based mount timing
  - `DeferredPanelMount.jsx`: lightweight placeholder wrapper with honest wording
- Prefer keeping these areas mounted immediately:
  - top legend
  - mainline overview
  - mainline rail
  - sticky position bar
  - summary layer
  - the four numbered mainline panels
- Prefer deferring these lower blocks when they are below the fold:
  - handoff/artifact deep dive
  - attack lessons
  - credibility summary
  - evidence pack
  - evidence linkage
  - candidate evidence
  - delivery/history
- Keep the wording honest:
  - this is front-end deferred mounting
  - not a new backend lazy-loading contract
  - not a data-loss or pending-fetch state by default
- If the browser does not support `IntersectionObserver`, fall back to immediate mount.

## 2026-04-09 Incremental Update: Section Navigation

- If the report page becomes long enough that a presenter has to hunt for the next block, prefer adding one explicit section-navigation layer before adding more visual density.
- A good pattern in this repo is `ReportsSectionNavigator.jsx`, placed near the top of `ReportsView.jsx` after the mainline-position layer.
- Recommended reading-path groups:
  - overview path
  - attack-loop path
  - evidence-and-delivery path
- Prefer mixing two jump styles:
  - mainline sections reuse the existing mainline jump logic
  - non-mainline sections use stable page anchors
- If some lower sections are deferred-mounted, put the anchor on the wrapper so users can still jump to the placeholder first and let the full panel mount near viewport.
- Keep the wording honest:
  - this is front-end narration/navigation support
  - not a new backend navigation API
  - not an auto-presenting agent
- Prefer labeling the navigator in Chinese for this repo, for example:
  - `章节导航与讲解路径`
  - `先讲全貌`
  - `再讲攻击闭环`
  - `最后讲证据与交付`

## 2026-04-09 Incremental Update: Desktop Quick Map

- If the report page becomes a true long-form defense page, prefer adding a desktop-only floating quick map before inventing more tabs.
- A good pattern in this repo is:
  - `useSectionSpy.js`: infer the current active section from scroll position
  - `ReportsQuickMap.jsx`: fixed desktop floating navigator on the right
- Recommended section registration:
  - overview summary
  - flow
  - replay
  - attack loop
  - execution plane
  - handoff deep dive
  - credibility
  - evidence pack
  - delivery/history
- Prefer mixing behaviors:
  - mainline sections reuse `jumpToMainlinePanel`
  - non-mainline sections reuse stable anchor jumps
- Keep the quick map desktop-only when it would otherwise squeeze the main content.
- Keep the wording honest:
  - this is front-end reading-position guidance
  - not a backend bookmark/index API
  - not an autoplay narration system

## 2026-04-09 Incremental Update: Report Hero Banner

- If the report page already contains many panels and navigators, prefer adding one strong hero-style cover section before stacking more utility controls.
- A good pattern in this repo is `ReportsHeroBanner`, placed at the top of `ReportsView.jsx`.
- The hero should answer, at a glance:
  - what report this is
  - which case is active
  - what the current delivery verdict is
  - whether the page is in global mode or focused mode
  - what the current attack-loop / delivery readiness state is
  - where the presenter can jump next
- Prefer deriving hero content from existing report props instead of inventing a new backend summary endpoint.
- Good jump targets for hero CTA buttons in this repo:
  - flow transparency
  - attack loop
  - final delivery
- Keep the wording honest:
  - this is a front-end answer-defense cover
  - not a separate report type
  - not a backend-generated executive summary API

## 2026-04-10 Incremental Update: Shared Storyline Language

- If the hero cover and the top overview start feeling like two unrelated designs, prefer unifying them with one shared storyline language before adding more sections.
- A good pattern in this repo is a shared five-part storyline:
  - case
  - decision
  - focus
  - attack
  - delivery
- Prefer using that same sequence in:
  - `ReportsHeroBanner`
  - `ReportsMainlineOverviewPanel`
- The hero can present it as a compact `答辩故事线`, while the overview can present it as a fuller `五段答辩路线`.
- This helps the top of the report read like:
  - cover
  - expanded storyline
  rather than two unrelated summary blocks.
- Keep the wording honest:
  - this is front-end narrative unification
  - not a new backend storyline schema
  - not a new report template family

## 2026-04-10 Incremental Update: Mainline Exhibition Frames

- If the hero/overview become visually strong but the four mainline panels still look like generic workbench cards, prefer upgrading the mainline frames and rail into one shared exhibition-like language.
- Good upgrades in this repo:
  - stronger chapter header
  - numbered badge
  - section status copy
  - short progress strip
  - accent-themed rail cards matching each mainline panel
- Prefer keeping the accent mapping stable:
  - flow -> sky
  - replay -> cyan
  - attack -> rose
  - dispatch -> amber
- This helps the top of the report read like:
  - hero cover
  - expanded storyline
  - guided rail
  - chapter frames
  rather than jumping back to generic panels.
- Keep the wording honest:
  - this is front-end exhibition styling
  - not a backend progress API
  - not a new workflow-state schema

## 2026-04-10 Incremental Update: Section Dividers

- If the report page now reads like a long defense board, prefer adding explicit section dividers between major layers before adding even more cards.
- A good pattern in this repo is `ReportsSectionDivider.jsx`.
- Recommended divider layers:
  - mainline transparency layer
  - attack-and-governance layer
  - evidence-and-delivery layer
- Each divider can include:
  - chapter label
  - short narration summary
  - one concise presenter hint
  - status chips tied to current front-end focus
- This helps presenters transition naturally from one major layer to the next instead of feeling like they are scrolling through unrelated modules.
- Keep the wording honest:
  - this is front-end narration scaffolding
  - not a new backend chapter model
  - not a new workflow stage family

## 2026-04-09 Incremental Update: Mainline Panels Split

- If `ReportsView.jsx` starts becoming a massive presentation file, prefer extracting the visible “答辩主图” sections into their own module before doing deeper UI work.
- Recommended split after the first mainline redesign:
  - `ReportsMainlineChrome.jsx`
    - `MainlinePanelFrame`
    - `MainlinePanelRail`
    - `MainlinePositionBar`
  - `ReportsMainlinePanels.jsx`
    - `ReportsMainlineOverviewPanel`
    - `WorkflowAttackBridgePanel`
- If `AttackLoopPanel` becomes both visually important and technically dense, extract it into `AttackLoopPanel.jsx` rather than leaving it inside `ReportsView.jsx`.
- Keep the report page shell responsible for orchestration, and let the attack loop file own:
  - replay-linked attack summary
  - sandbox target service presentation
  - round cards
  - traffic fluctuation chart
  - vulnerability / patch summary
  - reflection-card rendering
- If the top legend becomes a stable part of the page language, extract it into `ReplayFocusLegendPanel.jsx` so the report shell no longer owns both orchestration and “how to read this page” guidance.
- If the report page top half contains several stable summary panels, extract them into one module such as `ReportsSummaryPanels.jsx` instead of keeping multiple medium-sized business panels inside `ReportsView.jsx`.
- A good summary-layer split is:
  - `ProjectMemoryPanel`
  - `RequirementPanel`
  - `AuditDecisionPanel`
- If the lower half of the report page contains stable “result interpretation” blocks, extract them into a dedicated module such as `ReportsOutcomePanels.jsx`.
- A good outcome-layer split is:
  - `CredibilityPanel`
  - `DeliveryPanel`
- If report-page evidence linkage starts owning too much local state, extract that state into a dedicated hook such as `useReportsEvidenceState.js`.
- A good evidence-state hook should own:
  - selected evidence synchronization
  - replay focus writeback
  - evidence-to-round/recommendation/delivery linkage
  - evidence-to-proposal linkage
  - proposal-to-delivery fragment mapping
  - delivery-fragment reverse proposal mapping
  - replay jump handlers for event / snapshot / handoff / run / stage / artifact
- Keep `ReportsView.jsx` focused on:
  - shared state wiring
  - focus orchestration
  - panel ordering
  - prop handoff
- When splitting display-only mainline components, do not introduce new backend contracts just to “justify” the file split.
- If a bridge or overview panel needs target service text, prefer going through the same helper path instead of reading ad hoc `service_name` fields inline.

## 2026-04-08 Incremental Update: Attack Loop Focus Lens

- `ReportsView.jsx`
  - If the page still feels too “panel-by-panel”, prefer adding one full-width top summary panel before the denser sections.
  - Recommended title direction: `整页主线总览`
  - Recommended chain: `项目 -> 审计判定 -> 当前阶段 -> 攻击闭环 -> 代码交付`
  - This layer should be a reading-coordinate panel for humans, derived locally from existing props.
  - If the top summary is still not enough, add a second full-width rail directly below it.
  - Recommended title direction: `主线联动轨道`
  - Recommended rail: `流程透明化 -> Replay 深钻 -> 攻击闭环 -> 执行平面`
  - Prefer also wrapping those four panels with numbered outer frames so the active part of the mainline is visible even before the user reads the panel body.
  - If the rail is already visible, prefer making each rail node clickable and scroll it to the corresponding framed panel.
  - When helpful, let the rail click also write a reasonable default focus such as `stageRef`, `runId`, or `targetServiceRef`; keep this as a front-end guidance behavior, not a new backend contract.
  - For long report pages, consider adding a sticky mini-bar below the rail that keeps showing the current mainline position and re-exposes the same jump actions.
  - `AttackLoopPanel` can now add a prominent `共享 Replay 焦点透镜` summary block near the top when the page already contains many replay-linked panels.
  - Prefer this pattern when the user says “启动后看不出变化” or when replay linkage exists but is too隐性:
    - one large visual summary block
    - one clear state line (`当前正在跟随 Replay 焦点` vs `当前是攻击闭环总览`)
    - one or two quick scope counters (`命中轮次` / `主链轮次`)
    - one short observation-path strip (`观察模式` / `当前轮次` / `代码交付`)
    - one service-link explanation card
    - one stage-link explanation card
  - If the page already contains `FlowTransparencyPanel`, `ReplayTimelinePanel`, and `AttackLoopPanel`, prefer adding one full-width bridge panel between replay and attack sections:
    - title direction: `联动主线与当前观察路径`
    - bridge chain: `流程阶段 -> 目标服务 -> 攻击轮次 -> 代码交付`
    - data should be derived locally from existing props; do not invent a new backend API just for this presentation layer
- Round cards inside `AttackLoopPanel`
  - if a round hits `replayScope.targetServiceRef`, prefer stronger border/shadow plus a short explanation line
  - if a round only hits the attack-chain `stageRef`, still show a secondary highlighted explanation block so users understand why the round matters
- Keep the wording honest:
  - this is shared replay focus visualization
  - not automatic runtime recovery execution
  - not a new backend replay contract

## When To Use

- 你要改 UI 交互、状态管理、流式展示、错误边界
- 后端接口字段变化导致前端渲染报错

## Key Files

- 入口：
  - `frontend/src/main.jsx`
  - `frontend/src/App.jsx`
- API client：
  - `frontend/src/api/client.js`
- Zustand store：
  - `frontend/src/store/index.js`
- 组件：
  - `frontend/src/components/`
  - `frontend/src/features/mas/`
    - `MissionView.jsx`：企业密码交付总览
    - `RuntimeConsoleView.jsx`：专家模式运行控制台第一版，桥接任务发起、主流程观测、攻击闭环与交付 / replay 预览
    - `WorkbenchView.jsx`：业务需求输入、行业专家选择、审计博弈、工程交付；当前是“上方主工作区、下方结果区”的企业控制台
    - `clarificationHelpers.js`：关键约束补充栏、阻断项检查、补充内容拼接与发起前检查
    - `ReportsView.jsx`：合规与风险摘要、可信度概览、交付决策看板
    - `FlowTransparencyPanel.jsx`：流程透明化、独立上下文窗口、结构化 handoff 与攻击规划证据展示
    - `ReplayTimelinePanel.jsx`：单 case、本地 replay 概览、handoff 关系、目标服务轨迹与 retry 恢复点 drilldown 展示
    - `SandboxDispatcherPanel.jsx`：执行平面、dispatcher 审批与调度治理展示
    - `RoundComparisonPanel.jsx`：baseline / regression 轮次对比展示
    - `HandoffArtifactPanel.jsx`：handoff / artifact / evidence 深钻展示
    - `AttackLessonsPanel.jsx`：attack lesson 来源、年份、关注点与模板适配展示
    - `EvidencePackPanel.jsx`：规范依据与证据包卡片区
    - `EvidenceLinkPanel.jsx`：证据点击后的联动解读区
    - `CandidateEvidencePanel.jsx`：证据支撑候选方案区
    - `ComponentsView.jsx`：密码组件库浏览器
    - `OpsView.jsx`：本地数据、知识资产与设置
    - `SettingsView.jsx`：连接与模型设置、密钥输入、后端 `.env` 同步与预览
    - `StudioHeaderView.jsx`：工作区页头、运行状态总览、主导航切换
    - `StudioShell.jsx`：工作台外层壳、页面级布局容器
    - `WorkspaceStatusBanner.jsx`：成功 / 错误 / 信息提示条
    - `useMasDerivedState.js`：MAS 派生数据聚合、比较表/交付包/工作流进度等计算
    - `evidenceHelpers.js`：证据关键词抽取、联动匹配与高亮辅助逻辑
    - `masHelpers.js`：`actorMatches`、`displayOrDash`、阶段归一化等共享业务辅助逻辑
    - `useMasActions.js`：连接校验、配置同步、组件/行业专家拉取、行业专家推荐与 MAS 执行动作
    - `useMasLocalOps.js`：本地缓存、历史载入、模板应用、需求骨架拼接与剪贴板复制
    - `useMasExport.js`：JSON / Markdown / LaTeX / HTML 导出与企业交付报告生成
    - `exportHelpers.js`：导出文件名、时间戳、下载、Markdown/LaTeX 文档组装

## Invariants

- `frontend/src/api/client.js` 的路径与参数必须与 FastAPI 对齐
- 前端依赖 `MASResponse` 字段：
  - 例如 `result.analyst.structured_spec`、`result.architect.candidates`、`result.delivery`
- 当前前端默认把 LangGraph 作为首选执行引擎；如果调整该策略，需要同步检查：
  - `frontend/src/api/client.js` 默认设置
  - `frontend/src/features/mas/SettingsView.jsx` 设置文案
  - `frontend/src/features/mas/useMasActions.js` 对通用方案流程 / 行业专家流程的执行参数透传
  - `frontend/src/features/mas/WorkbenchView.jsx` 与 `frontend/src/features/mas/ReportsView.jsx` 的引擎展示
- 面向用户的工作台文案可以改成业务表达，但 `strict_clarification` 这类稳定请求字段不要随 UI 文案一起改名

## Common Changes

- 新增/修改 API 字段：
  - 同步更新前端读取路径（通常在 `App.jsx`）
  - 如是破坏性变更，必须同步更新 `frontend/README.md` 和 `QUICK_START_V3.md`
- 新增 replay scope 筛选条件：
  - 先检查 `App.jsx` 是否把 camelCase 状态正确映射到后端 snake_case query 参数
  - `retryResumeCheckpointRef / retryResumeInputRef` 这类字段，语义是“回看查询范围”，不是自动恢复执行命令
  - 同步检查 `frontend/src/features/mas/README.md` 与 `docs/TECHNICAL_DOCUMENTATION.md` 的口径
  - 若某些筛选仅用于前端二次过滤（例如阶段 / 目标服务），要在界面上明确标出，不要伪装成后端已应用 scope
- 如果开始把 replay 数据拆成独立拉取，优先保持 `overview / drilldown / events / snapshots / lineage` 各自职责清晰，不要重新耦回单一超大请求
- 若聚合接口失败但基础列表仍可用，优先让界面降级可用，并把失败面明确标给用户
- 如果做联调导向的 replay 面板，优先提供“最近刷新时间”和“单源重拉”能力，避免每次都整页刷新
- 若要帮助前后端对 scope 契约做联调，优先把“请求参数快照”和“返回 scope”并排展示出来
- 若要增强答辩/联调表现，可额外保留每个数据源最近几次成功/失败健康历史
- 面向外行演示时，可把健康历史进一步压成“链路健康时间带”，让状态变化更一眼可读
- 若已经有流程透明化面板，优先把 replay 健康状态同步接到流程节点上，形成“流程 + 观测”联动
- 若还有执行/dispatcher 面板，继续把 `replayScope.stageRef` 接过去，形成“流程阶段 -> 执行节点”联动
- 若还有攻击闭环或轮次对比面板，也继续把同一个 `stageRef` 接过去，形成整页级联动焦点
- 若页面已经形成多面板联动，优先把 `stageRef / projectionRef / handoffRef / targetServiceRef` 收口到统一视觉 helper，避免同类焦点在不同面板里长得不一样
  - 扩展统一视觉 helper 时，优先覆盖与 replay 联动最密集的面板：`FlowTransparencyPanel / ReplayTimelinePanel / SandboxDispatcherPanel / RoundComparisonPanel / HandoffArtifactPanel / EvidenceLinkPanel / CandidateEvidencePanel / AttackLessonsPanel`
  - 如果整页已经存在较多联动面板，优先在 `ReportsView.jsx` 靠前位置补一个“联动图例与当前焦点”总览条，先解释颜色语义，再解释局部 drilldown
  - 图例条优先复用 `masHelpers.js` 中的 `REPLAY_FOCUS_ORDER / getReplayFocusMeta / buildReplayFocusLabel / getReplayFocusTone`，不要在页面里再手写一套颜色说明
  - 如果共享 replay focus helper 已经扩到更多 query-backed ref，也要同步让 `ReportsView.jsx` 的图例解释这些新焦点，不要让图例停留在旧的四类主焦点
  - 具体到 JSX 落地时，优先复用 `ReplayFocusPill.jsx`，不要在每个面板里重复写一层 `TagPill + button + ring` 逻辑
  - 优先把 `EvidenceLinkPanel / CandidateEvidencePanel / HandoffArtifactPanel` 这类证据与深钻区也切到同一套共享组件，避免焦点按钮样式再次分叉
  - `ReplayTimelinePanel` 里的主入口拓扑卡与详情区标签也应逐步切到这套共享组件，不要让核心回看面板成为最后一个旧样式孤岛
  - `ReplayTimelinePanel` 继续收口时，优先把会改写共享 `replayScope` 的入口切到 `ReplayFocusButton`
  - `FilterPill` 尽量只留给局部动作或局部筛选，例如单源刷新、本地 lineage 对焦、artifact/evidence lookup、resume 定位点
  - UI 文案上要明确区分：
    - 后端已应用的 replay scope
    - 整页共享的 replay 联动焦点
    - 仅限面板内的二次过滤
  - 如果某个 replay 焦点还存在“混合语义”，也要继续拆开写：
    - 哪些字段会回写后端查询
    - 哪些字段主要承担前端联动或局部观察
  - 如果一个大区块里同时存在两类入口，优先直接做视觉分栏，而不是只靠补一行解释文案
    - 例如把“本地导航镜头”和“后端深钻入口”拆成左右栏
  - 如果 replay 深钻里同时存在 `artifact / evidence` 两类 query-backed ref，优先让它们都拥有独立入口，不要让其中一类长期只挂在另一类卡片的小标签里
  - 如果 `artifact / evidence / retry checkpoint / resume input` 这些 ref 已经成为稳定的 query-backed 焦点，优先补到共享 replay focus helper 中，而不是继续在单文件里手写标签标题
  - 如果某些按钮只用于本地动作或局部过滤，组件名也应显式区分，例如用 `LocalFilterPill`，不要继续和共享 replay focus 按钮混叫
  - 当前项目里尤其要保持诚实口径：
    - `阶段 / 目标服务` 可以是整页共享联动焦点
    - 但不等于后端已经按它们做了 drilldown 查询
- 想把 LangGraph 作为主线执行引擎：
  - 不只改默认值，还要确认行业专家执行链是否也透传了同一引擎偏好
  - UI 至少应在设置页、工作台摘要、报告决策区显示当前引擎或引擎模式，避免“界面默认 LangGraph，实际结果是 Legacy”
- 想把前端“组件业务化”而不是继续堆在单文件：
  - 优先按业务域拆到 `frontend/src/features/mas/`，例如 Mission / Workbench / Reports
  - 通用承载壳（如 `Panel`、`MetricCard`）放到 `frontend/src/components/`，业务叙事和页面块放到 feature 目录
  - 报告区优先呈现“交付结论 / 合规与风险摘要 / 可信度概览 / 上线建议”，技术 JSON 放在其后
  - 对企业评审高频场景，优先做“上线判定 / 主要阻断项 / 通关路径”这类业务卡，不要让用户先看原始 JSON
- 想增强 evidence pack 的业务化表达：
  - 优先看 `EvidencePackPanel.jsx`，不要把证据卡结构重新塞回 `ReportsView.jsx`
  - 如果要做“点击证据 -> 联动审计/整改/交付”，优先看 `EvidenceLinkPanel.jsx` 与 `evidenceHelpers.js`
  - 如果要做“点击证据 -> 联动候选方案 / 对比表”，优先看 `CandidateEvidencePanel.jsx` 与 `evidenceHelpers.js`
  - 如果要把报告页里已经形成的 `proposal -> delivery fragment` 语言带回工作台，优先补 `WorkbenchView.jsx` 的 `AuditArena`，不要急着加新的全局导航 store
  - 如果要调整自动滚动和聚焦动画，优先看 `ReportsView.jsx` 的 ref/target 逻辑与 `frontend/src/index.css` 里的 `cg-scroll-target`、`cg-focus-block`
  - 如果要把报告页的联动焦点继续带到别的 tab，优先看 `App.jsx` 里的共享状态 `selectedProposalId`
  - `useMasDerivedState.js` 中的 `evidencePack` 与 `deliveryPackage.evidence_pack` 需要保持一致，避免页面有证据、导出没有
- 想改组件库页的视觉：
  - 优先改 `frontend/src/features/mas/ComponentsView.jsx` 的卡片结构
  - 动效、弹性反馈和全局样式优先收口到 `frontend/src/index.css` 的 `cg-bouncy-*` 类
  - 不要退回成“按分类堆一排小标签”的开发态列表
- 想改澄清门禁或补充栏：
  - 先改 `frontend/src/features/mas/clarificationHelpers.js`，保持补充字段拼接、阻断项检查和页面提示共用一套规则
  - 再改 `frontend/src/features/mas/useMasActions.js`，确认通用方案流程与行业专家流程都会透传 `strict_clarification`
  - 最后改 `frontend/src/features/mas/WorkbenchView.jsx`，避免只改文案不改真实行为
- 想调整“生成按钮太靠下”的问题：
  - 优先在 `WorkbenchView.jsx` 的顶部发起区处理，保持按钮和关键参数在一个粘性业务卡中
  - 不要把按钮重新散回需求区底部，否则长表单场景会再次退化
- 涉及用户可见显示词：
  - 优先复用 `frontend/src/components/DisplayValue.jsx`
  - 状态/可信等级/支持等级/完成态优先复用 `frontend/src/components/SemanticPill.jsx`
  - 纯展示性的数量、版本、分数、固定标签优先使用 `TagPill`，不要混用 `SemanticPill`
  - `MetricCard` 优先走 `valueLabel` / `valueBoolean`
  - 像 `case_id`、`request_id`、`run_id` 这类稳定标识，前端展示优先换成业务词，例如“项目编号 / 导入编号 / 任务编号”，不要把程序字段名直接暴露给用户
  - 不要在页面里继续散落 `label || raw`、`String(bool)`、`high ? ok : warn` 这类回退或 tone 判断逻辑
  - 如果前端仍保留本地 Markdown / LaTeX 导出，也要同步保持中文优先标题与字段名，不要只改页面展示
- 想继续把知识导入做成“可治理资产”而不是一次性上传：
  - 优先看 `OpsView.jsx`
  - 再看 `useMasActions.js` 里的 `fetchKnowledgeAssets()/uploadKnowledgeFiles()/removeKnowledgeArtifacts()/removeKnowledgeQdrantArtifacts()`
  - 同步检查 `frontend/src/api/client.js` 的 `GET /api/v1/knowledge/ingestions`、`POST /api/v1/knowledge/ingest/{request_id}/qdrant` 与 `DELETE /api/v1/knowledge/ingest/{request_id}/qdrant`
  - 页面里应明确区分“本地文件是否还在”和“Qdrant 是否仍需单独治理”
  - 如果页面新增治理时间或状态字段，优先使用后端返回的持久化字段；当前 Qdrant 治理时间使用 `qdrant_deleted_at`

## Verification

- 运行前端：`cd frontend && npm run dev`
- 构建检查：`cd frontend && npm run build`

## 2026-04-06 Incremental Update: Replay Retry Recovery View

- `ReplayTimelinePanel.jsx`
  - now includes a dedicated `Retry 恢复点` section
  - prefers `replayDrilldown.summary.retry_*`
  - falls back to `timelineOverview.latest_snapshot.metadata.retry_*`
  - `resume checkpoint / resume input` tags can drive drilldown scope updates
- Recommended UI treatment:
  - `retry_projection_refs / retry_handoff_refs` 用可点击筛选标签
  - `retry_compression_policies / retry_compression_stages` 用说明性标签
  - `retry_resume_checkpoint_refs / retry_resume_input_refs` 用恢复定位标签
- Keep the wording honest:
  - say `恢复点可回看`
  - do not say `已支持自动恢复执行`
## 增量更新：当前项目卡片（2026-03-24）

- `App.jsx`
  - 维护 `currentCaseId` 与 `caseCatalog`
- `useMasActions.js`
  - 负责 `fetchCases()`、`selectCase()`、执行时透传 `case_id`
- `WorkbenchView.jsx`
  - 顶部新增“当前项目”业务卡片
  - 在当前页完成继续项目、新建项目、切换最近项目、手动输入 `case_id`
- `ReportsView.jsx`
  - 新增“项目连续性”面板

这条链路的设计目标是把 case 做成工作台里的企业项目对象，而不是额外造一个聊天式页面。

## 2026-03-26 Incremental Update

- `useMasDerivedState.js`
  - current derived fields include `attackLoop` and `codeArtifacts`
- `ReportsView.jsx`
  - current report page includes an `攻击闭环与沙盒态势` panel
  - the panel consumes `delivery.attack_loop.attack_results[*].metrics.traffic_series`
- If backend changes `service_port`, `service_base_url`, `service_health_url`, `probe_count`, or `traffic_series`, update the report panel and this skill doc together.

## 2026-03-26 Round View Update

- `ReportsView.jsx` now also consumes `attack_loop.rounds` and `attack_loop.current_round`.
- Keep the UI wording honest:
  - `baseline` means executed
  - `regression` means executed patched regression probing on the local shell

## 2026-03-26 Regression Round Update

- Backend semantics now promote round 2 to an executed `regression` round.
- Frontend expectations should therefore be:
  - `baseline` = executed baseline round
  - `regression` = executed patched-version regression round
- The wording still needs to stay honest:
  - this is a patched-shell redeploy plus formal regression probing
  - not a container-isolated production patch validation flow

## 2026-03-26 Flow Transparency Update

- If frontend starts consuming `delivery.context_projections` and `delivery.memory_handoffs`, prefer a layout with:
  - agent flow timeline
  - independent context window panel
  - handoff detail drawer
  - sandbox status panel
- Recommended user-facing Chinese labels:
  - `独立上下文窗口`
  - `结构化交接包`
  - `工件引用`
  - `证据引用`
  - `沙盒态势`
  - `补丁回归结果`
- Keep the wording honest:
  - say this is a local restricted-process sandbox demo loop
  - do not say this is a production-grade isolated attack platform

## 2026-03-28 Frontend Adaptation Update

- `ReportsView.jsx` now directly consumes:
  - `delivery.workflow_trace`
  - `delivery.context_projections`
  - `delivery.memory_handoffs`
  - `delivery.sandbox_dispatcher`
- `App.jsx` now also fetches:
  - `GET /api/v1/cases/{case_id}/timeline`
  - `GET /api/v1/cases/{case_id}/timeline/drilldown`
- `ReportsView.jsx` now also consumes:
  - `timelineOverview`
  - `replayDrilldown`
- `useMasDerivedState.js` now derives:
  - `workflowTrace`
  - `workflowProgress`
  - `contextProjections`
  - `memoryHandoffs`
  - `sandboxDispatcher`
- `FlowTransparencyPanel.jsx` currently shows:
  - workflow node completion
  - six role-aware context windows
  - structured handoff summaries
  - `attack_planner_evidence` hits and source metadata
- `RoundComparisonPanel.jsx` currently shows:
  - baseline vs regression findings
  - verdict drift
  - removed / retained / added findings
- `HandoffArtifactPanel.jsx` currently shows:
  - handoff chain selection
  - handoff cards
  - artifact refs
  - evidence refs
- `AttackLessonsPanel.jsx` currently shows:
  - paper vs benchmark attack lessons
  - `lesson_kind`
  - `source_title`
  - `source_year`
  - `attack_focus`
  - `regression_focus`
  - template applicability
  - handoff / patch / reflection / next_action impact chain
  - shared replay focus entry points for `attack_executor / projectionRef / handoffRef`
  - direct evidence-focus handoff into `selectedEvidenceChunkId / replayScope.evidenceLookupRef`
- `SandboxDispatcherPanel.jsx` currently shows:
  - backend / policy summary
  - baseline / regression deployment approval
  - baseline / regression attack approval
  - `failure_items` and `audit_trail` summaries
- `ReplayTimelinePanel.jsx` currently shows:
  - replay 概览计数
  - `handoff_relationships`
  - `service_trajectories`
  - local `run / stage / artifact` hierarchy navigation
  - drilldown 命中的 `events`
  - drilldown 命中的 `snapshots`
  - 当前选中 event / snapshot 的 metadata、typed contract 与 refs 详情
  - 最近 snapshot / version lineage 摘要
- replay 请求口径当前固定为：
  - 优先按当前 `run_id`
  - 否则回退 `latest_run_id`
  - 点击 `projection_ref / handoff_ref` 时重拉 `timeline/drilldown`
  - 点击 `target_service_ref` 时补拉 `timeline/lineage`
  - 仅展示单 case、本地 replay 深钻，不要写成跨 case replay center
- 当前跨面板 replay 联动建议固定为：
  - 复用 `App.jsx` 中的共享 `replayScope`，不要在 `FlowTransparencyPanel.jsx`、`ReplayTimelinePanel.jsx`、`HandoffArtifactPanel.jsx` 各自维护第二套焦点状态
  - `FlowTransparencyPanel.jsx` 应作为 replay 的反向焦点源，支持点击 projection / handoff 卡片直接驱动 drilldown
  - `HandoffArtifactPanel.jsx` 应优先跟随 `replayScope.handoffRef` 自动选中对应 handoff，并允许继续反向切到 projection drilldown
  - `RoundComparisonPanel.jsx` 应消费 `replayScope.targetServiceRef`，并高亮命中的 baseline / regression 轮次列
- `SandboxDispatcherPanel.jsx` 应消费 `replayScope.targetServiceRef`，并高亮命中的 deployment / attack 审批卡片
- 报告页内部 `AttackLoopPanel` 应消费 `replayScope.targetServiceRef`，说明当前 replay 焦点是否与本轮 target service 对齐
- 如需从这些面板反向切换目标服务焦点，优先复用同一个 `setReplayScope`，不要再加第三套本地 target-service 选中态
- `AttackLoopPanel` 里的 `Replay 目标服务焦点 / Replay 阶段焦点 / 轮次卡片标签` 也优先复用 `ReplayFocusPill / ReplayFocusButton`，不要回退到局部 `TagPill + button` 组合
- projection 稳定 ref 的推导顺序优先使用后端显式 `window_ref / projection_ref`，缺失时再回退 `agent_id + round_id`
- If backend changes these fields, update the panel code and this skill doc together:
  - `delivery.workflow_trace`
  - `delivery.context_projections`
  - `delivery.memory_handoffs`
  - `delivery.sandbox_dispatcher.*`
  - `attack_planner_evidence`
  - `timeline_summary`
  - `handoff_relationships`
  - `service_trajectories`
  - `ReplayVersionLineagePayload`
  - `window_ref / projection_ref / handoff_id`

## 2026-03-31 Replay Timeline Topic View Update

- `ReplayTimelinePanel.jsx`
  - `service_trajectories` should no longer be treated as a flat list only; the panel now promotes one `selectedServiceTrajectory` into a topic view.
  - Selection rule:
    - prefer `replayScope.targetServiceRef`
    - fall back to the first trajectory when no explicit target-service focus exists
  - The topic summary should expose:
    - `latest_status`
    - `latest_summary`
    - `event_kind_counts`
    - `stages`
    - `baseline_versions`
    - `patched_versions`
    - related lineage slices from `replayLineage.items`
  - The trajectory list cards should visually mark the current topic and include quick pills for total event count and stage count, so users can decide whether to continue drilling down without re-reading long summaries.
- Frontend verification:
  - `cd frontend && npm run build`

## 2026-03-31 Replay Path Jump Update

- `App.jsx`
  - Shared `replayScope` should now also carry:
    - `runId`
    - `stageRef`
  - These are front-end navigation focus fields only; do not invent new backend replay request params for them.
- `ReportsView.jsx`
  - Reverse focus helpers from `event / snapshot / handoff` should populate `runId / stageRef` when the source record has enough information.
  - Evidence-path helpers should also support:
    - `focusReplayFromRun`
    - `focusReplayFromStage`
    - `focusReplayFromArtifact`
- `EvidenceLinkPanel.jsx`
  - In `Replay 命中路径`, the `run / stage / artifact` tags should be clickable jump controls, not passive pills.
  - Keep them on the same shared `replayScope`; do not introduce a second replay-navigation store.
- `ReplayTimelinePanel.jsx`
  - Local hierarchy navigation should consume shared `runId / stageRef / artifactLookupRef / evidenceLookupRef` so cross-panel jumps and local narrowing stay aligned.
- Frontend verification:
  - `cd frontend && npm run build`

## 2026-03-31 Evidence To Delivery Fragment Update

- `evidenceHelpers.js`
  - Prefer building a small delivery-fragment catalog from:
    - `delivery.next_action`
    - `delivery.scenario_fit`
    - `delivery.production_guide[*]`
    - `result.compliance_report.summary_text`
    - `result.vulnerability_report.summary_text`
    - `finalScheme.design_rationale`
- `EvidenceLinkPanel.jsx`
  - `linkedDeliveryFragments` should be clickable jump cards, not passive text blocks.
- `ReportsView.jsx`
  - Keep delivery-fragment focus local to the report page with something like `selectedDeliveryFragmentId`.
  - Render the delivery-fragment catalog in the delivery/report area (`DeliveryPanel` / final delivery section), not inside `AttackLoopPanel`, so evidence-to-delivery jumps land in the real delivery context.
  - If the app already has a shared `selectedProposalId`, prefer deriving a lightweight local `proposal -> delivery fragment` linkage from `architectCandidates + deliveryFragments` before inventing new backend schema.
  - If you need reverse navigation, prefer deriving a local `delivery -> proposal` linkage from the selected fragment instead of adding another global store or backend contract.
  - If a fragment is selected, the page should scroll to the matching `delivery-fragment-*` target and visually mark it.
  - If proposal focus already exists, prefer adding a local `Proposal Replay Path` block in `CandidateEvidencePanel.jsx` and reuse the existing replay focus callbacks instead of inventing a separate proposal-replay state machine.
  - If you want the replay panel itself to respond to proposal focus, prefer passing the same `proposalReplayContext` down to `ReplayTimelinePanel.jsx` and render a local `Proposal Lens` there instead of creating another cross-panel store.
  - For richer defense-demo visuals, prefer deriving `proposalHandoffLanes` from existing `handoffTopology` plus `proposalReplayContext.handoffRefs` before inventing a separate graph backend.
- Frontend verification:
  - `cd frontend && npm run build`

## 2026-03-31 Replay Timeline Lineage Focus Update

- `ReplayTimelinePanel.jsx`
  - The topic view now keeps a local `selectedLineageEntry` for the currently focused target-service lineage.
  - `baseline_versions`, `patched_versions`, and `patch_ids` in the topic card should be treated as clickable lineage-focus controls, not passive labels.
  - The related lineage list should support click-to-focus and visually mark the active lineage entry.
- Frontend verification:
  - `cd frontend && npm run build`

## 2026-04-01 Proposal Handoff Swimlane Update

- `ReplayTimelinePanel.jsx`
  - `Proposal Handoff Lens` should now be treated as a lightweight relationship view, not only a metric summary.
  - Each proposal-focused lane card should expose:
    - `sourceAgent -> dominant contract -> targetAgent`
    - a short stage-pair flow strip
    - `relation_ref / target_service_ref / dominant contract` tags for drilldown narration
  - Keep this view derived from existing `handoffTopology + proposalReplayContext.handoffRefs`; do not add a new graph endpoint just for the demo lane view.
  - The lane click behavior should still reuse the existing `replayScope.handoffRef` focus path so the swimlane card and the raw relation drilldown stay aligned.
- Frontend verification:
  - `cd frontend && npm run build`

## 2026-03-31 Replay Timeline Handoff Topology Update

- `ReplayTimelinePanel.jsx`
  - `handoff_relationships` should now be read in two layers:
    - aggregated topology lanes grouped by `source_agent_id -> target_agent_id`
    - raw relation cards for concrete `relation_ref` drilldown
  - The topology lane cards summarize:
    - relation count
    - event count
    - snapshot count
    - stage pairs
    - dominant typed contracts
    - target-service tags
  - When a concrete `replayScope.handoffRef` is active, the panel should also expose a small focused-relation summary above the raw relation list.
- Frontend verification:
  - `cd frontend && npm run build`

## 2026-03-31 Replay Timeline Hierarchy Navigation Update

- `ReplayTimelinePanel.jsx`
  - The panel should now add three local aggregation layers:
    - `runTopology`
    - `stageTopology`
    - `artifactTopology`
  - These layers are for front-end narrowing only; do not introduce new backend replay endpoints just for this navigation.
  - Recommended drilldown order:
    - choose `run_id`
    - then choose `stage`
    - then choose `artifact_lookup_ref`
    - finally inspect filtered `events` and `snapshots`
  - The filtered detail panels should reuse existing event/snapshot selection behavior instead of creating a second detail system.
- Frontend verification:
  - `cd frontend && npm run build`

## 2026-03-31 Replay Artifact / Evidence Focus Update

- `App.jsx`
  - Shared `replayScope` should now also carry:
    - `artifactLookupRef`
    - `evidenceLookupRef`
  - Existing `GET /api/v1/cases/{case_id}/timeline/drilldown` requests should pass these fields when present.
- `ReplayTimelinePanel.jsx`
  - Artifact and evidence refs in event cards, snapshot cards, and snapshot detail should be clickable replay-focus controls.
  - Prefer reusing the same shared replay scope rather than adding local global-ish artifact/evidence selection state.
- `HandoffArtifactPanel.jsx`
  - Artifact refs and evidence refs inside a selected handoff should be able to reverse-drive replay drilldown.
- `ReportsView.jsx`
  - If replay focus hits an `evidenceLookupRef`, the evidence-pack selection should sync to the same evidence item when possible.
  - Clicking an evidence card can also reverse-set replay evidence focus, but avoid forcing replay focus during passive default selection.
- Frontend verification:
  - `cd frontend && npm run build`

## 2026-03-31 Replay Evidence Path Explanation Update

- `ReportsView.jsx`
  - Prefer building one local `replayEvidenceContext` from:
    - selected evidence item
    - current `replayDrilldown`
    - current `replayScope`
  - Keep this explanation local to the report layer instead of inventing a new global store.
- `EvidenceLinkPanel.jsx`
  - Besides audit / recommendation / delivery linkage, the panel should now explain:
    - which replay events reference the selected evidence
    - which snapshots carry the selected evidence
    - which handoffs explicitly reference the selected evidence
    - which run / stage / artifact tags are involved
  - This is an explanation layer for the current single-case replay path, not a new replay center.
- Frontend verification:
  - `cd frontend && npm run build`
## 2026-04-08 Incremental Update: Mainline Panel Spotlight

- `ReportsView.jsx`
  - If the numbered `MainlinePanelFrame` wrappers are already present, prefer adding one internal spotlight strip inside each framed panel before splitting more components.
  - The strip should explain why the current shared focus hits that panel and what story the reader should continue with next.
  - If the user clicks the mainline rail or the sticky mini-bar, prefer echoing that jump inside the panel body as well, not only on the outer border.
  - Keep this derived from existing front-end state such as `replayScope / workflowProgress / attackLoop / timelineOverview`; do not invent a backend API for it.
## 2026-04-08 Incremental Update: Sticky Reading Hint

- `ReportsView.jsx`
  - If the sticky `MainlinePositionBar` already exists, prefer letting it do more than navigation.
  - Add one short reading-hint strip under the jump buttons so the page keeps telling the presenter what to explain next.
  - Prefer echoing the latest jump target when the user just clicked a mainline button; otherwise derive a default reading suggestion from the currently active mainline panel.
  - Keep this as front-end guidance derived from existing state, not a backend contract change.
## 2026-04-09 Incremental Update: Route-Level Lazy Views

- `frontend/src/App.jsx`
  - If the initial bundle starts growing because multiple large MAS pages are imported at the top level, prefer splitting those pages with `React.lazy + Suspense`.
  - Good candidates in this repo are `MissionView / WorkbenchView / ReportsView / ComponentsView / OpsView / SettingsView`.
  - Prefer showing one lightweight loading card so the first visit to a tab still feels intentional rather than blank.
  - Treat this as an engineering optimization only; do not imply any backend loading-state contract change.
