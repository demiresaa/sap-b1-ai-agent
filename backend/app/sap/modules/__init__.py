"""SAP B1 modülleri — her endpoint için ayrı dosya.

MVP modülleri aktif. Faz 2/3 stub'ları kasıtlı olarak boş — sıra geldiğinde
docstring'lerindeki TODO'lara göre doldurulacak.
"""
from app.sap.modules.business_partners import BusinessPartnersModule
from app.sap.modules.items import ItemsModule
from app.sap.modules.quotations import QuotationsModule
from app.sap.modules.sales_orders import SalesOrdersModule

__all__ = [
    "BusinessPartnersModule",
    "ItemsModule",
    "QuotationsModule",
    "SalesOrdersModule",
]
