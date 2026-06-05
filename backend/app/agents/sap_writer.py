"""SAPWriter — onaylı belgeyi Service Layer'a yazar.

LLM kullanmaz; deterministik. Sorumlulukları:
  - Idempotency anahtarı kontrolü (Redis'te varsa eski sonuç döner)
  - Quotation veya Sales Order seçimi (`kind` parametresi)
  - SAP retry, transient hata yönetimi `client.py`'de zaten var
  - SAPError → Türkçe mesaj
  - Document_ApprovalRequests → SAP onay prosedürü algılama
"""
from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.sap import SAPError, pool
from app.sap.idempotency import IdempotencyStore, hash_payload, make_key
from app.sap.modules import QuotationsModule, SalesOrdersModule


class SAPWriterAgent(BaseAgent):
    name = "sap_writer"
    model = "n/a"

    async def _run(
        self,
        ctx: AgentContext,
        kind: str = "sales_order",
        payload: dict[str, Any] | None = None,
        idempotency_store: IdempotencyStore | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        if not payload:
            raise ValueError("payload zorunlu")
        if kind not in {"sales_order", "quotation"}:
            raise ValueError(f"Geçersiz kind: {kind}")

        operation = "order" if kind == "sales_order" else "quotation"
        source = ctx.metadata.get("idempotency_source") or hash_payload(payload)
        idem_key = make_key(operation, source)

        if idempotency_store is not None:
            cached = await idempotency_store.get(idem_key)
            if cached and cached != "__pending__":
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    confidence=1.0,
                    data={"sap": cached, "idempotency_hit": True, "idempotency_key": idem_key},
                )
            await idempotency_store.acquire(idem_key)

        try:
            async with pool.acquire() as client:
                module = (
                    SalesOrdersModule(client) if kind == "sales_order" else QuotationsModule(client)
                )
                response = await module.create(payload)
        except SAPError as exc:
            return AgentResult(
                agent_name=self.name,
                success=False,
                confidence=0.0,
                needs_human=True,
                human_reason="SAP yazımı başarısız",
                error=exc.message_tr,
                data={
                    "sap_code": exc.code,
                    "http_status": exc.status_code,
                    "idempotency_key": idem_key,
                },
            )

        # SAP onay prosedürü kontrolü (EnableApprovalProcedureInDI=tYES)
        # Belge oluştu ama onay bekliyorsa kullanıcıya bildir
        approval_requests = response.get("Document_ApprovalRequests") or []
        sap_approval_pending = bool(approval_requests)

        result_data: dict[str, Any] = {
            "sap_doc_entry": response.get("DocEntry"),
            "sap_doc_num": response.get("DocNum"),
            "kind": kind,
            "sap_approval_pending": sap_approval_pending,
        }
        if sap_approval_pending:
            result_data["sap_approval_requests"] = approval_requests

        if idempotency_store is not None:
            await idempotency_store.set(idem_key, result_data)

        if sap_approval_pending:
            return AgentResult(
                agent_name=self.name,
                success=True,
                confidence=1.0,
                needs_human=True,
                human_reason="Belge SAP onay prosedürüne girdi — yetkili onayına kadar beklemede",
                data={"sap": result_data, "idempotency_key": idem_key},
            )

        return AgentResult(
            agent_name=self.name,
            success=True,
            confidence=1.0,
            data={"sap": result_data, "idempotency_key": idem_key},
        )
