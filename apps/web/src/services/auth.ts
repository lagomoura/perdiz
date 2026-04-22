import type { AuthUser, LoginPayload, RegisterPayload } from '@/types/auth';
import { apiFetch } from './api/client';

interface LoginResponse {
  access_token: string;
  user: {
    id: string;
    email: string;
    email_verified: boolean;
    role: string;
    first_name: string | null;
    last_name: string | null;
  };
}

interface RegisterResponse {
  user: {
    id: string;
    email: string;
    email_verified: boolean;
    role: string;
    first_name: string | null;
    last_name: string | null;
  };
}

function toAuthUser(raw: LoginResponse['user']): AuthUser {
  return {
    id: raw.id,
    email: raw.email,
    emailVerified: raw.email_verified,
    role: raw.role as AuthUser['role'],
    firstName: raw.first_name,
    lastName: raw.last_name,
  };
}

export async function login(payload: LoginPayload): Promise<{ user: AuthUser; accessToken: string }> {
  const data = await apiFetch<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email: payload.email, password: payload.password }),
    skipRefresh: true,
  });
  return { user: toAuthUser(data.user), accessToken: data.access_token };
}

export async function register(payload: RegisterPayload): Promise<AuthUser> {
  const data = await apiFetch<RegisterResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      first_name: payload.firstName ?? null,
      last_name: payload.lastName ?? null,
    }),
    skipRefresh: true,
  });
  return toAuthUser(data.user);
}

export async function logout(): Promise<void> {
  await apiFetch<void>('/auth/logout', { method: 'POST', skipRefresh: true });
}

export async function refreshSession(): Promise<{ user: AuthUser; accessToken: string } | null> {
  try {
    const data = await apiFetch<{ access_token: string }>('/auth/refresh', {
      method: 'POST',
      skipRefresh: true,
    });
    const me = await apiFetch<{ user: LoginResponse['user'] }>('/users/me', {
      headers: { Authorization: `Bearer ${data.access_token}` },
      skipRefresh: true,
    });
    return { user: toAuthUser(me.user), accessToken: data.access_token };
  } catch {
    return null;
  }
}

export async function getMe(): Promise<AuthUser> {
  const data = await apiFetch<{ user: LoginResponse['user'] }>('/users/me');
  return toAuthUser(data.user);
}

export async function verifyEmail(token: string): Promise<AuthUser> {
  const data = await apiFetch<{ user: LoginResponse['user'] }>('/auth/email/verify', {
    method: 'POST',
    body: JSON.stringify({ token }),
    skipRefresh: true,
  });
  return toAuthUser(data.user);
}

export async function resendVerification(): Promise<void> {
  await apiFetch<void>('/auth/email/resend-verification', { method: 'POST' });
}
