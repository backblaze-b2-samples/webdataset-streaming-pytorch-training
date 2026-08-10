<!-- last_verified: 2026-08-10 -->
# Feature: Raw media (direct-to-B2 upload)

## Purpose
Stage raw images in Backblaze B2 so the **raw** dataset source can pack them
into WebDataset shards. It is the starter's direct-to-B2 upload flow, reframed:
images upload straight from the browser to B2 (presigned PUT), the bytes never
pass through the API, and they land under the `uploads/` prefix — exactly where
the dataset-create step reads them from.

## Used By
- UI: `/ingest` page ("Raw media"), upload form component
- API: `POST /upload/presign`, `POST /upload/verify`
- Consumed by: the **raw** dataset source in `service/datasets.py` (`_raw_samples`)

## Core Functions
- `apps/web/src/lib/upload-queue-context.tsx` — app-wide upload queue (survives navigation)
- `apps/web/src/components/upload/upload-form.tsx` / `dropzone.tsx` / `upload-progress.tsx`
- `apps/web/src/lib/api-client.ts` — `uploadFile()`: presign → direct browser→B2 PUT → verify
- `services/api/app/runtime/upload.py`, `service/upload.py`, `repo/b2_upload.py`

## Canonical Files
- Presign/verify handler pattern: `services/api/app/runtime/upload.py`
- Service orchestration pattern: `services/api/app/service/upload.py`

## Inputs
- Presign: `{ filename, content_type, size_bytes }` (JSON)
- Direct PUT: raw image bytes to the signed B2 URL (never through the API)
- Verify: `{ key }` (JSON)

## Outputs
- Object stored in B2 under `uploads/{sanitized_filename}` by the browser
- The shared listing cache is invalidated on verify so the object appears in `/files`
- The image becomes eligible for the **raw** dataset source

## Flow
- User drops images in the dropzone on `/ingest`
- Client presigns, PUTs bytes directly to B2, then calls verify
- API validates (allow-list, extension↔type, size, magic-byte sniff) and mints the `uploads/` key
- Later, creating a dataset with `source: "raw"` lists `uploads/`, filters image extensions, resizes each to the dataset's `image_size`, and packs them into shards

## Edge Cases
- File too large / wrong type / extension mismatch → `/upload/presign` returns 413/415
- Content bytes don't match declared type → `/upload/verify` returns 415 and deletes the object
- No raw images staged when creating a `raw` dataset → `POST /datasets` returns 400 with guidance to upload first or use the synthetic source

## UX States
- Empty: dropzone with instructions
- Loading: per-file determinate progress, then an indeterminate "Verifying upload..." phase
- Error: per-file reason + retry
- Complete: green check + "Clear finished"

## Verification
- Test files: `services/api/tests/test_upload_validation.py`, `test_upload_conflict.py`, `test_error_handling.py`, `apps/web/src/lib/upload-status.test.ts`
- Required cases: presign rejections (413/415/400), signed PUT returned, verify accept/reject+delete, key-prefix guard
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Datasets](datasets.md)
- [Shard ingest](shard-ingest.md)
- [File Browser](file-browser.md)
- [App Workflows](../app-workflows.md)
