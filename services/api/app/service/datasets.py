"""Dataset lifecycle: create, list, read, shards, stats, edit, delete, stream.

A ``Dataset`` is a WebDataset shard collection under ``datasets/<slug>/`` in B2.
There is no database — the ``manifest.json`` object IS the record
(stateless-over-B2). All object I/O flows through ``repo/datasets_repo`` and the
shards/streaming through ``repo/webdataset_repo``; the bounded PyTorch loop
lives in ``service/training``.
"""

from __future__ import annotations

import io
import logging
import random
import re
import zlib
from collections.abc import Iterator
from datetime import UTC, datetime

from PIL import Image

from app.repo import datasets_repo as repo
from app.repo import webdataset_repo as wds_repo
from app.service import synthetic
from app.service import training as training_service
from app.service.upload import UPLOAD_PREFIX
from app.types import (
    Dataset,
    DatasetStats,
    ShardEntry,
    ShardListEntry,
    StreamRequest,
    StreamResult,
)
from app.types.datasets import (
    BATCH_SIZE_CHOICES,
    IMAGE_SIZE_CHOICES,
    MAX_BATCHES_CHOICES,
    NUM_NODES_CHOICES,
    NUM_SAMPLES_CHOICES,
    NUM_WORKERS_CHOICES,
    SAMPLES_PER_SHARD_CHOICES,
    SHUFFLE_BUFFER_CHOICES,
    SOURCES,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)
