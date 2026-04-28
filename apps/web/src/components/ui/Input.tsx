import { cn } from '@/lib/utils';
import { forwardRef, type InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

/**
 * Native HTML validation attributes (required, min/maxLength, pattern) are
 * stripped so Chromium doesn't render its own validation UI — all validation
 * goes through zod via react-hook-form. `aria-*` equivalents are forwarded
 * for assistive tech.
 *
 * The component forwards refs so react-hook-form's `register()` can bind to
 * the underlying DOM element (otherwise RHF can't read the field value and
 * emits the default "Required" error).
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    error,
    className,
    required,
    minLength: _minLength,
    maxLength: _maxLength,
    pattern: _pattern,
    min: _min,
    max: _max,
    ...props
  },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        'w-full rounded-md border bg-neutral-0 px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400',
        'transition-colors focus-visible:outline-none focus-visible:shadow-focus',
        error ? 'border-error-500' : 'border-neutral-200 hover:border-neutral-400',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      aria-required={required || undefined}
      aria-invalid={error || undefined}
      {...props}
    />
  );
});
