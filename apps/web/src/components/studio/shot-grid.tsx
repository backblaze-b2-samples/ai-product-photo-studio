"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PresignedImage } from "@/components/presigned-image";
import type { GenerationResult } from "@ai-product-photo-studio/shared";

export function ShotGrid({ result }: { result: GenerationResult }) {
  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5 flex flex-row items-center justify-between">
        <div>
          <CardTitle className="card-title">
            {result.shots.length} shot{result.shots.length === 1 ? "" : "s"} for{" "}
            {result.sku}
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-1 font-mono">
            run {result.run_id}
          </p>
        </div>
        <Link
          href={`/library?sku=${encodeURIComponent(result.sku)}`}
          className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          View in library
          <ArrowRight className="h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent className="p-5">
        {result.failed > 0 && (
          <p className="mb-3 text-xs text-[var(--blaze-amber,#d97706)]">
            {result.failed} variant{result.failed === 1 ? "" : "s"} failed to
            generate.
          </p>
        )}
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {result.shots.map((shot, i) => (
            <figure
              key={shot.key ?? i}
              className="group rounded-lg border border-border overflow-hidden"
            >
              {shot.key ? (
                <PresignedImage
                  objectKey={shot.key}
                  alt={shot.prompt}
                  className="aspect-square w-full object-cover bg-muted"
                />
              ) : (
                <div className="aspect-square w-full bg-muted" />
              )}
              <figcaption className="p-3 space-y-2">
                <p className="text-xs text-muted-foreground line-clamp-2">
                  {shot.prompt}
                </p>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="secondary" className="text-[10px]">
                    {shot.size}
                  </Badge>
                  <Badge variant="secondary" className="text-[10px]">
                    {shot.quality}
                  </Badge>
                  {shot.cost_usd !== null && shot.cost_usd !== undefined && (
                    <Badge variant="outline" className="text-[10px]">
                      ${shot.cost_usd.toFixed(2)}
                    </Badge>
                  )}
                </div>
                {shot.sha256 && (
                  <p className="flex items-center gap-1 text-[10px] font-mono text-muted-foreground">
                    <ShieldCheck className="h-3 w-3 text-[var(--success)]" />
                    sha256 {shot.sha256.slice(0, 12)}…
                  </p>
                )}
              </figcaption>
            </figure>
          ))}
        </div>
        {result.manifest_uri && (
          <p className="mt-4 text-[11px] text-muted-foreground break-all">
            Provenance manifest:{" "}
            <a
              href={result.manifest_uri}
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-foreground"
            >
              {result.manifest_uri}
            </a>
          </p>
        )}
      </CardContent>
    </Card>
  );
}