DATASETS_PREFIX = "datasets/"
_MANIFEST = "manifest.json"
_RUN = "runs/latest.json"
# Raw media staged via the Raw media (upload) page lands under uploads/; the
# raw dataset source packs images from there. See docs/features/raw-media.md.
RAW_MEDIA_PREFIX = UPLOAD_PREFIX
_IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "webp", "gif", "bmp")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class DatasetError(Exception):
    """Raised when a dataset operation fails with a client-facing status."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    if not (2 <= len(slug) <= 50):
        raise DatasetError("Name must slugify to 2-50 url-safe characters")
    return slug


def _prefix(slug: str) -> str:
    return f"{DATASETS_PREFIX}{slug}/"


def _validate_create(source: str, num_samples: int, per_shard: int, size: int) -> None:
    if source not in SOURCES:
        raise DatasetError(f"source must be one of {SOURCES}")
    if num_samples not in NUM_SAMPLES_CHOICES:
        raise DatasetError(f"num_samples must be one of {NUM_SAMPLES_CHOICES}")
    if per_shard not in SAMPLES_PER_SHARD_CHOICES:
        raise DatasetError(f"samples_per_shard must be one of {SAMPLES_PER_SHARD_CHOICES}")
    if size not in IMAGE_SIZE_CHOICES:
        raise DatasetError(f"image_size must be one of {IMAGE_SIZE_CHOICES}")


def _raw_samples(num_samples: int, image_size: int) -> Iterator[dict]:
    """Pack up to ``num_samples`` images staged under the raw-media prefix."""
    objects = [
        obj
        for obj in repo.list_prefix(RAW_MEDIA_PREFIX)
        if obj["key"].rsplit(".", 1)[-1].lower() in _IMAGE_EXTENSIONS
    ]
    if not objects:
        raise DatasetError(
            "No raw media found. Upload images on the Raw media page first, "
            "or create with the synthetic source.",
        )
    objects.sort(key=lambda o: o["key"])
    for index, obj in enumerate(objects[:num_samples]):
        raw = repo.get_bytes(obj["key"])
        if raw is None:
            continue
        image = Image.open(io.BytesIO(raw)).convert("RGB").resize(
            (image_size, image_size)
        )
        yield {
            "__key__": f"sample{index:06d}",
            "png": image,
            "cls": index % synthetic.NUM_CLASSES,
        }


def _manifest_to_dataset(data: dict) -> Dataset:
    return Dataset(**data)


def _build_manifest(
    slug: str,
    display_name: str,
    description: str,
    image_size: int,
    seed: int,
    shards: list[dict],
) -> dict:
    sample_count = sum(s["count"] for s in shards)
    total_bytes = sum(s["size_bytes"] for s in shards)
    val = sample_count // 10
    return Dataset(
        slug=slug,
        display_name=display_name,
        description=description,
        modality="image",
        image_size=image_size,
        seed=seed,
        created_at=datetime.now(UTC),
        sample_count=sample_count,
        shard_count=len(shards),
        total_size_bytes=total_bytes,
        size_human=humanize_bytes(total_bytes),
        shards=[ShardEntry(**s) for s in shards],
        splits={"train": sample_count - val, "val": val},
    ).model_dump()


def create_dataset(
    name: str,
    description: str | None,
    source: str,
    num_samples: int,
    samples_per_shard: int,
    image_size: int,
) -> Dataset:
    _validate_create(source, num_samples, samples_per_shard, image_size)
    slug = slugify(name)
    prefix = _prefix(slug)
    if repo.read_json(prefix + _MANIFEST) is not None:
        raise DatasetError(f"A dataset named '{slug}' already exists", status_code=409)

    # Stable per-slug seed → recreating with the same params is reproducible.
    seed = zlib.crc32(slug.encode("utf-8"))
    if source == "synthetic":
        samples = synthetic.generate_samples(num_samples, image_size, seed)
    else:
        samples = _raw_samples(num_samples, image_size)

    shards = wds_repo.write_shards(prefix, samples, samples_per_shard)
    if not shards:
        raise DatasetError("No samples were packed; nothing to write")

    manifest = _build_manifest(
        slug, name, description or "", image_size, seed, shards
    )
    repo.write_json(prefix + _MANIFEST, manifest)
    return _manifest_to_dataset(manifest)


def _read_manifest(slug: str) -> dict:
    data = repo.read_json(_prefix(slug) + _MANIFEST)
    if data is None:
        raise DatasetError(f"Dataset '{slug}' not found", status_code=404)
    return data


def list_datasets() -> list[Dataset]:
    out: list[Dataset] = []
    for obj in repo.list_prefix(DATASETS_PREFIX):
        if not obj["key"].endswith("/" + _MANIFEST):
            continue
        try:
            if (data := repo.read_json(obj["key"])) is not None:
                out.append(_manifest_to_dataset(data))
        except Exception as e:  # one bad/transient manifest must not 500 the list
            logger.warning("Skipping unreadable dataset manifest %s: %s", obj["key"], e)
    out.sort(key=lambda d: d.created_at, reverse=True)
    return out


def get_dataset(slug: str) -> Dataset:
    return _manifest_to_dataset(_read_manifest(slug))


def get_shards(slug: str) -> list[ShardListEntry]:
    manifest = _read_manifest(slug)
    rows: list[ShardListEntry] = []
    for shard in manifest.get("shards", []):
        key = shard["key"]
        rows.append(
            ShardListEntry(
                key=key,
                filename=key.rsplit("/", 1)[-1],
                size_bytes=shard["size_bytes"],
                size_human=humanize_bytes(shard["size_bytes"]),
                count=shard["count"],
                preview_url=repo.presign_get(key),
            )
        )
    return rows


def edit_dataset(slug: str, display_name: str | None, description: str | None) -> Dataset:
    manifest = _read_manifest(slug)
    if display_name is not None:
        manifest["display_name"] = display_name
    if description is not None:
        manifest["description"] = description
    repo.write_json(_prefix(slug) + _MANIFEST, manifest)
    return _manifest_to_dataset(manifest)


def delete_dataset(slug: str) -> int:
    # Prefix-scoped: only this dataset's objects, never a bucket-wide wipe.
    deleted = repo.delete_prefix(_prefix(slug))
    if deleted == 0:
        raise DatasetError(f"Dataset '{slug}' not found", status_code=404)
    return deleted


def get_stats() -> DatasetStats:
    datasets = list_datasets()
    total_shards = sum(d.shard_count for d in datasets)
    total_samples = sum(d.sample_count for d in datasets)
    total_bytes = sum(d.total_size_bytes for d in datasets)
    last_run = _latest_run(datasets)
    return DatasetStats(
        total_datasets=len(datasets),
        total_shards=total_shards,
        total_samples=total_samples,
        total_size_bytes=total_bytes,
        total_size_human=humanize_bytes(total_bytes),
        last_run_samples_per_s=last_run["samples_per_s"] if last_run else None,
        last_run_device=last_run["device"] if last_run else None,
    )


def _latest_run(datasets: list[Dataset]) -> dict | None:
    latest: dict | None = None
    for dataset in datasets:
        run = repo.read_json(_prefix(dataset.slug) + _RUN)
        if run is None:
            continue
        if latest is None or run.get("created_at", "") > latest.get("created_at", ""):
            latest = run
    return latest


def _validate_stream(req: StreamRequest) -> None:
    for value, choices, label in (
        (req.num_workers, NUM_WORKERS_CHOICES, "num_workers"),
        (req.num_nodes, NUM_NODES_CHOICES, "num_nodes"),
        (req.batch_size, BATCH_SIZE_CHOICES, "batch_size"),
        (req.max_batches, MAX_BATCHES_CHOICES, "max_batches"),
        (req.shuffle_buffer, SHUFFLE_BUFFER_CHOICES, "shuffle_buffer"),
    ):
        if value not in choices:
            raise DatasetError(f"{label} must be one of {choices}")


def stream_dataset(slug: str, req: StreamRequest) -> StreamResult:
    _validate_stream(req)
    manifest = _read_manifest(slug)
    shards = manifest.get("shards", [])
    if not shards:
        raise DatasetError("Dataset has no shards to stream", status_code=409)

    # Deterministic shard shuffle by the manifest seed, then build s3:// urls so
    # WebDataset reads each shard body straight from B2 (custom UA, no local copy).
    order = list(range(len(shards)))
    random.Random(manifest.get("seed", 0)).shuffle(order)
    urls = [wds_repo.shard_url(shards[i]["key"]) for i in order]

    sample_count = max(1, manifest.get("sample_count", 1))
    avg_bytes = manifest.get("total_size_bytes", 0) / sample_count
    result = training_service.run_stream(urls, req, len(shards), avg_bytes)

    repo.write_json(_prefix(slug) + _RUN, result.model_dump())
    return result
