"""Hermetic streaming/training checks — no network.

Builds a WebDataset tar locally, reads it back through the same decode/transform
pipeline the B2 loader uses (via file:// URLs), and runs one forward pass of the
tiny CNN. Also asserts the s3:// opener is installed and the shard split plan
matches WebDataset's round-robin semantics.
"""

import importlib
import os

import torch
import webdataset as wds

from app.repo import webdataset_repo
from app.service import synthetic
from app.service.training import TinyCNN, pick_device


def test_register_b2_opener_installs_s3_scheme():
    webdataset_repo.register_b2_opener()
    gopen_mod = importlib.import_module("webdataset.gopen")
    assert "s3" in gopen_mod.gopen_schemes
    assert gopen_mod.gopen_schemes["s3"] is webdataset_repo._s3_opener


def test_s3_opener_rejects_write_mode():
    import pytest

    with pytest.raises(ValueError):
        webdataset_repo._s3_opener("s3://bucket/key", mode="wb")


def test_local_tar_streams_and_model_does_forward_pass(tmp_path):
    # Build a real tar shard locally (no B2).
    shard = os.path.join(tmp_path, "shard-000000.tar")
    writer = wds.ShardWriter(
        os.path.join(tmp_path, "shard-%06d.tar"),
        maxcount=100,
        maxsize=10**12,
        verbose=0,
    )
    for sample in synthetic.generate_samples(12, image_size=32, seed=7):
        writer.write(sample)
    writer.close()
    assert os.path.exists(shard)

    # Read it back through the same decode+transform pipeline the B2 path uses.
    tuples = list(webdataset_repo.iter_local_tuples([f"file://{shard}"]))
    assert len(tuples) == 12
    image, label = tuples[0]
    assert image.shape == (3, 32, 32)
    assert isinstance(label, int)

    # One forward pass of the tiny CNN on the streamed sample (CPU is fine).
    model = TinyCNN().to("cpu")
    batch = torch.as_tensor(image, dtype=torch.float32).unsqueeze(0)
    logits = model(batch)
    assert logits.shape == (1, synthetic.NUM_CLASSES)


def test_pick_device_returns_supported_backend():
    assert pick_device() in {"cuda", "mps", "cpu"}


def test_split_plan_is_round_robin_and_non_overlapping():
    plan = webdataset_repo.compute_split_plan(num_shards=5, world_size=2)
    assert plan[0]["shard_indices"] == [0, 2, 4]
    assert plan[1]["shard_indices"] == [1, 3]
    # Non-overlapping and complete.
    seen = sorted(i for a in plan for i in a["shard_indices"])
    assert seen == [0, 1, 2, 3, 4]


def test_split_plan_single_rank_reads_all():
    plan = webdataset_repo.compute_split_plan(num_shards=4, world_size=1)
    assert plan == [{"rank": 0, "world_size": 1, "shard_indices": [0, 1, 2, 3]}]
