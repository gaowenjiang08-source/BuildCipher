import { useMemo, useState } from "react";
import { runConstructionDemo } from "../../api/client";
import {
  ArrowRightIcon,
  BriefcaseIcon,
  CheckCircleIcon,
  DatabaseIcon,
  FlowIcon,
  LayersIcon,
  PulseIcon,
  ShieldIcon,
  SparkIcon,
} from "../../components/Icons";
import { CONSTRUCTION_ATTACKS, attackResultByType, buildConstructionState } from "./constructionBusinessState";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

const VIEW_META = {
  overview: ["工程可信总览", "把模型、设备、参与方和验收证据放进同一条可信交付链。"],
  workbench: ["工程项目工作台", "定义工程资产、参与方、可信目标与交付边界。"],
  context: ["可信协同依据", "解释每项控制保护什么、由谁负责、产生哪些证据。"],
  validation: ["安全验证实验室", "用同一组五类攻击比较补丁前后的真实状态。"],
  delivery: ["可信交付中心", "汇总可交付结论、证据引用和工程复核边界。"],
};

const PARTICIPANTS = [
  ["建设单位", "确认交付目标与最终接收范围"],
  ["设计单位", "签发模型、图纸和版本变更"],
  ["总承包方", "组织专业协同与施工交付"],
  ["专业分包", "仅接收本专业最小必要数据"],
  ["监理单位", "签批验收结论并固化证据"],
];

function Metric({ label, value, note, tone = "blue" }) {
  const tones = {
    blue: "border-blue-200 bg-blue-50/70 text-blue-800",
    green: "border-emerald-200 bg-emerald-50/70 text-emerald-800",
    amber: "border-amber-200 bg-amber-50/70 text-amber-800",
    slate: "border-slate-200 bg-white text-slate-800",
  };
  return (
    <div className={cn("rounded-2xl border p-4", tones[tone])}>
      <p className="text-xs font-bold uppercase tracking-[0.14em] opacity-70">{label}</p>
      <p className="mt-2 text-3xl font-black tracking-[-0.05em]">{value}</p>
      {note ? <p className="mt-2 text-xs leading-5 opacity-75">{note}</p> : null}
    </div>
  );
}

