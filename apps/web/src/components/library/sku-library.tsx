"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Images, Package, ShieldCheck } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useSku, useSkus } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import type { SkuAsset } from "@ai-product-photo-studio/shared";

function AssetCard({ asset }: { asset: SkuAsset }) {
  return (
    <figure className="rounded-lg border border-border overflow-hidden">
      {asset.url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={asset.url}
          alt={asset.filename}
          className="aspect-square w-full object-cover bg-muted"
        />
      ) : (
        <div className="aspect-square w-full bg-muted" />
      )}
      <figcaption className="p-2.5 space-y-1.5">
        <p className="truncate text-xs font-medium">{asset.filename}</p>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="secondary" className="text-[10px]">
            {asset.size_human}
          </Badge>
          {asset.run_id && (
            <Badge variant="outline" className="text-[10px] font-mono">
              {asset.run_id.slice(0, 8)}
            </Badge>
          )}
        </div>
        <p className="flex items-center gap-1 text-[10px] text-muted-foreground">
          <ShieldCheck className="h-3 w-3 text-[var(--success)]" />
          {formatDate(asset.uploaded_at)}
        </p>
      </figcaption>
    </figure>
  );
}

function SkuPicker() {
  const { data: skus = [], isLoading, error, refetch } = useSkus();

  if (isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (skus.length === 0) {
    return (
      <EmptyState
        icon={Package}
        title="No SKUs yet"
        description="Generate shots in the Studio to populate your library."
      />
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {skus.map((s) => (
        <Link key={s.sku} href={`/library?sku=${encodeURIComponent(s.sku)}`}>
          <Card className="card-hover h-full">
            <CardHeader className="py-4 px-5 flex flex-row items-center justify-between">
              <CardTitle className="card-title">{s.sku}</CardTitle>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="px-5 pb-4 text-xs text-muted-foreground space-y-1">
              <div>
                {s.reference_count} reference · {s.shot_count} shots
              </div>
              <div>{s.total_size_human} stored</div>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

export function SkuLibrary({ sku }: { sku?: string }) {
  const [activeSku] = useState(sku);
  const { data, isLoading, error, refetch } = useSku(activeSku);

  if (!activeSku) {
    return <SkuPicker />;
  }

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="aspect-square w-full" />
        ))}
      </div>
    );
  }
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;

  const references = data?.references ?? [];
  const shots = (data?.shots ?? []).filter((a) => !a.is_manifest);

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Package className="h-4 w-4 text-muted-foreground" />
          Reference photos
        </h2>
        {references.length === 0 ? (
          <EmptyState
            icon={Package}
            title="No reference photos"
            description="Upload a product photo in the Studio for this SKU."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {references.map((a) => (
              <AssetCard key={a.key} asset={a} />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Images className="h-4 w-4 text-muted-foreground" />
          Generated shots
        </h2>
        {shots.length === 0 ? (
          <EmptyState
            icon={Images}
            title="No generations yet"
            description="Generate shots for this SKU in the Studio."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {shots.map((a) => (
              <AssetCard key={a.key} asset={a} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
