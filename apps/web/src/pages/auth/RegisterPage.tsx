import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { FormMessage } from '@/components/ui/FormMessage';
import { useRegister, isApiError } from '@/features/auth/hooks';
import { registerSchema, type RegisterFormValues } from '@/features/auth/schemas';
import { getErrorMessage } from '@/lib/errors';

export function RegisterPage() {
  const { t } = useTranslation();
  const [succeeded, setSucceeded] = useState(false);

  const { mutate: doRegister, isPending, error } = useRegister();

  const errorMessage = isApiError(error)
    ? getErrorMessage(error.code, error.message)
    : null;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    mode: 'onTouched',
    defaultValues: { email: '', password: '', firstName: '', lastName: '' },
  });

  function onSubmit(values: RegisterFormValues) {
    doRegister(
      { email: values.email, password: values.password, firstName: values.firstName, lastName: values.lastName },
      { onSuccess: () => setSucceeded(true) },
    );
  }

  if (succeeded) {
    return (
      <div className="py-4 text-center">
        <CheckCircle className="mx-auto mb-4 h-12 w-12 text-success-500" aria-hidden="true" />
        <h2 className="font-display text-xl font-bold text-neutral-900">
          {t('auth.register.successTitle')}
        </h2>
        <p className="mt-2 text-sm text-neutral-600">{t('auth.register.successMessage')}</p>
        <Link
          to="/auth/ingresar"
          className="mt-6 inline-block text-sm font-medium text-brand-orange-500 hover:text-brand-orange-600"
        >
          {t('auth.login.subtitle')} {t('auth.login.subtitleLink')}
        </Link>
      </div>
    );
  }

  return (
    <>
      <h1 className="mb-6 font-display text-2xl font-bold text-neutral-900">
        {t('auth.register.title')}
      </h1>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="firstName">{t('auth.register.firstName')}</Label>
            <Input id="firstName" autoComplete="given-name" className="mt-1" {...register('firstName')} />
          </div>
          <div>
            <Label htmlFor="lastName">{t('auth.register.lastName')}</Label>
            <Input id="lastName" autoComplete="family-name" className="mt-1" {...register('lastName')} />
          </div>
        </div>

        <div>
          <Label htmlFor="email">{t('auth.register.email')}</Label>
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
          <Label htmlFor="password">{t('auth.register.password')}</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            error={!!errors.password}
            className="mt-1"
            {...register('password')}
          />
          <FormMessage message={errors.password?.message} />
          {!errors.password && (
            <p className="mt-1 text-xs text-neutral-400">{t('auth.register.passwordHint')}</p>
          )}
        </div>

        {errorMessage && <FormMessage message={errorMessage} />}

        <Button type="submit" loading={isPending} className="w-full" size="lg">
          {isPending ? t('auth.register.submitting') : t('auth.register.submit')}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-neutral-600">
        {t('auth.register.subtitle')}{' '}
        <Link
          to="/auth/ingresar"
          className="font-medium text-brand-orange-500 hover:text-brand-orange-600"
        >
          {t('auth.register.subtitleLink')}
        </Link>
      </p>
    </>
  );
}
