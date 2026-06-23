import re

from app.config import settings
from app.repo import upload_file
from app.service.metadata import extract_metadata
from app.types import FileUploadResponse
from app.types.formatting import humanize_bytes

# Product-photo studio accepts raster reference images only. (Narrowed from
# the starter's broad allow-list: no pdf/csv/json/zip/mp4/audio/gif/svg —
# gpt-image-1 edits operate on png/jpeg/webp.)
ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MIME_EXTENSION_MAP: dict[str, set[str]] = {
    "image/jpeg": {"jpg", "jpeg", "jfif"},
    "image/png": {"png"},
    "image/webp": {"webp"},
}

_SAFE_FILENAME_RE = re.compile(r"[^\w\-.]")
_SKU_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename: strip path components, remove unsafe chars, limit length."""
    name = filename.replace("\\", "/").split("/")[-1]
    name = name.replace("\x00", "")
    name = _SAFE_FILENAME_RE.sub("_", name)
    name = re.sub(r"[_.]{2,}", "_", name)
    name = name.lstrip(".").strip()
    if len(name) > 200:
        base, _, ext = name.rpartition(".")
        name = base[: 200 - len(ext) - 1] + "." + ext if ext else name[:200]
    return name or "unnamed"


def validate_extension_matches_type(filename: str, content_type: str) -> bool:
    """Verify the file extension is consistent with the declared MIME type."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_exts = MIME_EXTENSION_MAP.get(content_type)
    if allowed_exts is None:
        return False
    if not ext:
        return True
    return ext in allowed_exts


class UploadError(Exception):
    """Raised when upload validation fails."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def process_upload(
    file_data: bytes,
    filename: str,
    content_type: str,
    content_length: int | None = None,
    sku: str | None = None,
) -> FileUploadResponse:
    """Validate and process a file upload. Raises UploadError on failure.

    When ``sku`` is provided, the file is stored as a reference photo under
    ``uploads/<sku>/reference/<filename>`` so the studio can find it; otherwise
    it lands in the flat ``uploads/`` prefix (browsable in the file explorer).
    """
    if not filename:
        raise UploadError("No filename provided")

    if sku is not None and not _SKU_RE.match(sku):
        raise UploadError(
            "Invalid SKU. Use 1-64 chars: letters, digits, '.', '_', '-'."
        )

    if content_length and content_length > settings.max_file_size:
        raise UploadError(
            f"File too large. Max size: {humanize_bytes(settings.max_file_size)}",
            status_code=413,
        )

    if content_type not in ALLOWED_TYPES:
        raise UploadError(
            f"File type '{content_type}' not allowed", status_code=415
        )

    safe_name = sanitize_filename(filename)

    if not validate_extension_matches_type(safe_name, content_type):
        raise UploadError(
            "File extension does not match declared content type",
            status_code=415,
        )

    if len(file_data) == 0:
        raise UploadError("Empty file")

    if len(file_data) > settings.max_file_size:
        raise UploadError(
            f"File too large. Max size: {humanize_bytes(settings.max_file_size)}",
            status_code=413,
        )

    # B2 buckets are always versioned — uploading the same key creates a new
    # version automatically.  No duplicate rejection needed.
    key = f"uploads/{sku}/reference/{safe_name}" if sku else f"uploads/{safe_name}"
    result = upload_file(file_data, key, content_type)
    metadata = extract_metadata(file_data, safe_name, content_type)

    return FileUploadResponse(
        key=result.key,
        filename=result.filename,
        size_bytes=result.size_bytes,
        size_human=result.size_human,
        content_type=content_type,
        uploaded_at=result.uploaded_at,
        url=result.url,
        metadata=metadata,
    )
