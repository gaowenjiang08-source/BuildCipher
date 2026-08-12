"""Unit tests for citation-driven report output."""

from cipher_genius.api.report_service import MASReportService


def test_markdown_report_contains_citation_summary():
    """Markdown export should preserve evidence-pack citations."""
    service = MASReportService()
    mas_result = {
        "request_id": "req-1",
        "run_id": "run-1",
        "delivery": {
            "status": "best_effort",
            "compliance_score": 78.2,
            "risk_score": 18,
            "selected_proposal": "proposal-2",
            "next_action": "继续补齐密钥轮换策略。",
            "scenario_fit": "BIM/IFC 可信交付",
            "scoring": {},
        },
        "credibility_assessment": {
            "credibility_score": 0.81,
            "algorithm_strength_score": 0.77,
            "evidence_coverage": 0.66,
            "audit_readiness": 0.72,
            "trust_level": "medium",
            "trust_level_label": "中",
            "sources": [],
        },
        "compliance_report": {"summary_text": "存在待补齐的密钥治理要求。"},
        "vulnerability_report": {"summary_text": "当前无严重漏洞。", "summary": {}},
        "evidence_pack": {
            "items": [
                {
                    "doc_type": "template",
                    "title": "建筑工程可信交付模板",
                    "section": "推荐密码控制措施",
                    "snippet": "建议补齐密钥轮换与审计留痕要求。",
                    "score": 8.4,
                    "metadata": {
                        "clause_code": "3.2.1",
                        "section_path": ["密码治理要求", "推荐密码控制措施"],
                    },
                }
            ]
        },
    }

    markdown = service._build_markdown(
        mas_result=mas_result,
        scenario="construction",
        selected_scheme="AES-GCM + HSM",
        comparison={},
        deployment_guide=["补齐密钥轮换策略。"],
        template=None,
        enterprise_delivery={},
        include_code=False,
    )

    assert "## 引用依据摘要" in markdown
    assert "建筑工程可信交付模板" in markdown
    assert "条款 3.2.1" in markdown
    assert "建议补齐密钥轮换与审计留痕要求" in markdown
