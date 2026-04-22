import { type ReactNode, useEffect, useState } from 'react';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

import '../app/i18n';
import { refreshSession } from '@/services/auth';
import { useAuthStore } from '@/stores/auth';
import { router } from './router';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
    mutations: { retry: 0 },
  },
});

function SessionGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const setAuth = useAuthStore((s) => s.setAuth);

  useEffect(() => {
    refreshSession()
      .then((session) => {
        if (session) setAuth(session.user, session.accessToken);
      })
      .finally(() => setReady(true));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!ready) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-200 border-t-brand-orange-500"
          aria-label="Cargando sesión"
        />
      </div>
    );
  }

  return <>{children}</>;
}

export function Providers() {
  return (
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <SessionGate>
          <RouterProvider router={router} />
        </SessionGate>
      </QueryClientProvider>
    </HelmetProvider>
  );
}
