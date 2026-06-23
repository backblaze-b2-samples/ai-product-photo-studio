"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { ImageUp, Wand2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { GeneratingLoader } from "@/components/ui/generating-loader";
import { PresignedImage } from "@/components/presigned-image";
import { ShotGrid } from "./shot-grid";
import { ApiError, uploadFile } from "@/lib/api-client";
import { useGenerateShots } from "@/lib/queries";
import type {
  FileUploadResponse,
  GenerationResult,
} from "@ai-product-photo-studio/shared";

const ANGLE_OPTIONS = ["front", "three-quarter", "top-down", "close-up detail"];
const SEASON_OPTIONS = ["spring", "summer", "autumn", "winter holiday"];
const QUALITIES = ["low", "medium", "high"];
const SIZES = ["1024x1024", "1536x1024", "1024x1536"];

function toggle(list: string[], value: string): string[] {
  return list.includes(value)
    ? list.filter((v) => v !== value)
    : [...list, value];
}

export function StudioForm() {
  const [sku, setSku] = useState("");
  const [scenePrompt, setScenePrompt] = useState("");
  const [reference, setReference] = useState<FileUploadResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [angles, setAngles] = useState<string[]>(["front"]);
  const [seasons, setSeasons] = useState<string[]>([]);
  const [variants, setVariants] = useState(3);
  const [quality, setQuality] = useState("medium");
  const [size, setSize] = useState("1024x1024");
  const [result, setResult] = useState<GenerationResult | null>(null);

  const generate = useGenerateShots();

  const onReferenceSelected = useCallback(
    async (file: File) => {
      if (!sku.trim()) {
        toast.error("Enter a SKU before uploading a reference photo.");
        return;
      }
      setUploading(true);
      try {
        const res = await uploadFile(file, undefined, sku.trim());
        setReference(res);
        toast.success("Reference photo uploaded.");
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [sku],
  );

  const onGenerate = useCallback(() => {
    if (!sku.trim() || !reference?.key || !scenePrompt.trim()) {
      toast.error("SKU, reference photo, and scene prompt are required.");
      return;
    }
    setResult(null);
    generate.mutate(
      {
        sku: sku.trim(),
        req: {
          scene_prompt: scenePrompt.trim(),
          reference_key: reference.key,
          angle_presets: angles,
          season_presets: seasons,
          variants,
          size,
          quality,
        },
      },
      {
        onSuccess: (res) => {
          setResult(res);
          toast.success(
            `Generated ${res.shots.length} shot${res.shots.length === 1 ? "" : "s"} for ${res.sku}.`,
          );
        },
        onError: (err) => {
          // 408 = the request timed out client-side. The server may have
          // finished the run, so the shots can already be in B2 — point the
          // user to the Library (which onSettled has just refreshed) instead
          // of implying the work was lost.
          if (err instanceof ApiError && err.status === 408) {
            toast.error(
              `Generation is taking longer than expected. If it completed, your shots will appear in the Library for ${sku.trim()}.`,
            );
            return;
          }
          toast.error(err instanceof Error ? err.message : "Generation failed");
        },
      },
    );
  }, [sku, reference, scenePrompt, angles, seasons, variants, size, quality, generate]);

  const isGenerating = generate.isPending;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr]">
      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">New generation</CardTitle>
        </CardHeader>
        <CardContent className="p-5 space-y-5">
          <div className="space-y-1.5">
            <Label htmlFor="sku">SKU</Label>
            <Input
              id="sku"
              placeholder="e.g. CANDLE-001"
              value={sku}
              onChange={(e) => setSku(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              The product identifier. References and generations are stored
              under this SKU.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label>Reference photo</Label>
            <label
              className={`flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-muted/30 px-4 py-6 text-center transition-colors ${
                uploading
                  ? "cursor-wait opacity-70"
                  : "cursor-pointer hover:bg-muted/50"
              }`}
            >
              <ImageUp className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {uploading
                  ? "Uploading…"
                  : reference
                    ? reference.filename
                    : "Click to upload a product photo (PNG, JPEG, WebP)"}
              </span>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                disabled={uploading}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) onReferenceSelected(f);
                  // reset so re-selecting the same file fires onChange again
                  e.target.value = "";
                }}
              />
            </label>
            {reference?.key && (
              <PresignedImage
                objectKey={reference.key}
                alt="Reference"
                className="mt-2 h-28 w-28 rounded-md object-cover border border-border"
              />
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="scene">Scene prompt</Label>
            <Textarea
              id="scene"
              rows={3}
              placeholder="e.g. on a marble kitchen counter beside fresh herbs, soft morning light"
              value={scenePrompt}
              onChange={(e) => setScenePrompt(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label>Angles</Label>
            <div className="flex flex-wrap gap-2">
              {ANGLE_OPTIONS.map((a) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => setAngles((prev) => toggle(prev, a))}
                  className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                    angles.includes(a)
                      ? "border-primary bg-primary/10 text-foreground"
                      : "border-border text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {a}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label>Seasonal variants</Label>
            <div className="flex flex-wrap gap-2">
              {SEASON_OPTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSeasons((prev) => toggle(prev, s))}
                  className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                    seasons.includes(s)
                      ? "border-primary bg-primary/10 text-foreground"
                      : "border-border text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="variants">Variants</Label>
              <Input
                id="variants"
                type="number"
                min={1}
                max={6}
                value={variants}
                onChange={(e) => setVariants(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Quality</Label>
              <Select value={quality} onValueChange={setQuality}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {QUALITIES.map((q) => (
                    <SelectItem key={q} value={q}>
                      {q}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Size</Label>
              <Select value={size} onValueChange={setSize}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SIZES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button
            className="w-full"
            onClick={onGenerate}
            disabled={isGenerating || uploading}
          >
            <Wand2 className="h-4 w-4" />
            {isGenerating ? "Generating…" : "Generate shots"}
          </Button>
          <p className="text-xs text-muted-foreground">
            Powered by OpenAI gpt-image-1 (reference-faithful edits) via the
            Genblaze SDK. Defaults (medium / 1024×1024 / 3 variants) cost
            ~$0.21 per generation.
          </p>
        </CardContent>
      </Card>

      <div className="min-h-[320px]">
        {isGenerating ? (
          <Card className="h-full">
            <CardContent className="flex h-full min-h-[320px] flex-col items-center justify-center gap-4">
              <GeneratingLoader size="lg" variant="stars" label="Generating shots…" />
              <p className="text-sm text-muted-foreground">
                Editing your reference photo into {variants} scene
                {variants === 1 ? "" : "s"} and writing each to B2.
              </p>
            </CardContent>
          </Card>
        ) : result ? (
          <ShotGrid result={result} />
        ) : (
          <Card className="h-full">
            <CardContent className="flex h-full min-h-[320px] flex-col items-center justify-center gap-2 text-center">
              <Wand2 className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Your generated product shots will appear here.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
