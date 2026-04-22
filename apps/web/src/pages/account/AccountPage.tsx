import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, AlertCircle } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { useResendVerification } from '@/features/auth/hooks';
import { useAuthStore } from '@/stores/auth';

export function AccountPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user)!;
  const [resendSuccess, setResendSuccess] = useState(false);

  const { mutate: resend, isPending } = useResendVerification();

  function handleResend() {
    resend(undefined, { onSuccess: () => setResendSuccess(true) });
  }

  return (
    <div className="space-y-8">
      <h1 className="font-display text-3xl font-bold text-brand-graphite-900">
        {t('account.title')}
      </h1>

      {!user.emailVerified && (
        <div className="flex items-start gap-3 rounded-lg border border-warning-500/30 bg-warning-500/10 p-4">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-warning-500" aria-hidden="true" />
          <div className="flex-1">
            <p className="text-sm font-medium text-brand-graphite-900">
              {t('account.verificationBanner')}
            </p>
            {resendSuccess ? (
              <p className="mt-1 text-xs text-success-500">{t('auth.verify.resendSuccess')}</p>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                loading={isPending}
                onClick={handleResend}
                className="mt-2 px-0 text-brand-orange-500 hover:text-brand-orange-600 hover:bg-transparent"
              >
                {t('account.resendVerification')}
              </Button>
            )}
          </div>
        </div>
      )}

      <div className="divide-y divide-neutral-100 rounded-xl border border-neutral-100 bg-neutral-0">
        <Row label={t('account.name')}>
          {[user.firstName, user.lastName].filter(Boolean).join(' ') || '—'}
        </Row>
        <Row label={t('account.email')}>
          <span className="flex items-center gap-2">
            {user.email}
            {user.emailVerified ? (
              <CheckCircle size={14} className="text-success-500" aria-label={t('account.verified')} />
            ) : (
              <AlertCircle size={14} className="text-warning-500" aria-label={t('account.notVerified')} />
            )}
          </span>
        </Row>
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-5 py-4">
      <span className="text-sm text-neutral-600">{label}</span>
      <span className="text-sm font-medium text-brand-graphite-900">{children}</span>
    </div>
  );
}
