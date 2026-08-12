"""Component library for managing cryptographic components"""

import os
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache

from cipher_genius.models.component import (
    Component,
    ComponentParameters,
    ComponentType,
    ImplementationSource,
    Performance,
    Reference,
    SecurityAnalysis,
    SecurityProfile,
    StandardMetadata,
)

COMPONENTS_DIR_ENV = "CIPHER_GENIUS_COMPONENTS_DIR"


def _has_yaml_files(path: Path) -> bool:
    return path.exists() and any(path.rglob("*.yaml"))


def _resolve_default_component_dir() -> Path:
    env_dir = os.getenv(COMPONENTS_DIR_ENV)
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    module_file = Path(__file__).resolve()
    cwd = Path.cwd().resolve()
    candidate_roots = [*module_file.parents, cwd, *cwd.parents]

    candidates: List[Path] = []
    seen: set[str] = set()
    for root in candidate_roots:
        candidate = root / "data" / "components"
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)

    for candidate in candidates:
        if _has_yaml_files(candidate):
            return candidate

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return module_file.parents[3] / "data" / "components"


class ComponentLibrary:
    """Library of cryptographic components"""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = _resolve_default_component_dir()

        self.data_dir = Path(data_dir)
        self._components: Dict[str, Component] = {}
        self._load_components()

    def _load_components(self) -> None:
        """Load all components from YAML files"""
        if not self.data_dir.exists():
            print(f"Warning: Data directory not found: {self.data_dir}")
            return

        yaml_files = list(self.data_dir.rglob("*.yaml"))
        if not yaml_files:
            print(f"Warning: No component YAML files found in: {self.data_dir}")
            return

        # Load from all subdirectories
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    component = self._parse_component(data)
                    self._components[component.name] = component
            except Exception as e:
                print(f"Error loading {yaml_file}: {e}")

    def _parse_component(self, data: Dict[str, Any]) -> Component:
        """Parse component from YAML data"""

        # Parse parameters
        params_data = data.get("parameters", {})
        parameters = ComponentParameters(
            key_size=params_data.get("key_size"),
            block_size=params_data.get("block_size"),
            output_size=params_data.get("output_size"),
            rounds=params_data.get("rounds"),
            nonce_size=params_data.get("nonce_size"),
            tag_size=params_data.get("tag_size"),
        )

        # Parse performance
        perf_data = data.get("performance", {})
        performance = Performance(
            software_speed=perf_data.get("software_speed", "unknown"),
            hardware_speed=perf_data.get("hardware_speed"),
            memory=perf_data.get("memory", "unknown"),
            power=perf_data.get("power", "unknown"),
        )

        # Parse security
        sec_data = data.get("security", {})
        security = SecurityAnalysis(
            security_level=sec_data.get("security_level", 128),
            best_attack=sec_data.get("best_attack"),
            attack_complexity=sec_data.get("attack_complexity"),
            status=sec_data.get("status", "secure"),
            standardized=sec_data.get("standardized", False),
            proven_security=sec_data.get("proven_security", False),
        )

        security_profile_data = data.get("security_profile")
        security_profile = (
            SecurityProfile.model_validate(security_profile_data)
            if isinstance(security_profile_data, dict)
            else None
        )
        standard_data = data.get("standard")
        standard = (
            StandardMetadata.model_validate(standard_data)
            if isinstance(standard_data, dict)
            else None
        )
        implementation_sources = [
            ImplementationSource.model_validate(item)
            for item in data.get("implementation_sources", [])
            if isinstance(item, dict)
        ]

        # Parse references
        references = []
        for ref_data in data.get("references", []):
            ref = Reference(
                type=ref_data["type"],
                title=ref_data["title"],
                authors=ref_data.get("authors"),
                year=ref_data.get("year"),
                url=ref_data.get("url"),
            )
            references.append(ref)

        # Create component
        component = Component(
            name=data["name"],
            full_name=data.get("full_name"),
            category=ComponentType(data["category"]),
            description=data.get("description"),
            parameters=parameters,
            properties=data.get("properties", []),
            performance=performance,
            security=security,
            security_profile=security_profile,
            standard=standard,
            implementation_sources=implementation_sources,
            compatible_with=data.get("compatible_with", []),
            not_compatible_with=data.get("not_compatible_with", []),
            use_cases=data.get("use_cases", []),
            not_recommended_for=data.get("not_recommended_for", []),
            references=references,
            implementation_notes=data.get("implementation_notes"),
        )

        return component

    def get(self, name: str) -> Optional[Component]:
        """Get component by name"""
        return self._components.get(name)

    def list_all(self) -> List[Component]:
        """List all components"""
        return list(self._components.values())

    def find_by_category(self, category: ComponentType) -> List[Component]:
        """Find components by category"""
        return [c for c in self._components.values() if c.category == category]

    def find_by_security_level(self, min_level: int) -> List[Component]:
        """Find components meeting minimum security level"""
        return [c for c in self._components.values()
                if c.security.security_level >= min_level]

    def find_by_use_case(self, use_case: str) -> List[Component]:
        """Find components suitable for a use case"""
        return [c for c in self._components.values()
                if use_case in c.use_cases]

    def find_compatible(self, component: Component) -> List[Component]:
        """Find components compatible with given component"""
        compatible = []
        for c in self._components.values():
            if c.name != component.name and component.is_compatible_with(c):
                compatible.append(c)
        return compatible

    def search(
        self,
        category: Optional[ComponentType] = None,
        min_security: Optional[int] = None,
        use_case: Optional[str] = None,
        properties: Optional[List[str]] = None,
    ) -> List[Component]:
        """Search components with multiple filters"""
        results = self.list_all()

        if category:
            results = [c for c in results if c.category == category]

        if min_security:
            results = [c for c in results if c.security.security_level >= min_security]

        if use_case:
            results = [c for c in results if use_case in c.use_cases]

        if properties:
            results = [c for c in results
                      if all(prop in c.properties for prop in properties)]

        return results

    def get_summary(self) -> str:
        """Get summary of library contents"""
        summary = f"Component Library Summary\n"
        summary += f"Total Components: {len(self._components)}\n\n"

        # Count by category
        by_category: Dict[str, int] = {}
        for comp in self._components.values():
            cat = comp.category
            by_category[cat] = by_category.get(cat, 0) + 1

        summary += "By Category:\n"
        for cat, count in sorted(by_category.items()):
            summary += f"  {cat}: {count}\n"

        return summary


# Global instance
@lru_cache()
def get_component_library() -> ComponentLibrary:
    """Get global component library instance"""
    return ComponentLibrary()
