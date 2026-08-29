# BuildCipher Studio Remaining Work

最后更新：2026-04-19  
状态：active

## 文档用途

本文件只回答三个问题：

1. 当前还缺什么
2. 哪些缺口最影响“后端架构完整性”
3. 下一阶段应该先补哪里

如果要看“项目现在已经有什么”，请看 [README.md](README.md) 与 [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md)。
如果要看“下一轮具体执行清单”，请看 [TODO_VIBING.md](TODO_VIBING.md)。

## 一句话判断

当前项目已经不是 demo，但也还不能说“后端架构已经完整完成”。  
更准确的判断是：

- 后端主线已成型
- 关键 agent 已基本接通
- 记忆、执行、回放已进入第一版
- 真正的难点仍集中在上下文管理、执行平面升级、闭环稳定性与前后端稳定对齐

## P0：当前最重要缺口

### 1. 独立上下文与记忆传递还未彻底收口

当前已有：

- `context_projections`
- `memory_handoffs`
- `case_memory`
- `timeline / replay`

当前缺口：

- 不是所有主链角色都已稳定做到 projection-only
- 长链路压缩与保真机制还不够稳
- agent 之间的传递虽然已经结构化，但仍需继续证明“信息足够、不失真、可回查”

为什么这是 P0：

- 这是多 agent 系统能否长期扩展的硬基础
- 也是后续多轮闭环与 replay 可解释性的根基

### 2. 执行平面还只是演示级

当前已有：

- `LocalSandboxDispatcher`
- `LocalSandboxRuntime`
- `ExecutionPlaneBuilder`
- patch apply / rollback plan 第一版

当前缺口：

- 仍是本地受限进程执行
- `container / remote_worker` 仍未变成真实执行器
- 还没有生产级隔离、远程执行和统一执行调度

为什么这是 P0：

- 用户的目标是“真实 LLM 决策的攻击 agent”
- 如果执行面太弱，后续攻防闭环的技术深度会被卡住

### 3. Expert Gate 多轮闭环仍未完成

当前已有：

- 基线攻击
- 漏洞评估
- 专家闸门
- same-run retry 第一版
- patch planning
- regression replay

当前缺口：

- retry 预算目前只支持 `0` 或 `1`
- 还不是完整多轮 attack -> evaluate -> gate -> patch -> regress 子图
- 还没有更细的终止策略和预算策略

为什么这是 P0：

- 这直接决定系统是不是“会迭代优化的攻防闭环”

### 4. 交付证据链还需要进一步稳定

当前已有：

- 中文优先企业报告
- evidence pack
- replay / timeline
- delivery 汇总对象

当前缺口：

- 证据覆盖率与引用绑定还需增强
- 工件、漏洞、补丁、交付之间的可追溯性还需继续收口

为什么这是 P0：

- 企业交付与答辩都依赖“可解释、可引用、可证明”

## P1：重要但次于主架构补齐

### 1. 前端与后端稳定对象的全面对齐

当前已有：

- 前端业务模式 / 专家模式框架
- 工作台、报告页、运维页、设置页的大重构

当前缺口：

- 仍需围绕 `backend_architecture / attack_loop / replay_plane / memory_bus` 做一一映射
- 还需进一步压缩历史页面残留结构

### 2. replay 可视化与 drilldown 解释层

当前已有：

- timeline / events / snapshots / drilldown / lineage API

当前缺口：

- 前端如何把它讲得让外行也看懂，还未完全收口
- retry 恢复点与 handoff 图谱的叙事仍可继续加强

### 3. 检索增强力度

当前已有：

- 知识导入
- Qdrant
- evidence pack

当前缺口：

- generation / audit / attack planning 还需要更强的 RAG 影响力
- ranking / selection 层还需更可解释

## P2：后续增强项

### 1. 全局记忆与跨项目收益

当前已有的是项目级记忆，尚未完成真正意义上的跨项目全局收益层。

### 2. Reflection policy 层

当前 reflection 已能回灌 generation / audit，但还未形成更成熟的 policy、prompt、检索、记忆多层优化框架。

### 3. 自动微调闭环

当前可作为文档展示方向保留，但不应写成已落地能力。

## 前端剩余缺口

当前前端不再以“美化 UI”为主问题，更关键的是：

- 页面模块要严格映射后端稳定对象
- 让外行能看懂主流程、闭环和证据链
- 让专家能钻到 replay、handoff、artifact、lineage 细节
- 继续治理构建、编码与页面一致性问题

当前特别说明：

- 本环境下 `frontend` 的真实生产构建仍被 `esbuild spawn EPERM` 阻断
- 因此前端验收应区分“页面结构改好了”与“生产构建已通过”

## 文档与答辩剩余缺口

- 总文档要继续坚持“现状说明 + 能力边界 + 路线图”口径
- 模块文档要继续沉淀“为什么这样设计、如何验证、如何扩展”
- 架构图、流程图、对外讲解图仍可继续整理

## 当前完成度判断

### 后端架构

- 结论：未完成，但主骨架已成型

### 攻击 agent / 评估 agent / 修补 agent

- 结论：已具备真实 LLM 决策层，但闭环稳定性和执行面还需继续补强

### 沙盒

- 结论：演示级可用，但未到真实隔离执行级别

### 前端

- 结论：已进入重构中后段，但还需要继续按后端对象收口

## 下一步推荐

推荐继续按下面顺序推进：

1. 先补 `memory_bus` 与上下文传递策略
2. 再补 `execution_plane` 与 sandbox contract
3. 再推进 expert gate 多轮闭环
4. 最后让前端围绕稳定对象完成透明化展示
