import { cn } from '@/lib/utils';

interface FormMessageProps {
  message?: string;
  variant?: 'error' | 'success' | 'info';
  className?: string;
}

const variantClasses = {
  error: 'text-error-500',
  success: 'text-success-500',
  info: 'text-neutral-600',
};

export function FormMessage({ message, variant = 'error', className }: FormMessageProps) {
  if (!message) return null;
  return (
    <p className={cn('mt-1 text-xs', variantClasses[variant], className)} role="alert">
      {message}
    </p>
  );
}
