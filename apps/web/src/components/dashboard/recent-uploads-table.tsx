"use client";

import Link from "next/link";
import { ArrowRight, Package } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { ClientFormattedDate } from "@/components/client-formatted-date";
import { useSkus } from "@/lib/queries";

// "Recent generations" table — most recently active SKUs, newest first.
export function RecentUploadsTable() {
  const { data: skus = [], isLoading, error, refetch } = useSkus();

  const recent = [...skus]
    .sort((a, b) => {
      const at = a.latest_at ? Date.parse(a.latest_at) : 0;
      const bt = b.latest_at ? Date.parse(b.latest_at) : 0;
      return bt - at;
    })
    .slice(0, 8);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Generations</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/library"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View library
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : recent.length === 0 ? (
          <EmptyState
            icon={Package}
            title="No generations yet"
            description="Head to Studio to generate your first product shots."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[32%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  SKU
                </TableHead>
                <TableHead className="w-[18%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Shots
                </TableHead>
                <TableHead className="w-[22%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Storage
                </TableHead>
                <TableHead className="w-[28%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Last active
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((s) => (
                <TableRow key={s.sku} className="table-row-hover">
                  <TableCell className="font-medium">
                    <Link
                      href={`/library?sku=${encodeURIComponent(s.sku)}`}
                      className="truncate hover:underline"
                    >
                      {s.sku}
                    </Link>
                  </TableCell>
                  <TableCell className="tabular-nums text-muted-foreground">
                    {s.shot_count}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                    {s.total_size_human}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {s.latest_at ? (
                      <ClientFormattedDate value={s.latest_at} />
                    ) : (
                      "—"
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
