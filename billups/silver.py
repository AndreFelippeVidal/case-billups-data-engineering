"""Validate and enrich a completed Bronze stage into Silver."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from billups.common import add_load_metadata, build_spark, json_value, require_paths, write_json
from billups.transforms import to_silver


def quality_metrics(silver: DataFrame, conflicts: DataFrame) -> dict[str, Any]:
    """Collect proportional Silver data-quality metrics."""
    row = silver.agg(
        F.count(F.lit(1)).alias("row_count"),
        F.sum(F.when(F.col("merchant_id").isNull(), 1).otherwise(0)).alias("missing_merchant_id"),
        F.sum(F.when(~F.col("merchant_lookup_matched"), 1).otherwise(0)).alias("unmatched_merchant_lookup"),
        F.sum(F.when(F.col("category") == "Unknown category", 1).otherwise(0)).alias("unknown_category"),
        F.sum(F.when(F.col("city_id").isNull() | (F.col("city_id") == -1), 1).otherwise(0)).alias("unknown_city"),
        F.sum(F.when(F.col("state_id").isNull() | (F.col("state_id") == -1), 1).otherwise(0)).alias("unknown_state"),
        F.sum(F.when(F.col("authorized_flag") == "N", 1).otherwise(0)).alias("denied"),
        F.sum(F.when(~F.col("authorized_flag").isin("Y", "N") | F.col("authorized_flag").isNull(), 1).otherwise(0)).alias("unknown_authorization"),
        F.sum(F.when(F.col("purchase_amount") <= 0, 1).otherwise(0)).alias("nonpositive_amount"),
        F.sum(F.when(F.col("installments").isNull() | (F.col("installments") < 0) | (F.col("installments") == 999), 1).otherwise(0)).alias("unknown_installments"),
        F.sum("purchase_amount").alias("total_amount"),
    ).first().asDict()
    row["ambiguous_merchant_ids"] = conflicts.count()
    return {key: json_value(value) for key, value in row.items()}


def run(bronze_dir: Path, output_dir: Path, spark: SparkSession | None = None) -> None:
    """Overwrite validated and merchant-enriched Silver outputs."""
    require_paths(
        [bronze_dir / "historical_transactions", bronze_dir / "merchants"], "Silver"
    )
    owns_spark = spark is None
    spark = spark or build_spark("billups-silver")
    output_dir.mkdir(parents=True, exist_ok=True)
    cached = None
    try:
        transactions = spark.read.parquet(str(bronze_dir / "historical_transactions"))
        merchants = spark.read.parquet(str(bronze_dir / "merchants"))
        result = to_silver(transactions, merchants)
        loaded_at = datetime.now(timezone.utc)
        cached = add_load_metadata(
            result.transactions, "silver", loaded_at
        ).persist(StorageLevel.DISK_ONLY)
        cached.write.mode("overwrite").parquet(str(output_dir / "transactions"))
        add_load_metadata(result.merchant_lookup, "silver", loaded_at).write.mode(
            "overwrite"
        ).parquet(str(output_dir / "merchant_lookup"))
        add_load_metadata(result.merchant_conflicts, "silver", loaded_at).write.mode(
            "overwrite"
        ).parquet(str(output_dir / "merchant_conflicts"))
        write_json(output_dir / "dq.json", quality_metrics(cached, result.merchant_conflicts))
    finally:
        if cached is not None:
            cached.unpersist(blocking=True)
        if owns_spark:
            spark.stop()


def main() -> None:
    """Run the Bronze-to-Silver command-line stage."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--bronze-dir", type=Path, default=Path("data/bronze"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/silver"))
    args = parser.parse_args()
    run(args.bronze_dir, args.output_dir)


if __name__ == "__main__":
    main()
