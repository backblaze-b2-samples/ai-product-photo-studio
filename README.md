<!-- last_verified: 2026-06-23 -->
# AI Product Photo Studio

Generate studio-quality product photos for every SKU you sell — without a photographer, a lightbox, or a single re-shoot. Upload one product photo, describe a scene, and **AI Product Photo Studio** produces reference-faithful lifestyle shots, multiple angles, and seasonal variants, then keeps a per-SKU history that accumulates over time. Built for e-commerce sellers (Shopify / Etsy / Amazon) and powered end-to-end by **[Backblaze B2](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-product-photo-studio)** object storage.

Image generation runs through the **[Genblaze SDK](https://github.com/backblaze-labs/genblaze)** (`Pipeline → DalleProvider (gpt-image-1 edits) → ObjectStorageSink`): every generated asset is written to B2 with a SHA-256 provenance manifest, so you always know exactly how each image was made.

**Why B2:** a product catalog is the textbook storage-curve workload. A growing reference library plus *many* generations per SKU (angles × seasons × revisions) piles up fast — exactly the durable, flat-priced storage B2 is built for. This app makes that curve visible on the dashboard.

**What you get:**
- **Studio** — upload a reference photo, write a scene prompt, pick angle/seasonal presets + count + quality, and generate in parallel.
- **Per-SKU Library** — a scoped explorer showing each SKU's reference photo and every generated shot, with provenance (SHA-256 + manifest URI).
- **Full-bucket File Explorer** — browse, preview, download, and delete everything in the bucket.
- **Storage-curve dashboard** — SKUs, generated shots, total storage, and a cumulative storage-growth chart.
- FastAPI backend with strict layered architecture, structural tests, and SDK containment.

## Core capability: reference-faithful generation

The headline feature is real, not simulated. A generate request:

1. Resolves the SKU's uploaded reference photo to a short-lived presigned B2 URL.
2. Builds a Genblaze `Pipeline` that fans the scene prompt out into N edit steps, each seeded with the reference photo as `external_inputs` — which routes gpt-image-1 to its `/images/edits` endpoint for reference-faithful editing (`input_fidelity="high"`).
3. Runs the steps concurrently; the `ObjectStorageSink` writes each generated image and a SHA-256 manifest to B2 under `skus/<sku>/generations/<run_id>/`.

All `genblaze_*` imports are confined to `services/api/app/repo/studio_pipeline.py` (mirroring the "boto3 only in `repo/`" rule), enforced by a structural test.

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, a free **[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-product-photo-studio)**, and an **[OpenAI API key](https://platform.openai.com/api-keys)** (gpt-image-1 has no free tier — see cost note below).

**1. Install dependencies**

```bash
pnpm install
```

**2. Set up the backend**

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # installs genblaze-core/-openai/-s3 + boto3
cd ../..
```

**3. Add your credentials**

```bash
cp .env.example .env
```

Open `.env` and fill in:

- From the [Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-product-photo-studio):
  - **Bucket Unique Name** → `B2_BUCKET_NAME`
  - The bucket's **region** (e.g. `us-west-004`) → `B2_REGION` — the S3 endpoint is derived from this (`https://s3.{B2_REGION}.backblazeb2.com`), so there's no separate endpoint variable.
  - Create an **application key** with *Read and Write*: **keyID** → `B2_APPLICATION_KEY_ID`, **applicationKey** → `B2_APPLICATION_KEY` *(shown once)*.
  - **Public URL base** for the bucket (e.g. `https://<bucket>.s3.<region>.backblazeb2.com`) → `B2_PUBLIC_URL_BASE`. Genblaze uses this to build durable, credential-free asset URLs.
- From OpenAI: your key → `OPENAI_API_KEY`.

> Walkthroughs: [creating a bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-product-photo-studio) and [creating app keys](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-product-photo-studio).

**4. Run it**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000`. Go to **Studio**, enter a SKU, upload a product photo, write a scene, and generate.

`pnpm dev` runs `pnpm doctor` first — a preflight that catches the common setup gotchas (wrong Node/Python version, missing venv, missing or placeholder `.env`, ports taken). Run it standalone with `pnpm doctor`.

## Cost note (core API — surfaced for transparency)

OpenAI's gpt-image-1 has no free tier. At the app defaults (`quality="medium"`, `size="1024x1024"`, 3 variants) one generate is roughly 3 × $0.07 ≈ **$0.21**; a 3-SKU walkthrough ≈ **$0.85** — under $1. Raising quality to `high` (~$0.19/image) or generating more variants pushes a full run over $1. The defaults are conservative on the *knobs* only — gpt-image-1 stays the model.

## How it's themed for SKUs

```
uploads/<sku>/reference/<filename>               # user-uploaded product photo
skus/<sku>/generations/<run_id>/<variant>.png    # generated shots (Genblaze sink)
skus/<sku>/generations/<run_id>/manifest.json    # SHA-256 provenance manifest
```

- **Studio** (`/studio`) — the generation surface.
- **Library** (`/library`) — per-SKU explorer scoped to the `skus/<sku>/` prefix.
- **Files** (`/files`) — full-bucket explorer (reusable starter surface, kept).
- **Dashboard** (`/`) — the SKU / storage-curve story.

## Agent-First Architecture

This repo is optimized for coding agents. **Repository knowledge is the system of record** — everything an agent needs is versioned, co-located, and discoverable.

**[AGENTS.md](AGENTS.md) is the single source of truth.** Architecture is enforced mechanically (structural tests + lints), not by convention: layering rules, import boundaries (boto3 *and* genblaze only in `repo/`), file-size limits, and SDK containment all run on every change.

```
AGENTS.md              Single source of truth — layout, invariants, commands
ARCHITECTURE.md        System layout, the Genblaze pipeline layer, data flows
docs/
  features/            Feature docs (generation, library, provenance, upload…)
  app-workflows.md     Seller journey
  dev-workflows.md     Engineering workflows and testing
  SECURITY.md          Security principles
  RELIABILITY.md       Reliability expectations
  exec-plans/          Execution plans and tech debt tracker
```

| Principle | Implementation |
|-----------|---------------|
| Single source of truth for agents | AGENTS.md — layout, invariants, commands, conventions |
| Enforce invariants mechanically | Structural tests + ruff + ESLint verify boundaries |
| Strict layered architecture | `types → config → repo → service → runtime`, enforced by tests |
| Contain external SDKs | `boto3` **and** `genblaze_*` only in `repo/` — verified by structural tests |
| Keep files agent-sized | 300-line limit per file, enforced by test |
| Docs updated with code | Same-PR requirement prevents documentation rot |
| Structured observability | JSON logging, `/metrics` endpoint, request tracing |

## Core Features

- [Product Photo Generation](docs/features/product-photo-generation.md) — reference-faithful gpt-image-1 edits via Genblaze
- [Per-SKU Library](docs/features/per-sku-library.md) — scoped explorer for one SKU's reference + generations
- [Provenance Manifest](docs/features/provenance-manifest.md) — SHA-256 manifest written to B2 per run
- [File Upload](docs/features/file-upload.md) — drag-and-drop reference-photo upload with progress
- [File Browser](docs/features/file-browser.md) — full-bucket list, preview, download, delete
- [Dashboard](docs/features/dashboard.md) — SKU/shot stats and the storage-growth curve
- [Metadata Extraction](docs/features/metadata-extraction.md) — image dimensions, EXIF, checksums
- [Design System](docs/design-system.md) — tokens, primitives, the blaze generating loader. Live preview at `/design`.

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts
- TanStack Query — caching, dedup, retry for every fetch
- Python 3.11+, FastAPI, Pydantic v2, Pillow
- **Genblaze SDK** (`genblaze-core`, `genblaze-openai`, `genblaze-s3`) — provider orchestration + B2 sink with provenance
- OpenAI **gpt-image-1** — reference-faithful image edits
- Backblaze B2 (S3-compatible object storage) via boto3
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` | Frontend only |
| `pnpm dev:api` | Backend only |
| `pnpm build` | Build frontend |
| `pnpm lint` | Lint frontend |
| `pnpm lint:api` | Lint backend (ruff) |
| `pnpm test:api` | Run backend tests |
| `pnpm check:structure` | Verify layering + SDK containment |
| `pnpm test:e2e` | Playwright e2e tests (run `pnpm --filter @ai-product-photo-studio/web exec playwright install chromium` once first) |

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, Genblaze pipeline layer, data flows |
| [docs/features/](docs/features/) | Feature docs |
| [docs/app-workflows.md](docs/app-workflows.md) | Seller journey |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |
| [docs/exec-plans/](docs/exec-plans/) | Execution plans and tech debt tracker |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Claude Agent B2 Skill

Manage Backblaze B2 from your terminal using natural language (list/search, audits, stale or large file detection, security checks, safe cleanup).

Repo: [https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage](https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage)
