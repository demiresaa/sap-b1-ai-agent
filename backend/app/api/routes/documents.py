"""Document endpoint'leri — upload, list, detail, process, submit, PDF, kabul."""
from __future__ import annotations

import io
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.db.base import new_uuid, utcnow
from app.db.models import (
    Document,
    DocumentEvent,
    DocumentStatus,
    ExtractedData,
    QuotationPdf,
    Tenant,
)
from app.schemas.document import (
    ConvertToOrderResponse,
    DocumentDetail,
    DocumentOut,
    DocumentPatch,
    ExtractedDataOut,
    SubmitResponse,
)
from app.services.documents import DuplicateDocument, upload_document
from app.services.quotation_pdf import TenantInfo, render_quotation_pdf
from app.services.storage import storage
from app.workers.tasks import enqueue_process_document, enqueue_submit_document

router = APIRouter(tags=["documents"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_MIMETYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
}


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload(
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
    file: UploadFile = File(...),
) -> DocumentOut:
    if file.content_type and file.content_type not in ALLOWED_MIMETYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Desteklenmeyen dosya tipi: {file.content_type}",
        )
    try:
        doc = await upload_document(
            db,
            file.file,
            original_filename=file.filename,
            mime_type=file.content_type,
            uploaded_by_id=user.id,
        )
    except DuplicateDocument as dup:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Bu dosya zaten yüklenmiş ({dup.existing.id}).")

    if doc.file_size_bytes and doc.file_size_bytes > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Dosya boyutu 25 MB üstü.")

    # NOT: AI otomatik tetiklenmez. Kullanıcı listeden "AI ile Teklif Hazırla"
    # butonuyla manuel olarak /process endpoint'ini çağırır. Bu, gereksiz LLM
    # maliyetini ve "boş ekran"da işlenme belirsizliğini önler.
    return DocumentOut.model_validate(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    user: CurrentUser,
    db: DbSession,
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> list[DocumentOut]:
    stmt = select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
    if status_filter:
        stmt = stmt.where(Document.status == status_filter)
    result = await db.execute(stmt)
    return [DocumentOut.model_validate(d) for d in result.scalars().all()]


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: str, user: CurrentUser, db: DbSession) -> DocumentDetail:
    stmt = (
        select(Document)
        .options(selectinload(Document.extracted))
        .where(Document.id == document_id)
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Belge bulunamadı.")
    payload = DocumentDetail.model_validate(doc)
    if doc.extracted:
        payload.extracted = ExtractedDataOut(
            version=doc.extracted.version,
            payload=doc.extracted.payload,
            confidence=doc.extracted.confidence,
        )
    return payload


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str, user: CurrentUser, db: DbSession
) -> None:
    """Belgeyi DB'den ve storage'tan tamamen siler.

    İlişkili tüm satırlar (extracted_data, events, sap_submissions, agent_runs,
    quotation_pdfs) FK CASCADE ile otomatik temizlenir.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Belge bulunamadı.")

    storage_path = doc.storage_path
    await db.delete(doc)
    await db.commit()

    if storage_path:
        try:
            storage.delete(storage_path)
        except FileNotFoundError:
            pass


@router.patch("/{document_id}", response_model=DocumentDetail)
async def update_extracted_data(
    document_id: str, patch: DocumentPatch, user: CurrentUser, db: DbSession
) -> DocumentDetail:
    stmt = (
        select(Document)
        .options(selectinload(Document.extracted))
        .where(Document.id == document_id)
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Belge bulunamadı.")
    if doc.status in (DocumentStatus.SUBMITTED, DocumentStatus.SUBMITTING):
        raise HTTPException(status.HTTP_409_CONFLICT, "SAP'a gönderilmiş belge düzenlenemez.")

    if doc.extracted is None:
        doc.extracted = ExtractedData(
            document_id=doc.id, version=1, payload=patch.payload, confidence=None
        )
    else:
        doc.extracted.version += 1
        doc.extracted.payload = patch.payload

    db.add(
        DocumentEvent(
            document_id=doc.id,
            actor_id=user.id,
            event_type="extracted_updated",
            payload={"version": doc.extracted.version},
            created_at=utcnow(),
        )
    )

    payload = DocumentDetail.model_validate(doc)
    payload.extracted = ExtractedDataOut(
        version=doc.extracted.version,
        payload=doc.extracted.payload,
        confidence=doc.extracted.confidence,
    )
    return payload


@router.post("/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
async def trigger_processing(
    document_id: str,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> dict[str, str]:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Belge bulunamadı.")
    # Status'u hemen READING yap ve commit et — frontend polling'i hemen başlatır
    doc.status = DocumentStatus.READING
    db.add(DocumentEvent(
        document_id=doc.id,
        actor_id=user.id,
        event_type="process_queued",
        payload={},
        created_at=utcnow(),
    ))
    await db.commit()
    background.add_task(enqueue_process_document, doc.id)
    return {"status": "queued", "document_id": doc.id}


@router.post("/{document_id}/submit", response_model=SubmitResponse)
async def submit_to_sap(
    document_id: str,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> SubmitResponse:
    from sqlalchemy.orm import selectinload

    from app.core.config import settings
    from app.db.base import new_uuid, utcnow
    from app.db.models import DocumentEvent, SAPSubmission
    from app.workers.tasks import _build_sap_payload, _endpoint_for

    stmt = (
        select(Document)
        .options(selectinload(Document.extracted))
        .where(Document.id == document_id)
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Belge bulunamadı.")
    SUBMITTABLE = {
        DocumentStatus.READY,
        DocumentStatus.PDF_GENERATED,
        DocumentStatus.CUSTOMER_ACCEPTED,
        DocumentStatus.EDITED_AFTER_ACCEPTANCE,
    }
    if doc.status not in SUBMITTABLE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Belge gönderim için hazır değil (durum: {doc.status.value}). "
            "AI işleminin tamamlanmış ve en az bir satır bulunması gerekir.",
        )
    if not doc.extracted:
        raise HTTPException(status.HTTP_409_CONFLICT, "Çıkarılmış veri yok, önce AI çalıştırın.")

    payload = _build_sap_payload(doc.extracted.payload, doc.kind)
    endpoint = _endpoint_for(doc.kind)

    # Dry-run karar: tenant.sap_dry_run > settings.sap_dry_run (tenant context resolve edilebiliyorsa)
    dry_run_flag = settings.sap_dry_run
    try:
        from app.core.tenant_context import current_tenant
        from app.db.models.tenant import Tenant

        ctx = current_tenant()
        if ctx and ctx.slug:
            t = await db.execute(select(Tenant).where(Tenant.slug == ctx.slug))
            t_row = t.scalar_one_or_none()
            if t_row is not None:
                dry_run_flag = t_row.sap_dry_run
    except Exception:
        # Tenant resolve edilemezse global setting fallback
        pass

    # Dry-run: SAP'a YAZMA, payload'ı kayıt + response olarak döner
    if dry_run_flag:
        submission = SAPSubmission(
            document_id=doc.id,
            idempotency_key=f"dryrun:{doc.id}:{new_uuid()}",
            target_endpoint=endpoint,
            request_payload=payload,
            response_payload={"dry_run": True, "message": "SAP_DRY_RUN aktif, gerçek yazım yapılmadı."},
            http_status=200,
            attempt=1,
        )
        db.add(submission)
        doc.status = DocumentStatus.SUBMITTED
        db.add(
            DocumentEvent(
                document_id=doc.id,
                actor_id=user.id,
                event_type="sap_dry_run",
                payload={"endpoint": endpoint, "payload": payload},
                created_at=utcnow(),
            )
        )
        await db.flush()
        return SubmitResponse(
            submission_id=submission.id,
            dry_run=True,
            sap_endpoint=endpoint,
            sap_payload=payload,
            message=(
                f"DRY-RUN: SAP'a yazılmadı. Aşağıdaki JSON {endpoint} endpoint'ine "
                f"POST edilecekti."
            ),
        )

    # Gerçek mod — eski akış (Celery / inline)
    submission_id = await enqueue_submit_document(db, doc, actor_id=user.id)
    return SubmitResponse(
        submission_id=submission_id,
        sap_endpoint=endpoint,
        sap_payload=payload,
        message="SAP'a gönderildi, sonuç işleniyor.",
    )


@router.post("/{document_id}/generate-pdf")
async def generate_quotation_pdf(
    document_id: str,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, object]:
    """Bizim ürettiğimiz teklif PDF'ini render edip S3'e kaydeder, versiyon döner."""
    stmt = (
        select(Document)
        .options(selectinload(Document.extracted))
        .where(Document.id == document_id)
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Belge bulunamadı.")
    if not doc.extracted or not doc.extracted.payload:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Çıkarılmış veri yok, önce AI çalıştırın."
        )

    # Tenant info — kullanıcının tenant'ı veya fallback
    tenant_name = "SAP B1 AI Agent"
    tenant_slug = "default"
    template_name = "default"
    if user.tenant_id:
        t = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        t_row = t.scalar_one_or_none()
        if t_row is not None:
            tenant_name = t_row.name
            tenant_slug = t_row.slug
            template_name = t_row.default_pdf_template

    pdf_bytes = render_quotation_pdf(
        doc.extracted.payload,
        tenant=TenantInfo(name=tenant_name, slug=tenant_slug),
        template_name=template_name,
    )

    # Storage'a yaz — tenant prefix'li
    stored = storage.save_stream(
        io.BytesIO(pdf_bytes),
        original_filename=f"teklif-{doc.id[:8]}.pdf",
        mime_type="application/pdf",
        key_prefix=f"tenant-{tenant_slug}/quotations",
    )

    # Versiyon belirle — eş zamanlı isteklerde çakışmayı önlemek için lock
    existing_versions = await db.execute(
        select(QuotationPdf.version)
        .where(QuotationPdf.document_id == doc.id)
        .order_by(desc(QuotationPdf.version))
        .limit(1)
        .with_for_update()
    )
    last_version = existing_versions.scalar_one_or_none() or 0
    next_version = last_version + 1

    pdf_row = QuotationPdf(
        id=new_uuid(),
        document_id=doc.id,
        version=next_version,
        storage_path=stored.storage_path,
        size_bytes=stored.size_bytes,
        template_name=template_name,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(pdf_row)

    if doc.status == DocumentStatus.READY:
        doc.status = DocumentStatus.PDF_GENERATED

    db.add(
        DocumentEvent(
            document_id=doc.id,
            actor_id=user.id,
            event_type="quotation_pdf_generated",
            payload={"version": next_version, "size_bytes": stored.size_bytes},
            created_at=utcnow(),
        )
    )
    await db.flush()

    return {
        "id": pdf_row.id,
        "document_id": doc.id,
        "version": next_version,
        "size_bytes": stored.size_bytes,
        "download_url": f"/api/documents/{doc.id}/quotation.pdf",
    }


@router.get("/{document_id}/quotation.pdf")
async def download_quotation_pdf(
    document_id: str,
    user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    """En son üretilmiş teklif PDF'ini stream eder."""
    result = await db.execute(
        select(QuotationPdf)
        .where(QuotationPdf.document_id == document_id)
        .order_by(desc(QuotationPdf.version))
        .limit(1)
    )
    pdf = result.scalar_one_or_none()
    if not pdf:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Bu belge için henüz teklif PDF'i üretilmemiş."
        )

    data = storage.open_read(pdf.storage_path)
    pdf.downloaded_at = datetime.now(timezone.utc)
    await db.flush()

    headers = {
        "Content-Disposition": f'attachment; filename="teklif-{document_id[:8]}-v{pdf.version}.pdf"'
    }
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers=headers)


