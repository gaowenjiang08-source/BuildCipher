"""Ingest PDF/Word enterprise documents into retrieval-ready JSONL chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cipher_genius.ingestion import KnowledgeIngestionPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest PDF/Word documents into knowledge chunks.")
    parser.add_argument("--source", required=True, help="Source file or directory containing PDF/Word documents.")
    parser.add_argument("--doc-type", required=True, help="Knowledge doc_type, e.g. standard / policy / case.")
    parser.add_argument("--output", required=True, help="Output JSONL path.")
    parser.add_argument("--title", default="", help="Optional title override for single-file ingestion.")
    parser.add_argument("--metadata", default="{}", help="Optional JSON metadata to attach to every chunk.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source)
    metadata = json.loads(args.metadata or "{}")
    pipeline = KnowledgeIngestionPipeline()

    if source.is_dir():
        chunks = pipeline.ingest_directory(source, doc_type=args.doc_type, metadata=metadata)
    else:
        _, chunks = pipeline.ingest_file(
            source,
            doc_type=args.doc_type,
            metadata=metadata,
            title=args.title or None,
        )

    output_path = pipeline.write_jsonl(chunks, args.output)
    print(f"Ingested {len(chunks)} chunks -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
