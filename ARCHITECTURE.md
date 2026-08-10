<!-- last_verified: 2026-08-06 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Datasets: list + create, and a detail page (manifest, shard explorer, edit, delete, stream/train panel)
  - Dashboard with dataset stats and last-run throughput
  - Raw media upload (drag-and-drop, direct-to-B2) and a full-bucket file browser
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for the dataset lifecycle (create/list/read/shards/stats/edit/delete/stream) plus raw-media upload and file listing
  - B2 S3 integration via boto3, including a custom WebDataset `s3://` opener
  - WebDataset shard writing (`ShardWriter`) + a bounded PyTorch training loop
  - Health check, structured JSON logging, Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (Dataset, ShardListEntry, StreamResult, …)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (Dataset, StreamResult, FileMetadata, ...)
    config/                Settings loaded from environment (B2_REGION-derived endpoint)
    repo/                  B2 S3 access: b2_client, datasets_repo, webdataset_repo (ShardWriter + s3:// opener)
    service/               Business logic: datasets, synthetic, training (torch), upload, files, metadata
    runtime/               FastAPI route handlers: datasets, files, upload, health, metrics
  tests/                   pytest tests (structural + integration; hermetic, no network)
```

`repo/webdataset_repo.py` is the B2↔WebDataset boundary: it registers the
`s3://` opener (streaming shard reads through the user-agent-tagged client),
drives `ShardWriter` uploads, and builds the `WebLoader`. torch is confined to
`service/training.py`; boto3 stays only in `repo/`.

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/list_cache.py`, the B2 connectivity cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`. The listing cache also owns the only background thread in the app: a stale entry is served immediately while that thread re-scans (stale-while-revalidate), and `main.lifespan` warms it once at startup so no user pays for the cold full-bucket scan.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repository: `web` builds from the
  repository root because it consumes `packages/shared`; `api` builds from
  `services/api`. The versioned per-service configs and the human-approved
  staging/production contract live in [infra/railway/README.md](infra/railway/README.md).
- **Vercel** — one project using [Vercel Services](https://vercel.com/docs/services):
  the `web` (Next.js) and `api` (FastAPI) services build from the same repo and
  share one origin — the web app at `/`, the API under `/api`. The repo-root
  `vercel.json` declares both services and routes `/api/*` to the API service;
  the Vercel-only `services/api/index.py` strips the `/api` prefix so FastAPI
  keeps its native paths (`/health`, `/files`, …). Uploads go directly from the
  browser to B2 via a presigned PUT (see
  [File Upload](docs/features/file-upload.md)), so they bypass the Function's
  4.5 MB payload ceiling entirely — the bucket must allow the deploy origin in
  its CORS. A two-separate-Projects alternative and the full delivery contract
  live in [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API)
  - Datasets live under `datasets/<slug>/` (`.tar` shards, `manifest.json`, `runs/latest.json`); raw media under `uploads/`
  - The `manifest.json` object IS the dataset record — no application database
  - Shards are read back sequentially through the WebDataset `s3://` opener (`get_object` streaming body), never staged to local disk

## External Services

- **Backblaze B2 S3 API** — file storage, retrieval, deletion, presigned URLs

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Create dataset**: Browser -> `POST /datasets` -> service generates samples (synthetic or from `uploads/`) -> `repo/webdataset_repo.write_shards` drives `ShardWriter`, uploading each `.tar` to B2 -> service writes `manifest.json` -> response
- **Stream/train**: Browser -> `POST /datasets/{slug}/stream` -> service builds seed-shuffled `s3://` shard URLs -> WebDataset reads each shard body through the `s3://` opener -> bounded PyTorch loop on the auto-detected device -> `runs/latest.json` written -> throughput + split plan response
- **Raw upload**: Browser -> `POST /upload/presign` -> Browser PUTs bytes **directly to B2** under `uploads/` -> `POST /upload/verify` -> response
- **List / delete**: Browser -> `GET /datasets` (or `/files`) / `DELETE /datasets/{slug}` -> service -> repo (prefix-scoped delete for datasets)

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

The frontend client keeps a small `API_CLIENT_ROUTES` registry in
`apps/web/src/lib/api-client.ts`. Tests compare that registry to the checked-in
OpenAPI artifact so route changes fail loudly before the hand-written client can
silently drift from FastAPI. `GET /metrics` is intentionally server-only.

## Canonical Files

- Layered API handler: `services/api/app/runtime/datasets.py`
- Service orchestration: `services/api/app/service/datasets.py`
- B2↔WebDataset boundary (repo): `services/api/app/repo/webdataset_repo.py`
- B2 object access (repo): `services/api/app/repo/datasets_repo.py`, `b2_client.py`
- Training loop (torch, service): `services/api/app/service/training.py`
- Pydantic models: `services/api/app/types/` (`datasets.py`, `files.py`, `upload.py`, `stats.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- OpenAPI contract: `docs/api/openapi.json`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Datasets](docs/features/datasets.md)
- [Shard ingest](docs/features/shard-ingest.md)
- [Streaming training](docs/features/streaming-training.md)
- [Distributed sharding](docs/features/distributed-sharding.md)
- [Shard explorer](docs/features/shard-explorer.md)
- [File Browser](docs/features/file-browser.md)
- [Raw media](docs/features/raw-media.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