@router.post("/{document_id}/customer-accepted")
async def mark_customer_accepted(
    document_id: str, user: CurrentUser, db: DbSession
) -> dict[str, str]:
    doc = await _get_doc_or_404(db, document_id)
    if doc.status not in (
        DocumentStatus.PDF_GENERATED,
        DocumentStatus.EDITED_AFTER_ACCEPTANCE,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Müşteri kabulü için önce PDF üretmeniz gerekir.",
        )
    doc.status = DocumentStatus.CUSTOMER_ACCEPTED
    db.add(
        DocumentEvent(
            document_id=doc.id,
            actor_id=user.id,
            event_type="customer_accepted",
            payload={},
            created_at=utcnow(),
        )
    )
    return {"status": doc.status.value, "document_id": doc.id}


@router.post("/{document_id}/customer-rejected")
async def mark_customer_rejected(
    document_id: str, user: CurrentUser, db: DbSession, reason: str | None = None
) -> dict[str, str]:
    doc = await _get_doc_or_404(db, document_id)
    if doc.status not in (
        DocumentStatus.PDF_GENERATED,
        DocumentStatus.EDITED_AFTER_ACCEPTANCE,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Bu durumda red işlemi yapılamaz."
        )
    doc.status = DocumentStatus.CUSTOMER_REJECTED
    db.add(
        DocumentEvent(
            document_id=doc.id,
            actor_id=user.id,
            event_type="customer_rejected",
            payload={"reason": reason} if reason else {},
            created_at=utcnow(),
        )
    )
    return {"status": doc.status.value, "document_id": doc.id}


