"use client";

import { usePreviewUrl } from "@/lib/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface PresignedImageProps {
  /** B2 object key (e.g. skus/<sku>/generations/.../foo.png). */
  objectKey: string | null | undefined;
  alt: string;
  className?: string;
}

/**
 * Renders a B2 object in an <img> via the app's inline presigned-preview
 * endpoint (`/files/{key}/preview`). The shared bucket is private, so embedding
 * the static public URL would 401 in the browser; fetching a short-lived inline
 * presigned URL renders the image regardless of bucket ACL. Mirrors the pattern
 * the Files explorer already uses for its preview modal.
 *
 * All fetching flows through the `usePreviewUrl` TanStack Query hook — no bare
 * useEffect+fetch (per AGENTS.md §3).
 */
export function PresignedImage({ objectKey, alt, className }: PresignedImageProps) {
  const { data, isLoading } = usePreviewUrl(objectKey ?? undefined, !!objectKey);
  const url = data?.url;

  if (isLoading || !url) {
    return <Skeleton className={cn("bg-muted", className)} />;
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={url} alt={alt} className={className} />
  );
}
