import { Link } from 'react-router-dom';
import { Logo } from '@/components/ui/Logo';

export function Footer() {
  return (
    <footer className="border-t border-neutral-100 bg-neutral-50">
      <div className="mx-auto max-w-7xl px-4 py-10 md:px-6">
        <div className="flex flex-col items-center gap-6 md:flex-row md:justify-between">
          <Logo className="h-10" />
          <nav className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-neutral-600">
            <Link to="/#como-funciona" className="hover:text-brand-graphite-900">
              Cómo funciona
            </Link>
            <Link to="/#contacto" className="hover:text-brand-graphite-900">
              Contacto
            </Link>
            <Link to="/terminos" className="hover:text-brand-graphite-900">
              Términos
            </Link>
            <Link to="/privacidad" className="hover:text-brand-graphite-900">
              Privacidad
            </Link>
          </nav>
          <p className="text-xs text-neutral-400">
            © {new Date().getFullYear()} p3rDiz. Hecho en Argentina.
          </p>
        </div>
      </div>
    </footer>
  );
}
