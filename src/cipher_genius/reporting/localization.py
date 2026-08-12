"""Chinese-first labels and delivery-localization helpers."""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List

STATUS_LABELS = {
    "approved": "已通过审计",
    "best_effort": "尽力交付",
    "rejected": "未通过审计",
    "needs_clarification": "需要补充澄清",
    "halted": "已暂停",
    "pass": "通过",
    "reject": "拒绝",
    "retry": "重试中",
    "hardened": "已加固",
    "done": "已完成",
    "fallback": "回退模式",
    "failed": "失败",
    "passed": "通过",
    "skipped": "已跳过",
    "unknown": "未知",
    "--": "--",
}

TRUST_LEVEL_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
    "unknown": "未知",
    "--": "--",
}

SEVERITY_LABELS = {
    "critical": "严重",
    "high": "高",
    "medium": "中",
    "low": "低",
    "info": "提示",
    "--": "--",
}

PRIORITY_LABELS = {
    "critical": "紧急",
    "high": "高",
    "medium": "中",
    "low": "低",
    "--": "--",
}

COMPLIANCE_STATUS_LABELS = {
    "compliant": "符合要求",
    "non_compliant": "未符合要求",
    "partial": "部分符合",
    "not_applicable": "不适用",
    "ready": "可进入认证准备",
    "not_ready": "暂不具备认证准备条件",
    "Compliant": "符合要求",
    "Non-Compliant": "未符合要求",
    "Ready": "可进入认证准备",
    "Not Ready": "暂不具备认证准备条件",
}

SCENARIO_LABELS = {
    "construction": "建筑工程",
    "general": "通用",
    "finance": "金融",
    "iot": "物联网",
}

USE_CASE_LABELS = {
    "General Purpose / Best Overall": "通用场景 / 综合最优",
    "Maximum Security Required": "最高安全优先",
    "Performance Critical Applications": "性能敏感场景",
    "Future-Proof / Quantum Threat Protection": "面向未来 / 后量子防护",
    "Regulatory Compliance / Industry Standards": "合规与行业标准优先",
    "Rapid Development / Simple Implementation": "快速研发 / 易实施优先",
}

ACTOR_LABELS = {
    "Supervisor": "总控协调器",
    "Requirement Analyst": "需求分析师",
    "Cryptography Architect": "密码架构师",
    "Architect": "架构师",
    "Security & Compliance Auditor": "安全与合规审计员",
    "Code Engineer": "代码工程师",
}

TERM_REPLACEMENTS = [
    ("ePHI", "电子受保护健康信息（ePHI）"),
    ("General Purpose / Best Overall", "通用场景 / 综合最优"),
    ("Maximum Security Required", "最高安全优先"),
    ("Performance Critical Applications", "性能敏感场景"),
    ("Future-Proof / Quantum Threat Protection", "面向未来 / 后量子防护"),
    ("Regulatory Compliance / Industry Standards", "合规与行业标准优先"),
    ("Rapid Development / Simple Implementation", "快速研发 / 易实施优先"),
    ("role-based access control", "基于角色的访问控制"),
    ("split knowledge", "分离知识原则"),
    ("access control", "访问控制"),
    ("audit logging", "审计日志"),
    ("authenticated encryption", "认证加密"),
    ("key rotation", "密钥轮换"),
    ("key separation", "密钥隔离"),
    ("key management", "密钥管理"),
    ("key zeroization", "密钥清零"),
    ("key deletion", "密钥删除"),
    ("power-up self-tests", "上电自检"),
    ("conditional self-tests", "条件自检"),
    ("self-tests", "自检"),
    ("random number generation", "随机数生成"),
    ("approved RNG", "合规随机源"),
    ("encryption", "加密"),
    ("decryption", "解密"),
    ("operator roles", "操作员角色"),
    ("algorithm", "算法"),
    ("algorithms", "算法"),
    ("security", "安全"),
    ("compliance", "合规"),
    ("certificate", "认证"),
    ("requirements", "要求"),
    ("requirement", "要求"),
    ("recommendations", "建议"),
    ("recommendation", "建议"),
    ("evidence", "证据"),
    ("gaps", "缺口"),
    ("gap", "缺口"),
    ("critical", "严重"),
    ("high", "高"),
    ("medium", "中"),
    ("low", "低"),
    ("plaintext", "明文"),
    ("encrypted", "已加密"),
    ("enabled", "已启用"),
    ("disabled", "已禁用"),
    ("implemented", "已实现"),
    ("unknown", "未知"),
]

