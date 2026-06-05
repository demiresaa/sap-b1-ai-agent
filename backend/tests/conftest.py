"""Test ortamı için ortak fixture'lar."""
from __future__ import annotations

import os

# .env yüklenmesini bypass et — test sırasında gerçek SAP/credential olmamalı
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("SAP_SERVICE_LAYER_URL", "https://sap.test:50000/b1s/v1")
os.environ.setdefault("SAP_COMPANY_DB", "TESTDB")
os.environ.setdefault("SAP_USERNAME", "manager")
os.environ.setdefault("SAP_PASSWORD", "test")
os.environ.setdefault("SAP_VERIFY_SSL", "false")
os.environ.setdefault("OPENROUTER_API_KEY", "sk-or-test")


def _register_jsonb_for_sqlite() -> None:
    """SQLite üzerinde testleri çalıştırabilmek için JSONB → JSON map'le."""
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    def visit_JSONB(self, type_, **kw):  # noqa: N802
        return "JSON"

    SQLiteTypeCompiler.visit_JSONB = visit_JSONB  # type: ignore[attr-defined]


_register_jsonb_for_sqlite()
