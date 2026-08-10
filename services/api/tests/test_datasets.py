"""Dataset CRUD tests — hermetic, by mocking the B2 repo boundary.

No network: an in-memory dict stands in for B2 objects, and shard writing is
replaced with a fake that consumes the (real) sample generator and records
deterministic shard entries. Mirrors the existing repo-boundary mocking style.
"""

import json
from datetime import UTC, datetime

import pytest

from app.repo import datasets_repo, webdataset_repo


@pytest.fixture
def fake_b2(monkeypatch):
    """In-memory object store wired into datasets_repo + webdataset_repo."""
    store: dict[str, bytes] = {}

    def read_json(key):
        raw = store.get(key)
        return json.loads(raw) if raw is not None else None

    def write_json(key, obj):
        store[key] = json.dumps(obj, default=str).encode()

    def list_prefix(prefix):
        return [
            {"key": k, "size": len(v), "last_modified": datetime.now(UTC)}
            for k, v in store.items()
            if k.startswith(prefix)
        ]

    def get_bytes(key):
        return store.get(key)

    def delete_prefix(prefix):
        keys = [k for k in store if k.startswith(prefix)]
        for k in keys:
            del store[k]
        return len(keys)

    def presign_get(key, expires_in=600):
        return f"https://example.test/{key}"

    def write_shards(prefix, samples, samples_per_shard):
        # Consume the real generator so synthetic image gen is exercised, then
        # chunk deterministically into shard records + fake shard objects.
        items = list(samples)
        shards = []
        for start in range(0, len(items), samples_per_shard):
            chunk = items[start : start + samples_per_shard]
            key = f"{prefix}shard-{start // samples_per_shard:06d}.tar"
            store[key] = b"TARDATA" * len(chunk)
            shards.append({"key": key, "size_bytes": len(store[key]), "count": len(chunk)})
        return shards

    monkeypatch.setattr(datasets_repo, "read_json", read_json)
    monkeypatch.setattr(datasets_repo, "write_json", write_json)
    monkeypatch.setattr(datasets_repo, "list_prefix", list_prefix)
    monkeypatch.setattr(datasets_repo, "get_bytes", get_bytes)
    monkeypatch.setattr(datasets_repo, "delete_prefix", delete_prefix)
    monkeypatch.setattr(datasets_repo, "presign_get", presign_get)
    monkeypatch.setattr(webdataset_repo, "write_shards", write_shards)
    return store


async def test_create_writes_manifest_and_shards(client, fake_b2):
    resp = await client.post(
        "/datasets",
        json={
            "name": "Demo Set",
            "source": "synthetic",
            "num_samples": 128,
            "samples_per_shard": 64,
            "image_size": 32,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["slug"] == "demo-set"
    assert body["sample_count"] == 128
    assert body["shard_count"] == 2
    assert body["splits"]["train"] + body["splits"]["val"] == 128
    assert "datasets/demo-set/manifest.json" in fake_b2


async def test_create_rejects_out_of_range_choice(client, fake_b2):
    resp = await client.post(
        "/datasets",
        json={
            "name": "bad",
            "source": "synthetic",
            "num_samples": 999,  # not in the allowed set
            "samples_per_shard": 64,
            "image_size": 32,
        },
    )
    assert resp.status_code == 400


async def test_duplicate_slug_conflicts(client, fake_b2):
    payload = {
        "name": "dup",
        "source": "synthetic",
        "num_samples": 128,
        "samples_per_shard": 128,
        "image_size": 32,
    }
    first = await client.post("/datasets", json=payload)
    assert first.status_code == 200
    second = await client.post("/datasets", json=payload)
    assert second.status_code == 409


async def test_list_and_read_and_shards(client, fake_b2):
    await client.post(
        "/datasets",
        json={
            "name": "listme",
            "source": "synthetic",
            "num_samples": 128,
            "samples_per_shard": 64,
            "image_size": 32,
        },
    )
    listing = await client.get("/datasets")
    assert listing.status_code == 200
    assert [d["slug"] for d in listing.json()] == ["listme"]

    one = await client.get("/datasets/listme")
    assert one.status_code == 200
    assert one.json()["sample_count"] == 128

    shards = await client.get("/datasets/listme/shards")
    assert shards.status_code == 200
    rows = shards.json()
    assert len(rows) == 2
    assert rows[0]["preview_url"].startswith("https://example.test/")


async def test_read_missing_is_404(client, fake_b2):
    resp = await client.get("/datasets/nope")
    assert resp.status_code == 404


async def test_edit_updates_manifest(client, fake_b2):
    await client.post(
        "/datasets",
        json={
            "name": "editme",
            "source": "synthetic",
            "num_samples": 128,
            "samples_per_shard": 128,
            "image_size": 32,
        },
    )
    resp = await client.patch(
        "/datasets/editme",
        json={"display_name": "Renamed", "description": "now with words"},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Renamed"
    manifest = json.loads(fake_b2["datasets/editme/manifest.json"])
    assert manifest["description"] == "now with words"


async def test_delete_is_prefix_scoped(client, fake_b2):
    await client.post(
        "/datasets",
        json={
            "name": "killme",
            "source": "synthetic",
            "num_samples": 128,
            "samples_per_shard": 128,
            "image_size": 32,
        },
    )
    # A neighbour dataset's object must survive a scoped delete.
    fake_b2["datasets/keepme/manifest.json"] = b"{}"
    resp = await client.delete("/datasets/killme")
    assert resp.status_code == 200
    assert not any(k.startswith("datasets/killme/") for k in fake_b2)
    assert "datasets/keepme/manifest.json" in fake_b2


async def test_list_skips_unreadable_manifest(client, fake_b2):
    # A good dataset plus a neighbour whose manifest is corrupt/partially
    # written. One bad manifest must not turn the whole list/stats endpoint
    # into a 500 — the sample streams from B2 where read failures are expected.
    await client.post(
        "/datasets",
        json={
            "name": "goodset",
            "source": "synthetic",
            "num_samples": 128,
            "samples_per_shard": 128,
            "image_size": 32,
        },
    )
    fake_b2["datasets/badset/manifest.json"] = b"{not valid json"

    listing = await client.get("/datasets")
    assert listing.status_code == 200, listing.text
    assert [d["slug"] for d in listing.json()] == ["goodset"]

    stats = await client.get("/datasets/stats")
    assert stats.status_code == 200, stats.text
    assert stats.json()["total_datasets"] == 1


async def test_stats_aggregate(client, fake_b2):
    await client.post(
        "/datasets",
        json={
            "name": "statset",
            "source": "synthetic",
            "num_samples": 256,
            "samples_per_shard": 128,
            "image_size": 32,
        },
    )
    resp = await client.get("/datasets/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_datasets"] == 1
    assert stats["total_shards"] == 2
    assert stats["total_samples"] == 256
    assert stats["last_run_samples_per_s"] is None
