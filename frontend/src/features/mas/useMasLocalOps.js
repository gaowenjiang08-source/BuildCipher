export default function useMasLocalOps({
  runHistoryKey,
  componentCacheKey,
  businessReadingContextKey,
  resetBusinessReadingContext,
  resetReportFocus,
  setHistory,
  setComponents,
  setNotice,
  setResult,
  setView,
  setRequirement,
}) {
  async function copyText(text, successHint) {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setNotice(successHint || "已复制到剪贴板");
    } catch {
      setNotice("复制失败，请检查浏览器权限");
    }
  }

  function clearLocalData() {
    localStorage.removeItem(runHistoryKey);
    localStorage.removeItem(componentCacheKey);
    if (businessReadingContextKey) {
      localStorage.removeItem(businessReadingContextKey);
    }
    setHistory([]);
    setComponents([]);
    resetBusinessReadingContext?.();
    setNotice("本地缓存已清理");
  }

  function loadFromHistory(item) {
    setResult(item);
    setView("workbench");
    setNotice("已载入历史交付");
  }

  function applyTemplate(template) {
    if (!template?.requirement) return;
    setRequirement(template.requirement);
    setNotice(`模板已载入：${template.title}`);
  }

  function appendRequirementDimension(prefix, value) {
    const line = `${prefix}: ${value}`;
    setRequirement((prev) => {
      const base = String(prev || "").trim();
      if (!base) return line;
      if (base.includes(line)) return base;
      return `${base}\n${line}`;
    });
  }

  function insertConstructionSkeleton() {
    const skeleton = [
      "工程资产: BIM/IFC 模型, 施工图纸, 检测报告, 工地设备遥测",
      "参与方: 建设单位, 设计单位, 总承包方, 专业分包, 监理单位",
      "可信目标: 内容防篡改, 版本防回滚, 最小权限交付, 设备防冒充, 证据可追溯",
      "项目约束: 多参与方协同, 工地离线网络, 长期归档, localhost 部署",
      "验收方式: 五类攻击基线与加固回归, 交付证据账本复核",
    ].join("\n");
    setRequirement((prev) => {
      const base = String(prev || "").trim();
      if (!base) return skeleton;
      return `${base}\n${skeleton}`;
    });
    setNotice("已插入建筑工程需求骨架");
  }

  return {
    copyText,
    clearLocalData,
    loadFromHistory,
    applyTemplate,
    appendRequirementDimension,
    insertConstructionSkeleton,
  };
}
