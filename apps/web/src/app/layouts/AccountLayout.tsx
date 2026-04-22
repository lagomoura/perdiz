import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { useAuthStore } from '@/stores/auth';

export function AccountLayout() {
  const user = useAuthStore((s) => s.user);
  const location = useLocation();

  if (!user) {
    return (
      <Navigate
        to={`/auth/ingresar?from=${encodeURIComponent(location.pathname)}`}
        replace
      />
    );
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-10 md:px-6">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
