"""
Security Assessment Tool
对密码学方案进行全面的安全评估
"""

from typing import Dict, List, Any, Set, Tuple
from enum import Enum
from datetime import datetime
import hashlib


class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityAssessor:
    """Assess security of cryptographic schemes"""

    def __init__(self):
        # Known weak algorithms and components
        self.weak_algorithms = {
            'md5': ThreatLevel.CRITICAL,
            'sha1': ThreatLevel.HIGH,
            'des': ThreatLevel.CRITICAL,
            '3des': ThreatLevel.HIGH,
            'rc4': ThreatLevel.CRITICAL,
            'blowfish': ThreatLevel.MEDIUM,
        }

        # Strong modern algorithms
        self.strong_algorithms = {
            'aes': ['aes-128', 'aes-192', 'aes-256'],
            'sha': ['sha-256', 'sha-384', 'sha-512', 'sha3-256', 'sha3-512'],
            'rsa': ['rsa-2048', 'rsa-3072', 'rsa-4096'],
            'ecdsa': ['ecdsa-p256', 'ecdsa-p384', 'ecdsa-p521'],
            'chacha20': ['chacha20-poly1305'],
        }

        # Minimum key lengths for security levels
        self.min_key_lengths = {
            'symmetric': {
                'minimum': 128,
                'recommended': 256
            },
            'rsa': {
                'minimum': 2048,
                'recommended': 3072
            },
            'ecc': {
                'minimum': 256,
                'recommended': 384
            }
        }

        # Post-quantum resistant algorithms
        self.pq_resistant = {
            'kyber', 'dilithium', 'sphincs+', 'falcon',
            'ntru', 'saber', 'crystals'
        }

        # Known attack types
        self.attack_types = [
            'brute_force',
            'chosen_plaintext',
            'chosen_ciphertext',
            'side_channel',
            'timing',
            'birthday',
            'collision',
            'quantum',
            'mitm',
            'replay'
        ]

    def assess_scheme(self, scheme: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive security assessment

        Args:
            scheme: Dictionary containing:
                - algorithm: str (e.g., 'aes-256-gcm')
                - key_length: int
                - mode: str (optional)
                - hash_function: str (optional)
                - use_case: str (optional)

        Returns:
            - overall_score: 0-100
            - vulnerabilities: List of potential vulnerabilities
            - attack_vectors: Possible attack methods
            - compliance: Standards compliance (FIPS, ISO, etc.)
            - quantum_readiness: Post-quantum assessment
            - recommendations: Security improvements
        """
        # Handle both dict and CryptographicScheme objects
        if hasattr(scheme, 'model_dump'):
            scheme_dict = scheme.model_dump()
        elif hasattr(scheme, 'to_dict'):
            scheme_dict = scheme.to_dict()
        elif isinstance(scheme, dict):
            scheme_dict = scheme
        else:
            scheme_dict = str(scheme)

        assessment = {
            'timestamp': datetime.now().isoformat(),
            'scheme_info': scheme_dict,
            'overall_score': 0,
            'threat_level': ThreatLevel.MEDIUM.value,
            'vulnerabilities': [],
            'attack_vectors': {},
            'compliance': {},
            'quantum_readiness': {},
            'recommendations': [],
            'strengths': []
        }

        # Extract scheme components - handle both dict and CryptographicScheme objects
        if isinstance(scheme, dict):
            algorithm = scheme.get('algorithm', '').lower()
            key_length = scheme.get('key_length', 0)
            mode = scheme.get('mode', '').lower()
            hash_function = scheme.get('hash_function', '').lower()
        elif hasattr(scheme, 'architecture') and hasattr(scheme.architecture, 'components'):
            # Extract from CryptographicScheme object
            components = scheme.architecture.components
            algorithm = components[0].name.lower() if components else ''
            key_length = scheme.parameters.key_size if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'key_size') else 0
            mode = scheme.parameters.additional_params.get('mode', '').lower() if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'additional_params') else ''
            hash_function = scheme.parameters.additional_params.get('hash_function', '').lower() if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'additional_params') else ''
        else:
            algorithm = ''
            key_length = 0
            mode = ''
            hash_function = ''

        # Initialize score
        score = 100

        # 1. Check for weak algorithms
        weak_check = self._check_weak_algorithms(algorithm, hash_function)
        score -= weak_check['penalty']
        assessment['vulnerabilities'].extend(weak_check['vulnerabilities'])

        # 2. Evaluate key length
        key_check = self._evaluate_key_length(algorithm, key_length)
        score -= key_check['penalty']
        if key_check['vulnerability']:
            assessment['vulnerabilities'].append(key_check['vulnerability'])
        if key_check['strength']:
            assessment['strengths'].append(key_check['strength'])

        # 3. Evaluate mode of operation
        mode_check = self._evaluate_mode(mode, algorithm)
        score -= mode_check['penalty']
        if mode_check['vulnerability']:
            assessment['vulnerabilities'].append(mode_check['vulnerability'])
        if mode_check['strength']:
            assessment['strengths'].append(mode_check['strength'])

        # 4. Evaluate attack resistance
        assessment['attack_vectors'] = self.evaluate_attack_resistance(scheme)
        attack_score = self._calculate_attack_score(assessment['attack_vectors'])
        score = min(score, attack_score)

        # 5. Check compliance
        assessment['compliance'] = self.compliance_check(scheme)

        # 6. Quantum readiness
        assessment['quantum_readiness'] = self._assess_quantum_readiness(algorithm)
        if not assessment['quantum_readiness']['resistant']:
            assessment['vulnerabilities'].append({
                'type': 'quantum_vulnerability',
                'severity': ThreatLevel.MEDIUM.value,
                'description': 'Scheme is not quantum-resistant',
                'estimated_years_until_vulnerable': assessment['quantum_readiness']['years_until_vulnerable']
            })

        # 7. Generate recommendations
        assessment['recommendations'] = self._generate_recommendations(
            scheme, assessment['vulnerabilities'], assessment['compliance']
        )

        # Finalize score and threat level
        assessment['overall_score'] = max(0, min(100, score))
        assessment['threat_level'] = self._determine_threat_level(assessment['overall_score'])

        return assessment

    def _check_weak_algorithms(self, algorithm: str, hash_function: str) -> Dict[str, Any]:
        """Check for known weak algorithms"""
        result = {'penalty': 0, 'vulnerabilities': []}

        # Check main algorithm
        for weak_alg, threat_level in self.weak_algorithms.items():
            if weak_alg in algorithm:
                penalty = {
                    ThreatLevel.LOW: 10,
                    ThreatLevel.MEDIUM: 25,
                    ThreatLevel.HIGH: 50,
                    ThreatLevel.CRITICAL: 80
                }[threat_level]

                result['penalty'] += penalty
                result['vulnerabilities'].append({
                    'type': 'weak_algorithm',
                    'component': algorithm,
                    'severity': threat_level.value,
                    'description': f'{weak_alg.upper()} is cryptographically weak',
                    'cve_references': self._get_cve_references(weak_alg)
                })

        # Check hash function
        if hash_function:
            for weak_alg, threat_level in self.weak_algorithms.items():
                if weak_alg in hash_function:
                    result['penalty'] += 30
                    result['vulnerabilities'].append({
                        'type': 'weak_hash',
                        'component': hash_function,
                        'severity': threat_level.value,
                        'description': f'{hash_function.upper()} has known collision vulnerabilities'
                    })

        return result

    def _evaluate_key_length(self, algorithm: str, key_length: int) -> Dict[str, Any]:
        """Evaluate if key length is sufficient"""
        result = {'penalty': 0, 'vulnerability': None, 'strength': None}

        if key_length == 0:
            return result

        # Determine algorithm type
        if any(alg in algorithm for alg in ['aes', 'chacha', 'camellia']):
            min_len = self.min_key_lengths['symmetric']['minimum']
            rec_len = self.min_key_lengths['symmetric']['recommended']
            alg_type = 'symmetric'
        elif 'rsa' in algorithm:
            min_len = self.min_key_lengths['rsa']['minimum']
            rec_len = self.min_key_lengths['rsa']['recommended']
            alg_type = 'rsa'
        elif any(alg in algorithm for alg in ['ecc', 'ecdsa', 'ecdh']):
            min_len = self.min_key_lengths['ecc']['minimum']
            rec_len = self.min_key_lengths['ecc']['recommended']
            alg_type = 'ecc'
        else:
            return result

        if key_length < min_len:
            result['penalty'] = 40
            result['vulnerability'] = {
                'type': 'insufficient_key_length',
                'severity': ThreatLevel.HIGH.value,
                'description': f'{alg_type.upper()} key length {key_length} bits is below minimum secure length of {min_len} bits',
                'current_length': key_length,
                'minimum_length': min_len
            }
        elif key_length < rec_len:
            result['penalty'] = 15
            result['vulnerability'] = {
                'type': 'suboptimal_key_length',
                'severity': ThreatLevel.MEDIUM.value,
                'description': f'{alg_type.upper()} key length {key_length} bits is below recommended length of {rec_len} bits',
                'current_length': key_length,
                'recommended_length': rec_len
            }
        else:
            result['strength'] = f'Strong key length: {key_length} bits'

        return result

    def _evaluate_mode(self, mode: str, algorithm: str) -> Dict[str, Any]:
        """Evaluate mode of operation security"""
        result = {'penalty': 0, 'vulnerability': None, 'strength': None}

        if not mode:
            return result

        # Weak modes
        weak_modes = {
            'ecb': (ThreatLevel.CRITICAL, 'ECB mode leaks patterns in plaintext'),
            'cbc': (ThreatLevel.MEDIUM, 'CBC mode vulnerable to padding oracle attacks without proper implementation'),
        }

        # Strong modes
        strong_modes = ['gcm', 'ccm', 'eax', 'ocb', 'poly1305']

        if mode in weak_modes:
            threat_level, description = weak_modes[mode]
            penalty = 50 if threat_level == ThreatLevel.CRITICAL else 20
            result['penalty'] = penalty
            result['vulnerability'] = {
                'type': 'weak_mode',
                'severity': threat_level.value,
                'description': description,
                'mode': mode.upper()
            }
        elif any(strong_mode in mode for strong_mode in strong_modes):
            result['strength'] = f'Authenticated encryption mode: {mode.upper()}'

        return result

    def evaluate_attack_resistance(self, scheme) -> Dict[str, List[str]]:
        """Evaluate resistance against various attacks"""
        # Extract scheme components - handle both dict and CryptographicScheme objects
        if isinstance(scheme, dict):
            algorithm = scheme.get('algorithm', '').lower()
            key_length = scheme.get('key_length', 0) or 0
            mode = scheme.get('mode', '').lower()
        elif hasattr(scheme, 'architecture') and hasattr(scheme.architecture, 'components'):
            # Extract from CryptographicScheme object
            components = scheme.architecture.components
            algorithm = components[0].name.lower() if components else ''

            # Extract key length from parameters or components
            key_length = 0
            if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'key_size'):
                key_length = scheme.parameters.key_size or 0

            # Try to get key size from components if not found in parameters
            if not key_length and components:
                for comp in components:
                    if hasattr(comp, 'parameters') and hasattr(comp.parameters, 'key_size'):
                        key_sizes = comp.parameters.key_size
                        if isinstance(key_sizes, list) and key_sizes:
                            key_length = key_sizes[0]  # Use the first key size
                            break
                        elif isinstance(key_sizes, int):
                            key_length = key_sizes
                            break

            # Extract mode from parameters or component names
            mode = ''
            if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'additional_params'):
                mode = scheme.parameters.additional_params.get('mode', '').lower()
        else:
            algorithm = ''
            key_length = 0
            mode = ''

        # Ensure key_length is an integer
        if key_length is None:
            key_length = 0

        resistance = {
            'resistant': [],
            'vulnerable': [],
            'potentially_vulnerable': []
        }

        # Brute force
        if key_length >= 128:
            resistance['resistant'].append('brute_force: Key space is computationally infeasible to exhaust')
        elif key_length >= 80:
            resistance['potentially_vulnerable'].append('brute_force: Key length provides moderate security')
        else:
            resistance['vulnerable'].append('brute_force: Key length is too short')

        # Mode-specific vulnerabilities
        if mode == 'ecb':
            resistance['vulnerable'].append('chosen_plaintext: ECB mode reveals identical plaintext blocks')
            resistance['vulnerable'].append('pattern_analysis: ECB mode leaks data patterns')
        elif mode in ['gcm', 'ccm', 'eax']:
            resistance['resistant'].append('chosen_plaintext: Authenticated encryption prevents tampering')
            resistance['resistant'].append('chosen_ciphertext: Authentication tag validates integrity')

        # Timing attacks
        if 'gcm' in mode or 'poly1305' in algorithm:
            resistance['resistant'].append('timing: Constant-time implementations widely available')
        else:
            resistance['potentially_vulnerable'].append('timing: Implementation-dependent vulnerability')

        # Side-channel attacks
        if any(weak in algorithm for weak in ['des', 'rc4', 'md5']):
            resistance['vulnerable'].append('side_channel: Known side-channel vulnerabilities exist')
        else:
            resistance['potentially_vulnerable'].append('side_channel: Requires secure implementation practices')

        # Quantum attacks
        if any(pq in algorithm for pq in self.pq_resistant):
            resistance['resistant'].append('quantum: Post-quantum resistant algorithm')
        elif 'rsa' in algorithm or 'ecc' in algorithm or 'ecdsa' in algorithm:
            resistance['vulnerable'].append('quantum: Vulnerable to Shor\'s algorithm on quantum computers')
        elif 'aes' in algorithm:
            if key_length >= 256:
                resistance['resistant'].append('quantum: AES-256 maintains adequate security against Grover\'s algorithm')
            else:
                resistance['potentially_vulnerable'].append('quantum: AES-128 security halved by Grover\'s algorithm')

        # Collision attacks (for hash functions)
        hash_func = ''
        if isinstance(scheme, dict):
            if scheme.get('hash_function'):
                hash_func = scheme['hash_function'].lower()
        elif hasattr(scheme, 'architecture'):
            # Check if any component is a hash function
            components = scheme.architecture.components if hasattr(scheme.architecture, 'components') else []
            hash_components = [comp for comp in components if hasattr(comp, 'category') and hasattr(comp, 'name') and
                             ('hash' in comp.category.lower() or 'hash' in comp.name.lower())]
            if hash_components:
                hash_func = hash_components[0].name.lower()

        if hash_func:
            if 'md5' in hash_func:
                resistance['vulnerable'].append('collision: MD5 has practical collision attacks')
            elif 'sha1' in hash_func:
                resistance['vulnerable'].append('collision: SHA-1 collision attacks are feasible')
            elif 'sha-256' in hash_func or 'sha3' in hash_func:
                resistance['resistant'].append('collision: No practical collision attacks known')

        # MITM attacks
        includes_auth = False
        if isinstance(scheme, dict):
            includes_auth = scheme.get('includes_authentication', False)
        elif hasattr(scheme, 'architecture'):
            # Check if any component provides authentication
            components = scheme.architecture.components if hasattr(scheme.architecture, 'components') else []
            includes_auth = any('mac' in comp.category.lower() or 'aead' in comp.category.lower() or 'authentication' in comp.name.lower()
                              for comp in components if hasattr(comp, 'category') and hasattr(comp, 'name'))

        if includes_auth:
            resistance['resistant'].append('mitm: Authentication prevents man-in-the-middle attacks')
        else:
            resistance['potentially_vulnerable'].append('mitm: Requires additional authentication mechanism')

        # Replay attacks
        includes_nonce = False
        if isinstance(scheme, dict):
            includes_nonce = scheme.get('includes_nonce', False)
        elif hasattr(scheme, 'parameters'):
            # Check if parameters include nonce/IV
            includes_nonce = (hasattr(scheme.parameters, 'nonce_size') and scheme.parameters.nonce_size is not None) or \
                           ('gcm' in mode or 'ccm' in mode or 'eax' in mode)

        if includes_nonce or 'gcm' in mode:
            resistance['resistant'].append('replay: Nonce/IV prevents replay attacks')
        else:
            resistance['potentially_vulnerable'].append('replay: Should implement nonce or timestamp validation')

        return resistance

    def _calculate_attack_score(self, attack_vectors: Dict[str, List[str]]) -> int:
        """Calculate score based on attack resistance"""
        resistant_count = len(attack_vectors.get('resistant', []))
        vulnerable_count = len(attack_vectors.get('vulnerable', []))
        potentially_vulnerable_count = len(attack_vectors.get('potentially_vulnerable', []))

        # Start with base score
        score = 100

        # Penalize vulnerabilities
        score -= vulnerable_count * 15
        score -= potentially_vulnerable_count * 5

        # Bonus for strong resistance
        score += resistant_count * 2

        return max(0, min(100, score))

    def compliance_check(self, scheme) -> Dict[str, bool]:
        """Check compliance with various standards"""
        # Extract scheme components - handle both dict and CryptographicScheme objects
        if isinstance(scheme, dict):
            algorithm = scheme.get('algorithm', '').lower()
            key_length = scheme.get('key_length', 0) or 0
            mode = scheme.get('mode', '').lower()
        elif hasattr(scheme, 'architecture') and hasattr(scheme.architecture, 'components'):
            # Extract from CryptographicScheme object
            components = scheme.architecture.components
            algorithm = components[0].name.lower() if components else ''

            # Extract key length from parameters or components
            key_length = 0
            if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'key_size'):
                key_length = scheme.parameters.key_size or 0

            # Try to get key size from components if not found in parameters
            if not key_length and components:
                for comp in components:
                    if hasattr(comp, 'parameters') and hasattr(comp.parameters, 'key_size'):
                        key_sizes = comp.parameters.key_size
                        if isinstance(key_sizes, list) and key_sizes:
                            key_length = key_sizes[0]  # Use the first key size
                            break
                        elif isinstance(key_sizes, int):
                            key_length = key_sizes
                            break

            # Extract mode from parameters or component names
            mode = ''
            if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'additional_params'):
                mode = scheme.parameters.additional_params.get('mode', '').lower()
        else:
            algorithm = ''
            key_length = 0
            mode = ''

        # Ensure key_length is an integer
        if key_length is None:
            key_length = 0

        compliance = {
            'fips_140_2': False,
            'fips_140_3': False,
            'iso_iec_18033': False,
            'nist_approved': False,
            'pci_dss': False,
            'hipaa_compliant': False,
            'gdpr_suitable': False
        }

        # FIPS 140-2/3 compliance
        fips_algorithms = ['aes', 'sha-256', 'sha-384', 'sha-512', 'rsa', 'ecdsa']
        if any(alg in algorithm for alg in fips_algorithms):
            if 'aes' in algorithm and key_length >= 128:
                compliance['fips_140_2'] = True
                compliance['fips_140_3'] = True
            elif 'rsa' in algorithm and key_length >= 2048:
                compliance['fips_140_2'] = True
                compliance['fips_140_3'] = True
            elif 'ecdsa' in algorithm and key_length >= 256:
                compliance['fips_140_2'] = True
                compliance['fips_140_3'] = True

        # NIST approved
        if compliance['fips_140_2']:
            compliance['nist_approved'] = True

        # ISO/IEC 18033 (encryption algorithms)
        iso_algorithms = ['aes', 'camellia', 'rsa', 'ecc']
        if any(alg in algorithm for alg in iso_algorithms):
            compliance['iso_iec_18033'] = True

        # PCI DSS (Payment Card Industry)
        if 'aes' in algorithm and key_length >= 128 and mode != 'ecb':
            compliance['pci_dss'] = True
        elif 'rsa' in algorithm and key_length >= 2048:
            compliance['pci_dss'] = True

        # HIPAA (Healthcare)
        if key_length >= 128 and mode in ['gcm', 'ccm', 'cbc']:
            compliance['hipaa_compliant'] = True

        # GDPR (General Data Protection Regulation)
        if key_length >= 128 and 'aes' in algorithm:
            compliance['gdpr_suitable'] = True

        return compliance

    def _assess_quantum_readiness(self, algorithm: str) -> Dict[str, Any]:
        """Assess post-quantum cryptography readiness"""
        algorithm = algorithm.lower()

        assessment = {
            'resistant': False,
            'algorithm_type': 'classical',
            'years_until_vulnerable': None,
            'migration_priority': 'low',
            'recommended_alternatives': []
        }

        # Check if already post-quantum
        if any(pq in algorithm for pq in self.pq_resistant):
            assessment['resistant'] = True
            assessment['algorithm_type'] = 'post-quantum'
            assessment['migration_priority'] = 'none'
            return assessment

        # Assess vulnerability timeline
        if 'rsa' in algorithm or 'ecdsa' in algorithm or 'ecdh' in algorithm:
            assessment['years_until_vulnerable'] = 10  # Estimated
            assessment['migration_priority'] = 'high'
            assessment['recommended_alternatives'] = [
                'Kyber (key encapsulation)',
                'Dilithium (digital signatures)',
                'SPHINCS+ (stateless signatures)'
            ]
        elif 'aes' in algorithm:
            assessment['years_until_vulnerable'] = 20  # Grover's algorithm impact
            assessment['migration_priority'] = 'medium'
            assessment['recommended_alternatives'] = [
                'AES-256 (increased key size for quantum resistance)'
            ]
        elif 'sha' in algorithm:
            assessment['years_until_vulnerable'] = 20
            assessment['migration_priority'] = 'low'
            assessment['recommended_alternatives'] = [
                'SHA-512',
                'SHA3-256'
            ]

        return assessment

    def _generate_recommendations(self, scheme,
                                   vulnerabilities: List[Dict],
                                   compliance: Dict[str, bool]) -> List[str]:
        """Generate security improvement recommendations"""
        recommendations = []

        # Extract scheme components - handle both dict and CryptographicScheme objects
        if isinstance(scheme, dict):
            algorithm = scheme.get('algorithm', '').lower()
            key_length = scheme.get('key_length', 0) or 0
            mode = scheme.get('mode', '').lower()
        elif hasattr(scheme, 'architecture') and hasattr(scheme.architecture, 'components'):
            # Extract from CryptographicScheme object
            components = scheme.architecture.components
            algorithm = components[0].name.lower() if components else ''

            # Extract key length from parameters or components
            key_length = 0
            if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'key_size'):
                key_length = scheme.parameters.key_size or 0

            # Try to get key size from components if not found in parameters
            if not key_length and components:
                for comp in components:
                    if hasattr(comp, 'parameters') and hasattr(comp.parameters, 'key_size'):
                        key_sizes = comp.parameters.key_size
                        if isinstance(key_sizes, list) and key_sizes:
                            key_length = key_sizes[0]  # Use the first key size
                            break
                        elif isinstance(key_sizes, int):
                            key_length = key_sizes
                            break

            # Extract mode from parameters or component names
            mode = ''
            if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'additional_params'):
                mode = scheme.parameters.additional_params.get('mode', '').lower()
        else:
            algorithm = ''
            key_length = 0
            mode = ''

        # Ensure key_length is an integer
        if key_length is None:
            key_length = 0

        # Address critical vulnerabilities first
        critical_vulns = [v for v in vulnerabilities if v.get('severity') == ThreatLevel.CRITICAL.value]
        if critical_vulns:
            recommendations.append('URGENT: Replace cryptographically broken algorithms immediately')
            for vuln in critical_vulns:
                if vuln.get('type') == 'weak_algorithm':
                    recommendations.append(f"Replace {vuln.get('component')} with AES-256-GCM or ChaCha20-Poly1305")

        # Key length recommendations
        if key_length > 0 and key_length < 256:
            if 'aes' in algorithm:
                recommendations.append('Consider upgrading to AES-256 for long-term security')
            elif 'rsa' in algorithm and key_length < 3072:
                recommendations.append('Upgrade RSA key length to 3072 or 4096 bits')

        # Mode recommendations
        if mode == 'ecb':
            recommendations.append('Replace ECB mode with GCM or CCM for authenticated encryption')
        elif mode == 'cbc':
            recommendations.append('Consider migrating to GCM mode for built-in authentication')
        elif not mode and 'aes' in algorithm:
            recommendations.append('Specify an authenticated encryption mode like GCM')

        # Compliance recommendations
        if not compliance.get('fips_140_2'):
            recommendations.append('Consider using FIPS 140-2 validated cryptographic modules for regulated industries')

        # Quantum readiness
        if 'rsa' in algorithm or 'ecc' in algorithm:
            recommendations.append('Begin planning migration to post-quantum cryptography (Kyber, Dilithium)')

        # General best practices
        has_hash_function = False
        if isinstance(scheme, dict):
            has_hash_function = 'hash_function' in scheme and scheme['hash_function']
        elif hasattr(scheme, 'architecture'):
            # Check if any component is a hash function
            components = scheme.architecture.components if hasattr(scheme.architecture, 'components') else []
            has_hash_function = any('hash' in comp.category.lower() or 'hash' in comp.name.lower()
                                  for comp in components if hasattr(comp, 'category') and hasattr(comp, 'name'))

        if not has_hash_function:
            recommendations.append('Include hash function for integrity verification')

        # Check authentication and nonce based on scheme type
        includes_auth = False
        includes_nonce = False

        if isinstance(scheme, dict):
            includes_auth = scheme.get('includes_authentication', False)
            includes_nonce = scheme.get('includes_nonce', False)
        elif hasattr(scheme, 'architecture'):
            # Check if any component provides authentication
            components = scheme.architecture.components if hasattr(scheme.architecture, 'components') else []
            includes_auth = any('mac' in comp.category.lower() or 'aead' in comp.category.lower() or 'authentication' in comp.name.lower()
                              for comp in components if hasattr(comp, 'category') and hasattr(comp, 'name'))

            # Check nonce/IV from parameters
            if hasattr(scheme, 'parameters'):
                includes_nonce = (hasattr(scheme.parameters, 'nonce_size') and scheme.parameters.nonce_size is not None) or \
                               any('gcm' in comp.name.lower() or 'ccm' in comp.name.lower() or 'eax' in comp.name.lower()
                                   for comp in components if hasattr(comp, 'name'))

        if not includes_auth:
            recommendations.append('Implement message authentication (HMAC or authenticated encryption)')

        if not includes_nonce:
            recommendations.append('Ensure unique nonce/IV for each encryption operation')

        # Add positive reinforcement if scheme is strong
        if not recommendations:
            recommendations.append('Scheme follows current cryptographic best practices')
            recommendations.append('Regularly review security advisories for your cryptographic libraries')
            recommendations.append('Implement secure key management and rotation policies')

        return recommendations

    def _determine_threat_level(self, score: int) -> str:
        """Determine threat level from overall score"""
        if score >= 80:
            return ThreatLevel.LOW.value
        elif score >= 60:
            return ThreatLevel.MEDIUM.value
        elif score >= 40:
            return ThreatLevel.HIGH.value
        else:
            return ThreatLevel.CRITICAL.value

    def _get_cve_references(self, algorithm: str) -> List[str]:
        """Get relevant CVE references for known vulnerabilities"""
        cve_map = {
            'md5': ['CVE-2004-2761', 'CVE-2008-1384'],
            'sha1': ['CVE-2017-15277', 'CVE-2020-10735'],
            'des': ['CVE-1999-0554'],
            'rc4': ['CVE-2013-2566', 'CVE-2015-2808'],
        }
        return cve_map.get(algorithm, [])

    def check_component_compatibility(self, components: List[str]) -> Dict[str, Any]:
        """Check if components are securely compatible"""
        result = {
            'compatible': True,
            'issues': [],
            'warnings': [],
            'recommendations': []
        }

        components_lower = [c.lower() for c in components]

        # Check for incompatible combinations
        if 'ecb' in components_lower and any('aes' in c for c in components_lower):
            result['issues'].append({
                'severity': ThreatLevel.CRITICAL.value,
                'description': 'AES-ECB combination is cryptographically weak',
                'components': ['AES', 'ECB']
            })
            result['compatible'] = False

        # Check for weak component in otherwise strong scheme
        weak_components = [c for c in components_lower if any(w in c for w in self.weak_algorithms.keys())]
        if weak_components:
            result['issues'].append({
                'severity': ThreatLevel.HIGH.value,
                'description': f'Weak components detected: {", ".join(weak_components)}',
                'components': weak_components
            })
            result['compatible'] = False

        # Check for missing authentication in encryption schemes
        has_encryption = any(alg in ' '.join(components_lower) for alg in ['aes', 'chacha', 'rsa'])
        has_authentication = any(auth in ' '.join(components_lower) for auth in ['gcm', 'hmac', 'poly1305', 'ccm'])

        if has_encryption and not has_authentication:
            result['warnings'].append({
                'severity': ThreatLevel.MEDIUM.value,
                'description': 'Encryption without authentication detected',
                'recommendation': 'Add HMAC or use authenticated encryption mode'
            })

        # Check for hash function compatibility
        if 'hmac' in components_lower:
            has_hash = any(h in ' '.join(components_lower) for h in ['sha-256', 'sha-384', 'sha-512', 'sha3'])
            if not has_hash:
                result['warnings'].append({
                    'severity': ThreatLevel.MEDIUM.value,
                    'description': 'HMAC specified without explicit hash function',
                    'recommendation': 'Specify SHA-256 or stronger hash function'
                })

        # Provide combination recommendations
        if result['compatible'] and not result['warnings']:
            result['recommendations'].append('Component combination is secure')
        else:
            result['recommendations'].append('Review warnings and consider alternative combinations')

        return result

    def generate_security_report(self, assessment: Dict[str, Any]) -> str:
        """Generate a human-readable security report"""
        report_lines = [
            "=" * 80,
            "CRYPTOGRAPHIC SECURITY ASSESSMENT REPORT",
            "=" * 80,
            f"\nTimestamp: {assessment['timestamp']}",
            f"\nScheme: {assessment['scheme_info'].get('algorithm', 'Unknown')}",
            f"Overall Score: {assessment['overall_score']}/100",
            f"Threat Level: {assessment['threat_level'].upper()}",
            "\n" + "-" * 80,
        ]

        # Vulnerabilities
        if assessment['vulnerabilities']:
            report_lines.append("\nVULNERABILITIES DETECTED:")
            for vuln in assessment['vulnerabilities']:
                report_lines.append(f"\n  [{vuln.get('severity', 'unknown').upper()}] {vuln.get('type', 'Unknown')}")
                report_lines.append(f"  Description: {vuln.get('description', 'No description')}")

        # Attack Vectors
        report_lines.append("\n" + "-" * 80)
        report_lines.append("\nATTACK RESISTANCE ANALYSIS:")

        if assessment['attack_vectors'].get('resistant'):
            report_lines.append("\n  Resistant to:")
            for attack in assessment['attack_vectors']['resistant']:
                report_lines.append(f"    ✓ {attack}")

        if assessment['attack_vectors'].get('vulnerable'):
            report_lines.append("\n  Vulnerable to:")
            for attack in assessment['attack_vectors']['vulnerable']:
                report_lines.append(f"    ✗ {attack}")

        # Compliance
        report_lines.append("\n" + "-" * 80)
        report_lines.append("\nCOMPLIANCE STATUS:")
        for standard, compliant in assessment['compliance'].items():
            status = "✓ COMPLIANT" if compliant else "✗ NON-COMPLIANT"
            report_lines.append(f"  {standard.upper()}: {status}")

        # Recommendations
        if assessment['recommendations']:
            report_lines.append("\n" + "-" * 80)
            report_lines.append("\nRECOMMENDATIONS:")
            for i, rec in enumerate(assessment['recommendations'], 1):
                report_lines.append(f"  {i}. {rec}")

        report_lines.append("\n" + "=" * 80)

        return "\n".join(report_lines)
