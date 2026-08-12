from cipher_genius.testing import ConstructionBenchmarkRunner, get_construction_benchmark_dataset


def test_construction_benchmark_dataset_loads_seven_cases():
    dataset = get_construction_benchmark_dataset()

    assert dataset.benchmark_id == "construction-trusted-delivery-v1"
    assert len(dataset.cases) == 7


def test_construction_benchmark_hits_expected_skills_templates_and_sections():
    result = ConstructionBenchmarkRunner().run()

    assert result.total_cases == 7
    assert result.skill_hit_rate == 1.0
    assert result.template_hit_rate == 1.0
    assert result.section_hit_rate == 1.0
    assert all(case.skill_match for case in result.cases)
    assert all(case.template_match for case in result.cases)
    assert all(case.section_coverage_ok for case in result.cases)

