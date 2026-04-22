export function Spinner({ label = 'Cargando' }: { label?: string }) {
  return (
    <div className="flex min-h-dvh items-center justify-center">
      <div
        className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-200 border-t-brand-orange-500"
        aria-label={label}
        role="status"
      />
    </div>
  );
}
