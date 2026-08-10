<!-- last_verified: 2026-08-10 -->
# WebDataset Streaming PyTorch Training

Keep your entire training corpus on **[Backblaze B2](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-webdataset-streaming-pytorch-training)** and stream it straight into PyTorch — **no local staging disk**. This app packs media into [WebDataset](https://github.com/webdataset/webdataset) `.tar` shards with `ShardWriter`, writes the shards and a JSON manifest directly to B2, then streams them back through `WebDataset`/`WebLoader` as an `IterableDataset` and runs a short PyTorch loop that reports live throughput (samples/s, MB/s). It is a working reference for teams evaluating object storage as the **data plane for large-scale training**.

Everything runs on **local open-source only** — PyTorch + WebDataset on-device, device auto-detected (CUDA → Apple MPS → CPU). Your **B2 credentials are the only secret**; there is no second API key and no external AI provider.

Explore the official [Backblaze B2 AI integrations and sample applications](https://www.backblaze.com/cloud-storage/b2-ai-integrations?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-webdataset-streaming-pytorch-training) directory and the checked-in [local OpenAPI contract](docs/api/openapi.json).

**What you get out of the box:**
- Dataset lifecycle over B2 — create (synthetic or from raw media), list, edit, delete, and **stream** WebDataset shard collections that live under `datasets/<slug>/`.
- A custom `s3://` WebDataset opener so every shard read carries the app's B2 user agent and copies nothing to local disk.
- A bounded PyTorch training loop (tiny CNN) with live throughput and a per-step loss curve.
- A distributed-sharding plan visualization — the non-overlapping shard ranges each worker/node reads from one bucket.
- Scoped shard explorer per dataset, plus a full-bucket file browser and direct-to-B2 raw-media upload.
- FastAPI backend with strict layered architecture and structural tests, and agent-optimized docs.

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.12, and a free **[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-webdataset-streaming-pytorch-training)**.

### Supported local environments

Local scripts are supported on macOS, Linux, and WSL2. Native Windows is not
supported yet because the dev scripts use POSIX shell syntax and
`services/api/.venv/bin/*` paths; use WSL2 on Windows.

Cloud or sandboxed coding-agent environments also need permission for dependency
downloads during `pnpm run setup` (PyTorch is the large download here). Running
the app or Playwright E2E requires localhost server binding for the web server
on port 3000 and the API on 8000-8009. If a sandbox denies binding,
`pnpm run doctor` and `scripts/pick-port.mjs` report `EPERM`/`EACCES` as a
permissions issue instead of a busy port.

### Setup

**1. Run setup**

```bash
pnpm run setup
```

This copies `.env.example` to `.env` only when `.env` does not already exist,
installs workspace dependencies from `pnpm-lock.yaml`, creates
`services/api/.venv` if missing, validates that an existing venv uses Python
3.12+, and installs the API's committed Python 3.12 resolution (including
PyTorch and WebDataset) from `services/api/requirements.lock`. It is safe to
rerun and never overwrites an existing `.env`.

> Use the `pnpm run` form: `setup` (like `doctor`) is a built-in pnpm command
> before pnpm 11, so bare `pnpm setup` would run pnpm's own command instead of
> this script.

**2. Add your B2 credentials**

Open `.env` and fill in the standardized `B2_*` values from the [Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-webdataset-streaming-pytorch-training):

1. **Create a bucket** → paste its unique name into `B2_BUCKET_NAME`, and its region (e.g. `us-west-004`) into `B2_REGION`. The S3 endpoint is derived from the region — no endpoint URL to configure.
2. **Create an application key** with `Read and Write` permission:
   - **keyID** → `B2_APPLICATION_KEY_ID`
   - **applicationKey** → `B2_APPLICATION_KEY` *(only shown once — paste it now)*

`B2_PUBLIC_URL_BASE` is optional (public-bucket object URLs only) and can stay commented out.

> Want a walkthrough? See the docs for [creating a bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-webdataset-streaming-pytorch-training) and [creating app keys](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-webdataset-streaming-pytorch-training).

**3. Run it**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000`. Go to **Datasets → New dataset**, keep the defaults (512 synthetic samples at 32 px → four shards), and create it — the app generates images, packs them into `.tar` shards, and writes them to B2. Open the dataset and hit **Start run** to stream the shards back from B2 into a PyTorch loop and watch the throughput. Interactive API docs (Swagger UI) are at `localhost:8000/docs`.

`pnpm dev` runs the preflight check first — it catches the common setup gotchas (wrong Node/Python version, missing venv, missing or placeholder `.env`, ports already taken). Run it standalone any time with `pnpm run doctor`.

## Why B2 for training data

WebDataset was built to stream sharded datasets over the network so training
nodes never need the whole corpus on a local disk. Point it at B2 over the
S3-compatible API and you get one bucket as the shared data plane: shards are
read sequentially per worker, multiple workers/nodes read **non-overlapping**
shard ranges from the same bucket, and egress is pay-as-you-go with no per-node
copy. This app makes that concrete — the `s3://` opener streams each shard body
through a user-agent-tagged boto3 client, so every read is attributable and
nothing is staged locally.

## When to use

Use this as a template or reference when you keep training data on object
storage and want a proven pattern for streaming it into PyTorch: sharding with
`ShardWriter`, a manifest index, a custom `s3://` opener, and the worker/node
split that scales to multi-GPU / multi-node reads from one bucket. It ships with
strict architecture, contract checks, tests, and deployment runbooks so you
start from a dependable scaffold.

## When not to use

Do not expect a complete hosted training service or a large-scale distributed
trainer. The PyTorch loop here is a deliberately tiny CNN bounded to a handful
of batches — it demonstrates streaming throughput, not model quality. There is
no managed hosting, user accounts, authentication, tenant isolation, or GPU
cluster orchestration. You own product-specific security, operations, capacity,
and compliance for anything you adapt.

## Building on this app

When you adapt this repo, keep the shared scaffolding and swap what's specific:

- **Keep** the UI kit (`apps/web/src/components/ui/` + design tokens in `globals.css` + `/design`).
- **Keep** the full-bucket File Explorer (`/files`) and the direct-to-B2 Raw media upload (`/ingest`) — the reusable B2-backed surface.
- **The primary entity is the Dataset** — the datasets router/service and the `repo/webdataset_repo.py` B2↔WebDataset boundary are what you extend for a real corpus (swap the synthetic generator for your own ingestion).
- **Rebrand** by editing one file: `apps/web/src/lib/app-config.ts` (`APP_NAME`, `APP_DESCRIPTION`) updates the title, sidebar, and breadcrumb everywhere.

Full contract and rationale: [AGENTS.md §2 — Building on this app](AGENTS.md#2-building-on-this-app).

## Agent-First Architecture

This repo is optimized for coding agents. **[AGENTS.md](AGENTS.md) is the single source of truth** — a bounded, agent-sized entry point with the repository layout, architectural invariants, commands, and conventions. Agent-specific files (CLAUDE.md, GEMINI.md, Copilot instructions) are thin pointers back to it.

Architecture is enforced mechanically: layering rules (`types → config → repo → service → runtime`), import boundaries (`boto3` only in `repo/`), a 300-line-per-file limit, and the OpenAPI contract are all verified by structural tests and lints on every change.

## Core Features

- [Datasets](docs/features/datasets.md) — create / list / edit / delete WebDataset shard collections on B2
- [Shard ingest](docs/features/shard-ingest.md) — `ShardWriter` packs media into `.tar` shards written directly to B2
- [Streaming training](docs/features/streaming-training.md) — the `s3://` opener + bounded PyTorch loop with live throughput
- [Distributed sharding](docs/features/distributed-sharding.md) — the worker/node split that reads non-overlapping shard ranges
- [Shard explorer](docs/features/shard-explorer.md) — scoped per-dataset shard listing with size, sample count, and preview
- [File Browser](docs/features/file-browser.md) — full-bucket list, preview, download, delete
- [Raw media](docs/features/raw-media.md) — drag-and-drop direct-to-B2 upload of images to pack
- [Metadata Extraction](docs/features/metadata-extraction.md) — image dimensions, EXIF, PDF info, checksums for the file browser
- [Dashboard](docs/features/dashboard.md) — dataset stats and last-run throughput
- [Design System](docs/design-system.md) — tokens, primitives, loader, error/empty states. Live at `/design`.
- Checked local API contract — [`docs/api/openapi.json`](docs/api/openapi.json) plus `pnpm contract:check` catch FastAPI/client route drift.
- Structural tests, structured JSON logging, `/health` (B2 connectivity), `/metrics` (Prometheus), per-IP rate limiting.

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, TanStack Query
- Python 3.12+, FastAPI, boto3, Pydantic v2, **PyTorch (CPU/MPS/CUDA)**, **WebDataset**, NumPy, Pillow, PyPDF2
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm run setup` | Idempotently copy `.env.example` to `.env` only if missing, install workspace dependencies, create the backend venv, and install the locked API dependencies |
| `pnpm run doctor` | Preflight environment check (also runs automatically before `pnpm dev`) |
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` | Frontend only |
| `pnpm dev:api` | Backend only |
| `pnpm contract:export` | Export deterministic FastAPI OpenAPI JSON to `docs/api/openapi.json` |
| `pnpm contract:check` | Verify the checked-in OpenAPI artifact and frontend API client route registry |
| `pnpm check:agent-docs` | Validate agent shims, command docs, CI claims, and `.env` ignore coverage |
| `pnpm verify` | Credential-free canonical non-live pre-PR suite — runs `check:agent-docs`, `verify:api`, then `verify:web` |
| `pnpm verify:api` | Backend half: API lint, API tests, structure tests |
| `pnpm verify:web` | Frontend half: web lint, web unit tests, web typecheck + build |
| `pnpm verify:full` | `pnpm run doctor`, then `pnpm verify`, then Playwright E2E; requires populated `.env`, local server/browser permission, port 3000 free, and Chromium installed |
| `pnpm build` | Build frontend |
| `pnpm lint` | Lint frontend |
| `pnpm lint:api` | Lint backend (ruff) |
| `pnpm test:web` | Run frontend unit tests (vitest) |
| `pnpm test:api` | Run backend tests |
| `pnpm test:live:b2` | Opt-in real B2 connectivity test; requires `RUN_LIVE_B2_TESTS=1` and non-production credentials |
| `pnpm check:structure` | Verify layering rules |
| `pnpm test:e2e` | Playwright E2E smoke tests (run `pnpm --filter @webdataset-streaming-pytorch-training/web exec playwright install chromium` once first) |

Run `pnpm run setup` once before local development, and rerun it after pulling
dependency changes. Run `pnpm verify` before opening a PR; it needs
`services/api/.venv` from setup and neither B2 credentials nor a browser. For an
API dependency change, follow the reviewed refresh workflow in
[docs/dev-workflows.md](docs/dev-workflows.md#python-dependency-updates). Use
`pnpm verify:full` when you can start the local app stack and browser tests.

## Deploying to Vercel

This app deploys to Vercel as **one project** using Vercel
[Services](https://vercel.com/docs/services): the Next.js web app and the
FastAPI API build from the same repo and share a single origin — web at `/`, API
under `/api`. One click, one project, **no CORS and no wiring two URLs
together**.

[![Deploy to Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fbackblaze-b2-samples%2Fwebdataset-streaming-pytorch-training&project-name=webdataset-streaming-pytorch-training&env=B2_APPLICATION_KEY_ID,B2_APPLICATION_KEY,B2_BUCKET_NAME,B2_REGION&envDescription=B2%20credentials%2C%20region%2C%20and%20bucket&envLink=https%3A%2F%2Fgithub.com%2Fbackblaze-b2-samples%2Fwebdataset-streaming-pytorch-training%2Fblob%2Fmain%2Finfra%2Fvercel%2FREADME.md)

Set the B2 credentials, region, and bucket. Raw-media uploads go **directly from
the browser to B2** (presigned PUT), so Vercel's 4.5 MB Function payload limit
doesn't apply — one caveat: the bucket must allow your deploy origin in its CORS
(see the [Vercel delivery contract](infra/vercel/README.md)). The web app reaches
the API at the same-origin `/api` automatically, so **no `NEXT_PUBLIC_API_URL`
is needed**. Note that a streaming run does CPU-bound PyTorch work inside the
Function; the small defaults finish quickly, but heavy runs belong on a real
worker, not a serverless Function.

For the full variable classification, the two-Project alternative, security
controls, and rollback, follow the [Vercel delivery contract](infra/vercel/README.md).
The API is unauthenticated and bucket-wide, so use a dedicated B2 bucket/prefix
and key for any preview. Deploying is a human-approved action — nothing here
performs one for you.

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs (datasets, shard ingest, streaming, sharding, explorers, raw media) |
| [docs/design-system.md](docs/design-system.md) | Design tokens, primitives, loader, error/empty states |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |
| [docs/api/openapi.json](docs/api/openapi.json) | Checked contract for the local FastAPI API |
| [infra/vercel/README.md](infra/vercel/README.md) | Vercel deployment contract |
| [docs/exec-plans/](docs/exec-plans/) | Execution plans and tech debt tracker |

## FAQ

**What does this app do?**
It packs images into WebDataset `.tar` shards, writes them and a `manifest.json` index to Backblaze B2, then streams the shards back through WebDataset into a bounded PyTorch training loop — with no local staging disk — and reports live throughput plus the worker/node shard split.

**How does WebDataset read shards from B2 without downloading them first?**
The app registers a custom `s3://` scheme in `webdataset.gopen.gopen_schemes` that returns the streaming body of an S3 `get_object` call through the same user-agent-tagged boto3 client. WebDataset consumes that stream sequentially, so each shard is read on demand with the custom user agent and nothing is copied to disk.

**Do I need a GPU?**
No. Device selection auto-detects CUDA → Apple MPS → CPU and defaults to CPU. The demo defaults run in seconds on a laptop CPU.

**Does it need an AI provider API key?**
No. Everything is local open-source (PyTorch + WebDataset). Your B2 credentials are the only secret.

**What's a "dataset" here?**
A shard collection under `datasets/<slug>/` in your bucket: the `.tar` shards, a `manifest.json` index (samples, shards, splits, seed), and a `runs/latest.json` last-run summary. There is no database — the manifest object is the record.

**Can I use my own images instead of synthetic ones?**
Yes. Upload images on the **Raw media** page (they land under `uploads/` in B2), then create a dataset with the **raw** source to pack them into shards.

**Is it free?**
The code is MIT-licensed (see [License](#license)), and Backblaze B2 offers a free account to get started.

**Can I use it in production?**
It's a sample Backblaze maintains to help developers get started with B2. Production use is possible with caution and your own validation; the repository software carries no SLA. See [When not to use](#when-not-to-use) and [Maintenance and support](#maintenance-and-support).

**Does it work on Windows?**
Local scripts are supported on macOS, Linux, and WSL2. Native Windows is not supported yet — use WSL2.

**Where do I get help or report bugs?**
Report repository defects through [GitHub Issues](https://github.com/backblaze-b2-samples/webdataset-streaming-pytorch-training/issues). For B2 account, billing, service, or API help, use [Backblaze Support](https://www.backblaze.com/help?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-webdataset-streaming-pytorch-training).

## Maintenance and support

Backblaze maintains this open-source sample to help developers get started with
B2. Production use is possible with caution and requires your own validation.
Report repository defects and feature requests through
[GitHub Issues](https://github.com/backblaze-b2-samples/webdataset-streaming-pytorch-training/issues);
for B2 account, billing, service, or API help, use
[Backblaze Support](https://www.backblaze.com/help?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-webdataset-streaming-pytorch-training). This sample is
not covered by the Backblaze service level agreement, and no SLA is provided
for the repository software.

## Contributing

Start with [AGENTS.md](AGENTS.md). It's the map — everything else is discoverable from there. For local commit hooks, follow [the pre-commit workflow](docs/dev-workflows.md#pre-commit).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Claude Agent B2 Skill

Manage Backblaze B2 from your terminal using natural language (list/search, audits, stale or large file detection, security checks, safe cleanup).

Repo: [https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage](https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage)
