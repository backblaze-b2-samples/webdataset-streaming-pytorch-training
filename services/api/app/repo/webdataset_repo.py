"""The B2 <-> WebDataset boundary.

This is where WebDataset is taught to read and write shards directly on
Backblaze B2 over the S3 API — no local staging disk:

* ``register_b2_opener`` installs a custom ``s3://`` scheme in
  ``webdataset.gopen.gopen_schemes`` that streams object bodies through the
  SAME custom-user-agent boto3 client the rest of the app uses
  (``repo.b2_client.get_s3_client``). Every shard GET therefore carries the B2
  attribution user agent, and nothing is copied to disk first.
* ``write_shards`` drives ``wds.ShardWriter`` with a ``post`` callback that
  uploads each finished ``.tar`` to B2 and deletes the local temp file, so
  shards land directly in the bucket.
* ``make_loader`` builds the ``WebDataset``/``WebLoader`` streaming pipeline
  used by the PyTorch training loop.

boto3 stays confined to the repo/ layer; this module lives here for that
reason. It imports ``webdataset``/``numpy`` (data libraries, not an external
service SDK) but never ``torch`` — the training loop owns torch in service/.
"""

from __future__ import annotations

import importlib
import os
import tempfile
from collections.abc import Iterable, Iterator
from urllib.parse import urlparse

import numpy as np
import webdataset as wds

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache

# The `webdataset.gopen` NAME is the re-exported gopen() function, not the
# submodule that owns the `gopen_schemes` dispatch table — import the submodule
# explicitly so the s3:// scheme can be registered on it.
_gopen = importlib.import_module("webdataset.gopen")

_S3_SCHEME = "s3"


def _s3_opener(url: str, mode: str = "rb", bufsize: int = 8192, **_kw):
    """Stream an ``s3://bucket/key`` object body through the app's B2 client.

    Returns the boto3 ``StreamingBody`` (a read-only file-like) so WebDataset's
    tar reader consumes shard bytes sequentially with no local copy. The
    custom user agent rides along because this reuses ``get_s3_client``.
    """
    if mode != "rb":
        raise ValueError(f"s3:// opener is read-only; got mode={mode!r}")
    parsed = urlparse(url)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    response = get_s3_client().get_object(Bucket=bucket, Key=key)
    return response["Body"]


def register_b2_opener() -> None:
    """Install (idempotently) the ``s3://`` scheme in WebDataset's opener table."""
    _gopen.gopen_schemes[_S3_SCHEME] = _s3_opener


# Register at import time so DataLoader worker processes — which re-import this
# module on spawn — also get the s3:// scheme, not just the parent process.
register_b2_opener()


def shard_url(key: str) -> str:
    """The ``s3://`` URL WebDataset reads a shard from, for the current bucket."""
    return f"s3://{settings.b2_bucket_name}/{key}"


def write_shards(
    prefix: str, samples: Iterable[dict], samples_per_shard: int
) -> list[dict]:
    """Pack ``samples`` into WebDataset ``.tar`` shards written directly to B2.

    ``prefix`` ends with ``/`` (e.g. ``datasets/<slug>/``). ``samples`` yields
    WebDataset sample dicts (``{"__key__", "png": PIL.Image, "cls": int}``).
    Returns ``[{key, size_bytes, count}]`` in shard order. Uses a temp dir the
    ``post`` callback empties as each shard finishes, so peak local disk is one
    shard regardless of dataset size.
    """
    client = get_s3_client()
    recorded: list[dict] = []
    with tempfile.TemporaryDirectory() as tmp:
        pattern = os.path.join(tmp, "shard-%06d.tar")
        # maxsize is set absurdly high so ONLY maxcount triggers rotation —
        # that keeps shard membership deterministic for the manifest.
        writer = wds.ShardWriter(
            pattern, maxcount=samples_per_shard, maxsize=10**12, verbose=0
        )

        def _post(fname: str) -> None:
            # Called by ShardWriter as each shard closes; writer.count is that
            # finished shard's sample count at this point.
            key = prefix + os.path.basename(fname)
            size = os.path.getsize(fname)
            count = writer.count
            with open(fname, "rb") as handle:
                client.put_object(
                    Bucket=settings.b2_bucket_name,
                    Key=key,
                    Body=handle,
                    ContentType="application/x-tar",
                )
            recorded.append({"key": key, "size_bytes": size, "count": count})
            os.remove(fname)

        writer.post = _post
        for sample in samples:
            writer.write(sample)
        writer.close()
    _invalidate_list_cache()
    return recorded


def _pil_to_chw(img) -> np.ndarray:
    """Decode a PIL image to a CHW float32 array in [0, 1].

    Module-level (not a closure) so it pickles cleanly for DataLoader workers.
    """
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    return np.transpose(arr, (2, 0, 1))


def _identity(x):
    return x


def make_loader(
    urls: list[str],
    batch_size: int,
    num_workers: int,
    shuffle_buffer: int,
):
    """Build the streaming ``WebLoader`` the training loop iterates.

    Shards are already deterministically ordered by the caller (seeded shuffle),
    so ``shardshuffle`` is off; ``nodesplitter=split_by_node`` gives each
    distributed rank a non-overlapping shard range. Images decode to CHW float
    arrays; the loop converts them to torch tensors on the selected device.
    """
    ds = wds.WebDataset(
        urls,
        nodesplitter=wds.split_by_node,
        shardshuffle=False,
        empty_check=False,
    )
    if shuffle_buffer and shuffle_buffer > 0:
        ds = ds.shuffle(shuffle_buffer)
    ds = (
        ds.decode("pil")
        .to_tuple("png;jpg;jpeg", "cls")
        .map_tuple(_pil_to_chw, _identity)
        .batched(batch_size)
    )
    return wds.WebLoader(ds, num_workers=num_workers, batch_size=None)


def iter_local_tuples(urls: list[str]) -> Iterator[tuple]:
    """Iterate ``(CHW float array, label)`` samples with no batching/workers.

    Used by the hermetic unit test to read a locally-built tar (``file://``
    urls) without touching the network or a DataLoader.
    """
    ds = (
        wds.WebDataset(urls, shardshuffle=False, empty_check=False)
        .decode("pil")
        .to_tuple("png;jpg;jpeg", "cls")
        .map_tuple(_pil_to_chw, _identity)
    )
    yield from ds


def compute_split_plan(num_shards: int, world_size: int) -> list[dict]:
    """Which shard indices each rank reads under WebDataset's round-robin split.

    Mirrors ``split_by_node``/``split_by_worker`` exactly
    (``islice(src, rank, None, world_size)`` == ``indices[rank::world_size]``),
    so the UI can show non-overlapping shard ranges even when the demo runs in a
    single process.
    """
    world_size = max(1, world_size)
    return [
        {
            "rank": rank,
            "world_size": world_size,
            "shard_indices": list(range(rank, num_shards, world_size)),
        }
        for rank in range(world_size)
    ]
