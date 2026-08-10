from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Finite option sets. The web form renders these as selectors; the API also
# validates against them so a hand-crafted request cannot smuggle an unbounded
# value that would blow up ingest time or memory in the verify gate.
SOURCES = ("synthetic", "raw")
NUM_SAMPLES_CHOICES = (128, 256, 512, 1024)
SAMPLES_PER_SHARD_CHOICES = (64, 128, 256)
IMAGE_SIZE_CHOICES = (32, 64)

NUM_WORKERS_CHOICES = (0, 2, 4)
NUM_NODES_CHOICES = (1, 2, 4)
BATCH_SIZE_CHOICES = (16, 32, 64)
MAX_BATCHES_CHOICES = (10, 20, 50)
SHUFFLE_BUFFER_CHOICES = (0, 100, 1000)


class ShardEntry(BaseModel):
    """One WebDataset `.tar` shard as recorded in the manifest."""

    key: str
    size_bytes: int
    count: int


class Dataset(BaseModel):
    """A WebDataset shard collection living under `datasets/<slug>/` in B2.

    This IS the `manifest.json` index — there is no database; the manifest
    object in B2 is the source of truth (stateless-over-B2, like the starter).
    """

    slug: str
    display_name: str
    description: str = ""
    modality: Literal["image"] = "image"
    image_size: int
    seed: int
    created_at: datetime
    sample_count: int
    shard_count: int
    total_size_bytes: int = 0
    size_human: str = ""
    shards: list[ShardEntry] = Field(default_factory=list)
    # Sample counts per split (deterministic 90/10 by default).
    splits: dict[str, int] = Field(default_factory=dict)


class CreateDatasetRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    source: Literal["synthetic", "raw"] = "synthetic"
    num_samples: int = 512
    samples_per_shard: int = 128
    image_size: int = 32


class EditDatasetRequest(BaseModel):
    """Cheap metadata edit — the slug is immutable, only display fields change."""

    display_name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class ShardListEntry(BaseModel):
    """Scoped shard-explorer row for one dataset's detail page."""

    key: str
    filename: str
    size_bytes: int
    size_human: str
    count: int
    preview_url: str | None = None


class DatasetStats(BaseModel):
    """Dataset-centric dashboard aggregates."""

    total_datasets: int
    total_shards: int
    total_samples: int
    total_size_bytes: int
    total_size_human: str
    last_run_samples_per_s: float | None = None
    last_run_device: str | None = None


class StreamRequest(BaseModel):
    num_workers: int = 0
    num_nodes: int = 1
    batch_size: int = 32
    max_batches: int = 20
    shuffle_buffer: int = 100


class ShardAssignment(BaseModel):
    """Which shard indices one worker/node reads under the round-robin split.

    Demonstrates non-overlapping shard ranges across a distributed run even
    when the demo executes single-process.
    """

    rank: int
    world_size: int
    shard_indices: list[int]


class StreamResult(BaseModel):
    device: str
    elapsed_s: float
    samples: int
    batches: int
    bytes_read: int
    samples_per_s: float
    mb_per_s: float
    loss_curve: list[float]
    worker_plan: list[ShardAssignment]
    node_plan: list[ShardAssignment]
    num_workers: int
    num_nodes: int
    batch_size: int
    created_at: datetime
