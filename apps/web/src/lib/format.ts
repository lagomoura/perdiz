const arsFormatter = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  maximumFractionDigits: 0,
});

export function formatArs(cents: number): string {
  return arsFormatter.format(Math.round(cents / 100));
}
