import { Navigate, NavLink, Outlet, useLocation } from 'react-router-dom';

import { Logo } from '@/components/ui/Logo';
import { useLogout } from '@/features/auth/hooks';
import { useAuthStore } from '@/stores/auth';

const ITEMS = [
  { to: '/admin', label: 'Dashboard', end: true },
  { to: '/admin/categorias', label: 'Categorías' },
  { to: '/admin/productos', label: 'Productos' },
];

export function AdminLayout() {
  const user = useAuthStore((s) => s.user);
  const location = useLocation();
  const { mutate: doLogout } = useLogout();

  if (!user) {
    return (
      <Navigate
        to={`/auth/ingresar?from=${encodeURIComponent(location.pathname)}`}
        replace
      />
    );
  }
  if (user.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  const baseLink =
    'block rounded-lg px-3 py-2 text-sm font-medium transition-colors';
  const inactive = 'text-neutral-600 hover:bg-neutral-100';
  const active = 'bg-brand-orange-50 text-brand-orange-700';

  return (
    <div className="flex min-h-dvh bg-neutral-50">
      <aside className="flex w-64 shrink-0 flex-col border-r border-neutral-200 bg-white px-4 py-6">
        <div className="mb-8 flex items-center gap-3 px-2">
          <Logo className="h-10" />
          <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
            admin
          </span>
        </div>
        <nav className="flex-1 space-y-1">
          {ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `${baseLink} ${isActive ? active : inactive}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-4 border-t border-neutral-200 pt-4">
          <p className="mb-2 truncate px-2 text-xs text-neutral-500">
            {user.email}
          </p>
          <button
            type="button"
            onClick={() => doLogout()}
            className="w-full rounded-lg px-3 py-2 text-left text-sm text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          >
            Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
