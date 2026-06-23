"use client";

import { Package, Images, HardDrive, Wand2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useFileStats, useSkus } from "@/lib/queries";

export function StatsCards() {
  const { data: stats, isLoading: statsLoading, error, refetch } = useFileStats();
  const { data: skus = [], isLoading: skusLoading } = useSkus();

  // Surface fetch failures inline rather than rendering zeros — that lies to
  // the user about the bucket state when really the API is just unreachable.
  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const isLoading = statsLoading || skusLoading;
  const totalShots = skus.reduce((sum, s) => sum + s.shot_count, 0);

  const cards = [
    { title: "SKUs", value: skus.length, icon: Package },
    { title: "Generated Shots", value: totalShots, icon: Images },
    { title: "Storage Used", value: stats?.total_size_human ?? "0 B", icon: HardDrive },
    { title: "Generations Today", value: stats?.uploads_today ?? 0, icon: Wand2 },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="stat-value">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
