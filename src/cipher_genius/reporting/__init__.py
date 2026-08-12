"""Report template registry and helpers."""

from cipher_genius.reporting.localization import (
    display_actor,
    display_bool,
    display_compliance_status,
    display_priority,
    display_scenario,
    display_severity,
    display_status,
    display_trust_level,
    display_use_case,
    localize_compliance_report,
    localize_discussion_turn,
    localize_variant_comparison,
    localize_vulnerability_report,
    summarize_compliance,
    summarize_vulnerability,
    translate_text,
)
from cipher_genius.reporting.templates import (
    ReportTemplateManifest,
    ReportTemplateRegistry,
    ReportTemplateSection,
    get_report_template_registry,
)

__all__ = [
    "display_actor",
    "display_bool",
    "display_compliance_status",
    "display_priority",
    "display_scenario",
    "display_severity",
    "display_status",
    "display_trust_level",
    "display_use_case",
    "localize_compliance_report",
    "localize_discussion_turn",
    "localize_variant_comparison",
    "localize_vulnerability_report",
    "ReportTemplateManifest",
    "ReportTemplateRegistry",
    "ReportTemplateSection",
    "summarize_compliance",
    "summarize_vulnerability",
    "translate_text",
    "get_report_template_registry",
]
