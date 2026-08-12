"""
Benchmark Runner
自动化基准测试套件
"""

from typing import Dict, List, Any, Optional
import time
import hashlib
import secrets
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics


@dataclass
class BenchmarkResult:
    """Benchmark result"""
    operation: str
    throughput_mbps: float
    latency_ms: float
    operations_per_second: int
    cpu_usage_percent: float
    memory_mb: float


class BenchmarkRunner:
    """Run automated benchmarks"""

    # Industry baseline standards (approximate values)
    BASELINES = {
        'AES-128': {'throughput_mbps': 500, 'latency_ms': 0.01},
        'AES-256': {'throughput_mbps': 400, 'latency_ms': 0.012},
        'RSA-2048': {'throughput_mbps': 10, 'latency_ms': 2.0},
        'RSA-4096': {'throughput_mbps': 2, 'latency_ms': 8.0},
        'SHA-256': {'throughput_mbps': 600, 'latency_ms': 0.008},
        'SHA-512': {'throughput_mbps': 550, 'latency_ms': 0.009},
        'ECDSA-256': {'throughput_mbps': 50, 'latency_ms': 0.5},
        'ECDSA-384': {'throughput_mbps': 30, 'latency_ms': 0.8},
    }

    def __init__(self):
        """Initialize benchmark runner"""
        self.results_history = []

    def run_benchmark_suite(self,
                           scheme: Dict[str, Any],
                           data_sizes: List[int] = None) -> Dict[str, Any]:
        """
        Run comprehensive benchmark suite

        Args:
            scheme: Cryptographic scheme configuration
            data_sizes: List of data sizes to test (in bytes)

        Returns:
            - results: Benchmark results
            - comparison: vs industry standards
            - bottlenecks: Performance bottlenecks
            - recommendations: Optimization suggestions
        """
        if data_sizes is None:
            data_sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB

        results = {
            'timestamp': datetime.now().isoformat(),
            'scheme': scheme,
            'data_sizes': data_sizes,
            'benchmarks': [],
            'summary': {},
        }

        # Extract scheme details
        encryption_algo = scheme.get('encryption', {}).get('algorithm', 'AES')
        key_size = scheme.get('encryption', {}).get('key_size', 256)
        hash_algo = scheme.get('hashing', {}).get('algorithm', 'SHA-256')
        signature_algo = scheme.get('signature', {}).get('algorithm', 'RSA')
        sig_key_size = scheme.get('signature', {}).get('key_size', 2048)

        # Run encryption benchmarks
        for size in data_sizes:
            enc_result = self.benchmark_encryption(encryption_algo, key_size, size)
            results['benchmarks'].append(asdict(enc_result))

        # Run hashing benchmarks
        for size in data_sizes:
            hash_result = self.benchmark_hashing(hash_algo, size)
            results['benchmarks'].append(asdict(hash_result))

        # Run signature benchmarks (only for smaller sizes)
        for size in [s for s in data_sizes if s <= 102400]:
            sig_result = self.benchmark_signature(signature_algo, sig_key_size)
            results['benchmarks'].append(asdict(sig_result))

        # Calculate summary statistics
        results['summary'] = self._calculate_summary(results['benchmarks'])

        # Compare with baselines
        comparison = self.compare_with_baseline(results['benchmarks'])

        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(results['benchmarks'], comparison)

        # Generate recommendations
        recommendations = self._generate_recommendations(bottlenecks, scheme)

        return {
            'results': results,
            'comparison': comparison,
            'bottlenecks': bottlenecks,
            'recommendations': recommendations
        }

    def benchmark_encryption(self, algo: str, key_size: int, data_size: int) -> BenchmarkResult:
        """Benchmark encryption performance"""
        operation = f"{algo}-{key_size} Encryption"

        # Simulate encryption operations
        iterations = max(10, 1000000 // data_size)  # Adjust iterations based on data size

        # Generate test data
        test_data = secrets.token_bytes(data_size)

        # Warm-up
        for _ in range(min(5, iterations)):
            self._simulate_encryption(algo, key_size, test_data)

        # Actual benchmark
        latencies = []
        start_time = time.perf_counter()

        for _ in range(iterations):
            op_start = time.perf_counter()
            self._simulate_encryption(algo, key_size, test_data)
            op_end = time.perf_counter()
            latencies.append((op_end - op_start) * 1000)  # Convert to ms

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Calculate metrics
        avg_latency = statistics.mean(latencies)
        ops_per_second = int(iterations / total_time)
        total_data_mb = (data_size * iterations) / (1024 * 1024)
        throughput_mbps = total_data_mb / total_time

        # Estimate CPU and memory usage based on algorithm
        cpu_usage = self._estimate_cpu_usage(algo, key_size, 'encryption')
        memory_mb = self._estimate_memory_usage(algo, key_size, data_size)

        return BenchmarkResult(
            operation=operation,
            throughput_mbps=round(throughput_mbps, 2),
            latency_ms=round(avg_latency, 4),
            operations_per_second=ops_per_second,
            cpu_usage_percent=round(cpu_usage, 1),
            memory_mb=round(memory_mb, 2)
        )

    def benchmark_hashing(self, algo: str, data_size: int) -> BenchmarkResult:
        """Benchmark hash performance"""
        operation = f"{algo} Hashing"

        # Simulate hashing operations
        iterations = max(10, 2000000 // data_size)

        # Generate test data
        test_data = secrets.token_bytes(data_size)

        # Get hash function
        hash_func = self._get_hash_function(algo)

        # Warm-up
        for _ in range(min(5, iterations)):
            hash_func(test_data).digest()

        # Actual benchmark
        latencies = []
        start_time = time.perf_counter()

        for _ in range(iterations):
            op_start = time.perf_counter()
            hash_func(test_data).digest()
            op_end = time.perf_counter()
            latencies.append((op_end - op_start) * 1000)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Calculate metrics
        avg_latency = statistics.mean(latencies)
        ops_per_second = int(iterations / total_time)
        total_data_mb = (data_size * iterations) / (1024 * 1024)
        throughput_mbps = total_data_mb / total_time

        cpu_usage = self._estimate_cpu_usage(algo, 0, 'hashing')
        memory_mb = self._estimate_memory_usage(algo, 0, data_size)

        return BenchmarkResult(
            operation=operation,
            throughput_mbps=round(throughput_mbps, 2),
            latency_ms=round(avg_latency, 4),
            operations_per_second=ops_per_second,
            cpu_usage_percent=round(cpu_usage, 1),
            memory_mb=round(memory_mb, 2)
        )

    def benchmark_signature(self, algo: str, key_size: int) -> BenchmarkResult:
        """Benchmark signature performance"""
        operation = f"{algo}-{key_size} Signature"

        # Signature operations are slower, use fewer iterations
        iterations = 100

        # Generate test data (hash of message)
        test_data = secrets.token_bytes(32)

        # Warm-up
        for _ in range(5):
            self._simulate_signature(algo, key_size, test_data)

        # Actual benchmark
        latencies = []
        start_time = time.perf_counter()

        for _ in range(iterations):
            op_start = time.perf_counter()
            self._simulate_signature(algo, key_size, test_data)
            op_end = time.perf_counter()
            latencies.append((op_end - op_start) * 1000)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Calculate metrics
        avg_latency = statistics.mean(latencies)
        ops_per_second = int(iterations / total_time)

        # Throughput for signatures is operation-based, not data-based
        throughput_mbps = ops_per_second * 0.032  # Approximate

        cpu_usage = self._estimate_cpu_usage(algo, key_size, 'signature')
        memory_mb = self._estimate_memory_usage(algo, key_size, 32)

        return BenchmarkResult(
            operation=operation,
            throughput_mbps=round(throughput_mbps, 2),
            latency_ms=round(avg_latency, 4),
            operations_per_second=ops_per_second,
            cpu_usage_percent=round(cpu_usage, 1),
            memory_mb=round(memory_mb, 2)
        )

    def compare_with_baseline(self, results: List[Dict]) -> Dict:
        """Compare with industry baselines"""
        comparisons = []

        for result in results:
            operation = result['operation']

            # Find matching baseline
            baseline_key = None
            for key in self.BASELINES.keys():
                if key in operation:
                    baseline_key = key
                    break

            if baseline_key:
                baseline = self.BASELINES[baseline_key]
                throughput_ratio = result['throughput_mbps'] / baseline['throughput_mbps']
                latency_ratio = baseline['latency_ms'] / result['latency_ms']  # Inverted (lower is better)

                performance_score = (throughput_ratio + latency_ratio) / 2

                comparisons.append({
                    'operation': operation,
                    'baseline': baseline_key,
                    'throughput_ratio': round(throughput_ratio, 2),
                    'latency_ratio': round(latency_ratio, 2),
                    'performance_score': round(performance_score, 2),
                    'status': self._get_performance_status(performance_score)
                })

        return {
            'comparisons': comparisons,
            'average_score': round(statistics.mean([c['performance_score'] for c in comparisons]), 2) if comparisons else 0
        }

    def generate_performance_report(self, results: Dict) -> str:
        """Generate detailed performance report"""
        report = []
        report.append("=" * 80)
        report.append("PERFORMANCE BENCHMARK REPORT")
        report.append("=" * 80)
        report.append(f"Timestamp: {results['results']['timestamp']}")
        report.append(f"Data Sizes Tested: {', '.join(map(str, results['results']['data_sizes']))} bytes")
        report.append("")

        # Benchmark Results
        report.append("-" * 80)
        report.append("BENCHMARK RESULTS")
        report.append("-" * 80)
        report.append(f"{'Operation':<30} {'Throughput':<15} {'Latency':<15} {'Ops/sec':<12} {'CPU %':<8} {'Mem MB':<8}")
        report.append("-" * 80)

        for bench in results['results']['benchmarks']:
            report.append(
                f"{bench['operation']:<30} "
                f"{bench['throughput_mbps']:>10.2f} MB/s "
                f"{bench['latency_ms']:>10.4f} ms "
                f"{bench['operations_per_second']:>12,} "
                f"{bench['cpu_usage_percent']:>7.1f} "
                f"{bench['memory_mb']:>7.2f}"
            )

        # Summary Statistics
        report.append("")
        report.append("-" * 80)
        report.append("SUMMARY STATISTICS")
        report.append("-" * 80)
        summary = results['results']['summary']
        report.append(f"Average Throughput: {summary['avg_throughput']:.2f} MB/s")
        report.append(f"Average Latency: {summary['avg_latency']:.4f} ms")
        report.append(f"Total Operations: {summary['total_operations']:,}")
        report.append(f"Peak Throughput: {summary['peak_throughput']:.2f} MB/s")
        report.append(f"Min Latency: {summary['min_latency']:.4f} ms")

        # Baseline Comparison
        report.append("")
        report.append("-" * 80)
        report.append("BASELINE COMPARISON")
        report.append("-" * 80)
        report.append(f"Overall Performance Score: {results['comparison']['average_score']:.2f}")
        report.append("")
        report.append(f"{'Operation':<30} {'Baseline':<20} {'Score':<10} {'Status':<15}")
        report.append("-" * 80)

        for comp in results['comparison']['comparisons']:
            report.append(
                f"{comp['operation']:<30} "
                f"{comp['baseline']:<20} "
                f"{comp['performance_score']:<10.2f} "
                f"{comp['status']:<15}"
            )

        # Bottlenecks
        if results['bottlenecks']:
            report.append("")
            report.append("-" * 80)
            report.append("IDENTIFIED BOTTLENECKS")
            report.append("-" * 80)
            for i, bottleneck in enumerate(results['bottlenecks'], 1):
                report.append(f"{i}. {bottleneck['operation']}")
                report.append(f"   Type: {bottleneck['type']}")
                report.append(f"   Severity: {bottleneck['severity']}")
                report.append(f"   Details: {bottleneck['details']}")
                report.append("")

        # Recommendations
        if results['recommendations']:
            report.append("-" * 80)
            report.append("OPTIMIZATION RECOMMENDATIONS")
            report.append("-" * 80)
            for i, rec in enumerate(results['recommendations'], 1):
                report.append(f"{i}. [{rec['priority']}] {rec['recommendation']}")
                report.append(f"   Impact: {rec['impact']}")
                report.append(f"   Effort: {rec['effort']}")
                report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    def _simulate_encryption(self, algo: str, key_size: int, data: bytes) -> bytes:
        """Simulate encryption operation"""
        # Use actual hashing as a stand-in for encryption workload
        # In real implementation, would use actual crypto libraries
        key = secrets.token_bytes(key_size // 8)

        # Simulate block cipher operations
        if 'AES' in algo.upper():
            # AES-like operation
            result = hashlib.sha256(key + data).digest()
            # Multiple rounds for larger key sizes
            rounds = key_size // 128
            for _ in range(rounds):
                result = hashlib.sha256(result + data).digest()
        else:
            # Generic symmetric encryption simulation
            result = hashlib.sha256(key + data).digest()

        return result

    def _simulate_signature(self, algo: str, key_size: int, data: bytes) -> bytes:
        """Simulate signature operation"""
        # Simulate expensive asymmetric operation
        key = secrets.token_bytes(key_size // 8)

        # More expensive operation for RSA
        if 'RSA' in algo.upper():
            result = data
            # Simulate modular exponentiation cost
            iterations = key_size // 256
            for _ in range(iterations):
                result = hashlib.sha512(result + key).digest()
        elif 'ECDSA' in algo.upper() or 'ECC' in algo.upper():
            # ECDSA is faster than RSA
            result = hashlib.sha384(data + key).digest()
            iterations = key_size // 512
            for _ in range(max(1, iterations)):
                result = hashlib.sha384(result).digest()
        else:
            result = hashlib.sha256(data + key).digest()

        return result

    def _get_hash_function(self, algo: str):
        """Get hash function by algorithm name"""
        algo_upper = algo.upper().replace('-', '')

        hash_map = {
            'SHA256': hashlib.sha256,
            'SHA512': hashlib.sha512,
            'SHA384': hashlib.sha384,
            'SHA1': hashlib.sha1,
            'MD5': hashlib.md5,
        }

        return hash_map.get(algo_upper, hashlib.sha256)

    def _estimate_cpu_usage(self, algo: str, key_size: int, operation_type: str) -> float:
        """Estimate CPU usage percentage"""
        base_cpu = 10.0

        if operation_type == 'encryption':
            if 'AES' in algo.upper():
                base_cpu = 15.0 + (key_size / 256) * 5
            else:
                base_cpu = 20.0
        elif operation_type == 'hashing':
            if 'SHA-512' in algo.upper():
                base_cpu = 12.0
            elif 'SHA-256' in algo.upper():
                base_cpu = 10.0
            else:
                base_cpu = 8.0
        elif operation_type == 'signature':
            if 'RSA' in algo.upper():
                base_cpu = 30.0 + (key_size / 1024) * 10
            elif 'ECDSA' in algo.upper():
                base_cpu = 20.0 + (key_size / 256) * 5
            else:
                base_cpu = 25.0

        return min(base_cpu, 100.0)

    def _estimate_memory_usage(self, algo: str, key_size: int, data_size: int) -> float:
        """Estimate memory usage in MB"""
        # Base memory overhead
        base_memory = 0.5

        # Data size contribution
        data_memory = data_size / (1024 * 1024)

        # Key size contribution
        key_memory = (key_size / 8) / (1024 * 1024)

        # Algorithm overhead
        if 'RSA' in algo.upper():
            algo_overhead = 2.0
        elif 'AES' in algo.upper():
            algo_overhead = 0.5
        else:
            algo_overhead = 1.0

        return base_memory + data_memory + key_memory + algo_overhead

    def _calculate_summary(self, benchmarks: List[Dict]) -> Dict:
        """Calculate summary statistics"""
        throughputs = [b['throughput_mbps'] for b in benchmarks]
        latencies = [b['latency_ms'] for b in benchmarks]
        total_ops = sum(b['operations_per_second'] for b in benchmarks)

        return {
            'avg_throughput': round(statistics.mean(throughputs), 2),
            'avg_latency': round(statistics.mean(latencies), 4),
            'total_operations': total_ops,
            'peak_throughput': round(max(throughputs), 2),
            'min_latency': round(min(latencies), 4),
            'max_latency': round(max(latencies), 4),
        }

    def _identify_bottlenecks(self, benchmarks: List[Dict], comparison: Dict) -> List[Dict]:
        """Identify performance bottlenecks"""
        bottlenecks = []

        for bench in benchmarks:
            issues = []

            # Check for high latency
            if bench['latency_ms'] > 10:
                issues.append({
                    'operation': bench['operation'],
                    'type': 'High Latency',
                    'severity': 'HIGH' if bench['latency_ms'] > 50 else 'MEDIUM',
                    'details': f"Latency of {bench['latency_ms']:.2f}ms exceeds threshold"
                })

            # Check for low throughput
            if bench['throughput_mbps'] < 10:
                issues.append({
                    'operation': bench['operation'],
                    'type': 'Low Throughput',
                    'severity': 'HIGH' if bench['throughput_mbps'] < 1 else 'MEDIUM',
                    'details': f"Throughput of {bench['throughput_mbps']:.2f} MB/s is below target"
                })

            # Check for high CPU usage
            if bench['cpu_usage_percent'] > 70:
                issues.append({
                    'operation': bench['operation'],
                    'type': 'High CPU Usage',
                    'severity': 'MEDIUM',
                    'details': f"CPU usage of {bench['cpu_usage_percent']:.1f}% may limit scalability"
                })

            # Check for high memory usage
            if bench['memory_mb'] > 100:
                issues.append({
                    'operation': bench['operation'],
                    'type': 'High Memory Usage',
                    'severity': 'LOW',
                    'details': f"Memory usage of {bench['memory_mb']:.2f} MB may be optimized"
                })

            bottlenecks.extend(issues)

        # Check baseline comparisons
        for comp in comparison.get('comparisons', []):
            if comp['performance_score'] < 0.5:
                bottlenecks.append({
                    'operation': comp['operation'],
                    'type': 'Below Baseline',
                    'severity': 'HIGH',
                    'details': f"Performance score {comp['performance_score']:.2f} is significantly below industry baseline"
                })

        return bottlenecks

    def _generate_recommendations(self, bottlenecks: List[Dict], scheme: Dict) -> List[Dict]:
        """Generate optimization recommendations"""
        recommendations = []

        # Group bottlenecks by type
        bottleneck_types = {}
        for b in bottlenecks:
            b_type = b['type']
            if b_type not in bottleneck_types:
                bottleneck_types[b_type] = []
            bottleneck_types[b_type].append(b)

        # High latency recommendations
        if 'High Latency' in bottleneck_types:
            recommendations.append({
                'priority': 'HIGH',
                'recommendation': 'Consider using hardware acceleration (AES-NI) for cryptographic operations',
                'impact': 'Can reduce latency by 50-80%',
                'effort': 'Medium - requires hardware support detection and implementation'
            })

            recommendations.append({
                'priority': 'MEDIUM',
                'recommendation': 'Implement operation batching to amortize overhead costs',
                'impact': 'Can improve throughput by 30-50%',
                'effort': 'Low - modify API to accept batch operations'
            })

        # Low throughput recommendations
        if 'Low Throughput' in bottleneck_types:
            recommendations.append({
                'priority': 'HIGH',
                'recommendation': 'Enable parallel processing for independent operations',
                'impact': 'Can increase throughput by 2-4x on multi-core systems',
                'effort': 'Medium - implement thread pool or async processing'
            })

            recommendations.append({
                'priority': 'MEDIUM',
                'recommendation': 'Use streaming APIs for large data processing',
                'impact': 'Reduces memory usage and improves throughput for large files',
                'effort': 'Medium - refactor to support streaming interfaces'
            })

        # High CPU usage recommendations
        if 'High CPU Usage' in bottleneck_types:
            recommendations.append({
                'priority': 'MEDIUM',
                'recommendation': 'Reduce key sizes where security requirements allow',
                'impact': 'Can reduce CPU usage by 20-40% for RSA operations',
                'effort': 'Low - update configuration, review security requirements'
            })

            recommendations.append({
                'priority': 'MEDIUM',
                'recommendation': 'Consider switching to ECC for public-key operations',
                'impact': 'Provides similar security with better performance',
                'effort': 'High - significant algorithm change'
            })

        # Below baseline recommendations
        if 'Below Baseline' in bottleneck_types:
            recommendations.append({
                'priority': 'HIGH',
                'recommendation': 'Update to latest cryptographic libraries with optimizations',
                'impact': 'Can improve performance by 30-100%',
                'effort': 'Low - library upgrade and testing'
            })

            recommendations.append({
                'priority': 'HIGH',
                'recommendation': 'Profile code to identify specific slow paths',
                'impact': 'Enables targeted optimization',
                'effort': 'Medium - requires profiling tools and analysis'
            })

        # General recommendations
        recommendations.append({
            'priority': 'LOW',
            'recommendation': 'Implement caching for frequently used keys and contexts',
            'impact': 'Reduces initialization overhead',
            'effort': 'Low - add simple caching layer'
        })

        recommendations.append({
            'priority': 'LOW',
            'recommendation': 'Monitor performance in production to identify real-world bottlenecks',
            'impact': 'Provides data-driven optimization targets',
            'effort': 'Medium - implement monitoring and metrics collection'
        })

        return recommendations

    def _get_performance_status(self, score: float) -> str:
        """Get performance status based on score"""
        if score >= 1.0:
            return 'EXCELLENT'
        elif score >= 0.8:
            return 'GOOD'
        elif score >= 0.6:
            return 'ACCEPTABLE'
        elif score >= 0.4:
            return 'POOR'
        else:
            return 'CRITICAL'
