"""Build business outputs from a completed Silver stage."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from billups.common import build_spark, require_paths, write_json
from billups.report import render_previews, render_report
from billups.transforms import gold_frames


def normalize_parquet_filename(directory: Path) -> None:
    """Rename a single Spark part file to a stable Gold filename."""
    parts = list(directory.glob("part-*.parquet"))
    if len(parts) != 1:
        raise ValueError(f"Expected one Parquet part in {directory}, found {len(parts)}")
    parts[0].replace(directory / "data.parquet")
    for checksum in directory.glob(".part-*.crc"):
        checksum.unlink()


def reconcile(silver: DataFrame, cities: DataFrame) -> dict[str, Any]:
    """Reconcile whole-population Silver and Gold counts and amounts."""
    source = silver.agg(
        F.count(F.lit(1)).alias("count"), F.sum("purchase_amount").alias("amount")
    ).first()
    result = cities.agg(
        F.sum("all_attempt_count").alias("count"), F.sum("all_attempt_amount").alias("amount")
    ).first()
    if source["count"] != result["count"] or source["amount"] != result["amount"]:
        raise ValueError(f"Gold reconciliation failed: source={source}, gold={result}")
    return {
        "passed": True,
        "silver_count": source["count"],
        "gold_count": result["count"],
        "silver_amount": str(source["amount"]),
        "gold_amount": str(result["amount"]),
    }


def run(
    silver_dir: Path,
    output_dir: Path,
    results_dir: Path,
    spark: SparkSession | None = None,
) -> None:
    """Overwrite Gold business tables, reconciliation, and reports."""
    require_paths([silver_dir / "transactions"], "Gold")
    owns_spark = spark is None
    spark = spark or build_spark("billups-gold")
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    cached = spark.read.parquet(str(silver_dir / "transactions")).persist(StorageLevel.DISK_ONLY)
    try:
        frames = gold_frames(cached)
        for name, frame in frames.items():
            table_dir = output_dir / name
            frame.coalesce(1).write.mode("overwrite").parquet(str(table_dir))
            normalize_parquet_filename(table_dir)
        persisted = {name: spark.read.parquet(str(output_dir / name)) for name in frames}
        reconciliation = reconcile(cached, persisted["q5_cities"])
        write_json(output_dir / "reconciliation.json", reconciliation)
        render_report(persisted, results_dir / "report.md")
        render_previews(persisted, reconciliation, results_dir / "previews.md")
    finally:
        cached.unpersist()
        if owns_spark:
            spark.stop()


def main() -> None:
    """Run the Silver-to-Gold command-line stage."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--silver-dir", type=Path, default=Path("data/silver"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/gold"))
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    run(args.silver_dir, args.output_dir, args.results_dir)


if __name__ == "__main__":
    main()
