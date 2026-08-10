<!-- last_verified: 2026-08-10 -->
# Feature: Shard ingest

## Purpose
Pack media into WebDataset `.tar` shards and write them **directly to Backblaze
B2** — never to a local staging disk that outlives one shard.

## Used By
- UI: the Create dialog on `/datasets`
- API: `POST /datasets` (create path)

## Core Functions
- `services/api/app/repo/webdataset_repo.py::write_shards` — drives `wds.ShardWriter` with a `post` callback that uploads each finished `.tar` to B2 and deletes the local temp file
- `services/api/app/service/synthetic.py::generate_samples` — deterministic labeled PIL images (zero-download demo source)
- `services/api/app/service/datasets.py::_raw_samples` — packs staged images from `uploads/`

## Canonical Files
- B2↔WebDataset write boundary: `services/api/app/repo/webdataset_repo.py`

## Inputs
- Sample dicts `{ "__key__", "png": PIL.Image, "cls": int }`
- `samples_per_shard` (finite selector), `image_size`, `num_samples`, `seed`

## Outputs
- `.tar` shards at `datasets/<slug>/shard-000000.tar` …, each containing `<key>.png` + `<key>.cls`
- A list of `{ key, size_bytes, count }` recorded into the manifest

## Flow
- `ShardWriter(pattern, maxcount=samples_per_shard, maxsize=<huge>, post=upload_cb)` — only `maxcount` triggers rotation, so shard membership is deterministic
- On each finished shard, the `post` callback uploads the `.tar` to B2 via the user-agent-tagged client, records size + `writer.count`, and removes the temp file
- Peak local disk is one shard regardless of dataset size

## Edge Cases
- Empty sample stream → no shards written → create returns 400
- Final partial shard → uploaded on `writer.close()` with its true count
- Raw source: non-image objects under `uploads/` are skipped

## UX States
- Loading: "Packing shards..." on the Create dialog submit button
- Error: toast with the API message

## Verification
- Test files: `services/api/tests/test_streaming.py` (local ShardWriter round-trip), `services/api/tests/test_datasets.py` (create writes shards)
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: shards written with correct counts; `pnpm verify` green

## Related Docs
- [Datasets](datasets.md)
- [Streaming training](streaming-training.md)
