"""e-Fatura entegratör adapter (GİB UBL 2.1 TR profili).

Adapter pattern: Hangi entegratör kullanıldığına bakılmaksızın aynı arayüz.
Desteklenen sağlayıcılar: Logo (default), Foriba, İzibiz.

EINVOICE_PROVIDER = "logo" | "foriba" | "izibiz"
EINVOICE_API_KEY  = <entegratör API anahtarı>
EINVOICE_API_URL  = <entegratör endpoint>

Şimdilik: SAP fatura payload'unu UBL XML şemasına çevirir,
entegratöre POST eder ve UUID döner. Gerçek imzalama (HSM/NES)
entegratör tarafı sorumluluğundadır.
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EInvoiceError(Exception):
    """e-Fatura gönderimi başarısız."""


class BaseEInvoiceAdapter(ABC):
    """Tüm entegratör adapter'larının ortak arayüzü."""

    @abstractmethod
    async def send(self, invoice_payload: dict[str, Any]) -> str:
        """SAP fatura dict'ini entegratöre gönderir, UUID döner."""


class LogoAdapter(BaseEInvoiceAdapter):
    """Logo İbrahim Bey / Logo Entegrasyon adapter'ı."""

    async def send(self, invoice_payload: dict[str, Any]) -> str:
        xml = _build_ubl_xml(invoice_payload)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.einvoice_api_url}/send",
                content=xml,
                headers={
                    "Content-Type": "application/xml",
                    "Authorization": f"Bearer {settings.einvoice_api_key}",
                },
            )
        if resp.status_code >= 400:
            raise EInvoiceError(f"Logo entegratör hatası: {resp.status_code} {resp.text[:200]}")
        data = resp.json()
        inv_uuid = data.get("uuid") or data.get("UUID") or str(uuid.uuid4())
        logger.info("[einvoice] Logo gönderim başarılı uuid=%s", inv_uuid)
        return inv_uuid


class ForibaAdapter(BaseEInvoiceAdapter):
    """Foriba e-Fatura adapter'ı."""

    async def send(self, invoice_payload: dict[str, Any]) -> str:
        xml = _build_ubl_xml(invoice_payload)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.einvoice_api_url}/invoice/send",
                content=xml,
                headers={
                    "Content-Type": "text/xml",
                    "X-Api-Key": settings.einvoice_api_key,
                },
            )
        if resp.status_code >= 400:
            raise EInvoiceError(f"Foriba entegratör hatası: {resp.status_code} {resp.text[:200]}")
        data = resp.json()
        inv_uuid = data.get("invoiceUUID") or str(uuid.uuid4())
        logger.info("[einvoice] Foriba gönderim başarılı uuid=%s", inv_uuid)
        return inv_uuid


class IzibizAdapter(BaseEInvoiceAdapter):
    """İzibiz e-Fatura adapter'ı."""

    async def send(self, invoice_payload: dict[str, Any]) -> str:
        xml = _build_ubl_xml(invoice_payload)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.einvoice_api_url}/efatura/gonder",
                content=xml,
                headers={
                    "Content-Type": "application/xml",
                    "apikey": settings.einvoice_api_key,
                },
            )
        if resp.status_code >= 400:
            raise EInvoiceError(f"İzibiz hatası: {resp.status_code} {resp.text[:200]}")
        data = resp.json()
        inv_uuid = data.get("uuid") or str(uuid.uuid4())
        logger.info("[einvoice] İzibiz gönderim başarılı uuid=%s", inv_uuid)
        return inv_uuid


_ADAPTERS: dict[str, type[BaseEInvoiceAdapter]] = {
    "logo": LogoAdapter,
    "foriba": ForibaAdapter,
    "izibiz": IzibizAdapter,
}


def get_adapter() -> BaseEInvoiceAdapter:
    """Config'ten provider seçer, adapter örneği döner."""
    provider = settings.einvoice_provider.lower()
    cls = _ADAPTERS.get(provider)
    if cls is None:
        raise EInvoiceError(
            f"Bilinmeyen e-fatura sağlayıcı: {provider!r}. "
            f"Geçerli değerler: {list(_ADAPTERS)}"
        )
    return cls()


async def send_invoice(invoice_payload: dict[str, Any]) -> str:
    """SAP fatura payload'unu aktif adapter üzerinden gönderir.

    einvoice_enabled=False ise gönderim simüle edilir ve test UUID döner.
    """
    if not settings.einvoice_enabled:
        fake_uuid = str(uuid.uuid4())
        logger.info("[einvoice] disabled — simülasyon uuid=%s", fake_uuid)
        return fake_uuid
    adapter = get_adapter()
    return await adapter.send(invoice_payload)


def _build_ubl_xml(payload: dict[str, Any]) -> bytes:
    """SAP fatura dict'ini minimal UBL 2.1 XML'ine çevirir.

    Üretim ortamında bu şablon entegratör gereksinimine göre genişletilmeli.
    Zorunlu alanlar: CardCode, DocNum, DocDate, DocumentLines.
    """
    lines_xml = ""
    for i, line in enumerate(payload.get("DocumentLines", []), start=1):
        lines_xml += (
            f"<cac:InvoiceLine>"
            f"<cbc:ID>{i}</cbc:ID>"
            f'<cbc:InvoicedQuantity unitCode="EA">'
            f"{line.get('Quantity', 0)}</cbc:InvoicedQuantity>"
            f"<cac:Item><cbc:Name>{line.get('ItemDescription', '')}</cbc:Name></cac:Item>"
            f"</cac:InvoiceLine>"
        )

    xml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"'
        f' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'
        f' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">'
        f'<cbc:UBLVersionID>2.1</cbc:UBLVersionID>'
        f'<cbc:ID>{payload.get("DocNum", "")}</cbc:ID>'
        f'<cbc:IssueDate>{payload.get("DocDate", "")}</cbc:IssueDate>'
        f'<cbc:DocumentCurrencyCode>{payload.get("DocCurrency", "TRY")}</cbc:DocumentCurrencyCode>'
        f'<cac:AccountingCustomerParty>'
        f'<cac:Party><cbc:EndpointID>{payload.get("CardCode", "")}</cbc:EndpointID></cac:Party>'
        f'</cac:AccountingCustomerParty>'
        f'{lines_xml}'
        f'</Invoice>'
    )
    return xml.encode("utf-8")
