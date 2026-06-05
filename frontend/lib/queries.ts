/**
 * React Query hook'ları — backend endpoint'leri için.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, setTokens, setTenantSlug } from "./api";
import {
  BusinessPartner,
  ConvertToOrderResponse,
  CurrentUser,
  DocumentDetail,
  DocumentStatus,
  DocumentSummary,
  ExtractedDocument,
  Item,
  OrderCandidateOut,
  SubmitResponse,
  TokenResponse,
} from "./types";

// -------- Auth --------

export function useCurrentUser() {
  return useQuery<CurrentUser>({
    queryKey: ["me"],
    queryFn: async () => (await api.get<CurrentUser>("/auth/me")).data,
    retry: false,
  });
}

export function useLogin() {
  return useMutation({
    mutationFn: async (payload: { email: string; password: string }) => {
      const { data } = await api.post<TokenResponse>("/auth/login", payload);
      setTokens(data.access_token, data.refresh_token);
      setTenantSlug(data.tenant_slug ?? null);
      return data;
    },
  });
}

// -------- Documents --------

const ACTIVE_STATUSES: DocumentStatus[] = ["received", "reading", "matching", "submitting", "converting_to_order"];

export function useDocuments(status?: DocumentStatus) {
  return useQuery<DocumentSummary[]>({
    queryKey: ["documents", status ?? "all"],
    queryFn: async () => {
      const params = status ? { status } : undefined;
      return (await api.get<DocumentSummary[]>("/documents", { params })).data;
    },
    // Sadece AI/SAP aktif çalışırken kısa aralıkla yenile; yoksa hiç polling yok.
    refetchInterval: (query) => {
      const data = query.state.data as DocumentSummary[] | undefined;
      if (!data || data.length === 0) return false;
      return data.some((d) => ACTIVE_STATUSES.includes(d.status)) ? 4000 : false;
    },
    refetchOnWindowFocus: false,
  });
}

export function useDocument(documentId: string | null) {
  return useQuery<DocumentDetail>({
    queryKey: ["document", documentId],
    enabled: !!documentId,
    queryFn: async () => (await api.get<DocumentDetail>(`/documents/${documentId}`)).data,
    // Aktif statulerde 3s'de bir otomatik yenile — butona basinca hemen guncellenir
    refetchInterval: (query) => {
      const d = query.state.data as DocumentDetail | undefined;
      if (!d) return false;
      return ACTIVE_STATUSES.includes(d.status as DocumentStatus) ? 3000 : false;
    },
    refetchOnWindowFocus: false,
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post<DocumentSummary>("/documents/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: (newDoc) => {
      // Cache'deki tüm document listelerine yeni belgeyi başa ekle — UI anında güncellenir.
      qc.setQueriesData<DocumentSummary[]>({ queryKey: ["documents"] }, (old) => {
        if (!old) return [newDoc];
        if (old.some((d) => d.id === newDoc.id)) return old;
        return [newDoc, ...old];
      });
      // Arka planda backend'den taze veri de çekilsin
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useUpdateExtractedData() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { documentId: string; payload: ExtractedDocument }) => {
      const { data } = await api.patch<DocumentDetail>(`/documents/${input.documentId}`, {
        payload: input.payload,
      });
      return data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["document", data.id] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useSubmitDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (documentId: string): Promise<SubmitResponse> => {
      const { data } = await api.post<SubmitResponse>(`/documents/${documentId}/submit`);
      return data;
    },
    onSuccess: (_, documentId) => {
      qc.invalidateQueries({ queryKey: ["document", documentId] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useReprocessDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (documentId: string) => {
      const { data } = await api.post(`/documents/${documentId}/process`);
      return data;
    },
    onSuccess: (_, documentId) => {
      qc.invalidateQueries({ queryKey: ["document", documentId] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useDeleteDocuments() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (documentIds: string[]) => {
      const results = await Promise.allSettled(
        documentIds.map((id) => api.delete(`/documents/${id}`)),
      );
      const failed = results.filter((r) => r.status === "rejected").length;
      return { total: documentIds.length, failed };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useGenerateQuotationPdf() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (documentId: string) => {
      const { data } = await api.post<{
        id: string;
        document_id: string;
        version: number;
        size_bytes: number;
        download_url: string;
      }>(`/documents/${documentId}/generate-pdf`);
      return data;
    },
    onSuccess: (_, documentId) => {
      qc.invalidateQueries({ queryKey: ["document", documentId] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useDownloadQuotationPdf() {
  return useMutation({
    mutationFn: async (documentId: string) => {
      const resp = await api.get(`/documents/${documentId}/quotation.pdf`, {
        responseType: "blob",
      });
      const blob = new Blob([resp.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `teklif-${documentId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      return { ok: true };
    },
  });
}

export function useCustomerAccepted() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (documentId: string) => {
      const { data } = await api.post<{ status: string; document_id: string }>(
        `/documents/${documentId}/customer-accepted`,
      );
      return data;
    },
    onSuccess: (_, documentId) => {
      qc.invalidateQueries({ queryKey: ["document", documentId] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useCustomerRejected() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (params: { documentId: string; reason?: string }) => {
      const { data } = await api.post<{ status: string; document_id: string }>(
        `/documents/${params.documentId}/customer-rejected`,
        null,
        { params: params.reason ? { reason: params.reason } : undefined },
      );
      return data;
    },
    onSuccess: (_, { documentId }) => {
      qc.invalidateQueries({ queryKey: ["document", documentId] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

// -------- Orders --------

export function useOrderCandidates(filter: "candidates" | "converted" | "all" = "all") {
  return useQuery<OrderCandidateOut[]>({
    queryKey: ["orders", filter],
    queryFn: async () =>
      (await api.get<OrderCandidateOut[]>("/orders", { params: { filter } })).data,
    refetchInterval: (query) => {
      const data = query.state.data as OrderCandidateOut[] | undefined;
      if (!data || data.length === 0) return false;
      return data.some((o) => o.status === "candidate") ? 10000 : false;
    },
    refetchOnWindowFocus: false,
  });
}

export function useConvertToOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (documentId: string): Promise<ConvertToOrderResponse> => {
      const { data } = await api.post<ConvertToOrderResponse>(
        `/documents/${documentId}/convert-to-order`,
      );
      return data;
    },
    onSuccess: (_, documentId) => {
      qc.invalidateQueries({ queryKey: ["orders"] });
      qc.invalidateQueries({ queryKey: ["document", documentId] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

// -------- SAP master data --------

export function useBusinessPartners(search: string) {
  return useQuery<BusinessPartner[]>({
    queryKey: ["bp", search],
    enabled: search.length >= 2,
    queryFn: async () =>
      (await api.get<BusinessPartner[]>("/sap/business-partners", { params: { search, top: 30 } })).data,
    staleTime: 30_000,
  });
}

export function useItems(search: string) {
  return useQuery<Item[]>({
    queryKey: ["items", search],
    enabled: search.length >= 2,
    queryFn: async () =>
      (await api.get<Item[]>("/sap/items", { params: { search, top: 30 } })).data,
    staleTime: 30_000,
  });
}

export function useItemAvailability(itemCode: string | null) {
  return useQuery<{ Available?: number; InStock?: number }>({
    queryKey: ["availability", itemCode],
    enabled: !!itemCode,
    queryFn: async () => (await api.get(`/sap/items/${itemCode}/availability`)).data,
  });
}
