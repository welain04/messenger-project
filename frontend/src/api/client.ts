// Тонкий fetch-клиент: базовый URL, токены (access + refresh), авто-refresh при 401.

const ACCESS_KEY = "messenger.token";
const REFRESH_KEY = "messenger.refresh";

export function getApiBaseUrl(): string {
  const fromEnv = (import.meta as any)?.env?.VITE_API_BASE_URL as string | undefined;
  return (fromEnv && fromEnv.replace(/\/$/, "")) || "http://localhost:8000/api/v1";
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(ACCESS_KEY);
  } catch {
    return null;
  }
}

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export function setTokens(pair: TokenPair | null): void {
  try {
    if (pair) {
      localStorage.setItem(ACCESS_KEY, pair.access_token);
      localStorage.setItem(REFRESH_KEY, pair.refresh_token);
    } else {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    }
  } catch {
    // ignore (SSR / приватный режим)
  }
}

// Совместимость со старым API: одиночный access-токен.
export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(ACCESS_KEY, token);
    else {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    }
  } catch {
    // ignore
  }
}

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown, message?: string) {
    super(message ?? `API error ${status}`);
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | undefined> | Record<string, unknown>;
  auth?: boolean; // default true
  _retried?: boolean; // внутренний флаг: повтор после refresh
}

// Дедупликация одновременных refresh-запросов.
let refreshPromise: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const url = getApiBaseUrl() + "/auth/refresh";
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) {
          setTokens(null);
          return false;
        }
        const data = (await res.json()) as TokenPair;
        setTokens(data);
        return true;
      } catch {
        setTokens(null);
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, auth = true, _retried = false } = options;
  const url = new URL(getApiBaseUrl() + path);
  if (query) {
    for (const [k, v] of Object.entries(query as Record<string, unknown>)) {
      if (v !== undefined && v !== null) url.searchParams.append(k, String(v));
    }
  }

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const t = getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }

  const res = await fetch(url.toString(), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // Авто-refresh: один раз пробуем обновить токен и повторить запрос.
  if (res.status === 401 && auth && !_retried) {
    const ok = await refreshTokens();
    if (ok) {
      return request<T>(path, { ...options, _retried: true });
    }
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? safeJson(text) : null;

  if (!res.ok) {
    const detail = (data as any)?.detail ?? data ?? text;
    throw new ApiError(res.status, detail, typeof detail === "string" ? detail : undefined);
  }

  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
