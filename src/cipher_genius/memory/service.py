"""Lightweight persistence for project-level case memory."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from cipher_genius.api.schemas import CaseMemoryPayload, CaseMemorySummaryPayload
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class CaseMemoryService:
    """Persist and retrieve case snapshots for cross-run reuse."""

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        if storage_dir is None:
            repo_root = Path(__file__).resolve().parents[3]
            storage_dir = repo_root / ".cache" / "case_memory"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def build_case_id(self) -> str:
        """Create a stable-looking case identifier for a new project thread."""
        return f"case-{uuid4().hex[:12]}"

    def create_empty(self, case_id: str) -> CaseMemoryPayload:
        """Create an in-memory empty snapshot without persisting it."""
        now = datetime.now(timezone.utc)
        return CaseMemoryPayload(case_id=case_id, created_at=now, updated_at=now)

    def load(self, case_id: str) -> CaseMemoryPayload | None:
        """Load a persisted case snapshot if present."""
        path = self._path_for(case_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CaseMemoryPayload.model_validate(data)
        except Exception as exc:
            logger.warning("Failed to load case memory %s: %s", case_id, exc)
            return None

    def load_or_create(self, case_id: str) -> CaseMemoryPayload:
        """Load an existing case or return a new empty snapshot."""
        return self.load(case_id) or self.create_empty(case_id)

    def save(self, snapshot: CaseMemoryPayload) -> CaseMemoryPayload:
        """Persist the given snapshot atomically."""
        path = self._path_for(snapshot.case_id)
        payload = snapshot.model_dump(mode="json")
        temp_path = path.with_suffix(".tmp")
        with self._lock:
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            temp_path.replace(path)
        return snapshot

    def get(self, case_id: str) -> CaseMemoryPayload:
        """Read a case snapshot or raise if it does not exist."""
        snapshot = self.load(case_id)
        if snapshot is None:
            raise FileNotFoundError(f"Case memory not found: {case_id}")
        return snapshot

    def summarize(self, snapshot: CaseMemoryPayload) -> CaseMemorySummaryPayload:
        """Build a lightweight summary for project selection UIs."""
        return CaseMemorySummaryPayload(
            case_id=snapshot.case_id,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            status=snapshot.status,
            status_label=snapshot.status_label,
            scenario=snapshot.scenario,
            requirement_summary=snapshot.requirement_summary,
            selected_proposal=snapshot.selected_proposal,
            latest_compliance_score=snapshot.latest_compliance_score,
            latest_risk_score=snapshot.latest_risk_score,
            blocking_count=len(snapshot.blocking_items),
            open_question_count=len(snapshot.open_questions),
            rejected_count=len(snapshot.rejected_options),
            decision_count=len(snapshot.decision_log),
            reflection_count=len(snapshot.recent_reflections),
            evidence_ref_count=len(snapshot.latest_evidence_refs),
        )

    def list(self, limit: int = 20) -> list[CaseMemorySummaryPayload]:
        """List recently updated cases for frontend project switching."""
        snapshots: list[CaseMemoryPayload] = []
        for path in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                snapshots.append(CaseMemoryPayload.model_validate(data))
            except Exception as exc:
                logger.warning("Failed to read case memory summary %s: %s", path, exc)

        snapshots.sort(key=lambda item: item.updated_at, reverse=True)
        return [self.summarize(snapshot) for snapshot in snapshots[: max(1, int(limit))]]

    def delete(self, case_id: str) -> None:
        """Delete a persisted case snapshot."""
        path = self._path_for(case_id)
        if not path.exists():
            raise FileNotFoundError(f"Case memory not found: {case_id}")
        with self._lock:
            if not path.exists():
                raise FileNotFoundError(f"Case memory not found: {case_id}")
            path.unlink()

    def fingerprint(self, snapshot: CaseMemoryPayload | None) -> str:
        """Create a small signature so cache keys can track memory evolution."""
        if snapshot is None:
            return ""
        signature = {
            "case_id": snapshot.case_id,
            "updated_at": snapshot.updated_at.isoformat(),
            "status": snapshot.status,
            "selected_proposal": snapshot.selected_proposal,
            "decision_count": len(snapshot.decision_log),
            "rejected_count": len(snapshot.rejected_options),
            "blocking_count": len(snapshot.blocking_items),
            "reflection_count": len(snapshot.recent_reflections),
        }
        encoded = json.dumps(signature, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:24]

    def _path_for(self, case_id: str) -> Path:
        safe_case_id = "".join(ch for ch in case_id if ch.isalnum() or ch in {"-", "_"})
        if not safe_case_id:
            raise ValueError("Invalid case_id")
        return self.storage_dir / f"{safe_case_id}.json"
