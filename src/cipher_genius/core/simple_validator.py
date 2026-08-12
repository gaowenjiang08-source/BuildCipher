"""Simple validation functions for scheme generation"""

from typing import List, Tuple
from cipher_genius.models.component import Component
from cipher_genius.models.requirement import SchemeType
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


def validate_components_compatible(components: List[Component]) -> Tuple[bool, List[str]]:
    """
    Validate that components are compatible with each other.

    Args:
        components: List of components to validate

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    if len(components) < 2:
        return True, []

    # Check pairwise compatibility
    for i, comp1 in enumerate(components):
        for comp2 in components[i+1:]:
            # Check if comp2 is in comp1's incompatible list
            if comp2.name in comp1.not_compatible_with:
                errors.append(
                    f"Components '{comp1.name}' and '{comp2.name}' are incompatible"
                )

            # Check if comp1 is in comp2's incompatible list
            if comp1.name in comp2.not_compatible_with:
                errors.append(
                    f"Components '{comp2.name}' and '{comp1.name}' are incompatible"
                )

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_security_level(components: List[Component], target_level: int) -> Tuple[bool, List[str]]:
    """
    Validate that all components meet the target security level.

    Args:
        components: List of components
        target_level: Target security level in bits

    Returns:
        Tuple of (is_valid, warnings)
    """
    warnings = []

    # Check if target level is reasonable
    if target_level < 128:
        warnings.append(
            f"Security level {target_level}-bit is below minimum recommended (128-bit)"
        )

    # Check if any component has lower security level
    for comp in components:
        if comp.security.security_level < target_level:
            warnings.append(
                f"Component '{comp.name}' has lower security level "
                f"({comp.security.security_level}-bit) than target ({target_level}-bit)"
            )

    return True, warnings  # Warnings don't make it invalid


def validate_scheme_type_components(scheme_type: str, components: List[Component]) -> Tuple[bool, List[str]]:
    """
    Validate that components match the scheme type.

    Args:
        scheme_type: Type of scheme
        components: List of components

    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []

    # Map scheme types to expected component categories
    type_requirements = {
        "authenticated_encryption": {
            "required": ["cipher"],
            "alternative": [
                ["mode"],  # Option 1: cipher + AEAD mode (e.g., AES-GCM)
                ["mac"]    # Option 2: cipher + MAC (e.g., ChaCha20-Poly1305)
            ]
        },
        "encryption": {
            "required": ["cipher"],
            "optional": ["mode"]
        },
        "signature": {
            "required": ["signature"],
            "optional": ["hash"]
        },
        "hash": {
            "required": ["hash"],
            "optional": []
        },
        "mac": {
            "required": ["mac"],
            "optional": []
        },
        "key_derivation": {
            "required": ["construction"],
            "optional": ["hash"]
        },
        "key_exchange": {
            "required": ["key_exchange", "protocol"],
            "optional": []
        }
    }

    # Get requirements for this scheme type
    reqs = type_requirements.get(scheme_type.lower())
    if not reqs:
        return True, []  # Unknown type, skip validation

    # Get component categories
    categories = [str(comp.category) for comp in components]

    # Check required categories
    for req_cat in reqs.get("required", []):
        if not any(req_cat in cat for cat in categories):
            errors.append(
                f"Scheme type '{scheme_type}' requires component of type '{req_cat}' but none found"
            )

    # Check alternative requirements (for AEAD: need either mode OR mac)
    if "alternative" in reqs:
        alternatives = reqs["alternative"]
        satisfied = False

        for alt_reqs in alternatives:
            # Check if this alternative is satisfied
            if all(any(req_cat in cat for cat in categories) for req_cat in alt_reqs):
                satisfied = True
                break

        if not satisfied:
            # Create error message listing alternatives
            alt_desc = " OR ".join(["+".join(alt) for alt in alternatives])
            errors.append(
                f"Scheme type '{scheme_type}' requires one of: {alt_desc}"
            )

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_aead_scheme(components: List[Component]) -> Tuple[bool, List[str]]:
    """
    Validate AEAD (Authenticated Encryption with Associated Data) scheme.

    AEAD can be constructed in two ways:
    1. Cipher + AEAD mode (e.g., AES-GCM)
    2. Cipher + MAC (e.g., ChaCha20-Poly1305)

    Args:
        components: List of components

    Returns:
        Tuple of (is_valid, warnings)
    """
    warnings = []

    # Find cipher, mode, and MAC
    cipher = None
    mode = None
    mac = None

    for comp in components:
        if "cipher" in str(comp.category):
            cipher = comp
        elif comp.category == "mode":
            mode = comp
        elif comp.category == "mac":
            mac = comp

    if not cipher:
        warnings.append("AEAD scheme missing cipher component")
        return False, warnings

    # Check if we have either mode OR mac (both are valid AEAD constructions)
    if not mode and not mac:
        warnings.append("AEAD scheme needs either an AEAD mode (e.g., GCM) or MAC (e.g., Poly1305)")
        return False, warnings

    # If we have a mode, check if it's an AEAD mode
    if mode:
        aead_modes = ["GCM", "CCM"]
        if mode.name in aead_modes:
            # AEAD mode provides authentication, no MAC needed
            if mac:
                warnings.append(
                    f"AEAD mode '{mode.name}' provides authentication, separate MAC not needed"
                )
            return True, warnings
        else:
            # Non-AEAD mode should have MAC
            if not mac:
                warnings.append(
                    f"Mode '{mode.name}' is not an AEAD mode, should include MAC for authentication"
                )

    # If we have cipher + MAC (no mode), check for known AEAD constructions
    if mac:
        # ChaCha20-Poly1305 is a valid AEAD construction
        if cipher.name == "ChaCha20" and mac.name == "Poly1305":
            return True, warnings

        # AES + HMAC is a valid encrypt-then-MAC construction
        if "AES" in cipher.name and "HMAC" in mac.name:
            return True, warnings

        # Generic cipher + MAC is acceptable
        return True, warnings

    return True, warnings


