import { Link, Outlet } from 'react-router-dom';
import { Logo } from '@/components/ui/Logo';

export function AuthLayout() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-neutral-50 px-4 py-12">
      <Link to="/" className="mb-8" aria-label="Ir al inicio">
        <Logo className="h-14" />
      </Link>
      <div className="w-full max-w-md rounded-xl border border-neutral-100 bg-neutral-0 p-8 shadow-md">
        <Outlet />
      </div>
    </div>
  );
}