function Section({ title, description, children, id }) {
  return (
    <section id={id} className="rounded-[28px] border border-slate-200 bg-white/95 p-5 shadow-[0_20px_50px_rgba(15,23,42,0.06)] md:p-6">
      <div className="max-w-3xl">
        <h2 className="text-xl font-black tracking-[-0.035em] text-slate-950">{title}</h2>
        {description ? <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p> : null}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function AttackComparison({ state, demo }) {
  const hardenedResults = demo?.results || state.regression;
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200">
      <div className="grid grid-cols-[1.4fr_0.7fr_0.7fr] gap-3 bg-slate-950 px-4 py-3 text-xs font-bold uppercase tracking-[0.12em] text-slate-300">
        <span>验证场景</span><span>补丁前</span><span>补丁后</span>
      </div>
      {CONSTRUCTION_ATTACKS.map((attack) => {
        const before = attackResultByType(state.baseline, attack.id);
        const after = attackResultByType(hardenedResults, attack.id) || demo?.results?.find((item) => item.attack_type === attack.id);
        const beforeBlocked = Boolean(before?.metrics?.blocked ?? before?.blocked);
        const afterBlocked = Boolean(after?.metrics?.blocked ?? after?.blocked);
        return (
          <div key={attack.id} className="grid grid-cols-[1.4fr_0.7fr_0.7fr] gap-3 border-t border-slate-200 px-4 py-4 text-sm first:border-t-0">
            <div className="min-w-0">
              <p className="font-bold text-slate-900">{attack.label}</p>
              <p className="mt-1 text-xs text-slate-500">{attack.asset} · {attack.control}</p>
            </div>
            <span className={cn("font-bold", before ? (beforeBlocked ? "text-emerald-700" : "text-rose-700") : "text-slate-400")}>
              {before ? (beforeBlocked ? "已阻断" : "可利用") : "待运行"}
            </span>
            <span className={cn("font-bold", after ? (afterBlocked ? "text-emerald-700" : "text-rose-700") : "text-slate-400")}>
              {after ? (afterBlocked ? "已阻断" : "未阻断") : "待回归"}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function ConstructionWorkspaceView({
  view,
  currentCaseSummary,
  delivery,
  attackLoop,
  settings,
  workbenchContent,
  exportFormats = [],
  exportDelivery,
  onOpenProject,
  onOpenContext,
  onOpenValidation,
  onOpenDelivery,
}) {
  const state = useMemo(
    () => buildConstructionState({ attackLoop, delivery, currentCaseSummary }),
    [attackLoop, delivery, currentCaseSummary]
  );
  const [demo, setDemo] = useState(null);
  const [demoStatus, setDemoStatus] = useState("idle");
  const [demoError, setDemoError] = useState("");
  const [title, subtitle] = VIEW_META[view] || VIEW_META.overview;

  async function executeDemo() {
    setDemoStatus("loading");
    setDemoError("");
    try {
      const result = await runConstructionDemo(
        { project_id: state.caseId === "待创建工程项目" ? "buildtrust-demo-project" : state.caseId },
        settings
      );
      setDemo(result);
      setDemoStatus("done");
    } catch (error) {
      setDemoError(error?.message || "演示运行失败");
      setDemoStatus("error");
    }
  }

  const header = (
    <div className="relative overflow-hidden rounded-[32px] border border-slate-800 bg-[linear-gradient(135deg,#07111f_0%,#10243b_55%,#12364a_100%)] p-6 text-white shadow-[0_30px_80px_rgba(15,23,42,0.18)] md:p-8">
      <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-cyan-400/10 blur-2xl" />
      <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-100">BuildTrust v1</span>
            <span className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">{state.targetLabel}</span>
          </div>
          <h1 className="mt-4 text-3xl font-black tracking-[-0.055em] md:text-5xl">{title}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300 md:text-base">{subtitle}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm backdrop-blur">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">当前工程</p>
          <p className="mt-1 max-w-sm break-all font-bold text-white">{state.caseId}</p>
          <p className="mt-1 text-xs text-cyan-200">{state.statusLabel}</p>
        </div>
      </div>
    </div>
  );

  if (view === "workbench") {
    return <div className="space-y-5">{header}{workbenchContent}</div>;
  }

  if (view === "overview") {
    return (
      <div className="space-y-5">
        {header}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Metric label="建筑攻击" value="5" note="模型、权限与设备数据" tone="blue" />
          <Metric label="补丁前阻断" value={`${state.baselineBlocked}/${state.baseline.length || 5}`} note="未运行时显示预期基线" tone="amber" />
          <Metric label="补丁后阻断" value={`${state.regressionBlocked}/${state.regression.length || 5}`} note="hardened 回归状态" tone="green" />
          <Metric label="证据引用" value={state.evidenceCount} note="文件工件与摘要引用" tone="slate" />
        </div>
        <Section id="journey" title="第一版场景主线" description="从工程资产开始，经过可信控制与攻击验证，最终形成可复核交付。">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {[
              [BriefcaseIcon, "定义工程项目", "录入模型、参与方与验收边界", onOpenProject],
              [FlowIcon, "建立可信协同", "明确签批、版本和最小权限", onOpenContext],
              [ShieldIcon, "执行五类验证", "比较 baseline 与 hardened", onOpenValidation],
              [SparkIcon, "形成可信交付", "汇总结论、证据和边界", onOpenDelivery],
            ].map(([Icon, itemTitle, note, action]) => (
              <button key={itemTitle} type="button" onClick={action} className="group rounded-2xl border border-slate-200 bg-slate-50/70 p-4 text-left transition hover:-translate-y-0.5 hover:border-blue-300 hover:bg-white hover:shadow-lg">
                <Icon size={20} className="text-blue-700" />
                <p className="mt-4 font-black text-slate-950">{itemTitle}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{note}</p>
                <span className="mt-4 inline-flex items-center gap-2 text-xs font-bold text-blue-700">进入 <ArrowRightIcon size={14} /></span>
              </button>
            ))}
          </div>
        </Section>
      </div>
    );
  }

  if (view === "context") {
    return (
      <div className="space-y-5">{header}
        <Section id="participants" title="参与方责任边界" description="第一版只表达角色与交付包级权限，不宣称构件或属性级授权。">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {PARTICIPANTS.map(([name, duty]) => <div key={name} className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><p className="font-black text-slate-900">{name}</p><p className="mt-2 text-xs leading-5 text-slate-600">{duty}</p></div>)}
          </div>
        </Section>
        <Section id="evidence" title="证据链结构" description="每一次验证结果同时保留业务状态、文件工件和摘要引用。">
          <div className="grid gap-3 lg:grid-cols-3">
            {[[LayersIcon,"工程资产","IFC、版本、角色、设备消息"],[ShieldIcon,"验证结论","检测、阻断、修复、回归"],[DatabaseIcon,"证据引用","JSON 工件、哈希链、SHA-256"]].map(([Icon,name,note])=><div key={name} className="rounded-2xl border border-slate-200 p-5"><Icon size={20} className="text-blue-700"/><p className="mt-3 font-black">{name}</p><p className="mt-2 text-sm text-slate-600">{note}</p></div>)}
          </div>
        </Section>
      </div>
    );
  }

  if (view === "validation") {
    return (
      <div className="space-y-5">{header}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Metric label="基线阻断" value={`${state.baselineBlocked}/${state.baseline.length || 5}`} tone="amber" />
          <Metric label="补丁后阻断" value={`${state.regressionBlocked}/${state.regression.length || 5}`} tone="green" />
          <Metric label="补丁状态" value={state.patchApplied ? "已应用" : "待应用"} tone="blue" />
          <Metric label="证据账本" value={state.ledgerValid || demo?.evidence_ledger_valid ? "有效" : "待验证"} tone="slate" />
        </div>
        <Section id="attacks" title="五类攻击前后对比" description="没有 MAS 结果时，可运行 hardened 参考演示验证后置控制。">
          <AttackComparison state={state} demo={demo} />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={executeDemo} disabled={demoStatus === "loading"} className="cg-button cg-button-primary disabled:cursor-wait disabled:opacity-60">
              <PulseIcon size={16} /> {demoStatus === "loading" ? "正在执行" : "运行参考演示"}
            </button>
            {demoStatus === "done" ? <span className="text-sm font-bold text-emerald-700">完成：{demo.blocked_count}/{demo.attack_count} 已阻断</span> : null}
            {demoError ? <span role="alert" className="text-sm font-bold text-rose-700">{demoError}</span> : null}
          </div>
        </Section>
      </div>
    );
  }

  return (
    <div className="space-y-5">{header}
      <Section id="conclusion" title="可信交付结论" description="交付内容包含可复核证据，同时明确演示能力与生产能力的边界。">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5"><CheckCircleIcon size={22} className="text-emerald-700"/><p className="mt-3 font-black text-emerald-950">五攻击控制</p><p className="mt-2 text-sm text-emerald-800">{state.regressionBlocked}/{state.regression.length || 5} 已形成回归阻断证据</p></div>
          <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5"><DatabaseIcon size={22} className="text-blue-700"/><p className="mt-3 font-black text-blue-950">证据材料</p><p className="mt-2 text-sm text-blue-800">{state.evidenceCount} 个去重引用进入当前交付</p></div>
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5"><ShieldIcon size={22} className="text-amber-700"/><p className="mt-3 font-black text-amber-950">人工复核</p><p className="mt-2 text-sm text-amber-800">生产接入前仍需 BIM、密码与项目治理专家确认</p></div>
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          {exportFormats.map((format) => <button key={format.id} type="button" onClick={() => exportDelivery?.(format)} className="cg-button cg-button-secondary">{format.label}</button>)}
        </div>
      </Section>
      <Section id="boundaries" title="第一版能力边界">
        <ul className="grid gap-3 text-sm leading-6 text-slate-700 md:grid-cols-2">
          {["IFC 按文件字节验证，尚未解析实体、GUID 或模型视图。","身份认证使用 HMAC 演示，不等于生产 PKI 或人员证书。","证据账本是本地 JSON 哈希链，不是数据库、WORM 或外部可信时间。","权限控制到角色和完整交付包级，尚未实现字段与构件级最小披露。"].map((item)=><li key={item} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">{item}</li>)}
        </ul>
      </Section>
    </div>
  );
}
