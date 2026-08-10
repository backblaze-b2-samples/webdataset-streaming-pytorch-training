<!-- last_verified: 2026-08-10 -->
# Feature: Dashboard

## Purpose
Provide an at-a-glance overview of the dataset corpus on B2 and how fast it last
streamed into PyTorch.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /datasets/stats`, `GET /datasets`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 dataset stat cards (datasets, shards, samples, shard storage)
- `apps/web/src/components/dashboard/recent-datasets-table.tsx` — most recent datasets
- `apps/web/src/components/dashboard/last-run-card.tsx` — last streaming run throughput + device
- `apps/web/src/lib/queries.ts` — `useDatasetStats()`, `useDatasets()`
- `services/api/app/runtime/datasets.py` — `GET /datasets/stats` handler
- `services/api/app/service/datasets.py` — `get_stats()` business logic

## Canonical Files
- Dashboard stat cards: `apps/web/src/components/dashboard/stats-cards.tsx`
- Stats service logic: `services/api/app/service/datasets.py::get_stats`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /datasets/stats` → `DatasetStats` (total_datasets, total_shards, total_samples, total_size_bytes, total_size_human, last_run_samples_per_s, last_run_device)
- `GET /datasets` → `Dataset[]` for the recent-datasets table (newest first)

## Flow
- Page loads → two API calls (dataset stats + list)
- Stats read every `datasets/*/manifest.json` (a bucket listing plus small GETs) and the newest `runs/latest.json` for last-run throughput
- Stat cards show dataset / shard / sample counts and total shard storage
- The recent-datasets table links each row to its detail page
- The last-run card shows samples/s and the device of the most recent streaming run

## Edge Cases
- API unavailable → inline error states with retry
- No datasets yet → empty stat values and an empty-state table
- No runs yet → last-run card shows an empty state

## UX States
- Loading: an on-screen "Loading dataset stats…" notice above skeleton cards
- Empty: "No datasets yet" / "No runs yet"
- Loaded: populated cards, table, and last-run card

## Verification
- Test files: `services/api/tests/test_datasets.py` (`test_stats_aggregate`)
- Required cases: stats aggregate across manifests, empty state, API error fallback
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Datasets](datasets.md)
- [Streaming training](streaming-training.md)
- [App Workflows](../app-workflows.md)
