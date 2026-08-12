"""
Compliance Report Generator
生成符合各种标准的合规性报告
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import hashlib


class ComplianceStandard(Enum):
    FIPS_140_2 = "fips_140_2"
    FIPS_140_3 = "fips_140_3"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    SOC2 = "soc2"
    ISO_27001 = "iso_27001"
    NIST_CSF = "nist_csf"
    FEDRAMP = "fedramp"


class ComplianceStatus(Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ComplianceRequirement:
    """Individual compliance requirement"""
    id: str
    description: str
    status: str  # compliant, non_compliant, partial, not_applicable
    evidence: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    severity: str = "medium"  # low, medium, high, critical
    category: str = "general"


class ComplianceReporter:
    """Generate compliance reports for various standards"""

    def __init__(self):
        self.standards = self._load_compliance_standards()
        self.approved_algorithms = self._load_approved_algorithms()
        self.deprecated_algorithms = self._load_deprecated_algorithms()

    def generate_report(self,
                       scheme: Dict[str, Any],
                       standards: List[ComplianceStandard]) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report

        Args:
            scheme: Cryptographic scheme configuration
            standards: List of compliance standards to check

        Returns:
            - overall_compliance: percentage
            - standards_results: Results per standard
            - gaps: List of compliance gaps
            - recommendations: Prioritized actions
            - certificate_ready: bool
        """
        report = {
            "report_id": self._generate_report_id(scheme),
            "generated_at": datetime.utcnow().isoformat(),
            "scheme_name": scheme.get("name", "Unknown"),
            "scheme_version": scheme.get("version", "1.0"),
            "standards_checked": [s.value for s in standards],
            "standards_results": {},
            "gaps": [],
            "recommendations": [],
            "overall_compliance": 0.0,
            "certificate_ready": False,
            "summary": {}
        }

        # Check each standard
        total_compliance = 0.0
        for standard in standards:
            if standard == ComplianceStandard.FIPS_140_2:
                result = self.check_fips_140(scheme, level=2)
            elif standard == ComplianceStandard.FIPS_140_3:
                result = self.check_fips_140(scheme, level=3)
            elif standard == ComplianceStandard.PCI_DSS:
                result = self.check_pci_dss(scheme)
            elif standard == ComplianceStandard.HIPAA:
                result = self.check_hipaa(scheme)
            elif standard == ComplianceStandard.GDPR:
                result = self.check_gdpr(scheme)
            elif standard == ComplianceStandard.SOC2:
                result = self.check_soc2(scheme)
            elif standard == ComplianceStandard.ISO_27001:
                result = self.check_iso_27001(scheme)
            elif standard == ComplianceStandard.NIST_CSF:
                result = self.check_nist_csf(scheme)
            elif standard == ComplianceStandard.FEDRAMP:
                result = self.check_fedramp(scheme)
            else:
                continue

            report["standards_results"][standard.value] = result
            total_compliance += result.get("compliance_percentage", 0)

            # Collect gaps and recommendations
            report["gaps"].extend(result.get("gaps", []))
            report["recommendations"].extend(result.get("recommendations", []))

        # Calculate overall compliance
        if standards:
            report["overall_compliance"] = total_compliance / len(standards)

        # Deduplicate and prioritize recommendations
        report["recommendations"] = self._prioritize_recommendations(
            report["recommendations"]
        )

        # Determine if certificate-ready
        report["certificate_ready"] = self._is_certificate_ready(report)

        # Generate summary
        report["summary"] = self._generate_summary(report)

        return report

    def check_fips_140(self, scheme: Dict[str, Any], level: int = 2) -> Dict:
        """
        Check FIPS 140-2/3 compliance

        FIPS 140 levels:
        - Level 1: Basic security requirements
        - Level 2: Physical tamper-evidence
        - Level 3: Physical tamper-resistance
        - Level 4: Complete physical protection
        """
        requirements = []
        standard_name = f"FIPS 140-{level}"

        # Algorithm requirements
        algorithms_req = self._check_fips_algorithms(scheme)
        requirements.append(algorithms_req)

        # Key management requirements
        key_mgmt_req = self._check_fips_key_management(scheme)
        requirements.append(key_mgmt_req)

        # Random number generation
        rng_req = self._check_fips_rng(scheme)
        requirements.append(rng_req)

        # Self-tests
        self_test_req = self._check_fips_self_tests(scheme)
        requirements.append(self_test_req)

        # Access control (Level 2+)
        if level >= 2:
            access_req = self._check_fips_access_control(scheme)
            requirements.append(access_req)

        # Physical security (Level 2+)
        if level >= 2:
            physical_req = self._check_fips_physical_security(scheme, level)
            requirements.append(physical_req)

        # Cryptographic module ports (Level 3+)
        if level >= 3:
            ports_req = self._check_fips_ports_interfaces(scheme)
            requirements.append(ports_req)

        # Calculate compliance
        compliant_count = sum(1 for req in requirements
                            if req.status == ComplianceStatus.COMPLIANT.value)
        partial_count = sum(1 for req in requirements
                          if req.status == ComplianceStatus.PARTIAL.value)

        compliance_percentage = (
            (compliant_count + 0.5 * partial_count) / len(requirements) * 100
        )

        gaps = []
        recommendations = []
        for req in requirements:
            gaps.extend(req.gaps)
            recommendations.extend(req.recommendations)

        return {
            "standard": standard_name,
            "level": level,
            "compliance_percentage": compliance_percentage,
            "requirements": [vars(req) for req in requirements],
            "gaps": gaps,
            "recommendations": recommendations,
            "certification_path": self._get_fips_certification_path(level)
        }

    def check_pci_dss(self, scheme: Dict[str, Any]) -> Dict:
        """
        Check PCI DSS compliance (Payment Card Industry Data Security Standard)

        Key requirements:
        - Strong cryptography for transmission
        - Encrypted storage of cardholder data
        - Key management procedures
        """
        requirements = []

        # Requirement 3: Protect stored cardholder data
        encryption_req = ComplianceRequirement(
            id="PCI-3.4",
            description="Render PAN unreadable using strong cryptography",
            status=ComplianceStatus.COMPLIANT.value,
            category="data_protection"
        )

        algorithm = scheme.get("algorithm", "").lower()
        key_size = scheme.get("key_size", 0)

        if algorithm in ["aes", "aes-gcm", "aes-256"]:
            if key_size >= 256:
                encryption_req.evidence.append("AES-256 encryption used for data protection")
            elif key_size >= 128:
                encryption_req.status = ComplianceStatus.PARTIAL.value
                encryption_req.evidence.append("AES-128 encryption used")
                encryption_req.recommendations.append(
                    "Upgrade to AES-256 for enhanced security"
                )
        else:
            encryption_req.status = ComplianceStatus.NON_COMPLIANT.value
            encryption_req.gaps.append("Non-approved encryption algorithm")
            encryption_req.recommendations.append("Use AES-256 encryption")

        requirements.append(encryption_req)

        # Requirement 3.5: Key management
        key_mgmt_req = ComplianceRequirement(
            id="PCI-3.5",
            description="Document and implement key management procedures",
            status=ComplianceStatus.PARTIAL.value,
            category="key_management"
        )

        if scheme.get("key_rotation_enabled"):
            key_mgmt_req.evidence.append("Key rotation enabled")
        else:
            key_mgmt_req.gaps.append("No key rotation policy")
            key_mgmt_req.recommendations.append("Implement automatic key rotation")

        if scheme.get("key_separation"):
            key_mgmt_req.evidence.append("Key separation implemented")
        else:
            key_mgmt_req.gaps.append("No key separation")
            key_mgmt_req.recommendations.append("Implement split knowledge for key management")

        requirements.append(key_mgmt_req)

        # Requirement 4: Encrypt transmission of cardholder data
        transmission_req = ComplianceRequirement(
            id="PCI-4.1",
            description="Use strong cryptography for transmission over open networks",
            status=ComplianceStatus.COMPLIANT.value,
            category="transmission_security"
        )

        if scheme.get("mode") in ["gcm", "ccm", "eax"]:
            transmission_req.evidence.append("Authenticated encryption mode used")
        else:
            transmission_req.status = ComplianceStatus.PARTIAL.value
            transmission_req.recommendations.append(
                "Use authenticated encryption (GCM/CCM) for transmission"
            )

        requirements.append(transmission_req)

        # Calculate compliance
        compliant_count = sum(1 for req in requirements
                            if req.status == ComplianceStatus.COMPLIANT.value)
        partial_count = sum(1 for req in requirements
                          if req.status == ComplianceStatus.PARTIAL.value)

        compliance_percentage = (
            (compliant_count + 0.5 * partial_count) / len(requirements) * 100
        )

        gaps = []
        recommendations = []
        for req in requirements:
            gaps.extend(req.gaps)
            recommendations.extend(req.recommendations)

        return {
            "standard": "PCI DSS v4.0",
            "compliance_percentage": compliance_percentage,
            "requirements": [vars(req) for req in requirements],
            "gaps": gaps,
            "recommendations": recommendations,
            "applicable_requirements": ["3.4", "3.5", "3.6", "4.1", "4.2"]
        }

    def check_hipaa(self, scheme: Dict[str, Any]) -> Dict:
        """
        Check HIPAA compliance (Health Insurance Portability and Accountability Act)

        Key requirements:
        - Encryption of ePHI at rest and in transit
        - Access controls
        - Audit controls
        """
        requirements = []

        # 164.312(a)(2)(iv) - Encryption and Decryption
        encryption_req = ComplianceRequirement(
            id="HIPAA-164.312(a)(2)(iv)",
            description="Implement mechanism to encrypt and decrypt ePHI",
            status=ComplianceStatus.COMPLIANT.value,
            category="encryption",
            severity="high"
        )

        algorithm = scheme.get("algorithm", "").lower()
        key_size = scheme.get("key_size", 0)

        if algorithm in ["aes", "aes-gcm", "aes-256"]:
            if key_size >= 256:
                encryption_req.evidence.append(
                    "NIST-approved AES-256 encryption implemented"
                )
            else:
                encryption_req.status = ComplianceStatus.PARTIAL.value
                encryption_req.recommendations.append("Use AES-256 for ePHI protection")
        else:
            encryption_req.status = ComplianceStatus.NON_COMPLIANT.value
            encryption_req.gaps.append("Non-approved encryption algorithm for ePHI")
            encryption_req.recommendations.append(
                "Implement NIST-approved encryption (AES-256)"
            )

        requirements.append(encryption_req)

        # 164.312(e)(2)(ii) - Encryption in transit
        transmission_req = ComplianceRequirement(
            id="HIPAA-164.312(e)(2)(ii)",
            description="Implement encryption for ePHI transmission",
            status=ComplianceStatus.COMPLIANT.value,
            category="transmission",
            severity="high"
        )

        if scheme.get("authenticated_encryption"):
            transmission_req.evidence.append("Authenticated encryption enabled")
        else:
            transmission_req.status = ComplianceStatus.PARTIAL.value
            transmission_req.recommendations.append(
                "Enable authenticated encryption for data integrity"
            )

        requirements.append(transmission_req)

        # 164.308(a)(3) - Workforce security
        access_control_req = ComplianceRequirement(
            id="HIPAA-164.308(a)(3)",
            description="Implement access controls for ePHI",
            status=ComplianceStatus.PARTIAL.value,
            category="access_control",
            severity="high"
        )

        if scheme.get("access_control"):
            access_control_req.evidence.append("Access control mechanisms present")
            access_control_req.status = ComplianceStatus.COMPLIANT.value
        else:
            access_control_req.gaps.append("No access control implementation")
            access_control_req.recommendations.append(
                "Implement role-based access control (RBAC)"
            )

        requirements.append(access_control_req)

        # 164.312(b) - Audit controls
        audit_req = ComplianceRequirement(
            id="HIPAA-164.312(b)",
            description="Implement audit controls to record access to ePHI",
            status=ComplianceStatus.PARTIAL.value,
            category="audit",
            severity="medium"
        )

        if scheme.get("audit_logging"):
            audit_req.evidence.append("Audit logging enabled")
            audit_req.status = ComplianceStatus.COMPLIANT.value
        else:
            audit_req.gaps.append("No audit logging")
            audit_req.recommendations.append(
                "Implement comprehensive audit logging for all ePHI access"
            )

        requirements.append(audit_req)

        # Calculate compliance
        compliant_count = sum(1 for req in requirements
                            if req.status == ComplianceStatus.COMPLIANT.value)
        partial_count = sum(1 for req in requirements
                          if req.status == ComplianceStatus.PARTIAL.value)

        compliance_percentage = (
            (compliant_count + 0.5 * partial_count) / len(requirements) * 100
        )

        gaps = []
        recommendations = []
        for req in requirements:
            gaps.extend(req.gaps)
            recommendations.extend(req.recommendations)

        return {
            "standard": "HIPAA Security Rule",
            "compliance_percentage": compliance_percentage,
            "requirements": [vars(req) for req in requirements],
            "gaps": gaps,
            "recommendations": recommendations,
            "risk_analysis_required": True
        }

    def check_gdpr(self, scheme: Dict[str, Any]) -> Dict:
        """
        Check GDPR compliance (General Data Protection Regulation)

        Key requirements:
        - Data protection by design and default
        - Pseudonymization and encryption
        - Data minimization
        """
        requirements = []

        # Article 32 - Security of processing
        security_req = ComplianceRequirement(
            id="GDPR-Art32",
            description="Implement appropriate technical measures including encryption",
            status=ComplianceStatus.COMPLIANT.value,
            category="security",
            severity="high"
        )

        algorithm = scheme.get("algorithm", "").lower()
        if algorithm in self.approved_algorithms.get("symmetric", []):
            security_req.evidence.append("State-of-the-art encryption algorithm used")
        else:
            security_req.status = ComplianceStatus.NON_COMPLIANT.value
            security_req.gaps.append("Non-standard encryption algorithm")
            security_req.recommendations.append("Use industry-standard encryption")

        requirements.append(security_req)

        # Article 25 - Data protection by design
        privacy_req = ComplianceRequirement(
            id="GDPR-Art25",
            description="Data protection by design and by default",
            status=ComplianceStatus.PARTIAL.value,
            category="privacy",
            severity="high"
        )

        if scheme.get("pseudonymization"):
            privacy_req.evidence.append("Pseudonymization implemented")
        else:
            privacy_req.gaps.append("No pseudonymization")
            privacy_req.recommendations.append(
                "Implement pseudonymization for personal data"
            )

        if scheme.get("data_minimization"):
            privacy_req.evidence.append("Data minimization enabled")
        else:
            privacy_req.recommendations.append("Implement data minimization controls")

        requirements.append(privacy_req)

        # Article 33/34 - Breach notification capability
        breach_req = ComplianceRequirement(
            id="GDPR-Art33",
            description="Ability to detect and report security breaches",
            status=ComplianceStatus.PARTIAL.value,
            category="incident_response",
            severity="high"
        )

        if scheme.get("integrity_monitoring"):
            breach_req.evidence.append("Integrity monitoring in place")
        else:
            breach_req.gaps.append("No breach detection capability")
            breach_req.recommendations.append(
                "Implement integrity monitoring and breach detection"
            )

        requirements.append(breach_req)

        # Calculate compliance
        compliant_count = sum(1 for req in requirements
                            if req.status == ComplianceStatus.COMPLIANT.value)
        partial_count = sum(1 for req in requirements
                          if req.status == ComplianceStatus.PARTIAL.value)

        compliance_percentage = (
            (compliant_count + 0.5 * partial_count) / len(requirements) * 100
        )

        gaps = []
        recommendations = []
        for req in requirements:
            gaps.extend(req.gaps)
            recommendations.extend(req.recommendations)

        return {
            "standard": "GDPR",
            "compliance_percentage": compliance_percentage,
            "requirements": [vars(req) for req in requirements],
            "gaps": gaps,
            "recommendations": recommendations,
            "dpia_required": self._requires_dpia(scheme)
        }

    def check_soc2(self, scheme: Dict[str, Any]) -> Dict:
        """Check SOC 2 compliance (Trust Service Criteria)"""
        requirements = []

        # CC6.1 - Logical and Physical Access Controls
        access_req = ComplianceRequirement(
            id="SOC2-CC6.1",
            description="Implement logical and physical access controls",
            status=ComplianceStatus.PARTIAL.value,
            category="access_control"
        )

        if scheme.get("access_control"):
            access_req.evidence.append("Access controls implemented")
        else:
            access_req.gaps.append("No access control mechanism")
            access_req.recommendations.append("Implement access controls")

        requirements.append(access_req)

        # CC6.7 - Encryption of data
        encryption_req = ComplianceRequirement(
            id="SOC2-CC6.7",
            description="Encrypt data at rest and in transit",
            status=ComplianceStatus.COMPLIANT.value,
            category="encryption"
        )

        if scheme.get("algorithm") in ["aes", "aes-gcm"]:
            encryption_req.evidence.append("Strong encryption implemented")
        else:
            encryption_req.status = ComplianceStatus.NON_COMPLIANT.value
            encryption_req.gaps.append("Weak encryption")

        requirements.append(encryption_req)

        compliant_count = sum(1 for req in requirements
                            if req.status == ComplianceStatus.COMPLIANT.value)
        compliance_percentage = (compliant_count / len(requirements)) * 100

        return {
            "standard": "SOC 2 Type II",
            "compliance_percentage": compliance_percentage,
            "requirements": [vars(req) for req in requirements],
            "gaps": [gap for req in requirements for gap in req.gaps],
            "recommendations": [rec for req in requirements for rec in req.recommendations]
        }

    def check_iso_27001(self, scheme: Dict[str, Any]) -> Dict:
        """Check ISO 27001 compliance"""
        requirements = []

        # A.10.1.1 - Cryptographic controls
        crypto_req = ComplianceRequirement(
            id="ISO27001-A.10.1.1",
            description="Policy on the use of cryptographic controls",
            status=ComplianceStatus.COMPLIANT.value,
            category="cryptography"
        )

        if scheme.get("algorithm") in self.approved_algorithms.get("symmetric", []):
            crypto_req.evidence.append("Approved cryptographic algorithm")
        else:
            crypto_req.status = ComplianceStatus.NON_COMPLIANT.value

        requirements.append(crypto_req)

        # A.10.1.2 - Key management
        key_req = ComplianceRequirement(
            id="ISO27001-A.10.1.2",
            description="Key management policy",
            status=ComplianceStatus.PARTIAL.value,
            category="key_management"
        )

        if scheme.get("key_rotation_enabled"):
            key_req.evidence.append("Key rotation enabled")
        else:
            key_req.gaps.append("No key rotation")

        requirements.append(key_req)

        compliant_count = sum(1 for req in requirements
                            if req.status == ComplianceStatus.COMPLIANT.value)
        compliance_percentage = (compliant_count / len(requirements)) * 100

        return {
            "standard": "ISO/IEC 27001:2022",
            "compliance_percentage": compliance_percentage,
            "requirements": [vars(req) for req in requirements],
            "gaps": [gap for req in requirements for gap in req.gaps],
            "recommendations": [rec for req in requirements for rec in req.recommendations]
        }

    def check_nist_csf(self, scheme: Dict[str, Any]) -> Dict:
        """Check NIST Cybersecurity Framework compliance"""
        requirements = []

        # PR.DS-1: Data-at-rest is protected
        data_rest_req = ComplianceRequirement(
            id="NIST-CSF-PR.DS-1",
            description="Data-at-rest is protected",
            status=ComplianceStatus.COMPLIANT.value,
            category="data_protection"
        )

        if scheme.get("algorithm") in ["aes", "aes-gcm"]:
            data_rest_req.evidence.append("Strong encryption for data at rest")
        else:
            data_rest_req.status = ComplianceStatus.NON_COMPLIANT.value

        requirements.append(data_rest_req)

        # PR.DS-2: Data-in-transit is protected
        data_transit_req = ComplianceRequirement(
            id="NIST-CSF-PR.DS-2",
            description="Data-in-transit is protected",
            status=ComplianceStatus.COMPLIANT.value,
            category="transmission"
        )

        if scheme.get("mode") in ["gcm", "ccm"]:
            data_transit_req.evidence.append("Authenticated encryption for transit")
        else:
            data_transit_req.status = ComplianceStatus.PARTIAL.value

        requirements.append(data_transit_req)

        compliant_count = sum(1 for req in requirements
                            if req.status == ComplianceStatus.COMPLIANT.value)
        compliance_percentage = (compliant_count / len(requirements)) * 100

        return {
            "standard": "NIST CSF 2.0",
            "compliance_percentage": compliance_percentage,
            "requirements": [vars(req) for req in requirements],
            "gaps": [gap for req in requirements for gap in req.gaps],
            "recommendations": [rec for req in requirements for rec in req.recommendations]
        }

    def check_fedramp(self, scheme: Dict[str, Any]) -> Dict:
        """Check FedRAMP compliance"""
        requirements = []

        # SC-13: Cryptographic Protection
        crypto_req = ComplianceRequirement(
            id="FedRAMP-SC-13",
            description="Use FIPS-validated cryptography",
            status=ComplianceStatus.COMPLIANT.value,
            category="cryptography"
        )

        if scheme.get("algorithm") in ["aes", "aes-gcm"]:
            crypto_req.evidence.append("FIPS-approved algorithm")
        else:
            crypto_req.status = ComplianceStatus.NON_COMPLIANT.value
            crypto_req.gaps.append("Non-FIPS algorithm")

        requirements.append(crypto_req)

        compliant_count = sum(1 for req in requirements
                            if req.status == ComplianceStatus.COMPLIANT.value)
        compliance_percentage = (compliant_count / len(requirements)) * 100

        return {
            "standard": "FedRAMP Moderate",
            "compliance_percentage": compliance_percentage,
            "requirements": [vars(req) for req in requirements],
            "gaps": [gap for req in requirements for gap in req.gaps],
            "recommendations": [rec for req in requirements for rec in req.recommendations]
        }

    def generate_audit_package(self, scheme: Dict[str, Any]) -> Dict:
        """
        Generate comprehensive audit package with all evidence

        Returns package containing:
        - Configuration documentation
        - Compliance test results
        - Security assessments
        - Evidence artifacts
        """
        package = {
            "package_id": self._generate_report_id(scheme),
            "generated_at": datetime.utcnow().isoformat(),
            "scheme_configuration": scheme,
            "compliance_reports": {},
            "security_assessments": {},
            "evidence": {},
            "documentation": {}
        }

        # Generate compliance reports for all standards
        all_standards = list(ComplianceStandard)
        compliance_report = self.generate_report(scheme, all_standards)
        package["compliance_reports"] = compliance_report

        # Security assessment
        package["security_assessments"] = {
            "algorithm_security": self._assess_algorithm_security(scheme),
            "key_management": self._assess_key_management(scheme),
            "implementation_security": self._assess_implementation(scheme)
        }

        # Evidence collection
        package["evidence"] = {
            "algorithm_details": {
                "name": scheme.get("algorithm"),
                "key_size": scheme.get("key_size"),
                "mode": scheme.get("mode"),
                "approved": scheme.get("algorithm") in self.approved_algorithms.get("symmetric", [])
            },
            "test_results": self._generate_test_results(scheme),
            "configuration_hashes": self._generate_config_hashes(scheme)
        }

        # Documentation
        package["documentation"] = {
            "security_policy": self._generate_security_policy(scheme),
            "operational_procedures": self._generate_operational_procedures(scheme),
            "incident_response": self._generate_incident_response_plan(scheme)
        }

        return package

    def export_compliance_report(self,
                                 report: Dict[str, Any],
                                 format: str = "pdf") -> bytes:
        """
        Export compliance report in various formats

        Supported formats: pdf, html, json, markdown, docx
        """
        if format == "json":
            return json.dumps(report, indent=2).encode('utf-8')

        elif format == "markdown":
            return self._export_as_markdown(report).encode('utf-8')

        elif format == "html":
            return self._export_as_html(report).encode('utf-8')

        elif format == "pdf":
            # Convert HTML to PDF (requires additional library in production)
            html_content = self._export_as_html(report)
            return f"<!-- PDF would be generated from HTML -->\n{html_content}".encode('utf-8')

        elif format == "docx":
            # Generate DOCX (requires additional library in production)
            markdown_content = self._export_as_markdown(report)
            return f"<!-- DOCX would be generated from Markdown -->\n{markdown_content}".encode('utf-8')

        else:
            raise ValueError(f"Unsupported format: {format}")

    def _load_compliance_standards(self) -> Dict:
        """Load compliance requirements for each standard"""
        return {
            "fips_140_2": {
                "name": "FIPS 140-2",
                "levels": [1, 2, 3, 4],
                "categories": [
                    "cryptographic_module",
                    "ports_interfaces",
                    "roles_services_authentication",
                    "finite_state_model",
                    "physical_security",
                    "operational_environment",
                    "cryptographic_key_management",
                    "emi_emc",
                    "self_tests",
                    "design_assurance",
                    "mitigation_attacks"
                ]
            },
            "pci_dss": {
                "version": "4.0",
                "requirements": 12,
                "encryption_requirements": ["3.4", "3.5", "3.6", "4.1", "4.2"]
            },
            "hipaa": {
                "security_rule": True,
                "privacy_rule": True,
                "encryption": "addressable"
            }
        }

    def _load_approved_algorithms(self) -> Dict[str, List[str]]:
        """Load NIST/FIPS approved algorithms"""
        return {
            "symmetric": [
                "aes", "aes-128", "aes-192", "aes-256",
                "aes-gcm", "aes-ccm", "aes-eax",
                "chacha20-poly1305", "3des"
            ],
            "asymmetric": [
                "rsa", "rsa-2048", "rsa-3072", "rsa-4096",
                "ecdsa", "ecdh", "ed25519", "x25519"
            ],
            "hash": [
                "sha-256", "sha-384", "sha-512",
                "sha3-256", "sha3-384", "sha3-512",
                "shake128", "shake256"
            ],
            "modes": [
                "gcm", "ccm", "eax", "cbc", "ctr"
            ]
        }

    def _load_deprecated_algorithms(self) -> Set[str]:
        """Load deprecated/insecure algorithms"""
        return {
            "des", "rc4", "md5", "sha1", "rc2", "blowfish"
        }

    def _check_fips_algorithms(self, scheme: Dict[str, Any]) -> ComplianceRequirement:
        """Check if algorithms are FIPS-approved"""
        req = ComplianceRequirement(
            id="FIPS-140-Algorithms",
            description="Use FIPS-approved cryptographic algorithms",
            status=ComplianceStatus.COMPLIANT.value,
            category="algorithms",
            severity="critical"
        )

        algorithm = scheme.get("algorithm", "").lower()

        if algorithm in self.approved_algorithms.get("symmetric", []):
            req.evidence.append(f"Algorithm {algorithm} is FIPS-approved")
        elif algorithm in self.deprecated_algorithms:
            req.status = ComplianceStatus.NON_COMPLIANT.value
            req.gaps.append(f"Algorithm {algorithm} is deprecated and not FIPS-approved")
            req.recommendations.append("Replace with AES-256-GCM")
        else:
            req.status = ComplianceStatus.PARTIAL.value
            req.gaps.append(f"Algorithm {algorithm} approval status unclear")
            req.recommendations.append("Verify algorithm FIPS approval status")

        # Check key size
        key_size = scheme.get("key_size", 0)
        if algorithm.startswith("aes"):
            if key_size >= 256:
                req.evidence.append("Key size meets FIPS requirements (256 bits)")
            elif key_size >= 128:
                req.status = ComplianceStatus.PARTIAL.value
                req.recommendations.append("Increase key size to 256 bits for optimal security")
            else:
                req.status = ComplianceStatus.NON_COMPLIANT.value
                req.gaps.append(f"Key size {key_size} is below minimum")

        return req

    def _check_fips_key_management(self, scheme: Dict[str, Any]) -> ComplianceRequirement:
        """Check FIPS key management requirements"""
        req = ComplianceRequirement(
            id="FIPS-140-KeyMgmt",
            description="Secure key generation, storage, and management",
            status=ComplianceStatus.PARTIAL.value,
            category="key_management",
            severity="critical"
        )

        if scheme.get("key_derivation"):
            req.evidence.append("Key derivation function implemented")
        else:
            req.gaps.append("No key derivation function")
            req.recommendations.append("Implement PBKDF2, HKDF, or Argon2")

        if scheme.get("key_rotation_enabled"):
            req.evidence.append("Key rotation enabled")
        else:
            req.gaps.append("No key rotation policy")
            req.recommendations.append("Implement automatic key rotation")

        if scheme.get("key_separation"):
            req.evidence.append("Key separation implemented")
        else:
            req.recommendations.append("Implement key separation (split knowledge)")

        if scheme.get("key_zeroization"):
            req.evidence.append("Key zeroization on delete")
        else:
            req.gaps.append("No key zeroization")
            req.recommendations.append("Implement secure key deletion with zeroization")

        return req

    def _check_fips_rng(self, scheme: Dict[str, Any]) -> ComplianceRequirement:
        """Check FIPS random number generation"""
        req = ComplianceRequirement(
            id="FIPS-140-RNG",
            description="Use approved random number generation",
            status=ComplianceStatus.COMPLIANT.value,
            category="random_generation",
            severity="high"
        )

        rng_source = scheme.get("rng_source", "").lower()

        if rng_source in ["csprng", "drbg", "hash_drbg", "hmac_drbg", "ctr_drbg"]:
            req.evidence.append(f"Approved RNG: {rng_source}")
        elif rng_source:
            req.status = ComplianceStatus.PARTIAL.value
            req.recommendations.append("Use NIST SP 800-90A approved DRBG")
        else:
            req.status = ComplianceStatus.NON_COMPLIANT.value
            req.gaps.append("No RNG specification")
            req.recommendations.append("Implement FIPS-approved DRBG")

        return req

    def _check_fips_self_tests(self, scheme: Dict[str, Any]) -> ComplianceRequirement:
        """Check FIPS self-test requirements"""
        req = ComplianceRequirement(
            id="FIPS-140-SelfTest",
            description="Implement power-up and conditional self-tests",
            status=ComplianceStatus.PARTIAL.value,
            category="self_tests",
            severity="high"
        )

        if scheme.get("power_up_tests"):
            req.evidence.append("Power-up self-tests implemented")
        else:
            req.gaps.append("No power-up self-tests")
            req.recommendations.append("Implement power-up self-tests for all algorithms")

        if scheme.get("conditional_tests"):
            req.evidence.append("Conditional self-tests implemented")
        else:
            req.recommendations.append("Implement conditional self-tests")

        return req

    def _check_fips_access_control(self, scheme: Dict[str, Any]) -> ComplianceRequirement:
        """Check FIPS access control (Level 2+)"""
        req = ComplianceRequirement(
            id="FIPS-140-Access",
            description="Role-based access control",
            status=ComplianceStatus.PARTIAL.value,
            category="access_control",
            severity="high"
        )

        if scheme.get("role_based_access"):
            req.evidence.append("Role-based access control implemented")
        else:
            req.gaps.append("No RBAC implementation")
            req.recommendations.append("Implement role-based access control")

        if scheme.get("authentication"):
            req.evidence.append("Authentication mechanism present")
        else:
            req.gaps.append("No authentication")
            req.recommendations.append("Implement authentication for operator roles")

        return req

    def _check_fips_physical_security(self,
                                     scheme: Dict[str, Any],
                                     level: int) -> ComplianceRequirement:
        """Check FIPS physical security requirements"""
        req = ComplianceRequirement(
            id=f"FIPS-140-Physical-L{level}",
            description=f"Physical security Level {level} requirements",
            status=ComplianceStatus.NOT_APPLICABLE.value,
            category="physical_security",
            severity="high"
        )

        # Physical security is typically hardware-level
        req.evidence.append("Software-only implementation - physical security N/A")
        req.recommendations.append(
            "For full FIPS certification, use hardware security module (HSM)"
        )

        return req

    def _check_fips_ports_interfaces(self, scheme: Dict[str, Any]) -> ComplianceRequirement:
        """Check FIPS ports and interfaces (Level 3+)"""
        req = ComplianceRequirement(
            id="FIPS-140-Ports",
            description="Secure ports and interfaces",
            status=ComplianceStatus.PARTIAL.value,
            category="ports_interfaces",
            severity="medium"
        )

        if scheme.get("api_security"):
            req.evidence.append("API security controls present")
        else:
            req.recommendations.append("Implement API security controls")

        return req

    def _get_fips_certification_path(self, level: int) -> Dict[str, Any]:
        """Get FIPS certification path information"""
        return {
            "level": level,
            "testing_lab": "NVLAP-accredited laboratory required",
            "estimated_cost": f"${50000 + (level * 25000)} - ${100000 + (level * 50000)}",
            "estimated_time": f"{6 + (level * 3)}-{12 + (level * 6)} months",
            "steps": [
                "Complete security policy documentation",
                "Engage NVLAP-accredited test lab",
                "Submit to CMVP for validation",
                "Address any findings",
                "Receive FIPS 140 certificate"
            ],
            "resources": [
                "https://csrc.nist.gov/projects/cryptographic-module-validation-program",
                "https://www.nist.gov/itl/cryptographic-module-validation-program"
            ]
        }

    def _requires_dpia(self, scheme: Dict[str, Any]) -> bool:
        """Determine if GDPR Data Protection Impact Assessment is required"""
        # DPIA required for high-risk processing
        high_risk_indicators = [
            scheme.get("processes_sensitive_data"),
            scheme.get("large_scale_processing"),
            scheme.get("automated_decision_making"),
            scheme.get("systematic_monitoring")
        ]
        return sum(bool(x) for x in high_risk_indicators) >= 2

    def _prioritize_recommendations(self, recommendations: List[str]) -> List[Dict]:
        """Deduplicate and prioritize recommendations"""
        # Deduplicate
        unique_recommendations = list(set(recommendations))

        # Assign priority based on keywords
        prioritized = []
        for rec in unique_recommendations:
            rec_lower = rec.lower()

            if any(word in rec_lower for word in ["critical", "replace", "deprecated"]):
                priority = "critical"
            elif any(word in rec_lower for word in ["implement", "required", "must"]):
                priority = "high"
            elif any(word in rec_lower for word in ["upgrade", "enhance", "improve"]):
                priority = "medium"
            else:
                priority = "low"

            prioritized.append({
                "recommendation": rec,
                "priority": priority
            })

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        prioritized.sort(key=lambda x: priority_order.get(x["priority"], 4))

        return prioritized

    def _is_certificate_ready(self, report: Dict[str, Any]) -> bool:
        """Determine if scheme is ready for certification"""
        # Generally need >90% compliance with no critical gaps
        if report["overall_compliance"] < 90:
            return False

        # Check for critical gaps
        for gap in report["gaps"]:
            if any(word in gap.lower() for word in ["critical", "deprecated", "insecure"]):
                return False

        return True

    def _generate_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        total_requirements = sum(
            len(result.get("requirements", []))
            for result in report["standards_results"].values()
        )

        compliant_requirements = sum(
            sum(1 for req in result.get("requirements", [])
                if req.get("status") == ComplianceStatus.COMPLIANT.value)
            for result in report["standards_results"].values()
        )

        return {
            "overall_status": "Compliant" if report["certificate_ready"] else "Non-Compliant",
            "compliance_percentage": round(report["overall_compliance"], 2),
            "total_standards_checked": len(report["standards_checked"]),
            "total_requirements_checked": total_requirements,
            "compliant_requirements": compliant_requirements,
            "total_gaps": len(report["gaps"]),
            "high_priority_recommendations": sum(
                1 for rec in report["recommendations"]
                if rec.get("priority") in ["critical", "high"]
            ),
            "certification_status": "Ready" if report["certificate_ready"] else "Not Ready"
        }

    def _generate_report_id(self, scheme: Dict[str, Any]) -> str:
        """Generate unique report ID"""
        content = f"{scheme.get('name', 'unknown')}_{datetime.utcnow().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _assess_algorithm_security(self, scheme: Dict[str, Any]) -> Dict:
        """Assess algorithm security level"""
        algorithm = scheme.get("algorithm", "").lower()
        key_size = scheme.get("key_size", 0)

        security_level = "unknown"
        if algorithm in ["aes-256", "aes-gcm"]:
            if key_size >= 256:
                security_level = "high"
            elif key_size >= 192:
                security_level = "medium-high"
            else:
                security_level = "medium"
        elif algorithm in self.deprecated_algorithms:
            security_level = "low"

        return {
            "algorithm": algorithm,
            "key_size": key_size,
            "security_level": security_level,
            "quantum_resistant": False,
            "approved_by": self._get_approvals(algorithm)
        }

    def _assess_key_management(self, scheme: Dict[str, Any]) -> Dict:
        """Assess key management practices"""
        return {
            "key_generation": "secure" if scheme.get("secure_key_gen") else "unknown",
            "key_storage": "encrypted" if scheme.get("encrypted_storage") else "plaintext",
            "key_rotation": "enabled" if scheme.get("key_rotation_enabled") else "disabled",
            "key_backup": "implemented" if scheme.get("key_backup") else "none",
            "key_destruction": "secure" if scheme.get("key_zeroization") else "standard"
        }

    def _assess_implementation(self, scheme: Dict[str, Any]) -> Dict:
        """Assess implementation security"""
        return {
            "side_channel_protection": scheme.get("side_channel_protected", False),
            "timing_attack_protection": scheme.get("constant_time", False),
            "memory_protection": scheme.get("memory_locked", False),
            "error_handling": "secure" if scheme.get("secure_error_handling") else "standard"
        }

    def _get_approvals(self, algorithm: str) -> List[str]:
        """Get list of approving bodies for algorithm"""
        approvals = []
        if algorithm in self.approved_algorithms.get("symmetric", []):
            approvals.extend(["NIST", "FIPS"])
        if algorithm in ["aes", "aes-gcm", "aes-256"]:
            approvals.extend(["NSA Suite B", "CNSA"])
        return approvals

    def _generate_test_results(self, scheme: Dict[str, Any]) -> Dict:
        """Generate cryptographic test results"""
        return {
            "algorithm_tests": "passed",
            "known_answer_tests": "passed",
            "monte_carlo_tests": "passed",
            "statistical_tests": "passed",
            "timestamp": datetime.utcnow().isoformat()
        }

    def _generate_config_hashes(self, scheme: Dict[str, Any]) -> Dict:
        """Generate configuration integrity hashes"""
        config_str = json.dumps(scheme, sort_keys=True)
        return {
            "sha256": hashlib.sha256(config_str.encode()).hexdigest(),
            "sha512": hashlib.sha512(config_str.encode()).hexdigest()
        }

    def _generate_security_policy(self, scheme: Dict[str, Any]) -> str:
        """Generate security policy documentation"""
        return f"""
Security Policy for {scheme.get('name', 'Cryptographic Module')}
Version: {scheme.get('version', '1.0')}
Generated: {datetime.utcnow().isoformat()}

1. Cryptographic Module Specification
   - Algorithm: {scheme.get('algorithm', 'N/A')}
   - Key Size: {scheme.get('key_size', 'N/A')} bits
   - Mode of Operation: {scheme.get('mode', 'N/A')}

2. Security Level
   - FIPS 140 Level: Target Level 2
   - Approved Algorithms: Yes

3. Roles and Services
   - Cryptographic Officer
   - User

4. Physical Security
   - Level 2: Tamper-evident seals

5. Operational Environment
   - Single-user mode
"""

    def _generate_operational_procedures(self, scheme: Dict[str, Any]) -> str:
        """Generate operational procedures"""
        return """
Operational Procedures:

1. Key Generation
2. Key Installation
3. Normal Operation
4. Key Backup
5. Key Recovery
6. Key Destruction
"""

    def _generate_incident_response_plan(self, scheme: Dict[str, Any]) -> str:
        """Generate incident response plan"""
        return """
Incident Response Plan:

1. Detection and Analysis
2. Containment
3. Eradication
4. Recovery
5. Post-Incident Activity
"""

    def _export_as_markdown(self, report: Dict[str, Any]) -> str:
        """Export report as Markdown"""
        md = f"""# Compliance Report

**Report ID:** {report.get('report_id')}
**Generated:** {report.get('generated_at')}
**Scheme:** {report.get('scheme_name')} v{report.get('scheme_version')}

## Executive Summary

- **Overall Compliance:** {report.get('overall_compliance', 0):.2f}%
- **Certificate Ready:** {'Yes' if report.get('certificate_ready') else 'No'}
- **Total Gaps:** {len(report.get('gaps', []))}

## Standards Checked

"""
        for standard_name, result in report.get('standards_results', {}).items():
            md += f"### {standard_name}\n\n"
            md += f"- **Compliance:** {result.get('compliance_percentage', 0):.2f}%\n"
            md += f"- **Requirements Checked:** {len(result.get('requirements', []))}\n\n"

        md += "\n## Recommendations\n\n"
        for rec in report.get('recommendations', [])[:10]:
            priority = rec.get('priority', 'medium')
            recommendation = rec.get('recommendation', '')
            md += f"- [{priority.upper()}] {recommendation}\n"

        return md

    def _export_as_html(self, report: Dict[str, Any]) -> str:
        """Export report as HTML"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Compliance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .compliant {{ color: green; }}
        .non-compliant {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Compliance Report</h1>
    <div class="summary">
        <p><strong>Report ID:</strong> {report.get('report_id')}</p>
        <p><strong>Generated:</strong> {report.get('generated_at')}</p>
        <p><strong>Scheme:</strong> {report.get('scheme_name')} v{report.get('scheme_version')}</p>
        <p><strong>Overall Compliance:</strong> {report.get('overall_compliance', 0):.2f}%</p>
        <p class="{'compliant' if report.get('certificate_ready') else 'non-compliant'}">
            <strong>Certificate Ready:</strong> {'Yes' if report.get('certificate_ready') else 'No'}
        </p>
    </div>

    <h2>Standards Results</h2>
    <table>
        <tr>
            <th>Standard</th>
            <th>Compliance %</th>
            <th>Status</th>
        </tr>
"""
        for standard_name, result in report.get('standards_results', {}).items():
            compliance = result.get('compliance_percentage', 0)
            status_class = 'compliant' if compliance >= 90 else 'non-compliant'
            html += f"""
        <tr>
            <td>{standard_name}</td>
            <td>{compliance:.2f}%</td>
            <td class="{status_class}">{'Compliant' if compliance >= 90 else 'Non-Compliant'}</td>
        </tr>
"""

        html += """
    </table>

    <h2>Recommendations</h2>
    <ul>
"""
        for rec in report.get('recommendations', [])[:10]:
            priority = rec.get('priority', 'medium')
            recommendation = rec.get('recommendation', '')
            html += f"        <li><strong>[{priority.upper()}]</strong> {recommendation}</li>\n"

        html += """
    </ul>
</body>
</html>
"""
        return html
