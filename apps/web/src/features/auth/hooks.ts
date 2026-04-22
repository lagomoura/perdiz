import { useMutation } from '@tanstack/react-query';

import { ApiError } from '@/lib/errors';
import { login, logout, register, resendVerification, verifyEmail } from '@/services/auth';
import { useAuthStore } from '@/stores/auth';
import type { LoginPayload, RegisterPayload } from '@/types/auth';

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth);

  return useMutation({
    mutationFn: (payload: LoginPayload) => login(payload),
    onSuccess: ({ user, accessToken }) => {
      setAuth(user, accessToken);
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (payload: RegisterPayload) => register(payload),
  });
}

export function useLogout() {
  const clearAuth = useAuthStore((s) => s.clearAuth);

  return useMutation({
    mutationFn: logout,
    onSettled: () => clearAuth(),
  });
}

export function useVerifyEmail() {
  return useMutation({
    mutationFn: (token: string) => verifyEmail(token),
  });
}

export function useResendVerification() {
  return useMutation({
    mutationFn: resendVerification,
  });
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError;
}
