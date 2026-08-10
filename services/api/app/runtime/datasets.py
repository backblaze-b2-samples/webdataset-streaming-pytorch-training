import logging

# The dataset handlers are intentionally sync `def`: create/stream do blocking
# boto3 + CPU-bound (PIL/torch) work, and a sync handler runs in Starlette's
# threadpool so one slow ingest/run doesn't stall the event loop.
from fastapi import APIRouter, HTTPException

from app.service.datasets import (
    DatasetError,
    create_dataset,
    delete_dataset,
    edit_dataset,
    get_dataset,
    get_shards,
    get_stats,
    list_datasets,
    stream_dataset,
)
from app.types import (
    CreateDatasetRequest,
    Dataset,
    DatasetStats,
    EditDatasetRequest,
    ShardListEntry,
    StreamRequest,
    StreamResult,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: like /files, these routes are intentionally UNAUTHENTICATED and
# bucket-wide (single-tenant demo stance — see docs/SECURITY.md). A multi-tenant
# clone must add auth AND scope the datasets/ prefix per caller.


def _raise(err: DatasetError) -> None:
    raise HTTPException(status_code=err.status_code, detail=err.detail) from None


@router.post("/datasets", response_model=Dataset)
def create_dataset_endpoint(req: CreateDatasetRequest):
    try:
        dataset = create_dataset(
            name=req.name,
            description=req.description,
            source=req.source,
            num_samples=req.num_samples,
            samples_per_shard=req.samples_per_shard,
            image_size=req.image_size,
        )
    except DatasetError as e:
        logger.warning("Dataset create rejected: %s", e.detail)
        _raise(e)
    logger.info(
        "Dataset created: slug=%s samples=%d shards=%d",
        dataset.slug,
        dataset.sample_count,
        dataset.shard_count,
    )
    return dataset


@router.get("/datasets", response_model=list[Dataset])
def list_datasets_endpoint():
    return list_datasets()


# Declared BEFORE /datasets/{slug} so the literal "stats" segment is matched
# by this route rather than captured as a slug.
@router.get("/datasets/stats", response_model=DatasetStats)
def dataset_stats_endpoint():
    return get_stats()


@router.get("/datasets/{slug}", response_model=Dataset)
def get_dataset_endpoint(slug: str):
    try:
        return get_dataset(slug)
    except DatasetError as e:
        _raise(e)


@router.get("/datasets/{slug}/shards", response_model=list[ShardListEntry])
def dataset_shards_endpoint(slug: str):
    try:
        return get_shards(slug)
    except DatasetError as e:
        _raise(e)


@router.patch("/datasets/{slug}", response_model=Dataset)
def edit_dataset_endpoint(slug: str, req: EditDatasetRequest):
    try:
        return edit_dataset(slug, req.display_name, req.description)
    except DatasetError as e:
        _raise(e)


@router.delete("/datasets/{slug}")
def delete_dataset_endpoint(slug: str):
    try:
        deleted = delete_dataset(slug)
    except DatasetError as e:
        _raise(e)
    logger.info("Dataset deleted: slug=%s objects=%d", slug, deleted)
    return {"deleted": True, "slug": slug, "objects": deleted}


@router.post("/datasets/{slug}/stream", response_model=StreamResult)
def stream_dataset_endpoint(slug: str, req: StreamRequest):
    try:
        result = stream_dataset(slug, req)
    except DatasetError as e:
        logger.warning("Dataset stream rejected: %s", e.detail)
        _raise(e)
    logger.info(
        "Dataset stream complete: slug=%s device=%s samples_per_s=%.2f",
        slug,
        result.device,
        result.samples_per_s,
    )
    return result
