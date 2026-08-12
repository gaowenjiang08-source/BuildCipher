"""
Threat Modeling Tool
基于STRIDE的威胁建模工具

This module provides comprehensive threat modeling capabilities using the STRIDE methodology
(Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service,
Elevation of Privilege) for analyzing cryptographic systems.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from collections import defaultdict


class ThreatCategory(Enum):
    """STRIDE threat categories"""
    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"


class AttackComplexity(Enum):
    """Attack complexity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImpactLevel(Enum):
    """Security impact levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class AssetType(Enum):
    """Types of assets in cryptographic systems"""
    PRIVATE_KEY = "private_key"
    PUBLIC_KEY = "public_key"
    SYMMETRIC_KEY = "symmetric_key"
    PLAINTEXT = "plaintext"
    CIPHERTEXT = "ciphertext"
    SIGNATURE = "signature"
    AUTHENTICATION_TOKEN = "authentication_token"
    RANDOM_NUMBER = "random_number"


@dataclass
class Threat:
    """Individual threat representation"""
    id: str
    category: ThreatCategory
    title: str
    description: str
    likelihood: float  # 0-1
    impact: float  # 0-1
    risk_score: float  # likelihood * impact
    attack_vectors: List[str]
    mitigations: List[str]
    residual_risk: float
    affected_assets: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    complexity: AttackComplexity = AttackComplexity.MEDIUM
    cvss_score: Optional[float] = None


@dataclass
class AttackNode:
    """Node in an attack tree"""
    id: str
    description: str
    node_type: str  # 'AND' or 'OR' or 'LEAF'
    children: List['AttackNode'] = field(default_factory=list)
    probability: float = 0.0
    cost: float = 0.0
    skill_required: str = "low"
    detection_difficulty: str = "easy"


@dataclass
class DataFlowElement:
    """Element in a data flow diagram"""
    id: str
    name: str
    element_type: str  # 'process', 'datastore', 'external', 'dataflow'
    trust_boundary: str = "untrusted"
    properties: Dict[str, Any] = field(default_factory=dict)


class ThreatModeler:
    """STRIDE-based threat modeling for cryptographic systems"""

    def __init__(self):
        self.threat_library = self._load_threat_library()
        self.attack_tree = self._build_attack_trees()
        self.threat_counter = 0

    def model_threats(self, scheme: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete threat model analysis

        Args:
            scheme: Cryptographic scheme configuration with keys:
                - name: Scheme name
                - type: Scheme type (e.g., 'public_key', 'symmetric')
                - components: List of components
                - operations: List of operations
                - parameters: Scheme parameters

        Returns:
            Dictionary containing:
            - threats: List of identified threats
            - attack_surface: Attack surface analysis
            - risk_matrix: Risk heat map data
            - mitigation_strategy: Recommended controls
            - residual_risk: Risk level after mitigations
            - attack_trees: Attack tree structures
            - data_flow: Data flow diagram
        """
        # Identify threats using STRIDE
        threats = self.identify_threats_stride(scheme)

        # Analyze attack surface
        attack_surface = self.analyze_attack_surface(scheme)

        # Build attack trees for high-risk threats
        attack_trees = {}
        high_risk_threats = [t for t in threats if t.risk_score > 0.6]
        for threat in high_risk_threats[:5]:  # Top 5 high-risk threats
            attack_trees[threat.id] = self.build_attack_tree(threat.title)

        # Generate risk matrix
        risk_matrix = self._generate_risk_matrix(threats)

        # Recommend mitigations
        mitigations = self.recommend_mitigations(threats)

        # Calculate residual risk
        residual_risk = self._calculate_residual_risk(threats)

        # Generate data flow diagram
        dfd = self.generate_data_flow_diagram(scheme)

        return {
            'threats': [self._threat_to_dict(t) for t in threats],
            'attack_surface': attack_surface,
            'risk_matrix': risk_matrix,
            'mitigation_strategy': mitigations,
            'residual_risk': residual_risk,
            'attack_trees': attack_trees,
            'data_flow_diagram': dfd,
            'summary': {
                'total_threats': len(threats),
                'critical_threats': len([t for t in threats if t.risk_score > 0.8]),
                'high_threats': len([t for t in threats if 0.6 < t.risk_score <= 0.8]),
                'medium_threats': len([t for t in threats if 0.3 < t.risk_score <= 0.6]),
                'low_threats': len([t for t in threats if t.risk_score <= 0.3]),
                'overall_risk': sum(t.risk_score for t in threats) / len(threats) if threats else 0
            }
        }

    def identify_threats_stride(self, scheme: Dict[str, Any]) -> List[Threat]:
        """
        Identify threats using STRIDE methodology

        Args:
            scheme: Cryptographic scheme configuration

        Returns:
            List of identified Threat objects
        """
        threats = []
        scheme_name = scheme.get('name', 'Unknown')
        scheme_type = scheme.get('type', 'unknown')

        # Spoofing threats
        threats.extend(self._identify_spoofing_threats(scheme))

        # Tampering threats
        threats.extend(self._identify_tampering_threats(scheme))

        # Repudiation threats
        threats.extend(self._identify_repudiation_threats(scheme))

        # Information Disclosure threats
        threats.extend(self._identify_information_disclosure_threats(scheme))

        # Denial of Service threats
        threats.extend(self._identify_dos_threats(scheme))

        # Elevation of Privilege threats
        threats.extend(self._identify_privilege_escalation_threats(scheme))

        # Calculate risk scores and CVSS
        for threat in threats:
            threat.risk_score = threat.likelihood * threat.impact
            threat.cvss_score = self.calculate_risk_score(threat)

        return sorted(threats, key=lambda t: t.risk_score, reverse=True)

    def _identify_spoofing_threats(self, scheme: Dict[str, Any]) -> List[Threat]:
        """Identify spoofing threats"""
        threats = []
        scheme_type = scheme.get('type', 'unknown')

        # Identity spoofing threat
        if 'authentication' in str(scheme).lower() or scheme_type in ['public_key', 'signature']:
            threat_id = self._generate_threat_id('SPOOF')
            threats.append(Threat(
                id=threat_id,
                category=ThreatCategory.SPOOFING,
                title="Identity Spoofing Attack",
                description="Attacker impersonates legitimate user by compromising authentication credentials or forging signatures",
                likelihood=0.6,
                impact=0.9,
                risk_score=0.54,
                attack_vectors=[
                    "Private key theft or compromise",
                    "Certificate forgery",
                    "Man-in-the-middle credential interception",
                    "Weak key generation allowing prediction"
                ],
                mitigations=[
                    "Use secure key storage (HSM, TPM)",
                    "Implement strong key generation with sufficient entropy",
                    "Enable multi-factor authentication",
                    "Use certificate pinning",
                    "Implement key rotation policies"
                ],
                residual_risk=0.15,
                affected_assets=["private_key", "authentication_token"],
                complexity=AttackComplexity.MEDIUM
            ))

        # Message origin spoofing
        threat_id = self._generate_threat_id('SPOOF')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.SPOOFING,
            title="Message Origin Spoofing",
            description="Attacker forges message origin without proper authentication mechanisms",
            likelihood=0.5,
            impact=0.7,
            risk_score=0.35,
            attack_vectors=[
                "Lack of message authentication codes (MAC)",
                "Weak or missing digital signatures",
                "Replay of legitimate messages"
            ],
            mitigations=[
                "Implement HMAC or authenticated encryption (AEAD)",
                "Use digital signatures for non-repudiation",
                "Include timestamps and nonces to prevent replay",
                "Validate message integrity before processing"
            ],
            residual_risk=0.1,
            affected_assets=["ciphertext", "signature"],
            complexity=AttackComplexity.LOW
        ))

        return threats

    def _identify_tampering_threats(self, scheme: Dict[str, Any]) -> List[Threat]:
        """Identify tampering threats"""
        threats = []

        # Ciphertext tampering
        threat_id = self._generate_threat_id('TAMP')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.TAMPERING,
            title="Ciphertext Manipulation Attack",
            description="Attacker modifies ciphertext to alter decrypted plaintext without detection",
            likelihood=0.7,
            impact=0.85,
            risk_score=0.595,
            attack_vectors=[
                "Bit-flipping attacks on unauthenticated encryption",
                "Padding oracle attacks",
                "Malleability in encryption schemes",
                "CBC bit-flipping"
            ],
            mitigations=[
                "Use authenticated encryption (AES-GCM, ChaCha20-Poly1305)",
                "Implement encrypt-then-MAC",
                "Validate all inputs before decryption",
                "Use integrity checks (HMAC, digital signatures)",
                "Avoid malleable encryption schemes"
            ],
            residual_risk=0.12,
            affected_assets=["ciphertext", "plaintext"],
            complexity=AttackComplexity.MEDIUM
        ))

        # Key material tampering
        threat_id = self._generate_threat_id('TAMP')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.TAMPERING,
            title="Key Material Corruption",
            description="Attacker modifies stored cryptographic keys to compromise system security",
            likelihood=0.4,
            impact=0.95,
            risk_score=0.38,
            attack_vectors=[
                "File system manipulation",
                "Memory corruption attacks",
                "Hardware tampering",
                "Supply chain attacks on key storage"
            ],
            mitigations=[
                "Store keys in tamper-resistant hardware (HSM)",
                "Implement key integrity verification",
                "Use secure enclaves (SGX, TrustZone)",
                "Enable file integrity monitoring",
                "Implement secure boot and measured boot"
            ],
            residual_risk=0.08,
            affected_assets=["private_key", "symmetric_key"],
            complexity=AttackComplexity.HIGH
        ))

        # Protocol tampering
        threat_id = self._generate_threat_id('TAMP')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.TAMPERING,
            title="Protocol Parameter Manipulation",
            description="Attacker modifies protocol parameters to downgrade security or force weak cryptography",
            likelihood=0.55,
            impact=0.75,
            risk_score=0.4125,
            attack_vectors=[
                "Version rollback attacks",
                "Cipher suite downgrade",
                "Parameter injection",
                "MITM parameter modification"
            ],
            mitigations=[
                "Enforce minimum security standards",
                "Disable weak algorithms and parameters",
                "Implement parameter validation",
                "Use authenticated key exchange",
                "Sign protocol parameters"
            ],
            residual_risk=0.15,
            affected_assets=["authentication_token"],
            complexity=AttackComplexity.MEDIUM
        ))

        return threats

    def _identify_repudiation_threats(self, scheme: Dict[str, Any]) -> List[Threat]:
        """Identify repudiation threats"""
        threats = []
        scheme_type = scheme.get('type', 'unknown')

        # Action repudiation
        if scheme_type in ['signature', 'public_key', 'hybrid']:
            threat_id = self._generate_threat_id('REPU')
            threats.append(Threat(
                id=threat_id,
                category=ThreatCategory.REPUDIATION,
                title="Transaction Repudiation",
                description="User denies performing action due to lack of non-repudiation controls",
                likelihood=0.45,
                impact=0.65,
                risk_score=0.2925,
                attack_vectors=[
                    "Lack of digital signatures",
                    "Insufficient audit logging",
                    "Key sharing between users",
                    "Weak timestamp mechanisms"
                ],
                mitigations=[
                    "Implement digital signatures for critical operations",
                    "Use trusted timestamping services",
                    "Maintain comprehensive audit logs",
                    "Enforce individual key ownership",
                    "Implement blockchain-based audit trails"
                ],
                residual_risk=0.1,
                affected_assets=["signature", "authentication_token"],
                complexity=AttackComplexity.LOW
            ))

        # Logging bypass
        threat_id = self._generate_threat_id('REPU')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.REPUDIATION,
            title="Audit Log Tampering",
            description="Attacker modifies or deletes logs to hide malicious activities",
            likelihood=0.5,
            impact=0.7,
            risk_score=0.35,
            attack_vectors=[
                "Direct log file modification",
                "Log injection attacks",
                "Log deletion",
                "Time manipulation"
            ],
            mitigations=[
                "Use write-once storage for logs",
                "Implement cryptographic log signing",
                "Send logs to remote SIEM immediately",
                "Use append-only databases",
                "Implement log integrity verification"
            ],
            residual_risk=0.12,
            affected_assets=[],
            complexity=AttackComplexity.MEDIUM
        ))

        return threats

    def _identify_information_disclosure_threats(self, scheme: Dict[str, Any]) -> List[Threat]:
        """Identify information disclosure threats"""
        threats = []

        # Side-channel attacks
        threat_id = self._generate_threat_id('INFO')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.INFORMATION_DISCLOSURE,
            title="Side-Channel Information Leakage",
            description="Attacker extracts secrets through timing, power, or electromagnetic side channels",
            likelihood=0.65,
            impact=0.9,
            risk_score=0.585,
            attack_vectors=[
                "Timing attacks on cryptographic operations",
                "Power analysis (SPA, DPA)",
                "Cache-timing attacks (Spectre, Meltdown variants)",
                "Acoustic cryptanalysis",
                "Electromagnetic emanation analysis"
            ],
            mitigations=[
                "Implement constant-time algorithms",
                "Use blinding techniques",
                "Add random delays",
                "Implement physical shielding",
                "Use side-channel resistant implementations",
                "Enable address space layout randomization (ASLR)"
            ],
            residual_risk=0.2,
            affected_assets=["private_key", "symmetric_key"],
            complexity=AttackComplexity.HIGH
        ))

        # Key exposure
        threat_id = self._generate_threat_id('INFO')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.INFORMATION_DISCLOSURE,
            title="Cryptographic Key Exposure",
            description="Private keys or symmetric keys leaked through insecure storage or transmission",
            likelihood=0.55,
            impact=0.95,
            risk_score=0.5225,
            attack_vectors=[
                "Keys stored in plaintext",
                "Keys in source code or configuration files",
                "Memory dumps containing keys",
                "Insufficient key zeroization",
                "Insecure key exchange"
            ],
            mitigations=[
                "Encrypt keys at rest using KEK (Key Encryption Key)",
                "Use secure key derivation functions",
                "Implement proper key zeroization after use",
                "Store keys in hardware security modules",
                "Never hardcode keys in source code",
                "Use environment variables or key vaults"
            ],
            residual_risk=0.1,
            affected_assets=["private_key", "symmetric_key"],
            complexity=AttackComplexity.LOW
        ))

        # Plaintext leakage
        threat_id = self._generate_threat_id('INFO')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.INFORMATION_DISCLOSURE,
            title="Plaintext Data Leakage",
            description="Sensitive plaintext data exposed through logs, error messages, or insecure channels",
            likelihood=0.6,
            impact=0.8,
            risk_score=0.48,
            attack_vectors=[
                "Verbose error messages revealing data",
                "Logging sensitive information",
                "Unencrypted data transmission",
                "Temporary file exposure",
                "Swap file/hibernation file exposure"
            ],
            mitigations=[
                "Sanitize error messages",
                "Implement data classification and handling policies",
                "Encrypt all sensitive data in transit and at rest",
                "Disable swap for sensitive processes",
                "Securely delete temporary files",
                "Implement data loss prevention (DLP) controls"
            ],
            residual_risk=0.15,
            affected_assets=["plaintext"],
            complexity=AttackComplexity.LOW
        ))

        # Random number generator weakness
        threat_id = self._generate_threat_id('INFO')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.INFORMATION_DISCLOSURE,
            title="Weak Random Number Generation",
            description="Predictable random numbers allow attackers to guess keys or nonces",
            likelihood=0.5,
            impact=0.9,
            risk_score=0.45,
            attack_vectors=[
                "Use of weak PRNGs (e.g., rand(), Math.random())",
                "Insufficient entropy at system startup",
                "Predictable seed values",
                "RNG state compromise"
            ],
            mitigations=[
                "Use cryptographically secure RNGs (CSPRNG)",
                "Ensure sufficient entropy sources",
                "Use hardware RNGs when available",
                "Properly seed RNGs with high-entropy data",
                "Never reuse nonces or IVs"
            ],
            residual_risk=0.08,
            affected_assets=["random_number", "symmetric_key"],
            complexity=AttackComplexity.MEDIUM
        ))

        return threats

    def _identify_dos_threats(self, scheme: Dict[str, Any]) -> List[Threat]:
        """Identify denial of service threats"""
        threats = []

        # Computational DoS
        threat_id = self._generate_threat_id('DOS')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.DENIAL_OF_SERVICE,
            title="Cryptographic Computation Exhaustion",
            description="Attacker forces expensive cryptographic operations to exhaust system resources",
            likelihood=0.7,
            impact=0.6,
            risk_score=0.42,
            attack_vectors=[
                "Repeated signature verification requests",
                "Multiple key exchange initiations",
                "Hash collision attacks forcing rehashing",
                "Large exponent attacks in RSA",
                "Slowloris-style cryptographic handshake attacks"
            ],
            mitigations=[
                "Implement rate limiting on cryptographic operations",
                "Use proof-of-work or CAPTCHA for expensive operations",
                "Set timeouts on cryptographic operations",
                "Implement request queuing and prioritization",
                "Use efficient algorithms and parameters",
                "Deploy resource monitoring and auto-scaling"
            ],
            residual_risk=0.15,
            affected_assets=[],
            complexity=AttackComplexity.LOW
        ))

        # Key revocation DoS
        threat_id = self._generate_threat_id('DOS')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.DENIAL_OF_SERVICE,
            title="Certificate/Key Revocation DoS",
            description="Attacker causes mass key revocation or blocks revocation checking",
            likelihood=0.4,
            impact=0.65,
            risk_score=0.26,
            attack_vectors=[
                "OCSP server flooding",
                "CRL download DoS",
                "False revocation requests",
                "Blocking revocation checking channels"
            ],
            mitigations=[
                "Implement OCSP stapling",
                "Use CDN for CRL distribution",
                "Cache revocation information",
                "Implement fallback mechanisms",
                "Rate limit revocation checks",
                "Use short-lived certificates"
            ],
            residual_risk=0.1,
            affected_assets=["public_key"],
            complexity=AttackComplexity.MEDIUM
        ))

        # Resource exhaustion
        threat_id = self._generate_threat_id('DOS')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.DENIAL_OF_SERVICE,
            title="Memory/Storage Exhaustion",
            description="Attacker fills storage or memory with cryptographic material",
            likelihood=0.5,
            impact=0.55,
            risk_score=0.275,
            attack_vectors=[
                "Session state exhaustion",
                "Filling key storage",
                "Log flooding",
                "Cache poisoning with cryptographic data"
            ],
            mitigations=[
                "Implement storage quotas",
                "Set session limits and timeouts",
                "Implement garbage collection for old keys",
                "Use disk and memory monitoring",
                "Implement backpressure mechanisms"
            ],
            residual_risk=0.12,
            affected_assets=[],
            complexity=AttackComplexity.LOW
        ))

        return threats

    def _identify_privilege_escalation_threats(self, scheme: Dict[str, Any]) -> List[Threat]:
        """Identify elevation of privilege threats"""
        threats = []

        # Key misuse
        threat_id = self._generate_threat_id('PRIV')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.ELEVATION_OF_PRIVILEGE,
            title="Cryptographic Key Privilege Escalation",
            description="Attacker uses compromised low-privilege key to gain higher privileges",
            likelihood=0.5,
            impact=0.85,
            risk_score=0.425,
            attack_vectors=[
                "Lack of key usage restrictions",
                "Cross-domain key reuse",
                "Privilege separation failures",
                "Key hierarchy bypass"
            ],
            mitigations=[
                "Implement key usage extensions and constraints",
                "Enforce principle of least privilege for keys",
                "Use separate keys for different purposes",
                "Implement hierarchical key management",
                "Regular key access audits"
            ],
            residual_risk=0.15,
            affected_assets=["private_key"],
            complexity=AttackComplexity.MEDIUM
        ))

        # Authentication bypass
        threat_id = self._generate_threat_id('PRIV')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.ELEVATION_OF_PRIVILEGE,
            title="Cryptographic Authentication Bypass",
            description="Attacker bypasses authentication mechanisms through cryptographic weaknesses",
            likelihood=0.45,
            impact=0.9,
            risk_score=0.405,
            attack_vectors=[
                "Weak signature verification",
                "Null signature acceptance",
                "Algorithm confusion attacks",
                "Signature malleability",
                "Hash collision exploitation"
            ],
            mitigations=[
                "Strict signature validation",
                "Reject null or empty signatures",
                "Enforce algorithm matching",
                "Use collision-resistant hash functions",
                "Implement defense in depth"
            ],
            residual_risk=0.1,
            affected_assets=["signature", "authentication_token"],
            complexity=AttackComplexity.MEDIUM
        ))

        # Oracle attacks leading to privilege escalation
        threat_id = self._generate_threat_id('PRIV')
        threats.append(Threat(
            id=threat_id,
            category=ThreatCategory.ELEVATION_OF_PRIVILEGE,
            title="Cryptographic Oracle Exploitation",
            description="Attacker uses padding oracle or timing oracle to forge privileged tokens",
            likelihood=0.55,
            impact=0.8,
            risk_score=0.44,
            attack_vectors=[
                "Padding oracle attacks",
                "Timing oracle attacks",
                "Error message oracles",
                "Bleichenbacher's attack variants"
            ],
            mitigations=[
                "Use authenticated encryption",
                "Implement uniform error handling",
                "Use constant-time comparisons",
                "Avoid detailed error messages",
                "Implement attack detection and blocking"
            ],
            residual_risk=0.12,
            affected_assets=["ciphertext", "authentication_token"],
            complexity=AttackComplexity.HIGH
        ))

        return threats

    def analyze_attack_surface(self, scheme: Dict[str, Any]) -> Dict:
        """
        Analyze attack surface of the cryptographic scheme

        Args:
            scheme: Cryptographic scheme configuration

        Returns:
            Dictionary with attack surface analysis
        """
        attack_surface = {
            'entry_points': [],
            'trust_boundaries': [],
            'data_flows': [],
            'assets': [],
            'attack_vectors': {},
            'exposure_score': 0.0
        }

        # Identify entry points
        entry_points = []
        if 'operations' in scheme:
            for op in scheme.get('operations', []):
                entry_points.append({
                    'name': op.get('name', 'unknown'),
                    'type': 'cryptographic_operation',
                    'inputs': op.get('inputs', []),
                    'authentication_required': op.get('auth_required', False),
                    'exposure': 'external' if not op.get('internal', False) else 'internal'
                })

        attack_surface['entry_points'] = entry_points

        # Identify trust boundaries
        trust_boundaries = [
            {'name': 'Key Storage', 'description': 'Boundary between secure key storage and application'},
            {'name': 'Network', 'description': 'Boundary between system and external network'},
            {'name': 'Process', 'description': 'Boundary between trusted and untrusted processes'}
        ]
        attack_surface['trust_boundaries'] = trust_boundaries

        # Identify critical assets
        assets = []
        scheme_type = scheme.get('type', 'unknown')

        if scheme_type in ['public_key', 'signature', 'hybrid']:
            assets.extend([
                {'name': 'Private Key', 'type': AssetType.PRIVATE_KEY.value, 'criticality': 'critical'},
                {'name': 'Public Key', 'type': AssetType.PUBLIC_KEY.value, 'criticality': 'high'}
            ])

        if scheme_type in ['symmetric', 'hybrid']:
            assets.append({
                'name': 'Symmetric Key',
                'type': AssetType.SYMMETRIC_KEY.value,
                'criticality': 'critical'
            })

        assets.extend([
            {'name': 'Plaintext Data', 'type': AssetType.PLAINTEXT.value, 'criticality': 'high'},
            {'name': 'Ciphertext', 'type': AssetType.CIPHERTEXT.value, 'criticality': 'medium'},
            {'name': 'Random Numbers', 'type': AssetType.RANDOM_NUMBER.value, 'criticality': 'high'}
        ])

        attack_surface['assets'] = assets

        # Map attack vectors to entry points
        attack_vectors = {
            'network_attacks': ['MITM', 'Eavesdropping', 'Replay', 'Injection'],
            'cryptographic_attacks': ['Chosen plaintext', 'Chosen ciphertext', 'Known plaintext', 'Brute force'],
            'implementation_attacks': ['Side-channel', 'Fault injection', 'API misuse'],
            'social_engineering': ['Key theft', 'Credential compromise']
        }
        attack_surface['attack_vectors'] = attack_vectors

        # Calculate exposure score
        exposure_score = len(entry_points) * 0.2
        exposure_score += len([e for e in entry_points if e.get('exposure') == 'external']) * 0.3
        exposure_score += len(assets) * 0.1
        exposure_score = min(exposure_score, 1.0)
        attack_surface['exposure_score'] = round(exposure_score, 2)

        return attack_surface

    def build_attack_tree(self, target: str) -> Dict:
        """
        Build attack tree for specific target

        Args:
            target: Target threat or goal

        Returns:
            Attack tree structure
        """
        # Create root node based on target
        if 'key' in target.lower() and 'exposure' in target.lower():
            root = AttackNode(
                id="root",
                description="Obtain Private Key",
                node_type="OR",
                probability=0.3,
                cost=10000
            )

            # Branch 1: Direct key theft
            direct_theft = AttackNode(
                id="direct_theft",
                description="Steal Key from Storage",
                node_type="AND",
                probability=0.2,
                cost=5000
            )
            direct_theft.children = [
                AttackNode(
                    id="gain_access",
                    description="Gain System Access",
                    node_type="LEAF",
                    probability=0.4,
                    cost=2000,
                    skill_required="medium",
                    detection_difficulty="medium"
                ),
                AttackNode(
                    id="locate_key",
                    description="Locate Key Storage",
                    node_type="LEAF",
                    probability=0.6,
                    cost=1000,
                    skill_required="low",
                    detection_difficulty="easy"
                ),
                AttackNode(
                    id="extract_key",
                    description="Extract Key Material",
                    node_type="LEAF",
                    probability=0.8,
                    cost=2000,
                    skill_required="medium",
                    detection_difficulty="hard"
                )
            ]

            # Branch 2: Side-channel attack
            side_channel = AttackNode(
                id="side_channel",
                description="Side-Channel Key Extraction",
                node_type="AND",
                probability=0.15,
                cost=15000
            )
            side_channel.children = [
                AttackNode(
                    id="timing_attack",
                    description="Timing Analysis",
                    node_type="LEAF",
                    probability=0.5,
                    cost=8000,
                    skill_required="high",
                    detection_difficulty="very_hard"
                ),
                AttackNode(
                    id="power_analysis",
                    description="Power Analysis",
                    node_type="LEAF",
                    probability=0.3,
                    cost=20000,
                    skill_required="expert",
                    detection_difficulty="very_hard"
                )
            ]

            # Branch 3: Cryptanalysis
            cryptanalysis = AttackNode(
                id="cryptanalysis",
                description="Mathematical Key Recovery",
                node_type="OR",
                probability=0.05,
                cost=50000
            )
            cryptanalysis.children = [
                AttackNode(
                    id="weak_params",
                    description="Exploit Weak Parameters",
                    node_type="LEAF",
                    probability=0.1,
                    cost=30000,
                    skill_required="expert",
                    detection_difficulty="impossible"
                ),
                AttackNode(
                    id="quantum_attack",
                    description="Quantum Algorithm Attack",
                    node_type="LEAF",
                    probability=0.01,
                    cost=1000000,
                    skill_required="expert",
                    detection_difficulty="impossible"
                )
            ]

            root.children = [direct_theft, side_channel, cryptanalysis]

        elif 'tampering' in target.lower() or 'manipulation' in target.lower():
            root = AttackNode(
                id="root",
                description="Manipulate Ciphertext",
                node_type="OR",
                probability=0.4,
                cost=3000
            )

            root.children = [
                AttackNode(
                    id="bit_flip",
                    description="Bit-Flipping Attack",
                    node_type="LEAF",
                    probability=0.6,
                    cost=1000,
                    skill_required="medium",
                    detection_difficulty="medium"
                ),
                AttackNode(
                    id="padding_oracle",
                    description="Padding Oracle Attack",
                    node_type="LEAF",
                    probability=0.3,
                    cost=5000,
                    skill_required="high",
                    detection_difficulty="hard"
                ),
                AttackNode(
                    id="replay",
                    description="Replay Valid Ciphertext",
                    node_type="LEAF",
                    probability=0.5,
                    cost=500,
                    skill_required="low",
                    detection_difficulty="easy"
                )
            ]

        else:
            # Generic attack tree
            root = AttackNode(
                id="root",
                description=f"Compromise: {target}",
                node_type="OR",
                probability=0.3,
                cost=5000
            )

            root.children = [
                AttackNode(
                    id="technical",
                    description="Technical Attack",
                    node_type="LEAF",
                    probability=0.4,
                    cost=8000,
                    skill_required="high",
                    detection_difficulty="medium"
                ),
                AttackNode(
                    id="social",
                    description="Social Engineering",
                    node_type="LEAF",
                    probability=0.5,
                    cost=2000,
                    skill_required="low",
                    detection_difficulty="hard"
                ),
                AttackNode(
                    id="physical",
                    description="Physical Access",
                    node_type="LEAF",
                    probability=0.2,
                    cost=3000,
                    skill_required="medium",
                    detection_difficulty="easy"
                )
            ]

        return self._attack_node_to_dict(root)

    def calculate_risk_score(self, threat: Threat) -> float:
        """
        Calculate CVSS-like risk score

        Args:
            threat: Threat object

        Returns:
            CVSS-style score (0-10)
        """
        # Base score components
        attack_vector = 0.85  # Assume network accessible
        attack_complexity = {
            AttackComplexity.LOW: 0.77,
            AttackComplexity.MEDIUM: 0.62,
            AttackComplexity.HIGH: 0.44
        }.get(threat.complexity, 0.62)

        privileges_required = 0.62  # Assume low privileges
        user_interaction = 0.85  # Assume none required

        # Impact components
        confidentiality_impact = threat.impact
        integrity_impact = threat.impact * 0.9
        availability_impact = threat.impact * 0.8

        # Base score calculation (simplified CVSS v3)
        impact_score = 1 - ((1 - confidentiality_impact) * (1 - integrity_impact) * (1 - availability_impact))

        exploitability = attack_vector * attack_complexity * privileges_required * user_interaction

        if impact_score <= 0:
            base_score = 0
        else:
            base_score = min(((impact_score + exploitability) * 1.08), 10.0)

        return round(base_score, 1)

    def recommend_mitigations(self, threats: List[Threat]) -> List[Dict]:
        """
        Recommend security controls based on identified threats

        Args:
            threats: List of threats

        Returns:
            Prioritized list of mitigation recommendations
        """
        mitigation_map = defaultdict(lambda: {
            'priority': 0,
            'threats_mitigated': [],
            'implementation_cost': 'unknown',
            'effectiveness': 0.0
        })

        for threat in threats:
            for mitigation in threat.mitigations:
                mitigation_map[mitigation]['threats_mitigated'].append(threat.id)
                mitigation_map[mitigation]['priority'] += threat.risk_score
                mitigation_map[mitigation]['effectiveness'] += (1 - threat.residual_risk)

        # Convert to list and add metadata
        recommendations = []
        for mitigation, data in mitigation_map.items():
            threat_count = len(data['threats_mitigated'])
            avg_effectiveness = data['effectiveness'] / threat_count if threat_count > 0 else 0

            # Estimate implementation cost based on mitigation type
            cost = 'medium'
            if any(keyword in mitigation.lower() for keyword in ['hsm', 'hardware', 'tpm']):
                cost = 'high'
            elif any(keyword in mitigation.lower() for keyword in ['policy', 'disable', 'enforce']):
                cost = 'low'

            recommendations.append({
                'mitigation': mitigation,
                'priority_score': round(data['priority'], 3),
                'threats_addressed': threat_count,
                'threat_ids': data['threats_mitigated'],
                'estimated_cost': cost,
                'effectiveness': round(avg_effectiveness, 2),
                'category': self._categorize_mitigation(mitigation)
            })

        # Sort by priority
        recommendations.sort(key=lambda x: x['priority_score'], reverse=True)

        return recommendations

    def generate_data_flow_diagram(self, scheme: Dict[str, Any]) -> str:
        """
        Generate data flow diagram in DOT format (Graphviz)

        Args:
            scheme: Cryptographic scheme configuration

        Returns:
            DOT format string
        """
        dot = ['digraph ThreatModel {']
        dot.append('  rankdir=LR;')
        dot.append('  node [shape=box];')
        dot.append('')

        # Define node styles
        dot.append('  // Node styles')
        dot.append('  node [shape=circle, style=filled, fillcolor=lightblue] external;')
        dot.append('  node [shape=box, style=filled, fillcolor=lightgreen] process;')
        dot.append('  node [shape=cylinder, style=filled, fillcolor=lightyellow] datastore;')
        dot.append('')

        # Define nodes
        dot.append('  // External entities')
        dot.append('  user [label="User", shape=circle];')
        dot.append('  attacker [label="Attacker", shape=circle, fillcolor=red];')
        dot.append('')

        dot.append('  // Processes')
        scheme_name = scheme.get('name', 'Crypto System')
        dot.append(f'  encrypt [label="Encryption\\n({scheme_name})", shape=box];')
        dot.append(f'  decrypt [label="Decryption\\n({scheme_name})", shape=box];')
        dot.append('  keygen [label="Key Generation", shape=box];')
        dot.append('')

        dot.append('  // Data stores')
        dot.append('  keystore [label="Key Storage", shape=cylinder];')
        dot.append('  datastore [label="Data Storage", shape=cylinder];')
        dot.append('')

        # Define data flows
        dot.append('  // Data flows')
        dot.append('  user -> encrypt [label="Plaintext"];')
        dot.append('  encrypt -> datastore [label="Ciphertext"];')
        dot.append('  datastore -> decrypt [label="Ciphertext"];')
        dot.append('  decrypt -> user [label="Plaintext"];')
        dot.append('  keygen -> keystore [label="Keys"];')
        dot.append('  keystore -> encrypt [label="Key"];')
        dot.append('  keystore -> decrypt [label="Key"];')
        dot.append('')

        # Threat annotations
        dot.append('  // Threat points (dashed red lines)')
        dot.append('  attacker -> encrypt [label="T: Tampering", style=dashed, color=red];')
        dot.append('  attacker -> keystore [label="I: Info Disclosure", style=dashed, color=red];')
        dot.append('  attacker -> datastore [label="S: Spoofing", style=dashed, color=red];')
        dot.append('')

        # Trust boundaries
        dot.append('  // Trust boundaries')
        dot.append('  subgraph cluster_trusted {')
        dot.append('    label="Trusted Zone";')
        dot.append('    style=dashed;')
        dot.append('    color=blue;')
        dot.append('    keystore;')
        dot.append('    keygen;')
        dot.append('  }')
        dot.append('')

        dot.append('}')

        return '\n'.join(dot)

    def _load_threat_library(self) -> Dict:
        """Load threat patterns library"""
        return {
            'stride_categories': {
                'spoofing': 'Authentication threats',
                'tampering': 'Integrity threats',
                'repudiation': 'Non-repudiation threats',
                'information_disclosure': 'Confidentiality threats',
                'denial_of_service': 'Availability threats',
                'elevation_of_privilege': 'Authorization threats'
            },
            'common_crypto_threats': [
                'Weak key generation',
                'Insufficient key length',
                'Deprecated algorithms',
                'Side-channel vulnerabilities',
                'Improper key management',
                'Lack of authentication',
                'Missing integrity checks',
                'Replay attacks',
                'Oracle attacks'
            ]
        }

    def _build_attack_trees(self) -> Dict:
        """Build attack tree templates"""
        return {
            'key_compromise': 'Template for key compromise scenarios',
            'data_breach': 'Template for data exfiltration',
            'service_disruption': 'Template for DoS attacks',
            'privilege_escalation': 'Template for authorization bypass'
        }

    def _generate_threat_id(self, prefix: str) -> str:
        """Generate unique threat ID"""
        self.threat_counter += 1
        hash_input = f"{prefix}_{self.threat_counter}".encode()
        hash_suffix = hashlib.sha256(hash_input).hexdigest()[:6]
        return f"{prefix}_{self.threat_counter:03d}_{hash_suffix}"

    def _threat_to_dict(self, threat: Threat) -> Dict:
        """Convert Threat object to dictionary"""
        return {
            'id': threat.id,
            'category': threat.category.value,
            'title': threat.title,
            'description': threat.description,
            'likelihood': threat.likelihood,
            'impact': threat.impact,
            'risk_score': threat.risk_score,
            'cvss_score': threat.cvss_score,
            'attack_vectors': threat.attack_vectors,
            'mitigations': threat.mitigations,
            'residual_risk': threat.residual_risk,
            'affected_assets': threat.affected_assets,
            'complexity': threat.complexity.value,
            'risk_level': self._get_risk_level(threat.risk_score)
        }

    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to categorical level"""
        if risk_score > 0.8:
            return 'critical'
        elif risk_score > 0.6:
            return 'high'
        elif risk_score > 0.3:
            return 'medium'
        else:
            return 'low'

    def _generate_risk_matrix(self, threats: List[Threat]) -> Dict:
        """Generate risk matrix/heat map data"""
        matrix = {
            'data': [],
            'categories': {
                'likelihood': ['Very Low', 'Low', 'Medium', 'High', 'Very High'],
                'impact': ['Negligible', 'Low', 'Medium', 'High', 'Critical']
            }
        }

        for threat in threats:
            likelihood_idx = int(threat.likelihood * 4)
            impact_idx = int(threat.impact * 4)

            matrix['data'].append({
                'threat_id': threat.id,
                'title': threat.title,
                'likelihood_index': likelihood_idx,
                'impact_index': impact_idx,
                'risk_score': threat.risk_score,
                'category': threat.category.value
            })

        return matrix

    def _calculate_residual_risk(self, threats: List[Threat]) -> Dict:
        """Calculate overall residual risk after mitigations"""
        if not threats:
            return {'score': 0.0, 'level': 'negligible'}

        total_initial = sum(t.risk_score for t in threats)
        total_residual = sum(t.residual_risk for t in threats)

        avg_residual = total_residual / len(threats)
        reduction_percent = ((total_initial - total_residual) / total_initial * 100) if total_initial > 0 else 0

        return {
            'score': round(avg_residual, 3),
            'level': self._get_risk_level(avg_residual),
            'reduction_percentage': round(reduction_percent, 1),
            'initial_risk': round(total_initial / len(threats), 3),
            'threats_count': len(threats)
        }

    def _categorize_mitigation(self, mitigation: str) -> str:
        """Categorize mitigation control"""
        mitigation_lower = mitigation.lower()

        if any(word in mitigation_lower for word in ['encrypt', 'hash', 'sign', 'aead', 'hmac']):
            return 'cryptographic'
        elif any(word in mitigation_lower for word in ['hsm', 'tpm', 'hardware', 'enclave']):
            return 'hardware'
        elif any(word in mitigation_lower for word in ['policy', 'procedure', 'audit', 'review']):
            return 'administrative'
        elif any(word in mitigation_lower for word in ['implement', 'use', 'enable', 'deploy']):
            return 'technical'
        elif any(word in mitigation_lower for word in ['monitor', 'log', 'detect', 'alert']):
            return 'detective'
        else:
            return 'preventive'

    def _attack_node_to_dict(self, node: AttackNode) -> Dict:
        """Convert AttackNode to dictionary recursively"""
        return {
            'id': node.id,
            'description': node.description,
            'type': node.node_type,
            'probability': node.probability,
            'cost': node.cost,
            'skill_required': node.skill_required,
            'detection_difficulty': node.detection_difficulty,
            'children': [self._attack_node_to_dict(child) for child in node.children]
        }
