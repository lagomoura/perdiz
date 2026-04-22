import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
}

export function Logo({ className }: LogoProps) {
  return (
    <img
      src="/brand/logo.svg"
      alt="p3rDiz — Soluciones 3D"
      className={cn('w-auto', className)}
    />
  );
}
