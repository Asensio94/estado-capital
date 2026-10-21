"""Parquet persistence for data/processed and optional upload to S3."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pandas as pd

from core.config import PROCESSED_DIR

log = logging.getLogger(__name__)


def write_processed(df: pd.DataFrame, name: str) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / f"{name}.parquet"
    df.to_parquet(path, index=False)
    log.info("wrote %s (%d rows)", path, len(df))
    return path


def read_processed(name: str) -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / f"{name}.parquet")


def write_manifest(manifest: dict) -> Path:
    path = PROCESSED_DIR / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def read_manifest() -> dict:
    return json.loads((PROCESSED_DIR / "manifest.json").read_text(encoding="utf-8"))


def upload_processed_to_s3() -> list[str]:
    """Copy data/processed/* to s3://$CAPITAL_S3_BUCKET/$CAPITAL_S3_PREFIX.

    Credentials come from the standard AWS chain (env vars, profile, role); none live in code.
    """
    bucket = os.environ.get("CAPITAL_S3_BUCKET")
    if not bucket:
        raise RuntimeError("CAPITAL_S3_BUCKET is not set")
    prefix = os.environ.get("CAPITAL_S3_PREFIX", "estado-capital/processed").strip("/")

    import boto3  # optional dependency: pip install .[s3]

    s3 = boto3.client("s3")
    keys = []
    for path in sorted(PROCESSED_DIR.iterdir()):
        if path.name.startswith("."):
            continue
        key = f"{prefix}/{path.name}"
        s3.upload_file(str(path), bucket, key)
        keys.append(key)
        log.info("uploaded s3://%s/%s", bucket, key)
    return keys
