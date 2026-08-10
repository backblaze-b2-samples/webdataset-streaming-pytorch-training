<!-- last_verified: 2026-08-10 -->
# App Workflows

User journeys inside the application.

## Create a dataset

- User navigates to `/datasets` and clicks **New dataset**
- The Create dialog uses selectors for every finite field: source (synthetic / raw), samples (128/256/**512**/1024), samples per shard (64/**128**/256), image size (**32**/64); name and description are free text. A guidance line states what the defaults do — no autofill button
- On submit the API generates samples (synthetic images, or images packed from the Raw media prefix), drives `ShardWriter` to write `.tar` shards **directly to B2**, and writes a `manifest.json` index under `datasets/<slug>/`
- On success: a toast reports the sample and shard counts; the new dataset appears in the list
- On failure (duplicate slug, no raw media, out-of-range choice): an error toast with the reason
- See: [Datasets](features/datasets.md), [Shard ingest](features/shard-ingest.md)

## Stream a dataset into PyTorch

- User opens a dataset at `/datasets/[slug]` and reviews the manifest summary
- In the **Stream & train** panel, all knobs are selectors: workers (**0**/2/4), nodes (**1**/2/4), batch size (16/**32**/64), max batches (10/**20**/50), shuffle buffer (0/**100**/1000). The detected device is shown read-only
- On **Start run**, WebDataset reads each shard body straight from B2 through the `s3://` opener (custom user agent, no local copy) and a bounded PyTorch loop runs on the auto-detected device (CUDA → MPS → CPU)
- The result shows live throughput (samples/s, MB/s), elapsed time, a per-step loss sparkline, and the node/worker split plan — the non-overlapping shard ranges each rank reads
- See: [Streaming training](features/streaming-training.md), [Distributed sharding](features/distributed-sharding.md)

## Browse one dataset's shards

- On the dataset detail page, the **Shards** card lists just this dataset's `.tar` shards with size, sample count, and a presigned link to each shard on B2
- See: [Shard explorer](features/shard-explorer.md)

## Edit or delete a dataset

- **Edit** opens pre-filled with the real manifest (display name + description; the slug and shards are immutable)
- **Delete** opens a confirm dialog and removes every object under `datasets/<slug>/` — a prefix-scoped delete, never a bucket-wide wipe
- See: [Datasets](features/datasets.md)

## Stage raw media

- User navigates to `/ingest` ("Raw media") and drops images
- Files upload **directly from the browser to B2** (presigned PUT) under `uploads/`; a determinate bar tracks the bytes, then an indeterminate "Verifying upload..." phase runs while the API sniffs the object
- Those images then feed a dataset created with the **raw** source
- See: [Raw media](features/raw-media.md)

## Browse the whole bucket

- User navigates to `/files`
- The full-bucket explorer lists the 100 most recent objects in a tree view with preview, download, and delete. This is the bucket-wide counterpart to the per-dataset shard explorer
- See: [File Browser](features/file-browser.md)

## View the dashboard

- User navigates to `/` (home)
- Stat cards show dataset / shard / sample counts and total shard storage; a table lists recent datasets and a card shows the last streaming run's throughput and device
- See: [Dashboard](features/dashboard.md)

## Change preferences

- User navigates to `/settings`
- A banner states the page is mostly a demonstration: only Theme is wired for real; the rest persists to `localStorage` and drives no behaviour
- See: [Settings](features/settings.md)
