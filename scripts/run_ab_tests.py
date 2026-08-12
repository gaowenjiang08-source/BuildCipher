#!/usr/bin/env python
"""Run A/B tests comparing legacy and LangGraph MAS engines."""

from cipher_genius.testing.ab_tester import MASEngineABTester

# Test requirements covering different cryptographic scenarios
TEST_REQUIREMENTS = [
    "Design a secure digital signature scheme for approved BIM/IFC package delivery",
    "Implement AES-GCM authenticated encryption for IoT device communication with 128-bit security",
    "Create HMAC-SHA256 message authentication for REST API request signing",
    "Design RSA-PSS signature scheme for software code signing with 2048-bit keys",
    "Implement ChaCha20-Poly1305 AEAD for secure messaging application",
    "Design ECDSA signature using P-256 curve for blockchain transactions",
    "Create bcrypt password hashing scheme for user authentication system",
    "Implement X25519 key exchange for end-to-end encrypted chat",
]


def main():
    """Run A/B tests."""
    print("=" * 80)
    print("MAS Engine A/B Testing")
    print("=" * 80)
    print("\nThis will compare legacy MAS engine vs LangGraph MAS engine")
    print(f"Testing {len(TEST_REQUIREMENTS)} requirements...\n")

    tester = MASEngineABTester(llm_provider="openai")
    results = tester.run_batch_tests(TEST_REQUIREMENTS)

    # Save results to file
    import json
    from datetime import datetime

    output_file = f"ab_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    results_data = []
    for result in results:
        results_data.append({
            "requirement": result.requirement,
            "timestamp": result.timestamp,
            "winner": result.winner,
            "speedup_factor": result.speedup_factor,
            "legacy": {
                "success": result.legacy_metrics.success,
                "execution_time": result.legacy_metrics.execution_time,
                "num_candidates": result.legacy_metrics.num_candidates,
                "has_audit": result.legacy_metrics.has_audit,
                "has_code": result.legacy_metrics.has_code,
                "error": result.legacy_metrics.error_message,
            },
            "langgraph": {
                "success": result.langgraph_metrics.success,
                "execution_time": result.langgraph_metrics.execution_time,
                "num_candidates": result.langgraph_metrics.num_candidates,
                "has_audit": result.langgraph_metrics.has_audit,
                "has_code": result.langgraph_metrics.has_code,
                "error": result.langgraph_metrics.error_message,
            },
        })

    with open(output_file, "w") as f:
        json.dump(results_data, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
