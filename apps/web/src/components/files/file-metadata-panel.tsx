"use client";

import type { ReactNode } from "react";

import { ClientFormattedDate } from "@/components/client-formatted-date";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { FileMetadataDetail } from "@ai-product-photo-studio/shared";

interface FileMetadataPanelProps {
  metadata: FileMetadataDetail;
}

function MetaRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono text-right max-w-[60%] truncate">{value}</span>
    </div>
  );
}

export function FileMetadataPanel({ metadata }: FileMetadataPanelProps) {
  return (
    <Card>
      <CardHeader className="pb-3 px-5 pt-5">
        <CardTitle className="card-title">File Details</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 px-5 pb-5">
        <MetaRow label="Filename" value={metadata.filename} />
        <MetaRow label="Size" value={metadata.size_human} />
        <MetaRow label="Type" value={metadata.mime_type} />
        <MetaRow label="Extension" value={metadata.extension || "none"} />

        <Separator />
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Checksums
        </p>
        <MetaRow label="MD5" value={metadata.md5} />
        <MetaRow label="SHA-256" value={metadata.sha256} />

        {/* Image metadata */}
        {metadata.image_width && metadata.image_height && (
          <>
            <Separator />
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Image
            </p>
            <MetaRow
              label="Dimensions"
              value={`${metadata.image_width} x ${metadata.image_height}`}
            />
            {metadata.exif && (
              <div className="space-y-1">
                {Object.entries(metadata.exif)
                  .slice(0, 8)
                  .map(([key, val]) => (
                    <MetaRow key={key} label={key} value={val} />
                  ))}
              </div>
            )}
          </>
        )}

        <Separator />
        <MetaRow
          label="Uploaded"
          value={
            <ClientFormattedDate
              value={metadata.uploaded_at}
              variant="numericDateTime"
            />
          }
        />
      </CardContent>
    </Card>
  );
}
