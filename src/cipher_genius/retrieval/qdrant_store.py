"""Reusable Qdrant store helpers for enterprise knowledge payloads."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

from qdrant_client import QdrantClient
from qdrant_client import models as qdrant_models


class QdrantKnowledgeStore:
    """Manage a Qdrant collection for retrieval knowledge payloads."""

    def __init__(
        self,
        client: QdrantClient,
        *,
        collection_name: str,
        vector_size: int = 1,
    ) -> None:
        self.client = client
        self.collection_name = collection_name
        self.vector_size = max(1, int(vector_size))

    def ensure_collection(self, *, recreate: bool = False) -> None:
        if recreate and self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)

        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=self.vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

    def upsert_payloads(self, payloads: Iterable[dict[str, Any]], *, batch_size: int = 64) -> int:
        items = [self.normalize_payload(payload) for payload in payloads if payload]
        if not items:
            return 0

        total = 0
        normalized_batch_size = max(1, int(batch_size))
        for start in range(0, len(items), normalized_batch_size):
            batch = items[start : start + normalized_batch_size]
            points = [self._build_point(payload) for payload in batch]
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
            total += len(batch)
        return total

    def count_by_request_id(self, request_id: str) -> int:
        normalized_request_id = str(request_id or "").strip()
        if not normalized_request_id or not self.client.collection_exists(self.collection_name):
            return 0

        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=self._request_filter(normalized_request_id),
            exact=True,
        )
        return int(getattr(result, "count", 0) or 0)

    def delete_by_request_id(self, request_id: str) -> int:
        normalized_request_id = str(request_id or "").strip()
        if not normalized_request_id or not self.client.collection_exists(self.collection_name):
            return 0

        total = self.count_by_request_id(normalized_request_id)
        if total <= 0:
            return 0

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=self._request_filter(normalized_request_id),
            wait=True,
        )
        return total

    def delete_by_chunk_ids(self, chunk_ids: Iterable[str]) -> int:
        normalized_chunk_ids = [str(item).strip() for item in chunk_ids if str(item).strip()]
        if not normalized_chunk_ids or not self.client.collection_exists(self.collection_name):
            return 0

        point_ids = [self._stable_int_id(chunk_id) for chunk_id in normalized_chunk_ids]
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=point_ids,
            wait=True,
        )
        return len(point_ids)

    def _build_point(self, payload: dict[str, Any]) -> qdrant_models.PointStruct:
        return qdrant_models.PointStruct(
            id=self._stable_int_id(self._identity_text(payload)),
            vector=self._default_vector(),
            payload=payload,
        )

    @staticmethod
    def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        metadata = dict(normalized.get("metadata") or {})

        region = str(normalized.get("region") or metadata.get("region") or "").strip().upper()
        normalized["region"] = region or "GLOBAL"

        scenario_value = normalized.get("scenario_tokens") or metadata.get("scenario") or []
        if isinstance(scenario_value, str):
            scenario_tokens = [scenario_value.strip().lower()] if scenario_value.strip() else []
        else:
            scenario_tokens = [str(item).strip().lower() for item in scenario_value if item]
        normalized["scenario_tokens"] = scenario_tokens or ["general"]

        tags_value = normalized.get("tags") or metadata.get("tags") or []
        normalized["tags"] = [str(item).strip() for item in tags_value if item]

        normalized["metadata"] = metadata
        return normalized

    def _default_vector(self) -> list[float]:
        return [0.0 for _ in range(self.vector_size)]

    def _identity_text(self, payload: dict[str, Any]) -> str:
        return str(
            payload.get("chunk_id")
            or payload.get("doc_id")
            or payload.get("title")
            or payload
        )

    @staticmethod
    def _request_filter(request_id: str) -> qdrant_models.Filter:
        return qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="request_id",
                    match=qdrant_models.MatchValue(value=request_id),
                )
            ]
        )

    def _stable_int_id(self, text: str) -> int:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        return int(digest, 16)
