import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CheckCircle, XCircle } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { useVerifyEmail, useResendVerification } from '@/features/auth/hooks';
import { useAuthStore } from '@/stores/auth';

export function VerifyEmailPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const user = useAuthStore((s) => s.user);
  const setAuth = useAuthStore((s) => s.setAuth);
  const accessToken = useAuthStore((s) => s.accessToken);
  const [resendSuccess, setResendSuccess] = useState(false);

  const { mutate: verify, isPending: verifying, isSuccess, isError } = useVerifyEmail();
  const { mutate: resend, isPending: resending } = useResendVerification();

  useEffect(() => {
    if (token) {
      verify(token, {
        onSuccess: (verifiedUser) => {
          if (user && accessToken) {
            setAuth({ ...user, emailVerified: true }, accessToken);
          }
          void verifiedUser;
        },
      });
    }
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleResend() {
    resend(undefined, {
      onSuccess: () => setResendSuccess(true),
    });
  }

  if (!token) {
    return (
      <div className="py-4 text-center">
        <h2 className="font-display text-xl font-bold text-brand-graphite-900">
          {t('auth.verify.title')}
        </h2>
        <p className="mt-2 text-sm text-neutral-600">{t('auth.verify.noToken')}</p>
        {user && !user.emailVerified && (
          <div className="mt-6">
            {resendSuccess ? (
              <p className="text-sm text-success-500">{t('auth.verify.resendSuccess')}</p>
            ) : (
              <Button onClick={handleResend} loading={resending} variant="secondary" size="sm">
                {resending ? t('auth.verify.resending') : t('auth.verify.resend')}
              </Button>
            )}
          </div>
        )}
      </div>
    );
  }

  if (verifying) {
    return (
      <div className="py-8 text-center text-sm text-neutral-600">
        {t('auth.verify.verifying')}
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="py-4 text-center">
        <CheckCircle className="mx-auto mb-4 h-12 w-12 text-success-500" aria-hidden="true" />
        <h2 className="font-display text-xl font-bold text-brand-graphite-900">
          {t('auth.verify.successTitle')}
        </h2>
        <p className="mt-2 text-sm text-neutral-600">{t('auth.verify.successMessage')}</p>
        <Link
          to="/auth/ingresar"
          className="mt-6 inline-block text-sm font-medium text-brand-orange-500 hover:text-brand-orange-600"
        >
          {t('auth.login.submit')}
        </Link>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-4 text-center">
        <XCircle className="mx-auto mb-4 h-12 w-12 text-error-500" aria-hidden="true" />
        <h2 className="font-display text-xl font-bold text-brand-graphite-900">
          {t('auth.verify.errorTitle')}
        </h2>
        <p className="mt-2 text-sm text-neutral-600">{t('auth.verify.errorMessage')}</p>
        {user && !user.emailVerified && (
          <div className="mt-6">
            {resendSuccess ? (
              <p className="text-sm text-success-500">{t('auth.verify.resendSuccess')}</p>
            ) : (
              <Button onClick={handleResend} loading={resending} variant="secondary" size="sm">
                {resending ? t('auth.verify.resending') : t('auth.verify.resend')}
              </Button>
            )}
          </div>
        )}
      </div>
    );
  }

  return null;
}
