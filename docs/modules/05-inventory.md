# Modül: Inventory (Stok Yönetimi)

**Durum:** Faz 3 (hazır placeholder)
**SAP Endpoint:** `/b1s/v1/Items`, `/Warehouses`, `/StockTransfers`, `/InventoryGenEntries`, `/InventoryGenExits`, `/InventoryCountings`, `/InventoryPostings`
**Backend:** `backend/app/sap/modules/inventory.py`, `stock_transfers.py` (stub)
**Faz:** 3

---

## Amaç
Depo operasyonlarını AI destekli yönetmek: sayım, transfer, fire, mal kabul/çıkış. MVP'de sadece **availability sorgu** kullanılıyor — bu modül tam yönetim için açılacak.

## Aktif Olduğunda Yapılacaklar (TODO)

- [ ] StockTransfer POST (depolar arası transfer)
- [ ] InventoryCounting (sayım başlat/kapat)
- [ ] InventoryGenEntries (fire/mal giriş)
- [ ] InventoryGenExits (sarf/mal çıkış)
- [ ] BatchNumberDetails (parti takibi)
- [ ] SerialNumberDetails (seri no takibi)
- [ ] **Inventory Agent**: transfer önerisi (yoğun depo → boş depo)
- [ ] Min/max seviye uyarı motoru
- [ ] Stok devir hızı analizi

## Use Cases
- Sayım sonuçlarını OCR ile fişten oku, SAP'a yaz
- Yoğun depodan boşa transfer önerisi (AI)
- Düşük dönen ürün uyarısı (analytics)
- Parti/seri no takibi otomasyonu

## Bağımlılıklar
- Faz 2 Inventory function importları (availability mevcut)
- BatchNumber / SerialNumber özellikli ürünler

## Faz 3 Sprint Tahmin
~12 iş günü
