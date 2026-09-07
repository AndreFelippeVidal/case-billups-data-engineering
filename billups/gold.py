"""Build business outputs from a completed Silver stage."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from billups.common import build_spark, json_value, require_completed_stage, write_json
from billups.report import render_report
from billups.transforms import gold_frames


def reconcile(silver: DataFrame, cities: DataFrame) -> dict[str, Any]:
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


def write_preview(frame: DataFrame, destination: Path, rows: int = 20) -> None:
    records = [
        {key: json_value(value) for key, value in row.asDict(recursive=True).items()}
        for row in frame.limit(rows).collect()
    ]
    write_json(destination, records)


def run(
    silver_dir: Path,
    output_dir: Path,
    publish_gold: Path | None = None,
    spark: SparkSession | None = None,
) -> None:
    require_completed_stage(silver_dir, "Silver")
    if output_dir.exists():
        raise FileExistsError(f"Gold output directory already exists: {output_dir}")
    if publish_gold and publish_gold.exists():
        raise FileExistsError(f"Published Gold directory already exists: {publish_gold}")
    owns_spark = spark is None
    spark = spark or build_spark("billups-gold")
    output_dir.mkdir(parents=True)
    previews_dir = output_dir / "previews"
    previews_dir.mkdir()
    cached = spark.read.parquet(str(silver_dir / "transactions")).persist(StorageLevel.DISK_ONLY)
    try:
        frames = gold_frames(cached)
        for name, frame in frames.items():
            frame.coalesce(1).write.mode("errorifexists").parquet(str(output_dir / name))
        persisted = {name: spark.read.parquet(str(output_dir / name)) for name in frames}
        reconciliation = reconcile(cached, persisted["q5_cities"])
        write_json(output_dir / "dq.json", {"reconciliation": reconciliation})
        report_metadata = render_report(persisted, output_dir / "report.md")
        for name, frame in persisted.items():
            columns = frame.columns[: min(3, len(frame.columns))]
            write_preview(frame.orderBy(*columns), previews_dir / f"{name}.json")
        success = {
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "dq": "dq.json",
            "gold_tables": sorted(frames),
            "report": "report.md",
            "report_metadata": report_metadata,
            "stage": "gold",
        }
        write_json(output_dir / "SUCCESS.json", success)
        if publish_gold:
            publish_gold.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(output_dir, publish_gold)
    finally:
        cached.unpersist()
        if owns_spark:
            spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--silver-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--publish-gold", type=Path)
    args = parser.parse_args()
    run(args.silver_dir, args.output_dir, args.publish_gold)


if __name__ == "__main__":
    main()
