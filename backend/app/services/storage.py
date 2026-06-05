"""Belge storage backend'leri.

İki backend:
  - LocalStorage: dev/test default, disk üzerinde `{ROOT}/{yyyy}/{mm}/{dd}/{uuid}.{ext}`
  - S3Storage: prod (AWS S3) ve dev (MinIO). settings.storage_backend ile seçilir.

Dedup için SHA-256 hash hesaplanır. Path/key Postgres'te tutulur, binary tutulmaz.
Tenant izolasyonu için S3 key prefix: `tenant-{slug}/intake/{document_id}.{ext}`
(çağıran bu prefix'i kendisi verir; storage agnostic).
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import BinaryIO, Protocol, runtime_checkable

import boto3
from botocore.client import Config as BotoConfig

from app.core.config import settings
from app.db.base import new_uuid

DEFAULT_ROOT = pathlib.Path(os.environ.get("STORAGE_ROOT", ".storage"))


@dataclass(slots=True)
class StoredFile:
    storage_path: str  # local path veya S3 key
    file_hash: str
    size_bytes: int
    mime_type: str | None


@runtime_checkable
class Storage(Protocol):
    """Storage backend kontratı — backend-agnostic kullanım için."""

    def save_stream(
        self,
        stream: BinaryIO,
        original_filename: str | None,
        mime_type: str | None = None,
        *,
        key_prefix: str | None = None,
    ) -> StoredFile: ...

    def delete(self, storage_path: str) -> None: ...

    def open_read(self, storage_path: str) -> bytes: ...

    def signed_url(self, storage_path: str, *, expires_in: int | None = None) -> str | None: ...


class LocalStorage:
    def __init__(self, root: pathlib.Path | str | None = None) -> None:
        self.root = pathlib.Path(root) if root else DEFAULT_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def save_stream(
        self,
        stream: BinaryIO,
        original_filename: str | None,
        mime_type: str | None = None,
        *,
        key_prefix: str | None = None,
    ) -> StoredFile:
        now = datetime.now(timezone.utc)
        suffix = pathlib.Path(original_filename or "").suffix or ""
        prefix_parts = [p for p in (key_prefix or "").split("/") if p]
        dir_path = self.root.joinpath(
            *prefix_parts,
            f"{now.year:04d}",
            f"{now.month:02d}",
            f"{now.day:02d}",
        )
        dir_path.mkdir(parents=True, exist_ok=True)
        target = dir_path / f"{new_uuid()}{suffix}"
        sha = hashlib.sha256()
        size = 0
        with target.open("wb") as out:
            while chunk := stream.read(64 * 1024):
                sha.update(chunk)
                out.write(chunk)
                size += len(chunk)
        return StoredFile(
            storage_path=str(target.resolve()),
            file_hash=sha.hexdigest(),
            size_bytes=size,
            mime_type=mime_type,
        )

    def delete(self, storage_path: str) -> None:
        path = pathlib.Path(storage_path)
        if path.exists():
            path.unlink()

    def open_read(self, storage_path: str) -> bytes:
        return pathlib.Path(storage_path).read_bytes()

    def signed_url(self, storage_path: str, *, expires_in: int | None = None) -> str | None:
        # Local backend için signed URL yok; çağıran direkt dosya stream'i kullanır.
        return None

    def clear(self) -> None:
        """Sadece test ortamı için."""
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)


class S3Storage:
    """boto3 sync istemcisi. MinIO ve AWS S3 ile uyumlu (endpoint_url farkı)."""

    def __init__(
        self,
        *,
        bucket: str | None = None,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None,
    ) -> None:
        self.bucket = bucket or settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or settings.s3_endpoint_url or None,
            aws_access_key_id=access_key or settings.s3_access_key,
            aws_secret_access_key=secret_key or settings.s3_secret_key,
            region_name=region or settings.s3_region,
            config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except self._client.exceptions.ClientError:
            self._client.create_bucket(Bucket=self.bucket)

    def save_stream(
        self,
        stream: BinaryIO,
        original_filename: str | None,
        mime_type: str | None = None,
        *,
        key_prefix: str | None = None,
    ) -> StoredFile:
        now = datetime.now(timezone.utc)
        suffix = pathlib.Path(original_filename or "").suffix or ""
        prefix = (key_prefix or "intake").strip("/")
        key = (
            f"{prefix}/{now.year:04d}/{now.month:02d}/{now.day:02d}/{new_uuid()}{suffix}"
        )

        # SHA-256 hesaplamak için bellekte topluyoruz (intake max 25MB).
        data = stream.read()
        sha = hashlib.sha256(data).hexdigest()

        put_kwargs: dict[str, object] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": data,
            "Metadata": {"sha256": sha},
        }
        if mime_type:
            put_kwargs["ContentType"] = mime_type
        self._client.put_object(**put_kwargs)

        return StoredFile(
            storage_path=key,
            file_hash=sha,
            size_bytes=len(data),
            mime_type=mime_type,
        )

    def delete(self, storage_path: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=storage_path)

    def open_read(self, storage_path: str) -> bytes:
        resp = self._client.get_object(Bucket=self.bucket, Key=storage_path)
        return resp["Body"].read()

    def signed_url(self, storage_path: str, *, expires_in: int | None = None) -> str | None:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_path},
            ExpiresIn=expires_in or settings.s3_signed_url_expire_seconds,
        )


def _build_default_storage() -> Storage:
    backend = settings.storage_backend.lower()
    if backend in {"s3", "minio"}:
        return S3Storage()
    return LocalStorage()


storage: Storage = _build_default_storage()