EXACT_TEXT_TRANSLATIONS = {
    "Need at least two variants for comparison.": "至少需要两个候选方案才能生成对比。",
    "No schemes provided for comparison": "未提供可用于对比的方案。",
    "At least 2 schemes required for comparison": "至少需要两个方案才能进行对比。",
    "No schemes provided": "未提供方案。",
    "No scheme selected; evidence assessment unavailable.": "未选择方案，暂时无法生成证据可信度评估。",
    "Most selected components include traceable references or standards.": "大部分选定组件都附带可追溯的标准或参考资料。",
    "The scheme is primarily built from standardized cryptographic components.": "该方案主要由标准化密码组件构成。",
    "The evidence set includes formal standards that support enterprise review.": "当前证据集中包含正式标准，能够支撑企业评审。",
    "Algorithm combination shows strong security posture for high-assurance scenarios.": "该算法组合在高保障场景下表现出较强的安全实力。",
    "Current MAS audit gate passed, which improves production readiness.": "当前已通过 MAS 审计门禁，生产就绪度更高。",
    "The selected design already includes a clear post-quantum migration path.": "当前设计已包含清晰的后量子迁移路径。",
    "Evidence coverage is low; several components lack strong supporting references.": "证据覆盖率偏低，部分组件缺少有力的参考依据。",
    "Evidence coverage is partial; add more standards or primary papers for enterprise trust.": "证据覆盖仍不完整，建议补充更多标准文档或一手论文。",
    "For full FIPS certification, use hardware security module (HSM)": "如需进一步满足 FIPS 认证路径，建议配套使用硬件安全模块（HSM）。",
    "Requirement parsing confidence is moderate; clarify constraints before approval.": "需求解析置信度一般，建议在批准前进一步澄清约束。",
    "Compiler returned no diagnostic output.": "编译器未返回可用诊断信息。",
    "fallback compile passed": "回退模板编译通过",
    "Python syntax check passed.": "Python 语法检查通过。",
    "Python code auto-repaired and passed.": "Python 代码已自动修复并通过检查。",
    "No C compiler found (gcc/clang).": "未检测到可用的 C 编译器（gcc/clang）。",
    "C syntax check passed.": "C 语法检查通过。",
    "C code auto-repaired and passed.": "C 代码已自动修复并通过检查。",
    "LLM parser unavailable, used heuristic parser.": "LLM 解析器不可用，已改用启发式解析。",
}

