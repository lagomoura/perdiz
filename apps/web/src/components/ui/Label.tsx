import { cn } from '@/lib/utils';
import type { LabelHTMLAttributes } from 'react';

export function Label({ className, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn('block text-sm font-medium text-neutral-900', className)}
      {...props}
    />
  );
}
