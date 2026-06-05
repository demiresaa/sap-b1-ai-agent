"""Yerel dosya storage'ı."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.services.storage import LocalStorage


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path)


def test_save_stream_writes_file_and_returns_hash(storage: LocalStorage) -> None:
    data = b"hello world" * 1000
    stored = storage.save_stream(io.BytesIO(data), "ornek.pdf", "application/pdf")

    assert Path(stored.storage_path).exists()
    assert Path(stored.storage_path).read_bytes() == data
    assert stored.size_bytes == len(data)
    assert len(stored.file_hash) == 64  # sha256 hex


def test_same_content_produces_same_hash(storage: LocalStorage) -> None:
    data = b"belge icerigi"
    h1 = storage.save_stream(io.BytesIO(data), "a.pdf", "application/pdf").file_hash
    h2 = storage.save_stream(io.BytesIO(data), "b.pdf", "application/pdf").file_hash
    assert h1 == h2


def test_delete_removes_file(storage: LocalStorage) -> None:
    stored = storage.save_stream(io.BytesIO(b"x"), "x.pdf", "application/pdf")
    storage.delete(stored.storage_path)
    assert not Path(stored.storage_path).exists()
