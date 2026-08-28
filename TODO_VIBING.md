# BuildCipher Studio TODO

最后更新：2026-04-19  
状态：active

## 当前主线

当前主线不是继续堆零散功能，而是把后端补齐到“结构清晰、对象稳定、闭环可解释、前端可对接”的状态。  
本阶段默认优先级为：

1. 后端架构补齐
2. 前后端稳定对象对齐
3. 可视化与答辩表达增强

## 本周必做

### P0-1 独立上下文与记忆总线继续收口

目标：

- 让更多主链角色稳定依赖 `projection + handoff + ref lookup`
- 减少共享长上下文的隐性耦合

完成判定：

- generation / audit / attack / patch / reflection 的运行输入都能主要从结构化对象恢复
- 回看某一轮时，能解释“上游到底传了什么、丢了什么、保留了什么”

### P0-2 执行平面合同继续统一

目标：

- 继续收口 deploy / attack / patch_apply / rollback / regression_replay 的统一摘要结构

完成判定：

- `delivery.backend_architecture.execution_plane` 能稳定解释一轮执行
- 前端与 replay 层不需要各自重新拼装执行语义

### P0-3 Expert Gate 多轮闭环继续推进

目标：

- 把当前单次 same-run retry 第一版，继续推进到更清晰的多轮闭环设计

完成判定：

- 能明确描述每一轮为何继续、为何停止、为何进入 patch
- 预算、终止信号、下一步路由都有稳定解释字段

### P0-4 证据与交付引用继续绑定

目标：

- 让 evidence、artifact、vulnerability、patch、delivery 之间的链路更完整

完成判定：

- 报告、前端、replay 能围绕同一批 ref 与摘要对象解释结果

## 后端优先事项

### 1. Memory Bus

- 继续补 `typed_contracts`
- 继续补压缩策略与 retained refs
- 继续补 agent 间传递的可解释性

### 2. Sandbox / Execution Plane

- 继续统一 dispatcher contract
- 继续补 patch / rollback / regression 的工件摘要
- 为 `container / remote_worker` 保留明确接线口，不误写成已落地

### 3. Attack Loop

- 继续补充多轮 expert gate 设计
- 继续增强 attack planning 的 skill / retrieval 接线
- 继续稳定 `loop_status`、`same_run_retry_summary`、`attempt_trace`

### 4. Replay / Timeline

- 继续加强 projection / handoff / lineage 的 drilldown 可解释性
- 继续把 retry 恢复点、resume ref、压缩策略纳入统一回放口径

## 前端优先事项

### 1. 围绕后端稳定对象重排页面

- 项目入口与系统状态
- 需求与上下文
- 方案与审计
- 攻击沙盒与执行态势
- replay / handoff / evidence
- 交付与导出

### 1.1 按新运行控制台架构推进

- 当前进度（2026-04-20）：
  - 已新增专家模式 `运行控制台` 第一版
  - 已把 `RunCreator / Live Console / Attack Loop` 合并进一个可见桥接页
  - 已新增 `useRunDraftStore / useRunSessionStore / useStageConsoleStore / useAttackLoopStore` 第一版状态骨架
  - 已通过 `cd frontend; npm.cmd run build`
- 下一步继续：
  - 把底部交付预览拆成独立 `Delivery Workspace`
  - 把 replay 预览拆成独立 `Replay / 复盘`
  - 将后端标准化流式事件逐步分发进前端状态总线
  - 将轻量 telemetry 升级为 ECharts 滚动时间窗

- 先落 `RunCreator`
- 再落 `Live Console`
- 再落 `Attack Loop`
- 之后再补 `Delivery Workspace`
- 最后补 `Replay / 复盘`

设计基线见：

- `docs/modules/frontend_runtime_console_architecture.md`

### 1.2 先稳定事件模型，再堆页面

- 优先约定流式事件 schema
- 优先约定阶段状态对象
- 优先约定 attack loop 事件对象
- 避免前端直接消费原始文本流做大面积页面逻辑

### 1.3 先稳定页面树与 Zustand 状态树

- 优先定义一级页面树
- 优先定义 store 分域边界
- 优先定义 selector 分层
- 避免继续把运行态、攻击态、交付态、replay 态混在一个总状态里

状态设计基线见：

- `docs/modules/frontend_page_state_architecture.md`

### 2. 继续去除历史页面残留逻辑

- 避免同一数据被多个旧组件重复解释
- 避免临时状态与正式状态混用

### 3. 保持中文优先企业表达

- 标题、建议、章节、推荐理由默认中文
- `template_id`、`skill_id`、`scenario`、API 字段名保持稳定

## 文档优先事项

### 1. 总文档

- 保持“当前已有 + 当前未完成 + 下一阶段路线图”
- 不再让总文档主体继续膨胀成补记日志

### 2. 模块文档

若涉及以下内容，优先更新 `docs/modules/*.md`：

- 为什么这样设计
- 如何构建
- 替代方案取舍
- 如何扩展
- 如何验证

### 3. 模块 README

若改动某个目录下的代码，同步更新该目录 `README.md`

## 验证方式

### 后端

```powershell
poetry run pytest tests/unit -q
python -m compileall src streamlit scripts tests
poetry run cipher-genius-api
```

### 前端

```powershell
cd frontend
npm run dev
npm run build
```

当前说明：

- `npm run build` 在本环境下仍可能受 `esbuild spawn EPERM` 影响
- 因此需要同时记录“代码是否对齐”和“当前环境是否允许完成构建验收”

## 当前不应误判为已完成的事项

- 生产级容器隔离沙盒
- 远程攻击执行平面
- 完整多轮 expert orchestration graph
- 跨项目全局记忆收益
- 自动微调闭环

## 本阶段完成标志

当以下条件同时满足时，才能认为当前主线基本收口：

1. 后端主流程、记忆传递、执行平面、回放平面可以统一解释
2. 攻击闭环的继续 / 停止 / 修补 / 回归都有稳定状态语义
3. 前端主要页面已映射后端稳定对象
4. 文档可以直接回答“系统现在是什么、还缺什么、下一步做什么”
