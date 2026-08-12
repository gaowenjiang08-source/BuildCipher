import { DisplayValue } from "../../components/DisplayValue";
import { Panel } from "../../components/Panel";
import { SemanticPill, TagPill } from "../../components/SemanticPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

function MissionSnapshotCard({ eyebrow, value, detail, tone = "slate", statusLabel }) {
  const toneClass = {
    slate: "border-[color:var(--cg-border)] bg-[rgba(255,255,255,0.82)]",
    sky: "border-[color:var(--cg-accent-border)] bg-[color:var(--cg-accent-fog)]",
    amber: "border-[color:var(--cg-warning-border)] bg-[color:var(--cg-warning-fog)]",
    emerald: "border-[color:var(--cg-success-border)] bg-[color:var(--cg-success-fog)]",
  };

  return (
    <div className={cn("rounded-[24px] border px-4 py-4 shadow-[var(--cg-shadow-soft)]", toneClass[tone] || toneClass.slate)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">{eyebrow}</p>
        {statusLabel ? <TagPill tone={tone === "amber" ? "warn" : tone === "emerald" ? "ok" : "neutral"}>{statusLabel}</TagPill> : null}
      </div>
      <p className="mt-2 text-lg font-black text-slate-950">{value}</p>
      <p className="mt-2 text-sm leading-6 text-slate-700">{detail}</p>
    </div>
  );
}

function MissionActionCard({ step, eyebrow, title, detail, tone = "slate", onClick }) {
  const toneClass = {
    slate: "border-[color:var(--cg-border)] bg-[rgba(255,255,255,0.84)] hover:border-[color:var(--cg-border-strong)]",
    sky: "border-[color:var(--cg-accent-border)] bg-[color:var(--cg-accent-fog)] hover:border-[rgba(124,138,125,0.45)]",
    amber: "border-[color:var(--cg-warning-border)] bg-[color:var(--cg-warning-fog)] hover:border-[rgba(136,112,77,0.45)]",
    emerald: "border-[color:var(--cg-success-border)] bg-[color:var(--cg-success-fog)] hover:border-[rgba(85,100,87,0.45)]",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full rounded-[24px] border px-4 py-4 text-left transition hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-[rgba(124,138,125,0.18)]",
        toneClass[tone] || toneClass.slate
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-[color:var(--cg-border)] bg-white/90 text-xs font-black text-[color:var(--cg-text-soft)]">
            {step}
          </span>
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">{eyebrow}</p>
            <p className="mt-1 text-sm font-black text-slate-950">{title}</p>
          </div>
        </div>
        <TagPill tone="neutral">点击进入</TagPill>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600">{detail}</p>
    </button>
  );
}

function ExpertSeatCard({ member, latest, active = false, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-[26px] border bg-white/82 p-4 text-left transition duration-200 hover:-translate-y-0.5 hover:shadow-[var(--cg-shadow-soft)]",
        member.border,
        active ? "ring-2 ring-slate-900 shadow-[0_20px_40px_-28px_rgba(15,23,42,0.45)]" : ""
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-lg font-black text-slate-900">
          {member.icon} {member.title}
        </p>
        <TagPill tone={active ? "ok" : "neutral"}>{active ? "当前聚焦" : "可筛选"}</TagPill>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{member.mission}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {member.tools.map((tool) => (
          <span
            key={tool}
            className="rounded-full border border-white/70 bg-white/75 px-2 py-1 text-[11px] font-semibold text-slate-700"
          >
            {tool}
          </span>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <SemanticPill kind="status" value={latest?.status || "pending"} label={latest?.status_label} />
        <TagPill tone="neutral">{latest?.phase || "等待执行"}</TagPill>
      </div>
    </button>
  );
}

function WorkflowStageCard({ step, index }) {
  return (
    <div className="relative rounded-[24px] border border-slate-200 bg-white/92 p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-black",
            step.done ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-600"
          )}
        >
          {String(index + 1).padStart(2, "0")}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-black text-slate-900">{step.label}</p>
            <SemanticPill kind="boolean" value={step.done} trueText="已完成" falseText="进行中" falseTone="warn" />
          </div>
          <p className="mt-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">责任角色</p>
          <p className="mt-1 text-sm text-slate-700">{step.owner || "待分配"}</p>
        </div>
      </div>
    </div>
  );
}

export default function MissionView({
  scenarioTemplates,
  applyTemplate,
  businessReturnContext,
  onReturnToBusinessContext,
  setView,
  teamMembers,
  discussionLog,
  selectedActor,
  setSelectedActor,
  actorMatches,
  workflowProgress,
  filteredDiscussionLog,
  formatTime,
}) {
  const completedSteps = workflowProgress.filter((item) => item.done).length;
  const activeTemplate = scenarioTemplates[0] || null;
  const activeRoleCount = teamMembers.length;
  const discussionCount = discussionLog.length;

  const missionSnapshotCards = [
    {
      id: "workflow",
      eyebrow: "主线推进",
      value: `${completedSteps}/${workflowProgress.length || 0} 阶段已完成`,
      detail: "专家模式首页会先把需求澄清、候选生成、攻击闭环和交付收口讲成一条主线，再进入深层报告与工作台。",
      tone: completedSteps > 0 ? "emerald" : "slate",
      statusLabel: completedSteps > 0 ? "已有进展" : "待启动",
    },
    {
      id: "roles",
      eyebrow: "专家席位",
      value: `${activeRoleCount} 个角色在线`,
      detail: "不同角色对应不同职责、工具和判断口径，首页先用席位图帮助用户理解谁负责哪一段。",
      tone: "sky",
      statusLabel: selectedActor === "all" ? "当前看全体" : "已聚焦单角色",
    },
    {
      id: "discussion",
      eyebrow: "协作记录",
      value: `${discussionCount} 条内部记录`,
      detail: "讨论回放区用于展示多 Agent 的可解释协作过程，而不是只给出单次黑盒输出。",
      tone: discussionCount > 0 ? "amber" : "slate",
      statusLabel: discussionCount > 0 ? "可回放" : "待生成",
    },
  ];

  const missionActionCards = [
    {
      id: "reports",
      step: "01",
      eyebrow: "直接看主图",
      title: "进入专家报告页",
      detail: "适合已经有运行结果时，直接从主线、攻防闭环、证据和交付四段开始讲解。",
      tone: "sky",
      onClick: () => setView("reports"),
    },
    {
      id: "workbench",
      step: "02",
      eyebrow: "进入执行区",
      title: "打开执行工作台",
      detail: "适合继续运行 MAS、切换项目、查看候选方案和推进后续生成审计动作。",
      tone: "amber",
      onClick: () => setView("workbench"),
    },
    {
      id: "template",
      step: "03",
      eyebrow: "快速起步",
      title: activeTemplate ? `套用样例：${activeTemplate.title}` : "等待样例模板",
      detail: activeTemplate
        ? "会把首页推荐样例直接带入执行工作台，适合演示从需求进入系统的完整过程。"
        : "当前尚未加载可用样例模板。",
      tone: "emerald",
      onClick: () => {
        if (!activeTemplate) return;
        applyTemplate(activeTemplate);
        setView("workbench");
      },
    },
  ];

  return (
    <>
      {businessReturnContext?.summary ? (
        <div className="rounded-[24px] border border-amber-200 bg-[linear-gradient(135deg,#fffdf5_0%,#ffffff_60%,#f8fafc_100%)] p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <TagPill tone="warn">业务回跳锚点</TagPill>
            <TagPill tone="neutral">{businessReturnContext.viewLabel}</TagPill>
            <TagPill tone="ok">{businessReturnContext.sectionLabel}</TagPill>
            <TagPill tone={businessReturnContext.sectionSource === "manual" ? "warn" : "neutral"}>
              {businessReturnContext.sectionSource === "manual" ? "手动阅读落点" : "系统推荐落点"}
            </TagPill>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{businessReturnContext.summary}</p>
          {onReturnToBusinessContext ? (
            <button
              type="button"
              onClick={() => onReturnToBusinessContext?.()}
              className="mt-3 rounded-xl border border-amber-300 bg-white px-4 py-2 text-sm font-bold text-amber-800 transition hover:bg-amber-100"
            >
              返回业务上下文
            </button>
          ) : null}
        </div>
      ) : null}

      <section className="overflow-hidden rounded-[34px] border border-slate-200 bg-[radial-gradient(circle_at_top_left,rgba(251,191,36,0.18),transparent_24%),radial-gradient(circle_at_88%_8%,rgba(14,165,233,0.18),transparent_28%),linear-gradient(140deg,rgba(255,255,255,0.98),rgba(248,250,252,0.96),rgba(238,246,255,0.98))] p-6 shadow-[0_28px_60px_-32px_rgba(15,23,42,0.25)]">
        <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[28px] border border-white/70 bg-white/84 p-5 shadow-sm backdrop-blur">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="neutral">专家模式首页</TagPill>
              <TagPill tone="ok">主线透明化入口</TagPill>
              <TagPill tone="neutral">适合答辩开场</TagPill>
            </div>

            <div className="mt-5 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div className="max-w-3xl">
                <p className="text-[11px] font-black uppercase tracking-[0.28em] text-slate-500">专家首页摘要</p>
                <h1 className="mt-3 max-w-4xl text-3xl font-black tracking-tight text-slate-950 md:text-4xl">
                  把多 Agent 协作、推进阶段和内部讨论先讲清楚
                </h1>
                <p className="mt-3 text-sm leading-7 text-slate-600 md:text-base">
                  这页不直接下钻到某一个算法或某一张报告图，而是先帮助用户建立“谁在工作、现在推进到哪、下一步该去哪里”的整体心智模型。
                  适合在答辩、汇报和对外演示时作为专家模式的第一页。
                </p>
              </div>

              <div className="rounded-[28px] border border-slate-200 bg-slate-950 px-5 py-4 text-white shadow-sm">
                <p className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-300">首页定位</p>
                <p className="mt-2 text-lg font-black">先讲清角色、阶段和协作</p>
                <p className="mt-2 text-sm leading-6 text-slate-200">
                  如果要详细展示攻击闭环、证据链和交付收口，建议从这里进入专家报告页或执行工作台。
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <TagPill tone="neutral">{`${activeRoleCount} 个席位`}</TagPill>
                  <TagPill tone="neutral">{`${workflowProgress.length || 0} 个阶段`}</TagPill>
                </div>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
              {missionSnapshotCards.map((item) => (
                <MissionSnapshotCard key={item.id} {...item} />
              ))}
            </div>
          </div>

          <div className="rounded-[28px] border border-white/70 bg-white/88 p-5 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="neutral">推荐下一步</TagPill>
              <TagPill tone="neutral">点击直接跳转</TagPill>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              如果你是在演示系统，建议按下面顺序讲解；如果你正在继续推进项目，也可以直接进入执行工作台。
            </p>
            <div className="mt-4 space-y-3">
              {missionActionCards.map((item) => (
                <MissionActionCard key={item.id} {...item} />
              ))}
            </div>

            <div className="mt-4 rounded-[24px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_100%)] p-4">
              <div className="flex flex-wrap gap-2">
                {scenarioTemplates.slice(0, 3).map((item) => (
                  <button
                    key={item.title}
                    type="button"
                    onClick={() => {
                      applyTemplate(item);
                      setView("workbench");
                    }}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
                  >
                    {item.title}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <Panel
        title="专家席位与职责地图"
        subtitle="每个席位对应一类责任、工具和协作边界。先让用户理解“谁负责哪一段”，再去看具体的讨论回放和执行细节。"
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {teamMembers.map((member) => {
            const latest = [...discussionLog].reverse().find((item) => actorMatches(item.actor, member.actor));
            const active = selectedActor === member.actor;
            return (
              <ExpertSeatCard
                key={member.actor}
                member={member}
                latest={latest}
                active={active}
                onClick={() => setSelectedActor((prev) => (prev === member.actor ? "all" : member.actor))}
              />
            );
          })}
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.95fr_1.25fr]">
        <Panel
          title="主线推进阶段"
          subtitle="把 MAS 过程翻译成业务用户也能理解的推进状态。这里更适合讲“现在走到哪一步”，而不是直接展开底层技术细节。"
        >
          <div className="space-y-3">
            {workflowProgress.map((step, idx) => (
              <WorkflowStageCard key={step.phase} step={step} index={idx} />
            ))}
          </div>
        </Panel>

        <Panel
          title="内部讨论与决策回放"
          subtitle="这里展示的是可解释协作过程，而不是单次黑盒生成。可以按角色筛选，帮助外行人看懂每个 Agent 在项目里的职责。"
          right={
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setSelectedActor("all")}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-bold",
                  selectedActor === "all" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 bg-white text-slate-700"
                )}
              >
                全部
              </button>
              {teamMembers.map((member) => (
                <button
                  key={member.actor}
                  type="button"
                  onClick={() => setSelectedActor(member.actor)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs font-bold",
                    selectedActor === member.actor
                      ? "border-slate-900 bg-slate-900 text-white"
                      : "border-slate-300 bg-white text-slate-700"
                  )}
                >
                  {member.title}
                </button>
              ))}
            </div>
          }
        >
          <div className="max-h-[30rem] space-y-2 overflow-auto rounded-[24px] border border-slate-200 bg-slate-50/85 p-3">
            {filteredDiscussionLog.length === 0 ? <p className="text-sm text-slate-500">等待运行 MAS 后展示内部讨论...</p> : null}
            {filteredDiscussionLog.map((item, idx) => (
              <article key={`${idx}-${item.time || item.phase}`} className="rounded-[20px] border border-slate-200 bg-white p-3 shadow-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-bold text-slate-900">
                    <DisplayValue label={item.actor_label} value={item.actor} />
                  </p>
                  <SemanticPill kind="status" value={item.status} label={item.status_label} />
                  <TagPill tone="neutral">{item.phase}</TagPill>
                  <span className="text-xs text-slate-400">{formatTime(item.time)}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{item.message}</p>
              </article>
            ))}
          </div>
        </Panel>
      </div>
    </>
  );
}
