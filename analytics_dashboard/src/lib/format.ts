export const fmtInt = (n: number): string =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n);

export const fmtTND = (n: number): string =>
  `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n)} TND`;

export const fmtPct = (n: number): string =>
  `${(n * 100).toFixed(1)}%`;
