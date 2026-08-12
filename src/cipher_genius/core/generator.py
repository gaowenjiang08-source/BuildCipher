"""Scheme generator for creating cryptographic schemes"""

import json
import re
from typing import Dict, List, Optional
from datetime import datetime

from cipher_genius.models.requirement import Requirement
from cipher_genius.models.scheme import (
    CryptographicScheme,
    SchemeMetadata,
    SchemeArchitecture,
    SchemeParameters,
    SecurityAnalysis,
)
from cipher_genius.models.component import Component
from cipher_genius.core.llm_interface import get_llm_interface
from cipher_genius.knowledge.components import get_component_library
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class SchemeGenerator:
    """Generate cryptographic schemes based on requirements"""

    def __init__(self, llm_provider: Optional[str] = None):
        self.llm = get_llm_interface(llm_provider)
        self.component_lib = get_component_library()

    def generate(
        self,
        requirement: Requirement,
        num_variants: int = 1
    ) -> List[CryptographicScheme]:
        """Generate cryptographic schemes based on requirements"""

        schemes = []
        seen_fingerprints = set()
        max_extra_attempts = max(3, num_variants * 3)

        for i in range(num_variants):
            chosen_scheme = None
            for attempt in range(max_extra_attempts):
                # Spread search space when fallback/LLM outputs are repetitive.
                effective_variant = i + attempt * num_variants
                try:
                    candidate = self._generate_single_scheme(requirement, variant_index=effective_variant)
                except Exception as e:
                    logger.error(f"Error generating scheme variant {i+1} (attempt {attempt+1}): {e}")
                    continue

                fingerprint = self._scheme_fingerprint(candidate)
                if fingerprint in seen_fingerprints and attempt < max_extra_attempts - 1:
                    continue

                # Keep visible variant numbering stable (Variant 2/3/4...)
                candidate.metadata.name = self._generate_scheme_name(candidate.architecture.components, i)
                chosen_scheme = candidate
                seen_fingerprints.add(fingerprint)
                break

            if chosen_scheme is not None:
                schemes.append(chosen_scheme)

        # Sort by score
        schemes.sort(key=lambda s: s.score, reverse=True)

        return schemes

    def _scheme_fingerprint(self, scheme: CryptographicScheme) -> tuple:
        """Create a lightweight signature used to avoid duplicate variants."""
        names = tuple(comp.name for comp in scheme.architecture.components)
        pattern = str(scheme.architecture.composition.get("pattern", "standard"))
        return names, pattern

    def _generate_single_scheme(
        self,
        requirement: Requirement,
        variant_index: int = 0
    ) -> CryptographicScheme:
        """Generate a single cryptographic scheme"""

        # Step 1: Select components - pass variant_index to introduce variation
        selected_components = self._select_components(requirement, variant_index)

        # Step 2: Design scheme architecture with LLM
        architecture = self._design_architecture(requirement, selected_components)

        # Step 3: Determine parameters
        parameters = self._determine_parameters(requirement, selected_components)

        # Step 4: Security analysis
        security_analysis = self._analyze_security(requirement, selected_components, architecture)

        # Step 5: Generate design rationale
        rationale = self._generate_rationale(requirement, selected_components, architecture)

        # Step 6: Calculate score
        score = self._calculate_score(requirement, selected_components, security_analysis)

        # Create scheme metadata
        scheme_name = self._generate_scheme_name(selected_components, variant_index)
        metadata = SchemeMetadata(
            name=scheme_name,
            scheme_type=requirement.scheme_type,
            generated_at=datetime.now(),
        )

        # Create scheme
        scheme = CryptographicScheme(
            metadata=metadata,
            requirements=requirement,
            architecture=architecture,
            parameters=parameters,
            security_analysis=security_analysis,
            design_rationale=rationale,
            score=score,
        )

        return scheme

    def _select_components(self, requirement: Requirement, variant_index: int = 0) -> List[Component]:
        """Select appropriate components for the requirement"""

        # Search components meeting security requirements
        # For AEAD schemes, we need to be more flexible with MAC/mode components
        # since the overall security level is determined by the cipher, not the MAC
        primary_candidates = self.component_lib.search(
            min_security=requirement.security.security_level
        )

        logger.debug(f"Found {len(primary_candidates)} primary candidates meeting security level {requirement.security.security_level}")

        # For AEAD schemes, also include MAC/mode components with lower security levels
        # because MAC security (128-bit) is acceptable even with 256-bit ciphers
        if requirement.scheme_type == "authenticated_encryption":
            # Get all MAC and mode components (regardless of security level)
            all_components = self.component_lib.list_all()
            secondary_candidates = [
                c for c in all_components
                if c.category in ["mac", "mode"] and c not in primary_candidates
            ]

            # Combine primary and secondary candidates
            candidates = primary_candidates + secondary_candidates
            logger.debug(f"AEAD scheme: added {len(secondary_candidates)} MAC/mode components, total {len(candidates)} candidates")
        else:
            candidates = primary_candidates

        # Filter by use case - but be more flexible for specific scheme types
        platform_type = requirement.target_platform.type
        scheme_type = requirement.scheme_type

        # For specific scheme types, don't filter by platform use case
        # Instead, use all candidates that meet security requirements
        if scheme_type in ["mac", "signature", "hash", "key_derivation"]:
            suitable = candidates
            logger.debug(f"Scheme type '{scheme_type}' - using all {len(suitable)} security-qualified candidates")
        else:
            # For encryption/AEAD, apply platform-based use case filtering
            use_case_map = {
                "iot_device": "iot_encryption",
                "mobile": "mobile_encryption",
                "server": "general_purpose",
            }

            use_case = use_case_map.get(platform_type, "general_purpose")
            logger.debug(f"Platform {platform_type}, use_case filter: {use_case}")

            # If no specific use case found, use all candidates
            suitable = [c for c in candidates if use_case in c.use_cases] or candidates
            logger.debug(f"After use_case filter: {len(suitable)} suitable components")

        logger.debug(f"Suitable component names (showing first 20): {[c.name for c in suitable[:20]]}")

        if requirement.scheme_type == "authenticated_encryption":
            selected = self._select_authenticated_encryption_components(requirement, suitable, variant_index)
            if selected:
                logger.debug(
                    "Structured AEAD selection chose components: %s",
                    [component.name for component in selected],
                )
                return selected

        # Build a rotating candidate window so fallback mode can still diversify variants.
        window_size = min(20, len(suitable))
        if not suitable:
            component_slice = []
            start_idx = 0
            end_idx = 0
        elif len(suitable) <= window_size:
            shift = variant_index % len(suitable)
            rotated = suitable[shift:] + suitable[:shift]
            component_slice = rotated[:window_size]
            start_idx = shift
            end_idx = shift + window_size
        else:
            start_idx = (variant_index * 5) % len(suitable)
            end_idx = start_idx + window_size
            if end_idx <= len(suitable):
                component_slice = suitable[start_idx:end_idx]
            else:
                overflow = end_idx - len(suitable)
                component_slice = suitable[start_idx:] + suitable[:overflow]

        logger.debug(f"Variant {variant_index}: selecting from components {start_idx}-{end_idx} (total {len(component_slice)} components)")

        selected = self._llm_select_components(requirement, component_slice, variant_index)

        return self._refine_component_selection(requirement, selected, suitable, variant_index)

    def _llm_select_components(
        self,
        requirement: Requirement,
        candidates: List[Component],
        variant_index: int = 0
    ) -> List[Component]:
        """Use LLM to select best component combination"""

        # First, try to match components explicitly mentioned in requirements
        req_text_lower = requirement.description.lower()
        explicit_matches = []
        remaining_candidates = []

        for comp in candidates:
            # Check if component name is explicitly mentioned
            comp_name_variants = [
                comp.name.lower(),
                comp.name.lower().replace("-", " "),
                comp.name.lower().replace("_", " ")
            ]

            if any(variant in req_text_lower for variant in comp_name_variants):
                explicit_matches.append(comp)
                logger.debug(f"Explicit match found: {comp.name}")
            else:
                remaining_candidates.append(comp)

        # If we have explicit matches that make a complete scheme, use them
        if explicit_matches:
            if len(explicit_matches) >= 2 or requirement.scheme_type in ["hash", "key_exchange"]:
                logger.debug(f"Using {len(explicit_matches)} explicitly matched components")
                return explicit_matches

        # Otherwise, use LLM to select from all candidates
        variant_guidance = ""
        if variant_index > 0:
            variant_guidance = f"\n\nIMPORTANT: This is variant #{variant_index + 1}. Please select DIFFERENT components from what you would typically choose first to provide variety."

        system_prompt = f"""You are a cryptography expert selecting components for a secure scheme.
Given requirements and candidate components, select the optimal combination.

CRITICAL RULES:
1. If the requirement explicitly mentions component names (e.g., "HMAC", "SHA-256"), you MUST select those components
2. For MAC schemes: always select MAC component + hash function (e.g., HMAC + SHA-256)
3. For authenticated encryption: select cipher + AEAD mode OR cipher + MAC
4. For signatures: select signature algorithm + hash function
5. Match the scheme type exactly{variant_guidance}"""

        # Build component descriptions with enhanced info
        comp_desc = []
        for i, comp in enumerate(candidates):
            desc = f"{i}. **{comp.name}** (category: {comp.category})"
            desc += f"\n   Security: {comp.security.security_level}-bit"
            desc += f"\n   Performance: {comp.performance.software_speed}"
            desc += f"\n   Properties: {', '.join(comp.properties[:3])}"
            comp_desc.append(desc)

        # Determine recommended components for scheme type with examples
        recommendations = {
            "mac": "You MUST select: 1 MAC component (like HMAC) + 1 hash_function (like SHA-256)",
            "authenticated_encryption": "Select: 1 cipher + 1 AEAD mode (like GCM/CCM) OR 1 cipher + 1 MAC",
            "signature": "Select: 1 signature component + 1 hash_function",
            "encryption": "Select: 1 cipher (block_cipher or stream_cipher) + 1 mode",
            "key_derivation": "Select: 1 construction (HKDF/PBKDF2) + 1 hash_function",
            "key_exchange": "Select: 1 key_exchange component only",
            "hash": "Select: 1 hash_function only"
        }

        rec = recommendations.get(requirement.scheme_type, "Select appropriate components")

        # Add few-shot examples
        examples = """
EXAMPLES:
1. Requirement: "Message authentication with HMAC-SHA-256"
   Scheme type: mac
   Components available: HMAC (mac), SHA-256 (hash_function), AES (block_cipher)
   Correct selection: [HMAC, SHA-256] (indices of HMAC and SHA-256)

2. Requirement: "Authenticated encryption for IoT"
   Scheme type: authenticated_encryption
   Components: ChaCha20 (stream_cipher), Poly1305 (mac), AES (block_cipher)
   Correct selection: [ChaCha20, Poly1305] (cipher + MAC for AEAD)
"""

        user_prompt = f"""Requirements:
{requirement.get_summary()}

Scheme Type: {requirement.scheme_type}

Available Components:
{chr(10).join(comp_desc)}

{examples}

Task: {rec}

CRITICAL:
- Requirement text: "{requirement.description}"
- If component names are mentioned in the requirement, YOU MUST SELECT THEM
- Match scheme type exactly (current type: {requirement.scheme_type})
- For "mac" type, you need BOTH a MAC component AND a hash function

Respond with JSON:
{{
  "selected_indices": [0, 3],
  "rationale": "Selected HMAC (index 0) and SHA-256 (index 3) because they are explicitly mentioned in requirements and form a complete MAC scheme"
}}"""

        try:
            response = self.llm.generate_json(user_prompt, system_prompt, temperature=0.3)
            indices = response["selected_indices"]
            selected = [candidates[i] for i in indices if i < len(candidates)]

            logger.debug(f"LLM selected {len(selected)} components: {[c.name for c in selected]}")
            logger.debug(f"Rationale: {response.get('rationale', 'N/A')}")

            if not selected:
                logger.debug("No components selected by LLM, falling back to heuristic")
                selected = candidates[:2]
            elif len(selected) == 1 and requirement.scheme_type in ["authenticated_encryption", "encryption"]:
                # For AEAD, if LLM only selected one component, try to find compatible components
                logger.debug(f"LLM selected only 1 component for AEAD, attempting to find compatible components")
                compatible = self._find_compatible_components(selected[0], candidates)
                if compatible:
                    # Add the first compatible component
                    selected.append(compatible[0])
                    logger.debug(f"Added compatible component: {compatible[0].name}")

            return selected

        except Exception as e:
            logger.debug(f"LLM component selection failed: {e}")
            # Fallback: heuristic selection
            return self._heuristic_select_components(requirement, candidates, variant_index)

    def _find_compatible_components(
        self,
        base_component: Component,
        candidates: List[Component],
        target_category: Optional[str] = None
    ) -> List[Component]:
        """
        Find components compatible with the base component.

        Args:
            base_component: The component to find matches for
            candidates: Pool of candidate components
            target_category: Optional category filter

        Returns:
            List of compatible components, sorted by preference
        """
        compatible = []

        # Check compatibility field in component metadata
        if base_component.compatible_with:
            for candidate in candidates:
                # Skip if target_category specified and doesn't match
                if target_category and candidate.category != target_category:
                    continue

                # Check if candidate name is in base component's compatible_with list
                if candidate.name in base_component.compatible_with:
                    compatible.append(candidate)

        # Built-in compatibility rules for common patterns
        # ChaCha20 + Poly1305
        if base_component.name == "ChaCha20":
            poly = [c for c in candidates if c.name == "Poly1305"]
            if poly and poly[0] not in compatible:
                compatible.extend(poly)

        # AES + AEAD modes (GCM, CCM)
        elif base_component.name == "AES":
            aead_modes = [c for c in candidates
                         if c.category == "mode" and "authenticated_encryption" in c.properties
                         and c.name in ["GCM", "CCM"]]
            for mode in aead_modes:
                if mode not in compatible:
                    compatible.append(mode)

        # Stream ciphers generally need MAC for AEAD
        elif base_component.category == "stream_cipher":
            macs = [c for c in candidates if c.category == "mac"]
            for mac in macs:
                if mac.name in base_component.compatible_with and mac not in compatible:
                    compatible.append(mac)

        logger.debug(f"Compatible components for {base_component.name}: {[c.name for c in compatible]}")
        return compatible

    def _select_authenticated_encryption_components(
        self,
        requirement: Requirement,
        candidates: List[Component],
        variant_index: int = 0,
    ) -> List[Component]:
        """Prefer production-ready AEAD bundles for enterprise requirements."""

        bundles = self._build_authenticated_encryption_bundles(requirement, candidates)
        if not bundles:
            return []

        bundle = bundles[variant_index % len(bundles)]
        return [component.model_copy(deep=True) for component in bundle]

    def _build_authenticated_encryption_bundles(
        self,
        requirement: Requirement,
        candidates: List[Component],
    ) -> List[List[Component]]:
        """Construct curated AEAD bundles and rank them by scenario fit."""

        all_components = {component.name: component for component in self.component_lib.list_all()}
        all_components.update({component.name: component for component in candidates})
        profile = self._build_requirement_profile(requirement)
        ordered_specs: List[tuple[int, List[str]]] = []

        if self._mentions_any(requirement, ["gcm-siv", "nonce reuse", "misuse resistant", "重放", "随机数复用", "nonce 复用"]):
            ordered_specs.extend(
                [
                    (112, ["AES", "AES-GCM-SIV"]),
                    (108, ["AES", "GCM-SIV"]),
                ]
            )

        if self._mentions_any(requirement, ["chacha20", "poly1305"]):
            ordered_specs.append((110, ["ChaCha20-Poly1305"]))

        if self._mentions_any(requirement, ["ascon"]):
            ordered_specs.append((106, ["Ascon"]))

        if profile["regulated"] or profile["server_friendly"]:
            ordered_specs.extend(
                [
                    (104, ["AES", "GCM"]),
                    (99, ["AES", "AES-GCM-SIV"]),
                    (95, ["AES", "GCM-SIV"]),
                    (82, ["ChaCha20-Poly1305"]),
                ]
            )
        elif profile["lightweight"]:
            ordered_specs.extend(
                [
                    (104, ["ChaCha20-Poly1305"]),
                    (99, ["AES", "CCM"]),
                    (95, ["AES", "GCM"]),
                    (93, ["Ascon"]),
                ]
            )
        else:
            ordered_specs.extend(
                [
                    (102, ["AES", "GCM"]),
                    (97, ["ChaCha20-Poly1305"]),
                    (93, ["AES", "AES-GCM-SIV"]),
                    (88, ["AES", "CCM"]),
                ]
            )

        if profile["low_latency"]:
            ordered_specs.extend(
                [
                    (96, ["AES", "GCM"]),
                    (94, ["ChaCha20-Poly1305"]),
                ]
            )

        if requirement.security.security_level <= 128 and profile["lightweight"]:
            ordered_specs.append((97, ["Ascon"]))

        seen_names: set[tuple[str, ...]] = set()
        bundles: List[tuple[int, List[Component]]] = []
        for base_score, names in ordered_specs:
            bundle = self._resolve_bundle(names, all_components)
            if not bundle:
                continue

            key = tuple(component.name for component in bundle)
            if key in seen_names:
                continue
            seen_names.add(key)

            score = base_score + self._score_authenticated_encryption_bundle(requirement, bundle)
            bundles.append((score, bundle))

        if not bundles:
            return []

        bundles.sort(key=lambda item: item[0], reverse=True)
        return [bundle for _, bundle in bundles]

    def _resolve_bundle(
        self,
        names: List[str],
        available: Dict[str, Component],
    ) -> List[Component]:
        bundle: List[Component] = []
        for name in names:
            component = available.get(name)
            if component is None:
                return []
            bundle.append(component)
        return bundle

    def _build_requirement_profile(self, requirement: Requirement) -> Dict[str, bool]:
        raw = requirement.description.lower()
        features = " ".join(str(item).lower() for item in (requirement.additional_features or []))
        combined = f"{raw} {features}"
        latency = str(requirement.performance.max_latency or "").lower()
        resource_level = str(requirement.target_platform.resource_level)
        platform = str(requirement.target_platform.type)

        latency_match = re.search(r"(\d+(?:\.\d+)?)\s*ms", latency)
        latency_value = float(latency_match.group(1)) if latency_match else None
        low_latency = "low-latency" in latency or "低延迟" in combined or (latency_value is not None and latency_value <= 20)
        regulated = any(
            token in combined
            for token in [
                "pci",
                "gdpr",
                "fedramp",
                "payment",
                "finance",
                "支付",
                "金融",
                "iso 19650",
                "建筑",
                "施工",
                "工程验收",
            ]
        )
        lightweight = platform in {"iot_device", "embedded", "mobile"} or resource_level in {"lightweight", "ultra_lightweight"}
        server_friendly = platform in {"server", "cloud", "desktop", "web"} and not lightweight

        return {
            "regulated": regulated,
            "low_latency": low_latency,
            "lightweight": lightweight,
            "server_friendly": server_friendly,
        }

    def _mentions_any(self, requirement: Requirement, keywords: List[str]) -> bool:
        raw = requirement.description.lower()
        return any(keyword in raw for keyword in keywords)

    def _score_authenticated_encryption_bundle(
        self,
        requirement: Requirement,
        bundle: List[Component],
    ) -> int:
        names = {component.name.lower() for component in bundle}
        profile = self._build_requirement_profile(requirement)
        score = 0

        has_aes = any(name == "aes" or name.startswith("aes-") for name in names)
        has_gcm = "gcm" in names or "aes-gcm-siv" in names or "gcm-siv" in names
        has_chacha = "chacha20-poly1305" in names
        has_ccm = "ccm" in names
        has_ascon = "ascon" in names

        if profile["regulated"] and has_aes and has_gcm:
            score += 8
        elif profile["regulated"] and has_chacha:
            score -= 6

        if profile["lightweight"] and has_chacha:
            score += 6
        if profile["lightweight"] and has_ccm:
            score += 4
        if profile["lightweight"] and has_aes and "gcm" in names:
            score -= 3

        if profile["server_friendly"] and has_aes and has_gcm:
            score += 5
        if profile["server_friendly"] and has_ascon:
            score -= 8

        if requirement.security.security_level >= 256 and has_ascon:
            score -= 12

        primary_primitives = sum(1 for component in bundle if self._counts_as_primary_primitive(component))
        if primary_primitives > 1 and not (has_aes and has_gcm and primary_primitives == 1):
            score -= 10

        return score

    def _refine_component_selection(
        self,
        requirement: Requirement,
        selected: List[Component],
        candidates: List[Component],
        variant_index: int = 0,
    ) -> List[Component]:
        """Normalize selected components into maintainable scheme-shaped bundles."""

        deduped: List[Component] = []
        seen_names: set[str] = set()
        for component in selected:
            if component.name in seen_names:
                continue
            seen_names.add(component.name)
            deduped.append(component)

        if requirement.scheme_type != "authenticated_encryption":
            return deduped

        return self._refine_authenticated_encryption_selection(requirement, deduped, candidates, variant_index)

    def _refine_authenticated_encryption_selection(
        self,
        requirement: Requirement,
        selected: List[Component],
        candidates: List[Component],
        variant_index: int = 0,
    ) -> List[Component]:
        """Ensure AEAD schemes stay on clean, auditable component combinations."""

        bundles = self._build_authenticated_encryption_bundles(requirement, candidates)
        if not selected:
            return [component.model_copy(deep=True) for component in bundles[variant_index % len(bundles)]] if bundles else []

        selected_names = {component.name.lower() for component in selected}
        primary_primitives = sum(1 for component in selected if self._counts_as_primary_primitive(component))

        if primary_primitives > 1 and bundles:
            return [component.model_copy(deep=True) for component in bundles[variant_index % len(bundles)]]

        if "chacha20-poly1305" in selected_names:
            return self._bundle_or_selected("ChaCha20-Poly1305", bundles, selected)

        if "ascon" in selected_names:
            return self._bundle_or_selected("Ascon", bundles, selected)

        if "aes-gcm-siv" in selected_names or "gcm-siv" in selected_names:
            preferred = self._bundle_with_names({"AES-GCM-SIV", "GCM-SIV"}, bundles)
            if preferred:
                return preferred

        if "aes" in selected_names or "gcm" in selected_names or "ccm" in selected_names:
            preferred = self._bundle_with_names({"AES", "GCM", "AES-GCM-SIV", "GCM-SIV", "CCM"}, bundles)
            if preferred:
                return preferred

        return [component.model_copy(deep=True) for component in bundles[variant_index % len(bundles)]] if bundles else selected

    def _bundle_or_selected(
        self,
        component_name: str,
        bundles: List[List[Component]],
        fallback: List[Component],
    ) -> List[Component]:
        preferred = self._bundle_with_names({component_name}, bundles)
        if preferred:
            return preferred
        return fallback

    def _bundle_with_names(
        self,
        preferred_names: set[str],
        bundles: List[List[Component]],
    ) -> List[Component]:
        for bundle in bundles:
            bundle_names = {component.name for component in bundle}
            if preferred_names & bundle_names:
                return [component.model_copy(deep=True) for component in bundle]
        return []

    def _counts_as_primary_primitive(self, component: Component) -> bool:
        category = str(component.category)
        name = component.name.lower()
        return category in {"block_cipher", "stream_cipher", "aead"} or name in {"chacha20-poly1305", "ascon"}

    def _heuristic_select_components(
        self,
        requirement: Requirement,
        candidates: List[Component],
        variant_index: int = 0,
    ) -> List[Component]:
        """Fallback heuristic component selection"""

        selected = []

        # For authenticated encryption, need cipher + MAC or AEAD mode
        if requirement.scheme_type in ["authenticated_encryption", "encryption"]:
            # Select a cipher
            ciphers = [c for c in candidates
                      if c.category in ["block_cipher", "stream_cipher"]]
            if ciphers:
                cipher = ciphers[variant_index % len(ciphers)]
                selected.append(cipher)

                # For AEAD, try to find compatible components
                if requirement.scheme_type == "authenticated_encryption":
                    # First, try to find compatible AEAD modes or MACs
                    compatible = self._find_compatible_components(cipher, candidates)

                    # Filter for AEAD modes or MACs
                    aead_or_mac = [c for c in compatible
                                  if (c.category == "mode" and "authenticated_encryption" in c.properties)
                                  or c.category == "mac"]

                    if aead_or_mac:
                        picked = aead_or_mac[(variant_index // max(1, len(ciphers))) % len(aead_or_mac)]
                        selected.append(picked)
                        logger.debug(f"Auto-selected compatible component: {picked.name} for {cipher.name}")
                    else:
                        # Fallback: any AEAD mode or MAC from candidates
                        aead_modes = [c for c in candidates
                                    if c.category == "mode" and "authenticated_encryption" in c.properties]
                        if aead_modes:
                            selected.append(aead_modes[variant_index % len(aead_modes)])
                        else:
                            macs = [c for c in candidates if c.category == "mac"]
                            if macs:
                                selected.append(macs[variant_index % len(macs)])

        # For MAC, select MAC + hash
        elif requirement.scheme_type == "mac":
            macs = [c for c in candidates if c.category == "mac"]
            hashes = [c for c in candidates if c.category == "hash_function"]

            if macs:
                selected.append(macs[variant_index % len(macs)])
            if hashes:
                selected.append(hashes[(variant_index * 2) % len(hashes)])

        # For signature, select signature + hash
        elif requirement.scheme_type == "signature":
            sigs = [c for c in candidates if c.category == "signature"]
            hashes = [c for c in candidates if c.category == "hash_function"]

            if sigs:
                selected.append(sigs[variant_index % len(sigs)])
            if hashes:
                selected.append(hashes[(variant_index * 2) % len(hashes)])

        # For key derivation, select construction + hash
        elif requirement.scheme_type == "key_derivation":
            kdf = [c for c in candidates if c.category == "construction"]
            hashes = [c for c in candidates if c.category == "hash_function"]

            if kdf:
                selected.append(kdf[variant_index % len(kdf)])
            if hashes:
                selected.append(hashes[(variant_index * 2) % len(hashes)])

        # For other types, select first suitable component
        if not selected and candidates:
            selected = [candidates[variant_index % len(candidates)]]

        return selected

    def _design_architecture(
        self,
        requirement: Requirement,
        components: List[Component]
    ) -> SchemeArchitecture:
        """Design scheme architecture"""

        # Use LLM to design composition
        comp_names = [c.name for c in components]

        system_prompt = """You are a cryptographer designing secure scheme architecture."""

        user_prompt = f"""Design architecture for {requirement.scheme_type} using:
Components: {', '.join(comp_names)}

Requirements: {requirement.get_summary()}

Describe the dataflow as simple string descriptions, NOT as JSON objects.

Respond with JSON:
{{
  "composition": {{
    "pattern": "encrypt-then-mac or mac-then-encrypt etc"
  }},
  "dataflow": [
    "Step 1: Detailed description of first step",
    "Step 2: Detailed description of second step",
    "Step 3: Detailed description of third step"
  ]
}}

IMPORTANT: dataflow must be an array of STRINGS, not objects."""

        try:
            response = self.llm.generate_json(user_prompt, system_prompt, temperature=0.4)

            # Ensure dataflow is a list of strings
            dataflow = response.get("dataflow", [])
            if dataflow and isinstance(dataflow[0], dict):
                # Convert dict objects to strings
                dataflow = [
                    f"Step {item.get('step', i+1)}: {item.get('description', str(item))}"
                    for i, item in enumerate(dataflow)
                ]

            return SchemeArchitecture(
                components=components,
                composition=response.get("composition", {}),
                dataflow=dataflow,
            )

        except Exception as e:
            logger.warning(f"Architecture design failed: {e}")
            # Fallback: simple architecture
            return SchemeArchitecture(
                components=components,
                composition={"pattern": "standard"},
                dataflow=["Input → Component 1 → Component 2 → Output"],
            )

    def _determine_parameters(
        self,
        requirement: Requirement,
        components: List[Component]
    ) -> SchemeParameters:
        """Determine scheme parameters"""

        params = SchemeParameters()

        # Extract from components
        for comp in components:
            if comp.parameters.key_size:
                # Use maximum key size that meets security requirement
                key_sizes = comp.parameters.key_size if isinstance(comp.parameters.key_size, list) else [comp.parameters.key_size]
                suitable = [k for k in key_sizes if k >= requirement.security.security_level]
                if suitable:
                    params.key_size = suitable[0]

            if comp.parameters.block_size and not params.block_size:
                params.block_size = comp.parameters.block_size

            if comp.parameters.nonce_size and not params.nonce_size:
                params.nonce_size = comp.parameters.nonce_size

            if comp.parameters.tag_size and not params.tag_size:
                params.tag_size = comp.parameters.tag_size

        return params

    def _analyze_security(
        self,
        requirement: Requirement,
        components: List[Component],
        architecture: SchemeArchitecture
    ) -> SecurityAnalysis:
        """Analyze security of the scheme"""

        # Collect security properties from components
        properties = set()
        for comp in components:
            properties.update(comp.properties)

        # Common AEAD properties
        if requirement.scheme_type == "authenticated_encryption":
            properties.update(["IND-CPA", "INT-CTXT"])

        return SecurityAnalysis(
            threat_model={"adversary": "standard cryptographic adversary"},
            properties=list(properties),
            assumptions=["Components used correctly", "Keys generated securely"],
            concerns=self._identify_concerns(requirement, components),
        )

    def _identify_concerns(
        self,
        requirement: Requirement,
        components: List[Component]
    ) -> List[str]:
        """Identify potential security concerns"""

        concerns = []

        # Check nonce management
        for comp in components:
            if comp.category == "stream_cipher":
                concerns.append("⚠ Nonce must never be reused with the same key")

        # Check quantum resistance
        if requirement.security.quantum_resistant:
            concerns.append("⚠ Selected components are not quantum-resistant")

        return concerns

    def _generate_rationale(
        self,
        requirement: Requirement,
        components: List[Component],
        architecture: SchemeArchitecture
    ) -> str:
        """Generate design rationale"""

        rationale = f"## Design Rationale\n\n"
        rationale += f"This scheme was designed to meet the requirement: {requirement.description}\n\n"

        rationale += "### Component Selection\n"
        for comp in components:
            rationale += f"- **{comp.name}**: {comp.description or 'Selected for its proven security and performance.'}\n"

        rationale += "\n### Architecture\n"
        rationale += f"Pattern: {architecture.composition.get('pattern', 'standard')}\n"

        return rationale

    def _calculate_score(
        self,
        requirement: Requirement,
        components: List[Component],
        security: SecurityAnalysis
    ) -> float:
        """Calculate overall scheme score"""

        score = 0.0
        fit_score = self._calculate_requirement_fit_score(requirement, components)

        # Security score (35%)
        sec_score = min(10.0, len(security.properties) * 2.0)
        score += 0.35 * sec_score

        # Component maturity (25%)
        standardized = sum(1 for c in components if c.security.standardized)
        mat_score = (standardized / len(components)) * 10 if components else 0
        score += 0.25 * mat_score

        # Performance (15%)
        perf_map = {
            "very_high": 9.5,
            "extremely_high": 9.7,
            "high": 8.5,
            "very_fast": 9.2,
            "fast": 8.3,
            "medium_high": 7.7,
            "medium": 7.0,
            "configurable": 7.0,
            "low": 5.5,
            "slow": 4.8,
            "slow_by_design": 4.4,
            "very_low": 3.8,
            "unknown": 6.0,
        }
        perf_values = []
        for comp in components:
            key = str(comp.performance.software_speed).strip().lower()
            perf_values.append(perf_map.get(key, 6.5))
        perf_score = sum(perf_values) / len(perf_values) if perf_values else 7.0
        score += 0.15 * perf_score

        # Simplicity (5%)
        simp_score = max(0, 10 - len(components))
        score += 0.05 * simp_score

        # Requirement fit (20%)
        score += 0.2 * fit_score

        return round(score, 2)

    def _calculate_requirement_fit_score(
        self,
        requirement: Requirement,
        components: List[Component],
    ) -> float:
        """Estimate how well a component stack fits the requirement semantics."""

        if not components:
            return 0.0

        profile = self._build_requirement_profile(requirement)
        names = {component.name.lower() for component in components}
        score = 5.0

        has_aes = any(name == "aes" or name.startswith("aes-") for name in names)
        has_gcm = "gcm" in names or "aes-gcm-siv" in names or "gcm-siv" in names
        has_chacha = "chacha20-poly1305" in names
        has_ccm = "ccm" in names
        has_ascon = "ascon" in names
        has_pq = any(
            any(keyword in component.name.lower() for keyword in ["kyber", "ml-kem", "dilithium", "ml-dsa", "falcon", "sphincs"])
            for component in components
        )
        primary_primitives = sum(1 for component in components if self._counts_as_primary_primitive(component))

        if requirement.scheme_type == "authenticated_encryption":
            if has_aes and has_gcm:
                score += 2.5
            elif has_chacha or has_ascon or has_ccm:
                score += 1.5
            else:
                score -= 2.5

            if primary_primitives > 1 and not has_gcm:
                score -= 3.0

        if profile["regulated"] and has_aes and has_gcm:
            score += 2.5
        elif profile["regulated"] and has_chacha:
            score -= 2.0

        if profile["lightweight"] and has_chacha:
            score += 1.5
        if profile["lightweight"] and has_ccm:
            score += 1.2
        if profile["server_friendly"] and has_ascon:
            score -= 2.0

        if requirement.security.security_level >= 256 and has_ascon:
            score -= 2.5

        if requirement.security.quantum_resistant:
            score += 1.5 if has_pq else -1.0

        if profile["low_latency"]:
            fast_components = sum(
                1
                for component in components
                if str(component.performance.software_speed).strip().lower() in {"very_high", "high", "very_fast", "fast"}
            )
            score += min(1.5, fast_components * 0.6)

        return max(0.0, min(10.0, score))

    def _generate_scheme_name(
        self,
        components: List[Component],
        variant_index: int
    ) -> str:
        """Generate a name for the scheme"""

        if len(components) == 1:
            name = components[0].name
        elif len(components) == 2:
            name = f"{components[0].name}-{components[1].name}"
        else:
            name = f"{components[0].name}-based"

        if variant_index > 0:
            name += f" (Variant {variant_index + 1})"

        return name
