<!-- last_verified: 2026-08-10 -->
# Feature: Datasets

## Purpose
Manage the primary entity — a **Dataset**, a WebDataset shard collection living
under `datasets/<slug>/` in Backblaze B2. There is no database; the
`manifest.json` object is the record (stateless-over-B2).

## Used By
- UI: `/datasets` (list + create), `/datasets/[slug]` (detail: manifest, edit, delete, shard explorer, stream panel)
- API: `POST /datasets`, `GET /datasets`, `GET /datasets/stats`, `GET /datasets/{slug}`, `GET /datasets/{slug}/shards`, `PATCH /datasets/{slug}`, `DELETE /datasets/{slug}`, `POST /datasets/{slug}/stream`

## Core Functions
- `services/api/app/service/datasets.py` — create/list/read/shards/stats/edit/delete/stream orchestration
- `services/api/app/repo/datasets_repo.py` — B2 object I/O (JSON put/get, list prefix, prefix-scoped delete, presign)
- `services/api/app/repo/webdataset_repo.py` — shard writing + the `s3://` streaming boundary
- `services/api/app/runtime/datasets.py` — the `datasets` router
- `apps/web/src/components/datasets/**`, `apps/web/src/lib/queries.ts` (dataset hooks)

## Canonical Files
- Service orchestration: `services/api/app/service/datasets.py`
- Router pattern: `services/api/app/runtime/datasets.py`

## Inputs
- Create: `{ name, description?, source: "synthetic"|"raw", num_samples, samples_per_shard, image_size }`
- Edit: `{ display_name?, description? }` (slug is immutable)

## Outputs
- `Dataset` (the manifest): `slug`, `display_name`, `description`, `modality`, `image_size`, `seed`, `created_at`, `sample_count`, `shard_count`, `total_size_bytes`, `size_human`, `shards[]`, `splits{train,val}`
- Side effects: `.tar` shards + `manifest.json` written under `datasets/<slug>/`; delete removes that prefix only

## Data model
```
datasets/<slug>/
  manifest.json         # the index (see Dataset fields above)
  shard-000000.tar ...  # WebDataset shards (<key>.png + <key>.cls per sample)
  runs/latest.json      # last stream/train run summary
```

## Flow
- Create → generate samples (synthetic, or pack images from `uploads/`) → `ShardWriter` writes shards to B2 → write manifest → return Dataset
- List → read every `datasets/*/manifest.json`
- Edit → patch `display_name`/`description` in the manifest
- Delete → prefix-scoped `delete_objects` of `datasets/<slug>/**`
- Stream → see [Streaming training](streaming-training.md)

## Edge Cases
- Duplicate slug → 409
- Unknown slug (read/shards/edit/stream) → 404
- Out-of-range create/stream choice → 400 (API re-validates the finite option sets)
- `raw` source with no staged images → 400

## UX States
- Empty: "No datasets yet" with a create CTA
- Loading: skeleton cards / manifest skeleton
- Error: inline `ErrorState` with retry; 404 → "Dataset not found"

## Verification
- Test files: `services/api/tests/test_datasets.py`
- Required cases: create writes manifest+shards, duplicate 409, list/read/shards, 404, edit, prefix-scoped delete, stats aggregate
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Shard ingest](shard-ingest.md)
- [Streaming training](streaming-training.md)
- [Shard explorer](shard-explorer.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
