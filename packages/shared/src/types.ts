export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific (product photos are raster images only)
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Studio (product-photo generation) ---

export interface GenerationRequest {
  scene_prompt: string;
  reference_key: string;
  angle_presets: string[];
  season_presets: string[];
  variants: number | null;
  size: string | null;
  quality: string | null;
}

export interface GeneratedShot {
  key: string | null;
  url: string | null;
  sha256: string | null;
  prompt: string;
  size: string;
  quality: string;
  cost_usd: number | null;
  width: number | null;
  height: number | null;
}

export interface GenerationResult {
  sku: string;
  run_id: string;
  manifest_uri: string | null;
  canonical_hash: string | null;
  shots: GeneratedShot[];
  failed: number;
}

export interface SkuSummary {
  sku: string;
  reference_count: number;
  shot_count: number;
  total_size_bytes: number;
  total_size_human: string;
  latest_at: string | null;
}

export interface SkuAsset {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  run_id: string | null;
  is_manifest: boolean;
}

export interface SkuDetail {
  sku: string;
  references: SkuAsset[];
  shots: SkuAsset[];
}
