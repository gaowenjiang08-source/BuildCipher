"""
CipherGenius Enhanced Web Interface v2.0
功能增强版Web界面 - 包含所有新功能
"""

import sys
import io
import streamlit as st
from typing import Optional, List, Dict, Any

# 设置编码
try:
    if sys.stdout and hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except (ValueError, AttributeError):
    pass

# 导入核心模块
from cipher_genius.core.parser import RequirementParser
from cipher_genius.core.generator import SchemeGenerator
from cipher_genius.core.simple_validator import quick_validate
from cipher_genius.core.scheme_detector import detect_scheme_type
from cipher_genius.knowledge.components import ComponentLibrary
from cipher_genius.codegen.generator import CodeGenerator

# 导入新功能模块
try:
    from cipher_genius.features import (
        SchemeComparator, SecurityAssessor, ComponentRecommender,
        PerformanceEstimator, SchemeExporter, TutorialManager,
        Platform, PerformanceLevel
    )
    FEATURES_AVAILABLE = True
except ImportError:
    FEATURES_AVAILABLE = False
    st.warning("⚠️ Advanced features not available. Please check installation.")

# 页面配置
st.set_page_config(
    page_title="CipherGenius Enhanced - 密码学方案生成器",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }

    .feature-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        margin: 1rem 0;
    }

    .feature-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 12px rgba(0, 0, 0, 0.2);
    }

    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid #667eea;
        margin: 0.5rem 0;
    }

    .tutorial-step {
        background: #f8f9fa;
        padding: 1rem;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
        border-radius: 4px;
    }

    .comparison-table {
        width: 100%;
        border-collapse: collapse;
    }

    .comparison-table th {
        background: #667eea;
        color: white;
        padding: 0.75rem;
    }

    .comparison-table td {
        padding: 0.75rem;
        border: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if 'generated_schemes' not in st.session_state:
        st.session_state.generated_schemes = []
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 'Home'
    if 'tutorial_progress' not in st.session_state:
        st.session_state.tutorial_progress = {}
    if 'component_library' not in st.session_state:
        st.session_state.component_library = ComponentLibrary()


def render_header():
    """渲染页面头部"""
    st.markdown('<h1 class="main-header">🔐 CipherGenius Enhanced</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666; font-size: 1.1rem;">AI-Powered Cryptographic Scheme Generator with Advanced Tools</p>', unsafe_allow_html=True)
    st.markdown("---")


def render_home_tab():
    """主页 - 方案生成"""
    st.header("🏠 Scheme Generation")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📝 Describe Your Requirements")
        requirement_text = st.text_area(
            "Enter your security requirements in natural language:",
            height=150,
            placeholder="Example: I need an authenticated encryption scheme for IoT devices with 128-bit security..."
        )

        col_gen1, col_gen2, col_gen3 = st.columns(3)
        with col_gen1:
            num_variants = st.slider("Number of variants:", 1, 5, 3)
        with col_gen2:
            generate_code = st.checkbox("Generate code", value=True)
        with col_gen3:
            auto_validate = st.checkbox("Auto-validate", value=True)

        if st.button("🚀 Generate Scheme", type="primary", use_container_width=True):
            if requirement_text.strip():
                with st.spinner("Generating cryptographic scheme..."):
                    try:
                        # 解析需求
                        parser = RequirementParser()
                        req = parser.parse(requirement_text)

                        # 生成方案
                        generator = SchemeGenerator()
                        schemes = generator.generate(req, num_variants=num_variants)

                        st.session_state.generated_schemes = schemes
                        st.success(f"✅ Generated {len(schemes)} scheme(s)!")

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter your requirements first.")

    with col2:
        st.subheader("📊 Quick Examples")
        examples = {
            "🌐 IoT Encryption": "Lightweight encryption for IoT devices with 128-bit security and low memory usage",
            "🔮 Post-Quantum": "Post-quantum secure key exchange and digital signature for long-term security",
            "🔐 Digital Signature": "Digital signature scheme for document signing with 256-bit security",
            "🔑 Key Exchange": "Secure key exchange protocol for TLS with perfect forward secrecy"
        }

        for name, example in examples.items():
            if st.button(name, use_container_width=True):
                requirement_text = example
                st.rerun()

    # 显示生成的方案
    if st.session_state.generated_schemes:
        st.markdown("---")
        st.subheader("📋 Generated Schemes")

        for idx, scheme in enumerate(st.session_state.generated_schemes):
            with st.expander(f"Scheme {idx + 1}: {scheme.get('name', 'Untitled')}", expanded=(idx == 0)):
                st.json(scheme)


def render_component_library():
    """组件库浏览器"""
    st.header("📚 Component Library (152 Components)")

    # 搜索和过滤
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("🔍 Search components:", placeholder="e.g., AES, SHA-256, Kyber...")
    with col2:
        category_filter = st.selectbox("Category:", ["All", "Block Cipher", "Hash", "Signature", "Key Exchange", "AEAD", "Protocol"])
    with col3:
        security_filter = st.selectbox("Security:", ["All", "128-bit", "192-bit", "256-bit", "Post-Quantum"])

    # 组件统计
    st.markdown("### 📊 Statistics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Components", "152", "+97")
    with col2:
        st.metric("Primitives", "122", "80.3%")
    with col3:
        st.metric("Modes", "16", "10.5%")
    with col4:
        st.metric("Protocols", "14", "9.2%")

    # 组件列表
    st.markdown("### 🔮 Components")

    categories = {
        "Block Ciphers": ["AES", "ChaCha20", "Camellia", "ARIA", "Twofish", "Serpent", "Blowfish", "DES", "3DES", "CAST5", "IDEA", "RC6", "MARS", "SM4", "Salsa20"],
        "Hash Functions": ["SHA-256", "SHA-512", "SHA-3", "BLAKE2", "BLAKE3", "Keccak", "Whirlpool", "SM3", "Streebog", "Tiger"],
        "Signatures": ["RSA", "ECDSA", "EdDSA", "Schnorr", "BLS", "Dilithium", "FALCON", "SPHINCS+", "SM2"],
        "Key Exchange": ["ECDH", "DH", "X25519", "Kyber", "NTRU", "Classic McEliece", "FrodoKEM"],
        "AEAD": ["GCM", "CCM", "ChaCha20-Poly1305", "EAX", "OCB", "Ascon", "AEGIS"],
        "Protocols": ["zkSNARK", "zkSTARK", "PLONK", "OPAQUE", "SPAKE2+", "PSI"]
    }

    for category, components in categories.items():
        with st.expander(f"📁 {category} ({len(components)} components)"):
            cols = st.columns(4)
            for idx, comp in enumerate(components):
                with cols[idx % 4]:
                    if st.button(comp, key=f"comp_{category}_{comp}"):
                        st.info(f"Selected: {comp}\n\nSecurity: Modern\nStandardized: Yes\nQuantum-Safe: Varies")


def render_tutorials():
    """交互式教程"""
    st.header("🎓 Interactive Tutorials")

    if not FEATURES_AVAILABLE:
        st.error("Tutorial system not available")
        return

    tutorial_mgr = TutorialManager()
    tutorials = tutorial_mgr.get_all_tutorials()

    # 教程选择
    tutorial_titles = [f"{t.title} ({t.difficulty}, {t.duration_minutes} min)" for t in tutorials]
    selected_idx = st.selectbox("Select Tutorial:", range(len(tutorials)), format_func=lambda x: tutorial_titles[x])

    if selected_idx is not None:
        tutorial = tutorials[selected_idx]

        st.markdown(f"### {tutorial.title}")
        st.markdown(f"**Difficulty:** {tutorial.difficulty} | **Duration:** {tutorial.duration_minutes} minutes")
        st.markdown(tutorial.description)

        st.markdown("---")
        st.markdown("### 📝 Tutorial Steps")

        for step_idx, step in enumerate(tutorial.steps):
            with st.expander(f"Step {step_idx + 1}: {step.get('title', 'Step')}", expanded=(step_idx == 0)):
                st.markdown(step.get('content', ''))
                if 'code' in step:
                    st.code(step['code'], language='python')
                if 'exercise' in step:
                    st.info(f"💪 Exercise: {step['exercise']}")


def render_tools():
    """高级工具"""
    st.header("🛠️ Advanced Tools")

    if not FEATURES_AVAILABLE:
        st.error("Advanced tools not available")
        return

    tool_tabs = st.tabs(["🔍 Comparator", "🛡️ Security Assessor", "💡 Recommender", "⚡ Performance Estimator"])

    with tool_tabs[0]:
        st.subheader("Scheme Comparator")
        st.markdown("Compare multiple cryptographic schemes side-by-side")

        if st.session_state.generated_schemes and len(st.session_state.generated_schemes) >= 2:
            comparator = SchemeComparator()
            result = comparator.compare_schemes(st.session_state.generated_schemes[:3])

            st.markdown("### 📊 Comparison Results")
            st.json(result)
        else:
            st.info("Generate at least 2 schemes to use the comparator")

    with tool_tabs[1]:
        st.subheader("Security Assessor")
        st.markdown("Comprehensive security analysis of your scheme")

        if st.session_state.generated_schemes:
            assessor = SecurityAssessor()
            scheme = st.session_state.generated_schemes[0]
            assessment = assessor.assess_scheme(scheme)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Security Score", f"{assessment.get('overall_score', 0)}/100")
            with col2:
                st.metric("Threat Level", assessment.get('threat_level', 'UNKNOWN'))
            with col3:
                st.metric("Quantum Safe", "Yes" if assessment.get('quantum_readiness', {}).get('quantum_safe', False) else "No")

            st.markdown("### Vulnerabilities")
            st.json(assessment.get('vulnerabilities', []))
        else:
            st.info("Generate a scheme first to assess its security")

    with tool_tabs[2]:
        st.subheader("Component Recommender")
        st.markdown("Get intelligent component recommendations")

        col1, col2 = st.columns(2)
        with col1:
            security_level = st.slider("Security Level (bits):", 128, 256, 128, 64)
        with col2:
            performance = st.selectbox("Performance:", ["any", "very_high", "high", "medium", "low"])

        if st.button("Get Recommendations"):
            recommender = ComponentRecommender()
            requirements = {
                'security_level': security_level,
                'performance': performance
            }
            recommendations = recommender.recommend_components(requirements, num_recommendations=5)

            st.markdown("### 💡 Top Recommendations")
            for idx, rec in enumerate(recommendations):
                st.markdown(f"**{idx + 1}. {rec.get('name', 'Unknown')}** (Score: {rec.get('score', 0):.2f})")
                st.markdown(f"*{rec.get('rationale', 'No explanation available')}*")
                st.markdown("---")

    with tool_tabs[3]:
        st.subheader("Performance Estimator")
        st.markdown("Estimate performance across different platforms")

        platform = st.selectbox("Select Platform:", ["SERVER", "DESKTOP", "MOBILE", "IOT", "EMBEDDED"])
        data_size = st.slider("Data Size (MB):", 0.1, 100.0, 1.0)

        if st.session_state.generated_schemes:
            estimator = PerformanceEstimator()
            scheme = st.session_state.generated_schemes[0]
            perf = estimator.estimate_performance(scheme, Platform[platform], data_size)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Throughput", f"{perf.get('throughput_mbps', 0):.2f} MB/s")
            with col2:
                st.metric("Latency", f"{perf.get('latency_ms', 0):.2f} ms")
            with col3:
                st.metric("Memory", f"{perf.get('memory_kb', 0):.2f} KB")
        else:
            st.info("Generate a scheme first to estimate performance")


def render_export():
    """导出和分享"""
    st.header("📤 Export & Share")

    if not FEATURES_AVAILABLE or not st.session_state.generated_schemes:
        st.info("Generate a scheme first to export")
        return

    exporter = SchemeExporter()
    scheme = st.session_state.generated_schemes[0]

    st.markdown("### Export Formats")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📄 JSON", use_container_width=True):
            json_output = exporter.export_to_json(scheme)
            st.download_button("Download JSON", json_output, "scheme.json", "application/json")

    with col2:
        if st.button("📝 Markdown", use_container_width=True):
            md_output = exporter.export_to_markdown(scheme)
            st.download_button("Download MD", md_output, "scheme.md", "text/markdown")

    with col3:
        if st.button("📚 LaTeX", use_container_width=True):
            latex_output = exporter.export_to_latex(scheme)
            st.download_button("Download LaTeX", latex_output, "scheme.tex", "text/plain")

    with col4:
        if st.button("📋 YAML", use_container_width=True):
            yaml_output = exporter.export_to_yaml(scheme)
            st.download_button("Download YAML", yaml_output, "scheme.yaml", "text/yaml")

    st.markdown("---")
    st.markdown("### 🔗 Share")

    if st.button("Generate Shareable Link"):
        link = exporter.create_shareable_link(scheme)
        st.code(link, language=None)
        st.success("✅ Link generated! Share this with others.")


def main():
    """主函数"""
    init_session_state()
    render_header()

    # 主导航
    tabs = st.tabs(["🏠 Home", "📚 Library", "🎓 Tutorials", "🛠️ Tools", "📤 Export"])

    with tabs[0]:
        render_home_tab()

    with tabs[1]:
        render_component_library()

    with tabs[2]:
        render_tutorials()

    with tabs[3]:
        render_tools()

    with tabs[4]:
        render_export()

    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p><strong>CipherGenius Enhanced v2.0</strong> - 152 Components | AI-Powered | Open Source</p>
        <p>Built with ❤️ for the cryptography community</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
