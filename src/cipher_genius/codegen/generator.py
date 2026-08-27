"""Code generator for cryptographic schemes"""

from typing import Optional

from cipher_genius.models.scheme import CryptographicScheme, Implementation
from cipher_genius.core.llm_interface import get_llm_interface
from cipher_genius.core.safety_notice import has_meaningful_artifact, with_disclaimer


class CodeGenerator:
    """Generate code implementations for cryptographic schemes"""

    def __init__(self, llm_provider: Optional[str] = None):
        self.llm = get_llm_interface(llm_provider)

    def generate_all(self, scheme: CryptographicScheme) -> Implementation:
        """Generate all code implementations"""

        implementation = Implementation(
            pseudocode=self.generate_pseudocode(scheme),
            python=self.generate_python(scheme),
            c=self.generate_c(scheme),
        )

        return implementation

    def generate_pseudocode(self, scheme: CryptographicScheme) -> str:
        """Generate pseudocode for the scheme"""

        system_prompt = """You are a cryptography expert writing clear, educational pseudocode."""

        component_desc = "\n".join([
            f"- {comp.name}: {comp.description or comp.category}"
            for comp in scheme.architecture.components
        ])

        user_prompt = f"""Generate pseudocode for this cryptographic scheme:

Scheme: {scheme.metadata.name}
Type: {scheme.metadata.scheme_type}

Components:
{component_desc}

Architecture:
Pattern: {scheme.architecture.composition.get('pattern', 'standard')}
Dataflow: {', '.join(scheme.architecture.dataflow)}

Parameters:
{self._format_parameters(scheme)}

Write clear, step-by-step pseudocode for:
1. Encryption/signing function
2. Decryption/verification function

Use standard cryptographic notation. Include comments explaining each step."""

        try:
            pseudocode = self.llm.generate(user_prompt, system_prompt, temperature=0.3)
            if not has_meaningful_artifact(pseudocode, "pseudocode"):
                raise ValueError("LLM did not return implementation-shaped pseudocode")
            return with_disclaimer(pseudocode, "pseudocode")
        except Exception as e:
            print(f"Error generating pseudocode: {e}")
            return with_disclaimer(self._fallback_pseudocode(scheme), "pseudocode")

    def generate_python(self, scheme: CryptographicScheme) -> str:
        """Generate Python implementation"""

        system_prompt = """You are an expert Python developer specializing in cryptography.
Write production-quality, well-documented Python code using the cryptography library."""

        spec = scheme.get_specification()

        user_prompt = f"""Generate Python implementation for this scheme:

{spec}

Requirements:
- Use the 'cryptography' library (from cryptography.hazmat.primitives...)
- Include comprehensive docstrings
- Add type hints
- Include error handling
- Follow PEP 8 style
- Add usage example in main block

Generate complete, runnable code."""

        try:
            code = self.llm.generate(user_prompt, system_prompt, temperature=0.2, max_tokens=2000)
            code = self._clean_code(code)
            if not has_meaningful_artifact(code, "python"):
                raise ValueError("LLM did not return implementation-shaped Python code")
            return with_disclaimer(code, "python")
        except Exception as e:
            print(f"Error generating Python code: {e}")
            return with_disclaimer(self._fallback_python(scheme), "python")

    def generate_c(self, scheme: CryptographicScheme) -> str:
        """Generate C implementation"""

        system_prompt = """You are an expert C programmer specializing in cryptographic implementations.
Write secure, efficient C code."""

        spec = scheme.get_specification()

        user_prompt = f"""Generate C implementation for this scheme:

{spec}

Requirements:
- Use standard C (C11)
- Include necessary headers
- Add comprehensive comments
- Include error handling
- Use secure coding practices
- Add example usage in main()

Generate complete, compilable code."""

        try:
            code = self.llm.generate(user_prompt, system_prompt, temperature=0.2, max_tokens=2000)
            code = self._clean_code(code)
            if not has_meaningful_artifact(code, "c"):
                raise ValueError("LLM did not return implementation-shaped C code")
            return with_disclaimer(code, "c")
        except Exception as e:
            print(f"Error generating C code: {e}")
            return with_disclaimer(self._fallback_c(scheme), "c")

    def _format_parameters(self, scheme: CryptographicScheme) -> str:
        """Format parameters for display"""
        params = []
        if scheme.parameters.key_size:
            params.append(f"Key Size: {scheme.parameters.key_size} bits")
        if scheme.parameters.block_size:
            params.append(f"Block Size: {scheme.parameters.block_size} bits")
        if scheme.parameters.nonce_size:
            params.append(f"Nonce Size: {scheme.parameters.nonce_size} bits")
        if scheme.parameters.tag_size:
            params.append(f"Tag Size: {scheme.parameters.tag_size} bits")

        return "\n".join(params) if params else "Standard parameters"

    def _clean_code(self, code: str) -> str:
        """Clean generated code"""
        # Remove markdown code blocks if present
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```c" in code:
            code = code.split("```c")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]

        return code.strip()

    def _fallback_pseudocode(self, scheme: CryptographicScheme) -> str:
        """Fallback pseudocode generation"""

        components = ", ".join([c.name for c in scheme.architecture.components])

        pseudocode = f"""
# {scheme.metadata.name} - Pseudocode

## Encryption/Signing
function encrypt(key, message):
    // Initialize {components}
    state = initialize(key)

    // Process message
    ciphertext = process(state, message)

    // Return result
    return ciphertext

## Decryption/Verification
function decrypt(key, ciphertext):
    // Initialize {components}
    state = initialize(key)

    // Process ciphertext
    plaintext = process_inverse(state, ciphertext)

    // Return result
    return plaintext

## Notes
- Replace with specific operations for {components}
- Add proper error handling
- Ensure secure parameter handling
"""
        return pseudocode.strip()

    def _fallback_python(self, scheme: CryptographicScheme) -> str:
        """Fallback Python code generation"""

        components = scheme.get_component_names()

        code = f'''"""
{scheme.metadata.name}
Auto-generated cryptographic scheme implementation
"""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class {scheme.metadata.name.replace("-", "").replace(" ", "")}:
    """
    Implementation of {scheme.metadata.name}

    Components: {", ".join(components)}
    Security Level: {scheme.requirements.security.security_level}-bit
    """

    def __init__(self, key: bytes):
        """
        Initialize the scheme

        Args:
            key: Encryption key ({scheme.parameters.key_size or 256} bits)
        """
        if len(key) != {(scheme.parameters.key_size or 256) // 8}:
            raise ValueError("Invalid key size")

        self.key = key
        # TODO: Initialize components

    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt plaintext

        Args:
            plaintext: Data to encrypt

        Returns:
            Ciphertext
        """
        # TODO: Implement using {components[0] if components else "cipher"}
        raise NotImplementedError("Implementation pending")

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypt ciphertext

        Args:
            ciphertext: Data to decrypt

        Returns:
            Plaintext
        """
        # TODO: Implement using {components[0] if components else "cipher"}
        raise NotImplementedError("Implementation pending")


if __name__ == "__main__":
    # Example usage
    key = b"\\x00" * {(scheme.parameters.key_size or 256) // 8}
    cipher = {scheme.metadata.name.replace("-", "").replace(" ", "")}(key)

    message = b"Hello, World!"
    print(f"Original: {{message}}")

    # ciphertext = cipher.encrypt(message)
    # plaintext = cipher.decrypt(ciphertext)
    # print(f"Decrypted: {{plaintext}}")
'''
        return code

    def _fallback_c(self, scheme: CryptographicScheme) -> str:
        """Fallback C code generation"""

        components = ", ".join(scheme.get_component_names())

        code = f'''/*
 * {scheme.metadata.name}
 * Auto-generated cryptographic scheme implementation
 *
 * Components: {components}
 * Security Level: {scheme.requirements.security.security_level}-bit
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

#define KEY_SIZE {(scheme.parameters.key_size or 256) // 8}
#define BLOCK_SIZE {(scheme.parameters.block_size or 128) // 8}

/* Encryption function */
int encrypt(const uint8_t *key, const uint8_t *plaintext, size_t len,
            uint8_t *ciphertext) {{
    /* TODO: Implement encryption using {components} */
    memcpy(ciphertext, plaintext, len);
    return 0;
}}

/* Decryption function */
int decrypt(const uint8_t *key, const uint8_t *ciphertext, size_t len,
            uint8_t *plaintext) {{
    /* TODO: Implement decryption using {components} */
    memcpy(plaintext, ciphertext, len);
    return 0;
}}

/* Example usage */
int main() {{
    uint8_t key[KEY_SIZE] = {{0}};
    uint8_t plaintext[] = "Hello, World!";
    uint8_t ciphertext[sizeof(plaintext)];
    uint8_t decrypted[sizeof(plaintext)];

    printf("Original: %s\\n", plaintext);

    encrypt(key, plaintext, sizeof(plaintext), ciphertext);
    decrypt(key, ciphertext, sizeof(plaintext), decrypted);

    printf("Decrypted: %s\\n", decrypted);

    return 0;
}}
'''
        return code
