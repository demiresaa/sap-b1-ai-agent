"""SAP error çevirisi testleri."""
from __future__ import annotations

import httpx

from app.sap.errors import SAPError, sap_error_from_response, translate_sap_error


def test_translate_known_code_returns_turkish() -> None:
    payload = {"error": {"code": "-1029", "message": {"value": "BP not found"}}}
    message, code = translate_sap_error(payload)
    assert "Müşteri" in message
    assert code == "-1029"


def test_translate_unknown_code_falls_back_to_raw() -> None:
    payload = {"error": {"code": "-9999", "message": {"value": "weird issue"}}}
    message, code = translate_sap_error(payload)
    assert "-9999" in message
    assert "weird issue" in message
    assert code == "-9999"


def test_translate_empty_payload() -> None:
    message, code = translate_sap_error(None)
    assert message
    assert code is None


def test_sap_error_from_response_uses_payload() -> None:
    payload = {"error": {"code": "-10", "message": {"value": "missing field"}}}
    resp = httpx.Response(400, json=payload)
    err = sap_error_from_response(resp)
    assert isinstance(err, SAPError)
    assert err.code == "-10"
    assert err.status_code == 400
    assert "Geçersiz veri" in err.message_tr


def test_sap_error_from_response_handles_non_json() -> None:
    resp = httpx.Response(503, text="<html>service unavailable</html>")
    err = sap_error_from_response(resp)
    assert err.status_code == 503
    assert "hizmet" in err.message_tr.lower() or "ulaşıl" in err.message_tr.lower()
