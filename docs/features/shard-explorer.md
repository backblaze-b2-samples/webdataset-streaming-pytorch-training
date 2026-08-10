<!-- last_verified: 2026-08-10 -->
# Feature: Shard explorer

## Purpose
Browse just **one dataset's** shards — the scoped counterpart to the full-bucket
File Browser. Lists the `.tar` shards under `datasets/<slug>/` with size, sample
count, and a presigned download/preview link.

## Used By
- UI: the Shards card on `/datasets/[slug]`
- API: `GET /datasets/{slug}/shards`

## Core Functions
- `services/api/app/service/datasets.py::get_shards` — reads the manifest and presigns each shard
- `services/api/app/repo/datasets_repo.py::presign_get` — inline presigned GET
- `apps/web/src/components/datasets/shard-explorer.tsx`

## Canonical Files
- Scoped listing: `services/api/app/service/datasets.py::get_shards`

## Inputs
- `slug` (path param)

## Outputs
- `ShardListEntry[]`: `key`, `filename`, `size_bytes`, `size_human`, `count`, `preview_url`

## Flow
- Read the dataset's `manifest.json`
- For each shard entry, build a row with a presigned inline URL to the `.tar` on B2

## Edge Cases
- Unknown slug → 404
- Dataset with no shards → empty state

## UX States
- Empty: "No shards"
- Loading: row skeletons
- Error: inline `ErrorState` with retry

## Verification
- Test files: `services/api/tests/test_datasets.py` (`test_list_and_read_and_shards`)
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: shard rows returned with presigned URLs; `pnpm verify` green

## Related Docs
- [Datasets](datasets.md)
- [File Browser](file-browser.md)
