import { TagPill } from "../../components/SemanticPill";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

export default function ReportsQuickMap({
  items = [],
  activeSectionId = "",
  currentMainlineLabel = "",
  selectedEvidence,
  selectedDeliveryFragmentId,
  onJumpToMainlinePanel,
  onJumpToSection,
}) {
  const activeItem = items.find((item) => item.id === activeSectionId) || items[0] || null;

  function handleJump(item) {
    if (!item) return;
    if (item.kind === "mainline") {
      onJumpToMainlinePanel?.(item.id);
      return;
    }
    onJumpToSection?.(item.id);
  }

  return (
    <aside className="hidden 2xl:block">
      <div className="cg-report-quickmap">
        <div className="rounded-[28px] border border-slate-200 bg-[linear-gradient(160deg,rgba(255,255,255,0.97),rgba(248,250,252,0.95),rgba(239,246,255,0.96))] p-4 shadow-[0_24px_45px_-28px_rgba(15,23,42,0.28)] backdrop-blur">
          <div className="flex flex-wrap items-center gap-2">
            <TagPill tone={activeItem ? "ok" : "neutral"}>{activeItem ? "当前阅读位置" : "等待定位"}</TagPill>
            <TagPill tone="neutral">右侧阅读小地图</TagPill>
            {currentMainlineLabel ? <TagPill tone="warn">{currentMainlineLabel}</TagPill> : null}
          </div>
          <p className="mt-3 text-base font-black text-slate-950">{activeItem?.label || "正在读取整页报告"}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {activeItem?.detail || "右侧小地图会跟随滚动高亮当前章节，也支持直接跳到主线、证据或交付区域。"}
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            <TagPill tone={selectedEvidence ? "ok" : "neutral"}>{selectedEvidence ? "证据已锁定" : "证据未锁定"}</TagPill>
            <TagPill tone={selectedDeliveryFragmentId ? "warn" : "neutral"}>
              {selectedDeliveryFragmentId ? "交付片段已锁定" : "交付片段未锁定"}
            </TagPill>
          </div>

          <div className="mt-5 space-y-2">
            {items.map((item, index) => {
              const active = item.id === activeSectionId;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleJump(item)}
                  className={cn(
                    "flex w-full items-start gap-3 rounded-2xl border px-3 py-3 text-left transition focus:outline-none focus:ring-2 focus:ring-sky-300",
                    active
                      ? "border-slate-900 bg-slate-950 text-white shadow-sm"
                      : "border-slate-200 bg-white/90 text-slate-700 hover:border-slate-300"
                  )}
                >
                  <div
                    className={cn(
                      "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-black",
                      active ? "border-white/25 bg-white/10 text-white" : "border-slate-200 bg-slate-50 text-slate-600"
                    )}
                  >
                    {String(index + 1).padStart(2, "0")}
                  </div>
                  <div className="min-w-0">
                    <p className={cn("text-sm font-black", active ? "text-white" : "text-slate-900")}>{item.label}</p>
                    <p className={cn("mt-1 text-xs leading-5", active ? "text-slate-200" : "text-slate-600")}>{item.detail}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
}
