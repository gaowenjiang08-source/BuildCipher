"""Manifest-driven skill registry."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

SKILLS_DIR_ENV = "CIPHER_GENIUS_SKILLS_DIR"


def _has_yaml_files(path: Path) -> bool:
    return path.exists() and any(path.rglob("*.yaml"))


def _resolve_default_skill_dir() -> Path:
    env_dir = os.getenv(SKILLS_DIR_ENV)
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    module_file = Path(__file__).resolve()
    cwd = Path.cwd().resolve()
    candidate_roots = [*module_file.parents, cwd, *cwd.parents]

    candidates: List[Path] = []
    seen: set[str] = set()
    for root in candidate_roots:
        candidate = root / "data" / "skills"
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

    return module_file.parents[3] / "data" / "skills"


class SkillManifest(BaseModel):
    """Skill definition loaded from YAML manifest."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    description: str
    version: str = "1.0.0"
    status: str = "active"
    category: str = "general"
    execution_mode: str = "mas"
    route_priority: int = 100
    auto_route_enabled: bool = True
    tags: List[str] = Field(default_factory=list)
    route_keywords: List[str] = Field(default_factory=list)
    target_users: List[str] = Field(default_factory=list)
    output_focus: List[str] = Field(default_factory=list)
    prompt_preamble: str = ""
    prompt_appendix: str = ""
    example_requirement: str = ""
    recommended_num_variants: int = 3
    recommended_max_audit_rounds: int = 4
    generate_code_default: bool = True
    strict_clarification_default: bool = False


class SkillRegistry:
    """Load and expose available skills."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = _resolve_default_skill_dir()

        self.data_dir = Path(data_dir)
        self._skills: Dict[str, SkillManifest] = {}
        self._load_skills()

    def _load_skills(self) -> None:
        if not self.data_dir.exists():
            return

        for yaml_file in sorted(self.data_dir.rglob("*.yaml")):
            with open(yaml_file, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            skill = SkillManifest.model_validate(data)
            self._skills[skill.id] = skill

    def list_all(self) -> List[SkillManifest]:
        return sorted(self._skills.values(), key=lambda item: (item.category.lower(), item.name.lower()))

    def get(self, skill_id: str) -> Optional[SkillManifest]:
        return self._skills.get(skill_id)


@lru_cache()
def get_skill_registry() -> SkillRegistry:
    """Get global skill registry instance."""
    return SkillRegistry()
