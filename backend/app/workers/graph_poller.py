"""Microsoft Graph e-posta poller — OAuth2 client credentials ile posta kutusu okur.

IMAP poller'ın Microsoft 365 muadili. Okunmamış mesajları alır, izin verilen
türdeki ekleri belge olarak yükleyip işleme kuyruğuna ekler.

Konfigürasyon (.env):
  MS_GRAPH_ENABLED=true
  MS_TENANT_ID=<Azure AD tenant ID>
  MS_CLIENT_ID=<App registration client ID>
  MS_CLIENT_SECRET=<App registration secret>
  MS_GRAPH_MAILBOX=satis@firma.com

Azure AD app kaydında şu izinler zorunlu (Application türü):
  Mail.Read  —  posta kutusu okuma
"""
from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

import httpx
import msal

from app.core.config import settings
from app.db.models import DocumentSource
from app.db.session import SessionFactory
from app.services.documents import DuplicateDocument, upload_document
from app.workers.celery_app import celery_app
from app.workers.tasks import enqueue_process_document

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
ALLOWED_SUFFIXES = (".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg")

# Sayfa başına alınacak maksimum mesaj sayısı
_PAGE_SIZE = 20


def _get_access_token() -> str:
    """MSAL ConfidentialClientApplication ile client credentials token alır.

    Token MSAL cache'de tutulur; süresi dolmadıkça yeni istek yapılmaz.
    """
    app = msal.ConfidentialClientApplication(
        client_id=settings.ms_client_id,
        client_credential=settings.ms_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.ms_tenant_id}",
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "bilinmiyor"))
        raise RuntimeError(f"MS Graph token alınamadı: {error}")
    return result["access_token"]  # type: ignore[return-value]


@celery_app.task(name="app.workers.graph_poller.poll_graph_inbox")
def poll_graph_inbox() -> dict[str, Any]:
    """Periyodik Celery task — Graph API'den okunmamış mesajları çeker."""
    if not settings.ms_graph_enabled:
        logger.info("[graph_poller] MS_GRAPH_ENABLED=false, atlanıyor.")
        return {"skipped": True}
    if not all([settings.ms_tenant_id, settings.ms_client_id, settings.ms_client_secret,
                settings.ms_graph_mailbox]):
        logger.warning("[graph_poller] MS Graph konfigürasyonu eksik, atlanıyor.")
        return {"skipped": True, "reason": "config_missing"}
    return asyncio.run(_poll_async())


async def _poll_async() -> dict[str, Any]:
    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    processed = 0
    duplicates = 0
    errors = 0

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        messages = await _fetch_unread_messages(client)
        async with SessionFactory() as db:
            for msg in messages:
                r = await _ingest_message(db, client, msg)
                processed += r["created"]
                duplicates += r["duplicates"]
                errors += r["errors"]
                if r["created"] > 0:
                    await _mark_as_read(client, msg["id"])
            await db.commit()

    logger.info(
        "[graph_poller] tamamlandı: işlenen=%d tekrar=%d hata=%d",
        processed,
        duplicates,
        errors,
    )
    return {"processed": processed, "duplicates": duplicates, "errors": errors}


async def _fetch_unread_messages(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """Posta kutusundaki okunmamış mesajları sayfalayarak döner."""
    mailbox = settings.ms_graph_mailbox
    url = (
        f"{GRAPH_BASE}/users/{mailbox}/mailFolders/Inbox/messages"
        f"?$filter=isRead eq false"
        f"&$top={_PAGE_SIZE}"
        f"&$select=id,subject,from,hasAttachments,receivedDateTime"
    )
    messages: list[dict[str, Any]] = []
    while url:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        messages.extend(data.get("value", []))
        url = data.get("@odata.nextLink", "")
        if len(messages) >= _PAGE_SIZE * 5:
            # Maksimum 100 mesaj per çalışma — birikmiş büyük kutuları throttle eder
            break
    return messages


async def _ingest_message(
    db: Any,
    client: httpx.AsyncClient,
    msg: dict[str, Any],
) -> dict[str, int]:
    result = {"created": 0, "duplicates": 0, "errors": 0}
    if not msg.get("hasAttachments"):
        return result

    mailbox = settings.ms_graph_mailbox
    att_url = f"{GRAPH_BASE}/users/{mailbox}/messages/{msg['id']}/attachments"
    resp = await client.get(att_url)
    if resp.status_code != 200:
        logger.warning("[graph_poller] ek listesi alınamadı msg=%s", msg["id"])
        result["errors"] += 1
        return result

    from_addr = (msg.get("from") or {}).get("emailAddress", {}).get("address", "")
    subject = msg.get("subject", "")

    for att in resp.json().get("value", []):
        filename: str = att.get("name", "")
        if not filename.lower().endswith(ALLOWED_SUFFIXES):
            continue
        content_b64: str = att.get("contentBytes", "")
        if not content_b64:
            continue

        import base64
        raw_bytes = base64.b64decode(content_b64)
        content_type = att.get("contentType", "application/octet-stream")

        try:
            doc = await upload_document(
                db,
                io.BytesIO(raw_bytes),
                original_filename=filename,
                mime_type=content_type,
                uploaded_by_id=None,
                source=DocumentSource.EMAIL,
                source_email=from_addr,
                source_subject=subject,
            )
            await db.flush()
            enqueue_process_document(doc.id)
            result["created"] += 1
            logger.info("[graph_poller] belge yüklendi: %s (msg=%s)", filename, msg["id"])
        except DuplicateDocument:
            result["duplicates"] += 1
        except Exception as exc:
            logger.warning("[graph_poller] ek yüklenemedi %s: %s", filename, exc)
            result["errors"] += 1

    return result


async def _mark_as_read(client: httpx.AsyncClient, message_id: str) -> None:
    mailbox = settings.ms_graph_mailbox
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}"
    try:
        await client.patch(url, json={"isRead": True})
    except Exception as exc:
        logger.warning("[graph_poller] okundu işareti konamadı msg=%s: %s", message_id, exc)
