"""Page renderers for the Streamlit v3 app."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict, List

import streamlit as st

from cipher_genius.codegen.generator import CodeGenerator
from cipher_genius.core.generator import SchemeGenerator
from cipher_genius.core.parser import RequirementParser
from cipher_genius.core.simple_validator import quick_validate
from cipher_genius.features.exporter import SchemeExporter
from cipher_genius.ui.web_v3.state import reset_generation

try:
    from cipher_genius.features import SchemeComparator, SecurityAssessor

    FEATURES_AVAILABLE = True
    FEATURES_IMPORT_ERROR = ""
except Exception as exc:
    FEATURES_AVAILABLE = False
    FEATURES_IMPORT_ERROR = str(exc)


@st.cache_resource
def _get_requirement_parser() -> RequirementParser:
    return RequirementParser()


@st.cache_resource
def _get_scheme_generator() -> SchemeGenerator:
    return SchemeGenerator()


@st.cache_resource
def _get_code_generator() -> CodeGenerator:
    return CodeGenerator()


@st.cache_resource
def _get_exporter() -> SchemeExporter:
    return SchemeExporter()


def _safe_text(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _to_dict(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        return data
    if hasattr(data, "model_dump"):
        return data.model_dump()
    if hasattr(data, "to_dict"):
        return data.to_dict()
    return {}


def _component_name(component: Any) -> str:
    if isinstance(component, dict):
        return _safe_text(component.get("name"), "Unnamed")
    return _safe_text(getattr(component, "name", None), "Unnamed")


def _component_category(component: Any) -> str:
    if isinstance(component, dict):
        return _safe_text(component.get("category"), "unknown")
    return _safe_text(getattr(component, "category", None), "unknown")


def _component_security_level(component: Any) -> str:
    if isinstance(component, dict):
        security = component.get("security") or {}
        value = security.get("security_level")
    else:
        security = getattr(component, "security", None)
        value = getattr(security, "security_level", None) if security else None
    return _safe_text(value, "N/A")


def _component_speed(component: Any) -> str:
    if isinstance(component, dict):
        performance = component.get("performance") or {}
        value = performance.get("software_speed")
    else:
        performance = getattr(component, "performance", None)
        value = getattr(performance, "software_speed", None) if performance else None
    return _safe_text(value, "N/A")


def _scheme_name(scheme: Any) -> str:
    if hasattr(scheme, "metadata") and hasattr(scheme.metadata, "name"):
        return _safe_text(scheme.metadata.name, "Unnamed Scheme")
    if isinstance(scheme, dict):
        if "metadata" in scheme:
            return _safe_text((scheme.get("metadata") or {}).get("name"), "Unnamed Scheme")
        return _safe_text(scheme.get("name"), "Unnamed Scheme")
    return "Unnamed Scheme"


def _serialize_scheme_for_export(scheme: Any) -> Dict[str, Any]:
    scheme_dict = _to_dict(scheme)

    metadata = scheme_dict.get("metadata") or {}
    requirements = scheme_dict.get("requirements") or {}
    security = requirements.get("security") or {}
    parameters = scheme_dict.get("parameters") or {}
    architecture = scheme_dict.get("architecture") or {}
    components = architecture.get("components") or []
    component_names = [
        _safe_text((comp or {}).get("name"), "Unnamed") if isinstance(comp, dict) else _component_name(comp)
        for comp in components
    ]

    payload = {
        "name": _safe_text(metadata.get("name"), "Unnamed Scheme"),
        "type": _safe_text(metadata.get("scheme_type"), "unknown"),
        "security_level": security.get("security_level"),
        "created_at": metadata.get("generated_at"),
        "description": _safe_text(requirements.get("description"), ""),
        "parameters": parameters,
        "properties": {
            "component_count": len(component_names),
            "components": component_names,
            "score": scheme_dict.get("score"),
        },
        "security_analysis": scheme_dict.get("security_analysis") or {},
        "raw_scheme": scheme_dict,
    }
    return payload


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "buildtrust_scheme"


def _get_detailed_examples() -> Dict[str, str]:
    return {
        "Custom": "",
        "IoT AEAD (Ultra Lightweight)": (
            "Design an authenticated encryption scheme for battery-powered IoT sensors.\n"
            "Requirements:\n"
            "- Security level: 128-bit\n"
            "- Device class: Cortex-M0/M3\n"
            "- RAM budget: <= 2KB\n"
            "- Flash budget: <= 32KB\n"
            "- Latency target: <= 10ms for 256-byte payload\n"
            "- Threats: eavesdropping, tampering, replay\n"
            "- Nonce misuse resistance preferred"
        ),
        "Construction Sensor Firmware Signing": (
            "Design a digital signature workflow for over-the-air firmware updates of construction sensors.\n"
            "Requirements:\n"
            "- Security level: 192-bit or higher\n"
            "- Long-term verification support: >= 10 years\n"
            "- Threats: forgery, rollback, replay, man-in-the-middle\n"
            "- Must support key rotation and audit traceability\n"
            "- Verification must run on constrained edge hardware"
        ),
        "Cloud Object Storage Encryption": (
            "Design authenticated encryption for cloud object storage.\n"
            "Requirements:\n"
            "- Security level: 256-bit\n"
            "- Throughput target: >= 1 GB/s on server-side\n"
            "- Threats: data tampering, insider misuse, replay\n"
            "- Must support envelope encryption and key versioning\n"
            "- Compliance-friendly design and deterministic metadata handling"
        ),
        "Payment Tokenization Service": (
            "Design a cryptographic scheme for payment tokenization microservice.\n"
            "Requirements:\n"
            "- Security level: 128-bit minimum\n"
            "- p99 latency <= 15ms\n"
            "- Threats: token forgery, replay, data leakage\n"
            "- Need integrity protection, nonce strategy, and rotation plan\n"
            "- Must support high concurrency server deployment"
        ),
        "Industrial Gateway Key Exchange": (
            "Design key exchange for industrial gateway and field devices.\n"
            "Requirements:\n"
            "- Security level: 128-bit now, migration path to post-quantum\n"
            "- Threats: man-in-the-middle, replay, side-channel\n"
            "- Intermittent network conditions and low CPU budget\n"
            "- Must include session key derivation and forward secrecy preference"
        ),
        "Tamper-Evident Secure Logging": (
            "Design tamper-evident logging integrity mechanism for distributed services.\n"
            "Requirements:\n"
            "- Security level: 128-bit\n"
            "- Detect log tampering and out-of-order insertion\n"
            "- Threats: forgery, rollback, insider tampering\n"
            "- Need efficient verification for daily audit jobs\n"
            "- Storage overhead should remain moderate"
        ),
    }


def _build_scheme_explanation(scheme: Any, parsed_requirement: Any) -> Dict[str, List[str]]:
    description = ""
    platform = "unknown"
    scheme_type = _safe_text(getattr(getattr(scheme, "metadata", None), "scheme_type", None), "unknown")
    security_level = _safe_text(
        getattr(getattr(getattr(scheme, "requirements", None), "security", None), "security_level", None),
        "N/A",
    )
    if parsed_requirement is not None and hasattr(parsed_requirement, "requirement"):
        req = parsed_requirement.requirement
        description = _safe_text(getattr(req, "description", ""), "")
        platform = _safe_text(getattr(getattr(req, "target_platform", None), "type", None), "unknown")

    components = getattr(getattr(scheme, "architecture", None), "components", []) or []
    component_names = [_component_name(c) for c in components]
    analysis = getattr(scheme, "security_analysis", None)
    properties = list(getattr(analysis, "properties", []) or [])
    concerns = list(getattr(analysis, "concerns", []) or [])

    desc_lower = description.lower()
    explicit_matches: List[str] = []
    for name in component_names:
        normalized_name = name.lower().replace("-", " ").replace("_", " ")
        if normalized_name in desc_lower or name.lower() in desc_lower:
            explicit_matches.append(name)

    why_lines: List[str] = []
    why_lines.append(
        f"The scheme type is `{scheme_type}` with `{security_level}`-bit target security, aligned to `{platform}` deployment constraints."
    )
    if explicit_matches:
        why_lines.append(
            "The following components were selected because they are explicitly referenced in the requirement: "
            + ", ".join(explicit_matches)
            + "."
        )
    elif component_names:
        why_lines.append(
            "Component composition is chosen to satisfy functional completeness and compatibility: "
            + ", ".join(component_names[:6])
            + "."
        )
    rationale = _safe_text(getattr(scheme, "design_rationale", ""), "")
    if rationale and rationale != "N/A":
        why_lines.append("Model rationale: " + rationale[:260] + ("..." if len(rationale) > 260 else ""))

    security_lines: List[str] = []
    if properties:
        security_lines.append("Targeted security properties: " + ", ".join(properties[:6]) + ".")
    else:
        security_lines.append("No explicit formal properties were emitted; treat this as a draft-level design.")
    if concerns:
        security_lines.append("Known security caveats: " + "; ".join(concerns[:4]) + ".")
    else:
        security_lines.append("No major caveats were surfaced by the current analysis pass.")

    usage_lines: List[str] = []
    usage_lines.append(
        "Use this output as an architectural draft for requirement validation, component tradeoff analysis, and implementation planning."
    )
    usage_lines.append(
        "Do not deploy directly. Require cryptographer review, formal analysis, secure implementation review, and independent audit."
    )

    return {
        "why": why_lines,
        "security": security_lines,
        "usage": usage_lines,
    }


def _kpi_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class=\"cg-kpi-card\">
            <div class=\"cg-kpi-value\">{value}</div>
            <div class=\"cg-kpi-label\">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_growth_series(schemes: List[Any]) -> List[float]:
    baseline = [36, 52, 42, 61, 45, 54, 58, 49, 55, 63, 57, 60]
    if not schemes:
        return baseline

    scores = [float(getattr(s, "score", 0.0)) for s in schemes]
    for idx in range(len(baseline)):
        score = scores[idx % len(scores)]
        baseline[idx] = round(max(15.0, min(95.0, 18.0 + score * 7.2 + (idx % 3) * 1.6)), 2)
    return baseline


def _build_valuable_rows(schemes: List[Any]) -> List[Dict[str, Any]]:
    if not schemes:
        return [
            {"Scheme": "AES-GCM Profile", "Score": 8.7, "Security(bit)": 128, "Components": 3},
            {"Scheme": "ChaCha20-Poly1305", "Score": 8.4, "Security(bit)": 128, "Components": 2},
            {"Scheme": "Hybrid PQC Draft", "Score": 8.1, "Security(bit)": 256, "Components": 4},
            {"Scheme": "HMAC-SHA256 Pack", "Score": 7.9, "Security(bit)": 128, "Components": 2},
            {"Scheme": "Signature Bundle", "Score": 7.8, "Security(bit)": 192, "Components": 3},
        ]

    ranked = sorted(schemes, key=lambda x: getattr(x, "score", 0.0), reverse=True)[:5]
    rows: List[Dict[str, Any]] = []
    for scheme in ranked:
        sec_level = getattr(getattr(getattr(scheme, "requirements", None), "security", None), "security_level", "N/A")
        comp_count = len(getattr(getattr(scheme, "architecture", None), "components", []))
        rows.append(
            {
                "Scheme": _scheme_name(scheme),
                "Score": round(float(getattr(scheme, "score", 0.0)), 2),
                "Security(bit)": sec_level,
                "Components": comp_count,
            }
        )
    return rows


def _build_recent_rows(schemes: List[Any]) -> List[Dict[str, Any]]:
    if not schemes:
        return [
            {"Run": "Design Run #1", "Owner": "Security Team", "Status": "Ready", "Time": "09:40"},
            {"Run": "Design Run #2", "Owner": "Platform Team", "Status": "Ready", "Time": "10:25"},
            {"Run": "Benchmark Run", "Owner": "Infra", "Status": "Pending", "Time": "11:10"},
            {"Run": "Compliance Dry Run", "Owner": "Governance", "Status": "Pending", "Time": "11:50"},
            {"Run": "Export Bundle", "Owner": "Ops", "Status": "Ready", "Time": "12:20"},
        ]

    rows: List[Dict[str, Any]] = []
    for idx, scheme in enumerate(schemes[:5], start=1):
        has_code = bool(
            getattr(getattr(scheme, "implementation", None), "python", "")
            or getattr(getattr(scheme, "implementation", None), "c", "")
        )
        generated_at = getattr(getattr(scheme, "metadata", None), "generated_at", None)
        time_text = generated_at.strftime("%H:%M") if hasattr(generated_at, "strftime") else "--:--"
        rows.append(
            {
                "Run": f"Scheme #{idx}",
                "Owner": "Workspace",
                "Status": "Ready" if has_code else "Pending",
                "Time": time_text,
            }
        )
    return rows


def render_dashboard_page() -> None:
    st.markdown("### Dashboard")

    schemes = st.session_state.generated_schemes
    total = len(schemes)
    avg_score = sum(float(getattr(s, "score", 0.0)) for s in schemes) / total if total else 0.0
    high_security = sum(
        1
        for s in schemes
        if isinstance(getattr(getattr(getattr(s, "requirements", None), "security", None), "security_level", 0), int)
        and getattr(getattr(getattr(s, "requirements", None), "security", None), "security_level", 0) >= 128
    )
    code_ready = sum(
        1
        for s in schemes
        if getattr(getattr(s, "implementation", None), "python", "")
        or getattr(getattr(s, "implementation", None), "c", "")
    )
    parsed = st.session_state.parsed_requirement
    confidence = f"{parsed.confidence:.0%}" if parsed is not None and hasattr(parsed, "confidence") else "--"
    concern_count = sum(len(getattr(getattr(s, "security_analysis", None), "concerns", []) or []) for s in schemes)

    status_cards = [
        ("Generated Schemes", str(total), "+ stable"),
        ("Average Score", f"{avg_score:.2f}", "+ healthy"),
        ("High Security", str(high_security), "+ compliant"),
        ("Code Ready", str(code_ready), "+ ready"),
        ("Parser Confidence", confidence, "+ tracked"),
        ("Open Concerns", str(concern_count), "- attention"),
    ]

    left, right = st.columns([1.05, 1.65], gap="large")
    with left:
        st.markdown("<div class='cg-section-title'>Status Overview</div>", unsafe_allow_html=True)
        cards_html = "<div class='cg-mini-grid'>"
        for title, value, trend in status_cards:
            trend_color = "var(--cg-danger)" if trend.startswith("-") else "var(--cg-success)"
            cards_html += (
                "<div class='cg-mini-card'>"
                f"<div class='cg-mini-title'>{title}</div>"
                f"<div class='cg-mini-value'>{value}</div>"
                f"<div class='cg-mini-trend' style='color:{trend_color};'>{trend}</div>"
                "</div>"
            )
        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

    with right:
        st.markdown("<div class='cg-section-title'>Growth Chart</div>", unsafe_allow_html=True)
        st.line_chart({"Monthly": _build_growth_series(schemes)}, height=300)

    t1, t2 = st.columns(2, gap="large")
    with t1:
        st.markdown("<div class='cg-section-title'>Most Valuable Schemes</div>", unsafe_allow_html=True)
        st.dataframe(_build_valuable_rows(schemes), use_container_width=True, hide_index=True)
    with t2:
        st.markdown("<div class='cg-section-title'>Recent Runs</div>", unsafe_allow_html=True)
        st.dataframe(_build_recent_rows(schemes), use_container_width=True, hide_index=True)


def render_generate_page() -> None:
    st.markdown("### Generate")

    left, right = st.columns([2.2, 1], gap="large")

    template_map = _get_detailed_examples()

    with left:
        st.markdown("<div class='cg-section-title'>Requirement Studio</div>", unsafe_allow_html=True)
        selected_template = st.selectbox("Requirement template", list(template_map.keys()))
        if selected_template != "Custom":
            st.session_state.last_input = template_map[selected_template]

        requirement = st.text_area(
            "Describe your cryptographic requirement",
            value=st.session_state.last_input,
            height=220,
            placeholder="Example: authenticated encryption for IoT, 128-bit security, memory under 2KB",
        )

        a1, a2 = st.columns(2)
        with a1:
            variants = st.slider("Variants", min_value=1, max_value=5, value=2)
        with a2:
            generate_code = st.toggle("Generate implementation code", value=True)

        b1, b2 = st.columns(2)
        generate_clicked = b1.button("Generate Scheme", type="primary", use_container_width=True)
        clear_clicked = b2.button("Clear Session", use_container_width=True)

    with right:
        st.markdown("<div class='cg-section-title'>Ops Snapshot</div>", unsafe_allow_html=True)
        st.markdown("<div class='cg-note'>Use concise constraints: scheme type, security level, platform, and performance limits.</div>", unsafe_allow_html=True)
        _kpi_card("Existing Schemes", str(len(st.session_state.generated_schemes)))
        _kpi_card("Code Generation", "Enabled" if generate_code else "Disabled")
        _kpi_card("Template", selected_template)
        st.markdown("<div class='cg-section-title'>Example Preview</div>", unsafe_allow_html=True)
        preview_text = template_map.get(selected_template, "")
        if preview_text:
            st.code(preview_text, language="text")
        else:
            st.markdown(
                "<div class='cg-note'>Choose one detailed example above, or write your own custom requirement.</div>",
                unsafe_allow_html=True,
            )

    if clear_clicked:
        reset_generation()
        st.rerun()

    if generate_clicked:
        if not requirement.strip():
            st.warning("Please input requirements first.")
            return

        st.session_state.last_input = requirement
        st.session_state.last_error = None

        with st.status("Running parser and generator...", expanded=True) as status:
            try:
                parser = _get_requirement_parser()
                parsed = parser.parse(requirement)
                st.session_state.parsed_requirement = parsed
                st.write("Requirement parsing completed.")

                generator = _get_scheme_generator()
                schemes = generator.generate(parsed.requirement, num_variants=variants)
                if not schemes:
                    raise RuntimeError("No scheme was generated. Please refine your requirement and retry.")
                st.session_state.generated_schemes = schemes
                st.session_state.selected_scheme_index = 0
                st.write(f"Generated {len(schemes)} scheme(s).")

                if generate_code:
                    codegen = _get_code_generator()
                    for idx, scheme in enumerate(st.session_state.generated_schemes, start=1):
                        scheme.implementation = codegen.generate_all(scheme)
                        st.write(f"Code generated for scheme {idx}.")

                status.update(label="Generation finished.", state="complete")
            except Exception as exc:
                st.session_state.last_error = str(exc)
                status.update(label="Generation failed.", state="error")

    if st.session_state.last_error:
        st.error(st.session_state.last_error)


def _render_validation(scheme: Any) -> None:
    try:
        is_valid, errors, warnings = quick_validate(
            scheme_type=scheme.metadata.scheme_type,
            components=scheme.architecture.components,
            security_level=scheme.requirements.security.security_level,
            parameters={
                "key_size": scheme.parameters.key_size,
                "nonce_size": scheme.parameters.nonce_size,
                "tag_size": scheme.parameters.tag_size,
            },
        )
    except Exception as exc:
        st.warning(f"Validation skipped due to incompatible schema: {exc}")
        return

    if is_valid:
        st.success("Validation passed")
    else:
        st.error("Validation failed")

    for item in errors:
        st.write(f"- Error: {item}")
    for item in warnings:
        st.write(f"- Warning: {item}")


def render_results_page() -> None:
    st.markdown("### Results")

    schemes = st.session_state.generated_schemes
    if not schemes:
        st.info("No generated scheme yet.")
        return

    left, right = st.columns([2.2, 1], gap="large")

    with right:
        st.markdown("<div class='cg-section-title'>Scheme Navigator</div>", unsafe_allow_html=True)
        options = list(range(len(schemes)))
        default_index = min(st.session_state.selected_scheme_index, max(len(schemes) - 1, 0))
        selected_idx = st.selectbox(
            "Select scheme",
            options=options,
            index=default_index,
            format_func=lambda i: f"{i + 1}. {_scheme_name(schemes[i])}",
        )
        st.session_state.selected_scheme_index = selected_idx
        st.markdown("<div class='cg-note'>Switch variants quickly and compare outputs in the analysis tab.</div>", unsafe_allow_html=True)

    with left:
        scheme = schemes[st.session_state.selected_scheme_index]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Scheme", _scheme_name(scheme))
        with c2:
            st.metric("Score", f"{getattr(scheme, 'score', 0.0):.2f}/10")
        with c3:
            sec_level = getattr(getattr(getattr(scheme, "requirements", None), "security", None), "security_level", "N/A")
            st.metric("Security", f"{sec_level}-bit")

        components = getattr(getattr(scheme, "architecture", None), "components", [])
        st.markdown("<div class='cg-section-title'>Components</div>", unsafe_allow_html=True)
        if components:
            rows: List[Dict[str, str]] = []
            for component in components:
                rows.append(
                    {
                        "Name": _component_name(component),
                        "Category": _component_category(component),
                        "Security(bit)": _component_security_level(component),
                        "Software Speed": _component_speed(component),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.markdown(
                "".join(f'<span class="cg-pill">{row["Name"]}</span>' for row in rows),
                unsafe_allow_html=True,
            )
        else:
            st.warning("No components were attached to this scheme.")

        st.markdown("<div class='cg-section-title'>Security Analysis</div>", unsafe_allow_html=True)
        analysis = getattr(scheme, "security_analysis", None)
        if analysis is not None:
            col1, col2 = st.columns(2)
            with col1:
                st.write("Properties:")
                properties = getattr(analysis, "properties", [])
                if properties:
                    for item in properties:
                        st.write(f"- {item}")
                else:
                    st.write("- No explicit properties provided")
            with col2:
                st.write("Concerns:")
                concerns = getattr(analysis, "concerns", [])
                if concerns:
                    for item in concerns:
                        st.write(f"- {item}")
                else:
                    st.write("- No explicit concerns provided")

        parsed_requirement = st.session_state.parsed_requirement
        explanation = _build_scheme_explanation(scheme, parsed_requirement)
        st.markdown("<div class='cg-section-title'>Rationale and Explanation</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.write("Why this scheme:")
            for item in explanation["why"]:
                st.write(f"- {item}")
        with col2:
            st.write("Security interpretation:")
            for item in explanation["security"]:
                st.write(f"- {item}")
        st.write("Usage boundary:")
        for item in explanation["usage"]:
            st.write(f"- {item}")

        _render_validation(scheme)

        st.warning(
            "This output is for research and prototyping only. Production use requires independent cryptographic review and security audit."
        )

        implementation = getattr(scheme, "implementation", None)
        has_code = bool(
            implementation
            and (
                getattr(implementation, "python", "")
                or getattr(implementation, "c", "")
                or getattr(implementation, "pseudocode", "")
            )
        )
        if has_code:
            st.markdown("<div class='cg-section-title'>Generated Code</div>", unsafe_allow_html=True)
            tabs = st.tabs(["Python", "C", "Pseudocode"])
            with tabs[0]:
                st.code(implementation.python or "# Empty", language="python")
            with tabs[1]:
                st.code(implementation.c or "/* Empty */", language="c")
            with tabs[2]:
                st.code(implementation.pseudocode or "# Empty", language="text")


def render_tools_page() -> None:
    st.markdown("### Tools")

    schemes = st.session_state.generated_schemes
    if not schemes:
        st.info("Generate schemes first.")
        return

    if not FEATURES_AVAILABLE:
        st.warning("Advanced features are unavailable in the current environment.")
        if FEATURES_IMPORT_ERROR:
            st.code(FEATURES_IMPORT_ERROR, language=None)
        return

    tab1, tab2 = st.tabs(["Scheme Comparison", "Security Assessment"])

    with tab1:
        if len(schemes) < 2:
            st.info("Generate at least 2 variants for comparison.")
        else:
            try:
                comparator = SchemeComparator()
                comparison = comparator.compare_schemes(schemes[:5])
                st.json(comparison)
            except Exception as exc:
                st.error(f"Comparison failed: {exc}")

    with tab2:
        try:
            assessor = SecurityAssessor()
            selected_idx = min(st.session_state.selected_scheme_index, len(schemes) - 1)
            assessment = assessor.assess_scheme(schemes[selected_idx])
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Overall score", assessment.get("overall_score", "N/A"))
            with col2:
                st.metric("Threat level", _safe_text(assessment.get("threat_level"), "N/A").upper())
            st.json(assessment)
        except Exception as exc:
            st.error(f"Assessment failed: {exc}")


def render_export_page() -> None:
    st.markdown("### Export")

    schemes = st.session_state.generated_schemes
    if not schemes:
        st.info("Generate schemes first.")
        return

    selected_idx = min(st.session_state.selected_scheme_index, len(schemes) - 1)
    scheme = schemes[selected_idx]
    payload = _serialize_scheme_for_export(scheme)

    exporter = _get_exporter()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = _slugify(payload["name"])

    json_output = exporter.export_to_json(payload, pretty=True)
    markdown_output = exporter.export_to_markdown(payload)

    st.markdown("<div class='cg-note'>Export artifacts with normalized metadata for audit trails and handoff.</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download JSON",
            data=json_output,
            file_name=f"{base_name}_{timestamp}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download Markdown",
            data=markdown_output,
            file_name=f"{base_name}_{timestamp}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with st.expander("Markdown preview", expanded=False):
        st.code(markdown_output[:6000], language="markdown")
