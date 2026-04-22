import { ApiError } from '@/lib/errors';
import { useAuthStore } from '@/stores/auth';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/v1';

let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { access_token: string };
    return body.access_token;
  } catch {
    return null;
  }
}

async function refreshOnce(): Promise<string | null> {
  if (isRefreshing) return refreshPromise;
  isRefreshing = true;
  refreshPromise = doRefresh().finally(() => {
    isRefreshing = false;
    refreshPromise = null;
  });
  return refreshPromise;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { skipRefresh?: boolean },
): Promise<T> {
  const { accessToken } = useAuthStore.getState();
  const { skipRefresh, ...rest } = init ?? {};

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(rest.headers ?? {}),
  };
  if (accessToken) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${accessToken}`;
  }

  let response = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    credentials: 'include',
    headers,
  });

  if (response.status === 401 && !skipRefresh) {
    const newToken = await refreshOnce();
    if (newToken) {
      useAuthStore.getState().setAuth(useAuthStore.getState().user!, newToken);
      (headers as Record<string, string>)['Authorization'] = `Bearer ${newToken}`;
      response = await fetch(`${BASE_URL}${path}`, {
        ...rest,
        credentials: 'include',
        headers,
      });
    } else {
      useAuthStore.getState().clearAuth();
      window.location.href = '/auth/ingresar';
      throw new ApiError('AUTH_ERROR', 'Sesión expirada.', 401);
    }
  }

  if (response.status === 204) return undefined as T;

  if (!response.ok) {
    let code = 'HTTP_ERROR';
    let message = `Error ${response.status}`;
    let details: Record<string, unknown> | undefined;
    try {
      const body = (await response.json()) as {
        error?: { code: string; message: string; details?: Record<string, unknown> };
      };
      if (body.error) {
        code = body.error.code;
        message = body.error.message;
        details = body.error.details;
      }
    } catch {
      // ignore non-JSON bodies
    }
    throw new ApiError(code, message, response.status, details);
  }

  return (await response.json()) as T;
}
