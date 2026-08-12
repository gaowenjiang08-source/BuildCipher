"""
Scheme Comparison Feature
比较多个密码学方案的安全性、性能和适用性
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import statistics


@dataclass
class ComparisonMetrics:
    """Comparison metrics for schemes"""
    security_score: float  # 0-100
    performance_score: float  # 0-100
    complexity_score: float  # 0-100 (lower is better)
    standardization_score: float  # 0-100
    quantum_resistance: bool


class SchemeComparator:
    """Compare multiple cryptographic schemes"""

    # Known quantum-resistant algorithms
    QUANTUM_RESISTANT_SCHEMES = {
        'kyber', 'dilithium', 'sphincs', 'falcon', 'ntru', 'mceliece',
        'frodo', 'saber', 'rainbow', 'picnic', 'crystals-kyber',
        'crystals-dilithium', 'lattice', 'hash-based', 'code-based'
    }

    # Standardized schemes
    STANDARDIZED_SCHEMES = {
        'rsa': 100, 'aes': 100, 'sha-256': 100, 'sha-512': 100,
        'ecdsa': 100, 'ecdh': 100, 'ed25519': 100, 'curve25519': 100,
        'chacha20': 95, 'poly1305': 95, 'blake2': 90,
        'kyber': 85, 'dilithium': 85, 'sphincs': 80,
        'sha-3': 100, 'hmac': 100, 'gcm': 100, 'ccm': 100
    }

    # Security strength mappings (bits of security)
    SECURITY_STRENGTHS = {
        'aes-128': 128, 'aes-192': 192, 'aes-256': 256,
        'rsa-2048': 112, 'rsa-3072': 128, 'rsa-4096': 152,
        'sha-256': 128, 'sha-384': 192, 'sha-512': 256,
        'ecdsa-p256': 128, 'ecdsa-p384': 192, 'ecdsa-p521': 256,
        'ed25519': 128, 'curve25519': 128,
        'kyber512': 128, 'kyber768': 192, 'kyber1024': 256,
        'dilithium2': 128, 'dilithium3': 192, 'dilithium5': 256
    }

    def __init__(self):
        """Initialize the scheme comparator"""
        self.comparison_cache = {}

    def compare_schemes(self, schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare multiple schemes and return detailed comparison

        Args:
            schemes: List of scheme dictionaries with keys like:
                - name: Scheme name
                - type: Algorithm type (encryption, signature, hash, etc.)
                - key_size: Key size in bits
                - description: Optional description
                - properties: Optional dict of additional properties

        Returns:
            Dictionary containing:
            - side_by_side_table: Comparison table data
            - security_analysis: Security comparison
            - performance_analysis: Performance comparison
            - recommendations: Which scheme for which use case
        """
        if not schemes:
            return {
                'error': 'No schemes provided for comparison',
                'side_by_side_table': [],
                'security_analysis': {},
                'performance_analysis': {},
                'recommendations': []
            }

        if len(schemes) < 2:
            return {
                'error': 'At least 2 schemes required for comparison',
                'side_by_side_table': [],
                'security_analysis': {},
                'performance_analysis': {},
                'recommendations': []
            }

        # Calculate metrics for all schemes
        metrics_list = []
        for scheme in schemes:
            metrics = self.calculate_metrics(scheme)
            metrics_list.append({
                'scheme': scheme,
                'metrics': metrics
            })

        # Build side-by-side comparison table
        side_by_side = self._build_comparison_table(metrics_list)

        # Perform security analysis
        security_analysis = self._analyze_security(metrics_list)

        # Perform performance analysis
        performance_analysis = self._analyze_performance(metrics_list)

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics_list)

        return {
            'side_by_side_table': side_by_side,
            'security_analysis': security_analysis,
            'performance_analysis': performance_analysis,
            'recommendations': recommendations,
            'total_schemes': len(schemes)
        }

    def calculate_metrics(self, scheme) -> ComparisonMetrics:
        """
        Calculate comparison metrics for a single scheme

        Args:
            scheme: Dictionary or CryptographicScheme object containing scheme information

        Returns:
            ComparisonMetrics object with calculated scores
        """
        # Handle both dict and CryptographicScheme objects
        if isinstance(scheme, dict):
            name = scheme.get('name', '').lower()
            scheme_type = scheme.get('type', '').lower()
            key_size = scheme.get('key_size', 0)
            properties = scheme.get('properties', {})
        elif hasattr(scheme, 'metadata') and hasattr(scheme, 'architecture'):
            # Extract from CryptographicScheme object
            name = scheme.metadata.name.lower() if hasattr(scheme.metadata, 'name') else ''
            scheme_type = scheme.metadata.scheme_type.lower() if hasattr(scheme.metadata, 'scheme_type') else ''

            # Extract key size from parameters or components
            key_size = 0
            if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'key_size'):
                key_size = scheme.parameters.key_size or 0

            # Try to get key size from components if not found in parameters
            if not key_size and hasattr(scheme, 'architecture') and hasattr(scheme.architecture, 'components'):
                for comp in scheme.architecture.components:
                    if hasattr(comp, 'parameters') and hasattr(comp.parameters, 'key_size'):
                        key_sizes = comp.parameters.key_size
                        if isinstance(key_sizes, list) and key_sizes:
                            key_size = key_sizes[0]  # Use the first key size
                            break
                        elif isinstance(key_sizes, int):
                            key_size = key_sizes
                            break

            # Extract properties
            properties = {}
            if hasattr(scheme, 'security_analysis') and hasattr(scheme.security_analysis, 'properties'):
                properties = {'security_properties': scheme.security_analysis.properties}
        else:
            name = ''
            scheme_type = ''
            key_size = 0
            properties = {}

        # Ensure key_size is an integer
        if key_size is None:
            key_size = 0

        # Calculate security score (0-100)
        security_score = self._calculate_security_score(name, key_size, properties)

        # Calculate performance score (0-100)
        performance_score = self._calculate_performance_score(name, scheme_type, key_size)

        # Calculate complexity score (0-100, lower is better)
        complexity_score = self._calculate_complexity_score(name, scheme_type)

        # Calculate standardization score (0-100)
        standardization_score = self._calculate_standardization_score(name)

        # Determine quantum resistance
        quantum_resistance = self._is_quantum_resistant(name, properties)

        return ComparisonMetrics(
            security_score=security_score,
            performance_score=performance_score,
            complexity_score=complexity_score,
            standardization_score=standardization_score,
            quantum_resistance=quantum_resistance
        )

    def generate_comparison_chart(self, schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate data for visualization charts

        Args:
            schemes: List of scheme dictionaries

        Returns:
            Dictionary containing chart data for various visualizations
        """
        if not schemes:
            return {'error': 'No schemes provided'}

        # Helper to extract scheme name
        def get_scheme_name(scheme):
            if isinstance(scheme, dict):
                return scheme.get('name', 'Unknown')
            return scheme.metadata.name if hasattr(scheme, 'metadata') and hasattr(scheme.metadata, 'name') else 'Unknown'

        metrics_list = []
        for scheme in schemes:
            metrics = self.calculate_metrics(scheme)
            metrics_list.append({
                'name': get_scheme_name(scheme),
                'metrics': metrics
            })

        # Radar chart data (for multi-dimensional comparison)
        radar_data = {
            'labels': ['Security', 'Performance', 'Simplicity', 'Standardization'],
            'datasets': []
        }

        for item in metrics_list:
            radar_data['datasets'].append({
                'label': item['name'],
                'data': [
                    item['metrics'].security_score,
                    item['metrics'].performance_score,
                    100 - item['metrics'].complexity_score,  # Invert complexity
                    item['metrics'].standardization_score
                ]
            })

        # Bar chart data (for individual metric comparison)
        bar_data = {
            'labels': [item['name'] for item in metrics_list],
            'datasets': [
                {
                    'label': 'Security Score',
                    'data': [item['metrics'].security_score for item in metrics_list]
                },
                {
                    'label': 'Performance Score',
                    'data': [item['metrics'].performance_score for item in metrics_list]
                },
                {
                    'label': 'Standardization Score',
                    'data': [item['metrics'].standardization_score for item in metrics_list]
                }
            ]
        }

        # Scatter plot data (security vs performance)
        scatter_data = {
            'datasets': [{
                'label': item['name'],
                'data': [{
                    'x': item['metrics'].performance_score,
                    'y': item['metrics'].security_score,
                    'quantum_resistant': item['metrics'].quantum_resistance
                }]
            } for item in metrics_list]
        }

        # Quantum resistance pie chart
        quantum_resistant_count = sum(
            1 for item in metrics_list if item['metrics'].quantum_resistance
        )
        pie_data = {
            'labels': ['Quantum Resistant', 'Classical'],
            'data': [quantum_resistant_count, len(metrics_list) - quantum_resistant_count]
        }

        return {
            'radar_chart': radar_data,
            'bar_chart': bar_data,
            'scatter_plot': scatter_data,
            'quantum_pie_chart': pie_data,
            'total_schemes': len(schemes)
        }

    def _calculate_security_score(self, name: str, key_size: int,
                                   properties: Dict[str, Any]) -> float:
        """Calculate security score based on scheme characteristics"""
        base_score = 70.0

        # Check for known security strengths
        for scheme_key, bits in self.SECURITY_STRENGTHS.items():
            if scheme_key in name:
                # Map security bits to 0-100 scale
                # 128 bits = 85, 192 bits = 92, 256 bits = 100
                base_score = min(100, 60 + (bits / 256) * 40)
                break

        # Adjust based on key size
        if key_size >= 256:
            base_score = min(100, base_score + 10)
        elif key_size >= 192:
            base_score = min(100, base_score + 5)
        elif key_size > 0 and key_size < 128:
            base_score = max(20, base_score - 20)

        # Bonus for modern algorithms
        modern_algos = ['aes', 'sha-3', 'chacha20', 'ed25519', 'curve25519']
        if any(algo in name for algo in modern_algos):
            base_score = min(100, base_score + 5)

        # Penalty for deprecated algorithms
        deprecated = ['md5', 'sha-1', 'des', 'rc4']
        if any(algo in name for algo in deprecated):
            base_score = max(10, base_score - 40)

        # Check properties for security features
        if properties.get('authenticated'):
            base_score = min(100, base_score + 5)
        if properties.get('perfect_forward_secrecy'):
            base_score = min(100, base_score + 5)

        return round(base_score, 2)

    def _calculate_performance_score(self, name: str, scheme_type: str,
                                      key_size: int) -> float:
        """Calculate performance score based on algorithm characteristics"""
        base_score = 60.0

        # Symmetric algorithms are generally faster
        if scheme_type in ['encryption', 'cipher'] and any(
            sym in name for sym in ['aes', 'chacha', 'salsa']
        ):
            base_score = 85.0

        # Hash functions are typically fast
        if scheme_type == 'hash':
            base_score = 80.0
            if 'sha-256' in name or 'blake2' in name:
                base_score = 90.0

        # Asymmetric algorithms are slower
        if any(asym in name for asym in ['rsa', 'ecdsa', 'dsa']):
            base_score = 45.0
            # Elliptic curve is faster than RSA
            if 'ec' in name or 'ed25519' in name or 'curve25519' in name:
                base_score = 65.0

        # Post-quantum algorithms vary in performance
        if self._is_quantum_resistant(name, {}):
            # Lattice-based are relatively fast
            if any(lat in name for lat in ['kyber', 'dilithium', 'ntru']):
                base_score = 60.0
            # Hash-based are slower
            elif any(h in name for h in ['sphincs', 'hash-based']):
                base_score = 35.0
            # Code-based are very slow
            elif 'mceliece' in name:
                base_score = 25.0

        # Adjust based on key size (larger keys = slower)
        if key_size > 4096:
            base_score = max(20, base_score - 15)
        elif key_size > 2048:
            base_score = max(30, base_score - 10)

        return round(base_score, 2)

    def _calculate_complexity_score(self, name: str, scheme_type: str) -> float:
        """Calculate complexity score (lower is better)"""
        base_score = 50.0

        # Symmetric ciphers are simpler
        if any(sym in name for sym in ['aes', 'chacha', 'salsa']):
            base_score = 30.0

        # Hash functions are relatively simple
        if scheme_type == 'hash':
            base_score = 35.0

        # Asymmetric algorithms are more complex
        if 'rsa' in name:
            base_score = 60.0
        if any(ec in name for ec in ['ecdsa', 'ecdh', 'ed25519']):
            base_score = 55.0

        # Post-quantum algorithms are very complex
        if self._is_quantum_resistant(name, {}):
            base_score = 75.0
            # Lattice-based are moderately complex
            if any(lat in name for lat in ['kyber', 'dilithium']):
                base_score = 70.0
            # Hash-based are simpler
            elif 'sphincs' in name or 'hash-based' in name:
                base_score = 65.0

        # Well-documented algorithms are less complex to use
        if any(std in name for std in ['aes', 'sha-256', 'rsa', 'ecdsa']):
            base_score = max(20, base_score - 10)

        return round(base_score, 2)

    def _calculate_standardization_score(self, name: str) -> float:
        """Calculate standardization score based on adoption and standards"""
        # Check exact matches first
        for scheme, score in self.STANDARDIZED_SCHEMES.items():
            if scheme in name:
                return float(score)

        # Check for NIST standards
        nist_standards = ['fips', 'nist', 'sp800']
        if any(std in name for std in nist_standards):
            return 95.0

        # Check for ISO standards
        if 'iso' in name:
            return 90.0

        # Default for unknown schemes
        return 40.0

    def _is_quantum_resistant(self, name: str, properties: Dict[str, Any]) -> bool:
        """Determine if scheme is quantum resistant"""
        # Check explicit property
        if properties.get('quantum_resistant'):
            return True

        # Check against known quantum-resistant schemes
        return any(qr in name for qr in self.QUANTUM_RESISTANT_SCHEMES)

    def _build_comparison_table(self, metrics_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build side-by-side comparison table"""
        table = []

        for item in metrics_list:
            scheme = item['scheme']
            metrics = item['metrics']

            # Extract scheme information (handle both dict and CryptographicScheme)
            if isinstance(scheme, dict):
                name = scheme.get('name', 'Unknown')
                scheme_type = scheme.get('type', 'Unknown')
                key_size = scheme.get('key_size', 'N/A')
            else:
                # CryptographicScheme object
                name = scheme.metadata.name if hasattr(scheme, 'metadata') and hasattr(scheme.metadata, 'name') else 'Unknown'
                scheme_type = scheme.metadata.scheme_type if hasattr(scheme, 'metadata') and hasattr(scheme.metadata, 'scheme_type') else 'Unknown'

                # Extract key size
                key_size = 'N/A'
                if hasattr(scheme, 'parameters') and hasattr(scheme.parameters, 'key_size'):
                    key_size = scheme.parameters.key_size or 'N/A'

            table.append({
                'name': name,
                'type': scheme_type,
                'key_size': key_size,
                'security_score': metrics.security_score,
                'performance_score': metrics.performance_score,
                'complexity_score': metrics.complexity_score,
                'standardization_score': metrics.standardization_score,
                'quantum_resistant': bool(metrics.quantum_resistance),
                'overall_score': self._calculate_overall_score(metrics)
            })

        # Sort by overall score descending
        table.sort(key=lambda x: x['overall_score'], reverse=True)

        return table

    def _calculate_overall_score(self, metrics: ComparisonMetrics) -> float:
        """Calculate weighted overall score"""
        weights = {
            'security': 0.40,
            'performance': 0.25,
            'simplicity': 0.15,  # Inverted complexity
            'standardization': 0.20
        }

        overall = (
            metrics.security_score * weights['security'] +
            metrics.performance_score * weights['performance'] +
            (100 - metrics.complexity_score) * weights['simplicity'] +
            metrics.standardization_score * weights['standardization']
        )

        # Bonus for quantum resistance
        if metrics.quantum_resistance:
            overall = min(100, overall + 5)

        return round(overall, 2)

    def _analyze_security(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform detailed security analysis"""
        security_scores = [item['metrics'].security_score for item in metrics_list]

        highest_security = max(metrics_list, key=lambda x: x['metrics'].security_score)
        lowest_security = min(metrics_list, key=lambda x: x['metrics'].security_score)

        quantum_resistant = [
            item for item in metrics_list if item['metrics'].quantum_resistance
        ]

        # Helper to extract scheme name
        def get_scheme_name(scheme):
            if isinstance(scheme, dict):
                return scheme.get('name', 'Unknown')
            return scheme.metadata.name if hasattr(scheme, 'metadata') and hasattr(scheme.metadata, 'name') else 'Unknown'

        return {
            'average_security_score': round(statistics.mean(security_scores), 2),
            'median_security_score': round(statistics.median(security_scores), 2),
            'highest_security': {
                'name': get_scheme_name(highest_security['scheme']),
                'score': highest_security['metrics'].security_score
            },
            'lowest_security': {
                'name': get_scheme_name(lowest_security['scheme']),
                'score': lowest_security['metrics'].security_score
            },
            'quantum_resistant_count': len(quantum_resistant),
            'quantum_resistant_percentage': round(
                len(quantum_resistant) / len(metrics_list) * 100, 2
            ),
            'quantum_resistant_schemes': [
                get_scheme_name(item['scheme']) for item in quantum_resistant
            ]
        }

    def _analyze_performance(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform detailed performance analysis"""
        performance_scores = [item['metrics'].performance_score for item in metrics_list]

        fastest = max(metrics_list, key=lambda x: x['metrics'].performance_score)
        slowest = min(metrics_list, key=lambda x: x['metrics'].performance_score)

        # Helper to extract scheme name
        def get_scheme_name(scheme):
            if isinstance(scheme, dict):
                return scheme.get('name', 'Unknown')
            return scheme.metadata.name if hasattr(scheme, 'metadata') and hasattr(scheme.metadata, 'name') else 'Unknown'

        return {
            'average_performance_score': round(statistics.mean(performance_scores), 2),
            'median_performance_score': round(statistics.median(performance_scores), 2),
            'fastest_scheme': {
                'name': get_scheme_name(fastest['scheme']),
                'score': fastest['metrics'].performance_score
            },
            'slowest_scheme': {
                'name': get_scheme_name(slowest['scheme']),
                'score': slowest['metrics'].performance_score
            },
            'performance_range': round(max(performance_scores) - min(performance_scores), 2)
        }

    def _generate_recommendations(self, metrics_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate recommendations for different use cases"""
        recommendations = []

        # Helper to extract scheme name
        def get_scheme_name(scheme):
            if isinstance(scheme, dict):
                return scheme.get('name', 'Unknown')
            return scheme.metadata.name if hasattr(scheme, 'metadata') and hasattr(scheme.metadata, 'name') else 'Unknown'

        # Best overall
        best_overall = max(
            metrics_list,
            key=lambda x: self._calculate_overall_score(x['metrics'])
        )
        recommendations.append({
            'use_case': 'General Purpose / Best Overall',
            'recommended_scheme': get_scheme_name(best_overall['scheme']),
            'reason': f"Highest overall score ({self._calculate_overall_score(best_overall['metrics'])}), "
                     f"balancing security, performance, and standardization"
        })

        # Best security
        best_security = max(metrics_list, key=lambda x: x['metrics'].security_score)
        if best_security != best_overall:
            recommendations.append({
                'use_case': 'Maximum Security Required',
                'recommended_scheme': get_scheme_name(best_security['scheme']),
                'reason': f"Highest security score ({best_security['metrics'].security_score})"
            })

        # Best performance
        best_performance = max(metrics_list, key=lambda x: x['metrics'].performance_score)
        if best_performance != best_overall:
            recommendations.append({
                'use_case': 'Performance Critical Applications',
                'recommended_scheme': get_scheme_name(best_performance['scheme']),
                'reason': f"Highest performance score ({best_performance['metrics'].performance_score})"
            })

        # Quantum resistant recommendation
        quantum_resistant = [
            item for item in metrics_list if item['metrics'].quantum_resistance
        ]
        if quantum_resistant:
            best_quantum = max(
                quantum_resistant,
                key=lambda x: self._calculate_overall_score(x['metrics'])
            )
            recommendations.append({
                'use_case': 'Future-Proof / Quantum Threat Protection',
                'recommended_scheme': get_scheme_name(best_quantum['scheme']),
                'reason': 'Quantum resistant with best overall metrics among quantum-safe options'
            })

        # Best standardization
        best_standard = max(metrics_list, key=lambda x: x['metrics'].standardization_score)
        if best_standard['metrics'].standardization_score >= 90:
            recommendations.append({
                'use_case': 'Regulatory Compliance / Industry Standards',
                'recommended_scheme': get_scheme_name(best_standard['scheme']),
                'reason': f"Highest standardization score ({best_standard['metrics'].standardization_score}), "
                         "widely adopted and certified"
            })

        # Simplest to implement
        simplest = min(metrics_list, key=lambda x: x['metrics'].complexity_score)
        if simplest['metrics'].complexity_score <= 40:
            recommendations.append({
                'use_case': 'Rapid Development / Simple Implementation',
                'recommended_scheme': get_scheme_name(simplest['scheme']),
                'reason': f"Lowest complexity score ({simplest['metrics'].complexity_score}), "
                         "easier to implement and maintain"
            })

        return recommendations
