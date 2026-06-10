"""SAP B1 modülleri — her endpoint için ayrı dosya."""
from app.sap.modules.business_partners import BusinessPartnersModule
from app.sap.modules.delivery_notes import DeliveryNotesModule
from app.sap.modules.invoices import InvoicesModule
from app.sap.modules.items import ItemsModule
from app.sap.modules.purchase_orders import PurchaseOrdersModule
from app.sap.modules.quotations import QuotationsModule
from app.sap.modules.sales_orders import SalesOrdersModule

__all__ = [
    "BusinessPartnersModule",
    "DeliveryNotesModule",
    "InvoicesModule",
    "ItemsModule",
    "PurchaseOrdersModule",
    "QuotationsModule",
    "SalesOrdersModule",
]