REGEX_TRANSLATIONS = [
    (re.compile(r"^Detected (\d+) critical vulnerabilities\.$"), lambda m: f"检测到 {m.group(1)} 个严重漏洞。"),
    (re.compile(r"^Overall compliance too low: ([0-9.]+)%\.$"), lambda m: f"整体合规得分过低：{m.group(1)}%。"),
    (re.compile(r"^Risk score too high: (\d+)/100\.$"), lambda m: f"风险得分过高：{m.group(1)}/100。"),
    (re.compile(r"^Quantum-safe requirement not satisfied\.$"), lambda m: "未满足后量子安全要求。"),
    (re.compile(r"^Some components have limited support metadata: (.+)\.$"), lambda m: f"部分组件的支撑元数据不足：{m.group(1)}。"),
    (re.compile(r"^Compliance score is still below enterprise target: ([0-9.]+)\.$"), lambda m: f"合规得分仍低于企业目标：{m.group(1)}。"),
    (re.compile(r"^Residual risk remains elevated at (\d+)/100\.$"), lambda m: f"剩余风险仍偏高：{m.group(1)}/100。"),
    (re.compile(r"^The requirement requests quantum safety, but the selected stack is not fully quantum-ready\.$"), lambda m: "需求要求具备后量子安全，但当前技术栈尚未完全满足。"),
    (re.compile(r"^Parsed requirement with confidence=([0-9.]+)\.$"), lambda m: f"需求解析完成，置信度为 {m.group(1)}。"),
    (re.compile(r"^Generated (\d+) candidate schemes\.$"), lambda m: f"已生成 {m.group(1)} 个候选方案。"),
    (re.compile(r"^Heuristic mode generated (\d+) candidate schemes\.$"), lambda m: f"启发式模式生成了 {m.group(1)} 个候选方案。"),
    (re.compile(r"^Switch to (proposal-\d+) after rejection\.$"), lambda m: f"当前提案被拒绝，切换到 {m.group(1)}。"),
    (re.compile(r"^Applied hardening to (proposal-\d+)\.$"), lambda m: f"已对 {m.group(1)} 应用加固措施。"),
    (re.compile(r"^Workflow finished with ([a-z_]+)\.$"), lambda m: f"流程已结束，当前状态：{display_status(m.group(1))}。"),
    (re.compile(r"^Python compile failed: (.+)$"), lambda m: f"Python 编译失败：{m.group(1)}"),
    (re.compile(r"^C syntax check passed with diagnostics:\n(.+)$", re.S), lambda m: f"C 语法检查通过，但有诊断信息：\n{m.group(1)}"),
    (re.compile(r"^C compile finished with warnings:\n(.+)$", re.S), lambda m: f"C 编译完成，但存在告警：\n{m.group(1)}"),
    (re.compile(r"^C compile failed after repair:\n(.+)$", re.S), lambda m: f"C 代码修复后仍编译失败：\n{m.group(1)}"),
    (re.compile(r"^C compile failed:\n(.+)$", re.S), lambda m: f"C 编译失败：\n{m.group(1)}"),
    (re.compile(r"^Use (.+)$"), lambda m: f"使用 {m.group(1)}"),
    (re.compile(r"^Implement (.+)$"), lambda m: f"实现 {m.group(1)}"),
    (re.compile(r"^Enable (.+)$"), lambda m: f"启用 {m.group(1)}"),
    (re.compile(r"^Disable (.+)$"), lambda m: f"禁用 {m.group(1)}"),
    (re.compile(r"^Upgrade to (.+)$"), lambda m: f"升级到 {m.group(1)}"),
    (re.compile(r"^Replace (.+)$"), lambda m: f"替换 {m.group(1)}"),
    (re.compile(r"^No (.+)$"), lambda m: f"缺少 {m.group(1)}"),
    (re.compile(r"^Approved RNG: (.+)$"), lambda m: f"已使用合规随机源：{m.group(1)}"),
]


def display_status(value: Any) -> str:
    key = str(value or "--").strip()
    lowered = key.lower()
    return STATUS_LABELS.get(lowered, STATUS_LABELS.get(key, key or "--"))


def display_trust_level(value: Any) -> str:
    key = str(value or "--").strip()
    lowered = key.lower()
    return TRUST_LEVEL_LABELS.get(lowered, TRUST_LEVEL_LABELS.get(key, key or "--"))


def display_bool(value: Any) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value or "--").strip().lower()
    if text in {"true", "yes", "y", "1"}:
        return "是"
    if text in {"false", "no", "n", "0"}:
        return "否"
    if text in {"--", "", "none", "null"}:
        return "--"
    return str(value)


def display_scenario(value: Any) -> str:
    key = str(value or "--").strip()
    lowered = key.lower()
    return SCENARIO_LABELS.get(lowered, key or "--")


def display_severity(value: Any) -> str:
    key = str(value or "--").strip()
    lowered = key.lower()
    return SEVERITY_LABELS.get(lowered, key or "--")


