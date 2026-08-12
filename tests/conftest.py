"""Shared pytest fixtures for deterministic localhost validation."""

from __future__ import annotations

import pytest


class OfflineLLM:
    """Fail immediately so product fallbacks run without external network calls."""

    def generate(self, *args, **kwargs):
        raise RuntimeError("External LLM disabled during local tests")

    def generate_json(self, *args, **kwargs):
        raise RuntimeError("External LLM disabled during local tests")

    def generate_structured(self, *args, **kwargs):
        raise RuntimeError("External LLM disabled during local tests")


@pytest.fixture(autouse=True)
def disable_external_llm_calls(monkeypatch):
    """Keep the test suite local while preserving production provider interfaces."""
    from cipher_genius.codegen import generator as codegen_module
    from cipher_genius.core import attack_planning_agent
    from cipher_genius.core import audit_evaluation_agent
    from cipher_genius.core import expert_gate_agent
    from cipher_genius.core import generator as generator_module
    from cipher_genius.core import parser as parser_module
    from cipher_genius.core import patch_planning_agent
    from cipher_genius.core import reflection_agent
    from cipher_genius.core import vulnerability_evaluation_agent

    modules = [
        parser_module,
        generator_module,
        codegen_module,
        audit_evaluation_agent,
        attack_planning_agent,
        vulnerability_evaluation_agent,
        expert_gate_agent,
        patch_planning_agent,
        reflection_agent,
    ]
    for module in modules:
        monkeypatch.setattr(module, "get_llm_interface", lambda *args, **kwargs: OfflineLLM())

