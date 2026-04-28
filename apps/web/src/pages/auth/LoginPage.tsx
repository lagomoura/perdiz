import { useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { FormMessage } from '@/components/ui/FormMessage';
import { useLogin, isApiError } from '@/features/auth/hooks';
import { loginSchema, type LoginFormValues } from '@/features/auth/schemas';
import { getErrorMessage } from '@/lib/errors';
import { useAuthStore } from '@/stores/auth';

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const fromParam = searchParams.get('from');
  const user = useAuthStore((s) => s.user);

  const destinationFor = (role: 'user' | 'admin'): string =>
    fromParam ?? (role === 'admin' ? '/admin' : '/mi-cuenta');

  useEffect(() => {
    if (user) navigate(destinationFor(user.role), { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, navigate, fromParam]);

  const { mutate: doLogin, isPending, error } = useLogin();

  const errorMessage = isApiError(error)
    ? getErrorMessage(error.code, error.message)
    : null;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    mode: 'onTouched',
    defaultValues: { email: '', password: '' },
  });

  function onSubmit(values: LoginFormValues) {
    doLogin(values, {
      onSuccess: ({ user: loggedUser }) => {
        navigate(destinationFor(loggedUser.role), { replace: true });
      },
    });
  }

  return (
    <>
      <h1 className="mb-6 font-display text-2xl font-bold text-neutral-900">
        {t('auth.login.title')}
      </h1>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        <div>
          <Label htmlFor="email">{t('auth.login.email')}</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            error={!!errors.email}
            className="mt-1"
            {...register('email')}
          />
          <FormMessage message={errors.email?.message} />
        </div>

        <div>
          <div className="flex items-center justify-between">
            <Label htmlFor="password">{t('auth.login.password')}</Label>
            <Link
              to="/auth/olvide-password"
              className="text-xs text-neutral-600 hover:text-neutral-900"
            >
              {t('auth.login.forgotPassword')}
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            error={!!errors.password}
            className="mt-1"
            {...register('password')}
          />
          <FormMessage message={errors.password?.message} />
        </div>

        {errorMessage && (
          <FormMessage message={errorMessage} />
        )}

        <Button type="submit" loading={isPending} className="w-full" size="lg">
          {isPending ? t('auth.login.submitting') : t('auth.login.submit')}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-neutral-600">
        {t('auth.login.subtitle')}{' '}
        <Link
          to="/auth/registrarse"
          className="font-medium text-brand-orange-500 hover:text-brand-orange-600"
        >
          {t('auth.login.subtitleLink')}
        </Link>
      </p>
    </>
  );
}
