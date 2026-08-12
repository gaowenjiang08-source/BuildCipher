"""
Component Recommendation Engine
根据需求智能推荐最合适的密码学组件
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

from cipher_genius.models.component import Component, ComponentType
from cipher_genius.knowledge.components import ComponentLibrary, get_component_library


class PerformanceLevel(str, Enum):
    """Performance requirement levels"""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ANY = "any"


class UseCaseCategory(str, Enum):
    """Common use case categories"""
    DATA_ENCRYPTION = "data_encryption"
    COMMUNICATION = "communication"
    AUTHENTICATION = "authentication"
    INTEGRITY = "integrity"
    KEY_ESTABLISHMENT = "key_establishment"
    DIGITAL_SIGNATURE = "digital_signature"
    POST_QUANTUM = "post_quantum"
    LIGHTWEIGHT = "lightweight"
    HIGH_SECURITY = "high_security"


class ComponentRecommender:
    """Recommend best components for given requirements"""

    def __init__(self, library: Optional[ComponentLibrary] = None):
        """
        Initialize recommender

        Args:
            library: Component library instance (uses global if not provided)
        """
        self.library = library or get_component_library()
        self.component_scores: Dict[str, float] = {}

        # Use case to component category mappings
        self.use_case_mappings = {
            UseCaseCategory.DATA_ENCRYPTION: [
                ComponentType.BLOCK_CIPHER,
                ComponentType.AEAD,
                ComponentType.MODE_OF_OPERATION
            ],
            UseCaseCategory.COMMUNICATION: [
                ComponentType.AEAD,
                ComponentType.STREAM_CIPHER,
                ComponentType.KEY_EXCHANGE
            ],
            UseCaseCategory.AUTHENTICATION: [
                ComponentType.MAC,
                ComponentType.SIGNATURE,
                ComponentType.HASH_FUNCTION
            ],
            UseCaseCategory.INTEGRITY: [
                ComponentType.HASH_FUNCTION,
                ComponentType.MAC
            ],
            UseCaseCategory.KEY_ESTABLISHMENT: [
                ComponentType.KEY_EXCHANGE
            ],
            UseCaseCategory.DIGITAL_SIGNATURE: [
                ComponentType.SIGNATURE
            ],
            UseCaseCategory.POST_QUANTUM: [
                ComponentType.KEY_EXCHANGE,
                ComponentType.SIGNATURE
            ],
            UseCaseCategory.LIGHTWEIGHT: [
                ComponentType.BLOCK_CIPHER,
                ComponentType.STREAM_CIPHER,
                ComponentType.HASH_FUNCTION
            ],
            UseCaseCategory.HIGH_SECURITY: [
                ComponentType.BLOCK_CIPHER,
                ComponentType.AEAD,
                ComponentType.HASH_FUNCTION
            ]
        }

        # Performance speed mappings
        self.performance_mappings = {
            PerformanceLevel.VERY_HIGH: ["very_fast", "fast"],
            PerformanceLevel.HIGH: ["very_fast", "fast", "moderate"],
            PerformanceLevel.MEDIUM: ["fast", "moderate"],
            PerformanceLevel.LOW: ["moderate", "slow"],
            PerformanceLevel.ANY: ["very_fast", "fast", "moderate", "slow", "unknown"]
        }

    def recommend_components(
        self,
        requirements: Dict[str, Any],
        num_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recommend best components based on requirements

        Args:
            requirements: Dictionary with keys:
                - security_level: int (e.g., 128, 192, 256)
                - performance: str (very_high, high, medium, low, any)
                - use_case: str (optional, e.g., "data_encryption")
                - category: ComponentType (optional)
                - properties: List[str] (optional, e.g., ["authenticated", "parallel"])
                - constraints: Dict (optional, e.g., {"max_key_size": 256})
            num_recommendations: Number of recommendations to return

        Returns:
            List of recommended components with scores and rationale
        """
        # Extract requirements
        security_level = requirements.get("security_level", 128)
        performance = requirements.get("performance", "any")
        use_case = requirements.get("use_case")
        category = requirements.get("category")
        properties = requirements.get("properties", [])
        constraints = requirements.get("constraints", {})

        # Get candidate components
        candidates = self._get_candidates(
            security_level=security_level,
            performance=performance,
            use_case=use_case,
            category=category,
            properties=properties,
            constraints=constraints
        )

        # Score each candidate
        scored_candidates = []
        for component in candidates:
            score, breakdown = self._score_component(
                component,
                requirements
            )

            recommendation = {
                "component": component,
                "name": component.name,
                "full_name": component.full_name,
                "category": component.category,
                "score": score,
                "score_breakdown": breakdown,
                "rationale": self.explain_recommendation(component, requirements),
                "security_level": component.security.security_level,
                "performance": component.performance.software_speed,
                "standardized": component.security.standardized
            }
            scored_candidates.append(recommendation)

        # Sort by score and return top N
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:num_recommendations]

    def recommend_cipher(
        self,
        security_level: int,
        performance: str,
        constraints: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Recommend block/stream ciphers

        Args:
            security_level: Required security level in bits
            performance: Performance requirement (very_high, high, medium, low, any)
            constraints: Optional constraints (e.g., max_key_size, block_size)

        Returns:
            List of recommended cipher components
        """
        requirements = {
            "security_level": security_level,
            "performance": performance,
            "constraints": constraints or {},
            "category": None  # Will search both block and stream ciphers
        }

        # Get recommendations for both block and stream ciphers
        all_recommendations = []

        for cipher_type in [ComponentType.BLOCK_CIPHER, ComponentType.STREAM_CIPHER]:
            requirements["category"] = cipher_type
            recommendations = self.recommend_components(requirements, num_recommendations=3)
            all_recommendations.extend(recommendations)

        # Sort by score and return top results
        all_recommendations.sort(key=lambda x: x["score"], reverse=True)
        return all_recommendations[:5]

    def recommend_hash(
        self,
        output_size: int,
        performance: str
    ) -> List[Dict]:
        """
        Recommend hash functions

        Args:
            output_size: Required output size in bits
            performance: Performance requirement

        Returns:
            List of recommended hash functions
        """
        requirements = {
            "security_level": output_size // 2,  # Collision resistance ~ output_size/2
            "performance": performance,
            "category": ComponentType.HASH_FUNCTION,
            "constraints": {"min_output_size": output_size}
        }

        return self.recommend_components(requirements, num_recommendations=5)

    def recommend_pqc(
        self,
        use_case: str,
        key_size_limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Recommend post-quantum algorithms

        Args:
            use_case: Use case (key_exchange, signature)
            key_size_limit: Maximum acceptable key size in bits

        Returns:
            List of recommended post-quantum algorithms
        """
        # Determine category from use case
        if use_case.lower() in ["key_exchange", "kem", "encapsulation"]:
            category = ComponentType.KEY_EXCHANGE
        elif use_case.lower() in ["signature", "sign", "signing"]:
            category = ComponentType.SIGNATURE
        else:
            category = None

        requirements = {
            "security_level": 128,  # Post-quantum typically targets at least 128-bit security
            "performance": "any",
            "category": category,
            "properties": ["post-quantum"],
            "constraints": {}
        }

        if key_size_limit:
            requirements["constraints"]["max_key_size"] = key_size_limit

        return self.recommend_components(requirements, num_recommendations=5)

    def explain_recommendation(
        self,
        component: Component,
        requirements: Dict
    ) -> str:
        """
        Explain why a component was recommended

        Args:
            component: Component to explain
            requirements: Original requirements

        Returns:
            Explanation string
        """
        reasons = []

        # Security level
        req_security = requirements.get("security_level", 128)
        if component.security.security_level >= req_security:
            reasons.append(
                f"Meets security requirement ({component.security.security_level}-bit security)"
            )

        # Performance
        req_performance = requirements.get("performance", "any")
        if req_performance != "any":
            perf_match = component.performance.software_speed in self.performance_mappings.get(
                PerformanceLevel(req_performance),
                []
            )
            if perf_match:
                reasons.append(
                    f"Good performance ({component.performance.software_speed} software speed)"
                )

        # Standardization
        if component.security.standardized:
            reasons.append("Industry standardized")

        # Security proof
        if component.security.proven_security:
            reasons.append("Proven security")

        # Use cases
        req_use_case = requirements.get("use_case")
        if req_use_case and req_use_case in component.use_cases:
            reasons.append(f"Specifically designed for {req_use_case}")

        # Properties
        req_properties = requirements.get("properties", [])
        matching_props = [p for p in req_properties if p in component.properties]
        if matching_props:
            reasons.append(f"Provides {', '.join(matching_props)}")

        # Compose explanation
        if reasons:
            explanation = f"{component.name} is recommended because: "
            explanation += "; ".join(reasons)
        else:
            explanation = f"{component.name} meets the basic requirements."

        return explanation

    def _get_candidates(
        self,
        security_level: int,
        performance: str,
        use_case: Optional[str],
        category: Optional[ComponentType],
        properties: List[str],
        constraints: Dict
    ) -> List[Component]:
        """Get candidate components matching basic criteria"""
        candidates = []

        # Start with all components or filter by category
        if category:
            candidates = self.library.find_by_category(category)
        elif use_case and use_case in UseCaseCategory.__members__.values():
            # Get categories for this use case
            use_case_enum = UseCaseCategory(use_case)
            categories = self.use_case_mappings.get(use_case_enum, [])
            for cat in categories:
                candidates.extend(self.library.find_by_category(cat))
        else:
            candidates = self.library.list_all()

        # Filter by security level
        candidates = [c for c in candidates if c.security.security_level >= security_level]

        # Filter by performance
        if performance != "any" and performance != PerformanceLevel.ANY:
            acceptable_speeds = self.performance_mappings.get(
                PerformanceLevel(performance),
                []
            )
            candidates = [
                c for c in candidates
                if c.performance.software_speed in acceptable_speeds
            ]

        # Filter by properties
        if properties:
            candidates = [
                c for c in candidates
                if all(prop in c.properties for prop in properties)
            ]

        # Apply constraints
        candidates = self._apply_constraints(candidates, constraints)

        # Filter out not recommended for use case
        if use_case:
            candidates = [
                c for c in candidates
                if use_case not in c.not_recommended_for
            ]

        return candidates

    def _apply_constraints(
        self,
        candidates: List[Component],
        constraints: Dict
    ) -> List[Component]:
        """Apply various constraints to filter candidates"""
        filtered = candidates

        # Max key size constraint
        max_key_size = constraints.get("max_key_size")
        if max_key_size:
            filtered = [
                c for c in filtered
                if c.parameters.key_size is None or
                (isinstance(c.parameters.key_size, list) and
                 any(ks <= max_key_size for ks in c.parameters.key_size)) or
                (isinstance(c.parameters.key_size, int) and
                 c.parameters.key_size <= max_key_size)
            ]

        # Min key size constraint
        min_key_size = constraints.get("min_key_size")
        if min_key_size:
            filtered = [
                c for c in filtered
                if c.parameters.key_size is None or
                (isinstance(c.parameters.key_size, list) and
                 any(ks >= min_key_size for ks in c.parameters.key_size)) or
                (isinstance(c.parameters.key_size, int) and
                 c.parameters.key_size >= min_key_size)
            ]

        # Block size constraint
        block_size = constraints.get("block_size")
        if block_size:
            filtered = [
                c for c in filtered
                if c.parameters.block_size is None or
                c.parameters.block_size == block_size
            ]

        # Output size constraint
        min_output_size = constraints.get("min_output_size")
        if min_output_size:
            filtered = [
                c for c in filtered
                if c.parameters.output_size is None or
                c.parameters.output_size >= min_output_size
            ]

        # Memory constraint
        max_memory = constraints.get("max_memory", "high")
        memory_levels = {"low": 0, "moderate": 1, "high": 2, "very_high": 3, "unknown": 2}
        max_mem_level = memory_levels.get(max_memory, 2)
        filtered = [
            c for c in filtered
            if memory_levels.get(c.performance.memory, 2) <= max_mem_level
        ]

        return filtered

    def _score_component(
        self,
        component: Component,
        requirements: Dict
    ) -> Tuple[float, Dict[str, float]]:
        """
        Score a component based on how well it meets requirements

        Returns:
            (total_score, score_breakdown)
        """
        scores = {}
        weights = {
            "security": 0.35,
            "performance": 0.25,
            "standardization": 0.15,
            "proven_security": 0.10,
            "use_case_match": 0.10,
            "properties": 0.05
        }

        # Security score
        req_security = requirements.get("security_level", 128)
        security_excess = component.security.security_level - req_security
        if security_excess >= 128:
            scores["security"] = 1.0
        elif security_excess >= 64:
            scores["security"] = 0.9
        elif security_excess >= 0:
            scores["security"] = 0.8
        else:
            scores["security"] = 0.5  # Below requirement

        # Performance score
        req_performance = requirements.get("performance", "any")
        if req_performance == "any" or req_performance == PerformanceLevel.ANY:
            scores["performance"] = 0.8
        else:
            perf_rank = {
                "very_fast": 1.0,
                "fast": 0.8,
                "moderate": 0.6,
                "slow": 0.4,
                "unknown": 0.5
            }
            scores["performance"] = perf_rank.get(
                component.performance.software_speed,
                0.5
            )

        # Standardization score
        scores["standardization"] = 1.0 if component.security.standardized else 0.5

        # Proven security score
        scores["proven_security"] = 1.0 if component.security.proven_security else 0.6

        # Use case match score
        req_use_case = requirements.get("use_case")
        if req_use_case:
            if req_use_case in component.use_cases:
                scores["use_case_match"] = 1.0
            elif req_use_case in component.not_recommended_for:
                scores["use_case_match"] = 0.0
            else:
                scores["use_case_match"] = 0.5
        else:
            scores["use_case_match"] = 0.8

        # Properties score
        req_properties = requirements.get("properties", [])
        if req_properties:
            matching = sum(1 for p in req_properties if p in component.properties)
            scores["properties"] = matching / len(req_properties)
        else:
            scores["properties"] = 0.8

        # Calculate weighted total
        total_score = sum(scores[key] * weights[key] for key in scores)

        return total_score, scores

    def compare_components(
        self,
        component_names: List[str],
        requirements: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple components

        Args:
            component_names: List of component names to compare
            requirements: Optional requirements for scoring

        Returns:
            Comparison data including scores and differences
        """
        components = []
        for name in component_names:
            comp = self.library.get(name)
            if comp:
                components.append(comp)

        if not components:
            return {"error": "No valid components found"}

        comparison = {
            "components": [],
            "summary": {}
        }

        # If requirements provided, score each component
        if requirements:
            for comp in components:
                score, breakdown = self._score_component(comp, requirements)
                comparison["components"].append({
                    "name": comp.name,
                    "score": score,
                    "breakdown": breakdown,
                    "security_level": comp.security.security_level,
                    "performance": comp.performance.software_speed,
                    "standardized": comp.security.standardized
                })
        else:
            # Just provide basic comparison
            for comp in components:
                comparison["components"].append({
                    "name": comp.name,
                    "category": comp.category,
                    "security_level": comp.security.security_level,
                    "performance": comp.performance.software_speed,
                    "memory": comp.performance.memory,
                    "standardized": comp.security.standardized,
                    "properties": comp.properties
                })

        # Add summary
        comparison["summary"]["best_security"] = max(
            components,
            key=lambda c: c.security.security_level
        ).name

        perf_rank = {"very_fast": 4, "fast": 3, "moderate": 2, "slow": 1, "unknown": 0}
        comparison["summary"]["best_performance"] = max(
            components,
            key=lambda c: perf_rank.get(c.performance.software_speed, 0)
        ).name

        standardized = [c for c in components if c.security.standardized]
        if standardized:
            comparison["summary"]["standardized_options"] = [c.name for c in standardized]

        return comparison

    def get_alternatives(
        self,
        component_name: str,
        requirements: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Find alternative components to the given component

        Args:
            component_name: Name of the component to find alternatives for
            requirements: Optional requirements for filtering

        Returns:
            List of alternative components with explanations
        """
        component = self.library.get(component_name)
        if not component:
            return []

        # Build requirements based on component if not provided
        if not requirements:
            requirements = {
                "security_level": component.security.security_level,
                "performance": "any",
                "category": component.category,
                "use_case": component.use_cases[0] if component.use_cases else None
            }
        else:
            # Ensure category matches
            requirements["category"] = component.category

        # Get recommendations
        recommendations = self.recommend_components(requirements, num_recommendations=10)

        # Filter out the original component
        alternatives = [
            rec for rec in recommendations
            if rec["name"] != component_name
        ]

        return alternatives[:5]


# Convenience function for global recommender instance
_global_recommender = None


def get_recommender() -> ComponentRecommender:
    """Get global recommender instance"""
    global _global_recommender
    if _global_recommender is None:
        _global_recommender = ComponentRecommender()
    return _global_recommender
