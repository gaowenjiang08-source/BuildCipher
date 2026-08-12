import { Panel } from "../../components/Panel";
import { TagPill } from "../../components/SemanticPill";

function normalizeName(item) {
  if (!item) return "";
  if (typeof item === "string") return item;
  return String(item.name || item.component_name || item.id || "").trim();
}

export default function ComponentsView({
  fetchComponents,
  componentFilter,
  setComponentFilter,
  filteredComponents,
}) {
  const keyword = String(componentFilter || "").trim().toLowerCase();
  const componentNames = filteredComponents
    .map(normalizeName)
    .filter(Boolean)
    .filter((name) => (keyword ? name.toLowerCase().includes(keyword) : true))
    .slice(0, 152);

  return (
    <Panel
      title="组件库"
      subtitle="集中查看 152 个密码学组件名称。"
      right={(
        <button
          type="button"
          onClick={fetchComponents}
          className="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
        >
          刷新组件
        </button>
      )}
    >
      <div className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={componentFilter}
            onChange={(event) => setComponentFilter(event.target.value)}
            placeholder="按组件名称搜索"
            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-slate-400 focus:bg-white md:w-[22rem]"
          />
          <TagPill tone="neutral">{`显示 ${componentNames.length} / 152`}</TagPill>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {componentNames.length === 0 ? (
            <div className="col-span-full rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
              没有匹配到组件名称。
            </div>
          ) : null}

          {componentNames.map((name, index) => (
            <article
              key={`${name}-${index}`}
              className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 transition hover:border-slate-300 hover:bg-white"
            >
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">
                {String(index + 1).padStart(3, "0")}
              </p>
              <p className="mt-2 text-sm font-semibold leading-6 text-slate-900">{name}</p>
            </article>
          ))}
        </div>
      </div>
    </Panel>
  );
}
