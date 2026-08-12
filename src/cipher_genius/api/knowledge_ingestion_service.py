"""API-facing service to ingest uploaded PDF/DOCX knowledge documents."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from fastapi import UploadFile
from qdrant_client import QdrantClient

from cipher_genius.api.schemas import (
    KnowledgeChunkPreviewPayload,
    KnowledgeDeleteResponse,
    KnowledgeIngestedFilePayload,
    KnowledgeIngestionListResponse,
    KnowledgeIngestionRecordPayload,
    KnowledgeIngestionResponse,
    KnowledgeQdrantDeleteResponse,
    KnowledgeQdrantReingestResponse,
)
from cipher_genius.ingestion import KnowledgeIngestionPipeline
from cipher_genius.ingestion.models import KnowledgeChunk
from cipher_genius.retrieval.qdrant_store import QdrantKnowledgeStore
from cipher_genius.utils.config import get_settings


@dataclass
class _StoredUpload:
    file_name: str
    stored_path: Path


class KnowledgeIngestionService:
    """Persist uploaded documents, chunk them, and optionally seed Qdrant."""

    SUPPORTED_SUFFIXES = {".pdf", ".docx"}
    REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")

    def __init__(self, project_root: str | Path | None = None) -> None:
        if project_root is None:
            project_root = Path(__file__).resolve().parents[3]
        self.project_root = Path(project_root)
        self.settings = get_settings()
        self.pipeline = KnowledgeIngestionPipeline()
        self.raw_root = self.project_root / "knowledge" / "raw" / "uploads"
        self.output_root = self.project_root / "knowledge" / "processed" / "chunks" / "uploads"
        self.manifest_path = self.output_root / "manifest.json"
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.output_root.mkdir(parents=True, exist_ok=True)

    async def ingest_uploads(
        self,
        *,
        files: Iterable[UploadFile],
        doc_type: str,
        metadata: dict | None = None,
        title: str | None = None,
        upsert_qdrant: bool = False,
    ) -> KnowledgeIngestionResponse:
        request_id = f"ingest-{uuid4().hex[:10]}"
        upload_dir = self.raw_root / request_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        normalized_metadata = dict(metadata or {})
        stored_uploads = await self._store_uploads(files, upload_dir)
        if not stored_uploads:
            raise ValueError("至少需要上传一个 PDF 或 DOCX 文件。")

        all_chunks: list[KnowledgeChunk] = []
        file_results: list[KnowledgeIngestedFilePayload] = []
        title_override = (title or "").strip() or None

        for index, item in enumerate(stored_uploads):
            parsed, chunks = self.pipeline.ingest_file(
                item.stored_path,
                doc_type=doc_type,
                metadata=normalized_metadata,
                title=title_override if len(stored_uploads) == 1 and index == 0 else None,
            )
            all_chunks.extend(chunks)
            file_results.append(
                KnowledgeIngestedFilePayload(
                    file_name=item.file_name,
                    stored_path=str(item.stored_path),
                    doc_id=parsed.doc_id,
                    title=parsed.title,
                    block_count=len(parsed.blocks),
                    chunk_count=len(chunks),
                    previews=[
                        KnowledgeChunkPreviewPayload(
                            chunk_id=chunk.chunk_id,
                            title=chunk.title,
                            section=chunk.section,
                            snippet=(chunk.citation_snippet or chunk.content[:160]).strip(),
                            source_page=chunk.source_page,
                        )
                        for chunk in chunks[:5]
                    ],
                )
            )

        output_path = self.output_root / f"{request_id}_{doc_type}.jsonl"
        self.pipeline.write_jsonl(all_chunks, output_path)

        qdrant_upserted = False
        qdrant_message = "未请求写入 Qdrant"
        if upsert_qdrant:
            qdrant_upserted, qdrant_message = self._try_upsert_qdrant(request_id=request_id, chunks=all_chunks)

        response = KnowledgeIngestionResponse(
            request_id=request_id,
            doc_type=doc_type,
            total_files=len(file_results),
            total_chunks=len(all_chunks),
            output_path=str(output_path),
            metadata=normalized_metadata,
            qdrant_requested=upsert_qdrant,
            qdrant_upserted=qdrant_upserted,
            qdrant_message=qdrant_message,
            files=file_results,
        )
        self._upsert_record(response)
        return response

    def list_ingestions(self, *, limit: int = 20) -> KnowledgeIngestionListResponse:
        records = self._load_records()
        records.sort(key=lambda item: item.created_at, reverse=True)
        return KnowledgeIngestionListResponse(total=len(records), items=records[:limit])

    def delete_ingestion_artifacts(self, request_id: str) -> KnowledgeDeleteResponse:
        normalized_request_id = self._normalize_request_id(request_id)
        deleted_paths: list[str] = []

        upload_dir = self.raw_root / normalized_request_id
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
            deleted_paths.append(str(upload_dir))

        for output_path in sorted(self.output_root.glob(f"{normalized_request_id}_*.jsonl")):
            output_path.unlink()
            deleted_paths.append(str(output_path))

        if not deleted_paths:
            raise FileNotFoundError(f"未找到 request_id={normalized_request_id} 对应的知识导入产物。")

        self._mark_record_deleted(normalized_request_id)
        return KnowledgeDeleteResponse(
            request_id=normalized_request_id,
            deleted=True,
            deleted_paths=deleted_paths,
            message="已删除本次知识导入产生的本地文件。如已写入 Qdrant，请后续通过知识库管理能力处理向量库副本。",
        )

    def delete_qdrant_artifacts(self, request_id: str) -> KnowledgeQdrantDeleteResponse:
        normalized_request_id = self._normalize_request_id(request_id)
        record = self._get_record(normalized_request_id)
        if record is None:
            raise FileNotFoundError(f"未找到 request_id={normalized_request_id} 对应的知识导入记录。")

        deleted_points = self._delete_qdrant_points(record)
        deleted_at = datetime.now(timezone.utc)
        if deleted_points > 0:
            message = f"已删除 Qdrant 副本：{deleted_points} 条知识块"
        else:
            message = "未找到可删除的 Qdrant 副本，已按已清理状态回写 manifest。"

        self._update_record(
            normalized_request_id,
            qdrant_upserted=False,
            qdrant_cleanup_required=False,
            qdrant_message=message,
            qdrant_deleted_at=deleted_at,
        )
        return KnowledgeQdrantDeleteResponse(
            request_id=normalized_request_id,
            deleted=True,
            deleted_points=deleted_points,
            qdrant_deleted_at=deleted_at,
            message=message,
        )

    def reingest_qdrant_artifacts(self, request_id: str) -> KnowledgeQdrantReingestResponse:
        normalized_request_id = self._normalize_request_id(request_id)
        record = self._get_record(normalized_request_id)
        if record is None:
            raise FileNotFoundError(f"未找到 request_id={normalized_request_id} 对应的知识导入记录。")

        output_path = Path(record.output_path or "")
        if not output_path.exists():
            raise ValueError("当前本地 JSONL 不存在，无法执行重入库。")

        payloads = self._load_qdrant_payloads_from_jsonl(output_path, request_id=normalized_request_id)
        if not payloads:
            raise ValueError("当前 JSONL 中没有可写入 Qdrant 的知识块。")

        upserted_points = self._upsert_qdrant_payloads(payloads)
        message = f"已重新写入 Qdrant：{upserted_points} 条知识块"
        self._update_record(
            normalized_request_id,
            qdrant_requested=True,
            qdrant_upserted=upserted_points > 0,
            qdrant_cleanup_required=upserted_points > 0,
            qdrant_message=message,
            qdrant_deleted_at=None,
        )
        return KnowledgeQdrantReingestResponse(
            request_id=normalized_request_id,
            reingested=True,
            upserted_points=upserted_points,
            message=message,
        )

    async def _store_uploads(self, files: Iterable[UploadFile], upload_dir: Path) -> list[_StoredUpload]:
        stored_uploads: list[_StoredUpload] = []
        for upload in files:
            file_name = Path(upload.filename or "").name
            suffix = Path(file_name).suffix.lower()
            if suffix not in self.SUPPORTED_SUFFIXES:
                raise ValueError(f"仅支持 PDF 或 DOCX 文件，当前文件：{file_name or 'unknown'}")

            safe_name = self._sanitize_file_name(file_name)
            target_path = upload_dir / safe_name
            content = await upload.read()
            if not content:
                raise ValueError(f"上传文件为空：{file_name}")
            target_path.write_bytes(content)
            stored_uploads.append(_StoredUpload(file_name=file_name or safe_name, stored_path=target_path))
        return stored_uploads

    def _try_upsert_qdrant(self, *, request_id: str, chunks: list[KnowledgeChunk]) -> tuple[bool, str]:
        try:
            count = self._upsert_qdrant_payloads(self._build_qdrant_payloads(request_id=request_id, chunks=chunks))
            return True, f"已写入 Qdrant：{count} 条知识块"
        except Exception as exc:
            return False, f"Qdrant 写入失败，已保留本地 JSONL：{exc}"

    def _load_records(self) -> list[KnowledgeIngestionRecordPayload]:
        if not self.manifest_path.exists():
            return []

        try:
            raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        if not isinstance(raw, list):
            return []

        records: list[KnowledgeIngestionRecordPayload] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                records.append(KnowledgeIngestionRecordPayload.model_validate(item))
            except Exception:
                continue
        return records

    def _save_records(self, records: list[KnowledgeIngestionRecordPayload]) -> None:
        payload = [item.model_dump(mode="json") for item in records]
        self.manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _upsert_record(self, response: KnowledgeIngestionResponse) -> None:
        records = self._load_records()
        next_record = KnowledgeIngestionRecordPayload(
            request_id=response.request_id,
            created_at=datetime.now(timezone.utc),
            deleted_at=None,
            qdrant_deleted_at=None,
            doc_type=response.doc_type,
            total_files=response.total_files,
            total_chunks=response.total_chunks,
            output_path=response.output_path,
            metadata=response.metadata,
            qdrant_requested=response.qdrant_requested,
            qdrant_upserted=response.qdrant_upserted,
            qdrant_message=response.qdrant_message,
            local_artifacts_present=True,
            qdrant_cleanup_required=bool(response.qdrant_upserted),
            files=response.files,
        )
        rest = [item for item in records if item.request_id != response.request_id]
        self._save_records([next_record, *rest])

    def _mark_record_deleted(self, request_id: str) -> None:
        self._update_record(
            request_id,
            local_artifacts_present=False,
            deleted_at=datetime.now(timezone.utc),
        )

    def _get_record(self, request_id: str) -> KnowledgeIngestionRecordPayload | None:
        records = self._load_records()
        for item in records:
            if item.request_id == request_id:
                return item
        return None

    def _update_record(self, request_id: str, **updates: object) -> None:
        records = self._load_records()
        if not records:
            return

        updated_records: list[KnowledgeIngestionRecordPayload] = []
        changed = False
        for item in records:
            if item.request_id == request_id:
                changed = True
                updated_records.append(item.model_copy(update=updates))
            else:
                updated_records.append(item)

        if changed:
            self._save_records(updated_records)

    def _delete_qdrant_points(self, record: KnowledgeIngestionRecordPayload) -> int:
        client = self._build_qdrant_client()
        if not client.collection_exists(self.settings.qdrant_collection_name):
            return 0

        store = QdrantKnowledgeStore(
            client,
            collection_name=self.settings.qdrant_collection_name,
        )

        deleted_by_request = store.delete_by_request_id(record.request_id)
        if deleted_by_request > 0:
            return deleted_by_request

        output_path = Path(record.output_path or "")
        if output_path.exists():
            chunk_ids = self._load_chunk_ids_from_jsonl(output_path)
            if chunk_ids:
                return store.delete_by_chunk_ids(chunk_ids)

        return 0

    def _upsert_qdrant_payloads(self, payloads: list[dict]) -> int:
        client = self._build_qdrant_client()
        store = QdrantKnowledgeStore(
            client,
            collection_name=self.settings.qdrant_collection_name,
        )
        store.ensure_collection(recreate=False)
        return store.upsert_payloads(payloads)

    def _build_qdrant_client(self) -> QdrantClient:
        return QdrantClient(
            host=self.settings.qdrant_host,
            port=self.settings.qdrant_port,
            timeout=5.0,
            check_compatibility=False,
        )

    @staticmethod
    def _load_chunk_ids_from_jsonl(path: Path) -> list[str]:
        chunk_ids: list[str] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                normalized = line.strip()
                if not normalized:
                    continue
                payload = json.loads(normalized)
                chunk_id = str(payload.get("chunk_id") or "").strip()
                if chunk_id:
                    chunk_ids.append(chunk_id)
        except Exception:
            return []
        return chunk_ids

    @staticmethod
    def _load_qdrant_payloads_from_jsonl(path: Path, *, request_id: str) -> list[dict]:
        payloads: list[dict] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                normalized = line.strip()
                if not normalized:
                    continue
                payload = json.loads(normalized)
                if not isinstance(payload, dict):
                    continue
                chunk_id = str(payload.get("chunk_id") or "").strip()
                if not chunk_id:
                    continue
                next_payload = dict(payload)
                next_payload["request_id"] = request_id
                payloads.append(next_payload)
        except Exception:
            return []
        return payloads

    @staticmethod
    def _build_qdrant_payloads(*, request_id: str, chunks: list[KnowledgeChunk]) -> list[dict]:
        payloads: list[dict] = []
        for chunk in chunks:
            payload = chunk.model_dump(mode="json")
            payload["request_id"] = request_id
            payloads.append(payload)
        return payloads

    @staticmethod
    def _sanitize_file_name(file_name: str) -> str:
        sanitized = "".join(ch for ch in file_name if ch.isalnum() or ch in {"-", "_", ".", " "}).strip()
        return sanitized or f"upload-{uuid4().hex[:8]}"

    @classmethod
    def _normalize_request_id(cls, request_id: str) -> str:
        normalized = str(request_id or "").strip()
        if not normalized:
            raise ValueError("request_id 不能为空。")
        if not cls.REQUEST_ID_PATTERN.fullmatch(normalized):
            raise ValueError("request_id 非法。")
        return normalized
