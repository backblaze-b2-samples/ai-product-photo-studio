import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function humanizeBytes(bytes: number) {
  for (const unit of ["B", "KB", "MB", "GB"]) {
    if (Math.abs(bytes) < 1024) {
      // No decimals for bytes, one decimal for larger units
      return unit === "B"
        ? `${Math.round(bytes)} ${unit}`
        : `${bytes.toFixed(1)} ${unit}`;
    }
    bytes /= 1024;
  }
  return `${bytes.toFixed(1)} TB`;
}

const dateTimeFormatOptions = {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
} satisfies Intl.DateTimeFormatOptions;

const monthDayFormatOptions = {
  month: "short",
  day: "numeric",
} satisfies Intl.DateTimeFormatOptions;

const dateFormatters = {
  dateTime: (date: Date) =>
    date.toLocaleDateString("en-US", dateTimeFormatOptions),
  dateOnly: (date: Date) => date.toLocaleDateString(),
  monthDay: (date: Date) =>
    date.toLocaleDateString("en-US", monthDayFormatOptions),
  localDateTime: (date: Date) => date.toLocaleString(),
} satisfies Record<string, (date: Date) => string>;

export type DateFormatVariant = keyof typeof dateFormatters;

export function formatDate(
  dateStr: string,
  variant: DateFormatVariant = "dateTime",
) {
  return dateFormatters[variant](new Date(dateStr));
}
