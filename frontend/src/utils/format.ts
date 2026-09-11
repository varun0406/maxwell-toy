export function formatCurrency(amount: number | string): string {
  const num = Number(amount);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(num);
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}
