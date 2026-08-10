"""B2 object operations for datasets.

Focused, low-level S3 helpers the dataset service builds on: raw byte/JSON
put+get, prefix listing, and a prefix-scoped bulk delete. Kept in the repo/
layer (boto3 lives only here) and separate from ``b2_client`` — which returns
``FileMetadata`` models for the file browser — so this module can stay under the
300-line ceiling and speak in plain keys/bytes.

Deletes are ALWAYS scoped to a caller-supplied prefix; there is no
bucket-wide wipe path, per the repo safety rule.
"""

from __future__ import annotations

import io
import json

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache


def put_bytes(key: str, data: bytes, content_type: str) -> int:
    """Write raw bytes to ``key``. Returns the byte length. Raises RuntimeError."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put_object failed for '{key}': {e}") from e
    _invalidate_list_cache()
    return len(data)


def write_json(key: str, obj: dict) -> None:
    """Serialize ``obj`` and write it as application/json."""
    put_bytes(key, json.dumps(obj, default=str).encode("utf-8"), "application/json")


def get_bytes(key: str) -> bytes | None:
    """Read an object's bytes, or None if it does not exist. Raises on other errors."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return response["Body"].read()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get_object failed for '{key}': {e}") from e
    except BotoCoreError as e:
        raise RuntimeError(f"B2 get_object failed for '{key}': {e}") from e


def read_json(key: str) -> dict | None:
    """Read+parse a JSON object, or None if missing."""
    raw = get_bytes(key)
    if raw is None:
        return None
    return json.loads(raw)


def list_prefix(prefix: str) -> list[dict]:
    """Every object under ``prefix`` as ``{key, size, last_modified}`` dicts.

    Paginates fully so callers see every key, not just the first 1000. Raises
    RuntimeError on S3 failure.
    """
    client = get_s3_client()
    out: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                out.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    }
                )
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 list failed for prefix '{prefix}': {e}") from e
    return out


def delete_prefix(prefix: str) -> int:
    """Delete every object under ``prefix`` (batched). Returns the count deleted.

    SAFETY: the caller is responsible for passing a specific, non-empty prefix
    (e.g. ``datasets/<slug>/``); an empty prefix is rejected so a bug can never
    turn this into a bucket-wide wipe.
    """
    if not prefix or prefix in ("/", "*"):
        raise ValueError("delete_prefix requires a specific non-empty prefix")
    client = get_s3_client()
    keys = [{"Key": obj["key"]} for obj in list_prefix(prefix)]
    if not keys:
        return 0
    deleted = 0
    try:
        for start in range(0, len(keys), 1000):
            batch = keys[start : start + 1000]
            client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": batch, "Quiet": True},
            )
            deleted += len(batch)
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 delete failed for prefix '{prefix}': {e}") from e
    _invalidate_list_cache()
    return deleted


def presign_get(key: str, expires_in: int = 600) -> str:
    """Presigned inline GET URL for previewing a shard/object in the browser."""
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.b2_bucket_name,
                "Key": key,
                "ResponseContentDisposition": "inline",
            },
            ExpiresIn=expires_in,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e