def validate_parameters(params: dict, scheme_type: str) -> Tuple[bool, List[str]]:
    """
    Validate scheme parameters.

    Args:
        params: Parameter dictionary
        scheme_type: Type of scheme

    Returns:
        Tuple of (is_valid, warnings)
    """
    warnings = []

    # Validate key sizes
    if "key_size" in params:
        key_size = params["key_size"]
        if isinstance(key_size, int):
            if key_size < 128:
                warnings.append(
                    f"Key size {key_size}-bit is below minimum recommended (128-bit)"
                )
            elif key_size > 4096:
                warnings.append(
                    f"Key size {key_size}-bit is unusually large"
                )

    # Validate nonce/IV sizes
    if "nonce_size" in params:
        nonce_size = params["nonce_size"]
        if isinstance(nonce_size, int):
            if nonce_size < 64:
                warnings.append(
                    f"Nonce size {nonce_size}-bit may be too small (recommend 96+ bits)"
                )

    # Validate tag sizes for AEAD
    if scheme_type == "authenticated_encryption":
        if "tag_size" in params:
            tag_size = params["tag_size"]
            if isinstance(tag_size, int):
                if tag_size < 64:
                    warnings.append(
                        f"Authentication tag size {tag_size}-bit is too small (recommend 128+ bits)"
                    )

    return True, warnings


def quick_validate(
    scheme_type: str,
    components: List[Component],
    security_level: int,
    parameters: dict = None
) -> Tuple[bool, List[str], List[str]]:
    """
    Quick validation of a scheme.

    Args:
        scheme_type: Type of scheme
        components: List of components
        security_level: Target security level
        parameters: Scheme parameters (optional)

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    # Validate components exist
    if not components or len(components) == 0:
        errors.append("Scheme has no components")
        return False, errors, warnings

    # Validate component compatibility
    is_valid, compat_errors = validate_components_compatible(components)
    errors.extend(compat_errors)

    # Validate scheme type matches components
    is_valid2, type_errors = validate_scheme_type_components(scheme_type, components)
    errors.extend(type_errors)

    # Validate security level
    _, sec_warnings = validate_security_level(components, security_level)
    warnings.extend(sec_warnings)

    # Validate AEAD if applicable
    if scheme_type == "authenticated_encryption":
        _, aead_warnings = validate_aead_scheme(components)
        warnings.extend(aead_warnings)

    # Validate parameters
    if parameters:
        _, param_warnings = validate_parameters(parameters, scheme_type)
        warnings.extend(param_warnings)

    is_valid = len(errors) == 0

    if is_valid:
        logger.info(f"✅ Scheme validation passed ({len(warnings)} warnings)")
    else:
        logger.error(f"❌ Scheme validation failed ({len(errors)} errors)")

    return is_valid, errors, warnings
