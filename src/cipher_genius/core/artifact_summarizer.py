"""Compact artifact summarization helpers for projection and handoff payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cipher_genius.api.schemas import AttackResultPayload
from cipher_genius.api.schemas import PatchSpecPayload


class ArtifactSummarizer:
    """Turn large sandbox artifacts into compact summaries for agent windows."""

    def summarize_attack_results(
        self,
        attack_results: list[AttackResultPayload],
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Summarize a bounded number of attack results."""

        return [self.summarize_attack_result(item) for item in attack_results[:limit]]

    def summarize_attack_result(self, attack_result: AttackResultPayload) -> dict[str, Any]:
        """Compress one attack result into a stable card-friendly payload."""

        artifact_summaries = self.summarize_artifact_paths(
            attack_result.artifact_refs,
            attack_id=attack_result.attack_id,
            status=attack_result.status,
            fallback_summary=attack_result.summary,
        )
        top_findings = self._collect_findings(
            direct_findings=attack_result.findings,
            artifact_summaries=artifact_summaries,
        )
        return {
            "attack_id": attack_result.attack_id,
            "target_service_ref": attack_result.target_service_ref,
            "status": attack_result.status,
            "status_label": attack_result.status_label,
            "summary": attack_result.summary,
            "finding_count": len(attack_result.findings),
            "top_findings": top_findings,
            "metrics_summary": self._compact_metrics(attack_result.metrics or {}),
            "artifact_count": len(attack_result.artifact_refs),
            "artifact_summaries": artifact_summaries,
        }

    def summarize_artifact_paths(
        self,
        artifact_paths: list[str],
        *,
        attack_id: str,
        status: str,
        fallback_summary: str = "",
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Summarize artifact files referenced by one attack result."""

        summaries: list[dict[str, Any]] = []
        for index, raw_path in enumerate(artifact_paths[:limit], start=1):
            summaries.append(
                self.summarize_artifact_path(
                    raw_path,
                    attack_id=attack_id,
                    status=status,
                    index=index,
                    fallback_summary=fallback_summary,
                )
            )
        return summaries

    def collect_top_findings_from_summaries(
        self,
        attack_result_summaries: list[dict[str, Any]],
        *,
        limit: int = 6,
    ) -> list[str]:
        """Merge top findings from multiple compressed attack summaries."""

        findings: list[str] = []
        seen: set[str] = set()
        for item in attack_result_summaries[:5]:
            for finding in item.get("top_findings") or []:
                text = str(finding or "").strip()
                if not text or text in seen:
                    continue
                findings.append(text)
                seen.add(text)
                if len(findings) >= limit:
                    return findings
        return findings

    def flatten_artifact_paths(
        self,
        attack_result_summaries: list[dict[str, Any]],
        *,
        limit: int = 6,
    ) -> list[str]:
        """Collect unique artifact paths from compact attack summaries."""

        paths: list[str] = []
        seen: set[str] = set()
        for item in attack_result_summaries[:5]:
            for artifact in item.get("artifact_summaries") or []:
                path = str(artifact.get("path") or "").strip()
                if not path or path in seen:
                    continue
                paths.append(path)
                seen.add(path)
                if len(paths) >= limit:
                    return paths
        return paths

    def summarize_patch_artifacts(
        self,
        *,
        patch_spec: PatchSpecPayload,
        baseline_workspace: str | None,
        patched_workspace: str | None,
        limit: int = 4,
    ) -> dict[str, Any]:
        """Summarize patched code artifacts and lightweight diff stats."""

        candidates = self._resolve_patch_artifact_candidates(
            changed_artifacts=patch_spec.changed_artifacts,
            patched_workspace=patched_workspace,
        )
        changed_artifact_summaries: list[dict[str, Any]] = []
        for artifact_key, relative_name in candidates[:limit]:
            changed_artifact_summaries.append(
                self._summarize_patch_artifact(
                    artifact_key=artifact_key,
                    relative_name=relative_name,
                    baseline_workspace=baseline_workspace,
                    patched_workspace=patched_workspace,
                )
            )
        supporting_artifact_summaries = self._summarize_supporting_patch_artifacts(
            baseline_workspace=baseline_workspace,
            patched_workspace=patched_workspace,
            limit=6,
        )
        artifact_inventory = self._build_patch_artifact_inventory(
            changed_artifact_summaries=changed_artifact_summaries,
            supporting_artifact_summaries=supporting_artifact_summaries,
        )
        return {
            "artifact_pipeline_version": "v2",
            "patch_id": patch_spec.patch_id,
            "strategy": patch_spec.strategy,
            "summary": patch_spec.summary,
            "next_version": patch_spec.next_version,
            "changed_artifact_count": len(changed_artifact_summaries),
            "changed_artifact_summaries": changed_artifact_summaries,
            "supporting_artifact_summaries": supporting_artifact_summaries,
            "artifact_inventory": artifact_inventory,
            "regression_focus": list(patch_spec.regression_focus or []),
        }

    def summarize_artifact_path(
        self,
        raw_path: str,
        *,
        attack_id: str,
        status: str,
        index: int,
        fallback_summary: str = "",
    ) -> dict[str, Any]:
        """Summarize one artifact file referenced by the sandbox runtime."""

        path = Path(str(raw_path or ""))
        artifact_kind = self._infer_artifact_kind(path)
        summary = fallback_summary or f"攻击工件摘要：{path.name or raw_path}"
        metadata: dict[str, Any] = {
            "attack_id": attack_id,
            "status": status,
            "artifact_kind": artifact_kind,
            "file_name": path.name,
            "path_exists": path.exists(),
        }

        if path.exists():
            if artifact_kind == "metrics":
                metrics = self._load_json(path)
                metadata.update(self._compact_metrics(metrics))
                probe_count = int(metadata.get("probe_count") or 0)
                latency = metadata.get("latency_p95_ms")
                summary = f"metrics 摘要：{probe_count} 次探针，P95 延迟 {latency} ms。"
            elif artifact_kind == "finding":
                finding_payload = self._load_json(path)
                findings = self._sanitize_list(finding_payload.get("findings"), limit=4)
                risk_score = finding_payload.get("risk_score")
                metadata.update(
                    {
                        "top_findings": findings,
                        "risk_score": risk_score,
                    }
                )
                findings_text = "；".join(findings[:2]) or "未提取到发现摘要"
                summary = f"finding 摘要：{findings_text}"
            elif artifact_kind == "trace":
                trace_summary = self._summarize_trace(path)
                metadata.update(trace_summary)
                summary = (
                    f"trace 摘要：{trace_summary.get('event_count', 0)} 个事件，"
                    f"最终阶段 {trace_summary.get('last_phase') or 'unknown'}。"
                )

        return {
            "artifact_id": f"{attack_id}:{index}",
            "artifact_type": f"attack_{artifact_kind}",
            "title": path.name or str(raw_path),
            "path": str(raw_path) if str(raw_path).strip() else None,
            "summary": summary,
            "metadata": metadata,
        }

    def _infer_artifact_kind(self, path: Path) -> str:
        name = path.name.lower()
        if "metrics" in name:
            return "metrics"
        if "finding" in name:
            return "finding"
        if "trace" in name:
            return "trace"
        if "runtime" in name:
            return "runtime_info"
        return "artifact"

    def _resolve_patch_artifact_candidates(
        self,
        *,
        changed_artifacts: list[str],
        patched_workspace: str | None,
    ) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []
        seen: set[str] = set()
        mapping = {
            "python": "implementation.py",
            "c": "implementation.c",
            "pseudocode": "implementation.pseudo.txt",
            "pseudo": "implementation.pseudo.txt",
        }
        for item in changed_artifacts or []:
            text = str(item or "").strip()
            if not text:
                continue
            artifact_key = text.split(":")[-1].strip().lower()
            relative_name = mapping.get(artifact_key)
            if not relative_name or relative_name in seen:
                continue
            candidates.append((artifact_key, relative_name))
            seen.add(relative_name)

        patched_root = Path(str(patched_workspace or ""))
        if patched_root.exists():
            for artifact_key, relative_name in mapping.items():
                if artifact_key == "pseudo":
                    continue
                if relative_name in seen:
                    continue
                if (patched_root / relative_name).exists():
                    candidates.append((artifact_key, relative_name))
                    seen.add(relative_name)
        return candidates

    def _summarize_patch_artifact(
        self,
        *,
        artifact_key: str,
        relative_name: str,
        baseline_workspace: str | None,
        patched_workspace: str | None,
    ) -> dict[str, Any]:
        baseline_path = self._join_optional_path(baseline_workspace, relative_name)
        patched_path = self._join_optional_path(patched_workspace, relative_name)
        before_text = self._read_optional_text(baseline_path)
        after_text = self._read_optional_text(patched_path)
        before_lines = before_text.splitlines()
        after_lines = after_text.splitlines()
        diff_preview = self._build_line_diff_preview(before_lines, after_lines, limit=4)
        added_line_count = sum(1 for item in diff_preview if item.startswith("+"))
        removed_line_count = sum(1 for item in diff_preview if item.startswith("-"))
        return {
            "artifact_key": artifact_key,
            "artifact_type": f"patch_{artifact_key}",
            "artifact_role": "code_patch",
            "relative_name": relative_name,
            "baseline_path": str(baseline_path).replace("\\", "/") if baseline_path else None,
            "patched_path": str(patched_path).replace("\\", "/") if patched_path else None,
            "baseline_exists": baseline_path.exists() if baseline_path else False,
            "patched_exists": patched_path.exists() if patched_path else False,
            "file_size_bytes": len(after_text.encode("utf-8")) if after_text else 0,
            "before_line_count": len(before_lines),
            "after_line_count": len(after_lines),
            "line_delta": len(after_lines) - len(before_lines),
            "added_line_count": added_line_count,
            "removed_line_count": removed_line_count,
            "diff_preview": diff_preview,
            "summary": (
                f"{relative_name} 行数 {len(before_lines)} -> {len(after_lines)}，"
                f"增量预览 {len(diff_preview)} 行。"
            ),
        }

    def _summarize_supporting_patch_artifacts(
        self,
        *,
        baseline_workspace: str | None,
        patched_workspace: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        patched_root = Path(str(patched_workspace or ""))
        if not patched_root.exists():
            return []

        candidates = [
            ("manifest", "service_manifest.json", "deployment_manifest"),
            ("runtime_info", "runtime_info.json", "runtime_telemetry"),
            ("service_log", "service_stdout.log", "runtime_log"),
            ("service_runtime", "service_runtime.py", "service_bootstrap"),
        ]
        summaries: list[dict[str, Any]] = []
        for artifact_key, relative_name, artifact_role in candidates[:limit]:
            patched_path = patched_root / relative_name
            baseline_path = self._join_optional_path(baseline_workspace, relative_name)
            if not patched_path.exists() and not (baseline_path and baseline_path.exists()):
                continue
            summaries.append(
                self._summarize_supporting_patch_artifact(
                    artifact_key=artifact_key,
                    artifact_role=artifact_role,
                    relative_name=relative_name,
                    baseline_path=baseline_path,
                    patched_path=patched_path,
                )
            )
        return summaries

    def _summarize_supporting_patch_artifact(
        self,
        *,
        artifact_key: str,
        artifact_role: str,
        relative_name: str,
        baseline_path: Path | None,
        patched_path: Path,
    ) -> dict[str, Any]:
        before_text = self._read_optional_text(baseline_path)
        after_text = self._read_optional_text(patched_path)
        before_lines = before_text.splitlines()
        after_lines = after_text.splitlines()
        preview = self._build_supporting_artifact_preview(patched_path, after_text)
        return {
            "artifact_key": artifact_key,
            "artifact_type": f"patch_supporting_{artifact_key}",
            "artifact_role": artifact_role,
            "relative_name": relative_name,
            "baseline_path": str(baseline_path).replace("\\", "/") if baseline_path else None,
            "patched_path": str(patched_path).replace("\\", "/"),
            "baseline_exists": baseline_path.exists() if baseline_path else False,
            "patched_exists": patched_path.exists(),
            "file_size_bytes": patched_path.stat().st_size if patched_path.exists() else 0,
            "before_line_count": len(before_lines),
            "after_line_count": len(after_lines),
            "line_delta": len(after_lines) - len(before_lines),
            "preview": preview,
            "summary": (
                f"{relative_name} 已纳入补丁执行工件收口，"
                f"当前大小 {patched_path.stat().st_size if patched_path.exists() else 0} 字节。"
            ),
        }

    def _build_patch_artifact_inventory(
        self,
        *,
        changed_artifact_summaries: list[dict[str, Any]],
        supporting_artifact_summaries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        tracked_files = [
            str(item.get("relative_name") or "").strip()
            for item in [*changed_artifact_summaries, *supporting_artifact_summaries]
            if str(item.get("relative_name") or "").strip()
        ]
        return {
            "changed_code_artifact_count": len(changed_artifact_summaries),
            "supporting_artifact_count": len(supporting_artifact_summaries),
            "total_tracked_artifact_count": len(changed_artifact_summaries) + len(supporting_artifact_summaries),
            "added_line_total": sum(int(item.get("added_line_count") or 0) for item in changed_artifact_summaries),
            "removed_line_total": sum(int(item.get("removed_line_count") or 0) for item in changed_artifact_summaries),
            "line_delta_total": sum(int(item.get("line_delta") or 0) for item in changed_artifact_summaries),
            "tracked_files": tracked_files[:10],
        }

    def _build_supporting_artifact_preview(self, path: Path, text: str) -> list[str]:
        name = path.name.lower()
        if name.endswith(".json"):
            payload = self._load_json(path)
            keys = [str(key).strip() for key in payload.keys() if str(key).strip()][:4]
            return [f"json_keys: {', '.join(keys)}"] if keys else []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return []
        if name.endswith(".log"):
            return lines[-3:]
        return lines[:3]

    def _compact_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        return {
            "latency_p95_ms": metrics.get("latency_p95_ms"),
            "health_latency_ms": metrics.get("health_latency_ms"),
            "probe_count": metrics.get("probe_count"),
            "tx_bytes": metrics.get("tx_bytes"),
            "rx_bytes": metrics.get("rx_bytes"),
            "traffic_sample_count": len(metrics.get("traffic_series") or []),
            "service_port": metrics.get("service_port"),
            "health_status": metrics.get("health_status"),
        }

    def _collect_findings(
        self,
        *,
        direct_findings: list[str],
        artifact_summaries: list[dict[str, Any]],
    ) -> list[str]:
        direct = self._sanitize_list(direct_findings, limit=6)
        if direct:
            return direct
        findings: list[str] = []
        seen: set[str] = set()
        for artifact in artifact_summaries:
            for finding in (artifact.get("metadata") or {}).get("top_findings") or []:
                text = str(finding or "").strip()
                if not text or text in seen:
                    continue
                findings.append(text)
                seen.add(text)
                if len(findings) >= 6:
                    return findings
        return findings

    def _summarize_trace(self, path: Path) -> dict[str, Any]:
        event_count = 0
        phases: list[str] = []
        last_phase = ""
        last_message = ""
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                event_count += 1
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    continue
                phase = str(payload.get("phase") or "").strip()
                if phase:
                    phases.append(phase)
                    last_phase = phase
                message = str(payload.get("message") or "").strip()
                if message:
                    last_message = message
        return {
            "event_count": event_count,
            "phases": phases[:6],
            "last_phase": last_phase,
            "last_message": last_message,
        }

    def _join_optional_path(self, root: str | None, relative_name: str) -> Path | None:
        base = str(root or "").strip()
        if not base:
            return None
        return Path(base) / relative_name

    def _load_json(self, path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _read_optional_text(self, path: Path | None) -> str:
        if path is None or not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def _build_line_diff_preview(
        self,
        before_lines: list[str],
        after_lines: list[str],
        *,
        limit: int,
    ) -> list[str]:
        preview: list[str] = []
        seen: set[str] = set()
        before_set = {line.rstrip() for line in before_lines if line.strip()}
        after_set = {line.rstrip() for line in after_lines if line.strip()}
        for line in after_lines:
            text = line.rstrip()
            if not text or text in before_set:
                continue
            candidate = f"+ {text}"
            if candidate in seen:
                continue
            preview.append(candidate)
            seen.add(candidate)
            if len(preview) >= limit:
                return preview
        for line in before_lines:
            text = line.rstrip()
            if not text or text in after_set:
                continue
            candidate = f"- {text}"
            if candidate in seen:
                continue
            preview.append(candidate)
            seen.add(candidate)
            if len(preview) >= limit:
                return preview
        return preview

    def _sanitize_list(self, values: Any, *, limit: int) -> list[str]:
        clean: list[str] = []
        seen: set[str] = set()
        for item in values or []:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            clean.append(text)
            seen.add(text)
            if len(clean) >= limit:
                break
        return clean
