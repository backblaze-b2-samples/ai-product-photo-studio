import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { SkuLibrary } from "@/components/library/sku-library";

export default async function LibraryPage({
  searchParams,
}: {
  searchParams: Promise<{ sku?: string }>;
}) {
  const { sku } = await searchParams;

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">{sku ? `Library · ${sku}` : "Library"}</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            {sku
              ? `Reference photos and every generated shot for ${sku}, scoped to its B2 prefix.`
              : "Per-SKU asset explorer. Pick a SKU to see its reference photo and generations."}
          </p>
        </div>
        {sku && (
          <Link
            href="/library"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-3 w-3" />
            All SKUs
          </Link>
        )}
      </div>
      <div className="animate-fade-in-up stagger-2">
        <SkuLibrary sku={sku} />
      </div>
    </div>
  );
}
