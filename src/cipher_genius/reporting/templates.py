"""Manifest-driven report template registry."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

REPORT_TEMPLATES_DIR_ENV = "CIPHER_GENIUS_REPORT_TEMPLATES_DIR"


def _has_yaml_files(path: Path) -> bool:
    return path.exists() and any(path.rglob("*.yaml"))


def _resolve_default_template_dir() -> Path:
    env_dir = os.getenv(REPORT_TEMPLATES_DIR_ENV)
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    module_file = Path(__file__).resolve()
    cwd = Path.cwd().resolve()
    candidate_roots = [*module_file.parents, cwd, *cwd.parents]

    candidates: List[Path] = []
    seen: set[str] = set()
    for root in candidate_roots:
        candidate = root / "data" / "report_templates"
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

    return module_file.parents[3] / "data" / "report_templates"


class ReportTemplateSection(BaseModel):
    """Single report template section."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    purpose: str = ""


class ReportTemplateManifest(BaseModel):
    """Report template definition loaded from YAML."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    status: str = "active"
    scenario: str = "general"
    applies_to_skills: List[str] = Field(default_factory=list)
    summary: str = ""
    target_audiences: List[str] = Field(default_factory=list)
    control_focus: List[str] = Field(default_factory=list)
    evidence_checklist: List[str] = Field(default_factory=list)
    open_question_prompts: List[str] = Field(default_factory=list)
    sections: List[ReportTemplateSection] = Field(default_factory=list)

    @property
    def section_titles(self) -> List[str]:
        return [section.title for section in self.sections]


class ReportTemplateRegistry:
    """Load and expose available report templates."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = _resolve_default_template_dir()

        self.data_dir = Path(data_dir)
        self._templates: Dict[str, ReportTemplateManifest] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        if not self.data_dir.exists():
            return

        for yaml_file in sorted(self.data_dir.rglob("*.yaml")):
            with open(yaml_file, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            template = ReportTemplateManifest.model_validate(data)
            self._templates[template.id] = template

    def list_all(self) -> List[ReportTemplateManifest]:
        return sorted(self._templates.values(), key=lambda item: (item.scenario.lower(), item.name.lower()))

    def get(self, template_id: str) -> Optional[ReportTemplateManifest]:
        return self._templates.get(template_id)

    def resolve(self, scenario: str, skill_id: str | None = None) -> Optional[ReportTemplateManifest]:
        """Resolve the best report template for the given scenario/skill.

        Resolution order:
        1. Active template explicitly bound to the skill.
        2. Active scenario-default template (same scenario, no `applies_to_skills`).
        3. Active general default template.
        """
        normalized_scenario = str(scenario or "general").strip().lower() or "general"
        active_templates = [
            template for template in self.list_all() if str(template.status).lower() == "active"
        ]

        if skill_id:
            for template in active_templates:
                if skill_id in template.applies_to_skills:
                    return template

        for template in active_templates:
            if template.scenario.lower() == normalized_scenario and not template.applies_to_skills:
                return template

        for template in active_templates:
            if template.scenario.lower() == "general" and not template.applies_to_skills:
                return template

        return active_templates[0] if active_templates else None


@lru_cache()
def get_report_template_registry() -> ReportTemplateRegistry:
    """Get global report template registry instance."""
    return ReportTemplateRegistry()

