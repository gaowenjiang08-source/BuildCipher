"""
Performance Estimator
估算密码学方案在不同平台上的性能
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import math


class Platform(Enum):
    SERVER = "server"  # High-end x86_64
    DESKTOP = "desktop"  # Consumer PC
    MOBILE = "mobile"  # Smartphone
    IOT = "iot"  # Resource-constrained IoT
    EMBEDDED = "embedded"  # Embedded systems


class PerformanceEstimator:
    """Estimate performance of cryptographic schemes"""

    def __init__(self):
        # Benchmark data for common algorithms on different platforms
        self.benchmarks = {}
        self._load_benchmarks()

        # Platform specifications
        self.platform_specs = {
            Platform.SERVER: {
                "cpu_ghz": 3.5,
                "cores": 16,
                "cache_mb": 32,
                "ram_gb": 64,
                "simd": "AVX512",
                "aes_ni": True,
                "power_watts": 150
            },
            Platform.DESKTOP: {
                "cpu_ghz": 3.0,
                "cores": 8,
                "cache_mb": 16,
                "ram_gb": 16,
                "simd": "AVX2",
                "aes_ni": True,
                "power_watts": 65
            },
            Platform.MOBILE: {
                "cpu_ghz": 2.5,
                "cores": 8,
                "cache_mb": 4,
                "ram_gb": 8,
                "simd": "NEON",
                "aes_ni": True,
                "power_watts": 5
            },
            Platform.IOT: {
                "cpu_ghz": 0.8,
                "cores": 2,
                "cache_mb": 0.5,
                "ram_gb": 0.512,
                "simd": None,
                "aes_ni": False,
                "power_watts": 1
            },
            Platform.EMBEDDED: {
                "cpu_ghz": 0.168,
                "cores": 1,
                "cache_mb": 0.256,
                "ram_gb": 0.256,
                "simd": None,
                "aes_ni": False,
                "power_watts": 0.3
            }
        }

    def estimate_performance(self,
                           scheme: Dict[str, Any],
                           platform: Platform,
                           data_size_mb: float = 1.0) -> Dict[str, Any]:
        """
        Estimate performance metrics

        Returns:
            - throughput_mbps: MB/s
            - latency_ms: Milliseconds per operation
            - cpu_cycles: Approximate CPU cycles
            - memory_kb: Memory usage
            - energy_mj: Energy consumption (millijoules)
            - bottleneck: Performance bottleneck
        """
        if not isinstance(platform, Platform):
            platform = Platform(platform)

        algorithm = scheme.get('algorithm', '').lower()
        mode = scheme.get('mode', '').lower()
        key_size = scheme.get('key_size', 128)

        # Get base benchmark for this algorithm
        base_perf = self._get_base_performance(algorithm, mode, key_size, platform)

        if not base_perf:
            return self._estimate_unknown_algorithm(scheme, platform, data_size_mb)

        # Calculate metrics
        throughput_mbps = base_perf['throughput_mbps']

        # Adjust for platform-specific features
        throughput_mbps = self._apply_platform_multipliers(
            throughput_mbps, algorithm, platform
        )

        # Calculate latency for given data size
        latency_ms = (data_size_mb / throughput_mbps) * 1000

        # Estimate CPU cycles
        platform_spec = self.platform_specs[platform]
        cpu_cycles = int(latency_ms * platform_spec['cpu_ghz'] * 1_000_000)

        # Estimate memory usage
        memory_kb = self._estimate_memory(algorithm, mode, key_size, data_size_mb)

        # Estimate energy consumption
        energy_mj = self._estimate_energy(
            latency_ms, platform_spec['power_watts']
        )

        # Find bottleneck
        bottleneck = self.find_bottleneck(scheme, platform)

        return {
            'throughput_mbps': round(throughput_mbps, 2),
            'latency_ms': round(latency_ms, 3),
            'cpu_cycles': cpu_cycles,
            'memory_kb': round(memory_kb, 2),
            'energy_mj': round(energy_mj, 3),
            'bottleneck': bottleneck,
            'platform': platform.value,
            'data_size_mb': data_size_mb
        }

    def compare_platforms(self,
                         scheme: Dict[str, Any],
                         data_size_mb: float = 1.0) -> Dict[Platform, Dict]:
        """Compare performance across all platforms"""
        results = {}

        for platform in Platform:
            results[platform] = self.estimate_performance(
                scheme, platform, data_size_mb
            )

        # Add relative performance metrics
        server_throughput = results[Platform.SERVER]['throughput_mbps']

        for platform, metrics in results.items():
            metrics['relative_performance'] = round(
                metrics['throughput_mbps'] / server_throughput, 3
            )
            metrics['platform_name'] = platform.value

        return results

    def find_bottleneck(self, scheme: Dict[str, Any],
                       platform: Platform) -> str:
        """Identify performance bottleneck"""
        if not isinstance(platform, Platform):
            platform = Platform(platform)

        algorithm = scheme.get('algorithm', '').lower()
        mode = scheme.get('mode', '').lower()
        key_size = scheme.get('key_size', 128)

        platform_spec = self.platform_specs[platform]

        # Check for various bottlenecks
        bottlenecks = []

        # Memory constraints
        if 'rsa' in algorithm or 'ecc' in algorithm or 'kyber' in algorithm:
            if platform_spec['ram_gb'] < 1:
                bottlenecks.append("Insufficient RAM for key operations")

        # No hardware acceleration
        if 'aes' in algorithm and not platform_spec['aes_ni']:
            bottlenecks.append("Missing AES-NI hardware acceleration")

        # SIMD limitations
        if algorithm in ['chacha20', 'blake2', 'sha3']:
            if not platform_spec['simd']:
                bottlenecks.append("No SIMD support for parallel operations")

        # CPU speed for asymmetric crypto
        if algorithm in ['rsa', 'ecc', 'ecdsa', 'ecdh']:
            if platform_spec['cpu_ghz'] < 1.0:
                bottlenecks.append("Low CPU frequency for public-key operations")

        # Cache size for large operations
        required_cache = self._estimate_cache_requirement(algorithm, key_size)
        if required_cache > platform_spec['cache_mb']:
            bottlenecks.append("Insufficient cache size causing memory stalls")

        # Mode-specific bottlenecks
        if mode in ['gcm', 'ccm']:
            if not platform_spec['aes_ni']:
                bottlenecks.append("AEAD mode without hardware support")

        if mode == 'cbc':
            bottlenecks.append("CBC mode prevents parallel processing")

        if not bottlenecks:
            # Determine primary bottleneck based on algorithm type
            if 'rsa' in algorithm or 'ecc' in algorithm:
                return "CPU-bound: Public-key operations require intensive computation"
            elif mode == 'gcm':
                return "Memory-bound: GCM requires frequent memory access for GHASH"
            elif platform_spec['cpu_ghz'] < 2.0:
                return "CPU frequency limiting throughput"
            else:
                return "Memory bandwidth optimal, CPU efficient"

        return "; ".join(bottlenecks)

    def recommend_optimization(self,
                              scheme: Dict[str, Any],
                              platform: Platform) -> List[str]:
        """Recommend performance optimizations"""
        if not isinstance(platform, Platform):
            platform = Platform(platform)

        algorithm = scheme.get('algorithm', '').lower()
        mode = scheme.get('mode', '').lower()
        key_size = scheme.get('key_size', 128)

        recommendations = []
        platform_spec = self.platform_specs[platform]

        # Algorithm-specific recommendations
        if 'aes' in algorithm:
            if not platform_spec['aes_ni']:
                recommendations.append(
                    "Consider ChaCha20 instead of AES for better software performance"
                )
            if mode == 'cbc':
                recommendations.append(
                    "Switch from CBC to CTR mode for parallel encryption"
                )
            if mode not in ['gcm', 'ccm', 'eax']:
                recommendations.append(
                    "Use authenticated encryption mode (GCM/CCM) for security"
                )

        if 'rsa' in algorithm:
            if key_size > 2048:
                recommendations.append(
                    f"RSA-{key_size} is slow; consider ECC for equivalent security"
                )
            if platform_spec['ram_gb'] < 1:
                recommendations.append(
                    "Insufficient RAM for RSA operations; use ECC or Ed25519"
                )
            recommendations.append(
                "Cache RSA public key operations when possible"
            )

        if algorithm in ['ecdsa', 'ecdh', 'ecc']:
            recommendations.append(
                "Use precomputed tables for common elliptic curve operations"
            )
            if platform == Platform.EMBEDDED or platform == Platform.IOT:
                recommendations.append(
                    "Consider Curve25519 for faster operations on constrained devices"
                )

        # Hash function recommendations
        if algorithm in ['sha256', 'sha512']:
            if platform_spec['simd']:
                recommendations.append(
                    "Enable SIMD optimizations for SHA-2 parallel processing"
                )
            if algorithm == 'sha512' and platform == Platform.MOBILE:
                recommendations.append(
                    "SHA-256 may be faster than SHA-512 on 32-bit ARM processors"
                )

        if algorithm == 'sha3':
            recommendations.append(
                "Consider BLAKE2 for better performance with similar security"
            )

        # Platform-specific recommendations
        if platform == Platform.SERVER:
            recommendations.append(
                "Utilize multi-threading for bulk encryption operations"
            )
            if 'aes' in algorithm:
                recommendations.append(
                    "Enable AES-NI and AVX-512 instruction sets"
                )

        elif platform == Platform.MOBILE:
            recommendations.append(
                "Batch cryptographic operations to reduce power consumption"
            )
            recommendations.append(
                "Use hardware crypto accelerators if available (ARM TrustZone)"
            )

        elif platform == Platform.IOT or platform == Platform.EMBEDDED:
            recommendations.append(
                "Prefer lightweight algorithms: ChaCha20, Ed25519, BLAKE2"
            )
            recommendations.append(
                "Minimize key exchanges; use session keys for bulk encryption"
            )
            if 'aes' in algorithm and key_size > 128:
                recommendations.append(
                    "AES-128 provides sufficient security with better performance"
                )

        # Post-quantum considerations
        if 'kyber' in algorithm or 'dilithium' in algorithm:
            recommendations.append(
                "Post-quantum algorithms are compute-intensive; use hybrid schemes"
            )
            recommendations.append(
                "Cache PQ public keys to amortize computational cost"
            )

        # General recommendations
        if not recommendations:
            recommendations.append(
                "Current configuration is well-optimized for the target platform"
            )

        return recommendations

    def _get_base_performance(self, algorithm: str, mode: str,
                            key_size: int, platform: Platform) -> Optional[Dict]:
        """Get base performance metrics for an algorithm"""
        # Try exact match first
        key = f"{algorithm}_{mode}_{key_size}".lower()
        if key in self.benchmarks.get(platform, {}):
            return self.benchmarks[platform][key]

        # Try without mode
        key = f"{algorithm}_{key_size}".lower()
        if key in self.benchmarks.get(platform, {}):
            return self.benchmarks[platform][key]

        # Try without key size
        key = f"{algorithm}_{mode}".lower()
        if key in self.benchmarks.get(platform, {}):
            return self.benchmarks[platform][key]

        # Try just algorithm
        if algorithm in self.benchmarks.get(platform, {}):
            return self.benchmarks[platform][algorithm]

        return None

    def _apply_platform_multipliers(self, throughput: float,
                                   algorithm: str, platform: Platform) -> float:
        """Apply platform-specific performance multipliers"""
        spec = self.platform_specs[platform]

        # AES-NI gives ~4-8x speedup for AES
        if 'aes' in algorithm and spec['aes_ni']:
            # Already included in benchmarks, no additional multiplier
            pass
        elif 'aes' in algorithm and not spec['aes_ni']:
            throughput *= 0.2  # Software AES is ~5x slower

        # SIMD benefits for certain algorithms
        if algorithm in ['chacha20', 'blake2', 'sha256', 'sha512']:
            if spec['simd'] == 'AVX512':
                throughput *= 1.3
            elif spec['simd'] == 'AVX2':
                throughput *= 1.15
            elif spec['simd'] == 'NEON':
                throughput *= 1.1

        return throughput

    def _estimate_memory(self, algorithm: str, mode: str,
                        key_size: int, data_size_mb: float) -> float:
        """Estimate memory usage in KB"""
        base_memory = 0

        # Algorithm-specific memory
        if 'aes' in algorithm:
            base_memory = 4  # Key schedule + state
        elif 'chacha20' in algorithm:
            base_memory = 2  # Minimal state
        elif 'rsa' in algorithm:
            base_memory = key_size / 4  # Key storage
        elif 'ecc' in algorithm or 'ecdsa' in algorithm:
            base_memory = 1  # Point coordinates
        elif 'sha' in algorithm or 'blake' in algorithm:
            base_memory = 0.5  # Hash state
        elif 'kyber' in algorithm:
            base_memory = 32  # Polynomial representation
        elif 'dilithium' in algorithm:
            base_memory = 64  # Signature vectors

        # Mode overhead
        if mode == 'gcm':
            base_memory += 4  # GHASH tables
        elif mode == 'ccm':
            base_memory += 2

        # Buffer memory (assume double-buffering)
        buffer_memory = min(data_size_mb * 1024, 4096)  # Cap at 4MB buffers

        return base_memory + buffer_memory

    def _estimate_energy(self, latency_ms: float, power_watts: float) -> float:
        """Estimate energy consumption in millijoules"""
        # E = P * t
        time_seconds = latency_ms / 1000
        energy_joules = power_watts * time_seconds
        return energy_joules * 1000  # Convert to millijoules

    def _estimate_cache_requirement(self, algorithm: str, key_size: int) -> float:
        """Estimate required cache size in MB"""
        if 'aes' in algorithm:
            return 0.5  # T-tables
        elif 'rsa' in algorithm:
            return key_size / 1024  # Key operations
        elif algorithm in ['sha256', 'sha512']:
            return 0.1
        else:
            return 0.05

    def _estimate_unknown_algorithm(self, scheme: Dict[str, Any],
                                   platform: Platform,
                                   data_size_mb: float) -> Dict[str, Any]:
        """Provide conservative estimates for unknown algorithms"""
        platform_spec = self.platform_specs[platform]

        # Conservative estimates
        throughput_mbps = platform_spec['cpu_ghz'] * 50  # Rough estimate
        latency_ms = (data_size_mb / throughput_mbps) * 1000
        cpu_cycles = int(latency_ms * platform_spec['cpu_ghz'] * 1_000_000)
        memory_kb = 1024  # 1MB buffer
        energy_mj = self._estimate_energy(latency_ms, platform_spec['power_watts'])

        return {
            'throughput_mbps': round(throughput_mbps, 2),
            'latency_ms': round(latency_ms, 3),
            'cpu_cycles': cpu_cycles,
            'memory_kb': memory_kb,
            'energy_mj': round(energy_mj, 3),
            'bottleneck': 'Unknown algorithm - estimates are conservative',
            'platform': platform.value,
            'data_size_mb': data_size_mb
        }

    def _load_benchmarks(self):
        """Load benchmark data for algorithms"""
        # Benchmarks in MB/s (megabytes per second)
        # Based on real-world measurements from OpenSSL, libsodium, and other libraries

        # SERVER platform (high-end x86_64 with AES-NI and AVX-512)
        self.benchmarks[Platform.SERVER] = {
            # Symmetric encryption
            'aes_cbc_128': {'throughput_mbps': 3500},
            'aes_cbc_192': {'throughput_mbps': 3000},
            'aes_cbc_256': {'throughput_mbps': 2600},
            'aes_ctr_128': {'throughput_mbps': 4200},
            'aes_ctr_192': {'throughput_mbps': 3600},
            'aes_ctr_256': {'throughput_mbps': 3200},
            'aes_gcm_128': {'throughput_mbps': 3800},
            'aes_gcm_192': {'throughput_mbps': 3200},
            'aes_gcm_256': {'throughput_mbps': 2900},
            'chacha20': {'throughput_mbps': 2800},
            'chacha20_poly1305': {'throughput_mbps': 2600},

            # Hash functions
            'sha256': {'throughput_mbps': 2200},
            'sha512': {'throughput_mbps': 1800},
            'sha3_256': {'throughput_mbps': 800},
            'sha3_512': {'throughput_mbps': 600},
            'blake2b': {'throughput_mbps': 2500},
            'blake2s': {'throughput_mbps': 1800},

            # Public-key crypto (operations per second, converted to effective MB/s)
            'rsa_2048': {'throughput_mbps': 2.5},  # ~2000 sign/s
            'rsa_3072': {'throughput_mbps': 0.8},  # ~600 sign/s
            'rsa_4096': {'throughput_mbps': 0.3},  # ~250 sign/s
            'ecdsa_256': {'throughput_mbps': 12},  # ~10000 sign/s
            'ecdsa_384': {'throughput_mbps': 6},   # ~5000 sign/s
            'ecdh_256': {'throughput_mbps': 15},   # ~12000 ops/s
            'ed25519': {'throughput_mbps': 25},    # ~20000 sign/s
            'curve25519': {'throughput_mbps': 30}, # ~25000 ops/s

            # Post-quantum
            'kyber512': {'throughput_mbps': 8},
            'kyber768': {'throughput_mbps': 5},
            'kyber1024': {'throughput_mbps': 3},
            'dilithium2': {'throughput_mbps': 6},
            'dilithium3': {'throughput_mbps': 4},
            'dilithium5': {'throughput_mbps': 2},
        }

        # DESKTOP platform (consumer PC with AES-NI)
        self.benchmarks[Platform.DESKTOP] = {
            'aes_cbc_128': {'throughput_mbps': 2000},
            'aes_cbc_192': {'throughput_mbps': 1700},
            'aes_cbc_256': {'throughput_mbps': 1500},
            'aes_ctr_128': {'throughput_mbps': 2400},
            'aes_ctr_192': {'throughput_mbps': 2000},
            'aes_ctr_256': {'throughput_mbps': 1800},
            'aes_gcm_128': {'throughput_mbps': 2200},
            'aes_gcm_192': {'throughput_mbps': 1800},
            'aes_gcm_256': {'throughput_mbps': 1600},
            'chacha20': {'throughput_mbps': 1600},
            'chacha20_poly1305': {'throughput_mbps': 1500},

            'sha256': {'throughput_mbps': 1200},
            'sha512': {'throughput_mbps': 1000},
            'sha3_256': {'throughput_mbps': 450},
            'sha3_512': {'throughput_mbps': 350},
            'blake2b': {'throughput_mbps': 1400},
            'blake2s': {'throughput_mbps': 1000},

            'rsa_2048': {'throughput_mbps': 1.5},
            'rsa_3072': {'throughput_mbps': 0.5},
            'rsa_4096': {'throughput_mbps': 0.2},
            'ecdsa_256': {'throughput_mbps': 7},
            'ecdsa_384': {'throughput_mbps': 3.5},
            'ecdh_256': {'throughput_mbps': 9},
            'ed25519': {'throughput_mbps': 15},
            'curve25519': {'throughput_mbps': 18},

            'kyber512': {'throughput_mbps': 5},
            'kyber768': {'throughput_mbps': 3},
            'kyber1024': {'throughput_mbps': 2},
            'dilithium2': {'throughput_mbps': 4},
            'dilithium3': {'throughput_mbps': 2.5},
            'dilithium5': {'throughput_mbps': 1.5},
        }

        # MOBILE platform (ARM with NEON and crypto extensions)
        self.benchmarks[Platform.MOBILE] = {
            'aes_cbc_128': {'throughput_mbps': 800},
            'aes_cbc_192': {'throughput_mbps': 680},
            'aes_cbc_256': {'throughput_mbps': 600},
            'aes_ctr_128': {'throughput_mbps': 950},
            'aes_ctr_192': {'throughput_mbps': 800},
            'aes_ctr_256': {'throughput_mbps': 700},
            'aes_gcm_128': {'throughput_mbps': 850},
            'aes_gcm_192': {'throughput_mbps': 720},
            'aes_gcm_256': {'throughput_mbps': 650},
            'chacha20': {'throughput_mbps': 600},
            'chacha20_poly1305': {'throughput_mbps': 550},

            'sha256': {'throughput_mbps': 400},
            'sha512': {'throughput_mbps': 200},  # Slower on 32-bit ARM
            'sha3_256': {'throughput_mbps': 150},
            'sha3_512': {'throughput_mbps': 100},
            'blake2b': {'throughput_mbps': 450},
            'blake2s': {'throughput_mbps': 500},

            'rsa_2048': {'throughput_mbps': 0.4},
            'rsa_3072': {'throughput_mbps': 0.15},
            'rsa_4096': {'throughput_mbps': 0.06},
            'ecdsa_256': {'throughput_mbps': 2},
            'ecdsa_384': {'throughput_mbps': 1},
            'ecdh_256': {'throughput_mbps': 2.5},
            'ed25519': {'throughput_mbps': 4},
            'curve25519': {'throughput_mbps': 5},

            'kyber512': {'throughput_mbps': 1.5},
            'kyber768': {'throughput_mbps': 1},
            'kyber1024': {'throughput_mbps': 0.6},
            'dilithium2': {'throughput_mbps': 1.2},
            'dilithium3': {'throughput_mbps': 0.8},
            'dilithium5': {'throughput_mbps': 0.4},
        }

        # IOT platform (low-power ARM Cortex-M, no crypto extensions)
        self.benchmarks[Platform.IOT] = {
            'aes_cbc_128': {'throughput_mbps': 8},
            'aes_cbc_192': {'throughput_mbps': 6.5},
            'aes_cbc_256': {'throughput_mbps': 5.5},
            'aes_ctr_128': {'throughput_mbps': 9},
            'aes_ctr_192': {'throughput_mbps': 7.5},
            'aes_ctr_256': {'throughput_mbps': 6.5},
            'aes_gcm_128': {'throughput_mbps': 7},
            'aes_gcm_192': {'throughput_mbps': 5.8},
            'aes_gcm_256': {'throughput_mbps': 5},
            'chacha20': {'throughput_mbps': 12},  # Better in software
            'chacha20_poly1305': {'throughput_mbps': 10},

            'sha256': {'throughput_mbps': 5},
            'sha512': {'throughput_mbps': 2},
            'sha3_256': {'throughput_mbps': 1.5},
            'sha3_512': {'throughput_mbps': 1},
            'blake2b': {'throughput_mbps': 6},
            'blake2s': {'throughput_mbps': 8},

            'rsa_2048': {'throughput_mbps': 0.01},
            'rsa_3072': {'throughput_mbps': 0.003},
            'rsa_4096': {'throughput_mbps': 0.001},
            'ecdsa_256': {'throughput_mbps': 0.05},
            'ecdsa_384': {'throughput_mbps': 0.025},
            'ecdh_256': {'throughput_mbps': 0.06},
            'ed25519': {'throughput_mbps': 0.08},
            'curve25519': {'throughput_mbps': 0.1},

            'kyber512': {'throughput_mbps': 0.04},
            'kyber768': {'throughput_mbps': 0.025},
            'kyber1024': {'throughput_mbps': 0.015},
            'dilithium2': {'throughput_mbps': 0.03},
            'dilithium3': {'throughput_mbps': 0.02},
            'dilithium5': {'throughput_mbps': 0.01},
        }

        # EMBEDDED platform (8-bit/16-bit microcontroller)
        self.benchmarks[Platform.EMBEDDED] = {
            'aes_cbc_128': {'throughput_mbps': 0.5},
            'aes_cbc_192': {'throughput_mbps': 0.4},
            'aes_cbc_256': {'throughput_mbps': 0.35},
            'aes_ctr_128': {'throughput_mbps': 0.55},
            'aes_ctr_192': {'throughput_mbps': 0.45},
            'aes_ctr_256': {'throughput_mbps': 0.4},
            'aes_gcm_128': {'throughput_mbps': 0.4},
            'aes_gcm_192': {'throughput_mbps': 0.33},
            'aes_gcm_256': {'throughput_mbps': 0.3},
            'chacha20': {'throughput_mbps': 0.8},
            'chacha20_poly1305': {'throughput_mbps': 0.7},

            'sha256': {'throughput_mbps': 0.3},
            'sha512': {'throughput_mbps': 0.1},
            'sha3_256': {'throughput_mbps': 0.08},
            'sha3_512': {'throughput_mbps': 0.05},
            'blake2b': {'throughput_mbps': 0.35},
            'blake2s': {'throughput_mbps': 0.5},

            'rsa_2048': {'throughput_mbps': 0.0005},
            'rsa_3072': {'throughput_mbps': 0.0002},
            'rsa_4096': {'throughput_mbps': 0.0001},
            'ecdsa_256': {'throughput_mbps': 0.003},
            'ecdsa_384': {'throughput_mbps': 0.0015},
            'ecdh_256': {'throughput_mbps': 0.004},
            'ed25519': {'throughput_mbps': 0.005},
            'curve25519': {'throughput_mbps': 0.006},

            'kyber512': {'throughput_mbps': 0.002},
            'kyber768': {'throughput_mbps': 0.001},
            'kyber1024': {'throughput_mbps': 0.0008},
            'dilithium2': {'throughput_mbps': 0.0015},
            'dilithium3': {'throughput_mbps': 0.001},
            'dilithium5': {'throughput_mbps': 0.0006},
        }
