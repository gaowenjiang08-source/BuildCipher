import { Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";
import useDeferredMount from "./useDeferredMount";

function SkeletonRow({ widthClass = "w-full" }) {
  return <div className={`h-3 rounded-full bg-slate-200/90 ${widthClass}`} />;
}

export default function DeferredPanelMount({
  title,
  subtitle,
  sectionId = "",
  className = "",
  minHeightClass = "min-h-[220px]",
  rootMargin = "320px 0px",
  children,
}) {
  const { mounted, targetRef } = useDeferredMount({ rootMargin });

  return (
    <div id={sectionId || undefined} ref={targetRef} className={`cg-scroll-target ${className}`.trim()}>
      {mounted ? (
        children
      ) : (
        <Panel
          title={title}
          subtitle={subtitle || "该面板会在滚动接近可视区域后再挂载，优先把主线与首屏信息更早呈现出来。"}
        >
          <div
            className={`rounded-[28px] border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#f8fafc_42%,#eef6ff_100%)] p-5 shadow-sm ${minHeightClass}`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <TagPill tone="neutral">Deferred Mount</TagPill>
              <TagPill tone="neutral">接近视口后加载</TagPill>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              该区域当前先显示轻量占位卡，等滚动接近这里时再加载完整内容，避免报告页首屏一次性挂载过多重面板。
            </p>
            <div className="mt-4 space-y-3 rounded-2xl border border-white/80 bg-white/80 p-4 shadow-sm">
              <SkeletonRow widthClass="w-24" />
              <SkeletonRow widthClass="w-4/5" />
              <SkeletonRow widthClass="w-full" />
              <SkeletonRow widthClass="w-5/6" />
              <SkeletonRow widthClass="w-3/4" />
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}
