export function formatPrice(value: string | null | undefined, currency?: string): string {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return value;
  }
  const precision = Math.abs(numeric) >= 1000 ? 2 : 4;
  const formatted = numeric.toLocaleString(undefined, {
    maximumFractionDigits: precision,
  });
  return currency ? `${formatted} ${currency}` : formatted;
}

export function formatPct(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return value;
  }
  return `${(numeric * 100).toFixed(2)}%`;
}

export function pctInputToDecimal(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const numeric = Number(trimmed);
  if (!Number.isFinite(numeric)) {
    return null;
  }
  return String(numeric / 100);
}

export function decimalToPctInput(value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "";
  }
  return String(numeric * 100);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "N/A";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function addDays(dateValue: string, days: number): string {
  const date = new Date(`${dateValue}T00:00:00`);
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

export function subtractMonths(dateValue: string, months: number): string {
  const date = new Date(`${dateValue}T00:00:00`);
  const day = date.getDate();
  date.setMonth(date.getMonth() - months);
  if (date.getDate() !== day) {
    date.setDate(0);
  }
  return date.toISOString().slice(0, 10);
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
