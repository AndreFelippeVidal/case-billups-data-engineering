"""Build business outputs from a completed Silver stage."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

from billups.common import add_load_metadata, build_spark, require_paths, write_json
from billups.report import render_previews, render_report
from billups.transforms import gold_frames


QUALITY_SCHEMA = T.StructType(
    [
        T.StructField("check_name", T.StringType(), False),
        T.StructField("status", T.StringType(), False),
        T.StructField("result_count", T.LongType(), False),
        T.StructField("population_count", T.LongType(), True),
        T.StructField("result_rate", T.DoubleType(), True),
        T.StructField("description", T.StringType(), False),
    ]
)


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


def quality_rows(metrics: dict[str, Any], reconciliation: dict[str, Any]) -> list[tuple[Any, ...]]:
    """Convert Silver checks and Gold reconciliation into presentation rows."""
    population = int(metrics["row_count"])
    rows_dropped = population - int(reconciliation["gold_count"])

    def warning_status(count: int) -> str:
        """Return Passed when a warning condition has no affected rows."""
        return "Passed" if count == 0 else "Warning"

    definitions = [
        ("Rows processed", "Informational", population, population, "Silver rows evaluated by the quality checks."),
        ("Rows dropped", warning_status(rows_dropped), rows_dropped, population, "Rows not conserved between Silver and reconciled Gold."),
        ("Missing merchant ID", warning_status(int(metrics["missing_merchant_id"])), int(metrics["missing_merchant_id"]), population, "Transactions without a merchant identifier; name falls back to Unknown merchant."),
        ("Unmatched merchant lookup", warning_status(int(metrics["unmatched_merchant_lookup"])), int(metrics["unmatched_merchant_lookup"]), population, "Transactions without a matching merchant metadata row; merchant ID is used as the name."),
        ("Merchant identity collisions", warning_status(int(metrics["ambiguous_merchant_ids"])), int(metrics["ambiguous_merchant_ids"]), None, "Merchant IDs associated with more than one nonblank source name."),
        ("Unknown category", warning_status(int(metrics["unknown_category"])), int(metrics["unknown_category"]), population, "Null or blank categories retained as Unknown category."),
        ("Unknown city", warning_status(int(metrics["unknown_city"])), int(metrics["unknown_city"]), population, "Null or -1 transaction city identifiers."),
        ("Unknown state", warning_status(int(metrics["unknown_state"])), int(metrics["unknown_state"]), population, "Null or -1 transaction state identifiers."),
        ("Denied authorization", "Informational", int(metrics["denied"]), population, "Valid denied attempts retained for recorded-attempt analysis."),
        ("Unknown authorization", warning_status(int(metrics["unknown_authorization"])), int(metrics["unknown_authorization"]), population, "Authorization values outside Y and N."),
        ("Nonpositive amount", warning_status(int(metrics["nonpositive_amount"])), int(metrics["nonpositive_amount"]), population, "Purchase amounts less than or equal to zero."),
        ("Unknown installments", warning_status(int(metrics["unknown_installments"])), int(metrics["unknown_installments"]), population, "Null, negative, or sentinel 999 installment values."),
    ]
    return [
        (
            name,
            status,
            count,
            denominator,
            count / denominator if denominator else None,
            description,
        )
        for name, status, count, denominator, description in definitions
    ]


def warning_samples(silver: DataFrame, limit_per_check: int = 5) -> DataFrame:
    """Return deterministic bounded examples for observable warning conditions."""
    columns = [
        "merchant_id",
        "merchant_name",
        "purchase_date",
        "city_id",
        "state_id",
        "category",
        "installments",
        "authorized_flag",
        "purchase_amount",
    ]
    checks = [
        ("Missing merchant ID", F.col("merchant_id").isNull()),
        ("Unmatched merchant lookup", ~F.col("merchant_lookup_matched")),
        ("Unknown category", F.col("category") == "Unknown category"),
        ("Unknown state", F.col("state_id").isNull() | (F.col("state_id") == -1)),
        (
            "Unknown installments",
            F.col("installments").isNull()
            | (F.col("installments") < 0)
            | (F.col("installments") == 999),
        ),
    ]
    tagged = [
        silver.filter(condition).select(F.lit(name).alias("check_name"), *columns)
        for name, condition in checks
    ]
    combined = tagged[0]
    for frame in tagged[1:]:
        combined = combined.unionByName(frame)
    order = Window.partitionBy("check_name").orderBy(
        F.asc_nulls_last("merchant_id"),
        F.asc("purchase_date"),
        F.asc_nulls_last("city_id"),
        F.asc_nulls_last("state_id"),
    )
    return (
        combined.withColumn("sample_rank", F.row_number().over(order))
        .filter(F.col("sample_rank") <= limit_per_check)
        .select("check_name", "sample_rank", *columns)
        .orderBy("check_name", "sample_rank")
    )


def run(
    silver_dir: Path,
    output_dir: Path,
    results_dir: Path,
    spark: SparkSession | None = None,
) -> None:
    """Overwrite Gold business tables, reconciliation, and reports."""
    require_paths(
        [silver_dir / "transactions", silver_dir / "merchant_conflicts", silver_dir / "dq.json"],
        "Gold",
    )
    owns_spark = spark is None
    spark = spark or build_spark("billups-gold")
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    cached = spark.read.parquet(str(silver_dir / "transactions")).persist(StorageLevel.DISK_ONLY)
    try:
        loaded_at = datetime.now(timezone.utc)
        frames = gold_frames(cached)
        for name, frame in frames.items():
            table_dir = output_dir / name
            add_load_metadata(frame, "gold", loaded_at).coalesce(1).write.mode(
                "overwrite"
            ).parquet(str(table_dir))
            normalize_parquet_filename(table_dir)
        persisted = {name: spark.read.parquet(str(output_dir / name)) for name in frames}
        reconciliation = reconcile(cached, persisted["q5_cities"])
        write_json(output_dir / "reconciliation.json", reconciliation)
        metrics = json.loads((silver_dir / "dq.json").read_text(encoding="utf-8"))
        quality_frames = {
            "data_quality_summary": spark.createDataFrame(
                quality_rows(metrics, reconciliation), schema=QUALITY_SCHEMA
            ),
            "data_quality_warning_samples": warning_samples(cached),
            "data_quality_merchant_conflicts": spark.read.parquet(
                str(silver_dir / "merchant_conflicts")
            ).orderBy("merchant_id"),
        }
        for name, frame in quality_frames.items():
            table_dir = output_dir / name
            add_load_metadata(frame, "gold", loaded_at).coalesce(1).write.mode(
                "overwrite"
            ).parquet(str(table_dir))
            normalize_parquet_filename(table_dir)
        render_report(persisted, results_dir / "report.md")
        render_previews(persisted, reconciliation, results_dir / "previews.md")
    finally:
        cached.unpersist(blocking=True)
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
