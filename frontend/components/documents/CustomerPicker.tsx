"use client";

import { useState } from "react";

import { Combobox } from "@/components/ui/Combobox";
import { FieldState } from "@/components/ui/Input";
import { useBusinessPartners } from "@/lib/queries";
import { BusinessPartner, ExtractedCustomer } from "@/lib/types";

interface Props {
  customer: ExtractedCustomer;
  onChange: (customer: ExtractedCustomer, bp?: BusinessPartner) => void;
  fieldState?: FieldState;
}

export function CustomerPicker({ customer, onChange, fieldState = "empty" }: Props) {
  const [query, setQuery] = useState(customer.card_name ?? customer.name ?? "");
  const { data: results = [], isLoading } = useBusinessPartners(query);

  return (
    <Combobox
      label={customer.card_name || customer.name || ""}
      value={customer.card_code ?? null}
      placeholder="Müşteri ara (en az 2 karakter)…"
      fieldState={fieldState}
      onSearch={setQuery}
      loading={isLoading}
      onChange={(opt) => {
        if (opt) {
          const bp = results.find((r) => r.CardCode === opt.value);
          onChange(
            {
              ...customer,
              card_code: opt.value,
              card_name: opt.label,
              // İletişim
              email: bp?.EmailAddress ?? customer.email,
              phone: bp?.Phone1 ?? customer.phone,
              phone2: bp?.Phone2 ?? customer.phone2,
              cellular: bp?.Cellular ?? customer.cellular,
              fax: bp?.Fax ?? customer.fax,
              website: bp?.Website ?? customer.website,
              tax_id: bp?.FederalTaxID ?? customer.tax_id,
              // Adres
              address: bp?.MailAddress ?? customer.address,
              city: bp?.MailCity ?? customer.city,
              country: bp?.MailCountry ?? customer.country,
              zip_code: bp?.MailZipCode ?? customer.zip_code,
              // Finans
              currency: bp?.Currency ?? customer.currency,
              credit_limit: bp?.CreditLimit ?? customer.credit_limit,
              discount_pct: bp?.DiscountPercent ?? customer.discount_pct,
              price_list_num: bp?.PriceListNum ?? customer.price_list_num,
              payment_terms_code: bp?.PaymentTermsGroupCode ?? customer.payment_terms_code,
              vat_group: bp?.VatGroup ?? customer.vat_group,
              // Bakiyeler
              balance: bp?.Balance ?? customer.balance,
              orders_balance: bp?.OrdersBal ?? customer.orders_balance,
            },
            bp,
          );
        } else {
          onChange({ ...customer, card_code: null, card_name: null });
        }
      }}
      options={results.map((bp) => ({
        value: bp.CardCode,
        label: bp.CardName,
        hint: [bp.CardCode, bp.FederalTaxID, bp.Currency].filter(Boolean).join(" · "),
      }))}
    />
  );
}
