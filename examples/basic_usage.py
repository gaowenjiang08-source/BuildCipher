"""
Basic usage example for BuildTrust
"""
# -*- coding: utf-8 -*-

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from cipher_genius.core.parser import RequirementParser
from cipher_genius.core.generator import SchemeGenerator
from cipher_genius.codegen.generator import CodeGenerator


def main():
    """Basic usage demonstration"""

    # Step 1: Parse natural language requirements
    print("=" * 60)
    print("BuildTrust - Basic Usage Example")
    print("=" * 60)

    requirement_text = (
        "Generate a lightweight authenticated encryption scheme for "
        "IoT devices with 128-bit security, memory under 2KB, and "
        "latency under 10ms"
    )

    print(f"\nRequirement: {requirement_text}\n")

    # Initialize parser
    parser = RequirementParser()

    # Parse requirements
    print("Parsing requirements...")
    parsed = parser.parse(requirement_text)

    print(f"\nParsed successfully! (Confidence: {parsed.confidence:.0%})")
    print("\nStructured Requirement:")
    print(parsed.requirement.get_summary())

    if parsed.ambiguities:
        print("\n⚠ Ambiguities:")
        for amb in parsed.ambiguities:
            print(f"  - {amb}")

    if parsed.assumptions:
        print("\nℹ Assumptions:")
        for assumption in parsed.assumptions:
            print(f"  - {assumption}")

    # Step 2: Generate scheme
    print("\n" + "=" * 60)
    print("Generating Schemes...")
    print("=" * 60)

    generator = SchemeGenerator()

    # Generate 2 variants
    schemes = generator.generate(parsed.requirement, num_variants=2)

    print(f"\nGenerated {len(schemes)} scheme(s)!\n")

    # Display schemes
    for i, scheme in enumerate(schemes, 1):
        print(f"\n{'=' * 60}")
        print(f"Scheme {i}: {scheme.metadata.name}")
        print(f"Score: {scheme.score}/10")
        print(f"{'=' * 60}")

        print("\n" + scheme.get_specification())

        print("\nDesign Rationale:")
        print(scheme.design_rationale)

    # Step 3: Generate code for top scheme
    print("\n" + "=" * 60)
    print("Generating Code Implementation...")
    print("=" * 60)

    top_scheme = schemes[0]
    codegen = CodeGenerator()

    print("\nGenerating Python implementation...")
    python_code = codegen.generate_python(top_scheme)

    print("\n--- Python Code ---")
    print(python_code)

    print("\n" + "=" * 60)
    print("✓ Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
