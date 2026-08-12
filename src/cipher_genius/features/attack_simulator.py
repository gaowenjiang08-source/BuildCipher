"""
Attack Simulator
模拟攻击测试工具

Simulates various cryptographic attacks to assess security strength.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass
import math


class AttackType(Enum):
    """Types of cryptographic attacks"""
    BRUTE_FORCE = "brute_force"
    TIMING_ATTACK = "timing_attack"
    PADDING_ORACLE = "padding_oracle"
    COLLISION = "collision"
    MITM = "mitm"
    REPLAY = "replay"
    QUANTUM = "quantum"


@dataclass
class AttackResult:
    """Attack simulation result"""
    attack_type: AttackType
    success_probability: float  # 0.0 to 1.0
    time_to_break: str  # Human readable time estimate
    computational_cost: str  # Number of operations
    feasibility: str  # practical, theoretical, infeasible
    mitigation_effectiveness: float  # 0.0 to 1.0
    details: Optional[str] = None


class AttackSimulator:
    """Simulate various cryptographic attacks"""

    # Attack complexity constants (operations per second)
    STANDARD_PC_OPS = 1e9  # 1 billion ops/sec
    CLUSTER_OPS = 1e15  # 1 petaflop/sec
    SUPERCOMPUTER_OPS = 1e18  # 1 exaflop/sec
    QUANTUM_SPEEDUP_SHOR = lambda self, n: n**3  # Polynomial for Shor's
    QUANTUM_SPEEDUP_GROVER = lambda self, n: math.sqrt(2**n)  # Square root for Grover's

    # Time constants (in seconds)
    SECOND = 1
    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    YEAR = 31536000

    def simulate_attacks(self, scheme: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate all relevant attacks

        Args:
            scheme: Encryption scheme configuration containing:
                - algorithm: Algorithm name
                - key_size: Key size in bits
                - mode: Encryption mode
                - parameters: Additional parameters

        Returns:
            Dictionary containing:
            - attack_results: Results per attack type
            - weakest_link: Most vulnerable component
            - time_to_compromise: Estimated time for fastest attack
            - mitigation_status: Current protections
            - overall_security_score: 0.0 to 1.0
        """
        algorithm = scheme.get('algorithm', '').upper()
        key_size = scheme.get('key_size', 128)
        mode = scheme.get('mode', '')

        attack_results = {}

        # Brute force attack (always applicable)
        attack_results['brute_force'] = self.simulate_brute_force(key_size)

        # Timing attack (applicable to most implementations)
        attack_results['timing_attack'] = self.simulate_timing_attack(scheme)

        # Padding oracle (applicable to CBC mode)
        if mode and 'CBC' in mode.upper():
            attack_results['padding_oracle'] = self.simulate_padding_oracle(scheme)

        # Collision attack (applicable to hash functions)
        if 'SHA' in algorithm or 'MD5' in algorithm or 'HASH' in algorithm:
            attack_results['collision'] = self.simulate_collision_attack(scheme)

        # MITM attack (applicable to key exchange)
        if 'DH' in algorithm or 'ECDH' in algorithm or 'KEY_EXCHANGE' in scheme.get('type', ''):
            attack_results['mitm'] = self.simulate_mitm_attack(scheme)

        # Replay attack (applicable to authentication)
        if scheme.get('type') == 'authentication' or 'MAC' in algorithm:
            attack_results['replay'] = self.simulate_replay_attack(scheme)

        # Quantum attack (applicable to RSA, ECC, DH)
        if any(alg in algorithm for alg in ['RSA', 'ECC', 'DH', 'DSA']):
            attack_results['quantum'] = self.simulate_quantum_attack(scheme)

        # Determine weakest link
        weakest_link = self._find_weakest_link(attack_results)

        # Calculate time to compromise (fastest successful attack)
        time_to_compromise = self._calculate_time_to_compromise(attack_results)

        # Assess mitigation status
        mitigation_status = self._assess_mitigation_status(scheme, attack_results)

        # Calculate overall security score
        security_score = self._calculate_security_score(attack_results)

        return {
            'attack_results': {k: self._result_to_dict(v) for k, v in attack_results.items()},
            'weakest_link': weakest_link,
            'time_to_compromise': time_to_compromise,
            'mitigation_status': mitigation_status,
            'overall_security_score': security_score,
            'recommendations': self._generate_recommendations(attack_results, scheme)
        }

    def simulate_brute_force(self, key_size: int) -> AttackResult:
        """
        Simulate brute force attack

        Args:
            key_size: Key size in bits

        Returns:
            AttackResult with brute force analysis
        """
        # Total possible keys
        total_keys = 2 ** key_size

        # Average case: need to try half the keyspace
        avg_operations = total_keys / 2

        # Calculate time with different computing resources
        time_pc = avg_operations / self.STANDARD_PC_OPS
        time_cluster = avg_operations / self.CLUSTER_OPS
        time_super = avg_operations / self.SUPERCOMPUTER_OPS

        # Determine feasibility
        if time_super > 100 * self.YEAR:
            feasibility = "infeasible"
            success_prob = 0.0
            time_str = f"{self._format_time(time_super)} (supercomputer)"
        elif time_cluster > 10 * self.YEAR:
            feasibility = "theoretical"
            success_prob = 0.1
            time_str = f"{self._format_time(time_cluster)} (cluster)"
        elif time_pc < 1 * self.YEAR:
            feasibility = "practical"
            success_prob = 0.9
            time_str = f"{self._format_time(time_pc)} (standard PC)"
        else:
            feasibility = "theoretical"
            success_prob = 0.3
            time_str = f"{self._format_time(time_pc)} (standard PC)"

        # Mitigation effectiveness (key size dependent)
        mitigation = min(1.0, (key_size - 56) / 200.0) if key_size > 56 else 0.0

        details = (f"Keyspace: 2^{key_size} = {total_keys:.2e} keys. "
                  f"Average operations: {avg_operations:.2e}. "
                  f"Strong keys (>=128 bits) make brute force infeasible.")

        return AttackResult(
            attack_type=AttackType.BRUTE_FORCE,
            success_probability=success_prob,
            time_to_break=time_str,
            computational_cost=f"{avg_operations:.2e} operations",
            feasibility=feasibility,
            mitigation_effectiveness=mitigation,
            details=details
        )

    def simulate_timing_attack(self, scheme: Dict) -> AttackResult:
        """
        Simulate timing attack

        Args:
            scheme: Encryption scheme configuration

        Returns:
            AttackResult with timing attack analysis
        """
        algorithm = scheme.get('algorithm', '').upper()
        has_constant_time = scheme.get('constant_time_impl', False)

        # Timing attacks are more effective against certain algorithms
        vulnerable_algos = ['RSA', 'DSA', 'ECDSA']
        is_vulnerable_algo = any(alg in algorithm for alg in vulnerable_algos)

        if has_constant_time:
            success_prob = 0.05
            feasibility = "infeasible"
            time_to_break = "N/A (constant-time implementation)"
            mitigation = 0.95
            details = "Constant-time implementation prevents timing attacks."
        elif is_vulnerable_algo:
            success_prob = 0.7
            feasibility = "practical"
            time_to_break = "Hours to days (with precise timing measurements)"
            mitigation = 0.2
            details = (f"{algorithm} vulnerable to timing attacks. "
                      "Side-channel leakage can reveal key bits through execution time.")
        else:
            success_prob = 0.3
            feasibility = "theoretical"
            time_to_break = "Days to weeks (requires many samples)"
            mitigation = 0.5
            details = "Moderate vulnerability. Timing variations may leak information."

        return AttackResult(
            attack_type=AttackType.TIMING_ATTACK,
            success_probability=success_prob,
            time_to_break=time_to_break,
            computational_cost="Low (statistical analysis)",
            feasibility=feasibility,
            mitigation_effectiveness=mitigation,
            details=details
        )

    def simulate_padding_oracle(self, scheme: Dict) -> AttackResult:
        """
        Simulate padding oracle attack

        Args:
            scheme: Encryption scheme configuration

        Returns:
            AttackResult with padding oracle attack analysis
        """
        mode = scheme.get('mode', '').upper()
        has_mac = scheme.get('authenticated', False) or 'GCM' in mode or 'CCM' in mode

        if has_mac:
            success_prob = 0.01
            feasibility = "infeasible"
            time_to_break = "N/A (authenticated encryption)"
            mitigation = 0.99
            details = "Authenticated encryption prevents padding oracle attacks."
        elif 'CBC' in mode:
            success_prob = 0.8
            feasibility = "practical"
            time_to_break = "Minutes to hours (128 * block_count queries)"
            mitigation = 0.1
            details = ("CBC mode without authentication is vulnerable. "
                      "Attacker can decrypt ciphertext by observing padding errors.")
        else:
            success_prob = 0.1
            feasibility = "theoretical"
            time_to_break = "Varies by implementation"
            mitigation = 0.7
            details = "Limited vulnerability depending on error handling."

        return AttackResult(
            attack_type=AttackType.PADDING_ORACLE,
            success_probability=success_prob,
            time_to_break=time_to_break,
            computational_cost="Low (adaptive chosen-ciphertext)",
            feasibility=feasibility,
            mitigation_effectiveness=mitigation,
            details=details
        )

    def simulate_collision_attack(self, scheme: Dict) -> AttackResult:
        """
        Simulate collision attack on hash functions

        Args:
            scheme: Hash function configuration

        Returns:
            AttackResult with collision attack analysis
        """
        algorithm = scheme.get('algorithm', '').upper()
        output_size = scheme.get('output_size', 256)

        # Birthday paradox: collisions in ~2^(n/2) operations
        collision_complexity = 2 ** (output_size / 2)

        time_to_collide = collision_complexity / self.CLUSTER_OPS

        if 'MD5' in algorithm:
            success_prob = 1.0
            feasibility = "practical"
            time_to_break = "Seconds (known attacks)"
            mitigation = 0.0
            details = "MD5 is broken. Practical collision attacks exist."
        elif 'SHA1' in algorithm or 'SHA-1' in algorithm:
            success_prob = 0.9
            feasibility = "practical"
            time_to_break = "Days (with substantial resources)"
            mitigation = 0.1
            details = "SHA-1 is deprecated. Practical collision attacks demonstrated."
        elif output_size < 224:
            success_prob = 0.5
            feasibility = "theoretical"
            time_to_break = self._format_time(time_to_collide)
            mitigation = 0.4
            details = f"Birthday attack complexity: 2^{output_size/2} = {collision_complexity:.2e}"
        else:
            success_prob = 0.01
            feasibility = "infeasible"
            time_to_break = self._format_time(time_to_collide)
            mitigation = 0.95
            details = f"Strong hash function. Collision resistance: 2^{output_size/2} operations."

        return AttackResult(
            attack_type=AttackType.COLLISION,
            success_probability=success_prob,
            time_to_break=time_to_break,
            computational_cost=f"{collision_complexity:.2e} hash operations",
            feasibility=feasibility,
            mitigation_effectiveness=mitigation,
            details=details
        )

    def simulate_mitm_attack(self, scheme: Dict) -> AttackResult:
        """
        Simulate man-in-the-middle attack

        Args:
            scheme: Key exchange scheme configuration

        Returns:
            AttackResult with MITM attack analysis
        """
        has_authentication = scheme.get('authenticated', False)
        has_certificates = scheme.get('use_certificates', False)

        if has_certificates or has_authentication:
            success_prob = 0.05
            feasibility = "infeasible"
            time_to_break = "N/A (authenticated key exchange)"
            mitigation = 0.95
            details = "Certificate-based authentication prevents MITM attacks."
        else:
            success_prob = 0.95
            feasibility = "practical"
            time_to_break = "Real-time (during key exchange)"
            mitigation = 0.0
            details = ("Unauthenticated key exchange vulnerable to MITM. "
                      "Attacker can intercept and relay messages.")

        return AttackResult(
            attack_type=AttackType.MITM,
            success_probability=success_prob,
            time_to_break=time_to_break,
            computational_cost="Minimal (passive interception)",
            feasibility=feasibility,
            mitigation_effectiveness=mitigation,
            details=details
        )

    def simulate_replay_attack(self, scheme: Dict) -> AttackResult:
        """
        Simulate replay attack

        Args:
            scheme: Authentication scheme configuration

        Returns:
            AttackResult with replay attack analysis
        """
        has_nonce = scheme.get('use_nonce', False)
        has_timestamp = scheme.get('use_timestamp', False)
        has_sequence = scheme.get('use_sequence', False)

        replay_protection = has_nonce or has_timestamp or has_sequence

        if replay_protection:
            success_prob = 0.1
            feasibility = "theoretical"
            time_to_break = "Limited window (nonce/timestamp protection)"
            mitigation = 0.9
            details = "Nonce/timestamp/sequence protection prevents replay attacks."
        else:
            success_prob = 0.99
            feasibility = "practical"
            time_to_break = "Immediate (capture and replay)"
            mitigation = 0.0
            details = ("No replay protection. Attacker can capture and replay "
                      "authentication messages indefinitely.")

        return AttackResult(
            attack_type=AttackType.REPLAY,
            success_probability=success_prob,
            time_to_break=time_to_break,
            computational_cost="Minimal (message capture)",
            feasibility=feasibility,
            mitigation_effectiveness=mitigation,
            details=details
        )

    def simulate_quantum_attack(self, scheme: Dict) -> AttackResult:
        """
        Simulate quantum attack (Shor's/Grover's algorithms)

        Args:
            scheme: Cryptographic scheme configuration

        Returns:
            AttackResult with quantum attack analysis
        """
        algorithm = scheme.get('algorithm', '').upper()
        key_size = scheme.get('key_size', 128)

        # Shor's algorithm (breaks RSA, DH, ECC in polynomial time)
        if any(alg in algorithm for alg in ['RSA', 'DH', 'DSA', 'ECDSA', 'ECDH', 'ECC']):
            # Polynomial time for Shor's algorithm
            quantum_ops = key_size ** 3
            success_prob = 0.95
            feasibility = "theoretical"
            time_to_break = "Hours to days (on large quantum computer)"
            mitigation = 0.0
            details = (f"Shor's algorithm breaks {algorithm} in polynomial time. "
                      f"Requires fault-tolerant quantum computer with ~{key_size*2} qubits.")

        # Grover's algorithm (symmetric crypto - square root speedup)
        else:
            # Grover's provides quadratic speedup: 2^(n/2) instead of 2^n
            grover_ops = 2 ** (key_size / 2)

            if key_size >= 256:
                success_prob = 0.01
                feasibility = "infeasible"
                mitigation = 0.95
                details = f"256+ bit keys resist Grover's algorithm. Effective security: {key_size/2} bits."
            elif key_size >= 128:
                success_prob = 0.3
                feasibility = "theoretical"
                mitigation = 0.7
                details = f"Grover's reduces effective security to {key_size/2} bits. Still secure."
            else:
                success_prob = 0.7
                feasibility = "theoretical"
                mitigation = 0.2
                details = f"Weak against Grover's. Effective security: {key_size/2} bits."

            time_to_break = f"{grover_ops:.2e} quantum operations"

        return AttackResult(
            attack_type=AttackType.QUANTUM,
            success_probability=success_prob,
            time_to_break=time_to_break,
            computational_cost=f"Polynomial/quadratic on quantum computer",
            feasibility=feasibility,
            mitigation_effectiveness=mitigation,
            details=details
        )

    def calculate_time_to_break(self,
                               key_size: int,
                               attack_type: AttackType) -> str:
        """
        Calculate time to break with given attack type

        Args:
            key_size: Key size in bits
            attack_type: Type of attack to simulate

        Returns:
            Human-readable time estimate
        """
        if attack_type == AttackType.BRUTE_FORCE:
            result = self.simulate_brute_force(key_size)
            return result.time_to_break
        elif attack_type == AttackType.QUANTUM:
            scheme = {'algorithm': 'AES', 'key_size': key_size}
            result = self.simulate_quantum_attack(scheme)
            return result.time_to_break
        else:
            return "Attack type specific - use simulate_attacks() for full analysis"

    def _format_time(self, seconds: float) -> str:
        """Format time in human-readable format"""
        if seconds < self.MINUTE:
            return f"{seconds:.2f} seconds"
        elif seconds < self.HOUR:
            return f"{seconds/self.MINUTE:.2f} minutes"
        elif seconds < self.DAY:
            return f"{seconds/self.HOUR:.2f} hours"
        elif seconds < self.YEAR:
            return f"{seconds/self.DAY:.2f} days"
        else:
            years = seconds / self.YEAR
            if years > 1e9:
                return f"{years:.2e} years"
            else:
                return f"{years:.2f} years"

    def _find_weakest_link(self, attack_results: Dict[str, AttackResult]) -> Dict[str, Any]:
        """Find the most vulnerable attack vector"""
        if not attack_results:
            return {'attack': 'none', 'score': 1.0}

        # Find attack with highest success probability and practical feasibility
        weakest = min(
            attack_results.items(),
            key=lambda x: (
                0 if x[1].feasibility == 'practical' else 1,
                -x[1].success_probability
            )
        )

        return {
            'attack': weakest[0],
            'type': weakest[1].attack_type.value,
            'success_probability': weakest[1].success_probability,
            'feasibility': weakest[1].feasibility,
            'time_to_break': weakest[1].time_to_break
        }

    def _calculate_time_to_compromise(self, attack_results: Dict[str, AttackResult]) -> str:
        """Calculate fastest time to compromise"""
        practical_attacks = [
            r for r in attack_results.values()
            if r.feasibility == 'practical'
        ]

        if not practical_attacks:
            return "No practical attacks identified"

        # Return the fastest practical attack
        fastest = min(practical_attacks, key=lambda x: x.success_probability, reverse=True)
        return fastest.time_to_break

    def _assess_mitigation_status(self,
                                  scheme: Dict[str, Any],
                                  attack_results: Dict[str, AttackResult]) -> Dict[str, Any]:
        """Assess current mitigation status"""
        if not attack_results:
            return {'status': 'unknown', 'coverage': 0.0}

        total_mitigation = sum(r.mitigation_effectiveness for r in attack_results.values())
        avg_mitigation = total_mitigation / len(attack_results)

        # Check for specific protections
        protections = []
        if scheme.get('authenticated'):
            protections.append('authenticated_encryption')
        if scheme.get('constant_time_impl'):
            protections.append('constant_time_implementation')
        if scheme.get('use_nonce'):
            protections.append('replay_protection')
        if scheme.get('use_certificates'):
            protections.append('certificate_authentication')

        if avg_mitigation > 0.8:
            status = 'strong'
        elif avg_mitigation > 0.5:
            status = 'moderate'
        else:
            status = 'weak'

        return {
            'status': status,
            'coverage': avg_mitigation,
            'active_protections': protections,
            'unmitigated_attacks': [
                k for k, v in attack_results.items()
                if v.mitigation_effectiveness < 0.5
            ]
        }

    def _calculate_security_score(self, attack_results: Dict[str, AttackResult]) -> float:
        """Calculate overall security score (0.0 to 1.0)"""
        if not attack_results:
            return 0.5

        # Weight factors
        weights = {
            'mitigation': 0.4,
            'feasibility': 0.4,
            'success_probability': 0.2
        }

        # Calculate component scores
        avg_mitigation = sum(r.mitigation_effectiveness for r in attack_results.values()) / len(attack_results)

        # Penalize practical attacks
        feasibility_score = sum(
            1.0 if r.feasibility == 'infeasible' else
            0.5 if r.feasibility == 'theoretical' else 0.0
            for r in attack_results.values()
        ) / len(attack_results)

        # Inverse of success probability
        success_score = 1.0 - (sum(r.success_probability for r in attack_results.values()) / len(attack_results))

        overall_score = (
            weights['mitigation'] * avg_mitigation +
            weights['feasibility'] * feasibility_score +
            weights['success_probability'] * success_score
        )

        return round(overall_score, 3)

    def _generate_recommendations(self,
                                 attack_results: Dict[str, AttackResult],
                                 scheme: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on attack results"""
        recommendations = []

        for attack_name, result in attack_results.items():
            if result.success_probability > 0.5 and result.feasibility == 'practical':
                if result.attack_type == AttackType.BRUTE_FORCE:
                    recommendations.append(
                        f"Increase key size to at least 128 bits to prevent brute force attacks"
                    )
                elif result.attack_type == AttackType.TIMING_ATTACK:
                    recommendations.append(
                        "Implement constant-time operations to prevent timing attacks"
                    )
                elif result.attack_type == AttackType.PADDING_ORACLE:
                    recommendations.append(
                        "Use authenticated encryption (GCM, CCM) to prevent padding oracle attacks"
                    )
                elif result.attack_type == AttackType.MITM:
                    recommendations.append(
                        "Implement certificate-based authentication for key exchange"
                    )
                elif result.attack_type == AttackType.REPLAY:
                    recommendations.append(
                        "Add nonce or timestamp to prevent replay attacks"
                    )
                elif result.attack_type == AttackType.COLLISION:
                    recommendations.append(
                        "Upgrade to SHA-256 or SHA-3 for collision resistance"
                    )
                elif result.attack_type == AttackType.QUANTUM:
                    recommendations.append(
                        "Consider post-quantum cryptography for long-term security"
                    )

        if not recommendations:
            recommendations.append("Security configuration appears robust against common attacks")

        return recommendations

    def _result_to_dict(self, result: AttackResult) -> Dict[str, Any]:
        """Convert AttackResult to dictionary"""
        return {
            'attack_type': result.attack_type.value,
            'success_probability': result.success_probability,
            'time_to_break': result.time_to_break,
            'computational_cost': result.computational_cost,
            'feasibility': result.feasibility,
            'mitigation_effectiveness': result.mitigation_effectiveness,
            'details': result.details
        }
