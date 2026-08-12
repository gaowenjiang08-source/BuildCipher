"""Routing and report-template regression benchmark for construction delivery."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

from cipher_genius.reporting import ReportTemplateRegistry, get_report_template_registry
from cipher_genius.skills import SkillRegistry, get_skill_registry
from cipher_genius.skills.router import SkillRouter

BENCHMARKS_DIR_ENV = "CIPHER_GENIUS_BENCHMARKS_DIR"


def _resolve_benchmark_dir() -> Path:
    env_dir = os.getenv(BENCHMARKS_DIR_ENV)
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    module_file = Path(__file__).resolve()
    for root in [*module_file.parents, Path.cwd().resolve(), *Path.cwd().resolve().parents]:
        candidate = root / "data" / "benchmarks"
        if candidate.exists():
            return candidate
    return module_file.parents[3] / "data" / "benchmarks"


class ConstructionBenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    case_id: str
    scenario: str = "construction"
    requirement: str
    expected_skill_id: str
    expected_template_id: str
    required_sections: List[str] = Field(default_factory=list)


class ConstructionBenchmarkDataset(BaseModel):
    model_config = ConfigDict(extra="ignore")

    benchmark_id: str
    name: str
    description: str = ""
    cases: List[ConstructionBenchmarkCase] = Field(default_factory=list)


@dataclass
class ConstructionBenchmarkCaseResult:
    case_id: str
    scenario: str
    requirement: str
    expected_skill_id: str
    recommended_skill_id: str | None
    expected_template_id: str
    resolved_template_id: str | None
    skill_match: bool
    template_match: bool
    section_coverage_ok: bool
    candidate_ids: List[str]
    missing_sections: List[str]


@dataclass
class ConstructionBenchmarkResult:
    benchmark_id: str
    benchmark_name: str
    scenario: str
    total_cases: int
    skill_hits: int
    template_hits: int
    section_hits: int
    skill_hit_rate: float
    template_hit_rate: float
    section_hit_rate: float
    cases: List[ConstructionBenchmarkCaseResult]


class ConstructionBenchmarkRunner:
    """Run construction Skill routing and report-template coverage checks."""

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        template_registry: ReportTemplateRegistry | None = None,
        dataset: ConstructionBenchmarkDataset | None = None,
    ):
        self.registry = registry or get_skill_registry()
        self.template_registry = template_registry or get_report_template_registry()
        self.router = SkillRouter(self.registry)
        self.dataset = dataset or get_construction_benchmark_dataset()

    def run(self) -> ConstructionBenchmarkResult:
        cases: List[ConstructionBenchmarkCaseResult] = []
        for case in self.dataset.cases:
            routed = self.router.route(case.requirement, max_candidates=3)
            recommended = routed.recommended_skill.id if routed.recommended_skill else None
            candidate_ids = [candidate.skill.id for candidate in routed.candidates]
            template = self.template_registry.resolve(case.scenario, recommended)
            resolved = template.id if template else None
            titles = template.section_titles if template else []
            missing = [title for title in case.required_sections if title not in titles]
            cases.append(
                ConstructionBenchmarkCaseResult(
                    case_id=case.case_id,
                    scenario=case.scenario,
                    requirement=case.requirement,
                    expected_skill_id=case.expected_skill_id,
                    recommended_skill_id=recommended,
                    expected_template_id=case.expected_template_id,
                    resolved_template_id=resolved,
                    skill_match=recommended == case.expected_skill_id,
                    template_match=resolved == case.expected_template_id,
                    section_coverage_ok=not missing,
                    candidate_ids=candidate_ids,
                    missing_sections=missing,
                )
            )

        total = len(cases)
        skill_hits = sum(item.skill_match for item in cases)
        template_hits = sum(item.template_match for item in cases)
        section_hits = sum(item.section_coverage_ok for item in cases)
        return ConstructionBenchmarkResult(
            benchmark_id=self.dataset.benchmark_id,
            benchmark_name=self.dataset.name,
            scenario="construction",
            total_cases=total,
            skill_hits=skill_hits,
            template_hits=template_hits,
            section_hits=section_hits,
            skill_hit_rate=round(skill_hits / total, 4) if total else 0.0,
            template_hit_rate=round(template_hits / total, 4) if total else 0.0,
            section_hit_rate=round(section_hits / total, 4) if total else 0.0,
            cases=cases,
        )


@lru_cache()
def get_construction_benchmark_dataset(
    benchmark_file: Optional[str] = None,
) -> ConstructionBenchmarkDataset:
    path = (
        Path(benchmark_file)
        if benchmark_file
        else _resolve_benchmark_dir() / "construction_trusted_delivery.yaml"
    )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ConstructionBenchmarkDataset.model_validate(data)

