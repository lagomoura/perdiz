import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LogOut, User } from 'lucide-react';

import { Logo } from '@/components/ui/Logo';
import { useAuthStore } from '@/stores/auth';
import { logout } from '@/services/auth';

export function Header() {
  const { t } = useTranslation();
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  async function handleLogout() {
    try {
      await logout();
    } finally {
      clearAuth();
      navigate('/');
    }
  }

  return (
    <header className="sticky top-0 z-30 border-b border-neutral-100 bg-neutral-0/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 md:px-6">
        <Link to="/" className="flex-shrink-0" aria-label="Ir al inicio">
          <Logo className="h-14 md:h-16" />
        </Link>

        <nav className="hidden items-center gap-6 md:flex" aria-label="Navegación principal">
          <Link
            to="/catalogo"
            className="text-sm font-medium text-neutral-600 transition-colors hover:text-brand-graphite-900"
          >
            {t('nav.catalog')}
          </Link>
          <Link
            to="/#como-funciona"
            className="text-sm font-medium text-neutral-600 transition-colors hover:text-brand-graphite-900"
          >
            {t('nav.howItWorks')}
          </Link>
          <Link
            to="/#contacto"
            className="text-sm font-medium text-neutral-600 transition-colors hover:text-brand-graphite-900"
          >
            {t('nav.contact')}
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          {user ? (
            <>
              <Link
                to="/mi-cuenta"
                className="flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-50 hover:text-brand-graphite-900"
              >
                <User size={16} aria-hidden="true" />
                <span className="hidden sm:inline">
                  {user.firstName ?? user.email.split('@')[0]}
                </span>
              </Link>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 rounded-md px-3 py-2 text-sm text-neutral-600 transition-colors hover:bg-neutral-50 hover:text-brand-graphite-900"
                aria-label={t('auth.logout')}
              >
                <LogOut size={16} aria-hidden="true" />
                <span className="hidden sm:inline">{t('auth.logout')}</span>
              </button>
            </>
          ) : (
            <>
              <Link
                to="/auth/ingresar"
                className="rounded-md px-4 py-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-50 hover:text-brand-graphite-900"
              >
                {t('nav.login')}
              </Link>
              <Link
                to="/auth/registrarse"
                className="inline-flex items-center rounded-md bg-brand-orange-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-orange-600 focus-visible:shadow-focus"
              >
                {t('nav.register')}
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
