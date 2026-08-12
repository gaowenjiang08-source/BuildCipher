"""Unit tests for reusable Qdrant knowledge store helpers."""

from cipher_genius.retrieval.qdrant_store import QdrantKnowledgeStore


class _FakeQdrantClient:
    def __init__(self) -> None:
        self.collections: set[str] = set()
        self.created: list[str] = []
        self.deleted: list[str] = []
        self.upserts: list[tuple[str, list]] = []
        self.payloads_by_collection: dict[str, list] = {}
        self.deleted_selectors: list[tuple[str, object]] = []

    def collection_exists(self, name: str) -> bool:
        return name in self.collections

    def create_collection(self, collection_name: str, vectors_config) -> None:
        self.collections.add(collection_name)
        self.created.append(collection_name)

    def delete_collection(self, collection_name: str) -> None:
        self.collections.discard(collection_name)
        self.deleted.append(collection_name)

    def upsert(self, collection_name: str, points, wait: bool = True) -> None:
        self.upserts.append((collection_name, list(points)))
        self.payloads_by_collection.setdefault(collection_name, []).extend(list(points))

    def count(self, collection_name: str, count_filter=None, exact: bool = True):
        payloads = self.payloads_by_collection.get(collection_name, [])
        request_id = None
        if count_filter and getattr(count_filter, "must", None):
            request_id = getattr(getattr(count_filter.must[0], "match", None), "value", None)
        count = len([point for point in payloads if point.payload.get("request_id") == request_id])
        return type("CountResult", (), {"count": count})()

    def delete(self, collection_name: str, points_selector, wait: bool = True) -> None:
        self.deleted_selectors.append((collection_name, points_selector))
        payloads = self.payloads_by_collection.get(collection_name, [])
        if isinstance(points_selector, list):
            ids = set(points_selector)
            self.payloads_by_collection[collection_name] = [point for point in payloads if point.id not in ids]
            return

        request_id = None
        if getattr(points_selector, "must", None):
            request_id = getattr(getattr(points_selector.must[0], "match", None), "value", None)
        self.payloads_by_collection[collection_name] = [
            point for point in payloads if point.payload.get("request_id") != request_id
        ]


def test_qdrant_store_creates_and_recreates_collection():
    client = _FakeQdrantClient()
    store = QdrantKnowledgeStore(client, collection_name="crypto_knowledge")

    store.ensure_collection()
    assert client.created == ["crypto_knowledge"]

    store.ensure_collection(recreate=True)
    assert client.deleted == ["crypto_knowledge"]
    assert client.created == ["crypto_knowledge", "crypto_knowledge"]


def test_qdrant_store_upserts_payloads_in_batches():
    client = _FakeQdrantClient()
    store = QdrantKnowledgeStore(client, collection_name="crypto_knowledge")
    client.collections.add("crypto_knowledge")

    total = store.upsert_payloads(
        [
            {"chunk_id": "chunk-1", "title": "A"},
            {"chunk_id": "chunk-2", "title": "B"},
            {"chunk_id": "chunk-3", "title": "C"},
        ],
        batch_size=2,
    )

    assert total == 3
    assert len(client.upserts) == 2
    first_batch = client.upserts[0][1]
    assert first_batch[0].payload["chunk_id"] == "chunk-1"
    assert first_batch[0].vector == [0.0]


def test_qdrant_store_normalizes_filter_fields():
    payload = QdrantKnowledgeStore.normalize_payload(
        {
            "chunk_id": "chunk-1",
            "doc_type": "standard",
            "metadata": {
                "region": "cn",
                "scenario": ["bim_delivery", "construction_cde"],
                "tags": ["静态加密", "审计"],
            },
        }
    )

    assert payload["region"] == "CN"
    assert payload["scenario_tokens"] == ["bim_delivery", "construction_cde"]
    assert payload["tags"] == ["静态加密", "审计"]


def test_qdrant_store_counts_and_deletes_by_request_id():
    client = _FakeQdrantClient()
    store = QdrantKnowledgeStore(client, collection_name="crypto_knowledge")
    client.collections.add("crypto_knowledge")

    store.upsert_payloads(
        [
            {"chunk_id": "chunk-1", "request_id": "ingest-a", "title": "A"},
            {"chunk_id": "chunk-2", "request_id": "ingest-a", "title": "B"},
            {"chunk_id": "chunk-3", "request_id": "ingest-b", "title": "C"},
        ]
    )

    assert store.count_by_request_id("ingest-a") == 2
    assert store.delete_by_request_id("ingest-a") == 2
    assert store.count_by_request_id("ingest-a") == 0
    assert store.count_by_request_id("ingest-b") == 1


def test_qdrant_store_deletes_by_chunk_ids():
    client = _FakeQdrantClient()
    store = QdrantKnowledgeStore(client, collection_name="crypto_knowledge")
    client.collections.add("crypto_knowledge")

    store.upsert_payloads(
        [
            {"chunk_id": "chunk-1", "title": "A"},
            {"chunk_id": "chunk-2", "title": "B"},
        ]
    )

    deleted = store.delete_by_chunk_ids(["chunk-1"])
    assert deleted == 1
    remaining_ids = [point.payload["chunk_id"] for point in client.payloads_by_collection["crypto_knowledge"]]
    assert remaining_ids == ["chunk-2"]
