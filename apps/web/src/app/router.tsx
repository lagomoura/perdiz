import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';

import { Spinner } from '@/components/feedback/Spinner';
import { PublicLayout } from './layouts/PublicLayout';
import { AuthLayout } from './layouts/AuthLayout';
import { AccountLayout } from './layouts/AccountLayout';

const HomePage = lazy(() => import('@/pages/home/HomePage').then((m) => ({ default: m.HomePage })));
const LoginPage = lazy(() => import('@/pages/auth/LoginPage').then((m) => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage').then((m) => ({ default: m.RegisterPage })));
const VerifyEmailPage = lazy(() => import('@/pages/auth/VerifyEmailPage').then((m) => ({ default: m.VerifyEmailPage })));
const AccountPage = lazy(() => import('@/pages/account/AccountPage').then((m) => ({ default: m.AccountPage })));

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
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
