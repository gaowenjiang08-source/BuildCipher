import { formatDisplayValue } from "../../components/DisplayValue";
import { displayOrDash } from "./masHelpers";

export function fileSafeName(value = "buildtrust_delivery") {
  const safe = String(value)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return safe || "buildtrust_delivery";
}

export function timestampSlug() {
  const now = new Date();
  const pad = (num) => String(num).padStart(2, "0");
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

export function downloadTextFile(filename, content, mime = "text/plain;charset=utf-8") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function escapeLatex(value = "") {
  let text = String(value);
  text = text.replace(/\\/g, "\\textbackslash{}");
  text = text.replace(/([&%$#_{}])/g, "\\$1");
  text = text.replace(/~/g, "\\textasciitilde{}");
  text = text.replace(/\^/g, "\\textasciicircum{}");
  return text;
}

export function buildMarkdownExport(pkg = {}) {
  const scheme = pkg.final_scheme || {};
  const components = scheme.components || [];
  const findings = pkg.audit?.findings || [];
  const recommendations = pkg.audit?.recommendations || [];
  const credibility = pkg.credibility_assessment || scheme.credibility_assessment || {};
  const appliedSkill = pkg.applied_skill || pkg.delivery?.applied_skill || null;
  const lines = [
    `# BuildCipher Studio 交付文档 - ${scheme.name || "未命名方案"}`,
    "",
    "## 执行摘要",
    `- 交付编号：${pkg.request_id || "--"}`,
    `- 任务编号：${pkg.run_id || "--"}`,
    `- 生成时间：${pkg.generated_at || "--"}`,
    `- 交付状态：${formatDisplayValue({ label: pkg.delivery?.status_label, value: pkg.delivery?.status })}`,
    `- 选中方案：${pkg.delivery?.selected_proposal || "--"}`,
    `- 合规得分：${pkg.delivery?.compliance_score ?? "--"}`,
    `- 风险得分：${pkg.delivery?.risk_score ?? "--"}`,
    `- 行业专家：${appliedSkill?.name || "--"}`,
    `- 可信度得分：${credibility?.credibility_score ?? "--"}`,
    `- 算法实力得分：${credibility?.algorithm_strength_score ?? "--"}`,
    `- 证据覆盖率：${credibility?.evidence_coverage ?? "--"}`,
    "",
    "## 最终方案",
    `- 方案名称：${scheme.name || "--"}`,
    `- 方案类型：${scheme.scheme_type || "--"}`,
    `- 安全等级：${scheme.security_level || "--"}`,
    `- 综合评分：${scheme.score ?? "--"}`,
    "",
    "## 组件清单",
  ];

  if (!components.length) {
    lines.push("- 暂无组件信息");
  } else {
    components.forEach((item) => {
      lines.push(
        `- ${item.name || "--"} | 类别=${displayOrDash(item.category)} | 安全等级=${item.security_level ?? "--"} | 软件速度=${displayOrDash(item.software_speed)}`
      );
    });
  }

  lines.push("", "## 可信度摘要");
  if (!Object.keys(credibility || {}).length) {
    lines.push("- 暂无可信度摘要");
  } else {
    (credibility.strengths || []).slice(0, 4).forEach((item) => lines.push(`- 亮点：${item}`));
    (credibility.gaps || []).slice(0, 4).forEach((item) => lines.push(`- 缺口：${item}`));
    (credibility.sources || []).slice(0, 6).forEach((item) => {
      lines.push(`- 来源： [${item.type || "--"}] ${item.component || "--"} - ${item.title || "--"}`);
    });
  }

  lines.push("", "## 设计理由", scheme.design_rationale || "暂无设计说明", "", "## 审计发现");
  if (!findings.length) {
    lines.push("- 暂无审计发现");
  } else {
    findings.forEach((item) => lines.push(`- ${item}`));
  }

  lines.push("", "## 审计建议");
  if (!recommendations.length) {
    lines.push("- 暂无审计建议");
  } else {
    recommendations.forEach((item) => lines.push(`- ${item}`));
  }

  lines.push("", "## 说明", "- 本文档用于工程交接与企业评审。", "- 在正式投产前仍需进行独立密码学复核与安全审计。");
  return lines.join("\n");
}

export function buildLatexExport(pkg = {}) {
  const scheme = pkg.final_scheme || {};
  const components = scheme.components || [];
  const findings = pkg.audit?.findings || [];
  const recommendations = pkg.audit?.recommendations || [];
  const credibility = pkg.credibility_assessment || scheme.credibility_assessment || {};
  const appliedSkill = pkg.applied_skill || pkg.delivery?.applied_skill || null;
  const componentItems = components.length
    ? components
        .map(
          (item) =>
            `\\item ${escapeLatex(item.name || "--")}（类别=${escapeLatex(displayOrDash(item.category))}，安全等级=${escapeLatex(item.security_level ?? "--")}，软件速度=${escapeLatex(displayOrDash(item.software_speed))}）`
        )
        .join("\n")
    : "\\item 暂无组件信息";
  const findingItems = findings.length ? findings.map((item) => `\\item ${escapeLatex(item)}`).join("\n") : "\\item 暂无审计发现";
  const recommendationItems = recommendations.length ? recommendations.map((item) => `\\item ${escapeLatex(item)}`).join("\n") : "\\item 暂无审计建议";
  const credibilityItems = [
    `\\item 可信度得分：${escapeLatex(credibility?.credibility_score ?? "--")}`,
    `\\item 算法实力得分：${escapeLatex(credibility?.algorithm_strength_score ?? "--")}`,
    `\\item 证据覆盖率：${escapeLatex(credibility?.evidence_coverage ?? "--")}`,
    ...((credibility?.strengths || []).slice(0, 3).map((item) => `\\item 亮点：${escapeLatex(item)}`)),
    ...((credibility?.gaps || []).slice(0, 3).map((item) => `\\item 缺口：${escapeLatex(item)}`)),
  ].join("\n");
  const rationale = escapeLatex(scheme.design_rationale || "");

  return [
    "\\documentclass[11pt]{article}",
    "\\usepackage[utf8]{inputenc}",
    "\\usepackage[a4paper,margin=1in]{geometry}",
    "\\usepackage{hyperref}",
    "\\title{BuildCipher Studio 本地交付文档}",
    "\\author{BuildCipher Studio}",
    `\\date{${escapeLatex(pkg.generated_at || "--")}}`,
    "\\begin{document}",
    "\\maketitle",
    "\\section{执行摘要}",
    `\\textbf{交付编号}: ${escapeLatex(pkg.request_id || "--")}\\\\`,
    `\\textbf{任务编号}: ${escapeLatex(pkg.run_id || "--")}\\\\`,
    `\\textbf{交付状态}: ${escapeLatex(formatDisplayValue({ label: pkg.delivery?.status_label, value: pkg.delivery?.status }))}\\\\`,
    `\\textbf{选中方案}: ${escapeLatex(pkg.delivery?.selected_proposal || "--")}\\\\`,
    `\\textbf{合规得分}: ${escapeLatex(pkg.delivery?.compliance_score ?? "--")}\\\\`,
    `\\textbf{风险得分}: ${escapeLatex(pkg.delivery?.risk_score ?? "--")}\\\\`,
    `\\textbf{行业专家}: ${escapeLatex(appliedSkill?.name || "--")}`,
    "\\section{可信度摘要}",
    "\\begin{itemize}",
    credibilityItems,
    "\\end{itemize}",
    "\\section{最终方案}",
    `\\textbf{方案名称}: ${escapeLatex(scheme.name || "--")}\\\\`,
    `\\textbf{方案类型}: ${escapeLatex(scheme.scheme_type || "--")}\\\\`,
    `\\textbf{安全等级}: ${escapeLatex(scheme.security_level || "--")}\\\\`,
    `\\textbf{综合评分}: ${escapeLatex(scheme.score ?? "--")}`,
    "\\subsection{组件清单}",
    "\\begin{itemize}",
    componentItems,
    "\\end{itemize}",
    "\\subsection{设计理由}",
    rationale || "暂无设计说明",
    "\\section{审计发现}",
    "\\begin{itemize}",
    findingItems,
    "\\end{itemize}",
    "\\section{审计建议}",
    "\\begin{itemize}",
    recommendationItems,
    "\\end{itemize}",
    "\\section{说明}",
    "本文档用于设计交接与评审流程，正式投产前仍需独立密码学验证与安全审计。",
    "\\end{document}",
  ].join("\n");
}
