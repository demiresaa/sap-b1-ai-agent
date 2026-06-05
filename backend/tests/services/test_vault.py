"""Vault istemcisi — disabled fallback ve cache davranışı."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core import vault as vault_module
from app.core.vault import VaultClient, VaultUnavailable


def test_disabled_vault_raises_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vault_module.settings, "vault_enabled", False)
    client = VaultClient()
    with pytest.raises(VaultUnavailable):
        client.get_secret("tenants/elekon/sap")


def test_enabled_vault_reads_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vault_module.settings, "vault_enabled", True)
    monkeypatch.setattr(vault_module.settings, "vault_token", "dev-token")
    monkeypatch.setattr(vault_module.settings, "vault_secret_cache_ttl_seconds", 300)

    fake_response = {
        "data": {"data": {"username": "manager", "password": "NyNl.2021"}}
    }
    fake_hvac = MagicMock()
    fake_hvac.secrets.kv.v2.read_secret_version.return_value = fake_response

    client = VaultClient()
    with patch.object(client, "_get_client", return_value=fake_hvac):
        data = client.get_secret("tenants/elekon/sap")
        # ikinci çağrı cache'den dönmeli — read_secret_version sadece 1 kez çağrılır
        data2 = client.get_secret("tenants/elekon/sap")

    assert data == {"username": "manager", "password": "NyNl.2021"}
    assert data2 == data
    assert fake_hvac.secrets.kv.v2.read_secret_version.call_count == 1


def test_tenant_sap_credentials_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vault_module.settings, "vault_enabled", False)
    monkeypatch.setattr(vault_module.settings, "sap_username", "env_user")
    monkeypatch.setattr(vault_module.settings, "sap_password", "env_pass")
    monkeypatch.setattr(vault_module.settings, "sap_company_db", "env_db")
    monkeypatch.setattr(vault_module.settings, "sap_service_layer_url", "https://env/b1s/v1")

    creds = vault_module.get_tenant_sap_credentials("any-tenant")
    assert creds["username"] == "env_user"
    assert creds["password"] == "env_pass"
    assert creds["company_db"] == "env_db"
    assert creds["sl_base_url"] == "https://env/b1s/v1"
