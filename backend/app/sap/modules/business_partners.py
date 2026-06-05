"""SAP B1 BusinessPartners — müşteri (CardType='C') ve tedarikçi (CardType='S')."""
from __future__ import annotations

from typing import Any

from app.sap.client import SAPServiceLayerClient
from app.sap.odata import ODataQuery, contains, eq, escape_literal, or_

# SAP Service Layer'dan çekilen tüm faydalı BP alanları.
# $select ile sadece bunları isteyerek response boyutunu küçültürüz.
CUSTOMER_SELECT_FIELDS = (
    # Kimlik
    "CardCode",
    "CardName",
    "CardType",
    "GroupCode",
    "FederalTaxID",       # Vergi No
    "Indicator",          # Segment/gösterge kodu
    # İletişim
    "EmailAddress",
    "Phone1",
    "Phone2",
    "Cellular",           # Cep telefonu
    "Fax",
    "Website",
    # Adres (kart üzerindeki varsayılan)
    "MailAddress",        # Sokak/cadde
    "MailCity",           # Şehir
    "MailCounty",         # İlçe
    "MailZipCode",        # Posta kodu
    "MailCountry",        # Ülke kodu (TR, DE, …)
    # Finans
    "Currency",           # Para birimi
    "CreditLimit",        # Kredi limiti
    "DiscountPercent",    # Varsayılan iskonto %
    "PriceListNum",       # Fiyat listesi no
    "PaymentTermsGroupCode",  # Ödeme koşulları
    "VatGroup",           # KDV grubu
    # Satış
    "SalesPersonCode",    # Sorumlu satış temsilcisi
    "Territory",          # Bölge kodu
    "ContactPersonCode",  # Varsayılan irtibat kişisi
    # Bakiyeler (sadece okunur bilgi)
    "Balance",            # Cari bakiye
    "OrdersBal",          # Açık sipariş bakiyesi
    "DNotesBal",          # Açık irsaliye bakiyesi
)


class BusinessPartnersModule:
    PATH = "/BusinessPartners"

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    async def list_customers(
        self, *, top: int = 100, skip: int = 0, search: str | None = None
    ) -> list[dict[str, Any]]:
        query = (
            ODataQuery()
            .select(*CUSTOMER_SELECT_FIELDS)
            .filter(eq("CardType", "cCustomer"))
            .top(top)
            .skip(skip)
            .orderby("CardName")
        )
        if search:
            query.filter(or_(contains("CardName", search), contains("CardCode", search)))
        resp = await self.client.get(self.PATH, **query.build())
        return resp.get("value", [])

    async def get(self, card_code: str) -> dict[str, Any]:
        """Tek müşteri — tüm alanlar (ContactPersons + BPAddresses expand)."""
        return await self.client.get(
            f"{self.PATH}('{escape_literal(card_code)}')",
            **ODataQuery()
            .select(*CUSTOMER_SELECT_FIELDS)
            .expand("ContactPersons", "BPAddresses")
            .build(),
        )

    async def search_by_tax_id(self, tax_id: str) -> list[dict[str, Any]]:
        query = (
            ODataQuery()
            .select(*CUSTOMER_SELECT_FIELDS)
            .filter(eq("FederalTaxID", tax_id))
            .top(20)
        )
        resp = await self.client.get(self.PATH, **query.build())
        return resp.get("value", [])

    async def search_by_email(self, email: str) -> list[dict[str, Any]]:
        query = (
            ODataQuery()
            .select(*CUSTOMER_SELECT_FIELDS)
            .filter(eq("EmailAddress", email))
            .top(20)
        )
        resp = await self.client.get(self.PATH, **query.build())
        return resp.get("value", [])
