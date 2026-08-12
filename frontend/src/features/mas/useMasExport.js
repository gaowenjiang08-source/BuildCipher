import { generateMasReport } from "../../api/client";
import {
  buildLatexExport,
  buildMarkdownExport,
  downloadTextFile,
  fileSafeName,
  timestampSlug,
} from "./exportHelpers";

export default function useMasExport({
  deliveryPackage,
  result,
  structuredSpec,
  settings,
  setNotice,
  setError,
}) {
  async function exportDelivery(formatId) {
    if (!deliveryPackage) {
      setError("暂无可导出的交付包，请先运行 MAS。");
      return;
    }

    const baseName = fileSafeName(deliveryPackage.final_scheme?.name || "buildtrust_delivery");
    const stamp = timestampSlug();

    if (formatId === "json") {
      downloadTextFile(`${baseName}_${stamp}.json`, JSON.stringify(deliveryPackage, null, 2), "application/json;charset=utf-8");
      setNotice("已导出 JSON 交付包");
      return;
    }

    if (formatId === "md") {
      downloadTextFile(`${baseName}_${stamp}.md`, buildMarkdownExport(deliveryPackage), "text/markdown;charset=utf-8");
      setNotice("已导出 Markdown 文档");
      return;
    }

    if (formatId === "tex") {
      downloadTextFile(`${baseName}_${stamp}.tex`, buildLatexExport(deliveryPackage), "text/plain;charset=utf-8");
      setNotice("已导出 LaTeX 文档");
      return;
    }

    if (formatId === "html") {
      try {
        const report = await generateMasReport(
          {
            mas_result: result,
            scenario: structuredSpec?.domain || "construction",
            include_code: true,
            include_pdf: false,
          },
          settings
        );
        if (report?.html) {
          downloadTextFile(`${baseName}_${stamp}.html`, report.html, "text/html;charset=utf-8");
          setNotice("已导出完整 HTML 报告");
          return;
        }
        throw new Error("后端未返回 HTML 报告内容");
      } catch (err) {
        setError(err.message || "HTML 报告导出失败");
        return;
      }
    }

    setError(`不支持的导出格式：${formatId}`);
  }

  return {
    exportDelivery,
  };
}