def display_priority(value: Any) -> str:
    key = str(value or "--").strip()
    lowered = key.lower()
    return PRIORITY_LABELS.get(lowered, key or "--")


def display_compliance_status(value: Any) -> str:
    key = str(value or "--").strip()
    lowered = key.lower()
    return COMPLIANCE_STATUS_LABELS.get(key, COMPLIANCE_STATUS_LABELS.get(lowered, key or "--"))


def display_actor(value: Any) -> str:
    key = str(value or "--").strip()
    return ACTOR_LABELS.get(key, key or "--")


def display_use_case(value: Any) -> str:
    key = str(value or "--").strip()
    return USE_CASE_LABELS.get(key, key or "--")


def translate_text(text: Any) -> Any:
    if not isinstance(text, str):
        return text

    stripped = text.strip()
    if not stripped:
        return stripped

    if stripped in EXACT_TEXT_TRANSLATIONS:
        return EXACT_TEXT_TRANSLATIONS[stripped]

    translated = stripped
    for pattern, renderer in REGEX_TRANSLATIONS:
        match = pattern.match(translated)
        if match:
            translated = renderer(match)
            break

    for source, target in TERM_REPLACEMENTS:
        translated = translated.replace(source, target)

    return translated


def summarize_vulnerability(summary: Dict[str, Any] | None) -> str:
    summary = summary or {}
    pieces: List[str] = []
    for key in ("critical", "high", "medium", "low", "info"):
        count = int(summary.get(key, 0) or 0)
        if count:
            pieces.append(f"{display_severity(key)} {count} 项")

    if not pieces:
        return "未发现显著漏洞问题。"
    return "漏洞概览：" + "，".join(pieces) + "。"


def summarize_compliance(report: Dict[str, Any] | None) -> str:
    report = report or {}
    summary = report.get("summary") or {}
    status_text = display_compliance_status(summary.get("overall_status") or ("ready" if report.get("certificate_ready") else "non_compliant"))
    percent = round(float(report.get("overall_compliance", summary.get("compliance_percentage", 0.0)) or 0.0), 2)
    standards = len(report.get("standards_checked", []) or [])
    gaps = len(report.get("gaps", []) or [])
    high_priority = summary.get("high_priority_recommendations", 0)
    return (
        f"合规概览：整体状态为{status_text}，综合合规得分 {percent}% ，"
        f"已检查 {standards} 项标准，当前存在 {gaps} 个缺口，高优先级建议 {high_priority} 项。"
    )


def localize_discussion_turn(turn: Dict[str, Any]) -> Dict[str, Any]:
    localized = copy.deepcopy(turn)
    localized["actor_label"] = display_actor(localized.get("actor"))
    localized["status_label"] = display_status(localized.get("status"))
    localized["message"] = translate_text(localized.get("message", ""))

    data = localized.get("data")
    if isinstance(data, dict) and "reasons" in data and isinstance(data["reasons"], list):
        data["reasons"] = [translate_text(item) for item in data["reasons"]]
    return localized


