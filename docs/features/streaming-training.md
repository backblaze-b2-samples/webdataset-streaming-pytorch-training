<!-- last_verified: 2026-08-10 -->
# Feature: Streaming training

## Purpose
Stream a dataset's shards straight from Backblaze B2 into a bounded PyTorch
training loop — **no local staging disk** — and report live throughput
(samples/s, MB/s), a per-step loss curve, and the worker/node shard plan.

## Used By
- UI: the Stream & train panel on `/datasets/[slug]`
- API: `POST /datasets/{slug}/stream`

## Core Functions
- `services/api/app/repo/webdataset_repo.py::register_b2_opener` — installs an `s3://` scheme in `webdataset.gopen.gopen_schemes` that returns the streaming body of an S3 `get_object` through the same user-agent-tagged boto3 client (custom UA on every shard read, no local copy)
- `services/api/app/repo/webdataset_repo.py::make_loader` — `WebDataset(urls, nodesplitter=split_by_node).decode("pil").to_tuple(...).map_tuple(...).batched(...)` wrapped in `WebLoader`
- `services/api/app/service/training.py::run_stream` / `TinyCNN` / `pick_device`

## Canonical Files
- Streaming boundary: `services/api/app/repo/webdataset_repo.py`
- Training loop: `services/api/app/service/training.py`

## Inputs
- `{ num_workers, num_nodes, batch_size, max_batches, shuffle_buffer }` (all finite selectors)

## Outputs
- `StreamResult`: `device`, `elapsed_s`, `samples`, `batches`, `bytes_read`, `samples_per_s`, `mb_per_s`, `loss_curve[]`, `worker_plan[]`, `node_plan[]`
- Side effect: `runs/latest.json` written under the dataset prefix

## Device selection
Runtime auto-detect: **CUDA → Apple MPS → CPU**, defaulting to CPU. No GPU is
ever hard-required (this feature is `deployment: local`).

## Flow
- Build `s3://{bucket}/{key}` URLs from the manifest, deterministically shuffled by the manifest `seed`
- WebDataset reads each shard body through the `s3://` opener; images decode to CHW float arrays
- For ≤ `max_batches`, run a forward+backward pass of the tiny CNN on the selected device; accumulate samples/bytes/loss
- Compute throughput and the worker/node split plan; write `runs/latest.json`

## Edge Cases
- Dataset with no shards → 409
- `max_batches` exceeds available batches → loop ends early; actual batch count is reported
- Out-of-range run choice → 400

## UX States
- Idle: run form with defaults; "Detected device: auto (CUDA → MPS → CPU)"
- Loading: "Streaming..." button state
- Result: metric grid, loss sparkline, and the node/worker split visualization
- Error: toast with the API message

## Verification
- Test files: `services/api/tests/test_streaming.py` (opener install, local tar iterate + one forward pass, device selection), `services/api/tests/test_datasets.py`
- Note: hermetic tests use a locally-built tar via `file://`; full B2 streaming is exercised by the live verify step, not a hermetic unit test
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: opener installed, model forward pass runs, `pnpm verify` green

## Related Docs
- [Distributed sharding](distributed-sharding.md)
- [Datasets](datasets.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
