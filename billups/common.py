"""Shared local pipeline utilities."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def configure_logging() -> None:
    """Configure concise operational logs for command-line pipeline runs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("py4j").setLevel(logging.WARNING)


def build_spark(app_name: str) -> SparkSession:
    """Create the local Spark session used by pipeline stages."""
    spark = (
        SparkSession.builder.master("local[2]")
        .appName(app_name)
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "16")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.marksuccessfuljobs", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def add_load_metadata(
    frame: DataFrame,
    stage: str,
    loaded_at: datetime,
    source_file_name: str | None = None,
) -> DataFrame:
    """Add consistent source and stage-load metadata columns."""
    result = frame
    if source_file_name is not None:
        result = result.withColumn("source_file_name", F.lit(source_file_name))
    return result.withColumn(
        f"{stage}_load_timestamp", F.lit(loaded_at).cast("timestamp")
    )


def sha256(path: Path) -> str:
    """Calculate a deterministic SHA-256 for a file or dataset directory."""
    digest = hashlib.sha256()
    files = [path] if path.is_file() else sorted(item for item in path.rglob("*") if item.is_file())
    for file in files:
        if path.is_dir():
            digest.update(file.relative_to(path).as_posix().encode("utf-8"))
        with file.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def source_bytes(path: Path) -> int:
    """Return the total byte size of a file or dataset directory."""
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def json_value(value: Any) -> Any:
    """Convert supported analytical values to JSON-safe values."""
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def write_json(path: Path, value: Any) -> None:
    """Write formatted deterministic JSON to a local path."""
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=json_value) + "\n", encoding="utf-8")


def require_paths(paths: list[Path], stage: str) -> None:
    """Require the input paths needed by a pipeline stage."""
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"{stage} inputs are missing: {', '.join(missing)}")
