"""Upsert retrieval-ready JSONL knowledge chunks into Qdrant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qdrant_client import QdrantClient

from cipher_genius.ingestion.models import KnowledgeChunk
from cipher_genius.retrieval.qdrant_store import QdrantKnowledgeStore
from cipher_genius.utils.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upsert ingestion JSONL chunks into Qdrant.")
    parser.add_argument("--source", required=True, help="JSONL file or directory containing ingested chunks.")
    parser.add_argument("--collection", default="", help="Optional Qdrant collection override.")
    parser.add_argument("--host", default="", help="Optional Qdrant host override.")
    parser.add_argument("--port", type=int, default=0, help="Optional Qdrant port override.")
    parser.add_argument("--batch-size", type=int, default=64, help="Qdrant upsert batch size.")
    parser.add_argument("--recreate", action="store_true", help="Recreate collection before upsert.")
    return parser.parse_args()


def load_chunk_payloads(source: str | Path) -> list[dict]:
    path = Path(source)
    jsonl_files = [path] if path.is_file() else sorted(path.rglob("*.jsonl"))
    payloads: list[dict] = []
    for jsonl_path in jsonl_files:
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    chunk = KnowledgeChunk.model_validate(json.loads(line))
                except Exception as exc:
                    raise ValueError(f"Invalid chunk at {jsonl_path}:{line_number}: {exc}") from exc
                payloads.append(chunk.model_dump(mode="json"))
    return payloads


def main() -> int:
    args = parse_args()
    settings = get_settings()
    source = Path(args.source)
    payloads = load_chunk_payloads(source)
    if not payloads:
        print(f"No JSONL chunks found under {source}")
        return 1

    client = QdrantClient(
        host=args.host or settings.qdrant_host,
        port=args.port or settings.qdrant_port,
        timeout=5.0,
        check_compatibility=False,
    )
    store = QdrantKnowledgeStore(
        client,
        collection_name=args.collection or settings.qdrant_collection_name,
    )
    store.ensure_collection(recreate=args.recreate)
    total = store.upsert_payloads(payloads, batch_size=args.batch_size)
    print(
        f"Upserted {total} knowledge payloads into "
        f"{store.collection_name} from {source}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