def localize_variant_comparison(payload: Dict[str, Any]) -> Dict[str, Any]:
    localized = copy.deepcopy(payload)
    if "note" in localized:
        localized["note"] = translate_text(localized["note"])
    if "error" in localized:
        localized["error"] = translate_text(localized["error"])

    comparison = localized.get("comparison")
    if isinstance(comparison, dict):
        if "error" in comparison:
            comparison["error"] = translate_text(comparison["error"])
        if "recommendations" in comparison and isinstance(comparison["recommendations"], list):
            for item in comparison["recommendations"]:
                if not isinstance(item, dict):
                    continue
                item["use_case_label"] = display_use_case(item.get("use_case", "--"))
                item["reason"] = translate_text(item.get("reason", ""))

        for row in comparison.get("side_by_side_table", []) or []:
            if isinstance(row, dict):
                row["quantum_resistant_label"] = display_bool(row.get("quantum_resistant", "--"))

        security_analysis = comparison.get("security_analysis")
        if isinstance(security_analysis, dict):
            security_analysis["summary_text"] = (
                f"安全分析：平均安全得分 {security_analysis.get('average_security_score', '--')}，"
                f"后量子方案占比 {security_analysis.get('quantum_resistant_percentage', '--')}%。"
            )

        performance_analysis = comparison.get("performance_analysis")
        if isinstance(performance_analysis, dict):
            performance_analysis["summary_text"] = (
                f"性能分析：平均性能得分 {performance_analysis.get('average_performance_score', '--')}，"
                f"性能跨度 {performance_analysis.get('performance_range', '--')}。"
            )

    charts = localized.get("charts")
    if isinstance(charts, dict):
        radar = charts.get("radar_chart")
        if isinstance(radar, dict):
            radar["labels"] = ["安全", "性能", "易用性", "标准化"]

        bar = charts.get("bar_chart")
        if isinstance(bar, dict):
            for dataset in bar.get("datasets", []) or []:
                if isinstance(dataset, dict):
                    dataset["label"] = translate_text(dataset.get("label", ""))

        pie = charts.get("quantum_pie_chart")
        if isinstance(pie, dict):
            pie["labels"] = ["后量子", "经典"]

    return localized


def localize_vulnerability_report(report: Dict[str, Any]) -> Dict[str, Any]:
    localized = copy.deepcopy(report)
    summary = localized.get("summary") or {}
    localized["summary_text"] = summarize_vulnerability(summary)

    for vuln in localized.get("vulnerabilities", []) or []:
        if not isinstance(vuln, dict):
            continue
        vuln["severity_label"] = display_severity(vuln.get("severity", "--"))
        vuln["title"] = translate_text(vuln.get("title", ""))
        vuln["description"] = translate_text(vuln.get("description", ""))
        vuln["remediation"] = translate_text(vuln.get("remediation", ""))

    for rec in localized.get("recommendations", []) or []:
        if not isinstance(rec, dict):
            continue
        rec["severity_label"] = display_severity(rec.get("severity", "--"))
        rec["title"] = translate_text(rec.get("title", ""))
        rec["action"] = translate_text(rec.get("action", ""))

    return localized


def localize_compliance_report(report: Dict[str, Any]) -> Dict[str, Any]:
    localized = copy.deepcopy(report)
    summary = localized.get("summary") or {}
    if isinstance(summary, dict):
        summary["overall_status"] = display_compliance_status(summary.get("overall_status", "--"))
        summary["certification_status"] = display_compliance_status(summary.get("certification_status", "--"))
    localized["summary_text"] = summarize_compliance(localized)

    if not localized.get("recommendations"):
        localized["recommendations"] = [
            {
                "recommendation": "当前方案已通过当前合规门槛，建议继续保留 HSM/KMS 托管、密钥轮换与上线前人工密码学复核。",
                "priority": "low",
            }
        ]

    for item in localized.get("recommendations", []) or []:
        if not isinstance(item, dict):
            continue
        item["priority_label"] = display_priority(item.get("priority", "--"))
        item["recommendation"] = translate_text(item.get("recommendation", ""))

    localized["gaps"] = [translate_text(item) for item in localized.get("gaps", []) or []]

    standards_results = localized.get("standards_results") or {}
    for result in standards_results.values():
        if not isinstance(result, dict):
            continue
        result["gaps"] = [translate_text(item) for item in result.get("gaps", []) or []]
        result["recommendations"] = [translate_text(item) for item in result.get("recommendations", []) or []]
        for req in result.get("requirements", []) or []:
            if not isinstance(req, dict):
                continue
            req["status_label"] = display_compliance_status(req.get("status", "--"))
            req["severity_label"] = display_severity(req.get("severity", "--"))
            req["description"] = translate_text(req.get("description", ""))
            req["evidence"] = [translate_text(item) for item in req.get("evidence", []) or []]
            req["gaps"] = [translate_text(item) for item in req.get("gaps", []) or []]
            req["recommendations"] = [translate_text(item) for item in req.get("recommendations", []) or []]

    return localized
