"""Application service for regression benchmark runs."""

from __future__ import annotations

from cipher_genius.api.schemas import BenchmarkCaseResultPayload, BenchmarkRunResponse
from cipher_genius.testing import (
    ConstructionBenchmarkResult,
    ConstructionBenchmarkRunner,
)


class BenchmarkService:
    """Expose benchmark utilities through the API layer."""

    def run_construction_benchmark(self) -> BenchmarkRunResponse:
        return self._to_response(ConstructionBenchmarkRunner().run())

    def _to_response(
        self,
        result: ConstructionBenchmarkResult,
    ) -> BenchmarkRunResponse:
        return BenchmarkRunResponse(
            benchmark_id=result.benchmark_id,
            benchmark_name=result.benchmark_name,
            scenario=result.scenario,
            total_cases=result.total_cases,
            skill_hits=result.skill_hits,
            template_hits=result.template_hits,
            section_hits=result.section_hits,
            skill_hit_rate=result.skill_hit_rate,
            template_hit_rate=result.template_hit_rate,
            section_hit_rate=result.section_hit_rate,
            cases=[
                BenchmarkCaseResultPayload(
                    case_id=case.case_id,
                    scenario=case.scenario,
                    requirement=case.requirement,
                    expected_skill_id=case.expected_skill_id,
                    recommended_skill_id=case.recommended_skill_id,
                    expected_template_id=case.expected_template_id,
                    resolved_template_id=case.resolved_template_id,
                    skill_match=case.skill_match,
                    template_match=case.template_match,
                    section_coverage_ok=case.section_coverage_ok,
                    candidate_ids=case.candidate_ids,
                    missing_sections=case.missing_sections,
                )
                for case in result.cases
            ],
        )
