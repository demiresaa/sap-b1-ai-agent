"""Tüm SQLAlchemy modelleri — Alembic autogenerate buradan tarar."""
from app.db.models.agent import AgentRun, AgentStep, LLMCall
from app.db.models.audit import AuditLog
from app.db.models.document import (
    Document,
    DocumentEvent,
    DocumentKind,
    DocumentSource,
    DocumentStatus,
    ExtractedData,
    SAPSubmission,
)
from app.db.models.sap_cache import (
    BusinessPartnerCache,
    CustomerAlias,
    ItemCache,
    ItemEmbedding,
)
from app.db.models.quotation_pdf import QuotationPdf
from app.db.models.tenant import Tenant
from app.db.models.tenant_schema import TenantMasterData, TenantSapEntity, TenantUdf
from app.db.models.user import User, UserRole, UserRoleAssignment

__all__ = [
    "AgentRun",
    "AgentStep",
    "AuditLog",
    "BusinessPartnerCache",
    "CustomerAlias",
    "Document",
    "DocumentEvent",
    "DocumentKind",
    "DocumentSource",
    "DocumentStatus",
    "ExtractedData",
    "ItemCache",
    "ItemEmbedding",
    "LLMCall",
    "SAPSubmission",
    "QuotationPdf",
    "Tenant",
    "TenantMasterData",
    "TenantSapEntity",
    "TenantUdf",
    "User",
    "UserRole",
    "UserRoleAssignment",
]