@router.post("/{document_id}/convert-to-order", response_model=ConvertToOrderResponse)
async def convert_to_order(
    document_id: str,
    user: CurrentUser,
    db: DbSession,
) -> ConvertToOrderResponse:
    """Müşteri kabul ettiği teklifi SAP Sales Order'a dönüştürür (BaseType=23)."""
    from app.core.config import settings
    from app.db.models import DocumentKind, SAPSubmission
    from app.sap import SAPError, pool
    from app.sap.modules.sales_orders import SalesOrdersModule

    doc = await _get_doc_or_404(db, document_id)

    if doc.kind != DocumentKind.QUOTATION:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Sadece teklif belgeleri (kind=quotation) siparişe dönüştürülebilir.",
        )
    if doc.status not in (
        DocumentStatus.CUSTOMER_ACCEPTED,
        DocumentStatus.CONVERTING_TO_ORDER,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Sipariş dönüşümü için belge 'Müşteri Kabul Etti' durumunda olmalı (şu an: {doc.status.value}).",
        )

    # Quotation'ın SAP submission kaydını bul
    q_sub_result = await db.execute(
        select(SAPSubmission)
        .where(SAPSubmission.document_id == document_id)
        .where(SAPSubmission.target_endpoint == "/Quotations")
        .order_by(SAPSubmission.created_at.desc())
        .limit(1)
    )
    quotation_sub = q_sub_result.scalar_one_or_none()
    if not quotation_sub or not quotation_sub.sap_doc_entry:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Teklif henüz SAP'a gönderilmemiş. Önce 'SAP'a Gönder' işlemini yapın.",
        )

    # Idempotency: zaten dönüştürülmüş mü?
    ord_sub_result = await db.execute(
        select(SAPSubmission)
        .where(SAPSubmission.document_id == document_id)
        .where(SAPSubmission.target_endpoint == "/Orders")
        .order_by(SAPSubmission.created_at.desc())
        .limit(1)
    )
    existing_order_sub = ord_sub_result.scalar_one_or_none()
    if existing_order_sub and existing_order_sub.sap_doc_entry:
        return ConvertToOrderResponse(
            order_doc_entry=existing_order_sub.sap_doc_entry,
            order_doc_num=existing_order_sub.sap_doc_num,
            dry_run=existing_order_sub.response_payload.get("dry_run", False)
            if existing_order_sub.response_payload
            else False,
            message="Sipariş zaten oluşturulmuştu.",
        )

    # Dönüşüm başlıyor
    doc.status = DocumentStatus.CONVERTING_TO_ORDER
    await db.flush()

    # Dry-run kararı
    dry_run_flag = settings.sap_dry_run
    try:
        from app.core.tenant_context import current_tenant
        from app.db.models.tenant import Tenant

        ctx = current_tenant()
        if ctx and ctx.slug:
            t = await db.execute(select(Tenant).where(Tenant.slug == ctx.slug))
            t_row = t.scalar_one_or_none()
            if t_row is not None:
                dry_run_flag = t_row.sap_dry_run
    except Exception:
        pass

    idempotency_key = f"order-conv:{document_id}"

    if dry_run_flag:
        mock_entry = 99000 + (abs(hash(document_id)) % 1000)
        order_sub = SAPSubmission(
            document_id=document_id,
            idempotency_key=idempotency_key,
            target_endpoint="/Orders",
            request_payload={
                "dry_run": True,
                "quotation_doc_entry": quotation_sub.sap_doc_entry,
            },
            response_payload={"dry_run": True, "DocEntry": mock_entry, "DocNum": mock_entry},
            sap_doc_entry=mock_entry,
            sap_doc_num=mock_entry,
            http_status=200,
            attempt=1,
            parent_submission_id=quotation_sub.id,
        )
        result_entry = mock_entry
        result_num = mock_entry
        message = "[Dry-run] Sipariş simüle edildi. Gerçek SAP yazımı yapılmadı."
    else:
        try:
            async with pool.acquire() as client:
                so_module = SalesOrdersModule(client)
                response = await so_module.create_from_quotation(
                    quotation_sub.sap_doc_entry
                )
        except SAPError as exc:
            doc.status = DocumentStatus.CUSTOMER_ACCEPTED
            await db.flush()
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, exc.message_tr) from exc

        result_entry = response["DocEntry"]
        result_num = response.get("DocNum")
        order_sub = SAPSubmission(
            document_id=document_id,
            idempotency_key=idempotency_key,
            target_endpoint="/Orders",
            request_payload={"quotation_doc_entry": quotation_sub.sap_doc_entry},
            response_payload=response,
            sap_doc_entry=result_entry,
            sap_doc_num=result_num,
            http_status=201,
            attempt=1,
            parent_submission_id=quotation_sub.id,
        )
        message = f"Sipariş SAP'a kaydedildi (DocEntry: {result_entry})."

    db.add(order_sub)
    doc.status = DocumentStatus.ORDER_SUBMITTED
    db.add(
        DocumentEvent(
            document_id=doc.id,
            actor_id=user.id,
            event_type="order_submitted",
            payload={
                "order_doc_entry": result_entry,
                "order_doc_num": result_num,
                "quotation_doc_entry": quotation_sub.sap_doc_entry,
                "dry_run": dry_run_flag,
            },
            created_at=utcnow(),
        )
    )
    await db.flush()

    return ConvertToOrderResponse(
        order_doc_entry=result_entry,
        order_doc_num=result_num,
        dry_run=dry_run_flag,
        message=message,
    )


async def _get_doc_or_404(db, document_id: str) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Belge bulunamadı.")
    return doc
