Merhaba,

SAP B1 Service Layer üzerinden test DB’den alınan dump dosyasını ekte iletiyorum.

CompanyDB:
2026_Test

Base URL:
https://10.11.10.46:50000/b1s/v1

ZIP içeriğinde şunlar bulunmaktadır:

* metadata.xml: Service Layer genel şema çıktısı
* udf_*.json: Teklif, sipariş, müşteri ve ürün UDF alanları
* user_tables.json: SAP B1 custom tablo listesi
* sample_quotations.json: Örnek satış teklifleri
* sample_orders.json: Örnek satış siparişleri
* master_*.json: Satış çalışanı, proje, depo, para birimi, vergi kodu ve fiyat listesi gibi master data listeleri
* README.txt: Ortam ve bağlantı notları

Not:
Bu çıktı test ortamından alınmıştır. Canlı DB bilgisi ve şifre paylaşılmamıştır. SSL sertifikası trusted olmadığı için testlerde verify=False kullanılmıştır.
