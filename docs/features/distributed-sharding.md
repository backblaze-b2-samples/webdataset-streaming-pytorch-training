<!-- last_verified: 2026-08-10 -->
# Feature: Distributed sharding

## Purpose
Show how a multi-GPU / multi-node run reads **non-overlapping** shard ranges
from one B2 bucket — the split that lets WebDataset scale reads across
processes without any node copying the whole corpus.

## Used By
- UI: the node/worker split visualization in the Stream & train panel on `/datasets/[slug]`
- API: part of the `POST /datasets/{slug}/stream` response

## Core Functions
- `services/api/app/repo/webdataset_repo.py::compute_split_plan` — mirrors WebDataset's `split_by_node` / `split_by_worker` (`islice(src, rank, None, world_size)` == `indices[rank::world_size]`)
- `make_loader(...)` passes `nodesplitter=wds.split_by_node`, so a real distributed run applies the same rule

## Canonical Files
- Split logic + loader wiring: `services/api/app/repo/webdataset_repo.py`

## Inputs
- `num_nodes`, `num_workers`, and the dataset's `shard_count`

## Outputs
- `worker_plan` and `node_plan`: for each rank, `{ rank, world_size, shard_indices }`

## Flow
- For `world_size = num_nodes` (and separately `num_workers`), each rank `r` reads shard indices `range(r, shard_count, world_size)`
- The ranges are non-overlapping and jointly cover every shard
- The demo runs single-process but computes and returns the full plan, so the UI shows exactly which shards each rank would read at scale

## Edge Cases
- `world_size = 1` → the single rank reads all shards
- More ranks than shards → some ranks get an empty range (shown as "(no shards)")

## UX States
- Shown only after a run completes, alongside the throughput metrics

## Verification
- Test files: `services/api/tests/test_streaming.py` (`test_split_plan_is_round_robin_and_non_overlapping`, `test_split_plan_single_rank_reads_all`)
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: plans are round-robin, non-overlapping, and complete; `pnpm verify` green

## Related Docs
- [Streaming training](streaming-training.md)
- [Datasets](datasets.md)
