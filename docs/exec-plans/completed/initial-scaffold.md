# Build plan — `webdataset-streaming-pytorch-training`

Scaffolded from `vibe-coding-starter-kit` (cloned fresh to
`.claude/scratch/vcsk-583fc32f-0a78-4899-b223-5314746d3cb1/` — the ONLY source of truth).
Next.js (App Router) web + FastAPI (`services/api`) backend, boto3 S3 to B2,
stateless-over-B2 (no database). Python 3.12.

---

## 1. Purpose

A working reference for teams that keep their entire training corpus on
Backblaze B2 and want to **stream it straight into PyTorch — no local staging
disk**. The app packs media into [WebDataset](https://github.com/webdataset/webdataset)
`.tar` shards with `ShardWriter`, writes those shards and a JSON manifest
directly to B2, then streams them back through `WebDataset`/`WebLoader` as an
`IterableDataset` and runs a short PyTorch loop that reports live throughput
(samples/s, MB/s). It shows B2 as the **S3-compatible training-data layer**:
shards are read sequentially over a custom-user-agent `s3://` opener with no
local copy, and a `nodesplitter`/worker split demonstrates how multi-GPU /
multi-node runs read non-overlapping shard ranges from one bucket. Audience:
ML engineers and platform teams evaluating object storage as the data plane for
large-scale training.

Everything runs on **local OSS only** — PyTorch + WebDataset on-device, no
second API key, **B2 credentials the only secret**. No external AI provider and
no Genblaze (the description names neither).

---

## 2. Architecture delta from `vibe-coding-starter-kit`

The starter kit is the ceiling. Keep its whole spine (Next.js + shadcn/ui +
tanstack-query + FastAPI layered `repo`/`service`/`runtime`/`types`, list-cache,
rate-limit, health, presign, hermetic tests, Vercel/Railway contract). Reframe
the domain from "upload & browse files" to "shard, index, stream, distribute".

### KEEP (as-is or near-as-is)
- Entire `apps/web` chrome: `layout/` (sidebar, header, health-banner,
  theme-provider, command-palette), all of `components/ui/**`, `components/design/**`
  + `/design` page (design-system reference — screenshots use it), `lib/**`
  (api-client, queries, query-client, refresh-context, utils, theming).
- **Bucket explorer** — `apps/web/src/app/files/**` + `components/files/**` +
  the `/files*` API (`runtime/files.py`, `service/files.py`, `repo/b2_client.py`
  list/stat/detail/presign/delete). **Non-negotiable keep** (full-bucket browse).
- FastAPI spine: `main.py`, `index.py` (Vercel), `app/config`, `app/runtime/{health,metrics,ratelimit}.py`,
  `app/repo/{b2_client,list_cache,counter,b2_object}.py`, `app/types/**`, the
  hermetic test harness (`tests/conftest.py` network-deny + repo-boundary mocks).
- Settings showcase (`/settings`, `components/settings/**`) — light rewrite only.
- Infra: `infra/{vercel,railway}`, `.github/workflows/ci.yml`, scripts/ — rename only.
- `metadata-extraction` (image/PDF detail) — kept; it powers the bucket
  explorer's file-detail panel. Keep `Pillow` + `PyPDF2`.

### TRIM (remove or repurpose from starter)
- **Do NOT delete the upload feature — repurpose it** as **"Raw media"**
  (`/ingest`): the same direct-to-B2 upload flow, now staging raw images under a
  `raw/` prefix that the dataset-create step can pack. Rename the nav item +
  page copy; keep `runtime/upload.py`, `service/upload.py`, `repo/b2_upload.py`,
  `components/upload/**`, `app/upload → app/ingest`. (Repurposing beats deletion:
  it strengthens the "Ingest" narrative and avoids churning the openapi contract
  / structure / e2e tests. Default create-source is synthetic, so nothing
  *requires* an upload first.)
- Dashboard widgets that assume generic file uploads (`components/dashboard/*`)
  are re-pointed at dataset-centric stats (below), not deleted.
- Starter exec-plans under `docs/exec-plans/completed/*` (the starter's own
  history) — remove; this sample starts its own history.

### ADD (new for this sample)
- **Primary entity = `Dataset`** (a WebDataset shard collection living under
  `datasets/<slug>/` in B2 — see §4). New API router + web pages.
- **`app/repo/webdataset_repo.py`** — the B2↔WebDataset boundary:
  - `write_shards(...)` — `wds.ShardWriter(pattern, maxcount, maxsize, post=upload_cb)`;
    the `post` callback uploads each finished `.tar` to B2 via the UA-tagged
    client and deletes the local temp file → shards land **directly on B2**.
  - `register_b2_opener()` — install a custom `s3://` scheme in
    `webdataset.gopen.gopen_schemes` that streams object bodies through the
    **same UA-tagged boto3 client** (`get_object(...)["Body"]`). This is how
    WebDataset reads shards natively from B2 with the custom user-agent and no
    local copy.
  - `build_manifest(...)` / `read_manifest(...)` — the `manifest.json` index.
- **`app/service/datasets.py`** — create/list/read/edit/delete + the streaming
  run (throughput + split plan). Reuses `repo/b2_client.py` for object ops.
- **`app/service/synthetic.py`** — generate N deterministic labeled sample
  images (PIL, seeded) so a demo run needs no external download and no prior upload.
- **`app/service/training.py`** — the bounded PyTorch loop: tiny CNN,
  CrossEntropy, device autodetect **CUDA → MPS → CPU (CPU default)**, capped at
  `max_batches`; returns throughput + per-step loss + the worker/node shard plan.
- **`app/runtime/datasets.py`** — the `datasets` router (§4).
- Web: `app/datasets/page.tsx` (list + create), `app/datasets/[slug]/page.tsx`
  (detail: manifest, **scoped shard explorer**, edit, delete, stream/run panel
  with live metrics + split visualization); dataset components under
  `components/datasets/**`; dataset queries in `lib/queries.ts`.
- **Sample-specific asset explorer (mandatory ADD)** — the shard explorer on the
  dataset detail page: lists just this dataset's `.tar` shards + `manifest.json`
  under `datasets/<slug>/`, with size / sample-count / preview. This is the
  scoped counterpart to the kept full-bucket explorer.

> Bucket-explorer tension note: none. The full-bucket explorer stays; the shard
> explorer is additive and scoped, exactly as the skill requires.

---

## 3. B2 surface (S3-compatible only — no b2-native)

All access is S3 via boto3 with `user_agent_extra` set on the one shared client
(`repo/b2_client.py::get_s3_client`). Operations exercised:

| Op | Where | Purpose |
|----|-------|---------|
| `put_object` | shard `post` upload, manifest/run write, raw-media upload | write `.tar` shards + `manifest.json` + `runs/latest.json` to B2 |
| `list_objects_v2` (paginated) | list datasets, list shards, bucket explorer, stats | enumerate `datasets/` and per-dataset prefixes |
| `get_object` (streaming Body) | **WebDataset `s3://` opener**, manifest read | stream shard bytes into training with the custom UA, no local copy |
| `head_object` | file/shard detail | metadata |
| `generate_presigned_url` | shard/file preview + download | browser-side preview of shards/objects |
| `delete_object` / `delete_objects` | delete dataset (prefix-scoped), delete file | remove a dataset's shards + manifest |

**No b2-native API anywhere.** The custom UA must ride *every* B2 read,
including WebDataset streaming — guaranteed by routing the `s3://` opener through
the same UA-tagged client rather than WebDataset's default `gopen`/curl.
Deletes are always scoped to the specific `datasets/<slug>/` prefix (never a
bucket-wide wipe) per the repo safety rule.

---

## 4. Primary-entity lifecycle + data model

**Entity: `Dataset`** — a shard collection at `datasets/<slug>/` in B2. No DB;
state lives in B2 objects (stateless-over-B2, like the starter).

```
datasets/<slug>/
  manifest.json            # the Index: {slug, display_name, description, modality:"image",
                           #   image_size, seed, created_at, sample_count, shard_count,
                           #   shards:[{key,size_bytes,count}], splits:{train,val}}
  shard-000000.tar ...     # WebDataset tar shards (each: <key>.png + <key>.cls)
  runs/latest.json         # last stream/train run summary (throughput, device, loss)
```

### API (new `datasets` router, mounted in `main.py`)
| Verb | Route | Notes |
|------|-------|-------|
| create | `POST /datasets` | body `{name, description?, source:"synthetic"\|"raw", num_samples, samples_per_shard, image_size}` → synth images (or pack `raw/`) → `ShardWriter` → upload shards → write manifest → return `Dataset` |
| read (list) | `GET /datasets` | read every `datasets/*/manifest.json` |
| read (one) | `GET /datasets/{slug}` | manifest + derived stats |
| read (shards) | `GET /datasets/{slug}/shards` | scoped shard explorer data (keys, sizes, counts, presigned preview) |
| read (stats) | `GET /datasets/stats` | `{datasets, shards, samples, bytes, last_run_throughput}` for the dashboard |
| edit | `PATCH /datasets/{slug}` | update `display_name` + `description` in manifest (cheap metadata edit; slug immutable) |
| delete | `DELETE /datasets/{slug}` | prefix-scoped `delete_objects` of `datasets/<slug>/**` |
| run | `POST /datasets/{slug}/stream` | body `{num_workers, num_nodes, batch_size, max_batches, shuffle_buffer}` → stream from B2 + bounded PyTorch loop → `{device, elapsed_s, samples_per_s, mb_per_s, batches, loss_curve[], worker_plan, node_plan}`; also writes `runs/latest.json` |

### UI verb coverage — ALL FIVE built, no omissions
`create` (create form on `/datasets`), `read` (list + detail + scoped shard
explorer), `edit` (metadata form on detail), `delete` (danger-zone confirm on
detail), `run` (Stream/Train panel on detail). → **`omitted_ui_verbs: []`.**

### Streaming run design (the crux — build exactly this)
1. `register_b2_opener()` once at import: `gopen_schemes["s3"] = opener` where
   `opener(url, mode="rb", **kw)` parses `s3://<bucket>/<key>` and returns
   `get_s3_client().get_object(Bucket=bucket, Key=key)["Body"]` (a file-like
   stream) → custom UA on every shard GET, zero local staging.
2. Build shard URL list from the manifest (`s3://{bucket}/{key}`), apply
   deterministic shuffle by manifest `seed`.
3. `wds.WebDataset(urls, nodesplitter=wds.split_by_node, shardshuffle=...)`
   `.decode("pil").to_tuple("png;jpg", "cls").map(to_tensor).batched(batch_size)`;
   wrap in `wds.WebLoader(ds, num_workers=num_workers, batch_size=None)`.
4. Iterate ≤ `max_batches`, forward+backward a **tiny CNN** on `device`
   (autodetect CUDA→MPS→CPU); accumulate bytes + samples + loss; compute
   throughput.
5. `worker_plan` / `node_plan`: compute (and return for UI viz) which shard
   indices each of `num_workers`×`num_nodes` reads via the same round-robin
   `split_by_node`/`split_by_worker` rule — demonstrates non-overlapping ranges
   even when the demo runs single-process.

**Keep it fast + reliable for the verify gate:** defaults `num_samples=512`,
`image_size=32`, `samples_per_shard=128` (→ 4 shards), `batch_size=32`,
`max_batches=20`, `num_workers=0` (macOS-safe default). Whole ingest+stream
completes in seconds on CPU with small shards.

`deployment: local` for **every** feature — synthetic gen, tar packing, and the
PyTorch loop all run on-device. **No external API provider, cost $0/run beyond
B2 storage+egress. No provider env var. No Genblaze.**

---

## 5. Form UX conventions

**Create Dataset** (`/datasets`, dialog or inline form; model on
`components/settings/settings-form.tsx`):
- Selectors (finite value sets → `Select`, never free text):
  `source` = `synthetic` (default) | `raw`; `num_samples` = 128|256|**512**|1024;
  `samples_per_shard` = 64|**128**|256; `image_size` = **32**|64.
- Free text: `name` (slugified, validated 2–50 chars), `description` (optional textarea).
- CREATE safe-default guidance via `placeholder`/`FormDescription` (guidance
  only, never an autofill button): e.g. "512 synthetic samples → four 32-px
  shards; a fast, offline demo run."

**Edit Dataset** (detail page, opens **pre-filled** with the real manifest):
`display_name` (text), `description` (textarea). No default-hints (edit is
pre-filled). No finite fields → no selectors needed.

**Stream/Train** run form (finite → all `Select`): `num_workers` = **0**|2|4;
`num_nodes` = **1**|2|4; `batch_size` = 16|**32**|64; `max_batches` = 10|**20**|50;
`shuffle_buffer` = 0|**100**|1000. Detected `device` shown read-only. Defaults
surfaced as guidance.

---

## 6. Doc transforms

- **Rewrite:** `README.md`, `PRODUCT.md`, `ARCHITECTURE.md`, `docs/app-workflows.md`,
  `docs/design-system.md` (light), `docs/RELIABILITY.md` + `docs/SECURITY.md`
  (keep single-tenant/unauth stance; update surface list), `docs/features/dashboard.md`
  (→ dataset stats), `docs/features/settings.md` (light), `docs/features/file-browser.md`
  (→ bucket explorer, keep), `docs/features/file-upload.md` → **`raw-media.md`**,
  keep `docs/features/metadata-extraction.md` (bucket-explorer detail).
- **New feature-doc stubs** (from `docs/features/_template.md`; these seed the
  README feature list): `datasets.md`, `shard-ingest.md`, `streaming-training.md`,
  `distributed-sharding.md`, `shard-explorer.md`.
- **Regenerate** `docs/api/openapi.json` via `pnpm contract:export` after routes
  change; update `apps/web/src/lib/api-contract.test.ts` expectations.
- Remove starter's `docs/exec-plans/completed/*` and `active/*`; the skill drops
  this plan into `docs/exec-plans/completed/initial-scaffold.md` on PASS.

---

## 7. Rename table (`vibe-coding-starter-kit` → `webdataset-streaming-pytorch-training`)

Builder: run a repo-wide grep for the three case variants + the UTM/UA tags
across all 33 hits, replace, then hand-fix semantic prose.

| Kind | From | To |
|------|------|----|
| kebab / repo slug | `vibe-coding-starter-kit` | `webdataset-streaming-pytorch-training` |
| pnpm workspace scope | `@vibe-coding-starter-kit/web` | `@webdataset-streaming-pytorch-training/web` |
| Title Case | `Vibe Coding Starter Kit` | `WebDataset Streaming PyTorch Training` |
| web APP_NAME (`lib/app-config.ts`) | `Vibe Coding Starter Kit` | `WebDataset Streaming PyTorch Training` |
| web APP_DESCRIPTION | file-mgmt template | `Stream WebDataset shards straight from Backblaze B2 into PyTorch training` |
| API_TITLE (`main.py`) | `Vibe Coding Starter Kit API` | `WebDataset Streaming PyTorch Training API` |
| snake (any py/test id) | `vibe_coding_starter_kit` | `webdataset_streaming_pytorch_training` |
| UTM `utm_content` (sidebar + README links) | `b2ai-oss-start` | `webdataset-streaming-pytorch-training` |
| **S3 `user_agent_extra`** (`b2_client.py`) | `b2ai-oss-start` | `webdataset-streaming-pytorch-training` |
| Docker/Railway/Vercel tags, workflow slugs | `vibe-coding-starter-kit` | `webdataset-streaming-pytorch-training` |

### Env var rename → parent Standard #3 (CLAUDE.md standard #3)
The starter deviates; this sample must ship the standard names.
| Starter | This sample | Handling |
|---------|-------------|----------|
| `B2_ENDPOINT` (full URL) | `B2_REGION` (e.g. `us-west-004`) | `settings.b2_endpoint` becomes a derived property `https://s3.{b2_region}.backblazeb2.com`; pass `region_name=b2_region` to boto3 too. Default `us-west-004` so `Settings()` stays test-safe. |
| `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` | rename attr `b2_key_id`→`b2_application_key_id` + all refs |
| `B2_APPLICATION_KEY` | `B2_APPLICATION_KEY` | keep |
| `B2_BUCKET_NAME` | `B2_BUCKET_NAME` | keep |
| `B2_PUBLIC_URL` | `B2_PUBLIC_URL_BASE` | rename attr `b2_public_url`→`b2_public_url_base`; **stays OPTIONAL** (empty default, NOT in REQUIRED) — a missing optional key must never block startup/verify |

Update every consumer: `main.py` (REQUIRED_B2_SETTINGS + PLACEHOLDER_VALUES —
region placeholder `your_b2_region`), `.env.example` (+ fake reference values),
`README.md`, `settings-form`/settings docs, `scripts/{setup,doctor}.mjs`, e2e,
and any test referencing the old names.

---

## 8. Dependencies

`services/api/requirements.txt` — add (lower-bound pins per starter convention;
regenerate `requirements.lock`). **Pin ML deps with upper bounds** — unpinned
torch/webdataset is a known clean-install false-green:
- `torch>=2.2,<2.9` (CPU/MPS arm64 wheel; no torchvision — decode via PIL, hand
  convert PIL→tensor)
- `webdataset>=0.2.100,<0.3` — builder confirms the installed version's
  `gopen_schemes` + `split_by_node`/`split_by_worker` API and codes to it
- `numpy<2` (torch/decode compatibility)
- keep `Pillow`, `PyPDF2`, `boto3`, fastapi stack.

`allowBuilds` / node side unchanged. `.python-version` stays `3.12`.

---

## 9. Tests (must stay hermetic — no B2 network; see `tests/conftest.py`)

- Add `test_structure.py` entries for new modules; keep it green.
- Unit-test the dataset service by **mocking the repo boundary** (monkeypatch
  `repo.b2_client` / `webdataset_repo`), mirroring existing tests: create writes
  a manifest + N shards; list/read/edit/delete manipulate manifest+prefix.
- Streaming: a unit test that (a) `register_b2_opener()` installs the `s3`
  scheme, and (b) `wds.WebDataset` iterates a **locally-built** tar (no network)
  and the tiny model does one forward pass. Full B2 streaming is the verify
  step's job, not a hermetic unit test.
- Regenerate `docs/api/openapi.json`; update `api-contract.test.ts` +
  `test_openapi_contract.py`. Adapt/extend `e2e/upload.spec.ts` (raw-media) and
  add a light datasets e2e (create→list→delete) if cheap; keep e2e green.
- `pnpm verify` (`lint:api` ruff + `test:api` pytest + `check:structure` +
  web `lint`+`test:web`+`build`) must pass before commit.

---

## 10. Deliverable checklist for the builder
1. Copy starter tree, strip `.git`, apply the rename table (§7) incl. env vars.
2. Repurpose upload→raw-media; keep bucket explorer + spine (§2).
3. Add Dataset repo/service/runtime/router + synthetic + training + webdataset_repo (§2,§4).
4. Build all web pages/components incl. scoped shard explorer + all 5 UI verbs (§4) with form UX (§5).
5. Pin deps (§8); rewrite docs + stubs (§6); regenerate openapi.
6. `pnpm verify` green; commit inside the sample repo. Do NOT push, screenshot, or touch siblings.
