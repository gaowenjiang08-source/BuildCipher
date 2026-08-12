"""Cryptographic scheme validation engine"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from cipher_genius.models.component import Component
from cipher_genius.models.scheme import CryptographicScheme
from cipher_genius.models.requirement import SchemeType
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationSeverity(str, Enum):
    """Validation issue severity levels"""
    ERROR = "error"      # Critical - scheme is invalid
    WARNING = "warning"  # Important - scheme may have issues
    INFO = "info"        # Informational - suggestions for improvement


class ValidationIssue:
    """Represents a validation issue"""

    def __init__(
        self,
        severity: ValidationSeverity,
        category: str,
        message: str,
        component: Optional[str] = None
    ):
        self.severity = severity
        self.category = category
        self.message = message
        self.component = component

    def __repr__(self):
        comp_str = f" [{self.component}]" if self.component else ""
        return f"{self.severity.value.upper()}{comp_str}: {self.message}"


class SchemeValidator:
    """Validates cryptographic schemes for correctness and security"""

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate(self, scheme: CryptographicScheme) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate a cryptographic scheme.

        Args:
            scheme: The scheme to validate

        Returns:
            Tuple of (is_valid, issues)
            - is_valid: True if no errors (warnings/info are OK)
            - issues: List of validation issues found
        """
        self.issues = []

        logger.info(f"Validating scheme: {scheme.metadata.name}")

        # Run all validation checks
        self._validate_scheme_type(scheme)
        self._validate_components_exist(scheme)
        self._validate_component_compatibility(scheme)
        self._validate_security_level(scheme)
        self._validate_scheme_completeness(scheme)
        self._validate_parameters(scheme)

        # Check if there are any errors
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
        is_valid = not has_errors

        if is_valid:
            logger.info(f"✅ Scheme validation passed ({len(self.issues)} warnings/info)")
        else:
            error_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
            logger.error(f"❌ Scheme validation failed ({error_count} errors)")

        return is_valid, self.issues

    def _validate_scheme_type(self, scheme: CryptographicScheme):
        """Validate scheme type is appropriate"""
        if not scheme.scheme_type:
            self.issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "scheme_type",
                "Scheme type is missing"
            ))
            return

        # Validate scheme type matches components
        type_component_map = {
            SchemeType.SYMMETRIC_ENCRYPTION: ["cipher", "mode"],
            SchemeType.AUTHENTICATED_ENCRYPTION: ["cipher", "mode", "mac"],
            SchemeType.HASH: ["hash"],
            SchemeType.MAC: ["mac"],
            SchemeType.DIGITAL_SIGNATURE: ["signature", "hash"],
            SchemeType.KEY_EXCHANGE: ["key_exchange"],
            SchemeType.KEY_DERIVATION: ["kdf", "construction"],
        }

        expected_categories = type_component_map.get(scheme.scheme_type, [])
        if expected_categories:
            actual_categories = [comp.category for comp in scheme.components]

            # Check if at least one expected category is present
            has_expected = any(
                any(cat in str(actual_cat) for cat in expected_categories)
                for actual_cat in actual_categories
            )

            if not has_expected:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "scheme_type",
                    f"Scheme type '{scheme.scheme_type.value}' typically requires components "
                    f"of type {expected_categories}, but none found"
                ))

    def _validate_components_exist(self, scheme: CryptographicScheme):
        """Validate that scheme has components"""
        if not scheme.components or len(scheme.components) == 0:
            self.issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "components",
                "Scheme has no components"
            ))

    def _validate_component_compatibility(self, scheme: CryptographicScheme):
        """Validate that components are compatible with each other"""
        components = scheme.components

        if len(components) < 2:
            return  # Single component schemes don't need compatibility check

        # Check pairwise compatibility
        for i, comp1 in enumerate(components):
            for comp2 in components[i+1:]:
                # Check if comp2 is in comp1's incompatible list
                if comp2.name in comp1.not_compatible_with:
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        "compatibility",
                        f"Components '{comp1.name}' and '{comp2.name}' are incompatible",
                        comp1.name
                    ))

        # Check for AEAD-specific compatibility
        self._validate_aead_compatibility(scheme)

    def _validate_aead_compatibility(self, scheme: CryptographicScheme):
        """Validate AEAD scheme component compatibility"""
        if scheme.scheme_type != SchemeType.AUTHENTICATED_ENCRYPTION:
            return

        # Find cipher and mode
        cipher = None
        mode = None

        for comp in scheme.components:
            if "cipher" in str(comp.category):
                cipher = comp
            elif comp.category == "mode":
                mode = comp

        if not cipher or not mode:
            return

        # Check if mode is AEAD
        aead_modes = ["GCM", "CCM", "ChaCha20-Poly1305"]
        if mode.name in aead_modes:
            # AEAD mode should be compatible with the cipher
            if cipher.name not in mode.compatible_with and mode.name not in cipher.compatible_with:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "aead",
                    f"AEAD mode '{mode.name}' may not be compatible with cipher '{cipher.name}'",
                    mode.name
                ))

    def _validate_security_level(self, scheme: CryptographicScheme):
        """Validate security level is consistent across components"""
        if not scheme.security_level:
            self.issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "security",
                "Scheme security level not specified"
            ))
            return

        # Check if any component has lower security level
        for comp in scheme.components:
            if comp.security.security_level < scheme.security_level:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "security",
                    f"Component '{comp.name}' has lower security level ({comp.security.security_level}-bit) "
                    f"than scheme ({scheme.security_level}-bit)",
                    comp.name
                ))

        # Warn about weak security levels
        if scheme.security_level < 128:
            self.issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "security",
                f"Security level {scheme.security_level}-bit is below minimum recommended (128-bit)"
            ))
        elif scheme.security_level < 192:
            self.issues.append(ValidationIssue(
                ValidationSeverity.INFO,
                "security",
                f"Security level {scheme.security_level}-bit is adequate for most applications. "
                "Consider 256-bit for long-term security."
            ))

    def _validate_scheme_completeness(self, scheme: CryptographicScheme):
        """Validate that scheme has all necessary components for its type"""
        scheme_type = scheme.scheme_type
        components = scheme.components

        if scheme_type == SchemeType.AUTHENTICATED_ENCRYPTION:
            # Should have cipher + AEAD mode OR cipher + mode + MAC
            has_cipher = any("cipher" in str(c.category) for c in components)
            has_mode = any(c.category == "mode" for c in components)
            has_mac = any(c.category == "mac" for c in components)
            has_aead_mode = any(
                c.name in ["GCM", "CCM", "ChaCha20-Poly1305"]
                for c in components
            )

            if not has_cipher:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    "completeness",
                    "Authenticated encryption scheme missing cipher component"
                ))

            if not has_mode:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    "completeness",
                    "Authenticated encryption scheme missing mode component"
                ))

            if not has_aead_mode and not has_mac:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "completeness",
                    "Authenticated encryption scheme should use AEAD mode (GCM/CCM) or include MAC"
                ))

        elif scheme_type == SchemeType.DIGITAL_SIGNATURE:
            has_signature = any(c.category == "signature" for c in components)
            has_hash = any(c.category == "hash_function" for c in components)

            if not has_signature:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    "completeness",
                    "Digital signature scheme missing signature component"
                ))

            if not has_hash:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "completeness",
                    "Digital signature scheme typically requires hash function"
                ))

    def _validate_parameters(self, scheme: CryptographicScheme):
        """Validate scheme parameters are reasonable"""
        if not scheme.parameters:
            return

        params = scheme.parameters

        # Validate key sizes
        if "key_size" in params:
            key_size = params["key_size"]
            if isinstance(key_size, int):
                if key_size < 128:
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        "parameters",
                        f"Key size {key_size}-bit is below minimum recommended (128-bit)"
                    ))
                elif key_size > 4096:
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        "parameters",
                        f"Key size {key_size}-bit is unusually large"
                    ))

        # Validate nonce/IV sizes
        if "nonce_size" in params:
            nonce_size = params["nonce_size"]
            if isinstance(nonce_size, int):
                if nonce_size < 64:
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        "parameters",
                        f"Nonce size {nonce_size}-bit may be too small (recommend 96+ bits)"
                    ))

        # Validate tag sizes for AEAD
        if scheme.scheme_type == SchemeType.AUTHENTICATED_ENCRYPTION:
            if "tag_size" in params:
                tag_size = params["tag_size"]
                if isinstance(tag_size, int):
                    if tag_size < 64:
                        self.issues.append(ValidationIssue(
                            ValidationSeverity.WARNING,
                            "parameters",
                            f"Authentication tag size {tag_size}-bit may be too small (recommend 128+ bits)"
                        ))

    def _validate_use_case_alignment(self, scheme: CryptographicScheme):
        """Validate components are suitable for intended use case"""
        if not scheme.use_case:
            return

        use_case = scheme.use_case.lower()

        # Check if components support the use case
        for comp in scheme.components:
            if comp.use_cases:
                # Check if any component use case matches scheme use case
                matches = any(
                    use_case in uc.lower() or uc.lower() in use_case
                    for uc in comp.use_cases
                )

                if not matches:
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.INFO,
                        "use_case",
                        f"Component '{comp.name}' may not be optimal for use case '{scheme.use_case}'",
                        comp.name
                    ))

            # Check if use case is in not_recommended list
            if comp.not_recommended_for:
                not_recommended = any(
                    use_case in nr.lower() or nr.lower() in use_case
                    for nr in comp.not_recommended_for
                )

                if not_recommended:
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        "use_case",
                        f"Component '{comp.name}' is not recommended for use case '{scheme.use_case}'",
                        comp.name
                    ))


def validate_scheme(scheme: CryptographicScheme) -> Tuple[bool, List[ValidationIssue]]:
    """
    Convenience function to validate a scheme.

    Args:
        scheme: The scheme to validate

    Returns:
        Tuple of (is_valid, issues)
    """
    validator = SchemeValidator()
    return validator.validate(scheme)
