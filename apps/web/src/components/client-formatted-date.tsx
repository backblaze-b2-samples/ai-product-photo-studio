"use client";

import { formatDate, type DateFormatVariant } from "@/lib/utils";

interface ClientFormattedDateProps {
  value: string;
  variant?: DateFormatVariant;
}

export function ClientFormattedDate({
  value,
  variant = "dateTime",
}: ClientFormattedDateProps) {
  const formatted =
    typeof window === "undefined" ? "" : formatDate(value, variant);

  return <span suppressHydrationWarning>{formatted}</span>;
}
