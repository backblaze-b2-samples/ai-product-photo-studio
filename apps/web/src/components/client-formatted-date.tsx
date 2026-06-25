"use client";

import { useEffect, useState } from "react";

import { formatDate, type DateFormatVariant } from "@/lib/utils";

interface ClientFormattedDateProps {
  value: string;
  variant?: DateFormatVariant;
}

export function ClientFormattedDate({
  value,
  variant = "dateTime",
}: ClientFormattedDateProps) {
  const [formatted, setFormatted] = useState("");

  useEffect(() => {
    setFormatted(formatDate(value, variant));
  }, [value, variant]);

  return <span suppressHydrationWarning>{formatted}</span>;
}
