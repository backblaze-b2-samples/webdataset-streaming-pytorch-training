"""The bounded PyTorch training loop that streams shards from B2.

Device selection is runtime auto-detect: CUDA -> Apple MPS -> CPU, defaulting to
CPU. There is no hard GPU requirement anywhere (this feature is
``deployment: local``). The loop is capped at ``max_batches`` and uses a tiny
CNN so a demo run completes in seconds on CPU.

torch lives only in this module (the service layer); the WebDataset/B2
streaming boundary — and all boto3 — stays in ``repo/webdataset_repo``.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import numpy as np
import torch
from torch import nn

from app.repo import webdataset_repo as wds_repo
from app.service.synthetic import NUM_CLASSES
from app.types import ShardAssignment, StreamRequest, StreamResult


def pick_device() -> str:
    """First available of CUDA -> Apple MPS -> CPU (CPU default).

    Never hard-requires a GPU: a machine with neither CUDA nor MPS simply runs
    on CPU, which is the reliable path for the verify gate.
    """
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


class TinyCNN(nn.Module):
    """A deliberately small CNN — enough to exercise a real forward+backward
    pass on streamed batches without dominating the streaming throughput we
    are measuring. AdaptiveAvgPool makes it work for any input image size."""

    def __init__(self, num_classes: int = NUM_CLASSES):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 8, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(8, 16, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(4),
        )
        self.head = nn.Linear(16 * 4 * 4, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = torch.flatten(x, 1)
        return self.head(x)


def _as_float_tensor(batch_images, device: str) -> torch.Tensor:
    array = np.asarray(batch_images, dtype=np.float32)
    return torch.as_tensor(array, dtype=torch.float32, device=device)


def _as_long_tensor(batch_labels, device: str) -> torch.Tensor:
    array = np.asarray(batch_labels).astype(np.int64)
    return torch.as_tensor(array, dtype=torch.long, device=device)


def run_stream(
    urls: list[str],
    req: StreamRequest,
    shard_count: int,
    avg_bytes_per_sample: float,
) -> StreamResult:
    """Stream shards from B2 and run a bounded training loop over them.

    ``urls`` are the ``s3://`` shard URLs (already seed-shuffled by the caller).
    Returns throughput, the per-step loss curve, and the worker/node shard
    plans. Reads nothing to local disk — WebDataset pulls each shard body
    through the B2 opener.
    """
    device = pick_device()
    model = TinyCNN().to(device)
    model.train()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.05, momentum=0.9)
    loss_fn = nn.CrossEntropyLoss()

    loader = wds_repo.make_loader(
        urls,
        batch_size=req.batch_size,
        num_workers=req.num_workers,
        shuffle_buffer=req.shuffle_buffer,
    )

    loss_curve: list[float] = []
    samples = 0
    batches = 0
    start = time.perf_counter()
    for batch_images, batch_labels in loader:
        if batches >= req.max_batches:
            break
        images = _as_float_tensor(batch_images, device)
        labels = _as_long_tensor(batch_labels, device)
        optimizer.zero_grad()
        logits = model(images)
        loss = loss_fn(logits, labels)
        loss.backward()
        optimizer.step()
        loss_curve.append(round(float(loss.detach().cpu()), 4))
        samples += int(images.shape[0])
        batches += 1
    elapsed = max(time.perf_counter() - start, 1e-6)

    bytes_read = int(samples * avg_bytes_per_sample)
    worker_plan = [
        ShardAssignment(**a)
        for a in wds_repo.compute_split_plan(shard_count, max(1, req.num_workers))
    ]
    node_plan = [
        ShardAssignment(**a)
        for a in wds_repo.compute_split_plan(shard_count, req.num_nodes)
    ]

    return StreamResult(
        device=device,
        elapsed_s=round(elapsed, 4),
        samples=samples,
        batches=batches,
        bytes_read=bytes_read,
        samples_per_s=round(samples / elapsed, 2),
        mb_per_s=round((bytes_read / 1_000_000) / elapsed, 3),
        loss_curve=loss_curve,
        worker_plan=worker_plan,
        node_plan=node_plan,
        num_workers=req.num_workers,
        num_nodes=req.num_nodes,
        batch_size=req.batch_size,
        created_at=datetime.now(UTC),
    )
