from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Backblaze B2 — standardized B2_* names (S3-compatible API).
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_region: str = ""
    b2_public_url_base: str = ""

    # OpenAI — image generation provider (separate from B2 credentials).
    openai_api_key: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # --- Studio generation defaults (gpt-image-1 via Genblaze) ---------------
    # Conservative defaults keep a typical generate under ~$0.25. The model
    # itself is never downgraded — only these knobs default low.
    studio_default_quality: str = "medium"  # low | medium | high | auto
    studio_default_size: str = "1024x1024"  # 1024x1024 | 1536x1024 | 1024x1536 | auto
    studio_default_variants: int = 3
    studio_max_variants: int = 6
    studio_run_timeout: int = 300

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def b2_endpoint(self) -> str:
        """Derive the S3-compatible endpoint from the region.

        Standardized on B2_REGION (parent standard #3): no separate
        B2_ENDPOINT env var, no hardcoded region string in source.
        """
        return f"https://s3.{self.b2_region}.backblazeb2.com"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]


settings = Settings()
