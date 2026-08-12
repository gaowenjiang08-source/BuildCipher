"""Report builder for MAS execution results."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Tuple

from cipher_genius.api.schemas import MASReportResponse
from cipher_genius.features.exporter import SchemeExporter
from cipher_genius.features.scheme_comparator import SchemeComparator
from cipher_genius.reporting import (
    ReportTemplateManifest,
    display_bool,
    display_scenario,
    display_status,
    display_trust_level,
    get_report_template_registry,
    localize_compliance_report,
    localize_vulnerability_report,
    summarize_compliance,
    summarize_vulnerability,
)


class MASReportService:
    """Generate comprehensive report artifacts from MAS result payload."""

    def __init__(self) -> None:
        self.comparator = SchemeComparator()
        self.exporter = SchemeExporter()
        self.template_registry = get_report_template_registry()

    def generate_report(
        self,
        mas_result: Dict[str, Any],
        scenario: str | None = None,
        include_code: bool = True,
        include_pdf: bool = True,
    ) -> MASReportResponse:
        scenario_name = (scenario or self._infer_scenario(mas_result) or "general").strip().lower()
        selected_scheme = self._pick_selected_scheme_name(mas_result)
        variants = self._extract_variants(mas_result)
        comparison, charts = self._build_comparison(variants)
        deployment_guide = self._build_deployment_guide(mas_result, scenario_name)
        template = self.template_registry.resolve(
            scenario_name,
            self._extract_applied_skill_id(mas_result),
        )
        enterprise_delivery = self._build_enterprise_delivery(
            mas_result=mas_result,
            scenario=scenario_name,
            selected_scheme=selected_scheme,
            deployment_guide=deployment_guide,
            template=template,
        )

        markdown = self._build_markdown(
            mas_result=mas_result,
            scenario=scenario_name,
            selected_scheme=selected_scheme,
            comparison=comparison,
            deployment_guide=deployment_guide,
            template=template,
            enterprise_delivery=enterprise_delivery,
            include_code=include_code,
        )
        latex = self._build_latex(
            mas_result=mas_result,
            scenario=scenario_name,
            selected_scheme=selected_scheme,
            comparison=comparison,
            deployment_guide=deployment_guide,
            template=template,
            enterprise_delivery=enterprise_delivery,
            include_code=include_code,
        )
        html = self._build_html(
            mas_result=mas_result,
            scenario=scenario_name,
            selected_scheme=selected_scheme,
            comparison=comparison,
            deployment_guide=deployment_guide,
            template=template,
            enterprise_delivery=enterprise_delivery,
            include_code=include_code,
        )

        pdf_base64: str | None = None
        pdf_error: str | None = None
        if include_pdf:
            pdf_input = self._build_pdf_input(
                mas_result=mas_result,
                scenario=scenario_name,
                selected_scheme=selected_scheme,
                comparison=comparison,
                deployment_guide=deployment_guide,
            )
            pdf_bytes = self.exporter.generate_pdf_report(pdf_input, include_code=include_code)
            if isinstance(pdf_bytes, bytes) and pdf_bytes.startswith(b"%PDF"):
                pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
            else:
                decoded = (
                    pdf_bytes.decode("utf-8", errors="ignore")
                    if isinstance(pdf_bytes, bytes)
                    else str(pdf_bytes)
                )
                latex_pdf, latex_error = self._compile_latex_pdf(latex)
                if latex_pdf is not None and latex_pdf.startswith(b"%PDF"):
                    pdf_base64 = base64.b64encode(latex_pdf).decode("ascii")
                else:
                    merged_error = " | ".join([item for item in [decoded[:300], latex_error] if item])
                    pdf_error = merged_error[:500] or "PDF generation failed."

        return MASReportResponse(
            generated_at=datetime.now(timezone.utc),
            scenario=scenario_name,
            selected_scheme=selected_scheme,
            template_id=template.id if template is not None else "",
            template_name=template.name if template is not None else "",
            enterprise_delivery=enterprise_delivery,
            html=html,
            markdown=markdown,
            latex=latex,
            comparison=comparison,
            charts=charts,
            deployment_guide=deployment_guide,
            pdf_base64=pdf_base64,
            pdf_error=pdf_error,
        )

    def _infer_scenario(self, mas_result: Dict[str, Any]) -> str:
        spec = mas_result.get("analyst", {}).get("structured_spec", {})
        text_parts = [
            str(spec.get("domain", "")),
            str(spec.get("compliance", "")),
            str(mas_result.get("request_id", "")),
        ]
        text = " ".join(text_parts).lower()
        if any(token in text for token in ["construction", "building", "bim", "ifc", "openbim", "cde", "建筑", "施工", "工地", "工程验收", "图纸"]):
            return "construction"
        return "general"

    def _pick_selected_scheme_name(self, mas_result: Dict[str, Any]) -> str:
        final_scheme = mas_result.get("final_scheme") or {}
        name = str(final_scheme.get("name", "")).strip()
        if name:
            return name
        delivery = mas_result.get("delivery", {})
        return str(delivery.get("selected_proposal", "unknown"))

    def _extract_applied_skill_id(self, mas_result: Dict[str, Any]) -> str | None:
        delivery = mas_result.get("delivery", {}) or {}
        applied_skill = delivery.get("applied_skill", {}) or {}
        skill_id = str(applied_skill.get("id", "")).strip()
        return skill_id or None

    def _extract_variants(self, mas_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        variants: List[Dict[str, Any]] = []
        candidates = mas_result.get("architect", {}).get("candidates", [])
        for candidate in candidates:
            components = candidate.get("components") or []
            component_names = [
                str(comp.get("name"))
                for comp in components
                if isinstance(comp, dict) and comp.get("name")
            ]
            merged_name = " ".join([str(candidate.get("name", "")), " ".join(component_names)]).lower()
            variants.append(
                {
                    "name": candidate.get("name", "unknown"),
                    "type": candidate.get("scheme_type", "unknown"),
                    "key_size": candidate.get("security_level", 0) or 0,
                    "properties": {
                        "quantum_resistant": any(
                            keyword in merged_name for keyword in ["kyber", "dilithium", "sphincs", "falcon", "mceliece"]
                        ),
                        "authenticated": any(
                            token in merged_name for token in ["gcm", "poly1305", "ccm", "aead"]
                        ),
                    },
                }
            )
        return variants

    def _build_comparison(self, variants: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if len(variants) < 2:
            return {"note": "至少需要两个候选方案才能生成对比。"}, {}
        try:
            comparison = self.comparator.compare_schemes(variants)
            charts = self.comparator.generate_comparison_chart(variants)
            return comparison, charts
        except Exception as exc:
            return {"error": str(exc)}, {}

    def _build_deployment_guide(self, mas_result: Dict[str, Any], scenario: str) -> List[str]:
        delivery = mas_result.get("delivery", {})
        compliance = str(mas_result.get("analyst", {}).get("structured_spec", {}).get("compliance", "NIST_CSF"))
        guide = [
            "固定运行时与依赖版本（含 Python/C 工具链），并生成可复现构建清单。",
            "将密钥托管在 HSM/KMS 中，落实轮换制度与服务间严格密钥隔离。",
            "启用结构化审计日志，并通过完整性保护手段防止日志被篡改。",
            "在 CI 中启用安全门禁，包括 SAST、依赖扫描、敏感信息扫描和强制代码评审。",
            "上线前完成面向目标时延与吞吐 SLO 的性能回归测试。",
            f"正式投产前补齐针对 {compliance} 的合规证据映射材料。",
            "采用分阶段灰度发布与回滚预案，持续监控错误预算与密码相关异常。",
        ]
        if scenario == "construction":
            guide.extend(
                [
                    "将模型、图纸、检测记录和签批结论绑定到稳定的版本与证据引用。",
                    "按建设、设计、总包、分包和监理角色验证交付包级最小权限。",
                    "为长期归档保存算法、凭据版本、签批上下文和验签所需元数据。",
                ]
            )
        if delivery.get("status") != "approved":
            guide.append("正式上线前需先关闭仍未解决的审计拒绝项。")
        return guide

    def _extract_evidence_pack(self, mas_result: Dict[str, Any]) -> Dict[str, Any]:
        delivery = mas_result.get("delivery", {}) or {}
        return mas_result.get("evidence_pack") or delivery.get("evidence_pack") or {}

    def _build_evidence_lines(self, evidence_pack: Dict[str, Any], limit: int = 5) -> List[str]:
        items = evidence_pack.get("items") or []
        lines: List[str] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "--"))
            section = str(item.get("section", "")).strip()
            snippet = str(item.get("snippet", "")).strip()
            score = item.get("score", "--")
            doc_type = str(item.get("doc_type", "--"))
            metadata = item.get("metadata") or {}
            clause_code = str(metadata.get("clause_code", "")).strip()
            section_path = metadata.get("section_path") or []
            parent_path = ""
            if isinstance(section_path, list) and len(section_path) > 1:
                parent_path = " > ".join(str(part).strip() for part in section_path[:-1] if str(part).strip())
            section_text = f" / {section}" if section else ""
            clause_text = f" [条款 {clause_code}]" if clause_code and clause_code not in section else ""
            path_text = f"（路径 {parent_path}）" if parent_path else ""
            snippet_text = f"：{snippet}" if snippet else ""
            lines.append(f"[{doc_type}] {title}{section_text}{clause_text}{path_text}（相关度 {score}）{snippet_text}")
        return lines

    def _build_enterprise_delivery(
        self,
        mas_result: Dict[str, Any],
        scenario: str,
        selected_scheme: str,
        deployment_guide: List[str],
        template: ReportTemplateManifest | None,
    ) -> Dict[str, Any]:
        if template is None:
            return {}

        analyst = mas_result.get("analyst", {}) or {}
        delivery = mas_result.get("delivery", {}) or {}
        final_scheme = mas_result.get("final_scheme") or {}
        credibility = mas_result.get("credibility_assessment") or delivery.get("credibility_assessment") or {}
        compliance_report = mas_result.get("compliance_report", {}) or {}
        vulnerability_report = mas_result.get("vulnerability_report", {}) or {}
        evidence_pack = self._extract_evidence_pack(mas_result)
        applied_skill = delivery.get("applied_skill") or {}
        spec = analyst.get("structured_spec", {}) or {}
        clarifications = analyst.get("clarifications") or []
        assumptions = analyst.get("assumptions") or []
        latest_audit = (mas_result.get("auditor_rounds") or [{}])[-1] or {}

        sections: List[Dict[str, Any]] = []
        for section in template.sections:
            items = self._build_enterprise_section_items(
                section_id=section.id,
                scenario=scenario,
                selected_scheme=selected_scheme,
                spec=spec,
                analyst=analyst,
                delivery=delivery,
                final_scheme=final_scheme,
                credibility=credibility,
                compliance_report=compliance_report,
                vulnerability_report=vulnerability_report,
                evidence_pack=evidence_pack,
                applied_skill=applied_skill,
                clarifications=clarifications,
                assumptions=assumptions,
                latest_audit=latest_audit,
                deployment_guide=deployment_guide,
                template=template,
            )
            sections.append(
                {
                    "id": section.id,
                    "title": section.title,
                    "purpose": section.purpose,
                    "items": items,
                }
            )

        return {
            "template_id": template.id,
            "template_name": template.name,
            "summary": template.summary,
            "scenario": scenario,
            "selected_scheme": selected_scheme,
            "target_audiences": template.target_audiences,
            "control_focus": template.control_focus,
            "evidence_checklist": template.evidence_checklist,
            "evidence_pack": evidence_pack,
            "sections": sections,
        }

    def _build_enterprise_section_items(
        self,
        *,
        section_id: str,
        scenario: str,
        selected_scheme: str,
        spec: Dict[str, Any],
        analyst: Dict[str, Any],
        delivery: Dict[str, Any],
        final_scheme: Dict[str, Any],
        credibility: Dict[str, Any],
        compliance_report: Dict[str, Any],
        vulnerability_report: Dict[str, Any],
        evidence_pack: Dict[str, Any],
        applied_skill: Dict[str, Any],
        clarifications: List[Dict[str, Any]],
        assumptions: List[str],
        latest_audit: Dict[str, Any],
        deployment_guide: List[str],
        template: ReportTemplateManifest,
    ) -> List[str]:
        components = final_scheme.get("components") or []
        component_names = [
            str(item.get("name"))
            for item in components
            if isinstance(item, dict) and item.get("name")
        ]
        sources = credibility.get("sources") or []
        output_focus = applied_skill.get("output_focus") or []
        target_users = applied_skill.get("target_users") or template.target_audiences
        compliance_target = str(spec.get("compliance", "NIST_CSF"))
        domain = str(spec.get("domain", scenario))
        platform = str(spec.get("platform", "--"))
        resource_level = str(spec.get("resource_level", "--"))
        evidence_lines = self._build_evidence_lines(evidence_pack, limit=3)

        if section_id == "business_context":
            return [
                f"交付场景：{self._display_scenario(scenario)}；业务域：{domain}；主要合规目标：{compliance_target}。",
                f"选定方案：{selected_scheme}；已应用专家模式：{applied_skill.get('name', '--')}。",
                f"场景适配说明：{delivery.get('scenario_fit', '--')}。",
                f"平台与资源约束：平台={platform}；资源等级={resource_level}。",
            ]

        if section_id == "regulatory_mapping":
            items = [
                f"当前主控焦点：{', '.join(template.control_focus) if template.control_focus else compliance_target}。",
                f"合规摘要：{compliance_report.get('summary_text', summarize_compliance(compliance_report))}",
                f"交付状态：{self._display_status(delivery.get('status'))}；合规得分：{delivery.get('compliance_score', '--')}；风险得分：{delivery.get('risk_score', '--')}。",
            ]
            items.extend([f"专家模式输出重点：{item}" for item in output_focus[:2]])
            return items

        if section_id == "data_boundaries":
            items = [
                f"目标使用者 / 审阅角色：{', '.join(target_users) if target_users else '--'}。",
                f"访问隔离应保持与场景匹配的业务边界：{delivery.get('scenario_fit', '--')}。",
            ]
            if output_focus:
                items.append(f"本次建议重点强调：{output_focus[0]}。")
            if component_names:
                items.append(f"当前涉及该边界的核心组件：{', '.join(component_names[:6])}。")
            return items

        if section_id == "crypto_controls":
            items = [f"部署建议：{item}" for item in deployment_guide[:4]]
            if component_names:
                items.append(f"选定方案的核心组件：{', '.join(component_names[:6])}。")
            items.extend([f"专家模式强调：{item}" for item in output_focus[:2]])
            return items

        if section_id == "evidence_validation":
            items = [
                f"可信等级={credibility.get('trust_level_label', self._display_trust_level(credibility.get('trust_level', '--')))}；证据覆盖率={credibility.get('evidence_coverage', '--')}；审计就绪度={credibility.get('audit_readiness', '--')}。",
                f"当前 MAS 结果附带证据来源数量：{len(sources)}。",
            ]
            items.extend([f"检查项：{item}" for item in template.evidence_checklist])
            items.extend([f"引用依据：{item}" for item in evidence_lines])
            return items

        if section_id == "open_questions":
            items = [f"当前假设：{item}" for item in assumptions[:3]]
            items.extend(
                [
                    f"待澄清问题：{item.get('question', '--')}"
                    for item in clarifications[:4]
                    if isinstance(item, dict)
                ]
            )
            if not items:
                items.extend([f"建议向业务方确认：{item}" for item in template.open_question_prompts])
            return items or ["当前分析阶段未检测到显式开放问题。"]

        if section_id == "residual_risks":
            items = [
                f"下一步动作：{delivery.get('next_action', '--')}。",
                f"漏洞摘要：{vulnerability_report.get('summary_text', summarize_vulnerability(vulnerability_report.get('summary')))}",
                f"当前结构化引用数：{len(evidence_pack.get('items') or [])}。",
            ]
            findings = latest_audit.get("key_findings") or []
            items.extend([f"最近一轮审计发现：{item}" for item in findings[:3]])
            gaps = credibility.get("gaps") or []
            items.extend([f"可信度缺口：{item}" for item in gaps[:2]])
            return items

        return [f"模板摘要：{template.summary}"]

    def _build_markdown(
        self,
        mas_result: Dict[str, Any],
        scenario: str,
        selected_scheme: str,
        comparison: Dict[str, Any],
        deployment_guide: List[str],
        template: ReportTemplateManifest | None,
        enterprise_delivery: Dict[str, Any],
        include_code: bool,
    ) -> str:
        delivery = mas_result.get("delivery", {})
        compliance_report = localize_compliance_report(mas_result.get("compliance_report", {}) or {})
        vulnerability_report = localize_vulnerability_report(mas_result.get("vulnerability_report", {}) or {})
        final_scheme = mas_result.get("final_scheme") or {}
        scoring = delivery.get("scoring") or {}
        credibility = mas_result.get("credibility_assessment") or delivery.get("credibility_assessment") or {}
        evidence_pack = self._extract_evidence_pack(mas_result)
        evidence_lines = self._build_evidence_lines(evidence_pack, limit=6)
        applied_skill = delivery.get("applied_skill") or {}
        table_rows = comparison.get("side_by_side_table") or []
        compliance_recommendations = [
            item.get("recommendation")
            for item in (compliance_report.get("recommendations") or [])[:2]
            if isinstance(item, dict) and item.get("recommendation")
        ]
        vulnerability_actions = [
            item.get("action")
            for item in (vulnerability_report.get("recommendations") or [])[:2]
            if isinstance(item, dict) and item.get("action")
        ]

        lines: List[str] = [
            f"# BuildTrust 企业交付报告（{self._display_scenario(scenario)}）",
            "",
            "## 执行摘要",
            f"- 请求 ID：{mas_result.get('request_id', '--')}",
            f"- 运行 ID：{mas_result.get('run_id', '--')}",
            f"- 选定方案：{selected_scheme}",
            f"- 交付状态：{self._display_status(delivery.get('status'))}",
            f"- 已应用专家模式：{applied_skill.get('name', '--')}",
            f"- 合规得分：{delivery.get('compliance_score', '--')}",
            f"- 风险得分：{delivery.get('risk_score', '--')}",
            "",
            "## 方案选择依据",
            f"- 选中的候选提案：{delivery.get('selected_proposal', '--')}",
            f"- 下一步动作：{delivery.get('next_action', '--')}",
            f"- 场景适配说明：{delivery.get('scenario_fit', '--')}",
            "",
            "## 评分概览",
            f"- 安全得分：{scoring.get('security_score', '--')}",
            f"- 性能得分：{scoring.get('performance_score', '--')}",
            f"- 复杂度得分：{scoring.get('complexity_score', '--')}",
            f"- 标准化得分：{scoring.get('standardization_score', '--')}",
            f"- 综合得分：{scoring.get('overall_score', '--')}",
            f"- 是否具备后量子属性：{scoring.get('quantum_resistant_label', self._display_bool(scoring.get('quantum_resistant', '--')))}",
            "",
            "## 可信度概览",
            f"- 可信度得分：{credibility.get('credibility_score', '--')}",
            f"- 算法实力得分：{credibility.get('algorithm_strength_score', '--')}",
            f"- 证据覆盖率：{credibility.get('evidence_coverage', '--')}",
            f"- 审计就绪度：{credibility.get('audit_readiness', '--')}",
            f"- 可信等级：{credibility.get('trust_level_label', self._display_trust_level(credibility.get('trust_level', '--')))}",
            "",
            "## 候选方案对比",
        ]

        if not table_rows:
            lines.append("- 当前无可用对比表。")
        else:
            lines.append("| 方案 | 安全 | 性能 | 复杂度 | 标准化 | 综合 | 后量子 |")
            lines.append("|---|---:|---:|---:|---:|---:|---|")
            for row in table_rows:
                lines.append(
                    "| {name} | {security_score} | {performance_score} | {complexity_score} | {standardization_score} | {overall_score} | {quantum_resistant} |".format(
                        name=row.get("name", "--"),
                        security_score=row.get("security_score", "--"),
                        performance_score=row.get("performance_score", "--"),
                        complexity_score=row.get("complexity_score", "--"),
                        standardization_score=row.get("standardization_score", "--"),
                        overall_score=row.get("overall_score", "--"),
                        quantum_resistant=row.get("quantum_resistant_label", self._display_bool(row.get("quantum_resistant", "--"))),
                    )
                )

        lines.extend(
            [
                "",
                "## 合规与风险摘要",
                f"- 合规摘要：{compliance_report.get('summary_text', summarize_compliance(compliance_report))}",
                f"- 漏洞摘要：{vulnerability_report.get('summary_text', summarize_vulnerability(vulnerability_report.get('summary')))}",
                "",
                "## 证据摘要",
            ]
        )
        if compliance_recommendations:
            lines.insert(len(lines) - 2, f"- 合规建议：{compliance_recommendations[0]}")
        if vulnerability_actions:
            lines.insert(len(lines) - 2, f"- 漏洞处置建议：{vulnerability_actions[0]}")

        sources = credibility.get("sources") or []
        if not sources:
            lines.append("- 当前未附带显式证据来源。")
        else:
            for source in sources[:6]:
                lines.append(
                    f"- [{source.get('type', '--')}] {source.get('component', '--')}: {source.get('title', '--')}（{source.get('year', '--')}）"
                )

        lines.extend(["", "## 引用依据摘要"])
        if not evidence_lines:
            lines.append("- 当前未生成结构化引用依据。")
        else:
            lines.extend([f"- {item}" for item in evidence_lines])

        if enterprise_delivery:
            lines.extend(
                [
                    "",
                    "## 企业交付模板",
                    f"- 模板 ID：{enterprise_delivery.get('template_id', '--')}",
                    f"- 模板名称：{enterprise_delivery.get('template_name', '--')}",
                    f"- 模板摘要：{enterprise_delivery.get('summary', '--')}",
                    "",
                ]
            )
            for section in enterprise_delivery.get("sections", []):
                lines.append(f"### {section.get('title', '--')}")
                purpose = str(section.get("purpose", "")).strip()
                if purpose:
                    lines.append(f"- 目的：{purpose}")
                items = section.get("items") or []
                if not items:
                    lines.append("- 未生成条目。")
                else:
                    lines.extend([f"- {item}" for item in items])
                lines.append("")

        lines.extend(
            [
                "",
                "## 生产部署建议",
            ]
        )
        lines.extend([f"- {item}" for item in deployment_guide])

        if include_code:
            implementation = final_scheme.get("implementation") or {}
            lines.extend(
                [
                    "",
                    "## 可执行代码说明",
                    "- Python（最终修正版本）：",
                    "```python",
                    str(implementation.get("python") or "# no python code"),
                    "```",
                    "",
                    "- C（最终修正版本）：",
                    "```c",
                    str(implementation.get("c") or "/* no c code */"),
                    "```",
                ]
            )

        return "\n".join(lines)

    def _build_html(
        self,
        mas_result: Dict[str, Any],
        scenario: str,
        selected_scheme: str,
        comparison: Dict[str, Any],
        deployment_guide: List[str],
        template: ReportTemplateManifest | None,
        enterprise_delivery: Dict[str, Any],
        include_code: bool,
    ) -> str:
        delivery = mas_result.get("delivery", {})
        scoring = delivery.get("scoring") or {}
        credibility = mas_result.get("credibility_assessment") or delivery.get("credibility_assessment") or {}
        evidence_pack = self._extract_evidence_pack(mas_result)
        evidence_lines = self._build_evidence_lines(evidence_pack, limit=6)
        applied_skill = delivery.get("applied_skill") or {}
        final_scheme = mas_result.get("final_scheme") or {}
        implementation = final_scheme.get("implementation") or {}
        table_rows = comparison.get("side_by_side_table") or []
        compliance_report = localize_compliance_report(mas_result.get("compliance_report", {}) or {})
        vulnerability_report = localize_vulnerability_report(mas_result.get("vulnerability_report", {}) or {})
        compliance_recommendations = [
            item.get("recommendation")
            for item in (compliance_report.get("recommendations") or [])[:2]
            if isinstance(item, dict) and item.get("recommendation")
        ]
        vulnerability_actions = [
            item.get("action")
            for item in (vulnerability_report.get("recommendations") or [])[:2]
            if isinstance(item, dict) and item.get("action")
        ]

        summary_rows = [
            ("请求 ID", mas_result.get("request_id", "--")),
            ("运行 ID", mas_result.get("run_id", "--")),
            ("场景", self._display_scenario(scenario)),
            ("选定方案", selected_scheme),
            ("交付状态", delivery.get("status_label", self._display_status(delivery.get("status", "--")))),
            ("已应用专家模式", applied_skill.get("name", "--")),
            ("合规得分", delivery.get("compliance_score", "--")),
            ("风险得分", delivery.get("risk_score", "--")),
        ]
        score_rows = [
            ("安全得分", scoring.get("security_score", "--")),
            ("性能得分", scoring.get("performance_score", "--")),
            ("复杂度得分", scoring.get("complexity_score", "--")),
            ("标准化得分", scoring.get("standardization_score", "--")),
            ("综合得分", scoring.get("overall_score", "--")),
            ("后量子属性", scoring.get("quantum_resistant_label", self._display_bool(scoring.get("quantum_resistant", "--")))),
        ]
        credibility_rows = [
            ("可信度得分", credibility.get("credibility_score", "--")),
            ("算法实力", credibility.get("algorithm_strength_score", "--")),
            ("证据覆盖率", credibility.get("evidence_coverage", "--")),
            ("审计就绪度", credibility.get("audit_readiness", "--")),
            ("可信等级", credibility.get("trust_level_label", self._display_trust_level(credibility.get("trust_level", "--")))),
        ]
        evidence_html = (
            "<ul>"
            + "".join(f"<li>{self._escape_html(item)}</li>" for item in evidence_lines)
            + "</ul>"
            if evidence_lines
            else "<p class='muted'>当前未生成结构化引用依据。</p>"
        )

        def kv_table(items: List[tuple[str, Any]]) -> str:
            lines = ["<table class='kv'>", "<tbody>"]
            for key, value in items:
                lines.append(
                    f"<tr><th>{self._escape_html(str(key))}</th><td>{self._escape_html(str(value))}</td></tr>"
                )
            lines.extend(["</tbody>", "</table>"])
            return "\n".join(lines)

        comparison_html = "<p class='muted'>当前无可用对比表。</p>"
        if table_rows:
            header = (
                "<tr><th>方案</th><th>安全</th><th>性能</th>"
                "<th>复杂度</th><th>标准化</th><th>综合</th><th>后量子</th></tr>"
            )
            rows = []
            for row in table_rows:
                rows.append(
                    "<tr>"
                    f"<td>{self._escape_html(str(row.get('name', '--')))}</td>"
                    f"<td>{self._escape_html(str(row.get('security_score', '--')))}</td>"
                    f"<td>{self._escape_html(str(row.get('performance_score', '--')))}</td>"
                    f"<td>{self._escape_html(str(row.get('complexity_score', '--')))}</td>"
                    f"<td>{self._escape_html(str(row.get('standardization_score', '--')))}</td>"
                    f"<td>{self._escape_html(str(row.get('overall_score', '--')))}</td>"
                    f"<td>{self._escape_html(str(row.get('quantum_resistant_label', self._display_bool(row.get('quantum_resistant', '--')))))}</td>"
                    "</tr>"
                )
            comparison_html = (
                "<table class='cmp'><thead>"
                + header
                + "</thead><tbody>"
                + "\n".join(rows)
                + "</tbody></table>"
            )

        guide_html = "<ul>" + "".join(
            f"<li>{self._escape_html(item)}</li>" for item in deployment_guide
        ) + "</ul>"

        enterprise_html = ""
        if enterprise_delivery:
            section_blocks = []
            for section in enterprise_delivery.get("sections", []):
                purpose = str(section.get("purpose", "")).strip()
                purpose_html = (
                    f"<p class='muted'>{self._escape_html(purpose)}</p>" if purpose else ""
                )
                items = section.get("items") or []
                items_html = "<ul>" + "".join(
                    f"<li>{self._escape_html(str(item))}</li>" for item in items
                ) + "</ul>"
                section_blocks.append(
                    "<div class='enterprise-block'>"
                    f"<h3>{self._escape_html(str(section.get('title', '--')))}</h3>"
                    f"{purpose_html}"
                    f"{items_html}"
                    "</div>"
                )
            enterprise_html = (
                "<section>"
                "<h2>企业交付模板</h2>"
                f"<p><strong>模板名称：</strong> {self._escape_html(str(enterprise_delivery.get('template_name', '--')))}</p>"
                f"<p class='muted'>{self._escape_html(str(enterprise_delivery.get('summary', '--')))}</p>"
                + "".join(section_blocks)
                + "</section>"
            )

        code_html = ""
        if include_code:
            code_html = (
                "<section><h2>可执行代码说明</h2>"
                "<h3>Python</h3>"
                f"<pre>{self._escape_html(str(implementation.get('python') or '# no python code'))}</pre>"
                "<h3>C</h3>"
                f"<pre>{self._escape_html(str(implementation.get('c') or '/* no c code */'))}</pre>"
                "</section>"
            )

        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BuildTrust 企业交付报告</title>
  <style>
    body {{ font-family: 'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', 'Segoe UI', sans-serif; margin: 24px; color: #0f172a; background: #f8fafc; }}
    h1, h2, h3 {{ margin: 0 0 12px; }}
    section {{ margin: 18px 0; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; }}
    .muted {{ color: #64748b; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 8px; text-align: left; font-size: 13px; }}
    th {{ background: #f1f5f9; }}
    .kv th {{ width: 220px; }}
    pre {{ background: #0f172a; color: #f8fafc; padding: 10px; border-radius: 8px; overflow: auto; font-size: 12px; }}
    ul {{ margin: 0; padding-left: 20px; }}
    .meta {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .enterprise-block {{ border-top: 1px dashed #cbd5e1; padding-top: 10px; margin-top: 10px; }}
  </style>
</head>
<body>
  <h1>BuildTrust 企业交付报告</h1>
  <p class="muted">生成时间：{self._escape_html(datetime.now(timezone.utc).isoformat())}</p>
  <section>
    <h2>执行摘要</h2>
    <div class="meta">
      <div>{kv_table(summary_rows)}</div>
      <div>{kv_table(score_rows)}</div>
    </div>
    <p><strong>场景适配说明：</strong> {self._escape_html(str(delivery.get("scenario_fit", "--")))}</p>
    <p><strong>下一步动作：</strong> {self._escape_html(str(delivery.get("next_action", "--")))}</p>
  </section>
  <section>
    <h2>可信度概览</h2>
    <div>{kv_table(credibility_rows)}</div>
    <ul>
      {"".join(
          f"<li>{self._escape_html(str(item.get('component', '--')))}: {self._escape_html(str(item.get('title', '--')))}</li>"
          for item in (credibility.get("sources") or [])[:6]
      )}
    </ul>
  </section>
  <section>
    <h2>引用依据摘要</h2>
    {evidence_html}
  </section>
  <section>
    <h2>合规与风险摘要</h2>
    <p><strong>合规摘要：</strong> {self._escape_html(compliance_report.get("summary_text", summarize_compliance(compliance_report)))}</p>
    <p><strong>漏洞摘要：</strong> {self._escape_html(vulnerability_report.get("summary_text", summarize_vulnerability(vulnerability_report.get("summary"))))}</p>
    <ul>
      {"".join(f"<li>合规建议：{self._escape_html(str(item))}</li>" for item in compliance_recommendations[:1])}
      {"".join(f"<li>漏洞处置建议：{self._escape_html(str(item))}</li>" for item in vulnerability_actions[:1])}
    </ul>
  </section>
  {enterprise_html}
  <section>
    <h2>候选方案对比</h2>
    {comparison_html}
  </section>
  <section>
    <h2>生产部署建议</h2>
    {guide_html}
  </section>
  {code_html}
</body>
</html>
"""

    def _build_latex(
        self,
        mas_result: Dict[str, Any],
        scenario: str,
        selected_scheme: str,
        comparison: Dict[str, Any],
        deployment_guide: List[str],
        template: ReportTemplateManifest | None,
        enterprise_delivery: Dict[str, Any],
        include_code: bool,
    ) -> str:
        delivery = mas_result.get("delivery", {})
        scoring = delivery.get("scoring") or {}
        credibility = mas_result.get("credibility_assessment") or delivery.get("credibility_assessment") or {}
        evidence_pack = self._extract_evidence_pack(mas_result)
        evidence_lines = self._build_evidence_lines(evidence_pack, limit=6)
        applied_skill = delivery.get("applied_skill") or {}
        table_rows = comparison.get("side_by_side_table") or []
        final_scheme = mas_result.get("final_scheme") or {}
        implementation = final_scheme.get("implementation") or {}
        compliance_report = localize_compliance_report(mas_result.get("compliance_report", {}) or {})
        vulnerability_report = localize_vulnerability_report(mas_result.get("vulnerability_report", {}) or {})
        compliance_recommendations = [
            item.get("recommendation")
            for item in (compliance_report.get("recommendations") or [])[:2]
            if isinstance(item, dict) and item.get("recommendation")
        ]
        vulnerability_actions = [
            item.get("action")
            for item in (vulnerability_report.get("recommendations") or [])[:2]
            if isinstance(item, dict) and item.get("action")
        ]

        lines: List[str] = [
            r"\documentclass{ctexart}",
            r"\usepackage{longtable}",
            r"\usepackage{geometry}",
            r"\usepackage{listings}",
            r"\geometry{a4paper, margin=1in}",
            rf"\title{{BuildTrust 企业交付报告（{self._escape_latex(self._display_scenario(scenario))}）}}",
            r"\author{BuildTrust}",
            rf"\date{{{datetime.now().strftime('%Y-%m-%d')}}}",
            r"\begin{document}",
            r"\maketitle",
            r"\section{执行摘要}",
            rf"选定方案：{self._escape_latex(selected_scheme)}\\",
            rf"交付状态：{self._escape_latex(str(delivery.get('status_label', self._display_status(delivery.get('status', '--')))))}\\",
            rf"已应用专家模式：{self._escape_latex(str(applied_skill.get('name', '--')))}\\",
            rf"合规得分：{self._escape_latex(str(delivery.get('compliance_score', '--')))}\\",
            rf"风险得分：{self._escape_latex(str(delivery.get('risk_score', '--')))}\\",
            r"\section{评分概览}",
            r"\begin{itemize}",
            rf"\item 安全得分：{self._escape_latex(str(scoring.get('security_score', '--')))}",
            rf"\item 性能得分：{self._escape_latex(str(scoring.get('performance_score', '--')))}",
            rf"\item 复杂度得分：{self._escape_latex(str(scoring.get('complexity_score', '--')))}",
            rf"\item 标准化得分：{self._escape_latex(str(scoring.get('standardization_score', '--')))}",
            rf"\item 综合得分：{self._escape_latex(str(scoring.get('overall_score', '--')))}",
            rf"\item 后量子属性：{self._escape_latex(str(scoring.get('quantum_resistant_label', self._display_bool(scoring.get('quantum_resistant', '--')))))}",
            r"\end{itemize}",
            r"\section{可信度概览}",
            r"\begin{itemize}",
            rf"\item 可信度得分：{self._escape_latex(str(credibility.get('credibility_score', '--')))}",
            rf"\item 算法实力得分：{self._escape_latex(str(credibility.get('algorithm_strength_score', '--')))}",
            rf"\item 证据覆盖率：{self._escape_latex(str(credibility.get('evidence_coverage', '--')))}",
            rf"\item 审计就绪度：{self._escape_latex(str(credibility.get('audit_readiness', '--')))}",
            rf"\item 可信等级：{self._escape_latex(str(credibility.get('trust_level_label', self._display_trust_level(str(credibility.get('trust_level', '--'))))))}",
            r"\end{itemize}",
            r"\section{引用依据摘要}",
            r"\begin{itemize}",
        ]
        if evidence_lines:
            lines.extend([rf"\item {self._escape_latex(str(item))}" for item in evidence_lines])
        else:
            lines.append(r"\item 当前未生成结构化引用依据。")
        lines.extend(
            [
                r"\end{itemize}",
            r"\section{合规与风险摘要}",
            rf"合规摘要：{self._escape_latex(compliance_report.get('summary_text', summarize_compliance(compliance_report)))}\\",
            rf"漏洞摘要：{self._escape_latex(vulnerability_report.get('summary_text', summarize_vulnerability(vulnerability_report.get('summary'))))}\\",
            r"\begin{itemize}",
            ]
        )
        for item in compliance_recommendations[:1]:
            lines.append(rf"\item 合规建议：{self._escape_latex(str(item))}")
        for item in vulnerability_actions[:1]:
            lines.append(rf"\item 漏洞处置建议：{self._escape_latex(str(item))}")
        lines.append(r"\end{itemize}")
        lines.append(r"\section{候选方案对比}")

        if table_rows:
            lines.extend(
                [
                    r"\begin{longtable}{|l|c|c|c|c|c|c|}",
                    r"\hline",
                    r"方案 & 安全 & 性能 & 复杂度 & 标准化 & 综合 & 后量子 \\ \hline",
                ]
            )
            for row in table_rows:
                lines.append(
                    f"{self._escape_latex(str(row.get('name', '--')))} & "
                    f"{self._escape_latex(str(row.get('security_score', '--')))} & "
                    f"{self._escape_latex(str(row.get('performance_score', '--')))} & "
                    f"{self._escape_latex(str(row.get('complexity_score', '--')))} & "
                    f"{self._escape_latex(str(row.get('standardization_score', '--')))} & "
                    f"{self._escape_latex(str(row.get('overall_score', '--')))} & "
                    f"{self._escape_latex(str(row.get('quantum_resistant_label', self._display_bool(row.get('quantum_resistant', '--')))))} \\\\ \\hline"
                )
            lines.append(r"\end{longtable}")
        else:
            lines.append("当前无可用对比数据。")

        lines.extend([r"\section{生产部署建议}", r"\begin{itemize}"])
        lines.extend([rf"\item {self._escape_latex(item)}" for item in deployment_guide])
        lines.append(r"\end{itemize}")

        source_lines = credibility.get("sources") or []
        if source_lines:
            lines.extend([r"\section{证据摘要}", r"\begin{itemize}"])
            for item in source_lines[:6]:
                lines.append(
                    rf"\item {self._escape_latex(str(item.get('component', '--')))}: {self._escape_latex(str(item.get('title', '--')))}"
                )
            lines.append(r"\end{itemize}")

        if enterprise_delivery:
            lines.extend(
                [
                    r"\section{企业交付模板}",
                    rf"模板名称：{self._escape_latex(str(enterprise_delivery.get('template_name', '--')))}\\",
                    self._escape_latex(str(enterprise_delivery.get("summary", "--"))),
                ]
            )
            for section in enterprise_delivery.get("sections", []):
                lines.append(rf"\subsection{{{self._escape_latex(str(section.get('title', '--')))}}}")
                purpose = str(section.get("purpose", "")).strip()
                if purpose:
                    lines.append(self._escape_latex(purpose))
                items = section.get("items") or []
                lines.append(r"\begin{itemize}")
                if not items:
                    lines.append(r"\item 未生成条目。")
                else:
                    lines.extend([rf"\item {self._escape_latex(str(item))}" for item in items])
                lines.append(r"\end{itemize}")

        if include_code:
            lines.extend(
                [
                    r"\section{Python 代码}",
                    r"\begin{lstlisting}[language=Python]",
                    str(implementation.get("python") or "# no python code"),
                    r"\end{lstlisting}",
                    r"\section{C 代码}",
                    r"\begin{lstlisting}[language=C]",
                    str(implementation.get("c") or "/* no c code */"),
                    r"\end{lstlisting}",
                ]
            )

        lines.append(r"\end{document}")
        return "\n".join(lines)

    def _build_pdf_input(
        self,
        mas_result: Dict[str, Any],
        scenario: str,
        selected_scheme: str,
        comparison: Dict[str, Any],
        deployment_guide: List[str],
    ) -> Dict[str, Any]:
        delivery = mas_result.get("delivery", {})
        scoring = delivery.get("scoring") or {}
        table_rows = comparison.get("side_by_side_table") or []
        best_row = table_rows[0] if table_rows else {}
        impl = (mas_result.get("final_scheme") or {}).get("implementation") or {}
        algorithms = {"python": impl.get("python", ""), "c": impl.get("c", "")}
        return {
            "name": f"{selected_scheme}（{self._display_scenario(scenario)}）",
            "type": "mas_delivery",
            "security_level": (mas_result.get("final_scheme") or {}).get("security_level", "N/A"),
            "description": (
                f"场景={self._display_scenario(scenario)}，交付状态={delivery.get('status_label', self._display_status(delivery.get('status', '--')))}，"
                f"选中提案={delivery.get('selected_proposal', '--')}，综合表现最佳候选={best_row.get('name', '--')}"
            ),
            "parameters": {
                "合规得分": delivery.get("compliance_score", "--"),
                "风险得分": delivery.get("risk_score", "--"),
                "综合得分": scoring.get("overall_score", "--"),
                "后量子属性": scoring.get("quantum_resistant_label", self._display_bool(scoring.get("quantum_resistant", "--"))),
            },
            "properties": {
                "生产部署建议": " | ".join(deployment_guide[:6]),
                "场景适配说明": delivery.get("scenario_fit", "--"),
            },
            "security_analysis": {
                "审计发现": mas_result.get("auditor_rounds", []),
                "建议项": deployment_guide,
            },
            "algorithms": algorithms,
        }

    def _display_scenario(self, scenario: str | None) -> str:
        return display_scenario(scenario)

    def _display_status(self, status: Any) -> str:
        return display_status(status)

    def _display_trust_level(self, trust_level: Any) -> str:
        return display_trust_level(trust_level)

    def _display_bool(self, value: Any) -> str:
        return display_bool(value)

    def _escape_html(self, text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _escape_latex(self, text: str) -> str:
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        result = str(text)
        for source, target in replacements.items():
            result = result.replace(source, target)
        return result

    def _compile_latex_pdf(self, latex_content: str) -> Tuple[bytes | None, str | None]:
        compilers = ["xelatex", "lualatex", "pdflatex"]
        try:
            with tempfile.TemporaryDirectory(prefix="buildtrust_report_") as tmpdir:
                tex_path = os.path.join(tmpdir, "report.tex")
                with open(tex_path, "w", encoding="utf-8") as handle:
                    handle.write(latex_content)

                last_error: str | None = None
                for tex_compiler in compilers:
                    cmd = [
                        tex_compiler,
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "report.tex",
                    ]
                    try:
                        proc = subprocess.run(
                            cmd,
                            cwd=tmpdir,
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                    except FileNotFoundError:
                        last_error = f"{tex_compiler} not found on system."
                        continue

                    if proc.returncode != 0:
                        tail = (proc.stderr or proc.stdout or "").splitlines()[-8:]
                        last_error = f"LaTeX PDF build failed with {tex_compiler}: " + " | ".join(tail)
                        continue

                    pdf_path = os.path.join(tmpdir, "report.pdf")
                    if not os.path.exists(pdf_path):
                        last_error = f"LaTeX PDF build with {tex_compiler} finished but report.pdf not found."
                        continue

                    with open(pdf_path, "rb") as handle:
                        return handle.read(), None

                return None, last_error or "No LaTeX compiler available."
        except Exception as exc:
            return None, f"LaTeX PDF build error: {exc}"
