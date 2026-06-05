/**
 * Backend ile paylaşılan domain tipleri.
 * Backend: app/schemas/* ve app/db/models/* karşılıkları.
 */

export type DocumentStatus =
  | "received"
  | "reading"
  | "matching"
  | "ready"
  | "pdf_generated"
  | "customer_accepted"
  | "customer_rejected"
  | "edited_after_acceptance"
  | "submitting"
  | "submitted"
  | "converting_to_order"
  | "order_submitted"
  | "error"
  | "rejected";

export type DocumentKind = "quotation" | "sales_order" | "unknown";
export type DocumentSource = "upload" | "email" | "api";

export interface DocumentSummary {
  id: string;
  source: DocumentSource;
  kind: DocumentKind;
  status: DocumentStatus;
  original_filename: string | null;
  file_size_bytes: number | null;
  source_email: string | null;
  source_subject: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractedCustomer {
  card_code?: string | null;
  card_name?: string | null;
  name?: string | null;
  tax_id?: string | null;
  email?: string | null;
  phone?: string | null;
  phone2?: string | null;
  cellular?: string | null;
  fax?: string | null;
  website?: string | null;
  address?: string | null;
  city?: string | null;
  country?: string | null;
  zip_code?: string | null;
  // Finans
  currency?: string | null;
  credit_limit?: number | null;
  discount_pct?: number | null;
  price_list_num?: number | null;
  payment_terms_code?: number | null;
  vat_group?: string | null;
  // Bakiyeler
  balance?: number | null;
  orders_balance?: number | null;
}

export interface ExtractedLine {
  line_no: number;
  description: string;
  item_code?: string | null;
  item_code_raw?: string | null;
  item_name?: string | null;
  barcode?: string | null;
  quantity: number;
  unit?: string | null;
  unit_price?: number | null;
  discount_pct?: number | null;
  tax_code?: string | null;
  total?: number | null;
}

export interface ExtractedDocument {
  kind?: DocumentKind;
  customer: ExtractedCustomer;
  reference_no?: string | null;
  doc_date?: string | null;
  due_date?: string | null;
  currency?: string | null;
  lines: ExtractedLine[];
  notes?: string | null;
  confidence?: Record<string, number>;
}

export interface ExtractedDataOut {
  version: number;
  payload: ExtractedDocument;
  confidence: Record<string, number> | null;
}

export interface DocumentDetail extends DocumentSummary {
  extracted?: ExtractedDataOut | null;
}

export interface BusinessPartner {
  // Kimlik
  CardCode: string;
  CardName: string;
  CardType?: string;
  GroupCode?: number;
  FederalTaxID?: string;
  Indicator?: string;
  // İletişim
  EmailAddress?: string;
  Phone1?: string;
  Phone2?: string;
  Cellular?: string;
  Fax?: string;
  Website?: string;
  // Adres
  MailAddress?: string;
  MailCity?: string;
  MailCounty?: string;
  MailZipCode?: string;
  MailCountry?: string;
  // Finans
  Currency?: string;
  CreditLimit?: number;
  DiscountPercent?: number;
  PriceListNum?: number;
  PaymentTermsGroupCode?: number;
  VatGroup?: string;
  // Satış
  SalesPersonCode?: number;
  Territory?: number;
  ContactPersonCode?: number;
  // Bakiyeler
  Balance?: number;
  OrdersBal?: number;
  DNotesBal?: number;
  // İrtibat kişileri ve adresler (expand ile gelir)
  ContactPersons?: Array<{
    Name?: string;
    FirstName?: string;
    LastName?: string;
    Phone1?: string;
    MobilePhone?: string;
    E_Mail?: string;
    Position?: string;
  }>;
  BPAddresses?: Array<{
    AddressName?: string;
    AddressType?: string;
    Street?: string;
    City?: string;
    ZipCode?: string;
    Country?: string;
  }>;
}

export interface Item {
  ItemCode: string;
  ItemName: string;
  BarCode?: string;
  SalesUnit?: string;
}

export interface SubmitResponse {
  submission_id: string;
  sap_doc_entry: number | null;
  sap_doc_num: number | null;
  dry_run: boolean;
  sap_endpoint: string | null;
  sap_payload: Record<string, unknown> | null;
  message: string | null;
}

export interface ConvertToOrderResponse {
  order_doc_entry: number;
  order_doc_num: number | null;
  dry_run: boolean;
  message: string;
}

export interface OrderCandidateOut {
  document_id: string;
  status: "candidate" | "converted";
  card_code: string | null;
  card_name: string | null;
  doc_currency: string | null;
  doc_total: number | null;
  original_filename: string | null;
  quotation_doc_entry: number | null;
  quotation_doc_num: number | null;
  order_doc_entry: number | null;
  order_doc_num: number | null;
  created_at: string;
  converted_at: string | null;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string | null;
  roles: string[];
  is_active: boolean;
  tenant_slug: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  tenant_slug: string | null;
}

export const STATUS_LABEL: Record<DocumentStatus, string> = {
  received: "AI Bekliyor",
  reading: "AI Okuyor",
  matching: "Eşleştiriyor",
  ready: "Hazır",
  pdf_generated: "PDF Hazır",
  customer_accepted: "Müşteri Kabul Etti",
  customer_rejected: "Müşteri Reddetti",
  edited_after_acceptance: "Kabul Sonrası Düzenlendi",
  submitting: "SAP'a Yazılıyor",
  submitted: "SAP'a Yazıldı",
  converting_to_order: "Sipariş Oluşturuluyor",
  order_submitted: "Sipariş Oluşturuldu",
  error: "Hata",
  rejected: "Reddedildi",
};

/** Her durumun ne olduğunu, kullanıcının ne yapması gerektiğini anlatan kısa açıklama. */
export const STATUS_HINT: Record<DocumentStatus, string> = {
  received:
    "Dosya yüklendi, AI henüz çalıştırılmadı. 'AI ile Teklif Hazırla' butonuyla işlemi başlatın.",
  reading: "AI dosyayı okuyor ve içerikteki ürün/müşteri satırlarını çıkarıyor. 10–30 sn sürebilir.",
  matching: "Çıkarılan müşteri ve ürünler SAP master verisiyle eşleştiriliyor.",
  ready: "AI çıkarımı tamam. Verileri kontrol edin, gerekirse düzeltin.",
  pdf_generated: "Teklif PDF'i hazır. Müşteriye gönderebilir veya sonucu bekleyebilirsiniz.",
  customer_accepted: "Müşteri kabul etti. 'Siparişe Dönüştür' ile SAP Order oluşturabilirsiniz.",
  customer_rejected: "Müşteri reddetti.",
  edited_after_acceptance: "Kabul sonrası düzenleme yapıldı. Yeni PDF üretilmeli.",
  submitting: "SAP Service Layer'a yazılıyor…",
  submitted: "SAP'a başarıyla yazıldı.",
  converting_to_order: "SAP Sales Order oluşturuluyor…",
  order_submitted: "SAP Sales Order başarıyla oluşturuldu.",
  error: "İşleme hatası oluştu. 'Tekrar Dene' ile yeniden çalıştırabilirsiniz.",
  rejected: "Operatör tarafından reddedildi.",
};

export const PIPELINE_COLUMNS: { key: DocumentStatus | "processing"; title: string; statuses: DocumentStatus[] }[] = [
  { key: "received", title: "Gelen", statuses: ["received"] },
  { key: "processing", title: "AI İşliyor", statuses: ["reading", "matching"] },
  { key: "ready", title: "Hazır", statuses: ["ready"] },
  { key: "pdf_generated", title: "Teklif Aşaması", statuses: ["pdf_generated", "customer_accepted", "customer_rejected", "edited_after_acceptance"] },
  { key: "submitted", title: "SAP'a Yazıldı", statuses: ["submitting", "submitted"] },
  { key: "error", title: "Hata", statuses: ["error", "rejected"] },
];
