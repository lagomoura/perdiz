/**
 * Lightweight fetch wrapper. The generated OpenAPI client will sit next to this
 * file in src/services/api/generated/ and will be called through this wrapper.
 *
 * Responsibilities (to implement as auth feature lands):
 *  - inject Authorization: Bearer <accessToken>
 *  - on 401, attempt one refresh via POST /auth/refresh and retry once
 *  - add Idempotency-Key on sensitive mutations
 *  - map error.code to a typed ApiError
 */

const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/v1';

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: Record<string, unknown>,
    public requestId?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let code = 'HTTP_ERROR';
    let message = `Request failed with ${response.status}`;
    let details: Record<string, unknown> | undefined;
    let requestId: string | undefined;
    try {
      const body = (await response.json()) as {
        error?: { code: string; message: string; details?: Record<string, unknown>; request_id?: string };
      };
      if (body.error) {
        code = body.error.code;
        message = body.error.message;
        details = body.error.details;
        requestId = body.error.request_id;
      }
    } catch {
      // ignore non-json error bodies
    }
    throw new ApiError(code, message, response.status, details, requestId);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
