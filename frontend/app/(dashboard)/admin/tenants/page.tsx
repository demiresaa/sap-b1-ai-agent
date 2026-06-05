"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";

interface TenantOut {
  id: string;
  slug: string;
  name: string;
  schema_name: string;
  sl_base_url: string;
  company_db: string;
  vault_secret_path: string;
  sap_dry_run: boolean;
  is_active: boolean;
  default_warehouse: string | null;
  default_sales_person_id: number | null;
  default_currency: string | null;
  default_pdf_template: string;
}

function useTenants() {
  return useQuery<TenantOut[]>({
    queryKey: ["admin-tenants"],
    queryFn: async () => (await api.get<TenantOut[]>("/admin/tenants")).data,
  });
}

function useUpdateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      slug,
      patch,
    }: {
      slug: string;
      patch: Partial<TenantOut>;
    }) => (await api.patch<TenantOut>(`/admin/tenants/${slug}`, patch)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-tenants"] }),
  });
}

export default function AdminTenantsPage() {
  const { data, isLoading, error } = useTenants();

  return (
    <div className="space-y-4 p-6">
      <h1 className="text-xl font-semibold">Tenant Yönetimi</h1>
      {isLoading && <div className="text-sm text-slate-500">Yükleniyor…</div>}
      {error && <div className="text-sm text-red-600">Hata: {(error as Error).message}</div>}
      {data && (
        <div className="grid gap-4">
          {data.map((tenant) => (
            <TenantCard key={tenant.id} tenant={tenant} />
          ))}
        </div>
      )}
    </div>
  );
}

function TenantCard({ tenant }: { tenant: TenantOut }) {
  const update = useUpdateTenant();
  const [warehouse, setWarehouse] = useState(tenant.default_warehouse ?? "");
  const [currency, setCurrency] = useState(tenant.default_currency ?? "");

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">{tenant.name}</h2>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <code className="rounded bg-slate-100 px-1.5 py-0.5">{tenant.slug}</code>
            <code className="rounded bg-slate-100 px-1.5 py-0.5">{tenant.schema_name}</code>
            <code className="rounded bg-slate-100 px-1.5 py-0.5">{tenant.company_db}</code>
            <span>·</span>
            <span>{tenant.sl_base_url}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <Badge tone={tenant.is_active ? "accent" : "neutral"} size="sm">
            {tenant.is_active ? "Aktif" : "Pasif"}
          </Badge>
          <Badge tone={tenant.sap_dry_run ? "warn" : "accent"} size="sm">
            {tenant.sap_dry_run ? "DRY-RUN" : "CANLI"}
          </Badge>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="text-xs text-slate-600">
          Varsayılan Depo
          <Input
            value={warehouse}
            onChange={(e) => setWarehouse(e.target.value)}
            placeholder="örn. 02"
          />
        </label>
        <label className="text-xs text-slate-600">
          Varsayılan Para Birimi
          <Input
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            placeholder="EUR"
          />
        </label>
        <div className="flex items-end gap-2">
          <Button
            onClick={() =>
              update.mutate({
                slug: tenant.slug,
                patch: {
                  default_warehouse: warehouse || null,
                  default_currency: currency || null,
                },
              })
            }
            loading={update.isPending}
          >
            Kaydet
          </Button>
          <Button
            variant={tenant.sap_dry_run ? "primary" : "secondary"}
            onClick={() =>
              update.mutate({
                slug: tenant.slug,
                patch: { sap_dry_run: !tenant.sap_dry_run },
              })
            }
            loading={update.isPending}
          >
            {tenant.sap_dry_run ? "CANLI moda al" : "DRY-RUN moda al"}
          </Button>
        </div>
      </div>
    </div>
  );
}
