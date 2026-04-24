import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';

import { Spinner } from '@/components/feedback/Spinner';
import { AccountLayout } from './layouts/AccountLayout';
import { AdminLayout } from './layouts/AdminLayout';
import { AuthLayout } from './layouts/AuthLayout';
import { PublicLayout } from './layouts/PublicLayout';

const HomePage = lazy(() => import('@/pages/home/HomePage').then((m) => ({ default: m.HomePage })));
const LoginPage = lazy(() => import('@/pages/auth/LoginPage').then((m) => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage').then((m) => ({ default: m.RegisterPage })));
const VerifyEmailPage = lazy(() => import('@/pages/auth/VerifyEmailPage').then((m) => ({ default: m.VerifyEmailPage })));
const AccountPage = lazy(() => import('@/pages/account/AccountPage').then((m) => ({ default: m.AccountPage })));
const AdminDashboardPage = lazy(() =>
  import('@/pages/admin/AdminDashboardPage').then((m) => ({ default: m.AdminDashboardPage })),
);
const CategoriesListPage = lazy(() =>
  import('@/pages/admin/CategoriesListPage').then((m) => ({ default: m.CategoriesListPage })),
);
const CategoryEditPage = lazy(() =>
  import('@/pages/admin/CategoryEditPage').then((m) => ({ default: m.CategoryEditPage })),
);
const ProductsListPage = lazy(() =>
  import('@/pages/admin/ProductsListPage').then((m) => ({ default: m.ProductsListPage })),
);
const ProductEditPage = lazy(() =>
  import('@/pages/admin/ProductEditPage').then((m) => ({ default: m.ProductEditPage })),
);

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<Spinner />}>
            <HomePage />
          </Suspense>
        ),
      },
      {
        path: 'catalogo',
        element: (
          <div className="mx-auto max-w-4xl px-4 py-24 text-center text-neutral-600 md:px-6">
            Catálogo en construcción.
          </div>
        ),
      },
    ],
  },
  {
    element: <AuthLayout />,
    children: [
      {
        path: 'auth/ingresar',
        element: (
          <Suspense fallback={<Spinner />}>
            <LoginPage />
          </Suspense>
        ),
      },
      {
        path: 'auth/registrarse',
        element: (
          <Suspense fallback={<Spinner />}>
            <RegisterPage />
          </Suspense>
        ),
      },
      {
        path: 'auth/verificar-email',
        element: (
          <Suspense fallback={<Spinner />}>
            <VerifyEmailPage />
          </Suspense>
        ),
      },
    ],
  },
  {
    element: <AccountLayout />,
    children: [
      {
        path: 'mi-cuenta',
        element: (
          <Suspense fallback={<Spinner />}>
            <AccountPage />
          </Suspense>
        ),
      },
    ],
  },
  {
    path: 'admin',
    element: <AdminLayout />,
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<Spinner />}>
            <AdminDashboardPage />
          </Suspense>
        ),
      },
      {
        path: 'categorias',
        element: (
          <Suspense fallback={<Spinner />}>
            <CategoriesListPage />
          </Suspense>
        ),
      },
      {
        path: 'categorias/nueva',
        element: (
          <Suspense fallback={<Spinner />}>
            <CategoryEditPage />
          </Suspense>
        ),
      },
      {
        path: 'categorias/:id',
        element: (
          <Suspense fallback={<Spinner />}>
            <CategoryEditPage />
          </Suspense>
        ),
      },
      {
        path: 'productos',
        element: (
          <Suspense fallback={<Spinner />}>
            <ProductsListPage />
          </Suspense>
        ),
      },
      {
        path: 'productos/nuevo',
        element: (
          <Suspense fallback={<Spinner />}>
            <ProductEditPage />
          </Suspense>
        ),
      },
      {
        path: 'productos/:id',
        element: (
          <Suspense fallback={<Spinner />}>
            <ProductEditPage />
          </Suspense>
        ),
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
