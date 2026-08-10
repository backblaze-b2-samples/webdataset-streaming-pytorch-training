"""Deterministic synthetic image generation for a zero-download demo dataset.

Produces N labeled images with a real per-class visual signal (a class-colored
background plus seeded noise), so the tiny CNN's loss actually moves during a
streaming run — while needing no external download and no prior upload. Fully
determined by the dataset seed, so re-creating a dataset with the same
parameters yields byte-identical shards.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
from PIL import Image

NUM_CLASSES = 10

# One distinct base color per class — the signal the CNN learns.
_PALETTE = (
    (220, 40, 40),
    (40, 180, 60),
    (40, 90, 220),
    (230, 200, 40),
    (200, 60, 200),
    (40, 200, 200),
    (240, 140, 40),
    (120, 120, 120),
    (150, 90, 40),
    (30, 30, 30),
)


def _make_image(label: int, image_size: int, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = np.array(_PALETTE[label % NUM_CLASSES], dtype=np.int16)
    noise = rng.integers(-30, 31, size=(image_size, image_size, 3), dtype=np.int16)
    arr = np.clip(base.reshape(1, 1, 3) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def generate_samples(
    num_samples: int, image_size: int, seed: int
) -> Iterator[dict]:
    """Yield WebDataset sample dicts (``{"__key__", "png", "cls"}``).

    Labels are assigned round-robin so every class is balanced, and each image
    is seeded from ``seed + index`` for reproducibility.
    """
    for index in range(num_samples):
        label = index % NUM_CLASSES
        image = _make_image(label, image_size, seed + index)
        yield {"__key__": f"sample{index:06d}", "png": image, "cls": label}
