/**
 * Backend API client.
 *
 * - Access token localStorage'tan eklenir.
 * - 401 yakalanırsa önce /auth/refresh ile yenilenir, başarısızsa /login'e atılır.
 * - Eş zamanlı 401'ler tek bir refresh çağrısını paylaşır (queue).
 * - Hata mesajları (TR) `error.message` olarak yeniden raise edilir.
 */
import axios, { AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api",
  timeout: 30000,
});

const TOKEN_KEY = "sap_b1_ai_agent_token";
const REFRESH_KEY = "sap_b1_ai_agent_refresh";
const TENANT_KEY = "sap_b1_ai_agent_tenant";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, access);
  window.localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
  window.localStorage.removeItem(TENANT_KEY);
}

export function getTenantSlug(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TENANT_KEY);
}

export function setTenantSlug(slug: string | null): void {
  if (typeof window === "undefined") return;
  if (slug) {
    window.localStorage.setItem(TENANT_KEY, slug);
  } else {
    window.localStorage.removeItem(TENANT_KEY);
  }
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const tenant = getTenantSlug();
  if (tenant) {
    config.headers["X-Tenant-Slug"] = tenant;
  }
  return config;
});

// --- 401 → refresh flow -----------------------------------------------------

interface PendingItem {
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}

let isRefreshing = false;
let pendingQueue: PendingItem[] = [];

function flushQueue(error: unknown, token: string | null = null) {
  pendingQueue.forEach((p) => {
    if (token) p.resolve(token);
    else p.reject(error);
  });
  pendingQueue = [];
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  clearTokens();
  if (!window.location.pathname.startsWith("/login")) {
    // Geri dönmek için mevcut yolu next= olarak saklayabiliriz; şimdilik basit redirect.
    window.location.href = "/login";
  }
}

async function refreshAccessToken(): Promise<string> {
  const refresh = getRefreshToken();
  if (!refresh) throw new Error("no_refresh_token");
  // Ham axios — interceptor recursion'a girmesin diye instance'ı kullanmıyoruz.
  const baseURL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
  const resp = await axios.post<{
    access_token: string;
    refresh_token: string;
    tenant_slug: string | null;
  }>(`${baseURL}/auth/refresh`, { refresh_token: refresh }, { timeout: 15000 });
  setTokens(resp.data.access_token, resp.data.refresh_token);
  if (resp.data.tenant_slug !== undefined) {
    setTenantSlug(resp.data.tenant_slug);
  }
  return resp.data.access_token;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string }>) => {
    const detail = error.response?.data?.detail;
    if (detail) error.message = detail;

    const original = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined;
    const status = error.response?.status;

    // 401 değilse — veya zaten refresh endpoint'i için 401 ise — direkt reject.
    const url = original?.url ?? "";
    if (status !== 401 || !original || original._retry || url.includes("/auth/refresh") || url.includes("/auth/login")) {
      if (status === 401 && url.includes("/auth/refresh")) {
        // Refresh de düştü — logout.
        flushQueue(error, null);
        redirectToLogin();
      }
      return Promise.reject(error);
    }

    // Refresh token yoksa direkt logout.
    if (!getRefreshToken()) {
      redirectToLogin();
      return Promise.reject(error);
    }

    original._retry = true;

    // Eğer şu an başka bir refresh devam ediyorsa, kuyruğa eklen ve bekle.
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({
          resolve: (token) => {
            if (original.headers) {
              original.headers.Authorization = `Bearer ${token}`;
            }
            resolve(api(original as AxiosRequestConfig));
          },
          reject,
        });
      });
    }

    // Aktif refresh — sadece bir tane.
    isRefreshing = true;
    try {
      const newToken = await refreshAccessToken();
      flushQueue(null, newToken);
      if (original.headers) {
        original.headers.Authorization = `Bearer ${newToken}`;
      }
      return api(original as AxiosRequestConfig);
    } catch (refreshErr) {
      flushQueue(refreshErr, null);
      redirectToLogin();
      return Promise.reject(refreshErr);
    } finally {
      isRefreshing = false;
    }
  },
);
