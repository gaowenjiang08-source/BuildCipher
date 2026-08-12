"""A/B testing framework for comparing MAS engines."""

from __future__ import annotations

import time
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

from cipher_genius.api.schemas import MASRequest, MASResponse
from cipher_genius.api.mas_service import MASOrchestrationService
from cipher_genius.core.langgraph_mas import LangGraphMASService
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EngineMetrics:
    """Metrics for a single engine execution."""
    engine_name: str
    execution_time: float
    success: bool
    error_message: str | None
    num_candidates: int
    has_audit: bool
    has_code: bool
    result: MASResponse | None


@dataclass
class ABTestResult:
    """A/B test comparison result."""
    requirement: str
    legacy_metrics: EngineMetrics
    langgraph_metrics: EngineMetrics
    winner: str | None
    speedup_factor: float | None
    timestamp: str


class MASEngineABTester:
    """A/B testing framework for MAS engines."""

    def __init__(self, llm_provider: str = "openai"):
        """Initialize A/B tester."""
        self.llm_provider = llm_provider
        self.legacy_service = MASOrchestrationService(llm_provider)
        self.langgraph_service = LangGraphMASService(llm_provider)

    def _execute_with_metrics(
        self,
        service: Any,
        request: MASRequest,
        engine_name: str,
    ) -> EngineMetrics:
        """Execute MAS with a specific engine and collect metrics."""
        start_time = time.perf_counter()
        success = False
        error_message = None
        result = None
        num_candidates = 0
        has_audit = False
        has_code = False

        try:
            result = service.execute(request)
            success = True

            # Extract metrics from result
            if result.architect and result.architect.candidates:
                num_candidates = len(result.architect.candidates)

            if result.auditor_rounds:
                has_audit = True

            if result.final_scheme and (
                (result.final_scheme.implementation.pseudocode or "").strip()
                or (result.final_scheme.implementation.python or "").strip()
                or (result.final_scheme.implementation.c or "").strip()
            ):
                has_code = True

        except Exception as exc:
            error_message = str(exc)
            logger.error(f"[{engine_name}] Execution failed: {exc}")

        execution_time = time.perf_counter() - start_time

        return EngineMetrics(
            engine_name=engine_name,
            execution_time=execution_time,
            success=success,
            error_message=error_message,
            num_candidates=num_candidates,
            has_audit=has_audit,
            has_code=has_code,
            result=result,
        )

    def run_ab_test(self, request: MASRequest) -> ABTestResult:
        """Run A/B test comparing both engines."""
        logger.info(f"Starting A/B test for requirement: {request.requirement[:50]}...")

        # Execute with legacy engine
        logger.info("Testing legacy engine...")
        legacy_metrics = self._execute_with_metrics(
            self.legacy_service,
            request,
            "legacy",
        )

        # Execute with LangGraph engine
        logger.info("Testing LangGraph engine...")
        langgraph_metrics = self._execute_with_metrics(
            self.langgraph_service,
            request,
            "langgraph",
        )

        # Determine winner
        winner = None
        speedup_factor = None

        if legacy_metrics.success and langgraph_metrics.success:
            if langgraph_metrics.execution_time < legacy_metrics.execution_time:
                winner = "langgraph"
                speedup_factor = legacy_metrics.execution_time / langgraph_metrics.execution_time
            else:
                winner = "legacy"
                speedup_factor = langgraph_metrics.execution_time / legacy_metrics.execution_time
        elif legacy_metrics.success:
            winner = "legacy"
        elif langgraph_metrics.success:
            winner = "langgraph"

        result = ABTestResult(
            requirement=request.requirement,
            legacy_metrics=legacy_metrics,
            langgraph_metrics=langgraph_metrics,
            winner=winner,
            speedup_factor=speedup_factor,
            timestamp=datetime.now().isoformat(),
        )

        self._log_results(result)
        return result

    def _log_results(self, result: ABTestResult) -> None:
        """Log A/B test results."""
        logger.info("=" * 80)
        logger.info("A/B Test Results")
        logger.info("=" * 80)
        logger.info(f"Requirement: {result.requirement[:60]}...")
        logger.info("")

        logger.info("Legacy Engine:")
        logger.info(f"  Success: {result.legacy_metrics.success}")
        logger.info(f"  Time: {result.legacy_metrics.execution_time:.2f}s")
        logger.info(f"  Candidates: {result.legacy_metrics.num_candidates}")
        logger.info(f"  Has Audit: {result.legacy_metrics.has_audit}")
        logger.info(f"  Has Code: {result.legacy_metrics.has_code}")
        if result.legacy_metrics.error_message:
            logger.info(f"  Error: {result.legacy_metrics.error_message}")
        logger.info("")

        logger.info("LangGraph Engine:")
        logger.info(f"  Success: {result.langgraph_metrics.success}")
        logger.info(f"  Time: {result.langgraph_metrics.execution_time:.2f}s")
        logger.info(f"  Candidates: {result.langgraph_metrics.num_candidates}")
        logger.info(f"  Has Audit: {result.langgraph_metrics.has_audit}")
        logger.info(f"  Has Code: {result.langgraph_metrics.has_code}")
        if result.langgraph_metrics.error_message:
            logger.info(f"  Error: {result.langgraph_metrics.error_message}")
        logger.info("")

        if result.winner:
            logger.info(f"Winner: {result.winner.upper()}")
            if result.speedup_factor:
                logger.info(f"Speedup: {result.speedup_factor:.2f}x")
        else:
            logger.info("Winner: NONE (both failed)")

        logger.info("=" * 80)

    def run_batch_tests(
        self,
        requirements: List[str],
        llm_provider: str | None = None,
    ) -> List[ABTestResult]:
        """Run A/B tests on multiple requirements."""
        results = []

        for i, requirement in enumerate(requirements, 1):
            logger.info(f"\n[{i}/{len(requirements)}] Testing requirement...")

            request = MASRequest(
                requirement=requirement,
                llm_provider=llm_provider or self.llm_provider,
                num_variants=1,
                max_audit_rounds=1,
                generate_code=False,
            )

            result = self.run_ab_test(request)
            results.append(result)

        self._log_batch_summary(results)
        return results

    def _log_batch_summary(self, results: List[ABTestResult]) -> None:
        """Log summary of batch tests."""
        logger.info("\n" + "=" * 80)
        logger.info("Batch Test Summary")
        logger.info("=" * 80)

        total = len(results)
        legacy_wins = sum(1 for r in results if r.winner == "legacy")
        langgraph_wins = sum(1 for r in results if r.winner == "langgraph")
        failures = sum(1 for r in results if r.winner is None)

        logger.info(f"Total tests: {total}")
        logger.info(f"Legacy wins: {legacy_wins} ({legacy_wins/total*100:.1f}%)")
        logger.info(f"LangGraph wins: {langgraph_wins} ({langgraph_wins/total*100:.1f}%)")
        logger.info(f"Both failed: {failures} ({failures/total*100:.1f}%)")

        # Average speedup for LangGraph wins
        langgraph_speedups = [
            r.speedup_factor for r in results
            if r.winner == "langgraph" and r.speedup_factor
        ]
        if langgraph_speedups:
            avg_speedup = sum(langgraph_speedups) / len(langgraph_speedups)
            logger.info(f"Average LangGraph speedup: {avg_speedup:.2f}x")

        logger.info("=" * 80)
