import type {
  DailyUploadCount,
  FileMetadata,
  FileUploadResponse,
  GenerationRequest,
  GenerationResult,
  SkuAsset,
  SkuDetail,
  SkuSummary,
  UploadStats,
} from "@ai-product-photo-studio/shared";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Typed API error with HTTP status code for caller-side branching. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** True for 408, 429, 500, 502, 503, 504 — worth retrying. */
  get isRetryable(): boolean {
    return [408, 429, 500, 502, 503, 504].includes(this.status);
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  // Optional client-side deadline. Without it a stalled connection (e.g. an
  // edge/proxy that dropped a long request after the server finished its work)
  // would leave the caller's promise pending forever. On expiry we abort and
  // surface a 408 so callers can recover instead of hanging.
  timeoutMs?: number,
): Promise<T> {
  const controller = new AbortController();
  const timer = timeoutMs
    ? setTimeout(() => controller.abort(), timeoutMs)
    : null;
  try {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}${path}`, {
        ...init,
        signal: controller.signal,
      });
    } catch {
      if (controller.signal.aborted) {
        throw new ApiError(
          "Request timed out. The work may still be completing on the server.",
          408,
        );
      }
      // Network failure (offline, DNS, CORS, etc.)
      throw new ApiError("Network error — check your connection", 0);
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(
        body.detail || `API error: ${res.status}`,
        res.status,
      );
    }
    return res.json();
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export async function getHealth() {
  return apiFetch<{ status: string; b2_connected: boolean }>("/health");
}

export async function getFiles(prefix = "", limit = 100) {
  return apiFetch<FileMetadata[]>(
    `/files?prefix=${encodeURIComponent(prefix)}&limit=${limit}`
  );
}

export async function getFileStats() {
  return apiFetch<UploadStats>("/files/stats");
}

export async function getUploadActivity(days = 7) {
  return apiFetch<DailyUploadCount[]>(`/files/stats/activity?days=${days}`);
}

export async function getFile(key: string) {
  return apiFetch<FileMetadata>(`/files/${key}`);
}

export async function getDownloadUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/download`);
}

/** Preview-only presigned URL — does NOT increment the download counter. */
export async function getPreviewUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/preview`);
}

export async function deleteFile(key: string) {
  return apiFetch<{ deleted: boolean; key: string }>(`/files/${key}`, {
    method: "DELETE",
  });
}

// --- Studio (product-photo generation) ---

export async function listSkus() {
  return apiFetch<SkuSummary[]>("/skus");
}

export async function getSku(sku: string) {
  return apiFetch<SkuDetail>(`/skus/${encodeURIComponent(sku)}`);
}

export async function getSkuShots(sku: string) {
  return apiFetch<SkuAsset[]>(`/skus/${encodeURIComponent(sku)}/shots`);
}

// Sits just above the backend's studio_run_timeout (300s): a run that is going
// to succeed returns within the server cap, so a longer wait means the
// connection has stalled. Bounding it here guarantees the UI never spins
// forever — on expiry the mutation settles and we refresh from B2 (see
// useGenerateShots), where any completed shots have already landed.
const GENERATE_TIMEOUT_MS = 360_000;

export async function generateShots(sku: string, req: GenerationRequest) {
  return apiFetch<GenerationResult>(
    `/skus/${encodeURIComponent(sku)}/generate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    },
    GENERATE_TIMEOUT_MS,
  );
}

export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void,
  sku?: string,
): Promise<FileUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);
    if (sku) formData.append("sku", sku);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new ApiError(body.detail || `Upload failed: ${xhr.status}`, xhr.status));
        } catch {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      }
    });

    xhr.addEventListener("error", () =>
      reject(new ApiError("Network error — check your connection", 0)),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError("Upload aborted", 0)),
    );

    xhr.open("POST", `${API_BASE}/upload`);
    xhr.send(formData);
  });
}
